---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [coverage]
---

# Toolchain - `Coverage.py`

Coverage is used to measure Python code coverage.

## Commands

A coverage report can be generated through uv:

```bash
uv run coverage run -m pytest -v
uv run coverage report
```

The Justfile `coverage` recipe can also be used:

```bash
just coverage
```
