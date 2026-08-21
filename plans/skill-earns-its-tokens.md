---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/skill-content.md
authors:
  - specs/commands/setup.md
issues: [51, 52, 53]
pr: 58
---

# Plan: The skill earns its tokens

## Scope

Three issues from the `0.3.0rc1` agent evaluation all edit `src/venvaxi/SKILL.md`, and none of
them can say what makes a skill edit right. [#52](https://github.com/andyrids/venv-axi/issues/52)
adds four gotchas from observed failures and corrects an exit-code claim that contradicts
`specs/behaviors/output-contract.md`; [#53](https://github.com/andyrids/venv-axi/issues/53) cuts a
paragraph that influenced no decision across 10 agents;
[#51](https://github.com/andyrids/venv-axi/issues/51) widens the `description`, which since
[`plans/ambient-collapse-to-skill.md`](ambient-collapse-to-skill.md) is the only thing deciding
whether the AXI is used at all. As a batch they are three taste calls on one token budget.

Nothing governs the skill's content. That is how a contradiction of the output contract shipped
with no gate objecting, and why #53 has to argue a paragraph out on its merits rather than against
a bar. Declare the bar first, then make all three edits under it.

Out of scope: `inherits` gaining a bases-of-X query, owned by
[#48](https://github.com/andyrids/venv-axi/issues/48) - only the skill-side gotcha and the worked
example are in scope here; `getSymbolTool`'s missing module fallback, owned by
[#47](https://github.com/andyrids/venv-axi/issues/47), likewise skill-side only; running the eval
suite ([#40](https://github.com/andyrids/venv-axi/issues/40)) and detecting skill/code drift
([#39](https://github.com/andyrids/venv-axi/issues/39)), both declared Out of scope in the new
spec.

## Implements

`specs/behaviors/skill-content.md`, written by this plan, in full - the packaged skill is derived
material that may assert nothing `specs/**` does not declare, must cover the alternatives an agent
reaches for and the failure modes it hits, and carries a `description` naming situations by what
the caller is doing. The same plan writes the spec and brings the shipped artifact into
conformance with it, which `plans/README.md` resolves in favour of `specs:`.

Also `specs/commands/setup.md` Actions item 4, in `authors:` - one cross-reference sentence
scoping that item to installation and pointing at the new spec for content. No behaviour moves, so
nothing is verified against it.

## Approach

1. Flip to `status: in-progress`.
2. Write `specs/behaviors/skill-content.md` and add the cross-reference to
   `specs/commands/setup.md` Actions item 4; run the ripple check in `specs/README.md`.
3. Audit the existing skill against the new bar before adding anything, and record what survives.
   A principle asserted and not applied in the commit that declares it is worth less than no
   principle.
4. Issue #53 - reduce the token-savings gotcha to its one actionable implication, dropping the
   percentage figures.
5. Issue #52 - correct the exit-code paragraph to the three-way contract; add gotchas for `inherits`
   direction, unindexed dunders, empty namespace accessors and decorator passthroughs; state the
   hard boundary the decorator case exposes; add the `getSymbolTool` line under MCP differences;
   flip the `inherits` worked example to the child-to-parent case.
6. Issue #51 - widen the `description` to name debugging framings, and add the case against executing
   the dependency to the Overview.
7. Add eval case 10, the debugging-framing scenario, to
   `.claude/skills/venvaxi/evals/evals.json`.
8. Regenerate `.claude/skills/venvaxi/SKILL.md` via `just skill-sync`. The repo copy is generated
   output and is never hand-edited.
9. `CHANGELOG.md` under `Changed`.

## Validation

- [x] The packaged skill shall describe the exit-code contract as three outcomes, naming exit `2`
      as a venvaxi fault distinct from a reported `Error` at exit `1`.
      — `src/venvaxi/SKILL.md:141-146`, with all three outcomes reproduced live (`venvaxi list`
      exit `0`; `venvaxi show nosuchpkg-xyz` exit `1` with a TOON error block; `venvaxi
      --nonsense` exit `2` with 0 bytes on stdout), and the venvaxi-fault shape evidenced by
      `tests/test_stdout_encoding.py::test_unexpected_error_survives_non_cp1252_message`
- [x] The packaged skill shall name where the measured token-efficiency figures live rather than
      reproduce them, retaining only the implication that savings scale with row count and
      collapse on single-object output.
      — `src/venvaxi/SKILL.md:255-257`, with a grep for `~45%`, `~27%`, `~6%` and `~40%`
      returning 0 matches across the file
- [x] The packaged skill shall state why the AXI is preferred to executing the dependency, not
      only to recalling it from memory.
      — `src/venvaxi/SKILL.md:29-33`
- [x] The packaged skill shall carry an entry for each of the four observed failure modes:
      `inherits` answering only child-of, unindexed dunders, empty namespace accessors, and
      decorators introspecting as passthroughs.
      — `src/venvaxi/SKILL.md:202`, `:206`, `:215`, `:220`, with all four underlying claims
      reproduced live - the last two in a throwaway venv carrying `polars` 1.43.2 and
      `numba` 0.67.0
- [x] The packaged skill shall state that the compiler and runtime semantics of a decorated
      function are reachable by no `venvaxi` command.
      — `src/venvaxi/SKILL.md:225`, with the negative spot-checked: `inspect numba::jit
      --docstring` contains no occurrence of 'parallel', and `inspect numba::prange` returns
      `signature: (*args)`
- [x] The packaged skill's `inherits` worked example shall demonstrate the child-to-parent case
      rather than the query returning an ambiguous zero.
      — `src/venvaxi/SKILL.md:101`, with `inherits rich.progress::ProgressColumn` returning
      `count: 11` against the superseded example's `count: 0`; see the wording note below
- [x] The skill `description` shall name a debugging framing - observed misbehaviour whose cause
      is a signature fact - alongside the authoring and review framings.
      — `src/venvaxi/SKILL.md:7-9`, 696 characters total, and the harness re-served the skill
      listing with the new description after `just skill-sync`
- [x] The eval suite shall contain 10 cases with unique ids, including one whose prompt is framed
      as a bug report and never names `venvaxi`.
      — `.claude/skills/venvaxi/evals/evals.json` parsed programmatically: 10 cases, ids `[1..10]`
      unique, case 10 `debugging-framing-fires-unprompted` with `'venvaxi' in prompt.lower()`
      returning `False`
- [x] `.claude/skills/venvaxi/SKILL.md` shall be byte-identical to `src/venvaxi/SKILL.md`.
      — `tests/test_skill_parity.py`, 3 passed, and `cmp` reporting no difference

## Risks / unknowns

- **Eight of the nine criteria cannot be observed failing.** They assert that a document says
  something, so they are satisfied by the act of writing it and verified by reading it back.
  `reference-standard-validation.md` warns that a ubiquitous criterion is often vacuous, and this
  is that case: the checklist proves the edit was made, not that it works. Only the parity
  criterion has a test behind it. This is the honest shape for prose work - `skill-parity-and-evals`
  set the same precedent - but the ticks must not be read as nine proofs, and the limitation
  belongs in Notes at closeout.
- **#51 is the one change whose effect is unmeasurable here.** Whether the widened description
  actually fires on a debugging framing can only be answered by running the eval suite, and #40
  records that nothing does. The issue's own evidence is a self-assessed counterfactual from an
  agent that had already read the instruction to use venvaxi - suggestive, not conclusive. A
  single subagent trial at stage 03 would be one non-blind data point and cannot be a criterion;
  worth taking if it can be staged cheaply, worth discarding if it cannot.
- **No test is added, deliberately.** A test asserting the skill mentions exit `2` would cover one
  sentence while implying coverage of the other twenty, which is the shape of check this project
  has already built and defeated once. #39 owns drift detection and defers it on purpose.
- The skill grows on net despite #53's cut. The audit in Approach step 3 is what keeps that
  honest; if it finds nothing to remove, that is a finding to record rather than a step to skip.
- #52 and #51 both touch the `inherits` material, and eval case 6 asserts the interpretation of
  `count: 0` from the very query the worked example is being flipped away from. The case stays
  valid - it is about reading the zero, not about the example - but it must be re-read after the
  edit rather than assumed unaffected.

## Notes

**The exit-code paragraph has now been wrong three times, the same way each time.** The original
claimed errors exit `1` and omitted exit `2`, which is what #52 was filed for. The first draft of
the fix claimed a 'three-way contract' and omitted argparse, which also exits `2` on an unknown
flag or a missing positional - so it would have told an agent to file a bug about its own typo.
The CHANGELOG entry then shipped the same 'three-way contract' phrase and survived the commit that
removed it from the skill, and was corrected at closeout. The recurring error is **how many
outcomes there are**, not which ones, and it has now escaped three separate reviews in three
separate documents. `specs/behaviors/output-contract.md` states the carve-out directly under its
exit-code table; the next exit-code edit should start there rather than from the previous wording.

**The shipped text discriminates on what is observable, which is why it is durable.** Exit `2`
with no TOON on stdout is an argparse rejection - retype. Exit `2` with an `Unexpected error:`
block on stdout is a venvaxi fault - file a bug. Counting outcomes invites the omission; naming
the observable difference does not. The first Validation criterion still holds as written because
the spec itself scopes its contract to venvaxi's own outcomes.

**Eight of nine ticks are not eight proofs.** They record that a document says something, which
writing it guarantees. What carries weight is that stage 03 reproduced the factual claims behind
them rather than re-reading the edits - the exit codes, both `inherits` counts, the accessor
shape, the decorator signatures, and the boundary as a negative. A skill entry can be present and
wrong; this run hit exactly that failure once already.

**The two claims stage 02 could not verify were verified at stage 03.** A throwaway `uv` project
on Python 3.12 with `polars` 1.43.2, `numba` 0.67.0 and this branch's wheel reproduced both
exactly, and was deleted; the repository was untouched. `Series.struct` inspects as
`kind: attribute` with an empty signature; `njit` and its fully qualified spelling both report
`(*args, **kws)`. The `njit` docstring pointer is stronger than the skill implies - it names
`jit()` as the preferred API in its first line.

**The accessor gotcha's fallback works, but is fragile.** Stage 02 kept the entry as written on
the argument that searching the accessor's own name surfaces the implementing class. It does:
`find struct --package polars` returns `StructNameSpace` at rank 17 of the default limit 20. At
`--limit 12` it falls off entirely, and the same query returns three namespace classes, so
choosing among them still requires knowing the receiver is a `Series` rather than an `Expr`. An
earlier probe at `--limit 12` appeared to refute the claim and did not - it truncated the answer.

**No trigger trial was staged for the widened `description`, deliberately.** The skill is already
loaded in the authoring session's own listing, so any subagent's context is contaminated by
construction. A single non-blind shot would have produced a number too weak to report and too
tempting to cite. Recorded as not done rather than done badly. Eval case 10 is the specimen; #40
owns running it.

**This is the project's first `specs:` conformance claim against prose rather than code.** It
worked, and the reason it worked is that the new spec's clauses make factual claims that can be
reproduced, not merely read - the exit-code contract, the failure modes, the correct move each
gotcha names. A spec that only asserted tone or length would have produced a vacuous conformance
check. Worth remembering if a second document-governing spec is ever written.

**Where the principle went, and why not `specs/principles.md`.** The stage 01 gate proposed the
earns-its-place rule as a project-wide principle. `ICM/_config/reference-standard-spec.md` sends it
elsewhere: promotion is triggered by the same principle appearing in a *second* spec, and it
appears in one. So it is a **Local** principle on `specs/behaviors/skill-content.md` - which had
to be created, since the artifact it governs had no spec at all. That absence is the root cause of
all three issues. Promotion stays available if the same bar later shows up governing `help[]`
footers or error text.

**The `metadata.version` bump was defended better at stage 02 than it was specified.** The
techspec argued consumers should see the version move. The stronger argument, which is the one on
the record: the field already exists, so a version that does not move while the content does is a
false claim two installed copies would repeat. Removing the field entirely is the YAGNI-pure
alternative and is a different decision no issue asked for.

**The step 3 audit found exactly one entry failing the new bar.** Everything else survives with a
named action it changes - the qualified-name form, cold-cache `--package`, definitive `count: 0`,
docstring truncation, `doc: (no docstring)`, when to `--refresh`, `tree` depth, MCP-needs-the-extra,
`setup`-is-not-a-diagnostic, and the `AGENTS.md` legacy Pointer. Only the token-savings percentages
failed, and they are what edit G cut. Net growth is about 35 lines, all of it traceable to an
observed failure.

**Criterion 6's wording says 'child-to-parent' where the shipped example is parent-to-children.**
The latter is the direction `inherits` actually supports; the criterion inherited #52's phrasing of
the complaint rather than describing the fix. The substance passes and the box is ticked.
`reference-standard-validation.md` makes the box text the identifier stage 03 quotes verbatim, so
it was not reworded at closeout - recorded here instead.

**One item was reconciled at closeout.** The Commands table's `setup` row listed only `--no-skill`
while `--help` renders `[--skill | --no-skill]`. `plans/setup-skill-by-default.md` handed this
to #52 at closeout and this is the plan implementing it, but it was dropped at stage 01 - present in
neither the techspec nor the checklist. Fixed under `plans/README.md` step 6: a one-token prose
change inside the file this plan already owns, changing no declared behaviour. Every other row was
checked against its `--help` and is accurate.

## Follow-ups

- **Issue [#52](https://github.com/andyrids/venv-axi/issues/52)** - fully discharged by this plan,
  including the Commands table row inherited from `plans/setup-skill-by-default.md`. Two entries in
  the packaged skill remain candidates for a later tightening, neither urgent and neither owned:
  the `setup` is-not-a-diagnostic gotcha is the longest in the file at 12 lines and repeats its own
  point, and the namespace-accessor gotcha states a recovery move that presupposes the implementing
  class's name when the transferable move is to search by naming convention - the rank-17-of-20
  evidence above is the argument for restating it.
- **Issue [#39](https://github.com/andyrids/venv-axi/issues/39)** - now carries more weight than it
  did. `specs/behaviors/skill-content.md` declares nine clauses that nothing automatically checks,
  and its own Out of scope says so plainly: 'until it lands every rule above is a rule a human
  checks'. The exit-code error escaping three reviews in this single run is the case for that issue
  rather than an argument against the spec.
- **Issue [#40](https://github.com/andyrids/venv-axi/issues/40)** - the eval suite is now 10 cases
  and still runs nowhere. Case 10 is the only instrument that would measure whether the widened
  `description` fires, so this issue is what makes the #51 half of this plan verifiable at all.
- **Issue [#47](https://github.com/andyrids/venv-axi/issues/47)** - `getSymbolTool`'s missing module
  fallback. The skill now documents the workaround under MCP differences; the fix is untouched.
- **Issue [#48](https://github.com/andyrids/venv-axi/issues/48)** - a bases-of-X query for
  `inherits`. The skill now documents the direction limit and the guess-the-base workaround; the
  feature is untouched.
- **None deferred** - no `Deferred to` entries, so no downstream plan required absorption in the
  closeout commit.
