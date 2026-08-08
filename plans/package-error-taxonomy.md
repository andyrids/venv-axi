---
status: done
depends: []
specs:
  - specs/commands/find.md
  - specs/commands/tree.md
  - specs/commands/show.md
  - specs/commands/inspect.md
  - specs/commands/inherits.md
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

`specs/commands/inspect.md` and `specs/commands/inherits.md` are amended by this plan rather
than implemented as written. The fix lands in the graph builder those two commands share with
the other three, so they gain the same `PackageNotFoundError` behaviour. Documenting the
taxonomy on three of five commands and leaving the other two silently different would make the
distinction a property of which verb was typed rather than of what is true about the venv.

`specs/commands/show.md` additionally gains a malformed-name clause - see Approach.

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
rather than a missing one. That second use is retagged to `InvalidArgumentError` here - a
malformed name is not a missing one, and leaving both meanings on one exception would defeat
the taxonomy this plan exists to draw.

Add an availability check ahead of the import attempt, in the one place all five commands pass
through.

### Availability is decided by the import system, not by metadata

The obvious check - reuse `_packages.resolve_package`, which metadata mode already uses - is
wrong. It answers 'does a distribution claim this name', which is a narrower question than 'is
this importable'. A stdlib module, a namespace package and a local module on `sys.path` are all
importable with no distribution at all, and would be reported as needing installation.

`importlib.util.find_spec` answers the right question, and answers it without executing the
module. Probed live in this venv:

```text
json                  find_spec -> True     (stdlib, no distribution)
rich                  find_spec -> True
detect_secrets        find_spec -> True     (import name)
detect-secrets        find_spec -> False    (distribution name - must resolve first)
definitelynotapackage find_spec -> False
axi_fixture_mod       raises ValueError: `__spec__` is None
```

The last row is load-bearing. A module already in `sys.modules` that carries no `__spec__` - a
bare `types.ModuleType`, which is exactly what the test fixtures register - makes `find_spec`
*raise* rather than return. So `sys.modules` MUST be consulted first: an imported module is
available by definition.

Ordered check, given the import name from `_resolve_import_name`:

1. Present in `sys.modules` - available.
2. `find_spec` returns a spec - available.
3. Not located, but a distribution of that name resolves - available, and the subsequent import
   attempt reports `PackageImportError` (installed, unlocatable).
4. Otherwise - `PackageNotFoundError`, reusing the wording `_packages.resolve_package` already
   emits, so both paths say one thing.

`_resolve_import_name` MUST run *before* the check, or a dashed distribution name is misreported
as missing (row four above).

## Validation

- [x] `venvaxi tree <not-installed>` reports 'not installed in the active venv'
- [x] `venvaxi find X --package <not-installed>` reports the same
- [x] `venvaxi show <not-installed> --api` reports the same
- [x] A package that *is* installed but raises on import still reports `PackageImportError`
- [x] A package whose import name differs from its distribution name (e.g. dashed names) still
  resolves and is not misreported as missing
- [x] `show <not-installed>` metadata mode is unchanged
- [x] Unit tests cover both branches for each of the three commands
- [x] `venvaxi inspect <not-installed>::X` and `venvaxi inherits <not-installed>::X` report 'not
  installed in the active venv'
- [x] An importable module with no installed distribution (`venvaxi tree json`) is not
  misreported as not installed
- [x] `venvaxi show <malformed> --api` reports `InvalidArgumentError`, not `PackageNotFoundError`
- [x] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green

## Risks / unknowns

- **Resolved: importable means installed.** A namespace package, a stdlib module, or a local
  module on `sys.path` is importable with no installed distribution at all. The spec's intent is
  that an agent can tell 'install it' from 'investigate it', and for all three of those the
  answer is 'investigate it' - so they read as installed. This is what makes `find_spec`, rather
  than `importlib.metadata`, the primitive in Approach.
- **Resolved: no metadata lookup on the hot path.** The earlier concern was an extra
  `importlib.metadata` call on every `find`. With the ordered check above, the success path is a
  `sys.modules` hit or one finder search, and metadata is consulted only when a name has already
  failed to locate.
- **Open: a wrong answer is now louder.** Before this change, an unlocatable name still attempted
  the import and surfaced whatever the import system said. A guard that decides 'not installed'
  ahead of that suppresses the underlying `ImportError` for a genuinely broken but locatable
  package - hence step three, which is what keeps that class of failure reporting as an import
  error rather than a missing one.

## Notes

**The obvious implementation was the wrong one.** The Approach originally proposed reusing
`_packages.resolve_package`. That answers 'does a distribution claim this name', which is
narrower than 'is this importable', and would have reported every stdlib module as needing
installation. `importlib.util.find_spec` was substituted before any code was written - the
Approach above is the rewrite, not the original.

**`sys.modules` must be checked before `find_spec`.** `find_spec` raises
`ValueError: __spec__ is None` for a bare `types.ModuleType` registered in `sys.modules`, which
is exactly what `tests/test_introspect.py::fake_module` does. Without the short-circuit, every
`get_public_api` test fails with a spurious 'not installed'. This is recorded as a `NOTE:` in
the helper, because it reads as a redundant fast path and a later refactor would delete it.

**The check takes the top-level root, not the caller's `name`.** The first test run produced
``Package `this_module_does_not_exist_xyz::Nope` is not installed`` - `_build_store_for` passes
a qualified name for `inspect` and `inherits`. `_top_level_root` now runs first, and
`test_get_symbol_not_installed_raises` asserts `::Nope` never reaches the message.

**Installed-but-unlocatable falls through deliberately.** When `find_spec` locates nothing but a
distribution claims the name, the guard returns rather than raising, so the caller's import
attempt reports `PackageImportError`. This is what stops the new guard swallowing genuine import
failures, and it is the reason the check is three-stage rather than one.

**Two specs were amended rather than implemented.** `inspect` and `inherits` reach the same
builder, so they gained the behaviour whether or not their specs asked for it. Documenting the
taxonomy on three verbs and leaving two silently different would make the distinction a property
of which verb was typed.

**Verified**: 225 tests pass, 8/8 prek hooks pass, 97% total coverage. Live CLI exercised across
all five commands plus the metadata-mode and hot-path controls.

**`pr:` is unset.** No PR has been opened for this branch yet; it MUST be filled in when one is.
A closeout that invents a number is worse than one that admits the gap.

## Follow-ups

- **Issue** - a degenerate package name whose top-level root is empty (`venvaxi tree ".foo"`)
  escapes as `Unexpected error: A distribution name is required`. Confirmed pre-existing by
  stashing this plan's source change and reproducing the identical message at `HEAD`, where it
  originates in `_cache._installed_version`. The fix is boundary name validation for the verbs
  that have none - `show --api` already has `_VALID_NAME_RE`, `tree`, `find`, `inspect` and
  `inherits` do not. Out of scope here: this plan draws a distinction between two *valid*-name
  outcomes, and adding a third class of guard would widen it into a different change.
- **None** otherwise. No work was deferred to a downstream plan, so no absorption edit is owed.
