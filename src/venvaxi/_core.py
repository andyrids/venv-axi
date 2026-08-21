"""Core CLI state and project-root resolution for `venvaxi`."""

import argparse
import dataclasses
import logging
import sys
from itertools import chain
from pathlib import Path

from venvaxi import exceptions
from venvaxi._constants import NO_PROJECT_ROOT

logger = logging.getLogger(__package__)


class ExitCode:
    """Exit codes for the CLI commands."""

    EX_OK = 0
    EX_FAILURE = 1
    EX_SYNTAX = 2


@dataclasses.dataclass(frozen=True, slots=True)
class CLIContext:
    """Centralised state for the CLI commands.

    NOTE: Commands write raw TOON to `sys.stdout`, so there is no
    console abstraction to carry here.
    """

    args: argparse.Namespace
    is_verbose: bool = False


def get_project_root() -> Path:
    """Get the root path of the consuming repo.

    Returns:
        The root path of the consuming repo.
    """
    cwd = Path.cwd().resolve()
    for directory in chain([cwd], cwd.parents):
        if (directory / "pyproject.toml").exists():
            return directory

    venv_parent = Path(sys.prefix).parent
    if (venv_parent / "pyproject.toml").exists():
        return venv_parent

    msg = f"Cannot identify project root:- `{sys.prefix=}` | `{cwd=}`."
    raise exceptions.ProjectRootNotFoundError(msg)


def format_path(path: Path) -> str:
    """Format a path relative to $HOME.

    Args:
        path: The absolute path to format.

    Returns:
        A `~/`-prefixed path when under the home directory, else the
        unmodified absolute path.
    """
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)


def resolve_binding() -> tuple[str, str, str]:
    """Resolve the project root, venv and status this process serves.

    Returns:
        A `(root, venv, status)` triple - the resolved project root (or
        the `NO_PROJECT_ROOT` marker), the serving venv and
        `active`|`inactive`, with both paths `~/`-prefixed when under
        the home directory.
    """
    try:
        root = format_path(get_project_root())
    # NOTE: `ProjectRootNotFoundError` exactly, never a broad arm - a
    # failure to *find* a root is the fact the marker states, while any
    # other exception (an unreadable or deleted working directory) must
    # keep propagating to `_toon_errors` as the `Unexpected error:`
    # block. Widening this catch would convert a genuine fault into a
    # confident report that the project simply does not exist - see
    # `specs/mcp/tools.md`.
    except exceptions.ProjectRootNotFoundError:
        root = NO_PROJECT_ROOT
    venv = format_path(Path(sys.prefix).resolve())
    status = "active" if sys.prefix != sys.base_prefix else "inactive"
    return root, venv, status
