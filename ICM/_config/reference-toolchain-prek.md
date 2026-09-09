---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
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

## CI

The suite is not enforced by a contributor's local `prek install` alone. The `static` job in
`.github/workflows/ci.yml` runs it on every pull request: its `Run every prek hook` step is
`uv run -m prek run --all-files`, so every hook `prek.toml` declares is a gate.

Prek builds each hook's environment itself and never reads `uv.lock`, and `pkgdx` constrains its
tools with lower bounds only, so an unconstrained hook environment resolves whatever is newest on
PyPI - a tool release alone could then turn CI red. The preceding `Pin prek's hook environments to
uv.lock` step exports the lock's pins and the run step sets `UV_CONSTRAINT` to that file, so the
hooks resolve the versions the project resolves. `pkgdx` itself is excluded from the export
(`--no-emit-package pkgdx`): prek clones the hook repo without tags, so the version its `hatch-vcs`
config derives is not the one the lock records, and pinning it makes the environment unsolvable.
