---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/skill-content.md
authors:
  - specs/behaviors/symbol-graph.md
  - specs/behaviors/qualified-name-semantics.md
issues: [87]
pr: 103
---

# Plan: Private submodule contract

## Scope

`_walk_submodules` unconditionally skips any submodule whose own final name segment starts with
`_`. The behaviour is deliberate and already tested - `tests/resources/package/_impl.py` exists
as a dedicated fixture, `tests/test_cli.py:819` parametrizes `["nosuchmodule", "_impl"]` against
one assertion, and `tests/test_introspect.py:711-714` asserts a re-exported class member resolves
through it. **No file under `specs/` declared any of it.**
[#87](https://github.com/andyrids/venv-axi/issues/87) - per `specs/README.md` Invariant 2,
spec/code divergence is a bug in either direction, and code that is right while nothing says so is
the same failure as a spec describing behaviour the code lacks.

The code is already correct; nothing under `src/` changes. What is missing is the declaration,
plus the tests that keep it honest.

Out of scope, each with where it went:

- **Changing the behaviour.** #87 asks only that the skip be declared, not reconsidered - the code
  is not wrong. If a later spec wants to expose private submodules behind a flag, that is its own
  unit.
- **Sharpening `tree`'s hint.** `venvaxi tree pkg._impl` currently emits the same `count: 0` plus
  `venvaxi tree pkg` hint that a typo gets, which is why `tests/test_cli.py:819` can parametrize
  `["nosuchmodule", "_impl"]` against one assertion. A hint that told the two apart is a real
  improvement this plan does not make. Its own issue, filed at closeout.
- **Sharpening `show --api`'s empty-API hint.** `venvaxi show pkg._impl --api` emits `count: 0`
  plus a hint naming `venvaxi tree pkg._impl`, which returns `count: 0` as well - the offered
  recovery confirms the empty answer a second time. `specs/commands/show.md` justifies that hint
  on the grounds that an empty API usually means the symbols are one level down; here they are in
  that very module, unwalked. A behaviour change, so out of scope by #87's framing. Its own issue,
  filed at closeout.
- **The wider depth > 0 re-export filter.** `_walk_module` (`_introspect.py:728-743`) drops any
  cross-module re-export when a module declares no `__all__`; only the private-home carve-out
  inside that filter is declared by this plan. The filter's general behaviour is a separate,
  larger unit. Its own issue, filed at closeout.

## Implements

Nothing under `src/venvaxi/*.py` changes. The two behavior specs below are **authored** - written
to describe code that was already correct - so they sit in `authors:`, not `specs:`. Listing them
in `specs:` would make stage 03 verify a code conformance this plan never delivers: the trap
`plans/README.md` records the methodology walking into on first use, and which
`plans/find-ordering-contract.md` explains at its Notes.

`specs/behaviors/skill-content.md` is the one entry in `specs:`, and the distinction is the point.
That spec was **already** declared and already binding; `src/venvaxi/SKILL.md` did not conform to
it, because the skill must carry an entry for each failure mode costing an agent a wrong
conclusion and must state plainly where the AXI cannot answer a class of question - and the
private-submodule rule is both. This plan brings the skill into conformance, which is a code
conformance claim rather than an authorship one, and `plans/README.md` is explicit that
conformance is the stronger claim and subsumes authorship.

The ordering is causal, not incidental. `skill-content.md` also forbids the skill restating any
claim `specs/**` does not declare, so the Gotchas entry was **impossible to write** until the
`### Private submodules` subsection existed. Declaring the behaviour is what unblocked documenting
it where an agent would actually meet it.

- **`specs/behaviors/symbol-graph.md`** - a new `### Private submodules` subsection under
  `## Details`. This is the walk's own spec ("any change to the store schema or the introspection
  walk"), so the declaration belongs here rather than in a new file. It states the skip, that it
  is unconditional, the segment-vs-root asymmetry, the one-line *why*, the three observable cases
  as `If <trigger>, then` criteria, and that the absence is not a staleness signal.
- **`specs/behaviors/qualified-name-semantics.md`** - one cross-reference bullet, placed next to
  where `home_qualified_name` is specified, pointing at the new subsection. This is where a reader
  actually trips over the rule, and where issue #68's second comment wrongly expected to find it
  already. Linked, not restated, per the SHOULD NOT in `reference-standard-spec.md`.

**`specs/commands/tree.md`** receives a third edit - the existing phrase 'it does not exist, is
private, or failed to import during the walk' now links 'private' to the new subsection - but it
is **not** listed in `authors:`. Both `authors:` entries gain a fact a reader did not have -
the whole rule in one case, and that a node's home can itself be private in the other, which is
exactly what #68 needed and could not find. `tree.md`'s sentence was already true and already
alluded to the rule; the edit adds a pointer to where the rule lives, not a new fact about
`tree`, so the file carried no coverage gap for `authors:` to close. Listing it anyway would make
the field a diffstat - `git diff` already answers which files a plan touched - and dilute the
ownership claim the same way over-listing `specs:` does.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. The spec amendments (three edits above) are written and are stage 01's output; nothing further
   is authored here.
3. Add an unexported `Hidden` class to `tests/resources/package/_impl.py`. It must be **inert by
   construction**: `tests/resources/package/api.py` imports only `Base`, `Client` and `Sub`, so
   `Hidden` enters no walked module's namespace and can appear in no existing count. If any
   existing count assertion moves when `Hidden` is added, that *is* the finding - the declared
   behaviour would be false, and stage 02 must stop and report it rather than adjust the fixture
   to make counts match again.
4. Add characterization tests in `tests/test_introspect.py` for the three declared cases:
   - a private submodule named directly has no module node (already partly covered by
     `tests/test_cli.py:819`; extend at the introspection layer if the CLI-level assertion does
     not already pin the graph-level fact);
   - the existing re-export case (`tests/test_introspect.py:708-714`, `:817`, `:825`) is the
     evidence for the facade/home-keying case and needs no new test, only citation at closeout;
   - `Hidden`, added in step 3, is absent from every command's output - `find`, `show --api`, and
     a direct `get_symbol`/`inspect` lookup on both `pkg.api::Hidden` and `pkg._impl::Hidden` all
     read as a genuine miss, not a found-but-empty result.
5. These are **characterization tests**, not bug-fix regression tests - nothing is being fixed, so
   the show-it-failing SHOULD in `ICM/_config/reference-toolchain-pytest.md` (scoped to 'a test
   written for a bug fix') does not apply. This discharge must be **announced** in the stage 03
   report, never left silent.
6. Perform the two live checks against the real venv and record their output in the stage 02/03
   report:
   - `venvaxi tree _pytest --max-depth 1` walks a top-level package whose own name starts with
     `_` in full, demonstrating the root-vs-recursion asymmetry;
   - `venvaxi inspect pkg.api::Client.connect` (or the fixture-package equivalent) resolves to
     `pkg._impl::Client.connect` while `venvaxi tree pkg._impl` shows no module node for
     `pkg._impl` itself.
7. Stage 03's spec-comparison step is **vacuous by design** for an `authors:` plan - there is no
   code conformance to verify, only a spec-to-reality check that was already true going in. The
   report must say so rather than let it read as a clean conformance pass
   (`plans/find-ordering-contract.md` Notes is the precedent).
8. `CHANGELOG.md` entry under `Changed` - the contract is newly declared, not newly true.

## Validation

- [x] If a caller names a private submodule as the target of `inspect`, `tree`, or an MCP module
      lookup, then venvaxi shall answer as it does for a module that does not exist - no module
      node is recorded for it. — `tests/test_cli.py::test_command_tree_empty_hint_names_root_tree[_impl]`,
      `tests/test_introspect.py::test_show_module_raises_for_private_submodule_named_directly`
- [x] When a module the walk visits re-exports a class or function whose home is a private
      submodule, venvaxi shall record it, keyed at the re-exporting facade, with its
      `home_qualified_name` pointing into the unwalked private module and its class member rows
      keyed at that home. — `tests/test_introspect.py::test_get_symbol_resolves_facade_spelled_method`,
      `::test_get_inheritors_home_path_matches_facade`, `::test_home_qualified_name_records_private_home`
- [x] When a facade-spelled class member whose home is a private submodule is resolved
      (`pkg.api::Client.connect`), venvaxi shall answer with the home-keyed row
      (`pkg._impl::Client.connect`) while `pkg._impl` itself carries no module node in the graph.
      — `tests/test_introspect.py::test_get_symbol_resolves_facade_spelled_method`,
      `::test_show_module_raises_for_private_submodule_named_directly`
- [x] If a symbol is homed in a private submodule and re-exported nowhere, then venvaxi shall
      report it absent under both the facade and the home spelling - `find` returns `count: 0`
      for it and `inspect` raises `SymbolNotFoundError` for either spelling. —
      `tests/test_introspect.py::test_find_symbol_excludes_symbol_homed_in_private_submodule`,
      `::test_get_symbol_raises_for_symbol_homed_in_private_submodule`
- [x] When a caller asks for a private submodule's own public API, venvaxi shall report
      `count: 0` at `EX_OK` rather than the failure a submodule that does not exist raises. —
      `tests/test_introspect.py::test_get_public_api_empty_for_private_submodule`,
      `::test_get_public_api_raises_for_nonexistent_submodule` (contrast control)
- [x] When a top-level package's own name starts with `_`, venvaxi shall walk it in full as the
      query root, while its own underscore-prefixed submodules are skipped by the identical rule
      once the walk recurses into them. — live check re-run at stage 03:
      `uv run venvaxi tree _pytest --max-depth 1` (`count: 49` = 1 package + 48 modules, none
      underscore-prefixed), `uv run venvaxi tree _pytest.outcomes` (`count: 1`); `pkgutil
      .iter_modules(_pytest.__path__)` arithmetic 53 total / 5 underscore-prefixed / 48 remaining,
      exact match, `pytest==9.1.1`
- [x] When the same private-submodule query is run against a freshly built graph and again after
      `--refresh`, venvaxi shall report the identical absence both times. —
      `tests/test_introspect.py::test_private_submodule_miss_identical_after_refresh`
- [x] The packaged skill shall carry a Gotchas entry for the private-submodule rule, naming the
      correct move (query the public facade) rather than only the symptom, and asserting no claim
      `specs/**` does not declare. — stage 04 Task 0 clause-by-clause check of the "Private
      submodules are not indexed" entry against `specs/behaviors/symbol-graph.md#private-submodules`,
      `specs/behaviors/qualified-name-semantics.md`, `specs/commands/show.md` and
      `specs/commands/tree.md`: every clause traces to a declared statement, no divergence found;
      `diff src/venvaxi/SKILL.md .claude/skills/venvaxi/SKILL.md` — empty (byte-identical);
      `uv run -m prek run --all-files` — all eight hooks passed
- [x] The test suite shall pass. — `uv run coverage run -m pytest` → `500 passed, 21 deselected`

## Risks / unknowns

- The `Hidden` fixture addition is only as inert as the walk's own `__all__`-absence filter makes
  it. If `tests/resources/package/api.py` gains an `__all__` in some future change, `dir()`-based
  discovery stops applying and the inertness argument in Approach step 3 needs re-checking against
  the code at that time, not assumed to still hold.
- The root-vs-recursion asymmetry is demonstrated live against `_pytest`, a third-party package
  outside this project's control. A future `pytest` release could restructure its private modules
  and change the exact counts (53 submodules, 5 underscore-prefixed, 48 recorded) without changing
  the rule itself; the spec states the rule, not the counts, so this is a risk to the live-check
  evidence at closeout, not to the declaration.
- `authors:` excluding `tree.md` is a judgement call, argued in Implements above rather than
  mandated by `plans/README.md`. A reviewer could reasonably weigh the diffstat argument
  differently; flagged here rather than decided silently.

## Notes

**Re-entered stage 01 from the stage 02 gate.** Mutation-testing the new characterization tests -
removing the underscore skip and re-running - showed four of five failing and one passing, and the
one that passed asserted `Hidden`'s absence from `package.api`'s listing, which holds whether or
not the skip exists because `api.py` never imports it. Chasing that surfaced a fourth observable
surface the declaration did not cover: `show --api` on a private submodule answers `count: 0` at
`EX_OK`, while the same request for a submodule that does not exist raises `PackageNotFoundError`
at `EX_FAILURE`. The spec's first `If/then` bullet asserts an equivalence to nonexistence that
holds for `inspect`, `tree` and MCP lookups but **not** there, and `show --api` is the surface
where the wrong answer is most trusted - `count: 0` at `EX_OK` is a definitive empty state under
`specs/behaviors/output-contract.md`, and `specs/commands/show.md` justifies its hint on the
grounds that an empty API 'usually means the symbols are one level down rather than absent', which
is false in exactly this case. The delta added the fourth bullet, split the criterion, and
replaced the non-discriminating test with a pair that does discriminate: with the skip,
`get_public_api('package._impl').symbols == []`; without it, `['Base', 'Client', 'Hidden',
'Sub']`.

**Re-entered stage 01 a second time, from the stage 04 gate.** Stage 04's contract step 4 -
update any user-facing documentation the feature touches - surfaced that `src/venvaxi/SKILL.md`
carried no Gotchas entry for the rule, while `specs/behaviors/skill-content.md` requires one for
each failure mode costing an agent a wrong conclusion, and separately requires that a class of
question the AXI cannot answer be stated plainly. `SKILL.md` already carries 'Dunders are not
indexed', the same shape of deliberate walk exclusion producing a confidently-empty answer, so the
omission was a live divergence under `specs/README.md` Invariant 2 rather than a stylistic gap.
Adding the entry moved `skill-content.md` into `specs:` and un-vacuumed stage 03's spec-comparison
discharge, which was re-run against the new surface rather than left as first reported. The
repository's own copy at `.claude/skills/venvaxi/SKILL.md` was updated in the same edit and
verified byte-identical, per `skill-content.md`'s Applies to.

Further notes populated at closeout.

**Why `authors:` for the two behavior specs but `specs:` for `skill-content.md`.** All three specs
this plan touches describe code that was already correct going in, so the surface distinction -
"nothing under `src/` changes" - looks identical for all three. The field split tracks a different
fact: whether the *spec being amended* already existed and was already binding.
`symbol-graph.md`/`qualified-name-semantics.md` gained a subsection and a bullet that did not
exist before this plan wrote them, so there was no prior text for the code to have been out of
conformance with - authorship, not conformance, per `plans/README.md`'s "A spec belongs in one
field, never both." `specs/behaviors/skill-content.md`, by contrast, already existed and already
required a Gotchas entry for every failure mode costing an agent a wrong conclusion;
`src/venvaxi/SKILL.md` was missing one for a rule it already carried a sibling entry for
("Dunders are not indexed" is the same shape of deliberate walk exclusion). That is a live
divergence between an already-binding spec and the shipped skill, which is what `specs:` exists to
name - stage 03's spec-comparison step then has a real subject for that one file, and correctly
did not for the other two (Discharge 1 in the stage 03 report).

**The `_pytest` 53/5/48 evidence.** The root-vs-recursion asymmetry (criterion 6) is demonstrated
live rather than by unit test, because it depends on a real third-party package with real private
submodules rather than the fixture package. `pkgutil.iter_modules(_pytest.__path__)` yields 53
submodules, 5 underscore-prefixed (`_argcomplete`, `_code`, `_io`, `_py`, `_version`); `venvaxi
tree _pytest --max-depth 1` records 48 module nodes (53 - 5) plus the package node itself
(`count: 49`), and none of the five underscore-prefixed names appears among them. The techspec
recorded these numbers first; the stage 02 report re-derived them independently and matched
exactly; stage 03 re-derived them a third time, independently, against `pytest==9.1.1`, and again
matched exactly - no drift on this venv. The Risks section flags that a future `pytest` release
could move the raw counts without moving the rule itself, so the arithmetic is re-run at each
stage rather than copied forward, and that pattern held for all three stages.

**Mutation testing in place of show-it-failing, and why the substitution was legitimate.** The new
tests are characterization tests of already-shipped behaviour - nothing was fixed, so
`reference-toolchain-pytest.md`'s show-it-failing SHOULD (scoped explicitly to "a test written for
a bug fix") does not apply; there is no "previous implementation" to show the test failing
against, because the current implementation is the only one that has ever existed under this plan.
What a characterization test still owes the record is proof that it discriminates - that it would
catch a regression, not merely that it passes today. Stage 03 supplied that proof by temporarily
reverting `_walk_submodules`'s skip condition to `if subname in visited:` (removing the
underscore-prefix clause), re-running every new/cited test, and restoring the original line
afterward: 6 of 11 tests failed under the mutation (every test written or cited to pin the skip
itself), and 5 kept passing for reasons argued individually (the contrast control asserting
behaviour on a name that was never private; three facade-resolution tests pinning a property
independent of whether `_impl` gets its own node). This is the same proof-of-discrimination the
show-it-failing SHOULD exists to provide, applied at the rule level instead of the fix level - a
mutation is a synthetic "previous implementation" that never really shipped, which is exactly the
gap show-it-failing cannot span for a plan that fixes nothing. The plan's own Notes above record
an earlier mutation round (pre-re-entry) that caught a non-discriminating test the same way,
which is what surfaced the fourth spec bullet in the first place - the method was load-bearing
twice in this run, not just a closeout formality.

**Stage 02's implementation report went stale mid-run and was not updated.** The stage-02 gate
re-entry (documented above) swapped one test for a discriminating pair, but
`ICM/process-plan/stages/02-implementation/output/private-submodule-contract-code.md` still
describes the pre-re-entry state in places - "5 new tests" where 6 exist, and item 4 named as the
non-discriminating `test_get_public_api_excludes_symbol_homed_in_private_submodule` rather than
the replacement pair, with "Deviations from techspec: None" left unqualified. Stage 03 caught this
by diffing the report's claims against `git diff tests/test_introspect.py` rather than trusting
the report's own count, and found the code and tests on disk correct throughout - only the record
describing stage 02 was wrong, not the work itself. Recorded here because a plan's Notes is the
durable home for this kind of finding, and the discrepancy would otherwise be legible only inside
a stage report that this repository does not keep past the run.

**Stage 04 Task 0 - re-entry decision checked independently, found conforming.** The second
stage 01 re-entry (documented above) added the packaged-skill Gotchas entry and moved
`skill-content.md` into `specs:`, which un-vacuumed stage 03's spec-comparison discharge without
that discharge having actually been re-run against the new surface by a party independent of the
edit itself. Stage 04 checked the "Private submodules are not indexed" entry clause by clause
against `specs/behaviors/symbol-graph.md#private-submodules`, `specs/behaviors/
qualified-name-semantics.md`, `specs/commands/show.md` and `specs/commands/tree.md`: every clause
traces to a declared statement (the `tree pkg._impl` hint text and its own `count: 0` answer trace
through `show.md`'s hint rule combined with `symbol-graph.md`'s equivalence-to-nonexistence bullet
and `tree.md`'s no-node-in-graph response, rather than to a single sentence, but the chain holds
end to end); it clears `skill-content.md`'s "would an agent act differently" bar by the same
reasoning as the neighbouring "Dunders are not indexed" entry it was modelled on; and it names the
correct move (query the facade) rather than only the symptom. Both copies remain byte-identical.
No divergence found - reported as a clean pass with the clause-by-clause trail above rather than
left implicit.

## Follow-ups

- **Issue [#104](https://github.com/andyrids/venv-axi/issues/104)** - `venvaxi tree pkg._impl`
  currently emits the same `count: 0` plus `venvaxi tree pkg` hint that a mistyped or nonexistent
  submodule name gets, so the two cases read identically even
  though one is a definitive "private, not absent" answer and the other is a plain miss. A hint
  that told the two apart is a real improvement this plan does not make (declaring the existing
  behaviour, not changing it, is #87's whole scope). Named in this plan's Scope as "Its own issue,
  filed at closeout".
- **Issue [#105](https://github.com/andyrids/venv-axi/issues/105)** - `venvaxi show pkg._impl
  --api` emits `count: 0` plus a hint naming `venvaxi tree pkg._impl`, which itself answers
  `count: 0` - the offered recovery confirms the
  empty answer a second time rather than resolving it. `specs/commands/show.md` justifies that
  hint on the grounds that an empty API "usually means the symbols are one level down rather than
  absent," which this plan's new criterion 5 shows is false in exactly the private-submodule case.
  A behaviour change, so out of scope by #87's framing (declare, do not reconsider). Named in this
  plan's Scope as "Its own issue, filed at closeout".
- **Issue [#106](https://github.com/andyrids/venv-axi/issues/106)** - `_walk_module`'s
  cross-module re-export filter drops any re-export when the exporting module declares no
  `__all__`; this plan's `### Private submodules` subsection declares only the
  private-home carve-out inside that filter, not the filter's general behaviour, which is a
  separate and larger unit. Named in this plan's Scope as "Its own issue, filed at closeout".
- **Deferred to** - none.
- **Tracked as** - none.
