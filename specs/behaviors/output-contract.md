---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Behavior: Output contract

## Rule

Every command writes TOON to STDOUT and nothing else. Logging goes to STDERR. Errors are TOON
blocks on STDOUT, not tracebacks on STDERR.

## Applies To

Every CLI command and every MCP tool.

## Details

### Stream discipline

- Structured output is written with `sys.stdout.write`, not `print`, so a console renderer can
  never line-wrap a TOON payload.
- Logging is configured to STDERR at `WARNING`, or `DEBUG` under `--verbose`.
- The TOON error block on STDOUT *is* the error report. It MUST NOT also be logged at error
  level, which would duplicate it on STDERR. The log line is `DEBUG`-only.

### Exit codes

| Code | Name         | Meaning                                              |
| ---- | ------------ | ---------------------------------------------------- |
| 0    | `EX_OK`      | Command completed, including definitive empty results |
| 1    | `EX_FAILURE` | A `venvaxi.exceptions.Error` was raised and reported  |
| 2    | `EX_SYNTAX`  | An unexpected (non-`Error`) exception escaped         |

An empty result is **success**. `count: 0` exits `0`, never `1`.

### Error shape

Any `venvaxi.exceptions.Error` is caught at the entry point and rendered as:

```text
error: true
message: <human-readable message>
help[1]:
  Run `venvaxi --help` for available commands
```

Unexpected exceptions render the same shape with an `Unexpected error:` prefix, are logged to
STDERR at `ERROR` level with the traceback attached (`logger.exception`), and exit `2`.

MCP tools mirror this exactly: `Error` is caught and returned as the same TOON block rather than
escaping into FastMCP's generic error path.

### Definitive empty states

A command with no results MUST emit an explicit zero marker plus a `help[]` line that names the
concrete next step likely to produce results. Silent blank output is forbidden.

- Collection commands emit `count: 0`.
- `inspect` on a module with no children emits the header object, then `children count: 0`.

`count: 0` is a definitive answer, not a failure - it means the query resolved and matched
nothing. An unresolvable name raises `SymbolNotFoundError` instead.

### Aggregates

Collection output is preceded by a `count:` line so the caller never has to count rows to decide
whether to page or refine.

### Truncation

Docstrings are reduced to a truncated first line by default. The limit is 200 characters, applied
at emission rather than storage, so the cached graph keeps complete docstrings.

Over-limit text gains a size hint naming the total length and the escape hatch:

```text
... truncated, 2847 chars total - use --docstring to see complete body
```

`--docstring` (CLI) / `docstring=true` (MCP) returns the complete body unchanged.

### Contextual disclosure

Output ends with a `help[N]:` footer of concrete, runnable next-step commands - not a static
usage summary. Hints are situational: the footer after a `find` names `inspect`, and the footer
after an empty `find` names the flag that would index the package.

`--docstring`-style hints are suppressed once the flag is already set, so a footer never suggests
what the caller just did.

### Non-interactive

Commands MUST NOT prompt. Mutations are idempotent.

## Principles

**Inherited** - project principles that especially bite here:

- [STDOUT is the report, STDERR is the commentary](../principles.md#stdout-is-the-report-stderr-is-the-commentary)
  - the reason errors are TOON on STDOUT rather than a stderr traceback.
- [Measured token efficiency beats the headline claim](../principles.md#measured-token-efficiency-beats-the-headline-claim)
  - on single-object payloads, efficiency comes from truncation, not the encoding.
