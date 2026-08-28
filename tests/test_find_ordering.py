"""Unit tests for the `find` result-ordering contract.

Regression coverage for the six-key total order declared in
`specs/commands/find.md` under `### Result ordering`, driven through
`venvaxi._introspect.find_symbol` on both search backends.

NOTE: The relevance gap the spec leaves *deliberately unspecified*
between key 4 and key 5 (FTS5 `bm25`; absent on the `LIKE` fallback) is
not asserted anywhere in this module - a test there would make one
backend's behaviour the contract. Fixtures for keys 5 and 6 are built
with identical FTS token statistics (same name, same token count, same
matched terms, empty docs) so `bm25` ties exactly and the key under
test is what breaks the tie on the FTS path too.

NOTE: Key 3 is asserted on `search_like.sql` only, on *both* fixture
parameters. A path-shaped query cannot reach `search_fts.sql` at all -
FTS5's query grammar rejects an unquoted `.` or `:`, so `search_symbols`
raises `sqlite3.OperationalError` and routes it to the `LIKE` fallback
before MATCH is evaluated. Key 3's copy in `search_fts.sql` is mirrored
so the two files state one ordering contract rather than two, but it is
unexercised: deleting it from that file leaves every assertion here
passing (verified at the stage 02 review gate). Do not read a `[fts]`
parameter on a path-shaped test as proof that clause works.
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
    every assertion holds on both ORDER BY clauses - except for a
    path-shaped query, which reaches `search_like.sql` under either
    parameter. See this module's docstring.
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
    5 alone would reverse this order - the assertion fails if key 1 is
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
    `qualified_name` that key 5 would prefer.

    NOTE: This test does not use the `search_backend` fixture, so it
    only exercises the FTS path - unrelated to this fix. (A stale claim
    previously stood here that the `LIKE` fallback does not match
    docstrings at all; that predates #79/PR #83, which added the `doc`
    disjunct to `search_like.sql` too.) The docstring repeats the query
    term enough that `bm25` alone would rank the doc-only node first,
    so key 2 is the only reason this assertion holds - it fails if key
    2 is removed.
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


def test_find_orders_qualified_name_suffix_match_before_kind_tier(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """Key 3: a path-shaped query whose `qualified_name` ends with it,
    preceded by `.` or `::`, outranks a `class` row that ties on keys 1
    and 2 and also matches (its `qualified_name` contains the query as
    a substring, just not as a suffix). The class carries the
    *shorter* `qualified_name`, so keys 4 and 5 alone would reverse
    this order - the assertion fails if key 3 is removed
    ([#94](https://github.com/andyrids/venv-axi/issues/94))."""
    nodes = [
        make_symbol_node(
            qualified_name="pkg::AltOwner.method",
            kind=NodeKind.CLASS,
            name="AltOwner.method",
        ),
        make_symbol_node(
            qualified_name="pkg.deep.impl::Owner.method",
            kind=NodeKind.METHOD,
            name="method",
        ),
    ]
    results = _seed_and_find(nodes, "Owner.method")
    assert [node.qualified_name for node in results] == [
        "pkg.deep.impl::Owner.method",
        "pkg::AltOwner.method",
    ]


def test_find_path_shaped_query_excludes_docstring_only_match(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """A path-shaped query does not return a row that matches only in
    its `doc`, even when the doc text contains the query literally -
    prose about a symbol is not a spelling of it (`specs/commands/
    find.md`, Data requirements;
    [#94](https://github.com/andyrids/venv-axi/issues/94))."""
    nodes = [
        make_symbol_node(
            qualified_name="rich.align::Align",
            kind=NodeKind.CLASS,
            name="Align",
            doc="Example: console.print(Align.center('hi')).",
        ),
    ]
    results = _seed_and_find(nodes, "Console.print")
    assert results == []


def test_find_bare_query_still_matches_docstring_only(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """Contrast to the path-shaped narrowing above, on the same fixture
    graph: a bare query (no `.` or `::`) still returns a docstring-only
    match on both backends - the surface #79/PR #83 brought into
    conformance stays intact for every non-path-shaped query.

    Regression guard: this assertion passes against the pre-fix code
    too, since a bare query never reaches the new predicate. The pair
    with the test above is the whole point - one assertion alone proves
    nothing about scope.
    """
    nodes = [
        make_symbol_node(
            qualified_name="rich.align::Align",
            kind=NodeKind.CLASS,
            name="Align",
            doc="Example: console.print(Align.center('hi')).",
        ),
    ]
    results = _seed_and_find(nodes, "console")
    assert [node.name for node in results] == ["Align"]


def test_find_colon_only_query_ranks_and_narrows_like_dotted(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """A `::`-shaped query with no `.` is treated as path-shaped by
    both key 3 and the docstring narrowing - `"::" in query` is not
    redundant beside `"." in query` (`mod::Class` carries a separator
    and no dot). One test asserts both halves: the suffix match ranks
    above a shorter, kind-preferred competitor, and the docstring-only
    row is excluded entirely."""
    nodes = [
        make_symbol_node(
            qualified_name="modx.pkg::Widget",
            kind=NodeKind.METHOD,
            name="Widget",
        ),
        make_symbol_node(
            qualified_name="pkg::WidgetXtra",
            kind=NodeKind.CLASS,
            name="WidgetXtra",
        ),
        make_symbol_node(
            qualified_name="other::DocOnly",
            kind=NodeKind.CLASS,
            name="DocOnly",
            doc="Mentions pkg::Widget in prose.",
        ),
    ]
    results = _seed_and_find(nodes, "pkg::Widget")
    assert [node.qualified_name for node in results] == [
        "modx.pkg::Widget",
        "pkg::WidgetXtra",
    ]


def test_find_orders_class_kind_before_module_kind(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """Key 4: with names identical (keys 1 and 2 tied, and key 3 tied
    since both `qualified_name`s end `.parser`/`::parser`), a `class`
    sorts before a `module`. The module carries the shorter
    `qualified_name`, so key 5 alone would reverse this order."""
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
    """Key 5: tied on name, key 3 and kind, the shorter `qualified_name`
    sorts first. The shorter name is lexically *greater* (`zz` > `abc`),
    so key 6 alone would reverse this order - the assertion fails if
    key 5 is removed."""
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
    """Key 6: tied on every earlier key and equal in `qualified_name`
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
    identical rows in identical order - the property key 6 makes the
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
