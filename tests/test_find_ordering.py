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
parameter on a path-shaped test as proof that clause works. The
literal-matching tests (#108) sit under the same convention: key 2's
escaped copy in `search_fts.sql` is likewise mirrored but unexercised,
and each such test states which parameter proves what. A `_`-query
membership assertion is meaningful on `[like]` only - unicode61 splits
`print_json` into `print` and `json`, so the single-token competitor
`printXjson` never enters the FTS candidate set and that parameter
passes with or without escaping. A `%` or `\\` query reaches
`search_like.sql` under either parameter - FTS5 rejects both with a
syntax error, routing them to the fallback. The `_`-query ranking test
runs on the fallback only: `bm25` sits in the deliberately unspecified
gap between keys 4 and 5 on the FTS path and would own the tie that
test pins on key 5.
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


@pytest.fixture
def like_only(isolated_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable the FTS path after schema creation, mirroring how
    `SymbolStore` degrades when FTS5 is unavailable.

    Both the `search_backend` `like` parameter and the tests that run
    on `search_like.sql` alone consume this, so the degradation is
    described in one place rather than restated per caller.
    """
    original_init = SymbolStore.__init__

    def _init_without_fts(self: SymbolStore, db_path: Path) -> None:
        original_init(self, db_path)
        self._fts_enabled = False

    monkeypatch.setattr(SymbolStore, "__init__", _init_without_fts)


@pytest.fixture(params=["fts", "like"])
def search_backend(
    request: pytest.FixtureRequest, isolated_cache: Path
) -> str:
    """Run the dependent test once per search backend.

    The `like` variant takes `like_only`, so every assertion holds on
    both ORDER BY clauses - except for a path-shaped query, which
    reaches `search_like.sql` under either parameter. See this module's
    docstring.
    """
    if request.param == "like":
        request.getfixturevalue("like_only")
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


def test_find_underscore_query_matches_literal_substring_only(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """A `_` in the query matches only itself: `print_json` does not
    return `printXjson`, which matches only by substituting `X` for
    the `_` (`specs/commands/find.md`, Literal matching;
    [#108](https://github.com/andyrids/venv-axi/issues/108)).

    NOTE: Meaningful on `[like]` only - the competitor never enters
    the FTS candidate set, so that parameter passes with or without
    escaping. See the module docstring.
    """
    nodes = [
        make_symbol_node(
            qualified_name="pkg.mod::print_json",
            kind=NodeKind.FUNCTION,
            name="print_json",
        ),
        make_symbol_node(
            qualified_name="pkg.mod::printXjson",
            kind=NodeKind.FUNCTION,
            name="printXjson",
        ),
    ]
    results = _seed_and_find(nodes, "print_json")
    assert [node.name for node in results] == ["print_json"]


def test_find_percent_query_matches_literal_substring_only(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    """A `%` in the query matches only itself: `print%json` returns
    the row whose docstring carries `print%json` literally, and not
    `print_json`, which matches only by reading the `%` as a wildcard.

    Meaningful on both fixture parameters: FTS5 rejects `%` with
    `fts5: syntax error near "%"`, so `search_symbols` routes the
    query to the `LIKE` fallback under `[fts]` too (re-confirmed at
    stage 02 against this venv's SQLite 3.50.4).
    """
    nodes = [
        make_symbol_node(
            qualified_name="pkg.mod::print_json",
            kind=NodeKind.FUNCTION,
            name="print_json",
        ),
        make_symbol_node(
            qualified_name="pkg.mod::emit_markers",
            kind=NodeKind.FUNCTION,
            name="emit_markers",
            doc="Writes print%json markers.",
        ),
    ]
    results = _seed_and_find(nodes, "print%json")
    assert [node.name for node in results] == ["emit_markers"]


def test_find_underscore_query_does_not_rank_wildcard_prefix(
    like_only: None, make_symbol_node: NodeFactory
) -> None:
    """Key 2 compares a `_` literally: `printXjson` begins with
    `print_json` only under wildcard substitution, so it must not rank
    above `use_print_json`, whose name does not begin with the query
    at all. Both rows stay in the result set either way - the wildcard
    row matches through its docstring - so this asserts ranking, not
    membership (the fixture trap `plans/find-path-shaped-query.md`
    records in its Notes). Post-fix, key 2 is false for both rows and
    key 5 puts the shorter `qualified_name` first.

    NOTE: Asserted on `search_like.sql` only - `bm25` would own this
    tie on the FTS path. See the module docstring.
    """
    nodes = [
        make_symbol_node(
            qualified_name="pkg.deep.impl::printXjson",
            kind=NodeKind.FUNCTION,
            name="printXjson",
            doc="Formats print_json output.",
        ),
        make_symbol_node(
            qualified_name="pkg::use_print_json",
            kind=NodeKind.FUNCTION,
            name="use_print_json",
        ),
    ]
    results = _seed_and_find(nodes, "print_json")
    assert [node.name for node in results] == [
        "use_print_json",
        "printXjson",
    ]


def test_find_backslash_query_matches_literal_backslash(
    search_backend: str, make_symbol_node: NodeFactory
) -> None:
    r"""A `\` in the query matches only itself, without raising:
    `a\b` returns the row whose docstring carries `a\b` literally, and
    not the row carrying plain `ab`. Meaningful on both fixture
    parameters - FTS5 rejects `\` with a syntax error, so both route
    to the `LIKE` fallback.

    Regression guard for `_escape_like`'s step order, and expected to
    pass pre-fix too: with no `ESCAPE` clause a `\` was already
    literal. The failure this pins is a helper that escapes `%` and
    `_` but not the escape character itself - its pattern reads `\b`
    as an escaped `b`, so this fixture returns the `ab` row and drops
    the `a\b` row, silently (plan Risks; shown failing by mutation at
    stage 02).
    """
    nodes = [
        make_symbol_node(
            qualified_name="pkg.mod::parse_escape",
            kind=NodeKind.FUNCTION,
            name="parse_escape",
            doc="Parses the a\\b escape form.",
        ),
        make_symbol_node(
            qualified_name="pkg.mod::parse_plain",
            kind=NodeKind.FUNCTION,
            name="parse_plain",
            doc="Parses the ab plain form.",
        ),
    ]
    results = _seed_and_find(nodes, "a\\b")
    assert [node.name for node in results] == ["parse_escape"]
