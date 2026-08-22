---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/find.md
authors: []
issues: [79]
pr: 83
---

# Plan: fallback-doc-search

## Scope

Bring the `LIKE` fallback search path into conformance with `specs/commands/find.md`, which
declares the search surface as name **and docstring text**. `src/venvaxi/search_like.sql` matched
`name` and `qualified_name` only, so on a SQLite build without FTS5 a query that would match on
docstring text alone returned `count: 0` (issue 79).

**Eligibility for express-change.** All three conditions in `ICM/express-change/CONTEXT.md` hold.

1. **No spec change is required.** `specs/commands/find.md` already declares the contract on the
   default branch, twice - "The cached symbol graph, searched over name and docstring text"
   (Data requirements) and "the query is matched against name and docstring text as supplied"
   (Out of scope). The fallback serving a narrower surface is a code divergence from a spec that
   is already correct - Invariant 2 in `specs/README.md` - not a behaviour change needing a new
   declaration.
2. **One commit's worth**, with no new dependency and no new public surface: one SQL predicate,
   one parameter tuple, four tests.
3. **Every Validation criterion is evidenced within this run** - each is a store-level assertion
   runnable against the existing fixtures with `_fts_enabled` forced off.

Out of scope: any change to the FTS5 path (`search_fts.sql`), to the ordering contract, or to the
`logger.debug` level of the two fallback catch sites in `_store.py`. Issue 79 offers surfacing the
narrowing as an alternative resolution; it is not taken, because once both paths honour one
contract there is no narrowing left to report. Also out of scope: anything owned by issues 82, 67,
68, 49, 50 or 71, which are the remaining 0.4.0 units.

## Implements

`specs/commands/find.md`, Data requirements - the docstring half of the declared search surface,
on the fallback path only. The FTS5 path already conforms via `schema_fts5.sql`, which indexes
`qualified_name, name, doc`.

No part of the spec changes. This plan changes code until it matches, which is why
`specs/commands/find.md` sits in `specs:` and `authors:` is empty.

## Approach

1. Open this plan at `status: in-progress`.
2. Widen the predicate in `src/venvaxi/search_like.sql` to `OR doc LIKE ?`.
3. Add the matching positional parameter in `SymbolStore.search_symbols`
   (`src/venvaxi/_store.py`). The statement binds eight parameters positionally - three `LIKE`
   patterns, two package-filter values, two ordering values and the limit - so the new pattern
   goes third, before the package filter. An off-by-one here corrupts the ordering or the scope
   silently rather than raising, so the package-scope and limit criteria below exist to catch it.
4. Add a docstring-only regression test to `tests/test_store.py`: a node whose `name` and
   `qualified_name` contain no occurrence of the query and whose `doc` does. Confirm it fails
   against the unfixed SQL before it passes against the fixed SQL, and record both results.
5. Run the suite and coverage (`uv run coverage run -m pytest`, `uv run coverage report`) and the
   hooks (`uv run prek run --all-files`), capturing output verbatim.
6. Close out: tick each Validation box only where evidenced, with its citation, and add the
   `CHANGELOG.md` entry.

## Validation

- [x] While FTS5 is unavailable, when a query matches only a symbol's docstring text, the `find`
  command shall return that symbol. —
  `tests/test_store.py::test_search_symbols_docstring_only_match_like_fallback`; against the
  unfixed SQL the same test failed `assert [] == ['Widget']`
- [x] While FTS5 is unavailable, when a query matches only a symbol's docstring text, the `find`
  command shall restrict results to the named package where one is given. —
  `tests/test_store.py::test_search_symbols_docstring_only_match_filters_by_package_like_fallback`;
  against the unfixed SQL the same test failed `assert [] == ['a']`
- [x] While FTS5 is unavailable, when a query matches only a symbol's docstring text, the `find`
  command shall return no more results than the active limit. —
  `tests/test_store.py::test_search_symbols_docstring_only_match_respects_limit_like_fallback`;
  against the unfixed SQL the same test failed `assert 0 == 2`
- [x] While FTS5 is available, the `find` command shall return the same results for a
  docstring-only query as it did before this change. —
  `tests/test_store.py::test_search_symbols_docstring_only_match_fts`, which passed against both
  the unfixed and the fixed SQL; whole suite `uv run coverage run -m pytest` -> `370 passed`,
  `uv run coverage report` -> `TOTAL 1142 20 98%`

## Risks / unknowns

- **Positional binding.** The eight `?` placeholders in `search_like.sql` are positional and
  untyped; a misplaced parameter yields wrong ordering or a silently dropped package scope rather
  than an error. Criteria two and three exist to catch exactly that, and both were confirmed to
  fail against the unfixed statement before passing against the fixed one.
- **Fallback coverage in CI.** FTS5 is compiled into CPython's bundled SQLite on every platform
  the suite runs on, so the fallback is reachable in tests only by forcing `_fts_enabled = False`.
  A future change to this path is unguarded unless tests keep doing so. This is a narrower
  instance of issue 71, filed under Follow-ups.
- **An unindexed `doc` scan.** The fallback already scanned for `name` and `qualified_name`; this
  widens the scanned text to the largest column in the table. The fallback is the degraded path on
  a build without FTS5, so a scan cost there is accepted rather than optimised. No benchmark was
  taken - the criteria above assert correctness, not latency.

## Notes

**Why resolution 1, not resolution 2.** Issue 79 offers a choice: widen the predicate, or declare
the narrowing in `specs/commands/find.md` and surface it to the caller. Resolution 1 is taken
because the spec states one contract and a fallback quietly serving a different one is precisely
the divergence Invariant 2 rules out. Resolution 2 would have made this a spec change, which would
have failed express eligibility and routed the work to `/icm:specify` instead.

**Why the existing test did not catch it.** `test_search_symbols_like_fallback_when_fts_disabled`
queries `"Dog"` against a node *named* `Dog` whose `doc` is the fixture factory's default `""`, so
it is a pure name match that passes identically with or without `doc` in the predicate. It was
left unmodified - it still covers name matching on the fallback - and four new tests were added
beside it rather than reworking it.

**Scale of what was hidden.** Measured against the 0.3.2 store (100,455 nodes, 63,671 with
non-empty `doc`), ten docstring-only terms returned 8,538 distinct symbols through FTS5 and zero
through the fallback. The ceiling on the exposure is 63% of nodes - every node carrying `doc` text
the predicate never looked at.

**Why it read as definitive rather than incomplete.** Both fallback catch sites in `_store.py` log
at `logger.debug` and neither reaches output, so nothing distinguished "no symbol mentions this"
from "docstrings were not searched". Under the issue-69 contract a `count` below the limit is a
definitive answer carrying no hint, so the fallback manufactured a confidently-wrong empty result.
That contract is what made this worth fixing ahead of the rest of the 0.4.0 milestone.

**Evidence protocol.** The before-fix failure was captured during implementation, then
independently re-run at the review gate by reverting only `search_like.sql` and `_store.py` and
re-running the four tests: 3 failed, 1 passed, with the FTS5 test the one that passed. The working
tree was restored from a copy taken beforehand, and `git diff --stat` confirmed the restoration.

**Closeout ordering, learned here.** `status: done` and `pr:` are set together in the last commit
before merge, per `plans/README.md` - which is after the PR exists. This run first flipped to
`done` at the review gate, before any commit, and the closeout gate hook rejected it: a plan
claiming to be frozen while naming no PR is an incomplete record. The gate is what a plan looks
like at acceptance (`in-progress`, boxes ticked, evidence captured); the freeze is a separate
commit afterwards. Worth knowing for the six remaining 0.4.0 units, which take the same route.

## Follow-ups

- **Issue [#71](https://github.com/andyrids/venv-axi/issues/71)** - every introspection test walks
  a synthetic fixture, so no real-dependency pathology can fail the suite. This plan is a narrow
  instance: the fallback path is reachable only by forcing `_fts_enabled = False`, and a whole
  search dimension went missing without a test noticing. Owned by no current plan; it is the next
  unit of the 0.4.0 milestone.
- **Tracked as a gate question** - the `CHANGELOG.md` entry was filed under `## [Unreleased]`,
  which this file has not used before; prior releases created a dated version heading directly.
  Six further 0.4.0 units follow, so dating a `## [0.4.0]` heading now would stamp it with the
  first unit's date. Raised at the review gate rather than settled silently.
