"""Fixture private submodule whose classes surface via a facade."""


class Client:
    """A client implemented in a private module."""

    def connect(self) -> str:
        """Connect the client."""
        return "connected"


class Base:
    """A base class implemented in a private module."""


class Sub(Base):
    """A subclass implemented in a private module."""
