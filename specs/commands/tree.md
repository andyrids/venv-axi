---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [command, tree]
---

# Command: venvaxi tree

## Invocation / inputs

```text
venvaxi tree <package> [--max-depth N] [--refresh]
```

| Argument      | Default  | Meaning                             |
| ------------- | -------- | ----------------------------------- |
| `package`     | required | Package or dotted module name       |
| `--max-depth` | `2`      | Maximum submodule recursion depth   |
| `--refresh`   | off      | Rebuild the cached graph first      |

## Data requirements

The cached module graph for the package, built to at least `--max-depth`. If a graph is cached at
a shallower depth, then it shall be rebuilt rather than answered from - see
[Cache and refresh](../behaviors/cache-refresh.md).

## Outputs

The `tree` command shall emit `count: <n>` and a `tree` table of `depth`, `qualified_name`,
`kind`.

The `tree` command shall emit depth as a column rather than as indentation, so the payload stays
a uniform TOON table. Rendering a visual tree is the caller's business.

The `tree` command shall end output with a footer naming `venvaxi inspect <module>`.

When the named submodule has no node in the graph, the `tree` command shall emit `count: 0` plus
a hint naming the root package's own tree (`venvaxi tree <root>`), which shows the submodules
that do exist. Only a dotted module name reaches this state - the root package resolved and
imported, but the named submodule has no node in the graph: it does not exist, is
[private](../behaviors/symbol-graph.md#private-submodules), or failed to import during the walk.
A mistyped or uninstalled package never reaches it; that raises and exits `EX_FAILURE`.

## Failure modes

- If `package` is not a possible package name, then the `tree` command shall raise
  `InvalidArgumentError`, emit the TOON error block and exit `EX_FAILURE`.
- If the package is not installed in the venv, then the `tree` command shall raise
  `PackageNotFoundError`, emit the TOON error block and exit `EX_FAILURE`.
- If the package is installed but not importable, then the `tree` command shall raise
  `PackageImportError`, emit the TOON error block and exit `EX_FAILURE`.

The three classes are defined once in [Package resolution](../behaviors/package-resolution.md).
An empty result is success - `count: 0` exits `EX_OK`, per the
[exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **Symbol-level contents** - the tree lists modules; the symbols inside a module are
  `inspect`'s job, and a package's public surface is `show --api`'s.
- **Visual rendering** - depth is data, not indentation; drawing an ASCII tree is the caller's
  business. Never - a drawn tree would break the uniform-table encoding the payload depends on.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 1, token-efficient output](../principles.md#principle-1-token-efficient-output)
  - the flat depth column is
  what keeps this a table. Nesting would force per-row keys and lose the header amortization the
  encoding depends on.
