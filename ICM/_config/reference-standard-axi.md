---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
maximum-context-tokens: 2500
tags: [AXI, CLI]
---

# Standard - AXI principles

**This content has moved into `specs/`.** It described what MUST be true of `venvaxi`, which
makes it desired state, not a toolchain convention - see `specs/README.md` for the state vs
motion split.

This file remains as a pointer because it is cited from source docstrings and tests.

| You were looking for                  | Now at                                        |
| ------------------------------------- | --------------------------------------------- |
| The 10 AXI Principles (numbered 1-10) | `specs/principles.md`                         |
| Measured token efficiency vs ~40%     | `specs/principles.md`                         |
| Qualified name semantics              | `specs/behaviors/qualified-name-semantics.md` |
| Streams, exit codes, truncation       | `specs/behaviors/output-contract.md`          |

Principle numbers are stable. A source docstring citing 'AXI principle 3' still means content
truncation with size hints.
