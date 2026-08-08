---
context-hierarchy: Layer 2
context-hierarchy-role: Workspace control point
maximum-context-tokens: 300
---

# Create Feature

## Overview

This workspace is used to create new features or refactor existing ones.

Work is spec-driven. `specs/` declares what MUST be true and is permanent; `plans/` records the
work in flight and freezes at closeout; stage `output/` is ephemeral scratch. Read
`specs/README.md` for the split before starting.

## Routing

### Specification Stage

- **Navigate to**: stages/01-specification
- **Read**: CONTEXT.md

### Implementation Stage

- **Navigate to**: stages/02-implementation
- **Read**: CONTEXT.md

### Verification Stage

- **Navigate to**: stages/03-verification
- **Read**: CONTEXT.md

### Documentation Stage

- **Navigate to**: stages/04-documentation
- **Read**: CONTEXT.md

## Navigation

Each stage `CONTEXT.md` provides specific routing & reference material.

```text
create-feature/
├── CONTEXT.md
└── stages/                  <-- 4-stage pipeline
    ├── 01-specification/    <-- Spec change, plan & techspec
    │   ├── CONTEXT.md
    │   └── output/          <-- Technical specification
    │
    ├── 02-implementation/   <-- Feature implementation
    │   ├── CONTEXT.md
    │   └── output/          <-- Implemented specification
    │
    ├── 03-verification/     <-- Feature testing & spec conformance
    │   ├── CONTEXT.md
    │   └── output/          <-- Verification report
    │
    └── 04-documentation/    <-- Documentation & plan closeout
        ├── CONTEXT.md
        └── output/          <-- Documentation report
```

Stage `output/` is gitignored scratch. The tracked artifacts this pipeline produces live outside
the workspace:

```text
specs/                       <-- Permanent contract (written in stage 01)
plans/[slug].md              <-- Work record (opened in 01, frozen in 04)
```

## Re-entry

A decision that changes observable behaviour returns to the earliest stage whose output it
invalidates - normally 01, because the spec and the plan must change first. Re-run only the
delta, and record the re-entry in the plan's Notes.

A linear pass that quietly patches an earlier stage's output is how a spec and its implementation
drift apart inside a single run.

## Acceptance Criteria

- Artifact creation in accordance with stage guidance
- Adhere to naming convention standards
- Stage checkpoint review, over each output artifact and any modified or created sourcecode
- User review & acceptance MUST be explicit before continuation:
  - "approved" or "continue" - proceed as presented
  - approval carrying changes - apply them, and where they change observable behaviour,
    follow the re-entry rule above

A checkpoint marked *only if* is conditional. Its condition MUST be discharged with evidence in
the visible response ("216 passed, 0 failed - no gate"), so a skip is announced and can be
objected to. An unannounced skip is worse than the vacuous gate it replaces.
