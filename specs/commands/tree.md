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
a hint naming the root package's own tree (`venvaxi tree <root>`), unless the name is a
module-binding miss to a public module, whose hint names that module's tree instead - see below.
Only a dotted module name
reaches this state - the root package resolved and imported, but the named submodule has no node
in the graph: it does not exist, is
[private](../behaviors/symbol-graph.md#private-submodules), is a name bound to a module recorded
elsewhere or not at all, or failed to import during the walk.
A mistyped or uninstalled package never reaches it; that raises and exits `EX_FAILURE`.

If the named submodule is private - any non-root segment of its dotted name starts with `_` -
then the hint shall say so before naming the root's own tree, so the caller learns the module is
deliberately unwalked rather than genuinely missing. A private submodule and a nonexistent or
failed-import one otherwise share the identical `count: 0` at `EX_OK`; the hint is the only
place the two are told apart.

If the named submodule is a
[module-binding miss](../behaviors/symbol-graph.md#module-bindings) - its parent binds its final
segment to a module that has no node under this name - then the hint shall state what the name
is bound to before naming a next step, still at `count: 0` and `EX_OK`:

- If the bound module is a public module of this package under its own dotted name, then the hint
  shall name that module and name `venvaxi tree <that module>` as the next step. The module is
  recorded under that name wherever the walk reaches it, so its own tree is where the caller's
  question is answered, if anywhere. The name comes from the live binding, not from a guess at
  what was meant.
- If the bound module is a private module of this package, or a module registered at import time
  where the walk cannot discover it, then the hint shall name it, say it is never indexed, and
  name the root's own tree (`venvaxi tree <root>`) for the modules that are indexed.
- If the bound module belongs to another package, then the hint shall name it as a module outside
  the named package, and name the root's own tree for the submodules that exist.

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
