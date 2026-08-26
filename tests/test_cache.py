"""Unit tests for `venvaxi._cache`."""

import sqlite3
import sys
import types
from collections.abc import Callable, Iterator
from importlib import metadata
from pathlib import Path
from unittest import mock

import pytest

from venvaxi import _cache, exceptions
from venvaxi._store import SCHEMA_VERSION, NodeKind, SymbolNode, SymbolStore

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


def test_installed_version_single_distribution_returns_bare_version() -> None:
    """Exactly one claiming distribution records its bare version string
    (Validation criterion 1)."""
    assert _cache._installed_version(("pytest",)) == metadata.version("pytest")


def test_installed_version_multiple_distributions_composite() -> None:
    """Two or more claiming distributions record a sorted, comma-joined
    `name=version` composite (Validation criterion 2)."""
    versions = {"zeta-dist": "2.0.0", "alpha-dist": "1.0.0"}
    with mock.patch(
        f"{CACHE}.metadata.version", side_effect=lambda dist: versions[dist]
    ):
        result = _cache._installed_version(("zeta-dist", "alpha-dist"))
    assert result == "alpha-dist=1.0.0,zeta-dist=2.0.0"


def test_installed_version_no_distribution_returns_marker() -> None:
    """No claiming distribution records the literal `(no distribution)`
    marker (Validation criterion 3).

    This rewrites the prior pinned assertion
    (`_installed_version("this-is-not-a-real-distribution") == ""`),
    which asserted exactly the silent-wrong-value behaviour #89 exists
    to remove - an import name resolving to no distribution recorded
    `""`, which then compared equal to itself forever.
    """
    assert _cache._installed_version(()) == "(no distribution)"


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
        store = _cache.get_or_build_store(root, fake_module.__name__, ())
    try:
        node = store.get_node(fake_module.__name__)
        assert node is not None
        assert node.kind is NodeKind.PACKAGE
        children = store.get_children(fake_module.__name__)
        assert [child.name for child in children] == ["util"]
    finally:
        store.close()


def test_get_or_build_store_releases_store_on_base_exception(
    tmp_path: Path,
    fake_module: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A build aborted by a `BaseException` discards and closes the
    half-built store before the exception propagates - `except
    Exception` leaked the open store, which locks the cache database
    on Windows (#64)."""

    class WalkCrash(BaseException):
        """A `BaseException` subclass that is not an `Exception`."""

    def _crash(*args: object, **kwargs: object) -> None:
        raise WalkCrash

    root = tmp_path / "project"
    monkeypatch.setattr(f"{CACHE}._introspect._walk_module", _crash)
    with (
        mock.patch(f"{CACHE}._installed_version", return_value=""),
        pytest.raises(WalkCrash),
    ):
        _cache.get_or_build_store(root, fake_module.__name__, ())
    # The database is deletable, which an open connection blocks on
    # Windows - the observable release the spec requires.
    _cache.get_cache_db_path(root).unlink()


def test_get_or_build_store_skips_rebuild_when_valid(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """A cache hit does not re-walk the module."""
    root = tmp_path / "project"
    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        first = _cache.get_or_build_store(root, fake_module.__name__, ())
        first.close()
        with mock.patch("venvaxi._introspect._walk_module") as walk:
            second = _cache.get_or_build_store(root, fake_module.__name__, ())
            second.close()
        walk.assert_not_called()


def test_get_or_build_store_rebuilds_on_version_change(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """A version mismatch triggers a rebuild."""
    root = tmp_path / "project"
    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        first = _cache.get_or_build_store(root, fake_module.__name__, ())
        first.close()
    with mock.patch(f"{CACHE}._installed_version", return_value="2.0.0"):
        second = _cache.get_or_build_store(root, fake_module.__name__, ())
        try:
            node = second.get_node(fake_module.__name__)
            assert node is not None
            assert node.version == "2.0.0"
        finally:
            second.close()


def test_get_or_build_store_threads_distributions_to_installed_version(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """`get_or_build_store` resolves the version from the `distributions`
    tuple the caller threads in, not by re-deriving it (Validation
    criterion 7 - no second `packages_distributions()` call is needed
    here because the caller already resolved it)."""
    root = tmp_path / "project"
    with mock.patch(
        f"{CACHE}._installed_version", return_value="9.9.9"
    ) as installed_version:
        _cache.get_or_build_store(
            root, fake_module.__name__, ("some-dist", "other-dist")
        )
    installed_version.assert_called_once_with(("some-dist", "other-dist"))


def test_get_or_build_store_differing_import_name_records_real_version(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """A package whose import name differs from its claiming
    distribution's name records that distribution's real installed
    version, never `""` (Validation criterion 4) - `pytest` stands in
    for the live `dns`/`dnspython` case (#89)."""
    root = tmp_path / "project"
    store = _cache.get_or_build_store(root, fake_module.__name__, ("pytest",))
    try:
        node = store.get_node(fake_module.__name__)
        assert node is not None
        assert node.version == metadata.version("pytest")
        assert node.version != ""
    finally:
        store.close()


def test_get_or_build_store_rebuilds_on_claiming_distribution_version_change(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """A version change on the distribution claiming a cached import
    name invalidates the cache on the next query (Validation criterion
    5)."""
    root = tmp_path / "project"
    with mock.patch(f"{CACHE}.metadata.version", return_value="1.0.0"):
        first = _cache.get_or_build_store(
            root, fake_module.__name__, ("some-dist",)
        )
        first.close()
    with mock.patch(f"{CACHE}.metadata.version", return_value="2.0.0"):
        second = _cache.get_or_build_store(
            root, fake_module.__name__, ("some-dist",)
        )
        try:
            node = second.get_node(fake_module.__name__)
            assert node is not None
            assert node.version == "2.0.0"
        finally:
            second.close()


def test_get_or_build_store_no_distribution_stays_valid_without_rebuild(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """An import name claiming no distribution stays valid across
    queries at sufficient depth - it does not rebuild on the strength
    of a version comparison alone (Validation criterion 6)."""
    root = tmp_path / "project"
    first = _cache.get_or_build_store(root, fake_module.__name__, ())
    first.close()
    with mock.patch("venvaxi._introspect._walk_module") as walk:
        second = _cache.get_or_build_store(root, fake_module.__name__, ())
        second.close()
    walk.assert_not_called()


def test_get_or_build_store_force_refresh(
    tmp_path: Path, fake_module: types.ModuleType
) -> None:
    """`force_refresh=True` rebuilds even when the cache is valid."""
    root = tmp_path / "project"
    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        first = _cache.get_or_build_store(root, fake_module.__name__, ())
        first.close()
        with mock.patch("venvaxi._introspect._walk_module") as walk:
            second = _cache.get_or_build_store(
                root, fake_module.__name__, (), force_refresh=True
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
        _cache.get_or_build_store(root, fake_module.__name__, ())

    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        store = _cache.get_or_build_store(root, fake_module.__name__, ())
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
        _cache.get_or_build_store(root, fake_module.__name__, ())
    close_mock.assert_called_once()

    # On partial build (PACKAGE node) rollback, MUST rebuild
    with mock.patch(f"{CACHE}._installed_version", return_value="1.0.0"):
        store = _cache.get_or_build_store(root, fake_module.__name__, ())
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
        _cache.get_or_build_store(root, "definitely_not_a_real_module", ())
    close_mock.assert_called_once()


def test_read_cache_state_not_built_without_opening_sqlite(
    isolated_cache: Path, tmp_path: Path
) -> None:
    """A project with no cache database reports the not-built empty
    state - `schema_version: None`, `db_size_bytes: 0`, no builds -
    without opening SQLite at all (Validation criterion 2)."""
    root = tmp_path / "proj"
    root.mkdir()
    with mock.patch(f"{CACHE}.sqlite3.connect") as connect:
        state = _cache.read_cache_state(root)
    connect.assert_not_called()
    assert state.schema_version is None
    assert state.db_size_bytes == 0
    assert state.builds == []
    assert state.db_path == _cache.get_cache_db_path(root)


def test_read_cache_state_reports_builds_and_symbol_counts(
    isolated_cache: Path, tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A built cache reports each package's recorded version, depth
    and current symbol count, at the real recorded schema version
    (Validation criteria 1, 3)."""
    root = tmp_path / "proj"
    root.mkdir()
    db_path = _cache.get_cache_db_path(root)
    with SymbolStore(db_path) as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="rich",
                kind=NodeKind.PACKAGE,
                name="rich",
                package="rich",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="rich::Console",
                name="Console",
                package="rich",
            )
        )
        store.record_build("rich", "1.0.0", 2)
        store.flush()

    state = _cache.read_cache_state(root)
    assert state.schema_version == SCHEMA_VERSION
    assert state.db_size_bytes == db_path.stat().st_size
    assert state.builds == [
        _cache.PackageBuild(
            package="rich", version="1.0.0", depth=2, symbols=2
        )
    ]


def test_read_cache_state_symbols_default_to_zero_without_nodes(
    isolated_cache: Path, tmp_path: Path
) -> None:
    """A recorded build with no matching `nodes` rows reports
    `symbols: 0` rather than raising."""
    root = tmp_path / "proj"
    root.mkdir()
    db_path = _cache.get_cache_db_path(root)
    with SymbolStore(db_path) as store:
        store.record_build("ghost", "1.0.0", 2)
        store.flush()

    state = _cache.read_cache_state(root)
    assert state.builds == [
        _cache.PackageBuild(
            package="ghost", version="1.0.0", depth=2, symbols=0
        )
    ]


def test_read_cache_state_orders_builds_by_package(
    isolated_cache: Path, tmp_path: Path
) -> None:
    """Multiple recorded builds are ordered by `package`
    (`specs/commands/cache.md`, Outputs)."""
    root = tmp_path / "proj"
    root.mkdir()
    db_path = _cache.get_cache_db_path(root)
    with SymbolStore(db_path) as store:
        store.record_build("zeta", "1.0.0", 2)
        store.record_build("alpha", "1.0.0", 2)
        store.flush()

    state = _cache.read_cache_state(root)
    assert [build.package for build in state.builds] == ["alpha", "zeta"]


def test_read_cache_state_built_but_empty_reports_real_schema_version(
    isolated_cache: Path, tmp_path: Path
) -> None:
    """A cache database that exists but records zero builds reports
    the real recorded `schema_version`, distinguishable from the
    not-built state by that field alone (Validation criterion 3)."""
    root = tmp_path / "proj"
    root.mkdir()
    db_path = _cache.get_cache_db_path(root)
    SymbolStore(db_path).close()

    state = _cache.read_cache_state(root)
    assert state.schema_version == SCHEMA_VERSION
    assert state.builds == []


def test_read_cache_state_stale_schema_reported_unchanged(
    isolated_cache: Path, tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A cache database whose recorded schema version differs from the
    current schema version is reported with the stale value, unchanged
    (Validation criterion 6)."""
    root = tmp_path / "proj"
    root.mkdir()
    db_path = _cache.get_cache_db_path(root)
    with SymbolStore(db_path) as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg",
                kind=NodeKind.PACKAGE,
                name="pkg",
                package="pkg",
            )
        )
        store.record_build("pkg", "1.0.0", 2)
        store.flush()

    stale_version = SCHEMA_VERSION - 1
    raw = sqlite3.connect(db_path)
    try:
        raw.execute(f"PRAGMA user_version = {stale_version}")
        raw.commit()
    finally:
        raw.close()

    state = _cache.read_cache_state(root)
    assert state.schema_version == stale_version


def test_read_cache_state_does_not_mutate_stale_schema_database(
    isolated_cache: Path, tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """After `read_cache_state` reads a stale-schema cache, the
    database's own recorded schema version and `package_builds` rows
    are byte-identical to before the read (Validation criterion 7) -
    the guard against this unit's central risk: a `SymbolStore` open
    would drop and rebuild `nodes`/`edges`/`package_builds` as a side
    effect of merely connecting (`_store.py::_ensure_schema`).

    This is the test that fails against a `SymbolStore`-based
    implementation - see the stage 02 report for the failing-first
    demonstration.
    """
    root = tmp_path / "proj"
    root.mkdir()
    db_path = _cache.get_cache_db_path(root)
    with SymbolStore(db_path) as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg",
                kind=NodeKind.PACKAGE,
                name="pkg",
                package="pkg",
            )
        )
        store.record_build("pkg", "1.0.0", 2)
        store.flush()

    stale_version = SCHEMA_VERSION - 1
    raw = sqlite3.connect(db_path)
    try:
        raw.execute(f"PRAGMA user_version = {stale_version}")
        raw.commit()
    finally:
        raw.close()

    before_bytes = db_path.read_bytes()

    _cache.read_cache_state(root)

    raw = sqlite3.connect(db_path)
    try:
        (version_after,) = raw.execute("PRAGMA user_version").fetchone()
        rows_after = raw.execute(
            "SELECT package, version, max_depth FROM package_builds"
        ).fetchall()
    finally:
        raw.close()

    assert version_after == stale_version
    assert rows_after == [("pkg", "1.0.0", 2)]
    assert db_path.read_bytes() == before_bytes


def test_read_cache_state_wraps_sqlite_error(
    isolated_cache: Path, tmp_path: Path
) -> None:
    """A SQLite-level failure reading an existing cache database raises
    `StoreError` (Validation criterion 9)."""
    root = tmp_path / "proj"
    root.mkdir()
    db_path = _cache.get_cache_db_path(root)
    db_path.write_bytes(b"this is not a sqlite database, honest")

    with pytest.raises(exceptions.StoreError):
        _cache.read_cache_state(root)
