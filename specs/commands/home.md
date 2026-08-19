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
venvaxi [-v|--verbose]
```

The subparsers action is deliberately **not** `required`, so a bare `venvaxi` falls through to
this view instead of erroring.

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

## Failure modes

The bare invocation shall exit `EX_OK` on every run.

If the project root is unresolvable or the project is broken or uninitialized, then the bare
invocation shall still emit the status object and exit `EX_OK` - none by design, because this is
the first thing an agent runs and it has to answer before anything else works.

## Out of scope

- **Project and dependency introspection** - the view reports process state (`bin`, `venv`,
  `status`) only; dependency data belongs to `list` and package data to `show`. Never - reaching
  for the project root or the symbol store here would break the guarantee that this view works in
  a broken project.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 8, content first](../principles.md#principle-8-content-first), and
  [principle 9, contextual disclosure](../principles.md#principle-9-contextual-disclosure)
  - this command is the
  reference implementation of both. It is the first thing an agent runs, so it MUST answer with
  live state plus next steps, and never with a usage summary.
