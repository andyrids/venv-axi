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
- Logging shall be configured to STDERR at `WARNING`, or `DEBUG` under `--verbose`.
- The TOON error block on STDOUT *is* the error report. It shall not also be logged at error
  level, which would duplicate it on STDERR; the log line is `DEBUG`-only.

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

If a `venvaxi.exceptions.Error` is raised, then the entry point shall catch it and render:

```text
error: true
message: <human-readable message>
help[1]:
  Run `venvaxi --help` for available commands
```

If an unexpected exception escapes, then the entry point shall render the same shape with an
`Unexpected error:` prefix, log it to STDERR at `ERROR` level with the traceback attached
(`logger.exception`), and exit `2`.

MCP tools shall mirror this exactly: `Error` is caught and returned as the same TOON block rather
than escaping into FastMCP's generic error path.

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

- **Alternative encodings** - no `--json` or `--format` switch; TOON is the only encoding on
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
