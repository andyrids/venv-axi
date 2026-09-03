---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
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

Each carries its own heading so a spec can cite the principle it means. The wording below is the
cited source's; the headings are this project's, added so that a reference resolves to the
principle rather than to the list containing it.

### Principle 1, token-efficient output

Use TOON format for token savings over JSON.

### Principle 2, minimal default schemas

Return 3-4 fields per list item by default, not 10+.

### Principle 3, content truncation

Truncate large text fields with a size-hint suffix (e.g. `truncated, 2847 chars total`).

### Principle 4, pre-computed aggregates

Include derived fields (e.g. `count`) that eliminate round trips.

### Principle 5, definitive empty states

An explicit zero-result message on empty output, never silent blank output.

### Principle 6, structured errors and exit codes

Idempotent mutations, structured errors written to stdout, commands never prompt.

### Principle 7, ambient context

Installed into the agent's session/hooks via an explicit setup command.

### Principle 8, content first

A bare command with no arguments shows live, actionable data, not help text.

### Principle 9, contextual disclosure

`help[]` lines after output suggesting concrete next-step command templates.

### Principle 10, consistent way to get help

Every subcommand offers `--help` as a fallback.

## Measured token efficiency beats the headline claim

Principle 1's '~40%' is an external claim. Measured against the payload shapes `venvaxi` actually
emits (`tests/test_toon_benchmark.py`, characters vs compact JSON):

| Payload shape                | Command                    | Saving    |
| ---------------------------- | -------------------------- | --------- |
| Wide table, short cells      | `venvaxi list`             | ~45%      |
| Table with quoted `::` names | `venvaxi find`             | ~27%      |
| Flat object, any docstring   | `venvaxi inspect <symbol>` | ~10 chars |

The third column mixes units deliberately. A table's saving is a percentage because it scales with
the payload; an object's is a character count because it does not, and forcing the second into the
first is what let one figure stand for a whole command
([#98](https://github.com/andyrids/venv-axi/issues/98)).

The table saving comes from amortizing repeated JSON keys across a header, so it scales with row
count and collapses on single-object output.

On a flat object there is no header to amortize, and what remains does not depend on the values at
all. For the four fields symbol mode emits it is 14 characters, minus 2 for every value that takes
TOON's quoting branch - the braces, quoted keys and commas JSON spends, against the colon, space
and newline TOON spends - so a real symbol lands between 6 and 12, with ~10 the common case where
`qualified_name` and `signature` are quoted and `doc` is not. It is the same count whether `doc`
holds 20 characters or 10,000. Newlines cost nothing either way: JSON escapes `\n` to the same two
characters TOON does, so a multi-paragraph docstring encodes no worse than a single line.

As a *share* of the payload it is therefore whatever payload size makes it, and `--docstring` is
not the variable - symbol size is. `os.path::join` saves ~11% on the default path;
`rich.console::Console.print` saves ~1.5% on that same path and ~0.4% under `--docstring`; and
`os::getcwd` saves ~8% under `--docstring`, so a small symbol's complete docstring saves a larger
share than a large symbol's truncated one. Those are worked examples of one invariant, not four
figures to cite.

Every figure in the table above MUST be reproducible from a named fixture in
`tests/test_toon_benchmark.py`. A row no fixture measures is the defect this table already carried
once, and a character count is strictly easier to hold than a band.

**MUST NOT cite ~40% as a general figure.** On the `inspect` path the encoder's saving does not
scale with content, so truncation (principle 3) is the only lever that does. When a change trades
encoding cleverness against truncation quality on a single-object payload, truncation wins.

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
