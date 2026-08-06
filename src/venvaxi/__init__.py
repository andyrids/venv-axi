"""Agent eXperience Interface (AXI) CLI init.

Provides package metadata and public API introspection for packages installed
in the venv of a consuming repo. Output uses Token-Oriented Object Notation
(TOON) format, which is a token-efficient, human-readable, and
machine-parseable format for structured data.

TOON Documentation: https://toonformat.dev/
AXI Documentation: https://axi.md/
"""

import contextlib
from importlib import metadata
from pathlib import Path

from venvaxi import exceptions
from venvaxi._logging import configure_pkg_logging

__all__: list[str] = ["exceptions"]

VENVAXI_ROOT: Path = Path(__file__).parent

configure_pkg_logging()

with contextlib.suppress(metadata.PackageNotFoundError):
    __version__: str = metadata.version("venv-axi")
