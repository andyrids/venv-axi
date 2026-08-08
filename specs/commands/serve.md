---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Command: venvaxi serve

## Invocation

```text
venvaxi serve
```

No arguments. Runs a dedicated AXI MCP server over STDIO.

## Data Requirements

Requires the `venv-axi[mcp]` extra (`fastmcp>=0.1.0`).

Availability MUST be checked **up front**, before the server is constructed. This is not defensive
padding - it is what keeps a genuine `ImportError` raised mid-serve propagating as an unexpected
error, instead of being misreported as a missing extra.

`fastmcp` is imported lazily inside the handler, never at module scope, so the rest of the CLI
works without the extra installed.

## Output Rules

On success, STDIO belongs to the MCP protocol for the lifetime of the process. The TOON output
contract does not apply to the served stream.

The server is named `VenvAXI` and exposes the tools in [MCP tools](../mcp/tools.md).

## Exit Codes

- `EX_OK` on clean shutdown.
- `EX_FAILURE` when the `mcp` extra is missing. The message MUST name the extra
  (`venv-axi[mcp]`), since installing it is the only remedy.

## Errors

The missing-extra case is reported by log line and exit code, not as a TOON error block, because
STDOUT is reserved for the protocol stream on this command.

## Principles

**Inherited** - project principles that especially bite here:

- [Zero runtime dependencies](../principles.md#zero-runtime-dependencies) - the lazy import and
  the optional extra are this principle applied. `fastmcp` MUST NOT become a hard dependency to
  simplify this command.
