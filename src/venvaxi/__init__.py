"""Agent eXperience Interface (AXI) CLI init.

Provides package metadata and public API introspection for packages installed
in the venv of a consuming repo. Output uses Token-Oriented Object Notation
(TOON) format, which is a token-efficient, human-readable, and
machine-parseable format for structured data.

TOON Documentation: https://toonformat.dev/
AXI Documentation: https://axi.md/
"""

from importlib import metadata
from pathlib import Path

from venvaxi import exceptions
from venvaxi._logging import configure_pkg_logging

__all__: list[str] = ["exceptions", "__version__"]

VENVAXI_ROOT: Path = Path(__file__).parent

configure_pkg_logging()

# NOTE: Unconditionally bound - so both the CLI `--version` action and
# `describe_binding_tool` can read it directly, from an installed or an
# uninstalled source tree alike.
try:
    __version__: str = metadata.version("venv-axi")
except metadata.PackageNotFoundError:
    __version__ = ""
