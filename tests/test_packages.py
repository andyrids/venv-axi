"""Unit tests for `venvaxi._packages`."""

from pathlib import Path
from unittest import mock

import pytest

from venvaxi._packages import (
    PackageInfo,
    _requirement_name,
    discover_direct_dependencies,
    list_packages,
    resolve_package,
)
from venvaxi.exceptions import PackageNotFoundError

PACKAGES = "venvaxi._packages"


@pytest.mark.parametrize(
    ("requirement", "expected"),
    [
        ("fastmcp>=0.1.0", "fastmcp"),
        ("Rich[jupyter]>=15.0.0", "rich"),
        ("tomlkit ; python_version >= '3.11'", "tomlkit"),
    ],
)
def test_requirement_name(requirement: str, expected: str) -> None:
    """The bare package name is extracted from a requirement string."""
    assert _requirement_name(requirement) == expected


def test_discover_direct_dependencies(tmp_path: Path) -> None:
    """Direct dependencies are read from `project.dependencies`."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        "name = 'demo'\n"
        "dependencies = ['rich>=1.0', 'rich>=1.0', 'tomlkit']\n"
    )
    assert discover_direct_dependencies(tmp_path) == ["rich", "tomlkit"]


def test_discover_direct_dependencies_include_dev(tmp_path: Path) -> None:
    """Dev & optional dependency groups are included when requested."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        "name = 'demo'\n"
        "dependencies = ['rich']\n"
        "[project.optional-dependencies]\n"
        "extra = ['fastmcp']\n"
        "[dependency-groups]\n"
        "dev = ['pytest']\n"
    )
    names = discover_direct_dependencies(tmp_path, include_dev=True)
    assert names == ["rich", "pytest", "fastmcp"]


def test_discover_direct_dependencies_excludes_dev_by_default(
    tmp_path: Path,
) -> None:
    """Dev & optional dependency groups are excluded by default."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        "name = 'demo'\n"
        "dependencies = ['rich']\n"
        "[dependency-groups]\n"
        "dev = ['pytest']\n"
    )
    assert discover_direct_dependencies(tmp_path) == ["rich"]


def test_resolve_package() -> None:
    """An installed distribution resolves to a `PackageInfo`."""
    mock_dist = mock.MagicMock()
    mock_dist.metadata = {
        "Name": "rich",
        "Version": "15.0.0",
        "Summary": "Render rich text",
    }
    mock_dist.locate_file.return_value = "/venv/site-packages"

    with mock.patch(
        f"{PACKAGES}.metadata.distribution", return_value=mock_dist
    ):
        info = resolve_package("rich")

    assert info == PackageInfo(
        name="rich",
        version="15.0.0",
        location="/venv/site-packages",
        summary="Render rich text",
    )


def test_resolve_package_not_found() -> None:
    """An uninstalled distribution raises `PackageNotFoundError`."""
    with pytest.raises(PackageNotFoundError):
        resolve_package("this-package-does-not-exist-xyz")


def test_list_packages_skips_uninstalled(tmp_path: Path) -> None:
    """Uninstalled declared dependencies are skipped, not raised."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        "name = 'demo'\n"
        "dependencies = ['this-package-does-not-exist-xyz']\n"
    )
    assert list_packages(tmp_path) == []


def test_list_packages_resolves_installed(tmp_path: Path) -> None:
    """Resolvable declared dependencies are returned as `PackageInfo`."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'demo'\ndependencies = ['rich']\n")
    packages = list_packages(tmp_path)
    assert [package.name for package in packages] == ["rich"]
