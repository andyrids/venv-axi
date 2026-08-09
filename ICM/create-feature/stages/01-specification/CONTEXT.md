---
context-hierarchy: Layer 2
context-hierarchy-role: Stage control point
maximum-context-tokens: 500
---

# Specification

Declare what MUST be true, plan the work that gets there, then detail how.

## Inputs

- User feature request prompt

## Reference material

Material tagged 'COULD' should be read if relevant for the user prompt and context.

- Read (MUST):
  - `ICM/_config/reference-standard-markdown.md`
  - `ICM/_config/reference-standard-naming.md`
  - `ICM/_config/reference-standard-spec.md`
  - `ICM/_config/reference-standard-techspec.md`
  - `specs/README.md`
  - `plans/README.md`
- Read (COULD):
  - `specs/principles.md`
  - `ICM/_config/reference-standard-toon.md`

## Process

1. Read the provided feature request
2. Consult relevant reference material for additional context
3. Read the `specs/**` files the request touches - they are the current desired state, and the
   request is a proposal to change it
4. Review existing related implementation and tests in `src/` and `tests/` for reusable patterns,
   established conventions, and behavioral contracts that must be preserved
5. Decide the mode before drafting anything:
   - **One bounded feature** in a settled area - draft the spec change and its plan in tandem
   - **A batch of specs** being mapped out - finish the batch first, then propose a *set* of
     plans; the good partition rarely maps one-to-one onto spec files
   - **Unclear** - ask which it is; do not default
6. Write or amend the `specs/**` file(s) - what MUST be true, not how to build it
7. Write `plans/[slug].md` - frontmatter `specs:` naming the files from step 6, and a Validation
   checklist concrete enough to tick off in 03-verification
8. Define the architecture changes required within `src/`
9. Draft the techspec
10. CHECKPOINT - await user review in accordance with acceptance criteria

## Outputs

Three artifacts, two of them tracked:

- `specs/**` -> the permanent contract (tracked)
- `plans/[slug].md` -> the work record (tracked)
- `[slug]-spec.md` -> `01-specification/output/` (ephemeral scratch)

The spec says what MUST be true forever. The plan says what is being done about it now. The
techspec says how. Collapsing them is the failure this stage exists to prevent - see
`specs/README.md`.
