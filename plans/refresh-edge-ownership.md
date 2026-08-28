---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/cache-refresh.md
  - specs/commands/inherits.md
  - specs/behaviors/skill-content.md
authors: []
issues: [124]
pr:
---

# Plan: Refresh edge ownership

## Scope

Refreshing one package deletes another package's recorded inheritance, and the graph gives no sign
that it happened. `SymbolStore.clear_package` deletes every edge with the cleared package's node at
**either** end, but an `INHERITS` edge is written from the **subclass's** side, by the walk of the
subclass's own package. So clearing package A deletes an edge package B's walk recorded, while B's
class node survives untouched, and A's rebuild cannot restore it - the edge was never A's to write
([#124](https://github.com/andyrids/venv-axi/issues/124)).

The trigger is ordinary. Index a package that subclasses another indexed package, then `--refresh`
the base's package. Until the subclass's package is itself rebuilt, its ancestry is missing:

```text
before clear_package('alib'):  bases of blib.impl::Sub -> ['alib.core::Base']
after  clear_package('alib'):  bases of blib.impl::Sub -> []
                               blib.impl::Sub node still present -> True
```

**The code already guards this exact hazard one level up, and only for nodes.**
`_walk_class_members` refuses to claim a node for a cross-package home, and says why: claiming its
`package` field would let `clear_package` for one package delete another package's node. The same
hazard for *edges* is unguarded, and the `dst` arm is where it bites.

**This is the deferred half of [inherits-bases-direction](inherits-bases-direction.md).** That unit
found the defect at stage 02, re-entered stage 01 over it, and deliberately did not fix it - it
changes shared refresh machinery every command depends on, and its Notes say it earns its own unit
with its own verification. Its response was to stop the surface mis-describing the state, not to
fix the state: the `--bases` empty-state hint was widened from one cause to a two-cause disjunction
offering a rebuild as recovery, and that widening was carried into the MCP tool, the packaged skill
and `specs/commands/inherits.md`. Fixing the state retires all four.

So this unit has two halves, and the second is only safe because of the first:

1. **The fix** - a refresh deletes what its own walk recorded, and nothing else.
2. **The reversal** - the `--bases` empty state returns to a single definitive cause, on every
   surface that carries it.

Out of scope, each with where it went:

- **Collecting edges left without an endpoint.** Clearing a package can leave an edge whose
  endpoint has no node, in both directions, and nothing sweeps them. Declared in
  `specs/behaviors/cache-refresh.md` under Edges outliving their endpoints (harmless by
  construction) and named as the third unbounded-growth direction in its Out of scope. Not filed:
  an edge write is idempotent on its `(src, dst, kind)` identity, so a rebuild reuses the row
  rather than adding one.
- **A stale edge from a re-exported cross-package home.** Where package B re-exports a class homed
  in package A, B's walk keys that class's edges at A's name while claiming no node there, so
  neither deletion arm reaches those edges today. A base that A dropped between versions can
  therefore persist until A is itself indexed and refreshed. **Pre-existing and unchanged by this
  unit** - the `dst` arm never reached those edges either. Named here so stage 02 recognises it as
  out of scope rather than as a regression it caused.
- **MRO order** - `specs/commands/inherits.md` already records it as out of scope, and this unit
  does not move it.

## Implements

Three specs, all in `specs:` because this plan changes code until it conforms to each. Two were
amended at stage 01; the third was not, and the distinction matters.

`specs/behaviors/cache-refresh.md` - two new subsections and two amendments. **Refresh scope:
edges** declares what a refresh promises about *other* packages' edges, which was undeclared and is
why the defect was reachable: an edge is owned by the walk that recorded it, ownership is carried
by the origin endpoint and never by the target, and a clear deletes only what it owns. **Edges
outliving their endpoints** declares the consequence - an edge can survive its endpoint's node in
either direction - and pins why that is harmless: a read either joins a symbol record at the
endpoint it reports, or reports the endpoint's name, which stays true whether or not that package
was ever indexed. **Schema version covers the builder, not just the shape** gains a second trigger:
the bump condition is what the store ends up *holding*, so a change to what a clear removes counts
alongside a change to what a walk records. **Out of scope** gains edges as a third unbounded-growth
direction.

`specs/commands/inherits.md` - the reversal, written as a conditional claim rather than a
simplification. The `--bases` empty state returns to one cause and offers no recovery, and the
Direction section drops the recovery clause pointing at it. The counter-example paragraph is
**rewritten, not deleted**: the definitiveness is now stated as holding *because* a refresh no
longer deletes another walk's edges, with the pre-#124 behaviour recorded as the reason the hint
was widened, and a standing instruction that any change widening what a refresh deletes returns to
this section first.

`specs/behaviors/skill-content.md` - **read in full and deliberately not amended.** Its rules stay
true as written; what changes is `src/venvaxi/SKILL.md`, the derived artifact those rules govern.
The skill currently teaches that a `--bases` `count: 0` has two causes and names a `--refresh`
recovery, which this unit falsifies. It sits in `specs:` for the same reason
[inherits-bases-direction](inherits-bases-direction.md) and
[private-submodule-hints](private-submodule-hints.md) put it there: the plan brings the skill back
into conformance with an unchanged rule.

**Read at stage 01 and deliberately not amended**, recorded rather than assumed:

- `specs/behaviors/symbol-graph.md` - declares the edge kinds and which command reads each. Edge
  *ownership* is a property of the refresh, not of the graph's shape, and nothing about what an
  edge means or who reads it moves here. The one sentence that could have belonged - that an
  `INHERITS` edge is recorded from the subclass's side - is already there.
- `specs/behaviors/qualified-name-semantics.md` - already forbids claiming a foreign class's node
  for exactly this reason, and the new cache-refresh section cites it rather than restating it.
- `specs/mcp/tools.md` - `getBasesTool`'s contract is unchanged. Only its empty-state hint text
  moves, and that text is governed by `specs/commands/inherits.md`, which the tool mirrors.
- `specs/behaviors/output-contract.md` - `count: 0` still exits `EX_OK` and the hint is still a
  help block. No output shape moves.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. **Discharge the proof obligation before changing anything.**
   [#124](https://github.com/andyrids/venv-axi/issues/124) requires that no query relied on the
   `dst` deletion be established rather than assumed. Inventory every edge write in
   `src/venvaxi/_introspect.py` against every edge read (`get_children.sql`,
   `get_inheritors.sql`, `get_bases.sql`) and record the result in the stage 02 report. Stage 01
   traced it and expects: for every edge a walk writes, `src` is either the walked module or the
   class's home name, so the `src` arm alone removes everything the cleared package owns; and
   `EXPORTS`/`IMPORTS_FROM` are written but never read. **Re-derive this - do not copy it.** If the
   inventory disagrees with stage 01, that is a stage 01 re-entry, not a patch.
3. `src/venvaxi/_store.py` - `clear_package` deletes edges by `src` only. Statement order is
   unchanged and load-bearing: edges first, `package_builds` next, `nodes` last, because the
   sub-select reads `nodes`.
4. `src/venvaxi/_store.py` - `SCHEMA_VERSION` 8 to 9, its docstring gaining the second trigger to
   match the amended spec. This is what makes step 6 safe; see Risks.
5. `tests/test_store.py::test_get_bases_after_base_package_cleared` **inverts.** It currently
   asserts `store.get_bases("blib.impl::Sub") == []` after `store.clear_package("alib")`, and its
   docstring says it pins a limitation. Post-fix it asserts the base survives, and the docstring is
   rewritten to say what it now pins. Its fixture already seeds the cross-package case correctly.
6. `src/venvaxi/_cli.py` (`_command_inherits_bases`) and `src/venvaxi/_mcp.py` (`get_bases_tool`) -
   single-cause hint, no recovery offered. The `NOTE:`/comment above each explains the reversal and
   cites the spec section, so the next reader finds the condition and not only the conclusion.
7. `src/venvaxi/SKILL.md` - rewrite the `--bases` gotcha's two-cause claim. Byte-identical in three
   locations; see Risks.
8. Tests in `tests/test_store.py`, `tests/test_cli.py`, `tests/test_mcp.py` and
   `tests/test_skill_parity.py`. The cases that matter clear one package and do not rebuild it - a
   fixture holding both packages passes either implementation.
9. `CHANGELOG.md` - the deletion under `Fixed`, the hint and `SCHEMA_VERSION` under `Changed`.

## Validation

- [ ] When a package is cleared, the store shall delete every edge whose origin is one of that
      package's symbols.
- [ ] When a package is cleared, the store shall retain an `INHERITS` edge recorded by another
      package's walk whose target is one of the cleared package's symbols.
- [ ] When a base's package is cleared after the named class was indexed, the `inherits` command
      with `--bases` shall still report that base.
- [ ] When a base's package is cleared after a subclass was indexed, the `inherits` command without
      `--bases` shall still report that subclass.
- [ ] Where `--bases` is given and the named class has no recorded base, the `inherits` command
      shall emit `count: 0` plus a hint naming exactly one cause - direct derivation from `object` -
      offering no recovery, and shall exit `EX_OK`.
- [ ] When `getBasesTool` is called on a class with no recorded base, it shall return the same
      single-cause hint, naming no recovery.
- [ ] The packaged skill shall not claim that a `--bases` `count: 0` has more than one cause, and
      all copies of `SKILL.md` shall remain byte-identical.
- [ ] When a store recorded at the previous schema version is opened, the store shall drop and
      rebuild its tables and record the current schema version.
- [ ] When a package graph is queried with no package having been cleared, `show --api`, `find`,
      `tree`, `inspect` and `inherits` shall return the same results as before this change.
- [ ] The test suite and the conformance tier shall pass.

## Risks / unknowns

- **This is shared refresh machinery.** `clear_package` runs before every rebuild
  (`src/venvaxi/_cache.py`), so every command accepting `--refresh` depends on it. The mitigation is
  Approach step 2 - the inventory is re-derived at stage 02, not inherited from this file - and the
  second-to-last Validation criterion, which exists to catch a read that quietly relied on the
  deletion.
- **The most likely wrong implementation passes every fixture that seeds both packages.** A test
  that clears a package and then rebuilds it, or one whose graph holds a single package, cannot
  distinguish the two arms. Every criterion above naming a cleared package needs a fixture that
  clears and does **not** rebuild. Verify by mutation at the stage 02 gate: restore the `dst` arm
  and confirm criteria 2, 3 and 4 fail while the rest pass.
- **The reversal is indistinguishable, in the diff, from a mistake this project has already warned
  itself about.** [inherits-bases-direction](inherits-bases-direction.md) Follow-ups says a future
  reader might simplify the two-cause hint back to the wrong one-cause version, and calls that
  exactly the path stage 01 had to be re-entered to correct. That warning is against reverting
  *without* fixing the state. Two things make this reversal the legitimate one, and both must land
  or neither does: the deletion is fixed, and `SCHEMA_VERSION` is bumped so no cache written under
  the old deletion scope survives to falsify the claim. **A reversal without the bump is the
  warned-against change.** The spec states the condition rather than only the conclusion for the
  same reason.
- **The schema bump is a judgement, and its cost is real.** Every user's cache rebuilds once on
  first use after upgrade. Accepted: `specs/behaviors/cache-refresh.md` declares caches disposable
  derived data, and the alternative is an installed base carrying gaps the new code can neither
  produce nor detect. The amended bump trigger is what makes this a rule rather than a one-off call.
- **`SKILL.md` is byte-identical in three locations** - the packaged source, this repository's
  `.claude/skills/venvaxi/SKILL.md`, and the copy `venvaxi setup` writes. Editing one and not the
  others is a parity failure `tests/test_skill_parity.py` exists to catch, and this is the third
  unit in a row to edit the same gotcha
  ([skill-gotcha-corrections](skill-gotcha-corrections.md),
  [inherits-bases-direction](inherits-bases-direction.md)).
- **`Path.write_text` on Windows emits CRLF**, the defect `.gitattributes` names. Any file written
  by script this run must use explicit LF and be byte-checked - it cost two previous runs
  ([find-literal-query](find-literal-query.md) Notes).

## Notes

## Follow-ups
