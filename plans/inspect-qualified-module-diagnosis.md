---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/output-contract.md
  - specs/behaviors/skill-content.md
  - specs/behaviors/symbol-graph.md
  - specs/commands/inspect.md
  - specs/mcp/tools.md
authors: []
issues: [143]
pr:
---

# Plan: Inspect qualified module diagnosis

## Scope

[#143](https://github.com/andyrids/venv-axi/issues/143) follows up
[#130](https://github.com/andyrids/venv-axi/issues/130). Before #130 the walk recorded a submodule
bound on its parent as an `attribute` node keyed `pkg::sub`, so `inspect pkg::sub` answered, with
the wrong kind. #130 removed that node, and the same spelling now misses with nothing pointing at
the spelling that answers. Reproduced against this checkout at stage 01:

| Argument              | Message today                                                    |
| --------------------- | ---------------------------------------------------------------- |
| `venvaxi::exceptions` | ``Symbol `venvaxi::exceptions` not found``                       |
| `numpy::emath`        | ``Symbol `numpy::emath` not found``                              |
| `py::path`            | ``Symbol `py::path` not found``                                  |
| `numpy.emath`         | ``Module `numpy.emath` is bound to module `numpy.lib.scimath` `` |

Every row exits 1 with the generic `Run venvaxi --help` footer. An agent that reads
`from venvaxi import exceptions` and writes it in symbol form gets a bare not-found and a generic
hint. The last row is the dotted spelling of the second, which
[`module-binding-hints`](module-binding-hints.md) already diagnoses; the symbol spelling of the
same binding is still a generic miss.

This plan makes a symbol-mode miss `<module>::<name>` read itself against the dotted name
`<module>.<name>`, and say what answers. Two decisions were taken at planning, and a third at the
stage 03 re-entry (see Notes):

- **Scope: the module, then the #142 binding cases.** The issue proposed only the first -
  `<module>.<name>` is a module, so name it. The user widened it to the binding cases too, so
  `inspect numpy::emath` gets the answer `inspect numpy.emath` already gets, rather than one
  spelling of a binding being diagnosed and the other not. `module-binding-hints` named its check
  as the candidate building block for this.
- **Placement: the fact in the message, the next step in `help[]`.** The issue proposed `help[]`.
  The message is shared with `getSymbolTool`, so it states the fact and names no command; the
  footer names the surface's next step where a public module answers, and on the CLI replaces the
  generic footer. That is the shape `module-binding-hints` gave `tree` (fact, then the surface's
  step), and it needs the CLI's Error shape to allow an error-specific footer, which it did not.
- **Evidence for "is a module": the graph, then discovery - never the parent's attribute.**
  Within the lookup's depth the graph's node answers; below it, the walk's own discovery of the
  parent's submodules. The first design read the parent's live attribute below the lookup's depth,
  which made the answer depend on what the process had already imported.

Out of scope, each declared in `specs/commands/inspect.md`:

- **A dotted or private tail after `::`** (`pkg::sub.Thing`, `pkg::_x`). The first would be a
  cross-separator spelling correction. Never.
- **The same reading on `inherits`.**
- **A footer on the module-mode binding miss** (`inspect numpy.emath`). Its message already names
  the target. Recorded so the asymmetry this plan creates is declared.

## Implements

- **`specs/commands/inspect.md`, Data requirements**: defines **the lookup's depth** - the default
  build depth, or the module part's own depth where deeper - so `pkg::x` and `pkg.a::x` read a
  dotted name within it and `pkg.a.b::x` one below it. It is a fact about the name, not the cache.
- **`specs/commands/inspect.md`, Failure modes**
  - Adds the symbol-mode miss: a `<name>` that is a single Python identifier, with a non-private
    `<module>.<name>`, is read against `<module>.<name>`, at the same error class and exit code.
  - A module of the package - the graph's node within the lookup's depth, or the walk's discovery
    below it - gives "`<module>.<name>` is a module", never a binding claim, and a
    `venvaxi inspect <module>.<name>` footer.
  - Otherwise a module-binding miss in the symbol spelling gives the binding fact, with a
    `venvaxi inspect <target>` footer for a public target and the generic footer otherwise.
  - The message is shared with `getSymbolTool` and names no command. Where it names a module, it
    names it in its import spelling (`python-dotenv::main` names `dotenv.main`), as the footer does.
    The package the foreign case names is the caller's root as given, as in module mode.
- **`specs/commands/inspect.md`, Out of scope**: the three entries above.
- **`specs/behaviors/output-contract.md`, Error shape**
  - A CLI error takes an error-specific footer hint in place of the generic footer where its
    command's failure modes declare one as a footer - declared per failure mode, never inferred.
    A next step stated inside a message is unaffected.
  - The MCP sentence moves to the same declared-per-failure wording.
  - The `Unexpected error:` shape always takes its surface's fallback.
- **`specs/behaviors/symbol-graph.md`, Module bindings**
  - The symbol spelling asks first whether `<module>.<name>` is a module, and reads the binding
    only where none answers, with the cases as written and each fact in the caller's spelling.
  - The outcome class is the symbol miss's, and the footer is the one `inspect` declares; "only its
    wording changes" governs the module spelling alone.
  - The lookup's depth, never the cache's, fixes which evidence decides whether a module answers,
    and the parent's attribute is never that evidence. That discovery read is made under the
    imported module's own `__name__`, as the walk reads it; the binding cases' same-name check
    stays #142's in both spellings.
  - A private dotted name is never asked about, and the discovery read is an import boundary like
    the binding read. A raise in the discovery read ends the check: no binding is read.
- **`specs/mcp/tools.md`, Hint wording**: `getSymbolTool`'s error carries a `showModuleTool`
  footer hint with `name=` the module wherever `inspect`'s footer names one, and no footer
  otherwise.
- **`specs/behaviors/skill-content.md`** (unamended): the packaged skill's qualified-name gotcha
  gains its converse, as an observed failure mode that costs an agent a query.

The graph is unchanged, so `specs/behaviors/cache-refresh.md` needs no schema bump.

## Approach

1. Share the walk's discovery of a parent's submodules between the module-binding check and a new
   guarded "does discovery list this dotted name" read, inside the existing import boundary.
2. On a symbol-mode miss, after both the direct lookup and facade member resolution miss:
   - check the shape (single Python identifier, non-private dotted name);
   - within the lookup's depth, look up the module node; below it, ask discovery, which lists
     nothing where `<module>` imports under another `__name__`, and whose raise ends the check;
   - otherwise read the binding, inside the existing import boundary, leaving out a target that is
     `<module>.<name>` itself and that #142's same-name check lists, under the looked-up name (one
     it does not list is reported as registered at import time);
   - raise a `SymbolNotFoundError` that carries the module to inspect, if any.
3. Give each surface's single error-render site an error-specific footer hint for that error - the
   CLI entry point in place of the generic footer, the MCP error wrapper where it had none.
4. Keep the skill drift gate's hand-copied CLI error arm on the same rendering source.
5. Add the converse clause to the packaged skill's qualified-name gotcha, then sync the skill copy.
6. Fixtures and tests:
   - `package.subpkg` already binds `inner`, `nested` (= `inner`), `impl` (= `package._impl`) and
     `codec` (= `json`), and `package.subpkg.inner` has `leaf` - no fixture change expected.
   - The import-time-only case is set up in the test, as `module-binding-hints` did.

## Validation

Notation, per `specs/commands/inspect.md`: `<module>::<name>` is the caller's spelling as given, and
`<module>.<name>` is its dotted name in import spelling. **A single identifier** is a single Python
identifier, as `foo_bar` is and `foo.bar` and `foo-bar` are not. **The walk's discovery of
`<module>`** is the read that decides, below the lookup's depth, whether a module answers, as
`specs/behaviors/symbol-graph.md` declares. The miss makes it in that call, over the imported
`<module>`'s `__path__` as it then stands, under the `__name__` `<module>` carries, so where that
is not `<module>`'s own dotted name it lists nothing. **The same-name listing of `<module>`** is
the binding cases' same-name check, #142's and shared with module mode: the same `__path__`,
listed under `<module>`'s dotted name whatever `__name__` it carries. **A module answers** for
`<module>.<name>` where the graph holds its `module` or `package` node and it lies within the
lookup's depth, or the walk's discovery of `<module>`'s submodules lists it and it lies below that
depth. **No module answers** where neither holds and, below the lookup's depth, reading that
discovery raised nothing.

- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and lies within the lookup's depth, and the graph
  holds a module node `<module>.<name>`, then the `inspect` command shall raise
  `SymbolNotFoundError` with a message stating that `<module>.<name>` is a module.
  — `tests/test_introspect.py::test_get_symbol_states_a_symbol_spelled_module_is_a_module`;
  `uv run venvaxi inspect venvaxi::exceptions` and `uv run venvaxi inspect rich::console`, exit 1
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and lies below the lookup's depth, and the walk's
  discovery of `<module>`'s submodules lists it, then the `inspect` command shall raise
  `SymbolNotFoundError` with a message stating that `<module>.<name>` is a module.
  — `tests/test_introspect.py::test_get_symbol_states_a_below_depth_module_from_discovery`;
  `tests/test_introspect.py::test_get_symbol_states_a_below_depth_module_that_fails_to_import`;
  `uv run venvaxi inspect numpy.f2py.tests::test_callback`, exit 1
- [x] If `inspect` raises the message stating that `<module>.<name>` is a module, then the message
  shall make no claim about what `<module>` binds `<name>` to.
  — `tests/test_introspect.py::test_get_symbol_states_a_symbol_spelled_module_is_a_module` and
  `tests/test_introspect.py::test_get_symbol_states_a_below_depth_module_from_discovery`, each
  pinning the message by exact equality
- [x] If `inspect` raises the message stating that `<module>.<name>` is a module, then its footer
  shall name `venvaxi inspect <module>.<name>` in place of the generic footer.
  — `tests/test_cli.py::test_main_inspect_module_miss_footer_names_the_module`;
  `tests/test_cli.py::test_error_hint_is_declared_only_for_a_carried_module[carried-module]`
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and no module answers for it, and `<module>` binds
  `<name>` to a public module of the same package under another dotted name, then the `inspect`
  command shall raise `SymbolNotFoundError` with a message naming that module.
  — `tests/test_introspect.py::test_get_symbol_states_what_a_symbol_spelled_binding_is_bound_to`
  (`nested` case); `uv run venvaxi inspect numpy::emath`, exit 1
- [x] If `inspect` raises, for a symbol-mode `<module>::<name>`, a binding message naming a public
  module of the same package, then its footer shall name `venvaxi inspect <that module>` in place
  of the generic footer.
  — `tests/test_cli.py::test_main_inspect_module_miss_footer_names_the_module` (`.subpkg::nested`
  case); `uv run venvaxi inspect numpy::emath` gives footer
  ``Run `venvaxi inspect numpy.lib.scimath` for its symbols``
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and no module answers for it, and `<module>` binds
  `<name>` to a private module of the same package, then the message shall name that private
  module and state that it is never indexed.
  — `tests/test_introspect.py::test_get_symbol_states_what_a_symbol_spelled_binding_is_bound_to`
  (`impl` case)
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and no module answers for it, and `<module>` binds
  `<name>` to a module of another package, then the message shall name that module as outside the
  named package.
  — `tests/test_introspect.py::test_get_symbol_states_what_a_symbol_spelled_binding_is_bound_to`
  (`codec` case);
  `tests/test_introspect.py::test_get_symbol_lists_nothing_under_a_parent_of_another_name` (below
  depth); `uv run venvaxi inspect py::path` names `_pytest._py.path`, exit 1
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and no module answers for it, and `<module>` binds
  `<name>` to a module `<module>.<name>` registered at import time, which the same-name listing of
  `<module>` does not list, then the message shall state that the walk cannot discover it and that
  it is never indexed. —
  `tests/test_introspect.py::test_get_symbol_diagnoses_a_symbol_spelled_module_only_in_sys_modules`
- [x] If `inspect` raises, for a symbol-mode `<module>::<name>`, a binding message for a private
  module, a module of another package, or a module registered at import time, then its footer
  shall be the generic footer.
  — `tests/test_cli.py::test_main_inspect_module_miss_without_a_module_keeps_generic_footer`
  (`.subpkg::impl`, `.subpkg::codec` and `.subpkg::dyn` cases);
  `uv run venvaxi inspect py::path` gives the generic footer, exit 1
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and lies within the lookup's depth, the same-name
  listing of `<module>` lists it, the graph holds no node for it, and `<module>` binds `<name>`
  to no module other than `<module>.<name>` itself, then the `inspect` command shall raise
  `SymbolNotFoundError` with the existing `not found` message.
  — `tests/test_introspect.py::test_get_symbol_keeps_not_found_for_a_module_missing_within_depth`
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and no module answers for it, and `<module>` binds
  `<name>` to nothing, to an object that is not a module, or to a module carrying no string
  `__name__`, then the `inspect` command shall raise `SymbolNotFoundError` with the existing
  `not found` message.
  — `tests/test_introspect.py::test_get_symbol_keeps_not_found_for_an_excluded_symbol_spelling`
  (`::nosuch` case);
  `tests/test_introspect.py::test_module_binding_is_none_for_a_non_module_binding` and
  `tests/test_introspect.py::test_module_binding_is_none_for_a_module_without_a_name` (the
  shared binding read); `uv run venvaxi inspect venvaxi::nosuch`, exit 1
- [x] If a query in the same process builds the graph deeper or imports `<module>.<name>` between
  two `getSymbolTool` calls for a `<module>::<name>` whose `<module>.<name>` is not private and lies
  below the lookup's depth, where the parent of `<module>.<name>` imports under its own dotted name
  in both calls and its `__path__` lists the same entries in both, then the two calls shall agree
  on whether their message states that `<module>.<name>` is a module.
  — `tests/test_mcp.py::test_get_symbol_tool_below_depth_miss_is_unchanged_by_a_deeper_query`
- [x] If the cache already holds the graph deeper than the lookup's depth, then a symbol-mode miss
  on a `<module>::<name>` whose `<name>` is a single identifier and whose `<module>.<name>` is not
  private and lies below the lookup's depth shall state that `<module>.<name>` is a module exactly
  where the walk's discovery of `<module>` lists it.
  — `tests/test_introspect.py::test_get_symbol_states_a_below_depth_module_that_fails_to_import`
  (`deeper-cache` case)
- [x] If `<name>` contains a `.`, or `<module>.<name>` is private, then a miss on
  `<module>::<name>` shall keep the existing `not found` message.
  — `tests/test_introspect.py::test_get_symbol_keeps_not_found_for_an_excluded_symbol_spelling`
  (`::subpkg.inner` and `::_impl` cases)
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and lies below the lookup's depth, and reading the
  walk's discovery of `<module>` raises, then the `inspect` command shall raise
  `SymbolNotFoundError` with the existing `not found` message.
  — `tests/test_introspect.py::test_get_symbol_keeps_not_found_when_discovery_raises`;
  `tests/test_introspect.py::test_get_symbol_reads_no_binding_when_only_discovery_raises`
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and no module answers for it, and `<module>` raises
  while it is read for its binding, then the `inspect` command shall raise `SymbolNotFoundError`
  with the existing `not found` message.
  — `tests/test_introspect.py::test_get_symbol_keeps_not_found_when_the_parent_raises`
- [x] If `inspect` names a `<module>::<name>` that resolves to no symbol, where `<name>` is a single
  identifier, `<module>.<name>` is not private and lies below the lookup's depth, and importing the
  parent of `<module>.<name>` gives a module whose `__name__` is not that parent's dotted name, then
  the message shall not state that `<module>.<name>` is a module.
  — `tests/test_introspect.py::test_get_symbol_lists_nothing_under_a_parent_of_another_name`
- [x] If `KeyboardInterrupt` is raised while `<module>` is read for discovery or for its binding,
  then it shall propagate.
  — `tests/test_introspect.py::test_get_symbol_propagates_an_interrupt_from_the_binding_read`;
  `tests/test_introspect.py::test_get_symbol_propagates_an_interrupt_from_the_discovery_read`
- [x] If `inspect` raises any symbol-mode miss message above, then it shall exit `EX_FAILURE`.
  — `tests/test_cli.py::test_main_inspect_module_miss_footer_names_the_module`;
  `tests/test_cli.py::test_main_inspect_module_miss_without_a_module_keeps_generic_footer`
- [x] When `<module>::<name>` resolves to a symbol while `<module>.<name>` is also a module, the
  `inspect` command shall answer with the symbol's node.
  — `tests/test_introspect.py::test_get_symbol_answers_a_real_symbol_that_is_also_a_module`;
  `tests/test_conformance.py::test_symbol_named_like_a_submodule_keeps_its_answer`
  (`polars` and `fastmcp` cases); `uv run venvaxi inspect fastmcp::settings` gives
  `kind: attribute`, exit 0
- [x] The symbol-mode miss message shall name no command and no tool.
  — `tests/test_introspect.py::test_get_symbol_module_miss_names_no_command_or_tool`
- [x] The symbol-mode miss message shall name the miss by the caller's `<module>::<name>` as given.
  — `tests/test_introspect.py::test_get_symbol_module_miss_names_no_command_or_tool`, which
  asserts the caller's spelling as the message's prefix on all seven shapes
- [x] If the root of `<module>::<name>` is a distribution name whose import name differs, then a
  message reporting a module - the module that answers, or a binding's target, not the package a
  foreign-case message names - shall name it in its import spelling. —
  `tests/test_introspect.py::test_get_symbol_module_miss_names_a_distribution_root_by_import_name`;
  `uv run venvaxi inspect python-dotenv::main` names `dotenv.main`, exit 1
- [x] If the root of `<module>::<name>` is a distribution name whose import name differs, then a
  footer naming a module shall name it in its import spelling.
  — `tests/test_cli.py::test_error_hint_is_declared_only_for_a_carried_module[carried-module]`;
  `uv run venvaxi inspect python-dotenv::main` gives footer
  ``Run `venvaxi inspect dotenv.main` for its symbols``
- [x] When `getSymbolTool` is called with a name whose `inspect` miss names
  `venvaxi inspect <module>` in its footer, it shall return the TOON error block with the same
  message and a `help[]` hint naming `showModuleTool` with `name=` that module.
  — `tests/test_mcp.py::test_get_symbol_tool_module_miss_hint_names_show_module_tool`;
  `tests/test_mcp.py::test_get_symbol_tool_below_depth_miss_is_unchanged_by_a_deeper_query`
- [x] When `getSymbolTool` is called with a name whose `inspect` miss carries the generic footer,
  it shall return the TOON error block with no `help[]` footer.
  — `tests/test_mcp.py::test_get_symbol_tool_module_miss_without_a_module_omits_footer`
- [x] If a CLI error's failure mode declares no error-specific footer hint, then the error block
  shall be followed by the generic footer.
  — `tests/test_cli.py::test_main_maps_error_to_toon_and_exit_1`;
  `tests/test_cli.py::test_error_hint_is_declared_only_for_a_carried_module` (`no-module`,
  `plain-miss` and `module-mode-binding` cases)
- [x] The packaged skill's qualified-name gotcha shall state that a module name takes no `::`.
  — `tests/test_skill_parity.py::test_qualified_name_gotcha_states_the_converse`;
  `tests/test_skill_parity.py::test_installed_skill_matches_packaged`
- [x] When `venvaxi inspect venvaxi::exceptions` runs against this repository's venv, it shall
  fail with a message stating that `venvaxi.exceptions` is a module.
  — `uv run venvaxi inspect venvaxi::exceptions` gives
  ``Symbol `venvaxi::exceptions` not found - `venvaxi.exceptions` is a module``, exit 1
- [x] When `venvaxi inspect venvaxi::exceptions` runs against this repository's venv, its footer
  shall name `venvaxi inspect venvaxi.exceptions`.
  — `uv run venvaxi inspect venvaxi::exceptions` gives footer
  ``Run `venvaxi inspect venvaxi.exceptions` for its symbols``, exit 1
- [x] When `venvaxi inspect numpy::emath` runs against this repository's venv, it shall fail with a
  message naming `numpy.lib.scimath`.
  — `uv run venvaxi inspect numpy::emath` gives
  ``Symbol `numpy::emath` is bound to module `numpy.lib.scimath` ``, exit 1
- [x] When `venvaxi inspect python-dotenv::main` runs against this repository's venv, it shall fail
  with a message stating that `dotenv.main` is a module.
  — `uv run venvaxi inspect python-dotenv::main` gives
  ``Symbol `python-dotenv::main` not found - `dotenv.main` is a module``, exit 1

## Risks / unknowns

- **A symbol typo now imports the parent on a warm cache.** `torch::Tensr` imports `torch` before
  it says "not found", where it used to read only the store. Module-binding-hints took the same
  trade for module misses, but symbol typos are commoner. The cost is on the miss path only, the
  walk has already run that package's import-time code once, and an MCP server process pays it
  once.
- **"Is a module" claims less than the binding cases.** A node or a discovered name proves the
  module exists; a parent attribute the walk dropped can shadow a submodule of the same name. The
  binding cases may say "bound to", because they read the live attribute.
- **Discovery is not import.** Below the lookup's depth, a discovered submodule that fails to
  import gets a footer whose `inspect` misses in turn, and that dotted miss's reading statement
  points back at the `::` spelling - a two-step loop. It is the same property #142's public-alias
  `tree` hint has. Observed at stage 03: about 37 `numpy.f2py.tests` modules are discoverable but
  fail to import, all of them test modules, e.g. `numpy.f2py.tests::test_callback`. Discovery is
  still the right evidence: it is what the walk itself uses on reaching that depth, and unlike the
  parent's attribute no unrelated import rebinds it.
- **The binding cases still read the live attribute.** The rule fixes only *which evidence decides
  whether a module answers*, and keeps the attribute out of it. Where none answers, the binding
  read is #142's, and module mode shares it: within one process, importing a submodule that
  rewrites a parent attribute under another name changes the binding answer, so a long-lived MCP
  process can say "bound to" where a fresh CLI says `not found`. Stage 03 needed purpose-built
  fixtures to show it. Making the binding read history-independent would change #142's design for
  both spellings, which this plan does not take on.
- **The evidence is no steadier than the imports and `__path__` it rests on.** No rule can make an
  import's success, or the `__path__` it leaves, independent of the process's history, and both
  kinds of evidence rest on one.
  - Below the lookup's depth, discovery imports `<module>`. A `<module>` that imports only after
    another module has (a circular import that works in one order), or fails only on its first
    import, is discoverable in one process and not in another. Stage 03's `vxcirc.a.b::x` answers
    "is a module" from a cold CLI, whose own walk ran the enabling import, and `not found` from a
    warm one; in one MCP process it flips after an unrelated deeper query.
  - Below the lookup's depth, discovery also lists `<module>`'s `__path__` as it stands when the
    miss reads it, and package code can extend that `__path__` after the import has succeeded, as
    plugin-directory schemes do. Stage 03's `vxpath.a.b::late` gives `not found`, then "is a
    module" in the same MCP process after an unrelated deeper query imports the module that
    extends the parent's `__path__`. A fresh CLI on that deeper cache gives `not found` again,
    though the cache's own walk listed `late` and recorded its node.
  - Within the lookup's depth, the node is whatever the cache's walk recorded. A deeper build can
    import, and record, a within-depth module the lookup-depth walk failed to import: `vxcirc::z`
    misses on a depth-2 cache and answers "is a module" on a depth-3 one. Module mode has had the
    same property since the lazy-depth model, which takes a deeper graph as a superset of a
    shallower one; re-walking at the lookup's depth on every miss would remove it, at a cost out
    of proportion.

  Each needs a package whose imports depend on order, or that extends a `__path__` at runtime, and
  stage 03 needed purpose-built packages to show them.
- **The `__name__` guard checks `<module>` alone.** Below the lookup's depth, discovery lists
  nothing where `<module>` imports under another `__name__`, but no ancestor of `<module>` is
  checked. A `sys.modules` alias further up still lets discovery answer for a module the walk
  never reaches. In the auditor's `al4.a.b.d::x`, `al4.a.b` is the alias and `al4.a.b.d` imports
  through it under its own name, so the miss says `al4.a.b.d.x` is a module, and the footer's
  lookup then misses: the two-step loop of "Discovery is not import". Guarding the whole ancestor
  chain would widen the spec past C2, which fixed the parent alias stage 03 found, so it is not
  taken.
- **The error-specific footer is a new extension point.** No CLI or MCP error carried a footer hint
  before; `show`'s dotted-name next step lives in its message, which the rule leaves alone. The
  rule is declared per failure mode so the next diagnosed miss does not grow a footer unplanned.

## Notes

- **Re-entry from stage 03 (2026-10-17).** Two independent passes ran at stage 03: the verifier
  (all criteria passing as worded) and an `icm:spec-drift-auditor` audit, which found what the
  criterion-by-criterion pass could not. The user chose discovery for A1 and to fix every finding
  now.
  - **A1 (medium, spec/code).** Below the lookup's depth the same-name case was decided by the
    parent's live attribute, so one MCP process answered `not found`, then "bound to" after an
    unrelated deeper query, while a fresh CLI kept `not found`. Now decided by discovery, which
    also absorbed the Out of scope entry for a deep submodule its parent does not bind.
  - **A2 (medium, spec).** "The depth the lookup builds" was never defined; now defined once in
    inspect.md Data requirements, as the lookup's depth.
  - **A3 (medium, spec).** The new Error shape rule literally caught `show`'s in-message
    dotted-name next step; now scoped to a declared footer hint.
  - **A4 (low, spec).** "The cases apply as written" pulled in "only its wording changes"; the
    symbol spelling now states its own outcome class and footer.
  - **A5 (low, spec).** The public-target footer reason overclaimed a node always answering; now
    worded as tree.md's public-alias hint is.
  - **A6 (low, spec).** A distribution-name root answers in its import spelling; now stated.
  - **P1 (medium, plan).** Binding criteria lacked "no module answers", and the same-name criteria
    lacked "the walk's discovery lists it" - `package.subpkg::dyn` met a criterion as written and
    rightly failed it. Reworded.
  - **P2 (low, plan and tests).** The facade criterion could not fail; replaced by "a real symbol
    keeps its answer", which had no test.
  - **P3 (low, plan).** Criteria added for the depth being the lookup's own and for the message
    naming no command or tool.

  Delta: stage 01 amended inspect.md, symbol-graph.md, output-contract.md and tools.md, reworded
  this plan and updated the techspec; stage 02 changes the code and tests; stage 03 re-verifies
  the delta only. Found while tracing A3, pre-existing and out of scope: `showPackageTool` returns
  `show`'s dotted-name message in its CLI spelling (`show <package> --api`), against
  `specs/mcp/tools.md` Error message wording - a follow-up issue candidate at closeout.
- **Second re-entry from stage 03 (2026-10-17).** The two passes ran again on the delta: the
  verifier (25 pass, 2 fail as worded) and the auditor. Both found no spec/code divergence on either
  surface, module mode behaviourally identical to `HEAD`, and A1-A6, P2 and P3 resolved. What
  remained was criterion wording, plus one test. The user approved fixing it all.
  - **B1 (medium, plan).** Criteria still missed conditions the spec carries. The binding
    criteria lacked the symbol-mode opening conditions (`package::_impl` met the private one as
    written). The public-target footer criterion was not limited to symbol mode (`inspect
    numpy.emath` met it). The import-time criterion lacked the binding (an unbound `sys.modules`
    module keeps `not found`). The within-depth fallback lacked "binds `<name>` to no other module"
    (the optional-dependency fallback pattern gets a binding message). Reworded.
  - **B2 (low, plan and Risks).** The two determinism criteria promised the same message, but the
    spec promises only that whether a module answers is history-independent; the binding read
    still reads the live attribute. Narrowed, and the residual recorded in Risks.
  - **B3 (low, plan).** Criteria added for the "neither applies" miss (a typo, a non-module
    binding), the caller's `::` spelling, the footer's import spelling, and the message making no
    binding claim.
  - **B4 (low, spec).** symbol-graph.md now carries the non-private condition and names the
    discovery read as an import boundary; inspect.md's footers say "in its import spelling".
  - **B5 (low, plan).** A stale Approach sentence from the first design.
  - **B6 (low, tests).** A mutant trusting the cache's recorded depth passed every test; stage 02
    adds a below-depth submodule that fails to import, with a deeper-cache case.

  Delta: stage 01 wording only; stage 02 the B6 test; stage 03 a delta on the reworded criteria.
  A second closeout follow-up candidate, factory configuration and pre-existing:
  `plans/README.md` says Notes stay empty until closeout, while `ICM/process-plan/CONTEXT.md` says
  to record a re-entry in the plan's Notes, as this entry does.
- **Third re-entry from stage 03 (2026-10-17).** The two passes ran on the second delta: the
  verifier (28 pass, 3 fail as worded) and the auditor (no medium or high). B1-B6 held. Every
  finding is low, and the user approved the route below.
  - **C1 (spec/code).** A raising discovery read fell through to the binding read, so a second,
    succeeding import gave a binding message (`vxflaky.a.b::j`). The spec now says the raise ends
    the check; the criterion is split in two.
  - **C2 (spec/code).** Discovery listed the `__path__` of whatever importing `<module>` returned,
    so a `sys.modules` alias answered for a module the walk never reaches. The spec now reads
    discovery under the imported module's own `__name__`, as the walk does; one criterion added.
  - **C3 (spec).** "Never by which modules the process has already imported" over-promised:
    discovery imports `<module>`, and that import can depend on history (`vxcirc.a.b::x`).
    Narrowed to the evidence, criterion 13 narrowed, residual in Risks.
  - **C4 (spec).** "Never by the depth the cache happens to hold" over-promised within depth: a
    deeper build can record a within-depth module (`vxcirc::z`), as module mode already could.
    Narrowed to what decides between node and discovery, criterion 14 narrowed, residual in Risks.
  - **C5 (spec and plan).** "The module is named in its import spelling" and its criterion now
    cover only a message that names a module, and "a single identifier - no `.` -" now reads "a
    single Python identifier".
  - **C6 (ripple).** Frozen `plans/mcp-error-surface.md:68-70` states the generic footer follows
    every CLI `Error`; the amended Error shape supersedes it. Frozen plans are not edited, so stage
    04 records the supersession here at closeout.

  Delta: stage 01 wording (symbol-graph.md, inspect.md, this plan, the techspec); stage 02 C1 and
  C2 in code, with tests; stage 03 a delta on the changed criteria - 13, 14, 16-18 and 24, and,
  through the Validation notation's new terms, 2, 5, 7-9, 11 and 12.
- **Fourth re-entry from stage 03 (2026-10-18).** The two passes ran on the third delta: the
  verifier (30 pass, 3 fail as worded) and the auditor (0 violations, 4 low). C1 and C2 held, each
  pinned by a test its mutant fails, and no code breaks an explicit spec statement. Every finding
  is wording, and the user approved the route below.
  - **D1 (spec and plan).** The `__name__` rule read as covering the binding cases' same-name
    check too (`vxal.a.b::x`, criterion 9). Now scoped to the read that decides whether a module
    answers; the same-name check stays #142's in both spellings, with its own Notation term.
  - **D2 (plan).** Criterion 14 lacked "`<name>` is a single identifier" (`hy.a.b::c-d`). Added.
  - **D3 (plan, Risks and a code comment).** An unrelated import extending the parent's `__path__`
    flips criterion 13 (`vxpath.a.b::late`). Criterion 13 narrowed to an unchanged `__path__`; the
    Risks entry and symbol-graph.md name `__path__`; the `_discoverable_submodules` NOTE is
    reworded.
  - **D4 (Risks).** The `__name__` guard checks `<module>` alone (`al4.a.b.d::x`). Recorded, not
    fixed.
  - **D5 (spec and plan).** The foreign case names the package as the caller spelled its root
    (`python-dotenv.main::os`). inspect.md states it; criterion 24 now covers the module a message
    reports.

  Delta: stage 01 wording (symbol-graph.md, inspect.md, this plan, the techspec); stage 02 one
  code comment; stage 03, by the user's choice, a narrow evaluator check of criteria 9, 11, 13,
  14 and 24 plus the suite. A third closeout follow-up candidate: import-spell the package the
  foreign case names, in both spellings (D5).
- **Validation evidence.** All 33 boxes are ticked. Each citation is the stage 03 third
  verification's (2026-10-17), except criteria 9, 11, 13, 14 and 24, which were reworded after it
  and cite the fourth, narrow check (2026-10-18). The `uv run venvaxi` citations are live runs on
  this repo's venv and the real `~/.venvaxi` cache, where `numpy` was at depth 4. Every pass also
  probed purpose-built scratch packages (`vxcirc`, `vxpath`, `vxal`, `vxga` and others), which
  live only in the run's scratchpad, so no citation names them.
- **Why the diagnosis is a private `SymbolNotFoundError` subclass.** `SymbolModuleMissError`
  carries the module to inspect, if any, out of `get_symbol`. Each surface's single error-render
  site reads it: `__main__.error_report` through `_cli.error_hint` on the CLI, and
  `_mcp._error_hints` in the MCP error wrapper. Nothing else is observable: the error block prints
  only the message, and exit codes map by `isinstance`. The skill drift gate's hand-copied CLI
  error arm calls `error_report` too, so the gate renders footers exactly as `main()` does.
- **Why module mode is untouched.** The walk's discovery is shared through
  `_discoverable_submodules`, but C1's three-valued result and C2's `__name__` guard live only in
  `_discovery_lists`, which the symbol path alone calls. `module_binding`, `_read_module_binding`
  and `_classify_module_binding` keep #142's code, so `inspect numpy.emath` is byte-identical to
  `HEAD`. The first design's classifier change, and the filter that compensated for it, were
  reverted at the first re-entry: together they equalled `HEAD`.
- **No `SCHEMA_VERSION` bump.** The walk and the graph are unchanged.
- **C6: a frozen plan superseded, not edited.** `plans/mcp-error-surface.md:68-70` ticks "the
  entry point shall render the error object followed by the generic `venvaxi --help` footer,
  unchanged". This plan's amendment to `specs/behaviors/output-contract.md` Error shape supersedes
  it: a failure mode may now declare an error-specific footer in place of the generic one, and
  `inspect`'s symbol-mode module miss does. Frozen plans are edited only to correct the record,
  and that one was correct when frozen, so the supersession is recorded here.
- **One path no test asserts.** The amended Error shape says the `Unexpected error:` shape always
  takes its surface's fallback. No criterion covers it and no CLI test asserts its footer, as
  every verification pass noted. The path is unchanged by this plan.
- **Gotchas.**
  - Format through `uv run -m prek run`, never a bare `ruff format`, which uses Ruff's 88-column
    default rather than pkgdx's 79-column config.
  - A test that writes an importable file uses a `src_test` temp directory, not `tmp_path`, or
    `coverage report` fails with "No source for code".
  - Windows CRLF line endings crept into the working tree mid-run. `.gitattributes` normalises
    them on commit, but the tree was restored to LF. Git Bash `sed -i` proved unreliable for
    that; strip the CR bytes with a binary-mode Python rewrite, and count them the same way.

## Follow-ups

- Issue [#150](https://github.com/andyrids/venv-axi/issues/150): a footer on the module-mode
  binding miss. `inspect numpy.emath` names its target in the message but keeps the generic
  footer, while `inspect numpy::emath` names `venvaxi inspect numpy.lib.scimath`. Declared out of
  scope in `specs/commands/inspect.md`.
- Issue [#151](https://github.com/andyrids/venv-axi/issues/151): `showPackageTool` returns
  `show`'s dotted-name message in its CLI spelling (`show <package> --api`), against
  `specs/mcp/tools.md` Error message wording. Found while tracing A3. It predates this plan.
- Issue [#152](https://github.com/andyrids/venv-axi/issues/152): `plans/README.md` says Notes stay
  empty until closeout, while `ICM/process-plan/CONTEXT.md` says to record a re-entry in the
  plan's Notes, as this plan's four re-entry entries do. Both are factory configuration, amended
  deliberately.
- Issue [#153](https://github.com/andyrids/venv-axi/issues/153): the foreign case names the
  package as the caller spelled its root, so `python-dotenv.main::os` says "a module outside
  `python-dotenv`". Import-spelling it in both spellings is D5's follow-up. It predates this plan:
  module mode does the same.

The CLI `Unexpected error:` footer having no test is recorded in Notes and is not filed: its path
is unchanged. `inherits` taking the same reading is not a follow-up: `specs/commands/inspect.md`
Out of scope files it only if the shape turns up in use. No downstream plan absorbs any of these,
so there is no `Deferred to` entry.
