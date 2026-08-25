# Architecture

Foundational stack decisions and the module map. This file is documentation of the
implementation's shape, not specification: observable behaviour lives under `specs/` - the symbol
graph's contract in [symbol-graph](../specs/behaviors/symbol-graph.md), cache identity and
project root resolution in [cache-refresh](../specs/behaviors/cache-refresh.md) - and the value
judgements that resolve ambiguity live in [principles](../specs/principles.md).

## Stack

- **Language**: Python >=3.11 (`StrEnum`, `tomllib` and PEP 604 unions are used unguarded)
- **OS**: Windows / Linux / WSL2
- **Toolchain**: `uv` for environments and locking; `just` for recipes; `prek` for hooks
- **Build**: `hatchling` + `hatch-vcs` - the version is derived from git tags, never hand-edited
- **Runtime dependencies**: none. See
  [Zero runtime dependencies](../specs/principles.md#zero-runtime-dependencies)
- **Optional extras**: `mcp` (`fastmcp>=0.1.0`), imported lazily so the CLI works without it

## Module map

- `__main__.py` - CLI entry point, global `--verbose`/`--version`, top-level error handling
- `_ambient.py` - Ambient context installation (MCP config, optional skill, legacy block removal)
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

## Ambient context is the skill plus the MCP registration

[Principle 7](../specs/principles.md#principle-7-ambient-context) is satisfied by two artifacts
`venvaxi setup` writes: the MCP server entries, whose tool descriptions the harness keeps in
context, and the skill, which loads when its `description` matches the task.

The served initialization instructions are a best-effort third channel: `build_server` resolves
the binding once at startup and passes the project root, venv and status to `FastMCP` as
`instructions=`, so a client that surfaces them gives the agent the binding without a tool call;
`specs/commands/serve.md` carries the clause.

The registered command is the module form - `<python> -P -m venvaxi serve` - never the `venvaxi`
console-script shim. A long-lived server holding the shim open blocks the package manager from
reinstalling `venv-axi` on the next dependency change, which surfaces as an `os error 32` on an
unrelated `uv` sync; an interpreter is not replaced by a package reinstall. `-P` keeps the working
directory off `sys.path`, where a shim launch never put it. `specs/commands/setup.md` carries the
clause and the reasoning.

An always-on `AGENTS.md` block was a third channel until it was removed. It duplicated the skill
in every session of every consuming repo whether or not the task touched a dependency, and
`specs/mcp/tools.md` had already named MCP registration the primary ambient integration. `setup`
now strips a block left by an earlier version rather than leaving an orphan nothing refreshes;
`specs/commands/setup.md` carries the clause and the reasoning.

## Two skill copies, one source

- `src/venvaxi/SKILL.md` - the skill, shipped in the wheel and written into consuming repos by
  `venvaxi setup` (by default; `--no-skill` opts out). The only hand-edited copy.
- `.claude/skills/venvaxi/SKILL.md` - this repo's own copy, generated from the first.
  Regenerate with `just skill-sync`, which calls `install_skill` directly so the repo dogfoods
  its own installer without `setup` also rewriting `.mcp.json`.

`specs/commands/setup.md` declares the installed skill a byte-for-byte copy of the packaged one -
no merge, no marker block, no per-repo variation point. There is therefore no dev-facing fork to
protect, and `tests/test_skill_parity.py` fails on any byte of drift, which is what makes this an
enforced rule rather than operational caution.

`install_skill` overwrites unconditionally for any project root, and the returned mapping reports
only `SKILL.md: true|false` - never what a diverged copy contained before it was replaced.
