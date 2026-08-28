---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/inherits.md
  - specs/mcp/tools.md
  - specs/behaviors/symbol-graph.md
  - specs/behaviors/skill-content.md
authors: []
issues: [48]
pr: 123
---

# Plan: Inherits bases direction

## Scope

An agent evaluating the published `0.3.0rc1` wheel against a consuming project needed
`rich.logging.RichHandler`'s base class. It ran the obvious command:

```text
$ venvaxi inherits rich.logging::RichHandler
count: 0
```

and read it as *no inheritance data available*. It is the correct answer to a different question -
`RichHandler` has no indexed subclasses, and the fact wanted was one edge the other way. Recovering
it meant guessing the parent first ([#48](https://github.com/andyrids/venv-axi/issues/48)).

`specs/commands/inherits.md` required the empty-state hint to name **both** causes a caller can act
on - subclasses in an unindexed package, and subclasses below the built depth. Both say *index more,
or build deeper*, and neither can succeed when the caller wanted the parent, so the hint sent a
mis-directed query off to do work that could not help. There was a third cause it did not name, and
no way to act on it if it had.

**The data was already there, and is more complete in the new direction than the old one.**
`_introspect.py` records inheritance from the subclass's side, during the walk of the subclass's own
package:

```python
for base in cls.__bases__:
    if base is object:
        continue
    base_qualified_name = qualify(base.__module__, base.__name__)
    store.upsert_edge(
        SymbolEdge(
            src=class_qualified_name,
            dst=base_qualified_name,
            kind=EdgeKind.INHERITS,
        )
    )
```

| Direction | Reads | Depends on |
| --- | --- | --- |
| subclasses (existing) | `edges.dst = X` | the *subclass's* package having been indexed |
| bases (this unit) | `edges.src = X` | only X's own package, indexed by definition |

So if `inherits X` resolves `X` at all, X's bases are already stored. No schema change, no rebuild,
no new index: `edges` is keyed `(src, dst, kind)`, so a `src` lookup rides the primary key. The cost
of this unit is surface design, not storage.

**This is an added capability, not a bug fix.** Show-it-failing applies only to the changed hint on
the existing direction; the bases direction is new behaviour, and its tests are written against the
contract stage 01 declares rather than shown failing first.

Out of scope, each with where it went:

- **MRO order.** `--bases` reports which classes are direct bases, not the order Python resolves
  them in. Recorded in `specs/commands/inherits.md` `## Out of scope`: the edge table has no
  ordinal, so declaration order is lost at write time, and recovering it is a schema change and a
  `SCHEMA_VERSION` bump.
- **Transitive ancestry.** Direct bases only, mirroring the existing direct-subclasses rule.
- **A `refresh` parameter on `getBasesTool`.** `specs/mcp/tools.md` refuses one on every read tool;
  the new tool inherits that refusal rather than arguing with it.

## Implements

Four specs, all in `specs:` because this plan changes code until it conforms to each. Three were
amended at stage 01; the fourth was not, and the distinction matters.

`specs/commands/inherits.md` - the `--bases` flag in Invocation/inputs, with the positional
re-described as the class the caller has in hand rather than "the base class". A new `### Direction`
subsection under Data requirements declares that the command reads one edge kind both ways, and that
the two directions **do not have equal reach** - a base is reported whether or not its own package
was ever indexed, a subclass is not. `### Result ordering` and `### Empty states` are new
subsections: the ordering rule is `qualified_name` ascending and explicitly *not* declaration order,
and the three distinguishable empty states each get their own criterion and their own hint.

`specs/mcp/tools.md` - `getBasesTool` as a table row, and the arithmetic moved everywhere it is
stated: the consolidation preamble (ten to eleven tools, eight to nine CLI mirrors),
`describeBindingTool`'s degrade-where-others-raise rule (nine to ten), the no-`refresh` rule (nine
to ten read tools and schemas), and the `#49` out-of-scope note, whose "without adding an eleventh
tool" phrasing this unit would have falsified. A new Divergences bullet records the split, citing
the `show`/`inspect` precedent in the same section.

`specs/behaviors/symbol-graph.md` - the edge table's `Read by` cell for `INHERITS`, plus a paragraph
naming it as the one edge read in both directions and pointing at the command spec for what the
asymmetry means.

`specs/behaviors/skill-content.md` - **read in full and deliberately not amended.** Its rules stay
true as written; what changes is `src/venvaxi/SKILL.md`, the derived artifact those rules govern.
`SKILL.md` currently states "There is no bases-of query, so running `inherits` on the class you just
resolved returns `count: 0` and reads as a dead end", which this unit falsifies, and the spec's own
rule - "Where the AXI cannot answer a class of question at all, the packaged skill shall say so
plainly" - is what makes the stale text non-conformant once the boundary moves. It sits in `specs:`
for the same reason [private-submodule-hints](private-submodule-hints.md) put it there: the plan
brings the skill back into conformance with an unchanged rule.

**Read at stage 01 and deliberately not amended**, recorded rather than assumed:

- `specs/behaviors/qualified-name-semantics.md` - `inherits` resolves through
  `SymbolStore.canonical_name` for every input, because `INHERITS` edges are keyed at the home
  frame. The bases direction resolves identically, through the same call, so nothing about the
  facade/home contract moves.
- `specs/behaviors/output-contract.md` - the bases answer is a `count` plus a table plus a hint,
  the shapes that spec already governs. `count: 0` exits `EX_OK` under its existing exit-code rule;
  no new exit path exists.
- `specs/commands/inspect.md` - mentions base classes only in its own-docstring rule (an inherited
  docstring must not be substituted). That rule is about `doc`, not ancestry, and is untouched.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. `src/venvaxi/get_bases.sql` - select the edge's `dst` for `WHERE edges.src = :qualified_name AND
   edges.kind = :kind`, ordered by `dst`. **It must not require a node row** (see Risks) - any JOIN
   used to enrich `name`/`kind` must be a `LEFT JOIN`, and the row must still be returned when the
   join finds nothing.
3. `src/venvaxi/_store.py` - `SymbolStore.get_bases`, mirroring `get_inheritors`'s `canonical_name`
   resolution. Where no node row exists for a base, derive `name` from the qualified name's tail and
   report `kind` as `class` - a base is always a class, so this is a fact about the edge rather than
   a guess about the row.
4. `src/venvaxi/_introspect.py` - a `get_bases` wrapper beside `get_inheritors`, with the same
   refresh and resolution handling.
5. `src/venvaxi/_cli.py` - the `--bases` argument on the `inherits` subparser, and the branch in
   `command_inherits` emitting the `bases` table and the `object`-only empty state. The existing
   subclasses empty-state hint gains its third cause and names `--bases`.
6. `src/venvaxi/_mcp.py` - `get_bases_tool`, registered in `_TOOLS`, taking the surface to eleven.
7. `src/venvaxi/SKILL.md` - rewrite the gotcha at the "no bases-of query" claim so it demonstrates
   `--bases` instead of a guess-the-parent workaround, and check the `inherits` worked example and
   the command table against the new flag.
8. Tests in `tests/test_store.py`, `tests/test_cli.py`, `tests/test_mcp.py` and
   `tests/test_skill_parity.py`. The cross-package case is the one that matters and must be built on
   a graph where the base's package was never walked.
9. `CHANGELOG.md` entry under `Added`, with the hint change under `Changed`.

## Validation

- [x] When `inherits` is invoked with `--bases` on a class with at least one recorded base, the
      `inherits` command shall emit `count: <n>` and a `bases` table of `name`, `kind` and
      `qualified_name` listing each direct base. —
      `tests/test_store.py::test_get_bases_indexed_base` and
      `tests/test_cli.py::test_command_inherits_bases_with_results`, both passed; also evidenced
      live by `uv run venvaxi inherits rich.table::Table --bases`, emitting exactly the three
      declared fields (stage 03 report)
- [x] Where `--bases` is given, the `inherits` command shall report a base class whose own package
      has never been indexed. —
      `tests/test_store.py::test_get_bases_unindexed_base_package`, whose fixture asserts
      `store.get_node("logging::Handler") is None` before querying; shown failing under a mutation
      of `get_bases.sql` to the naive `nodes` JOIN. Evidenced live by `uv run venvaxi inherits
      rich.logging::RichHandler --bases` returning `logging::Handler` against a cache whose build
      list has no `logging`, re-checked after the run (stage 03 report)
- [x] Where `--bases` is given and the named class has no recorded base, the `inherits` command
      shall emit `count: 0` with a hint naming **both** causes - derivation from `object`, and a
      base's package refreshed since this class was indexed - naming `--refresh` on the named
      class's own package as the recovery for the second, and shall exit `EX_OK`. —
      `tests/test_cli.py::test_command_inherits_bases_empty_hint_names_both_causes` and
      `tests/test_mcp.py::test_get_bases_tool_empty_hint_names_both_causes`; evidenced live by
      `uv run venvaxi inherits rich.console::Console --bases` (exit `0`). The recovery was traced
      to `_build_store_for(qualified_name, refresh=refresh)`, which rebuilds the named class's own
      package - the walk that wrote the edge (stage 03 report)
- [x] When a base's package is cleared after the named class was indexed, the `inherits` command
      with `--bases` shall emit `count: 0`, and shall not assert that the class derives from
      `object`. — `tests/test_store.py::test_get_bases_after_base_package_cleared`. **This pins a
      limitation, not a fix**: it passes against unchanged store code because `clear_package`'s
      over-deletion is still present; what changed is that the surface no longer mis-describes its
      effect. Read as 'the edge survives a refresh' this tick would be exactly backwards. The
      surface half is satisfied by the hint being a disjunction rather than an assertion (stage 03
      report, Finding 2)
- [x] When `inherits` is invoked without `--bases` and the named class has zero indexed subclasses,
      the `inherits` command shall emit a hint naming three causes, one of which names
      `inherits <qualified_name> --bases`. — evidenced live by `uv run venvaxi inherits
      rich.logging::RichHandler`, the exact command #48 reports, which now prints the
      wrong-direction cause and its recovery; running that recovery is criterion 2 (stage 03
      report)
- [x] The `inherits` command shall order both tables by `qualified_name` ascending, and two runs
      against the same graph shall return the same rows in the same order. —
      `tests/test_store.py::test_get_bases_ordered_by_qualified_name`, which seeds edges
      non-alphabetically (`zpkg`, `apkg`, `mpkg`) so a rowid or insertion-order implementation
      fails, and asserts two successive calls are identical (stage 03 report)
- [x] If the named class does not resolve, then the `inherits` command shall raise
      `SymbolNotFoundError` and exit `EX_FAILURE`, whether or not `--bases` was given. —
      `tests/test_cli.py::test_command_inherits_bases_propagates_not_found`; evidenced live by
      `uv run venvaxi inherits rich.console::Nonexistent --bases`, emitting the TOON error block
      and exiting `1` (stage 03 report)
- [x] When `getBasesTool` is called with a `qualified_name`, it shall return the same rows in the
      same order as the `inherits` command invoked with that name and `--bases`. —
      `tests/test_mcp.py::test_get_bases_tool_returns_toon`, plus an in-process run against the
      real `build_server` (no mock) comparing `get_bases` output with the tool's, confirming the
      same rows in the same order (stage 03 report)
- [x] The MCP server shall register eleven tools, including `getBasesTool`. —
      `build_server().list_tools()` returns exactly eleven, `getBasesTool` among them, enumerated
      in full in the stage 03 report
- [x] When `inherits` is invoked without `--bases` on a class with indexed subclasses, the
      `inherits` command shall return the same rows in the same order as it did before this change.
      — all 531 pre-existing tests pass unchanged and the conformance tier passes `21 passed`; also
      evidenced live by `uv run venvaxi inherits rich.progress::ProgressColumn` still emitting
      `count: 11`, the figure `src/venvaxi/SKILL.md` documents (stage 03 report)
- [x] The packaged skill shall not claim that no bases-of query exists. —
      `tests/test_skill_parity.py::test_no_bases_of_query_denial`; `grep -c "no bases-of query"
      src/venvaxi/SKILL.md` returns `0`, the replacement states the two causes, and both copies are
      `cmp`-identical (stage 03 report)
- [x] The test suite shall pass. — `uv run coverage run -m pytest` → `545 passed, 21 deselected in
      70.41s (0:01:10)`, coverage `98%` (1377 statements, 24 missed); `uv run pytest -m
      conformance` → `21 passed, 545 deselected`; `pkgdx-lint-hook`, `pkgdx-format-hook`,
      `pkgdx-typing-hook -p venvaxi` and `pkgdx-markdown-hook` all exit `0` (stage 03 report)

## Risks / unknowns

- **A JOIN would silently reproduce the bug being fixed.** `get_inheritors.sql` joins `nodes` on the
  edge endpoint, and the walk writes the INHERITS *edge* for every base but **no node row** for a
  base whose package was never indexed - `_introspect.py` leaves a cross-package home alone so
  `clear_package` for one package cannot delete another's node. A bases query mirroring that JOIN
  would drop exactly the cross-package cases this unit exists to serve, including the issue's own
  `RichHandler` to `logging::Handler` example, and it would drop them *silently*, as a plausible
  `count: 0`. This is the single most likely way to implement this unit wrongly and have every
  hand-written fixture still pass; validation criterion 2 exists for it alone, and its fixture must
  seed the base's package as absent rather than present.
- **The `object` empty state's definitiveness did not hold, and the spec was wrong before it was
  corrected.** This risk was written as a conditional - "if that implication ever fails, the hint
  would assert something false" - and stage 02 found the route by which it fails. `clear_package`
  deletes every edge with the cleared package's node at either end, so refreshing a *base's* package
  strips an edge the *subclass's* walk wrote, leaving the subclass node in place with no ancestry.
  Resolved by re-entering stage 01 and naming both causes in the hint; see Notes. The residual risk
  is that a later reader restores the shorter, wrong claim because it reads better - which is why
  the spec now states the counter-example rather than only the rule.
- **Declaration order is lost at write time**, so the ordering contract cannot claim MRO order. The
  spec states `qualified_name` ascending and says why. The risk is an implementer "improving" this
  later by ordering on rowid or insertion order, which would look like declaration order on a fresh
  cache and diverge on a refreshed one.
- **Eleven tools changes an arithmetic stated in six places** in `specs/mcp/tools.md`. All six were
  moved at stage 01 and are listed in Implements; a seventh left behind would be a spec
  contradicting itself. Stage 03 re-greps rather than trusting the list.
- **`SKILL.md` is byte-identical in three locations** - the packaged source, the installed copy
  `venvaxi setup` writes, and this repository's own `.claude/skills/venvaxi/SKILL.md`. Editing one
  and not the others is a parity failure `tests/test_skill_parity.py` exists to catch, and the
  gotcha edit touches text that has already been corrected once
  ([skill-gotcha-corrections](skill-gotcha-corrections.md)).
- **`Path.write_text` on Windows emits CRLF**, the defect `.gitattributes` names. Any file written
  by script this run must use explicit LF and be byte-checked - it cost the previous run twice
  ([find-literal-query](find-literal-query.md) Notes).

## Notes

**The data was already there, and is more complete in the new direction than the old one.** This is
the finding that made the unit small. `_walk_class_members` records inheritance from the
*subclass's* side, iterating `cls.__bases__` during the walk of the subclass's own package, so the
two directions have different reach:

| Direction | Reads | Depends on |
| --- | --- | --- |
| subclasses | `edges.dst = X` | the *subclass's* package having been indexed |
| bases | `edges.src = X` | only X's own package, indexed by definition |

If `inherits X` resolves `X` at all, its bases are already stored. No schema change, no rebuild, no
new index - `edges` is keyed `(src, dst, kind)`, so a `src` lookup rides the primary key.
`SCHEMA_VERSION` stays 8: nothing about what is *stored* moved, only what is read back.

**Why `get_bases.sql` does not JOIN `nodes`, which is the whole unit in one decision.**
`get_inheritors.sql` joins `nodes` on the edge endpoint. The walk writes the `INHERITS` edge for
every base but **no node row** for a base homed in a package it is not walking - deliberately, since
claiming that node's `package` field would let `clear_package` for one package delete another's row.
A bases query mirroring that JOIN would therefore drop exactly the cross-package cases this unit
exists to serve, including the issue's own `RichHandler` to `logging::Handler`, and drop them
silently as a plausible `count: 0`. So the query reads `edges` alone and derives each row: `kind` is
`class` - a fact about the edge, not a guess about a missing row - and `name` is the tail after
`::`. Verified by mutation at the stage 02 gate: swapping in the naive JOIN fails three tests,
`test_get_bases_unindexed_base_package` among them, while `test_get_bases_indexed_base` still
passes. That last part is the point - a both-nodes fixture would have passed the wrong
implementation and proved nothing.

**Why the ordering is `qualified_name` and explicitly not declaration order.** The walk iterates
`cls.__bases__` in order, but `edges` has no ordinal column, so MRO order is lost at write time.
Ordering on rowid or insertion order would *resemble* declaration order on a fresh cache and diverge
after a refresh - a claim the stored data cannot support. The spec says so, and
`test_get_bases_ordered_by_qualified_name` seeds edges non-alphabetically so that implementation
fails rather than passing by luck.

**Why a CLI flag but a separate MCP tool.** Not a new decision: `specs/mcp/tools.md` already records
that `show --api` is a CLI boolean while MCP splits it into `showPackageTool` /
`showPackageApiTool`, "because a typed tool schema should not hide two different return shapes
behind one parameter". `inherits --bases` and `getBasesTool` apply the same rule. The extra reason
here is the asymmetric reach above: a boolean on one schema would hide it behind a parameter a
caller sets without reading, and the wrong default is the silent dead end #48 reports.

**`top_level_root` was promoted rather than imported.** `get_bases_tool`'s hint needed a package
root, and hand-rolled the two splits - on `::` then on the first dot - character-for-character what
`_introspect._top_level_root` already did, with a docstring covering that exact input shape.
The obvious fix was the wrong one: importing it under its private name would have been the first
cross-module private import in `src/` (checked - only `tests/test_introspect.py` reaches for
underscore-prefixed names, which is ordinary for testing internals). So the helper was made public.
Six occurrences, all in `_introspect.py`, none in tests, and the module declares no `__all__` - the
`__all__` matches in that file are `getattr(module, "__all__", ...)` reading the *walked* module's
exports. Equivalence proven over five input shapes before the substitution; the suite is 545 either
side.

**Stage 01 re-entry, from stage 02.** Recorded here as `ICM/process-plan/CONTEXT.md` requires: a
decision that changes observable behaviour returns to the earliest stage whose output it
invalidates, and only the delta is re-run.

Stage 01 declared the `--bases` empty state **definitive** - "a resolved class was walked, and a
walk records every base except `object`, so zero base edges means there is nothing further to
find" - and required its hint to offer no recovery. Stage 02 found that false and, correctly, did
not patch it: `SymbolStore.clear_package(A)` deletes every edge whose `src` *or* `dst` is one of
A's nodes, and a base edge is written from the subclass's side. Refreshing a base's package
therefore deletes an edge another package's walk recorded, while that package's class node
survives. Until the subclass is itself rebuilt, `--bases` answers `count: 0` and the hint asserted
a derivation from `object` that is false.

Reproduced directly against `SymbolStore` at the stage 02 review gate, on a temporary database:

```text
before clear_package('alib'):  bases of blib.impl::Sub -> ['alib.core::Base']
after  clear_package('alib'):  bases of blib.impl::Sub -> []
                               blib.impl::Sub node still present -> True
```

The distinction that makes this worth a re-entry rather than a note: the subclasses direction loses
the same edges today and merely **under-reports**, which its hint already covers by naming causes it
cannot rule out. The bases hint **mis-asserted** - a confident wrong answer, which is the one
failure shape this project exists to eliminate. A spec that requires a false statement is not a
spec the code can conform to.

The delta re-run: `specs/commands/inherits.md` (`### Empty states` names both causes and states the
counter-example; `### Direction` no longer implies the answer is beyond recovery), this plan's
Validation criterion 3 and its new criterion 4, this plan's Risks, and the stage 02 code and tests
that carried the claim - the CLI branch, the MCP tool, and the packaged skill.

Not taken: changing `clear_package` to stop deleting by `dst`. It is arguably the principled fix -
the edge is the subclass package's recorded fact, and the code already guards this exact hazard for
*nodes* (`_walk_class_members` refuses to claim a cross-package node so `clear_package` cannot
delete another package's row) while leaving the edge case unguarded. But it changes shared refresh
machinery every command depends on, and it earns its own unit with its own verification, on the same
reasoning that kept the bases direction out of #48's resolution 1. Filed as a follow-up.

## Follow-ups

- **Issue [#124](https://github.com/andyrids/venv-axi/issues/124)** - filed at this closeout.
  `SymbolStore.clear_package(A)` deletes every edge whose `src` **or `dst`** is one of A's nodes, so
  refreshing package A deletes package B's `INHERITS` edge into A - a fact B's walk recorded - while
  B's class node survives. Until B is rebuilt, `--bases` under-reports. The code already guards this
  exact hazard for *nodes*, and leaves it unguarded for edges. Not taken here: it changes shared
  refresh machinery every command depends on and deserves its own unit with its own verification,
  on the same reasoning that kept the bases direction out of #48's resolution 1. This unit's
  response was to stop the surface mis-describing the state, not to fix the state.
- **Validation criterion 4 pins a limitation, not a fix**, and its tick says so. It passes against
  unchanged store code; what this unit changed is that the hint no longer asserts `object` when the
  cause may be the deletion above. A future reader who takes the green tick as evidence that the
  edge survives a refresh would have it backwards, and would then 'simplify' the two-cause hint back
  to the wrong one-cause version - which is exactly the path stage 01 had to be re-entered to
  correct.
- **MRO order** - named out of scope in `specs/commands/inherits.md`. `--bases` reports which
  classes are direct bases, not the order Python resolves them in; recording it needs an ordinal on
  the edge and a `SCHEMA_VERSION` bump. Not filed: no caller has asked, and a caller needing the
  true MRO reads it from the class.
- **Deferred to** - none.
- **Tracked as** - none.
