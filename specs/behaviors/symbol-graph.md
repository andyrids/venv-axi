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
| `INHERITS`     | Subclass -> base class                              | `inherits`         |
| `EXPORTS`      | Module -> a symbol whose home module differs        | nothing            |
| `IMPORTS_FROM` | Module -> the home module it re-exports from        | nothing            |
| `DEPENDS_ON`   | never                                               | nothing            |

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

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - live introspection of the installed venv is what makes the report un-driftable; the graph
  records what is, never what documentation says.
