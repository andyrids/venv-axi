"""Agent eXperience Interface (AXI) Graph-Based Symbol Registry.

Stores a structural graph of introspected Python symbols including; packages,
modules, classes, functions, methods, attributes and their relationships.

Attribution:
    The SQLite Node|Edge graph architecture used in this module is inspired by
    `code-review-graph`.

    NOTE: `code-review-graph` populates its graph from a static AST, whereas
    this store is populated from live object introspection.

    Repository: https://github.com/tirth8205/code-review-graph
    License: MIT License - Copyright (c) 2026 Tirth Kanani
"""

import logging
import sqlite3
from dataclasses import asdict, dataclass
from enum import StrEnum
from functools import cache
from importlib import resources
from pathlib import Path
from types import TracebackType
from typing import Self

logger = logging.getLogger(__package__)

SCHEMA_VERSION = 10
"""The cache schema version, stored as SQLite's `PRAGMA user_version`.

NOTE: Tracks *what the store ends up holding*, not only the table
shape, and two triggers sit under that. **What a walk records** - node
fields are computed at walk time and frozen into the store, so a change
to how a docstring, signature or home name is derived leaves every
existing cache serving the old value. **What a clear removes** - a
change to which edges `clear_package` deletes reaches the same place by
the opposite route: the walk is unchanged, so a rebuild writes what it
always wrote, but an existing cache still holds the result of the old
deletion scope and no rebuild of the package a caller happens to
refresh restores what a previous clear took from a package they do not.
Bump on either kind of change; see `specs/behaviors/cache-refresh.md`,
Schema version covers the builder, not just the shape.

NOTE: 6 - signatures are now recorded for every callable symbol
whatever its kind (#66); a version-5 cache serves `""` for callable
attributes indefinitely.

NOTE: 7 - `_doc_of` now keeps an `attribute`'s docstring when it is the
same as its type's, unless that type is standard-library (#82); a
version-6 cache serves `(no docstring)` for a package-defined singleton
(`pytest.fail`) indefinitely.

NOTE: 8 - the recorded build `version` is now resolved from the
distribution(s) claiming a package's import name, not from the import
name treated as a distribution name (#89); a version-7 cache may hold
`""` for any package whose import name differs from its distribution
name, which compared equal to itself forever and made version-based
invalidation never fire for that class.

NOTE: 9 - `clear_package` now deletes an edge only by its `src`
endpoint, so a refresh no longer removes an `INHERITS` edge another
package's walk recorded (#124); a version-8 cache can hold a subclass
whose ancestry a previous clear removed, which no rebuild of the
refreshed package can restore and which would falsify the definitive
`--bases` empty state (`specs/commands/inherits.md`, Empty states).

NOTE: 10 - the re-export filter's private-home carve-out now calls
`is_private_submodule` instead of re-spelling it inline, so a package
whose own root name starts with `_` (`_pytest`) no longer keeps a
public-sibling re-export below its root (#106); a version-9 cache built
for such a package holds the duplicate rows the fixed walk no longer
writes, which no rebuild of an unrelated package can restore and which
`specs/behaviors/symbol-graph.md` Re-exported symbols now says shall
not happen.
"""


class NodeKind(StrEnum):
    """The kind of a `SymbolNode`."""

    PACKAGE = "package"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    ATTRIBUTE = "attribute"


class EdgeKind(StrEnum):
    """The kind of a `SymbolEdge`."""

    EXPORTS = "exports"
    INHERITS = "inherits"
    CONTAINS = "contains"
    IMPORTS_FROM = "imports_from"
    DEPENDS_ON = "depends_on"


@dataclass(frozen=True, slots=True)
class SymbolNode:
    """A single node in the symbol graph.

    NOTE: `qualified_name` keys the node at the correct module (a facade for
    re-exports); `home_qualified_name` is the canonical `module::name` derived
    from the corresponding `__module__`|`__name__` for a symbol.
    """

    qualified_name: str
    kind: NodeKind
    name: str
    module: str
    signature: str
    doc: str
    package: str
    version: str
    home_qualified_name: str

    def as_row(self) -> dict[str, str]:
        """Convert this node to a flat, string-valued TOON row.

        Returns:
            A dict keyed by every `SymbolNode` field, suitable for
            `venvaxi._toon.encode_table`|`encode_object`.
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SymbolEdge:
    """A directed edge between two symbol graph nodes."""

    src: str
    dst: str
    kind: EdgeKind


def qualify(module: str, *parts: str) -> str:
    """Build a qualified symbol name.

    Args:
        module: The dotted name for an owning module.
        parts: One or more dotted name components.

    Returns:
        A `module::a.b.c` qualified name, or the bare `module` name
        when `parts` is empty (module|package node naming).
    """
    if not parts:
        return module
    return f"{module}::{'.'.join(parts)}"


@cache
def _read_sql(filename: str) -> str:
    """Load & cache SQL queries to prevent disk I/O on every execution."""
    return (resources.files(__package__) / filename).read_text("UTF-8")


def _escape_like(query: str) -> str:
    r"""Escape SQLite `LIKE` wildcards so `query` matches literally.

    NOTE: The escape character is replaced first - swapped steps
    double-escape the escapes just introduced, and SQLite reads the
    resulting pattern silently as the wrong literal (`a\b` matching
    `ab`; `specs/commands/find.md`, Literal matching).

    Args:
        query: The free-text search query.

    Returns:
        The query with `\`, `%` and `_` each preceded by `\`, for a
        `LIKE` pattern carrying an `ESCAPE '\'` clause.
    """
    return query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SymbolStore:
    """A SQLite-backed store for an introspected symbol graph."""

    def __init__(self, db_path: Path) -> None:
        """Open (or create) the symbol store database.

        Args:
            db_path: The path to the SQLite database file.
        """
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
        self._fts_enabled = True
        try:
            self._ensure_schema()
        except BaseException:
            self._connection.close()
            raise

    def __enter__(self) -> Self:
        """Return `self` for use as a context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the underlying database connection."""
        self.close()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._connection.close()

    def flush(self) -> None:
        """Commit any pending writes to disk."""
        self._connection.commit()

    def rollback(self) -> None:
        """Discard any pending (uncommitted) writes."""
        self._connection.rollback()

    def _ensure_schema(self) -> None:
        """Create the `nodes`|`edges` tables and FTS5 index if missing.

        On a `user_version` mismatch the existing tables are dropped and
        rebuilt - cache databases are disposable, so no migrations. Stale
        package data simply rebuilds via `_cache.is_cache_valid()`.
        """
        (version,) = self._connection.execute("PRAGMA user_version").fetchone()
        if version != SCHEMA_VERSION:
            self._connection.executescript(
                "DROP TABLE IF EXISTS symbols_fts;"
                "DROP TABLE IF EXISTS nodes;"
                "DROP TABLE IF EXISTS edges;"
                "DROP TABLE IF EXISTS package_builds;"
            )

        self._connection.executescript(_read_sql("schema.sql"))

        try:
            self._connection.executescript(_read_sql("schema_fts5.sql"))
        except sqlite3.OperationalError:
            logger.debug("FTS5 unavailable, falling back to LIKE search")
            self._fts_enabled = False
        if version != SCHEMA_VERSION:
            self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self._connection.commit()

    def upsert_node(self, node: SymbolNode) -> None:
        """Insert or update a symbol node.

        NOTE: Writes stay pending until `flush()` - callers batching many
        upserts (e.g. an introspection walk) commit once at the end. The
        FTS5 index is kept in sync by `schema_fts5.sql` triggers.

        Args:
            node: The `SymbolNode` to persist.
        """
        self._connection.execute(
            _read_sql("upsert_node.sql"),
            (
                node.qualified_name,
                str(node.kind),
                node.name,
                node.module,
                node.signature,
                node.doc,
                node.package,
                node.version,
                node.home_qualified_name,
            ),
        )

    def upsert_edge(self, edge: SymbolEdge) -> None:
        """Insert an edge, ignoring if already present.

        NOTE: Writes stay pending until `flush()` - see `upsert_node`.

        Args:
            edge: The `SymbolEdge` to persist.
        """
        self._connection.execute(
            _read_sql("upsert_edge.sql"),
            (edge.src, edge.dst, str(edge.kind)),
        )

    def _row_to_node(self, row: sqlite3.Row) -> SymbolNode:
        """Map a raw `nodes` row to a typed `SymbolNode`.

        NOTE: Column names MUST match `SymbolNode` fields 1:1 - queries
        always project `nodes.*` & `strict=True` surfaces any drift.

        Args:
            row: A raw `sqlite3.Row` from the `nodes` table.

        Returns:
            The corresponding `SymbolNode`.
        """
        data = dict(zip(row.keys(), row, strict=True))
        data["kind"] = NodeKind(data["kind"])
        return SymbolNode(**data)

    def get_node(self, qualified_name: str) -> SymbolNode | None:
        """Fetch a single node by qualified name.

        Args:
            qualified_name: The node's qualified name.

        Returns:
            The matching `SymbolNode`, or `None` if not found.
        """
        cursor = self._connection.execute(
            "SELECT * FROM nodes WHERE qualified_name = ?", (qualified_name,)
        )
        row = cursor.fetchone()
        return self._row_to_node(row) if row else None

    def get_children(self, qualified_name: str) -> list[SymbolNode]:
        """Fetch direct `CONTAINS` children of a node.

        Args:
            qualified_name: The parent node's qualified name.

        Returns:
            The child `SymbolNode`s, ordered by name.
        """
        cursor = self._connection.execute(
            _read_sql("get_children.sql"),
            (qualified_name, str(EdgeKind.CONTAINS)),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]

    def canonical_name(self, qualified_name: str) -> str:
        """Resolve a qualified name to its canonical (home) form.

        NOTE: Nodes are keyed at their containing (facade) module, while
        `INHERITS`|`CONTAINS` edges are keyed at the home module.

        Args:
            qualified_name: The (possibly facade-keyed) qualified name.

        Returns:
            The `home_qualified_name`|`qualified_name` for a node.
        """
        node = self.get_node(qualified_name)
        return qualified_name if node is None else node.home_qualified_name

    def get_inheritors(self, qualified_name: str) -> list[SymbolNode]:
        """Fetch classes that directly inherit from a node.

        NOTE: `INHERITS` edges are keyed at the home module of a class,
        so `qualified_name` resolves through `canonical_name`.

        Args:
            qualified_name: The qualified name of the base class.

        Returns:
            The inheriting `SymbolNode` instances, ordered by name.
        """
        cursor = self._connection.execute(
            _read_sql("get_inheritors.sql"),
            (self.canonical_name(qualified_name), str(EdgeKind.INHERITS)),
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]

    def get_bases(self, qualified_name: str) -> list[SymbolNode]:
        """Fetch the classes a class directly inherits from.

        NOTE: `INHERITS` edges are keyed at the home module of a class,
        so `qualified_name` resolves through `canonical_name`.

        NOTE: Reads `edges` alone (`get_bases.sql`) - the walk records
        an `INHERITS` edge for every base except `object`, but writes
        no node row for a base homed in a never-indexed package, so a
        `nodes` JOIN would silently drop exactly the cross-package
        bases this query exists to report. Each row derives from the
        edge instead: `kind` is `class` (a base is always a class - a
        fact about the edge, not a guess about a missing row) and
        `name` is the tail of the qualified name.

        Args:
            qualified_name: The qualified name of the subclass.

        Returns:
            One `SymbolNode` per direct base, ordered by qualified name.
        """
        cursor = self._connection.execute(
            _read_sql("get_bases.sql"),
            (self.canonical_name(qualified_name), str(EdgeKind.INHERITS)),
        )
        bases: list[SymbolNode] = []
        for row in cursor.fetchall():
            base_qualified_name = row["dst"]
            module, _, name = base_qualified_name.rpartition("::")
            bases.append(
                SymbolNode(
                    qualified_name=base_qualified_name,
                    kind=NodeKind.CLASS,
                    name=name,
                    module=module,
                    signature="",
                    doc="",
                    package="",
                    version="",
                    home_qualified_name=base_qualified_name,
                )
            )
        return bases

    def _collect_module_tree(
        self,
        qualified_name: str,
        depth: int,
        max_depth: int,
        result: list[tuple[int, SymbolNode]],
    ) -> None:
        """Append `MODULE`|`PACKAGE` descendants to `result` (recursive).

        Args:
            qualified_name: The current node's qualified name.
            depth: The current recursion depth.
            max_depth: The maximum recursion depth.
            result: The accumulator list of `(depth, node)` pairs.
        """
        if depth > max_depth:
            return
        for child in self.get_children(qualified_name):
            if child.kind not in (NodeKind.MODULE, NodeKind.PACKAGE):
                continue
            result.append((depth, child))
            self._collect_module_tree(
                child.qualified_name, depth + 1, max_depth, result
            )

    def get_module_tree(
        self, module_name: str, max_depth: int = 2
    ) -> list[tuple[int, SymbolNode]]:
        """Walk the `CONTAINS` module|package hierarchy depth-first.

        Args:
            module_name: The qualified (bare) name of the root module.
            max_depth: The maximum recursion depth.

        Returns:
            `(depth, node)` pairs in depth-first order, restricted to
            `MODULE`|`PACKAGE` kind nodes.
        """
        root = self.get_node(module_name)
        if root is None:
            return []
        result: list[tuple[int, SymbolNode]] = [(0, root)]
        self._collect_module_tree(module_name, 1, max_depth, result)
        return result

    def search_symbols(
        self, query: str, limit: int = 20, package: str | None = None
    ) -> list[SymbolNode]:
        """Search symbols by name|docstring via FTS5 with a `LIKE` fallback.

        NOTE: Both paths share one deterministic ordering contract;
        exact name match, name-prefix match, qualified-name suffix
        match (path-shaped query only), class|function kind, relevance
        (FTS5 `bm25`; omitted on the fallback), qualified name length
        and then qualified name. A path-shaped query - one containing
        `.` or `::` - matches `name`|`qualified_name` only; it is never
        matched against docstring text. The query is matched literally
        on every `LIKE` surface - the fallback's match pattern and both
        paths' name-prefix key take the `_escape_like`d query with an
        `ESCAPE` clause, so a `\\`, `%` or `_` in a query is a
        character, never a wildcard.

        Args:
            query: The free-text search query.
            limit: The maximum number of results.
            package: Restrict matches to one package (import) name or `None`
                to search all cached packages.

        Returns:
            Matching `SymbolNode` instance(s), best match first.
        """
        path_shaped = "." in query or "::" in query
        escaped = _escape_like(query)
        if self._fts_enabled:
            try:
                cursor = self._connection.execute(
                    _read_sql("search_fts.sql"),
                    {
                        "match": f"{query}*",
                        "package": package,
                        "query": query,
                        "query_escaped": escaped,
                        "limit": limit,
                    },
                )
                return [self._row_to_node(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                logger.debug("FTS5 query failed (`%s`), using LIKE", query)

        like_pattern = f"%{escaped}%"
        cursor = self._connection.execute(
            _read_sql("search_like.sql"),
            {
                "pattern": like_pattern,
                "doc_pattern": None if path_shaped else like_pattern,
                "package": package,
                "query": query,
                "query_escaped": escaped,
                "limit": limit,
            },
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]

    def record_build(self, package: str, version: str, max_depth: int) -> None:
        """Record the version & depth for a package graph.

        NOTE: Writes stay pending until `flush()`, so an interrupted walk
        invalidates any previous build record.

        Args:
            package: The package (import) name.
            version: The installed version walked.
            max_depth: The submodule recursion depth walked.
        """
        self._connection.execute(
            "INSERT INTO package_builds (package, version, max_depth)"
            " VALUES (?, ?, ?) ON CONFLICT(package) DO UPDATE SET"
            " version = excluded.version, max_depth = excluded.max_depth",
            (package, version, max_depth),
        )

    def get_build(self, package: str) -> tuple[str, int] | None:
        """Fetch the version & depth for a package graph.

        Args:
            package: The package (import) name.

        Returns:
            The `(version, max_depth)` pair, or `None` if never built.
        """
        row = self._connection.execute(
            "SELECT version, max_depth FROM package_builds WHERE package = ?",
            (package,),
        ).fetchone()
        return None if row is None else (row["version"], row["max_depth"])

    def count_nodes(self, package: str) -> int:
        """Count the symbol nodes recorded for a package graph.

        Args:
            package: The package (import) name.

        Returns:
            The number of `nodes` rows belonging to `package`, or `0`
            if the package holds no graph.
        """
        row = self._connection.execute(
            "SELECT COUNT(*) AS total FROM nodes WHERE package = ?",
            (package,),
        ).fetchone()
        return int(row["total"])

    def clear_package(self, package: str) -> None:
        """Delete all nodes|edges belonging to a package.

        NOTE: Avoids Python-to-C context switching and N+1 query problem with
        sub-queries.

        NOTE: Edges are deleted by `src` alone, never by `dst`. An edge
        is owned by the walk that recorded it, and a walk records an
        edge only where the relationship's origin is a symbol it is
        walking - so ownership rides the origin endpoint and a clear
        deletes only what it owns (`specs/behaviors/cache-refresh.md`,
        Refresh scope: edges). A `dst` arm would delete another
        package's recorded facts: an `INHERITS` edge is written from
        the *subclass's* side, so clearing the base's package once
        stripped ancestry the cleared package never owned and its own
        rebuild could not restore (#124). An edge can therefore outlive
        the node at either endpoint, which is harmless by construction
        and declared as such in the same spec.

        Args:
            package: The package (distribution|import) name to clear.
        """
        # Clear the Edges (FTS5 index cleared via `nodes` delete trigger)
        self._connection.execute(
            "DELETE FROM edges WHERE "
            "src IN (SELECT qualified_name FROM nodes WHERE package = ?)",
            (package,),
        )

        self._connection.execute(
            "DELETE FROM package_builds WHERE package = ?", (package,)
        )

        # Clear the Nodes (MUST occur last)
        self._connection.execute(
            "DELETE FROM nodes WHERE package = ?", (package,)
        )
        self._connection.commit()
