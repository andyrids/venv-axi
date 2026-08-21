---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [docstrings]
---

# Standard - docstrings

Docstrings follow the Google style guide and PEP 257 guidelines.

## (1) Module-level docstrings

- MUST follow existing codebase style
- MUST include a summary line
- MUST include License section
- SHOULD have a summary line with enough information to understand the module purpose
- COULD add extra detail seperated from the summary by a blank line

```python
"""A one-line summary of the module or program, terminated by a period.

Leave one blank line. The rest of this docstring should contain an
overall description of the module or program.

License:
    SPDX-License-Identifier: Apache-2.0
"""
```

## (2) Functions and methods

- MUST follow existing codebase style
- MUST use the imperative-style in the summary line
- MUST include Args section
- MUST include Returns (or Yields for generators) section
- MUST include Raises section (if relevant)
- SHOULD have a summary line with enough information to call a function without reading the code
- COULD add extra detail seperated from the summary by a blank line
- COULD provide example usage or detail where needed

```python
def format_help(lines: Sequence[str]) -> str:
    """Format the contextual-disclosure `help[]` footer.

    NOTE: AXI principle 9 (contextual disclosure, see `specs/principles.md`):
    concrete next-step commands are surfaced instead of a static usage
    summary.

    Args:
        lines: Concrete next-step command suggestions.

    Returns:
        A `help[N]:` block, with indented lines for each suggestion.

        ```
        help[2]:
            Run `venvaxi list` for the venv package list
            Run `venvaxi show <package>` for package info
        ```
    """
    body = "\n".join(f"  {line}" for line in lines)
    return f"help[{len(lines)}]:\n{body}"
```

## (3) Classes

- MUST follow existing codebase style
- MUST have a summary line that describes what the class instance represents
- SHOULD include Attributes section for public attributes (excluding properties)
