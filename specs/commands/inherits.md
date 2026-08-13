---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state
immutable: false
tags: [command, inherits]
---

# Command: venvaxi inherits

## Invocation / inputs

```text
venvaxi inherits <qualified_name> [--refresh]
```

| Argument         | Default  | Meaning                                  |
| ---------------- | -------- | ---------------------------------------- |
| `qualified_name` | required | Qualified base class name (`module::Class`) |
| `--refresh`      | off      | Rebuild the cached graph first           |

## Data requirements

`INHERITS` edges from the cached graph. **Direct** subclasses only - not the transitive closure.

This command resolves through `SymbolStore.canonical_name` to the class's *home* module for
**every** input, because `INHERITS` edges are always keyed at the home frame. `inspect` shares
that resolution, but only through its class-member carve-out - a facade-spelled member with no
row of its own; `find` never resolves. See
[Qualified name semantics](../behaviors/qualified-name-semantics.md).

Build depth is derived from the canonical name, so facade and home spellings agree on a fresh
cache.

## Outputs

The `inherits` command shall emit `count: <n>` and an `inheritors` table of `name`, `kind`,
`qualified_name`.

The `inherits` command shall end output with a footer naming
`venvaxi inspect <qualified_name>`.

When the base class resolves with zero indexed subclasses, the `inherits` command shall emit
`count: 0` plus a hint naming `venvaxi find <name> --package <package>`. The hint shall name
**both** causes - subclasses in an unindexed package, and subclasses below the built depth -
because the caller cannot distinguish them from the output.

`count: 0` here means the base class resolved and has zero *indexed* subclasses. It is a
definitive empty state, not a lookup failure: an unresolvable name raises `SymbolNotFoundError`
upstream instead.

Answers may legitimately **grow** as build depth grows. A subclass homed deeper than the current
build stays undiscovered until some query builds that deep - the lazy-depth model in
[Cache and refresh](../behaviors/cache-refresh.md).

## Failure modes

- If the base class name does not resolve, then the `inherits` command shall raise
  `SymbolNotFoundError`, emit the TOON error block and exit `EX_FAILURE`.
- If the name's top-level component is not a possible package name, then the `inherits` command
  shall raise `InvalidArgumentError`, emit the TOON error block and exit `EX_FAILURE`.
- If the owning package is not installed in the venv, then the `inherits` command shall raise
  `PackageNotFoundError`, emit the TOON error block and exit `EX_FAILURE`.
- If the owning package is installed but cannot be imported to build the graph, then the
  `inherits` command shall raise `PackageImportError`, emit the TOON error block and exit
  `EX_FAILURE`.

The three package classes are defined once in
[Package resolution](../behaviors/package-resolution.md). An empty result is success - `count: 0`
exits `EX_OK`, per the [exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **The transitive closure** - direct subclasses only; a full descendant tree is composed by the
  caller from repeated calls. No future spec is planned.
- **Docstring reporting** - there is no `--docstring` flag and the table carries no `doc` column;
  per-symbol detail belongs to `inspect`.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 5, definitive empty states](../principles.md#principle-5-definitive-empty-states)
  - the separation between
  `count: 0` and `SymbolNotFoundError` is what makes a zero answer trustworthy. Collapsing them
  would make every empty result ambiguous.
- [The agent's spelling wins over the internally correct one](../principles.md#the-agents-spelling-wins-over-the-internally-correct-one)
  - the caller passes whichever spelling they have; resolution absorbs the facade/home
  difference rather than demanding the home path.
