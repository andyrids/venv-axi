"""Unit tests for `venvaxi._cache`."""

import sqlite3
import sys
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest import mock

import pytest

from venvaxi import _cache, exceptions
from venvaxi._store import NodeKind, SymbolNode, SymbolStore

NodeFactory = Callable[..., SymbolNode]

CACHE = "venvaxi._cache"


@pytest.fixture
def fake_module(isolated_cache: Path) -> Iterator[types.ModuleType]:
    """Register a throwaway module for cache-orchestration tests."""
    module = types.ModuleType("axi_cache_fixture_mod")

    def util() -> str:
        """Return a utility function."""
        return "ok"

    module.util = util  # type: ignore[attr-defined]
    sys.modules[module.__name__] = module
    try:
        yield module
    finally:
        del sys.modules[module.__name__]


def test_get_cache_dir_creates_directory(tmp_path: Path) -> None:
    """`get_cache_dir` creates (and returns) `~/.venvaxi`."""
    fake_home = tmp_path / "home"
    with mock.patch(f"{CACHE}.Path.home", return_value=fake_home):
        cache_dir = _cache.get_cache_dir()
    assert cache_dir == fake_home / ".venvaxi"
    assert cache_dir.is_dir()


def test_get_cache_db_path_is_stable(
    isolated_cache: Path, tmp_path: Path
) -> None:
    """The same project root always maps to the same db filename."""
    root = tmp_path / "proj"
    root.mkdir()
    first = _cache.get_cache_db_path(root)
    second = _cache.get_cache_db_path(root)
    assert first == second
    assert first.parent == isolated_cache


def test_get_cache_db_path_differs_per_project(
    isolated_cache: Path, tmp_path: Path
) -> None:
    """Different project roots map to different db filenames."""
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    assert _cache.get_cache_db_path(root_a) != _cache.get_cache_db_path(root_b)


def test_installed_version_known_package() -> None:
    """A real installed distribution resolves a non-empty version."""
    assert _cache._installed_version("pytest") != ""


def test_installed_version_unknown_package_returns_empty() -> None:
    """A non-distribution name degrades gracefully to an empty string."""
    assert _cache._installed_version("this-is-not-a-real-distribution") == ""


def test_is_cache_valid_false_when_node_missing(tmp_path: Path) -> None:
    """An empty store is never considered valid."""
    with SymbolStore(tmp_path / "store.db") as store:
        assert _cache.is_cache_valid(store, "pkg", "1.0.0") is False


def test_is_cache_valid_true_when_version_matches(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A recorded version matching the installed version is valid."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
        store.record_build("pkg", "1.0.0", 2)
        assert _cache.is_cache_valid(store, "pkg", "1.0.0") is True
        assert _cache.is_cache_valid(store, "pkg", "2.0.0") is False


def test_is_cache_valid_false_when_built_shallower(tmp_path: Path) -> None:
    """A graph built shallower than requested must not be reused."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.record_build("pkg", "1.0.0", 1)
        assert _cache.is_cache_valid(store, "pkg", "1.0.0", 1) is True
        assert _cache.is_cache_valid(store, "pkg", "1.0.0", 3) is False


def test_get_or_build_store_builds_on_first_call(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """A fresh cache builds the store and records the package node."""
    root = tmp_path / "project"
    with mock.patch(f"{CACHE}._installed_version", return_value=""):
        store = _cache.get_or_build_store(root, fake_module.__name__)
    try:
        node = store.get_node(fake_module.__name__)
        assert node is not None
        assert node.kind is NodeKind.PACKAGE
        children = store.get_children(fake_module.__name__)
        assert [child.name for child in children] == ["util"]
    finally:
        store.close()


def test_get_or_build_store_skips_rebuild_when_valid(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """A cache hit does not re-walk the module."""
    root = tmp_path / "project"
    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        first = _cache.get_or_build_store(root, fake_module.__name__)
        first.close()
        with mock.patch("venvaxi._introspect._walk_module") as walk:
            second = _cache.get_or_build_store(root, fake_module.__name__)
            second.close()
        walk.assert_not_called()


def test_get_or_build_store_rebuilds_on_version_change(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """A version mismatch triggers a rebuild."""
    root = tmp_path / "project"
    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        first = _cache.get_or_build_store(root, fake_module.__name__)
        first.close()
    with mock.patch(f"{CACHE}._installed_version", return_value="2.0.0"):
        second = _cache.get_or_build_store(root, fake_module.__name__)
        try:
            node = second.get_node(fake_module.__name__)
            assert node is not None
            assert node.version == "2.0.0"
        finally:
            second.close()


def test_get_or_build_store_force_refresh(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """`force_refresh=True` rebuilds even when the cache is valid."""
    root = tmp_path / "project"
    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        first = _cache.get_or_build_store(root, fake_module.__name__)
        first.close()
        with mock.patch("venvaxi._introspect._walk_module") as walk:
            second = _cache.get_or_build_store(
                root, fake_module.__name__, force_refresh=True
            )
            second.close()
        walk.assert_called_once()


def test_get_or_build_store_wraps_database_error(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """A mid-walk `sqlite3.DatabaseError` raises `StoreError`.

    NOTE: MUST clear any partial state to prevent a corrupted store from being
    used on subsequent calls.
    """
    root = tmp_path / "project"
    with (
        mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"),
        mock.patch(
            "venvaxi._introspect._walk_module",
            side_effect=sqlite3.IntegrityError("NOT NULL constraint failed"),
        ),
        pytest.raises(exceptions.StoreError),
    ):
        _cache.get_or_build_store(root, fake_module.__name__)

    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        store = _cache.get_or_build_store(root, fake_module.__name__)
    try:
        assert _cache.is_cache_valid(store, fake_module.__name__, "1.0.0")
    finally:
        store.close()


def test_get_or_build_store_non_database_error_not_poisoning(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """Non-database errors during a walk do not poison the cache.

    A non-database failure mid-walk:

    1. Propagates unwrapped
    2. Closes the store
    3. Leaves the cache invalid (forces rebuild)
    """
    root = tmp_path / "project"
    with (
        mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"),
        mock.patch(
            "venvaxi._introspect._walk_module",
            side_effect=TypeError("boom"),
        ),
        mock.patch.object(SymbolStore, "close", autospec=True) as close_mock,
        pytest.raises(TypeError),
    ):
        _cache.get_or_build_store(root, fake_module.__name__)
    close_mock.assert_called_once()

    # On partial build (PACKAGE node) rollback, MUST rebuild
    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        store = _cache.get_or_build_store(root, fake_module.__name__)
    try:
        assert _cache.is_cache_valid(store, fake_module.__name__, "1.0.0")
        children = store.get_children(fake_module.__name__)
        assert [child.name for child in children] == ["util"]
    finally:
        store.close()


def test_get_or_build_store_import_failure_closes_store(
    tmp_path: Path, isolated_cache: Path
) -> None:
    """Failed import of a module closes the store.

    A package that fails to import propagates the error and does not
    leak the store connection.
    """
    root = tmp_path / "project"
    with (
        mock.patch(f"{CACHE}._installed_version", return_value=""),
        mock.patch.object(SymbolStore, "close", autospec=True) as close_mock,
        pytest.raises(ModuleNotFoundError),
    ):
        _cache.get_or_build_store(root, "definitely_not_a_real_module")
    close_mock.assert_called_once()
