---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs: []
authors: []
issues: [113]
pr: 118
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

- [x] When a pull request targets `main` or `develop`, the CI workflow shall type-check the
      `venvaxi` package. — PR #118, run 33169206929, `static` job:
      `[uv run pkgdx-typing-hook -p venvaxi] Success: no issues found in 14 source files`
- [x] If a type error is present in `src/venvaxi/`, then the type check shall fail the job. —
      with `_verify_type_error: int = "not an int"` appended to `src/venvaxi/_constants.py`,
      `uv run pkgdx-typing-hook -p venvaxi` reports
      `Incompatible types in assignment (expression has type "str", variable has type "int")`
      and exits 1, against exit 0 on the reverted tree
- [x] While the renamed job runs, it shall continue to perform the lint and format checks it
      performed as `ruff-lint`. — run 33169206929 `static` job:
      `[uv run pkgdx-lint-hook] All checks passed!` and
      `[uv run pkgdx-format-hook] 140 files left unchanged`
- [x] When the workflow runs, no check run named `ruff-lint` shall remain. — PR #118 reports
      five check runs: `static`, `pytest (ubuntu-latest)`, `pytest (windows-latest)`,
      `conformance (ubuntu-latest)`, `conformance (windows-latest)`

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

**All four criteria ticked, and criterion 2 only because it was deliberately triggered.** It is an
`If <trigger>, then` about a type error that does not exist, so it would have sat un-triggered like
the two boxes [ci-platform-matrix](ci-platform-matrix.md) left unticked. Appending a deliberate
error, capturing the non-zero exit, and reverting is what converted it from a plausible claim into
an evidenced one. This is now the third unit in the CI sequence, and the pattern is worth stating
plainly: a criterion asserting on a failure path is evidenced by causing the failure, not by
reading the configuration and reasoning that it would fail.

**Why the step joined the existing job rather than getting its own.** The issue offered both. A
separate job buys cleaner failure attribution and costs a second checkout and `uv sync` for one
command that takes 21 seconds end to end. The two sibling `pkgdx` hooks were already in this job,
and the gap being closed was precisely that the third had been left out of the place the other two
live - putting it anywhere else would have preserved the asymmetry in a different shape.

**Why `-p venvaxi` is required rather than decorative.** The lint and format shims default to the
tree; mypy does not. A bare `pkgdx-typing-hook` exits 2 with `Missing target module, package,
files, or command` - loudly, which is worth recording, because the failure mode worth fearing here
would have been a silent no-op passing CI. It also refuses `-p` and file paths together
(`May only specify one of: module/package, files, or command`), so the coverage is the 14 files
under `src/venvaxi/` and not `tests/`. The commit hook may check changed test files where CI does
not; that asymmetry is real and is stated rather than papered over.

**Why the rename, and why now.** A job running three tools from two families should not be named
after one of them - the same stale-name problem [ci-conformance-tier](ci-conformance-tier.md) had
to amend in a Layer 3 reference. Renaming churns a check run name, and this was the cheapest moment
it will ever be: no ruleset requires status checks, and issue #110's publish gate does not exist
yet, so it can name `static` from the start instead of being written against `ruff-lint` and
corrected immediately. The `cache-suffix` moved with the job, matching how `pytest` and
`conformance` already name theirs.

**Two frozen plans mention `ruff-lint` and were deliberately left alone.**
[ci-platform-matrix](ci-platform-matrix.md) and [ci-conformance-tier](ci-conformance-tier.md) are
both at `status: done`. They record what was true when they were written, and a rename does not
falsify a historical statement. `plans/README.md` allows editing a frozen plan only to correct the
record, and there is nothing here to correct.

**No Layer 3 reference needed amending, and that was checked rather than assumed.** The preceding
unit found a reference its own issue had not listed, so the same sweep ran here:
`reference-toolchain-mypy.md` already documents `uv run pkgdx-typing-hook -p venvaxi` and claims
nothing about CI, and `reference-toolchain-prek.md` claims nothing about CI either. The only live
reference to the job name was `ci.yml` itself.

## Follow-ups

- **Issue** [#117](https://github.com/andyrids/venv-axi/issues/117) - resolution 3 of #113, running
  the whole `prek` suite in CI. Four hook families still run only on a developer's machine:
  PyMarkdown, `detect-secrets`, the TOML/YAML checks and the PEM check. `detect-secrets` makes that
  partly a security-control gap rather than a tidiness one. Filed with no milestone because it is
  blocked on #20, an open PyMarkdown tokenizer crash that would gate CI the moment the suite runs
  there, and #20 was deliberately left out of 0.5.0.
- **Issue** [#110](https://github.com/andyrids/venv-axi/issues/110) - the publish gate. It must name
  `static` rather than `ruff-lint`, alongside the four `pytest` and `conformance` matrix legs. Five
  check run names now, where before this sequence began there were two.
- **Deferred to** - none.
- **Tracked as** - none.
