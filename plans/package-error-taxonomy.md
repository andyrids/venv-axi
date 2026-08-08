---
status: planned
depends: []
specs:
  - specs/commands/find.md
  - specs/commands/tree.md
  - specs/commands/show.md
issues: []
pr:
---

# Plan: Distinguish not-installed from failed-to-import

## Scope

Make `find --package`, `tree` and `show --api` raise `PackageNotFoundError` when a package is not
installed, reserving `PackageImportError` for packages that are installed but cannot be imported.

Surfaced by the first `/audit-spec-drift` run against the new spec tree, and absorbed from
[spec-driven-icm](spec-driven-icm.md)'s Follow-ups.

## Implements

`specs/commands/find.md`, `specs/commands/tree.md` and `specs/commands/show.md` - each documents
`PackageNotFoundError` as 'not installed in the venv' and `PackageImportError` as 'installed but
cannot be imported for introspection'. The specs state the desired state and stay as written;
the code is what diverges.

## Approach

All three commands reach the graph builder, which goes straight to `importlib.import_module` and
lets the failure surface as `PackageImportError`. Live-verified against a nonexistent package:

```text
$ uv run venvaxi find Foo --package definitelynotapackage
message: Failed to import `definitelynotapackage` (from `definitelynotapackage`)

$ uv run venvaxi show definitelynotapackage        # metadata mode, for contrast
message: Package `definitelynotapackage` is not installed in the active venv
```

`PackageNotFoundError` is reachable from only two places today: `_packages.resolve_package`
(metadata mode, correct) and `get_public_api`, where it fires on an **invalid-character** name
rather than a missing one.

Add an installed check ahead of the import attempt, reusing the resolution `_packages` already
performs for metadata mode rather than writing a second one. Take care with the distinction the
codebase already draws between distribution names and import names (`_resolve_import_name`
handles dash/underscore and case normalization) - a package can be importable without its
distribution name matching, and vice versa, so the check must not reject a legitimately
importable module just because no distribution claims that exact name.

## Validation

- [ ] `venvaxi tree <not-installed>` reports 'not installed in the active venv'
- [ ] `venvaxi find X --package <not-installed>` reports the same
- [ ] `venvaxi show <not-installed> --api` reports the same
- [ ] A package that *is* installed but raises on import still reports `PackageImportError`
- [ ] A package whose import name differs from its distribution name (e.g. dashed names) still
  resolves and is not misreported as missing
- [ ] `show <not-installed>` metadata mode is unchanged
- [ ] Unit tests cover both branches for each of the three commands
- [ ] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green

## Risks / unknowns

- **The distinction is not always clean.** A namespace package, a stdlib module, or a local
  module on `sys.path` is importable with no installed distribution at all. Decide whether those
  count as 'installed' - the spec's intent is that an agent can tell 'install it' from
  'investigate it', so importable-but-undistributed should probably read as installed.
- **An extra metadata lookup on every call.** Small, but it sits on the hot path for `find`,
  which is the most-invoked command.

## Notes

Populated at closeout.

## Follow-ups

Populated at closeout.
