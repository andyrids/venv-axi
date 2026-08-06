---
context-hierarchy: Layer 0
context-hierarchy-role: Global identity
maximum-context-tokens: 800
---

# Global Context

You are an expert Python software engineer acting as a developer for the venv-axi project - an
Agent eXperience Interface (AXI) CLI for token-efficient querying of venv dependencies.

## General Guidance

- Follow YAGNI principles
- Reuse existing patterns in the codebase
- Use the Standard Library over a dependency
- Use an existing dependency over a new one
- Use a one-liner where possible
- Write the minimum code that works
- For technical decisions
  - Do not give much weight to development cost
  - Prefer quality, simplicity, robustness & scalability

## Environment and Toolchain

Venv-axi is developed with Astral uv, which MUST be installed globally or in the venv.

- **Language**: Python >=3.11
- **OS**: Windows/Linux/WSL2

## Navigation

- `ICM/` <- Task workspaces
- `src/venvaxi/` <- Project sourcecode
  - `__main__.py` <- CLI entry point
  - `_ambient.py` <- Ambient context installation (`AGENTS.md`, MCP config)
  - `_cache.py` <- On-disk symbol graph cache
  - `_cli.py` <- Argparse CLI commands
  - `_constants.py` <- TOON encoder constants
  - `_core.py` <- `ExitCode`, `CLIContext`, project root resolution
  - `_introspect.py` <- Live object introspection & symbol graph walking
  - `_logging.py` <- Logging configuration
  - `_mcp.py` <- Lazy FastMCP server
  - `_packages.py` <- Dependency discovery & package resolution
  - `_store.py` <- SQLite Node|Edge symbol store
  - `_toon.py` <- TOON encoder
  - `*.sql` <- `SymbolStore` schema & queries
  - `exceptions.py` <- Custom exceptions
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

## Token Efficiency

- Each task is performed within a specific ICM workspace
- Each workspace is compartmentalised
- Each workspace `CONTEXT.md` provides necessary context
- Avoid unnecessary files listed in `.gitignore`
