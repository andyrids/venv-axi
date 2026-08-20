---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/skill-content.md
authors:
  - specs/commands/setup.md
issues: [51, 52, 53]
pr:
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

- [ ] The packaged skill shall describe the exit-code contract as three outcomes, naming exit `2`
      as a venvaxi fault distinct from a reported `Error` at exit `1`.
- [ ] The packaged skill shall name where the measured token-efficiency figures live rather than
      reproduce them, retaining only the implication that savings scale with row count and
      collapse on single-object output.
- [ ] The packaged skill shall state why the AXI is preferred to executing the dependency, not
      only to recalling it from memory.
- [ ] The packaged skill shall carry an entry for each of the four observed failure modes:
      `inherits` answering only child-of, unindexed dunders, empty namespace accessors, and
      decorators introspecting as passthroughs.
- [ ] The packaged skill shall state that the compiler and runtime semantics of a decorated
      function are reachable by no `venvaxi` command.
- [ ] The packaged skill's `inherits` worked example shall demonstrate the child-to-parent case
      rather than the query returning an ambiguous zero.
- [ ] The skill `description` shall name a debugging framing - observed misbehaviour whose cause
      is a signature fact - alongside the authoring and review framings.
- [ ] The eval suite shall contain 10 cases with unique ids, including one whose prompt is framed
      as a bug report and never names `venvaxi`.
- [ ] `.claude/skills/venvaxi/SKILL.md` shall be byte-identical to `src/venvaxi/SKILL.md`.

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

## Follow-ups
