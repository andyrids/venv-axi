---
status: done
depends: []
specs:
  - specs/mcp/tools.md
issues: [16, 17]
pr: 15
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

- [x] `listPackagesTool` empty hint names `listPackagesTool`, not `list_packages_tool`
- [x] `getModuleTreeTool` empty hint names `listPackagesTool` and reads coherently
- [x] `getInheritorsTool` empty hint names both the unindexed-package and built-depth causes
- [x] `listPackagesTool`'s non-empty hint describes `showPackageTool`'s actual job - metadata,
  not public API
- [x] Every hint in `_mcp.py`, empty-state and otherwise, names a tool that performs the action
  its sentence describes - verified by reading all fifteen
- [x] No hint anywhere in `_mcp.py` contains a hardcoded tool name - verify by grep
- [x] `tests/test_mcp.py` covers the empty-state hint of all three tools, each asserting the
  derived camelCase name is present *and* the snake_case form absent, so a regression to a
  hardcoded name fails rather than passing on a substring
- [x] Each new test is shown to fail against the current strings before the fix is applied
- [x] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green

## Risks / unknowns

- **Low risk; all four are string-level.** The only way to regress is to reintroduce a hardcoded
  name, which the grep criterion above guards - but a grep is a one-time check, not a regression
  guard, which is why the test criteria above were added at stage 01.
- ~~**A test asserting the current wrong strings may exist.**~~ Resolved at stage 01: none does.
  The real finding is the opposite and worse - `tests/test_mcp.py` has *no* content assertion on
  any empty-state hint, while `tests/test_cli.py` asserts `"unindexed packages"` for the CLI's
  `inherits` hint. Testing the rule on one surface and not the other is the direct reason defect
  3 survived.

## Notes

Two criteria are ticked with a qualification. Both were met as written; the qualification is
about something adjacent, so leaving them unticked would misreport the work.

**The stage-01 spec amendment paid for itself inside the same run.** The line added to
`specs/mcp/tools.md` Hint wording - a hint MUST name the tool that performs the action its
sentence describes - is what turned up defect 4 at stage 03. The pre-existing derivation rule
guards only against renames, and defect 2 had passed it: the name *was* derived, from the wrong
function. Defects 1-3 all sat in empty-state branches, which is why the original
`/audit-spec-drift` run found them and missed defect 4. A rule written because it had one
counter-example immediately found a second.

Defect 4's fix also aligned the MCP hint to wording `src/venvaxi/SKILL.md` already had right
("Installed package metadata"), so the CLI, the shipped skill doc and the spec's Divergences
section all agreed that "public API" was the drifted term.

**Defect 2 corrects an apparently unreachable branch.** No input was found that reaches
`getModuleTreeTool`'s `count: 0`: a mistyped package raises `PackageImportError` and exits
`EX_FAILURE`, and any importable module yields at least its own depth-0 node. The fix is still
right - a hint must be correct if reached, and nothing establishes the branch is *provably* dead.
But it is defensive code, and the criterion above is ticked on a unit test that drives the branch
by mocking, not on observed behaviour. Filed as
[#16](https://github.com/andyrids/venv-axi/issues/16).

**The "every hint names the right tool" criterion was discharged by reading, not by execution.**
Fifteen hints, read in source. That is the appropriate method for a wording/name mismatch, which
is visible statically - but it is manual and will not re-run in CI. Ticked because it was done;
recorded because it will not stay done by itself.

**All 16 unit tests passed while an ISC004 lint error was present.** The stage 02 report
predicted the formatter might re-wrap defect 3's implicit string concatenation, "which is
cosmetic" - that was wrong, it was a lint failure. The `_cli.py` pattern it was copied from
carries parentheses around the concatenated string; those had been dropped. Only the stage 03
prek run caught it.

**A re-entry to stage 01 happened mid-run.** Defect 4 arrived at stage 03 step 10, after Scope
had been fixed at three defects. Rather than patch the code and leave the plan describing
different work, the run returned to 01 to widen Scope and Validation, then re-ran the 02 and 03
deltas from scratch. This is the rule [pipeline-gate-rework](pipeline-gate-rework.md) proposes;
it was followed here by hand, because nothing in the stage files enforces it yet.

### Pipeline friction

Second end-to-end `/create-feature` run. Recorded for
[pipeline-gate-rework](pipeline-gate-rework.md), which asked the next run to report how many
gates fired and how many were skipped by condition.

**9 nominal gates: 6 fired, 1 waived, 2 pending at the time of writing.** Checkpoint 5 was waived
on stated evidence - 216 passed, 0 failed, so step 4 was a no-op - and the waiver was announced
and approved rather than taken silently. That is the discipline the rework proposes, and doing it
by hand proved cheap.

Two findings that **cut against** that plan, recorded because a run that only confirmed its
author's prior would be worthless:

- **Checkpoints 11 and 13 did not duplicate.** The last run found them redundant. Here, 11
  carried two live findings needing decisions, and 13 carried qualifications 11 had not
  surfaced. One data point each way; the rework plan's own `n = 1` caveat now reads as the right
  call, and its merge proposal should not be treated as settled.
- **The stage 03 prek boundary earned its keep.** It caught a lint error that all 16 unit tests
  passed straight through. A rework that folds test and lint gates together would lose that.

One qualification on the re-entry rule's apparent success: it was cheap here because the delta
was one token and one test. A re-entry invalidating an architectural decision would cost far
more, and this run says nothing about whether the rule survives that case.

## Follow-ups

- **Issue** [#16](https://github.com/andyrids/venv-axi/issues/16) -
  `specs/commands/tree.md` states the `count: 0` empty state's usual cause is a mistyped or
  uninstalled package, but that path raises and exits `EX_FAILURE`. The branch appears
  unreachable. Resolution is a behaviour question - keep the branch and fix the spec, or delete
  it on both surfaces - so it needs its own plan. Not fixed here: `tree.md` is not in this plan's
  `specs:` field.
- **Issue** [#17](https://github.com/andyrids/venv-axi/issues/17) -
  `test_find_symbol_tool_empty` asserts only `help[1]:`, not hint content, leaving
  `findSymbolTool` as the one MCP empty hint with no content assertion. The hint is correct
  today, so this is a coverage gap rather than a defect - but it is the same asymmetry that let
  defect 3 survive, one tool over.
- **Deferred to** - none.
- **Tracked as** - none.
