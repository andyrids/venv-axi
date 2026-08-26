---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [behavior, cache, refresh]
---

# Behavior: Cache and refresh

## Rule

The symbol graph is cached per project and invalidated by **installed version plus build depth**,
never by file hash or incremental parse.

## Applies to

`show --api`, `find`, `tree`, `inspect`, `inherits` - every command accepting `--refresh` - and
`refreshPackageGraphTool`, the MCP tool that performs a rebuild with no query attached
([MCP tools](../mcp/tools.md#the-refresh-tool)).
`list` and `show` (metadata) read installed distribution metadata directly and are not cached.
[`cache`](../commands/cache.md) and `describeBindingTool`'s cache summary
([MCP tools](../mcp/tools.md#cache-summary)) read the store's recorded build state and schema
version directly, without invoking the path above, and therefore never rebuild.

## Details

### Cache identity

One SQLite database per consuming project at `~/.venvaxi/<hash>.db`, where `<hash>` is a
16-character SHA-256 digest of the resolved project root path. Two checkouts of the same project
at different paths therefore hold independent caches.

### Project root resolution

The consuming project root shall resolve to the nearest ancestor of the working directory
containing a `pyproject.toml`, falling back to the venv's parent directory. If no root resolves,
then the command shall raise `ProjectRootNotFoundError`.

### Validity

The store shall treat a cached graph as valid only when **all three** hold:

1. The store's schema version equals the current one.
2. The recorded build version equals the version currently resolved for the distribution(s)
   claiming the package's import name, per [Version resolution](#version-resolution).
3. The recorded build depth is **at least** the depth the current query requires.

Depth is part of the check by necessity: if a graph was built at `--max-depth 1`, then it shall
not satisfy a later `--max-depth 4` request, which would silently return a shallow tree and read
as a definitive empty answer.

If a package has no recorded build, then the store shall treat it as invalid and build it on
first query.

### Version resolution

The version compared under [Validity](#validity) item 2 is resolved from the distribution(s)
claiming the built package's *import* name, never from the import name treated as a distribution
name in its own right. `importlib.metadata` indexes installed distributions by distribution name,
and an import name coincides with its distribution name only by convention (`requests`), not by
rule (`dns` imports from the `dnspython` distribution). Resolving the import name as if it were a
distribution name fails silently for every package where the two differ, and a failed resolution
that degrades to an empty string compares equal to itself forever - the version check can then
never observe a real version change.

- If exactly one distribution claims an import name, then the store shall record that
  distribution's bare version string.
- If two or more distributions claim the same import name, then the store shall record a
  composite of every claiming distribution's full name and version, `name=version` pairs joined by
  a comma and sorted by distribution name, so that any one of them moving changes the composite and
  is observed as a version change:
  `jaraco.classes=3.4.0,jaraco.context=6.0.1,jaraco.functools=4.4.0`.
- If no distribution claims an import name, then the store shall record `(no distribution)`.
  Version-based invalidation is **inapplicable** for such an import name, not broken - a
  standard-library module and a local module importable on `sys.path` are both queryable by design
  and carry no distribution version to track. `SCHEMA_VERSION` and an explicit `--refresh` remain
  the invalidation path for this class, exactly as they already are for the editable-install case
  below ([When a rebuild is needed](#when-a-rebuild-is-needed)). Failing closed instead - rebuilding
  on every query for an undistributed import name - was considered and declined: it would rebuild
  `json` on every `venvaxi show json --api`.

### Schema version covers the builder, not just the shape

The schema version is stored as SQLite's `PRAGMA user_version`. If the schema version mismatches,
then the store shall drop and rebuild the tables from scratch - cache databases are disposable
derived data, so there are no migrations.

**It MUST be bumped whenever the *content* a walk records changes, not only when a table's
columns change.** Node fields are computed at walk time and frozen into the store, so a change to
how a docstring, signature or home name is derived leaves every existing cache serving the old
value. The version checks above cannot catch this: the distribution version has not moved, and
the depth is unchanged.

This is the subtle one, and the failure it prevents is silent. A user upgrading `venvaxi` to get
a correctness fix would otherwise keep the incorrect data indefinitely - until an unrelated
dependency bump happened to evict it - with no signal that anything was wrong, because incorrect
introspection output looks entirely plausible. Treat 'did I change what gets written?' as the
trigger, not 'did I change the table?'

### Rebuild

When `--refresh` is given, the store shall rebuild even when the cache is valid. Before walking,
the package's existing nodes shall be cleared, so a failed introspection cannot leave a
half-built graph behind that would then be treated as valid.

If a build raises, then the store shall roll back, close, and re-raise. If a SQLite-level failure
occurs, then it shall be re-raised as `StoreError`.

The clearing happens first and survives the failure, so a build that raises leaves the package
**unindexed** rather than stale. Under [Validity](#validity) it has no recorded build, so the next
query for it rebuilds. A failed refresh therefore costs the cached graph, which is the safe
direction to fail in: an absent graph is rebuilt on demand, and a half-built one would be served.

### Rebuild scope and depth

A rebuild request carrying no query has nothing to derive its scope or its depth from, so both
come from the request itself.

- A rebuild request naming no package shall be rejected. There is no 'rebuild everything' form:
  the graph is keyed by package, and a request naming none names no graph.
- Where a rebuild request carries no query to derive a depth from, the rebuild shall walk to the
  default build depth.

The second has a consequence worth stating, because it is observable and reads like a regression.
A graph previously built deeper - by a `tree` request at a greater depth, or by a query naming a
module below the default - is **narrowed** by such a rebuild, and its recorded depth is reset with
it. Most of that repairs itself: under [Validity](#validity) the next query requiring more depth
finds the recorded depth insufficient and rebuilds to what it needs.

[`inherits`](../commands/inherits.md) is the one that does not repair itself, because it requests
only the depth its own name implies rather than the depth the graph last held. A subclass homed
below the default depth becomes invisible again until some query builds that deep - the
[lazy-depth model](#lazy-depth-model) running backwards. That is why an `inherits` answer can
shrink as well as grow, and it is the price of a rebuild request that is scope-only by design.

### Lazy-depth model

The graph grows as queries demand depth; it is not exhaustively built up front. This has a
consequence callers MUST understand: `inherits` answers can *grow* over time. A subclass homed
deeper than the built depth stays undiscovered until some query builds that deep. This is why the
empty-state hint for `inherits` names both possible causes - an unindexed package, and
insufficient depth.

### When a rebuild is needed

After changing installed dependencies, the version check catches it automatically. An explicit
rebuild is for the cases the version check cannot see - a reinstall at the same version, an
editable install whose source changed, or a suspected corrupt graph.

The editable-install case is the common one, not a corner. The recorded version is the frozen
`Version` field of the installed distribution's metadata, so it does not move when source is
edited in place; only a reinstall moves it, and a dynamic version derived from VCS at build time
is no exception, because the value in the metadata was frozen at that build. For an ordinary
edit-and-verify loop against an editable-installed project, version-based invalidation never
fires at all, and an explicit rebuild is the only thing that will.

This is a different gap from [an import name with no distribution](#version-resolution). There, no
distribution version exists to move in the first place, and the check is declared inapplicable by
design; here, a real distribution version exists and genuinely has not moved, and the check is
blind to the only thing that *did* change - the source on disk. Both end in the identical remedy,
an explicit rebuild, but for different reasons -
[#89](https://github.com/andyrids/venv-axi/issues/89) is explicit that conflating them is the
mistake to avoid: a package resolving to `(no distribution)` is declared out of the version check's
reach, not silently broken the way a stale-cache package recording `""` for both sides was.

Every rebuild request names the package to rebuild, per
[Rebuild scope and depth](#rebuild-scope-and-depth). Most commands take that from the query they
are already answering; `find` requires `--package` alongside `--refresh` because a search has no
package scope of its own, and the MCP refresh tool takes the package as a required input for the
same reason.

## Out of scope

- **File-hash and incremental invalidation** - the Rule rejects them by name. Never - caches are
  disposable derived data, and version-plus-depth is the whole contract; a file-watching scheme
  would buy precision the disposable model does not need.
- **Cache eviction** - no size cap or LRU policy. No future spec is planned. The databases are not
  reliably small - a single three-dependency project's cache has been measured at 102 MiB
  ([#49](https://github.com/andyrids/venv-axi/issues/49), second comment) - but they remain
  per-project and safe to delete regardless of size. Growth is unbounded in two directions this
  spec does not bound: per project root, with nothing pruning a root that no longer exists, and per
  package within one cache, with nothing evicting a package no longer installed.
  [`cache`](../commands/cache.md) and `describeBindingTool`'s cache summary make both directions
  observable; neither bounds them.
- **A staleness signal carried by a read answer** - no command or tool annotates its answer with
  how current the graph behind it is. [#49](https://github.com/andyrids/venv-axi/issues/49) settled
  the narrower question - `describeBindingTool` now carries a cache summary, per
  [MCP tools](../mcp/tools.md#cache-summary) - but a signal folded into every *other* read answer
  is a wider question this spec still does not answer. An explicit rebuild, checked against the
  cache summary beforehand, is the remedy this spec provides.

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - the cache exists so answers track the installed version. Any caching change that could serve
  a stale signature defeats the tool's entire reason to exist.
