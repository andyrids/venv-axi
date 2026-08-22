---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [command, show]
---

# Command: venvaxi show

## Invocation / inputs

```text
venvaxi show <package> [--fields <csv>] [--api] [--docstring] [--refresh]
```

| Argument      | Default                 | Meaning                                     |
| ------------- | ----------------------- | ------------------------------------------- |
| `package`     | required                | Distribution or module name (see below)     |
| `--fields`    | `name,version,location` | Display fields, metadata mode only          |
| `--api`       | off                     | Show public API symbols instead of metadata |
| `--docstring` | off                     | Complete docstrings (with `--api`)          |
| `--refresh`   | off                     | Rebuild the cached symbol graph first       |

The command dispatches on `--api`: two distinct outputs behind one verb.

The positional argument widens under `--api`. In metadata mode it MUST be a distribution name; in
API mode any importable dotted module path is accepted, because the target is the import system
rather than the metadata database.

## Data requirements

- **Metadata mode**: installed distribution metadata. Not cached.
- **API mode**: public, top-level API symbols from the cached symbol graph, built on demand. See
  [Cache and refresh](../behaviors/cache-refresh.md).

## Outputs

**Metadata mode** - the `show` command shall emit a flat TOON object over the selected fields,
then a footer naming `show <package> --api`.

**API mode** - the `show` command shall emit `count: <n>` and a `symbols` table of `name`,
`kind`, `signature`, `doc`. Docstrings shall be truncated unless `--docstring` is set, and the
footer shall suggest `--docstring` only when it is not already set. A symbol defining no
docstring of its own reports `(no docstring)` - see
[Definitive empty states](../behaviors/output-contract.md#definitive-empty-states).

The `show` command shall report every public top-level **symbol** the package declares - any node
kind in [Symbol graph](../behaviors/symbol-graph.md#node-kinds) except `module` and `package`.

A package's `__all__` is its own declaration of its public API, and this command answers what that
API is. Reporting only `class` and `function` would drop every exported instance, namespace object
and constant - `pytest.skip`, `pytest.mark`, `requests.codes` - and, because a `count` below the
limit is definitive under
[Bounded results](find.md#bounded-results), would state as fact that the dropped names do not
exist. 'Callable' is no better a proxy: it keeps `pytest.fail` and still drops `pytest.mark`.

Submodules are the one exclusion, and it is a depth exclusion rather than a kind one. A package's
children in the graph include its submodules, recorded by the same walk under the same edge kind
as its symbols, so reporting 'every child' would answer a different question: `fastmcp` declares
six names in `__all__` and carries sixteen public submodules, and listing all twenty-two states
that its public API is twenty-two names. Nested module structure is `tree`'s job, per
[Out of scope](#out-of-scope).

Kinds stay honest. A reported symbol carries the kind it actually has - an exported instance
reports `attribute`, never promoted to `function` because it happens to be callable. Callability
decides the *signature*, not the kind; see
[Symbol graph](../behaviors/symbol-graph.md#node-kinds).

When the public API is empty, the `show` command shall emit `count: 0` plus a hint naming
`venvaxi tree <package>`, because an empty public API usually means the symbols are one level
down rather than absent.

## Failure modes

- If a `--fields` entry is unknown, then the `show` command shall raise `InvalidArgumentError`,
  emit the TOON error block and exit `EX_FAILURE`.
- If, in API mode, the `package` argument's spelling is malformed rather than merely absent, then
  the `show` command shall raise `InvalidArgumentError`, emit the TOON error block and exit
  `EX_FAILURE`.
- If the package is not installed in the venv, then the `show` command shall raise
  `PackageNotFoundError`, emit the TOON error block and exit `EX_FAILURE`.
- If the package is installed but cannot be imported for introspection, then the `show` command
  shall raise `PackageImportError`, emit the TOON error block and exit `EX_FAILURE`.

A malformed name and a missing one are different answers. `../etc/passwd` is not a package name
that failed to resolve; it is not a package name at all, and reporting it as 'not installed'
would invite the caller to try installing it. The three classes are defined once in
[Package resolution](../behaviors/package-resolution.md), whose Metadata mode section carves
metadata mode out: its answers are about the metadata database, so a spelling it cannot answer
reports as not installed, with the dotted-name hint where the name looks like a module path.

An empty API result is success - `count: 0` exits `EX_OK`, per the
[exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **Deep API enumeration** - `--api` reports public, top-level symbols only; nested module
  structure is `tree`'s job and per-symbol depth is `inspect`'s.
- **Recommendation** - the API table reports the surface; it does not rank, recommend, or
  explain which symbol to reach for. Never - the
  [Report what a symbol is](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  principle decides this.

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - `--api` reports the public surface. It does not rank, recommend, or explain which symbol to
  reach for.
