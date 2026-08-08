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

## Acceptance Criteria

- Artifact creation in accordance with stage guidance
- Adhere to naming convention standards
- Stage checkpoint review
  - User review & acceptance:
    - Each output artifact
    - Modified|created sourcecode
    - MUST be explicit before continuation - "approved" | "continue"
