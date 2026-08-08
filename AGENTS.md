---
context-hierarchy: Layer 0
context-hierarchy-role: Global identity
maximum-context-tokens: 900
---

# Global Context

You are an expert Python software engineer acting as a developer for the venv-axi project - an
Agent eXperience Interface (AXI) CLI for token-efficient querying of venv dependencies.

## General Guidance

- Read `ICM/_config/reference-standard-yagni.md`

## Environment and Toolchain

Venv-axi is developed with uv, which MUST be installed globally or in the venv.

- **Language**: Python >=3.11
- **OS**: Windows/Linux/WSL2

## Navigation

- `ICM/` <- Task workspaces
- `specs/` <- Desired state - what MUST be true (see `specs/architecture.md` for the module map)
- `plans/` <- Work in flight, frozen at closeout
- `src/venvaxi/` <- Project sourcecode
- `tests/` <- Project unit tests
- `.github/workflows/ci.yml` <- Project CI config
- `.secrets.baseline` <- Secrets baseline (`detect-secrets`)
- `AGENTS.md` <- Global project context
- `CHANGELOG.md` <- Project CHANGELOG
- `CLAUDE.md` <- Symbolic link to AGENTS.md
- `CONTEXT.md` <- Task routing
- `COPYRIGHT` <- Project COPYRIGHT
- `Justfile` <- Just recipes
- `LICENSE` <- Project LICENSE
- `prek.toml` <- Prek pre-commit hook configuration
- `pyproject.toml` <- Project configuration
- `README.md` <- Project README
- `uv.lock` <- Project lockfile

## Workspaces

Interpretable Context Methodology (ICM) is a structured filesystem hierarchy, where numbered
folders represent pipeline stages and Markdown files carry prompts and context.

Each ICM workspace has a `CONTEXT.md`, which is the main control point.

## Routing

User prompt tasking and workspace routing information is in the project root `CONTEXT.md`.

In Claude Code, the `/create-feature` command (`.claude/commands/`) is the preferred entry point.
Unit-test, documentation and refactor tasks are routed through the root `CONTEXT.md`, which fans
them out to the same consolidated `ICM/create-feature` workspace.

## Spec-Driven Development

`specs/` is the source of truth for what MUST be true. `plans/` is the work-in-flight record that
bridges specs to merged code. The `icm-spec` skill carries the full methodology.

- **Specs lead.** Before changing observable behaviour, change the spec; bring code into
  conformance after. Spec/code drift is a bug, not debt.
- **`plans/` is the planning system - not your built-in plan mode.** Every chunk of work lands as
  a file in `plans/` that freezes to `done` as the durable record of what got built. Do not skip
  it for "small" changes. Classic trap: an ephemeral plan of "write spec X, then build it" that
  ends with neither a reviewed spec nor a plan file - split those into the two real artifacts.
- **When to author a plan depends on intent:** mapping out a batch of specs -> finish the batch,
  then propose a *set* of plans; one bounded feature -> spec and plan in tandem; unclear -> ask.
- **A spec change ripples to its plans.** After editing a spec, review the plans implementing it
  (`grep -l '<spec-path>' plans/*.md`) and offer to update them.

Run `/audit-spec-drift` to compare `specs/` against the implementation.

## Token Efficiency

- Each task is performed within a specific, compartmentalised ICM workspace
- Each workspace `CONTEXT.md` provides necessary context
- Avoid unnecessary files listed in `.gitignore`

<!-- venvaxi:begin -->

## VenvAXI

`venvaxi` introspects dependencies for a consuming project - querying exact signatures present in
that venv, at the exact versions pinned there.

You SHOULD prefer `venvaxi` over API recall from memory, which drifts from the installed
version, whereas the AXI cannot.

You MUST scan the codebase with your tools and use any findings to drive the AXI, when conducting
tasks.

### (1) Scan

Locate the import and call sites of the dependency symbol you are working on with your own tools.
This gives you a bare symbol name (`Console.print`) and its owning package (`rich`).

### (2) Resolve

`venvaxi find Console.print --package rich` converts the bare name into a qualified name
(`rich.console::Console.print`), indexing the package if needed.

### (3) Inspect

`venvaxi inspect rich.console::Console.print` returns the real signature and docstring for the
installed version.

## Guidance

Docstrings are truncated by default; add `--docstring` if needed. Add `--refresh` to rebuild a
stale graph after updating dependencies (`find` requires `--package` alongside `--refresh`).

VenvAXI reports what a symbol *is*, not how to use it - reach for documentation if needed.

Other commands:

- `venvaxi` - status & next-step hints
- `venvaxi list [--all]` - installed dependencies
- `venvaxi show <package> [--api]` - metadata|public API symbols
- `venvaxi tree <package> [--max-depth N]` - nested module tree
- `venvaxi inspect <module>` - direct children
- `venvaxi inherits <qualified_name>` - direct subclasses
- `venvaxi serve` - MCP (STDIO)
- `venvaxi setup` - register MCP config & refresh

<!-- venvaxi:end -->
