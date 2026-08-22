---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/inspect.md
  - specs/commands/find.md
  - specs/behaviors/cache-refresh.md
authors:
  - specs/behaviors/output-contract.md
issues: [66, 69]
pr: 70
---

# Plan: definitive-answers

## Scope

Two fields that understate what the AXI knows, one principle - definitive answers - applied to
a scalar and a collection:

- `inspect "polars::col"` reports `signature:` as empty
  ([#66](https://github.com/andyrids/venv-axi/issues/66)). The issue blames a swallowed
  `TypeError`; the verified cause is the kind guard in the graph walk, which computes a
  signature only for class and function kinds. `pl.col` is a module-level callable instance,
  classified as an attribute, so the signature helper - which already handles failure
  correctly - is never called at all.
- `find array --package numpy` reports `count: 20` with no signal that 20 is the `--limit`,
  not the total ([#69](https://github.com/andyrids/venv-axi/issues/69)). A capped count reads
  as definitive when it means 'at least'.

In scope: signatures for every callable symbol whatever its kind, `""` declared as the
non-callable answer, and a bounded-results hint on both `find` surfaces at `count == limit`.
Out of scope: any change to symbol classification - promoting callable instances to function
kind would silently widen `show --api`'s class/function filter; and a `limit` for `show --api`
([#67](https://github.com/andyrids/venv-axi/issues/67)), deferred so the collection-bounds
rule stays in `find.md` until both commands can conform.

## Implements

- `specs/commands/inspect.md` - the signature rule now binds on every callable symbol
  whatever its `kind`; `""` is declared as the non-callable answer (no third marker); the
  recorded `(signature unavailable)` marker is declared a deliberate exception to the
  applied-at-emission rule.
- `specs/commands/find.md` - the new Bounded results rules: a hint when the returned count
  equals the active limit, surface-spelled; no hint below the limit; the rule deliberately
  kept out of `output-contract.md` until #67.
- `specs/behaviors/output-contract.md` (authored only, no behaviour change) - the
  applied-at-emission rule now names the recorded signature marker as its declared exception,
  so the drift audit does not read `inspect.md` as violating it.

## Approach

- In the graph walk's symbol upsert, compute the signature when the object is callable, not
  only for class and function kinds - the existing signature helper already returns
  `(signature unavailable)` on failure and needs no change.
- Append the bounded-results hint in the CLI `find` command and the MCP find tool when the
  row count equals the active limit, alongside each surface's existing next-step hint,
  through the existing footer helpers - extend the hint list, no new mechanism.
- Verification: a fixture attribute that is callable with a raising `__signature__`
  (asserting the marker), a well-behaved callable instance (asserting a real signature), a
  non-callable attribute (asserting `""`), and find tests at, above and below the limit on
  both surfaces.

## Validation

- [x] When a symbol is a callable instance of a class defining `__call__`, the `inspect`
      command shall report the signature derived from live introspection. —
      `tests/test_introspect.py::test_callable_instance_records_call_signature`
- [x] If `inspect.signature` fails on a callable symbol classified as an attribute, then the
      `inspect` command shall report `(signature unavailable)`. —
      `tests/test_introspect.py::test_callable_instance_failing_signature_records_marker`
- [x] When a symbol is not callable, the `inspect` command shall report `signature` as the
      empty string. —
      `tests/test_introspect.py::test_non_callable_attribute_records_empty_signature`
- [x] The `show --api` listing shall continue to report class and function kinds only. —
      `tests/test_introspect.py::test_get_public_api_keeps_class_function_filter`
- [x] When the `find` command returns exactly the active `--limit` rows, it shall append a
      hint stating that further matches may exist and naming `--limit`. —
      `tests/test_cli.py::test_command_find_at_limit_appends_bounded_hint`
- [x] When `findSymbolTool` returns exactly `limit` rows, it shall append a hint stating
      that further matches may exist and naming the `limit` parameter. —
      `tests/test_mcp.py::test_find_symbol_tool_at_limit_appends_bounded_hint`
- [x] When the `find` command returns fewer rows than the active limit, it shall emit no
      bounded-results hint, on either surface. —
      `tests/test_cli.py::test_command_find_below_limit_omits_bounded_hint` and
      `tests/test_mcp.py::test_find_symbol_tool_below_limit_omits_bounded_hint`
- [x] If a cache built by an earlier schema version is opened, then the store shall drop and
      rebuild it, so a graph recorded before this change cannot keep serving `""` for
      callable attributes. —
      `tests/test_store.py::test_schema_version_mismatch_rebuilds_tables` at
      `SCHEMA_VERSION = 6` (`src/venvaxi/_store.py`)

## Risks / unknowns

- Cached graphs built by an earlier venvaxi record `""` for callable attributes; package
  version and build depth cannot catch the change. `specs/behaviors/cache-refresh.md`
  already mandates the mechanism - the store schema version MUST be bumped when what a walk
  records changes - so the risk is missing the bump, not the staleness itself. (Stage 01
  missed it; found and corrected at verification - see Notes.)
- Computing signatures for every callable runs `inspect.signature` over arbitrary instances
  at build time. The helper's broad catch contains any `Exception`, but a `__signature__`
  descriptor raising a `BaseException` would escape the walk - the same class of leak
  `plans/import-crash-containment.md` closes at import boundaries. Stage 02 should decide
  whether that helper joins the sweep; stage 01 of that plan scoped it to import boundaries.
- Build cost grows with the number of callable attributes walked; expected negligible, worth
  a glance at the benchmark test if stage 03 notices drag.

## Notes

- 2026-08-21 - re-entry to stage 02, raised by stage 03's spec-conformance pass. The
  signature change alters what a walk records, and `specs/behaviors/cache-refresh.md`
  ('Schema version covers the builder, not just the shape') MUST-mandates a schema bump for
  exactly that - stage 01 missed it, planning a release-notes `--refresh` caveat instead.
  Delta: `SCHEMA_VERSION` 5 -> 6, `cache-refresh.md` added to `specs:`, criterion 8 added,
  the Risks entry corrected, and the CHANGELOG bullet reworded from 'pass `--refresh` once'
  to the automatic rebuild. The user-facing upgrade caveat is thereby eliminated, not
  documented.
- Design decision: callability decides the signature, kind decides everything else.
  `_classify` is untouched - promoting callable instances to `FUNCTION` would silently widen
  `get_public_api`'s class/function filter (criterion 4 pins it) - and the
  `home_qualified_name` kind guard is untouched for the same reason.
- Design decision: `""` stays the non-callable answer; no third marker. A marker would
  change every attribute row in every module listing for no gain, and callability already
  distinguishes 'not callable' from '(signature unavailable)'.
- Design decision: hint order on both surfaces is next-step first (`inspect` /
  `getSymbolTool`), bounded-results qualifier second - the primary action leads.
- Gotcha: `inspect.signature` on an instance follows `type(obj).__call__` and reads
  `obj.__signature__` inside a try that catches only `AttributeError` - a raising
  `__signature__` descriptor (the `pl.col` shape) escapes as `TypeError`, which is exactly
  what `_signature_of`'s broad catch converts to the marker.
- The changelog entries live under `[0.3.0rc2]` in `CHANGELOG.md`, written by
  `plans/withdraw-0-3-0.md`'s release-record edit - this run is part of that release.

## Follow-ups

- Issue [#67](https://github.com/andyrids/venv-axi/issues/67) - a row cap for `show --api`,
  deferred to 0.4.0. The bounded-results rule stays local to `specs/commands/find.md` until
  it lands; lifting the rule into `output-contract.md` is part of that work, not this plan.
- Needs an issue (left for the user to open): `_signature_of` still catches `Exception`
  only, so a `__signature__` descriptor raising a `BaseException` aborts the walk - the
  entry backstops from `plans/import-crash-containment.md` contain it (exit 2, store
  released), but one exotic symbol still costs the whole graph. Out of scope here: the
  import-boundary spec governs imports, and widening `_signature_of` deserves its own
  decision.
