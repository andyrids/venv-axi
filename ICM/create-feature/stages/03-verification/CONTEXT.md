---
context-hierarchy: Layer 2
context-hierarchy-role: Stage control point
maximum-context-tokens: 500
---

# Verification

Validate code changes through; existing unit tests, new unit tests (if necessary), live CLI
exercise and standard compliance checks.

## Inputs

- `02-implementation/output/[slug]-code.md`
- `plans/[slug].md` - the Validation checklist is the requirement identifier set
- The `specs/**` files named in that plan's `specs:` field
- `.claude/skills/venvaxi/evals/evals.json` - behaviour expectation, not source. An eval encoding
  superseded behaviour is a failing test, so it is checked and updated here

## Reference Material

Material tagged 'COULD' should be read if relevant to the implementation output or verification
process.

- Read (MUST):
  - `ICM/_config/reference-toolchain-coverage.md`
  - `ICM/_config/reference-toolchain-mypy.md`
  - `ICM/_config/reference-toolchain-prek.md`
  - `ICM/_config/reference-toolchain-pymarkdown.md`
  - `ICM/_config/reference-toolchain-pytest.md`
  - `ICM/_config/reference-toolchain-ruff.md`
  - `ICM/_config/reference-toolchain-uv.md`
  - `Justfile`
- Read (COULD):
  - `pyproject.toml`

## Process

1. Review the changes listed in `02-implementation/output/[slug]-code.md`
2. Run existing unit tests
3. CHECKPOINT - only if any test failed or needed fixing
4. Fix any broken existing unit tests (skip if none)
5. Create new unit tests to cover implementation stage
6. Ensure Prek hooks still pass
7. CHECKPOINT - await user review in accordance with acceptance criteria
8. Exercise the affected CLI commands live (`uv run venvaxi ...`) against a real installed package
9. Check conformance against every `specs/**` file named in the plan's `specs:` field - each
   Output Rule, Exit Code and Error, compared to observed behaviour. Divergence is a bug: fix
   the code, or amend the spec if the spec is the thing that is wrong
10. CHECKPOINT - the conformance findings and the decisions they force. A decision that changes
    observable behaviour follows the re-entry rule in `ICM/create-feature/CONTEXT.md`
11. Draft a verification report
    - List Validation criteria from `plans/[slug].md` accounted for, by checkbox text
    - List Validation criteria not covered by existing testing & compliance checks
    - List any spec/code divergence found in step 9, and how it was resolved
    - List unit test coverage percentage (if possible)
12. CHECKPOINT - only if step 10 produced changes, or the report surfaces something step 10 did
    not

Step 7 is unconditional by design, and stays a separate step from the test gate at 3. On the run
that produced this structure, every unit test passed while a lint error sat in the code - lint
and tests catch different classes of defect, so folding them into one gate loses the one that
fires.

## Outputs

- [slug]-test.md -> `03-verification/output/`
