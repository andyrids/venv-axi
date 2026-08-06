"""Fixture submodule re-exporting a symbol via explicit `__all__`."""

from package.module import util

__all__ = ["util"]
