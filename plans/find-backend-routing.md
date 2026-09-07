---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
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

- [x] If the search index refuses `query`, its query grammar rejecting one or more of the
      characters in it, then the `find` command shall return its results and exit `EX_OK`, raising
      nothing and reporting no degraded search. — Store-level degrade-without-raising:
      `tests/test_store.py::test_search_symbols_fts_syntax_error_degrades_to_like` - PASSED.
      Literal-answer-through-`find_symbol` half: `tests/test_find_ordering.py::test_find_percent_query_matches_literal_substring_only[fts]`/`[like]`
      and `::test_find_backslash_query_matches_literal_backslash[fts]`/`[like]` - all 4 PASSED.
      CLI-level `EX_OK` half - live run performed in stage 03 (transcript in
      `ICM/process-plan/stages/03-verification/output/find-backend-routing-test.md`, "Live-run
      transcript, criterion 1 CLI half"): both invocations exit `0`, stderr empty on both.
- [x] If the search index refuses `query`, its query grammar rejecting one or more of the
      characters in it, then the `find` command shall order two results tied on keys 1 to 4 and
      equal in `qualified_name` length by `qualified_name` ascending, with no relevance score
      interposed. — `tests/test_find_ordering.py::test_find_percent_query_ignores_bm25_and_falls_back_to_ordering`:
      `[fts]` PASSED (the parameter that is itself the assertion), `[like]` PASSED (holds for
      free, no `bm25` to interpose). Both parameters re-run individually, both green.
- [x] While no full-text index is available to a build, the `find` command shall order results by
      keys 1 to 6 alone for every query. — `like_only`-fixture-driven tests, re-run individually:
      `tests/test_find_ordering.py::test_find_orders_shorter_qualified_name_first[like]` (key 5) -
      PASSED; `tests/test_find_ordering.py::test_find_breaks_final_ties_on_qualified_name_ascending[like]`
      (key 6) - PASSED. Confirmed by reading `search_backend`'s fixture body
      (`tests/test_find_ordering.py:98-111`): the `like` parameter calls
      `request.getfixturevalue("like_only")`, which monkeypatches `SymbolStore.__init__` to set
      `self._fts_enabled = False` after schema creation - the "no full-text index available" case
      the criterion names.
- [x] The test suite shall pass. — `uv run pytest -v` -> `619 passed, 32 deselected in 76.70s`.

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

**Why consequence-framing, not routing-framing.** "Which backend answered" is not itself
observable - the only trace is a `DEBUG`-level log line at `_store.py:496` that no spec owns - so
every declaration in `### Result ordering` is stated over the ordering a caller can measure
instead. The decisive reason is the second one: a *routing* rule, if
[#122](https://github.com/andyrids/venv-axi/issues/122) resolution 1 ever lands, is deleted as an
internal reroute with nothing for a caller to notice. A *consequence* rule is instead **withdrawn
as a guarantee a caller was told it could rely on** - which is what resolution 1 actually costs,
and framing it this way is what makes that cost show up in the diff rather than disappearing
inside an implementation detail.

**Why the trigger is refusal, not text-versus-syntax.** The first draft fired on any query the
index reads as its own syntax. That set includes `name:print`, which the index *accepts* as a
column filter rather than rejecting - `bm25` is still interposed and the observed order is not key
5 ascending. That wording would have been violated by current behaviour on the day it landed,
manufacturing an Invariant 2 divergence (`specs/README.md`) inside a plan premised on nothing
changing. Keying the trigger on **refusal** excludes the accepted-but-misread case by construction
rather than by argument - `.`, `::`, `%` and `\` are rejected outright, `:` is not, and the leak
stays a Literal matching failure, filed as
[#134](https://github.com/andyrids/venv-axi/issues/134).

**The discrimination run** (scratch, not retained as a test): with the shipped fixture, the
`%`-bearing query (`rate%calc`) routes to the substring surface and returns
`[pkg.alpha::rate%calc, pkg.gamma::rate%calc]` (key 6, `qualified_name` ascending), while a plain
`widget` query stays on the full-text index and returns
`[pkg.gamma::rate%calc, pkg.alpha::rate%calc]` - the other order, `bm25` gamma
`-1.151849413183759`, alpha `-0.4356736122404892`. That inversion is what makes the new test
non-vacuous: an FTS build that failed to route the `%` query away would have produced the `bm25`
order on both parameters, not just on `[like]`. It was deliberately not retained as a test:
asserting it would place order *inside* the deliberately unspecified key 4/5 gap and make one
backend's `bm25` the contract by the back door -
[`plans/find-ordering-contract.md`](find-ordering-contract.md) Notes set that precedent.

**The bm25/IDF correction, and that it was a stage 03 re-entry into stage 02's output.** The
implementation report's original justification for the six filler rows claimed a two-row graph
ties **exactly** at zero, because the IDF of a term every row carries collapses to zero. That is
wrong: SQLite *floors* rather than zeroes that IDF, so a real, correctly-directed difference
survives at roughly `1e-6` (`pkg.gamma::rate%calc -> -1.4347826086956523e-06`,
`pkg.alpha::rate%calc -> -7.674418604651162e-07`), independently reproduced by stage 03 via a
fresh in-memory build of the project's own `schema_fts5.sql` rather than by trusting the report's
figures. The filler rows were kept, and correctly so, but for the corrected reason: not because a
two-row graph ties, but because they make the separation a designed signal of real magnitude
(`gamma -1.151849413183759`, `alpha -0.4356736122404892`, six orders of magnitude wider) rather
than a margin indistinguishable from floating-point noise. The shipped test's own correctness was
unaffected either way, because its query (`rate%calc`) never reaches `MATCH` regardless of graph
size - stage 03 caught the reasoning error, not a defect.

**Read and deliberately not amended:**

- `## Data requirements` and `## Principles` in `specs/commands/find.md` - routing does not change
  *what* is searched, and nothing here settles a trade-off a principle would need to state; see
  the plan's own Implements section for the full rationale.
- `src/venvaxi/SKILL.md` and the skill drift gate - the skill makes no claim about backends,
  relevance or ranking, and the gate's checks (flags, defaults, the command table, MCP tool
  signatures, exit codes, documented invocations) are all untouched by this delta. The skill's
  executed query `venvaxi find Console.print --package rich` is *described* by this delta - it is
  a path-shaped query that now has a declared refusal-ordering guarantee - but its own behaviour
  and the skill's claim about it are unchanged.
- `specs/mcp/tools.md` - restates no ordering guarantee of its own and inherits `find.md`'s
  guarantee through `findSymbolTool` rather than duplicating it.

**Version pin:** the SQLite version probed against this venv is **3.49.1**
(`sqlite3.sqlite_version`); [#122](https://github.com/andyrids/venv-axi/issues/122) was written
against 3.50.4. The spec deliberately names no version and enumerates no character set - the
trigger belongs to the index's own grammar and to whatever version of it a build ships, not to a
list that would drift the moment SQLite's FTS5 grammar changes.

**Ripple check:** `grep -l 'specs/commands/find.md' plans/*.md` returns 14 plans, all
`status: done` (listed in full in the stage 01 techspec's References section). Nothing is
stranded, and no frozen plan needed editing.

**`authors:` not `specs:`, and why.** This plan changes no file under `src/` - the routing
behaviour it declares already existed and was already deterministic. `specs:` would claim a code
conformance this plan never delivers, and adding a regression test is not a code conformance
either; `authors:` is the honest field for a plan that writes a spec describing behaviour already
true, following the precedent
[`plans/find-ordering-contract.md`](find-ordering-contract.md) set for the ordering keys
themselves.

## Follow-ups

- **Issue [#134](https://github.com/andyrids/venv-axi/issues/134)** - the `:` column-filter leak:
  `name:print` and `doc:json` reach the full-text index as column filters rather than as text, a
  live divergence against `find.md`'s Literal matching rule. Found while specifying this plan and
  filed during stage 01. Actionable, owned by no current plan.
- **[#122](https://github.com/andyrids/venv-axi/issues/122) resolution 1** (phrase-quoting the
  query so every query reaches the full-text index) is not started here and has no owning plan. It
  is recorded, with its cost - reintroducing the `%`-tokenizer regression
  [#108](https://github.com/andyrids/venv-axi/issues/108) closed - in `specs/commands/find.md`
  `## Out of scope`, and is explicitly gated on [#134](https://github.com/andyrids/venv-axi/issues/134)
  being settled first. It lives there, not in this plan's Follow-ups, because it is scope this
  plan declined rather than work this plan deferred to a named successor.
- **None deferred.** There are no `Deferred to` entries - no downstream plan absorbs anything from
  this run, so no plan besides this one needed editing in this commit.
- This plan resolves [#122](https://github.com/andyrids/venv-axi/issues/122): resolution 2
  (declare the routing consequence) was the one chosen and shipped; resolution 1 (phrase-quoting)
  is recorded above as not taken, gated on #134.
