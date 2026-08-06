"""Dependency discovery and installed-package resolution for `axi`."""

import logging
import re
from dataclasses import dataclass, fields
from importlib import metadata
from pathlib import Path

import tomllib

from venvaxi.exceptions import PackageNotFoundError

logger = logging.getLogger(__package__)

_NAME_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?")


@dataclass(frozen=True, slots=True)
class PackageInfo:
    """Stores a record of a resolved, installed package."""

    name: str
    version: str
    location: str
    summary: str = ""


PACKAGE_INFO_FIELDS = tuple(field.name for field in fields(PackageInfo))
"""The ordered `PackageInfo` field names, forming TOON tabular headers."""


def _requirement_name(requirement: str) -> str:
    """Extract the bare package name from a PEP 508 requirement string.

    Args:
        requirement: A raw dependency string, e.g. `"fastmcp>=0.1.0"`.

    Returns:
        The lowercase package name, without specifiers, extras or markers.
    """
    match = _NAME_RE.match(requirement.strip())
    name = match.group(0) if match else requirement.strip()
    return name.lower()


def discover_direct_dependencies(
    root: Path, *, include_dev: bool = False
) -> list[str]:
    """Discovers dependency names from the repo `pyproject.toml`.

    Args:
        root: The project root path.
        include_dev: Includes `dependency-groups.dev` and
            `project.optional-dependencies` groups. Defaults to False.

    Returns:
        A de-duplicated, order-preserved list of package names.
    """
    pyproject = root / "pyproject.toml"
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)

    project = data.get("project", {})
    requirements = list(project.get("dependencies", []))

    if include_dev:
        dependency_groups = data.get("dependency-groups", {})
        requirements += dependency_groups.get("dev", [])

        optional_dependencies = project.get("optional-dependencies", {})
        for extra_requirements in optional_dependencies.values():
            requirements += extra_requirements

    seen: set[str] = set()
    names: list[str] = []
    for requirement in requirements:
        name = _requirement_name(requirement)
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def resolve_package(name: str) -> PackageInfo:
    """Resolve metadata for an installed distribution.

    Args:
        name: The package (distribution) name.

    Raises:
        PackageNotFoundError: On `name` not being installed in the active
            venv.

    Returns:
        The resolved `PackageInfo`.
    """
    try:
        dist = metadata.distribution(name)
    except metadata.PackageNotFoundError as err:
        msg = f"Package `{name}` is not installed in the active venv"
        if "." in name:
            msg += (
                " - metadata mode takes a distribution name; for a"
                " dotted module path use `show <package> --api`"
            )
        raise PackageNotFoundError(msg) from err
    else:
        info = dist.metadata
        return PackageInfo(
            name=info.get("Name", name),
            version=info.get("Version", "unknown"),
            location=str(dist.locate_file("")),
            summary=info.get("Summary", ""),
        )


def _try_resolve_package(name: str) -> PackageInfo | None:
    """Resolve a package.

    NOTE: Skips uninstalled dependencies rather than raising.

    Args:
        name: The package (distribution) name.

    Returns:
        The resolved `PackageInfo`, or None if not installed.
    """
    try:
        return resolve_package(name)
    except PackageNotFoundError:
        logger.debug("Skipping uninstalled dependency `%s`", name)
        return None


def list_packages(
    root: Path, *, include_dev: bool = False
) -> list[PackageInfo]:
    """List resolved package info for declared dependencies.

    NOTE: Missing dependencies are skipped rather than raising.

    Args:
        root: The project root path.
        include_dev: Includes `dependency-groups.dev` and
            `project.optional-dependencies` groups. Defaults to False.

    Returns:
        Resolved package info with entries for each installed dependency.
    """
    names = discover_direct_dependencies(root, include_dev=include_dev)
    resolved = (_try_resolve_package(name) for name in names)
    return [package for package in resolved if package is not None]
