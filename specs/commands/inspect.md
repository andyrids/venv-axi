---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [command, inspect]
---

# Command: venvaxi inspect

## Invocation / inputs

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
the spelling the caller will import. Class members are the carve-out: member rows are keyed at
the owning class's *home* module only, so a member spelled through a facade
(`fastmcp::Client.call_tool`) shall resolve to its home-keyed row and answer with the home
spelling (`fastmcp.client.client::Client.call_tool`) - the only row that exists, and the same
name `find` returns for the symbol. Echoing the caller's facade spelling back would report a
qualified name no other command can resolve. A member spelling that still misses after
resolution raises `SymbolNotFoundError`. See
[Qualified name semantics](../behaviors/qualified-name-semantics.md).

## Outputs

**Symbol mode** (`::` present) - the `inspect` command shall emit a flat TOON object of
`qualified_name`, `kind`, `signature`, `doc`.

**Module mode** (no `::`) - the `inspect` command shall emit a header object of
`qualified_name`, `kind`, `doc`, then `children count: <n>` and a `children` table of `name`,
`kind`, `signature`, `doc`.

Rules binding both modes:

- The `inspect` command shall report the target's **own** docstring in `doc`; it shall not
  substitute the base class's, the metaclass's, or the type's docstring. Reporting an inherited
  docstring as the symbol's own records a false fact about the installed package, which is
  precisely the drift this tool exists to eliminate.
- If a symbol defines no docstring of its own, then the `inspect` command shall report the marker
  `(no docstring)`, not an empty string, in both truncated and `--docstring` modes. See
  [Definitive empty states](../behaviors/output-contract.md#definitive-empty-states) for why a
  bare `""` is insufficient.
- The `inspect` command shall report the real signature from live introspection for every
  callable symbol, whatever its `kind`. A module-level instance whose class defines `__call__`
  is as callable as a function - `polars::col` is exactly such an instance - and narrowing the
  rule to class and function kinds withholds an answer the walk had in hand.
- If `inspect.signature` fails on a callable, then the marker `(signature unavailable)` shall
  be recorded - distinct from every real signature, so 'introspection failed' is never
  confused with 'takes no arguments'. Recording it is a deliberate exception to the
  applied-at-emission rule in
  [Definitive empty states](../behaviors/output-contract.md#definitive-empty-states): the
  marker is a fact about introspection, discoverable only at build time while the live object
  is in hand.
- A non-callable symbol's `signature` shall be `""`. The empty signature states 'this symbol
  is not callable' - a definitive answer, distinct from the marker above, not a silent blank.
  No third marker: it would change every attribute row in every module listing for no gain,
  and callability already tells the two apart.
- The `inspect` command shall truncate docstrings at 200 characters unless `--docstring` is set,
  and the footer shall suggest `--docstring` only when it is not already set.
- When a module has no children, the `inspect` command shall emit the header object then
  `children count: 0`, with a hint naming `venvaxi tree`.

## Failure modes

- If the qualified name does not resolve in the store, then the `inspect` command shall raise
  `SymbolNotFoundError`, emit the TOON error block and exit `EX_FAILURE`. This is distinct from
  a zero-children answer, which is a definitive success.
- If the qualified name is a **module** name (no `::`) naming a
  [private submodule](../behaviors/symbol-graph.md#private-submodules) - any non-root segment of
  its dotted name starts with `_` - then the `inspect` command shall still raise
  `SymbolNotFoundError` and exit `EX_FAILURE`, but the message shall state that the module is
  private and never indexed, rather than merely not found, distinguishing this definitive
  "private, not absent" answer from a name that is mistyped or genuinely does not exist. A
  **symbol**-mode miss (`::` present) for a symbol homed in a private submodule and re-exported
  nowhere is unaffected by this bullet; it is governed by
  [Private submodules](../behaviors/symbol-graph.md#private-submodules) already.
- If the name's top-level component is not a possible package name, then the `inspect` command
  shall raise `InvalidArgumentError`, emit the TOON error block and exit `EX_FAILURE`.
- If the owning package is not installed in the venv, then the `inspect` command shall raise
  `PackageNotFoundError`, emit the TOON error block and exit `EX_FAILURE`.
- If the owning package is installed but cannot be imported to build the graph, then the
  `inspect` command shall raise `PackageImportError`, emit the TOON error block and exit
  `EX_FAILURE`.

The three package classes are defined once in
[Package resolution](../behaviors/package-resolution.md). Only the top-level component is
validated; a malformed tail resolves to `SymbolNotFoundError` above. A module with no children is
success and exits `EX_OK`, per the [exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **Usage guidance** - `inspect` reports what a symbol is (kind, signature, docstring), never how
  to use it; tutorials, recipes and migration notes are documentation's job. Never - the
  [Report what a symbol is](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  principle already decides this.
- **Recursive listing** - module mode lists direct children only; the nested view is `tree`'s
  job.

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - the own-docstring rule is this principle at its sharpest. An inherited docstring describes a
  different symbol, so surfacing it is a usage narrative rather than a report.
- [Measured token efficiency beats the headline claim](../principles.md#measured-token-efficiency-beats-the-headline-claim)
  - symbol mode is a flat single object, where TOON saves only ~6%. Efficiency here comes from
  truncation, so the 200-character default MUST NOT be relaxed to compensate for the encoding.
