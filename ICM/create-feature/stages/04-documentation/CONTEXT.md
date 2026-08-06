---
context-hierarchy: Layer 2
context-hierarchy-role: Stage control point
maximum-context-tokens: 500
---

# Documentation

Finalise the workflow by updating project documentation to reflect any changes.

## Inputs

- `03-verification/output/[slug]-test.md`

## Reference Material

Material tagged 'COULD' should be read if relevant to the implementation output or verification
process.

- Read (MUST):
  - `ICM/_config/reference-standard-changelog.md`
  - `ICM/_config/reference-standard-techspec.md`

## Process

1. Review the output from previous stages
2. Create a documentation report
   - List relevant documentation updates
     - `README.md`, `CHANGELOG.md` etc.
   - List new reusable design patterns introduced during implementation
     - Consider appending to a relevant `ICM/_config/reference-*.md` file
     - Consider creating a new `ICM/_config/reference-*.md` file
3. CHECKPOINT - await user review in accordance with acceptance criteria
4. Update project documentation

## Outputs

- [slug]-docs.md -> `04-documentation/output/`
