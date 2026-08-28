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


def test_get_bases_indexed_base(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A direct base with its own node row is found via the edge."""
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
        bases = store.get_bases("pkg::Dog")
    assert [(node.name, node.kind, node.qualified_name) for node in bases] == [
        ("Animal", NodeKind.CLASS, "pkg::Animal")
    ]


def test_get_bases_unindexed_base_package(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A base whose own package was never indexed is still reported.

    NOTE: The fixture deliberately seeds the `INHERITS` edge but **no**
    node row for `logging::Handler` - the walk writes the edge for a
    cross-package base and leaves the node alone
    (`_introspect._walk_class_members`). A naive `nodes` JOIN passes a
    both-nodes fixture and silently drops exactly this case
    (`specs/commands/inherits.md`, Direction; #48).
    """
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="rich.logging::RichHandler",
                name="RichHandler",
                module="rich.logging",
                package="rich",
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src="rich.logging::RichHandler",
                dst="logging::Handler",
                kind=EdgeKind.INHERITS,
            )
        )
        assert store.get_node("logging::Handler") is None
        bases = store.get_bases("rich.logging::RichHandler")
    assert [(node.name, node.kind, node.qualified_name) for node in bases] == [
        ("Handler", NodeKind.CLASS, "logging::Handler")
    ]


def test_get_bases_resolves_facade_via_canonical_name(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A facade-path `get_bases` finds home-keyed edges."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg.api::Sub",
                name="Sub",
                home_qualified_name="pkg._impl::Sub",
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src="pkg._impl::Sub",
                dst="pkg._impl::Base",
                kind=EdgeKind.INHERITS,
            )
        )
        bases = store.get_bases("pkg.api::Sub")
    assert [node.qualified_name for node in bases] == ["pkg._impl::Base"]


def test_get_bases_ordered_by_qualified_name(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """Bases order by qualified name, stable across repeated runs.

    NOTE: Edges are seeded in a non-alphabetical order, so an
    implementation ordering on rowid/insertion order fails here
    (`specs/commands/inherits.md`, Result ordering).
    """
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Multi", name="Multi")
        )
        for dst in ("zpkg::Late", "apkg::Early", "mpkg::Middle"):
            store.upsert_edge(
                SymbolEdge(src="pkg::Multi", dst=dst, kind=EdgeKind.INHERITS)
            )
        first = store.get_bases("pkg::Multi")
        second = store.get_bases("pkg::Multi")
    assert [node.qualified_name for node in first] == [
        "apkg::Early",
        "mpkg::Middle",
        "zpkg::Late",
    ]
    assert first == second


def test_get_bases_after_base_package_cleared(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`clear_package` on a base's package keeps the subclass's edge.

    NOTE: Pins what makes the `--bases` empty state definitive (plan
    Validation criterion 3; `specs/behaviors/cache-refresh.md`,
    Refresh scope: edges): the edge was written by the *subclass's*
    walk, so clearing the *base's* package must not reach it. The
    fixture clears `alib` and deliberately does not rebuild it - with
    both packages present either deletion scope passes. The base's
    node is gone and the edge survives, which is the
    edge-outliving-its-endpoint case the same spec declares harmless:
    `get_bases` reads `edges` alone and reports the endpoint's name.
    """
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="alib.core::Base",
                name="Base",
                module="alib.core",
                package="alib",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="blib.impl::Sub",
                name="Sub",
                module="blib.impl",
                package="blib",
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src="blib.impl::Sub",
                dst="alib.core::Base",
                kind=EdgeKind.INHERITS,
            )
        )
        store.flush()
        assert [
            node.qualified_name for node in store.get_bases("blib.impl::Sub")
        ] == ["alib.core::Base"]

        store.clear_package("alib")

        assert [
            node.qualified_name for node in store.get_bases("blib.impl::Sub")
        ] == ["alib.core::Base"]
        assert store.get_node("blib.impl::Sub") is not None
        assert store.get_node("alib.core::Base") is None


def test_get_inheritors_after_base_package_cleared(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`clear_package` on a base's package keeps its inheritors.

    NOTE: Validation criterion 4 - the same surviving edge read from
    the other direction. `get_inheritors` JOINs `nodes` on the edge's
    `src`, which is the subclass's own node in the uncleared package,
    so the row is still reportable. The fixture clears `alib` and does
    not rebuild it.
    """
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="alib.core::Base",
                name="Base",
                module="alib.core",
                package="alib",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="blib.impl::Sub",
                name="Sub",
                module="blib.impl",
                package="blib",
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src="blib.impl::Sub",
                dst="alib.core::Base",
                kind=EdgeKind.INHERITS,
            )
        )
        store.flush()

        store.clear_package("alib")

        assert [
            node.qualified_name
            for node in store.get_inheritors("alib.core::Base")
        ] == ["blib.impl::Sub"]


def test_clear_package_removes_edges_it_owns(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`clear_package` deletes every edge the package's walk recorded.

    NOTE: Validation criterion 1 - the half the narrowed `DELETE` must
    keep doing. The `blib` walk recorded both edges (an `INHERITS` to a
    base in another package and a `CONTAINS` to its own member), so
    clearing `blib` removes both, while the untouched `alib` node
    stays.
    """
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="alib.core::Base",
                name="Base",
                module="alib.core",
                package="alib",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="blib.impl::Sub",
                name="Sub",
                module="blib.impl",
                package="blib",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="blib.impl::Sub.run",
                kind=NodeKind.METHOD,
                name="run",
                module="blib.impl",
                package="blib",
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src="blib.impl::Sub",
                dst="alib.core::Base",
                kind=EdgeKind.INHERITS,
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src="blib.impl::Sub",
                dst="blib.impl::Sub.run",
                kind=EdgeKind.CONTAINS,
            )
        )
        store.flush()

        store.clear_package("blib")

        remaining = store._connection.execute(
            "SELECT src, dst, kind FROM edges"
        ).fetchall()
        assert [tuple(row) for row in remaining] == []
        assert store.get_node("alib.core::Base") is not None


def test_clear_package_keeps_a_foreign_walks_inherits_edge(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`clear_package` keeps an edge another package's walk recorded.

    NOTE: Validation criterion 2, asserted on the `edges` table rather
    than through a reader, so it pins the deletion scope itself. An
    `INHERITS` edge is written from the *subclass's* side, so clearing
    the base's package must leave the row exactly as the `blib` walk
    wrote it - and the fixture never rebuilds `alib`, because a graph
    holding both packages passes either deletion scope.
    """
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="alib.core::Base",
                name="Base",
                module="alib.core",
                package="alib",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="blib.impl::Sub",
                name="Sub",
                module="blib.impl",
                package="blib",
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src="blib.impl::Sub",
                dst="alib.core::Base",
                kind=EdgeKind.INHERITS,
            )
        )
        store.flush()

        store.clear_package("alib")

        remaining = store._connection.execute(
            "SELECT src, dst, kind FROM edges"
        ).fetchall()
        assert [tuple(row) for row in remaining] == [
            ("blib.impl::Sub", "alib.core::Base", str(EdgeKind.INHERITS))
        ]


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


def test_search_symbols_underscore_matches_literal_like_fallback(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The `LIKE` fallback matches a `_` in the query literally:
    `print_json` does not return `printXjson`, which matches only by
    reading the `_` as a single-character wildcard
    ([#108](https://github.com/andyrids/venv-axi/issues/108))."""
    with SymbolStore(tmp_path / "store.db") as store:
        store._fts_enabled = False
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::print_json",
                kind=NodeKind.FUNCTION,
                name="print_json",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::printXjson",
                kind=NodeKind.FUNCTION,
                name="printXjson",
            )
        )
        results = store.search_symbols("print_json")
    assert [node.name for node in results] == ["print_json"]


def test_search_symbols_docstring_only_match_like_fallback(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The `LIKE` fallback finds a symbol via a docstring-only query -
    the query string appears in neither `name` nor `qualified_name`."""
    with SymbolStore(tmp_path / "store.db") as store:
        store._fts_enabled = False
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::Widget",
                name="Widget",
                doc="A flibbertigibbet transport.",
            )
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Gadget", name="Gadget")
        )
        results = store.search_symbols("flibbertigibbet")
    assert [node.name for node in results] == ["Widget"]


def test_search_symbols_docstring_only_match_filters_by_package_like_fallback(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A docstring-only match still honors the `package` scope on the
    `LIKE` fallback path - catches a binding off-by-one that would
    drop or misalign the package filter."""
    with SymbolStore(tmp_path / "store.db") as store:
        store._fts_enabled = False
        store.upsert_node(
            make_symbol_node(
                qualified_name="a::Widget",
                name="Widget",
                package="a",
                doc="A flibbertigibbet transport.",
            )
        )
        store.upsert_node(
            make_symbol_node(
                qualified_name="b::Gizmo",
                name="Gizmo",
                package="b",
                doc="A flibbertigibbet transport.",
            )
        )
        scoped = store.search_symbols("flibbertigibbet", package="a")
        unscoped = store.search_symbols("flibbertigibbet")
    assert [node.package for node in scoped] == ["a"]
    assert len(unscoped) == 2


def test_search_symbols_docstring_only_match_respects_limit_like_fallback(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """A docstring-only match still honors `limit` on the `LIKE`
    fallback path - catches a binding off-by-one that would misalign
    the trailing `LIMIT ?` placeholder."""
    with SymbolStore(tmp_path / "store.db") as store:
        store._fts_enabled = False
        for index in range(5):
            store.upsert_node(
                make_symbol_node(
                    qualified_name=f"pkg::Sym{index}",
                    name=f"Sym{index}",
                    doc="A flibbertigibbet transport.",
                )
            )
        results = store.search_symbols("flibbertigibbet", limit=2)
    assert len(results) == 2


def test_search_symbols_docstring_only_match_fts(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """The FTS5 path (default, unchanged by this fix) already finds a
    symbol via a docstring-only query."""
    with SymbolStore(tmp_path / "store.db") as store:
        store.upsert_node(
            make_symbol_node(
                qualified_name="pkg::Widget",
                name="Widget",
                doc="A flibbertigibbet transport.",
            )
        )
        store.upsert_node(
            make_symbol_node(qualified_name="pkg::Gadget", name="Gadget")
        )
        results = store.search_symbols("flibbertigibbet")
    assert [node.name for node in results] == ["Widget"]


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


def test_schema_version_7_empty_version_row_evicted_on_open(
    tmp_path: Path,
) -> None:
    """A cache database recorded at schema version 7, holding a
    `package_builds` row with `version = ""` - the exact stale shape
    issue #89 reports, produced by resolving an import name as if it
    were a distribution name - is dropped and rebuilt on next open,
    regardless of its recorded build version (Validation criterion 9)."""
    db_path = tmp_path / "store.db"
    SymbolStore(db_path).close()

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA user_version = 7")
    connection.execute(
        "INSERT INTO package_builds (package, version, max_depth)"
        " VALUES ('dns', '', 2)"
    )
    connection.commit()
    connection.close()

    with SymbolStore(db_path) as store:
        assert store.get_build("dns") is None
        (version,) = store._connection.execute(
            "PRAGMA user_version"
        ).fetchone()
        assert version == SCHEMA_VERSION


def test_schema_version_8_wider_deletion_scope_evicted_on_open(
    tmp_path: Path,
) -> None:
    """A cache recorded at schema version 8 is dropped on next open.

    NOTE: Validation criterion 8. Version 8 is the *previous* version,
    written before `clear_package` narrowed to the `src` arm, so such
    a cache can hold a subclass whose ancestry an unrelated refresh
    removed (#124) - a gap no rebuild of the refreshed package
    restores, and which would falsify the definitive `--bases` empty
    state. The bump is what evicts it
    (`specs/behaviors/cache-refresh.md`, Schema version covers the
    builder, not just the shape).
    """
    db_path = tmp_path / "store.db"
    SymbolStore(db_path).close()

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA user_version = 8")
    connection.execute(
        "INSERT INTO nodes (qualified_name, kind, name, module, signature,"
        " doc, package, version, home_qualified_name) VALUES"
        " ('blib.impl::Sub', 'class', 'Sub', 'blib.impl', '', '', 'blib',"
        " '1.0.0', 'blib.impl::Sub')"
    )
    connection.commit()
    connection.close()

    with SymbolStore(db_path) as store:
        assert store.get_node("blib.impl::Sub") is None
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


def test_count_nodes_counts_only_the_named_package(
    tmp_path: Path, make_symbol_node: NodeFactory
) -> None:
    """`count_nodes` counts a package's own nodes, never a neighbour's -
    the refresh receipt's `symbols` field describes one walk."""
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
                qualified_name="other::Bar", name="Bar", package="other"
            )
        )
        assert store.count_nodes("pkg") == 2
        assert store.count_nodes("other") == 1


def test_count_nodes_unbuilt_package_is_zero(tmp_path: Path) -> None:
    """A package holding no graph counts zero rather than raising - a
    failed rebuild leaves the package unindexed, not absent."""
    with SymbolStore(tmp_path / "store.db") as store:
        assert store.count_nodes("never_built") == 0
