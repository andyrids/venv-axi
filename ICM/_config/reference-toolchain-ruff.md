---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [ruff, formatting]
---

# Toolchain - `Ruff`

Ruff is used to implement Python linting and formatting standards.

## Commands

- `uv run pkgdx-lint-hook` - Lint the codebase
- `uv run pkgdx-format-hook` - Format the codebase
- `uv run prek run --all-files` - Run the `lint`/`format` hooks alongside all other hooks

## Configuration

The Ruff config ships inside the installed `pkgdx` dev dependency
(`<site-packages>/pkgdx/standards/ruff.toml`) and is applied by the `pkgdx-lint-hook` and
`pkgdx-format-hook` shims - prefer the hooks over a hand-rolled `ruff` invocation.
