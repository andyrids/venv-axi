---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---

# Toolchain - `Pytest`

Pytest is used for unit testing, with tests colocated in `tests/`.

## Commands

- `uv run pytest -v` - Run the full test suite
- `uv run pytest tests/test_setup.py -v` - Run a single test module
- `uv run coverage run -m pytest` then `uv run coverage report` - Run under coverage (see
  `reference-toolchain-coverage.md`)

## Configuration

- `pyproject.toml` `[tool.pytest.ini_options]` - `addopts = ["--import-mode=importlib"]`

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
- A test asserting corrected *wording* SHOULD assert the wrong form is absent as well as the
  right form present. A one-way assertion passes on a substring: when a hint naming
  `showPackageTool` was reworded from "for a package's public API" to "for package metadata",
  `assert "showPackageTool" in result` passed before the fix, and only
  `assert "public API" not in result` failed
