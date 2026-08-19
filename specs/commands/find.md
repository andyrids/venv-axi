---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
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

The `find` command shall end output with a footer naming `venvaxi inspect <qualified_name>`.

Empty result hints are situational, and this distinction is load-bearing - 'searched and found
nothing' and 'nothing was searched' are different answers:

- When a search with `--package` matches nothing, the `find` command shall emit `count: 0` with a
  hint naming `venvaxi list --all` - the package was searched and matched nothing, so the useful
  check is whether the package name was spelled right.
- When a search without `--package` matches nothing, the `find` command shall emit `count: 0`
  with a hint naming `find <query> --package <package>` - nothing was indexed to search, and that
  invocation would index one.

### Result ordering

The `find` command shall order results by the following keys, in order, each applied only to break
ties left by the one above it:

1. A symbol whose `name` equals the query, ignoring case, shall sort before one whose does not.
2. A symbol whose `name` begins with the query, ignoring case, shall sort before one whose does
   not.
3. A symbol of kind `class` or `function` shall sort before a symbol of any other kind.
4. A symbol with the shorter `qualified_name` shall sort before one with a longer
   `qualified_name`.
5. Remaining ties shall be broken by `qualified_name`, ascending.

Key 4 is what prefers **short facade paths over home paths** - the correct public spelling for an
agent to import. It MUST NOT be 'fixed' to prefer home paths; see
[Qualified name semantics](../behaviors/qualified-name-semantics.md).

Key 5 makes the order **total**. Two runs of the same query against the same graph shall return
the same rows in the same order, so an agent can cite a result position, cache an answer, or diff
two runs without the order shifting underneath it.

One gap between key 3 and key 4 is **deliberately unspecified**: a full-text backend may interpose
a relevance score there, and a substring backend has none to offer. Both satisfy keys 1 to 3 and
key 5, and both are deterministic run to run. A caller shall not rely on the relative order of two
results that keys 1 to 3 leave tied and that differ in relevance but not in `qualified_name`
length - it is the one place the two backends legitimately disagree.

Writing the gap down is the point. v0.1.0 freezes `specs/` as the public contract, and
'unspecified' is only a safe answer where it is recorded as a decision rather than left as a
silence a caller has to discover.

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
- [Principle 5, definitive empty states](../principles.md#principle-5-definitive-empty-states)
  - the two different empty
  hints exist because 'searched and found nothing' and 'nothing was searched' are different
  answers, and collapsing them would send an agent down the wrong recovery path.
