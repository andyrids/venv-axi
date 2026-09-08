---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs: []
authors: []
issues: [115]
pr: 139
---

# Plan: CI Python version matrix

## Scope

`pyproject.toml` declares `requires-python = ">=3.11"` and four `Programming Language :: Python`
classifiers (3.11, 3.12, 3.13, 3.14). `.github/workflows/ci.yml` pins `python-version: "3.13"` on
every leg of both test jobs, so **three of the four declared versions are never run** - run
33159569557 logs `Using CPython 3.13.15` on both `pytest` legs. The pin arrived with
[ci-platform-matrix](ci-platform-matrix.md) and was correct there: it made the OS axis vary exactly
one thing. It also left this gap exactly where it was, which is why #111 split resolution 2 out as
issue #115.

The claim is not generic. Every symbol record this tool emits is derived from `inspect` at runtime
against the caller's interpreter - `_introspect.py` builds each record from `inspect.signature`,
`inspect.getdoc` and an MRO walk - so the stdlib module most likely to move between releases is the
one the project is built on. Rendered signatures are stored in the cache and asserted verbatim
(`tests/test_introspect.py:381`), and `_store.py:34` records that a change in how a signature is
derived invalidates every stored graph. 3.14 is the sharp end: PEP 649/749 defer annotation
evaluation, `inspect.signature` renders annotations, and the PyPI listing already tells installers
3.14 is safe.

This unit adds a `python-version` axis to **both** test jobs - `pytest` and `conformance` - as an
asymmetric matrix: all four declared versions on `ubuntu-latest`, plus one `windows-latest` leg per
job that keeps the existing 3.13 pin. Eleven check runs where there are seven today.

**Why both test jobs and not `pytest` alone.** Issue #115's Scope names "the matrix axis" while two
jobs carry one, and its evidence is drawn from the `pytest` job. Extending to `conformance` is a
deliberate widening, for a reason the issue's own argument supplies: `uv.lock` resolves *different
third-party versions per interpreter* - `numpy` 2.4.6 under `python_full_version < '3.12'` against
2.5.2 under `>= '3.14'`, by the lock's own `resolution-markers`. The conformance tier is where
`inspect` meets real third-party code, which is the mechanism issue #115 is about, and pinning it to
one interpreter would leave the version claim verified over fixtures and unverified over the code
that found #64-#69. Confirmed by the user at the plan gate.

**Why `windows-latest` stays on 3.13.** Confirmed by the user at the plan gate. Issue #111 pinned it
deliberately so a red leg identifies the operating system and nothing else; moving it to the ceiling
would make a red Windows leg ambiguous between OS and interpreter, which is the property this axis
must not spend. Windows x 3.14 is covered by this unit's local pre-flight, not by CI - stated as a
Risk rather than glossed.

**No `pyproject.toml` change.** Resolution 4 of issue #115 - narrowing the declared range -
is contingent on a version being found genuinely unsupported. The pre-flight found none: all
four interpreters pass both tiers on Windows. `requires-python` and all four classifiers stay
as they are.

**The file-and-pin rule.** This unit touches `.github/workflows/ci.yml`, this plan and
`CHANGELOG.md`. No source, no test, no reference file. If a leg surfaces a defect it is filed and
pinned as its own issue, never repaired here - the precedent
[ci-conformance-tier](ci-conformance-tier.md) set for exactly this situation.

**Eligibility for `express-change`.** All three conditions in `ICM/express-change/CONTEXT.md` hold,
restated with reason:

1. **No spec change is required.** `specs/README.md` -> `## What specs cover` is invocation, inputs,
   outputs and failure modes of the tool. Which interpreters CI exercises is infrastructure, not
   behaviour `venvaxi` promises a caller - the same class of change as the four preceding units in
   this sequence ([ci-platform-matrix](ci-platform-matrix.md),
   [ci-conformance-tier](ci-conformance-tier.md), [ci-static-typing](ci-static-typing.md),
   [release-publish-gate](release-publish-gate.md)), none of which touched `specs/**`. Issue #115's
   own Scope reaches the same conclusion on the same reasoning. No Layer 3 reference is falsified
   either: no file under `ICM/_config/` states a pinned interpreter, so unlike `ci-conformance-tier`
   this unit needs no amendment there.
2. **One commit's worth**, with no new dependency and no new public surface. One `strategy.matrix`
   block per test job, one `python-version` expression, one `cache-suffix` extension - no new action
   pinned, no source or test change.
3. **Every Validation criterion can be evidenced within this run except those asserting on GitHub's
   own scheduling and check-run reporting**, which need a real PR. That is the identical situation
   `ci-platform-matrix` and `ci-conformance-tier` both recorded; the plan stays
   `status: in-progress` until that PR runs it. The pre-flight closes the question that could have
   broken condition 1: a red 3.14 leg needing a behaviour fix would have re-entered `process-plan`,
   and there is not one.

## Implements

Nothing in `specs/**`. This is CI configuration, the same class of change as the four CI units
preceding it in the 0.5.0 sequence, so `specs:` and `authors:` are both empty.

`docs/architecture.md:11` claims **Python >=3.11 (`StrEnum`, `tomllib` and PEP 604 unions are used
unguarded)** and is unchanged by this unit - the unit makes the claim checkable, it does not restate
it. `docs/architecture.md` is by its own header "documentation of the implementation's shape, not
specification".

## Approach

1. Open this plan at `status: in-progress`.
2. `.github/workflows/ci.yml`, `pytest` job - replace the OS-only matrix with the asymmetric shape:

   ```yaml
   strategy:
     fail-fast: false
     matrix:
       os: [ubuntu-latest]
       python-version: ["3.11", "3.12", "3.13", "3.14"]
       include:
         - os: windows-latest
           python-version: "3.13"
   ```

   `include` adds the Windows combination rather than filtering a cross-product, so the five
   legs are stated rather than derived. `fail-fast: false` stays, so one red interpreter does
   not cancel the other four.
3. Same job - `python-version: ${{ matrix.python-version }}` on the `astral-sh/setup-uv` step, and
   `cache-suffix: pytest-${{ matrix.os }}-${{ matrix.python-version }}` so no two legs share a
   `uv` cache. A shared cache across interpreters is the one way this axis could report a green
   leg for an environment it did not build.
4. `conformance` job - the identical matrix block, `python-version: ${{ matrix.python-version }}`,
   and `cache-suffix: conformance-${{ matrix.os }}-${{ matrix.python-version }}`. The specimen guard
   step and `uv run pytest -m conformance -v` are unchanged.
5. `static` job untouched - it is platform- and interpreter-independent and stays single-runner.
   "CI exercises 3.11-3.14" is true of the two test jobs, not of the workflow; recorded in Notes
   rather than implied.
6. Local pre-flight over all four interpreters on this Windows machine, in environments
   isolated from the project venv (`UV_PROJECT_ENVIRONMENT` under the session scratchpad,
   `uv sync --frozen --python <v>`), capturing verbatim for each: the resolved `sys.version`,
   the default tier, and the conformance tier. 3.11 and 3.14 are already captured; 3.12 and 3.13
   complete the set. Fix any failure in this unit only if it is in `ci.yml`; a source or test
   failure is filed and pinned per the file-and-pin rule above, and does not get `skipif`-ed
   away or given `continue-on-error`.
7. Confirm the axis cannot silently collapse: assert the workflow's four `python-version` entries
   equal the four `Programming Language :: Python` classifiers in `pyproject.toml`, and capture the
   comparison. A matrix that drifts from the declared range re-opens this issue quietly.
8. Run the repo toolchain gate - `uv run -m prek run --all-files` with this plan staged
   (`git add -N`), per the trap [ci-platform-matrix](ci-platform-matrix.md) recorded: prek reads
   git-tracked files, so an untracked plan is a green that never looked.
9. `CHANGELOG.md` `[Unreleased]` -> `Changed` - one entry for the version axis on both test jobs,
   citing issue #115.
10. Stop before closeout. The criteria asserting on GitHub's scheduling and check-run reporting need
    a real PR run; the plan stays `status: in-progress` until then.

## Validation

- [x] When a pull request targets `main` or `develop`, the CI workflow shall run the `pytest` job
      once on `ubuntu-latest` for each of Python 3.11, 3.12, 3.13 and 3.14. — PR #139 run
      34280163798 reports `pytest (ubuntu-latest, 3.11)`, `(ubuntu-latest, 3.12)`,
      `(ubuntu-latest, 3.13)` and `(ubuntu-latest, 3.14)`, all `pass`, where `develop` reports
      `pytest (ubuntu-latest)` alone
- [x] When a pull request targets `main` or `develop`, the CI workflow shall run the `conformance`
      job once on `ubuntu-latest` for each of Python 3.11, 3.12, 3.13 and 3.14. — run 34280163798
      reports `conformance (ubuntu-latest, 3.11)` through `(ubuntu-latest, 3.14)`, all `pass`;
      11 check runs total against 7 on `develop`
- [x] While the version axis runs, each leg shall resolve the interpreter its matrix entry names, so
      a leg's result identifies the Python version and nothing else. — run 34280163798, the four
      ubuntu `pytest` legs log `Using CPython 3.11.16`, `3.12.3`, `3.13.15` and `3.14.7` at the
      `uv sync` step
- [x] While the version axis runs, the `windows-latest` leg of each test job shall continue to
      resolve Python 3.13, so the platform axis issue #111 established stays one-variable. — run
      34280163798, both windows legs log `Using CPython 3.13.15 interpreter at:
      C:\hostedtoolcache\windows\Python\3.13.15\x64\python.exe`
- [x] Where Python 3.14 defers annotation evaluation under PEP 649, when the `pytest` job runs
      against it, the job shall complete with zero test failures. — run 34280163798
      `pytest (ubuntu-latest, 3.14)`: `622 passed, 32 deselected in 28.98s`, coverage
      `TOTAL 1352 24 98%`
- [x] When the `conformance` job runs against Python 3.11 and against Python 3.14, it shall complete
      with zero test failures over the different third-party versions `uv.lock` resolves for
      each. — run 34280163798 `conformance (ubuntu-latest, 3.11)`: `32 passed, 622 deselected,
      4775 warnings
      in 50.18s`; `conformance (ubuntu-latest, 3.14)`: `32 passed, 622 deselected, 4795 warnings in
      52.40s`
- [x] While the version axis runs, each leg shall restore a `uv` cache keyed to its own interpreter
      version, so no leg reports on an environment another leg built. — run 34280163798, each leg
      resolves its own suffix (`cache-suffix: pytest-ubuntu-latest-3.11` against
      `pytest-ubuntu-latest-3.14`) and saves under it: `uv cache saved with key:
      setup-uv-2-x86_64-unknown-linux-gnu-ubuntu-24.04-3.11-<hash>-pytest-ubuntu-latest-3.11`.
      Key separation is what is evidenced, not a restore - see Notes
- [x] The `python-version` values in `.github/workflows/ci.yml` shall equal the Python versions
      `pyproject.toml` declares a `Programming Language :: Python` classifier for. — a comparison
      over both the array and `include:` scalar forms of `python-version` against the
      `Programming Language :: Python` classifiers reports both sides
      `['3.11', '3.12', '3.13', '3.14']` and `equal: True`
- [ ] If the suite fails on one interpreter only, then the workflow shall report the check run as
      failed rather than succeeded.

## Risks / unknowns

- **Five criteria need a real PR.** Criteria 1-4, 7 and 9 assert on GitHub Actions' own scheduling,
  interpreter resolution and check-run reporting. The local pre-flight predicts criteria 5 and 6 and
  evidences them for *this machine*, but the matrix's own behaviour cannot be produced here - the
  same limit `ci-platform-matrix` and `ci-conformance-tier` both recorded.
- **Criterion 9 will probably stay un-triggered.** Its trigger is a red leg, and the pre-flight
  found none. `ci-platform-matrix` left the identical box unticked rather than arguing it
  from the YAML, and this unit follows that: `fail-fast: false` with no `continue-on-error`
  is a reading of the file, not a run.
- **Check-run names change again, and issue #136 names the old spellings.** Five legs per
  test job renames `pytest (ubuntu-latest)` to `pytest (ubuntu-latest, 3.11)` and so on. Issue
  #136's resolution 2 quotes `pytest (ubuntu-latest)`, `pytest (windows-latest)`,
  `conformance (ubuntu-latest)` and `conformance (windows-latest)` verbatim as the ruleset
  entries it would add - all four spellings become wrong the moment this lands. The `verify-ci`
  job in `release.yml` is unaffected: it resolves the *workflow run's* conclusion by SHA, never a
  check-run name, which is the property issue #110 chose it for. Recorded as a Follow-up against
  issue #136.
- **Windows x 3.14 is not in CI.** The Windows leg stays pinned at 3.13 by decision, so the
  interpreter with the sharpest semantic change is exercised in CI on Linux only. This unit's
  pre-flight covers Windows x 3.11 and x 3.14 locally, which is evidence for today and not a
  standing gate. If a Windows-conditional 3.14 defect ever ships, that gap is the reason and
  the fix is a second `include` entry.
- **The pre-flight was green, and issue #115 predicted 3.14 would go red.** That is a weaker
  result than it looks: it says the suite passes against the interpreter and dependency versions
  resolved on the pre-flight date, on one operating system, and nothing more. The value of the
  axis is that the next interpreter or annotation-semantics change is caught by CI rather than
  by an installer following the PyPI classifiers.
- **Coverage is measured per leg with nothing combining it.** Each `pytest` leg runs
  `coverage run`, `report` and `xml` independently, so five reports are produced and none is
  merged. Nothing consumes `coverage.xml` today, so no `coverage combine` is added; `src/`
  carries no `sys.version_info` branch, so the per-leg totals should agree, and a disagreement
  would itself be worth investigating.
- **Runner minutes**: eleven legs where there are seven. The repository is public, so the cost is
  zero today; the Windows legs remain the ~2x-slower ones and neither is multiplied by this unit.

## Notes

**Eight of nine boxes ticked; the ninth is un-triggered, not satisfied.** Criterion 9 is an
`If <trigger>, then` over a red leg, and all eleven check runs passed on the first attempt. A
structural argument exists - `fail-fast: false` with no `continue-on-error` anywhere - but that is a
reading of the YAML, not a run, and [ci-platform-matrix](ci-platform-matrix.md) set the convention
of leaving such a box unticked rather than arguing it. Its own identical box is still open two units
later, which is the honest state of affairs: nothing has yet gone red on one leg only.

**Issue #115 expected 3.14 to go red and it did not.** All four interpreters pass both tiers, in CI
and in the local Windows pre-flight. Read narrowly: the suite passes against the interpreter and
dependency versions resolved on 2026-09-08, and that is all. The value of the unit is that the next
`inspect` or annotation-semantics change is caught by CI rather than by an installer who trusted the
classifiers. Worth noting the prediction was reasonable and the pre-flight is *why* it was cheap to
disprove - the eligibility call under `express-change` depended on knowing before writing the plan,
since a red 3.14 needing a behaviour fix would have re-entered `process-plan` at stage 01.

**PEP 649 changes what `coverage` counts, and the Risks section predicted the symptom without the
cause.** The 3.14 leg reports `TOTAL 1352` statements where 3.11, 3.12, 3.13 and Windows all report
`TOTAL 1385` - a 33-statement gap. This plan's Risks said `src/` carries no `sys.version_info`
branch so the per-leg totals "should agree, and a disagreement would itself be worth investigating".
They disagreed, so it was investigated, and the cause is exact:

| Module | 3.13 | 3.14 | Delta | Bare class-body annotations |
| --- | --- | --- | --- | --- |
| `_cache.py` | 95 | 87 | -8 | 8 |
| `_core.py` | 40 | 39 | -1 | 1 |
| `_introspect.py` | 300 | 291 | -9 | 9 |
| `_packages.py` | 70 | 67 | -3 | 3 |
| `_store.py` | 154 | 142 | -12 | 12 |
| **Total** | **1385** | **1352** | **-33** | **33** |

An `ast` walk counting `AnnAssign` nodes with no value inside a `ClassDef` matches the delta module
for module, with no residual. PEP 649 compiles class-body annotations into a lazily evaluated
`__annotate__` function, so a bare `qualified_name: str` is no longer an executed statement at class
creation time and `coverage` stops counting it. **This is a measurement artifact, not a coverage
regression**: misses are identical at 24 on every leg, and the percentage is 98% on all five. It is
also a neat confirmation of the issue's own argument for testing 3.14 - the interpreter change it
named as the risk is observable in this project's numbers, just not where anyone was looking.

**`cache-suffix` was not load-bearing, and the plan overstated it.** Approach step 3 justified the
suffix as "the one way this axis could report a green leg for an environment it did not build". The
saved key is
`setup-uv-2-x86_64-unknown-linux-gnu-ubuntu-24.04-3.11-<hash>-pytest-ubuntu-latest-3.11`, and
`setup-uv` already interpolates the interpreter version (`-3.11-`) ahead of our suffix.
Cross-version cache collision was therefore not possible before this change either. The suffix
still earns its place - it keys the cache per job as well as per version, and makes the key legible
in the log - but the stated justification was wrong and is corrected here rather than left
standing.

**Criterion 7 evidences key separation, not a restore.** Every suffix is new on the first run, so
every leg necessarily missed and `saved` rather than `restored`. The observable the criterion exists
for - no two legs sharing a key - is fully evidenced; the word "restore" will only be literally
true from the second run on. Worth stating rather than ticking past.

**One leg resolves the runner's system interpreter, not a uv-managed build.** The 3.12 legs log
`Using CPython 3.12.3 interpreter at: /usr/bin/python3.12`, where 3.11, 3.13 and 3.14 log a
uv-downloaded build with no path. The matrix entry is satisfied - 3.12.3 is 3.12 - so criterion 3
holds, but patch-level provenance is not uniform across the axis and a 3.12-only failure would be
worth checking against the runner image before the code.

**CI and the pre-flight disagree on patch level for 3.13.** Local ran `3.13.7` (already installed on
the machine); CI resolves `3.13.15`. Both satisfy the matrix entry. Recorded because the pre-flight
is cited as evidence in this plan and a future reader re-running it will not get the same build.

**Windows x 3.14 is exercised nowhere on a standing basis.** The Windows leg stays pinned at 3.13 by
decision at the plan gate, so the interpreter with the sharpest semantic change runs in CI on Linux
only. The local pre-flight covers Windows x 3.11 and x 3.14 and passed, which dates that
combination rather than gating it. If a Windows-conditional 3.14 defect ever ships, this paragraph
is the reason, and the fix is one more `include` entry.

**Why the axis went on both test jobs.** `uv.lock` resolves different third-party versions per
interpreter, so `conformance` is not a redundant multiplication of `pytest` - it walks different
real code on each leg. The differing warning counts across legs (4775 on 3.11, 4795 on
3.12/3.13/3.14 ubuntu, 4771 on Windows 3.13) are the visible trace of that. Cost was negligible:
the four ubuntu `conformance` legs ran 1m7s to 1m12s in parallel.

**The changelog entry landed in the implementation commit, not the closeout commit.** This plan's
Approach put it at step 9, before "stop before closeout" at step 10, and that is what was done. The
immediately preceding unit ([skill-gate-parser-access](skill-gate-parser-access.md)) landed its
entry in the closeout commit instead, and the `ICM/express-change` stage contract lists the
changelog under closeout. Both readings are live in the repo now; worth settling in the contract
rather than per plan, since the difference decides whether a changelog entry can describe a run that
has not happened yet.

**The review found two defects in the implementing agent's output**, both in `CHANGELOG.md`, both
corrected before the commit. The entry claimed "three of the four interpreters they name are now
exercised" - four are; three were previously unexercised, so the sentence inverted its own point.
Separately, the matrix/classifier check written to evidence criterion 8 read only the
`python-version: [...]` array form, so it would have passed even had the `include:` Windows pin
named an undeclared version, which is the one drift that criterion exists to catch. The citation
above is the corrected check, reading both forms. Recorded because it is the same shape as the
defect this whole CI sequence keeps closing: a check that reports success over something it never
examined.

## Follow-ups

- **Issue** [#136](https://github.com/andyrids/venv-axi/issues/136) - the GitHub-side publish gate.
  **Updated in this unit rather than only noted**: its resolution 2 quoted `pytest (ubuntu-latest)`,
  `pytest (windows-latest)`, `conformance (ubuntu-latest)` and `conformance (windows-latest)`
  verbatim as the ruleset entries to add, and all four spellings ceased to exist here. The body now
  lists the eleven real names and records that the name-drift risk resolution 2 has to "accept" is
  no longer hypothetical - the names have now drifted twice in this milestone, once per axis, each
  time silently invalidating every ruleset entry with no failure at the point of breakage. Adding or
  dropping a supported Python version rewrites five of the eleven. That is an argument for
  weighting resolution 1, which gates the `pypi` environment and names no checks at all.
- **Issue** [#117](https://github.com/andyrids/venv-axi/issues/117) - four prek hook families
  enforced only by local developer configuration. The last remaining "a claim CI enforces by
  nothing" issue that touches `ci.yml` itself. It lands against an eleven-leg matrix now, and its
  hooks are interpreter-independent, so it belongs on `static` rather than on either test job -
  worth deciding explicitly rather than by default.
- **Issue** [#120](https://github.com/andyrids/venv-axi/issues/120) - nothing exercises the `mcp`
  extra's declared floor. This unit multiplies the interpreter axis by nothing else; #120 adds a
  *dependency-version* axis, and crossing the two would be 8 legs per job for a floor claim. The
  precedent set here - asymmetric, cheapest platform carrying the widest axis - is the shape to
  reuse rather than a cross-product.
- **Deferred to** - none.
- **Tracked as** - none. The PEP 649 coverage artifact is documented in Notes and needs no issue:
  nothing consumes `coverage.xml`, no statement went uncovered, and per-leg totals are not compared
  by any gate.
