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


class _Documented:
    """A package-defined singleton class (the `pytest.fail` shape)."""


# NOTE: `documented` defines no docstring of its own - `documented.__doc__`
# resolves to `_Documented.__doc__` via the type, and `_Documented` is not
# standard-library, so `_doc_of` keeps it (#82).
documented = _Documented()

# NOTE: The `version_tuple`/`NewType` shape - `tuple` is standard-library,
# so `_doc_of` blanks the docstring rather than reporting *Built-in
# immutable sequence* (#82).
VERSION_TUPLE: tuple[int, int, int] = (1, 0, 0)
