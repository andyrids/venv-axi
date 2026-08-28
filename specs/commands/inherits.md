---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [command, inherits]
---

# Command: venvaxi inherits

## Invocation / inputs

```text
venvaxi inherits <qualified_name> [--bases] [--refresh]
```

| Argument         | Default  | Meaning                                              |
| ---------------- | -------- | ---------------------------------------------------- |
| `qualified_name` | required | Qualified class name (`module::Class`)               |
| `--bases`        | off      | Report the class's base classes instead of subclasses |
| `--refresh`      | off      | Rebuild the cached graph first                       |

The positional is the **base** class in the default direction and the **subclass** in the
`--bases` direction. It is one argument either way - the class the caller has in hand.

## Data requirements

`INHERITS` edges from the cached graph. **Direct** relations only - not the transitive closure,
in either direction.

### Direction

`INHERITS` edges run subclass to base ([Symbol graph](../behaviors/symbol-graph.md)). This command
reads them both ways: by default the `inherits` command shall report the classes that directly
subclass the named class, and with `--bases` it shall report the classes the named class directly
subclasses.

**The two directions do not have the same reach, and the difference is observable.** A subclass
edge is written while walking the *subclass's* package, so a subclass stays invisible until its own
package is indexed. A base edge is written by the walk that records the named class itself, from
the named class's side. Therefore:

- Where `--bases` is given, the `inherits` command shall report a base class whose own package has
  never been indexed.

`rich.logging::RichHandler` reports `logging::Handler` on a cache where `logging` was never walked,
because the edge was written from `rich`'s side. The consequence is that the two directions have
different empty states and different hints: indexing *another* package can add a subclass, but it
can never add a base, so an empty `--bases` answer has no 'index more' recovery to offer. Its
recovery, where it has one, is a rebuild of the named class's **own** package - see
[Empty states](#empty-states).

`object` is not recorded. The walk skips it, so a class deriving directly from `object` has no base
edge at all - which is what makes an empty `--bases` answer definitive rather than ambiguous.

This command resolves through `SymbolStore.canonical_name` to the class's *home* module for
**every** input, because `INHERITS` edges are always keyed at the home frame. `inspect` shares
that resolution, but only through its class-member carve-out - a facade-spelled member with no
row of its own; `find` never resolves. See
[Qualified name semantics](../behaviors/qualified-name-semantics.md).

Build depth is derived from the canonical name, so facade and home spellings agree on a fresh
cache.

## Outputs

The `inherits` command shall emit `count: <n>` and an `inheritors` table of `name`, `kind`,
`qualified_name`.

Where `--bases` is given, the `inherits` command shall emit `count: <n>` and a `bases` table of
the same three fields. The table is named for what it holds, so a caller reading the output alone
can tell which direction answered it.

The `inherits` command shall end output with a footer naming
`venvaxi inspect <qualified_name>`, in both directions.

### Result ordering

Both tables shall be ordered by `qualified_name`, ascending - a total, deterministic order, so two
runs against the same graph return the same rows in the same order.

For `--bases` this is deliberately **not** declaration order. A class's `__bases__` order carries
MRO significance, and the graph does not record it: edges are keyed `(src, dst, kind)` with no
ordinal, so the order is lost at write time. Presenting rows in any order that resembled
declaration order would be a claim the stored data cannot support. A caller needing MRO order must
read it from the class itself.

### Empty states

`count: 0` never means a lookup failure in either direction. An unresolvable name raises
`SymbolNotFoundError` upstream instead, so a zero count always means the named class resolved.
Three empty states are distinguishable, and they take different hints because they call for
different next moves:

- When the named class resolves with zero indexed subclasses, the `inherits` command shall emit
  `count: 0` plus a hint naming **three** causes - subclasses in an unindexed package, subclasses
  below the built depth, and the query having been pointed the wrong way - and that hint shall name
  `venvaxi inherits <qualified_name> --bases` as the recovery for the third.
- Where `--bases` is given and the named class has at least one recorded base, `count` shall be the
  number of those bases.
- Where `--bases` is given and the named class has no recorded base, the `inherits` command shall
  emit `count: 0` plus a hint naming **both** causes - the class derives directly from `object`,
  which is not indexed, or a base's package has been refreshed since this class was indexed - and
  that hint shall name `--refresh` on the named class's own package as the recovery for the second.

The third empty state is **not** the wholly definitive answer it first appears to be, and saying so
is load-bearing, because the first draft of this spec asserted that it was.

A walk records every base except `object`, so a freshly walked class with no base edge does derive
from `object` and there is nothing further to find. But that holds only while the graph is
untouched since the walk. `clear_package` deletes every edge with the cleared package's node at
*either* end, and a base edge is written from the **subclass's** side - so refreshing the base's
package deletes an edge the subclass's walk recorded, while the subclass's own node survives. The
subclass is then left in the graph with its ancestry silently removed, and a hint asserting
`object` in that state would be a confident wrong answer. That is the one thing this command must
never produce, which is why the hint names two causes rather than one.

The recovery for the second cause is `--refresh` on the **named class's** package, not the base's:
the edge is restored by the walk that wrote it. Indexing some other package cannot help, and the
hint must not suggest it - that is the mistake the subclasses hint made for the wrong-direction
case, in reverse.

The first hint's third cause is the one this command existed without. Both original causes say
*index more, or build deeper*, and neither can succeed when the caller wanted the parent - so an
agent that asked backwards was sent to do work that could not help
([#48](https://github.com/andyrids/venv-axi/issues/48)).

Answers may legitimately **grow** as build depth grows. A subclass homed deeper than the current
build stays undiscovered until some query builds that deep - the lazy-depth model in
[Cache and refresh](../behaviors/cache-refresh.md).

## Failure modes

- If the base class name does not resolve, then the `inherits` command shall raise
  `SymbolNotFoundError`, emit the TOON error block and exit `EX_FAILURE`.
- If the name's top-level component is not a possible package name, then the `inherits` command
  shall raise `InvalidArgumentError`, emit the TOON error block and exit `EX_FAILURE`.
- If the owning package is not installed in the venv, then the `inherits` command shall raise
  `PackageNotFoundError`, emit the TOON error block and exit `EX_FAILURE`.
- If the owning package is installed but cannot be imported to build the graph, then the
  `inherits` command shall raise `PackageImportError`, emit the TOON error block and exit
  `EX_FAILURE`.

The three package classes are defined once in
[Package resolution](../behaviors/package-resolution.md). An empty result is success - `count: 0`
exits `EX_OK`, per the [exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **The transitive closure** - direct relations only, in both directions; a full descendant tree or
  a full ancestry chain is composed by the caller from repeated calls. No future spec is planned.
- **MRO order** - `--bases` reports which classes are direct bases, not the order Python resolves
  them in. Recording it would need an ordinal on the edge and a schema version bump, and the
  ordering rule above states why the current data cannot support the claim. Filed if a need
  appears; a caller needing the true MRO reads it from the class.
- **Docstring reporting** - there is no `--docstring` flag and the table carries no `doc` column;
  per-symbol detail belongs to `inspect`.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 5, definitive empty states](../principles.md#principle-5-definitive-empty-states)
  - the separation between
  `count: 0` and `SymbolNotFoundError` is what makes a zero answer trustworthy. Collapsing them
  would make every empty result ambiguous.
- [The agent's spelling wins over the internally correct one](../principles.md#the-agents-spelling-wins-over-the-internally-correct-one)
  - the caller passes whichever spelling they have; resolution absorbs the facade/home
  difference rather than demanding the home path.
