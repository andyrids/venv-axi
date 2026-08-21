"""Fixture submodule holding instance constants without `__all__`."""

import re

PATTERN = re.compile("x")
MAX_RETRIES = 5


class _Caller:
    """A class whose instances are callable with a clean signature."""

    def __call__(self, column: str, *, strict: bool = True) -> str:
        """Return the column name."""
        return column


class _Opaque:
    """A callable whose `__signature__` access raises (`pl.col`-like)."""

    def __call__(self) -> None:
        """Do nothing."""

    @property
    def __signature__(self) -> None:
        """Raise, like an exotic callable's signature descriptor."""
        msg = "no signature"
        raise TypeError(msg)


col = _Caller()
opaque = _Opaque()
