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
3. CHECKPOINT - await user review in accordance with acceptance criteria
4. Fix any broken existing unit tests
5. CHECKPOINT - await user review in accordance with acceptance criteria
6. Create new unit tests to cover implementation stage
7. Ensure Prek hooks still pass
8. CHECKPOINT - await user review in accordance with acceptance criteria
9. Exercise the affected CLI commands live (`uv run venvaxi ...`) against a real installed package
10. CHECKPOINT - await user review in accordance with acceptance criteria
11. Draft a verification report
    - List requirement identifiers accounted for
    - List requirement identifiers not covered by existing testing & compliance checks
    - List unit test coverage percentage (if possible)
12. CHECKPOINT - await user review in accordance with acceptance criteria

## Outputs

- [slug]-test.md -> `03-verification/output/`
