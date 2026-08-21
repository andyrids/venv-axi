---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [pymarkdown]
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

A bare `uv run pymarkdown scan <file>` uses PyMarkdown's own defaults (80 characters, setext
headings), not the project's, so its output is misleading - it reports violations the hook does
not raise.

## Gotcha - `BadTokenizationError`

A pipe character inside a **nested** list item crashes the tokenizer:

```markdown
- User review & acceptance MUST be explicit before continuation:
  - "approved" | "continue" - proceed as presented
```

```text
Check Markdown [PyMarkdown]..............................................Failed
  Unexpected Error(BadTokenizationError): An unhandled error occurred
  processing the document.
```

The same pipe at the top level of a list is fine. Nesting depth alone does not predict it -
existing three-level items carrying pipes survive, so the trigger is narrower than 'pipes when
nested'.

**The diagnostic names no file, line or rule**, which is what makes this expensive. Bisect by
file first:

```sh
for f in <changed files>; do
  echo "$f" $(uv run -m prek run pkgdx-markdown --files "$f" 2>&1 \
    | grep -c BadTokenization)
done
```

Then bisect within the file by rewriting one block at a time. The fix is to drop the pipes -
write 'or' - rather than to restructure the list, since restructuring does not reliably help.

This is worth writing down precisely because the tool gives no signal. Contrast Ruff, which names
the rule and prints the remedy; a reference entry duplicating *that* would rot while the tool
stays right.
