---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---

# Toolchain - `PyMarkdown`

PyMarkdown is used to implement Markdown linting standards.

## Commands

- `uv run pkgdx-markdown-hook <file>` - Lint a file
- `uv run prek run --all-files` - Run the `markdown` hook alongside all other hooks

## Configuration

The PyMarkdown config ships inside the installed `pkgdx` dev dependency
(`<site-packages>/pkgdx/standards/pymarkdown.toml`) and is applied by the `pkgdx-markdown-hook`
shim - prefer the hook over a hand-rolled `pymarkdown` invocation.
