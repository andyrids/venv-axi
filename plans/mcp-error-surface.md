---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/output-contract.md
  - specs/mcp/tools.md
authors: []
issues: [47, 60]
pr:
---

# Plan: mcp-error-surface

## Scope

Make MCP tool error payloads speak to the MCP caller. Two defects, one cause - a single
hardcoded CLI spelling serving both surfaces:

- Every MCP tool error carries a footer, `Run venvaxi --help ...`, naming a shell command the
  caller cannot run ([#60](https://github.com/andyrids/venv-axi/issues/60)).
- `getSymbolTool` answers a fully-dotted name (no `::`) with `Symbol ... not found` - a
  definitive-sounding negative about the package, where the real fault is malformed input
  ([#47](https://github.com/andyrids/venv-axi/issues/47)).

In scope: the error footer becomes surface-addressed (CLI keeps its generic footer; MCP tool
errors carry no generic footer, only error-specific hints where one exists), and `getSymbolTool`
diagnoses a missing `::` instead of reporting a symbol miss. Out of scope: any module fallback
in `getSymbolTool` - the `inspect` split is a deliberate divergence and stays; and the stale
workaround line in the packaged skill, which stage 04 owns (see Risks / unknowns).

## Implements

- `specs/behaviors/output-contract.md` - the Error shape section no longer writes the CLI
  footer into the shape MCP must mirror. The error *object* and catch discipline are mirrored;
  the footer is per-surface, and an MCP error with no error-specific hint omits the `help[N]:`
  footer entirely under the existing suppression rule.
- `specs/mcp/tools.md` - the Contract error paragraph now cites the surface-addressed footer,
  and the new Malformed qualified names section requires `getSymbolTool` to diagnose a no-`::`
  input (naming `showModuleTool` for module lookups) before any lookup, including when the
  dotted name would resolve as a module.

## Approach

- Parameterize the shared error formatter so the generic footer is supplied by the CLI entry
  point rather than hardcoded - the same per-surface pattern the truncation escape hatch
  already uses. Both CLI error paths keep their current output byte-for-byte.
- Route every MCP tool error (all nine tools share one wrapper) through the no-footer shape.
- Guard `getSymbolTool` on `::` absence before lookup, raising the domain error whose message
  carries the diagnosis and the derived `showModuleTool` name.
- Update tests that assert the old MCP error footer or the old `Symbol not found` wording;
  add coverage for the new shapes.

## Validation

- [x] If an `Error` is raised inside an MCP tool, then the tool shall return the TOON error
      object without a `venvaxi --help` footer. —
      `tests/test_mcp.py::test_tool_axi_error_returns_toon_error_block`
- [x] If an MCP tool error carries no error-specific hint, then the payload shall omit the
      `help[N]:` footer entirely rather than emit it empty. —
      `tests/test_toon.py::test_format_error_without_hints_omits_footer`
- [x] If an unexpected exception is raised inside an MCP tool, then the tool shall return the
      `Unexpected error:` block with no `help[]` footer and log the traceback to STDERR. —
      `tests/test_mcp.py::test_tool_unexpected_error_returns_toon_error_block` and
      `tests/test_mcp.py::test_tool_unexpected_error_logs_traceback`
- [x] If a `venvaxi.exceptions.Error` is raised on the CLI, then the entry point shall render
      the error object followed by the generic `venvaxi --help` footer, unchanged. —
      `tests/test_cli.py::test_main_maps_error_to_toon_and_exit_1`
- [x] If `getSymbolTool` is called with a `qualified_name` containing no `::`, then it shall
      return an error whose message states that a `module::Symbol` name is required, that the
      given name has no `::`, and that names `showModuleTool` for module lookups. —
      `tests/test_mcp.py::test_get_symbol_tool_no_separator_diagnoses_before_lookup`
- [x] If `getSymbolTool` is called with a no-`::` name that resolves as a module in the graph,
      then it shall return the malformed-input diagnosis rather than the module's node. —
      `tests/test_mcp.py::test_get_symbol_tool_module_resolving_name_still_diagnosed`
- [x] When `getSymbolTool` is called with a resolvable `module::Symbol` name, it shall return
      the symbol node exactly as before. —
      `tests/test_mcp.py::test_get_symbol_tool_returns_toon`

## Risks / unknowns

- The packaged skill (`src/venvaxi/SKILL.md`, MCP differences) carries the #47 workaround line
  shipped in #58 ("Read that message as *wrong tool*, not *no such symbol*"). This change makes
  that line stale - it describes behaviour this plan removes. Stage 04 must rewrite or drop it,
  or the skill teaches a recovery for a message that no longer exists.
- The live parity record in issue #47 notes `help[]` text was the only tailored divergence;
  removing the generic error footer widens the deliberate footer asymmetry between surfaces.
  Any future parity sweep must read the amended Error shape, not byte-compare footers.
- `getSymbolTool("rich.console")` - a no-`::` name that names a real module - currently
  *succeeds* by accident, returning the bare module node. The new diagnosis converts that
  success into an error by design; anything relying on the accident breaks loudly.

## Notes

- 2026-08-21 - re-entry to stage 02, raised by stage 03 verification. Evidence-coverage
  finding on Validation criterion 3: the logging half ("log the traceback to STDERR") was
  unasserted - `logger.exception` in `_mcp._toon_errors` could be downgraded or deleted with
  all tests green. Added `test_tool_unexpected_error_logs_traceback` (`tests/test_mcp.py`,
  `caplog` at ERROR on the `venvaxi` logger, asserting `exc_info` is attached), shown to
  fail against a `logger.error` swap. No source changes.
- Design decision: the MCP side gets **no generic footer at all**, not a tool-surface
  equivalent of `Run venvaxi --help`. A connected agent already holds the tool list from the
  MCP handshake, so any generic "here is how to discover the surface" footer is a manufactured
  step - which the contextual-disclosure rule in `specs/behaviors/output-contract.md` already
  forbids. Error-specific hints (a genuine next step for *this* error) remain; only the
  generic footer is per-surface.
- Mechanism: `format_error` re-signed as `format_error(message, hints=None)` - `_toon.py` is
  now surface-neutral, and the CLI spelling lives in `__main__.py` as `CLI_ERROR_HINT`,
  following the `CLI_ESCAPE_HATCH` / `MCP_ESCAPE_HATCH` per-surface precedent in
  `_introspect.py`. The MCP arms already passed no hints, so the re-sign alone made all nine
  tools footer-free through the single `_toon_errors` choke point.
- Deliberate breaking change, reviewed and approved: `getSymbolTool` with a no-`::` name that
  previously *resolved as a module* (`rich.console`, `rich`) now returns the malformed-input
  diagnosis instead of the bare module node. The old success was an accident of lookup order;
  `showModuleTool` returns the fuller answer for the same spelling. Recorded in the CHANGELOG
  as breaking.
- The `getSymbolTool` diagnosis derives both tool names via `camel_case(...__name__)` per the
  Hint wording rule in `specs/mcp/tools.md` - a tool rename cannot strand a stale spelling in
  the message.
- Parity pin: removing the generic MCP footer widens the deliberate footer asymmetry between
  surfaces. Any future CLI/MCP parity sweep must read the amended Error shape in
  `specs/behaviors/output-contract.md`, not byte-compare footers (noted in issue #47's live
  parity record).
- The packaged skill's #47 workaround line ("Read that message as *wrong tool*...") went
  stale the moment stage 02 landed and was caught only because this plan's Risks flagged it
  for stage 04 - a live instance of the drift class issue #39 owns. Rewritten in stage 04 to
  describe the guard, keeping the one fact that still saves a round trip: `getSymbolTool`
  never falls back to modules, so module names go straight to `showModuleTool`.

## Follow-ups

- Issue [#39](https://github.com/andyrids/venv-axi/issues/39) - skill text can go stale
  against the CLI with no test noticing. This run is a live instance (the #47 workaround
  line, see Notes); the survival of every claim rewritten here still rests on review.
- Issue [#48](https://github.com/andyrids/venv-axi/issues/48) - `inherits count: 0` direction
  ambiguity, the sibling misleading-empty-state defect, deliberately out of scope here.
