"""Agent eXperience Interface (AXI) API and symbol-graph introspection.

Attribution:
    The recursive symbol-graph walking patterns used in this module are
    inspired by `code-review-graph`.

    NOTE: `code-review-graph` walks a static AST, whereas this module walks
    live objects via `importlib` and `inspect`.

    Repository: https://github.com/tirth8205/code-review-graph
    License: MIT License - Copyright (c) 2026 Tirth Kanani
"""

import importlib
import importlib.util
import inspect
import logging
import pkgutil
import re
import sys
from dataclasses import dataclass, fields
from importlib import metadata
from types import ModuleType
from typing import Any, cast

from venvaxi._store import (
    EdgeKind,
    NodeKind,
    SymbolEdge,
    SymbolNode,
    SymbolStore,
    qualify,
)
from venvaxi.exceptions import (
    InvalidArgumentError,
    PackageImportError,
    PackageNotFoundError,
    SymbolNotFoundError,
)

logger = logging.getLogger(__package__)

# NOTE: The single-character alternative is load-bearing - `_`, `a` and
# `2` are legal names, so the trailing group must be optional.
_VALID_NAME_RE = re.compile(r"^[A-Za-z0-9_]([A-Za-z0-9._-]*[A-Za-z0-9_])?$")
DEFAULT_TRUNCATE_LIMIT = 200
DEFAULT_MAX_DEPTH = 2

SIGNATURE_UNAVAILABLE = "(signature unavailable)"
"""Marker recorded when `inspect.signature` fails on a callable.

NOTE: Distinct from every real signature, so an agent can tell
"introspection failed" from "this callable takes `...`". Contains no
TOON structural characters, so the encoder never has to quote it.
"""

DOCSTRING_ABSENT = "(no docstring)"
"""Marker emitted for a symbol that defines no docstring of its own.

NOTE: AXI principle 5 (definitive empty states) - a bare `""` reads as
silent blank output, leaving an agent unable to tell "defines none" from
"something went wrong". States a different fact from
`SIGNATURE_UNAVAILABLE`: absence by definition, not failed introspection.

Applied at *emission* only. Recording it would put the literal text into
the FTS index, so `find docstring` would match every undocumented symbol
in the graph.
"""


@dataclass(frozen=True, slots=True)
class SymbolInfo:
    """A single public, top-level API symbol."""

    name: str
    kind: str
    signature: str
    doc: str


SYMBOL_INFO_FIELDS = tuple(field.name for field in fields(SymbolInfo))
"""The ordered `SymbolInfo` field names, forming TOON tabular headers."""


def truncate(text: str, limit: int = DEFAULT_TRUNCATE_LIMIT) -> str:
    """Truncate text to a set number of characters determined by `limit`.

    NOTE: AXI principle 3 (content truncation with size hints) - see
    `ICM/_config/reference-standard-axi.md`.

    Args:
        text: The text to truncate.
        limit: Maximum number of characters to keep. Defaults to 200.

    Returns:
        `text` unchanged or truncated with an appended size hint.
    """
    if len(text) <= limit:
        return text

    return (
        f"{text[:limit]}... truncated, {len(text)} chars total"
        " - use --docstring to see complete body"
    )


def summarize_doc(
    doc: str, *, docstring: bool = False, limit: int = DEFAULT_TRUNCATE_LIMIT
) -> str:
    """Reduce a docstring to a truncated first line, unless in full.

    NOTE: AXI principle 3 (content truncation with size hints) - see
    `ICM/_config/reference-standard-axi.md`. Applied at emission (not
    storage) so the cached graph keeps complete docstrings.

    Args:
        doc: The complete docstring.
        docstring: Return `doc` unchanged. Defaults to False.
        limit: The truncation limit. Defaults to 200.

    Returns:
        `DOCSTRING_ABSENT` when `doc` is empty, else `doc` unchanged or
        its truncated first line.
    """
    if not doc:
        return DOCSTRING_ABSENT
    if docstring:
        return doc
    return truncate(doc.splitlines()[0], limit)


def _own_doc(obj: Any) -> str:
    """Extract an object's own docstring, never an inherited one.

    NOTE: `inspect.getdoc` is `cleandoc` of the object's own `__doc__`
    plus a `_finddoc` fallback that walks the MRO - so an undocumented
    class, or a method overriding a documented one, is handed its base's
    docstring as if it were its own. Reading `__doc__` directly drops
    only that fallback, keeping `cleandoc`'s whitespace normalisation.

    Args:
        obj: The object to document.

    Returns:
        The object's own, whitespace-normalised docstring, or `""`.
    """
    doc = getattr(obj, "__doc__", None)
    return inspect.cleandoc(doc) if isinstance(doc, str) else ""


def _doc_of(obj: Any, kind: NodeKind) -> str:
    """Extract an object's own docstring.

    NOTE: An instance's `__doc__` *is* its type's, so a module-level
    `dict`/`str` constant would otherwise be recorded carrying the
    builtin's docstring as its own - hence the `ATTRIBUTE` comparison.

    Args:
        obj: The object to document.
        kind: The object's classified `NodeKind`.

    Returns:
        The object's own docstring, or `""`.
    """
    doc = _own_doc(obj)
    if kind is not NodeKind.ATTRIBUTE:
        return doc
    return "" if doc == _own_doc(type(obj)) else doc


def _resolve_import_name(name: str) -> str:
    """Resolve import slugs from distribution names.

    NOTE: Import names are case-sensitive (`PIL`, not `pil`) - a name
    already present as an import-name key is returned unchanged, and the
    fallback only normalizes dashes, never case.

    Args:
        name: The distribution (package) or import name.

    Returns:
        The best-effort importable top-level module name.
    """
    mapping = metadata.packages_distributions()
    if name in mapping:
        return name
    normalized = name.lower().replace("-", "_")
    for import_name, dist_names in mapping.items():
        for dist_name in dist_names:
            if dist_name.lower().replace("-", "_") == normalized:
                return import_name
    return name.replace("-", "_")


def _ensure_valid_name(root: str, name: str) -> None:
    """Raise if `root` cannot possibly be a package name.

    NOTE: Boundary validation of caller input, run before resolution -
    the dash/case fallback can only disguise a malformed name, never
    repair one. The message carries `name` because the root of a
    degenerate spelling (`.foo`) is `""`, which names nothing the
    caller can fix. See `specs/behaviors/package-resolution.md`.

    Args:
        root: The top-level component to validate, as supplied.
        name: The caller's original spelling, used for the message.

    Raises:
        InvalidArgumentError: On `root` not being a possible package
            name.
    """
    if not _VALID_NAME_RE.match(root):
        msg = f"Invalid package name `{name}`"
        raise InvalidArgumentError(msg)


def _ensure_installed(import_name: str, name: str) -> None:
    """Raise if nothing in the venv answers to `import_name`.

    NOTE: Availability is decided by the import system, not by
    `importlib.metadata` - a stdlib module, a namespace package and a
    local module on `sys.path` are all importable with no distribution
    claiming them, and 'install it' is the wrong advice for all three.

    NOTE: `sys.modules` is checked first because `find_spec` *raises*
    on a module whose `__spec__` is None (a bare `types.ModuleType`).
    An already-imported module is available by definition.

    Args:
        import_name: The resolved import name, from
            `_resolve_import_name`.
        name: The caller's original spelling, used for the message.

    Raises:
        PackageNotFoundError: On nothing in the venv providing
            `import_name`.
    """
    if import_name in sys.modules:
        return

    # NOTE: `find_spec` delegates to arbitrary `sys.meta_path` finders,
    # which may raise rather than return None. A finder that fails is
    # 'not located', not a crash - the distribution check below still
    # gets its say.
    try:
        if importlib.util.find_spec(import_name) is not None:
            return
    except (ImportError, ValueError):
        logger.debug("No module spec located for `%s`", import_name)

    # NOTE: Located by nothing, but a distribution claims the name - it
    # is installed and broken, so the caller's import attempt runs and
    # reports `PackageImportError` rather than 'not installed'.
    try:
        metadata.distribution(name)
    except metadata.PackageNotFoundError as err:
        msg = f"Package `{name}` is not installed in the active venv"
        raise PackageNotFoundError(msg) from err


def _signature_of(obj: Any) -> str:
    """Best-effort `inspect.signature` string for a callable.

    NOTE: Broad catch on purpose - `inspect.signature` can raise
    arbitrary exceptions on exotic objects (`RecursionError`,
    `__signature__` descriptors that raise); one bad callable must
    not abort the walk.

    Args:
        obj: The object to inspect.

    Returns:
        The signature string, or `SIGNATURE_UNAVAILABLE` if it cannot
        be determined.
    """
    try:
        return str(inspect.signature(obj))
    except Exception as err:
        logger.debug(
            "Signature unavailable for `%s` object: %s",
            type(obj).__name__,
            err,
        )
        return SIGNATURE_UNAVAILABLE


def _classify(obj: Any) -> NodeKind:
    """Classifies a module-level member as a class/function/attribute.

    Args:
        obj: The object to classify.

    Returns:
        The matching `NodeKind`.
    """
    if inspect.isclass(obj):
        return NodeKind.CLASS
    if inspect.isroutine(obj):
        return NodeKind.FUNCTION
    return NodeKind.ATTRIBUTE


def _walk_class_members(
    cls: type,
    *,
    containing_module: str,
    store: SymbolStore,
    package: str,
    version: str,
) -> None:
    """Walk a class's public members into `CONTAINS`/`INHERITS` edges.

    NOTE: Member nodes and edges are keyed at the class's *home*
    module (`cls.__module__`). For a facade re-export from inside the
    same package, the class node itself is also upserted at that home
    path - the `get_inheritors.sql` JOIN requires a node at every
    edge `src`, and private home modules are never walked directly. A
    cross-package home is left alone: claiming its node's `package`
    field would let `clear_package` for one package delete another
    package's node.

    Args:
        cls: The class to walk.
        containing_module: The module the class was recorded under
            (the facade module for a re-export).
        store: The `SymbolStore` to populate.
        package: The owning package (distribution/import) name.
        version: The owning package's installed version.
    """
    class_qualified_name = qualify(cls.__module__, cls.__name__)
    home_module: str | None = cls.__module__
    if (
        home_module is not None
        and home_module != containing_module
        and _top_level_root(home_module) == package
    ):
        store.upsert_node(
            SymbolNode(
                qualified_name=class_qualified_name,
                kind=NodeKind.CLASS,
                name=cls.__name__,
                module=home_module,
                signature=_signature_of(cls),
                doc=_doc_of(cls, NodeKind.CLASS),
                package=package,
                version=version,
                home_qualified_name=class_qualified_name,
            )
        )
    for member_name, member in inspect.getmembers(cls):
        if member_name.startswith("_"):
            continue
        kind = (
            NodeKind.METHOD
            if inspect.isroutine(member)
            else NodeKind.ATTRIBUTE
        )
        member_qualified_name = qualify(
            cls.__module__, cls.__name__, member_name
        )
        store.upsert_node(
            SymbolNode(
                qualified_name=member_qualified_name,
                kind=kind,
                name=member_name,
                module=cls.__module__,
                signature=_signature_of(member)
                if kind is NodeKind.METHOD
                else "",
                doc=_doc_of(member, kind),
                package=package,
                version=version,
                home_qualified_name=member_qualified_name,
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src=class_qualified_name,
                dst=member_qualified_name,
                kind=EdgeKind.CONTAINS,
            )
        )
    for base in cls.__bases__:
        if base is object:
            continue
        base_qualified_name = qualify(base.__module__, base.__name__)
        store.upsert_edge(
            SymbolEdge(
                src=class_qualified_name,
                dst=base_qualified_name,
                kind=EdgeKind.INHERITS,
            )
        )


def _record_symbol(
    module: ModuleType,
    symbol_name: str,
    obj: Any,
    *,
    store: SymbolStore,
    package: str,
    version: str,
) -> NodeKind:
    """Upsert a single module-level symbol node plus its edges.

    Args:
        module: The owning module.
        symbol_name: The symbol's bare name within `module`.
        obj: The symbol object.
        store: The `SymbolStore` to populate.
        package: The owning package (distribution/import) name.
        version: The owning package's installed version.

    Returns:
        The symbol's classified `NodeKind` (so callers can decide
        whether to recurse into class members).
    """
    kind = _classify(obj)
    symbol_qualified_name = qualify(module.__name__, symbol_name)
    obj_home_module = getattr(obj, "__module__", None) or module.__name__

    # NOTE: Kind guard - only classes/functions own their `__module__`
    home_qualified_name = (
        qualify(obj_home_module, getattr(obj, "__name__", symbol_name))
        if kind in (NodeKind.CLASS, NodeKind.FUNCTION)
        else symbol_qualified_name
    )
    signature = (
        _signature_of(obj)
        if kind in (NodeKind.CLASS, NodeKind.FUNCTION)
        else ""
    )
    store.upsert_node(
        SymbolNode(
            qualified_name=symbol_qualified_name,
            kind=kind,
            name=symbol_name,
            module=module.__name__,
            signature=signature,
            doc=_doc_of(obj, kind),
            package=package,
            version=version,
            home_qualified_name=home_qualified_name,
        )
    )
    store.upsert_edge(
        SymbolEdge(
            src=module.__name__,
            dst=symbol_qualified_name,
            kind=EdgeKind.CONTAINS,
        )
    )

    if obj_home_module != module.__name__:
        store.upsert_edge(
            SymbolEdge(
                src=module.__name__,
                dst=symbol_qualified_name,
                kind=EdgeKind.EXPORTS,
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src=module.__name__,
                dst=obj_home_module,
                kind=EdgeKind.IMPORTS_FROM,
            )
        )
    return kind


def _walk_submodules(
    module: ModuleType,
    *,
    package_root: str,
    depth: int,
    max_depth: int,
    visited: set[str],
    store: SymbolStore,
    package: str,
    version: str,
) -> None:
    """Discover and recursively walk a package's direct submodules.

    Args:
        module: The parent package module.
        package_root: The top-level import name recursion must stay
            within (prevents escaping into unrelated re-exported deps).
        depth: The current recursion depth.
        max_depth: The maximum recursion depth.
        visited: Module names already visited (cycle/re-import guard).
        store: The `SymbolStore` to populate.
        package: The owning package (distribution/import) name.
        version: The owning package's installed version.
    """
    if not hasattr(module, "__path__") or depth >= max_depth:
        return

    for _, subname, _ in pkgutil.iter_modules(
        module.__path__, prefix=f"{module.__name__}."
    ):
        if subname.rsplit(".", 1)[-1].startswith("_") or subname in visited:
            continue
        try:
            submodule = importlib.import_module(subname)
        except Exception as err:
            # NOTE: Broad on purpose - importing third-party submodules
            # runs arbitrary module-level code, which can raise anything

            logger.warning(
                "Skipping submodule `%s` (import failed: %s)", subname, err
            )
            # One bad submodule must not abort the whole walk.
            continue
        if not submodule.__name__.startswith(package_root):
            continue

        visited.add(subname)
        store.upsert_node(
            SymbolNode(
                qualified_name=submodule.__name__,
                kind=NodeKind.MODULE,
                name=submodule.__name__.rsplit(".", 1)[-1],
                module=module.__name__,
                signature="",
                doc=_own_doc(submodule),
                package=package,
                version=version,
                home_qualified_name=submodule.__name__,
            )
        )
        store.upsert_edge(
            SymbolEdge(
                src=module.__name__,
                dst=submodule.__name__,
                kind=EdgeKind.CONTAINS,
            )
        )
        _walk_module(
            submodule,
            package_root=package_root,
            depth=depth + 1,
            max_depth=max_depth,
            visited=visited,
            store=store,
            package=package,
            version=version,
        )


def _walk_module(
    module: ModuleType,
    *,
    package_root: str,
    depth: int,
    max_depth: int,
    visited: set[str],
    store: SymbolStore,
    package: str,
    version: str,
) -> None:
    """Recursively walks a module's public API into the symbol store.

    NOTE: Without `__all__`, a walked submodule `dir()` will include names,
    which are merely imported.

    Args:
        module: The module to walk.
        package_root: The top-level import name recursion must stay
            within (prevents escaping into unrelated re-exported deps).
        depth: The current recursion depth.
        max_depth: The maximum recursion depth for submodules.
        visited: Module names already visited (cycle/re-import guard).
        store: The `SymbolStore` to populate.
        package: The owning package (distribution/import) name.
        version: The owning package's installed version.
    """
    explicit_exports = getattr(module, "__all__", None)
    public_names = list(
        explicit_exports or [n for n in dir(module) if not n.startswith("_")]
    )
    for symbol_name in sorted(public_names):
        obj: Any = getattr(module, symbol_name, None)
        if explicit_exports is None and depth > 0:
            if inspect.ismodule(obj):
                continue
            obj_home = getattr(obj, "__module__", None)
            if (
                (inspect.isclass(obj) or inspect.isroutine(obj))
                and obj_home is not None
                and obj_home != module.__name__
            ):
                private_home_facade = obj_home.startswith(
                    f"{package_root}."
                ) and any(
                    segment.startswith("_") for segment in obj_home.split(".")
                )
                if not private_home_facade:
                    continue
        kind = _record_symbol(
            module,
            symbol_name,
            obj,
            store=store,
            package=package,
            version=version,
        )
        if kind is NodeKind.CLASS:
            _walk_class_members(
                cast(type, obj),
                containing_module=module.__name__,
                store=store,
                package=package,
                version=version,
            )

    _walk_submodules(
        module,
        package_root=package_root,
        depth=depth,
        max_depth=max_depth,
        visited=visited,
        store=store,
        package=package,
        version=version,
    )


def _top_level_root(name: str) -> str:
    """Extract the top-level package/module name from any identifier.

    Args:
        name: A bare module name (`"rich"`), dotted module name
            (`"rich.table"`), or fully qualified symbol name
            (`"rich.table::Table.add_row"`).

    Returns:
        The top-level (first dotted) component, e.g. `"rich"`.
    """
    module_part = name.split("::", 1)[0]
    return module_part.split(".", 1)[0]


def _module_offset(resolved: str) -> int:
    """Count how many levels below its top-level package a name sits.

    NOTE: Depth (`package_builds.max_depth`) is measured from the top-level
    package and the depth frame for dotted submodule names must be translated
    into the root frame before building.

    Args:
        resolved: A resolved bare|dotted module name or fully qualified
            symbol name.

    Returns:
        The number of dots in the module component, indicating its depth.
    """
    return resolved.split("::", 1)[0].count(".")


def _resolve_qualified_name(name: str) -> str:
    """Resolve a name's leading distribution component to an import name.

    NOTE: As the store is keyed by import name, any difference in distribution
    name (`detect-secrets` -> `detect_secrets`) must be resolved.

    Args:
        name: A bare|dotted|qualified name.

    Returns:
        `name` with its top component resolved to an import name.
    """
    root = _top_level_root(name)
    import_root = _resolve_import_name(root)
    return name if import_root == root else f"{import_root}{name[len(root) :]}"


def _build_store_for(
    name: str, *, max_depth: int = DEFAULT_MAX_DEPTH, refresh: bool = False
) -> SymbolStore:
    """Build|fetch the top package for a cached store owning `name`.

    Args:
        name: A bare module name, dotted module name, or fully
            qualified symbol name.
        max_depth: The maximum submodule recursion depth to build (on
            rebuild).
        refresh: Rebuild even if the cached graph is still current.

    Raises:
        InvalidArgumentError: On the top-level root of `name` not being
            a possible package name.
        PackageNotFoundError: On the resolved package not being installed
            in the active venv.
        PackageImportError: On resolved module import error.

    Returns:
        An open `SymbolStore`, populated with the symbol graph for the
        resolved top-level package. MUST be closed (`close()`).
    """
    from venvaxi import _cache
    from venvaxi._core import get_project_root

    # NOTE: The check takes the *root*, not `name` - a qualified name
    # carries `.module::Symbol` that neither names a distribution nor
    # belongs in a 'not installed' message.
    root = _top_level_root(name)
    _ensure_valid_name(root, name)
    root_package = _resolve_import_name(root)
    _ensure_installed(root_package, root)
    try:
        return _cache.get_or_build_store(
            get_project_root(),
            root_package,
            max_depth=max_depth,
            force_refresh=refresh,
        )
    except ImportError as err:
        msg = f"Failed to import `{root_package}` (from `{name}`)"
        raise PackageImportError(msg) from err


def show_module(
    name: str, *, refresh: bool = False
) -> tuple[SymbolNode, list[SymbolNode]]:
    """Show a module/package node and its direct children.

    Args:
        name: The module's bare or dotted import name.
        refresh: Rebuild the cached graph first. Defaults to False.

    Raises:
        SymbolNotFoundError: If `name` has no matching node.

    Returns:
        The module's `SymbolNode` and its direct `CONTAINS` children.
    """
    resolved = _resolve_qualified_name(name)
    # NOTE: `+ 1` so the named (dotted) module's own children exist
    max_depth = max(DEFAULT_MAX_DEPTH, _module_offset(resolved) + 1)
    with _build_store_for(name, max_depth=max_depth, refresh=refresh) as store:
        node = store.get_node(resolved)
        if node is None:
            msg = f"Module `{name}` not found"
            raise SymbolNotFoundError(msg)
        return node, store.get_children(resolved)


def _resolve_facade_member(
    store: SymbolStore, resolved: str
) -> SymbolNode | None:
    """Resolve a facade-spelled class member to its home-keyed node.

    NOTE: Member nodes are keyed at their owner class's *home* module
    only (`_walk_class_members`), so a facade spelling such as
    `fastmcp::Client.call_tool` has no row of its own - unlike classes
    and functions, which are keyed at every containing module. The
    owner resolves via `canonical_name`; the answer is the home row
    as stored, per `specs/behaviors/qualified-name-semantics.md`.

    NOTE: No depth guard, unlike `get_inheritors` - member `CONTAINS`
    rows are written by the same class walk that wrote the owner node,
    keyed at home regardless of build depth, so a found owner implies
    its member rows exist and a candidate miss is definitive.

    Args:
        store: The open `SymbolStore` to resolve against.
        resolved: The import-name-resolved qualified name.

    Returns:
        The home-keyed member `SymbolNode`, or `None` on a genuine miss.
    """
    _, separator, symbol_part = resolved.partition("::")
    if not separator or "." not in symbol_part:
        return None
    # NOTE: Last-dot split, matching member key shape (`Class.member`) -
    # a nested-class owner (`mod::Outer.Inner`) stays intact.
    owner, _, member = resolved.rpartition(".")
    canonical = store.canonical_name(owner)
    if canonical == owner:
        # NOTE: Owner absent, or already home-keyed - a genuine miss.
        return None
    # NOTE: Concatenation, not `qualify()` - `canonical` already
    # carries its `::` separator.
    return store.get_node(f"{canonical}.{member}")


def get_symbol(qualified_name: str, *, refresh: bool = False) -> SymbolNode:
    """Fetch a single symbol node by its qualified name.

    Args:
        qualified_name: The fully qualified symbol name.
        refresh: Rebuild the cached graph first. Defaults to False.

    Raises:
        SymbolNotFoundError: If no matching node exists.

    Returns:
        The matching `SymbolNode`.
    """
    resolved = _resolve_qualified_name(qualified_name)
    with _build_store_for(
        qualified_name,
        max_depth=max(DEFAULT_MAX_DEPTH, _module_offset(resolved)),
        refresh=refresh,
    ) as store:
        node = store.get_node(resolved)
        if node is None:
            node = _resolve_facade_member(store, resolved)
        if node is None:
            msg = f"Symbol `{qualified_name}` not found"
            raise SymbolNotFoundError(msg)
        return node


def get_inheritors(
    qualified_name: str, *, refresh: bool = False
) -> list[SymbolNode]:
    """Fetch classes that directly inherit from a class.

    NOTE: Build depth derives from the canonical name and the resolved name,
    because a facade re-export from inside the same package may sit shallower
    than the home module.

    Args:
        qualified_name: The base class's qualified name.
        refresh: Rebuild the cached graph first. Defaults to False.

    Raises:
        SymbolNotFoundError: If `qualified_name` has no matching node.

    Returns:
        The inheriting `SymbolNode` instance(s).
    """
    resolved = _resolve_qualified_name(qualified_name)
    built_depth = max(DEFAULT_MAX_DEPTH, _module_offset(resolved))
    with _build_store_for(
        qualified_name, max_depth=built_depth, refresh=refresh
    ) as store:
        if store.get_node(resolved) is None:
            msg = f"Symbol `{qualified_name}` not found"
            raise SymbolNotFoundError(msg)
        canonical = store.canonical_name(resolved)
        if _module_offset(canonical) <= built_depth:
            return store.get_inheritors(canonical)

    with _build_store_for(
        qualified_name, max_depth=_module_offset(canonical)
    ) as store:
        return store.get_inheritors(canonical)


def get_module_tree(
    name: str, max_depth: int = DEFAULT_MAX_DEPTH, *, refresh: bool = False
) -> list[tuple[int, SymbolNode]]:
    """Fetch a nested module tree for a module/package.

    Args:
        name: The module's bare or dotted import name.
        max_depth: The maximum recursion depth.
        refresh: Rebuild the cached graph first.

    Raises:
        InvalidArgumentError: On the top-level root of `name` not being
            a possible package name.
        PackageNotFoundError: On the owning package not being installed
            in the active venv.
        PackageImportError: On resolved module import error.

    Returns:
        `(depth, node)` pairs in depth-first order, with depth measured
        from the named module.
    """
    resolved = _resolve_qualified_name(name)
    with _build_store_for(
        name, max_depth=max_depth + _module_offset(resolved), refresh=refresh
    ) as store:
        return store.get_module_tree(resolved, max_depth)


def find_symbol(
    query: str,
    limit: int = 20,
    package: str | None = None,
    *,
    refresh: bool = False,
) -> list[SymbolNode]:
    """Search the project cached symbols by name|doc text.

    NOTE: (1) Without `package` - only searches cached results from previously
    walked packages. (2) With `package` - a symbol graph is built (if needed)
    and the search is scoped to that specific package.

    Args:
        query: The free-text search query.
        limit: The maximum number of results.
        package: Optional package to index and scope the search to.
            Accepts a distribution name or a bare|dotted|qualified name.
        refresh: Rebuild the cached graph first for `package`.

    Raises:
        InvalidArgumentError: On missing `query`, `refresh` without
            `package`, or a malformed `package` name.
        PackageNotFoundError: On `package` not being installed in the
            active venv.
        PackageImportError: On `package` import error.

    Returns:
        Matching `SymbolNode` instance(s).
    """
    from venvaxi._cache import get_cache_db_path
    from venvaxi._core import get_project_root

    if not query.strip():
        msg = "Search query must be non-empty"
        raise InvalidArgumentError(msg)

    if package is None:
        if refresh:
            msg = (
                "`--refresh` requires `--package` to name the graph to rebuild"
            )
            raise InvalidArgumentError(msg)
        with SymbolStore(get_cache_db_path(get_project_root())) as store:
            return store.search_symbols(query, limit)

    import_name = _resolve_import_name(_top_level_root(package))
    with _build_store_for(package, refresh=refresh) as store:
        return store.search_symbols(query, limit, package=import_name)


def get_public_api(
    name: str,
    *,
    docstring: bool = False,
    limit: int = DEFAULT_TRUNCATE_LIMIT,
    refresh: bool = False,
) -> list[SymbolInfo]:
    """Extract top-level public functions & classes from a package.

    NOTE: Compatibility shim over the `SymbolStore` introspection engine.

    Args:
        name: The package (distribution) name.
        docstring: Return complete docstrings instead of the truncated
            first line.
        limit: The docstring truncation limit.
        refresh: Rebuild the cached graph first.

    Raises:
        InvalidArgumentError: On `name` not being a possible package
            name.
        PackageNotFoundError: On `name` not being installed in the active
            venv.
        PackageImportError: On resolved module import error.

    Returns:
        Public top-level symbols, with their kind, signature and
        docstring.
    """
    _ensure_valid_name(name, name)

    import_name = _resolve_import_name(name)
    _ensure_installed(import_name, name)
    try:
        importlib.import_module(import_name)
    except ImportError as err:
        msg = f"Failed to import `{import_name}` (from `{name}`)"
        raise PackageImportError(msg) from err

    with _build_store_for(name, refresh=refresh) as store:
        children = store.get_children(import_name)

    symbols: list[SymbolInfo] = []
    for node in children:
        if node.kind not in (NodeKind.CLASS, NodeKind.FUNCTION):
            continue
        symbols.append(
            SymbolInfo(
                name=node.name,
                kind=str(node.kind),
                signature=node.signature,
                doc=summarize_doc(node.doc, docstring=docstring, limit=limit),
            )
        )
    return sorted(symbols, key=lambda symbol: symbol.name)
