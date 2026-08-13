---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state
immutable: false
tags: [command, list]
---

# Command: venvaxi list

## Invocation / inputs

```text
venvaxi list [--all] [--fields <csv>]
```

| Argument   | Default          | Meaning                                      |
| ---------- | ---------------- | -------------------------------------------- |
| `--all`    | off              | Include dev and optional dependency groups   |
| `--fields` | `name,version`   | Comma-separated display fields               |

## Data requirements

The consuming project's **declared** dependencies, resolved against what is installed. The
project root is resolved as in [Cache and refresh](../behaviors/cache-refresh.md).

Declared, not merely installed: the answer is what the project asked for, so transitive packages
are excluded. Valid `--fields` values are the `PackageInfo` fields - `name`, `version`,
`location`, `summary`.

## Outputs

The `list` command shall emit `count: <n>` followed by a `packages` TOON table over the selected
fields.

The default fields are two, not the full four, per
[principle 2, minimal default schemas](../principles.md#principle-2-minimal-default-schemas).

When there are results, the `list` command shall end output with a footer naming
`venvaxi show <package>`.

Empty-state hints are conditional on `--all`, because the flag that widens the answer is only a
next step while it is still unused:

- When a `list` without `--all` returns no results, the `list` command shall emit `count: 0` plus
  a hint naming `--all`, which is the flag most likely to produce results.
- When a `list` with `--all` returns no results, the `list` command shall emit `count: 0` plus a
  hint naming `pyproject.toml` as the source of the declarations it found none of. There is no
  broader query left, so the honest next step is the file that would have to change.

Hinting `--all` to a caller who just passed `--all` is barred by the suppression rule in
[Output contract](../behaviors/output-contract.md#contextual-disclosure). It also misreads the
answer: an empty `list --all` is the definitive statement that the project declares no
dependencies, not a suggestion to search harder.

## Failure modes

- If a `--fields` entry is not a `PackageInfo` field, then the `list` command shall raise
  `InvalidArgumentError`, emit the TOON error block and exit `EX_FAILURE`. The message shall
  list both the invalid entries and the valid set, so the caller can correct it without a second
  lookup.
- If no project root resolves, then the `list` command shall raise `ProjectRootNotFoundError`,
  emit the TOON error block and exit `EX_FAILURE`.

An empty result is success - `count: 0` exits `EX_OK`, per the
[exit codes](../behaviors/output-contract.md#exit-codes).

## Out of scope

- **Transitive dependencies** - the answer is what the project declares, not everything installed
  in the venv. Never - an exhaustive installed-set listing would bury the declared dependencies
  the caller is actually working against.
- **Version currency** - no outdated-version or upgrade reporting; the answer is what is pinned
  here, not what is available elsewhere. No future spec is planned.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 2, minimal default schemas](../principles.md#principle-2-minimal-default-schemas)
  - `location` and `summary`
  are available but off by default; they are wide, low-signal columns that would dominate the
  payload.
- [Measured token efficiency beats the headline claim](../principles.md#measured-token-efficiency-beats-the-headline-claim)
  - this is the best case for TOON (~45%), because it is a wide table of short cells.
