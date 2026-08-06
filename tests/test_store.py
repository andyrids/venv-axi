"""Unit tests for `venvaxi._store`."""

import sqlite3
from collections.abc import Callable
from dataclasses import fields, replace
from pathlib import Path

import pytest

from venvaxi._store import (
    SCHEMA_VERSION,
    EdgeKind,
    NodeKind,
    SymbolEdge,
    SymbolNode,
    SymbolStore,
    qualify,
)

NodeFactory = Callable[..., SymbolNode]


def test_qualify_module_only() -> None:
    """A bare module name is returned unchanged when no parts given."""
    assert qualify("pkg.mod") == "pkg.mod"


def test_qualify_with_parts() -> None:
    """Extra parts are dot-joined after a `::` separator."""
    assert qualify("pkg.mod", "Foo", "bar") == "pkg.mod::Foo.bar"


def test_upsert_and_get_node(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A node can be inserted and fetched back by qualified name."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
        node = store.get_node("pkg")
    assert node is not None
    assert node.kind is NodeKind.PACKAGE


def test_get_node_missing_returns_none(tmp_path: Path) -> None:
    """A missing qualified name returns `None`."""
    with SymbolStore(tmp_path / "store.db") as store:
        assert store.get_node("does.not.exist") is None


def test_node_round_trip_preserves_all_fields(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`upsert_node` then `get_node` returns an equal `SymbolNode`."""
    node = make_symbol_node(signature="(x: int) -> str", doc="Docs.")
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(node)
        assert store.get_node(node.qualified_name) == node


def test_upsert_node_overwrites_existing(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """Re-upserting the same qualified name updates the stored fields."""
    node = make_symbol_node(
        qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
    )
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(node)
        store.upsert_node(replace(node, version="2.0.0"))
        stored = store.get_node("pkg")
    assert stored is not None
    assert stored.version == "2.0.0"


def test_get_children_returns_contains_edges_only(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """Only `CONTAINS`-linked nodes are returned as children."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Foo", name="Foo")
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::Bar", kind=NodeKind.FUNCTION, name="Bar"
            )
        )
        store.upsert_edge(
            SymbolEdge(src="pkg", dst="pkg::Foo", kind=EdgeKind.CONTAINS)
        )
        store.upsert_edge(
            SymbolEdge(src="pkg", dst="pkg::Bar", kind=EdgeKind.CONTAINS)
        )
        store.upsert_edge(
            SymbolEdge(src="pkg", dst="pkg::Bar", kind=EdgeKind.EXPORTS)
        )
        children = store.get_children("pkg")
    assert [node.name for node in children] == ["Bar", "Foo"]


def test_get_inheritors(tmp_path: Path, make_symbol_node: NodeFactory) -> None:
    """Direct subclasses are found via `INHERITS` edges."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Animal", name="Animal")
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Dog", name="Dog")
        )
        store.upsert_edge(
            SymbolEdge(
                src="pkg::Dog", dst="pkg::Animal", kind=EdgeKind.INHERITS
            )
        )
        inheritors = store.get_inheritors("pkg::Animal")
    assert [node.name for node in inheritors] == ["Dog"]


def test_canonical_name_noop_for_own_home(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`canonical_name` returns a non-re-exported node's name as-is."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(make_symbol_node(qualified_name="pkg::Foo"))
        assert store.canonical_name("pkg::Foo") == "pkg::Foo"


def test_canonical_name_unknown_name_passes_through(tmp_path: Path) -> None:
    """`canonical_name` returns an unknown name unchanged."""
    with SymbolStore(tmp_path / "store.db") as store:
        assert store.canonical_name("no.such::Name") == "no.such::Name"


def test_canonical_name_resolves_facade_to_home(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`canonical_name` maps a facade-keyed node to its home path."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg.api::Base",
                name="Base",
                home_qualified_name="pkg._impl::Base",
            )
        )
        assert store.canonical_name("pkg.api::Base") == "pkg._impl::Base"


def test_get_inheritors_resolves_facade_via_canonical_name(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A facade-path `get_inheritors` finds home-keyed edges."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg.api::Base",
                name="Base",
                home_qualified_name="pkg._impl::Base",
            )
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg._impl::Sub", name="Sub")
        )
        store.upsert_edge(
            SymbolEdge(
                src="pkg._impl::Sub",
                dst="pkg._impl::Base",
                kind=EdgeKind.INHERITS,
            )
        )
        inheritors = store.get_inheritors("pkg.api::Base")
    assert [node.name for node in inheritors] == ["Sub"]


def test_get_module_tree(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The module tree walks `CONTAINS` edges restricted to modules."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg.sub", kind=NodeKind.MODULE, name="sub"
            )
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Foo", name="Foo")
        )
        store.upsert_edge(
            SymbolEdge(src="pkg", dst="pkg.sub", kind=EdgeKind.CONTAINS)
        )
        store.upsert_edge(
            SymbolEdge(src="pkg", dst="pkg::Foo", kind=EdgeKind.CONTAINS)
        )
        pairs = store.get_module_tree("pkg")
    assert [(depth, node.name) for depth, node in pairs] == [
        (0, "pkg"),
        (1, "sub"),
    ]


def test_get_module_tree_missing_root_returns_empty(tmp_path: Path) -> None:
    """An unknown root module returns an empty tree."""
    with SymbolStore(tmp_path / "store.db") as store:
        assert store.get_module_tree("does.not.exist") == []


def test_search_symbols_matches_name(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`search_symbols` finds nodes by name/doc substring."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Dog", name="Dog")
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Cat", name="Cat")
        )
        results = store.search_symbols("Dog")
    assert [node.name for node in results] == ["Dog"]


def test_search_symbols_respects_limit(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`search_symbols` never returns more than `limit` results."""
    with SymbolStore(tmp_path / "store.db") as store:
        for index in range(5):
            store.upsert_node(
                make_symbol_node(
                    qualified_name=f"pkg::Sym{index}",
                    kind=NodeKind.FUNCTION,
                    name=f"Sym{index}",
                )
            )
        results = store.search_symbols("Sym", limit=2)
    assert len(results) == 2


def test_search_symbols_filters_by_package(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A `package`-scoped search only returns that package's nodes."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(qualified_name="a::Dog", name="Dog", package="a")
        )
        store.upsert_node(
            make_symbol_node(qualified_name="b::Dog", name="Dog", package="b")
        )
        scoped = store.search_symbols("Dog", package="a")
        unscoped = store.search_symbols("Dog")
    assert [node.package for node in scoped] == ["a"]
    assert len(unscoped) == 2


def test_search_symbols_filters_by_package_like_fallback(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The `LIKE` fallback path honors the `package` scope too."""
    with SymbolStore(tmp_path / "store.db") as store:
        store._fts_enabled = False
        store.upsert_node(
            make_symbol_node(qualified_name="a::Dog", name="Dog", package="a")
        )
        store.upsert_node(
            make_symbol_node(qualified_name="b::Dog", name="Dog", package="b")
        )
        scoped = store.search_symbols("Dog", package="a")
        unscoped = store.search_symbols("Dog")
    assert [node.package for node in scoped] == ["a"]
    assert len(unscoped) == 2


def test_search_symbols_like_fallback_when_fts_disabled(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """When FTS5 is unavailable, `search_symbols` still finds matches
    via the `LIKE` fallback path."""
    with SymbolStore(tmp_path / "store.db") as store:
        store._fts_enabled = False
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Dog", name="Dog")
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Cat", name="Cat")
        )
        results = store.search_symbols("Dog")
    assert [node.name for node in results] == ["Dog"]


def test_search_symbols_exact_match_ranks_first_fts(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The FTS path ranks an exact name match above prefix matches
    and docstring-only hits."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::Client",
                name="Client",
                doc="A Transport client.",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::TransportError", name="TransportError"
            )
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Transport", name="Transport")
        )
        results = store.search_symbols("Transport")
    assert [node.name for node in results] == [
        "Transport",
        "TransportError",
        "Client",
    ]


def test_search_symbols_exact_match_ranks_first_like(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The `LIKE` fallback ranks an exact name match above prefix and
    substring matches."""
    with SymbolStore(tmp_path / "store.db") as store:
        store._fts_enabled = False
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::get_transport", name="get_transport"
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::TransportError", name="TransportError"
            )
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Transport", name="Transport")
        )
        results = store.search_symbols("Transport")
    assert [node.name for node in results] == [
        "Transport",
        "TransportError",
        "get_transport",
    ]


def test_search_symbols_prefix_match_ranks_second_fts(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The FTS path ranks a name-prefix match above a docstring hit."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::Client",
                name="Client",
                doc="A Transport client.",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::TransportError", name="TransportError"
            )
        )
        results = store.search_symbols("Transport")
    assert [node.name for node in results] == ["TransportError", "Client"]


def test_search_symbols_prefix_match_ranks_second_like(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The `LIKE` fallback ranks a name-prefix match above a mid-name
    substring match."""
    with SymbolStore(tmp_path / "store.db") as store:
        store._fts_enabled = False
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::get_transport", name="get_transport"
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::TransportError", name="TransportError"
            )
        )
        results = store.search_symbols("Transport")
    assert [node.name for node in results] == [
        "TransportError",
        "get_transport",
    ]


def test_search_symbols_limit_applies_after_ranking(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """An exact match survives `limit=1` amid noisier hits inserted
    first (previously `LIMIT` could cut the best match entirely)."""
    with SymbolStore(tmp_path / "store.db") as store:
        for index in range(5):
            store.upsert_node(
                make_symbol_node(
                    qualified_name=f"pkg::TransportKind{index}",
                    name=f"TransportKind{index}",
                )
            )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Transport", name="Transport")
        )
        results = store.search_symbols("Transport", limit=1)
    assert [node.name for node in results] == ["Transport"]


def test_search_symbols_fts_syntax_error_degrades_to_like(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """An FTS5 query-syntax `OperationalError` degrades to the `LIKE`
    fallback at runtime, returning a clean empty result."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::print_and_run", name="print_and_run"
            )
        )
        assert store.search_symbols("print AND") == []


def test_clear_package_removes_nodes_and_edges(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`clear_package` deletes all of a package's nodes and edges."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Foo", name="Foo")
        )
        store.upsert_edge(
            SymbolEdge(src="pkg", dst="pkg::Foo", kind=EdgeKind.CONTAINS)
        )
        store.clear_package("pkg")
        assert store.get_node("pkg") is None
        assert store.get_children("pkg") == []


def test_as_row_contains_all_fields(make_symbol_node: NodeFactory) -> None:
    """`SymbolNode.as_row` exposes every field as a plain string."""
    row = make_symbol_node().as_row()
    assert row["qualified_name"] == "pkg::Foo"
    assert row["kind"] == "class"
    assert row["name"] == "Foo"


def test_as_row_keys_match_declared_fields(
    make_symbol_node: NodeFactory,
) -> None:
    """`as_row` keys track the `SymbolNode` field declaration order."""
    row = make_symbol_node().as_row()
    assert tuple(row) == tuple(field.name for field in fields(SymbolNode))


def test_upserts_discarded_without_flush(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """Upserts left pending at close are not persisted."""
    db_path = tmp_path / "store.db"
    with SymbolStore(db_path) as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
    with SymbolStore(db_path) as store:
        assert store.get_node("pkg") is None


def test_flush_persists_upserts(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`flush` commits pending upserts so they survive a reopen."""
    db_path = tmp_path / "store.db"
    with SymbolStore(db_path) as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
        store.upsert_edge(
            SymbolEdge(src="pkg", dst="pkg::Foo", kind=EdgeKind.CONTAINS)
        )
        store.flush()
    with SymbolStore(db_path) as store:
        assert store.get_node("pkg") is not None


def test_rollback_discards_pending_upserts(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`rollback` discards pending upserts on the open connection."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
        store.rollback()
        assert store.get_node("pkg") is None


def test_fts_index_tracks_upsert_update_and_clear(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The trigger-maintained FTS index follows the `nodes` lifecycle."""
    with SymbolStore(tmp_path / "store.db") as store:
        node = make_symbol_node(
            qualified_name="pkg::Dog", name="Dog", doc="barks loudly"
        )
        store.upsert_node(node)
        assert [n.name for n in store.search_symbols("barks")] == ["Dog"]

        # Re-upserting must replace the indexed doc, not duplicate it
        store.upsert_node(replace(node, doc="meows quietly"))
        assert store.search_symbols("barks") == []
        assert [n.name for n in store.search_symbols("meows")] == ["Dog"]

        store.clear_package("pkg")
        assert store.search_symbols("meows") == []


def test_schema_version_mismatch_rebuilds_tables(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A `user_version` mismatch drops and recreates the schema."""
    db_path = tmp_path / "store.db"
    with SymbolStore(db_path) as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg", kind=NodeKind.PACKAGE, name="pkg"
            )
        )
        store.flush()

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA user_version = 999")
    connection.commit()
    connection.close()

    with SymbolStore(db_path) as store:
        assert store.get_node("pkg") is None
        (version,) = store._connection.execute(
            "PRAGMA user_version"
        ).fetchone()
        assert version == SCHEMA_VERSION


def test_corrupt_database_raises_and_releases_file(tmp_path: Path) -> None:
    """A corrupt database file raises `sqlite3.DatabaseError` and the
    connection is closed (the file is deletable afterwards on Windows)."""
    db_path = tmp_path / "store.db"
    db_path.write_bytes(b"this is not a sqlite database, honest")
    with pytest.raises(sqlite3.DatabaseError):
        SymbolStore(db_path)
    db_path.unlink()
