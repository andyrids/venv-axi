"""Shared unit test fixtures."""

import argparse
import pathlib
from collections.abc import Callable
from typing import Any

import pytest

from venvaxi._core import CLIContext
from venvaxi._packages import PackageInfo
from venvaxi._store import NodeKind, SymbolNode


@pytest.fixture
def isolated_cache(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> pathlib.Path:
    """Isolates the `SymbolStore` cache dir to `tmp_path`.

    Prevents tests from reading/writing the real `~/.venvaxi/` cache
    directory.
    """
    monkeypatch.setattr("venvaxi._cache.get_cache_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def make_symbol_node() -> Callable[..., SymbolNode]:
    """Factory-build a `SymbolNode` with defaults for every field.

    NOTE: Field-change insulation - a `SymbolNode` field addition only
    requires a new default here, not edits across every test module.
    """

    def factory(**overrides: Any) -> SymbolNode:
        defaults: dict[str, Any] = {
            "qualified_name": "pkg::Foo",
            "kind": NodeKind.CLASS,
            "name": "Foo",
            "module": "pkg",
            "signature": "",
            "doc": "",
            "package": "pkg",
            "version": "1.0.0",
        }
        merged: dict[str, Any] = {**defaults, **overrides}
        # NOTE: Self-canonical default (mirrors `qualified_name`), so
        # `canonical_name` no-ops unless a test opts into a facade.
        merged.setdefault("home_qualified_name", merged["qualified_name"])
        return SymbolNode(**merged)

    return factory


@pytest.fixture
def make_package_info() -> Callable[..., PackageInfo]:
    """Factory-build a `PackageInfo` with defaults for every field."""

    def factory(**overrides: Any) -> PackageInfo:
        defaults: dict[str, Any] = {
            "name": "rich",
            "version": "15.0.0",
            "location": "/venv",
            "summary": "",
        }
        return PackageInfo(**{**defaults, **overrides})

    return factory


@pytest.fixture
def make_cli_context() -> Callable[..., CLIContext]:
    """Factory-build a `CLIContext` with defaults for every field."""

    def factory(**overrides: Any) -> CLIContext:
        # NOTE: Shared flag defaults mirror the argparse defaults in
        # `venvaxi._cli.add_subparser`, so each test declares only the
        # arguments its command actually reads.
        args = argparse.Namespace(refresh=False, docstring=False, package=None)
        vars(args).update(vars(overrides.pop("args", argparse.Namespace())))
        defaults: dict[str, Any] = {"args": args, "is_verbose": False}
        return CLIContext(**{**defaults, **overrides})

    return factory
