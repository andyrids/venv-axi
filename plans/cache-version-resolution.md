---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/cache-refresh.md
  - specs/commands/cache.md
authors: []
issues: [89]
pr:
---

# Plan: cache-version-resolution

## Scope

`_installed_version` (`src/venvaxi/_cache.py:166`) resolves a version by treating its argument as
a **distribution** name, but `get_or_build_store` (`:240`) calls it with the **import** name,
because `_build_store_for` (`src/venvaxi/_introspect.py:794`) has already mapped the caller's
spelling to an import name through `_resolve_import_name` before the call reaches `_cache.py`. For
any package whose import name is not also a distribution name, `metadata.version(import_name)`
raises `PackageNotFoundError` and `""` is recorded as the built version. `is_cache_valid`
(`:208`) then compares the recorded `""` against a freshly resolved `""` - both sides empty,
always equal - so version-based invalidation can never fire for that class of package.

**Confirmed live in this repo's own cache** (issue #89): `metadata.version('dns')` raises;
`metadata.version('dnspython')` returns `2.8.0`; the recorded row is `dns|""|2|3314`. Other common
cases resolve the same way in this venv - `yaml` (PyYAML), `bs4` (beautifulsoup4), `dateutil`
(python-dateutil), `PIL` (pillow) - each raises on its import name and would record `""` too.
`jaraco` is a live multi-distribution case: `importlib.metadata.packages_distributions()` maps it
to `['jaraco.classes', 'jaraco.context', 'jaraco.functools']` in this venv.

**Decisions taken by the maintainer, implemented here rather than relitigated:**

1. The version is resolved from the distribution(s) claiming the import name, via
   `metadata.packages_distributions()`'s reverse map - never from the import name treated as a
   distribution name.
2. An import name claimed by two or more distributions records a composite of every claiming
   distribution's full name and version (`name=version`, comma-joined, sorted by distribution name)
   so any one of them moving invalidates the cache. A single-distribution import name (the vast
   majority) stays a bare version string.
3. An import name claimed by no distribution - a standard-library module or a local module
   importable on `sys.path`, both of which `_ensure_installed` deliberately allows - records
   `(no distribution)`. Version invalidation is declared **inapplicable** for that class, not
   broken; `SCHEMA_VERSION` and an explicit `--refresh` remain its invalidation path, exactly as
   already stated for the editable-install case. Failing closed (rebuild on every query) was
   considered and declined - it would rebuild `json` on every `venvaxi show json --api`.
4. `SCHEMA_VERSION` moves `7 -> 8`. Rows already recorded with `""` stay valid forever under the
   old comparison even after the code fix lands; the spec's own bump trigger - a change to what a
   walk *records* - fires here regardless of the table shape being unchanged.

**The performance constraint the techspec must honour.**
`metadata.packages_distributions()` costs roughly 145 ms per call in this venv and is not
memoized. `_resolve_import_name` already calls it once per query, and `_build_store_for` calls
that immediately before `get_or_build_store`. A reverse lookup added naively inside
`_installed_version` would pay a **second** 145 ms call on every cached query - the fast path this
whole cache exists to keep fast. The fix instead resolves both the import name and its claiming
distributions from **one** call, threaded through the existing call chain; net new
`packages_distributions()` calls across the fix is zero. Memoizing the import-to-distribution map
across the life of `venvaxi serve` was considered and rejected: the server is long-lived, so a
cached map would go stale against a mid-session install - reintroducing the exact staleness class
this issue is about, one layer up.

**`specs/mcp/tools.md` is deliberately left unamended - no text change.** Its Cache summary section
already states the `builds` table is "field for field the same shape `venvaxi cache` reports, read
the same way" and explicitly defers field meaning: "See `venvaxi cache` for what each field means."
That reference-not-restate wording (`ICM/_config/reference-standard-spec.md`, "SHOULD NOT duplicate
a behaviour spec into an interface spec - link to it") already inherits `cache.md`'s amended
`version` definition with no edit needed here. This is also true at the code level, checked rather
than assumed: `_mcp.py`'s `describe_binding_tool` and `_cli.py`'s `command_cache` both call the
same `read_cache_state()` and render `asdict(build)` verbatim (`src/venvaxi/_mcp.py:203,230-235`;
`src/venvaxi/_cli.py:533,563-569`) - neither surface transforms `version` itself, so the fix in
`_cache.py`/`_introspect.py`/`_store.py` reaches both without a line of MCP- or CLI-specific code
changing. `specs/mcp/tools.md` is therefore named in neither `specs:` nor `authors:`: this plan
writes no text there and brings no code into conformance with it that was not already conformant.

Out of scope, stated so the boundary is not assumed: a sentinel that fails closed for
`(no distribution)` (decision 3, declined above); memoizing `packages_distributions()` across a
`serve` session (declined above, its own staleness class); any change to the `package_builds` table
schema - `version` is already a free-form `TEXT` column, so no migration is needed beyond the
`SCHEMA_VERSION` bump's usual drop-and-rebuild; any change to how `show <package>`'s own
installed-version comparison works - that is a direct `metadata.version()` read on the distribution
name the caller gave, untouched by this fix, per `specs/commands/cache.md`'s existing
"Installed-version comparison" Out of scope entry.

## Implements

`specs/behaviors/cache-refresh.md` - `## Details` → `### Validity` item 2 is reworded to resolve
the version from the distribution(s) claiming the import name rather than from the import name
itself, cross-referenced to a new `### Version resolution` subsection. That subsection states the
three resolution cases (single distribution, multi-distribution composite, no distribution) as
`If <trigger>, then` criteria, per the edge-case enumeration rule in
`ICM/_config/reference-standard-spec.md`. `### When a rebuild is needed` gains one paragraph
distinguishing the new `(no distribution)`-inapplicable case from the existing editable-install
blind-spot case, per issue #89's explicit note that conflating the two is the mistake to avoid.

`specs/commands/cache.md` - `## Outputs`, the `builds` row `version` field description, is
reworded to cover the composite and `(no distribution)` shapes, linked to
`cache-refresh.md#version-resolution` rather than restating it.

Both amended specs are in `specs:`, not `authors:`: this plan amends both files **and** brings
`src/venvaxi/_introspect.py`, `src/venvaxi/_cache.py` and `src/venvaxi/_store.py` into conformance
with the amended text - per `plans/README.md`, "if the same plan writes a spec *and* implements it,
that is `specs:` - the code conformance is the stronger claim and subsumes the authorship."

## Approach

1. Open this plan at `status: planned`; stage 02 flips it to `in-progress`.
2. `src/venvaxi/_introspect.py` - add `resolve_import_and_distributions(name: str) -> tuple[str,
   tuple[str, ...]]`, holding the existing `_resolve_import_name` matching logic plus the reverse
   lookup off the same `mapping = metadata.packages_distributions()` call. `_resolve_import_name`
   becomes a one-line delegate returning element 0, so its four call sites
   (`_introspect.py:790, 825, 1082, 1232`) stay untouched. `_build_store_for` (`:794`) calls the
   combined function once and threads the distributions tuple into `_cache.get_or_build_store`.
3. `src/venvaxi/_cache.py` - `get_or_build_store` gains a `distributions: tuple[str, ...]`
   parameter, passed through from `_build_store_for`. `_installed_version` is rewritten to accept
   that tuple rather than a name string, and to implement the three resolution cases from
   `Implements` above: one distribution -> its bare `metadata.version()`; two or more -> the sorted
   `name=version` composite; zero -> the literal string `(no distribution)`. `get_or_build_store`
   calls it with the threaded tuple instead of re-deriving anything.
4. `src/venvaxi/_store.py` - bump `SCHEMA_VERSION` from `7` to `8`, and append a `NOTE: 8 - ...`
   entry to its docstring, following the existing `NOTE: 6 -`/`NOTE: 7 -` pattern, naming the
   version-resolution fix as the trigger and the class of row (`""`-recorded, permanently valid)
   it evicts.
5. Tests - `tests/test_cache.py:74`, `test_installed_version_unknown_package_returns_empty`,
   currently asserts `_installed_version("this-is-not-a-real-distribution") == ""` and pins exactly
   the behaviour this plan fixes. It is rewritten, not merely adapted to a new signature: the
   equivalent case under the new signature is an empty distributions tuple, and the correct
   assertion is `_installed_version(()) == "(no distribution)"`. `test_installed_version_known_package`
   is rewritten to call `_installed_version(("pytest",))`. New tests cover: the multi-distribution
   composite (a synthetic two-distribution tuple, sorted and comma-joined); a live check against
   this venv's own `jaraco` case if still reproducible at stage 02/03 time, else a mocked
   `packages_distributions()` return; `resolve_import_and_distributions` returning the same import
   name `_resolve_import_name` would have for every existing `_resolve_import_name` test case, plus
   the correct distributions tuple; a `packages_distributions()` call-count assertion around
   `_build_store_for` (or `show_module`/equivalent) proving exactly one call per resolution, per the
   performance constraint in Scope - `mock.patch(..., wraps=metadata.packages_distributions)` and
   assert `call_count == 1`, not reasoned about. `tests/test_store.py`'s existing schema-mismatch
   test (`:640`, asserting a stale `PRAGMA user_version` is dropped and rebuilt to the current
   `SCHEMA_VERSION`) is parametrized against the `SCHEMA_VERSION` constant rather than a literal
   number, so the `7 -> 8` bump is exercised by that existing test without a new one; a targeted
   regression test additionally reconstructs the pre-fix failure directly - a database at
   `PRAGMA user_version = 7` carrying a `package_builds` row recorded `version=""` - and confirms
   opening it through `SymbolStore` (which runs `_ensure_schema`) drops and rebuilds the table,
   proving the exact stale row the issue reports gets evicted.
6. Verify both surfaces (`venvaxi cache`, `describeBindingTool`'s cache summary) render the new
   `version` shapes unchanged in code - neither surface transforms the field, per Scope - and
   re-run this repo's own live reproduction (`dns`/`dnspython`) to confirm the fixed value.
7. Run the suite, coverage and hooks.

## Validation

- [x] If exactly one distribution claims a package's import name, then the store shall record that
      distribution's bare version string as the package's build version. —
      `tests/test_cache.py::test_installed_version_single_distribution_returns_bare_version`
- [x] If two or more distributions claim the same import name, then the store shall record a
      composite of every claiming distribution's full name and version, `name=version` pairs joined
      by a comma and sorted by distribution name, as the package's build version. —
      `tests/test_cache.py::test_installed_version_multiple_distributions_composite`
- [x] If no distribution claims an import name, then the store shall record the literal string
      `(no distribution)` as the package's build version. —
      `tests/test_cache.py::test_installed_version_no_distribution_returns_marker`
- [x] When a package's import name differs from its distribution name, the recorded build `version`
      `venvaxi cache` and `describeBindingTool`'s cache summary report shall equal that
      distribution's real installed version, never `""`. —
      `tests/test_cache.py::test_get_or_build_store_differing_import_name_records_real_version`
- [x] When the installed version of a distribution claiming a cached import name changes, the store
      shall treat the cached graph as invalid on the next query naming that import name. —
      `tests/test_cache.py::test_get_or_build_store_rebuilds_on_claiming_distribution_version_change`
- [x] While an import name claims no distribution, a query against a cached graph built to
      sufficient depth shall find the cache valid, never rebuilding on the strength of a version
      comparison alone. —
      `tests/test_cache.py::test_get_or_build_store_no_distribution_stays_valid_without_rebuild`
- [x] While resolving one package name for a store build, `venvaxi` shall call
      `metadata.packages_distributions()` exactly once, so that threading the resolved
      distributions adds no lookup to the path a cached query already pays for. —
      `tests/test_introspect.py::test_build_store_for_calls_packages_distributions_at_most_once`
- [x] When any of `show`, `find`, `tree`, `inspect`, `inherits` or `refreshPackageGraphTool`
      resolves a distribution or import name, the resolved import name shall be unchanged from its
      value before this change, for every case already covered by existing tests. —
      `tests/test_introspect.py::test_resolve_import_name_returns_import_name_key_unchanged`,
      `tests/test_introspect.py::test_resolve_import_name_fallback_preserves_case`
- [x] The store's schema version shall be `8`; a cache database recorded at schema version `7`
      shall be dropped and rebuilt on next open, regardless of its recorded build version. —
      `src/venvaxi/_store.py:29` (`SCHEMA_VERSION = 8`) +
      `tests/test_store.py::test_schema_version_7_empty_version_row_evicted_on_open`
- [x] `venvaxi cache` and `describeBindingTool`'s cache summary shall render the `version` field
      identically for the same underlying cache row - no surface-specific transformation of the
      value. — `src/venvaxi/_cli.py:533,563` and `src/venvaxi/_mcp.py:203,231` both render
      `asdict(build)` off the same `read_cache_state()`; re-run with
      `uv run python -c "from venvaxi._mcp import describe_binding_tool; print(describe_binding_tool())"`
      compared against `uv run venvaxi cache` - `builds` rows match field for field

## Risks / unknowns

- **A dotted-name command still calls `metadata.packages_distributions()` twice, and this plan
  does not change that.** Measured at the stage-02 gate: `show_module('dns.resolver')` calls it
  twice both before and after this change, because `_resolve_qualified_name` is a second,
  pre-existing caller on the qualified-name path that #89 does not touch. The fix is therefore
  performance-neutral, which is what it set out to be - but Validation criterion 7 originally read
  'at most once' for *any* query, which that measurement makes false. The criterion was reworded
  during the stage-02 gate (never at closeout, per
  `ICM/_config/reference-standard-validation.md`) to state what is true and what the instrumented
  test actually proves: exactly one call on the store-build path. The residual ~145 ms second
  lookup on dotted names is a pre-existing inefficiency owned by no issue; whether it is worth
  filing is a maintainer decision recorded here rather than absorbed silently.

- **The live `jaraco` multi-distribution reproduction is a fact about this venv's current
  dependency set, not a guarantee.** If a future dependency bump changes which packages install
  `jaraco.*`, the specific three-distribution example cited in Scope and in the spec text may stop
  being reproducible verbatim, though the composite mechanism itself does not depend on that exact
  package. Stage 02/03 should re-confirm the live example still holds, or substitute a synthetic
  multi-distribution case if it does not.
- **`metadata.version(dist_name)` raising for a `dist_name` sourced from
  `packages_distributions()` was measured at the stage 01 gate, not left assumed.** All 98
  distributions the mapping names in this venv resolve; none raises. Both read the same
  installed-distribution index, and the mapping is built from that metadata, so a miss would imply
  a corrupted or concurrently-modified environment. Decision: **no defensive `try`/`except`** -
  `ICM/_config/reference-standard-yagni.md` rules out error handling for scenarios that cannot
  occur, and letting it propagate surfaces a genuine environment fault rather than masking it as
  `(no distribution)`, which would misreport a real distribution as untracked. Recorded as a
  decision rather than an open risk.
- **Existing cache databases on disk carry rows recorded under schema `7` with `version=""`.**
  The `SCHEMA_VERSION` bump evicts them on next open, per the spec's own bump trigger, but this is
  the first time a bump has been relied on specifically to correct a previously-silent defect
  rather than a walk-time recording change; worth confirming at stage 03 that the eviction is
  observed live against this repo's own pre-existing cache, not only against a constructed test
  database.

## Notes

- **Why the version is resolved from the distribution, not the import name.** `_installed_version`
  pre-fix called `metadata.version(import_name)`, treating the caller's already-resolved import
  name as if it were a distribution name. For any package where the two differ (`dns`/`dnspython`,
  `yaml`/PyYAML, `bs4`/beautifulsoup4, `dateutil`/python-dateutil, `PIL`/pillow), that call raises
  `PackageNotFoundError`, which was caught and recorded as `""`. The comparison in `is_cache_valid`
  then read `"" == ""` on every subsequent query - both sides degrade to the same empty string, so
  the check compares equal forever and can never observe a real version change. It fails silently
  rather than loudly: nothing errors, nothing warns, the cache just never invalidates for that
  class of package. The fix resolves the version from the distribution(s)
  `metadata.packages_distributions()` says actually claim the import name, which is the only name
  `metadata.version()` can legitimately be called with.

- **Why multi-distribution import names record a sorted composite.** An import name can be claimed
  by more than one installed distribution (`jaraco` -> `jaraco.classes`, `jaraco.context`,
  `jaraco.functools` is the live case in this venv, confirmed at all three stage gates). Recording
  only one of them would leave the cache blind to a version change in whichever distribution was
  dropped from the record, so the fix records every claiming distribution's `name=version` pair,
  comma-joined and sorted by distribution name so the string is deterministic across runs. Any one
  of the claiming distributions moving changes the composite string and invalidates the cache.

- **Why `(no distribution)` fails open rather than closed.** A standard-library module (`json`)
  or a local module importable on `sys.path` claims no distribution -
  `packages_distributions()` maps nothing to it - and `_ensure_installed` deliberately allows both.
  This case is declared **inapplicable** to version-based invalidation, not broken: `SCHEMA_VERSION`
  and an explicit `--refresh` remain its invalidation path, exactly as already stated for the
  editable-install blind spot. Failing closed (rebuilding on every query when no distribution
  claims the name) was considered and declined - it would rebuild `json` on every
  `venvaxi show json --api`, defeating the cache for every stdlib and local-module query.

- **Why no defensive `try`/`except` around the per-distribution `metadata.version()` call.**
  Measured at the stage 01 gate: every one of the 98 distributions `packages_distributions()`
  names in this venv resolves through `metadata.version()` with zero `PackageNotFoundError`s. Both
  functions read the same installed-distribution index, and the mapping is built from that same
  metadata, so a name appearing in it is by construction one whose metadata was just read - a miss
  would mean a corrupted or concurrently-modified environment, not an expected case.
  `ICM/_config/reference-standard-yagni.md` rules out handling for scenarios that cannot occur, and
  masking a real miss as `(no distribution)` would misreport a real distribution as untracked -
  the exact silent-wrong-value class issue #89 exists to remove.

- **Why `SCHEMA_VERSION` had to move `7 -> 8`.** Rows already recorded under schema 7 with
  `version=""` stay valid forever under the old comparison even after the code fix lands - nothing
  about opening an existing cache re-evaluates a comparison that already always returned
  `"" == ""`. The bump forces every such row to be dropped and rebuilt once, so the fix reaches
  caches that already exist, not only caches built fresh after upgrading. The spec's own bump
  trigger - a change to what a walk *records* - fires here regardless of the `package_builds`
  table's shape being unchanged.

- **The criterion-7 rewording at the stage-02 gate.** The original text claimed
  `metadata.packages_distributions()` is called at most once for *any* query. Measured directly:
  a dotted-name command (`show_module('dns.resolver')`) calls it twice, both before and after this
  change, because `_resolve_qualified_name` is a second, pre-existing caller on the dotted-name
  path this plan does not touch. Ticking the criterion unchanged would have ticked a false
  statement about the shipped behaviour. It was reworded during the stage-02 gate - never at
  closeout, per `ICM/_config/reference-standard-validation.md` - to state what the instrumented
  test actually proves: exactly one call on the store-build path (`_build_store_for`), which is
  the path the performance constraint is about.

- **Why `specs/mcp/tools.md` is in neither `specs:` nor `authors:`.** Verified at code level, not
  assumed: `_cli.py`'s `command_cache` (`:533,563`) and `_mcp.py`'s `describe_binding_tool`
  (`:203,231`) both call the same `read_cache_state()` and render `asdict(build)` verbatim - neither
  surface transforms `version` itself. `specs/mcp/tools.md`'s Cache summary section already defers
  field meaning to `venvaxi cache` ("See `venvaxi cache` for what each field means"), so no MCP
  code had to move and no spec text needed amending for the fix to reach that surface.

- **The performance design: threading resolved distributions rather than memoizing
  `packages_distributions()`.** `metadata.packages_distributions()` costs roughly 145ms per call in
  this venv and is not memoized anywhere in the codebase. Memoizing it across the life of a
  `venvaxi serve` session was considered and rejected: the server is long-lived, so a cached map
  would go stale against a mid-session package install - reintroducing the exact staleness class
  this issue removes, one layer up. Instead, `resolve_import_and_distributions` resolves both the
  import name and its claiming distributions from **one** call, threaded through
  `_build_store_for` -> `get_or_build_store` -> `_installed_version`; net new
  `packages_distributions()` calls across the fix is zero, confirmed by an instrumented call-count
  test and an in-process warm-query timing comparison (pre-fix 0.2794s mean vs post-fix 0.2801s
  mean, within run-to-run noise).

## Follow-ups

- Issue [#101](https://github.com/andyrids/venv-axi/issues/101) - a dotted-name query
  (`show_module('dns.resolver')` and equivalents) resolves the same import name twice, paying
  `metadata.packages_distributions()` (~145ms) on both the `_resolve_qualified_name` path and the
  `_build_store_for` path. Filed from this plan's stage-02 gate, where the double call was measured
  while verifying Validation criterion 7. Pre-existing - both call sites predate this plan and
  neither is touched by it - and out of scope here: this plan's performance constraint was that the
  fix add no *new* call, which it does not (confirmed by instrumented call-count test and diff
  review showing `_resolve_qualified_name` untouched), not that the pre-existing double call be
  eliminated.
