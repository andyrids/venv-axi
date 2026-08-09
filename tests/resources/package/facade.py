"""Fixture submodule re-exporting a symbol via explicit `__all__`."""

from package.module import util
from package.subpkg.inner.leaf import Widget

__all__ = ["Widget", "util"]
