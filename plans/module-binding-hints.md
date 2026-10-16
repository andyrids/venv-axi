---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/symbol-graph.md
  - specs/commands/inspect.md
  - specs/commands/tree.md
  - specs/mcp/tools.md
authors:
  - specs/commands/show.md
issues: [142]
pr:
---

# Plan: Module binding hints

## Scope

[#142](https://github.com/andyrids/venv-axi/issues/142) follows up
[`module-binding-exclusion`](module-binding-exclusion.md), which stopped the walk recording a
module object as a symbol. Where a name in `__all__` is bound to a module that has no node of its
own, the name is now absent from the graph. Two shapes cause this:

- a private submodule exported under a public alias (`from . import _impl as impl`);
- a module registered only in `sys.modules`.

A lookup of such a name misses with the generic wording. On the CLI that is
`Module ... not found` plus the dotted-path statement, or `count: 0` with a "tree the root" hint.
An agent that followed `__all__` to the name cannot tell a deliberate binding from a typo.

This plan does not index those names. It makes the miss say what the name is bound to.

The issue gave three resolutions:

1. A node under the alias. Rejected, for the same two-keying reason as #130.
2. Walk the alias under its public spelling. Rejected on measurement. Of 97 importable packages
   in this repo's venv, walked two levels deep, none leaves an `__all__` name without any
   answer. The only private aliases are in `numpy.core`, and each is also a public shim module of
   the same dotted name. No module that exists only in `sys.modules` turned up.
3. Leave it declared. The miss stays declared, and is now explained.

The same measurement found a related miss that is more common: a name bound to a public module
whose own name differs. There were 23 such names. In `numpy.emath` and `py.path`, a lookup by the
bound name misses (`numpy.emath` is `numpy.lib.scimath`). The same check answers it, so it is in
scope as one rule with four cases. These are named by what the bound module (the target) is:

- a module of another package;
- a private module of this package;
- a public module of this package under its own name;
- the name itself, registered at import time where the walk cannot discover it.

Out of scope:

- **`show <binding> --api`.** It fails as "not installed" before any graph is read. Changing that
  needs its own decision on the outcome class. `specs/commands/show.md` Out of scope declares it,
  and it is filed at closeout.
- **`inspect pkg::sub`.** This is [#143](https://github.com/andyrids/venv-axi/issues/143), the
  symbol spelling of a module binding. It is a separate miss, and it may reuse this plan's check.
- **A binding deeper than one segment** (`pkg.impl.sub`, where `pkg.impl` is itself a binding).
  The parent has to import by its dotted name. Otherwise the miss keeps its existing wording.

## Implements

- **`specs/behaviors/symbol-graph.md`, Module bindings**
  - Defines the **module-binding miss**: a non-private dotted module name with no module node,
    whose parent imports and binds the final segment to a module.
  - Gives its four cases as `If` criteria, plus the fallback, the unchanged outcome class and the
    import boundary.
  - Explains why naming the target is not the guessed correction that Package resolution rules
    out: the target is the object's own `__name__`.
  - The last bullet now says that no module node answers for such a name, rather than that neither
    `tree` nor `inspect` answers.
  - Out of scope keeps indexing unplanned, with the measurement as the reason.
- **`specs/commands/inspect.md`, Failure modes**
  - Adds a binding message for each case, at the same error class and exit code as the existing
    miss.
  - Shares that message with `showModuleTool`, so it names no command.
  - Excludes it from the dotted-path statement, as the private-submodule message already is.
- **`specs/commands/tree.md`, Outputs**
  - Adds a hint for each case at `count: 0`.
  - For a public target, the hint names the target's own tree as the next step. Otherwise it names
    the root's tree.
- **`specs/mcp/tools.md`, Hint wording**: `getModuleTreeTool` mirrors `tree` in its own spelling.
  `showModuleTool` gets the shared message.
- **`specs/commands/show.md`** (`authors:`, prose only)
  - The alias sentence points to the binding miss.
  - The `show <binding> --api` failure becomes an Out of scope entry.

The graph is unchanged, so `specs/behaviors/cache-refresh.md` needs no schema bump.

## Approach

1. Add one shared check that turns a missed dotted module name into its binding case, or no case.
   - It returns no case for a private name, which keeps the existing private message.
   - It imports the parent by its dotted name. Any exception leaves no case, except an interrupt,
     which propagates.
   - It reads the attribute named by the final segment, and requires a module object.
   - It classifies the module's `__name__` against the root and against the private rule.
   - When the target is the looked-up name itself, it lists the parent's discoverable submodules.
2. Raise the binding message from the module lookup behind `inspect` and `showModuleTool`, keeping
   `SymbolNotFoundError`. Exclude it from the CLI's dotted-path statement.
3. Add the binding hint to the `tree` empty state on both surfaces, after the private check, with
   the next step spelled for each surface.
4. Fixtures and tests:
   - The fixture's `package.subpkg` already binds `impl` (to `package._impl`) and `codec`
     (`json`).
   - Add a public alias under a different name, outside `__all__`, so `show --api` counts do not
     move.
   - Cover the `sys.modules`-only case in test setup, not at fixture import.

## Validation

- [x] If `inspect` names a dotted module whose parent binds its final segment to a private module
  of the same package, then the `inspect` command shall raise `SymbolNotFoundError` with a message
  naming that private module and stating that it is never indexed.
  — `tests/test_introspect.py::test_show_module_states_what_a_module_binding_is_bound_to`;
  `tests/test_cli.py::test_command_inspect_module_binding_message_states_no_reading`
- [x] If `inspect` names a dotted module whose parent binds its final segment to a public module of
  the same package under another dotted name, then the `inspect` command shall raise
  `SymbolNotFoundError` with a message naming that module.
  — `tests/test_introspect.py::test_show_module_states_what_a_module_binding_is_bound_to`;
  `uv run venvaxi inspect numpy.emath` gives exit 1
- [x] If `inspect` names a dotted module whose parent binds its final segment to a module of
  another package, then the `inspect` command shall raise `SymbolNotFoundError` with a message
  naming that module as outside the named package.
  — `tests/test_introspect.py::test_show_module_states_what_a_module_binding_is_bound_to`;
  `uv run venvaxi inspect py.path` names `_pytest._py.path`
- [x] If `inspect` names a dotted module registered at import time that the walk's discovery of
  its parent does not list, then the `inspect` command shall raise `SymbolNotFoundError` with a
  message stating that the walk cannot discover it and it is never indexed.
  — `tests/test_introspect.py::test_module_binding_diagnoses_a_module_only_in_sys_modules`
- [x] If the `inspect` command raises a module-binding message, then it shall not append the
  dotted-path reading statement.
  — `tests/test_cli.py::test_command_inspect_module_binding_message_states_no_reading`
- [x] If `inspect` names a dotted module whose parent binds its final segment to an object that is
  not a module, then the `inspect` command shall give the existing `not found` message.
  — `tests/test_introspect.py::test_module_binding_is_none_for_a_non_module_binding`
- [x] If `inspect` names a private submodule directly, then the `inspect` command shall give the
  existing private-and-never-indexed message.
  — `tests/test_introspect.py::test_show_module_raises_for_private_submodule_named_directly`;
  `tests/test_introspect.py::test_module_binding_leaves_a_private_name_to_its_own_message`
- [x] If the parent module raises while the binding is read, then the miss shall keep its existing
  wording.
  — `tests/test_introspect.py::test_module_binding_is_none_when_the_parent_raises`;
  `tests/test_introspect.py::test_module_binding_is_none_when_the_parent_cannot_be_imported`
- [x] If the bound module raises while it is inspected, then the miss shall keep its existing
  wording.
  — `tests/test_introspect.py::test_module_binding_is_none_when_a_lazy_bound_module_raises`
- [x] When `tree` names a dotted module bound to a public module of the same package under another
  name, the `tree` command shall emit `count: 0` at `EX_OK` with a hint naming that module and
  `venvaxi tree <that module>`.
  — `tests/test_cli.py::test_command_tree_empty_hint_names_a_module_binding`
- [x] When `tree` names a dotted module bound to a private module of the same package, the `tree`
  command shall emit `count: 0` at `EX_OK` with a hint naming that module as never indexed and
  naming `venvaxi tree <root>`.
  — `tests/test_cli.py::test_command_tree_empty_hint_names_a_module_binding`
- [x] When `tree` names a dotted module registered at import time that the walk's discovery of its
  parent does not list, the `tree` command shall emit `count: 0` at `EX_OK` with a hint stating
  that the walk cannot discover it, that it is never indexed, and naming `venvaxi tree <root>`.
  — `tests/test_cli.py::test_command_tree_empty_hint_names_an_undiscoverable_module`
- [x] When `tree` names a dotted module bound to a module of another package, the `tree` command
  shall emit `count: 0` at `EX_OK` with a hint naming that module as outside the package and naming
  `venvaxi tree <root>`.
  — `tests/test_cli.py::test_command_tree_empty_hint_names_a_module_binding`
- [x] When `getModuleTreeTool` is called with a dotted module bound to a public module of the same
  package under another name, it shall return `count: 0` with a hint naming `getModuleTreeTool`
  with `name=` that module.
  — `tests/test_mcp.py::test_get_module_tree_tool_alias_hint_names_the_bound_module`
- [x] When `getModuleTreeTool` is called with a dotted module bound to a private module or a module
  of another package, it shall return `count: 0` with a hint naming `getModuleTreeTool` with
  `name=` the root.
  — `tests/test_mcp.py::test_get_module_tree_tool_binding_hint_names_the_root`
- [x] When `showModuleTool` is called with a module-binding miss, it shall return the TOON error
  block carrying the same binding message as `inspect`.
  — `tests/test_mcp.py::test_show_module_tool_binding_returns_the_shared_message`
- [x] The walk shall record no node under a module-binding name.
  — `tests/test_introspect.py::test_walk_records_no_node_under_a_module_binding_name`
- [x] When `venvaxi inspect numpy.emath` runs against this repository's venv, it shall fail with a
  message naming `numpy.lib.scimath`.
  — `uv run venvaxi inspect numpy.emath` gives
  ``Module `numpy.emath` is bound to module `numpy.lib.scimath` ``, exit 1

## Risks / unknowns

- **The check imports the parent on a warm cache.** A miss that used to read only the store now
  imports the parent module. The cost is paid on the miss path alone, and the walk has already run
  that package's import-time code once. The import guard follows the existing import boundary.
- **`__name__` is what the object says it is.** A module with a rewritten `__name__`, or a lazy
  proxy, reports whatever name it carries. The rule reports the binding as stated rather than
  second-guessing it, which is the same stance the walk takes on `__module__`.
- **Discoverability for the `sys.modules` case.** "The walk cannot discover it" has to be checked
  against the parent's own submodule discovery, not inferred from a missing node. A missing node
  alone could equally mean a submodule that failed to import during the walk.

## Notes

- **Why explain the miss instead of indexing the name.** The user chose this at planning, based
  on a measurement taken before stage 01:
  - 97 importable packages in this venv, walked two levels deep.
  - None leaves an `__all__` name without any answer.
  - The only private aliases (`numpy.core`'s 17) are each also a public shim module under the
    same dotted name.
  - No module that exists only in `sys.modules` turned up.

  Indexing (#142 resolution 2) would have meant new rules for Keying and Private submodules to
  fix nothing measured. The same probe found 23 names bound to a module under a different name
  (`numpy.emath`, `numpy.matlib.*`, `py.path`). So the scope widened from #142's two shapes to
  one rule with four cases, and the gate accepted that.
- **Re-entry from stage 03 (2026-10-16).** The `icm:spec-drift-auditor` raised F1-F5, and the
  user chose "fix all".
  - **F1 (medium, code).** Only the parent import and `getattr` sat inside the import boundary,
    so a lazily-loaded bound module that raised escaped as an unexpected error. This was
    reproduced, and now every read runs in one guard.
  - **F2-F4 (spec wording).** `tree.md` and `tools.md` had unconditional "root's tree"
    sentences. The fallback list omitted a module with no `__name__`. The alias bullet
    overclaimed.
  - **F5 (code).** The CLI re-ran the binding check.

  Delta: stage 01 reworded the specs and added a Validation criterion (the bound module raising).
  Stage 02 made the fix and added tests. Stage 03 re-verified.
- **`ModuleBindingMissError` is a private `SymbolNotFoundError` subclass, not a new public
  class.** It carries the diagnosis out of `show_module`, so the CLI's dotted-path carve-out reads
  it instead of re-diagnosing. Re-diagnosing would re-import a parent that already failed, and
  could disagree with the first result. Nothing observable changes: the error block prints only
  the message, and exit codes map by `isinstance`.
- **Gotchas.**
  - `importlib.util.LazyLoader` raises on the first touch only. Afterwards the module reads as an
    ordinary one, so the lazy-module test makes a single lookup.
  - A test that writes an importable file must use a `src_test` temp directory. Under
    `tmp_path`, `coverage report` fails with "No source for code", and CI runs that report.
  - At stage 02, a bare `uv run ruff format` used Ruff's default 88-column config, not pkgdx's
    79-column one, and joined split f-strings across three files. The files were reverted and
    re-edited. Format through `uv run -m prek run`.
- **No packaged-skill change.** The miss now names the correct move itself: the bound module,
  and its tree for an alias. The skill teaches no binding spelling, so no gotcha entry is owed
  under `specs/behaviors/skill-content.md`. The skill drift gate passes in the full run.
- **No `SCHEMA_VERSION` bump.** The walk and the graph are unchanged.
- **One test gap left open.** The fallback where the walk's discovery lists the module is tested
  only on a name that has a node (`package.subpkg.inner`). Testing it on a real miss needs a
  submodule that fails during the walk but imports at query time, which is a flaky fixture.

## Follow-ups

- Issue [#147](https://github.com/andyrids/venv-axi/issues/147): `show <binding> --api`, and any
  dotted non-module, fails as "not installed". Declared out of scope in `specs/commands/show.md`.
- Issue [#148](https://github.com/andyrids/venv-axi/issues/148): a distribution that ships
  several import names resolves to whichever `packages_distributions()` lists first (`PyYAML` →
  `_yaml`). Found during this plan's stage 03 audit. The behaviour predates this plan and no spec
  covers it.
- Issue [#143](https://github.com/andyrids/venv-axi/issues/143): `inspect pkg::sub`. It stays its
  own issue, and `module_binding` is a candidate building block for it.
