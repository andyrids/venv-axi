"""A package fixture submodule raising a `BaseException` on import.

NOTE: The #64 specimen - `numpy.f2py` raises `_pytest.outcomes.Skipped`,
a `BaseException` that is not an `Exception`, at import time.
"""


class ImportCrash(BaseException):
    """A `BaseException` subclass that is not an `Exception`."""


raise ImportCrash("Error")
