"""Unit tests for `venvaxi._core`.

NOTE: These sit outside `test_mcp.py` deliberately. `format_path` and
`resolve_binding` are plain `_core` helpers with no `fastmcp` dependency,
and `test_mcp.py` opens with a module-level `importorskip("fastmcp")`.
Housing them there would gate the discriminating test below on an
unrelated extra, so an environment without `venv-axi[mcp]` would skip
the one test proving a genuine fault is not swallowed.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

from venvaxi._constants import NO_PROJECT_ROOT
from venvaxi._core import format_path, resolve_binding
from venvaxi.exceptions import ProjectRootNotFoundError

CORE = "venvaxi._core"


def test_format_path_prefixes_paths_under_home() -> None:
    """A path under the home directory renders `~/`-prefixed."""
    assert format_path(Path.home() / "proj") == "~/proj"


def test_format_path_keeps_paths_outside_home_absolute() -> None:
    """A path outside the home directory renders unmodified."""
    outside = Path(Path.home().anchor) / "elsewhere" / "proj"
    assert format_path(outside) == str(outside)


def test_resolve_binding_reports_root_venv_and_status() -> None:
    """The triple carries the formatted root, the serving venv and the
    same `status` computation the home view makes."""
    with mock.patch(
        f"{CORE}.get_project_root", return_value=Path.home() / "proj"
    ):
        root, venv, status = resolve_binding()
    assert root == "~/proj"
    assert venv == format_path(Path(sys.prefix).resolve())
    expected = "active" if sys.prefix != sys.base_prefix else "inactive"
    assert status == expected


def test_resolve_binding_no_root_returns_marker() -> None:
    """A failure to find a root becomes the marker, never an error."""
    with mock.patch(
        f"{CORE}.get_project_root",
        side_effect=ProjectRootNotFoundError("nope"),
    ):
        root, venv, status = resolve_binding()
    assert root == NO_PROJECT_ROOT
    assert venv
    assert status in {"active", "inactive"}


def test_resolve_binding_unexpected_error_propagates() -> None:
    """Anything other than a failure to find a root propagates.

    NOTE: The discriminating test for the scoped catch - a widened
    `except Exception` in `resolve_binding` passes every other test in
    the suite and turns a genuine fault into a confident
    `(no project root)` report (`specs/mcp/tools.md`, Failure modes).
    """
    with (
        mock.patch(f"{CORE}.get_project_root", side_effect=OSError("gone")),
        pytest.raises(OSError, match="gone"),
    ):
        resolve_binding()
