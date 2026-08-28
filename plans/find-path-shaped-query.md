---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/commands/find.md
authors: []
issues: [94]
pr:
---

# Plan: Find path-shaped query

## Scope

`find`'s whole job is turning a bare name scanned out of a codebase into a qualified one
(`specs/commands/find.md`, opening line). The natural spelling for a method an agent has just read
off a call site is `Class.method` - and that spelling ranks the method behind unrelated classes.
[#94](https://github.com/andyrids/venv-axi/issues/94), reproduced against this repo's own venv:

```text
$ venvaxi find 'Console.print' --package rich
count: 9
symbols[9|]{name|kind|qualified_name}:
  Align|class|"rich.align::Align"
  Panel|class|"rich.panel::Panel"
  RichRenderable|class|"rich.abc::RichRenderable"
  out|method|"rich.console::Console.out"
  pager|method|"rich.console::Console.pager"
  print|method|"rich.console::Console.print"
  ...
```

**Two mechanisms, both load-bearing, and fixing either alone leaves the command wrong.**

1. **Ranking.** Keys 1 and 2 are defined against `nodes.name` (`search_fts.sql:7-8`,
   `search_like.sql:6-7`) and a method's `name` is `print`, never `Console.print`
   (`schema.sql:5-7`). Both keys are false for *every row in the graph*, so ranking falls straight
   through to the kind key, which promotes every class above every method.
2. **Matching.** FTS5's query grammar rejects the unquoted `.`, so the query never reaches `bm25`
   at all - `_store.py:395` catches `sqlite3.OperationalError` and routes it to the `LIKE`
   fallback, confirmed live by `venvaxi -v find 'Console.print' --package rich` emitting
   `DEBUG: FTS5 query failed (Console.print), using LIKE`. That fallback's `WHERE` matches `doc`
   (`search_like.sql:3`), and `Align`, `Panel` and `RichRenderable` match *only* there: each
   docstring carries a literal `console.print(...)` usage example, and SQLite `LIKE` is
   case-insensitive on ASCII.

**Why both halves are in one unit.** Ranking alone puts `print` first but leaves `count: 9` with
three unrelated classes at ranks 2-4. `src/venvaxi/SKILL.md:66-74` documents this exact command
returning `count: 3` - `print`, `print_json`, `print_exception`, no classes. That output is not
stale fiction: it is precisely what `find` returns once a qualified-path spelling stops matching
prose. Taking only the ranking half would mean rewriting the packaged skill's flagship worked
example to a messier truth; taking both makes the example true as written.

**This is a bug fix, not a declaration.** Show-it-failing applies: every new assertion must be
shown failing against the pre-fix code before it is shown passing against the fix.

**The contract was satisfied, and the result was still wrong.** Every one of the five declared
keys fired exactly as written on the reproduction above. This is an *unspecified case*, not a
violation - which is why the resolution amends the spec rather than only the SQL, and why the
amendment adds a key rather than redefining what keys 1 and 2 mean.

Out of scope, each with where it went:

- **Query decomposition.** The head of a path-shaped query is not split off and matched against
  the owning class or module. Recorded in `specs/commands/find.md` `## Out of scope`, because it
  would change what a query *means* rather than how results are ranked, and #94's own option 2
  leaves the multi-dot and docstring-interaction questions unreasoned.
- **The FTS5 routing itself.** A path-shaped query will still fail the MATCH grammar and fall to
  `LIKE` through the existing `except` branch. Quoting the query into an FTS phrase would change
  which backend answers, and with it the result *set*, not only its order - a larger change than
  the defect needs.
- **Automated verification of the skill's worked examples** -
  [#39](https://github.com/andyrids/venv-axi/issues/39). This plan makes the flagship example true
  and records a live run proving it; it does not build the harness that would keep every example
  honest.
- **The remaining 0.5.0 units** - #48, #95, #96, #97.

## Implements

`specs/commands/find.md` sits in `specs:` and not `authors:` because this plan both writes the
amendment and changes code until it conforms; `plans/README.md` puts that combination in `specs:`.

`## Invocation / inputs` - the `query` row's Meaning is qualified: the search surface now depends
on the query's shape, and the table was the one place claiming otherwise unconditionally.

`## Data requirements` - gains the **path-shaped query** definition (a query containing `.` or
`::`) and the rule that it matches `name` and `qualified_name` only, never docstring text. The
paragraph states the *why* - prose about a symbol is not a spelling of it - and scopes the
narrowing explicitly to the path-shaped case, so the docstring surface
[#79](https://github.com/andyrids/venv-axi/issues/79) brought the fallback into conformance with
stays declared for every bare query.

`### Result ordering` - gains a new **key 3**: a `qualified_name` that equals the query, or ends
with it preceded by `.` or `::`, ignoring case. The old keys 3-5 renumber to 4-6, and the two
paragraphs naming keys by number ("Key 4 is what prefers short facade paths", "One gap between
key 3 and key 4") are renumbered with them. The key is additive - it tightens the region above the
kind key, and no existing key changes meaning or relative position.

`## Out of scope` - gains the **Query decomposition** bullet, and the existing **Fuzzy or
approximate matching** bullet stops asserting the query is matched "against name and docstring
text" unconditionally, which the amendment above makes false for one query shape. Divergence
created in the act of fixing something is still divergence (`specs/README.md`, Invariant 2).

**Read in full at stage 01 and deliberately not amended**, recorded here rather than assumed:

- `specs/behaviors/output-contract.md:147-148` - "Search reads names and docstring text, never
  signatures, so the recorded marker stays out of `find`'s reach". Its claim is about
  *signatures*, and the reasoning it protects (a stored `(signature unavailable)` marker must not
  become findable) is untouched: a bare query still reads docstring text, and a path-shaped query
  reads strictly less.
- `specs/mcp/tools.md:65` - maps `findSymbolTool` onto `find <query>` and declares no search
  surface of its own. `find_symbol` (`_introspect.py:1029`) passes `query` through unmodified and
  `findSymbolTool` (`_mcp.py:412`) calls it, so the MCP surface inherits both halves of this fix
  with no per-surface branch and no spec amendment.
- `specs/behaviors/skill-content.md` - this plan makes `SKILL.md`'s existing worked example true
  rather than falsifying a claim in it, so the skill needs no edit and the rule spec no change.
  The distinction matters: `private-submodule-hints` listed this spec in `specs:` precisely
  because it *did* falsify two skill claims.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. `src/venvaxi/search_like.sql` - add the key-3 expression to `ORDER BY`, above the kind key, and
   make the `doc` disjunct in `WHERE` conditional on a separate, nullable parameter.
3. `src/venvaxi/search_fts.sql` - add the identical key-3 expression in the identical position,
   above `bm25`. The `WHERE` is *not* narrowed there: a path-shaped query cannot reach that SQL,
   because the MATCH grammar rejects `.` and `:` before the statement runs. See Risks.
4. Convert both statements from positional `?` to named parameters. Key 3 needs `:query` three
   further times per file; under positional binding the correctness of the whole statement would
   rest on the order of a six-slot tuple. `_read_sql` is untouched - only the two `execute` calls
   in `SymbolStore.search_symbols` change from tuple to dict.
5. `src/venvaxi/_store.py::search_symbols` - the only code site. One predicate,
   `"." in query or "::" in query`, selects the `doc` pattern or `None`. Update the method's
   `NOTE:` docstring, which enumerates the ordering contract and is now one key short.
6. Add the regression coverage named in Validation to `tests/test_find_ordering.py` - every query
   seeded in that module today is single-token (`"widget"`, `"Widget"`, `"parser"`), so nothing
   there could have caught this. Run each new assertion against the pre-fix code first and record
   it failing.
7. While that module is open, correct two stale statements in its docstrings: the module header
   calls the contract a "five-key total order", and
   `test_find_orders_prefix_match_before_docstring_only_match` claims "the `LIKE` fallback does
   not match docstrings at all", which has been false since
   [#79](https://github.com/andyrids/venv-axi/issues/79)/PR #83 added the `doc` disjunct.
8. Re-verify `src/venvaxi/SKILL.md:61-74` against a live run and record the output. The example is
   expected to need **no edit**; if it does, that is a stage-01 re-entry, not a stage-02 patch.
9. `CHANGELOG.md` entry under `Fixed`.

## Validation

- [x] When `find` is invoked with a path-shaped query, and a symbol's `qualified_name` ends with
      that query preceded by `.` or `::`, then the `find` command shall return that symbol before
      any symbol whose `qualified_name` does not. —
      `tests/test_find_ordering.py::test_find_orders_qualified_name_suffix_match_before_kind_tier[fts]`
      and `[like]`, both passed; also evidenced live by `uv run venvaxi find
      'rich.console::Console.print'`, which ranks the row itself first via key 3's equality arm
      (stage 03 report)
- [x] When `find` is invoked with a path-shaped query, the `find` command shall not return a
      symbol that matches the query only in its docstring. —
      `tests/test_find_ordering.py::test_find_path_shaped_query_excludes_docstring_only_match[fts]`
      and `[like]`, both passed; also evidenced live by `uv run venvaxi find Console.print
      --package rich` (`count: 3`, excluding `Align`/`Panel`/`RichRenderable`, all docstring-only
      matches) (stage 03 report)
- [x] When `find` is invoked with a query containing neither `.` nor `::`, the `find` command
      shall return a symbol that matches the query only in its docstring. —
      `tests/test_find_ordering.py::test_find_bare_query_still_matches_docstring_only[fts]` and
      `[like]`, both passed (a regression guard, confirmed passing pre-fix too); also evidenced
      live by `uv run venvaxi find print --package rich`, which still returns docstring-only class
      matches (stage 03 report)
- [x] When `find` is invoked with a query containing `::` and no `.`, the `find` command shall
      rank and match it as a path-shaped query. —
      `tests/test_find_ordering.py::test_find_colon_only_query_ranks_and_narrows_like_dotted[fts]`
      and `[like]`, both passed - one test asserts both ranking and narrowing on a `::`-only,
      no-`.` fixture (stage 03 report)
- [x] When `find` is invoked with a path-shaped query matching no symbol, the `find` command shall
      emit `count: 0` with the situational hint its `--package` argument selects, and exit
      `EX_OK`. — not a test: evidenced by direct code read of `_cli.py:290-326` (the empty-state
      hint branch tests only `if package`, never `ctx.args.query`) plus the live commands `uv run
      venvaxi find "Nonexistent.methodxyz" --package rich` and `uv run venvaxi find
      "Nonexistent.methodxyz"`, both emitting `count: 0`, the correct situational hint, and exit
      `0` (stage 03 report, independent verification)
- [x] When `findSymbolTool` is called with a path-shaped `query`, it shall return the same symbols
      in the same order as the `find` command invoked with that query. —
      `tests/test_mcp.py::test_find_symbol_tool_path_shaped_query_matches_find_symbol`, re-run
      individually: `1 passed in 0.94s`; guard confirmed non-vacuous by reading the fixture in
      full (stage 03 report)
- [x] When `venvaxi find Console.print --package rich` is run against this repository's own venv,
      it shall emit `count: 3` and the rows `rich.console::Console.print`,
      `rich.console::Console.print_json`, `rich.console::Console.print_exception`, in that order,
      matching the worked example at `src/venvaxi/SKILL.md:66-74`. — not a test: evidenced by the
      live command `uv run venvaxi find Console.print --package rich`, output (`count: 3`,
      `print`/`print_json`/`print_exception`, in that order) confirmed byte-for-byte identical to
      a direct re-read of `src/venvaxi/SKILL.md:66-74` (stage 03 report)
- [x] The test suite shall pass. — `uv run coverage run -m pytest` → `522 passed, 21 deselected in
      64.63s (0:01:04)` (stage 03 report)

## Risks / unknowns

- **Key 3 in `search_fts.sql` is inert on arrival.** No path-shaped query reaches that statement:
  FTS5's query grammar rejects the unquoted `.` and `:`, so `_store.py`'s
  `except sqlite3.OperationalError` routes every such query to `LIKE` before MATCH is evaluated.
  It is mirrored anyway so the two files state one ordering contract rather than two, and so a
  future change to the routing does not silently un-fix half the behaviour - but it is untested
  code on arrival, and the tests must say so rather than imply both backends were proved.
  `tests/test_find_ordering.py`'s `search_backend` fixture will still run every path-shaped case
  under its `fts` parameter, and that run exercises `search_like.sql` through the fallback; a
  docstring claiming otherwise would be worse than no docstring.
- **The narrowing is a partial reversal of #79/PR #83 for one query shape.** That plan brought the
  `LIKE` fallback's search surface up to the spec's declared name-and-docstring contract. This one
  removes docstrings again, for path-shaped queries only, on both backends. Validation criterion 3
  exists solely to pin the shape that must *not* change, and the spec paragraph states the scope
  of the narrowing rather than leaving it to be inferred from the SQL.
- **`substr(X, -N)` semantics.** Key 3 uses `substr(lower(qualified_name), -(length(:query) + 1))`
  rather than a `LIKE` suffix pattern, because a query containing `_` (`Console.print_json`) would
  otherwise carry a LIKE wildcard into the ranking key. Confirmed at stage 01 against the venv's
  SQLite 3.50.4: the expression returns the whole string when the query is longer than the
  `qualified_name`, so an over-length query yields no false positive. Stage 02 re-confirms rather
  than trusting this note.
- **`--limit` interacts with the narrowing.** Dropping docstring-only rows from a path-shaped
  query lowers `count` for that query shape, so a previously capped result may now come in under
  the bound. That is a smaller answer, not a wrong one, and `### Bounded results` is unchanged -
  but it is the one observable this plan changes that no criterion above names directly.

## Notes

**Why both halves are one unit.** Ranking alone leaves `count: 9` with three doc-only classes at
ranks 2-4 - the exact reproduction in this plan's Scope - and would have forced a rewrite of
`SKILL.md`'s flagship example to a messier truth, since narrowing the docstring surface without
fixing ranking would remove the doc-matching classes but still leave the method behind other
kind-tier survivors. Only doing both makes the documented example (`count: 3`, `print`/
`print_json`/`print_exception`, no classes) true exactly as written - confirmed live at stage 02
and re-confirmed independently at stage 03 (Validation criterion 7).

**Why `substr`, not a `LIKE` suffix pattern.** A `LIKE '%' || :query` suffix pattern would carry
the query's own `_` and `%` characters into the pattern as wildcards - a query containing `_`
(`Console.print_json`) would then rank identically to `Console.printXjson`. `substr` compares
literal text and is immune to that. Verified against this venv's live SQLite 3.50.4 at stage 01,
re-verified independently at stage 02:

| `qualified_name` | `:query` | tail (`length+1`) | key 3 |
| ---------------- | -------- | ----------------- | ----- |
| `rich.console::Console.print` | `Console.print` | `:console.print` | 1 |
| `rich.console::Console.print_json` | `Console.print` | `ole.print_json` | 0 |
| `pkg.mod::Outer.Inner.method` | `Inner.method` | `.inner.method` | 1 |
| `abc` | `xxxxxxxxxx` | `abc` | 0 |
| `rich.console::Console.print` | `rich.console::Console.print` | (whole string) | 1 |

Row 4 is the over-length clamp: `substr` returns the whole string rather than erroring when the
query is longer than the `qualified_name`, so the comparison is simply false and there is no
false positive. Row 5 is why the equality disjunct exists alongside the suffix check: a caller who
types the complete qualified name has no separator in front of it.

**Why named parameters replaced `?`.** Key 3 needs `:query` three further times per file (the
equality arm, the suffix length, and the suffix comparison), on top of the existing key 1/key 2
uses. Under positional binding a six-slot tuple's correctness would rest entirely on argument
ordering, silently breakable by any future reordering of the `SELECT`. Named parameters make each
binding self-describing and order-independent.

**Why key 3 is mirrored into `search_fts.sql` even though it is unexercised.** The two files state
one ordering contract, not two - a future reader, or a future change to the FTS/LIKE routing,
should not find the two statements disagreeing on how a path-shaped query ranks, even though only
`search_like.sql` is reachable by one today (FTS5's `MATCH` grammar rejects the unquoted `.`/`:`
before `ORDER BY` is ever evaluated). This was raised as an undisclosed gap at the stage 02 review
gate - see that report's `## Gate addendum` section: three of the four new tests used the
`search_backend` fixture, whose docstring claimed every assertion "holds on both `ORDER BY`
clauses", which is false for a path-shaped query. Verified by mutation, not argument: key 3 was
deleted outright from `search_fts.sql` and the six path-shaped assertions re-run -
`6 passed, 13 deselected in 0.37s`, all six passing with the clause gone, on both fixture
parameters - proving it provably inert. Fixed at the gate: the module docstring in
`tests/test_find_ordering.py` now states key 3 is asserted on `search_like.sql` only, and the
`search_backend` fixture docstring's "both `ORDER BY` clauses" claim is qualified with the
path-shaped exception.

**The test-fixture trap.** A competitor row used to demonstrate key 3 must still satisfy the
unconditional `name`/`qualified_name` `LIKE` match in `WHERE`, or it never enters the result set at
all regardless of the fix, and the test's pass or fail proves nothing about ranking. This bit two
separate fixtures at stage 02: the first draft of
`test_find_orders_qualified_name_suffix_match_before_kind_tier` used a competitor row (`pkg::Owner`)
whose `qualified_name` did not contain the query substring, so the pre-fix failure read `1 == 2`
(a missing row) rather than a reordering; the `findSymbolTool` parity test's first draft tripped
the identical trap, with `assert len(expected) == 2` failing pre-fix for the same reason. Both
were caught by inspecting the actual pre-fix failure text - not trusting the assertion's boolean
result - and corrected to a competitor whose `qualified_name` contains the query as a substring
but not as a `.`/`::`-preceded suffix (`pkg::AltOwner.method`), so it matches `WHERE`
unconditionally but loses key 3. The most reusable lesson of the run.

## Follow-ups

- **Issue [#39](https://github.com/andyrids/venv-axi/issues/39)** - automated verification of the
  skill's worked examples. This run makes the flagship example true and records a live run
  proving it, but builds no harness that would catch a future divergence; already named out of
  scope in this plan's Scope.
- **Issue [#108](https://github.com/andyrids/venv-axi/issues/108)** - filed at this closeout.
  `search_symbols`'s `LIKE` fallback builds its `WHERE` pattern as `f"%{query}%"` with no
  escaping, so a query containing `_` or `%` carries a SQL `LIKE` wildcard into the match -
  `find 'print_json'` would also match `printXjson`. Discovered at stage 01, pre-existing and not
  introduced by this unit: key 3 deliberately avoids adding a *second* instance of this by using
  `substr` instead of a `LIKE` suffix pattern (see Notes above), but the `WHERE` clause's own
  wildcard exposure is untouched and undeclared in `specs/commands/find.md`. Owned by no current
  plan.
- Criterion 5 (empty-state hint) has no regression protection. It is true today, evidenced by code
  inspection plus a live run, but nothing in the suite would catch a future change making
  `command_find`'s hint selection query-dependent. No follow-up entry: the branch in question is
  two lines (`if package`) with no query-shape logic at all, so there is nothing distinct to
  regress against beyond the existing `test_command_find_empty` coverage - adding a
  path-shaped-query parametrize would exercise byte-identical code and add no real protection.
- **The `--limit` interaction**, named in this plan's Risks - a path-shaped query's `count` can
  now legitimately fall since docstring-only rows are excluded, and no Validation criterion names
  this directly. Not filed as an issue: it is a smaller, correct answer rather than a wrong one,
  `### Bounded results` in `specs/commands/find.md` is unchanged, and no caller-observable defect
  follows from it - recorded here as the deliberate omission it was, not left to be
  re-discovered as a gap.
- **Deferred to** - none.
- **Tracked as** - none.
