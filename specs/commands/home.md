---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [command, home, status]
---

# Command: venvaxi

The bare invocation. No subcommand.

## Invocation / inputs

```text
venvaxi [-v|--verbose] [--version]
```

The subparsers action is deliberately **not** `required`, so a bare `venvaxi` falls through to
this view instead of erroring.

`--version` is checked ahead of subcommand dispatch and short-circuits every other input,
including `-v`/`--verbose`; see [Outputs](#outputs) below.

## Data requirements

Live process state only. No package resolution, no symbol store, no project root lookup - this
view MUST work in a broken or uninitialized project.

- `bin` - the resolved path of `sys.argv[0]`
- `venv` - the resolved `sys.prefix`
- `status` - `active` when `sys.prefix != sys.base_prefix`, else `inactive`

Both paths are rendered `~/`-prefixed when under the home directory, else absolute.

## Outputs

The bare invocation shall emit a flat TOON object of `description`, `bin`, `venv`, `status`,
followed by a `help[]` footer naming every available command with a concrete, runnable template.

This is the content-first surface: it shows live, actionable state, never help text.

Where `--version` is given, the bare invocation shall instead emit a single `version: <version>`
TOON line and exit `EX_OK`, short-circuiting the view above - no `description`/`bin`/`venv`/
`status` object and no `help[]` footer are emitted alongside it. There is no next step to
disclose, so none is manufactured to keep the shape constant with every other command
(`specs/behaviors/output-contract.md#contextual-disclosure`).

## Failure modes

The bare invocation shall exit `EX_OK` on every run.

If the project root is unresolvable or the project is broken or uninitialized, then the bare
invocation shall still emit the status object and exit `EX_OK` - none by design, because this is
the first thing an agent runs and it has to answer before anything else works.

If package metadata is unavailable - an uninstalled source checkout, for example - then
`--version` shall emit `version: (no version metadata)` rather than raising, and still exit
`EX_OK`. The marker is a definitive empty state under
[Output contract](../behaviors/output-contract.md#definitive-empty-states), matching the house
pattern (`(no project root)`, `(no docstring)`) rather than a bare empty string a caller could
mistake for a real, empty version.

## Out of scope

- **Project and dependency introspection** - the view reports process state (`bin`, `venv`,
  `status`) only; dependency data belongs to `list` and package data to `show`. Never - reaching
  for the symbol store here would break the guarantee that this view works in a broken project.
- **The resolved project root** - not reported, though it could be. Never, but not for the reason
  above: [`describeBindingTool`](../mcp/tools.md#the-binding-report) resolves the root and degrades
  to a marker rather than raising, which is a working demonstration that a root lookup need not
  cost this view its broken-project guarantee. The reason is that it would tell a CLI caller
  nothing. The root is the nearest ancestor of the working directory holding a `pyproject.toml`,
  and a CLI caller chose that directory - so the answer is one they already have. An MCP caller
  chose neither the directory nor the interpreter, which is why the same field is load-bearing
  over there and inert here.
- **A short `-V` spelling for `--version`** - not offered. Never - `-v` already means
  `--verbose` and is unaffected by this addition
  ([#81](https://github.com/andyrids/venv-axi/issues/81) is explicit that the flag letter was
  never the defect, only the missing capability), and a second short flag was not asked for.
- **`version` on the home view's own output block** - not added, though issue #81's resolution 3
  named it as a cheap addition once `__version__` is already being read. Declined for now:
  `--version` alone already answers the question for a caller who reaches for it, and folding a
  version field into every bare `venvaxi` invocation conflates two different questions -
  'what am I running' and 'what state is this venv in' - on the one view built to answer the
  second quickly. Revisit only if a future issue argues the home block itself needs it.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 8, content first](../principles.md#principle-8-content-first), and
  [principle 9, contextual disclosure](../principles.md#principle-9-contextual-disclosure)
  - this command is the
  reference implementation of both. It is the first thing an agent runs, so it MUST answer with
  live state plus next steps, and never with a usage summary.
