---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/tree.md
  - specs/commands/show.md
  - specs/commands/inspect.md
  - specs/mcp/tools.md
  - specs/behaviors/symbol-graph.md
  - specs/behaviors/skill-content.md
authors: []
issues: [104, 105]
pr: 107
---

# Plan: Private submodule hints

## Scope

`private-submodule-contract` ([#87](https://github.com/andyrids/venv-axi/issues/87), PR #103)
declared the private-submodule skip. Declaring it made the next defect legible: on three surfaces
a private submodule is indistinguishable from a module that does not exist, and on two of them
the answer is a definitive success an agent is meant to stop searching on.

| Surface      | Private submodule                     | Nonexistent submodule |
| ------------ | -------------------------------------- | ----------------------- |
| `tree`       | `count: 0` + hint naming `tree pkg`    | identical                |
| `show --api` | `count: 0` + hint naming `tree pkg._impl` | raises, `EX_FAILURE`  |
| `inspect`    | `` Module `pkg._impl` not found ``     | identical                |

`show --api`'s hint is the sharpest defect: it routes to `tree pkg._impl`, which itself answers
`count: 0`, so the offered recovery confirms the empty answer a second time.
[#104](https://github.com/andyrids/venv-axi/issues/104) and
[#105](https://github.com/andyrids/venv-axi/issues/105) name the `tree` and `show --api` cases;
`inspect` was not filed as its own issue - it was folded in at the planning gate, because fixing
two of three surfaces and leaving the third silent teaches an agent the wrong lesson from the one
left behind.

**This is a bug fix, not a declaration.** Unlike `private-submodule-contract`, show-it-failing
applies here: every new assertion must be shown failing against the pre-fix code before it is
shown passing against the fix.

The strongest single piece of evidence is already on disk.
`tests/test_cli.py::test_command_tree_empty_hint_names_root_tree` parametrizes
`["nosuchmodule", "_impl"]` against one assertion, precisely because the two inputs produce
byte-identical output today. That parametrize is the defect written down as a passing test.
Splitting it into two assertions - one per input, each expecting *different* text - is the
show-it-failing evidence for the `tree` surface: stage 02 must show the split assertion for
`"_impl"` failing against the pre-fix hint before the fix makes it pass.

**The predicate.** Reachability is not "the final segment starts with `_`". `_walk_submodules`
skips at *every* recursion level, so `pkg._impl.sub` is unreachable through `_impl` even though
`sub` itself is a plain name - the walk never reaches far enough to discover it. The correct test
is **any non-root segment starting with `_`**:

```python
segments = name.split(".")
any(segment.startswith("_") for segment in segments[1:])
```

The root is excluded deliberately. A top-level package named `_pytest`, queried as the root, is
walked in full -
[Private submodules](../specs/behaviors/symbol-graph.md#private-submodules) records this at 53
submodules / 5 underscore-prefixed / 48 recorded, live against `pytest==9.1.1`. A predicate keyed
on the whole name would misreport every `_pytest.*` query as private, including the root itself.

Out of scope, each with where it went:

- **Changing what is walked.** The skip in `_walk_submodules` stays exactly as it is; only the
  *reporting* of an already-private answer changes, on the surfaces named above.
- **The wider `depth > 0` re-export filter.** `_walk_module`'s general `__all__`-absence
  behaviour is a separate, larger unit -
  [#106](https://github.com/andyrids/venv-axi/issues/106), filed at
  `private-submodule-contract`'s closeout.

## Implements

`specs/commands/tree.md` - the empty-state paragraph in Outputs gains an `If <trigger>, then`
criterion: when the named submodule is private, the hint says so before naming the root's own
tree, distinguishing it in wording (not in target - the existing hint was already root-scoped)
from the nonexistent/failed-import case that reaches the same branch.

`specs/commands/show.md` - the Outputs section's existing two-zero split ("the two zeroes mean
opposite things") gains a third zero. When the named module is private, the hint switches its
*target*, not only its wording: from `venvaxi tree <package>` (which answers `count: 0` for the
identical name) to `venvaxi show <root> --api` (the root's own public surface).

`specs/commands/inspect.md` - Failure modes gains a criterion: a module-mode miss on a private
submodule still raises `SymbolNotFoundError` and exits `EX_FAILURE` (the failure mode itself is
unchanged), but the message now states the module is private and never indexed rather than
merely "not found". Symbol-mode misses are explicitly carved out as unaffected.

`specs/mcp/tools.md` - `## Hint wording` gains a worked example naming the specific trap: mirroring
`tree`'s private case changes only `getModuleTreeTool`'s sentence (already root-scoped), while
mirroring `show --api`'s private case must also change `showPackageApiTool`'s *target* - away
from `getModuleTreeTool` scoped to the given (private) name, to `showPackageApiTool` itself
scoped to the root.

`specs/behaviors/symbol-graph.md` - `### Private submodules`'s first two `If <trigger>, then`
bullets are amended, not merely cited. The first declared that `inspect`, `tree` and an MCP module
lookup "shall answer as it does for a module that does not exist" - true of the graph node (still
none is recorded) but no longer true of what the caller is told, which is exactly what this plan
changes. The second bullet's closing clause called `show --api`'s empty answer "the least
distinguishable from a module that genuinely exposes nothing at this level" - also no longer true
once its hint carries the distinguishing fact. Both bullets are rewritten to separate the graph
fact (unchanged) from the observable answer (changed), per `specs/README.md` Invariant 2:
spec/code divergence created in the act of fixing one thing is still divergence.

`specs/behaviors/skill-content.md` is listed in `specs:` because `src/venvaxi/SKILL.md`'s
"Private submodules are not indexed" gotcha - added under the `private-submodule-contract` plan -
asserts two claims this plan falsifies: "its hint routes to `tree pkg._impl`, which is `count: 0`
as well" and "`inspect pkg._impl` raises instead, exactly as a module that does not exist would".
Both become false the moment the code conforms to the amended specs above. The rule spec itself -
`specs/behaviors/skill-content.md` - needs no text change: it already requires the skill restate
no claim `specs/**` does not declare, and already requires an entry per costly failure mode; this
plan does not change what the rule demands, only what the code (and, downstream, the skill) must
say to satisfy it. Confirmed by reading the rule spec in full at stage 01; recorded here rather
than assumed.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. Add a shared predicate beside `_walk_submodules`'s own skip in `_introspect.py` - the walk's
   per-level check and the reachability predicate are one rule stated twice, and adjacency is
   what keeps a future divergence between them visible. See the techspec for the exact call
   sites.
3. `command_tree` (`_cli.py`) - branch the existing empty-`pairs` hint on the predicate. Private:
   new wording, same root target. Not private: unchanged.
4. `_command_show_api` (`_cli.py`) - branch the existing empty-`symbols`, not-capped hint on the
   predicate. Private: retarget to `venvaxi show <root> --api`. Not private: unchanged
   `venvaxi tree <package>` hint.
5. `show_module` (`_introspect.py`) - branch the `SymbolNotFoundError` message on the predicate
   when `node is None`. Private: message states the module is private and never indexed. Not
   private: unchanged "not found" message. This is shared code, so `_command_inspect_module`
   (CLI) and `show_module_tool` (MCP) inherit the change identically with no per-surface branch
   of their own.
6. `get_module_tree_tool` (`_mcp.py`) - mirror step 3, phrased for the MCP caller per
   `specs/mcp/tools.md` Hint wording.
7. `show_package_api_tool` (`_mcp.py`) - mirror step 4, including the target switch (not only the
   wording) called out in the amended `## Hint wording`.
8. Split `tests/test_cli.py::test_command_tree_empty_hint_names_root_tree`'s
   `["nosuchmodule", "_impl"]` parametrize into two assertions expecting different hint text. Run
   the `"_impl"` case against the pre-fix code first and record it failing - this is the
   show-it-failing evidence named in Scope.
9. Add regression coverage for the `show --api` target switch, the `inspect` message split, both
   MCP mirrors, and the root-exclusion contrast (`_pytest`) - see Validation for the criteria
   each test must evidence.
10. Bring `src/venvaxi/SKILL.md`'s "Private submodules are not indexed" gotcha into conformance
    with the amended specs, and regenerate `.claude/skills/venvaxi/SKILL.md` to stay
    byte-identical, per `specs/behaviors/skill-content.md` Applies to.
11. `CHANGELOG.md` entry under `Fixed` - this corrects a misleading answer, not merely declares
    one.

## Validation

- [x] If `tree` is invoked on a dotted name whose non-root segment starts with `_`, then the
      `tree` command shall emit `count: 0` and a hint stating the name is private and never
      indexed, naming the root package's own tree as the modules that are indexed. —
      `tests/test_cli.py::test_command_tree_empty_hint_names_private_submodule` (asserts the
      complete sentence, including "for the modules that are indexed"; failed pre-fix on the
      missing final word, fixed and re-verified at the stage 03 gate - see stage 03 report's Gate
      addendum)
- [x] If `tree` is invoked on a dotted name with no graph node for a reason other than privacy
      (nonexistent or failed import), then the `tree` command shall emit `count: 0` and the
      unchanged generic hint, textually distinct from the private-case wording above. —
      `tests/test_cli.py::test_command_tree_empty_hint_names_root_tree`
- [x] If `show --api` is invoked on a dotted name whose non-root segment starts with `_`, then the
      `show` command shall emit `count: 0` and a hint naming the root package's own public API
      (`show <root> --api`), and shall not name `tree`. —
      `tests/test_cli.py::test_command_show_api_private_submodule_hint_names_root_api`
- [x] If `inspect` is invoked in module mode (no `::`) on a dotted name whose non-root segment
      starts with `_`, then `inspect` shall raise `SymbolNotFoundError`, exit `EX_FAILURE`, and
      the message shall state the module is private and never indexed. —
      `tests/test_introspect.py::test_show_module_raises_for_private_submodule_named_directly`
- [x] If `inspect` is invoked in module mode on a dotted name with no graph node for a reason
      other than privacy, then `inspect` shall raise `SymbolNotFoundError` with the unchanged
      generic "not found" message, textually distinct from the private-case wording above. —
      `tests/test_introspect.py::test_show_module_raises_not_found_for_nonexistent_submodule`
- [x] If `getModuleTreeTool` is called with a `name` whose non-root segment starts with `_`,
      then it shall return `count: 0` and a hint stating the name is private and never indexed,
      phrased for the MCP caller and naming `getModuleTreeTool` with `name=<root>`. —
      `tests/test_mcp.py::test_get_module_tree_tool_empty_hint_names_private_submodule`
- [x] If `showPackageApiTool` is called with a `name` whose non-root segment starts with `_`,
      then it shall return `count: 0` and a hint naming `showPackageApiTool` with `name=<root>`,
      and shall not name `getModuleTreeTool`. —
      `tests/test_mcp.py::test_show_package_api_tool_private_submodule_hint_names_root_api`
- [x] If `showModuleTool` is called with a `name` whose non-root segment starts with `_`, then
      it shall return the TOON error block whose message states the module is private and never
      indexed, sharing the same wording `inspect` raises on the CLI. —
      `tests/test_mcp.py::test_show_module_tool_private_submodule_returns_toon_error`
- [x] When a top-level package whose own name starts with `_` (`_pytest`) is queried as the root
      on `tree`, `show --api`, or `inspect`, it shall not be reported as private - the root
      segment is excluded from the predicate, and the package resolves, walks and answers
      normally. — `tests/test_introspect.py::test_is_private_submodule_checks_every_non_root_segment`
      (`_pytest`/`_pytest.outcomes` cases); live re-check `uv run venvaxi tree _pytest
      --max-depth 1` → `count: 49`, no underscore-prefixed segment among the recorded names
- [x] The packaged skill's "Private submodules are not indexed" entry shall carry no claim this
      plan's amended specs falsify - specifically neither "its hint routes to `tree pkg._impl`,
      which is `count: 0` as well" nor "`inspect pkg._impl` raises instead, exactly as a module
      that does not exist would" - and the repository's own copy at
      `.claude/skills/venvaxi/SKILL.md` shall stay byte-identical to `src/venvaxi/SKILL.md`. —
      `src/venvaxi/SKILL.md` "Private submodules are not indexed" entry read in full at stage 04:
      neither falsified claim present; `diff src/venvaxi/SKILL.md .claude/skills/venvaxi/SKILL.md`
      empty (re-confirmed at closeout)
- [x] The test suite shall pass. — `uv run coverage run -m pytest` → `513 passed, 21 deselected`
      (re-run at closeout, matches stage 02/03)

## Risks / unknowns

- The `show --api` retarget changes which tool/command a hint names, not only its wording - a
  larger surface for a mismatch than the `tree` case, where only the sentence changes. Stage 02
  should verify the retargeted hint against a live `venvaxi show <root> --api` call, not only the
  fixture package, since a root that is itself empty at the top level would make the "resolved"
  hint just as unhelpful as the one it replaces - see the next risk.
- The `venvaxi show <root> --api` hint assumes the root package's own public API is non-empty.
  Where it is not (a package whose entire surface lives below private submodules with no
  re-exporting facade), the new hint is a definitive `count: 0` pointing at another definitive
  `count: 0` - not confirming the same query twice, but still not resolving anything. This is a
  narrower version of the defect this plan fixes, on a case the agreed hint wording does not
  address and this plan does not claim to solve; flagged rather than silently accepted.
- `_walk_submodules`'s own per-level check - the discovered segment's last dotted component,
  tested against a leading underscore - and the new whole-name predicate are deliberately two
  expressions of one rule, not one shared function
  call - the former checks one discovered segment during recursion, the latter checks every
  non-root segment of an already-fully-qualified name. Stage 02 must keep them adjacent in
  `_introspect.py` (per the techspec) so a future edit to one is legible against the other, but
  they are not literally the same code path and must not be forced into one without re-verifying
  both call shapes.

## Notes

**Why "any non-root segment starts with `_`", not "the final segment starts with `_`".**
`_walk_submodules` skips at *every* recursion level it visits, and it never recurses into a
submodule it has just skipped. So a private ancestor makes everything beneath it unreachable
regardless of that name's own spelling - `pkg._impl.sub` has no node even though `sub` itself is
a plain name, because the walk never gets far enough to discover it. A predicate keyed on only
the final segment would call `pkg._impl.sub` public. `_pytest._code` is the live non-fixture case
this run exercised. The root is excluded from the predicate for a different reason: a top-level
package is walked directly as the query root, not discovered as its own submodule during
recursion, so a name like `_pytest` queried bare must resolve normally - `specs/behaviors/
symbol-graph.md`'s Private submodules subsection states both halves.

**Why the predicate sits beside `_walk_submodules` rather than at the call sites.** It is
adjacency, not sharing, that keeps the two rules honest: `_walk_submodules`'s own per-level skip
condition and `is_private_submodule`'s whole-name check are deliberately two expressions of one
rule rather than one shared function call - the former tests one discovered segment during
recursion, the latter tests every non-root segment of an already-fully-qualified name. They agree
on every input the walk actually produces (stage 02
traced the induction; stage 03 confirmed it against a live `_pytest` walk), but forcing them into
a single call would rest that agreement on a non-local invariant (skip-then-never-recurse) that a
future edit to either one could quietly break without the other noticing. Placed adjacently in
`_introspect.py`, a future divergence between them stays visible in a diff instead of hiding
behind a shared abstraction.

**The retarget asymmetry.** `tree`/`getModuleTreeTool` change only their hint's *sentence* - the
target was already root-scoped (`venvaxi tree <root>` / `getModuleTreeTool` with `name=<root>`),
so stating privacy first changes nothing about where the hint points. `show --api`/
`showPackageApiTool` change the *target* as well: the old hint pointed at `tree <package>` /
`getModuleTreeTool` scoped to the *given* (private) name, which itself answers `count: 0` for the
identical name - the offered recovery confirmed the empty answer a second time rather than
resolving it (issue #105's whole defect). The fix retargets both to the root's own public surface
(`show <root> --api` / `showPackageApiTool` with `name=<root>`), matching `tree`'s hint in scope
though not in the surface it names.

**Why `inspect`'s message names no command, while the two hints do.** `show_module`'s
`SymbolNotFoundError` is raised once in `_introspect.py` and reaches `_command_inspect_module`
(CLI) and `show_module_tool` (MCP) unaltered - confirmed by reading both call sites, neither
wraps or re-raises it. `specs/mcp/tools.md`'s Error message wording rule requires a message
raised by logic shared with the CLI to stay true on both surfaces; "run `venvaxi inspect`" or
"call `showModuleTool`" would each be true on only one. Separately, `specs/behaviors/
output-contract.md` gives the CLI exactly one generic footer for every `Error` (`venvaxi --help`),
with no per-error hint mechanism to hang a command-specific recovery off of, and `_mcp.py`'s
`_toon_errors` wrapper is the same shape on the MCP side. The message therefore states the
reachable root as a fact ("`package` is the reachable root") rather than an instruction - the
only channel available that stays true unaltered on both surfaces - while the CLI still appends
its unrelated generic footer (`Run venvaxi --help for available commands`) on top, unchanged.

**The truncated-sentence defect.** The most valuable thing this run produced. The `tree`/
`getModuleTreeTool` private hint shipped reading "...for the modules that are", missing its final
word. It entered at the *planning* gate, in the option preview that settled the wording; stage 01
recorded it in the techspec as agreed text "settled ... MUST NOT be renegotiated at stage 02";
stage 02 implemented it faithfully, exactly as instructed - neither stage was at fault, the
string handed to them was already wrong. It was then pinned by a test asserting the broken text
was correct (the pre-fix `test_command_tree_empty_hint_names_private_submodule` asserted
"...for the modules that are" with no further check). What caught it was the plan's own
Validation criterion 1, which named the phrase in full - "as the modules that are **indexed**" -
written from the desired behaviour rather than transcribed from the shipped code, so it disagreed
with the implementation it was meant to certify. That disagreement is exactly why a criterion is
worth deriving from the spec/plan intent rather than copied off whatever the code already does.
Criterion 6 (`getModuleTreeTool`'s identical bug) passed at first verification despite sharing the
defect, because its wording was looser - it did not repeat the "modules that are indexed" phrase,
so nothing in the criterion text disagreed with the truncated string. Both halves are worth
recording: criteria are worth writing precisely, and worth writing *before* the code, because a
criterion transcribed from the implementation can only ever confirm what already shipped. Fixed
at the stage 03 review gate (word `indexed` added at the three sites pinning the string plus the
four occurrences in the techspec); re-verified, full suite and hooks green; recorded in the stage
03 report's Gate addendum, not in this run's body text, since the FAIL it corrects was accurate at
the time it was written.

## Follow-ups

- **Issue [#106](https://github.com/andyrids/venv-axi/issues/106)** - the wider `depth > 0`
  re-export filter (`_walk_module` drops any cross-module re-export when the exporting module
  declares no `__all__`). Named in this plan's Scope as out of scope, filed at
  `private-submodule-contract`'s closeout; not touched by this unit either.
- **Deferred to** - none.
- **Tracked as** - none.
