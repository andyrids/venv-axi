# Agent eXperience Interface [`venv-axi`]

`venv-axi` provides an [Agent eXperience Interface (AXI)](https://axi.md/), which introspects
dependencies for consuming projects - querying exact signatures present in that venv, at the
exact versions pinned there - in a token-efficient [TOON](https://github.com/toon-format/spec)
format, on STDOUT.

The CLI is installed as `venvaxi` and the same tools are available over MCP (STDIO).

## Why?

The AXI allows introspection of installed packages by importing them, thereby covering
private, internal and undocumented distributions that documentation-retrieval tools cannot see.

The interface cannot drift from the pinned version - reporting what a symbol is rather than how to
use it - complimenting a documentation source such as `Context7`, `King Context` etc.

The AXI answers 'does this exist and what is its exact shape in the version I have
installed?' - other tools answer 'how do I use this and why?'

## How?

An agent scans the codebase with available tools and uses its findings to drive the AXI:

1. Scan the codebase -> bare name (`Console.print`) & package (`rich`)
2. Resolve bare name -> qualified name

```bash
uv run venvaxi find Console.print --package rich
```

```bash
uv run venvaxi inspect rich.console::Console.print
```

Other commands:

- `venvaxi` - Live status & next-step hints
- `venvaxi list` - Installed, declared dependencies
- `venvaxi show rich --api` - Public API symbols
- `venvaxi tree rich --max-depth 1` - Nested module tree
- `venvaxi inspect rich.console` - Direct children
- `venvaxi inherits <qualified_name>` - Direct subclasses
- `venvaxi inherits <qualified_name> --bases` - Direct base classes

Docstrings are truncated to a first line by default - add `--docstring` for complete bodies. The
`--refresh` option rebuilds a stale graph after a dependency version change.

Ambient context for agents is registered by `setup`, which writes MCP server entries into
`.vscode/mcp.json` and `.mcp.json`, and installs a Skill at `.claude/skills/venvaxi/SKILL.md`:

```bash
uv run venvaxi setup
```

The Skill covers the scan -> resolve -> inspect workflow, commands and MCP tool surface alongside
common gotchas. It is the agent-facing half of ambient context, loaded on demand rather than kept
in every session, and it is installed by default - pass `--no-skill` to suppress it:

```bash
uv run venvaxi setup --no-skill
```

Versions before v0.3.0 also injected an always-on block into `AGENTS.md` between
`<!-- venvaxi:begin -->` and `<!-- venvaxi:end -->` markers. That block duplicated the Skill in
every session, and is no longer written. `setup` removes one it finds, leaving every byte outside
the markers untouched.

> [!WARNING]
> `SKILL.md` is a bundled artifact - any local edits to a previously installed copy are
> overwritten.

The AXI tools can be served over MCP (STDIO) with the `venvaxi serve` command, which requires the
`mcp` extra:

```bash
uv add venv-axi --dev --extra mcp
```

The MCP server exposes; `describeBindingTool`, `listPackagesTool`, `showPackageTool`,
`showPackageApiTool`, `showModuleTool`, `getSymbolTool`, `findSymbolTool`, `getInheritorsTool`,
`getModuleTreeTool` and `refreshPackageGraphTool`

> [!NOTE]
> Tool names are in camelCase format, generated from the snake_case function names (`_mcp.py`).

## Installation

> [!NOTE]
> Installation is package-manager agnostic. Use another manager like Poetry and replace the
> `uv run` accordingly or omit entirely, with an activated venv.

```bash
uv add venv-axi --dev
```

With the MCP server extra:

```bash
uv add venv-axi --dev --extra mcp
```

Register ambient context (MCP config and the Skill; `--no-skill` opts out) in the consuming repo:

```bash
uv run venvaxi setup
```

> [!NOTE]
> The MCP config (`.mcp.json`) is only created on `setup` when `venv-axi` is installed with the
> `mcp` optional dependency. On adding this extra dependency, rerun the `setup` command.

`setup` registers the server as `<python> -P -m venvaxi serve` rather than the `venvaxi`
console-script. A running server holds whatever it was launched from open, and on Windows that
stops `uv` from reinstalling `venv-axi` on the next dependency change - the sync fails with
`os error 32` naming `venvaxi.exe`. An interpreter is not replaced by a package reinstall, so the
module form leaves the sync unobstructed.

> [!NOTE]
> An entry written by an earlier version still names the console script. Re-run `setup` to
> migrate it; stop the running server first, or it blocks the sync that `setup` itself triggers.

The symbol graph is cached per-project under `~/.venvaxi/`.

## A note on AI usage

This project is being used as a testbed for spec-driven development (spec-anchored) on top of
Interpretable Context Methodology Interpretable Context Methodology (ICM).

With spec-anchored development, a specification evolves alongside the software and is updated to
reflect the current state of the system as it changes. Adverserial agent verification is used to
automate spec-drift detection.

ICM replaces framework-level orchestration with filesystem structure. Numbered folders represent
stages. Plain markdown files carry prompts and context that tell a single AI agent what role to
play at each step.

> [!IMPORTANT]
> Concepts adapted from an Interpretable Context Methodology paper attributed to Van Clief, J.
> and McDermott, D., 2026 (arXiv:2603.16021).

The system is self-documenting and has been wrapped up in a Claude Code plugin at
[andyrids/icm-spec](https://github.com/andyrids/icm-spec).

A large community dedicated to this methodology can be found at [https://www.skool.com/cliefnotes](https://www.skool.com/cliefnotes/about?ref=478219c6d94340bd984dde6a8d1046e6).

A community member made a detailed and easy-to-understand video guide on YouTube -
[here](https://youtu.be/tvvaOCK_Z50?si=dX86mhIKVEXSVM0k).

> [!NOTE]
> ICM can leverage AI in a way that streamlines development, but also generates enough friction
> in the right areas to promote continued development (Friction Doctrine). This method of using
> Agents is a WIP.

`specs/` is the source of truth for behaviour; `plans/` is the durable record of what got built
and why. Stage outputs stay gitignored scratch. See [`specs/README.md`](specs/README.md) and
[`plans/README.md`](plans/README.md).

**TODO**:

- [X] ~~Research spec-driven development integration & ICM suitability~~
  - Referenced [JarvusInnovations/specops](https://github.com/JarvusInnovations/specops)
  - Created a Claude Code plugin - [andyrids/icm-spec](https://github.com/andyrids/icm-spec)
- [ ] Research verification loops & ICM suitability
  - [Getting started with loops](https://claude.com/blog/getting-started-with-loops)
  - [Building verification loops](https://claude.com/blog/building-verification-loops-in-claude-code-with-skills)
- [ ] Research context engineering changes
  - [The new rules of context engineering](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)

## Attribution

### `tirth8205/code-review-graph`

The SQLite Node|Edge graph architecture and symbol-graph walking patterns used in the AXI modules
are heavily inspired by `code-review-graph`.

`code-review-graph` populates its graph from a static AST, whereas the AXI populates its graph
from live object introspection via `importlib` and `inspect`.

- **Repository**: [tirth8205/code-review-graph](https://github.com/tirth8205/code-review-graph)
- **License**: MIT License - Copyright (c) 2026 Tirth Kanani

### `toon-format/toon-python`

The regex patterns, structural tokens and constant-extraction patterns for TOON format are directly
adapted from the official `toon-python` reference implementation.

- **Repository**: [toon-format/toon-python](https://github.com/toon-format/toon-python)
- **License**: MIT License - Copyright (c) 2025 TOON Format Organization

### `kunchenguid/axi`

I became aware of the AXI design principles through [Kun Chen](https://github.com/kunchenguid)
via his projects and [axi.md site](https://axi.md/). His benchmarks and use of TOON format inspired
and informed the creation of `venv-axi` - a future contribution to the AXI Community Catalog.

- **Repository**:
  - [kunchenguid/axi](https://github.com/kunchenguid/axi)
  - [kunchenguid/gh-axi](https://github.com/kunchenguid/gh-axi)
- **License**: MIT License - Copyright (c) 2026 Kun Chen
