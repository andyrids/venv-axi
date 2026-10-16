"""Fixture subpackage (depth 1)."""

# NOTE: `__all__` lists a module of each origin - `inner`, a submodule
# of this package; `codec`, a module from outside the package root; and
# `impl`, a public alias of the private `package._impl`. None is a
# symbol, so the walk records none as one, and `impl` - having no module
# node either - is absent from the graph
# (`specs/behaviors/symbol-graph.md`, Module bindings; #130).
import json as codec  # noqa: F401

from .. import _impl as impl  # noqa: F401
from . import inner  # noqa: F401

__all__ = ["codec", "impl", "inner"]

# NOTE: A public alias of a public submodule under a second name, kept
# out of `__all__` so no listing moves. A lookup of `subpkg.nested`
# misses - `inner` is recorded under its own name only - and the miss
# names `inner` as the module it is bound to (#142).
nested = inner
