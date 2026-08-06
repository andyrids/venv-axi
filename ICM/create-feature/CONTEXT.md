---
context-hierarchy: Layer 2
context-hierarchy-role: Workspace control point
maximum-context-tokens: 300
---

# Create Feature

## Overview

This workspace is used to create new features or refactor existing ones.

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
    ├── 01-specification/    <-- Feature specification
    │   ├── CONTEXT.md
    │   └── output/          <-- Technical specification
    │
    ├── 02-implementation/   <-- Feature implementation
    │   ├── CONTEXT.md 
    │   └── output/          <-- Implemented specification
    │
    ├── 03-verification/     <-- Feature testing
    │   ├── CONTEXT.md
    │   └── output/          <-- Verification report
    │
    └── 04-documentation/    <-- Feature documentation
        ├── CONTEXT.md
        └── output/          <-- Documentation report
```

## Acceptance Criteria

- Artifact creation in accordance with stage guidance
- Adhere to naming convention standards
- Stage checkpoint review
  - User review & acceptance of each output artifact
  - User review & acceptance of modified/created sourcecode
  - User review & acceptance must be explicit before continuation
    - "approved" or "continue" response
