---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: [111]
pr:
---

# Plan: CI platform matrix

## Scope

`docs/architecture.md:12` declares **OS: Windows / Linux / WSL2**. `.github/workflows/ci.yml` runs
both of its jobs on `runs-on: ubuntu-latest` with no `strategy.matrix` of any kind - two thirds of
the documented platform claim is never exercised, and this project's shipped bug history is
disproportionately Windows-specific: the `os error 32` `venvaxi.exe` MCP shim defect
(`CHANGELOG.md` `[0.3.0]`), CRLF corruption of skill and `AGENTS.md` writes (`[0.3.0rc1]`), and the
pytest fd-capture trap (#56). Every one was found by a person on Windows, because nothing in CI
could have been.

A smaller second half: `pyproject.toml` `classifiers` name Development Status, audience, four
Python versions and `Typing :: Typed`, with no `Operating System ::` classifier at all, so the PyPI
listing carries no platform information while the docs make a specific claim.

This unit adds a `windows-latest` leg to the `pytest` job's matrix alongside `ubuntu-latest`, pins
the interpreter both legs resolve so a red leg identifies the operating system and nothing else,
and adds the two `Operating System ::` classifiers matching `docs/architecture.md:12`.

**No Python version matrix.** That is resolution 2 of issue #111 and belongs to its own issue -
folding it in here would silently widen scope the issue itself says to keep separate.

**The conformance tier stays deselected on both legs.** `addopts = ["--import-mode=importlib",
"-m", "not conformance"]` excludes `tests/test_conformance.py` (21 of 543 tests) from every local
and CI run today, and this unit does not change that. A green matrix after this unit proves the
other 522 tests on both operating systems, not the conformance tier on either - that gap is
issue #112, sequenced immediately after this one.

## Implements

None. `specs/README.md` -> `## What specs cover` is invocation, inputs, data requirements,
outputs, failure modes, out of scope and principles - observable behaviour of the tool. A CI
matrix and PyPI classifiers are packaging and infrastructure, not behaviour the tool promises, so
neither `specs:` nor `authors:` names anything here. `docs/architecture.md` is explicitly
"documentation of the implementation's shape, not specification" (its own header), and its
platform claim is unchanged by this unit - the unit makes the claim true, it does not restate it.

## Approach

1. `.github/workflows/ci.yml` - `pytest` job only:
   - `strategy: { fail-fast: false, matrix: { os: [ubuntu-latest, windows-latest] } }`,
     `runs-on: ${{ matrix.os }}`. `fail-fast: false` so a Windows failure does not cancel the
     Ubuntu leg.
   - `python-version: "3.13"` added to the existing `astral-sh/setup-uv` step, so both legs
     resolve the same interpreter and a red leg cannot be ambiguous between OS and Python version.
   - `cache-suffix: pytest-${{ matrix.os }}` so the two legs do not share a cache key.
   - `ruff-lint` stays single-runner on `ubuntu-latest`, untouched. `coverage run` / `report` /
     `xml` stay as they are - nothing consumes `coverage.xml` today, so no `coverage combine` is
     needed.
2. `pyproject.toml` `classifiers` - add `"Operating System :: Microsoft :: Windows"` and
   `"Operating System :: POSIX :: Linux"`, matching `docs/architecture.md:12`. Not `OS
   Independent` - this project carries code paths that exist only to make Windows work.
3. Run the local toolchain gate on this Windows machine as the pre-flight for the Windows CI leg:
   `uv run coverage run -m pytest`, `uv run coverage report`, `uv run -m prek run --all-files`.
   Fix any failure in this unit; do not `skipif` a Windows failure away and do not add
   `continue-on-error` to the matrix.
4. Verify the classifiers against the built wheel's `METADATA`, not the source, then clean up
   `dist/` (gitignored, so no `git status` residue).
5. `CHANGELOG.md` `[Unreleased]` - a `Changed` entry for the matrix, an `Added` entry for the
   classifiers, both citing issue #111.
6. Stop before closeout. Three Validation criteria (1, 3, 4) need a real PR to evidence - the
   matrix legs reporting, the Windows leg's own pass/fail, and the check run's own status - and
   cannot be evidenced from this machine. The plan stays `status: in-progress` until the human
   reviews and the PR runs.

## Validation

- [ ] When a pull request targets `main` or `develop`, the CI workflow shall run the `pytest` job
      once on `ubuntu-latest` and once on `windows-latest`.
- [ ] While the OS matrix runs, each leg shall resolve the same pinned Python interpreter version,
      so a leg's result identifies the operating system and nothing else.
- [ ] When the `pytest` job runs on `windows-latest`, it shall complete with zero test failures.
- [ ] If a test fails on `windows-latest` only, then the workflow shall report the check run as
      failed rather than succeeded.
- [ ] When `uv build` produces a wheel, its metadata shall carry an `Operating System ::`
      classifier for each platform `docs/architecture.md` claims support for.
- [ ] When the Windows leg fails and is fixed, the fix shall keep the test running on Windows
      rather than skipping it there.

## Risks / unknowns

- **Criteria 1, 3 and 4 need a real PR.** They assert on GitHub Actions' own scheduling and check
  run reporting, which this machine cannot produce. Local coverage/prek runs and a wheel build
  predict, but do not evidence, the matrix's behaviour - the plan stays `in-progress` until a PR
  runs it.
- **Job renaming has a downstream consumer.** Matrixing renames the `pytest` check run to
  `pytest (ubuntu-latest)` / `pytest (windows-latest)`. No branch protection or ruleset currently
  requires status checks, so nothing breaks today, but issue #110 (the publish-gate issue landing
  after this one) will need to name the new spellings.
- **Windows runner minutes bill at 2x Linux** on private repos. This repository is public, so the
  cost is zero today - the doubling is real only if that ever changes.
- **The pinned `3.13` is a judgement, not a measurement.** It sits inside `requires-python =
  ">=3.11"` and inside the declared classifier range. The unexercised-Python-versions gap is
  resolution 2 of issue #111 and stays out of this unit.

## Notes

## Follow-ups
