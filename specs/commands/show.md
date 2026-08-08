---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi show

## Invocation

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

## Output rules

**Metadata mode** - a flat TOON object over the selected fields, then a footer naming
`show <package> --api`.

**API mode** - `count: <n>` and a `symbols` table of `name`, `kind`, `signature`, `doc`.
Docstrings are truncated unless `--docstring` is set; the footer suggests `--docstring` only when
it is not already set. A symbol defining no docstring of its own reports `(no docstring)` - see
[Definitive empty states](../behaviors/output-contract.md#definitive-empty-states).

Empty API result: `count: 0` plus a hint naming `venvaxi tree <package>`, because an empty public
API usually means the symbols are one level down rather than absent.

## Exit codes

`EX_OK`, including empty results. `EX_FAILURE` on any raised `Error`.

## Errors

- `InvalidArgumentError` - an unknown `--fields` entry.
- `PackageNotFoundError` - the package is not installed in the venv.
- `PackageImportError` - the package is installed but cannot be imported for introspection.

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - `--api` reports the public surface. It does not rank, recommend, or explain which symbol to
  reach for.
