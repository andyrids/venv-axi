---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/output-contract.md
  - specs/mcp/tools.md
  - specs/commands/tree.md
authors: []
issues: [64]
pr: 70
---

# Plan: import-crash-containment

## Scope

Contain `BaseException`s escaping third-party imports
([#64](https://github.com/andyrids/venv-axi/issues/64)). `tree numpy --max-depth 4` crashes
with a traceback and exit 2 on the CLI, and drops the whole MCP connection over
`getModuleTreeTool` - `numpy.f2py` raises `_pytest.outcomes.Skipped` at import time, which is
a `BaseException` but not an `Exception`, so it sails through the submodule import guard, both
entry-point backstops, and the cache cleanup arm.

The blast radius is wider than the issue reports: the escaping `BaseException` also skips the
cache build's cleanup arm, so the half-built store is neither discarded nor closed - on
Windows that can leave a locked cache database behind after the crash.

In scope: the submodule import guard, the top-level package import, the cache cleanup arm,
both entry-point backstops, and `show --api`'s import catch. Out of scope: any change to what
`tree` reports for a skipped submodule - its failure modes were already correct, and the
crash was a violation of them.

## Implements

- `specs/behaviors/output-contract.md` - the new Import boundaries section: import boundaries
  guard `BaseException`, submodule failures are skipped, a broken requested package reports
  `PackageImportError`, third-party `SystemExit` is contained, `KeyboardInterrupt` always
  propagates, and an aborted build releases the cache database. The Error shape section now
  defines the entry-point backstop over `BaseException`, re-raising only `KeyboardInterrupt`
  and `SystemExit`.
- `specs/mcp/tools.md` - the 'No exception escapes' contract now states that 'exception'
  means `BaseException`, caught at the tool boundary with the same two re-raises.
- `specs/commands/tree.md` - no amendment; the fix restores conformance with its existing
  failure modes, which #64 violated.

## Approach

- Widen the submodule import guard in the graph walk to `BaseException`, re-raising
  `KeyboardInterrupt` - the guard's existing NOTE ('can raise anything') already states the
  intent the code does not implement.
- Sweep the top-level package import in the cache build under the same rule: anything but
  `KeyboardInterrupt` raised by the requested package's own import reports as
  `PackageImportError`, matching `show --api`'s import catch, which is widened alongside.
- Widen the cache build's cleanup arm to `BaseException`. It re-raises, so widening only
  fixes the leaked store; it swallows nothing.
- Widen the CLI and MCP backstop arms to `BaseException`, re-raising `KeyboardInterrupt` and
  `SystemExit` first.
- New fixture beside the existing `RuntimeError` import-failure fixture, raising a
  `BaseException` subclass at module import; boundary tests on both surfaces.

## Validation

- [x] If a submodule raises a `BaseException` subclass that is not an `Exception` at import
      time, then the graph walk shall skip that submodule, log a warning to STDERR, and
      complete - the `tree` command exits `EX_OK` with the remaining modules. —
      `tests/test_introspect.py::test_walk_submodules_contains_base_exception_import` and
      `tests/test_cli.py::test_command_tree_completes_over_broken_submodules`
- [x] If a submodule raises `SystemExit` at import time, then the walk shall contain it and
      the command shall exit on its own result, never with the submodule's exit status. —
      `tests/test_introspect.py::test_walk_submodules_contains_system_exit_import` and
      `tests/test_cli.py::test_command_tree_completes_over_broken_submodules`
- [x] If the requested package itself raises a non-`Exception` `BaseException` at import
      time, then the command shall raise `PackageImportError`, emit the TOON error block and
      exit `EX_FAILURE`. —
      `tests/test_introspect.py::test_build_store_for_base_exception_import_reports_broken`
      and `tests/test_introspect.py::test_get_public_api_base_exception_import_reports_broken`
- [x] If a `BaseException` other than `KeyboardInterrupt` and `SystemExit` reaches the CLI
      entry point, then it shall render the `Unexpected error:` block and exit `EX_SYNTAX`. —
      `tests/test_cli.py::test_main_base_exception_maps_to_exit_2` and
      `tests/test_cli.py::test_main_reraises_system_exit_unrendered`
- [x] If a `BaseException` other than `KeyboardInterrupt` and `SystemExit` reaches an MCP
      tool boundary, then the tool shall return the `Unexpected error:` block rather than
      letting it escape into the transport. —
      `tests/test_mcp.py::test_tool_base_exception_returns_toon_error_block`
- [x] If `KeyboardInterrupt` is raised during a walk, then it shall propagate through the
      CLI and MCP boundaries unswallowed. —
      `tests/test_introspect.py::test_walk_submodules_reraises_keyboard_interrupt`,
      `tests/test_cli.py::test_main_reraises_keyboard_interrupt` and
      `tests/test_mcp.py::test_tool_reraises_keyboard_interrupt`
- [x] If a graph build is aborted by an escaping exception, then the cache database shall be
      released before the exception propagates, so the next command can open it. —
      `tests/test_cache.py::test_get_or_build_store_releases_store_on_base_exception`

## Risks / unknowns

- The reproduction (`numpy.f2py` raising `Skipped`) lives in a dependency this repo does not
  install; verification uses a fixture raising a plain `BaseException` subclass instead. The
  end-to-end numpy check runs from the consuming project after rc2, per the release plan.
- A fixture raising `BaseException` at import must not subclass anything the test runner
  treats as control flow (`KeyboardInterrupt`, `SystemExit`, pytest's own outcomes), or the
  suite aborts instead of asserting.
- Ordering inside the widened arms is load-bearing twice over: `KeyboardInterrupt` and
  `SystemExit` must be re-raised before the broad arm, and `Error` must still be caught
  before it, or every domain error collapses into the unexpected shape.

## Notes

- Design decision: `_cache.get_or_build_store` contains a foreign `BaseException` at the
  top-level import by chaining it into `ImportError`, rather than raising
  `PackageImportError` itself. `_build_store_for` stays the single conversion site, so the
  error message keeps the caller's original spelling (`` from `<name>` ``), which `_cache`
  never sees - and a non-import `BaseException` raised *during the walk* (a venvaxi bug)
  still surfaces as exit 2, not as a false 'broken package' verdict.
- Design decision: the boundary re-raises are exactly `KeyboardInterrupt` (every level - a
  walk must stay abortable) and, at the two entry points, `SystemExit` (venvaxi's own exit).
  Third-party `SystemExit` never reaches an entry point because the import boundaries
  convert it first, so the entry-point re-raise cannot leak a foreign exit status.
- Gotcha: arm ordering is load-bearing twice - `Error` before the broad arm (or every domain
  error collapses into the unexpected shape) and `KeyboardInterrupt`/`SystemExit` before
  `BaseException` (or the re-raise arms are dead).
- The two fixtures (`base_error.py`, `exit_error.py`) exercise the containment on every
  `fake_package` walk suite-wide, not only in the dedicated tests - the pinned child list in
  `test_show_module_returns_node_and_children` doubles as a regression tripwire.
- The changelog entry lives under `[0.3.0rc2]` in `CHANGELOG.md`, written by
  `plans/withdraw-0-3-0.md`'s release-record edit rather than an `[unreleased]` section -
  this run is part of that release.

## Follow-ups

- Issue [#67](https://github.com/andyrids/venv-axi/issues/67),
  issue [#68](https://github.com/andyrids/venv-axi/issues/68) and
  issue [#49](https://github.com/andyrids/venv-axi/issues/49) - the remaining rc2-adjacent
  findings, deliberately deferred to 0.4.0; none is owned by this plan.
- The end-to-end reproduction (`tree numpy --max-depth 4` from the consuming project) runs
  after `0.3.0rc2` is published - tracked as the release plan's manual verification step in
  `plans/withdraw-0-3-0.md`.
