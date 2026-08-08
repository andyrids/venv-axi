---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi find

Converts a bare symbol name scanned out of a codebase into a qualified name.

## Invocation

```text
venvaxi find <query> [--limit N] [--package <package>] [--refresh]
```

| Argument    | Default  | Meaning                                       |
| ----------- | -------- | --------------------------------------------- |
| `query`     | required | Free-text search over symbol names and docs   |
| `--limit`   | `20`     | Maximum results                               |
| `--package` | none     | Package to index and scope the search to      |
| `--refresh` | off      | Rebuild the cached graph before querying      |

`--package` does double duty: it **indexes** that package if needed and **scopes** the search to
it. This is what lets a symbol found by scanning a codebase resolve to its qualified name without
a separate `show --api` or `tree` warm-up step.

`--refresh` requires `--package`, because without a package scope there is nothing to rebuild.

## Data Requirements

The cached symbol graph, searched over name and docstring text. Without `--package`, only
already-indexed packages are searched - so a first-ever `find` with no `--package` legitimately
returns nothing.

## Output Rules

- `count: <n>` and a `symbols` table of `name`, `kind`, `qualified_name`.
- Ranking prefers **short facade paths** - the correct public spelling for an agent to import.
  This ordering MUST NOT be "fixed" to prefer home paths; see
  [Qualified name semantics](../behaviors/qualified-name-semantics.md).
- Footer names `venvaxi inspect <qualified_name>`.

Empty result hints are situational, and this distinction is load-bearing:

- **With** `--package` - the package was searched and matched nothing, so the hint names
  `venvaxi list --all` to check the package name was spelled right.
- **Without** `--package` - nothing was indexed to search, so the hint names
  `find <query> --package <package>`, which would index one.

## Exit Codes

`EX_OK`, including the empty case. `EX_FAILURE` on any raised `Error`.

## Errors

- `PackageNotFoundError` - `--package` names a package not installed in the venv.
- `PackageImportError` - the package cannot be imported for introspection.

## Principles

**Inherited** - project principles that especially bite here:

- [The agent's spelling wins over the internally correct one](../principles.md#the-agents-spelling-wins-over-the-internally-correct-one)
  - decides the facade-first ranking above.
- Principle 5, definitive empty states
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - the two different empty
  hints exist because "searched and found nothing" and "nothing was searched" are different
  answers, and collapsing them would send an agent down the wrong recovery path.
