"""Fixture submodule re-exporting a symbol without `__all__`."""

# NOTE: `OrderedDict` is homed outside the walked package root, so the
# below-the-root rule drops it (`specs/behaviors/symbol-graph.md`,
# Re-exported symbols, second `If/then` bullet's converse; #106).
from collections import OrderedDict  # noqa: F401

from package.module import util


def local() -> str:
    """Return a locally defined symbol."""
    return util()
