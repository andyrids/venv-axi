"""Unit tests for `venvaxi.__init__` - the package-level `__version__` binding.

The CLI `--version` action and `describeBindingTool` tests (`test_cli.py`,
`test_mcp.py`) mock `venvaxi.__version__` directly to prove each surface's
*emission site* renders the `(no version metadata)` marker on a falsy value.
Neither proves `__version__` itself actually becomes `""` when distribution
metadata is unavailable - the root cause the edge case was raised for. This
module closes that gap by forcing `importlib.metadata.version` to raise
`PackageNotFoundError` and reloading the real module, so the `except` arm in
`src/venvaxi/__init__.py` runs for real.
"""

import importlib
from importlib import metadata
from unittest import mock

import venvaxi


def test_version_binds_empty_string_when_metadata_unavailable() -> None:
    """`__version__` binds to `""`, not undefined, when
    `importlib.metadata.version` raises `PackageNotFoundError` - the
    fallback binding itself, not just the marker rendered from it."""
    try:
        with mock.patch.object(
            metadata, "version", side_effect=metadata.PackageNotFoundError
        ):
            importlib.reload(venvaxi)
            assert venvaxi.__version__ == ""
    finally:
        # Restore unconditionally - a failed assertion above must not
        # leave every later test in this session importing a
        # `venvaxi` module with `__version__` still bound to `""`.
        importlib.reload(venvaxi)
