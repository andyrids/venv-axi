---
name: venvaxi
description: >-
  This skill should be used before writing or reviewing code that calls into a dependency
  installed in the project venv, whenever an exact signature, docstring, return type or class
  hierarchy needs verifying against the installed version rather than memory recall. Also use
  when setting up, refreshing or troubleshooting the `venvaxi` CLI or its MCP server - a stale
  symbol graph, MCP registration, or a missing `fastmcp` extra.
metadata:
  version: "0.1.0"
---

# Driving the `venvaxi` CLI

## Overview

`venvaxi` is an Agent eXperience Interface (AXI), which answers "does this exist, and what is its
exact shape in the version I have installed?"

The AXI imports the venv package, introspects it, caches the result as a per-project SQLite symbol
graph and prints TOON - a compact tabular text format.

You SHOULD prefer `venvaxi` over API recall from memory, which drifts from the installed version,
whereas this AXI cannot.

You MUST not use `venvaxi` to explain usage - signatures, kinds, docstrings and inheritance edges
are in scope; tutorials, worked recipes and migration guides are not.

## Invocation

`venvaxi` is not on `PATH` here - it is a console script inside the project venv, so every command
MUST run through uv:

```sh
uv run venvaxi find Console.print --package rich
```

The bare `venvaxi ...` spelling used in `AGENTS.md` and in the `help[]` footers assumes an
activated venv or a consuming repo that has the console script on `PATH`. Prefix with `uv run` when
working in this repo.

## Workflow

`venvaxi` is keyed by *qualified* name (`rich.console::Console.print`), but the codebase references
a *bare* one (`Console.print`). The three steps bridge that gap

### (1) Scan

Locate the import and call sites of the dependency symbol you are working on with your own tools.
This gives you a bare symbol name (`Console.print`) and its owning package (`rich`).

### (2) Resolve

`venvaxi find Console.print --package rich` converts the bare name into a qualified name
(`rich.console::Console.print`), indexing the package if needed.

Output example:

```text
count: 3
symbols[3|]{name|kind|qualified_name}:
  print|method|"rich.console::Console.print"
  print_json|method|"rich.console::Console.print_json"
  print_exception|method|"rich.console::Console.print_exception"
help[1]:
  Run `venvaxi inspect <qualified_name>` for complete metadata
```

### (3) Inspect

`venvaxi inspect rich.console::Console.print --docstring` returns the real signature and docstring
for the installed version. Adding `--docstring` prints the full docstring.

```text
qualified_name: "rich.console::Console.print"
kind: method
signature: "(self, *objects: Any, sep: str = ' ', end: str = '\\n',
style: Union[rich.style.Style, str, NoneType] = None,
justify: Optional[Literal['default', 'left', 'center', 'right',
'full']] = None, overflow: Optional[Literal['fold', 'crop',
'ellipsis', 'ignore']] = None, no_wrap: Optional[bool] = None,
emoji: Optional[bool] = None, markup: Optional[bool] = None,
highlight: Optional[bool] = None, width: Optional[int] = None,
height: Optional[int] = None, crop: bool = True,
soft_wrap: Optional[bool] = None,
new_line_start: bool = False) -> None"
doc: Print to the console.
help[1]:
  Run `venvaxi inspect rich.console::Console.print --docstring` for
  the complete docstring
```

A follow-up query could include `inspect rich.console` for direct children discovery or
`inherits rich.console::Console` for direct subclasses.

## Commands

Verified against `venvaxi --help` output; defaults shown in parentheses.

| Command | Flags | Purpose |
| --- | --- | --- |
| `venvaxi` | - | Home view: bin/venv paths, active status, next-step hints |
| `venvaxi list` | `--all`, `--fields` (`name,version`) | Declared, installed venv packages |
| `venvaxi show <pkg>` | `--fields` (`name,version,location`) | Installed package metadata |
| `venvaxi show <pkg> --api` | `--docstring`, `--refresh` | Public top-level API symbols |
| `venvaxi find <query>` | `--package`, `--limit` (`20`), `--refresh` | Search cached symbols |
| `venvaxi tree <pkg>` | `--max-depth` (`2`), `--refresh` | Nested module tree |
| `venvaxi inspect <name>` | `--docstring`, `--refresh` | Symbol detail, or module children |
| `venvaxi inherits <qname>` | `--refresh` | Classes directly subclassing a base |
| `venvaxi serve` | - | Run the MCP server over stdio |
| `venvaxi setup` | `--skill` | Install ambient context (AGENTS.md + MCP config) |

Notes on the positional arguments and shared flags:

- `--fields` accepts any of `name`, `version`, `location`, `summary`; anything else is a hard
  error listing the valid set. It applies to `list` and to `show` *without* `--api` only.
- `show <pkg> --api` takes a distribution name or any importable dotted module path, and
  emits the columns `name|kind|signature|doc`.
- `inspect` takes either a qualified symbol name (`module::Symbol`, `module::Class.method`)
  or a bare/dotted module name - it dispatches on the presence of `::`.
- `--refresh` exists on `show`, `find`, `tree`, `inspect` and `inherits`; it forces a graph
  rebuild before the query.
- `setup --skill` additionally installs the *generic* skill packaged at `src/venvaxi/skill.md`
  into `.claude/skills/venvaxi/SKILL.md`, overwriting any existing copy. Do **not** run it in
  this repo - it would clobber this hand-maintained dev-facing file.

Output contract, common to every command:

- Structured TOON goes to **stdout**, including errors: `error: true` plus a `message:` line,
  with exit code `1`. Success is exit code `0`.
- Collection commands lead with `count: N`, then the table.
- Most commands close with a `help[]` block of concrete next-step commands - follow them
  rather than guessing at a spelling.

## MCP tools

`venvaxi serve` exposes the same surface over stdio MCP under the server name `VenvAXI`. Tool
names are a camelCase version of the underlying functions in `src/venvaxi/_mcp.py`. Every
tool returns a TOON string with the same `count:`/`help[]` contract as the CLI, and any `Error`
presents a TOON error block instead of an MCP transport error.

| Tool | Parameters | CLI equivalent |
| --- | --- | --- |
| `listPackagesTool` | `include_dev=False` | `venvaxi list [--all]` |
| `showPackageTool` | `name` | `venvaxi show <pkg>` |
| `showPackageApiTool` | `name`, `docstring=False` | `venvaxi show <pkg> --api` |
| `showModuleTool` | `name`, `docstring=False` | `venvaxi inspect <module>` |
| `getSymbolTool` | `qualified_name`, `docstring=False` | `venvaxi inspect <qname>` |
| `findSymbolTool` | `query`, `limit=20`, `package=None` | `venvaxi find <query>` |
| `getInheritorsTool` | `qualified_name` | `venvaxi inherits <qname>` |
| `getModuleTreeTool` | `name`, `max_depth=2` | `venvaxi tree <pkg>` |

Types are `str` for names|queries, `bool` for `include_dev`|`docstring`, `int` for
`limit`|`max_depth`, and `str | None` for `package`.

Notable CLI differences:

- The CLI `inspect` splits into `getSymbolTool` (qualified names, with `::`) and
  `showModuleTool` (module names) - pick by argument shape yourself.
- **No tool takes a `refresh` parameter.** A stale graph can only be rebuilt from the CLI, so
  after a dependency version bump run `uv run venvaxi <cmd> ... --refresh` once, then carry
  on over MCP.

## Gotchas

- **Qualified-name form.** The separator is `::`, not a dot: `rich.console::Console` and
  `rich.console::Console.print`. A fully dotted spelling like `rich.console.Console.print`
  has no `::`, so `inspect` treats it as a *module* name and it fails to resolve.
- **`find` without `--package` only searches what is already cached.** On a cold cache that
  is nothing, and you get `count: 0`. Always pass `--package` on the first lookup for a
  package - it indexes and scopes in one step. `--refresh` without `--package` is a hard
  error ("`--refresh` requires `--package` to name the graph to rebuild").
- **`count: 0` is a definitive empty state, not a failure.** Unresolvable names raise, so a
  zero count means the query resolved and genuinely matched nothing. For `inherits`
  specifically it means the base class resolved with zero *indexed* subclasses - subclasses
  living in an unindexed package, or below the built depth, are simply invisible until you
  index that package (`find <name> --package <pkg>`) or rebuild deeper (`tree <pkg>
  --max-depth N`).
- **Docstrings are truncated to a first line by default.** Add `--docstring` to `inspect` or
  to `show --api` when the parameter semantics matter, not just the signature.
- **When to `--refresh`.** The cache lives at `~/.venvaxi/<project-hash>.db` and already
  invalidates itself when a package's installed version changes, or when a query needs more
  depth than was built. Reach for `--refresh` when the version string cannot move but the
  code did - editable/local installs, a package patched in place - or when a build was
  interrupted.
- **`tree` defaults to `--max-depth 2`.** Deep packages are silently shallow at the default;
  raise it when you are hunting for a submodule rather than surveying.
- **MCP needs the extra.** `serve` requires `fastmcp` (`uv add venv-axi[mcp]`) and exits `1`
  with a "requires the `venv-axi[mcp]` extra" log line without it. `setup` deliberately *omits*
  the MCP entry from `.mcp.json` / `.vscode/mcp.json` when `fastmcp` is missing, so an absent
  server entry after `setup` means the extra is not installed.
- **`setup` writes files - it is not a diagnostic command.** It rewrites `AGENTS.md`'s ambient
  block and `.mcp.json`/`.vscode/mcp.json` every time it runs. "Idempotent" here only means
  repeated runs converge on the same result, not that a run is side-effect-free - it still
  touches tracked files. Diagnosing *whether* `fastmcp` is available is a read-only question:
  answer it with `venvaxi show fastmcp` (raises `PackageNotFoundError` if absent) rather than
  running `setup` to see what it does. Only run `setup` when you actually mean to (re-)register
  the MCP server - e.g. right after installing the extra, or when told to fix a stale
  registration - never as a way to confirm or explain a fix while investigating.
- **Token savings are payload-shaped, not a flat ~40%.** Measured against compact JSON
  (`tests/test_toon_benchmark.py`): `venvaxi list` ~45%, `venvaxi find` ~27%, `venvaxi inspect
  <symbol>` ~6%. The saving comes from amortising repeated JSON keys across a table header,
  so it scales with row count and collapses on single-object output. Do not budget for a
  general ~40%; on the `inspect` path, efficiency comes from truncation instead.

## Pointers

- `uv run venvaxi <cmd> --help` is the authoritative flag source. If the table above ever
  disagrees with it, `--help` wins - and this file needs updating.
- `ICM/_config/reference-standard-axi.md` covers the 10 AXI design principles, the measured
  token-efficiency benchmarks and the symbol-graph qualified-name invariants. Read it when
  modifying `src/venvaxi/` itself; it is not needed to *use* the CLI.
- The always-on summary injected into `AGENTS.md` is generated from `src/venvaxi/ambient.md`
  and refreshed by `venvaxi setup`. Edit the markdown, not the Markdown block.
