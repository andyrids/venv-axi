---
status: in-progress
depends: []
specs:
  - specs/mcp/tools.md
issues: []
pr:
---

# Plan: Fix MCP hint parity bugs

## Scope

Four defects in `_mcp.py` next-step hints, each violating a rule its own spec already states.
All are single-line fixes; none changes a tool signature or return shape.

Defects 1-3 sit in empty-state branches and were surfaced by the first `/audit-spec-drift` run
against the new spec tree, absorbed from [spec-driven-icm](spec-driven-icm.md)'s Follow-ups.
Defect 4 sits in a *non*-empty branch and was found at stage 03, by auditing every hint against
the spec line stage 01 had just added - see the re-entry recorded in Notes.

## Implements

`specs/mcp/tools.md` - the derive-the-name rule, the CLI parity principle, and (via
`specs/commands/inherits.md`) the requirement that an empty `inherits` hint names both causes.

Stage 01 amended that spec's Hint wording section with one sentence: a hint MUST name the tool
that performs the action its sentence describes. The pre-existing derivation rule guards only
against *renames*, and defect 2 below passed it - the name was derived, just from the wrong
function. A rule with a live counter-example in the repo is worth stating.

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

**4. Sentence names the wrong tool's job** (`_mcp.py:95-99`). `list_packages_tool`'s non-empty
hint reads `` Call `showPackageTool` for a package's public API ``. `showPackageTool` returns
fixed metadata fields - `name`, `version`, `location` - which the spec's own Divergences section
states. Public API is `showPackageApiTool`. Here the *sentence* drifted, not the name: the CLI
counterpart reads ``Run `venvaxi show <package>` for package info``, which is correct, and the
chain list -> metadata -> API is the intended one. Reword to `for package metadata`.

None of the four is listed under the spec's Divergences section, so all four are bugs rather
than deliberate differences.

## Validation

- [ ] `listPackagesTool` empty hint names `listPackagesTool`, not `list_packages_tool`
- [ ] `getModuleTreeTool` empty hint names `listPackagesTool` and reads coherently
- [ ] `getInheritorsTool` empty hint names both the unindexed-package and built-depth causes
- [ ] `listPackagesTool`'s non-empty hint describes `showPackageTool`'s actual job - metadata,
  not public API
- [ ] Every hint in `_mcp.py`, empty-state and otherwise, names a tool that performs the action
  its sentence describes - verified by reading all fifteen
- [ ] No hint anywhere in `_mcp.py` contains a hardcoded tool name - verify by grep
- [ ] `tests/test_mcp.py` covers the empty-state hint of all three tools, each asserting the
  derived camelCase name is present *and* the snake_case form absent, so a regression to a
  hardcoded name fails rather than passing on a substring
- [ ] Each new test is shown to fail against the current strings before the fix is applied
- [ ] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green

## Risks / unknowns

- **Low risk; all three are string-level.** The only way to regress is to reintroduce a hardcoded
  name, which the grep criterion above guards - but a grep is a one-time check, not a regression
  guard, which is why the test criteria above were added at stage 01.
- ~~**A test asserting the current wrong strings may exist.**~~ Resolved at stage 01: none does.
  The real finding is the opposite and worse - `tests/test_mcp.py` has *no* content assertion on
  any empty-state hint, while `tests/test_cli.py` asserts `"unindexed packages"` for the CLI's
  `inherits` hint. Testing the rule on one surface and not the other is the direct reason defect
  3 survived.

## Notes

Populated at closeout.

## Follow-ups

Populated at closeout.
