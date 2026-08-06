---
context-hierarchy: Layer 2
context-hierarchy-role: Stage control point
maximum-context-tokens: 500
---

# Specification

Analyse the incoming feature request and generate a comprehensive technical specification.

## Inputs

- User feature request prompt

## Reference Material

Material tagged 'COULD' should be read if relevant for the user prompt and context.

- Read (MUST):
  - `ICM/_config/reference-standard-naming.md`
  - `ICM/_config/reference-standard-techspec.md`
- Read (COULD):
  - `ICM/_config/reference-standard-axi.md`
  - `ICM/_config/reference-standard-toon.md`

## Process

1. Read the provided feature request
2. Consult relevant reference material for additional context
3. Review existing related implementation and tests in `src/` and `tests/` for reusable patterns,
   established conventions, and behavioral contracts that must be preserved
4. Define the architecture changes required within `src/`
5. Draft the specification
6. CHECKPOINT - await user review in accordance with acceptance criteria

## Outputs

- [slug]-spec.md -> `01-specification/output/`
