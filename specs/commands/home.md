---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi

The bare invocation. No subcommand.

## Invocation

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

## Output rules

A flat TOON object of `description`, `bin`, `venv`, `status`, followed by a `help[]` footer
naming every available command with a concrete, runnable template.

This is the content-first surface: it shows live, actionable state, never help text.

## Exit codes

Always `EX_OK`.

## Errors

None by design. This view MUST NOT raise on an unresolvable project root.

## Principles

**Inherited** - project principles that especially bite here:

- Principle 8, content first, and principle 9, contextual disclosure
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - this command is the
  reference implementation of both. It is the first thing an agent runs, so it MUST answer with
  live state plus next steps, and never with a usage summary.
