---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: [71]
pr:
---

# Plan: real-dependency-conformance

## Scope

Add a marker-gated conformance tier that walks real installed dependencies, so a pathology only
third-party code exhibits can fail the suite. Every introspection test today walks
`tests/resources/package/`, a fixture this repository wrote - small, well-behaved, pure Python -
so issues 64, 65, 66, 67, 68 and 69 were all found by dogfooding a published release rather than
by the 370-test suite (issue 71).

**Eligibility for express-change.** All three conditions in `ICM/express-change/CONTEXT.md` hold.

1. **No spec change is required.** `specs/**` covers observable behaviour of the tool, not test
   strategy; no criterion in any spec changes. The tier asserts contracts those specs already
   declare. `ICM/_config/reference-toolchain-pytest.md` is amended, which is an `immutable: true`
   Layer 3 reference and therefore a deliberate amendment rather than a passing one, but it is
   configuration of the factory and not a spec.
2. **One commit's worth**, with no new public surface. Two packages are added to the `dev`
   dependency group. Per the maintainer's ruling this is distinct from a dependency: a dev-group
   test dependency ships nothing to a consumer, cannot reach an install, cannot widen the API and
   cannot affect a downstream resolve, so the risk the condition guards is not present.
3. **Every Validation criterion is evidenced within this run** - see the note on the expected
   failure under Approach, which is why the criteria below assert the tier's isolation and
   execution rather than the truth of every invariant it carries.

Out of scope: fixing anything the tier finds. A newly-surfaced defect is filed and pinned, not
repaired here - repairing it would be the scope growth that means the eligibility call was wrong.
Also out of scope: anything owned by issues 82, 67, 68, 49 or 50.

## Implements

Nothing in `specs/**`; this plan is test-strategy work, which is why both `specs:` and `authors:`
are empty. It is the same class of change as a toolchain configuration amendment.

The invariants the tier asserts are drawn from contracts already declared elsewhere -
`specs/behaviors/output-contract.md` (truncation and collection bounds),
`specs/commands/find.md` (Bounded results) and `specs/behaviors/symbol-graph.md` (signature
recording) - but this plan brings no code into conformance with them, so it claims neither field.

## Approach

1. Open this plan at `status: in-progress`.
2. Add `numpy` and `polars` to `[dependency-groups] dev`. These are issue 71's own proven
   specimens; between them they carry every property in its table. `pydantic` and `fastmcp` are
   already installed here and are used as additional specimens at zero install cost.
3. Register a `conformance` marker in `[tool.pytest.ini_options]` (no markers are configured
   today) and add `-m "not conformance"` to `addopts`, so the default run and CI
   (`uv run coverage run -m pytest`, `.github/workflows/ci.yml`) exclude the tier while
   `uv run pytest -m conformance` opts into it.
4. Amend `ICM/_config/reference-toolchain-pytest.md` - a deliberate amendment to an
   `immutable: true` reference - recording the marker, the two run modes and when the tier is
   expected to run.
5. Add `tests/test_conformance.py` asserting surface-level invariants only, never version-pinned
   facts. The point is that the walk survives arbitrary third-party code, not that any package has
   a particular symbol.
6. Run both modes and the hooks, capturing output verbatim.
7. Close out and add the `CHANGELOG.md` entry under the existing `## [Unreleased]` heading.

**The expected failure, and why it is an `xfail` rather than a red test.** The payload-bound
invariant cannot pass until issue 67 bounds `show --api --docstring`; that is the point of
sequencing this unit ahead of it. It is recorded as `pytest.mark.xfail(strict=True)` naming issue
67. Strict is what makes this a gate rather than a concession: the tier stays green today, and the
moment issue 67 bounds the payload the xfail passes unexpectedly and **fails the suite**, so that
unit cannot land without acknowledging it. An assertion deleted or loosened to pass would instead
certify the bug - which is exactly what `tests/resources/package/error.py` did for issue 64, where
the one fixture standing for 'a submodule that fails to import' encoded the very assumption the
bug rested on.

## Validation

- [x] When the test suite is invoked with no marker selection, the suite shall not collect the
  conformance tier. — `uv run pytest` -> `370 passed, 17 deselected`, the 370 baseline unchanged;
  `uv run coverage run -m pytest` (the CI path, `.github/workflows/ci.yml:50`) -> the same
  `370 passed, 17 deselected`
- [x] When the test suite is invoked with `-m conformance`, the suite shall collect the tier and
  complete with no failures and no errors. — `uv run pytest -m conformance` ->
  `14 passed, 370 deselected, 3 xfailed`
- [x] While `show --api --docstring` carries no row-count bound, the conformance tier shall report
  the payload-bound assertion as an expected failure, and shall fail the suite if that assertion
  unexpectedly passes. — `tests/test_conformance.py::test_show_api_docstring_payload_stays_bounded`
  reports `3 xfailed` for `numpy`, `polars` and `pydantic`; raising `SANE_PAYLOAD_BYTES` to
  `10_000_000` to simulate issue 67 landing turned all three into
  `[XPASS(strict)] unbounded --api --docstring payload, issue #67` and the run into `3 failed`
- [x] Where a specimen package is not installed, the conformance tier shall skip that specimen
  rather than fail or error. — a specimen name that is not installed, added temporarily, produced
  four `SKIPPED ... could not import 'definitely_not_installed_pkg'` lines and
  `14 passed, 4 skipped, 370 deselected, 3 xfailed`

## Risks / unknowns

- **An invariant may fail on a real package.** That is the tier working as intended, but it lands
  mid-run as an unevidenceable Validation criterion. The rule for this run: report it, file it,
  and pin it with a strict `xfail` naming the new issue - never weaken the assertion to green the
  run. If what surfaces is large enough to need repair rather than pinning, the eligibility call
  was wrong and the work re-enters `process-plan` at stage 01.
- **CI install weight.** `uv sync` in `.github/workflows/ci.yml` installs the `dev` group, so
  every CI run now downloads `numpy` and `polars`. `numba` was deliberately left out despite being
  a confirmed specimen: it pulls `llvmlite` and is the heaviest of the candidates, and its
  property (decorator passthrough) is the least load-bearing of those on offer. Recorded under
  Follow-ups.
- **Platform-conditional pathologies.** The `numpy.f2py.tests.util` specimen raises a bare
  `BaseException` only on Windows ("No Fortran tests on Windows"), so an assertion pinned to it
  would pass here and skip silently elsewhere. The tier asserts the walk survives, never that a
  particular submodule raised.
- **Version drift.** Specimens are unpinned, so an upstream release can change what the tier
  walks. This is accepted: a pinned specimen tests a snapshot, and the property under test is
  survival of whatever third-party code is actually installed.

## Notes

**Why a strict `xfail` and not a red test.** The tier is committed green, which sounds like the
concession this unit exists to refuse, and is the opposite. `strict=True` means an unexpected pass
fails the suite, so the mark cannot outlive the defect: the moment issue 67 bounds the payload,
the three pinned specimens flip to `XPASS(strict)` and CI goes red until that unit removes them.
This was verified rather than assumed - raising `SANE_PAYLOAD_BYTES` to `10_000_000` to simulate
issue 67 landing produced `3 failed`, each reported as
`[XPASS(strict)] unbounded --api --docstring payload, issue #67`. A red test would have had to be
excluded from CI to be tolerable, and an excluded red test is one nobody looks at.

**`fastmcp` is deliberately not pinned.** It is the live regression guard on the payload
invariant: its `show --api --docstring` payload is roughly 7.2 KB against the 50,000-byte bound, so
it asserts normally and would fail if the bound ever regressed. A tier where every case carries the
mark asserts nothing about the invariant it names.

**The bound was chosen, not fitted.** 50,000 bytes is roughly 12,500 tokens at four bytes per
token, already generous for one response in an interface built for token efficiency. It was picked
before measuring, and the measurements then straddled it cleanly: `fastmcp` 7.2 KB under,
`pydantic` ~105 KB, `polars` ~380 KB and `numpy` ~737 KB over, by 2x to 14x. Fitting a bound to
whatever currently passes would have produced a number that proves nothing.

**Issue 67 is wider than its own report.** The issue cites `numpy` and `polars`; the tier found
`pydantic` unbounded too, at ~105 KB. So the threshold is not "a famously wide package" but any
package with a couple of hundred public symbols. No new issue was filed - issue 67 already owns
the defect generically - but the unit that fixes it inherits three pinned specimens, not one.

**Specimen versions are measured here, not quoted.** `numpy` 2.5.2, `polars` 1.43.2,
`pydantic` 2.13.4, `fastmcp` 3.4.6. Issue 71's comment reports `fastmcp` 3.4.7; that figure came
from a different project's venv, and the versions a conformance tier walks are a property of the
venv it runs in.

**One live shape the fixture could not have taught us.** `polars.sql` exists simultaneously as a
submodule and as a re-exported function of the same bare name, so a live `getattr` on the parent
resolves to the function and not the module. The empty-signature check excludes `MODULE` and
`PACKAGE` nodes for that reason. This is not a `venvaxi` defect, and it is precisely the class of
thing a hand-written fixture never exhibits - the argument of issue 71 in miniature.

## Follow-ups

- **Issue [#67](https://github.com/andyrids/venv-axi/issues/67)** - the next unit, and it now has
  a gate: `test_show_api_docstring_payload_stays_bounded` fails on landing until the three
  `xfail(strict=True)` marks are removed. That unit starts from a red suite by design, which is
  not a regression to diagnose.
- **`numba` as a fifth specimen** - a confirmed decorator-passthrough specimen (`njit` ->
  `(*args, **kws)`), left out because it pulls `llvmlite` and `uv sync` installs the `dev` group on
  every CI run. Its property is the least load-bearing of those on offer. Owned by no issue;
  worth revisiting only if a decorator-passthrough defect ever surfaces.
- **Depth of the walk** - the tier asserts over root-level children and one deliberately deeper
  case (`numpy.f2py`, at `max_depth=2`). A pathology below that depth would not be caught. Owned
  by no issue; a deliberate cost tradeoff, recorded so a later widening is a decision rather than
  a discovery.
- **Non-Windows verification** - the `numpy.f2py` specimen's bare `BaseException` is
  Windows-conditional, and only the Windows path was exercised here. The assertion is
  platform-agnostic by construction (exit code only, never which submodule raised), so CI on
  another platform exercises it as an ordinary deeper walk. Tracked as: the CI matrix.
