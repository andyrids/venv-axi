---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi inherits

## Invocation

```text
venvaxi inherits <qualified_name> [--refresh]
```

| Argument         | Default  | Meaning                                  |
| ---------------- | -------- | ---------------------------------------- |
| `qualified_name` | required | Qualified base class name (`module::Class`) |
| `--refresh`      | off      | Rebuild the cached graph first           |

There is no `--docstring` flag; the output carries no `doc` column.

## Data requirements

`INHERITS` edges from the cached graph. **Direct** subclasses only - not the transitive closure.

Unlike `inspect` and `find`, this command resolves through `SymbolStore.canonical_name` to the
class's *home* module, because `INHERITS` edges are keyed at the home frame. It is the only
consumer of that resolution. See
[Qualified name semantics](../behaviors/qualified-name-semantics.md).

Build depth is derived from the canonical name, so facade and home spellings agree on a fresh
cache.

## Output rules

- `count: <n>` and an `inheritors` table of `name`, `kind`, `qualified_name`.
- Footer names `venvaxi inspect <qualified_name>`.

Empty result: `count: 0` plus a hint naming `venvaxi find <name> --package <package>`. The hint
MUST name **both** causes - subclasses in an unindexed package, and subclasses below the built
depth - because the caller cannot distinguish them from the output.

`count: 0` here means the base class resolved and has zero *indexed* subclasses. It is a
definitive empty state, not a lookup failure: an unresolvable name raises `SymbolNotFoundError`
upstream instead.

Answers may legitimately **grow** as build depth grows. A subclass homed deeper than the current
build stays undiscovered until some query builds that deep - the lazy-depth model in
[Cache and refresh](../behaviors/cache-refresh.md).

## Exit codes

`EX_OK`, including the empty case. `EX_FAILURE` on any raised `Error`.

## Errors

- `SymbolNotFoundError` - the base class name does not resolve.
- `PackageImportError` - the owning package cannot be imported to build the graph.

## Principles

**Inherited** - project principles that especially bite here:

- Principle 5, definitive empty states
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - the separation between
  `count: 0` and `SymbolNotFoundError` is what makes a zero answer trustworthy. Collapsing them
  would make every empty result ambiguous.
- [The agent's spelling wins over the internally correct one](../principles.md#the-agents-spelling-wins-over-the-internally-correct-one)
  - the caller passes whichever spelling they have; resolution absorbs the facade/home
  difference rather than demanding the home path.
