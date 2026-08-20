---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [command, serve, mcp]
---

# Command: venvaxi serve

## Invocation / inputs

```text
venvaxi serve
python -P -m venvaxi serve
```

No arguments. Runs a dedicated AXI MCP server over STDIO.

The two spellings are the same entry point, and the `serve` command shall serve an identical tool
surface under either. The module form is what [`setup`](setup.md) registers, and `-P` is what makes
the two equivalent - without it the module form additionally imports from the working directory.
The equivalence is declared here because it is what makes that registration sound rather than a
private detail of the installer.

## Data requirements

Requires the `venv-axi[mcp]` extra (`fastmcp>=0.1.0`).

The `serve` command shall check the extra's availability **up front**, before the server is
constructed. This is not defensive padding - it is what keeps a genuine `ImportError` raised
mid-serve propagating as an unexpected error, instead of being misreported as a missing extra.

`fastmcp` is imported lazily inside the handler, never at module scope, so the rest of the CLI
works without the extra installed.

## Outputs

While the server is running, STDIO shall belong to the MCP protocol for the lifetime of the
process. The TOON output contract does not apply to the served stream.

The server shall be named `VenvAXI` and expose the tools in [MCP tools](../mcp/tools.md).

When the server shuts down cleanly, the `serve` command shall exit `EX_OK`.

## Failure modes

If the `mcp` extra is missing, then the `serve` command shall exit `EX_FAILURE` with a message
naming the extra (`venv-axi[mcp]`), since installing it is the only remedy.

The missing-extra case is reported by log line and exit code, not as a TOON error block, because
STDOUT is reserved for the protocol stream on this command. Exit statuses are the
[exit codes](../behaviors/output-contract.md#exit-codes) enum.

## Out of scope

- **HTTP or SSE transport** - STDIO only. No future spec is planned; STDIO is what
  `venvaxi setup` registers and what agent harnesses spawn.

## Principles

**Inherited** - project principles that especially bite here:

- [Zero runtime dependencies](../principles.md#zero-runtime-dependencies) - the lazy import and
  the optional extra are this principle applied. `fastmcp` MUST NOT become a hard dependency to
  simplify this command.
