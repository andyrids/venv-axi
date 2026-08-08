---
status: planned
depends: [mcp-hint-parity]
specs: []
issues: []
pr:
---

# Plan: Gate the create-feature pipeline on decisions, not on steps

## Scope

Rework the checkpoint structure of the `ICM/create-feature` pipeline: make gates conditional on
findings, add an explicit re-entry rule for late decisions, assign the one unowned artifact, and
widen the checkpoint response protocol.

Touches the four stage `CONTEXT.md` files and the workspace control point. No `src/venvaxi/`
change, no spec change.

**Revised after the second end-to-end run.** The first draft was written from one run
([inspect-own-docstring](inspect-own-docstring.md)). The second
([mcp-hint-parity](mcp-hint-parity.md)) confirmed three of the five proposed changes,
**contradicted one**, and produced no evidence either way on the fifth. The contradicted change
has been withdrawn and replaced; the headline gate reduction is smaller than first claimed. Both
plans carried a criterion requiring pipeline friction to be recorded at closeout, so this is
written from evidence rather than from theory.

`depends: [mcp-hint-parity]` is about the *record*, not about code: this revision cites that
plan's closeout Notes, which land with its PR. Merge that first or the citations point at an
unfinished plan.

## Implements

**No `specs/**` file** - hence `specs: []`. The pipeline is process, and `specs/` covers the
product. The stage `CONTEXT.md` files are the closest thing the pipeline has to a specification,
and this plan edits them directly.

Whether the pipeline *should* carry a spec is a real question, deliberately not answered here -
see Risks.

## Approach

### Diagnosis

The pipeline gates on **step completion**, not on **decisions**. A checkpoint exists so a human
can redirect; when there is nothing to redirect it is ceremony, and ceremony trains reflexive
approval. Vacuous gates devalue the gates that matter.

The diagnosis survives the second run. What changed is which gates are vacuous: fewer than the
first draft assumed, and not always the same ones.

### Evidence across both runs

| Gate                       | Run 1 (docstring fix) | Run 2 (hint fix)         |
| -------------------------- | --------------------- | ------------------------ |
| 03 step 3 - tests run       | vacuous               | vacuous, waived aloud    |
| 03 step 5 - tests fixed     | vacuous               | vacuous, waived aloud    |
| 03 step 8 - prek            | fired, real content   | fired, real content      |
| 03 step 11 - conformance    | duplicated 13         | **two live decisions**   |
| 03 step 13 - report         | duplicated 11         | **new qualifications**   |
| 04 step 8 - closeout        | **skipped silently**  | fired                    |

The two runs agree on the test gates and on prek. They **disagree on 11 and 13**, which is what
forces change 2 below to be withdrawn.

### (1) Conditional test gate - confirmed by both runs

Stage 03 steps 3 and 5 both gate on test outcomes. Fold them into one gate that fires only on a
finding:

```text
2. Run existing unit tests
3. CHECKPOINT - only if any test failed or needed fixing
4. Fix any broken existing unit tests (skip if none)
```

A gate on a green run teaches nothing. A gate on a red one is the most valuable in the pipeline.

Run 2 executed this by hand: the gate was waived on stated evidence ("216 passed, 0 failed, so
step 4 is a no-op"), announced, and approved. The waiver cost one line and produced no confusion,
which is the practical case for writing it into the stage file.

### (2) ~~Merge stage 03 checkpoints 11 and 13~~ - **withdrawn**

The first draft proposed drafting the verification report *before* the gate, so one checkpoint
reviewed a complete artifact instead of two reviewing the same findings. Run 2 contradicts this.

On run 2, checkpoint 11 produced **two decisions that changed the work**: widen the plan's scope
to a fourth defect (re-entering stage 01, changing source and adding a test), and file a spec
divergence as an issue rather than fixing it in scope. Had the report been drafted before that
gate, it would have described work that then changed - the merge would have been actively
harmful, not merely neutral.

Checkpoint 13 was also not redundant: it carried qualifications 11 had not surfaced, because they
only became visible while writing the report - that defect 2 corrects an apparently unreachable
branch, and that one criterion was discharged by reading rather than by execution.

**Replacement.** Keep both, and make 13 conditional on 11 having produced changes:

```text
 9. Exercise the affected CLI commands live
10. Check conformance against every specs/** file the plan names
11. CHECKPOINT - conformance findings and the decisions they force
12. Draft the verification report
13. CHECKPOINT - only if 11 produced changes, or the report surfaces
    something 11 did not
```

This keeps the plan's own principle intact - 11 gates *decisions*, which is exactly what it
should do - while removing the ceremony run 1 saw, where 11 produced nothing and 13 restated it.
The escape clause in 13 is deliberate: on run 2 the report itself surfaced new material, and a
condition that only checked "did 11 change anything" would have suppressed a gate that mattered.

### (3) Re-entry rule - the load-bearing change, confirmed twice

Add to `ICM/create-feature/CONTEXT.md`, since it is cross-stage:

> **Re-entry.** A decision that changes observable behaviour returns to the earliest stage whose
> output it invalidates - normally 01, because the spec and the plan must change first. Re-run
> only the delta, and record the re-entry in the plan's Notes. A linear pass that quietly patches
> an earlier stage's output is how a spec and its implementation drift apart inside a single run.

Reference it from stage 04's step-3 checkpoint and from stage 03's step-11 checkpoint - run 2
shows late decisions surface at both.

Run 1 is the negative case: stage 03 certified spec conformance, then stage 04 changed behaviour
across four spec files, source and tests. Verification was redone informally, and nothing in the
record would have shown it.

Run 2 is the positive case: a fourth defect arrived at stage 03 step 10, after Scope had been
fixed at three. The run returned to 01, widened Scope and Validation, then re-ran the 02 and 03
deltas from scratch rather than patching. The plan's Notes record it.

Two qualifications, so this does not read as settled:

- Run 2 followed the rule **because run 1's plan named it**, not because anything enforced it.
  That is the argument for writing it into the stage files, but it also means the rule has never
  been tested against an agent with no prior exposure to it.
- The re-entry was cheap - one token and one test. A re-entry invalidating an architectural
  decision would cost far more, and neither run says whether the rule survives that.

### (4) Assign `evals.json` - no new evidence

No stage claims `.claude/skills/venvaxi/evals/evals.json`. It is behaviour-expectation, not
source. Add it to stage 03's Inputs with the reasoning stated: an eval encoding superseded
behaviour is a failing test.

Run 1 needed it updated twice. **Run 2 did not touch it at all** - checked, and no eval asserts
hint text - so this change still rests on a single run. Retained because the reasoning is sound
independent of frequency, but flagged as the weakest-evidenced of the five.

### (5) Widen the checkpoint response protocol - confirmed, strongly

The workspace Acceptance Criteria demand `"approved"` or `"continue"`. On run 1 the most valuable
response was neither. On run 2, **three** of the checkpoints resolved by a response the protocol
has no name for: approve-and-amend-the-spec, approve-and-widen-scope (which reopened
implementation), and approve-and-file-an-issue-instead.

An agent following the criteria literally could treat any of those as plain approval and drop the
instruction.

```text
- User review & acceptance MUST be explicit before continuation:
  - "approved" | "continue" - proceed as presented
  - approval carrying changes - apply them, and where they change observable
    behaviour, follow the re-entry rule
```

This closes the loop between the protocol and (3).

### Deliberately unchanged: the stage 03 prek gate

Both runs fired it with real content, and run 2 makes the case sharply: **all 16 unit tests
passed while an ISC004 lint error sat in the code.** Only the prek run caught it.

Making it conditional would gain nothing - the condition has been true both times - while adding
one more gate an agent under momentum could mark as its own homework. It stays unconditional, and
it stays a separate step from the test gate, because the two catch different classes of defect.

Recorded here because "reduce the gate count" is the kind of goal that quietly eats a gate that
was working.

### Gate count

The first draft claimed 9 nominal to 5. With change 2 withdrawn, the honest figure is:

```text
9 nominal  ->  6 unconditional + 2 conditional
```

| Stage | Before | After                              |
| ----- | ------ | ---------------------------------- |
| 01    | 1      | 1                                  |
| 02    | 1      | 1                                  |
| 03    | 5      | 2 unconditional + 2 conditional    |
| 04    | 2      | 2                                  |

On a run with no test failures and no conformance findings, six gates fire. On run 2's shape,
seven would have. The reduction is real but modest, and smaller than the first draft advertised.

## Validation

- [ ] Stage 03's test gate is explicitly conditional, and the stage file requires the condition to
  be discharged with evidence in the visible response
- [ ] Stage 03 keeps checkpoints at both conformance (11) and report (13), with 13 conditional
  and carrying the escape clause for material the report itself surfaces
- [ ] The stage 03 prek gate is unchanged and still a separate step from the test gate
- [ ] `ICM/create-feature/CONTEXT.md` carries the re-entry rule, and both stage 03 step 11 and
  stage 04 step 3 reference it
- [ ] Stage 03 Inputs name `evals.json` with the reason it belongs there
- [ ] Workspace Acceptance Criteria admit approval-carrying-changes as a distinct response
- [ ] Nominal checkpoints across the four stages drop from 9 to 8, of which 6 are unconditional
- [ ] A dry read-through of all five files finds no step numbering left stale by the reordering
- [ ] `uv run -m prek run --all-files` passes
- [ ] The next `/create-feature` run reports how many gates fired, how many were skipped by
  condition, and whether any conditional skip went unannounced

## Risks / unknowns

- **A conditional gate is one the agent can skip by marking its own homework.** "Only if a test
  failed" delegates the stop/continue decision to the party with momentum. Mitigation: the
  condition must be discharged with evidence in the visible response ("216 passed, 0 failed - no
  gate"), so a skip is always announced and can be objected to. Run 2 did exactly this by hand
  and it worked, but run 2's agent had read the plan proposing it - which is the weakest possible
  test of whether the written rule is self-enforcing.
- **Fewer gates cut against the Friction Doctrine.** The counter-argument is that run 1
  demonstrated the doctrine failing in the other direction: a gate was silently skipped. Run 2
  skipped none. One run of clean behaviour is not evidence the problem is gone.
- **The re-entry rule could cause thrash.** Applied literally to a trivial wording change it
  would send the pipeline back to 01 for nothing. The trigger is deliberately "changes observable
  behaviour", matching the bar `specs/README.md` already uses. Run 2 exercised it once, on a
  change small enough that the rule was cheap either way, so the bar remains uncalibrated at the
  expensive end.
- **The pipeline itself is unspecified.** `specs/` governs the product; nothing governs the
  process, so this plan has `specs: []` and no conformance check can be run against its result.
  Making the stage files a spec would be circular - they are the instructions, not a description
  of desired state. Left open; flagged because the invariant in `specs/README.md` quietly assumes
  every plan implements a spec, and this one does not.
- **n = 2, and both runs were small.** A documentation-heavy docstring fix touching two source
  files, and a four-string fix touching one. Neither was feature-shaped, neither involved a real
  architectural choice, and both were driven by the same agent within days. The disagreement
  between them on checkpoints 11 and 13 is the most useful thing the second run produced - it
  shows the sample is not yet large enough to generalise from, and that a third run of a
  different shape could well contradict something here too.
- **Revising a plan against the run that tested it risks fitting to the sample.** Change 2 was
  withdrawn on one contradicting run. That is the right call when the contradiction is a
  mechanism rather than a coincidence - here, 11 gates decisions and decisions are not always
  present - but the general form of "revise after every run" converges on the last run rather
  than on the truth.

## Notes

Populated at closeout.

## Follow-ups

Populated at closeout.
