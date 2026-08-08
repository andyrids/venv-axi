"""Fixture leaf module (depth 3)."""


class Widget:
    """A deep-homed class surfaced via a shallow facade."""

    class Inner:
        """A nested class (recorded as an attribute member)."""

        def zoom(self) -> str:
            """Return a nested-class method result."""
            return "zoom"

    def poke(self) -> str:
        """Return a widget method result."""
        return "poked"


def ping() -> str:
    """Return a leaf-level function result."""
    return "pong"
