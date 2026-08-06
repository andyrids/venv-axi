---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
context-hierarchy-scope: Feature-scoped - read only when working on the axi CLI (src/venvaxi)
---

# AXI Principles

## The 10 AXI Principles

Source: [axi.md](https://axi.md/), "The 10 AXI Principles".

1. **Token-efficient output** - use TOON format for ~40% token savings over JSON.
2. **Minimal default schemas** - return 3-4 fields per list item by default, not 10+.
3. **Content truncation** - truncate large text fields with a size-hint suffix (e.g. `truncated,
   2847 chars total`).
4. **Pre-computed aggregates** - include derived fields (e.g. `totalCount`) that eliminate round
   trips.
5. **Definitive empty states** - an explicit zero-result message on empty output, never silent
   blank output.
6. **Structured errors & exit codes** - idempotent mutations, structured errors written to
   stdout, commands never prompt.
7. **Ambient context** - installed into the agent's session/hooks via an explicit setup command.
8. **Content first** - a bare command with no arguments shows live, actionable data, not help
   text.
9. **Contextual disclosure** - `help[]` lines after output suggesting concrete next-step command
   templates.
10. **Consistent way to get help** - every subcommand offers `--help` as a fallback.

## Measured Token Efficiency

Principle 1's "~40%" is an external claim. Measured against the payload shapes `axi` actually
emits (`tests/test_toon_benchmark.py`, characters vs compact JSON):

| Payload shape | Command | Saving |
| ------------- | ------- | ------ |
| Wide table, short cells | `axi list` | ~45% |
| Table with quoted `::` names | `axi find` | ~27% |
| Flat object, one large value | `axi inspect <symbol>` | ~6% |

The saving comes from amortising repeated JSON keys across a table header, so it scales with row
count and collapses on single-object output. Do not cite ~40% as a general figure: on the
`inspect` path token efficiency has to come from truncation (principle 3), not the encoding.

## Qualified Name Semantics

The symbol graph keys nodes and edges in two different frames - respect this invariant or
`inherits` silently returns zero for re-exported classes:

- **Nodes** are keyed at the *containing* (facade) module - the module whose walk recorded the
  symbol. **`INHERITS` and class-member `CONTAINS` edges** are keyed at the class's *home* module
  (`cls.__module__`), i.e. at the node's `home_qualified_name`.
- Every node stores its `home_qualified_name`: for classes/functions the `module::name` built
  from `__module__`/`__name__` (rename-proof for `import ... as` aliases); for attributes,
  modules and packages, the node's own `qualified_name`. An instance constant resolves
  `__module__` via its *class* (`re.compile(...)` -> `re`), so claiming a home there would record
  a false fact - hence the class/function kind guard in `_record_symbol`.
- `SymbolStore.canonical_name` is the single facade -> home resolution point. It is applied by
  `get_inheritors` only - `get_symbol`/`show_module` deliberately answer with facade-keyed data
  (rewriting would change the `module` field agents see), and `find` ranking deliberately prefers
  short facade paths (the correct public spelling for agents; never "fix" the ordering to prefer
  home paths - the resolver absorbs facade input where it matters).
- Home-path class nodes are materialized only when the home module sits inside the *same*
  package. A foreign (e.g. stdlib) class re-exported by two indexed packages must not have its
  home node's `package` field claimed, or `clear_package` for one package deletes the other
  package's node. Cross-package bases resolve once their owning package is indexed.
- `inherits` derives its build depth from the canonical name, so facade and home paths agree on
  a fresh cache. Answers can still *grow* as build depth grows (lazy-depth model): a subclass
  homed deeper than the base stays undiscovered until some query builds that deep.
- The `nodes` table must keep a stable rowid mapping for the external-content FTS5 index - never
  `VACUUM` these caches without rebuilding, or add an `INTEGER PRIMARY KEY` first.
