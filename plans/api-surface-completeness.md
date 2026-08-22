---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/show.md
  - specs/behaviors/symbol-graph.md
authors: []
issues: [82]
pr: 85
---

# Plan: api-surface-completeness

## Scope

`show --api` reports only `class` and `function` nodes, so every symbol a package exports as an
`attribute` is dropped after the walk has already recorded it. `show pytest --api` answers
`count: 77` against an 88-entry `__all__`, and `show fastmcp --api` answers `count: 5` against
six - both measured on `develop` at the head of this plan. The eleven hidden `pytest` exports
include `skip`, `fail`, `xfail`, `exit`, `mark`, `hookimpl` and `hookspec` (issue 82).

Two things are in scope, and the second is why the first is not a one-line change.

1. **The kind guard**, at the query layer only. The walk is already correct: `_walk_module` takes
   `__all__` verbatim, so the nodes exist and every other surface can see them.
2. **The docstring rule.** `_doc_of` blanks an `attribute`'s docstring whenever it equals its
   type's. That correctly stops `version_tuple :: tuple` reporting *Built-in immutable sequence*,
   and it also blanks every package-defined singleton - `pytest.fail` reports `(no docstring)`
   today while its real docstring sits in the class the package defined for it. Widening the
   filter puts that wart on the command that most needs it.

Out of scope: bounding the row count, which is issue 67 and the next unit; anything owned by
issues 68, 49 or 50. Also out of scope: promoting a callable `attribute` to `function` - kinds
stay honest, and the spec now says so.

## Implements

`specs/commands/show.md`, Outputs (API mode) - the command reports every public top-level symbol
the package declares, of any node kind except `module` and `package`, with kinds reported
honestly. The submodule exclusion arrived by re-entry mid-run; see Notes.

`specs/behaviors/symbol-graph.md`, Recorded docstrings - a new Details section declaring the
own-docstring rule, the attribute/type rule, and the standard-library exclusion that separates a
package-defined singleton from a stdlib construct.

Both sit in `specs:` rather than `authors:` because this plan changes code until it conforms.
`symbol-graph.md` also gains a statement that callability decides the signature and never the kind,
which is already true in code from issue 66; authorship there is subsumed by the conformance claim
on the same file, per `plans/README.md`.

## Approach

1. Open this plan at `status: planned`; stage 02 flips it to `in-progress`.
2. Invert the kind guard in `get_public_api` (`src/venvaxi/_introspect.py`): exclude
   `NodeKind.MODULE` and `NodeKind.PACKAGE`, emit every other kind, and correct the stale
   "functions & classes" docstring above it. This step originally read "drop the guard"; see
   Notes for why that was wrong and how it was caught.
3. Add a standard-library predicate and apply it in `_doc_of`. An `attribute` whose docstring is
   its own keeps it unchanged; one whose docstring is its type's is blanked **only** when that
   type is defined in the standard library.
4. Bump `SCHEMA_VERSION` in `src/venvaxi/_store.py` from 6 to 7.
5. Extend the fixture at `tests/resources/package/` with the two shapes the discriminator has to
   separate, and add unit tests plus a conformance-tier case.
6. Verify both surfaces, run the suite, coverage and hooks.

**The discriminator, settled here rather than left to stage 02.** Issue 82 leaves this unresolved
and records two candidates that fail. Both fail because they key on the *package*:
`type(obj).__module__ == "builtins"` is too narrow, leaking `NewType`'s docstring onto type
aliases whose types live in `typing` and `types`; a package-root allowlist is too strict, blanking
`pytest.fail`, whose type `_Fail` lives in `_pytest.outcomes` and not under `pytest.`.

Keying on the **standard library** rather than the package separates every documented case.
`sys.stdlib_module_names` is a frozenset available since 3.10, and the project requires 3.11, so
the test is a set membership on the top-level component of `type(obj).__module__`. Verified
against all four cases before this plan was written:

| Symbol | Type's module | In stdlib | Wanted | Rule gives |
| ------ | ------------- | --------- | ------ | ---------- |
| `pytest.fail` | `_pytest.outcomes` | no | keep | keep |
| `pytest.version_tuple` | `builtins` | yes | blank | blank |
| `fastmcp.settings` | `fastmcp.settings` | no | keep | keep |
| a `NewType` alias | `typing` | yes | blank | blank |

**Why `SCHEMA_VERSION` must move.** `_doc_of` runs at walk time and its result is frozen into the
store, so changing it leaves every existing cache serving the old value.
`specs/behaviors/cache-refresh.md` requires the version be bumped "whenever the *content* a walk
records changes, not only when a table's columns change", precisely because neither the
distribution version nor the depth moves for a change like this one. The cost is real and is
accepted: every cache on every machine is dropped and rebuilt on first query after upgrade. The
alternative is users keeping the wrong docstrings indefinitely with no signal, which is the silent
failure that rule exists to prevent.

## Validation

- [x] When `show <package> --api` is invoked for a package whose `__all__` declares a symbol that
  is neither a class nor a function, the `show` command shall include that symbol in the reported
  surface. — `tests/test_introspect.py::test_get_public_api_reports_non_callable_export_as_attribute`
  and `::test_get_public_api_widens_beyond_class_function`; live venv,
  `uv run venvaxi show fastmcp --api` -> `count: 6` matching `__all__`, including
  `settings|attribute` (was `count: 5`)
- [x] When `show <package> --api` reports a symbol that is an exported instance, the `show`
  command shall report its kind as `attribute` and shall not report it as `function`. —
  `tests/test_introspect.py::test_get_public_api_reports_non_callable_export_as_attribute`; live
  venv, `settings` and `pytest::fail` both report `attribute`, the latter carrying a full
  signature
- [x] Where an `attribute`'s type is defined outside the standard library and the attribute
  defines no docstring of its own, the graph shall record that type's docstring. —
  `tests/test_introspect.py::test_doc_of_package_defined_singleton_keeps_type_docstring` and
  `::test_doc_of_attribute_keeps_docstring_for_non_stdlib_type`; live venv,
  `uv run venvaxi inspect "pytest::fail" --docstring` -> the real docstring (was
  `(no docstring)`), and `show fastmcp --api` -> `settings ... FastMCP settings.`
- [x] Where an `attribute`'s type is defined in the standard library and the attribute defines no
  docstring of its own, the graph shall record no docstring, and the reporting command shall emit
  `(no docstring)`. — `tests/test_introspect.py::test_doc_of_stdlib_typed_attribute_blanks_docstring`
  and `::test_doc_of_attribute_blanks_docstring_for_stdlib_type`; live venv,
  `show pytest --api` -> `__version__` and `version_tuple` both `(no docstring)`
- [x] When a package cached before this change is queried after it, the store shall rebuild the
  graph rather than serve the previously recorded docstrings, without the caller passing
  `--refresh`. — a store populated and stamped back to `PRAGMA user_version = 6`, then reopened by
  the current code: node `None`, build `None`, `user_version` restamped to 7, so
  `_cache.is_cache_valid` returns False and the package rebuilds unprompted
  (`ICM/process-plan/stages/03-verification/output/api-surface-completeness-test.md`, criterion 5);
  `tests/test_store.py::test_schema_version_mismatch_rebuilds_tables` covers the mechanism
- [x] When `showPackageApiTool` is called, the tool shall report the same widened surface as
  `show <package> --api`, per the parity principle in `specs/mcp/tools.md`. —
  `tests/test_mcp.py::test_show_package_api_tool_matches_cli_widened_surface`; live parity check,
  CLI 6 symbols against tool `count: 6`, every name present, no `module` row

## Risks / unknowns

- **Every cache is invalidated.** The `SCHEMA_VERSION` bump drops and rebuilds every cached graph
  on first query after upgrade. For a large venv that is a slow first call, once. Accepted above;
  called out here because it is the most user-visible consequence of this unit and it is invisible
  in the diff.
- **The payload grows.** Widening the row set makes `show --api --docstring` larger for the nine
  affected packages, and issue 67's payloads are already unbounded. The conformance tier's
  `xfail(strict=True)` marks absorb this, but issue 67 must choose its bound against the
  post-widening row count rather than today's.
- **`sys.stdlib_module_names` is a name list, not an import check.** A third-party package
  installed under a name that collides with a stdlib top-level module would be misclassified as
  stdlib. This is already pathological for other reasons and no such case is known in the walked
  set; recorded rather than guarded.
- **Low-value rows.** The widened surface admits `__version__` and `version_tuple` in some
  packages, at roughly 30 characters each. Cheap against a confidently-wrong answer, and the issue
  takes the same position.

## Notes

**Stage 02 re-entered stage 01 once**, per the re-entry rule in `ICM/process-plan/CONTEXT.md`.

Stage 01 declared the widened surface as "every public top-level symbol the package declares, of
any node kind", and the techspec turned that into "delete the guard so every child of the resolved
module is emitted". Both were wrong in the same place. `_walk_submodules` records submodule nodes
under the same `CONTAINS` edge kind that `_record_symbol` uses for symbols, so `get_children`
returns both and an unguarded loop reports a package's submodules as part of its public API.
Measured: `show fastmcp --api` reached `count: 22`, sixteen of them `module` rows, against an
`__all__` of six.

That contradicts this command's own Out of scope - "nested module structure is `tree`'s job" - so
the fix was not a smaller filter but the inverse one: exclude `module` and `package`, report every
other kind. `specs/commands/show.md` now says so explicitly rather than leaving 'symbol' to be
inferred, and the techspec's directive was amended with the reason.

Worth recording for the remaining 0.4.0 units: `pytest` hid this. Its only non-underscore
submodule is `__main__`, which the leading-underscore check already drops, so `show pytest --api`
returned exactly `88` - matching `__all__` - and looked like proof the change was correct. The
issue's own worked example was the one package that could not show the defect.

**The discriminator, and why it reads backwards.** Issue 82 left this open with two candidates it
had already disproved, both keyed on the exporting package. Keying on the **standard library**
instead separates every documented case, and the reason is that a package's singleton is usually
an instance of a *private* class outside the package's own import root - `pytest.fail` is an
instance of `_pytest.outcomes._Fail`, which no rule anchored to `pytest.` can see. The stdlib is
the thing worth excluding, because a stdlib type documents a construct rather than the exported
value. `_is_stdlib_type` carries this in a NOTE naming both rejected alternatives, because the
obvious simplification is back to one of them.

A missing or empty `__module__` counts as not-stdlib, so the docstring is kept. That direction is
deliberate: a wrongly-kept docstring is visible and correctable, a wrongly-blanked one looks like
a definitive `(no docstring)`.

**Two behaviours, one unit, and why they belong together.** The kind guard is a query-layer filter;
the docstring rule is walk-time content frozen into the store. They were kept in one unit because
widening the filter is what puts the second defect on the surface that most needs it - `pytest.fail`
had reported `(no docstring)` on `inspect` since long before this change, unnoticed.

**No user-facing documentation needed changing**, which was checked rather than assumed.
`src/venvaxi/SKILL.md` describes `--api` as "Public top-level API symbols" and `README.md` as
"Public API symbols" - both kind-agnostic, and both more accurate after this change than before.
The skill's `doc: (no docstring)` entry states what the marker means, which is unchanged; what
changed is which symbols report it. Nothing in the skill claimed a class/function-only surface, so
there was no stale claim to correct.

## Follow-ups

- **Issue [#67](https://github.com/andyrids/venv-axi/issues/67)** - the next unit. It must choose
  its row bound against the post-widening count, not the figures in its own report, and it starts
  from a suite that fails until the conformance tier's three `xfail(strict=True)` marks are
  removed. Measured here: `show fastmcp --api --docstring` is 7,229 bytes after this change, so
  the widening cost is one attribute row, not a step change.
- **The conformance case restates the filter it guards.**
  `tests/test_conformance.py::test_public_api_surface_not_narrowed_by_kind` cross-checks
  `get_public_api` against `show_module`'s non-module children. Not tautological - the two reach
  the store by different paths - but an edit made to the implementation and to the test's own
  filter expression together would pass. Owned by no issue; recorded so a later reader knows the
  guard's limit.
- **`sys.stdlib_module_names` is a name list, not an import check.** A distribution installed
  under a stdlib top-level name would be misclassified and have its type docstring blanked. No
  such case exists in the walked set and it is not guarded. Owned by no issue.
- **The schema bump costs every user one rebuild.** Nothing tracks how long that takes on a large
  venv, and issue 49 (cache state inspection, a later unit in this milestone) is where that would
  become observable. Tracked as: issue 49's own scope.
