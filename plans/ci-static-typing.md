---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: [113]
pr:
---

# Plan: CI static typing

## Scope

`.github/workflows/ci.yml` has three jobs. `ruff-lint` runs `uv run pkgdx-lint-hook` and
`uv run pkgdx-format-hook`; `pytest` and `conformance` each run an OS matrix. None runs a type
check. The check exists as a `prek` hook (`pkgdx-typing`, `prek.toml`) and fires for any
contributor who has run `just setup`, but not for one who has not, for a commit made with
`--no-verify`, or for an edit made through the GitHub web UI. `pyproject.toml` declares
`"Typing :: Typed"`, a promise to consumers that nothing in CI currently checks.

This unit adds `uv run pkgdx-typing-hook -p venvaxi` as a third step in the first job, and renames
that job from `ruff-lint` to `static`, since it then runs three `pkgdx` hooks rather than two and
the old name would understate what it does - the same class of stale-name problem the
`ci-conformance-tier` unit's sibling, `ci-platform-matrix`, left as a note for the toolchain
reference it amended. `pytest` and `conformance` are untouched.

**Eligibility for `express-change`.** All three conditions in `ICM/express-change/CONTEXT.md`
hold.

1. **No spec change is required.** `specs/README.md` -> `## What specs cover` is observable
   behaviour of the tool - invocation, inputs, outputs, failure modes. This unit is CI
   configuration; it changes nothing the tool promises a caller. The only Layer 3 reference that
   names the CI job, `ICM/_config/reference-toolchain-mypy.md`, already documents
   `uv run pkgdx-typing-hook -p venvaxi` as the command and makes no claim about CI, so, unlike
   the toolchain-reference amendment `ci-conformance-tier` made, no reference is falsified by
   this change and none needs amending. Confirmed by reading both `reference-toolchain-mypy.md`
   and `reference-toolchain-prek.md` in full and by grepping the tree for `ruff-lint`: the only
   live hit outside this plan is `.github/workflows/ci.yml:16`.
2. **One commit's worth**, with no new dependency and no new public surface. Two edits to one job
   in one file - a key rename and one appended `run:` step - plus the plan and the changelog
   entry. No source change, no test change, no dependency added.
3. **Every Validation criterion can be evidenced within this run, or is explicitly deferred to a
   real PR run under the same precedent both preceding units in this sequence set.** Criterion 2
   (the deliberate-failure demonstration) is evidenced locally. Criteria 1, 3 and 4 assert on
   GitHub Actions' own scheduling and check-run naming for a pull request, which this run cannot
   produce - consistent with `ci-platform-matrix` and `ci-conformance-tier`, the plan stays
   `status: in-progress` with those boxes unticked until a real PR run evidences them.

## Implements

Nothing in `specs/**`; this is CI-configuration work, the same class of change as the two
preceding units in the sequence. `specs:` and `authors:` are both empty for that reason.

## Approach

1. Open this plan at `status: in-progress`.
2. `.github/workflows/ci.yml` - first job only: rename the job key `ruff-lint` to `static`, then
   append `- run: uv run pkgdx-typing-hook -p venvaxi` after the existing `pkgdx-format-hook`
   step. `pytest` and `conformance` are untouched - no new job, no new checkout, no new
   `uv sync`, no `continue-on-error`.
3. Demonstrate criterion 2: introduce a deliberate type error into a file under `src/venvaxi/`,
   run `uv run pkgdx-typing-hook -p venvaxi`, capture the error text and the non-zero exit code
   verbatim, then revert the file completely and confirm with `git diff` that no trace remains.
4. Run and capture verbatim: `uv run pkgdx-typing-hook -p venvaxi`,
   `uv run coverage run -m pytest`, `uv run coverage report`, `uv run -m prek run --all-files`
   (with this plan file staged via `git add -N`, since `prek` only sees tracked files).
5. Add the `CHANGELOG.md` entry under `[Unreleased]` -> `Changed`, citing issue #113, mentioning
   both the new type check and the job rename.
6. Stop before closeout. Criteria 1, 3 and 4 need a real PR run; the plan stays
   `status: in-progress`.

## Validation

- [ ] When a pull request targets `main` or `develop`, the CI workflow shall type-check the
      `venvaxi` package.
- [ ] If a type error is present in `src/venvaxi/`, then the type check shall fail the job.
- [ ] While the renamed job runs, it shall continue to perform the lint and format checks it
      performed as `ruff-lint`.
- [ ] When the workflow runs, no check run named `ruff-lint` shall remain.

## Risks / unknowns

- **Criteria 1, 3 and 4 need a real PR.** They assert on GitHub Actions' own scheduling and
  check-run naming, which this machine cannot produce. The local typing-hook run and the
  deliberate-failure demonstration predict, but do not evidence, the renamed job's behaviour in
  CI - the plan stays `in-progress` until a PR runs it.
- **The rename changes a check-run name with no branch-protection consumer today.** No ruleset
  currently requires status checks by name (`ci-platform-matrix` recorded the same for its own
  `pytest` rename), so nothing breaks, but issue #110 (the publish gate) will eventually need to
  name `static` rather than `ruff-lint`.

## Notes

## Follow-ups
