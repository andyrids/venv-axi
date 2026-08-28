---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: [112]
pr:
---

# Plan: CI conformance tier

## Scope

`pyproject.toml` deselects the `conformance` tier by default (`addopts = ["--import-mode=importlib",
"-m", "not conformance"]`), and `.github/workflows/ci.yml` never passes `-m conformance`, so CI
inherits the deselection. Twenty-one tests exist (`tests/test_conformance.py`) that no automated
process has ever run - verified this session: `522/543 tests collected (21 deselected)` by default,
`21/543` under `-m conformance`. The tier walks real installed dependencies (`numpy`, `polars`,
`pydantic`, `fastmcp`) precisely because issues #64, #65, #66, #67, #68 and #69 were all found by
dogfooding a published release and none of them failed the hand-written-fixture suite (#71); landing
deselected and absent from CI leaves that mechanism unused.

This unit adds a third CI job, `conformance`, parallel to `pytest`, running `-m conformance` on the
same `ubuntu-latest` / `windows-latest` matrix `pytest` already runs on (PR #114), plus a specimen
guard step so a missing specimen fails the job loudly instead of skipping silently.

**The file-and-pin rule.** This unit touches only `.github/workflows/ci.yml` (the new job) and
`ICM/_config/reference-toolchain-pytest.md` (the amendment the new job makes true). It does not
touch `addopts`, the `pytest` job, `ruff-lint`, or any assertion inside `tests/test_conformance.py`.
If the tier surfaces a defect when run for this plan, that defect is filed and pinned as a new
issue, never repaired here - repairing it would be scope growth past what this unit is chartered to
do, per the precedent `plans/real-dependency-conformance.md` set for this same tier.

**Eligibility for `express-change`.** All three conditions in `ICM/express-change/CONTEXT.md` hold.

1. **No spec change is required.** `specs/README.md` -> `## What specs cover` is observable
   behaviour of the tool - invocation, inputs, outputs, failure modes. This unit is CI
   configuration and a toolchain-reference amendment, neither of which is behaviour the tool
   promises. `ICM/_config/reference-toolchain-pytest.md` is `immutable: true`, so amending it is a
   deliberate act rather than a passing one, but it is factory configuration, not a spec -
   `real-dependency-conformance.md` made the identical amendment under the identical reasoning when
   it created the tier.
2. **One commit's worth**, with no new dependency and no new public surface. One new CI job, one
   amended reference file, the plan, and the changelog entry - no source change, no test change, no
   dependency added.
3. **Every Validation criterion can be evidenced within this run** - criteria 1 and 2 assert on
   GitHub Actions' own scheduling and check-run reporting for a pull request, which this run cannot
   produce (no PR is open yet, per instruction). Consistent with the identical situation in
   `plans/ci-platform-matrix.md`, the plan stays `status: in-progress` with those boxes unticked
   until a real PR run evidences them; criteria 3, 4 and 5 are evidenced locally in this run.

## Implements

Nothing in `specs/**`; this is test-strategy and CI-configuration work, the same class of change as
the toolchain amendment `real-dependency-conformance.md` made when it created the tier. `specs:` and
`authors:` are both empty for that reason.

## Approach

1. Open this plan at `status: in-progress`.
2. Add a `conformance` job to `.github/workflows/ci.yml`, parallel to `pytest`: the same
   `ubuntu-latest` / `windows-latest` matrix with `fail-fast: false`, the same pinned
   `actions/checkout@v6` and `astral-sh/setup-uv` steps with `cache-suffix:
   conformance-${{ matrix.os }}`, a specimen guard step (`Verify conformance specimens are
   installed`, `uv run python -c "import numpy, polars, pydantic, fastmcp"`) before pytest, then
   `uv run pytest -m conformance -v`. No coverage step - the tier asserts survival of third-party
   code, not line coverage. `addopts`, the `pytest` job and `ruff-lint` are untouched.
3. Amend the `conformance` marker entry in `ICM/_config/reference-toolchain-pytest.md` so it names
   the CI job that now runs the tier and no longer states that CI excludes it, while keeping "run it
   after touching `_introspect.py` or `_cli.py`" as local guidance rather than the only gate.
4. Run the tier locally, run the default suite under coverage to confirm it is unchanged, run
   `prek`, and capture all three verbatim.
5. Demonstrate the specimen guard fires: run the guard command with an extra, not-installed module
   name, capture the non-zero exit and `ModuleNotFoundError` verbatim, and leave no trace of that
   name in `ci.yml`.
6. Add the `CHANGELOG.md` entry under `[Unreleased]` -> `Changed`, citing issue #112.
7. Stop before closeout. Criteria 1 and 2 need a real PR run; the plan stays `status: in-progress`.

## Validation

- [ ] When a pull request targets `main` or `develop`, the CI workflow shall run the conformance
      tier once on `ubuntu-latest` and once on `windows-latest`.
- [ ] When the conformance job runs, it shall execute all 21 conformance tests, with none skipped
      for a missing specimen.
- [ ] If a specimen named in `SPECIMENS` is absent from the environment, then the conformance job
      shall fail at the specimen check before pytest runs, naming the missing module.
- [ ] While the conformance job exists, the default `pytest` job shall continue to exclude the
      tier, so a conformance failure and a unit failure are distinguishable at a glance.
- [ ] The `conformance` entry in `ICM/_config/reference-toolchain-pytest.md` shall name the CI job
      that runs the tier and shall no longer state that CI excludes it.

## Risks / unknowns

- **The tier's current state was unknown going in.** It has never run in CI, and its specimens are
  unpinned on purpose (`tests/test_conformance.py` module docstring), so version drift alone can
  turn it red independent of any change here. The local run in this unit is the first evidence
  either way.
- **Criteria 1 and 2 need a real PR** to schedule the matrix and report the check runs; they cannot
  be produced on this machine and stay unticked until that PR runs, per the identical situation in
  `plans/ci-platform-matrix.md`.
- **Job count rises on every PR** - a third parallel job (two legs) alongside the existing `pytest`
  matrix and `ruff-lint`. Relevant to issue #110, the publish gate, which will need to name
  `conformance (ubuntu-latest)` and `conformance (windows-latest)` alongside the `pytest` legs.
- **`pydantic` is transitive, not declared** - it reaches the venv through `fastmcp`. A future
  `fastmcp` release that drops it would make the specimen guard fail, correctly and loudly, and the
  fix at that point would be to declare `pydantic` directly in the dev group.

## Notes

None yet - populated at closeout.

## Follow-ups

None yet - populated at closeout.
