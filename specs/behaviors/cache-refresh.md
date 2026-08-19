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

`show --api`, `find`, `tree`, `inspect`, `inherits` - every command accepting `--refresh`.
`list` and `show` (metadata) read installed distribution metadata directly and are not cached.

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
2. The recorded build version equals the currently installed distribution version.
3. The recorded build depth is **at least** the depth the current query requires.

Depth is part of the check by necessity: if a graph was built at `--max-depth 1`, then it shall
not satisfy a later `--max-depth 4` request, which would silently return a shallow tree and read
as a definitive empty answer.

If a package has no recorded build, then the store shall treat it as invalid and build it on
first query.

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

### Lazy-depth model

The graph grows as queries demand depth; it is not exhaustively built up front. This has a
consequence callers MUST understand: `inherits` answers can *grow* over time. A subclass homed
deeper than the built depth stays undiscovered until some query builds that deep. This is why the
empty-state hint for `inherits` names both possible causes - an unindexed package, and
insufficient depth.

### When a rebuild is needed

After changing installed dependencies, the version check catches it automatically. `--refresh` is
for the cases the version check cannot see - a reinstall at the same version, an editable install
whose source changed, or a suspected corrupt graph.

`find` requires `--package` alongside `--refresh`, because there is no package scope to rebuild
otherwise.

## Out of scope

- **File-hash and incremental invalidation** - the Rule rejects them by name. Never - caches are
  disposable derived data, and version-plus-depth is the whole contract; a file-watching scheme
  would buy precision the disposable model does not need.
- **Cache eviction** - no size cap or LRU policy. No future spec is planned; the databases are
  small, per-project, and safe to delete.

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - the cache exists so answers track the installed version. Any caching change that could serve
  a stale signature defeats the tool's entire reason to exist.
