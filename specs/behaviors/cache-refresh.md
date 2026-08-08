---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Behavior: Cache and refresh

## Rule

The symbol graph is cached per project and invalidated by **installed version plus build depth**,
never by file hash or incremental parse.

## Applies To

`show --api`, `find`, `tree`, `inspect`, `inherits` - every command accepting `--refresh`.
`list` and `show` (metadata) read installed distribution metadata directly and are not cached.

## Details

### Cache identity

One SQLite database per consuming project at `~/.venvaxi/<hash>.db`, where `<hash>` is a
16-character SHA-256 digest of the resolved project root path.

### Validity

A cached graph is valid when **all three** hold:

1. The store's schema version equals the current one.
2. The recorded build version equals the currently installed distribution version.
3. The recorded build depth is **at least** the depth the current query requires.

Depth is part of the check by necessity: a graph built at `--max-depth 1` MUST NOT satisfy a
later `--max-depth 4` request, which would silently return a shallow tree and read as a
definitive empty answer.

A package with no recorded build is invalid, and is built on first query.

### Schema version covers the builder, not just the shape

The schema version is stored as SQLite's `PRAGMA user_version`. On mismatch the tables are
dropped and rebuilt from scratch - cache databases are disposable derived data, so there are no
migrations.

**It MUST be bumped whenever the *content* a walk records changes, not only when a table's
columns change.** Node fields are computed at walk time and frozen into the store, so a change to
how a docstring, signature or home name is derived leaves every existing cache serving the old
value. The version checks above cannot catch this: the distribution version has not moved, and
the depth is unchanged.

This is the subtle one, and the failure it prevents is silent. A user upgrading `venvaxi` to get
a correctness fix would otherwise keep the incorrect data indefinitely - until an unrelated
dependency bump happened to evict it - with no signal that anything was wrong, because incorrect
introspection output looks entirely plausible. Treat "did I change what gets written?" as the
trigger, not "did I change the table?"

### Rebuild

`--refresh` forces a rebuild even when the cache is valid. Before walking, the package's existing
nodes are cleared, so a failed introspection cannot leave a half-built graph behind that would
then be treated as valid.

A build that raises rolls back and closes the store, then re-raises. A SQLite-level failure is
re-raised as `StoreError`.

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

## Principles

**Inherited** - project principles that especially bite here:

- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - the cache exists so answers track the installed version. Any caching change that could serve
  a stale signature defeats the tool's entire reason to exist.
