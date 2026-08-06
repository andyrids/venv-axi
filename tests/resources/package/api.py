"""Fixture facade re-exporting from a private module, no `__all__`."""

from package._impl import Base, Client, Sub  # noqa: F401
