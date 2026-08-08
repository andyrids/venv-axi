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

The AXI answers "does this exist, and what is its exact shape in the version I have
installed?" - other tools answer "how do I use this and why?"

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

Docstrings are truncated to a first line by default - add `--docstring` for complete bodies. The
`--refresh` option rebuilds a stale graph after a dependency version change.

Ambient context for agents can be injected into `AGENTS.md` alongside MCP server entries in
`.vscode/mcp.json` and `.mcp.json`:

```bash
uv run venvaxi setup
```

The optional `--skill` flag additionally installs a Skill at `.claude/skills/venvaxi/SKILL.md`,
covering the scan -> resolve -> inspect workflow, commands and MCP tool surface alongside common
gotchas:

```bash
uv run venvaxi setup --skill
```

> [!WARNING]
> Unlike the marked `AGENTS.md` block, `SKILL.md` is a bundled artifact - any local edits to a
> previously installed copy are overwritten.

The AXI tools can be served over MCP (STDIO) with the `venvaxi serve` command, which requires the
`mcp` extra:

```bash
uv add venv-axi --dev --extra mcp
```

The MCP server exposes; `listPackagesTool`, `showPackageTool`, `showPackageApiTool`,
`showModuleTool`, `getSymbolTool`, `findSymbolTool`, `getInheritorsTool` and
`getModuleTreeTool`

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

Register ambient context (`AGENTS.md` block + MCP config) in the consuming repo:

```bash
uv run venvaxi setup
```

> [!NOTE]
> The MCP config (`.mcp.json`) is only created on `setup` when `venv-axi` is installed with the
> `mcp` optional dependency. On adding this extra dependency, rerun the `setup` command.

The symbol graph is cached per-project under `~/.venvaxi/`.

## A Note on AI Usage

This project is being used as a testbed for Interpretable Context Methodology (ICM), which uses
folder structure as Agent Architecture.

ICM replaces framework-level orchestration with filesystem structure. Numbered folders represent
stages. Plain markdown files carry prompts and context that tell a single AI agent what role to
play at each step.

The system is self-documenting - read `AGENTS.md` (symlink -> `CLAUDE.md`), which provide
development context. Navigate to `CONTEXT.md` as per `AGENTS.md` [`Routing`](AGENTS.md#routing)
instructions to see the necessary routing, context and reference that an agent would follow.

Context reference and guidance markdown files are kept in `ICM/_config` as living documents and
are routed into the agent context where necessary.

A community dedicated to this methodology can be found at [https://www.skool.com/cliefnotes](https://www.skool.com/cliefnotes/about?ref=478219c6d94340bd984dde6a8d1046e6).

> [!NOTE]
> ICM can leverage AI in a way that streamlines development, but also generates enough friction
> in the right areas to promote continued development (Friction Doctrine). This method of using
> Agents is a WIP.

ICM is spec-driven. Three artifact layers are kept deliberately separate:

| Layer    | Answers                       | Location            | Lifetime                     |
| -------- | ----------------------------- | ------------------- | ---------------------------- |
| Spec     | What MUST be true, forever    | `specs/`            | Permanent, changed by review |
| Plan     | What we are doing about it    | `plans/`            | Frozen at `status: done`     |
| Techspec | How, at implementation detail | ICM stage `output/` | Ephemeral scratch            |

`specs/` is the source of truth for behaviour; `plans/` is the durable record of what got built
and why. Stage outputs stay gitignored scratch. See [`specs/README.md`](specs/README.md) and
[`plans/README.md`](plans/README.md).

**TODO**:

- [X] ~~Research spec-driven development integration & ICM suitability~~ - adapted from
  [JarvusInnovations/specops](https://github.com/JarvusInnovations/specops)
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
