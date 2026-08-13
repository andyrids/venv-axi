---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends:
  - plan-record-repair
specs:
  - specs/behaviors/output-contract.md
  - specs/commands/list.md
  - specs/mcp/tools.md
authors: []
issues: [29, 30, 31]
pr: 34
---

# Plan: Hint surface parity

## Scope

Four defects of one class: a hint or footer that teaches the caller an invocation surface they are
not on, or that contradicts a rule the same tree already declares. They are planned together
because they land in one diff across `_cli.py`, `_mcp.py` and `_introspect.py`, and because fixing
any one in isolation leaves the surrounding surface still disagreeing with itself.

- **A** - `list --all` with zero results hints `--all`, the flag just used.
  Absorbs the fourth Follow-up of [spec-conformance-sweep](spec-conformance-sweep.md).
- **B** - the truncation suffix hardcodes `--docstring` and ships verbatim in MCP payloads.
  [#30](https://github.com/andyrids/venv-axi/issues/30).
- **C** - `findSymbolTool`'s empty hint names `listPackagesTool` without `include_dev=true`, while
  the CLI names `venvaxi list --all`. [#31](https://github.com/andyrids/venv-axi/issues/31).
- **F** - `listPackagesTool` called with `include_dev=true` and matching nothing still hints
  `include_dev=true`, the parameter just used. The MCP twin of A, found during stage 02 and
  absorbed by re-entry rather than deferred - see Approach step 6.
- **D** - `showPackageApiTool` and `showModuleTool` emit a `help[]` footer under `docstring=true`
  where the CLI emits none. [#29](https://github.com/andyrids/venv-axi/issues/29). The same issue
  carries **E**, the third Follow-up of [spec-conformance-sweep](spec-conformance-sweep.md): the
  `getSymbolTool` entry in `## Divergences from the CLI` describes parity, not divergence.

D is resolved by aligning MCP to the CLI rather than by listing the divergence, so the divergence
list shrinks by one entry instead of growing by two.

Out of scope: the CLI-side `find` empty hints, which are already correct and situational; and the
`refresh`, split-tool and fixed-field divergences, which stay listed and stay deliberate.

## Implements

`specs/behaviors/output-contract.md` - the amended Truncation rule (surface-spelled escape hatch)
and the amended Contextual disclosure rule (footer omitted entirely when suppression leaves no
hint, and never repopulated with an unrelated one). B and D conform code to these.

`specs/commands/list.md` - the amended Outputs section, whose empty-state hint is now conditional
on `--all`. A conforms code to it. The spec previously required the unconditional `--all` hint
that `output-contract.md` forbids; the code satisfied `list.md` and broke `output-contract.md`, so
this is a spec/spec conflict resolved in the cross-cutting behaviour's favour before any code
moved.

`specs/mcp/tools.md` - the amended Divergences list, with the false `getSymbolTool` entry replaced
by an explicit statement that footer suppression is parity (E, a spec-only correction), and the
amended Hint wording rule requiring scope-equivalence, not just tool-equivalence, across mirrored
hints. C and D conform code to these.

## Approach

1. Flip to `status: in-progress`.
2. **B** - give `truncate()` in `_introspect.py` the escape-hatch phrasing rather than hardcoding
   it, and thread it through `summarize_doc()`. `_cli.py` supplies the CLI spelling, `_mcp.py` the
   MCP spelling. Keep the CLI wording byte-identical to today's, so the change is additive on that
   surface and the existing assertion in `tests/test_introspect.py:104` still describes real
   behaviour.
3. **A** - branch the empty-state hint in `command_list()` on `ctx.args.all`: without it, today's
   `--all` hint; with it, the `pyproject.toml` hint the amended spec requires.
4. **C** - extend `find_symbol_tool()`'s **`package`-truthy** empty hint to name
   `include_dev=true`, deriving the tool name through the existing `camel_case(...)` idiom rather
   than writing the camelCase string out. That is the branch mirroring the CLI's
   `venvaxi list --all`; the no-package branch mirrors `find --package` and names no package list
   at all.
5. **D** - return early without a footer from `show_package_api_tool()` and `show_module_tool()`
   when `docstring` is set, matching the shape `get_symbol_tool()` already uses.
6. **F** - branch `list_packages_tool()`'s empty hint on `include_dev`, mirroring fix A on the CLI
   side: unset, name `include_dev=true`; set, name `pyproject.toml`.
7. Add the regression coverage in Validation below. No test currently asserts any hint wording,
   which is why every defect here survived a green suite; the assertions are the bridge the
   spec-anchored stance in `specs/README.md` requires.
8. `CHANGELOG.md` entry under `Fixed`.

**Re-entry to stage 01, during stage 02.** Steps 4 and 6 above were rewritten after implementation
began, which is why this plan carries a defect F that its first draft did not.

Step 4's original wording named the `package is None` branch as the one mirroring the CLI's
`venvaxi list --all`. It is the other branch. The criterion derived from it was wrong in the same
direction, and would have been satisfiable only by moving a hint that issue #31 does not ask to
move. Both were corrected at that point rather than at closeout, because
`ICM/_config/reference-standard-validation.md` makes the checkbox text the identifier stage 03
quotes verbatim - reword during re-entry, not after a verification report exists. None did yet;
the report written against these criteria is the first, so no mapping was broken.

Step 6 is new scope, taken deliberately. `listPackagesTool` is the MCP counterpart of the CLI
`list` this plan already fixes, and its hint violates the same suppression rule in
`specs/behaviors/output-contract.md` - a spec this plan carries in `specs:`. Leaving it would hand
stage 03 a live divergence against this plan's own declared conformance, so absorbing it costs one
branch and deferring it costs a false verification.

## Validation

- [x] When a `list` with `--all` returns no results, the `list` command shall emit `count: 0` and
      a hint naming `pyproject.toml`, and shall not name `--all`. —
      `tests/test_cli.py::test_command_list_empty_all_hint_names_pyproject`
- [x] When a `list` without `--all` returns no results, the `list` command shall emit `count: 0`
      and a hint naming `--all`. —
      `tests/test_cli.py::test_command_list_empty_hint_names_all`
- [x] When a docstring is truncated on the CLI, the size hint shall name `--docstring`. —
      `tests/test_introspect.py::test_truncate_default_suffix_is_byte_identical_cli_spelling`
- [x] When a docstring is truncated in an MCP tool payload, the size hint shall name
      `docstring=true` and shall not name `--docstring`. —
      `tests/test_introspect.py::test_truncate_mcp_escape_hatch_names_parameter` and
      `tests/test_mcp.py::test_show_module_tool_truncation_names_mcp_escape_hatch`
- [x] When `findSymbolTool` is called with `package` and matches nothing, the returned hint shall
      name `listPackagesTool` with `include_dev=true`. —
      `tests/test_mcp.py::test_find_symbol_tool_empty_with_package_names_list_tool`
- [x] When `findSymbolTool` is called without `package` and matches nothing, the returned hint
      shall name `package=<package>` and shall not name `listPackagesTool`. —
      `tests/test_mcp.py::test_find_symbol_tool_empty_without_package_hints_indexing`
- [x] When `listPackagesTool` is called with `include_dev=true` and returns no packages, the
      returned hint shall name `pyproject.toml` and shall not name `include_dev=true`. —
      `tests/test_mcp.py::test_list_packages_tool_empty_all_hint_names_pyproject`
- [x] When `listPackagesTool` is called without `include_dev` and returns no packages, the
      returned hint shall name `include_dev=true`. —
      `tests/test_mcp.py::test_list_packages_tool_empty_hint_names_include_dev`
- [x] Where `docstring=true` is passed to `showPackageApiTool`, the returned payload shall carry
      no `help[]` footer. —
      `tests/test_mcp.py::test_show_package_api_tool_docstring_suppresses_footer`
- [x] Where `docstring=true` is passed to `showModuleTool`, the returned payload shall carry no
      `help[]` footer. —
      `tests/test_mcp.py::test_show_module_tool_docstring_suppresses_footer`
- [x] Where `--docstring` is passed to `show --api` or to `inspect`, the CLI shall carry no
      `help[]` footer, unchanged by this plan. —
      `tests/test_cli.py::test_command_show_api_docstring_suppresses_footer` and
      `tests/test_cli.py::test_command_inspect_docstring_suppresses_footer`
- [x] The `## Divergences from the CLI` list in `specs/mcp/tools.md` shall contain no entry
      describing footer suppression under `docstring=true`. —
      inspection of the section shows four bullets
      (`refresh`, split `inspect`, split `show`, fixed fields); the only `docstring` mentions in
      that span are the prose declaring suppression to be parity
- [x] The test suite shall pass. —
      `uv run coverage run -m pytest` reports `293 passed in 28.73s`

## Risks / unknowns

- Threading the escape-hatch phrasing through `truncate()` touches the emission path every command
  shares. The mitigation is that the CLI spelling stays byte-identical, so any regression shows up
  on the MCP surface only, where the new assertions cover it.
- Removing the `docstring=true` footer removes a genuinely useful pointer for MCP callers
  (`Call getSymbolTool for one symbol's full detail`). It is removed anyway because the CLI does
  not offer it and parity was the chosen resolution; the amended
  `output-contract.md#contextual-disclosure` rule explicitly bars putting an unrelated hint back
  to keep the footer populated.
- `pyproject.toml` is a filename, not a runnable command, and Contextual disclosure asks for
  runnable next steps. Accepted deliberately: an empty `list --all` has no broader query left, and
  naming the file is more honest than inventing a command that would not help.

## Notes

**Why aligning beat listing.** Issue #29 offered both: list the `docstring=true` footer divergence,
or align the tools. Aligning was chosen because the divergence list is the file's own defence
against drift, and the shorter it is the more it is read. Listing would have grown it by two
entries while leaving a third - the false `getSymbolTool` one - to be deleted anyway. The cost is
real: MCP callers lose a useful pointer (`Call getSymbolTool for one symbol's full detail`) that
the CLI never offered. `output-contract.md#contextual-disclosure` gained a rule barring an
unrelated hint from being back-filled to keep the footer populated, so that loss cannot be quietly
undone later.

**A spec/spec conflict, not a code bug.** `list.md` required the unconditional `--all` empty hint;
`output-contract.md` forbids hinting a flag already set. The code satisfied the first by breaking
the second, so no amount of code reading would have settled it. Invariant 2 says fix the code or
amend the spec; here one spec had to yield first, and the cross-cutting behaviour won because a
command spec that contradicts an invariant is the narrower error.

**`pyproject.toml` is not a runnable command,** and Contextual disclosure asks for runnable next
steps. Taken deliberately on both surfaces: an empty `list --all` has no broader query left, so
naming the file that would have to change is more honest than inventing a command that would not
help. Recorded here because it is a knowing exception, not an oversight.

**Re-entry to stage 01 during stage 02, twice over.** Recorded in full after the Approach list. In
short: the techspec named the wrong branch for fix C, and the implementing agent reported the
mismatch rather than contorting the code to satisfy a defective criterion. The same pass surfaced
defect F. Both were absorbed by amending the plan and techspec before any verification report
existed, which is what kept the criterion-to-report mapping intact.

**A third artifact error, found at verification.** The techspec placed the escape-hatch constants
in `_constants.py` "beside `DEFAULT_TRUNCATE_LIMIT`". That constant is in `_introspect.py`, and
`_constants.py` is an attribution-scoped, encode-only subset of the upstream TOON constants
carrying a third-party licence header - project hint wording does not belong in it. The code was
right and the directive was wrong; the directive was corrected. Three artifact errors in one run,
all caught because implementation was told to report rather than comply.

**The durable part is the tests.** No test asserted any hint wording anywhere before this plan,
which is exactly why four of these five defects survived a green suite for a whole release. The 14
assertions are the bridge `specs/README.md`'s spec-anchored stance asks for, and they are what
stops the next hint from drifting silently.

## Follow-ups

- **Issue** [#20](https://github.com/andyrids/venv-axi/issues/20) - the PyMarkdown tokenizer crash
  is untouched here and stays open with its workaround.
- **Deferred to** - none.
- **Tracked as** - none.
