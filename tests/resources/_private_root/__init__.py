"""Fixture package whose own root name starts with `_`.

NOTE: The root name is the entire point. `is_private_submodule` excludes
the root segment deliberately, so this package is walked in full when
named as the query root (`specs/behaviors/symbol-graph.md`, Private
submodules) while the below-the-root re-export rule applies to its
submodules exactly as it does for a public root (#106).
"""
