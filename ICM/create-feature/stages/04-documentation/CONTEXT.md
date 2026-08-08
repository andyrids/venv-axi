---
context-hierarchy: Layer 2
context-hierarchy-role: Stage control point
maximum-context-tokens: 500
---

# Documentation and Closeout

Update project documentation, then freeze the plan as the durable record of what was built.

## Inputs

- `03-verification/output/[slug]-test.md`
- `plans/[slug].md` - the plan being closed out

## Reference Material

Material tagged 'COULD' should be read if relevant to the implementation output or verification
process.

- Read (MUST):
  - `ICM/_config/reference-standard-changelog.md`
  - `ICM/_config/reference-standard-techspec.md`
  - `plans/README.md`

## Process

1. Review the output from previous stages
2. Create a documentation report
   - List relevant documentation updates
     - `README.md`, `CHANGELOG.md` etc.
   - List new reusable design patterns introduced during implementation
     - Consider appending to a relevant `ICM/_config/reference-*.md` file
     - Consider creating a new `ICM/_config/reference-*.md` file
   - List the closeout edits planned for `plans/[slug].md`
3. CHECKPOINT - await user review in accordance with acceptance criteria
4. Update project documentation
5. Close out `plans/[slug].md` - this is the last edit before merge, after which the plan freezes
   as historical record:
   - Flip `status` to `done` and add `pr:`
   - Tick Validation boxes **only where verified** - leave the rest unticked and say why in
     Notes. A ticked box that was not checked is worse than an unticked one
   - Populate Notes: decisions taken, gotchas found, version pins
   - Populate Follow-ups using the taxonomy in `plans/README.md`; state `None` explicitly rather
     than leaving the section empty
   - Absorb any `Deferred to` entry into the named downstream plan **in this same commit** - a
     bullet in its Approach plus a new Validation criterion. An unabsorbed deferral is a
     non-binding pointer, and the work is lost between two documents each assuming the other
     owns it
6. Reconcile `specs/` - if the implementation diverged from the spec during 02 or 03, either the
   code or the spec is now wrong. Fix one. Divergence is a bug, not debt
7. Ripple check - for each spec touched, find the plans chasing it and offer to update them:
   `grep -l '<spec-path>' plans/*.md`. A `planned` plan may need revising; flag, do not silently
   rewrite, an `in-progress` one
8. CHECKPOINT - await user review in accordance with acceptance criteria

## Outputs

- [slug]-docs.md -> `04-documentation/output/`
