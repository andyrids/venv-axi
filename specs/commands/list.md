---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi list

## Invocation

```text
venvaxi list [--all] [--fields <csv>]
```

| Argument   | Default          | Meaning                                      |
| ---------- | ---------------- | -------------------------------------------- |
| `--all`    | off              | Include dev and optional dependency groups   |
| `--fields` | `name,version`   | Comma-separated display fields               |

## Data requirements

The consuming project's **declared** dependencies, resolved against what is installed. The
project root is the nearest ancestor containing a `pyproject.toml`.

Declared, not merely installed: the answer is what the project asked for, so transitive packages
are excluded. Valid `--fields` values are the `PackageInfo` fields - `name`, `version`,
`location`, `summary`.

## Output rules

- `count: <n>` followed by a `packages` TOON table over the selected fields.
- Default fields are two, not the full four, per principle 2 (minimal default schemas).
- Empty result: `count: 0` plus a hint naming `--all`, which is the flag most likely to produce
  results.
- Footer otherwise names `venvaxi show <package>`.

## Exit codes

`EX_OK`, including the empty case. `EX_FAILURE` on an invalid `--fields` value or an
unresolvable project root.

## Errors

- `InvalidArgumentError` - a `--fields` entry not in `PackageInfo`. The message MUST list both
  the invalid entries and the valid set, so the caller can correct it without a second lookup.
- `ProjectRootNotFoundError` - no `pyproject.toml` found.

## Principles

**Inherited** - project principles that especially bite here:

- Principle 2, minimal default schemas
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - `location` and `summary`
  are available but off by default; they are wide, low-signal columns that would dominate the
  payload.
- [Measured token efficiency beats the headline claim](../principles.md#measured-token-efficiency-beats-the-headline-claim)
  - this is the best case for TOON (~45%), because it is a wide table of short cells.
