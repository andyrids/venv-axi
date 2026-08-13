---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state
immutable: false
tags: [principles]
---

# Principles

The project's philosophy, written down. Each principle is decisive - it picks a side of a real
trade-off, so an implementer can resolve an unspecified case the way the author would.

Enumerated rules in a command spec only cover the cases someone thought to write down. These
cover the rest. A rule that cannot be disagreed with is a platitude, not a principle.

Command and behaviour specs reference these down into their own `## Principles` sections. To find
what a principle governs, grep for links to its anchor - no list is maintained here, because it
would rot.

## The 10 AXI Principles

Source: [axi.md](https://axi.md/), 'The 10 AXI Principles'. These are the design contract every
command output MUST satisfy.

1. **Token-efficient output** - use TOON format for token savings over JSON.
2. **Minimal default schemas** - return 3-4 fields per list item by default, not 10+.
3. **Content truncation** - truncate large text fields with a size-hint suffix (e.g. `truncated,
   2847 chars total`).
4. **Pre-computed aggregates** - include derived fields (e.g. `count`) that eliminate round
   trips.
5. **Definitive empty states** - an explicit zero-result message on empty output, never silent
   blank output.
6. **Structured errors & exit codes** - idempotent mutations, structured errors written to
   stdout, commands never prompt.
7. **Ambient context** - installed into the agent's session/hooks via an explicit setup command.
8. **Content first** - a bare command with no arguments shows live, actionable data, not help
   text.
9. **Contextual disclosure** - `help[]` lines after output suggesting concrete next-step command
   templates.
10. **Consistent way to get help** - every subcommand offers `--help` as a fallback.

## Measured token efficiency beats the headline claim

Principle 1's '~40%' is an external claim. Measured against the payload shapes `venvaxi` actually
emits (`tests/test_toon_benchmark.py`, characters vs compact JSON):

| Payload shape             | Command                    | Saving |
| ------------------------- | -------------------------- | ------ |
| Wide table, short cells   | `venvaxi list`             | ~45%   |
| Table with quoted `::` names | `venvaxi find`          | ~27%   |
| Flat object, one large value | `venvaxi inspect <symbol>` | ~6% |

The saving comes from amortizing repeated JSON keys across a table header, so it scales with row
count and collapses on single-object output.

**MUST NOT cite ~40% as a general figure.** On the `inspect` path, token efficiency has to come
from truncation (principle 3), not from the encoding. When a change trades encoding cleverness
against truncation quality on a single-object payload, truncation wins.

## Report what a symbol is, not how to use it

Signatures, kinds, docstrings and inheritance edges are in scope. Tutorials, worked recipes,
usage narratives and migration guides are not.

The AXI's value is that it cannot drift from the installed version. The moment it starts
explaining *usage*, it is reproducing documentation it does not own and cannot verify - and it
inherits exactly the staleness problem it exists to solve. When a feature would require venvaxi
to explain intent rather than report structure, the answer is to point at documentation instead.

## The agent's spelling wins over the internally correct one

Where a symbol's facade path (how it is imported) and its home path (where it is defined)
disagree, output favours the facade - that is the spelling an agent scanned out of a codebase and
the one that will work in an import statement.

Resolution absorbs the difference internally rather than pushing it onto the caller. Concretely:
`find` ranking prefers short facade paths, and `get_symbol`/`show_module` answer with
facade-keyed data. See
[Qualified name semantics](behaviors/qualified-name-semantics.md) for the full invariant.

## STDOUT is the report, STDERR is the commentary

STDOUT carries structured TOON output and nothing else - including errors, which are emitted as
TOON error blocks rather than raised through a stderr traceback. Logging goes to STDERR.

An agent parses STDOUT. Anything unstructured that leaks into it corrupts the payload, so the
report/commentary split is absolute and applies even on the failure path.

## Zero runtime dependencies

`venvaxi` introspects a consuming project's venv from inside it. Every runtime dependency it adds
is a package that can collide with what it is measuring.

`project.dependencies` MUST stay empty. Optional extras (`mcp`) are permitted where the feature
is inert without them and the import is lazy. Prefer the standard library; where that is
impossible, prefer making the feature optional over making it required.
