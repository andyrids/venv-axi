---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---

# Technical Spec: [slug]

The techspec is the *how*. It is ephemeral scratch, gitignored, and rebuilt per run.

It does not carry the feature narrative - that belongs in `specs/**`, which is permanent - and it
does not carry the acceptance criteria, which belong in a plan Validation checklist.

## (1) Spec Delta

{{Name the `specs/**` files created or amended, and summarise what is now declared true. Link the
plan at `plans/[slug].md`. Do not restate the spec here - point at it.}}

## (2) Component Architecture

{{List specific files within the project that require modification or creation. List required
external dependencies.}}

## (3) CLI Interface and UX

{{Detail how the feature interacts with the terminal. Specify argparse changes, STDOUT/STDERR
behavior, logging and rich console output formatting.}}

## (4) Implementation Directives

{{Provide the step-by-step logic required to fulfill the objective. Detail data mutations and
function flow.}}

## (5) Toolchain and Error Handling

{{Specify requirements to satisfy Mypy and Ruff strictness. Anticipate edge cases and define which
`venvaxi.exceptions` should be raised.}}

## (6) Verification Requirements

{{Do not restate acceptance criteria here - the Validation checklist in `plans/[slug].md` is the
single source, and its checkbox text supplies the requirement identifiers 03-verification reports
against. List only the specific functions or classes needing new unit test coverage, each mapped
to the Validation criterion it serves.}}

## (7) References

{{List all project files or external material that were read to generate this specification.}}
