---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---

# Attribution

When blending direct code snippets with architectural concepts, open-source etiquette mandates
both legal compliance and community gratitude.

Assuming permissive licenses such as MIT and Apache 2.0, there are three ways attribution can be
implemented, which are detailed below.

## (1) Module-Level Docstrings

When a whole file or core concept is adapted, include a clear `Attribution` in the module
docstring.

Example `src/venvaxi/_constants.py` (direct code porting):

```python
"""Constants for the Token-Orientated Object Notation (TOON) encoder.

Attribution:
    The regex patterns, structural tokens and constant-extraction patterns in
    this file are directly adapted from the official `toon-python` reference
    implementation.

    Repository: https://github.com/toon-format/toon-python
    License: MIT License - Copyright (c) 2025 TOON Format Organization
"""
```

Example `src/venvaxi/_store.py` and `src/venvaxi/_introspect.py` (architectural inspiration):

```python
"""Graph-Based Symbol Registry for venvaxi.

Attribution:
    The SQLite node/edge graph architecture and recursive AST walking patterns
    used in this module are heavily inspired by `code-review-graph`.

    Repository: https://github.com/tirth8205/code-review-graph
    License: MIT License - Copyright (c) 2026 Tirth Kanani
"""
```

## (2) Inline Comments (For Specific Functions)

If a new function is written, but the logic or algorithm is pulled directly from the other
projects, a comment above the function can be added.

## (3) Preserving Copyright Notices

A copy-paste of substantial chunks of actual source code results in adherence to permissive
licenses like MIT and Apache, which require you to preserve their copyright notice.

1. Pasting their short copyright header directly above the copied function/class in files.
2. Creating a `CREDITS.md` file in the project root:
   - Include full license text all projects
   - State which files use them

## (4) README Acknowledgements

Add an `Acknowledgements` section to the project `README`.
