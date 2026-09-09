---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs: []
authors: []
issues: [117]
pr: 140
---

# Plan: CI prek suite

## Scope

`prek.toml` declares eight hooks. `.github/workflows/ci.yml`'s `static` job runs three of them, and
not through prek: it calls the `pkgdx` console scripts directly, as `uv run pkgdx-lint-hook`,
`uv run pkgdx-format-hook` and `uv run pkgdx-typing-hook -p venvaxi`. Five hooks therefore run only
where a contributor has run `uv run prek install` on their own machine: `pkgdx-markdown`,
`pkgdx-secrets`, and the three prek builtins `check-toml`, `check-yaml` and `detect-private-key`. A
markdown violation, a committed credential, a malformed `prek.toml` and a malformed workflow file
all reach `develop` unchallenged by anything automated.

This unit replaces the three console-script steps with one step that runs the suite `prek.toml`
declares, `uv run -m prek run --all-files`, preceded by a step that pins prek's hook environments to
`uv.lock` and followed by a failure-only diagnostic step for the one hook whose failure names no
file. Nothing else in the workflow moves.

**Resolution 2 of issue #117 is unworkable, and that is why the whole suite is run instead.** That
resolution proposed adding the two missing `pkgdx` console scripts as further CI steps, spelled the
way the existing three are spelled. It cannot reach the same set of gates, for two separate reasons:

1. The three builtins live inside prek's own Rust binary. `check-toml`, `check-yaml` and
   `detect-private-key` are not `pkgdx` entry points and expose no console script at all, so no
   number of `uv run pkgdx-*-hook` steps ever runs them.
2. `pkgdx-secrets-hook` invoked with no filenames scans nothing and exits 0. Prek supplies each
   hook's file list from git; a console script called argless has no list, so the step would be a
   security gate that is green because it looked at nothing. That is worse than the gap it closes,
   because a vacuously green gate is the reason nobody looks again.

Running the suite through prek answers both: prek supplies the file lists, and the builtins are its
own.

**`UV_CONSTRAINT` is load-bearing, not a tidiness measure.** Prek builds each hook's environment
itself and never reads `uv.lock`, and `pkgdx` constrains its tools with lower bounds only. Measured
this session: `uv.lock` pins ruff 0.16.1 and mypy 2.3.0, and a fresh unconstrained hook environment
resolved ruff 0.16.6 and mypy 2.3.1. Unconstrained, a tool release alone turns `static` red on a
tree nobody has touched, and the commit that fails for it is innocent. Exporting the lock to a
constraints file and pointing `UV_CONSTRAINT` at it makes a fresh environment resolve 0.16.1 and
2.3.0, the versions the project itself resolves, so the only thing that can turn the job red is the
diff under test.

**The format step never gated, and this change fixes that incidentally.**
`uv run pkgdx-format-hook` argless, exactly as `ci.yml` runs it, is `ruff format` with no `--check`:
measured on a misformatted file it reformatted the file in place and exited 0. CI has been reporting
a green format check while silently rewriting a tree nothing reads afterwards, which is to say there
has been no format gate at all. Under prek the same hook carries `--exit-non-zero-on-format` from
its hook definition, so replacing the step converts it into a gate without anything in this unit
being aimed at it. Recorded here rather than left as a pleasant side effect, because it is another
instance of the shape this CI sequence keeps closing: a check reporting success over something it
never examined.

**The file-and-pin rule.** This unit touches `.github/workflows/ci.yml` (the `static` job alone),
three Layer 3 toolchain references, this plan and `CHANGELOG.md`. It does not touch `prek.toml`,
which `ICM/_config/reference-toolchain-prek.md` forbids hand-editing and requires re-running
`pkgdx init` to change, nor `pyproject.toml`, `uv.lock`, `src/`, `tests/`, `specs/`, or the `pytest`
and `conformance` jobs. If a newly-running hook surfaces a defect it is filed and pinned as its own
issue, never repaired here, per the precedent [ci-conformance-tier](ci-conformance-tier.md) set.

**Eligibility for `express-change`.** All three conditions in `ICM/express-change/CONTEXT.md` hold,
restated with reason:

1. **No spec change is required.** Nothing under `specs/` moves. `specs/README.md` scopes specs to
   invocation, inputs, outputs and failure modes of the tool; which hooks CI enforces is
   infrastructure, not behaviour `venvaxi` promises a caller. This is the same class of change as
   the five CI units preceding it in the 0.5.0 sequence
   ([ci-platform-matrix](ci-platform-matrix.md), [ci-conformance-tier](ci-conformance-tier.md),
   [ci-static-typing](ci-static-typing.md), [release-publish-gate](release-publish-gate.md),
   [ci-python-version-matrix](ci-python-version-matrix.md)), none of which touched `specs/`. Three
   Layer 3 references are amended, all `immutable: true`, because this change makes what they say
   false; that is a deliberate act rather than a passing one, following the precedent
   [ci-conformance-tier](ci-conformance-tier.md) set when it amended
   `ICM/_config/reference-toolchain-pytest.md` in the same commit as the job that falsified it.
2. **One commit's worth**, with no new dependency and no new public surface. prek already arrives
   transitively: `pkgdx` declares `Requires-Dist: prek~=0.4.8`, `uv.lock` records `prek==0.4.12`,
   and `uv run -m prek` resolves from the synced environment today. Nothing is added to
   `pyproject.toml`. Three steps are replaced by three steps, in one job.
3. **Every Validation criterion can be evidenced within this run except those needing a real PR.**
   Criterion 1 asserts on GitHub Actions' own scheduling and check-run reporting for a pull request,
   which cannot be produced on this machine; the plan stays `status: in-progress` until that run
   happens, the identical situation [ci-platform-matrix](ci-platform-matrix.md),
   [ci-conformance-tier](ci-conformance-tier.md) and
   [ci-python-version-matrix](ci-python-version-matrix.md) each recorded. The remaining criteria are
   produced locally in this run, under the same `UV_CONSTRAINT` and against an isolated `PREK_HOME`
   so the machine's real hook cache is not consulted or written.

## Implements

Nothing under `specs/`. This is CI configuration plus the three toolchain-reference amendments the
change makes true, the same class of change as the five CI units preceding it, so `specs:` and
`authors:` are both empty.

`ICM/_config/reference-toolchain-prek.md` is amended rather than authored, so it does not belong in
`authors:` either: that field is for `specs/`, and a Layer 3 reference is factory configuration.

## Approach

1. Open this plan at `status: in-progress`.
2. `.github/workflows/ci.yml`, `static` job only - remove the three console-script steps and add
   three in their place. `checkout`, `setup-uv` and `uv sync` are untouched, as are the `pytest` and
   `conformance` jobs.
3. `Pin prek's hook environments to uv.lock` - export the lock's pins to
   `${{ runner.temp }}/constraints.txt` with
   `uv export --frozen --no-hashes --no-emit-project --no-emit-package pkgdx`. The file is written
   to the runner's temp directory, never into the repository, so the tree the hooks then check is
   still the checked-out commit. `--frozen` keeps the export from re-resolving the lock.
   `--no-emit-package pkgdx` is required, not cosmetic: prek clones the hook repository without
   tags, so the version its `hatch-vcs` configuration derives is not the `0.2.0` `uv.lock` records,
   and a constraint pinning `pkgdx==0.2.0` makes the hook environment unsolvable.
4. `Run every prek hook` - `uv run -m prek run --all-files` with `UV_CONSTRAINT` set to that file,
   carrying `id: hooks` so the diagnostic step can read its outcome. Run at prek's default stage,
   which is what includes the `stages: [pre-commit]` secrets hook: `--dry-run` lists eight hooks at
   the default stage and seven under `--stage pre-push`. No `--skip`, and no `continue-on-error`.
5. `Locate a PyMarkdown tokenizer crash` - guarded by `if: failure() && steps.hooks.outcome ==
   'failure'`, running the per-file bisection loop `ICM/_config/reference-toolchain-pymarkdown.md`
   documents and emitting a `::error file=` annotation for each file that reproduces
   `BadTokenizationError`. It ends `exit 0`: it is a diagnostic, and the hook step above it is the
   gate. When the markdown failure was an ordinary rule violation it prints one line saying so and
   annotates nothing, because prek has already named file, line and rule.

   The loop is guarded by one whole-suite `prek run pkgdx-markdown --all-files`, and only runs when
   that reproduces `BadTokenizationError`. Without the guard every ruff or mypy failure - the
   common case, which reproduces no crash - paid the full per-file bisection to conclude nothing.
   Measured: 5.9s to short-circuit against 1m33s to run the loop. The guard deliberately does not
   read the hook step's own output, because capturing it through `tee` would make the gate's exit
   status depend on `pipefail`, and a gate that can pass for a shell reason is the defect this unit
   exists to remove.
6. Amend the three Layer 3 references the change falsifies.
   `ICM/_config/reference-toolchain-prek.md` gains a `## CI` section naming the step that runs the
   suite and the `UV_CONSTRAINT` pin, so the file no longer reads as though a local `prek install`
   were the only enforcement; its Commands list and its `prek.toml` no-hand-edits rule are
   unchanged. `ICM/_config/reference-toolchain-pymarkdown.md` keeps the bisection recipe verbatim,
   since CI now runs that recipe unchanged, and gains a paragraph saying so. Ruff's Commands entry
   for `pkgdx-format-hook` records that it rewrites and exits 0 whatever it finds, so it formats but
   does not gate.
7. Demonstrate each failure criterion by causing it, per the specimen-guard precedent
   [ci-conformance-tier](ci-conformance-tier.md) set, capturing verbatim: a misformatted Python file
   against the argless console script and then against prek; a pipe inside a nested list item
   against prek and then against the diagnostic loop; an over-length markdown line against the loop,
   which must stay silent; a fabricated AWS-style key against the secrets hook. Every experiment
   runs against a scratch `PREK_HOME`. Each induced change is reverted with `git checkout --` and
   re-verified, and `.secrets.baseline` is confirmed unmodified afterwards.
8. Run the repo toolchain gate with this plan staged (`git add -N`), per the trap
   [ci-platform-matrix](ci-platform-matrix.md) recorded: prek reads git-tracked files, so an
   untracked plan is a green that never looked at it.
9. `CHANGELOG.md` `[Unreleased]` and `Changed` - one entry citing issue #117.
10. Stop before closeout. Criterion 1 needs a real PR run; the plan stays `status: in-progress`
    until then.

## Validation

- [x] When a pull request targets `main` or `develop`, the `static` job shall run every hook
      `prek.toml` declares. — PR #140 run 34392992600, `static`: all eight hooks report `Passed`
      in one `uv run -m prek run --all-files` step (`Lint [Ruff]`, `Format [Ruff]`,
      `Check Markdown [PyMarkdown]`, `Typing [Mypy]`, `Detect Secrets [detect-secrets]`,
      `Check TOML`, `Check YAML`, `Detect PEM`), where `develop` ran three console-script steps
- [x] While the `static` job runs, each hook environment shall resolve the tool versions `uv.lock`
      pins, so a new tool release cannot turn CI red on an unchanged tree. — two halves, and
      neither alone is the whole claim. The configuration is verified in CI: run 34392992600 logs
      the export step and `UV_CONSTRAINT: /home/runner/work/_temp/constraints.txt` on the hook
      step. The effect is verified locally, since the CI log does not print hook-environment
      versions: with `UV_CONSTRAINT` set to the export, a fresh `PREK_HOME` built ruff 0.16.1 and
      mypy 2.3.0, matching `uv.lock`; the control with `UV_CONSTRAINT` unset built ruff 0.16.6 and
      mypy 2.3.1. See Notes on what this box does not evidence
- [x] While the `static` job runs, `detect-secrets` shall execute over the tracked files rather than
      be skipped. — run 34392992600 reports `Detect Secrets [detect-secrets]....Passed`, not
      `Skipped`; `uv run -m prek run --all-files --dry-run` lists eight hooks at the default stage
      against seven under `--stage pre-push`, the omitted one being this hook
- [x] If a tracked Python file is misformatted, then the `static` job shall fail rather than
      reformat it and report success. — misformatting `src/venvaxi/__init__.py`, then
      `uv run -m prek run --all-files`: `Format [Ruff]....Failed`, `exit code: 1`,
      `files were modified by this hook`. The superseded form on the same input:
      `uv run pkgdx-format-hook` reports `1 file reformatted` and exits `0`
- [x] If a tracked markdown file crashes PyMarkdown's tokenizer, then the `static` job shall report
      that file's path rather than a diagnostic naming no file. — restoring the issue #20
      reproducer at `ICM/express-change/CONTEXT.md:46` (`'approved' | 'continue'`), the hook reports
      only `Unexpected Error(BadTokenizationError)`; the diagnostic step body then emits
      `::error file=ICM/express-change/CONTEXT.md::PyMarkdown BadTokenizationError somewhere in
      this file (issue #20)` and exits 0. Reverted to blob `9747458f`
- [x] If the markdown hook fails on an ordinary rule violation, then the diagnostic step shall add
      no annotation, since prek already names file, line and rule. — an over-length line reports
      `MD013: Line length [Expected: 100, Actual: 185]` with its file and line, and the diagnostic
      step's guard short-circuits in 5.9s printing `No tokenizer crash`, emitting no annotation
- [x] `ICM/_config/reference-toolchain-prek.md` shall name the CI step that runs the suite and shall
      no longer imply the suite is enforced only by a local install. — the file gains a `## CI`
      section naming the `Run every prek hook` step, its `--all-files` invocation and the
      `UV_CONSTRAINT` pinning that precedes it

## Risks / unknowns

- **Criterion 1 needs a real PR run.** It asserts on GitHub Actions' scheduling and check-run
  reporting, which cannot be produced on this machine. The other six are evidenced locally in this
  run, against a scratch `PREK_HOME` under the same `UV_CONSTRAINT` the job sets, so what they
  evidence is the mechanism rather than the runner.
- **The diagnostic loop runs prek once per markdown file.** 107 tracked files, measured at 1m33s
  this session, and only when the guard ahead of it reproduces a crash - a failure that is not a
  tokenizer crash costs 5.9s instead. A green run never pays either. The loop grows with the
  repository, and the point at which it is slower than reading the crash by hand is the point at
  which it should be narrowed to the pull request's changed files rather than every tracked file.
- **prek cold-clones the hook repository and builds its environments**, where the three
  console-script steps ran inside the already-synced project environment. Measured cold against a
  fresh `PREK_HOME` on this machine: 40s for `prek prepare-hooks`, against a `static` job that
  completes in roughly 25s today. No `actions/cache` step is proposed. Measure the real number on
  the first PR run first, and note before anyone adds one that a cache over `PREK_HOME` would freeze
  the resolved tool versions invisibly: `UV_CONSTRAINT` would stop being what decides them, and a
  lock bump would not be picked up until something evicted the cache.
- **The `pkgdx` exclusion from the constraints export is a hand-maintained exception.** It is there
  because prek's clone carries no tags, so the built version disagrees with the lock and the pin is
  unsatisfiable. Any future dependency a hook environment installs from source rather than from an
  index needs the same exception. It announces itself the way this one did, with
  `No solution found when resolving dependencies` at the first hook, which is the failure mode to
  prefer over a silent one.
- **`--skip` fails open.** An unmatched `--skip` selector warns and then runs everything, so a
  design that excluded a hook by name would silently start running it again after any rename. This
  design uses no `--skip` for that reason: the set of enforced hooks is decided in `prek.toml` and
  nowhere else, which is also what keeps this job honest when a hook is added there.
- **`::error file=` carries no line number**, so GitHub anchors the annotation at line 1 of the
  named file. The tokenizer crash supplies no line to carry, which is the whole reason the
  diagnostic exists, so the message says "somewhere in this file" and the annotation cannot be
  misread as pointing at its first line.
- **CI's working tree is no longer the checked-out commit.** prek runs hooks concurrently, and
  `pkgdx-lint` and `pkgdx-format` write. Both are `pass_filenames: false`, so ruff runs over `.` and
  may rewrite anything it dislikes. The job fails when they do, so a rewrite is never mistaken for
  success, and the runner is discarded immediately after. Harmless and ephemeral, but recorded: a
  step added to `static` after the hook step cannot assume it is looking at the commit under test.
- **The gitlab coupling is not new.** `prek.toml` resolves its hooks from
  `gitlab.com/andyrids/pkgdx` at `rev = "v0.2.0"`, and `uv.lock` already resolves `pkgdx` itself
  from the same host, so `uv sync` has depended on gitlab being reachable since well before this
  unit. What is new is that CI performs a clone as well as a wheel resolution. The tag was confirmed
  publicly cold-clonable this session.
- **Eight hooks means eight ways for an unrelated tool to have an opinion.** Three of them have
  never run over this repository in CI, and `check-yaml` in particular now reads every workflow
  file. The baseline run is green, so nothing is filed and pinned, but that dates the result rather
  than guaranteeing it: the hooks are pinned to `uv.lock` now, and the next lock bump is the next
  time their opinions can change.

## Notes

**Seven of seven boxes ticked, which is unusual for this sequence** - the four preceding CI units
each froze with at least one un-triggered box. The difference is that every failure criterion here
was evidenced by *causing* the failure rather than waiting for one, following the specimen-guard
demonstration [ci-conformance-tier](ci-conformance-tier.md) did: a misformatted file, a restored
issue #20 reproducer, an over-length markdown line, a fake credential. A guard nobody has seen fail
is a guard nobody has checked.

**What criterion 2's box does not evidence.** The CI log prints no hook-environment versions, so the
run cannot show that ruff 0.16.1 rather than 0.16.6 was the one that ran. What CI evidences is that
the configuration is in force - the export step ran and `UV_CONSTRAINT` is on the hook step - and
what the local constrained/control pair evidences is that the configuration has the claimed effect.
The chain is complete but it is a chain, not one observation, and the box is ticked on that basis
deliberately rather than quietly. Making it a single CI observation is cheap and is a Follow-up.

**The cost prediction was wrong, and the reason is worth keeping.** This plan's Risks predicted 40s
of environment building against a ~25s job, so roughly a doubling. Measured on run 34392992600:
`static` completed in 33s against 18s, 21s and 21s on the three preceding `develop` runs - about
+12s, and the whole prek step took 24.4s including cold hook-environment builds. The reason is that
`setup-uv` sets `UV_CACHE_DIR` to a directory it caches on `uv.lock`, and prek builds its hook
environments with `uv pip install`, so they draw wheels from that restored cache instead of the
network. The local 40s figure was measured against a cache that had to fetch and build `pkgdx`'s
sdist. Two consequences: the cost is a rounding error rather than a doubling, and a dedicated
`actions/cache` over `PREK_HOME` is now clearly not worth adding - the caching that matters is
already there and is keyed on the lock, which is the correct key.

**The approved design would have failed on its first run, and the implementing agent caught it.**
The constraints export includes `pkgdx==0.2.0`, and that line makes every hook environment
unsolvable, so `static` would have failed at the first hook with `No solution found when resolving
dependencies`. The root cause is general and worth knowing beyond this unit: prek clones hook
repositories **without tags**, so any hook repository versioned by `hatch-vcs` or `setuptools-scm`
builds at a version its own lock entry disagrees with. `--no-emit-package pkgdx` is the fix. The
verification that authorised the design used a two-line constraints file and could not have found
this; only the real export did. The general lesson is that a verification narrower than the thing
shipped is not a verification of it.

**Why the diagnostic loop is guarded, and why not with `tee`.** Unguarded, the loop ran on any hook
failure, so a ruff or mypy failure - the common case - paid the full per-file bisection to conclude
nothing. Measured: 5.9s to short-circuit against 1m33s to bisect, a fifteenfold difference on the
failure people actually hit. The obvious guard is to capture the hook step's output with `tee` and
grep it, and that was rejected: piping the gate makes its exit status depend on `pipefail` being in
force, and a gate that can pass for a shell reason is exactly the defect this unit removes. One
extra whole-suite markdown run costs 5.9s and touches the gate not at all.

**The format step had never gated anything.** `uv run pkgdx-format-hook` argless is `ruff format`
with no `--check`. Measured on a deliberately misformatted `src/venvaxi/__init__.py`:
`1 file reformatted`, exit 0, and a clean `git diff` afterwards, because the rewrite had already
happened. So `140 files left unchanged` in the old CI log was an unconditional message rather than a
result, and [ci-static-typing](ci-static-typing.md) quotes it without anything being wrong with that
plan - the message simply cannot fail. This is filed under `Fixed` in `CHANGELOG.md` rather than
folded into the `Changed` entry, because it is a defect repair and not a change of approach.

**`detect-secrets` gates Python files only.** The hook carries `types_or: ["python", "pyi"]`, so a
credential in a YAML, JSON, `.env` or markdown file is still never checked, while the `Justfile`
`secrets-baseline` recipe scans the whole repository. The asymmetry is sharper than a coverage gap:
a baseline regeneration would *record* such a secret while nothing ever *gates* it. This unit
therefore enforces the security control issue #117 partly rests on, but only over Python, and says
so rather than claiming the broader gate. Widening it needs `prek.toml`, which
`ICM/_config/reference-toolchain-prek.md` forbids hand-editing, so the fix belongs upstream in
`pkgdx`; filed as a Follow-up.

**Three `immutable: true` references were amended**, more factory-configuration churn than any
earlier unit in this sequence. Each is small and each was false or incomplete without it: the prek
reference implied local enforcement was the only enforcement, the pymarkdown reference gave a
bisection recipe a contributor no longer has to run by hand, and the ruff reference described
`pkgdx-format-hook` as formatting the codebase without saying it never gates - which is the gap that
let the CI defect through in the first place.

**The review corrected one thing in the implementing agent's output**: the format-gate defect was
written into the `Changed` entry, where a bug fix is not what a reader of `Changed` is looking for.
Split into `Fixed`. Its own report flagged the `pkgdx` deviation, the loop-cost weakness and the
`tee` trade-off unprompted, which is what made those three decidable rather than discovered later.

## Follow-ups

- **Issue to file** - `pkgdx-secrets` scans Python files only (`types_or: ["python", "pyi"]`), so
  `detect-secrets` gates no YAML, JSON, `.env` or markdown file even though the `Justfile` baseline
  recipe scans all of them. The fix belongs in `pkgdx`'s `.pre-commit-hooks.yaml` upstream, since
  `prek.toml` must not be hand-edited and `pkgdx init` would revert a local widening. Worth noting
  in that issue that a locked repo-wide alternative exists without touching `prek.toml`, passing
  `git ls-files` output to `detect-secrets-hook` directly, and was rejected here as hand-rolling
  the file selection prek already does.
- **Issue** [#20](https://github.com/andyrids/venv-axi/issues/20) - the PyMarkdown tokenizer crash
  stays open and unmilestoned. This unit makes its failure legible, not fixed: CI now names the file
  rather than nothing. Its own resolution 1, narrowing the reproducer and reporting upstream, is
  unchanged and is still the only thing that removes the trap. The reproducer was restored and
  reverted in this run, so it is confirmed to still reproduce on `pymarkdownlnt` 0.9.39.
- **Making criterion 2 a single CI observation** - the hook environments' resolved tool versions are
  not printed by the run, so the pin is evidenced by a chain rather than an observation. A step that
  prints the versions from the built environments would close that, and is worth adding the first
  time the pin actually matters, which is a lock bump a hook environment fails to follow.
- **Issue** [#136](https://github.com/andyrids/venv-axi/issues/136) - unaffected. `static` keeps its
  check-run name, so the eleven names that issue now lists are still correct, and `release.yml`'s
  `verify-ci` resolves the workflow run's conclusion by SHA rather than any check name.
- **Deferred to** - none.
- **Tracked as** - none.
