"""Fixture submodule re-exporting a symbol without `__all__`."""

from package.module import util


def local() -> str:
    """Return a locally defined symbol."""
    return util()
