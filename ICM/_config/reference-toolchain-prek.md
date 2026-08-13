---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
maximum-context-tokens: 2500
tags: [prek, pre-commit]
---

# Toolchain - `Prek`

Prek is used as a pre-commit hook manager and is installed as a dependency. Running Prek through
`uv run` ensures that the project virtual environment is activated and utilized.

## Commands

- `uv run prek install` - Install Git shims
- `uv run prek run` - Run hooks for files staged in Git
- `uv run prek run -vvv` - Run hooks with verbose output
- `uv run prek run --all-files` - Run hooks for all files
- `uv run prek validate-config prek.toml` - Validate a Prek config

## Configuration

- Project config: `prek.toml`
  - Root Prek config for this repo, scaffolded by `uv run pkgdx init`
  - MUST not be changed by hand - re-run `pkgdx init` instead
- The hooks it references (`pkgdx-lint`, `pkgdx-format`, `pkgdx-typing`, `pkgdx-markdown`,
  `pkgdx-secrets`) are exposed by the `pkgdx` dev dependency
