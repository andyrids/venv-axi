---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/skill-content.md
authors: []
issues: [39]
pr:
---

# Plan: Skill drift gate

## Scope

`specs/behaviors/skill-content.md` declares nine content rules for the packaged skill, and its own
Out of scope said none of them was enforced by anything: nothing compared the skill's claims
against the CLI, so every rule was a rule a person checked
([#39](https://github.com/andyrids/venv-axi/issues/39)).

`tests/test_skill_parity.py` pins `src/venvaxi/SKILL.md` and `.claude/skills/venvaxi/SKILL.md` to
each other. That is a real check and it cannot answer this question - both copies go stale
*together*, byte-identical and green. #39 records four confirmed instances:

| Instance | Where it lived |
| --- | --- |
| Exit-code contract wrong x3 (#58 run) | Prose, then the CHANGELOG |
| `setup` row missing `--skill` (#58) | Commands table |
| `getSymbolTool` wording falsified (#62) | MCP-differences prose |
| `find` worked example falsified (#94) | Fenced output block |

The drift class has three tiers, and only the third is genuinely unreachable:

1. **Checkable against a declared interface** - flags and their defaults, MCP tool signatures,
   exit codes.
2. **Checkable by execution** - a documented query and the result it returns.
3. **Prose with no counterpart** - the #62 instance: a sentence about an error message, sitting in
   no table and citing no flag.

This unit builds 1 and 2, and declares 3 as residue rather than letting it be assumed covered.

**The blocker has cleared.** #39 required #94 to land before the executed check could pass. #94
landed (PR [#109](https://github.com/andyrids/venv-axi/pull/109)) and the flagship example now
reproduces exactly - `venvaxi find Console.print --package rich` returns `count: 3` with `print`,
`print_json`, `print_exception`, matching `src/venvaxi/SKILL.md` line for line.

Out of scope, each with where it went:

- **A prose-matching test over the skill's sentences** - rejected in #58 for covering one sentence
  while implying coverage of twenty, and rejected again here for the same reason. Tier 3 is
  declared in `specs/behaviors/skill-content.md` Out of scope as review-enforced, not gated.
- **Executing an example naming a package the project does not install** - `inspect numba::njit`
  is one. The spec requires it be recorded as unexecutable rather than passed over, so the gate
  reports the gap instead of a silent green. Adding `numba` to the dev group to close it is not
  proposed: a heavy compiler dependency to check one gotcha is the wrong trade.
- **Gating the eval suite** - `.claude/skills/venvaxi/evals/` is run by a person, never by CI.
  [#40](https://github.com/andyrids/venv-axi/issues/40) owns it and this unit does not move it.
- **Scraping `--help` output as the authority the gate reads.** The parser is what `--help` renders
  from, so the parser is what the gate introspects. `specs/README.md` Invariant 4 is satisfied by
  either, and this is the one that does not break on an argparse formatting change.

## Implements

`specs/behaviors/skill-content.md`, in `specs:` because this plan changes code until the spec's
new clauses hold.

The spec gained a **What is machine-checked** subsection at stage 01 declaring five conditional
rules - the command table's flags and defaults, the command table's completeness against each
command's real flags, the MCP tool table against registered signatures, the exit codes against
[Output contract](../specs/behaviors/output-contract.md), and a documented query against the venv
the project installs for itself - plus three limits that belong to the rule rather than being
exceptions to it:

- A documented result is venv-dependent, so an executed check asserts what the example teaches and
  never equality against the recorded block.
- An unexecutable example is recorded as such rather than passed over.
- A non-zero result count stated in prose gives way to the results the example teaches by. A fenced
  block reproducing real output keeps what it recorded, and `count: 0` is exempt as an empty state
  the output contract declares rather than a measurement of an installed version.

Its Out of scope bullet was **narrowed, not deleted**. The old bullet said nothing compares the
skill's claims against the CLI. The new one says a claim naming no flag, no exit code, no MCP tool
and no runnable query has nothing to diff against and stays enforced at review, citing the #62
instance as the shape of that residue.

**Read at stage 01 and deliberately not amended**, recorded rather than assumed:

- `specs/behaviors/output-contract.md` - the exit-code table is the authority the new clause cites.
  Nothing about what an exit code means moves; the clause asserts the skill agrees with it.
- `specs/commands/setup.md` - declares the installed skill byte-identical to the packaged source.
  Untouched: this unit adds a check against the *code*, and says nothing about how the copies
  relate to each other.
- `specs/mcp/tools.md` - each tool's contract is unchanged. The clause asserts the skill's table
  matches the registered signature, which is a claim about the skill, not about the tool.
- `specs/principles.md` - the skill's token-efficiency pointer is unchanged. The registry the gate
  reads lives in the test, so the ambient context pays nothing for being checkable.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. `src/venvaxi/__main__.py` - extract `build_parser()` from `main()`, returning the fully
   configured top-level parser. `main()` calls it and is otherwise unchanged. A refactor with no
   observable behaviour change; it exists so the gate introspects the real parser object rather
   than a reconstruction of it.
3. `tests/test_skill_drift.py` (new) - tier 1, default tier, needing no third-party package.
   - Parse the skill's Commands table. For each row resolve the subparser and assert every flag
     named is among that parser's option strings, and that each parenthesised default equals the
     parser's own default.
   - The completeness direction: every non-global flag on each subparser appears in that row.
     Global flags (`-v`/`--verbose`, `--version`) are documented in prose rather than the table and
     are excluded by name, not by a heuristic that would silently absorb a third.
   - Parse the MCP tool table. Assert its tool names are exactly the camelCase names
     `venvaxi._mcp` registers, and that each row's parameters and defaults match the underlying
     function's signature.
   - Assert every exit code the skill names is a value the output contract declares, that every
     declared value is named, and that the argparse carve-out sentence is present - a literal
     substring assertion in the style already used by
     `tests/test_skill_parity.py::test_no_bases_two_cause_claim`.
4. `tests/test_skill_drift.py` - tier 2, under `pytest.mark.conformance`, driven by an explicit
   registry. Each entry pairs a documented query with the property the skill teaches by it and
   carries the claim it evidences: the `find` worked example, the `ProgressColumn` inheritors
   count, the `RichHandler --bases` answer, and the `RichHandler.__init__` empty result.
   Assertions are on the taught property, never on a recorded block.
   - The registry also carries the unexecutable entries (`numba::njit`), and a test asserts each
     names why - so an example the gate cannot run is visible in the registry rather than absent
     from it.
5. `pyproject.toml` - add `rich` to the `dev` group. It is currently installed only as a transitive
   dependency of `fastmcp`, and the gate should not rest on another package's dependency tree. The
   conformance CI job already verifies its own specimens are installed; this is the same move one
   level down.
6. `src/venvaxi/SKILL.md` - the Workflow section states `inherits rich.progress::ProgressColumn`
   returns `count: 11`. It is the only non-zero prose count in the file, every other being
   `count: 0`. Replace the figure with the columns the example teaches by, then `just skill-sync`
   so all three copies stay byte-identical. This is the one skill edit the unit plans up front,
   and it is spec-driven rather than incidental.
7. Triage before fixing, if a check fires. A stale skill claim is corrected in
   `src/venvaxi/SKILL.md` followed by `just skill-sync`; a *code* defect surfaced through a
   documentation assertion is filed rather than papered over by relaxing the assertion.
8. **Re-entry delta (D3).** Widen the prose-count check to the form the spec's third limit
   states: match a `count: <non-zero>` span whose backticks wrap across a line, and an
   unbackticked one, over non-fenced lines. The 100-column wrap makes the split-span spelling a
   realistic edit, not a hypothetical one.
9. **Re-entry delta (D4).** Add the completeness guard the parsed surfaces already have: every
   `venvaxi ...` invocation the skill documents together with a result is either run by the gate
   or recorded as unexecutable with a reason. The registry is the one hand-written surface here,
   and it was the one with no anti-vacuity check.
10. Prove the gate can fail. Rename a real flag in `src/venvaxi/_cli.py`, confirm tier 1 goes red,
   revert. A gate never seen failing is the vacuous kind `ICM/process-plan/CONTEXT.md` warns about,
   so the stage 03 report carries the run and its output.
11. `CHANGELOG.md` - the gate under `Added`, the `build_parser()` extraction under `Changed`.

## Validation

- [x] Where the packaged skill's command table names a flag, the gate shall fail unless that flag
      is accepted by the command it is listed against.
      — `tests/test_skill_drift.py::test_documented_flag_is_accepted`, ten parameterisations,
      green; stage 03 control C1 (skill names `--deep` on `cache`) turns it RED.
- [x] Where the packaged skill's command table states a default for a flag, the gate shall fail
      unless that default is the command's own default.
      — `tests/test_skill_drift.py::test_documented_default_is_the_parser_default`, ten
      parameterisations, green; stage 03 control C2 (`--limit` stated as `50` on `find`, parser
      default `20`) turns it RED. `::test_commands_table_states_at_least_one_default` keeps the
      default parsing itself non-vacuous.
- [x] If a command accepts a non-global flag the packaged skill's command table does not name,
      then the gate shall fail.
      — `tests/test_skill_drift.py::test_every_non_global_flag_is_documented`, ten
      parameterisations, green; stage 03 control C3 (`--all` dropped from the `list` row) turns
      it RED. The global carve-out is the name list `-v`, `--verbose`, `--version`, `-h`,
      `--help`, not a heuristic.
- [x] Where the packaged skill names an MCP tool, the gate shall fail unless a tool is registered
      under that name with the parameters and defaults the skill states.
      — `tests/test_skill_drift.py::test_mcp_tool_names_match_the_registry` (set equality
      against `camel_case` over `venvaxi._mcp._TOOLS`) and `::test_mcp_tool_signature_matches`,
      eleven parameterisations, green; stage 03 controls C4 (`limit=10` stated for
      `showPackageApiTool`) and C9b (the `getBasesTool` row dropped) turn them RED. Scoped to the
      MCP tool table; a tool named in prose is the declared residue.
- [x] If the packaged skill names an exit code the output contract does not declare, or omits one
      it does declare, then the gate shall fail.
      — `tests/test_skill_drift.py::test_named_exit_codes_match_the_output_contract` asserts
      `{0, 1, 2}` both ways against `venvaxi._core.ExitCode`, with
      `::test_argparse_carve_out_is_still_stated` holding the carve-out sentence; stage 03
      control C5 (a fourth exit code named) turns it RED. Scoped to the exit-code paragraph; a
      code named elsewhere is the declared residue.
- [x] Where the packaged skill documents a query together with the result it returns, the gate
      shall run that query against the venv the project installs for itself and fail unless the
      property the example teaches holds of the result.
      — `tests/test_skill_drift.py::test_documented_query_teaches_what_it_claims` under
      `uv run pytest -m conformance` -> `29 passed, 609 deselected`; stage 03 control C6 (the
      `find Console.print` lead result falsified) turns it RED. Each query is parsed from the
      line the skill spells by `build_parser()` and dispatched through `args.func(CLIContext(...))`
      against real `rich` and `polars`.
- [x] If a documented query names a package the project does not install, then the gate shall
      report it as unexecutable rather than pass over it.
      — `tests/test_skill_drift.py::test_unexecutable_example_records_why`, in tier 1, green;
      stage 03 control C7 (an unexecutable entry loses its reason) turns it RED. `numba`
      confirmed absent by `importlib.util.find_spec("numba") is None`; `rich` and `polars`
      confirmed present.
- [x] If the packaged skill states a non-zero result count in prose, then the gate shall fail,
      whether or not that count is backticked and whether or not the span wraps across a line.
      — `tests/test_skill_drift.py::test_no_non_zero_result_count_in_prose`, re-reported
      against the amended tree: a span split across a line wrap and an unbackticked `count: 7`
      both turn it RED where both previously passed green, while a prose `count: 0` and a fenced
      non-zero count both stay GREEN, so neither scoping was lost in widening it.
- [x] If the packaged skill documents a query together with the result it returns and the gate
      neither runs it nor records it as unexecutable, then the gate shall fail.
      — `tests/test_skill_drift.py::test_every_documented_invocation_is_triaged`, with
      `::test_triage_lists_name_only_invocations_the_skill_makes` guarding the reverse; adding an
      untriaged documented query goes RED, deleting a `NOT_AN_EXAMPLE` reason goes RED, and
      pointing a registry entry at a query the skill does not make goes RED on both.
- [x] If the skill's command table or MCP tool table is parsed to fewer rows than there are
      registered commands and tools, then the gate shall fail rather than pass vacuously.
      — `tests/test_skill_drift.py::test_commands_table_covers_every_registered_subcommand`,
      `::test_mcp_tool_table_row_count_matches_the_registry` and
      `::test_mcp_tool_names_match_the_registry`, green; stage 03 controls C9a and C9b name the
      missing row, and C9c (the `## Commands` heading renamed, so the table parses to zero rows)
      errors at collection rather than passing vacuously.
- [x] When a flag is renamed in the CLI and the packaged skill is not updated, the gate shall fail.
      — stage 03 control C10: `--all` renamed to `--everything` at `src/venvaxi/_cli.py:750`,
      then `uv run pytest tests/test_skill_drift.py` -> `2 failed, 47 passed, 7 deselected`,
      failing `::test_documented_flag_is_accepted[list]` and
      `::test_every_non_global_flag_is_documented[list]` - both directions. Reverted, `git diff`
      empty, sha256 back to baseline.
- [x] When the CLI is invoked, it shall accept the same arguments and defaults, and render the same
      help text, as before the parser extraction.
      — stage 03 A/B against `git show HEAD:src/venvaxi/__main__.py`: ten `--help` captures
      (top level and all nine subcommands, stdout, stderr and exit status) `diff -r` identical,
      and 35 parser action rows identical, both builds reached by spying on
      `ArgumentParser.parse_args` so the pre-extraction parser is the real object.
- [x] The test suite and the conformance tier shall pass.
      — post-delta `uv run pytest` -> `609 passed, 29 deselected`; `uv run pytest -m conformance`
      -> `29 passed, 609 deselected`; `uv run -m prek run pkgdx-lint pkgdx-format pkgdx-typing
      pkgdx-markdown --all-files` -> all four Passed.

## Risks / unknowns

- **The gate may go red on landing, and that is it working.** #39's fourth comment predicted the
  worked example would fail for a code reason rather than a skill-edit reason. That prediction is
  discharged - the example reproduces - but a tier-1 check firing on a flag or a default is still
  live. The response is to fix the skill, never to weaken the assertion.
- **A documented result moves when a dependency moves.** Asserting the taught property rather than
  the recorded block is the mitigation. A `rich` release that reordered `find` results would still
  need a person to look, which is the correct outcome and not a false green.
- **`rich` is currently transitive.** Step 5 declares it. Until then the tier-2 premise is an
  accident of `fastmcp`'s dependency tree, and a `fastmcp` release dropping `rich` would turn the
  gate green by removing what it checks.
- **Table parsing is a surface with its own failure mode.** A parser silently matching zero rows
  passes every assertion vacuously, which is why the row-count criterion above is a criterion and
  not an implementation detail.
- **The prose-count rule rests on a boundary, not a blanket ban.** A fenced block reproducing
  real output keeps its recorded `count:`, and `count: 0` stays legal in prose as a declared empty
  state. A check written as "no `count: <int>` anywhere" would fire on eleven legitimate lines and
  on the flagship output block; stage 01 counted them, so the scoping is a requirement and not a
  refinement.
- **Tier 3 is not covered and must not read as if it were.** The narrowed Out of scope bullet is
  what stops the next reader assuming a stale prose line was checked. If that bullet is ever
  deleted rather than narrowed, the assumption returns.

## Notes

**Stage 01 re-entry, from the stage 03 gate.** Verification passed all twelve original criteria,
and two independent reviews - the drift auditor and the verification pass - converged on the same
defect in what stage 01 had *written* rather than in what stage 02 built. Recorded here per the
re-entry rule in `ICM/process-plan/CONTEXT.md`; only the delta was re-run.

Three divergences, every one in the same direction - the spec claimed wider coverage than the gate
delivers:

- **D1** - the Out of scope bullet stated the residue *lexically*, as "a claim naming no flag, no
  exit code, no MCP tool and no runnable query". That was wrong in both directions, and both were
  reproduced. It reached **more**: `` A `count: 7` result is normal. `` satisfies the criterion and
  the gate goes red on it. It reached **less**: the `getSymbolTool` prose the bullet cites as the
  residue's defining example names three MCP tools, so the criterion excluded it from the residue
  while the gate stayed blind to it. Amended to state the residue by *surface* - outside the
  command table, the MCP tool table, the exit-code contract statement and the documented queries -
  which is what the gate actually implements.
- **D2** - rules 3 and 4 read unscoped ("Where the packaged skill names an MCP tool / an exit
  code") while the checks are table-scoped and paragraph-scoped. An exit code named inside
  `## Commands` sits outside the exit-code window and passed green. Both rules scoped to match.
- **D3** - the third limit is form-agnostic but the check matched only a backticked, single-line
  span; a span split across a line wrap passed green. **The check widens rather than the spec
  narrowing** - the limit is the right rule, and the file wraps at 100 columns, so the split
  spelling is a realistic edit.

**D4**, separately, is a gap in the code rather than the spec: the worked-example registry is the
one hand-written surface in a gate where every parsed surface carries an anti-vacuity check, so a
future example added to the skill and omitted from the registry would pass silently - the
"green over four of five" the third limit forbids. A new clause and criterion cover it.

**Why the spec changed and not the gate, for D1 and D2.** The gate's scoping is deliberate and
argued: the plan's Out of scope rejected scraping prose, and #58 rejected a prose-matching test
for covering one sentence while implying coverage of twenty. Widening the gate to match the
over-claim would have rebuilt exactly what was rejected. Narrowing the claim is the honest move,
and it makes the residue larger and explicitly so.

**Why the gate introspects the parser rather than scraping `--help`.** `--help` is a *rendering*
of the parser, so a scraper asserts the rendering as much as the contract, and an argparse
formatting change - or a terminal width - turns a green gate red for a reason that is not drift.
`specs/README.md` Invariant 4 is satisfied by either source; the parser is the one that does not
break on presentation. That choice is the whole reason `build_parser()` exists: `main()` used to
build the parser inline, so there was no parser object to reach without running the CLI. The
extraction is behaviour-free by construction and proved so by the A/B on criterion 12, and it is
the only production change this unit makes.

**Why an explicit registry rather than scraping the fenced blocks.** A scraper over fenced output
would have exactly one assertion available to it - equality against the recorded block - and that
is the assertion the spec's first limit forbids, because a recorded `count:` is what one version
of a dependency returned. The property an example *teaches* - that the symbol the caller asked for
leads the results - is not written in the file, so it has to be written down somewhere, and a
registry entry is that somewhere. The price is that the registry is the one hand-written surface
in a gate whose every parsed surface carries an anti-vacuity check - which is precisely the gap
D4 closed: parser acceptance is now the concreteness filter, and every backticked invocation the
real parser accepts is triaged into run, recorded-unexecutable-with-a-reason, or recorded as
documenting no result.

**Why `rich` moved from transitive to declared.** Tier 2 rests on `rich` being importable. It was
present only as a `fastmcp` dependency, so a `fastmcp` release dropping it would have turned the
conformance tier green by deleting what it checks - green by absence, the same failure mode as a
table parser that matches zero rows. Declaring it in the `dev` group makes the premise ours. It is
declared unpinned and no installed version moved.

**The gate reads private argparse API, deliberately.** `tests/test_skill_drift.py` walks
`parser._actions` and matches `argparse._SubParsersAction` to reach the subparsers. Both are
private. The public alternative is the `--help` text this unit rejected above, so the dependence
is a consequence of that decision rather than an oversight. It pins the gate to CPython's argparse
internals; see Follow-ups.

**A line-oriented scan over a 100-column-wrapped document is a scoping bug, not a style choice.**
The prose-count check matched a backticked `count: <int>` span line by line, so a span whose
backticks wrapped across a line was invisible to it. Widening it (D3) meant collapsing the
non-fenced lines into one searchable string with an offset-to-line map, so failure messages still
name the source line via `bisect`. The defect had a second victim in the same file: once the
collapse landed, the D4 triage extraction found `venvaxi find StructNameSpace --package polars`
for the first time - its span wraps too. One scoping bug was hiding a stale count *and* a
documented query, which is the argument for widening the check rather than narrowing the rule.

**Scoping the prose-count rule is a requirement, not a refinement.** `src/venvaxi/SKILL.md`
carries 11 non-fenced `count: 0` spans and one fenced `count: 3` (the flagship `find` block). A
check written as "no `count: <int>` anywhere" fires on all twelve. The fence scoping and the
`count: 0` exemption were counted at stage 01 and re-counted at stage 03 against the file itself.

**Three smaller decisions worth keeping.** Anti-vacuity on the Commands table is *set* equality
rather than count equality, so a failure names which subcommand is missing or spurious.
`test_commands_table_states_at_least_one_default` exists because the default-capturing group is
optional, so a regex that stopped matching the documented-default spelling would leave the
stated-defaults test green over an empty mapping; it pins no figure, only that some default
parsed. And `test_unexecutable_example_records_why` sits in tier 1, not tier 2: the check that the
gate declares its own gaps must not hide behind the same opt-in flag as the thing it guards.

**Gotchas and costs.**

- `src/venvaxi/SKILL.md` is CRLF (337 line endings, 22,515 bytes) and parity is byte-exact. Any
  script that mutates and restores it must restore *bytes*; a stage 02 control script rewrote it
  LF-only and had to be repaired before `tests/test_skill_parity.py` meant anything again.
- Tier 2 is two orders of magnitude slower than tier 1 (about 3.9s against 0.12s): each example
  takes a cold `isolated_cache` and rebuilds the `rich` or `polars` graph. That is the trade
  `tests/test_conformance.py` already makes, and it is why tier 2 sits behind `-m conformance`.
- `tests/` is outside the `pkgdx-typing` hook's scope, so the new module is unchecked by mypy.
  Repo convention, not a change this unit made.
- The module adds 51 tier-1 and 8 tier-2 tests; the suite reads `609 passed, 29 deselected` by
  default and `29 passed, 609 deselected` under `-m conformance`.

## Follow-ups

Both issue-shaped items below are **drafted, not filed** - stage 04 does not open issues, and the
reviewer decides what gets a number.

- **Issue (drafted, not filed) - the gate's dependence on private argparse API.**
  `tests/test_skill_drift.py` reads `parser._actions` and `argparse._SubParsersAction` to reach
  the subparsers. The dependence is deliberate (see Notes) but unverified across interpreters:
  the project runs one. [#115](https://github.com/andyrids/venv-axi/issues/115) wants CI across
  Python 3.11-3.14, which is where a difference in argparse's internals would surface first - as
  a collection error or an empty subparser walk, not as a drift report. Worth putting the two
  attribute reads behind a single accessor with an explicit failure message before that matrix
  lands, so a future argparse change reads as "the gate cannot see the parser" rather than as
  "the skill is fine".
- **Issue (drafted, not filed) - a cheap check over one slice of the tier-3 residue.**
  `specs/behaviors/skill-content.md` now names the residue by surface: quoted error strings, a
  count of the read tools, the `--fields` value set, and an exit code named in a gotcha rather
  than in the contract statement all sit outside the four checked surfaces. #39's second comment
  proposed one narrow check for one slice of it - every quoted message fragment in `SKILL.md`
  appears somewhere in `src/venvaxi/**/*.py`. It was **explicitly declined for this unit**: it is
  the prose-matching shape #58 rejected for covering one sentence while implying coverage of
  twenty, and taking it on here would have widened the gate to match an over-claim the spec has
  since been narrowed to drop. It remains cheap and it remains real - the #62 instance is exactly
  a quoted error string going false - so it deserves its own issue, argued on its own terms,
  where the coverage it implies can be scoped honestly.
- **Issue [#40](https://github.com/andyrids/venv-axi/issues/40) - gating the eval suite.**
  Pre-existing and unmoved. `.claude/skills/venvaxi/evals/` is run by a person, never by CI; this
  unit's Out of scope says so and nothing here changes it. Recorded because a reader who has just
  seen the skill become machine-checked will reasonably ask whether the evals were too.
- **Deferred to** - None. No downstream plan absorbs work from this unit, so no plan was edited
  by this closeout.
- **Tracked as** - None. Nothing here waits on an external dependency.
