---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [behavior, symbol-graph, storage]
---

# Behavior: Symbol graph

## Rule

The symbol graph is a SQLite Node|Edge graph, populated by **live introspection** of imported
objects - never by static AST parsing. This is the decisive difference from the projects it is
adapted from: `venvaxi` only ever describes packages actually installed in the consuming venv, so
it reports what will really be imported at runtime, including C extensions and
dynamically-constructed attributes.

## Applies to

Every command and MCP tool answering from the cached graph - `show --api`, `find`, `tree`,
`inspect`, `inherits` - and any change to the store schema or the introspection walk.

## Details

### Node kinds

`package`, `module`, `class`, `function`, `method`, `attribute`.

A node's kind records what the symbol **is**. Callability decides the *signature*, never the kind:
a module-level instance whose class defines `__call__` classifies as `attribute` and still records
the signature the caller needs. Promoting it to `function` because it can be called would report
the object as something it is not, which
[Report what a symbol is](../principles.md#report-what-a-symbol-is-not-how-to-use-it) rules out.

### Recorded docstrings

The graph shall record a symbol's **own** docstring. A docstring reached only by walking the MRO
belongs to a base class, so an undocumented subclass, or a method overriding a documented one,
shall record `""` rather than inherit text that describes something else.

An instance's `__doc__` **is** its type's, so for a symbol of kind `attribute` the recorded
docstring shall be its own and not its type's - a module-level `dict` or `tuple` constant shall
not be recorded carrying the builtin's docstring as though it described that constant.

Where an `attribute`'s type is defined outside the standard library, that type's docstring
documents the symbol and shall be recorded. A package that ships a class solely to instantiate it
once as a public export - `pytest.fail`, an instance of `_pytest.outcomes._Fail` - documents the
export on that class, and blanking it reports `(no docstring)` for a symbol whose documentation
the graph already holds.

The standard library is the exclusion, not the package. A type from `builtins`, `typing` or
`types` describes a construct rather than the exported value: `version_tuple` is not documented by
*Built-in immutable sequence*, and a `NewType` alias is not documented by `NewType`'s own
docstring. Excluding by *type* rather than by package is what separates these cases - the
defining module of a package's singleton is frequently private and outside the package's own
import root (`_pytest.outcomes` for `pytest`), so a rule keyed to the package root would blank
exactly the docstrings worth keeping.

### Edge kinds

Five are declared; only two are read:

| Kind           | Written                                            | Read by            |
| -------------- | -------------------------------------------------- | ------------------ |
| `CONTAINS`     | Module or class -> each symbol it holds             | `inspect`, `tree`  |
| `INHERITS`     | Subclass -> base class                              | `inherits`, both ways |
| `EXPORTS`      | Module -> a symbol whose home module differs        | nothing            |
| `IMPORTS_FROM` | Module -> the home module it re-exports from        | nothing            |
| `DEPENDS_ON`   | never                                               | nothing            |

`INHERITS` is the one edge read in both directions. `inherits` follows it to the subclasses of a
class, and `inherits --bases` follows it back to that class's own bases - one stored edge, two
questions. The two directions do not have equal reach, because an edge is written by the walk of
the *subclass's* package; [`inherits`](../commands/inherits.md) declares what that means for each.

`EXPORTS` and `IMPORTS_FROM` are the **re-export record**: when a walked symbol's home module
differs from the module recording it, the walk shall write both edges together, capturing the
facade-to-home relationship as graph edges rather than only as a node field. No query consumes
them today - they exist so a future feature (re-export provenance, 'where does this really come
from') can be built without a cache rebuild, since the edges are already being accumulated.

`DEPENDS_ON` is declared but never written or read. It is dead, and should either gain a purpose
or be removed under YAGNI.

### Keying

Keying differs between `CONTAINS` and `INHERITS` - see
[Qualified name semantics](qualified-name-semantics.md).

### Re-exported symbols

A re-export is a name bound in one module whose object is defined in another. Whether the walk
records it turns on two things: whether the recording module declares `__all__`, and whether it
is the package's own root module.

Where a module declares `__all__`, every name it lists shall be recorded at that module, whatever
module defines the object, at any depth. `__all__` is the module's own statement of what it
exports, and a stated intent is not second-guessed.

Where a module declares no `__all__` and is not the package's own root module, a class or
function whose defining module differs from the recording module shall not be recorded there.
With no `__all__` to read there is no declaration, only the module's public attributes, and those
cannot tell a deliberate re-export from an incidental import - a module that imports a helper in
order to call it looks exactly like one re-exporting it. The symbol is already recorded at its
own defining module, so recording it again at every module that imported it would inflate the
graph with names the package never exported and report them as public surface.

Where a module declares no `__all__` and **is** the package's own root module, its re-exports
shall be recorded. Every walk begins at the installed top-level package, not at whatever dotted
module a query names, so this applies to the root module alone and to no submodule, however the
query spelled its target. At the root a re-export is the answer rather than a duplicate, because
the root is the spelling an agent imports from - see
[The agent's spelling wins](../principles.md#the-agents-spelling-wins-over-the-internally-correct-one).
It is also what lets [`show --api`](../commands/show.md#outputs) report a surface at all for a
facade package: one whose root defines nothing of its own and declares no `__all__`, but
re-exports its whole API from submodules.

The filter tests classes and functions, and no other kind. A module-level constant is therefore
recorded at the module that binds it, whatever module defines its type. An instance has no
defining module of its own - it reports its type's - so testing it the same way would attribute a
package's own constants to whatever library built them, and a compiled regular expression bound
at module level would read as belonging to `re` rather than to the module that defines it.

- If a class or function is re-exported into an `__all__`-less module below the root from
  outside the walked package root, then it shall not be recorded there. A package that imports a
  name from a dependency has not made that name part of its own API, and the graph shall not
  report that it has.
- If a class or function is re-exported into an `__all__`-less module below the root from a
  private submodule of the same package root, then it shall still be recorded at the re-exporting
  module. This is the single carve-out from the rule above, because the facade is that symbol's
  only public surface - declared at [Private submodules](#private-submodules).

### Private submodules

The walk shall not descend into a submodule whose own final name segment starts with `_`. The
skip is unconditional - independent of cache state, build depth and `--refresh`. This is a rule
about the segment discovered during recursion, not a filter on the query root: the top-level
package name is walked directly rather than discovered as one of its own submodules, so a package
whose own name starts with `_` is walked in full when named as the query root, and only its own
underscore-prefixed children are skipped, by the identical rule, once the walk recurses into
them. `_pytest` demonstrates both halves at once: named as the query root it resolves, imports
and populates the graph like any other package, while its own underscore-prefixed submodules
(`_pytest._code` among them) do not appear, skipped by the same segment rule that skips
`pkg._impl` inside any package.

A package's private implementation modules are not its API surface, so no **module** node is
recorded for one. Nodes homed there are a separate question, answered case by case below.

- If a caller names a private submodule as the target of `inspect`, `tree`, or an MCP module
  lookup, then no module node is recorded for it, identically to a module that does not exist.
  The graph fact is the same in both cases; what the caller is told is not - each surface states
  plainly that the name is private and never indexed, rather than leaving the two causes
  indistinguishable. See [`tree`](../commands/tree.md#outputs),
  [`inspect`](../commands/inspect.md#failure-modes) and
  [MCP tools](../mcp/tools.md#hint-wording) for the surface-specific wording.
- If a caller asks for a private submodule's own public API, then the answer shall be `count: 0`
  at `EX_OK`, not the failure a submodule that does not exist raises. The module imports, so it
  resolves; only its absence from the graph empties the API. This is the one surface where the
  node-level equivalence above never held observably - a raise and a `count: 0` were never
  confusable - and its hint carries the same private-and-never-indexed fact as the other
  surfaces, naming the root package's own public API rather than a tree walk of the identical,
  equally-empty name. See [`show --api`](../commands/show.md#outputs).
- If a module the walk visits re-exports a class or function whose home is a private submodule,
  then the graph shall still record it, keyed at the re-exporting facade, with its
  `home_qualified_name` pointing into the unwalked private module and its member rows (for a
  class) keyed at that home - see [Qualified name semantics](qualified-name-semantics.md).
- If a symbol is homed in a private submodule and re-exported nowhere, then it shall be absent
  from the graph entirely, and a command's `count: 0` or `SymbolNotFoundError` for it is a
  definitive negative about the graph, not about the installed package, per
  [Definitive empty states](output-contract.md#definitive-empty-states).

An underscore submodule's absence is not a cache-staleness signal: `--refresh` and a
schema-version bump both reproduce it identically, because the skip is applied on every walk
regardless of when or why it ran.

### FTS5 constraint

The `nodes` table backs an external-content FTS5 index, which constrains how it may be rewritten:
the rowid mapping must stay stable, per
[Qualified name semantics](qualified-name-semantics.md).

## Out of scope

- **Static analysis fallback** - a package that cannot be imported is reported as broken, never
  approximated by parsing its source. Never - reporting what would 'probably' import reintroduces
  exactly the drift live introspection exists to eliminate.
- **Re-export provenance queries** - the `EXPORTS`/`IMPORTS_FROM` edges are written but unread.
  Deferred to a future feature; no spec exists for it yet.
- **Opting private submodules into the walk** - no flag exposes them, and none is planned here.
  [#87](https://github.com/andyrids/venv-axi/issues/87) asks that the skip be declared, not
  reconsidered; exposing it would be its own unit, and would have to answer what a private
  module's presence means for `show --api`'s public-surface claim.
- **Opting an `__all__`-less re-export into the graph below the root** - no flag records one, and
  none is planned here. [#106](https://github.com/andyrids/venv-axi/issues/106) asks that the
  filter be declared, not changed; widening it would have to answer what the same symbol recorded
  at two modules means for `show --api`'s public-surface claim and for `find`'s preference for
  short facade paths.

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - live introspection of the installed venv is what makes the report un-driftable; the graph
  records what is, never what documentation says.
