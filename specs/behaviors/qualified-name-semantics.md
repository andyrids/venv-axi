---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Behavior: Qualified name semantics

## Rule

The symbol graph keys nodes and edges in two different frames. Respect this invariant or
`inherits` silently returns zero for re-exported classes.

## Applies to

`find`, `inspect`, `inherits`, and every MCP tool that resolves a qualified name. Any change to
`_store.py`, `_introspect.py` or the `*.sql` queries must be checked against this file.

## Details

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
  short facade paths (the correct public spelling for agents; never 'fix' the ordering to prefer
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

## Principles

**Inherited** - project principles that especially bite here:

- [The agent's spelling wins over the internally correct one](../principles.md#the-agents-spelling-wins-over-the-internally-correct-one)
  - this is the rule that decides every facade-vs-home tie above. Output favours the facade;
  resolution absorbs the difference internally.
