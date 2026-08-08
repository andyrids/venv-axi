"""Unit tests for `venvaxi._introspect`."""

import importlib
import logging
import shutil
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from venvaxi._introspect import (
    SIGNATURE_UNAVAILABLE,
    _doc_of,
    _own_doc,
    _resolve_import_name,
    _signature_of,
    _walk_module,
    find_symbol,
    get_inheritors,
    get_module_tree,
    get_public_api,
    get_symbol,
    show_module,
    truncate,
)
from venvaxi._store import NodeKind, SymbolStore
from venvaxi.exceptions import (
    InvalidArgumentError,
    PackageImportError,
    PackageNotFoundError,
    SymbolNotFoundError,
)


@pytest.fixture
def fake_module(
    isolated_cache: Path,
) -> Iterator[types.ModuleType]:
    """Register a throwaway module for API-introspection tests."""
    module = types.ModuleType("axi_fixture_mod")

    def greet(name: str) -> str:
        """Greets someone.

        Returns a friendly greeting for the given name.
        """
        return f"hello {name}"

    class Greeter:
        """Greets people repeatedly."""

    module.greet = greet  # type: ignore[attr-defined]
    module.Greeter = Greeter  # type: ignore[attr-defined]
    module.VERSION = "1.2.3"  # type: ignore[attr-defined]
    module._hidden = object()  # type: ignore[attr-defined]
    sys.modules[module.__name__] = module
    try:
        yield module
    finally:
        del sys.modules[module.__name__]


@pytest.fixture
def fake_package(
    isolated_cache: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[str]:
    """Register a real on-disk package with a submodule and a subclass."""
    from tests.resources import package

    src_test = tmp_path_factory.mktemp("src_test")
    shutil.copytree(
        Path(package.__file__).parent,
        src_test / "package",
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    sys.path.insert(0, str(src_test))
    try:
        yield "package"
    finally:
        sys.path.remove(str(src_test))
        for name in list(sys.modules):
            if name.startswith("package"):
                del sys.modules[name]


@pytest.fixture
def fake_module_with_none_module_attr(
    isolated_cache: Path,
) -> Iterator[types.ModuleType]:
    """Register a module containing a symbol whose `__module__` is `None`.

    NOTE: Sometimes seen with some C-extension/builtin objects.
    """
    module = types.ModuleType("axi_fixture_none_module_mod")

    def unset() -> str:
        """Return a function whose `__module__` is explicitly unset."""
        return "ok"

    unset.__module__ = None  # type: ignore[assignment]
    module.unset = unset  # type: ignore[attr-defined]
    sys.modules[module.__name__] = module
    try:
        yield module
    finally:
        del sys.modules[module.__name__]


def test_truncate_short_text_unchanged() -> None:
    """Text at or under the limit is returned unchanged."""
    assert truncate("short", limit=10) == "short"


def test_truncate_long_text_appends_hint() -> None:
    """Text over the limit is cut and a size hint is appended."""
    result = truncate("x" * 20, limit=5)
    assert result.startswith("xxxxx... truncated, 20 chars total")
    assert "use --docstring to see complete body" in result


def test_own_doc_normalises_whitespace() -> None:
    """An own docstring is returned dedented, as `getdoc` would."""

    class Documented:
        """Summary.

        Indented body.
        """

    assert _own_doc(Documented) == "Summary.\n\nIndented body."


def test_own_doc_absent_returns_empty() -> None:
    """An object with no docstring of its own yields an empty string."""

    class Bare:
        pass

    assert _own_doc(Bare) == ""


def test_own_doc_non_string_returns_empty() -> None:
    """A non-string `__doc__` yields an empty string rather than raising."""
    assert _own_doc(types.SimpleNamespace(__doc__=42)) == ""


def test_doc_of_undocumented_class_ignores_base_docstring() -> None:
    """A class with no docstring does not inherit its base class's."""

    class Base:
        """Base docstring."""

    class Derived(Base):
        pass

    assert _doc_of(Derived, NodeKind.CLASS) == ""


def test_doc_of_documented_class_returns_own_docstring() -> None:
    """A class that defines a docstring still reports it."""

    class Documented:
        """Own docstring."""

    assert _doc_of(Documented, NodeKind.CLASS) == "Own docstring."


def test_doc_of_override_without_docstring_returns_empty() -> None:
    """An override with no docstring does not inherit the base method's."""

    class Base:
        def run(self) -> None:
            """Run the base implementation."""

    class Derived(Base):
        def run(self) -> None:
            pass

    assert _doc_of(Derived.run, NodeKind.METHOD) == ""


def test_doc_of_inherited_method_returns_base_docstring() -> None:
    """An un-overridden method is the same object, so the base's docstring
    is genuinely its own and is reported."""

    class Base:
        def run(self) -> None:
            """Run the base implementation."""

    class Derived(Base):
        pass

    assert Derived.run is Base.run
    assert (
        _doc_of(Derived.run, NodeKind.METHOD) == "Run the base implementation."
    )


def test_doc_of_attribute_ignores_type_docstring() -> None:
    """A module-level constant is not recorded with its type's docstring."""
    assert _doc_of({"key": "value"}, NodeKind.ATTRIBUTE) == ""


def test_get_public_api_filters_private_and_non_callables(
    fake_module: types.ModuleType,
) -> None:
    """Only public functions/classes are surfaced, sorted by name."""
    symbols = get_public_api(fake_module.__name__)
    names = [symbol.name for symbol in symbols]
    assert names == ["Greeter", "greet"]


def test_show_module_captures_attribute_kind(
    fake_module: types.ModuleType,
) -> None:
    """A public non-callable module member is captured as an
    `ATTRIBUTE` node (previously silently skipped)."""
    _, children = show_module(fake_module.__name__)
    version_node = next(child for child in children if child.name == "VERSION")
    assert version_node.kind is NodeKind.ATTRIBUTE


def test_get_public_api_truncates_doc_by_default(
    fake_module: types.ModuleType,
) -> None:
    """The docstring's first line is used, truncated by default."""
    symbols = get_public_api(fake_module.__name__)
    greet = next(symbol for symbol in symbols if symbol.name == "greet")
    assert greet.doc == "Greets someone."
    assert greet.kind == "function"
    assert greet.signature == "(name: str) -> str"


def test_get_public_api_full_returns_complete_docstring(
    fake_module: types.ModuleType,
) -> None:
    """`docstring=True` returns the complete, untruncated docstring."""
    symbols = get_public_api(fake_module.__name__, docstring=True)
    greet = next(symbol for symbol in symbols if symbol.name == "greet")
    assert "friendly greeting" in greet.doc


def test_get_public_api_invalid_name_raises() -> None:
    """An invalid package name raises `PackageNotFoundError`."""
    with pytest.raises(PackageNotFoundError):
        get_public_api("../etc/passwd")


def test_get_public_api_import_error_raises() -> None:
    """A non-importable package raises `PackageImportError`."""
    with pytest.raises(PackageImportError):
        get_public_api("this-package-does-not-exist-xyz")


def test_show_module_returns_node_and_children(fake_package: str) -> None:
    """`show_module` returns the package node and its direct children."""
    node, children = show_module(fake_package)
    assert node.kind is NodeKind.PACKAGE
    names = [child.name for child in children]
    assert names == [
        "Animal",
        "Cat",
        "Dog",
        "api",
        "constants",
        "facade",
        "importer",
        "module",
        "subpkg",
    ]


def test_show_module_raises_for_unknown_symbol(fake_package: str) -> None:
    """An unknown module name raises `SymbolNotFoundError`."""
    show_module(fake_package)
    with pytest.raises(SymbolNotFoundError):
        show_module(f"{fake_package}.does_not_exist")


def test_show_module_excludes_reexports_without_all(
    fake_package: str,
) -> None:
    """A walked submodule without `__all__` does not claim symbols
    imported from elsewhere (they stay attributed to their home)."""
    _, children = show_module(f"{fake_package}.importer")
    assert [child.name for child in children] == ["local"]


def test_show_module_includes_reexports_with_all(fake_package: str) -> None:
    """A walked submodule with an explicit `__all__` keeps its
    re-exports (explicit export intent is trusted)."""
    _, children = show_module(f"{fake_package}.facade")
    assert "util" in [child.name for child in children]


def test_get_module_tree_unimportable_raises(
    isolated_cache: Path,
) -> None:
    """A non-importable module name raises `PackageImportError`
    (previously: a raw `ModuleNotFoundError` traceback)."""
    with pytest.raises(PackageImportError):
        get_module_tree("this_module_does_not_exist_xyz")


def test_get_symbol_unimportable_raises(isolated_cache: Path) -> None:
    """A qualified name under a non-importable module raises
    `PackageImportError` (previously: a raw `ModuleNotFoundError`)."""
    with pytest.raises(PackageImportError):
        get_symbol("this_module_does_not_exist_xyz::Nope")


def test_walk_module_handles_none_module_attribute(
    fake_module_with_none_module_attr: types.ModuleType,
) -> None:
    """A symbol whose `__module__` is `None` does not crash the walk
    (regression: `SymbolEdge(dst=None, ...)` violated the store's
    NOT NULL constraint) and is not mistaken for a foreign symbol."""
    node, children = show_module(fake_module_with_none_module_attr.__name__)
    assert node.kind is NodeKind.PACKAGE
    assert [child.name for child in children] == ["unset"]


def test_get_symbol_returns_class_node(fake_package: str) -> None:
    """`get_symbol` resolves a fully qualified class name."""
    node = get_symbol(f"{fake_package}::Dog")
    assert node.name == "Dog"
    assert node.kind is NodeKind.CLASS


def test_get_symbol_raises_for_unknown_symbol(fake_package: str) -> None:
    """An unknown qualified name raises `SymbolNotFoundError`."""
    with pytest.raises(SymbolNotFoundError):
        get_symbol(f"{fake_package}::DoesNotExist")


def test_get_inheritors_returns_subclasses(fake_package: str) -> None:
    """`get_inheritors` finds direct subclasses of a base class."""
    inheritors = get_inheritors(f"{fake_package}::Animal")
    names = [node.name for node in inheritors]
    assert names == ["Cat", "Dog"]


def test_get_inheritors_resolves_facade_reexport(fake_package: str) -> None:
    """A facade-path base class finds subclasses whose `INHERITS`
    edges are keyed at the private home module."""
    inheritors = get_inheritors(f"{fake_package}.api::Base")
    assert [node.name for node in inheritors] == ["Sub"]


def test_get_inheritors_home_path_matches_facade(fake_package: str) -> None:
    """The home-path query returns the same inheritors as the facade
    path, even though the private home module is never walked."""
    inheritors = get_inheritors(f"{fake_package}._impl::Base")
    assert [node.name for node in inheritors] == ["Sub"]


def test_home_qualified_name_records_private_home(fake_package: str) -> None:
    """A facade-recorded class stores its private home module path as
    its canonical `home_qualified_name`."""
    node = get_symbol(f"{fake_package}.api::Client")
    assert node.home_qualified_name == f"{fake_package}._impl::Client"


def test_home_qualified_name_self_for_instance_constants(
    fake_package: str,
) -> None:
    """An instance constant's `home_qualified_name` stays
    self-referential (its `__module__` resolves via its class, so a
    `re`-owned home would record a false fact)."""
    node = get_symbol(f"{fake_package}.constants::PATTERN")
    assert node.home_qualified_name == f"{fake_package}.constants::PATTERN"


def test_signature_of_broad_failure_returns_marker() -> None:
    """A `__signature__` descriptor raising outside `TypeError` |
    `ValueError` returns the unavailable marker, not a traceback."""

    class _Exploding:
        """A callable whose signature introspection explodes."""

        def __call__(self) -> None:
            """Do nothing."""

        @property
        def __signature__(self) -> None:
            """Raise on signature access."""
            msg = "boom"
            raise RuntimeError(msg)

    assert _signature_of(_Exploding()) == SIGNATURE_UNAVAILABLE


def test_signature_of_uninspectable_returns_marker() -> None:
    """A non-callable object returns the unavailable marker."""
    assert _signature_of(object()) == SIGNATURE_UNAVAILABLE


def test_get_module_tree_walks_submodules(fake_package: str) -> None:
    """`get_module_tree` walks the package's nested module hierarchy."""
    pairs = get_module_tree(fake_package)
    depths_and_names = [(depth, node.name) for depth, node in pairs]
    assert (0, fake_package) in depths_and_names
    assert (1, "module") in depths_and_names


def test_find_symbol_blank_query_raises(isolated_cache: Path) -> None:
    """A blank search query raises `InvalidArgumentError` (previously:
    arbitrary FTS prefix-match results were returned silently)."""
    with pytest.raises(InvalidArgumentError):
        find_symbol("   ")


def test_find_symbol_searches_cached_symbols(fake_package: str) -> None:
    """`find_symbol` searches symbols already cached for the project."""
    show_module(fake_package)
    results = find_symbol("Dog")
    names = [node.name for node in results]
    assert "Dog" in names


def test_walk_submodules_skips_import_failure(
    fake_package: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A submodule that raises on import is logged and skipped, and the
    walk continues over the remaining submodules."""
    with caplog.at_level(logging.WARNING, logger="venvaxi"):
        _, children = show_module(fake_package)
    names = [child.name for child in children]
    assert "module" in names
    assert "error" not in names
    assert "Skipping submodule" in caplog.text


def test_resolve_import_name_returns_import_name_key_unchanged() -> None:
    """A name already present as an import-name key keeps its case."""
    with mock.patch(
        "venvaxi._introspect.metadata.packages_distributions",
        return_value={"PIL": ["pillow"]},
    ):
        assert _resolve_import_name("PIL") == "PIL"
        assert _resolve_import_name("pillow") == "PIL"


def test_resolve_import_name_fallback_preserves_case() -> None:
    """The unmapped fallback normalizes dashes but never case."""
    with mock.patch(
        "venvaxi._introspect.metadata.packages_distributions",
        return_value={},
    ):
        assert _resolve_import_name("MyPkg") == "MyPkg"
        assert _resolve_import_name("my-pkg") == "my_pkg"


def test_get_module_tree_dotted_name_measures_depth_from_submodule(
    fake_package: str,
) -> None:
    """A dotted-name tree request builds deep enough to honor
    `max_depth` measured from the submodule, not the package root."""
    get_module_tree(fake_package)  # default-depth root build first
    pairs = get_module_tree(f"{fake_package}.subpkg", max_depth=2)
    depths_and_names = [(depth, node.name) for depth, node in pairs]
    assert (2, "leaf") in depths_and_names


def test_show_module_resolves_deep_dotted_module(fake_package: str) -> None:
    """A deep dotted module resolves with its children present."""
    node, children = show_module(f"{fake_package}.subpkg.inner.leaf")
    assert node.kind is NodeKind.MODULE
    assert "ping" in [child.name for child in children]


def test_walk_module_keeps_instance_constants_without_all(
    fake_package: str,
) -> None:
    """Instance constants (whose `__module__` resolves via their class)
    are kept as `ATTRIBUTE` nodes in a no-`__all__` submodule."""
    _, children = show_module(f"{fake_package}.constants")
    by_name = {child.name: child for child in children}
    assert by_name["PATTERN"].kind is NodeKind.ATTRIBUTE
    assert by_name["MAX_RETRIES"].kind is NodeKind.ATTRIBUTE


def test_walk_module_keeps_private_home_facade_reexports(
    fake_package: str,
) -> None:
    """A class re-exported from a private module inside the same
    package is kept (the facade is its only public surface)."""
    _, children = show_module(f"{fake_package}.api")
    client = next(child for child in children if child.name == "Client")
    assert client.kind is NodeKind.CLASS


def test_find_symbol_refresh_without_package_raises(
    isolated_cache: Path,
) -> None:
    """`refresh` without `package` raises instead of a silent no-op."""
    with pytest.raises(InvalidArgumentError):
        find_symbol("Console", refresh=True)


def test_find_symbol_package_scopes_results(
    fake_module: types.ModuleType, fake_package: str
) -> None:
    """`package` indexes the package (even when unrelated cached
    symbols exist) and scopes the search to it."""
    show_module(fake_module.__name__)  # warm an unrelated module's cache
    results = find_symbol("Dog", package=fake_package)
    assert "Dog" in [node.name for node in results]
    assert {node.package for node in results} == {fake_package}
    # A symbol cached for the unrelated module is excluded when scoped
    assert find_symbol("Greeter", package=fake_package) == []


def test_get_inheritors_raises_for_unknown_base(fake_package: str) -> None:
    """An unknown base class raises `SymbolNotFoundError`."""
    with pytest.raises(SymbolNotFoundError):
        get_inheritors(f"{fake_package}::DoesNotExist")


def test_walk_module_visited_set_prevents_revisit(
    fake_package: str, tmp_path: Path
) -> None:
    """A submodule name already present in `visited` is skipped, even
    though `pkgutil.iter_modules` would otherwise discover it."""
    module = importlib.import_module(fake_package)
    with SymbolStore(tmp_path / "revisit-store.db") as store:
        _walk_module(
            module,
            package_root=fake_package,
            depth=0,
            max_depth=2,
            visited={f"{fake_package}.module"},
            store=store,
            package=fake_package,
            version="1.0.0",
        )
        children = store.get_children(fake_package)
    assert "module" not in [child.name for child in children]
