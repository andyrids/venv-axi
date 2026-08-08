---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Architecture

Foundational decisions and the module map. Concrete tech and structure choices live here;
the value judgements that resolve ambiguity live in [principles.md](principles.md).

## Stack

- **Language**: Python >=3.11 (`StrEnum`, `tomllib` and PEP 604 unions are used unguarded)
- **OS**: Windows / Linux / WSL2
- **Toolchain**: `uv` for environments and locking; `just` for recipes; `prek` for hooks
- **Build**: `hatchling` + `hatch-vcs` - the version is derived from git tags, never hand-edited
- **Runtime dependencies**: none. See
  [Zero runtime dependencies](principles.md#zero-runtime-dependencies)
- **Optional extras**: `mcp` (`fastmcp>=0.1.0`), imported lazily so the CLI works without it

## Module map

- `__main__.py` - CLI entry point, global `--verbose`, top-level error handling
- `_ambient.py` - Ambient context installation (`AGENTS.md`, MCP config, optional skill)
- `_cache.py` - On-disk symbol graph cache, version-hash invalidation
- `_cli.py` - Argparse subcommands and their handlers
- `_constants.py` - TOON encoder constants
- `_core.py` - `ExitCode`, `CLIContext`, project root resolution
- `_introspect.py` - Live object introspection and symbol graph walking
- `_logging.py` - Logging configuration
- `_mcp.py` - Lazy FastMCP server
- `_packages.py` - Dependency discovery and package resolution
- `_store.py` - SQLite Node|Edge symbol store
- `_toon.py` - TOON encoder
- `*.sql` - `SymbolStore` schema and queries
- `exceptions.py` - Custom exceptions, all deriving from a single `Error` base

Everything except `exceptions.py` and `__main__.py` is underscore-private. The public surface is
the CLI and the MCP tools, not the Python API.

## Symbol graph

A SQLite Node|Edge graph, populated by **live introspection** of imported objects - not by static
AST parsing. This is the decisive difference from the projects it is adapted from: `venvaxi` only
ever describes packages actually installed in the consuming venv, so it reports what will really
be imported at runtime, including C extensions and dynamically-constructed attributes.

- **Nodes** are symbols (package, module, class, function, attribute).
- **Edges** are `CONTAINS` and `INHERITS`.
- Keying differs between the two edge kinds - see
  [Qualified name semantics](behaviors/qualified-name-semantics.md).
- The `nodes` table backs an external-content FTS5 index, which constrains how it may be
  rewritten.

## Cache location

The graph is cached per consuming project under `~/.venvaxi/<hash>.db`, where `<hash>` is a
16-character SHA-256 digest of the resolved project root. Two checkouts of the same project at
different paths therefore hold independent caches.

## Project root resolution

The consuming project root is the nearest ancestor of the working directory containing a
`pyproject.toml`, falling back to the venv's parent directory. Failure raises
`ProjectRootNotFoundError`.

## Two skill copies, deliberately

- `src/venvaxi/SKILL.md` - the generic skill, shipped in the wheel and written into consuming
  repos by `venvaxi setup --skill`
- `.claude/skills/venvaxi/SKILL.md` - a hand-maintained dev-facing fork for this repo

`setup --skill` MUST NOT be run inside this repo; it would clobber the dev-facing copy.
