"""Unit tests for the `find` result-ordering contract.

Regression coverage for the five-key total order declared in
`specs/commands/find.md` under `### Result ordering`, driven through
`venvaxi._introspect.find_symbol` on both search backends.

NOTE: The relevance gap the spec leaves *deliberately unspecified*
between key 3 and key 4 (FTS5 `bm25`; absent on the `LIKE` fallback) is
not asserted anywhere in this module - a test there would make one
backend's behaviour the contract. Fixtures for keys 4 and 5 are built
with identical FTS token statistics (same name, same token count, same
matched terms, empty docs) so `bm25` ties exactly and the key under
test is what breaks the tie on the FTS path too.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from venvaxi._cache import get_cache_db_path
from venvaxi._core import get_project_root
from venvaxi._introspect import find_symbol
from venvaxi._store import NodeKind, SymbolNode, SymbolStore

NodeFactory = Callable[..., SymbolNode]


def _seed_and_find(
    nodes: Sequence[SymbolNode], query: str
) -> list[SymbolNode]:
    """Seed the project cache via the store write path, then search.

    Nodes are written through `SymbolStore.upsert_node` - the same call
    the introspection walk uses - so `find_symbol` exercises the real
    search SQL rather than a hand-rolled ORDER BY.

    Args:
        nodes: The fixture graph to persist.
        query: The free-text search query.

    Returns:
        Matching `SymbolNode` instance(s), best match first.
    """
    with SymbolStore(get_cache_db_path(get_project_root())) as store:
        for node in nodes:
            store.upsert_node(node)
        store.flush()
    return find_symbol(query)


@pytest.fixture(params=["fts", "like"])
def search_backend(
    request: pytest.FixtureRequest,
    isolated_cache: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Run the dependent test once per search backend.

    The `like` variant disables the FTS path after schema creation,
    mirroring how `SymbolStore` degrades when FTS5 is unavailable, so
    every assertion holds on both ORDER BY clauses.
    """
    if request.param == "like":
        original_init = SymbolStore.__init__

        def _init_without_fts(self: SymbolStore, db_path: Path) -> None:
            original_init(self, db_path)
            self._fts_enabled = False

        monkeypatch.setattr(SymbolStore, "__init__", _init_without_fts)
    return request.param


def test_find_orders_exact_name_match_before_prefix_match(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """Key 1: a case-insensitive exact name match sorts before a prefix
    match. The exact node carries the *longer* `qualified_name`, so key
    4 alone would reverse this order - the assertion fails if key 1 is
    removed."""
    nodes = [
        make_symbol_node(
            qualified_name="pkg::WidgetError", name="WidgetError"
        ),
        make_symbol_node(qualified_name="pkg.gadgets::Widget", name="Widget"),
    ]
    results = _seed_and_find(nodes, "widget")
    assert [node.name for node in results] == ["Widget", "WidgetError"]


def test_find_orders_prefix_match_before_docstring_only_match(
    isolated_cache: Path, make_symbol_node: NodeFactory
) -> None:
    """Key 2: a name-prefix match sorts before a docstring-only match,
    even when the docstring-only node has the far shorter
    `qualified_name` that key 4 would prefer.

    NOTE: FTS backend only - the `LIKE` fallback does not match
    docstrings at all, so a doc-only hit cannot exist on that path. The
    docstring repeats the query term enough that `bm25` alone would
    rank the doc-only node first, so key 2 is the only reason this
    assertion holds - it fails if key 2 is removed.
    """
    nodes = [
        make_symbol_node(
            qualified_name="pkg::Assembler",
            name="Assembler",
            doc="Assemble a Widget. Wraps Widget parts, Widget tools "
            "and Widget jigs into one finished Widget.",
        ),
        make_symbol_node(
            qualified_name="pkg.gadgets.errors::WidgetError",
            name="WidgetError",
        ),
    ]
    results = _seed_and_find(nodes, "Widget")
    assert [node.name for node in results] == ["WidgetError", "Assembler"]


def test_find_orders_class_kind_before_module_kind(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """Key 3: with names identical (keys 1 and 2 tied), a `class` sorts
    before a `module`. The module carries the shorter `qualified_name`,
    so key 4 alone would reverse this order."""
    nodes = [
        make_symbol_node(
            qualified_name="pkg.parser", kind=NodeKind.MODULE, name="parser"
        ),
        make_symbol_node(
            qualified_name="pkg.deep.impl::parser",
            kind=NodeKind.CLASS,
            name="parser",
        ),
    ]
    results = _seed_and_find(nodes, "parser")
    assert [node.kind for node in results] == [
        NodeKind.CLASS,
        NodeKind.MODULE,
    ]


def test_find_orders_shorter_qualified_name_first(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """Key 4: tied on name and kind, the shorter `qualified_name` sorts
    first. The shorter name is lexically *greater* (`zz` > `abc`), so
    key 5 alone would reverse this order - the assertion fails if key 4
    is removed."""
    nodes = [
        make_symbol_node(qualified_name="pkg.abc::Widget", name="Widget"),
        make_symbol_node(qualified_name="pkg.zz::Widget", name="Widget"),
    ]
    results = _seed_and_find(nodes, "Widget")
    assert [node.qualified_name for node in results] == [
        "pkg.zz::Widget",
        "pkg.abc::Widget",
    ]


def test_find_breaks_final_ties_on_qualified_name_ascending(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """Key 5: tied on every earlier key and equal in `qualified_name`
    length, rows order by `qualified_name` ascending. The lexically
    greater row is inserted first, so insertion order cannot produce
    the pass."""
    nodes = [
        make_symbol_node(qualified_name="pkg.gamma::Widget", name="Widget"),
        make_symbol_node(qualified_name="pkg.alpha::Widget", name="Widget"),
    ]
    results = _seed_and_find(nodes, "Widget")
    assert [node.qualified_name for node in results] == [
        "pkg.alpha::Widget",
        "pkg.gamma::Widget",
    ]


def test_find_repeats_identical_rows_in_identical_order(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """The same query run twice against an unchanged graph returns
    identical rows in identical order - the property key 5 makes the
    order total for."""
    nodes = [
        make_symbol_node(qualified_name="pkg.gamma::Widget", name="Widget"),
        make_symbol_node(
            qualified_name="pkg::WidgetError", name="WidgetError"
        ),
        make_symbol_node(qualified_name="pkg.abc::Widget", name="Widget"),
        make_symbol_node(qualified_name="pkg.zz::Widget", name="Widget"),
        make_symbol_node(qualified_name="pkg.alpha::Widget", name="Widget"),
        make_symbol_node(
            qualified_name="pkg::Assembler",
            name="Assembler",
            doc="Builds a Widget from parts.",
        ),
    ]
    first = _seed_and_find(nodes, "Widget")
    second = find_symbol("Widget")
    assert first
    assert first == second
