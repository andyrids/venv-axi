---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: planned
depends: []
specs: []
authors:
  - specs/commands/find.md
issues: [122]
pr:
---

# Plan: Find search-surface routing contract

## Scope

Declare which search surface answers a query and what that costs the caller.
[#122](https://github.com/andyrids/venv-axi/issues/122) resolution 2 -
`specs/commands/find.md` says a full-text backend *may* interpose a relevance score between
ordering keys 4 and 5, and stops there. It never says that an entire class of query can never
reach that backend, so the relevance gap is not merely unspecified for those queries but reliably
absent. A caller reading the spec today cannot tell the two apart.

The behaviour is already correct and already deterministic; nothing under `src/` changes. What is
missing is the declaration, plus one test that keeps the new half of it honest.

Out of scope, with destinations:

- **The `:` leak** - `name:print` and `doc:json` reach the full-text index as *column filters*
  rather than as text, so `find "name:print"` returns rows carrying no such literal at exit `0`.
  That is a live divergence against `find.md`'s Literal matching rule, filed as
  [#134](https://github.com/andyrids/venv-axi/issues/134), and it is a defect to fix, not a routing
  rule to write down. The spec delta's trigger is **refusal by the index**, which excludes the leak
  by construction: `:` is accepted and misread, never rejected, so the trigger does not fire on it
  and the delta stays true whether or not #134 is fixed. `### Result ordering` names the boundary
  explicitly rather than leaving the next reader to rediscover `name:print`.
- **[#122](https://github.com/andyrids/venv-axi/issues/122) resolution 1** - quoting the query into
  a single FTS5 phrase so every query reaches the index. That changes the result *set*, needs its
  own plan and its own spec change, and would have to settle #134 first. Recorded in the spec's
  `## Out of scope` with its cost, not started here.
- **Changing any ordering key.** No key moves, and no key is added. This plan records what is.

## Implements

Nothing. This plan authors `specs/commands/find.md`, which is why it sits in `authors:` and not in
`specs:`. Listing it in `specs:` would make stage 03 verify a code conformance this plan never
delivers - the trap `plans/README.md` records the methodology walking into on first use - and
adding a regression test is not a code conformance either. The precedent is
[`plans/find-ordering-contract.md`](find-ordering-contract.md), which declared the ordering `find`
already implemented under the same field.

The amendment lands in three sections of `specs/commands/find.md`:

- `### Result ordering` - three paragraphs appended after the existing 'Writing the gap down is the
  point' paragraph, narrowing the deliberately unspecified gap in one direction only, and naming
  the accepted-but-misread case as a different one.
- `## Failure modes` - one `If <trigger>, then` criterion: a query the index refuses is still
  answered, at `EX_OK`, raising nothing and reporting no degraded search.
- `## Out of scope` - two entries: reporting which surface answered (never), and widening the
  index's reach (#122 resolution 1, gated on #134, with its cost recorded).

`## Data requirements` was read and **deliberately not amended**. Routing does not change *what* is
searched: the path-shaped rule already declares the name-only surface for its own case, and
[#79](https://github.com/andyrids/venv-axi/issues/79)'s docstring-surface parity already holds on
both search paths. A subsection there would imply the surfaces read different data, which is the
one thing this change must not suggest. No `## Principles` entry either - nothing here picks a side
of a trade-off that enumeration will not reach, and manufacturing one to fill the section would
produce a principle that rules nothing out.

## Approach

1. Flip to `status: in-progress`.
2. The spec amendment is written and is the stage 01 output; nothing further is authored under
   `specs/`.
3. **Criterion 1** - largely evidenced already. `tests/test_store.py:860`
   (`test_search_symbols_fts_syntax_error_degrades_to_like`) covers the degrade-without-raising
   half at store level, and `tests/test_find_ordering.py:379` and `:443` cover `%` and `\` reaching
   a literal answer through `find_symbol` on both fixture parameters. **Gap**: nothing asserts
   `EX_OK` at CLI level. Evidence that half with a **live run** - the form
   [`plans/find-literal-query.md`](find-literal-query.md) used for its `EX_OK` and situational-hint
   claims - rather than a new test.
4. **Criterion 2 - must be written; nothing asserts it today.** A new test in
   `tests/test_find_ordering.py`: two rows tied on keys 1 to 4 and *equal* in `qualified_name`
   length, differing only lexically, under a query carrying `%`, run on the `[fts]` parameter. That
   parameter is itself the assertion - an FTS-enabled build routed away, or the key 6 order would
   not be the one observed.
   **Critically, build the two rows so their token statistics DIFFER.** This inverts the convention
   the rest of the module follows (`tests/test_find_ordering.py:1-36`), where keys 5 and 6 fixtures
   are deliberately bm25-identical so the key under test breaks the tie on both paths. Here the
   point is the opposite: if the rows tie on bm25 the test passes vacuously and proves nothing
   about routing.
   Prove they differ with a **scratch run** - same fixture, plain (non-`%`) query, which must
   produce the *other* order - and record that in Notes at closeout. Do **not** retain the scratch
   run as a test: it asserts order *inside* the unspecified gap and would make one backend's bm25
   the contract by the back door.
   [`plans/find-ordering-contract.md`](find-ordering-contract.md) Notes set that precedent, where
   the discriminating harness was established and then not kept.
5. **Criterion 3** - evidenced already by the `like_only` fixture
   (`tests/test_find_ordering.py:74-89`) driving `:289` and `:307`, the key 5 and key 6 tests, with
   no relevance score available on that path. The box is kept anyway: it is the half that stops a
   reader inferring the converse of criterion 2, and a criterion that is already met is still the
   criterion 03-verification reports against.
6. **No box for repeatability.** Criterion 2 subsumes it - an order asserted to be total under keys
   1 to 6 is an order that repeats - and `find.md:125-127` already declares it under key 6. This
   delta does not move that declaration, so a new box would restate a criterion
   [`plans/find-ordering-contract.md`](find-ordering-contract.md) already ticked.
7. **No box for the `## Out of scope` entries.** Neither is an `If <trigger>, then` clause; they
   rule behaviour out rather than declare it. A box asserting `find` does not report which surface
   answered could not fail, and
   `ICM/_config/reference-standard-validation.md` rules out criteria that cannot fail.
8. **For stage 02** - `tests/test_find_ordering.py`'s module docstring needs a *precise* trim, not
   a rewrite. Its **contract** statements move into the spec and are replaced by a one-line pointer
   to `find.md` `### Result ordering`: 'A path-shaped query cannot reach `search_fts.sql` at all'
   and the `%`/`\` routing sentence are now declared behaviour, and a test module restating a spec
   is where the two drift apart. Its **test-design** statements MUST stay - the mirrored-but-
   unexercised-clause hazard ('do not read a `[fts]` parameter on a path-shaped test as proof that
   clause works') and the bm25-identical fixture convention are facts about these fixtures, which
   no spec owns. Add a note that criterion 2's new test **inverts** the token-statistics
   convention, so a later reader does not 'fix' the fixture back into a tie.
9. **For stage 04** - a `CHANGELOG.md` `## [Unreleased]` → `### Changed` entry. The contract is
   newly *stated*, not newly true.

## Validation

- [ ] If the search index refuses `query`, its query grammar rejecting one or more of the
      characters in it, then the `find` command shall return its results and exit `EX_OK`, raising
      nothing and reporting no degraded search.
- [ ] If the search index refuses `query`, its query grammar rejecting one or more of the
      characters in it, then the `find` command shall order two results tied on keys 1 to 4 and
      equal in `qualified_name` length by `qualified_name` ascending, with no relevance score
      interposed.
- [ ] While no full-text index is available to a build, the `find` command shall order results by
      keys 1 to 6 alone for every query.
- [ ] The test suite shall pass.

## Risks / unknowns

- **The trigger set is not enumerable, and over-claiming it is the unsafe direction.** 'Any
  non-identifier character' is false: `a*b`, `a+b` and `name:print` all parse against this venv's
  SQLite (**3.49.1** - #122 was written against 3.50.4, and the probed version is what is cited).
  The guarantee is a floor, so a wrong enumeration promises something the command does not deliver.
  The spec therefore states the rule over the consequence and names `.`, `::`, `%` and `\` only as
  the cases this command already meets through rules it already carries.
- **The trigger is refusal, and that is what keeps the `:` leak outside it.** #122 says a query
  carrying FTS5 metacharacters is answered by the substring backend; `name:print` shows that is
  false as written - the index *accepts* it and reads `name:` as a filter on one of its own fields,
  so `bm25` is interposed and the observed order is not key 5 ascending. A trigger phrased over
  text-versus-syntax would have fired there and been violated by current behaviour on the day it
  landed, manufacturing a divergence under `specs/README.md` Invariant 2 in a plan whose whole
  premise is that nothing changes. Phrasing it over **refusal** excludes the accepted-but-misread
  case by construction rather than by argument: `.`, `::`, `%` and `\` are rejected outright, `:`
  is not. The leak stays a Literal matching failure, filed as
  [#134](https://github.com/andyrids/venv-axi/issues/134), and the spec now says so in
  `### Result ordering` so the boundary is legible. **No re-entry is contingent on how #134 is
  resolved** - accepted-but-misread queries are outside this trigger whatever is decided about
  them.
- **Criterion 2 can pass vacuously.** Two fixture rows with identical token statistics tie on bm25,
  and the key 6 order then holds on the FTS path whether or not the query routed away - exactly the
  fixture trap [`plans/find-ordering-contract.md`](find-ordering-contract.md) Risks names. The
  scratch discrimination run in Approach step 4 is the mitigation and its result belongs in Notes.
- **Declaring routing narrows the gap, and a narrowed gap is harder to widen back.** A future
  change that put metacharacter queries on the full-text surface - #122 resolution 1 - now needs a
  spec amendment rather than a quiet query edit. That is the intended cost, and it is the same
  trade `find-ordering-contract` accepted when it froze the six keys.

## Notes

## Follow-ups
