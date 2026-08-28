---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [pytest, unit-testing]
---

# Toolchain - `Pytest`

Pytest is used for unit testing, with tests colocated in `tests/`.

## Commands

- `uv run pytest -v` - Run the full test suite (excludes the `conformance` tier)
- `uv run pytest tests/test_setup.py -v` - Run a single test module
- `uv run pytest -m conformance -v` - Run only the `conformance` tier
- `uv run coverage run -m pytest` then `uv run coverage report` - Run under coverage (see
  `reference-toolchain-coverage.md`); excludes the `conformance` tier, same as a bare `pytest` run

## Configuration

- `pyproject.toml` `[tool.pytest.ini_options]` - `addopts = ["--import-mode=importlib", "-m", "not
  conformance"]`
- `pyproject.toml` `[tool.pytest.ini_options]` `markers` - registers `conformance`

## Markers

- `conformance` (`tests/test_conformance.py`) - walks real installed dependencies (`numpy`,
  `polars`, `pydantic`, `fastmcp`) instead of the hand-written `tests/resources/package/` fixture,
  so a pathology only third-party code exhibits can fail the suite (#71). Excluded from the default
  run via `addopts`; a command-line `-m` overrides it, so `uv run pytest -m conformance` opts in.
  The `conformance` job in `.github/workflows/ci.yml` runs the tier with `-m conformance` on every
  pull request, so CI no longer excludes it. Running it locally after touching `_introspect.py` or
  `_cli.py` is still worth the faster feedback - the unit tests alone passed on every specimen
  behind #64-#69 - but it is no longer the only gate. A specimen not installed is skipped, not
  failed; the CI job guards against a silently skipped tier with a step that fails before pytest
  runs, naming the missing specimen.

## Conventions

- Test modules: `tests/test_<module>.py`, mirroring `src/venvaxi/<module>.py`
- Shared fixtures live once in `tests/conftest.py` and are consumed via dependency injection
  (e.g. `configured_logging`, `tty_stdout_enable`/`tty_stdout_disable`, `mock_subprocess_run`,
  `mock_project`) rather than re-declared per test module
- Dataclass instances are built via factory fixtures (`make_symbol_node`, `make_package_info`,
  `make_cli_context`) that supply defaults for every field and accept `**overrides` - tests
  override only the fields they assert on, so a model field addition touches a single conftest
  default rather than every construction site
- Mock external processes with `unittest.mock.patch` (see `mock_subprocess_run`) instead of
  invoking real subprocesses
- Use `tmp_path_factory` for isolated filesystem fixtures (see `mock_project`)
- Test names: `test_<behaviour>_<condition>`, e.g. `test_setup_progress_disabled_in_non_tty`
- One behavioural assertion focus per test; state the expected behaviour in a one-line docstring
- A test written for a bug fix SHOULD be shown to fail against the previous implementation - a
  regression test that passes both before and after the fix asserts nothing
- A test asserting on STDOUT or STDERR MUST NOT replace `sys.stdout` or `sys.stderr` with
  `mock.patch`. pytest's default fd-level capture re-asserts both mid-test - in the #45 run, while
  a fixture package was being imported - so the patched stream receives nothing and the test fails
  identically with and without the fix under test, which is the show-it-failing rule above
  defeated in the opposite direction. Request `capsys` and reconfigure the captured stream, itself
  a real `io.TextIOWrapper`, so the code under test meets the type it meets in production:
  `stream.reconfigure(encoding="cp1252")`. Measured driving `venvaxi.__main__.main()`, a patched
  stream received 0 bytes under the default capture and 291 under `--capture=no`.
  `tests/test_stdout_encoding.py` is the worked example and records the reasoning in its module
  docstring (#56)
- A test asserting corrected *wording* SHOULD assert the wrong form is absent as well as the
  right form present. A one-way assertion passes on a substring: when a hint naming
  `showPackageTool` was reworded from 'for a package's public API' to 'for package metadata',
  `assert "showPackageTool" in result` passed before the fix, and only
  `assert "public API" not in result` failed
