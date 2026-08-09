---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi tree

## Invocation

```text
venvaxi tree <package> [--max-depth N] [--refresh]
```

| Argument      | Default  | Meaning                             |
| ------------- | -------- | ----------------------------------- |
| `package`     | required | Package or dotted module name       |
| `--max-depth` | `2`      | Maximum submodule recursion depth   |
| `--refresh`   | off      | Rebuild the cached graph first      |

## Data requirements

The cached module graph for the package, built to at least `--max-depth`. A graph cached at a
shallower depth MUST be rebuilt rather than answered from - see
[Cache and refresh](../behaviors/cache-refresh.md).

## Output rules

- `count: <n>` and a `tree` table of `depth`, `qualified_name`, `kind`.
- Depth is emitted as a column rather than as indentation, so the payload stays a uniform TOON
  table. Rendering a visual tree is the caller's business.
- Footer names `venvaxi inspect <module>`.
- Empty result: `count: 0` plus a hint naming the root package's own tree
  (`venvaxi tree <root>`), which shows the submodules that do exist. Only a dotted module name
  reaches this state - the root package resolved and imported, but the named submodule has no
  node in the graph: it does not exist, is private, or failed to import during the walk. A
  mistyped or uninstalled package never reaches it; that raises and exits `EX_FAILURE`.

## Exit codes

`EX_OK`, including the empty case. `EX_FAILURE` on any raised `Error`.

## Errors

- `InvalidArgumentError` - `package` is not a possible package name.
- `PackageNotFoundError` - not installed in the venv.
- `PackageImportError` - installed but not importable.

The three classes are defined once in [Package resolution](../behaviors/package-resolution.md).

## Principles

**Inherited** - project principles that especially bite here:

- Principle 1, token-efficient output
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - the flat depth column is
  what keeps this a table. Nesting would force per-row keys and lose the header amortization the
  encoding depends on.
