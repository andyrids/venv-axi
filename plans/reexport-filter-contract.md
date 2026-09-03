---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/symbol-graph.md
  - specs/behaviors/skill-content.md
authors: []
issues: [106]
pr: 132
---

# Plan: Re-export filter contract

## Scope

`_walk_module` (`src/venvaxi/_introspect.py:744-765`) applies a filter no file under `specs/`
declares. When a walked module sits at depth greater than zero **and** declares no `__all__`, the
walk drops every cross-module re-export - any class or function whose defining module differs
from the recording module - with one carve-out for a symbol whose home is a private module inside
the same package root.
[#87](https://github.com/andyrids/venv-axi/issues/87) declared **only that carve-out**, because
the private-submodule rule is unreadable without it. So `specs/` states an exception to a rule it
never states, which is the same failure #87 was filed about, one level up
([#106](https://github.com/andyrids/venv-axi/issues/106)).

Three existing tests already pin branches of the filter
(`tests/test_introspect.py::test_show_module_excludes_reexports_without_all`,
`::test_show_module_includes_reexports_with_all`,
`::test_walk_module_keeps_private_home_facade_reexports`), so the behaviour is deliberate and
partly evidenced - it is simply undeclared. Per `specs/README.md` Invariant 2, code that is right
while nothing says so is the same divergence as a spec describing behaviour the code lacks.

What is missing is the declaration, plus the tests that keep the two undeclared-and-unpinned
halves honest.

**The code turned out not to be correct everywhere.** This plan opened on the premise that
nothing under `src/` changes; stage 02's probe 2 falsified it for one class of package, and the
stage 02 gate returned the work to stage 01 (Notes). The newly declared below-the-root rule is
false for any package whose own root name starts with `_`, because the carve-out's private-segment
test scans **every** segment of the home name including the root, while `is_private_submodule`
(`src/venvaxi/_introspect.py:606-625`) - which exists precisely to encode that rule - deliberately
excludes the root segment. For a root such as `_pytest` every same-root home satisfies the
carve-out, so public-sibling re-exports are kept below the root. One line of `src/` therefore
changes, bringing the code into conformance with the sentence the spec already states. The
declaration itself is unmoved; see Implements.

**The packaged skill is in scope too, and it was not at the first two gates.** The stage 04 gate
ran its packaged-skill check and found `src/venvaxi/SKILL.md` carrying no entry for the rule this
plan declares, while `specs/behaviors/skill-content.md` - already existing, already binding -
requires one for each observed failure mode costing an agent a wasted query or a wrong conclusion,
naming the correct move rather than only the symptom. That is a live spec/code divergence under
`specs/README.md` Invariant 2, not a documentation preference, so it returns to stage 01 rather
than being patched at closeout. The sharpest half is that the file already teaches the *carve-out*
without the rule: the `Private submodules are not indexed` entry ends by telling an agent to query
the facade, which an agent generalises straight into the failure. So the entry is a reconciliation
of existing text as much as an addition, and `SKILL.md` joins `_introspect.py` and `_store.py` as
a file this plan changes.

Out of scope, each with where it went:

- **Changing the filter.** #106 asks that it be declared, not reconsidered. Both questions the
  issue raises - the sibling-public drop below the root, and the third-party drop everywhere -
  resolve as intent, argued in Implements. If a later spec wants a flag opting an
  attribute-discovered re-export into the graph below the root, that is its own unit, and
  `specs/behaviors/symbol-graph.md` Out of scope now says so. The underscore-rooted fix now in
  scope is not a counter-example: it moves the code onto the filter as declared, and widens or
  narrows no declared rule.
- **The submodule-as-`attribute` finding.** A module object can reach `_record_symbol` by two
  routes the filter's own module guard does not cover, and would then surface as an `attribute`
  row in `show --api`. Recorded in Risks / unknowns as a finding for stage 02 to confirm by
  probe, **not** declared as intended behaviour and **not** fixed here. Its own issue at stage 04
  closeout if it reproduces, the way #104, #105 and #106 were themselves filed at #87's closeout.
- **Re-export provenance queries.** The `EXPORTS` and `IMPORTS_FROM` edges the walk writes for
  every recorded re-export are still unread. Already Out of scope in
  `specs/behaviors/symbol-graph.md`; nothing here changes that.

## Implements

`specs/behaviors/symbol-graph.md` sits in **`specs:`**. It began this plan in `authors:` and the
stage 02 gate moved it, which is a change of claim rather than a change of wording, so the
reasoning is restated from scratch rather than patched.

The distinction is not cosmetic. `specs:` claims that this plan changes code until it conforms,
and stage 03 verifies observable behaviour against every entry there. `authors:` claims only
authorship, and nothing is verified against it - the field exists so a spec-authoring plan can own
its spec without claiming a conformance it never delivers. `plans/README.md` is explicit that a
spec belongs in one field and never both, and that where a plan both writes a spec and implements
it the answer is `specs:`, conformance being the stronger claim and subsuming the authorship.

The `authors:` case was correct as long as the premise held. The `### Re-exported symbols`
subsection did not exist before this plan wrote it, so there was no prior text the code could have
been out of conformance with, and `plans/private-submodule-contract.md` states the test that
decides it: whether the *spec being amended* already existed and was already binding. Nothing
binding was being amended, so there was nothing to verify - the trap `plans/README.md` records the
methodology walking into on first use, where a plan listed every spec it had authored in `specs:`
and made Invariant 1 unfailable in the same commit.

**The premise was false, and probe 2 is what falsified it.** The declaration was written from a
read of the code; the code does not do what the read said for every package. For a root whose own
name starts with `_` the walk records public-sibling re-exports below the root, which the new
subsection's second paragraph says shall not happen. Under `specs/README.md` Invariant 2 that is
spec/code divergence, and the gate resolved it the way Invariant 2 prefers: fix the code. The
moment one line of `src/` moves to satisfy a declared sentence, the claim being made about that
file is conformance, and conformance is `specs:`.

**The parallel with `plans/private-submodule-contract.md` is exact, and the difference is where
the line falls.** That plan split its three spec files across both fields: `symbol-graph.md` and
`qualified-name-semantics.md` in `authors:`, because they gained text that did not exist before,
and `specs/behaviors/skill-content.md` in `specs:`, because it already existed, already bound
`src/venvaxi/SKILL.md`, and the skill did not conform. Its Notes call the deciding fact "whether
the *spec being amended* already existed and was already binding". Here there is only one spec
file, so there is no split to make - the file moves whole. What moved it is a variant of the same
fact: the sentence stage 01 wrote became binding the moment it was written, and the code was
already out of conformance with it. `symbol-graph.md` was an `authors:` entry in that plan and a
`specs:` entry in this one for a reason that is about the sentence, not the file.

One consequence follows for stage 03, and replaces the opposite claim this section made before
the re-entry. Its spec-comparison step is **not** vacuous: `specs/behaviors/symbol-graph.md` is a
real conformance subject, and the subject is specific - the `### Re-exported symbols` second
paragraph and its two `If/then` bullets, checked against a package whose own root name starts with
`_` as well as one whose does not. Criteria 2 and 8 are what it verifies against. Everything
else in the subsection remains a declaration of behaviour that was already true, so stage 03
should say which half it is reporting on rather than let one clean pass cover both.

- **`specs/behaviors/symbol-graph.md`** - a new `### Re-exported symbols` subsection under
  `## Details`, placed immediately **before** `### Private submodules` so the general rule reads
  before its carve-out. This is the walk's own spec ('any change to the store schema or the
  introspection walk'), so the declaration belongs here rather than in a new file, the same
  placement argument #87 made. It declares the `__all__`-present rule, the below-the-root drop
  with its one-line *why*, the root exemption with its principle citation, the class-and-function
  scope of the filter, and the two edge cases as `If <trigger>, then` criteria. `## Out of scope`
  gains a matching bullet ruling out widening the filter.

Two of those facts are the questions #106 raises and does not answer, and both resolve as intent:

- **The root exemption is intent, not an artefact of where the depth guard sits.** The root is
  the spelling an agent imports from, so a re-export recorded there is the answer rather than a
  duplicate - `specs/principles.md#the-agents-spelling-wins-over-the-internally-correct-one`
  decides it. It is also load-bearing: without it, `show --api` on a facade package whose root
  defines nothing of its own and declares no `__all__` would report `count: 0` for a package with
  a full public surface, which
  `specs/behaviors/output-contract.md#definitive-empty-states` makes a positive false claim
  rather than a shrug.
- **The class-and-function scope is intent.** An instance has no defining module of its own - it
  reports its type's - so applying the home test to it would attribute a module's own constants
  to whatever library built them. The fixture package already carries the live case:
  `PATTERN = re.compile("x")` in `tests/resources/package/constants.py` reports `re` as its
  defining module and is nonetheless recorded as `constants`' own constant.

Neither is pinned by any current test. That gap is stage 02's work and is covered by criteria 3
and 5 below.

**`specs/commands/show.md`** receives a second edit - the existing sentence 'A package's `__all__`
is its own declaration of its public API, and this command answers what that API is' now carries a
pointer to the new subsection for the module that declares none - but it is listed in **neither**
field. The sentence was already true and already implied the complementary case; the edit adds a
link to where that case is now declared, not a new fact about `show`, so the file carried no
coverage gap to close. The re-entry does not change that: the code the fix moves is the walk's,
and `show --api` reports whatever the walk recorded, so `show.md` gains no conformance claim
either. Listing it in either field would turn that field into a diffstat, which `git diff`
already answers, and would dilute the ownership claim the same way over-listing `specs:` does.
`plans/private-submodule-contract.md` excluded `specs/commands/tree.md` on exactly this
reasoning.

**`specs/behaviors/skill-content.md` joins `specs:`, and it is conformance rather than
authorship.** No line of that spec is written or amended here. It already exists, it already binds
`src/venvaxi/SKILL.md` (its Applies to names the packaged source and the two copies regenerated
from it), and its `What the skill must cover` already requires an entry for each observed failure
mode costing an agent a wasted query or a wrong conclusion, naming the correct move rather than
only the symptom. The skill did not conform. That is exactly the test
`plans/private-submodule-contract.md`'s Notes set out for this field - "whether the *spec being
amended* already existed and was already binding" - and it is exactly the answer that plan reached
for this same file, splitting `skill-content.md` into `specs:` while its two behaviour specs
stayed in `authors:`. The same file, the same argument, one unit later.

**The ordering is causal, not incidental, and it is why this could not have been a stage 04 edit
in the first pass either.** `skill-content.md`'s first content rule is that the packaged skill
shall restate no claim about `venvaxi` behaviour that `specs/**` does not declare. Before this
plan wrote `### Re-exported symbols`, `specs/` declared the carve-out and not the rule - #106's
whole thesis - so an entry stating the below-the-root rule would itself have been a claim
`specs/**` did not declare, forbidden by the very spec that now requires it. The entry became
writable at the moment the subsection landed, and became *owed* at the same moment. The
divergence is therefore this plan's own to close and not a pre-existing debt it inherited, which
is the second reason it is not deferred to a follow-up issue.

One consequence for stage 03, alongside the one recorded above for `symbol-graph.md`: its
spec-comparison step gains a second conformance subject it has never seen - `src/venvaxi/SKILL.md`
against `skill-content.md`'s content rules - and that subject must be discharged by a party
independent of the edit. `plans/private-submodule-contract.md` flags in its own Notes that it
un-vacuumed the identical discharge and then reported it without the re-run having been performed
independently; this plan does not repeat that.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. The spec amendments above are stage 01's output; nothing further is authored in stage 02.
3. Add one cross-module re-export at depth 0 to `tests/resources/package/__init__.py` -
   `from package.module import render_grid`. Pinning the root exemption needs a re-export whose
   home is a **public sibling**, because that is the shape the below-the-root rule drops. A
   re-export from `package._impl` would not do: under a mutation of the depth guard it would fall
   straight into the private-home carve-out and still be kept, so it cannot discriminate the
   exemption from the carve-out.
4. That import also binds `package.module` as an attribute of `package`, and the two nodes do not
   collide: `_record_symbol` keys the attribute row `package::module` while `_walk_submodules`
   keys the module row `package.module`, so both survive the walk. This is the same shape as the
   open finding in Risks / unknowns, arriving in the fixture package.
5. **Three existing assertions will move, and each is argued before it is edited.** `render_grid`
   appearing is the root exemption working; a `module` name appearing as an `attribute` is the
   finding. Editing either to make the suite green without saying which it is, is precisely the
   failure `plans/private-submodule-contract.md` records itself walking into at its own stage 02
   gate. The three:
   - `tests/test_introspect.py::test_get_public_api_top_level_keeps_default_depth` (`:503`),
     whose literal `["Animal", "Cat", "Dog"]` is the package's whole reported API
   - `::test_get_public_api_excludes_module_and_package_kind` (`:510-530`), whose
     `names.isdisjoint({...})` assertion names `module` explicitly
   - `::test_show_module_returns_node_and_children` (`:533-548`), whose literal children list is
     the package's whole `CONTAINS` fan-out
6. Add characterization tests in `tests/test_introspect.py` for the two declared facts nothing
   currently pins - the root exemption and the class-and-function scope. The other four criteria
   are already evidenced by existing tests, cited at closeout rather than duplicated:
   - `::test_show_module_includes_reexports_with_all` for criterion 1
   - `::test_show_module_excludes_reexports_without_all` for criterion 2
   - `::test_walk_module_keeps_private_home_facade_reexports` for criterion 6
   - criterion 7 needs a case no fixture carries today, resolved at the stage 01 gate as a
     **standard-library** home: one such class imported into `tests/resources/package/importer.py`,
     which already declares no `__all__` and already re-exports. The carve-out's first conjunct
     (`obj_home.startswith(f"{package_root}.")`, `_introspect.py:759-760`) is false for a
     standard-library and a third-party home alike, so both reach `continue` by the identical
     path. `::test_show_module_excludes_reexports_without_all` asserts children `== ["local"]`,
     which stays true and evidences criterion 7 alongside criterion 2 - no assertion moves
7. The tests of step 6 are **characterization tests**, not bug-fix regression tests - they pin
   behaviour that was already shipped, so
   `ICM/_config/reference-toolchain-pytest.md`'s show-it-failing SHOULD, scoped explicitly to 'a
   test written for a bug fix', does not apply to them. The discharge is conditional, so per the
   workspace acceptance criteria it MUST be **announced** in the stage 02 and 03 reports with the
   substitute evidence named, never left silent. Criterion 8's test, added at step 12, is the one
   exception in this plan and is held to the SHOULD in full - see there.
8. Substitute mutation testing, as #87 did, to prove the new tests discriminate rather than merely
   pass. Neutralise one guard at a time, re-run the new and cited tests, restore, and record which
   tests fell and which survived with a reason for each survivor:
   - `depth > 0` relaxed to `depth >= 0`, which should drop `render_grid` from the root
   - `inspect.isclass(obj) or inspect.isroutine(obj)` widened to every kind, which should drop
     `PATTERN` from `package.constants`
   - `if not private_home_facade: continue` removed, which should drop `Client` from `package.api`
   - the fourth guard, added by the re-entry: `is_private_submodule(obj_home)` reverted to the
     inline `any(...)` over every segment, which should keep `Exposed` at
     `_private_root.facade` and so fail criterion 8's test alone. This round is the
     show-it-failing evidence for the fix as well as a discrimination proof, because the mutation
     *is* the pre-fix implementation rather than a synthetic one.
9. Probe the open finding and record the raw output in the stage 02 report:
   `uv run venvaxi show venv-axi --api`, looking for an `exceptions` row of kind `attribute`. Do
   not fix it and do not amend the spec to bless it - the finding is reported, and filed as its
   own issue at stage 04 closeout if it reproduces.
10. Probe the second finding the same way, against a package whose own root name starts with `_`:
    whether a re-export from a **public** sibling inside `_pytest` is kept below the root, which
    the declared rule says it should not be. **This probe is what re-entered stage 01** - it
    reproduced, so the disposition it was written with ('report, do not fix') was superseded at
    the gate. Steps 11 to 13 are the delta.
11. **Fix the carve-out** in `_walk_module` (`src/venvaxi/_introspect.py:759-763`): replace the
    inline `any(segment.startswith("_") for segment in obj_home.split("."))` with
    `is_private_submodule(obj_home)`, so the condition reads as 'the home is a private submodule
    inside this package root' and one predicate answers that question everywhere. The two spellings
    differ only in the root segment, which the first conjunct
    (`obj_home.startswith(f"{package_root}.")`) pins to `package_root` itself - so the fix is a
    no-op for every root whose own name does not start with `_`, and that is what makes it a
    one-line correction rather than a re-negotiated filter. Carry a NOTE citing
    `specs/behaviors/symbol-graph.md` Re-exported symbols and #106, in the style the neighbouring
    guards use.
12. **Bump `SCHEMA_VERSION`** (`src/venvaxi/_store.py:29`) from `9` to `10`, and append a
    `NOTE: 10 - ...` entry to its docstring, following the existing `NOTE: 8 -`/`NOTE: 9 -`
    pattern, naming the carve-out fix as the trigger and the class of row - a public-sibling
    re-export duplicated below an `_`-rooted package's root - that it evicts.
    `specs/behaviors/cache-refresh.md`, Schema version covers the builder, not just the shape,
    decides this rather than leaving it open: the trigger is 'did I change what the store ends up
    holding', not 'did I change the table', and step 11 changes which rows the walk writes.
13. Add `tests/resources/_private_root/` - a four-file fixture package whose own root name starts
    with `_` - and a `fake_private_root_package` conftest fixture mirroring `fake_package`, then
    one test for criterion 8 asserting both halves at `_private_root.facade`: `Exposed` (public
    sibling) dropped, `Carved` (private sibling) kept. A fixture rather than a live `_pytest`
    check, and the choice is argued in Notes: the fact needs only a root whose *name* starts with
    `_`, which a fixture expresses exactly, whereas
    `plans/private-submodule-contract.md`'s criterion 6 needed a package with real private
    submodules discovered by recursion and had no fixture option. The live `_pytest` numbers stay
    in the record as the observation that drove the re-entry, not as a test.
14. Re-probe both `_pytest` and the `rich.align` contrast control, and re-derive the carve-out
    count. The control is the load-bearing half: a normally-rooted package's graph must be
    unchanged, or the fix has moved more than the `_`-rooted case.
15. `CHANGELOG.md` - the declaration goes under `Changed`, being newly declared rather than newly
    true; the underscore-rooted correction, including the schema bump and its consequence, goes
    under `Fixed`, being a behaviour the declared rule was already false for. The `Changed`
    entry's 'nothing under `src/` moves' clause is corrected in the same edit.
16. **Write the Gotchas entry** in `src/venvaxi/SKILL.md`, in the voice and shape of its
    neighbours, placed immediately **before** `Private submodules are not indexed` - the same
    ordering argument step 1's spec placement made, so the general rule reads before its
    carve-out. It names the rule, names the correct move (`find <name> --package <pkg>`, then
    `inspect` the returned `qualified_name`), and says that the module listing *succeeds* while
    being short of what the module binds, which is the half an agent cannot detect. The existing
    private-submodule sentence is **reconciled in the same edit** rather than left standing: 'so
    query the facade' becomes the single carve-out read against the rule above it, with the
    public-sibling case named as the thing it is not. Every clause traces to
    `specs/behaviors/symbol-graph.md#re-exported-symbols`, `#private-submodules`,
    `specs/commands/inspect.md` or `specs/commands/find.md`, per `skill-content.md`'s first
    content rule; the trace is recorded clause by clause in the stage 02 report.
17. **Mirror to `.claude/skills/venvaxi/SKILL.md` in the same edit**, per `skill-content.md`'s
    Applies to, and verify byte-identity with `diff`. `tests/test_skill_parity.py` pins it.
18. **Extend the PR-127 drift gate** (`tests/test_skill_drift.py`). Every concrete invocation the
    entry names must be triaged; a `rich.align` example is executable against the venv this
    project installs for itself, so all three rows go to `WORKED_EXAMPLES` with executed checks
    asserting the *taught property*, never equality against a recorded block
    (`skill-content.md`, first limit). The entry states no count in prose, which
    `::test_no_non_zero_result_count_in_prose` requires. One harness change is needed and is
    argued in Notes: the executor gains an `except Error` arm mirroring
    `venvaxi.__main__.main()`, so a documented query whose result is a *miss* can be run rather
    than mis-triaged as documenting no result.

## Validation

- [x] Where a module the walk visits declares `__all__`, venvaxi shall record every name it lists
      at that module, including a name whose defining module differs from it, at any depth.
      — `tests/test_introspect.py::test_show_module_includes_reexports_with_all`
- [x] Where a module the walk visits declares no `__all__` and is not the package's own root
      module, venvaxi shall not record a class or function whose defining module differs from it.
      — `tests/test_introspect.py::test_show_module_excludes_reexports_without_all`
- [x] Where a package's own root module declares no `__all__`, venvaxi shall record the classes
      and functions it re-exports from its own submodules as symbols of that root.
      — `tests/test_introspect.py::test_get_public_api_root_keeps_reexport_from_public_sibling`
- [x] When a dotted submodule that declares no `__all__` is named as the target of a query,
      venvaxi shall report its re-exports absent, identically to when the same submodule is
      reached through its parent - naming a module does not make it the walk's root.
      — `tests/test_introspect.py::test_show_module_reexports_identical_when_built_from_parent`,
      paired with `::test_show_module_excludes_reexports_without_all`
- [x] Where a module the walk visits declares no `__all__` and is not the package's own root
      module, venvaxi shall record a module-level constant it binds as that module's own symbol,
      whatever module defines the constant's type.
      — `tests/test_introspect.py::test_walk_module_keeps_constant_whose_type_is_homed_elsewhere`
- [x] If a class or function is re-exported into an `__all__`-less module below the root from a
      private submodule of the same package root, then venvaxi shall record it at the re-exporting
      module. — `tests/test_introspect.py::test_walk_module_keeps_private_home_facade_reexports`
- [x] If a class or function is re-exported into an `__all__`-less module below the root from
      outside the walked package root, then venvaxi shall not record it there.
      — `tests/test_introspect.py::test_show_module_excludes_reexport_homed_outside_package_root`,
      alongside `::test_show_module_excludes_reexports_without_all`
- [x] Where the walked package's own root name starts with `_`, venvaxi shall apply the
      below-the-root rule and its private-home carve-out identically to a package whose root name
      does not - a class re-exported from a public sibling shall not be recorded at an
      `__all__`-less module below the root, and one re-exported from a private sibling shall be.
      — `tests/test_introspect.py::test_show_module_below_root_rule_holds_for_underscore_root`;
      corroborated live at stage 03, `uv run venvaxi show _pytest.cacheprovider --api --limit 50`
      -> `count: 15` (27 pre-fix) and `uv run venvaxi show rich.align --api --limit 50` ->
      `count: 9`, the unchanged control
- [x] The test suite shall pass. — `uv run pytest -v` -> `614 passed, 32 deselected in 76.37s`;
      `uv run pytest -m conformance -v` -> `32 passed, 614 deselected`; `uv run coverage report`
      -> exit `0`, `TOTAL 1385 24 98%`
- [x] Where the packaged skill covers the below-the-root re-export rule, it shall name the
      recovery move - `find <name> --package <pkg>`, then `inspect` the `qualified_name` it
      returns - rather than only the symptom; shall state that a module listing below the root
      succeeds while omitting classes the module binds, so that there is no failure to prompt a
      retry; shall read its private-submodule carve-out against that rule rather than as a
      general permission; shall assert no claim `specs/**` does not declare; and shall have every
      invocation it names run against the venv this project installs for itself, each holding the
      property its example teaches.
      — five clauses, each separately evidenced in the stage 03 Delta pass. Recovery move and
      taught properties: `tests/test_skill_drift.py::test_documented_query_teaches_what_it_claims`
      at its three new ids - `[venvaxi find Measurement --package rich]`,
      `[venvaxi inspect rich.align]` and `[venvaxi inspect rich.align::Measurement]` - all PASSED
      under `-m conformance`, and both `rich.align` checks fail under the `depth > 0` -> `depth >
      99` mutation while the `find` check survives as the recovery route it pins. Registry
      completeness: `::test_every_documented_invocation_is_triaged`,
      `::test_triage_lists_name_only_invocations_the_skill_makes`. Carve-out reading and the
      no-undeclared-claim rule: stage 03's independent clause-by-clause trace of both the new
      "Below the package root, re-exports are not indexed" entry and the reconciled "Private
      submodules are not indexed" sentence against `specs/behaviors/symbol-graph.md#re-exported-symbols`,
      `specs/commands/inspect.md`, `specs/commands/find.md` and
      `specs/behaviors/output-contract.md#exit-codes` - no undeclared clause found. Mirror:
      `diff src/venvaxi/SKILL.md .claude/skills/venvaxi/SKILL.md` empty,
      `tests/test_skill_parity.py` 5 passed

## Risks / unknowns

- **A submodule can reach `_record_symbol` and surface as an `attribute` row.** The
  `inspect.ismodule(obj)` skip sits **inside** the `explicit_exports is None and depth > 0` branch
  (`_introspect.py:750-752`), so it does not run for a root module without `__all__` that imports
  its own submodules, nor for any module whose `__all__` names a submodule. `_classify`
  (`:419-432`) returns `ATTRIBUTE` for a module object - neither class nor routine - and
  `get_public_api` excludes only the `MODULE` and `PACKAGE` kinds (its NOTE at `:1206-1212`).
  The two node keys do not collide (`pkg::sub` against `pkg.sub`), so the module row does not
  overwrite the attribute row. `src/venvaxi/__init__.py:19` is a live instance:
  `__all__: list[str] = ["exceptions", "__version__"]`, where `exceptions` is a module. **This is
  a code read, not an observation.** If it reproduces it diverges from `specs/commands/show.md`'s
  'Submodules are the one exclusion, and it is a depth exclusion rather than a kind one' - it is
  the #82 defect class, reached by a route the kind-based fix does not cover. Stage 02 confirms by
  probe (Approach step 9); stage 04 files it as its own issue if confirmed. It is deliberately
  **not** declared in this plan's spec delta, because #106's framing is #87's: declare, do not
  reconsider, and blessing an artefact as intent is the opposite of both.
- **The underscore-rooted carve-out is no longer an unknown - it reproduced, and it is fixed
  here** (Scope, Approach steps 11 to 13, Notes). The schema-bump question is resolved, not open:
  `specs/behaviors/cache-refresh.md`, Schema version covers the builder, not just the shape,
  states the bump MUST be taken whenever *what the store ends up holding* changes, not only when a
  table's shape does, and names 'what a walk records' as one of the two triggers - a change to how
  a field is derived leaves every existing cache serving the old value, undetected by the version
  or depth checks. This fix changes which rows the walk writes for a package whose own root name
  starts with `_`, which is exactly that trigger. `SCHEMA_VERSION` (`src/venvaxi/_store.py:29`)
  moves 9 to 10 (Approach step 12). The counter-argument raised at the first stage 02 pass - that
  it forces a rebuild of every cached package for every user, for a correction that touches only
  `_`-rooted roots - is the trade-off that spec section has already weighed and rejected, and
  `specs/README.md` Invariant 2 forbids working around a spec in code rather than conforming to
  it. What remains is a genuine residual cost rather than a decision still to make: every cache,
  including one holding no `_`-rooted package at all, rebuilds once on first query after upgrade -
  the same one-time price the #89 and #124 bumps already charged, paid again here.
- **The `_pytest` figures are pinned to an installed version, and the rule is not.** The 326
  removed rows, the 2986-row graph and the 27-to-15 drop on `_pytest.cacheprovider` are all
  measured against `pytest==9.1.1` in this venv. A future release restructuring `_pytest`'s
  re-exports moves every one of those numbers without moving the rule, exactly as
  `plans/private-submodule-contract.md` flags for its own 53/5/48 arithmetic. That is why
  criterion 8 is pinned by a fixture rather than by the live check: the live numbers are the
  observation that drove the re-entry and are re-derived at each stage, never copied forward.
- **The fixture edit's collateral is the finding, and the cheap way round it hides the finding.**
  Importing from `package._impl` instead would bind no new public attribute and move no existing
  assertion, which makes it the tempting choice and the wrong one twice over: it cannot
  discriminate the root exemption from the private-home carve-out under mutation (Approach step
  3), and it would suppress exactly the observation stage 02 is meant to make.
- **Criterion 7's fixture demonstrates the branch, not the narrative.** The stage 01 gate resolved
  it to a standard-library home, which reaches `continue` by the identical path a third-party home
  does and costs no coupling to an installed package's surface. What it does not show is the
  vendored-dependency case the rule was written for - keeping a package's imported third-party
  names out of its own API. If that is ever wanted it belongs in the opt-in `-m conformance` tier
  (#71, PR 84), which exists for real-dependency checks, and not in the default suite.
- **Excluding `specs/commands/show.md` from both fields is a judgement call**, argued in
  Implements rather than mandated by `plans/README.md`. A reviewer could weigh the diffstat
  argument differently, and the re-entry gives them a second angle to weigh it from - `show --api`
  is the surface on which the underscore-rooted duplication was observed, even though the code
  that produced it is the walk's. Flagged here rather than decided silently, as #87 flagged the
  identical call for `specs/commands/tree.md`.

## Notes

**Re-entered stage 01 from the stage 02 gate.** Approach step 10's probe - written as a
report-only check against a package whose own root name starts with `_` - reproduced.
`venvaxi show _pytest.cacheprovider --api` returned 27 symbols including `Session` (homed
`_pytest.main`), `Config` (`_pytest.config`), `Parser` (`_pytest.config.argparsing`), `TestReport`
(`_pytest.reports`) and eight more, every one a **public** sibling re-export in an `__all__`-less
module below the root, which the subsection stage 01 had just written says shall not be recorded
there. `rich.align`, the same shape one level down under a public root, dropped all four of its
equivalents. The cause is that the carve-out re-spelled the private-submodule rule inline as
`any(segment.startswith("_") for segment in obj_home.split("."))`, scanning the root segment too,
while `is_private_submodule` - which exists to encode that rule - slices `[1:]` and excludes the
root deliberately, because the top-level package is walked directly rather than discovered as one
of its own submodules. For a root such as `_pytest` the root segment satisfies the inline test on
its own, so every same-root home fell into the carve-out.

**The gate decided to fix the code and leave the declared sentence alone**, over two rejected
alternatives: filing it for a later unit (which would leave a spec on the default branch that is
false for a live package, the divergence `specs/README.md` Invariant 2 calls a bug rather than
debt), and amending the spec to bless the widening (which would declare an implementation
artefact as intent, the opposite of #106's framing and #87's before it). Read at the right level
this is arguably a defect in **#87's** private-submodule contract rather than a change to #106's
filter: the carve-out is #87's rule, and it was encoded twice, once as a function with a docstring
explaining the root exclusion and once as an inline expression that forgot it. The fix deletes the
second copy.

**The declared text did not move, and that was checked rather than assumed.** Re-reading
`### Re-exported symbols` and `### Private submodules` after the fix: the below-the-root rule is
stated over 'the package's own root module' with no reference to how the root is spelled; the
carve-out bullet is stated over 'a private submodule of the same package root' and cross-references
`#private-submodules`, which already states the root-vs-recursion asymmetry explicitly and already
names `_pytest` as its worked example. Post-fix the carve-out's condition is exactly
`obj_home.startswith(f"{package_root}.") and is_private_submodule(obj_home)`, which is that bullet
transcribed. No `_`-rooted exception needs stating, and stating one would contradict
`#private-submodules`.

**What moved instead was the plan's own claim about itself.** `specs/behaviors/symbol-graph.md`
went from `authors:` to `specs:`, and with it the whole Implements argument, rewritten rather than
patched - see there. The short form: `authors:` was correct while the premise 'the code is already
correct, there is nothing to bring into conformance' held, and probe 2 falsified the premise. The
sentence stage 01 wrote became binding the moment it was written, and the code was already out of
conformance with it for one class of package. That also un-vacuums stage 03's spec-comparison
step, which this plan had explicitly declared vacuous by design.
`plans/private-submodule-contract.md`'s Notes record the same reversal happening to it, from the
other direction: it added a `specs:` entry mid-run and un-vacuumed its own stage 03 discharge.

**A fixture, not a live check, for criterion 8.** `plans/private-submodule-contract.md` proved its
own `_`-rooted criterion (6) live against `_pytest`, and flagged in its Risks that a future
`pytest` release could move the counts without moving the rule. The same option was open here and
was declined, because the two criteria need different things from the package. #87's needed a
package with *real private submodules discovered by recursion*, which no fixture carried and which
a fixture would have had to grow. #106's needs only a root whose *name* starts with `_` - a
four-file fixture expresses it exactly, deterministically, in the default suite, and can be
mutated. `tests/resources/_private_root/` re-exports `Carved` from a private sibling and `Exposed`
from a public one into an `__all__`-less `facade`, and criterion 8's test asserts both halves
because the pair is what discriminates: the drop alone would also pass with the carve-out deleted,
and the keep alone would also pass with the pre-fix inline test. The live `_pytest` figures stay
in the record as the observation that drove the re-entry, re-derived at each stage rather than
copied forward.

**Show-it-failing applies to criterion 8's test and is discharged in full**, which makes it the
one test in this plan that does not need the mutation-testing substitute. The other four are
characterization tests of already-shipped behaviour, where
`ICM/_config/reference-toolchain-pytest.md`'s SHOULD - scoped to 'a test written for a bug fix' -
does not apply and the substitute is announced instead. Criterion 8's test *is* written for a bug
fix, and the fourth mutation round is not a synthetic previous implementation: reverting
`is_private_submodule(obj_home)` to the inline `any(...)` restores the exact code that shipped, so
the round is a show-it-failing run and a discrimination proof at once. It fails with
`AssertionError: assert 'Exposed' not in ['Carved', 'Exposed']` - the fixture-scale spelling of
the `_pytest` symptom.

**The schema-bump question raised in Risks is resolved, not left for a later gate.**
`specs/behaviors/cache-refresh.md`, Schema version covers the builder, not just the shape, states
the bump MUST be taken whenever the content the store ends up holding changes - written or
deleted - and names 'what a walk records' as one of its two triggers, independent of whether a
table's shape moved. This fix changes which rows the walk writes for an `_`-rooted package's
`__all__`-less submodules, which is exactly that trigger, so `SCHEMA_VERSION` moves 9 to 10
(Approach step 12; `src/venvaxi/_store.py:29`). The rebuild-cost objection this plan's first
stage 02 pass raised - that the bump forces a rebuild of every cached package for every user, for
a correction that touches only `_`-rooted roots - is the exact trade-off that spec section
already weighs and rejects; declining the bump to avoid it would be working around a spec in
code, which `specs/README.md` Invariant 2 forbids.

**No new Validation criterion is added for the bump, unlike the #89 precedent.**
`plans/cache-version-resolution.md` added a criterion pairing its `7 -> 8` bump with a dedicated
regression test that reconstructed the exact pre-fix stale row (a database at schema 7 holding a
`package_builds` row recorded `version=""`) and confirmed it was dropped on open - warranted
there because the bug was in the *comparison* (`"" == ""` compares equal forever), so the
generic mismatch-eviction test could not, by itself, demonstrate that the specific stale shape
the issue reported would actually be caught. Here the mismatch is an ordinary `PRAGMA
user_version` inequality, already exercised content-independently by
`tests/test_store.py::test_schema_version_mismatch_rebuilds_tables`, which parametrizes on the
`SCHEMA_VERSION` constant rather than a literal and so needs no edit to keep proving that any
stale version, whatever it is, is dropped and rebuilt. What is specific to *this* bump - that the
fixed walk no longer writes the duplicate public-sibling rows - is already what criterion 8's
test (`::test_show_module_below_root_rule_holds_for_underscore_root`) proves about the walk
itself. Composing the two facts already on record (any stale schema is evicted; the fixed walk
writes fewer rows) establishes what a dedicated eviction test would otherwise re-demonstrate, so
one is not added here. A reviewer weighing the #89 precedent more literally could still ask for
one; flagged here rather than decided silently, in the same spirit as the two judgement calls
already recorded above.

**The stage 04 gate found a packaged-skill divergence, and closeout stopped there.**
`specs/behaviors/skill-content.md` requires the packaged skill to carry an entry for each observed
failure mode costing an agent a wasted query or a wrong conclusion, and to state plainly where the
AXI cannot answer a class of question. `src/venvaxi/SKILL.md` carries no entry for the rule this
plan declares, and the omission is not a stylistic gap - it is the same divergence #87 found at
its own stage 04 gate, one level up, and for the same reason the same file was the subject.

The evidence is live rather than derived. `rich.align` binds `Constrain`, `JupyterMixin`,
`Measurement` and `Segment` from public siblings and declares no `__all__`, so under the newly
declared below-the-root rule none of the four is recorded there. Two observable consequences
follow, and the second is the one that bites:

- `uv run venvaxi inspect "rich.align::Measurement"` answers `error: true`,
  `message: "Symbol rich.align::Measurement not found"` at exit `1`, with a `help[]` naming
  `venvaxi --help` and not `find`. The facade spelling is the one the reading agent has in hand,
  because it is the spelling the code under review imports by; the skill teaches that exit `1`
  means 'fix the query', and offers no route from there to the home spelling.
- `uv run venvaxi inspect rich.align` answers `children count: 9`, a definitive listing under
  `specs/behaviors/output-contract.md#bounded-collections` that silently omits four classes the
  module genuinely binds, while keeping five typing constructs the filter's class-and-function
  test lets through. There is no error and no signal - this is the private-submodule shape
  exactly: a confidently-complete answer that is not.

The neighbouring entry makes it worse rather than covering it. 'Private submodules are not
indexed' ends 'Symbols a public module re-exports from a private one *are* indexed, so query the
facade (`inspect pkg.api`)' - which is the carve-out stated without the rule it carves out of, and
an agent generalising that sentence to a public-sibling re-export reaches precisely the wrong
conclusion. That is #106's own framing ('`specs/` states an exception to a rule it never states')
reproduced inside `SKILL.md`, and #87 used the identical comparison - 'Dunders are not indexed',
the same shape of deliberate walk exclusion producing a confidently-empty answer - to conclude the
skill owed an entry.

**Not fixed here, because it is not a closeout edit.** Adding the entry brings
`src/venvaxi/SKILL.md` into conformance with an already-binding spec, which moves
`specs/behaviors/skill-content.md` into this plan's `specs:`, adds a Validation criterion, and
un-vacuums stage 03's spec-comparison step over a surface it never saw - the same delta #87 took.
Under the workspace re-entry rule that returns to stage 01, and it is the human's decision at this
gate rather than an edit stage 04 may make. The plan is therefore left at `status: in-progress`,
no Validation box ticked, no follow-up filed and nothing committed.

**What such an entry would owe the drift gate (PR 127).** `tests/test_skill_drift.py` triages
every concrete invocation the skill's prose names: `test_every_documented_invocation_is_triaged`
requires each one to be either a `WORKED_EXAMPLES` row with an executed check or a
`NOT_AN_EXAMPLE` row with a recorded reason, and `test_no_non_zero_result_count_in_prose` forbids
the entry stating a count like `children count: 9` in prose. An entry written around `rich.align`
is executable against the venv this project installs for itself, so it belongs in
`WORKED_EXAMPLES` with a check asserting the taught property - the facade spelling misses and the
`find` route resolves - rather than equality against a recorded block, per that spec's first
limit. `tests/test_skill_parity.py` requires `.claude/skills/venvaxi/SKILL.md` to be regenerated
byte-identically in the same edit.

**Re-entered stage 01 a second time, from the stage 04 gate, and the human accepted the
re-entry.** The paragraphs immediately above record what stage 04 found and why it declined to fix
it; this one records the delta that was then run, and supersedes 'Not fixed here'. The delta is
stage 01 and stage 02 only: no spec text is written, `specs/behaviors/skill-content.md` moves into
`specs:` as a conformance subject, Scope, Implements and Approach gain the skill entry, Validation
gains criterion 10, and stage 02 writes the entry, the mirror and the drift-gate rows. Stages 03
and 04 are re-run by other parties; nothing here ticks a box or amends their reports.

**The evidence was re-derived at this stage rather than copied from the stage 04 report**, per the
same discipline this plan applies to the `_pytest` figures. Against this venv: `rich/align.py`
declares no `__all__` and binds `Constrain`, `JupyterMixin`, `Measurement` and `Segment` from
public siblings, plus `chain` from `itertools`. `venvaxi inspect "rich.align::Measurement"` exits
`1` with `Symbol` `rich.align::Measurement` `not found` and a `help[]` naming only
`venvaxi --help`. `venvaxi find Measurement --package rich` resolves the bare name, leading with
the class at its home spelling. `venvaxi inspect rich.align` exits `0` with a children listing
that keeps the five typing constructs and drops all four classes. 241 instances of the shape in
`rich`, 313 in `polars` - the stage 04 sweep, not re-run here.

**Why it clears `skill-content.md`'s bar, in that spec's own terms.** Two of its rules are
engaged, not one. `What the skill must cover` requires an entry for each observed failure mode
costing an agent *a wasted query **or** a wrong conclusion*, naming the correct move rather than
only the symptom - the facade miss supplies the first, and the module listing supplies the second
with no error to prompt a retry. Its `Local` principle sets the test in both directions: an entry
earns its place only if an agent would act differently for having read it, and a failure mode
observed in the field is added even where its section is already the longest in the file. An agent
that reads this entry runs `find` instead of retyping the facade spelling, and reads a module
listing as the graph's record rather than the module's contents. Neither is derivable from the
file as it stood.

**The counter-argument, weighed and rejected.** The skill's three-step workflow - scan the code,
`find <name> --package <pkg>`, `inspect <qualified_name>` - already routes around the failure
entirely: an agent following it never types a facade-spelled symbol and never reads a module
listing as an inventory. On that reading the entry is redundant with the workflow and costs
context on every task the description matches. It loses on three counts. The skill itself steers
off the workflow, offering `inspect rich.console` for direct-children discovery and telling the
agent to query facades in the private-submodule entry, so the two failure paths are ones the file
opens rather than ones an agent wanders into. The trigger in the spec is a disjunction, and the
module-listing half is a wrong conclusion the agent cannot detect - the workflow prevents it only
for an agent who never departs from the workflow, which is not the population the Gotchas section
is written for. And the third count is the decisive one: the existing private-submodule sentence
is not merely silent about the rule, it teaches the carve-out as though it were general, so
leaving the section alone is not a neutral choice between covering and not covering - it is
leaving a sentence in place that points at the failure. That is why the edit *reconciles* rather
than appends.

**Issue #87 took this exact delta from this exact gate, and the mirror is close enough to be
worth stating.** `plans/private-submodule-contract.md` re-entered stage 01 a second time from
its own stage 04, for the same file, under the same two rules of the same spec, moving
`skill-content.md` into `specs:` while its behaviour specs stayed in `authors:`. The difference
here is the causal ordering set out in Implements: #87's rule was declarable and its entry
writable in either order, whereas this entry was *forbidden* until
`### Re-exported symbols` existed, because
`skill-content.md` bars the skill from restating a claim `specs/**` does not declare. The
similarity that matters more is the failure #87 recorded against itself - un-vacuuming stage 03's
spec-comparison discharge and then reporting it without an independent re-run. This delta is
handed to stage 03 undischarged for exactly that reason.

**One drift-gate harness change, and why it is not scope creep.** `tests/test_skill_drift.py`
dispatched each worked example as `int(args.func(CLIContext(args=args)))`, which lets a raise
escape - so a documented query whose *result is a miss* could not be run at all, and the only
triage left for it would be `NOT_AN_EXAMPLE`, recording a query the skill does document a result
for as documenting none. That is the 'four examples of five' `skill-content.md`'s third limit
forbids, dressed as a green run. The executor now carries an `except Error` arm mirroring
`venvaxi.__main__.main()` - the same `format_error` call, the same `CLI_ERROR_HINT`, the same
`EX_FAILURE` - so the check sees what the CLI would emit. The gate's reach widened by one shape;
no claim it makes about the skill was weakened.

**The three checks assert taught properties, and they were mutation-tested rather than trusted.**
None pins a count or a home module: the facade check asserts the class really is bound into
`rich.align` *and* that the query fails, the listing check asserts the module binds classes it
does not list, and the `find` check asserts the leading row is the class at a `qualified_name`
that is not the facade. The set of re-exported names is read off the live module rather than
frozen, so a `rich` release moving them is not reported as skill drift. Discrimination was proved
by mutating the depth guard in `_walk_module` from `depth > 0` to `depth > 99` - which is the
filter switched off - and re-running: both `rich.align` checks failed
(`assert not ({'Constrain', 'JupyterMixin', 'Measurement', 'Segment', 'chain'} & {...})`), and the
guard was restored and re-verified green. The `find` check survived the mutation, as recorded
rather than as a gap: what it pins is the recovery route - a bare name leading to a class at a
home spelling other than the facade - and that route is unchanged by whether the facade also
carries a row. Discrimination of the filter itself is the two `rich.align` checks' job, and they
do it.

**The stage 01 re-entry did not reach `CHANGELOG.md`, and closeout did.** The delta that added
the packaged-skill entry, its reconciled neighbour and the three drift-gate rows amended Scope,
Implements, Approach, Validation and Notes, but left the changelog carrying only the declaration
and the carve-out fix. The skill ships in the wheel and is written into consuming repos by
`venvaxi setup`, so an edit to it is user-facing by definition. A third `Changed` entry was added
at closeout covering the entry, the rewording, the mirror regeneration, the three executed rows
and the executor's `except Error` arm. Recorded because a re-entry that touches every other
section is exactly where a changelog entry goes missing unnoticed.

**The coverage-report break is fixed, and the fix is not where stage 03's delta looked for it.**
Pass 1 recorded `uv run coverage report` failing with `No source for code` against the
`_private_root` fixture's copied tree, diagnosed correctly: `pyproject.toml`'s
`[tool.coverage.run] omit = ["tests/*", "*/src_test*/*"]` does not match a directory named
`src_private_root0`. The fix taken was to rename the fixture's temp prefix rather than widen the
pattern - `tests/conftest.py`'s `fake_private_root_package` calls
`tmp_path_factory.mktemp("src_test_private_root")`, whose `src_test` substring the existing glob
already matches - so `pyproject.toml` is deliberately unchanged. The stage 03 delta re-ran
`coverage report` three times, got exit `0` at 98% each time, checked `git diff pyproject.toml`,
found it empty, and concluded the gap was "still present in the config as written" with the
failure's disappearance unexplained. It read the right file and the wrong one: the config is
untouched *because* the fixture moved to meet it. Recorded here because the delta leaves that as
an open discrepancy for the gate, and it is not one. Re-verified at closeout: `coverage report`
exit `0`, `TOTAL 1385 24 98%`.

**The third follow-up was withdrawn at closeout, because the premise was false.** This run
carried a claim - written into the stage 03 delta and repeated in the stage 04 report - that
`prek run --all-files` reads `git ls-files` and therefore silently skips untracked files, so the
all-pass line covered neither `plans/reexport-filter-contract.md` nor
`tests/resources/_private_root/`. It was approved as an issue to file. Tested directly before
filing, twice, rather than trusted: an untracked `_prek_probe.py` at the repository root, and a
second inside the untracked `tests/resources/_private_root/` directory, each carrying an unused
import and non-canonical spacing. Both times `uv run -m prek run --all-files` **failed** -
`pkgdx-lint` "Found 1 error (1 fixed, 0 remaining)", `pkgdx-format` "1 file reformatted" - and the
probe file came back rewritten. `git check-ignore` confirms neither the plan nor the fixture
directory is ignored. `prek` covers untracked, non-ignored files, including inside a wholly
untracked directory; the claim was inherited, propagated through two stage reports, and never
checked until the step that would have made it public. No issue was filed. The stage 03 delta's
extra `prek run --files ...` pass over those paths was therefore belt-and-braces rather than the
gap-closing it describes itself as - harmless, but it is evidence for a blind spot that does not
exist.

## Follow-ups

- **Issue [#130](https://github.com/andyrids/venv-axi/issues/130)** - a submodule reaches
  `show --api` as an `attribute` row. `inspect.ismodule(obj) -> continue` sits inside the
  `explicit_exports is None and depth > 0` branch (`src/venvaxi/_introspect.py:750-752`), so it
  does not run for a root without `__all__` that imports its own submodules, nor for any module
  whose `__all__` names a submodule; `_classify` returns `ATTRIBUTE` for a module object and
  `get_public_api` excludes only the `MODULE`/`PACKAGE` kinds. Live: `venvaxi show venvaxi --api`
  reports `exceptions` as kind `attribute`, contradicting `specs/commands/show.md`'s "Submodules
  are the one exclusion, and it is a depth exclusion rather than a kind one". Confirmed
  pre-existing on `develop` and independently re-derived by `icm:spec-drift-auditor` at stage 03.
  `tests/test_introspect.py::test_get_public_api_excludes_module_and_package_kind` pins the
  artefact on purpose (`assert "module" in names`, with a NOTE) so a fix trips it; the issue says
  so. Named in this plan's Scope as "its own issue at stage 04 closeout if it reproduces".
- **Issue [#131](https://github.com/andyrids/venv-axi/issues/131)** - `show venv-axi --api` fails
  under this editable install. `packages_distributions()` maps no import name to the `venv-axi`
  distribution, because the editable install's RECORD lists only `_editable_impl_venv_axi.pth`
  and there is no `top_level.txt`, so `resolve_import_and_distributions`
  (`src/venvaxi/_introspect.py:296-329`) falls back to the dash substitution `venv_axi` and the
  caller is told the package failed to import. Checked against
  `specs/behaviors/package-resolution.md` before filing, as the routing depends on it: the
  behaviour **conforms to the letter** of "if a distribution is installed but its module cannot be
  located, then the resolver shall report it as broken" while defeating the purpose clause of the
  same spec's Ordering paragraph and its "why three classes and not two" rationale, and the
  metadata-driven resolution the code actually performs is nowhere declared. Undeclared rather
  than divergent, so `ICM/process-plan` and stage 01 own it. Incidental to #106, found while
  probing at stage 02 and re-run at stage 03 (Probe 3).
- **Withdrawn, not filed** - `prek run --all-files` silently skipping untracked files. Approved as
  the third issue and falsified by direct experiment before filing; see Notes. No tracker entry
  exists for it and none should.
- **Deferred to** - none.
- **Tracked as** - none.
