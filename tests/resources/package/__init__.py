"""Fixture package."""

# NOTE: A re-export at depth 0 from a *public* sibling. The root
# exemption keeps it (`specs/behaviors/symbol-graph.md`, Re-exported
# symbols); a public sibling is required so the case discriminates the
# root exemption from the private-home carve-out (#106). The import is
# relative because `tests/conftest.py` imports this package as
# `tests.resources.package` before copying it, where an absolute
# `package.module` does not resolve; under the walk it binds
# `package.module` either way.
from .module import render_grid  # noqa: F401


class Animal:
    """An animal."""

    def speak(self) -> str:
        """Make a sound."""
        return "..."


class Cat(Animal):
    """A cat."""

    def speak(self) -> str:
        """Meow."""
        return "MEOW!"


class Dog(Animal):
    """A dog."""

    def speak(self) -> str:
        """Bark."""
        return "WOOF!"
