---
status: planned
depends: []
specs:
  - specs/mcp/tools.md
issues: []
pr:
---

# Plan: Fix MCP hint parity bugs

## Scope

Three defects in `_mcp.py` empty-state hints, each violating a rule its own spec already states.
All are single-line fixes; none changes a tool signature or return shape.

Surfaced by the first `/audit-spec-drift` run against the new spec tree, and absorbed from
[spec-driven-icm](spec-driven-icm.md)'s Follow-ups.

## Implements

`specs/mcp/tools.md` - the derive-the-name rule, the CLI parity principle, and (via
`specs/commands/inherits.md`) the requirement that an empty `inherits` hint names both causes.

## Approach

**1. Hardcoded snake_case tool name** (`_mcp.py:90`). `list_packages_tool`'s own empty hint reads
`` Call `list_packages_tool` with include_dev=true `` - the literal function name, in snake_case.
Every other hint in the file derives it via `camel_case(fn.__name__)`. This is exactly the
staleness the spec's rule exists to prevent, and it currently names a tool that is not registered
under that name at all. Replace with `camel_case(list_packages_tool.__name__)`.

**2. Wrong tool named in the tree hint** (`_mcp.py:238-240`). `get_module_tree_tool`'s empty hint
resolves `cname` from `show_module_tool` but keeps the CLI's wording, emitting
`` Call `showModuleTool` for the venv package list ``. `showModuleTool` does not list packages.
The wording was carried over from the CLI's `list`-referencing text while the tool name was
swapped. Point it at `list_packages_tool` so the name and the sentence agree.

**3. Incomplete inherits hint** (`_mcp.py:218-222`). The CLI names both causes of an empty
`inherits` result - subclasses in an unindexed package, and subclasses below the built depth. The
MCP hint says only `` Call `findSymbolTool` to locate a base class's name ``, which drops the
depth cause and misdescribes the problem: the base class name is already known, and the
ambiguity is about *subclasses*. Rewrite to carry both causes in MCP phrasing.

None of the three is listed under the spec's Divergences section, so all three are bugs rather
than deliberate differences.

## Validation

- [ ] `listPackagesTool` empty hint names `listPackagesTool`, not `list_packages_tool`
- [ ] `getModuleTreeTool` empty hint names `listPackagesTool` and reads coherently
- [ ] `getInheritorsTool` empty hint names both the unindexed-package and built-depth causes
- [ ] No hint anywhere in `_mcp.py` contains a hardcoded tool name - verify by grep
- [ ] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green

## Risks / unknowns

- **Low risk; all three are string-level.** The only way to regress is to reintroduce a hardcoded
  name, which the grep criterion above guards.
- **A test asserting the current wrong strings may exist** and will need updating alongside.

## Notes

Populated at closeout.

## Follow-ups

Populated at closeout.
