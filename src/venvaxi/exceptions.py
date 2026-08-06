"""Custom exceptions for `venvaxi`.

NOTE: Every `venvaxi` error is surfaced as a TOON error block on STDOUT,
so a single `Error` base carries the whole contract.
"""


class Error(Exception):
    """Base-class for all exceptions raised by `venvaxi`."""


class ProjectRootNotFoundError(Error):
    """Raised when the project root cannot be determined."""


class InvalidArgumentError(Error):
    """Raised on an invalid CLI/tool argument value."""


class PackageNotFoundError(Error):
    """Raised when a requested package is not installed in the venv."""


class PackageImportError(Error):
    """Raised when a package cannot be imported for API introspection."""


class AmbientContextError(Error):
    """Raised when `venvaxi` ambient context cannot be installed."""


class SymbolNotFoundError(Error):
    """Raised when a qualified symbol name cannot be found in the store."""


class StoreError(Error):
    """Raised on `SymbolStore`-level failures."""
