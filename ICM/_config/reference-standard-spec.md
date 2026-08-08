---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---

# Standard - specifications

How to write a file in `specs/`. The tree layout and the invariants it holds are in
`specs/README.md`; this file is the authoring bar and the templates.

## The right level of detail

Specs declare **what** MUST be true, not **how** to implement it.

- **Too vague** - 'The find command searches symbols and returns useful results.' An implementer
  still has to make a hundred decisions. Which fields? What ordering? What happens on no match?
- **Right** - 'Emit `count: <n>` and a `symbols` table of `name`, `kind`, `qualified_name`.
  Ranking prefers short facade paths. On no match with `--package` set, hint at `list --all`; on
  no match without it, hint at `--package`.' Testable by running the command.
- **Too detailed** - 'Call `find_symbol(query, limit, package)`, build rows via `node.as_row()`,
  pass to `encode_table` with fields `[...]`.' This is writing the code twice, and it rots on the
  first refactor.

The test: could two implementers read it and disagree about whether the code conforms? If yes, it
is too vague to be a spec.

## Rules

- MUST state behaviour observable from outside `src/venvaxi/` - invocation, output, exit codes,
  errors
- MUST NOT name functions, variables or module paths as requirements; those change freely
- MUST NOT restate `--help` output as prose. `venvaxi <cmd> --help` is authoritative; a spec that
  disagrees with it is the thing that is wrong
- SHOULD explain *why* a non-obvious rule exists, in one line. A rule whose reason is lost gets
  'simplified' away by the next implementer
- SHOULD NOT duplicate a behaviour spec into a command spec - link to it

## Principles

A principle is a generative rule that resolves the cases enumeration never reaches. It earns its
place only if it is **decisive**: it picks a side of a real trade-off and rules something out.

- **Not a principle** - 'Output should be clean and agent-friendly.' Rules nothing out.
- **A principle** - 'On single-object payloads, efficiency comes from truncation, not the
  encoding; MUST NOT relax the truncation default to compensate.' An implementer can act on it.

`ICM/_config/reference-standard-yagni.md` is the in-repo worked example - every line picks a
side.

### Placement

Default to **the most specific spec the principle governs**. A principle shaping one command
belongs in that command spec's `## Principles` section, next to the rules it backs, where an
implementer reading only that file will see it.

Reserve `specs/principles.md` for genuinely project-wide rules. The trigger to promote is
**the same or a similar principle appearing in a second spec** - that duplication means it has
outgrown any one file. Lift it once, then replace both copies with references, rather than
letting two near-identical statements drift apart.

Do not agonize at capture time. Put it on the spec you are in; promote later if it spreads.

### Referencing back down

Promotion sends principles up; this is the flow back down. An agent working from one command spec
will not open `specs/principles.md` on its own, so a project-wide principle quietly governing
that command is invisible.

In a spec's `## Principles` section, name the `principles.md` entries that **especially bite
here**, each with a one-line gloss of how it applies, linked to the full statement. Be selective:
a spec that links every principle teaches nothing.

Use the two-part shape - **Inherited** for linked `principles.md` entries, **Local** for
principles this spec owns. Omit either subsection if empty.

## Templates

### Command spec

```markdown
# Command: venvaxi <verb>

## Invocation
Positional arguments and flags, with defaults, as a table.

## Data requirements
What the command reads - installed metadata, the symbol store, live introspection.

## Output rules
Declarative description of the TOON payload: fields emitted by default, truncation,
the definitive empty state and its hint, the `help[]` footer.

## Exit codes
Which `ExitCode` under which condition.

## Errors
Which `venvaxi.exceptions` surface, and what the caller sees.

## Principles (optional)
**Inherited** - `principles.md` entries that bite here, one-line gloss each.
**Local** - principles owned by this command.
```

### Behavior spec

```markdown
# Behavior: <name>

## Rule
The invariant, stated declaratively.

## Applies to
Which commands, tools or modules this governs.

## Details
Edge cases, calculations, ordering, failure handling.

## Principles (optional)
Same two-part shape as above.
```

### Principle entry

```markdown
## <Short, stable heading>
The rule, stated so it rules something out. Include the *why* - the context
that makes the trade-off land - so a future reader applies it correctly
rather than literally.
```

The heading is the anchor other specs link to (`principles.md#<name>`). Keep it stable; changing
it breaks every inbound reference.

## Watch for specs mid-task

This is standing, not a stage. While implementing, debugging or reviewing, watch for the moment a
decision gets resolved that would change how a *future* implementer decides something:

- The user explains *why* they want something a certain way
- A trade-off is settled in conversation ('always favour X over Y')
- An unspecified case is hit, an answer picked, and that answer implies a general rule
- A 'we'll always' or 'we'll never' sentiment surfaces
- The same principle turns up in a second spec - the loudest promotion signal there is

When noticed, **stop and surface it**: name the decision, say whether it reads as an enumerated
rule or a principle, and propose where it belongs.

The bar: if it would only ever have affected that one line, let it go. If it would change a
future decision, it belongs in a spec.

A decision that lives only in code, a commit message or a chat scrollback is unspecified
behaviour the moment the context window closes - and the next agent will re-litigate it,
possibly differently.
