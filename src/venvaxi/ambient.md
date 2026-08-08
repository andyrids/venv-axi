## VenvAXI

`venvaxi` introspects dependencies for a consuming project - querying exact signatures present in
that venv, at the exact versions pinned there.

You SHOULD prefer `venvaxi` over API recall from memory, which drifts from the installed
version, whereas the AXI cannot.

You MUST scan the codebase with your tools and use any findings to drive the AXI, when conducting
tasks.

### (1) Scan

Locate the import and call sites of the dependency symbol you are working on with your own tools.
This gives you a bare symbol name (`Console.print`) and its owning package (`rich`).

### (2) Resolve

`venvaxi find Console.print --package rich` converts the bare name into a qualified name
(`rich.console::Console.print`), indexing the package if needed.

### (3) Inspect

`venvaxi inspect rich.console::Console.print` returns the real signature and docstring for the
installed version.

## Guidance

Docstrings are truncated by default; add `--docstring` if needed. Add `--refresh` to rebuild a
stale graph after updating dependencies (`find` requires `--package` alongside `--refresh`).

`doc: (no docstring)` means the symbol defines none of its own - a definitive answer, not a
failure. Do not retry, and do not substitute a base class's documentation or your own recall.

VenvAXI reports what a symbol *is*, not how to use it - reach for documentation if needed.

Other commands:

- `venvaxi` - status & next-step hints
- `venvaxi list [--all]` - installed dependencies
- `venvaxi show <package> [--api]` - metadata|public API symbols
- `venvaxi tree <package> [--max-depth N]` - nested module tree
- `venvaxi inspect <module>` - direct children
- `venvaxi inherits <qualified_name>` - direct subclasses
- `venvaxi serve` - MCP (STDIO)
- `venvaxi setup` - register MCP config & refresh
