---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [command, setup, ambient]
---

# Command: venvaxi setup

Installs ambient context into the **consuming** repo.

## Invocation / inputs

```text
venvaxi setup [--skill | --no-skill]
```

| Argument     | Default | Meaning                                          |
| ------------ | ------- | ------------------------------------------------ |
| `--skill`    | on      | Install `.claude/skills/venvaxi/SKILL.md`        |
| `--no-skill` | -       | Suppress the skill install                       |

Installing the skill **overwrites** any existing copy. `--skill` remains accepted so that an
existing invocation keeps working; it now names the default rather than opting into it.

**This command writes files. It is not a diagnostic.** A caller reaching for it to check
installation state will mutate the repo instead.

## Data requirements

The consuming project root, and whether `fastmcp` is importable in the venv.

## Actions

Three artifacts and one removal, all idempotent - repeated runs have no adverse effect:

1. **`AGENTS.md`** - the `setup` command shall remove a legacy ambient block delimited by
   `<!-- venvaxi:begin -->` and `<!-- venvaxi:end -->`, deleting the marked span along with the
   blank-line separator that preceded it.

   The `setup` command shall preserve content outside the markers **byte-for-byte**.
   Hand-authored project context lives there, and the block was machine-owned; the two coexisted
   only because the edit is bounded to the marked span, and removal is bounded the same way.

   If `AGENTS.md` does not exist, or exists without both markers, then the `setup` command shall
   make no write and shall report `AGENTS.md: false`. It shall never create the file.

   Ambient context is carried by the skill and the MCP registration below. An always-on block
   duplicating the skill costs every session of every consuming repo whether or not the task
   touches a dependency, so the guidance lives in the artifact that loads on demand.

2. **`.vscode/mcp.json`** - register the server under the `servers` key.
3. **`.mcp.json`** - register the server under the `mcpServers` key.
4. **Skill** - written on every run, suppressed only by `--no-skill`. The `setup` command shall
   write the installed skill as a byte-for-byte copy of the packaged skill - there is no merge,
   no marker block and no per-repo variation point. If an installed skill differs from the
   packaged skill, then the `setup` command shall replace it wholesale, and the returned
   `SKILL.md` key shall report `true` without describing what was discarded.

MCP registration is **gated on `fastmcp` availability**: if `fastmcp` is not importable, then the
`setup` command shall drop the MCP entries rather than write them. A registered server that
`venvaxi serve` cannot start would die on every agent session, which is worse than an absent
entry. The skill describes the CLI as well as the MCP surface, so it is not gated - and because
it is not, it is what makes a bare `setup` meaningful in a repo without the extra. Were the
skill also withheld by default, the explicit setup command that
[principle 7, ambient context](../principles.md#principle-7-ambient-context) depends on would
install nothing at all there, and still exit `EX_OK`.

## Outputs

The `setup` command shall emit a flat TOON object mapping each artifact to whether it was created,
modified or removed, keyed `AGENTS.md`, `.vscode`, `.mcp.json`, `SKILL.md`. The `SKILL.md` key
shall always be present, and shall be true only when the skill was **written**.

It is therefore false in two distinct cases: `--no-skill` was given, and the installed copy already
matched the packaged skill byte-for-byte. That is the same question the other three keys answer -
did this file change - rather than whether the caller asked for it, and it follows from the Local
principle below.

The `AGENTS.md` key means the file was modified, which is now true on removal rather than on
write. The key set does not change with the removal pass: a caller uses it to decide whether to
re-read a file, and stripping the block is exactly such a change.

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
- **Removal of the installed artifacts** - the MCP entries and the skill are installed, never
  uninstalled. Never - they are plain files a caller can delete, and an uninstall verb would have
  to guess which of them a repo still wants.

  The legacy `AGENTS.md` block is the one exception, and it is not an uninstall verb: `setup`
  strips it unconditionally because it is the artifact this command stopped owning, and a
  consumer that never learns it is dead keeps paying for it in every session. Marker-bounded
  removal is what makes that safe to do without asking.
- **Defaulting the skill off for non-Claude harnesses** - `.claude/` is Claude Code specific, and
  the skill is installed by default regardless. `--no-skill` is the escape hatch; no detection of
  the surrounding harness is offered. Never - a harness that cannot use the skill carries one
  unread file, while a repo without `fastmcp` and without the skill receives no ambient context
  at all, so the costs of the two wrong defaults are not symmetric.
- **A per-repo skill variation point** - the installed skill is a verbatim copy of the packaged
  one, with no marker block or overlay for local content. Never - byte-identity is what lets a
  parity check catch drift between the two copies.
- **A diff or refuse mode on skill divergence** - `setup` replaces a diverged installed copy
  without reporting what it discarded. No future spec is planned; revisit if a diverged
  copy ever proves to hold work worth protecting.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 7, ambient context](../principles.md#principle-7-ambient-context), and
  [principle 6, structured errors and exit codes](../principles.md#principle-6-structured-errors-and-exit-codes),
  which is where idempotent mutations are declared
  - state is made visible to
  the agent by an explicit command rather than by magic, and running it twice is always safe.

**Local**:

- **Never claim a write that did not happen.** The returned mapping reports what actually
  changed, not what was requested. An agent uses it to decide whether to re-read a file, so a
  false `true` costs a wasted read and a false `false` hides a change it needed to see.
