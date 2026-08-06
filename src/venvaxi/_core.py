"""Core CLI state and project-root resolution for `venvaxi`."""

import argparse
import dataclasses
import logging
import sys
from itertools import chain
from pathlib import Path

from venvaxi import exceptions

logger = logging.getLogger(__package__)


class ExitCode:
    """Exit codes for the CLI commands."""

    EX_OK = 0
    EX_FAILURE = 1
    EX_SYNTAX = 2


@dataclasses.dataclass(frozen=True, slots=True)
class CLIContext:
    """Centralized state for the CLI commands.

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
