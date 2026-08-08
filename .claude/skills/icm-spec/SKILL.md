---
name: icm-spec
description: >-
  This skill should be used before writing code that changes observable behaviour, whenever a
  spec needs authoring or amending, a plan needs opening or closing out, or a question of the
  form "what should X do when Y?" comes up and the answer is not already written down. Also use
  when a decision gets resolved mid-task that would change how a future implementer decides
  something - a trade-off settled in conversation, a "will always|will never" sentiment, or
  the same principle appearing in a second spec.
metadata:
  version: "0.1.0"
---

# Writing specs and plans

## Overview

This project is spec-driven. `specs/` declares what MUST be true and is permanent; `plans/`
records the work bringing code into conformance and freezes at closeout; ICM stage `output/` is
ephemeral scratch.

You SHOULD read the relevant `specs/**` file before writing code that changes observable
behaviour - it has already made the micro-decisions you are about to guess at.

You MUST NOT use this skill to run the feature pipeline. It teaches how to write a spec or a
plan; `ICM/create-feature/CONTEXT.md` owns the stages, the checkpoints and the acceptance
criteria. Reach for `/create-feature` to execute; reach for this skill to decide what the
artifacts should say.

## The split

| Layer    | Answers                       | Location            | Lifetime                     |
| -------- | ----------------------------- | ------------------- | ---------------------------- |
| Spec     | What MUST be true, forever    | `specs/**`          | Permanent, changed by review |
| Plan     | What we are doing about it    | `plans/<slug>.md`   | Frozen at `status: done`     |
| Techspec | How, at implementation detail | ICM stage `output/` | Ephemeral scratch            |

Confusing spec with plan is the failure this exists to prevent. 'Add a `--json` flag to `find`'
is motion - a plan. '`find` emits a `symbols` table ranked by facade path length' is state - a
spec.

## Workflow

### (1) Read the current state

Find the spec the request touches. The request is a proposal to change it, not a blank sheet.

```text
specs/commands/    <- one per CLI verb
specs/behaviors/   <- cross-cutting invariants
specs/mcp/         <- MCP tool contracts
specs/principles.md
```

If no spec covers it, that is itself the finding: the behaviour is currently unspecified.

### (2) Pick the mode before drafting

- **One bounded feature**, settled area - draft the spec change and its plan in tandem, present
  both.
- **A batch of specs** being mapped out - finish the batch first, *then* propose a set of plans.
  The good partition rarely maps one-to-one onto spec files, and a plan-per-spec churns while
  desired state is still moving.
- **Unclear** - ask. Do not default.

### (3) Write the spec

Templates and the decisive-principle bar are in `ICM/_config/reference-standard-spec.md`. The
test for any rule: could two implementers read it and disagree about whether the code conforms?

### (4) Write the plan

Frontmatter (`status`, `depends`, `specs`, `issues`, `pr`) and the fixed body order are in
`plans/README.md`. The Validation checklist is load-bearing - it converts `in-progress` to
`done`, and its checkbox text is what 03-verification reports against.

### (5) Close out

Last commit before merge: flip `status`, tick only what was verified, populate Notes and
Follow-ups, absorb deferrals in the same commit, reconcile `specs/` against what was actually
built.

## Gotchas

- **A spec that names a function or a file path is not a spec.** It is implementation detail that
  will rot on the first refactor. Specs describe behaviour observable from outside
  `src/venvaxi/`.
- **`venvaxi <cmd> --help` outranks any command spec.** If they disagree, the spec is the thing
  that is wrong. Fix it rather than 'correcting' the CLI to match prose.
- **Your built-in plan mode is not `plans/`.** An ephemeral plan evaporates when the turn ends.
  The classic trap is drafting 'write spec X, then build it', doing exactly that, and leaving
  neither a reviewed spec nor a plan file - split it into the two real artifacts.
- **'Too small for a plan' is how the record hollows out.** A bounded change still gets a file
  that freezes to `done`. The frozen plan plus its merged PR *is* the project's memory of what
  got built; skipping it trades seconds now for an unexplained change later.
- **Spec/code divergence is a bug, not debt.** Fix the code, or amend the spec. Never work around
  a spec in code - that leaves two contradictory sources of truth and no signal about which won.
- **A spec change ripples.** After editing a spec, find the plans chasing it:
  `grep -l '<spec-path>' plans/*.md`. Revise a `planned` plan; flag - do not silently rewrite -
  an `in-progress` one whose target just moved.
- **Duplication across specs is a promotion signal, not a style nit.** The same principle in a
  second spec means it has outgrown both. Lift it to `specs/principles.md` once and replace both
  copies with references, before they drift apart. Watch for *similar*, not just identical.
- **Principles get resolved mid-task, not at kickoff.** Most of a project's durable judgement is
  settled while doing something else, and it is unspecified behaviour the moment the context
  window closes. Surface it when it happens.

## Pointers

- `specs/README.md` - tree layout, the invariants, how to change a spec
- `plans/README.md` - frontmatter, lifecycle, closeout, Follow-ups taxonomy
- `ICM/_config/reference-standard-spec.md` - templates and the authoring bar
- `ICM/create-feature/CONTEXT.md` - the pipeline that produces these artifacts
- `/audit-spec-drift` - compare `specs/` against the implementation

`specs/README.md` is authoritative on the layout and invariants. If this file ever disagrees with
it, `specs/README.md` wins - and this file needs updating.
