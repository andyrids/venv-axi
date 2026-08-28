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

| Argument    | Default  | Meaning                                                           |
| ----------- | -------- | ----------------------------------------------------------------- |
| `query`     | required | Free-text search over names and docs; names only when path-shaped |
| `--limit`   | `20`     | Maximum results                                                   |
| `--package` | none     | Package to index and scope the search to                          |
| `--refresh` | off      | Rebuild the cached graph before querying                          |

`--package` does double duty: it **indexes** that package if needed and **scopes** the search to
it. This is what lets a symbol found by scanning a codebase resolve to its qualified name without
a separate `show --api` or `tree` warm-up step.

`--refresh` requires `--package`, because without a package scope there is nothing to rebuild.

## Data requirements

The cached symbol graph, searched over name and docstring text. Without `--package`, only
already-indexed packages are searched - so a first-ever `find` with no `--package` legitimately
returns nothing.

A **path-shaped query** - one containing `.` or `::` - is a spelling of a qualified name, not free
text. The `find` command shall match a path-shaped query against `name` and `qualified_name` only,
and shall not match it against docstring text.

A docstring that mentions `Console.print` in a usage example is prose *about* the symbol, not a
spelling *of* it, and can never be the qualified name the caller asked to resolve. Three `rich`
classes matched `Console.print` on exactly that basis, out-ranking the method itself
([#94](https://github.com/andyrids/venv-axi/issues/94)). The narrowing is scoped to the
path-shaped case: a bare query still searches docstring text on both backends, which is the
surface [#79](https://github.com/andyrids/venv-axi/issues/79) brought the fallback into
conformance with.

### Literal matching

The `find` command shall match `query` as a literal string: every character in it shall match only
itself, both when selecting results and when applying the [ordering keys](#result-ordering)
below.

`_` and `%` are where this bites. Both are wildcards to the substring backend's matcher, and both
are ordinary characters in a Python identifier - `print_json`, `get_module_tree`, `__init__`. Left
uninsulated from the matcher, `find print_json` also returns `printXjson` for any `X` and ranks it
as a prefix match, with no error and no indication the match was approximate
([#108](https://github.com/andyrids/venv-axi/issues/108)).

The rule is declared rather than left to whichever backend answers, because an approximate result
returned as if it were exact is the one failure shape this command must not have: a caller cannot
tell it apart from a correct answer, and the whole point of resolving a spelling is that the
resolution is trustworthy.

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

### Bounded results

`--limit` is `find`'s bound under
[Bounded collections](../behaviors/output-contract.md#bounded-collections), which governs what a
bound means on every collection command: the capped-count hint, the definitive count below it,
`0` as a bound honoured exactly, and the rejection of a negative value.

`find`'s default bound is **20**. The rejection criterion sits in
[Failure modes](#failure-modes) with the command's other argument rejections.

That rule lived here until `show --api` bounded its collection too
([#67](https://github.com/andyrids/venv-axi/issues/67)); it was promoted once a second command
conformed, rather than generalized while only one did.

### Result ordering

The `find` command shall order results by the following keys, in order, each applied only to break
ties left by the one above it:

1. A symbol whose `name` equals the query, ignoring case, shall sort before one whose does not.
2. A symbol whose `name` begins with the query, ignoring case, shall sort before one whose does
   not.
3. A symbol whose `qualified_name` equals the query, or ends with the query preceded by `.` or
   `::`, ignoring case, shall sort before one whose does not.
4. A symbol of kind `class` or `function` shall sort before a symbol of any other kind.
5. A symbol with the shorter `qualified_name` shall sort before one with a longer
   `qualified_name`.
6. Remaining ties shall be broken by `qualified_name`, ascending.

Every key above compares `query` literally, per [Literal matching](#literal-matching): a `_` or `%`
in a query is a character in the ordering keys exactly as it is in the match, and never a wildcard.

Key 3 is what makes `Class.method` - the spelling an agent reads straight off a call site -
resolve to the method itself. Keys 1 and 2 are defined against `name`, and no row's `name` is
dotted, so without key 3 a path-shaped query silently disables the two highest-priority keys for
every row in the graph, and ranking falls through to kind - promoting every class above the method
asked for ([#94](https://github.com/andyrids/venv-axi/issues/94)).

Key 5 is what prefers **short facade paths over home paths** - the correct public spelling for an
agent to import. It MUST NOT be 'fixed' to prefer home paths; see
[Qualified name semantics](../behaviors/qualified-name-semantics.md).

Key 6 makes the order **total**. Two runs of the same query against the same graph shall return
the same rows in the same order, so an agent can cite a result position, cache an answer, or diff
two runs without the order shifting underneath it.

One gap between key 4 and key 5 is **deliberately unspecified**: a full-text backend may interpose
a relevance score there, and a substring backend has none to offer. Both satisfy keys 1 to 4 and
key 6, and both are deterministic run to run. A caller shall not rely on the relative order of two
results that keys 1 to 4 leave tied and that differ in relevance but not in `qualified_name`
length - it is the one place the two backends legitimately disagree.

Writing the gap down is the point. v0.1.0 freezes `specs/` as the public contract, and
'unspecified' is only a safe answer where it is recorded as a decision rather than left as a
silence a caller has to discover.

## Failure modes

- If `query` is empty, then the `find` command shall raise `InvalidArgumentError`, emit the TOON
  error block and exit `EX_FAILURE`.
- If `--limit` is negative, then the `find` command shall raise `InvalidArgumentError`, emit the
  TOON error block and exit `EX_FAILURE`.
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

- **Fuzzy or approximate matching** - the query is matched as supplied, against the surface
  [Data requirements](#data-requirements) declares for its shape; there is no edit-distance
  recovery of a misspelled symbol. Never - a miss is answered
  by the situational empty-state hints above, and a guessed match would be an answer the caller
  cannot trust.
- **Wildcard or pattern search** - `query` carries no pattern syntax; `_` and `%` are matched as
  the literal characters they are in a Python identifier, and no quoting or escape form re-enables
  them ([Literal matching](#literal-matching)). Never - `find` resolves a spelling an agent read
  off a call site, and a pattern language would turn every ordinary identifier query into a
  question of whether it had been escaped correctly.
- **Cross-package relevance ranking** - ranking orders spellings (facade before home); it does
  not weigh one package's results against another's. No future spec is planned; `--package` is
  the supported way to narrow a search.
- **Query decomposition** - a path-shaped query is matched and ranked whole; its head is not split
  off and matched against the owning class or module. `Console.print` ranks the method first
  because the row's `qualified_name` ends with it, not because `Console` was resolved to a class,
  and a query carrying more than one dot behaves identically. No future spec is planned; head
  filtering would change what the query *means* rather than how results are ranked, and would be
  filed on its own if a need for it appears.

## Principles

**Inherited** - project principles that especially bite here:

- [The agent's spelling wins over the internally correct one](../principles.md#the-agents-spelling-wins-over-the-internally-correct-one)
  - decides the facade-first ranking above.
- [Principle 5, definitive empty states](../principles.md#principle-5-definitive-empty-states)
  - the two different empty
  hints exist because 'searched and found nothing' and 'nothing was searched' are different
  answers, and collapsing them would send an agent down the wrong recovery path.
