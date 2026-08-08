---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi inspect

## Invocation

```text
venvaxi inspect <qualified_name> [--docstring] [--refresh]
```

| Argument         | Default  | Meaning                                       |
| ---------------- | -------- | --------------------------------------------- |
| `qualified_name` | required | A symbol or module name (see below)           |
| `--docstring`    | off      | Complete docstrings, not truncated first lines |
| `--refresh`      | off      | Rebuild the cached graph first                |

`qualified_name` accepts `module::Symbol`, `module::Class.method`, or a bare/dotted module name.

## Data requirements

The cached symbol graph. Dispatch is on the **argument shape**, not on a flag: a qualified symbol
name always contains `::`, and a bare or dotted module name never does.

Both modes answer with **facade-keyed** data - the module the symbol was recorded under, which is
the spelling the caller will import. See
[Qualified name semantics](../behaviors/qualified-name-semantics.md).

## Output rules

**Symbol mode** (`::` present) - a flat TOON object of `qualified_name`, `kind`, `signature`,
`doc`.

**Module mode** (no `::`) - a header object of `qualified_name`, `kind`, `doc`, then
`children count: <n>` and a `children` table of `name`, `kind`, `signature`, `doc`.

Rules binding both modes:

- **`doc` MUST be the target's own docstring.** It MUST NOT inherit its base class's, its
  metaclass's, or its type's docstring. Reporting an inherited docstring as the symbol's own
  records a false fact about the installed package, which is precisely the drift this tool exists
  to eliminate.
- A symbol that defines no docstring of its own reports the marker `(no docstring)`, not an empty
  string, in both truncated and `--docstring` modes. See
  [Definitive empty states](../behaviors/output-contract.md#definitive-empty-states) for why a
  bare `""` is insufficient.
- `signature` is the real signature from live introspection. Where `inspect.signature` fails on a
  callable, the marker `(signature unavailable)` is recorded - distinct from every real
  signature, so 'introspection failed' is never confused with 'takes no arguments'.
- Docstrings truncate at 200 characters unless `--docstring` is set; the footer suggests
  `--docstring` only when it is not already set.
- Empty module: header object then `children count: 0`, with a hint naming `venvaxi tree`.

## Exit codes

`EX_OK`, including a module with no children. `EX_FAILURE` on any raised `Error`.

## Errors

- `SymbolNotFoundError` - the qualified name does not resolve in the store. This is distinct from
  a zero-children answer, which is a definitive success.
- `PackageImportError` - the owning package cannot be imported to build the graph.

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - the own-docstring rule is this principle at its sharpest. An inherited docstring describes a
  different symbol, so surfacing it is a usage narrative rather than a report.
- [Measured token efficiency beats the headline claim](../principles.md#measured-token-efficiency-beats-the-headline-claim)
  - symbol mode is a flat single object, where TOON saves only ~6%. Efficiency here comes from
  truncation, so the 200-character default MUST NOT be relaxed to compensate for the encoding.
