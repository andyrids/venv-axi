---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state
immutable: false
tags: [command, setup, ambient]
---

# Command: venvaxi setup

Installs ambient context into the **consuming** repo.

## Invocation / inputs

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

1. **`AGENTS.md`** - the `setup` command shall inject a block delimited by
   `<!-- venvaxi:begin -->` and `<!-- venvaxi:end -->`, sourced from `src/venvaxi/ambient.md`.
   The file is created if absent; the marked region is replaced if present, appended if the file
   exists without markers.

   The `setup` command shall preserve content outside the markers **byte-for-byte**.
   Hand-authored project context lives there, and the block is machine-owned; the two coexist
   only because replacement is bounded to the marked span.

2. **`.vscode/mcp.json`** - register the server under the `servers` key.
3. **`.mcp.json`** - register the server under the `mcpServers` key.
4. **Skill** - only with `--skill`.

MCP registration is **gated on `fastmcp` availability**: if `fastmcp` is not importable, then the
`setup` command shall drop the MCP entries rather than write them. A registered server that
`venvaxi serve` cannot start would die on every agent session, which is worse than an absent
entry. The `AGENTS.md` guidance is valid either way, so it is not gated.

## Outputs

The `setup` command shall emit a flat TOON object mapping each artifact to whether it was created
or modified, keyed `AGENTS.md`, `.vscode`, `.mcp.json`, `SKILL.md`. The `SKILL.md` key shall
always be present, and shall be true only when `--skill` was requested.

The footer shall name `venvaxi` to confirm ambient context is live, plus `uv add venv-axi[mcp]`
when the extra is missing.

## Failure modes

- If ambient context cannot be installed, then the `setup` command shall raise
  `AmbientContextError`, emit the TOON error block and exit `EX_FAILURE`.
- If no project root resolves, then the `setup` command shall raise `ProjectRootNotFoundError`,
  emit the TOON error block and exit `EX_FAILURE`.
- If a run is interrupted mid-write, then the target file shall be left untouched - writes are
  atomic, a same-directory temp file plus rename.

Success exits `EX_OK`, per the [exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **A read-only status mode** - `setup` mutates; checking installation state without writing is
  not offered. No future spec is planned; the warning under Invocation exists precisely because
  a reader would assume otherwise.
- **Removal** - artifacts are installed, never uninstalled. Never - the marked `AGENTS.md` block
  keeps hand-removal bounded, and the other artifacts are plain files a caller can delete.

## Principles

**Inherited** - project principles that especially bite here:

- Principle 7, ambient context, and principle 6, idempotent mutations
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - state is made visible to
  the agent by an explicit command rather than by magic, and running it twice is always safe.

**Local**:

- **Never claim a write that did not happen.** The returned mapping reports what actually
  changed, not what was requested. An agent uses it to decide whether to re-read a file, so a
  false `true` costs a wasted read and a false `false` hides a change it needed to see.
