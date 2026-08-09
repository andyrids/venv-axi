---
context-hierarchy: Layer 2
context-hierarchy-role: Stage control point
maximum-context-tokens: 500
---

# Implementation

Write Python code for the technical specification from the Specification stage.

## Inputs

- `01-specification/output/[slug]-spec.md` - the *how*
- `plans/[slug].md` - scope, approach and Validation criteria
- The `specs/**` files named in that plan's `specs:` field - what MUST be true

Set the plan's `status` to `in-progress` before starting. If the spec turns out to be ambiguous
or wrong, amend the spec - do not guess in code, and do not work around it.

## Reference material

Material tagged 'COULD' should be read if relevant to the technical specification.

- Read (MUST):
  - `ICM/_config/reference-standard-attribution.md`
  - `ICM/_config/reference-standard-docstrings.md`
- Read (COULD):
  - `ICM/_config/reference-standard-toon.md`

## Process

1. Implement the required logic within `src/venvaxi/`
2. Adhere to the project toolchain
3. Draft the implementation report
   - List changes in accordance with specification
     - List files modified
     - Explain decisions
     - Explain issues or concerns
4. CHECKPOINT - await user review in accordance with acceptance criteria

## Outputs

- [slug]-code.md -> `02-implementation/output/`
