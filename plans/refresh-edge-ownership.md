---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/cache-refresh.md
  - specs/commands/inherits.md
  - specs/behaviors/skill-content.md
authors: []
issues: [124]
pr: 125
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

- [x] When a package is cleared, the store shall delete every edge whose origin is one of that
      package's symbols. — `tests/test_store.py::test_clear_package_removes_edges_it_owns`, which
      asserts `SELECT src, dst, kind FROM edges` is empty after the clear rather than asserting
      through a reader
- [x] When a package is cleared, the store shall retain an `INHERITS` edge recorded by another
      package's walk whose target is one of the cleared package's symbols. —
      `tests/test_store.py::test_clear_package_keeps_a_foreign_walks_inherits_edge`; corroborated on
      a copy of the real cache, where replaying the pre-#124 two-arm `DELETE` for `logging` emptied
      `rich.logging::RichHandler`'s bases while its node survived
- [x] When a base's package is cleared after the named class was indexed, the `inherits` command
      with `--bases` shall still report that base. —
      `tests/test_store.py::test_get_bases_after_base_package_cleared` (inverted this unit); live,
      `uv run venvaxi show logging --api --refresh` then
      `uv run venvaxi inherits rich.logging::RichHandler --bases` returns `count: 1`,
      `logging::Handler`
- [x] When a base's package is cleared after a subclass was indexed, the `inherits` command without
      `--bases` shall still report that subclass. —
      `tests/test_store.py::test_get_inheritors_after_base_package_cleared`; live, after the same
      refresh `uv run venvaxi inherits logging::Handler` returns `count: 10` including
      `rich.logging::RichHandler`
- [x] Where `--bases` is given and the named class has no recorded base, the `inherits` command
      shall emit `count: 0` plus a hint naming exactly one cause - direct derivation from `object` -
      offering no recovery, and shall exit `EX_OK`. —
      `tests/test_cli.py::test_command_inherits_bases_empty_hint_names_one_cause`, which asserts the
      widened form absent as well as the single-cause form present; live,
      `uv run venvaxi inherits rich.console::Console --bases` returns `count: 0`, one help line and
      `exit=0`
- [x] When `getBasesTool` is called on a class with no recorded base, it shall return the same
      single-cause hint, naming no recovery. —
      `tests/test_mcp.py::test_get_bases_tool_empty_hint_names_one_cause`; checked as *same* rather
      than similar, the help text being byte-identical to the CLI's apart from the qualified-name
      substitution, with no rebuild tool named
- [x] The packaged skill shall not claim that a `--bases` `count: 0` has more than one cause, and
      all copies of `SKILL.md` shall remain byte-identical. —
      `tests/test_skill_parity.py::test_no_bases_two_cause_claim`,
      `tests/test_skill_parity.py::test_installed_skill_matches_packaged` and
      `tests/test_skill_parity.py::test_install_skill_is_noop_against_repo_copy`; all three copies
      22172 bytes, `sha 4ca411ee159637c6`, no CRLF
- [x] When a store recorded at the previous schema version is opened, the store shall drop and
      rebuild its tables and record the current schema version. —
      `tests/test_store.py::test_schema_version_8_wider_deletion_scope_evicted_on_open`; observed
      live in the criterion 9 A/B, after which `uv run venvaxi cache` reports `schema_version: 9`
      with the pre-A/B builds gone
- [x] When a package graph is queried with no package having been cleared, `show --api`, `find`,
      `tree`, `inspect` and `inherits` shall return the same results as before this change. —
      an A/B, not the suite: `git archive HEAD^ src` extracted and run against the same venv via
      `PYTHONPATH`, then the same six invocations under each tree; `diff old.txt new.txt` is
      byte-identical, 133 lines each
- [x] The test suite and the conformance tier shall pass. — `uv run coverage run -m pytest` returns
      `550 passed, 21 deselected`; `uv run pytest -m conformance` returns
      `21 passed, 550 deselected`; the four `prek` hooks pass

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

**Why ownership rides the origin endpoint and never the target.** An edge is a fact some walk
recorded, and the walk that recorded it is the only one that can record it again.
`_walk_class_members` iterates `cls.__bases__` while walking the *subclass's* package, so the
`INHERITS` edge `blib.impl::Sub -> alib.core::Base` is `blib`'s fact, keyed at `blib`'s end. The
target is merely a name that fact points at; the package owning that name never wrote the row and
cannot rewrite it. Deleting by `dst` therefore deleted what a clear had no standing to delete *and*
no way to restore - the rebuild of `alib` never visits `Sub`. Origin is the only endpoint where
'delete what this walk recorded' and 'delete rows keyed at this package' are the same set, which is
why the rule in `specs/behaviors/cache-refresh.md` (Refresh scope: edges) is stated as a property of
the origin rather than as a special case for `INHERITS`. The code already reasoned this way one
level up and only for nodes: `_walk_class_members` refuses to claim a node for a cross-package home
precisely so a clear for one package cannot delete another's row. This unit extends the same
reasoning to edges.

**The edge-ownership inventory, re-derived at stage 02 rather than inherited.**
[#124](https://github.com/andyrids/venv-axi/issues/124) required that no read relied on the `dst`
deletion be established, not assumed, and the plan made that Approach step 2. Six edge writes in
`src/venvaxi/_introspect.py`, three readers, all in `.sql` and none inline:

- Every `src` a walk writes is either the walked module (`CONTAINS` from `_record_symbol` and
  `_walk_submodules`, plus `EXPORTS` and `IMPORTS_FROM`) or the class's home name (`CONTAINS` and
  `INHERITS` from `_walk_class_members`), and in both cases the walk claims a `nodes` row at that
  name carrying `package`. So the `src` arm alone removes everything a cleared package owns.
- `get_children.sql` joins `nodes` on `dst` and cannot observe the difference; `get_inheritors.sql`
  joins on `src`, whose node is intact by construction, so it cannot return a phantom;
  `get_bases.sql` reads `edges` alone and reports the endpoint's *name*, which is the same mechanism
  by which `--bases` already reports a base whose package was never indexed.
- `EXPORTS` and `IMPORTS_FROM` are written and never read; `DEPENDS_ON` is defined and never
  written. Nothing relied on the `dst` arm.

The one exception is a class whose home is in another package: the walk deliberately claims no node
there, so those edges were unreachable by *either* arm before this change and remain so. That is the
re-exported cross-package home named out of scope - pre-existing and untouched. The inventory agreed
with stage 01 row for row, so there was no stage 01 re-entry.

**Why the `SCHEMA_VERSION` bump is what makes the hint reversal safe, and how a future reader tells
this reversal from the wrong one.** [inherits-bases-direction](inherits-bases-direction.md)
Follow-ups warns that a future reader might 'simplify' the two-cause hint back to the wrong
one-cause version, and calls that exactly the path stage 01 had to be re-entered to correct. That
warning is answered here rather than ignored, and the answer is that it was a warning against
reverting *without fixing the state*. Two things make this reversal the legitimate one and both
landed together: the deletion is fixed, and `SCHEMA_VERSION` went 8 to 9 so no cache written under
the old deletion scope survives the upgrade. Without the bump the code would be correct and the
installed data would not - a cache carrying a gap the old clear made would answer `count: 0`, and
the new hint would assert derivation from `object` over an ancestry a previous clear had removed.
That is a confident wrong answer, the one failure shape this project exists to eliminate. **A
reversal without the bump is the warned-against change.** The diff is how they are told apart: this
one moves `_store.py` as well as the hint. `specs/commands/inherits.md` states the definitiveness as
conditional for the same reason, with a standing instruction that any change widening what a refresh
deletes returns there first, and the `NOTE:` at each of the two code surfaces states that condition
rather than only the conclusion.

**The bump is a content bump, not a shape one.** `schema.sql` is untouched and no table moved. It is
covered by the amended trigger in `specs/behaviors/cache-refresh.md` (Schema version covers the
builder, not just the shape), which now reads on what the store ends up *holding* - so a change to
what a clear removes counts alongside a change to what a walk records. That is what makes this a
rule rather than a one-off call. The cost is real and accepted: every user's cache rebuilds once on
first use after upgrade, against an installed base that would otherwise carry gaps the new code can
neither produce nor detect.

**The mutation check was run, and showed what the plan predicted.** Risks says the most likely wrong
implementation passes every fixture that seeds both packages, so the `dst` arm was restored at the
stage 02 gate and the suite re-run: `3 failed, 547 passed, 21 deselected`. The three failures are
criteria 2, 3 and 4 - `test_clear_package_keeps_a_foreign_walks_inherits_edge`,
`test_get_bases_after_base_package_cleared` and `test_get_inheritors_after_base_package_cleared`.
Criterion 1's `test_clear_package_removes_edges_it_owns` passes under *both* implementations, which
is correct: it pins what a clear must still remove, not what it must now keep. Criteria 5 to 8 pass
under both too, since the hint, the skill and the schema bump are not what the deletion scope
decides. Every fixture serving criteria 2, 3 and 4 clears `alib` and never rebuilds it.

**Criterion 9 was discharged by an A/B against `HEAD^`, not by a green suite.** It claims equality
with the previous implementation, and a green suite only says the assertions already written down
still hold - it cannot see a behaviour nobody asserted. So stage 03 extracted the pre-change tree
with `git archive HEAD^ src`, confirmed the old module was the one loading (`SCHEMA_VERSION = 8`,
the `dst IN (...)` disjunct present), and ran the same six invocations under each tree from a cache
the schema thrash had just evicted, so both built from scratch. `diff` reports the two 133-line
transcripts byte-identical across `show --api`, `find`, `tree`, `inspect` and both `inherits`
directions. The only place output differs is the `--bases` `count: 0` hint, which is the intended
change under criterion 5 and not a same-results case.

**One real side effect of the run, outside the working tree.** Stage 03 indexed `logging` into this
repository's own cache (`~/.venvaxi/e549deaa9776dc38.db`) so that the criteria 3 and 4 live runs
cleared a real indexed base package rather than one that was never there, and the criterion 9 A/B
then evicted that build through the schema thrash. Cache contents are disposable derived data by
`specs/behaviors/cache-refresh.md`, so nothing needs restoring - but it is a state change this run
made, and it is recorded rather than left implicit.

**`CHANGELOG.md` carries three entries, one of them a correction.** The defect is under `Fixed`; the
hint reversal and the schema bump are two entries under `Changed`. The existing `Added` bullet for
`--bases` described the two-cause hint, and since it is unreleased and that hint never reached a
release in that form, it was corrected in place rather than left to be contradicted by the `Changed`
entry below it.

**`SKILL.md` is byte-identical in three locations** - `src/venvaxi/SKILL.md`, this repository's
`.claude/skills/venvaxi/SKILL.md`, and the copy `venvaxi setup` writes. This is the third unit in a
row to edit the same `--bases` gotcha. All three verified at 22172 bytes, `sha 4ca411ee159637c6`, LF
throughout. No user-facing documentation needed a change: `README.md` and `docs/architecture.md`
were checked for cache-refresh semantics, the graph's edges and the `--bases` empty state, and
neither describes any of the three at a level this unit falsifies.

## Follow-ups

- **Issue** - none filed. The three items the plan names as out of scope were re-checked at stage 03
  and none is actionable-but-unowned. *Edges left without an endpoint* is now more reachable in the
  target direction and is declared harmless and unbounded-by-design in
  `specs/behaviors/cache-refresh.md`; an edge write is idempotent on its `(src, dst, kind)` identity,
  so a rebuild reuses the row rather than adding one. *A stale edge from a re-exported cross-package
  home* is unchanged by this unit - neither deletion arm reached those edges before it either - and
  where the home package is itself indexed the `src` arm does reach them and that package's own walk
  records the identical row back. *MRO order* is recorded as out of scope in
  `specs/commands/inherits.md` and did not move.
- **Deferred to** - none. Nothing this unit found needs a downstream plan to absorb it, so no
  downstream plan was edited at this closeout.
- **Tracked as** - none. No external dependency, upstream fix or release gates anything here.
- **An observation, deliberately not a follow-up: `top_level_root` now has no cross-module
  consumer.** It was made public in [inherits-bases-direction](inherits-bases-direction.md) (PR
  [#123](https://github.com/andyrids/venv-axi/pull/123)) *for* `_mcp.py`, whose `get_bases_tool`
  hint needed a package root. Dropping that hint's recovery clause removed the only call, and the
  now-unused import went with it or `pkgdx-lint` would have failed. Recorded as an observation
  rather than filed, on three grounds: the name is still defined and used at five call sites inside
  `_introspect.py`, so it is public-with-no-external-caller and not dead code; `_introspect.py`
  declares no `__all__`, so nothing advertises it as an entry point that would now mislead; and the
  module is underscore-private, so no published surface moved and re-privatising it would be churn
  the next caller reverses. Verified at stage 03: no module, test or fixture imports it from
  `venvaxi._mcp`, and `venvaxi._introspect.top_level_root("rich.logging")` still returns `"rich"`.
  If a later unit establishes that `_introspect.py` is its only caller for good, renaming it back is
  a one-line change belonging to that unit rather than to a standing issue.
