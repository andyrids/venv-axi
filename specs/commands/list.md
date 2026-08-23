---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
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

The `installed` aggregate additionally reads every distribution the active venv's import system
reports, via the same resolution [Package resolution](../behaviors/package-resolution.md) uses to
answer `show <package>` - so every distribution counted is one `show` can resolve. The count
carries no filtering by role: the AXI's own distribution, build tooling, anything else the import
system reports all count, because there is no principled line between a 'meaningfully queryable'
distribution and any other - all of them resolve through the identical metadata lookup. Counted
once per distribution name.

## Outputs

The `list` command shall emit `count: <n>` followed by a `packages` TOON table over the selected
fields.

The default fields are two, not the full four, per
[principle 2, minimal default schemas](../principles.md#principle-2-minimal-default-schemas).

When there are results, the `list` command shall end output with a footer naming
`venvaxi show <package>`.

### Installed-package visibility

`count: <n>` states what the project declares; it says nothing about the venv's wider installed
set, which the project's own code can still import and every AXI command can still answer about
([#50](https://github.com/andyrids/venv-axi/issues/50)). A second aggregate closes that gap
without widening the declared answer itself, per
[principle 4, pre-computed aggregates](../principles.md#principle-4-pre-computed-aggregates).

- When `list` returns one or more packages, the `list` command shall append an `installed: <m>`
  line after the `packages` table and before the `help[]` footer, reporting the number of
  distributions installed in the active venv.
- When `list` returns `count: 0` and the active venv holds at least one importable distribution,
  the `list` command shall append the `installed: <m>` line between `count: 0` and the `help[]`
  footer. This is the sharpest case: a `count: 0` answer with no further signal reads as an empty
  venv, and `installed` is what tells the caller otherwise.
- If the declared count equals the installed count, then the `list` command shall omit the
  `installed:` line - a line reading `6 declared, 6 installed` states no gap, which is noise
  rather than a fact worth a line, and the same reasoning
  [Contextual disclosure](../behaviors/output-contract.md#contextual-disclosure) already applies
  to suppressing a `help[]` hint that names a step the caller does not need.

`installed` is a footer aggregate, not a `help[]` hint: it names no runnable next step, because
none exists on this command - there is no flag or tool call that lists the installed-but-undeclared
set by name (see Out of scope). It sits beside `count:` as a second pre-computed aggregate, never
inside the `help[]` block, and its presence or absence never changes which hint lines the
`--all`-conditional empty-state logic below emits - the two mechanisms are independent, and that
logic is unchanged by this section.

`installed` is unaffected by `--fields`; it is not a `PackageInfo` field and carries no per-package
detail, so there is nothing in it for `--fields` to select.

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
  the caller is actually working against. `installed` reports a bare count, not a list of names,
  so this boundary is unchanged by it.
- **Naming the installed-but-undeclared set** - no third tier on `--all`, no `--installed` flag,
  no enumeration of which distributions make up the gap `installed` reports. Never - a flag
  widening `list` to the whole venv puts two different questions on one command ('what does the
  project declare' and 'what can I query'), and the second is already answered per-package by
  `show <package>`, which needs no listing to work.
- **Flagging undeclared-but-imported packages** - no diagnostic comparing the venv's installed set
  against a project's actual imports. Never - that is a packaging linter, and venvaxi is not one.
- **Version currency** - no outdated-version or upgrade reporting; the answer is what is pinned
  here, not what is available elsewhere. No future spec is planned.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 2, minimal default schemas](../principles.md#principle-2-minimal-default-schemas)
  - `location` and `summary`
  are available but off by default; they are wide, low-signal columns that would dominate the
  payload.
- [Principle 4, pre-computed aggregates](../principles.md#principle-4-pre-computed-aggregates)
  - `installed` is exactly this: a derived field answering 'is the declared list the whole
  queryable surface' without a second round trip.
- [Principle 5, definitive empty states](../principles.md#principle-5-definitive-empty-states)
  - the same reasoning that makes `count: 0` a definitive, actionable answer is why `installed`
  appears on the empty branch too: a declared answer of zero sitting on a nonempty venv is the
  silent gap this principle exists to close, even though `count: 0` itself stays correct.
- [Measured token efficiency beats the headline claim](../principles.md#measured-token-efficiency-beats-the-headline-claim)
  - this is the best case for TOON (~45%), because it is a wide table of short cells.
