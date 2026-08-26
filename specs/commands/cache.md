---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [command, cache, status]
---

# Command: venvaxi cache

## Invocation / inputs

```text
venvaxi cache
```

No arguments. Reports this project's cache state without changing it - see
[Out of scope](#out-of-scope) for why there is no `--refresh`.

## Data requirements

This project's own cache database, per
[Cache identity](../behaviors/cache-refresh.md#cache-identity). No package name is taken, resolved
or imported, and no graph is built: the command reads what earlier queries already recorded, never
what a fresh walk would find.

**The read shall not mutate the cache it reports on.** Every other cached command opens the store
through the path that keeps it current, which includes dropping and rebuilding a schema-mismatched
cache's tables as a side effect of opening it at all
([Schema version covers the builder, not just the shape](../behaviors/cache-refresh.md#schema-version-covers-the-builder-not-just-the-shape)).
This command shall never take that path. A stale recorded schema version is reported as a fact, not
corrected by the act of asking about it - see [Principles](#principles).

## Outputs

The `cache` command shall emit a flat TOON object of `schema_version`, `db_path` and
`db_size_bytes`, then `count: <n>` and a `builds` table of `package`, `version`, `depth`, `symbols`,
ordered by `package`.

- `schema_version` is the schema version recorded in this project's cache database, read as it
  stands - never venvaxi's currently-running schema version, and never upgraded to it by this read.
- `db_path` and `db_size_bytes` are the cache database's path and its size in bytes, `~/`-prefixed
  when under the home directory, else absolute, matching [the home view](home.md).
- Each `builds` row reports one package's recorded build: `version` is the version of the
  distribution(s) claiming the package's import name, resolved as
  [Cache and refresh](../behaviors/cache-refresh.md#version-resolution) specifies - a bare version
  string for the common single-distribution case, a `name=version` composite for an import name two
  or more distributions claim, and `(no distribution)` for one no distribution claims. It is not
  necessarily the version installed now - `show <package>` answers that separately, per
  [Out of scope](#out-of-scope) - `depth` is the recorded build depth, and `symbols` is the number
  of graph nodes currently recorded for it.

Two situations both report no builds, and they are different facts an agent might act on
differently, so they stay distinguishable rather than collapsing into one empty answer, per
[Principle 5](../principles.md#principle-5-definitive-empty-states):

- When this project has never had a cache database created for it, the `cache` command shall report
  `schema_version: (not built)`, `db_size_bytes: 0`, `count: 0`, and `db_path` naming where the
  database would be created.
- When a cache database exists but records zero package builds - a freshly created file, or one
  emptied by a schema-version rebuild - the command shall report the real recorded `schema_version`
  and `count: 0`.

Both carry the same hint, because the next step is identical either way: when `count` is zero, the
`cache` command shall end output with a hint naming `venvaxi show <package> --api` as the way to
index a package into this project's cache.

When `count` is nonzero, the `cache` command shall end output with a hint naming
`venvaxi show <package> --api --refresh` as the way to rebuild a package whose recorded build looks
stale.

This is an unbounded collection, deliberately - see [Out of scope](#out-of-scope).

## Failure modes

- If no project root resolves, then the `cache` command shall raise `ProjectRootNotFoundError`,
  emit the TOON error block and exit `EX_FAILURE`.
- If the cache database exists but cannot be read due to a SQLite-level failure, then the `cache`
  command shall raise `StoreError`, emit the TOON error block and exit `EX_FAILURE`.

This command never resolves, imports or validates a package name, so none of the three
[package resolution](../behaviors/package-resolution.md) classes apply to it - there is no package
argument to be malformed, absent or broken. `count: 0` is success, per the
[exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **A `--refresh` flag.** Never - this is the one command guaranteed never to touch the cache it
  reports on. Accepting `--refresh` would put a mutation on the surface built to answer 'what does
  the cache hold, unmodified'.
- **A row bound.** Unbounded, like [`list`](list.md). A project's cache holds one row per package a
  query has actually touched, which stays small in practice for the same reason `list` does -
  bounded by the project's real dependency surface - and tighter, since a cache row requires a
  query to have run at all, where `list` reports every declared dependency whether queried or not.
  Whether this should change is a question with its own evidence, per
  [Bounded collections](../behaviors/output-contract.md#bounded-collections).
- **Installed-version comparison.** Each row reports the version a package was *built* at, not the
  version installed now. A side-by-side comparison field was considered and dropped: the
  editable-install case this command exists to make checkable is exactly the one where the two
  never differ, because an in-place source edit does not move the installed version string at all.
  Reporting a comparison would read as reassurance in the one case it cannot detect anything.
- **A build timestamp.** The cache schema records no temporal column anywhere - not on the build
  record, not on a graph node or edge - so 'when was this built' is not an additive query; it needs
  a schema change and a schema-version bump, where the honest answer for a pre-bump row is `null`,
  never a backfilled guess. This command is the additive read the current schema already supports;
  a timestamp is a separate, larger unit. No future spec is planned.
- **Cache eviction.** No size cap, no LRU, no pruning of a dead project's cache or an uninstalled
  package's rows. This command makes growth *observable*, which is the gap it was raised to close;
  it does not make growth *bounded*. See
  [Cache and refresh](../behaviors/cache-refresh.md#out-of-scope) Out of scope.

## Principles

**Local**:

- **Observability MUST NOT cost the observer a mutation.** A read of cache state MUST NOT go
  through any path capable of rebuilding the cache, including the schema-mismatch rebuild that
  opening the store for any other command performs as a side effect of connecting. A caller asking
  what the graph currently holds gets an honest, possibly-stale answer - never a freshly rebuilt
  one it did not ask for and cannot tell apart from the state it meant to inspect.
