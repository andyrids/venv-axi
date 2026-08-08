---
status: done
depends: []
specs:
  - specs/commands/tree.md
  - specs/mcp/tools.md
issues: [16, 17]
pr: 25
---

# Plan: Correct the tree empty-state cause

## Scope

`specs/commands/tree.md` states a cause for the `count: 0` empty state that cannot produce it:

> Empty result: `count: 0` plus a hint naming `venvaxi list`, because the usual cause is a
> mistyped or uninstalled package.

A mistyped or uninstalled package raises and exits `EX_FAILURE`. It never reaches `count: 0`.
Filed as [#16](https://github.com/andyrids/venv-axi/issues/16), surfaced during
[mcp-hint-parity](mcp-hint-parity.md)'s stage-03 spec-conformance check.

That issue offered two resolutions - fix the spec, or delete an apparently unreachable branch.
**Deletion is off the table: the branch is live.** See Approach. This widens the fix beyond what
the issue scoped, because once the real cause is a bad *submodule* rather than a bad *package*,
the `venvaxi list` hint is unhelpful on both surfaces and a third drift in the same spec file
becomes load-bearing.

Folds in [#17](https://github.com/andyrids/venv-axi/issues/17), a test-coverage gap in the same
file this plan already edits. It contributes nothing to `specs:` above.

## Implements

`specs/commands/tree.md` - the empty-result rule and the invocation table.

`specs/mcp/tools.md` - via its CLI-parity principle and the rule that a hint MUST name the tool
that performs the action its sentence describes. `getModuleTreeTool`'s empty hint was corrected
under [mcp-hint-parity](mcp-hint-parity.md) to name `listPackagesTool` instead of
`showModuleTool`. That fix was right against the spec as written; this plan changes the spec, so
the hint moves again.

## Approach

**The branch is reachable.** `store.get_module_tree` (`_store.py:333-351`) returns `[]` whenever
the root node is missing:

```python
root = self.get_node(module_name)
if root is None:
    return []
```

while `_build_store_for` validates only the **top-level** root - `_top_level_root(name)` at
`_introspect.py:708`, then `_ensure_valid_name` and `_ensure_installed` at 709-711. So a dotted
name whose root imports but whose tail was never walked lands on `count: 0` at `EX_OK`. Three
inputs reach it:

- `venvaxi tree rich.nosuchmodule` - the submodule does not exist
- `venvaxi tree <pkg>._private` - private submodules are skipped by the walk
  (`_introspect.py:503`)
- `venvaxi tree <pkg>.<sub>` where `<sub>` failed to import during the walk and was
  logged-and-skipped (`_introspect.py:505-515`)

Neither existing test could have settled this: `tests/test_cli.py:366-377` and
`tests/test_mcp.py:300-304` both `mock.patch` `get_module_tree` to return `[]`, so the branch is
covered without any input ever reaching it. That is why the reachability question survived the
issue that raised it.

**1. The empty-result rule** (`specs/commands/tree.md:32-33`). Replace with the real cause: a
dotted name whose root package resolved and imported, but whose tail has no node in the graph -
the submodule does not exist, is private, or failed to import during the walk. State the negative
half too, because it is the half that was wrong: a mistyped or uninstalled *package* raises and
exits `EX_FAILURE`, and never reaches this branch.

**2. Hint wording, both surfaces** (`_cli.py:322-323`, `_mcp.py:255-259`). A package list does not
help someone who named a submodule that is not there; the root package's own tree does, because
it shows which submodules exist. Reword both to point there. Derive the MCP tool name via
`camel_case(fn.__name__)` per `specs/mcp/tools.md` - never hardcode, and keep the two surfaces
behaviourally aligned while phrased for their own caller.

**3. The invocation table** (`specs/commands/tree.md:16`). It calls `package` a "Distribution
name", and `_cli.py:597` says "Package (distribution) name" - yet `get_module_tree` explicitly
supports dotted module names (`_introspect.py:813-838`, tested at
`tests/test_introspect.py:647-653`). This is a pre-existing drift, but it stops being cosmetic
here: rule 1 above cites a dotted input as the cause of the empty state, so leaving the table
saying dotted names are illegal would make the spec contradict itself in two adjacent sections.

Invariant 4 in `specs/README.md` makes `--help` authoritative, so the help string is the thing
that must be right first; the spec table follows it.

**4. `findSymbolTool` empty-hint coverage** (issue #17). `tests/test_mcp.py:186-193` asserts only
that a `help[1]:` footer exists:

```python
assert result.startswith("count: 0")
assert "help[1]:" in result
```

After [mcp-hint-parity](mcp-hint-parity.md) this is the only MCP empty-state hint with no content
assertion, and that exact asymmetry is why one of that plan's defects reached a spec audit
instead of CI. The hint itself is correct today - this is a coverage gap, not a defect. Extend
the test, or add a sibling, covering both branches: with `package` set (`listPackagesTool`
present, `list_packages_tool` absent) and without (the re-call wording present). Follow
`ICM/_config/reference-toolchain-pytest.md`: assert the wrong form absent as well as the right
form present, because a one-way assertion passes on a substring.

## Validation

- [x] `venvaxi tree rich.nosuchmodule` emits `count: 0` at exit 0
- [x] Its hint names the root package's tree, and the parallel `getModuleTreeTool` hint does the
      same in MCP phrasing with a camelCase-derived name
- [x] The `count: 0` test is driven by a **real input**, not by `mock.patch` on
      `get_module_tree` - on both surfaces
- [x] `venvaxi tree nonexistentpkg` still raises and exits `EX_FAILURE`, so the rule's negative
      half is covered too
- [x] The new `tree.md` empty-result rule names a cause the first criterion above actually
      produces
- [x] `venvaxi tree --help` and `specs/commands/tree.md:16` agree that dotted module names are
      accepted
- [x] No hint in `_mcp.py` contains a hardcoded tool name - verify by grep
- [x] `test_find_symbol_tool_empty` asserts hint content on both branches, wrong form absent
- [x] Each new test is shown to fail against the current strings before the fix is applied
- [x] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green

## Risks / unknowns

- **`rich.nosuchmodule` as a test input depends on `rich` staying installed.** It is a dev
  dependency, not a runtime one (removed as a runtime dep in v0.1.0rc1). A test fixture package
  under the repo's control would be sturdier if one already exists.
- **The private-submodule path may be the more honest reproducer** than a nonexistent one, since
  it reaches `count: 0` for a module that genuinely exists. Worth checking which makes the better
  regression test.
- **Unknown: whether the `_private` and failed-import cases deserve distinct hints.** One hint
  covering all three causes is the assumption here; if the wording ends up vague enough to be
  useless, that is the signal to reconsider rather than to pad it.
- **Low risk overall.** One spec file, two hint strings, one help string, and tests.

## Notes

One criterion is ticked with a qualification, following the precedent set by
[mcp-hint-parity](mcp-hint-parity.md); the qualification is stated rather than implied by the
tick.

**The reachability premise was re-verified live before any spec text was written.** At stage 01,
`uv run venvaxi tree rich.nosuchmodule` and `uv run venvaxi tree rich._log_render` both emitted
`count: 0` at exit 0, and `uv run venvaxi tree nonexistentpkg` raised at exit 1 - so the branch
is live on a nonexistent *and* on a private submodule, issue #16's deletion option stays off the
table, and no re-entry was needed. The third cause (failed import) is exercised incidentally in
every test walk: the fixture package's `error` submodule fails to import and is
logged-and-skipped.

**`specs/mcp/tools.md` was deliberately not edited.** Its Hint wording rules (MCP phrasing,
camelCase derivation, name-the-tool-that-performs-the-action) plus the Local parity principle
fully determine the new MCP hint; a per-tool rule would duplicate what is already written. The
MCP hint self-references `getModuleTreeTool` - correct, because the tool that shows the root's
tree is the tool itself - with the name still derived via `camel_case(fn.__name__)`.

**The criterion 9 qualification.** The three tree tests failed against the pre-fix strings, with
the failing assertion proving a real input reached `count: 0` on the old code. The two
`findSymbolTool` tests *cannot* fail pre-fix - the hint is already correct (issue #17 is a
coverage gap, as this plan's Approach states) - so their guard value was demonstrated by
mutation instead: hardcoding `cname = "list_packages_tool"` made the with-package test fail;
the mutation was then reverted.

**The `fake_package` fixture moved from `tests/test_introspect.py` to `tests/conftest.py`** so
both surface test modules can drive the branch with a real input, answering the first risk (no
dependence on `rich` staying installed - `rich.*` inputs were manual verification only). The
sibling branch ([facade-method-resolution](facade-method-resolution.md)) made the identical
move independently, so the merge sees the same change on both sides, alongside the known
trivial `CHANGELOG.md` overlap.

**The one-hint-for-three-causes assumption held.** The wording ('for the submodules that
exist') stays concrete because the hint embeds the actual root name rather than a placeholder,
per contextual disclosure - no distinct hints were needed, and no vagueness signal fired.

**Run in auto mode.** Checkpoints were discharged with recorded evidence in the stage outputs
instead of blocking: the stage 03 test gate's condition (249 passed, 0 failed - no gate), the
step 12 condition (step 10 forced no changes), and the eval check (no eval encodes the tree
hint). The stage 03 prek boundary was kept separate from the test gate and passed first run.

**Ripple check:** besides this plan, `specs/commands/tree.md` and `specs/mcp/tools.md` are
named only by frozen (`status: done`) plans, so no other plan needed revising.

## Follow-ups

- None.
