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
  - Rewrites files and exits 0 whatever it finds, so it formats but does not gate. `--check` is the
    gating form, and the `Format [Ruff]` hook carries `--exit-non-zero-on-format`
- `uv run prek run --all-files` - Run the `lint`/`format` hooks alongside all other hooks

## Configuration

The Ruff config ships inside the installed `pkgdx` dev dependency
(`<site-packages>/pkgdx/standards/ruff.toml`) and is applied by the `pkgdx-lint-hook` and
`pkgdx-format-hook` shims - prefer the hooks over a hand-rolled `ruff` invocation.
