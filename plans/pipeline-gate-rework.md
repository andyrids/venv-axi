---
status: planned
depends: []
specs: []
issues: []
pr:
---

# Plan: Gate the create-feature pipeline on decisions, not on steps

## Scope

Rework the checkpoint structure of the `ICM/create-feature` pipeline: make gates conditional on
findings, merge the pair that review the same material twice, add an explicit re-entry rule for
late decisions, assign the one unowned artifact, and widen the checkpoint response protocol.

Touches the four stage `CONTEXT.md` files and the workspace control point. No `src/venvaxi/`
change, no spec change.

Findings come from the first end-to-end `/create-feature` run
([inspect-own-docstring](inspect-own-docstring.md)), whose closeout Notes record them. That plan
carried the criterion *"Any friction found in the pipeline itself is recorded in Notes at
closeout"* precisely so this could be written from evidence rather than from theory.

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

Evidence from the one real run: 9 nominal checkpoints. Checkpoint 5 had nothing to show.
Checkpoints 11 and 13 showed the same findings twice. Stage 04's final checkpoint was **skipped
outright** - the agent went from "update documentation" straight to commit and push. That last
point is the argument in miniature: under momentum a 9-gate pipeline sheds gates, and the ones it
sheds are not chosen by importance.

The `README.md` Friction Doctrine wants friction *in the right areas*. This is not a plan to
reduce friction; it is a plan to relocate it.

### (1) Conditional gates

Stage 03 steps 3 and 5 both gate on test outcomes. Fold them into one gate that fires only on a
finding:

```text
2. Run existing unit tests
3. CHECKPOINT - only if any test failed or needed fixing
4. Fix any broken existing unit tests (skip if none)
```

A gate on a green run teaches nothing. A gate on a red one is the most valuable in the pipeline.

### (2) Merge stage 03 checkpoints 11 and 13

Draft the report *before* the gate, so one checkpoint reviews a complete artifact rather than raw
findings followed by a writeup of the same findings:

```text
 9. Exercise the affected CLI commands live
10. Check conformance against every specs/** file the plan names
11. Draft the verification report
12. CHECKPOINT
```

Stage 03 goes from five checkpoints to two, three when tests break. Pipeline total: 9 -> 5.

### (3) Re-entry rule - the load-bearing change

Add to `ICM/create-feature/CONTEXT.md`, since it is cross-stage:

> **Re-entry.** A decision that changes observable behaviour returns to the earliest stage whose
> output it invalidates - normally 01, because the spec and the plan must change first. Re-run
> only the delta, and record the re-entry in the plan's Notes. A linear pass that quietly patches
> an earlier stage's output is how a spec and its implementation drift apart inside a single run.

Reference it from stage 04's step-3 checkpoint, which is where late decisions actually surface.

Without this the pipeline's central guarantee is false. On the one real run, stage 03 certified
spec conformance and stage 04 then changed behaviour across four spec files, source and tests.
Verification was redone informally - and "informally" is exactly what the pipeline exists to
prevent. Nothing in the record would have shown it.

### (4) Assign `evals.json`

No stage claims `.claude/skills/venvaxi/evals/evals.json`. It is behaviour-expectation, not
source. Add it to stage 03's Inputs with the reasoning stated: an eval encoding superseded
behaviour is a failing test.

It needed updating twice on the one real run. With (3) in place the second update becomes part of
a recorded re-entry rather than an untracked fixup.

### (5) Widen the checkpoint response protocol

The workspace Acceptance Criteria demand `"approved"` or `"continue"`. The most valuable response
on the one real run was neither - it was approval carrying three changes, one of which reopened
implementation. An agent following the criteria literally could treat that as plain approval and
drop the changes.

```text
- User review & acceptance MUST be explicit before continuation:
  - "approved" | "continue" - proceed as presented
  - approval carrying changes - apply them, and where they change observable
    behaviour, follow the re-entry rule
```

This closes the loop between the protocol and (3).

## Validation

- [ ] Stage 03 has two unconditional checkpoints; the test-failure gate is explicitly conditional
- [ ] The verification report is drafted before stage 03's final checkpoint, not after
- [ ] `ICM/create-feature/CONTEXT.md` carries the re-entry rule, and stage 04 references it
- [ ] Stage 03 Inputs name `evals.json` with the reason it belongs there
- [ ] Workspace Acceptance Criteria admit approval-carrying-changes as a distinct response
- [ ] Total nominal checkpoints across the four stages drop from 9 to 5
- [ ] A dry read-through of all five files finds no step numbering left stale by the reordering
- [ ] `uv run -m prek run --all-files` passes
- [ ] The next `/create-feature` run reports how many gates fired and how many were skipped by
  condition, so the rework can be judged against evidence rather than intent

## Risks / unknowns

- **A conditional gate is one the agent can skip by marking its own homework.** "Only if a test
  failed" delegates the stop/continue decision to the party with momentum. Mitigation: the
  condition must be discharged with evidence in the visible response ("201 passed, 0 failed - no
  gate"), so a skip is always announced and can be objected to. An unannounced skip is the
  failure mode to watch for, and it is strictly worse than the vacuous gate it replaces.
- **Fewer gates cut against the Friction Doctrine.** The counter-argument is that this run
  demonstrated the doctrine failing in the other direction: a gate was silently skipped. Five
  gates that fire reliably beat nine that do not. Worth revisiting after two or three more runs
  rather than treating as settled.
- **The re-entry rule could cause thrash.** Applied literally to a trivial wording change it
  would send the pipeline back to 01 for nothing. The trigger is deliberately "changes observable
  behaviour", matching the bar `specs/README.md` already uses for what a spec covers - but that
  bar is a judgement call and will need at least one real case to calibrate.
- **The pipeline itself is unspecified.** `specs/` governs the product; nothing governs the
  process, so this plan has `specs: []` and no conformance check can be run against its result.
  Making the stage files a spec would be circular - they are the instructions, not a description
  of desired state. Left open; flagged because the invariant in `specs/README.md` quietly assumes
  every plan implements a spec, and this one does not.
- **n = 1.** Every finding here comes from a single run of a single bug fix, which was
  documentation-heavy and touched two source files. A feature-shaped run with real architectural
  choices might stress entirely different seams.

## Notes

Populated at closeout.

## Follow-ups

Populated at closeout.
