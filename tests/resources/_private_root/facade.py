"""Fixture facade below an underscore-rooted package, no `__all__`.

NOTE: The two re-exports differ only in whether the home is private.
`Carved` is kept by the private-home carve-out; `Exposed` is dropped by
the below-the-root rule, which an inline `any(...)` over every segment
of the home name got wrong for an underscore-rooted package because the
root segment satisfied it (`specs/behaviors/symbol-graph.md`,
Re-exported symbols; #106).
"""

from _private_root._impl import Carved  # noqa: F401
from _private_root.public import Exposed  # noqa: F401
