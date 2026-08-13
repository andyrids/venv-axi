---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state
immutable: false
tags: [command, find]
---

# Command: venvaxi find

Converts a bare symbol name scanned out of a codebase into a qualified name.

## Invocation / inputs

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

## Data requirements

The cached symbol graph, searched over name and docstring text. Without `--package`, only
already-indexed packages are searched - so a first-ever `find` with no `--package` legitimately
returns nothing.

## Outputs

The `find` command shall emit `count: <n>` and a `symbols` table of `name`, `kind`,
`qualified_name`.

When ranking results, the `find` command shall prefer short facade paths over home paths - the
correct public spelling for an agent to import. This ordering MUST NOT be 'fixed' to prefer home
paths; see [Qualified name semantics](../behaviors/qualified-name-semantics.md).

The `find` command shall end output with a footer naming `venvaxi inspect <qualified_name>`.

Empty result hints are situational, and this distinction is load-bearing - 'searched and found
nothing' and 'nothing was searched' are different answers:

- When a search with `--package` matches nothing, the `find` command shall emit `count: 0` with a
  hint naming `venvaxi list --all` - the package was searched and matched nothing, so the useful
  check is whether the package name was spelled right.
- When a search without `--package` matches nothing, the `find` command shall emit `count: 0`
  with a hint naming `find <query> --package <package>` - nothing was indexed to search, and that
  invocation would index one.

## Failure modes

- If `query` is empty, then the `find` command shall raise `InvalidArgumentError`, emit the TOON
  error block and exit `EX_FAILURE`.
- If `--refresh` is given without `--package`, then the `find` command shall raise
  `InvalidArgumentError`, emit the TOON error block and exit `EX_FAILURE`.
- If the `--package` value is not a possible package name, then the `find` command shall raise
  `InvalidArgumentError`, emit the TOON error block and exit `EX_FAILURE`.
- If `--package` names a package not installed in the venv, then the `find` command shall raise
  `PackageNotFoundError`, emit the TOON error block and exit `EX_FAILURE`.
- If the package cannot be imported for introspection, then the `find` command shall raise
  `PackageImportError`, emit the TOON error block and exit `EX_FAILURE`.

The three package classes are defined once in
[Package resolution](../behaviors/package-resolution.md). An empty result is success, not
failure - `count: 0` exits `EX_OK`, per the
[exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **Fuzzy or approximate matching** - the query is matched against name and docstring text as
  supplied; there is no edit-distance recovery of a misspelled symbol. Never - a miss is answered
  by the situational empty-state hints above, and a guessed match would be an answer the caller
  cannot trust.
- **Cross-package relevance ranking** - ranking orders spellings (facade before home); it does
  not weigh one package's results against another's. No future spec is planned; `--package` is
  the supported way to narrow a search.

## Principles

**Inherited** - project principles that especially bite here:

- [The agent's spelling wins over the internally correct one](../principles.md#the-agents-spelling-wins-over-the-internally-correct-one)
  - decides the facade-first ranking above.
- Principle 5, definitive empty states
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - the two different empty
  hints exist because 'searched and found nothing' and 'nothing was searched' are different
  answers, and collapsing them would send an agent down the wrong recovery path.
