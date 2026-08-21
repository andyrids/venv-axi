---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [behavior, output, TOON]
---

# Behavior: Output contract

## Rule

Every command writes TOON to STDOUT and nothing else. Logging goes to STDERR. Errors are TOON
blocks on STDOUT, not tracebacks on STDERR.

## Applies to

Every CLI command and every MCP tool.

## Details

### Stream discipline

- Structured output shall be written with `sys.stdout.write`, not `print`, so a console renderer
  can never line-wrap a TOON payload.
- Structured output shall be written as UTF-8, whatever character encoding the ambient console
  or pipe reports. Introspected docstrings carry whatever their authors wrote - rendered example
  tables, typographic punctuation, mathematical symbols - so the payload's character set is the
  dependency's business, and the ambient encoding of a captured pipe is an accident of the
  caller's shell rather than a fact about the payload.
- If a payload contains a character the ambient stream encoding cannot represent, then the
  command shall emit the payload in full and exit on its own merits, never exit `EX_SYNTAX`
  because of the encoding.
- Logging shall be configured to STDERR at `WARNING`, or `DEBUG` under `--verbose`.
- The TOON error block on STDOUT *is* the error report. It shall not also be logged at error
  level, which would duplicate it on STDERR; the log line is `DEBUG`-only.

STDERR is held to the same rule. Import warnings name third-party modules and quote their
exception text, so the commentary stream carries foreign characters for the same reason the
report does.

### Exit codes

| Code | Name         | Meaning                                              |
| ---- | ------------ | ---------------------------------------------------- |
| 0    | `EX_OK`      | Command completed, including definitive empty results |
| 1    | `EX_FAILURE` | A `venvaxi.exceptions.Error` was raised and reported  |
| 2    | `EX_SYNTAX`  | An unexpected (non-`Error`) exception escaped         |

An empty result is **success**. `count: 0` exits `0`, never `1`.

If a user-supplied argument *value* cannot be honoured, then the command shall raise an `Error`
and exit `1`, never `2`. Exit 2 is reserved for venvaxi being broken, so a caller can treat it as
a bug report rather than a prompt to retype - see
[Package resolution](package-resolution.md). Argparse rejecting an unknown flag or a missing
positional is a separate, earlier failure and keeps argparse's own exit status.

### Error shape

If a `venvaxi.exceptions.Error` is raised, then the entry point shall catch it and render the
TOON error object:

```text
error: true
message: <human-readable message>
```

On the CLI, the error object shall be followed by the generic footer:

```text
help[1]:
  Run `venvaxi --help` for available commands
```

If an unexpected exception escapes - any `BaseException` other than `KeyboardInterrupt` and
`SystemExit`, not merely any `Exception` - then the entry point shall render the same shape with
an `Unexpected error:` prefix, log it to STDERR at `ERROR` level with the traceback attached
(`logger.exception`), and exit `2`. `KeyboardInterrupt` and `SystemExit` shall be re-raised
unrendered: the first is the caller aborting, the second is venvaxi itself exiting, and neither
is a report about the venv. A catch narrowed to `Exception` renders venvaxi's own promise
conditional on what a dependency chooses to raise - see
[Import boundaries](#import-boundaries) for why that choice is not venvaxi's to constrain.

MCP tools shall mirror the error object and the catch discipline - `Error` is caught and
returned as the same TOON block rather than escaping into FastMCP's generic error path - and
shall never carry the CLI footer. That footer names a shell command a tool-calling agent cannot
run, and `venvaxi --help` has no tool-surface equivalent: a connected agent already holds the
tool list, so a generic substitute would be a manufactured step, which
[contextual disclosure](#contextual-disclosure) below forbids. An MCP tool error carries an
error-specific hint where a genuine next step exists, phrased per the
[MCP hint wording rule](../mcp/tools.md#hint-wording); if none exists, then the `help[N]:`
footer shall be omitted entirely rather than emitted empty, per the same suppression rule. The
`Unexpected error:` shape takes the identical per-surface footer - an unexpected error has no
next step to name, so over MCP it carries no footer at all.

### Import boundaries

Importing a third-party module runs arbitrary module-level code, which can raise anything -
including `BaseException` subclasses that are not `Exception`s (`_pytest.outcomes.Skipped`, a
module-level `sys.exit(...)`). A guard that catches `Exception` lets exactly those escape, and
what escapes a walk takes the whole command down - or, over MCP, the connection.

- An import boundary shall guard against `BaseException`, not `Exception`. What a dependency
  raises at import time is a fact about that dependency, never a venvaxi control-flow signal.
- If a submodule raises anything other than `KeyboardInterrupt` at import time during a walk,
  then the walk shall skip that submodule, log the warning to STDERR, and continue - one bad
  submodule must not abort the walk.
- If the requested package itself raises anything other than `KeyboardInterrupt` at import
  time, then the command shall report it as broken - `PackageImportError`, per
  [Package resolution](package-resolution.md) - and exit `EX_FAILURE`, never `EX_SYNTAX`.
- If a third-party module raises `SystemExit` at import time, then the import boundary shall
  contain it like any other import failure, never treat it as venvaxi exiting. The only
  `SystemExit` that means venvaxi is exiting is one raised by venvaxi's own entry point.
- If `KeyboardInterrupt` is raised at any level, then it shall propagate to the caller - a
  long walk must stay abortable, and an import guard is not a place to swallow the abort.
- If a graph build is aborted by an escaping exception, then the command shall release the
  cache database before propagating it. A crash that leaves the database open converts one
  broken import into a locked cache for every later command on platforms that lock open files.

### Definitive empty states

When a command has no results, it shall emit an explicit zero marker plus a `help[]` line naming
the concrete next step likely to produce results. Silent blank output is forbidden.

- Collection commands shall emit `count: 0`.
- When a module has no children, `inspect` shall emit the header object, then
  `children count: 0`.
- If a symbol defines no docstring of its own, then it shall be reported as
  `doc: (no docstring)`.

`count: 0` is a definitive answer, not a failure - it means the query resolved and matched
nothing. An unresolvable name raises `SymbolNotFoundError` instead.

The same reasoning governs scalar fields, which is why an absent docstring is a marker rather
than `""`. A bare empty string is the silent blank this rule forbids: an agent cannot tell
'defines none' from 'something went wrong', and the plausible recovery - retry, or fall back to
recalled documentation - is exactly the drift the AXI exists to prevent.

`(no docstring)` states a different fact from `(signature unavailable)`. The signature marker
means introspection failed; the docstring marker means the symbol genuinely defines none. Both
are chosen to be distinct from any real value and to contain no TOON structural characters.

Markers shall be applied at **emission**, never recorded. Storing one would put its literal text
into the searchable index, so a `find` for its wording would match every symbol carrying it.

`(signature unavailable)` is the deliberate exception, and [inspect](../commands/inspect.md)
declares it: the marker records a fact about introspection that is discoverable only at build
time, while the live object is in hand, so emission cannot recompute it. Search reads names and
docstring text, never signatures, so the recorded marker stays out of `find`'s reach and the
rationale above is untouched.

### Aggregates

Collection output shall be preceded by a `count:` line, so the caller never has to count rows to
decide whether to page or refine.

### Truncation

Docstrings shall be reduced to a truncated first line by default. The limit is 200 characters,
applied at emission rather than storage, so the cached graph keeps complete docstrings.

When text exceeds the limit, it shall gain a size hint naming the total length and the escape
hatch.

The escape hatch shall be named in the **spelling of the surface the caller is on** - the CLI flag
on the CLI, the tool parameter over MCP:

```text
... truncated, 2847 chars total - use --docstring to see complete body
... truncated, 2847 chars total - re-call with docstring=true for the complete body
```

The suffix travels inside the payload, so a single hardcoded spelling reaches both surfaces and
teaches one of them an invocation it cannot make. This is the same failure the
[MCP hint wording rule](../mcp/tools.md#hint-wording) forbids in footers, arriving through the
truncation path instead - the rule is about what the caller is told, not about which function
emits it.

Where `--docstring` (CLI) / `docstring=true` (MCP) is set, the complete body shall be returned
unchanged.

### Contextual disclosure

Output shall end with a `help[N]:` footer of concrete, runnable next-step commands - not a static
usage summary. Hints are situational: the footer after a `find` names `inspect`, and the footer
after an empty `find` names the flag that would index the package.

Where a flag is already set, its `--docstring`-style hint shall be suppressed, so a footer never
suggests what the caller just did. If suppression leaves no hint to emit, then the `help[N]:`
footer shall be omitted entirely rather than emitted empty - an empty footer is the silent blank
the definitive-empty-states rule above forbids, wearing a structural key.

A suppressed hint shall not be replaced by an unrelated one to keep the footer populated. The
footer exists to name the next step, and manufacturing a step so the shape stays constant is how
two surfaces over one graph end up disagreeing about what the caller should do next.

### Non-interactive

A command shall never prompt. Mutations shall be idempotent.

## Out of scope

- **Alternative payload formats** - no `--json` or `--format` switch; TOON is the only encoding on
  every surface. Never - the encoding is the token-efficiency contract, and a second format
  would fork every downstream parser.
- **Console styling** - no colour, no wrapping, no human-oriented tables. Never - the consumer
  is an agent parsing STDOUT, and styling is exactly the unstructured leak the Rule forbids.

## Principles

**Inherited** - project principles that especially bite here:

- [STDOUT is the report, STDERR is the commentary](../principles.md#stdout-is-the-report-stderr-is-the-commentary)
  - the reason errors are TOON on STDOUT rather than a stderr traceback.
- [Measured token efficiency beats the headline claim](../principles.md#measured-token-efficiency-beats-the-headline-claim)
  - on single-object payloads, efficiency comes from truncation, not the encoding.
