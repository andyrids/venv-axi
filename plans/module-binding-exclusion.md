---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/symbol-graph.md
  - specs/commands/show.md
  - specs/behaviors/cache-refresh.md
authors: []
issues: [130]
pr:
---

# Plan: Module binding exclusion

## Scope

`venvaxi show <pkg> --api` reports module objects as public-API symbols of kind `attribute`
([#130](https://github.com/andyrids/venv-axi/issues/130)). The walk's `inspect.ismodule` skip sits
inside the `__all__`-less, below-the-root branch of the re-export filter, so two routes bypass it:

1. **A root declaring no `__all__`.** Importing a submodule binds it on its parent, so the root's
   public attributes include every submodule anything has imported. The issue called this a code
   read; stage 01 reproduced it live. `show coverage --api` reports dozens of submodules
   (`annotate`, `bytecode`, `collector`, ...), and `detect_secrets`, `yaml`, `toolz` and
   `pymarkdown` do the same. The fixture root already exhibits it (`package::module`), which
   `tests/test_introspect.py::test_get_public_api_excludes_module_and_package_kind` pins on purpose.
2. **An `__all__` naming a submodule.** `show venvaxi --api` reports `exceptions`, and
   `show polars --api` reports `api`, `exceptions`, `plugins` and `selectors`.

A third shape rides on route 1. A root binding another package's module under a public name
(`adodbapi` binds `time`, `yaml` binds `io`) records that module as an `attribute` row as well.

Each such row breaks `specs/commands/show.md`, because a `count` below the bound is definitive, and
`specs/behaviors/symbol-graph.md` Node kinds, because a module is not an `attribute`. Under
`specs/README.md` Invariant 2 this is a bug, not debt.

Fix: skip a module-valued binding for every candidate in the walk, at every depth and whether or
not `__all__` is declared. This is the issue's resolution 1. The issue's two alternatives stay
rejected: filtering at read time leaves a dishonest node in the graph, and classifying the binding
as `module` produces two nodes for one module under two keying conventions.

Out of scope, each with where it went:

- **`from __future__ import annotations` surfacing as `annotations|attribute`.** Seen in
  `show coverage --api` while probing. It is a `__future__._Feature` instance, not a module, so
  this rule does not reach it and it is no kind mis-statement. Whether a compiler-directive binding
  is public API is a separate question. It becomes an issue at stage 04 closeout if it still
  reproduces.
- **The submodule walk itself.** `_walk_submodules` recording `pkg.sub` as a `module` node is
  correct, and it is what `tree` and `inspect pkg.sub` read. Nothing here changes it.
- **Re-export provenance for module bindings.** No `EXPORTS`/`IMPORTS_FROM` edge is written for a
  skipped module binding, and those edges are unread anyway (`symbol-graph.md` Out of scope).

## Implements

Both specs sit in **`specs:`**. Each was already binding before this plan and the code did not
conform to it:

- `specs/commands/show.md` already said "Submodules are the one exclusion" and already required
  honest kinds.
- `specs/behaviors/symbol-graph.md` Node kinds already ruled out reporting an object as a kind it
  is not.

Stage 01 sharpened both into explicit `If` criteria. In `show.md`, the muddled "depth exclusion
rather than a kind one" became an exclusion by what the object is, with three enumerated binding
routes. `symbol-graph.md` gains `### Module bindings`. It also amends `### Re-exported symbols`:
`__all__` is honoured for every listed name except a module, which is the one exception to "a
stated intent is not second-guessed". That subsection argues why the exception keeps the
declaration rather than discarding it.

`specs/behaviors/cache-refresh.md` is unamended but also sits in `specs:`. Its "Schema version
covers the builder" rule requires a bump whenever the content a walk records changes, and this
plan changes that content. Without a bump, an existing cache keeps serving the `attribute` rows
after upgrade, because neither the distribution version nor the depth has moved.

## Approach

1. In the walk's candidate loop, move the `inspect.ismodule(obj) -> continue` skip out of the
   `explicit_exports is None and depth > 0` branch so that it runs first, for every candidate. The
   re-export filter beneath it is unchanged.
2. In `test_get_public_api_excludes_module_and_package_kind`, add `module` back to the disjoint
   set and delete the pin and its NOTE.
3. Add a fixture shape for route 2, where a module's `__all__` lists a submodule, and pin it.
4. Pin the foreign-module shape: a root binding an outside module under a public name records no
   node for it.
5. Bump the store's schema version, per `cache-refresh.md`.
6. Confirm that `tree`, `inspect <dotted module>` and the `show_module` children tests are
   untouched.
7. (Re-entry from stage 03, F1.) Apply the same `ismodule` skip in the class-member walk, so a
   class holding a module records no member node for it. Add a fixture class holding a module and
   pin it. Narrow nothing: criterion 4 stands as worded.
8. (Re-entry from stage 03, F2.) No code change. Pin the declared absence: a private submodule
   exported under a public alias in `__all__` leaves no node under that name.

## Validation

- [x] If a package's `__all__` lists one of its own submodules, then `show --api` shall not
  report that name.
  — `tests/test_introspect.py::test_get_public_api_excludes_modules_listed_in_all`
- [x] If a package's root declares no `__all__` and binds one of its submodules as an attribute,
  then `show --api` shall not report that name.
  — `tests/test_introspect.py::test_get_public_api_excludes_module_and_package_kind`
- [x] If a package binds another package's module under a public name, then `show --api` shall
  not report that name.
  — `tests/test_introspect.py::test_get_public_api_excludes_modules_listed_in_all`
- [x] The walk shall record no node of kind `attribute` whose object is a module, at any depth.
  — `tests/test_introspect.py::test_walk_records_no_attribute_node_for_a_module`
- [x] When a public submodule is excluded from `show --api`, `tree` shall still report it as a
  `module` or `package` node, and `inspect` shall still answer it by its dotted module name.
  — `tests/test_introspect.py::test_get_public_api_excludes_modules_listed_in_all`;
  `uv run venvaxi inspect venvaxi.exceptions` gives `kind: module`
- [x] If a class holds a module as a public member, then the walk shall record no member node for
  it.
  — `tests/test_introspect.py::test_walk_records_no_member_node_for_a_module_on_a_class`
- [x] If a module's `__all__` lists a private submodule under a public alias, then that name shall
  be absent from the graph.
  — `tests/test_introspect.py::test_walk_leaves_a_private_alias_in_all_out_of_the_graph`
- [x] When `venvaxi show venvaxi --api` runs against this repository, it shall report `count: 1`
  and no `exceptions` row.
  — `uv run venvaxi show venvaxi --api --refresh` gives `count: 1`,
  `__version__` only
- [x] If a cache built before this change is opened, then the store shall rebuild it rather than
  serve its module-valued `attribute` rows.
  — `tests/test_store.py::test_schema_version_mismatch_rebuilds_tables` with
  `SCHEMA_VERSION = 11`

## Risks / unknowns

- **`inspect <pkg>::<submodule>` stops answering.** It currently resolves to the dishonest
  `attribute` node and will become not-found. The dotted spelling (`inspect pkg.sub`) is the
  correct one and still answers. Stage 03 should check that the not-found answer for the `::`
  spelling is the declared one in `specs/commands/inspect.md` and not a misleading class.
- **`find` result sets shrink.** A query matching a submodule name loses its `pkg::sub` attribute
  row and keeps the `pkg.sub` module row. This is the intended correction, but any test asserting
  on `find` counts over the fixture may move.

## Notes

- **Re-entry from stage 03 to stage 01 (2026-10-16).** The stage 03 spec-drift audit found three
  low-severity divergences.
  - F1: a module held as a class attribute was still recorded as `attribute`, failing criterion 4.
  - F2: `### Module bindings` and `show.md` overclaimed that every excluded submodule stays
    reachable through `tree` and `inspect`. That is false for a private submodule under a public
    alias and for a module only registered in `sys.modules`.
  - F3: `### Re-exported symbols` still opened with "turns on two things".

  The user chose to close F1 in code, and to declare F2 with a follow-up issue rather than give
  such aliases module-kind nodes. Recording one under its alias would reintroduce the two-keying
  case #130 resolution 3 rejected. The delta re-run:
  - Stage 01: both specs amended for F1, F2 and F3, and criterion 5 reworded to "public
    submodule".
  - Stage 02: the class-member skip, plus fixtures for F1 and F2.
  - Stage 03: re-verify.

- **Why fix the walk rather than the report.** #130 offered three resolutions:
  - (1) Lift the module skip so it runs for every candidate. Chosen.
  - (2) Filter module-named rows when `show --api` reads them. Rejected: it leaves a dishonest
    `attribute` node in the graph for `inspect` and `find` to serve.
  - (3) Classify a module binding as `module`. Rejected: it writes a second node for one module
    under a `::` key, beside the real dotted one.

  Only (1) fixes every surface that reads the graph at once.
- **The bug was wider than #130 reported.** The issue had observed only the `__all__` route; it
  called the root-without-`__all__` route a code read. Stage 01 reproduced that route live:
  `coverage` (dozens of submodules), `detect_secrets`, `yaml`, `toolz`, `pymarkdown`. It also
  found the foreign-module shape (`yaml`'s `io`, `adodbapi`'s `time`), which the issue did not
  name.
- **Four tests had pinned the bug**, not the one #130 named. Each carried a NOTE pointing at
  `plans/reexport-filter-contract.md` Risks / unknowns:
  - `test_get_public_api_excludes_module_and_package_kind`
  - `test_get_public_api_top_level_keeps_default_depth`
  - `test_show_module_returns_node_and_children`
  - `test_walk_module_visited_set_prevents_revisit`

  All four are restored to their un-narrowed assertions, and the NOTEs are removed.
- **Fixture placement.** The class-holding-a-module fixture lives in `subpkg/inner/__init__.py`
  because `package/constants.py` is pinned as attribute-only by two tests, one of them in
  `tests/test_mcp.py`. The private-alias fixture reuses `package._impl` instead of adding a
  module.
- **One schema bump for both stage 02 passes.** 11 was unreleased when the class-member skip
  joined it. Only a cache built on a development machine between the passes could hold a row the
  final walk does not write, so live checks used `--refresh`.
- **Evidence correction.** Stage 02's first pass cited `tests/test_cache.py` stale-schema tests
  for criterion 9. Those test the *status report*, so the ticked citation is the `tests/test_store.py`
  rebuild-on-open test. Bumps 7 and 8 had per-version eviction tests and 9-11 have none. Optional;
  not filed.
- **Verified on the user's pkgdx v0.4.0 toolchain and refreshed `uv.lock`.** These were
  uncommitted, and the work started from `develop` at `81487a5`. `develop` fast-forwarded to
  `f3e1f84` mid-run, and none of those 20 commits touched this plan's files. The upgrade's new
  PyMarkdown MD060 rule flagged the pre-existing Edge kinds table in `symbol-graph.md`. The
  realignment belongs in the user's upgrade commit, not this plan's.

## Follow-ups

- Issue [#142](https://github.com/andyrids/venv-axi/issues/142): a module the walk cannot reach by
  its own name (a private submodule under a public alias, or a module only registered in
  `sys.modules`) leaves an `__all__`-declared name absent from the graph. Declared in
  `specs/behaviors/symbol-graph.md` Out of scope.
- Issue [#143](https://github.com/andyrids/venv-axi/issues/143): `inspect pkg::sub` misses with
  only the generic hint. Removing the dishonest `attribute` node took away the answer that
  spelling used to get, and nothing points the caller to `pkg.sub`.
- Issue [#144](https://github.com/andyrids/venv-axi/issues/144): `from __future__ import
  annotations` reaches `show --api` as a public `annotations` attribute. It existed before this
  plan and was found during its stage 03. It is out of scope here, because the object is not a
  module.
