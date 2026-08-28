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
import sys
from dataclasses import dataclass, fields
from importlib import metadata
from types import ModuleType
from typing import Any, cast

# NOTE: `_ensure_valid_name` lives in `_packages` - the module
# `specs/behaviors/package-resolution.md` names as the resolution
# boundary - and is shared here for qualified-name roots.
from venvaxi._packages import _ensure_valid_name
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

DEFAULT_TRUNCATE_LIMIT = 200
DEFAULT_MAX_DEPTH = 2

DEFAULT_API_ROW_LIMIT = 20
"""The default row bound on a public API listing.

NOTE: Distinct from `DEFAULT_TRUNCATE_LIMIT`, which bounds *characters*
within one docstring. This one bounds *rows*, and is the same 20 `find`
carries, so one number covers both collection commands
(`specs/commands/show.md`; `specs/behaviors/output-contract.md`,
Bounded collections).
"""

CLI_ESCAPE_HATCH = "use --docstring to see complete body"
"""Truncation escape-hatch clause, spelled for the CLI surface.

NOTE: The escape hatch must be named in the spelling of the surface the
caller is on (`specs/behaviors/output-contract.md`, Truncation) - this
is the CLI flag spelling, and the default so existing callers keep
today's byte-identical suffix.
"""

MCP_ESCAPE_HATCH = "re-call with docstring=true for the complete body"
"""Truncation escape-hatch clause, spelled for the MCP surface.

NOTE: MCP tools pass this at each `summarize_doc`/`get_public_api` call
site - the suffix travels inside the payload, so the CLI default would
otherwise teach an MCP caller a flag it cannot pass.
"""

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


@dataclass(frozen=True, slots=True)
class PublicAPI:
    """A bounded public API listing, with the bound it was cut to.

    NOTE: The bound travels back with the rows so that capped-ness is
    derived in exactly one place. Returning the row list alone loses
    the fact entirely, and recomputing `len(symbols) == max_rows` at
    each call site duplicates the rule the capped-count hint depends
    on, which is how two surfaces over one graph start disagreeing
    about whether an answer was complete
    (`specs/behaviors/output-contract.md`, Bounded collections).
    """

    symbols: list[SymbolInfo]
    max_rows: int

    @property
    def capped(self) -> bool:
        """Whether the row bound cut the listing short.

        NOTE: A count equal to the active bound means *at least* that
        many, never exactly - which is what the capped-count hint
        exists to say. A bound of `0` is capped by the same rule: the
        listing is empty because the bound said so, not because the
        package declares no public API.
        """
        return len(self.symbols) == self.max_rows


@dataclass(frozen=True, slots=True)
class RefreshReceipt:
    """A record of one completed symbol-graph rebuild.

    NOTE: Named fields rather than a bare tuple, following `PublicAPI` -
    the three values are all short scalars about the same walk, and a
    positional triple leaves each call site free to unpack `depth` and
    `symbols` the wrong way round without the type checker noticing
    (`specs/mcp/tools.md`, The rebuild receipt).
    """

    package: str
    depth: int
    symbols: int


def truncate(
    text: str,
    limit: int = DEFAULT_TRUNCATE_LIMIT,
    *,
    escape_hatch: str = CLI_ESCAPE_HATCH,
) -> str:
    """Truncate text to a set number of characters determined by `limit`.

    NOTE: AXI principle 3 (content truncation with size hints) - see
    `specs/principles.md`.

    Args:
        text: The text to truncate.
        limit: Maximum number of characters to keep. Defaults to 200.
        escape_hatch: The size hint's escape-hatch clause, spelled for
            the caller's surface. Defaults to the CLI spelling.

    Returns:
        `text` unchanged or truncated with an appended size hint.
    """
    if len(text) <= limit:
        return text

    return (
        f"{text[:limit]}... truncated, {len(text)} chars total"
        f" - {escape_hatch}"
    )


def summarize_doc(
    doc: str,
    *,
    docstring: bool = False,
    limit: int = DEFAULT_TRUNCATE_LIMIT,
    escape_hatch: str = CLI_ESCAPE_HATCH,
) -> str:
    """Reduce a docstring to a truncated first line, unless in full.

    NOTE: AXI principle 3 (content truncation with size hints) - see
    `specs/principles.md`. Applied at emission (not storage) so the cached
    graph keeps complete docstrings.

    Args:
        doc: The complete docstring.
        docstring: Return `doc` unchanged. Defaults to False.
        limit: The truncation limit. Defaults to 200.
        escape_hatch: The size hint's escape-hatch clause, spelled for
            the caller's surface. Defaults to the CLI spelling.

    Returns:
        `DOCSTRING_ABSENT` when `doc` is empty, else `doc` unchanged or
        its truncated first line.
    """
    if not doc:
        return DOCSTRING_ABSENT
    if docstring:
        return doc
    return truncate(doc.splitlines()[0], limit, escape_hatch=escape_hatch)


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


def _is_stdlib_type(tp: type) -> bool:
    """Test whether a type is defined in the standard library.

    NOTE: The discriminator here is the standard library, not the
    exporting *package* - issue #82 records two package-keyed
    candidates and both fail. `type(obj).__module__ == "builtins"` is
    too narrow: it leaks `NewType`'s own docstring onto a type alias
    whose type actually lives in `typing`. A package-root allowlist
    (does the type's module start with the package's own import root)
    is too strict: it blanks `pytest.fail`, whose type `_Fail` lives
    in `_pytest.outcomes`, never under `pytest.` itself. Keying on
    `sys.stdlib_module_names` instead separates every documented case
    (`pytest.fail`, `pytest.version_tuple`, `fastmcp.settings`, a
    `NewType` alias) - do not "simplify" this back to either
    alternative; both are counter-examples on file.

    Args:
        tp: The type to test.

    Returns:
        Whether `tp`'s defining module's top-level component names a
        standard-library module. `False` for a missing or empty
        `__module__` - the safer direction, since a wrongly-kept
        docstring is visible and a wrongly-blanked one is not.
    """
    module = getattr(tp, "__module__", None)
    if not module:
        return False
    return module.split(".", 1)[0] in sys.stdlib_module_names


def _doc_of(obj: Any, kind: NodeKind) -> str:
    """Extract an object's own docstring.

    NOTE: An instance's `__doc__` *is* its type's, so a module-level
    `dict`/`str` constant would otherwise be recorded carrying the
    builtin's docstring as its own - hence the `ATTRIBUTE` comparison.
    That comparison alone is too blunt though: a package that ships a
    class solely to instantiate it once as a public export
    (`pytest.fail`, an instance of `_pytest.outcomes._Fail`) documents
    the export *on that class*, and blanking it would report `(no
    docstring)` for a symbol whose documentation the graph already
    holds. `_is_stdlib_type` decides which case applies - a type's
    docstring is kept unless the type itself is standard-library.

    Args:
        obj: The object to document.
        kind: The object's classified `NodeKind`.

    Returns:
        The object's own docstring, or `""`.
    """
    doc = _own_doc(obj)
    if kind is not NodeKind.ATTRIBUTE:
        return doc
    type_doc = _own_doc(type(obj))
    if doc != type_doc:
        return doc
    return "" if _is_stdlib_type(type(obj)) else doc


def resolve_import_and_distributions(name: str) -> tuple[str, tuple[str, ...]]:
    """Resolve an import name and the distribution(s) claiming it.

    NOTE: Import names are case-sensitive (`PIL`, not `pil`) - a name
    already present as an import-name key is returned unchanged, and the
    fallback only normalizes dashes, never case.

    NOTE: Holds the matching logic `_resolve_import_name` used to
    contain, plus the reverse lookup off the same `mapping` -
    `packages_distributions()` costs ~145ms and is not memoized, so a
    caller needing both the import name and its claiming distributions
    resolves both from one call rather than two (#89).

    Args:
        name: The distribution (package) or import name.

    Returns:
        The best-effort importable top-level module name, and the
        distribution name(s) `packages_distributions()` maps it to
        (empty if none).
    """
    mapping = metadata.packages_distributions()
    if name in mapping:
        import_name = name
    else:
        normalized = name.lower().replace("-", "_")
        import_name = name.replace("-", "_")
        for candidate, dist_names in mapping.items():
            if any(
                d.lower().replace("-", "_") == normalized for d in dist_names
            ):
                import_name = candidate
                break
    return import_name, tuple(mapping.get(import_name, ()))


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
    return resolve_import_and_distributions(name)[0]


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
        and top_level_root(home_module) == package
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
    # NOTE: Callability, not kind, decides the signature - a
    # module-level instance whose class defines `__call__` (`pl.col`)
    # classifies as ATTRIBUTE yet has a signature the caller needs, and
    # the kind guard withheld it as `""` (#66). Non-callables keep `""`:
    # 'not callable' is the definitive answer, not a silent blank
    # (`specs/commands/inspect.md`).
    signature = _signature_of(obj) if callable(obj) else ""
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


def is_private_submodule(name: str) -> bool:
    """Whether a dotted module name is unreachable through the walk.

    Mirrors `_walk_submodules`'s own per-level skip
    (`subname.rsplit(".", 1)[-1].startswith("_")`), applied to every
    non-root segment of an already-fully-qualified name rather than to
    the one segment discovered during recursion - the walk skips at
    every level, so a private ancestor makes every name beneath it
    unreachable regardless of that name's own spelling. The root
    segment is excluded: the top-level package is walked directly, not
    discovered as its own submodule (`specs/behaviors/symbol-graph.md`,
    Private submodules).

    Args:
        name: A bare or dotted module name.

    Returns:
        True if any segment after the first starts with `_`.
    """
    return any(segment.startswith("_") for segment in name.split(".")[1:])


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
        except KeyboardInterrupt:
            # NOTE: A long walk must stay abortable - never swallow the
            # caller's interrupt (`specs/behaviors/output-contract.md`,
            # Import boundaries).
            raise
        except BaseException as err:
            # NOTE: `BaseException`, and broad, on purpose - importing
            # third-party submodules runs arbitrary module-level code,
            # which can raise anything: `numpy.f2py` raises
            # `_pytest.outcomes.Skipped`, a `BaseException` that sailed
            # through the previous `except Exception` and took the whole
            # command (and MCP connection) down (#64).

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


def top_level_root(name: str) -> str:
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
    root = top_level_root(name)
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
    root = top_level_root(name)
    _ensure_valid_name(root, name)
    root_package, distributions = resolve_import_and_distributions(root)
    _ensure_installed(root_package, root)
    try:
        return _cache.get_or_build_store(
            get_project_root(),
            root_package,
            distributions,
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
            if is_private_submodule(resolved):
                msg = (
                    f"Module `{name}` is private and never indexed -"
                    f" `{resolved.split('.', 1)[0]}` is the reachable root"
                )
            else:
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


def get_bases(
    qualified_name: str, *, refresh: bool = False
) -> list[SymbolNode]:
    """Fetch the classes a class directly inherits from.

    NOTE: Build depth derives from the canonical name and the resolved name,
    because a facade re-export from inside the same package may sit shallower
    than the home module - the same handling as `get_inheritors`.

    Args:
        qualified_name: The subclass's qualified name.
        refresh: Rebuild the cached graph first. Defaults to False.

    Raises:
        SymbolNotFoundError: If `qualified_name` has no matching node.

    Returns:
        One `SymbolNode` per direct base, ordered by qualified name.
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
            return store.get_bases(canonical)

    with _build_store_for(
        qualified_name, max_depth=_module_offset(canonical)
    ) as store:
        return store.get_bases(canonical)


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


def _ensure_non_negative_limit(limit: int) -> None:
    """Reject a negative row bound before any work is done.

    NOTE: A negative limit is the absence of a bound, not a smaller one
    - it reaches SQLite's `LIMIT ?` unbounded, and slices a sorted
    listing from the wrong end, so the caller is handed the whole graph
    under the very argument that exists to prevent that, with the cap
    hint unable to fire because a count never equals a negative limit.
    Rejected, not clamped: clamping to the default answers a question
    the caller never asked, indistinguishably from theirs (#73, #67;
    `specs/behaviors/output-contract.md`, Bounded collections).

    NOTE: One rejection site, shared by every bounded collection, so
    both surfaces inherit it before any store is opened or graph built
    and a bad argument costs nothing. The message names neither
    `--limit` nor `limit=`, and calls the value a *result* limit rather
    than a *search* one - the path is shared by `find` and
    `show --api`, and only one of those is a search, so the wording has
    to be true of every command that reaches it as well as of both
    surfaces (`specs/mcp/tools.md`, Error message wording).

    Args:
        limit: The caller-supplied bound on returned rows.

    Raises:
        InvalidArgumentError: On `limit` being negative.
    """
    if limit < 0:
        msg = f"Result limit `{limit}` must not be negative"
        raise InvalidArgumentError(msg)


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
        InvalidArgumentError: On missing `query`, a negative `limit`,
            `refresh` without `package`, or a malformed `package` name.
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

    _ensure_non_negative_limit(limit)

    if package is None:
        if refresh:
            # NOTE: Names the missing package scope, not the flags that
            # spell it on the CLI - the guard sits on the path both
            # surfaces share, and `--refresh`/`--package` name nothing
            # a tool caller can set (`specs/mcp/tools.md`, Error
            # message wording). The guard stays here rather than at the
            # CLI boundary, or an internal caller's unscoped refresh is
            # silently ignored.
            msg = "A rebuild must name the package to rebuild"
            raise InvalidArgumentError(msg)
        with SymbolStore(get_cache_db_path(get_project_root())) as store:
            return store.search_symbols(query, limit)

    import_name = _resolve_import_name(top_level_root(package))
    with _build_store_for(package, refresh=refresh) as store:
        return store.search_symbols(query, limit, package=import_name)


def get_public_api(
    name: str,
    *,
    docstring: bool = False,
    limit: int = DEFAULT_TRUNCATE_LIMIT,
    max_rows: int = DEFAULT_API_ROW_LIMIT,
    escape_hatch: str = CLI_ESCAPE_HATCH,
    refresh: bool = False,
) -> PublicAPI:
    """Extract top-level public symbols from a package.

    NOTE: Compatibility shim over the `SymbolStore` introspection engine.

    NOTE: Build depth derives from the resolved name's module offset,
    mirroring `get_symbol` - a dotted module deeper than
    `DEFAULT_MAX_DEPTH` must not answer from whatever depth the cache
    happens to hold. See `specs/behaviors/cache-refresh.md` (Validity).

    NOTE: Two bounds, deliberately named apart. `limit` is a
    *character* count applied inside one docstring; `max_rows` is a
    *row* count applied to the listing. Wiring one to the other would
    silently trade a package's public surface for its prose width
    (`specs/commands/show.md`; `specs/behaviors/output-contract.md`,
    Truncation and Bounded collections).

    NOTE: `MODULE`/`PACKAGE` children are excluded, every other kind is
    reported - `_walk_submodules` records a package's submodules under
    the same `CONTAINS` edge kind as `_record_symbol` records its
    symbols, so an unfiltered listing would answer 'every child of this
    module' rather than 'this package's public API' (#82; nested module
    structure is `tree`'s job, per `specs/commands/show.md`, Out of
    scope).

    Args:
        name: The package (distribution) name, or a dotted module path.
        docstring: Return complete docstrings instead of the truncated
            first line.
        limit: The per-docstring character truncation limit.
        max_rows: The maximum number of symbol rows returned. Defaults
            to 20.
        escape_hatch: The size hint's escape-hatch clause, spelled for
            the caller's surface. Defaults to the CLI spelling.
        refresh: Rebuild the cached graph first.

    Raises:
        InvalidArgumentError: On `name` not being a possible package
            name, or a negative `max_rows`.
        PackageNotFoundError: On `name` not being installed in the active
            venv.
        PackageImportError: On resolved module import error.

    Returns:
        The bounded public top-level symbols, with their kind,
        signature and docstring, alongside the bound applied.
    """
    _ensure_valid_name(name, name)
    _ensure_non_negative_limit(max_rows)

    # NOTE: `_resolve_qualified_name`, not `_resolve_import_name` - the
    # store is keyed by root-resolved import names, and whole-argument
    # resolution would fall through to a dash replacement that repairs
    # the tail, which validation must never see repaired.
    resolved = _resolve_qualified_name(name)
    _ensure_installed(resolved, name)
    try:
        importlib.import_module(resolved)
    except KeyboardInterrupt:
        raise
    except BaseException as err:
        # NOTE: An import boundary guards `BaseException`, not merely
        # `ImportError` - the requested package runs arbitrary code at
        # import time, and whatever it raises means 'broken', which is
        # `PackageImportError`'s class (#64;
        # `specs/behaviors/output-contract.md`, Import boundaries).
        msg = f"Failed to import `{resolved}` (from `{name}`)"
        raise PackageImportError(msg) from err

    with _build_store_for(
        name,
        max_depth=max(DEFAULT_MAX_DEPTH, _module_offset(resolved)),
        refresh=refresh,
    ) as store:
        children = store.get_children(resolved)

    symbols = [
        SymbolInfo(
            name=node.name,
            kind=str(node.kind),
            signature=node.signature,
            doc=summarize_doc(
                node.doc,
                docstring=docstring,
                limit=limit,
                escape_hatch=escape_hatch,
            ),
        )
        for node in children
        if node.kind not in (NodeKind.MODULE, NodeKind.PACKAGE)
    ]
    # NOTE: Bounded *after* the sort, so the rows returned are the
    # first N of the declared order rather than an arbitrary N of it -
    # a bound over an unsorted listing makes the answer depend on walk
    # order (`specs/behaviors/output-contract.md`, Bounded
    # collections).
    ordered = sorted(symbols, key=lambda symbol: symbol.name)
    return PublicAPI(symbols=ordered[:max_rows], max_rows=max_rows)


def refresh_package_graph(name: str) -> RefreshReceipt:
    """Rebuild one package's cached symbol graph and report the walk.

    NOTE: No `max_depth` parameter, deliberately. A rebuild request
    carries no query to derive a depth from, so it walks to the default
    build depth and resets the recorded depth with it
    (`specs/behaviors/cache-refresh.md`, Rebuild scope and depth).
    Deriving a depth from whatever the graph previously held would make
    a refresh's cost depend on query history.

    NOTE: Validation and resolution are `_build_store_for`'s, not
    reimplemented here - every failure mode this raises is one that
    path already raises, which is why there is no error handling of its
    own.

    NOTE: The receipt is read inside the store the rebuild returned, so
    it describes that walk rather than whatever the cache file holds by
    the time a second connection opens.

    Args:
        name: The package to rebuild. Accepts a distribution name or a
            bare|dotted|qualified name; the top-level root is what is
            rebuilt.

    Raises:
        InvalidArgumentError: On the top-level root of `name` not being
            a possible package name.
        PackageNotFoundError: On the resolved package not being
            installed in the active venv.
        PackageImportError: On resolved module import error.
        ProjectRootNotFoundError: On no project root resolving.
        StoreError: On a SQLite-level failure during the rebuild.

    Returns:
        The resolved import name the graph is keyed by, the build depth
        recorded for it, and the number of symbol nodes recorded.
    """
    import_name = _resolve_import_name(top_level_root(name))
    with _build_store_for(name, refresh=True) as store:
        build = store.get_build(import_name)
        depth = DEFAULT_MAX_DEPTH if build is None else build[1]
        symbols = store.count_nodes(import_name)
    return RefreshReceipt(package=import_name, depth=depth, symbols=symbols)
