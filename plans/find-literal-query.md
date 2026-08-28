---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/find.md
authors: []
issues: [108]
pr: 121
---

# Plan: Find literal query

## Scope

`SymbolStore.search_symbols` builds the `LIKE` fallback's `WHERE` pattern as a plain f-string
(`src/venvaxi/_store.py:407`):

```python
like_pattern = f"%{query}%"
```

SQLite `LIKE` reads `_` as any single character and `%` as any run of characters, and neither is
escaped here, so the caller's own query characters become SQL wildcards. `_` is an ordinary
character in a Python identifier - `print_json`, `get_module_tree`, `__init__` - so
`find print_json` also matches `printXjson` for any `X`, with no error and no indication the match
was approximate ([#108](https://github.com/andyrids/venv-axi/issues/108)).

**The exposure is wider than the issue states.** The same raw `:query` is interpolated into
ranking **key 2** - `lower(name) LIKE lower(:query) || '%'` - in *both* `search_like.sql` and
`search_fts.sql`. The defect is therefore a matching defect on one backend and a ranking defect on
the statement of the ordering contract in both files, not a single `WHERE` clause. Keys 1 and 3 are
unaffected: key 1 is `=`, and key 3 uses `substr(...) IN (...)`, which
[find-path-shaped-query](find-path-shaped-query.md) chose over a `LIKE` suffix pattern for exactly
this reason.

**This is spec/code divergence, not only an undeclared behaviour.** `specs/commands/find.md`
already asserts, under `## Out of scope`, that "the query is matched as supplied", and key 2
already reads "begins with the query". Wildcard substitution satisfies neither. Under
`specs/README.md` Invariant 2 that is a bug to be fixed in code, and the amendment this plan makes
alongside it declares the rule positively rather than leaving it to be inferred from two statements
about something else.

**This is a bug fix, not a declaration.** Show-it-failing applies: every new assertion must be
shown failing against the pre-fix code, with its failure text read rather than its boolean
trusted, before it is shown passing against the fix.

Out of scope, each with where it went:

- **FTS5 `MATCH` metacharacter handling.** `_store.py:397` builds `f"{query}*"`, and a `"`, `%`,
  `:` or `*` in a query can break the MATCH grammar. It degrades *safely* through the existing
  `except sqlite3.OperationalError` branch onto the `LIKE` path, which this plan makes answer
  literally - so it is a routing quirk, not a silent wrong answer. Recorded as a Follow-up at
  closeout rather than widened into here.
- **A pattern or wildcard query syntax.** Recorded in `specs/commands/find.md` `## Out of scope` as
  never: a pattern language would turn every ordinary identifier query into a question of whether
  it had been escaped correctly.
- **[#97](https://github.com/andyrids/venv-axi/issues/97)**, in either half. Its own Scope routes
  the conformance test to `ICM/express-change` and gates the spec amendment on that test's result.

## Implements

`specs/commands/find.md` sits in `specs:` and not `authors:` because this plan both writes the
amendment and changes code until it conforms; `plans/README.md` puts that combination in `specs:`.

`## Data requirements` - gains `### Literal matching`, its own heading so a citation resolves to
the rule rather than to the section containing it
([principles-anchor-granularity](principles-anchor-granularity.md) established that bar). It
declares that every character of `query` matches only itself, on the match surface *and* the
ordering keys, and states the *why*: an approximate result returned as if it were exact cannot be
told apart from a correct one by the caller.

`### Result ordering` - gains one sentence after the key list, pointing at `### Literal matching`,
so the six keys are read literally by construction. No key changes meaning, position or wording.

`## Out of scope` - gains the **Wildcard or pattern search** bullet, next to the existing **Fuzzy
or approximate matching** bullet it is the natural neighbour of. This is the adjacent capability a
reader of the new rule would reasonably ask about, which is what
`ICM/_config/reference-standard-spec.md` says the section is for.

**Read in full at stage 01 and deliberately not amended**, recorded here rather than assumed:

- `## Out of scope`, **Fuzzy or approximate matching** - it already asserts the behaviour this plan
  restores ("the query is matched as supplied"). Rewording it would weaken the statement the fix
  conforms to; it is one of the two places the divergence was already visible.
- `## Failure modes` - unchanged. A query matching nothing after escaping is `count: 0`, which is
  success under the existing situational empty-state rules, not a new failure mode. No `If` clause
  is added because no new rejection exists.
- `specs/mcp/tools.md:65` - maps `findSymbolTool` onto `find <query>` and declares no search
  surface of its own. `find_symbol` passes `query` through unmodified and `findSymbolTool` calls
  it, so the MCP surface inherits the fix with no per-surface branch and no amendment.
- `specs/behaviors/skill-content.md` - `src/venvaxi/SKILL.md:61` documents
  `venvaxi find Console.print --package rich`. That query contains neither `_` nor `%`, and key 2
  is false for it either way, so the worked example is expected to be unaffected. Verified live at
  stage 03, not assumed.
- `specs/behaviors/output-contract.md` - the search-surface claim there is about *signatures*
  staying out of `find`'s reach. Escaping narrows what a query matches; it adds no column.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. `src/venvaxi/_store.py` - add a module-level `_escape_like(query: str) -> str` beside
   `_read_sql`, escaping the escape character **first**, then `%` and `_`. Order is load-bearing
   (see Risks). Google-style docstring per `ICM/_config/reference-standard-docstrings.md`.
3. `src/venvaxi/_store.py::search_symbols` - build `like_pattern` from the escaped value, and bind
   a new `:query_escaped` parameter for key 2. `:query` stays raw for keys 1 and 3, which are
   literal comparisons already. Extend the method's `NOTE:` docstring, which enumerates the
   ordering contract, with the literal-match rule.
4. `src/venvaxi/search_like.sql` - add an `ESCAPE` clause to the three `WHERE` `LIKE`s, and rewrite
   key 2 against `:query_escaped` with the same clause.
5. `src/venvaxi/search_fts.sql` - the identical key-2 change, in the identical position. Mirrored
   so the two files state one ordering contract rather than two, and inert on arrival (see Risks) -
   the tests must say so rather than imply both backends were proved.
6. Add the regression coverage named in Validation to `tests/test_find_ordering.py`, and a direct
   `search_symbols` assertion on the FTS-disabled fallback to `tests/test_store.py`. Run each new
   assertion against the pre-fix code first and record it failing, reading the failure text.
7. Extend the `tests/test_find_ordering.py` module docstring, which already carries the convention
   for an unexercised mirror in its key-3 `NOTE:`, to state which of the new assertions hold on
   `search_like.sql` only, and why.
8. `CHANGELOG.md` - a `Fixed` entry under `## [Unreleased]` naming issue #108.

## Validation

- [x] When `find` is invoked with a query containing `_`, the `find` command shall return only
      symbols carrying that query as a literal substring, and shall not return one that matches it
      only by substituting another character for the `_`. —
      `tests/test_find_ordering.py::test_find_underscore_query_matches_literal_substring_only[like]`
      and `tests/test_store.py::test_search_symbols_underscore_matches_literal_like_fallback`, both
      passed, and both shown failing under an identity mutation of `_escape_like` with
      `assert ['print_json', 'printXjson'] == ['print_json']`. The `[like]` parameter is the
      evidence; `[fts]` passes either way and is not (stage 03 report)
- [x] When `find` is invoked with a query containing `%`, the `find` command shall return only
      symbols carrying that query as a literal substring, and shall emit `count: 0` with the
      situational hint its `--package` argument selects where no symbol does. —
      `tests/test_find_ordering.py::test_find_percent_query_matches_literal_substring_only[fts]`
      and `[like]`, both passed and both shown failing under mutation; and evidenced live against
      the real `rich` package, where the pre-fix `venvaxi find 'print%json' --package rich`
      returned `count: 3` including `rich.json::JSON` - a symbol carrying no `print%json` in any
      form - against `count: 0` post-fix. Both situational hints and `EX_OK` evidenced live, with
      and without `--package` (stage 03 report)
- [x] When `find` is invoked with a query containing `_`, the `find` command shall not rank a
      symbol whose `name` begins with that query only under wildcard substitution above one whose
      `name` does not begin with it at all. —
      `tests/test_find_ordering.py::test_find_underscore_query_does_not_rank_wildcard_prefix`,
      passed, and shown failing under mutation with
      `assert ['printXjson', 'use_print_json'] == ['use_print_json', 'printXjson']` - both rows
      present, order reversed, so a ranking failure and not a membership one (stage 03 report)
- [x] When `find` is invoked with a query containing a backslash, the `find` command shall match
      the backslash as a literal character and shall not raise. —
      `tests/test_find_ordering.py::test_find_backslash_query_matches_literal_backslash[fts]` and
      `[like]`, both passed, and both shown failing under mutation with
      `assert ['parse_plain'] == ['parse_escape']`; also evidenced live by
      `uv run venvaxi -v find 'a\b' --package rich` (`count: 0`, exit `0`, no raise). The failing
      run is by mutation, not pre-fix, because with no `ESCAPE` clause a backslash was already
      literal - this criterion guards the fix's own failure mode (stage 03 report)
- [x] When `find` is invoked with a query containing no `_`, no `%` and no backslash, the `find`
      command shall return the same symbols in the same order as it did before this change. — all
      522 pre-existing tests passed unchanged, including the full six-key ordering suite; the
      opt-in conformance tier passed `21 passed, 531 deselected`; and criterion 7's live run is
      byte-identical to its pre-change documented output (stage 03 report)
- [x] When `findSymbolTool` is called with a `query` containing `_` or `%`, it shall return the
      same symbols in the same order as the `find` command invoked with that query. —
      `tests/test_mcp.py::test_find_symbol_tool_wildcard_char_query_matches_find_symbol`, passed.
      Ticked as a **guard, not a discriminator**: both sides call the same `find_symbol`, so it
      passes with and without the fix by construction. It evidences that the MCP surface inherits
      the fix with no per-surface branch, and would catch a future divergence between the two
      surfaces; it is not evidence that escaping works (stage 03 report, Finding 2)
- [x] When `venvaxi find Console.print --package rich` is run against this repository's own venv,
      it shall emit `count: 3` and the rows `rich.console::Console.print`,
      `rich.console::Console.print_json`, `rich.console::Console.print_exception`, in that order,
      matching the worked example at `src/venvaxi/SKILL.md:66-74`. — not a test: evidenced by the
      live command `uv run venvaxi find Console.print --package rich`, output confirmed identical
      line for line to a direct re-read of `src/venvaxi/SKILL.md:66-74`, `help[1]` footer included
      (stage 03 report)
- [x] The test suite shall pass. — `uv run coverage run -m pytest` → `531 passed, 21 deselected in
      65.97s (0:01:05)`, coverage `98%` (1332 statements, 20 missed); `uv run pytest -m
      conformance` → `21 passed, 531 deselected`; `pkgdx-lint-hook`, `pkgdx-format-hook`,
      `pkgdx-typing-hook -p venvaxi` and `pkgdx-markdown-hook` all clean (stage 03 report)

## Risks / unknowns

- **Escape order is load-bearing, and getting it wrong fails silently.** `_escape_like` must
  replace the escape character before `%` and `_`, or it double-escapes the escapes it just
  introduced. Verified at stage 01 against this venv's SQLite 3.50.4: a helper that escapes `%` and
  `_` but not the escape character itself turns the query `a\b` into a pattern SQLite reads as an
  escaped `b`, so it matches `ab` and *not* `a\b`. SQLite raises nothing for an escape before an
  ordinary character; the answer is simply wrong. Validation criterion 4 exists for this and
  nothing else.
- **Key 2's copy in `search_fts.sql` is inert on arrival**, for the same reason key 3's is. FTS5's
  unicode61 tokenizer splits `print_json` into `print` and `json`, so `printXjson` - a single
  token - can never enter the candidate set the `ORDER BY` runs over; and `name` is a Python
  identifier, so no candidate row can have a name where the unescaped prefix pattern is true and
  the escaped one false. It is mirrored anyway so a future change to the FTS/LIKE routing does not
  silently un-fix half the behaviour, but it is untested code on arrival and the tests must not
  imply otherwise.
- **The `[fts]` fixture parameter can pass vacuously.** A `_`-query assertion about the `WHERE`
  clause holds pre-fix on the FTS backend, because the wildcard-substituted competitor row is not
  in the candidate set at all - the fixture trap
  [find-path-shaped-query](find-path-shaped-query.md) records in its Notes, arriving by a second
  route. A `%` query is the shape that reaches the `LIKE` path on every install: FTS5 rejects `%`
  with a syntax error, so `_store.py:404` routes it to the fallback unconditionally. Verified at
  stage 01; stage 02 re-confirms rather than trusting this note.
- **`ESCAPE` disables SQLite's `LIKE` index optimisation.** No cost here: `schema.sql` declares no
  index on `name` or `qualified_name` (only `idx_edges_dst` and `idx_nodes_package`), and the
  `WHERE` pattern is `%`-leading, which is unindexable regardless.
- **A `%` query's result set legitimately shrinks.** `find` with a `%` in the query returns matches
  today and will correctly return none once `%` is a literal, unless a symbol really carries one.
  That is a smaller, correct answer rather than a wrong one, and criterion 2 pins the shape it must
  take - `count: 0` with a situational hint and `EX_OK`, not an error.
- **`Path.write_text` on Windows emits CRLF.** `.gitattributes` names this as the defect
  `_atomic_write_bytes` exists to prevent, arriving by a second route, and normalises the tree to
  LF. Any file written by script during this run must be written with explicit LF newlines - hit
  once at stage 01 and corrected before commit.

## Notes

**Why `ESCAPE` rather than `instr` or `GLOB`.** SQLite offers three ways to make a substring match
literal. `instr(haystack, needle) > 0` compares literal text and needs no escaping at all, but it
is case-*sensitive*, and `find` has matched case-insensitively since it existed - switching would
have been an unasked-for behaviour change wearing a bug fix's clothes. `GLOB` is case-sensitive
too, and swaps one metacharacter set (`_`, `%`) for a larger one (`*`, `?`, `[`). `LIKE ... ESCAPE`
keeps the existing case-insensitive ASCII semantics exactly and changes only which characters are
special. It was the only option that fixed the defect without moving anything else.

**Why the escape character is a backslash.** It needs no SQL-literal escaping in SQLite - a
backslash is not special inside a string literal - it is the conventional choice, and it cannot
appear in a Python identifier, so no query carrying one was ever going to match a symbol *name*.
Step 1 of the helper exists to make that miss honest rather than to rescue a match.

**Escape order is load-bearing, and getting it wrong fails silently.** `_escape_like` replaces the
backslash first, then `%`, then `_`. Reversing that double-escapes the escapes just introduced.
Verified against this venv's SQLite 3.50.4, and re-verified by mutation at stages 02 and 03:

| Helper | query | matches |
| ------ | ----- | ------- |
| correct | `a\b` | `a\b` |
| correct | `print_json` | `print_json`, `print_jsonx` |
| forgets step 1 | `a\b` | `ab` - **wrong** |
| none (pre-fix) | `print_json` | `print_json`, `printXjson`, `print_jsonx` |

Row 3 is the one that matters: SQLite raises nothing when the escape character precedes an ordinary
character - it simply treats that character as literal - so a mis-ordered helper returns a wrong
answer with no signal at all. That is the same failure shape this whole unit exists to remove,
reintroduced by the fix for it, which is why Validation criterion 4 exists and pins it.

**Why key 2 needed its own binding and keys 1 and 3 did not.** Key 1 is `=` and key 3 is
`substr(...) IN (...)`; both compare literal text already, and escaping their operand would have
broken them. Only key 2 is a `LIKE`. So `:query` stays bound raw and `:query_escaped` was added
alongside it, rather than escaping one parameter that three keys share.

**Why the `search_fts.sql` mirror was kept though it is inert.** No FTS candidate row can have a
`name` where the unescaped prefix pattern is true and the escaped one false - `name` is a Python
identifier, and the unicode61 tokenizer has already restricted the candidate set. Proven, not
argued: at stage 02 the mirrored line was reverted and the three test modules re-run, `159 passed`
with the clause gone. It is kept so the two files state one ordering contract rather than two, and
so a future change to the FTS/`LIKE` routing does not silently un-fix half the behaviour. This is
the same decision, for the same reason, that [find-path-shaped-query](find-path-shaped-query.md)
made for key 3 - the convention now covers two keys.

**The defect was more reachable than stage 01 claimed.** Stage 01's evidence table said a `_` query
reaches the `LIKE` path "only when FTS5 is unavailable". That holds for a *bare* query and is false
for a path-shaped one: `uv run venvaxi -v find 'Console.print_json' --package rich` logs
`DEBUG: FTS5 query failed`, because FTS5's grammar rejects the unquoted `.` before `MATCH` is
evaluated - so the query lands on the unescaped `WHERE` with its `_` intact, on every install.
`Console.print_json` is the spelling `src/venvaxi/SKILL.md` teaches an agent to type. Found at
stage 03 while verifying criterion 1, rather than inherited from the upstream evidence; it changes
no decision, but a stage that only re-confirms its own inputs is not verifying anything.

**The `[fts]` parameter passes vacuously for a `_` query**, and the tests say so rather than
implying both backends were proved. unicode61 splits `print_json` into `print` and `json`, so the
single-token competitor `printXjson` never enters the candidate set. A `%` or backslash query is
the shape that reaches `search_like.sql` under either parameter, because FTS5 rejects both with a
syntax error. This is the fixture trap [find-path-shaped-query](find-path-shaped-query.md) records
in its Notes, arriving by a second route - there the competitor was missing from the result set,
here the whole backend is the wrong one to assert against.

**`like_only` was extracted at the stage 02 review gate.** The key-2 ranking test disabled FTS with
a verbatim copy of the `search_backend` fixture's `like` branch - two copies of one degradation, in
a module whose docstring makes a point of stating one contract once. Both consumers now take a
`like_only` fixture, `search_backend` reaching it through `request.getfixturevalue`. The mutation
run was repeated after the extraction and produced an identical `7 failed, 2 passed` split, which
is what proves the extracted fixture still disables FTS rather than quietly making that test
vacuous.

**Gotcha, which cost this run twice: writing files by script on Windows.** `Path.write_text`
translates the newline to `os.linesep`, so it emits CRLF - the defect `.gitattributes` names and
`_atomic_write_bytes` exists to prevent, arriving by a third route. Stage 01 introduced CRLF into
`specs/commands/find.md` and normalised it before commit; every later write used `write_bytes`, and
every touched file was byte-checked. Separately, a shell heredoc mangled backslash escapes in a
mutation script at stage 02, and the `git checkout --` used to clean up after it reverted the
in-flight fix; the fix was re-applied and everything downstream re-run against the restored file.
Both are recorded because the next run on a Windows tree will meet them again.

## Follow-ups

- **Issue [#122](https://github.com/andyrids/venv-axi/issues/122)** - filed at this closeout.
  `_store.py` builds the FTS query as `f"{query}*"`, so a `"`, `%`, `:`, `*` or backslash in a
  query can break the MATCH grammar and route it to `LIKE`. It degrades *safely* - the existing
  `except sqlite3.OperationalError` catches it, and after this unit the fallback answers literally
  - so it reaches a correct answer by a longer path rather than a wrong one silently. What it
  costs is that an entire class of query, defined by punctuation, never receives `bm25`, and that
  the routing is undeclared. Named out of scope in this plan's Scope from stage 01 and
  deliberately not widened into: escaping the MATCH operand would change *which backend answers*
  for those queries, and with it the result set rather than only its order. Owned by no current
  plan.
- **Validation criterion 6 is a guard, not a discriminator.** The `findSymbolTool` parity test
  passes with and without the fix by construction. It is ticked above with that stated plainly, so
  a later reader does not mistake it for evidence that escaping works. No separate follow-up: the
  MCP surface genuinely has no per-surface search branch to test, and inventing one would be worse
  than the guard.
- **The `[fts]` literal-matching parameters have nothing to regress against**, because the
  tokenizer prevents the defect there. If FTS5's tokenizer configuration ever changed, those
  parameters would begin to discriminate and nothing announces the transition. Not filed: the
  tokenizer is SQLite's default and this project pins no FTS5 configuration, so there is no change
  to watch for on this side.
- **Deferred to** - none.
- **Tracked as** - none.
