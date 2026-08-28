---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/commands/inherits.md
  - specs/mcp/tools.md
  - specs/behaviors/symbol-graph.md
  - specs/behaviors/skill-content.md
authors: []
issues: [48]
pr:
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

- [ ] When `inherits` is invoked with `--bases` on a class with at least one recorded base, the
      `inherits` command shall emit `count: <n>` and a `bases` table of `name`, `kind` and
      `qualified_name` listing each direct base.
- [ ] Where `--bases` is given, the `inherits` command shall report a base class whose own package
      has never been indexed.
- [ ] Where `--bases` is given and the named class has no recorded base, the `inherits` command
      shall emit `count: 0` with a hint naming **both** causes - derivation from `object`, and a
      base's package refreshed since this class was indexed - naming `--refresh` on the named
      class's own package as the recovery for the second, and shall exit `EX_OK`.
- [ ] When a base's package is cleared after the named class was indexed, the `inherits` command
      with `--bases` shall emit `count: 0`, and shall not assert that the class derives from
      `object`.
- [ ] When `inherits` is invoked without `--bases` and the named class has zero indexed subclasses,
      the `inherits` command shall emit a hint naming three causes, one of which names
      `inherits <qualified_name> --bases`.
- [ ] The `inherits` command shall order both tables by `qualified_name` ascending, and two runs
      against the same graph shall return the same rows in the same order.
- [ ] If the named class does not resolve, then the `inherits` command shall raise
      `SymbolNotFoundError` and exit `EX_FAILURE`, whether or not `--bases` was given.
- [ ] When `getBasesTool` is called with a `qualified_name`, it shall return the same rows in the
      same order as the `inherits` command invoked with that name and `--bases`.
- [ ] The MCP server shall register eleven tools, including `getBasesTool`.
- [ ] When `inherits` is invoked without `--bases` on a class with indexed subclasses, the
      `inherits` command shall return the same rows in the same order as it did before this change.
- [ ] The packaged skill shall not claim that no bases-of query exists.
- [ ] The test suite shall pass.

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

## Follow-ups
