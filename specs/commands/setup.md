---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi setup

Installs ambient context into the **consuming** repo.

## Invocation

```text
venvaxi setup [--skill]
```

| Argument  | Default | Meaning                                             |
| --------- | ------- | --------------------------------------------------- |
| `--skill` | off     | Also install `.claude/skills/venvaxi/SKILL.md`      |

`--skill` **overwrites** any existing copy.

**This command writes files. It is not a diagnostic.** A caller reaching for it to check
installation state will mutate the repo instead.

## Data requirements

The consuming project root, and whether `fastmcp` is importable in the venv.

## Actions

Four artifacts, all idempotent - repeated runs have no adverse effect:

1. **`AGENTS.md`** - inject a block delimited by `<!-- venvaxi:begin -->` and
   `<!-- venvaxi:end -->`, sourced from `src/venvaxi/ambient.md`. Created if absent; the marked
   region is replaced if present, appended if the file exists without markers.

   **Content outside the markers MUST be preserved byte-for-byte.** Hand-authored project context
   lives there, and the block is machine-owned; the two coexist only because replacement is
   bounded to the marked span.

2. **`.vscode/mcp.json`** - register the server under the `servers` key.
3. **`.mcp.json`** - register the server under the `mcpServers` key.
4. **Skill** - only with `--skill`.

MCP registration is **gated on `fastmcp` availability**; without it the entry is dropped rather
than written. A registered server that `venvaxi serve` cannot start would die on every agent
session, which is worse than an absent entry. The `AGENTS.md` guidance is valid either way, so it
is not gated.

Writes are atomic - a same-directory temp file plus rename - so an interrupted run leaves the
target untouched.

## Output rules

A flat TOON object mapping each artifact to whether it was created or modified, keyed
`AGENTS.md`, `.vscode`, `.mcp.json`, `SKILL.md`. The `SKILL.md` key is always present, and is
only ever true when `--skill` was requested.

Footer names `venvaxi` to confirm ambient context is live, plus `uv add venv-axi[mcp]` when the
extra is missing.

## Exit codes

`EX_OK`. `EX_FAILURE` on `AmbientContextError`.

## Errors

- `AmbientContextError` - ambient context cannot be installed.
- `ProjectRootNotFoundError` - no project root resolved.

## Principles

**Inherited** - project principles that especially bite here:

- Principle 7, ambient context, and principle 6, idempotent mutations
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - state is made visible to
  the agent by an explicit command rather than by magic, and running it twice is always safe.

**Local**:

- **Never claim a write that did not happen.** The returned mapping reports what actually
  changed, not what was requested. An agent uses it to decide whether to re-read a file, so a
  false `true` costs a wasted read and a false `false` hides a change it needed to see.
