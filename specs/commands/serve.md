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

When the server starts, the `serve` command shall advertise the bound project root and venv in the
server's initialization instructions, so the binding is available without spending a tool call.

The obligation is to **advertise**, not to be read. Whether a client puts the instructions in front
of a model is the client's business and the MCP specification leaves it optional, so this clause is
satisfied by the string being served. That is also why it does not replace
[`describeBindingTool`](../mcp/tools.md#the-binding-report): the queryable surface is the half that
can be relied upon, and this is the half that costs nothing when it happens to work.

The instructions are computed once, at startup. Nothing in the server changes its working directory
afterwards, so the value they carry stays equal to what the tool resolves per call.

When the server shuts down cleanly, the `serve` command shall exit `EX_OK`.

## Failure modes

If the `mcp` extra is missing, then the `serve` command shall exit `EX_FAILURE` with a message
naming the extra (`venv-axi[mcp]`), since installing it is the only remedy.

The missing-extra case is reported by log line and exit code, not as a TOON error block, because
STDOUT is reserved for the protocol stream on this command. Exit statuses are the
[exit codes](../behaviors/output-contract.md#exit-codes) enum.

If no project root resolves when the instructions are built, then the `serve` command shall start
anyway, serve the full tool surface, and carry the same `(no project root)` marker
[`describeBindingTool`](../mcp/tools.md#failure-modes) reports.

Resolving the root is the one thing this command now does that can fail before the server exists,
and the case where it fails - an ephemeral or tool-venv registration - is exactly the
misconfiguration the binding report was added to expose. A server that refused to start there would
withhold the diagnosis at the only moment it is worth anything, and would present as a server that
will not connect rather than as a server bound to nothing.

## Out of scope

- **HTTP or SSE transport** - STDIO only. No future spec is planned; STDIO is what
  `venvaxi setup` registers and what agent harnesses spawn.

## Principles

**Inherited** - project principles that especially bite here:

- [Zero runtime dependencies](../principles.md#zero-runtime-dependencies) - the lazy import and
  the optional extra are this principle applied. `fastmcp` MUST NOT become a hard dependency to
  simplify this command.
