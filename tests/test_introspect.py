"""Unit tests for `venvaxi._introspect`."""

import importlib
import logging
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from venvaxi._cache import get_cache_db_path
from venvaxi._core import get_project_root
from venvaxi._introspect import (
    DEFAULT_MAX_DEPTH,
    DOCSTRING_ABSENT,
    MCP_ESCAPE_HATCH,
    SIGNATURE_UNAVAILABLE,
    _doc_of,
    _ensure_installed,
    _ensure_valid_name,
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
    summarize_doc,
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


def test_truncate_default_suffix_is_byte_identical_cli_spelling() -> None:
    """The default suffix keeps today's exact CLI wording - the escape
    hatch names `--docstring`, the flag the CLI caller can pass."""
    result = truncate("x" * 20, limit=5)
    assert result == (
        "xxxxx... truncated, 20 chars total"
        " - use --docstring to see complete body"
    )


def test_truncate_mcp_escape_hatch_names_parameter() -> None:
    """The MCP phrasing names `docstring=true`, never the CLI flag -
    the suffix travels inside the payload, so a hardcoded CLI spelling
    would teach an MCP caller an invocation it cannot make (#30)."""
    result = truncate("x" * 20, limit=5, escape_hatch=MCP_ESCAPE_HATCH)
    assert result == (
        "xxxxx... truncated, 20 chars total"
        " - re-call with docstring=true for the complete body"
    )
    assert "--docstring" not in result


def test_summarize_doc_forwards_escape_hatch() -> None:
    """`summarize_doc` threads the caller's phrasing into `truncate`."""
    result = summarize_doc("x" * 20, limit=5, escape_hatch=MCP_ESCAPE_HATCH)
    assert "docstring=true" in result
    assert "--docstring" not in result


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


def test_summarize_doc_absent_returns_marker() -> None:
    """An absent docstring emits the marker, not a silent blank."""
    assert summarize_doc("") == DOCSTRING_ABSENT


def test_summarize_doc_absent_returns_marker_in_full_mode() -> None:
    """The marker is emitted under `docstring=True` too."""
    assert summarize_doc("", docstring=True) == DOCSTRING_ABSENT


def test_summarize_doc_present_is_unaffected_by_marker() -> None:
    """A real docstring is still reduced to its first line."""
    assert summarize_doc("First line.\n\nBody.") == "First line."


def test_doc_of_does_not_record_the_absent_marker() -> None:
    """The marker is emission-only - recording it would put its text into
    the FTS index and make every undocumented symbol match a search."""

    class Bare:
        pass

    assert _doc_of(Bare, NodeKind.CLASS) == ""
    assert DOCSTRING_ABSENT not in _doc_of(Bare, NodeKind.CLASS)


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


def test_get_public_api_forwards_escape_hatch(
    fake_module: types.ModuleType,
) -> None:
    """`get_public_api` threads the caller's phrasing into truncation -
    it is the only path by which `showPackageApiTool` payloads reach
    `truncate`, so a dropped forward reverts #30 for that tool."""
    symbols = get_public_api(
        fake_module.__name__, limit=5, escape_hatch=MCP_ESCAPE_HATCH
    )
    greet = next(symbol for symbol in symbols if symbol.name == "greet")
    assert "docstring=true" in greet.doc
    assert "--docstring" not in greet.doc


def test_get_public_api_full_returns_complete_docstring(
    fake_module: types.ModuleType,
) -> None:
    """`docstring=True` returns the complete, untruncated docstring."""
    symbols = get_public_api(fake_module.__name__, docstring=True)
    greet = next(symbol for symbol in symbols if symbol.name == "greet")
    assert "friendly greeting" in greet.doc


def test_get_public_api_invalid_name_raises() -> None:
    """A malformed package name raises `InvalidArgumentError`.

    NOTE: Distinct from `PackageNotFoundError` - `../etc/passwd` is not
    a package name that failed to resolve, so reporting it as missing
    would invite the caller to try installing it.
    """
    with pytest.raises(InvalidArgumentError):
        get_public_api("../etc/passwd")


def test_get_public_api_not_installed_raises() -> None:
    """An uninstalled package raises `PackageNotFoundError`."""
    with pytest.raises(PackageNotFoundError, match="not installed"):
        get_public_api("this-package-does-not-exist-xyz")


@pytest.mark.parametrize(
    "name",
    [".foo", "...", "", "a b", "../etc/passwd", "foo/bar", "-x", "foo-", "."],
)
def test_ensure_valid_name_rejects_degenerate(name: str) -> None:
    """A name that cannot possibly name a package raises
    `InvalidArgumentError`, carrying the caller's spelling."""
    with pytest.raises(InvalidArgumentError, match="Invalid package name"):
        _ensure_valid_name(name, name)


@pytest.mark.parametrize(
    "name",
    ["rich.console", "detect-secrets", "zope.interface", "2to3", "_", "a"],
)
def test_ensure_valid_name_accepts_legitimate(name: str) -> None:
    """Every legitimate name shape passes, including the single-character
    and digit-leading forms the trailing regex group must not require."""
    _ensure_valid_name(name, name)


def test_get_module_tree_malformed_raises() -> None:
    """A degenerate name raises `InvalidArgumentError`, not the
    unhandled `ValueError` that produced `EX_SYNTAX` (previously:
    `Unexpected error: A distribution name is required.`)."""
    with pytest.raises(InvalidArgumentError, match="Invalid package name"):
        get_module_tree(".foo")


def test_get_symbol_malformed_raises() -> None:
    """A qualified name with a malformed root raises
    `InvalidArgumentError` naming the caller's full spelling - the root
    of `.foo::Bar` is `""`, which names nothing the caller can fix."""
    with pytest.raises(InvalidArgumentError) as excinfo:
        get_symbol(".foo::Bar")
    assert ".foo::Bar" in str(excinfo.value)


def test_get_inheritors_malformed_raises() -> None:
    """`inherits` shares the builder guard with `inspect`."""
    with pytest.raises(InvalidArgumentError, match="Invalid package name"):
        get_inheritors(".foo::Bar")


def test_find_symbol_malformed_package_raises() -> None:
    """`--package` with an impossible name raises `InvalidArgumentError`
    rather than inviting an install that can never succeed (previously:
    `PackageNotFoundError`)."""
    with pytest.raises(InvalidArgumentError, match="Invalid package name"):
        find_symbol("Nope", package="a b")


def test_get_public_api_space_name_raises() -> None:
    """A space-carrying name is malformed, not absent (previously:
    `PackageNotFoundError`)."""
    with pytest.raises(InvalidArgumentError, match="Invalid package name"):
        get_public_api("a b")


def test_get_public_api_derives_build_depth(fake_package: str) -> None:
    """A dotted module deeper than `DEFAULT_MAX_DEPTH` answers from a
    graph built to its own depth.

    NOTE: `refresh=True` is load-bearing - it pins the answer against a
    *rebuilt* cache, so this test cannot pass merely because an earlier
    query deepened the shared graph, and fails if the depth derivation
    is dropped again (`specs/behaviors/cache-refresh.md`, Validity).
    """
    symbols = get_public_api(f"{fake_package}.subpkg.inner.leaf", refresh=True)
    assert [symbol.name for symbol in symbols] == ["Widget", "ping"]


def test_get_public_api_top_level_keeps_default_depth(
    fake_package: str,
) -> None:
    """A top-level package still builds at `DEFAULT_MAX_DEPTH` - the
    depth derivation must not trigger a deeper build it does not need."""
    symbols = get_public_api(fake_package)
    assert [symbol.name for symbol in symbols] == ["Animal", "Cat", "Dog"]
    with SymbolStore(get_cache_db_path(get_project_root())) as store:
        build = store.get_build(fake_package)
    assert build is not None
    assert build[1] == DEFAULT_MAX_DEPTH


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


def test_get_module_tree_not_installed_raises(
    isolated_cache: Path,
) -> None:
    """An uninstalled module name raises `PackageNotFoundError`."""
    with pytest.raises(PackageNotFoundError, match="not installed"):
        get_module_tree("this_module_does_not_exist_xyz")


def test_get_symbol_not_installed_raises(isolated_cache: Path) -> None:
    """A qualified name under an uninstalled package raises
    `PackageNotFoundError`, naming the package rather than the whole
    qualified name."""
    with pytest.raises(PackageNotFoundError) as excinfo:
        get_symbol("this_module_does_not_exist_xyz::Nope")
    assert "::Nope" not in str(excinfo.value)


def test_get_inheritors_not_installed_raises(isolated_cache: Path) -> None:
    """An uninstalled package raises `PackageNotFoundError` for
    `inherits`, which shares the builder with `inspect`."""
    with pytest.raises(PackageNotFoundError, match="not installed"):
        get_inheritors("this_module_does_not_exist_xyz::Nope")


def test_find_symbol_not_installed_raises(isolated_cache: Path) -> None:
    """`--package` naming an uninstalled package raises
    `PackageNotFoundError`."""
    with pytest.raises(PackageNotFoundError, match="not installed"):
        find_symbol("Nope", package="this_module_does_not_exist_xyz")


def test_ensure_installed_accepts_undistributed_module() -> None:
    """An importable module with no installed distribution passes.

    NOTE: A stdlib module is claimed by no distribution at all, and
    'install it' is the wrong advice for one - the check asks the import
    system, not `importlib.metadata`.
    """
    _ensure_installed("json", "json")


def test_ensure_installed_accepts_specless_module(
    fake_module: types.ModuleType,
) -> None:
    """A `sys.modules` entry with no `__spec__` passes.

    NOTE: `importlib.util.find_spec` *raises* on such a module rather
    than returning, so the `sys.modules` short-circuit is what keeps a
    bare `types.ModuleType` from reading as uninstalled.
    """
    assert fake_module.__spec__ is None
    _ensure_installed(fake_module.__name__, fake_module.__name__)


def test_ensure_installed_accepts_dashed_distribution_name() -> None:
    """A dashed distribution name resolves to its import name first."""
    import_name = _resolve_import_name("detect-secrets")
    assert import_name == "detect_secrets"
    _ensure_installed(import_name, "detect-secrets")


def test_ensure_installed_survives_a_raising_finder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `sys.meta_path` finder that raises reads as 'not located'.

    NOTE: `find_spec` may raise rather than return None; the failure
    must fall through to the distribution check, not escape as an
    unhandled error.
    """

    def _raise(name: str) -> None:
        msg = f"finder blew up on {name}"
        raise ImportError(msg)

    monkeypatch.setattr("venvaxi._introspect.importlib.util.find_spec", _raise)
    with pytest.raises(PackageNotFoundError, match="not installed"):
        _ensure_installed("nothing_claims_this_xyz", "nothing_claims_this_xyz")


def test_ensure_installed_defers_to_import_for_installed_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An installed distribution that cannot be located passes the check.

    NOTE: Installed-but-broken is an investigate-it answer, so the guard
    falls through and lets the caller's import attempt report
    `PackageImportError` instead.
    """
    monkeypatch.setattr(
        "venvaxi._introspect.importlib.util.find_spec", lambda _: None
    )
    monkeypatch.delitem(sys.modules, "detect_secrets", raising=False)
    _ensure_installed("detect_secrets", "detect-secrets")


def test_build_store_for_installed_but_broken_raises_import_error(
    isolated_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An installed package raising on import still reports
    `PackageImportError`, not `PackageNotFoundError`."""

    def _raise(name: str) -> types.ModuleType:
        msg = f"boom: {name}"
        raise ImportError(msg)

    monkeypatch.setattr("importlib.import_module", _raise)
    with pytest.raises(PackageImportError):
        get_module_tree("rich")


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


def test_get_symbol_resolves_facade_spelled_method(fake_package: str) -> None:
    """A method spelled through a facade resolves to its home-keyed row,
    answered as stored (the home spelling, never the caller's)."""
    node = get_symbol(f"{fake_package}.api::Client.connect")
    assert node.qualified_name == f"{fake_package}._impl::Client.connect"
    assert node.kind is NodeKind.METHOD
    assert node.module == f"{fake_package}._impl"


def test_get_symbol_facade_member_miss_raises(fake_package: str) -> None:
    """A facade-spelled member absent from the home row is a genuine
    miss, keyed to the caller's spelling in the message."""
    with pytest.raises(SymbolNotFoundError, match="api::Client.nosuchmethod"):
        get_symbol(f"{fake_package}.api::Client.nosuchmethod")


def test_get_symbol_home_keyed_member_miss_raises(fake_package: str) -> None:
    """A missing member on an already home-keyed owner raises without
    engaging the fallback (`canonical_name` is a no-op there)."""
    with pytest.raises(SymbolNotFoundError):
        get_symbol(f"{fake_package}._impl::Client.nosuchmethod")


def test_get_symbol_resolves_facade_spelled_nested_class(
    fake_package: str,
) -> None:
    """A nested class resolves through the fallback as an attribute
    member of its outer class."""
    node = get_symbol(f"{fake_package}.facade::Widget.Inner")
    leaf = f"{fake_package}.subpkg.inner.leaf"
    assert node.qualified_name == f"{leaf}::Widget.Inner"
    assert node.kind is NodeKind.ATTRIBUTE


def test_get_symbol_nested_class_member_missing_both_spellings(
    fake_package: str,
) -> None:
    """Members of nested classes are not indexed - the not-found answer
    is definitive under the facade and the home spelling alike."""
    leaf = f"{fake_package}.subpkg.inner.leaf"
    with pytest.raises(SymbolNotFoundError):
        get_symbol(f"{fake_package}.facade::Widget.Inner.zoom")
    with pytest.raises(SymbolNotFoundError):
        get_symbol(f"{leaf}::Widget.Inner.zoom")


def test_get_symbol_resolves_deep_home_member_without_rebuild(
    fake_package: str,
) -> None:
    """A member homed deeper than the built depth (offset 3 against a
    built depth of 2) resolves with no deeper rebuild - member rows are
    written by the class walk at home keys regardless of build depth."""
    from venvaxi import _introspect

    with mock.patch.object(
        _introspect,
        "_build_store_for",
        side_effect=_introspect._build_store_for,
    ) as build_spy:
        node = get_symbol(f"{fake_package}.facade::Widget.poke")
    assert node.qualified_name == (
        f"{fake_package}.subpkg.inner.leaf::Widget.poke"
    )
    assert node.kind is NodeKind.METHOD
    assert build_spy.call_count == 1


def test_get_symbol_module_level_miss_skips_fallback(
    fake_package: str,
) -> None:
    """A dot-free tail takes the unchanged raise path - the fallback
    disengages before any owner resolution."""
    with (
        mock.patch.object(
            SymbolStore, "canonical_name", autospec=True
        ) as canonical_spy,
        pytest.raises(SymbolNotFoundError),
    ):
        get_symbol(f"{fake_package}::DoesNotExist")
    canonical_spy.assert_not_called()


def test_module_docs_route_through_own_doc(fake_package: str) -> None:
    """`PACKAGE` and submodule node docs match each module's own
    docstring after the `_own_doc` reroute - asserted against a real
    on-disk package walked by the real builder, not a mock."""
    package_node, _ = show_module(fake_package)
    assert package_node.doc == "Fixture package."
    submodule_node, _ = show_module(f"{fake_package}.module")
    assert submodule_node.doc == "Fixture package submodule."


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


def test_find_symbol_negative_limit_raises(isolated_cache: Path) -> None:
    """A negative limit raises `InvalidArgumentError` (previously: it
    reached SQLite's `LIMIT ?` as unbounded and returned the whole
    graph, defeating the cap it was asked to set) (#73)."""
    with pytest.raises(InvalidArgumentError):
        find_symbol("a", -5)


def test_find_symbol_negative_limit_message_suits_both_surfaces(
    isolated_cache: Path,
) -> None:
    """The rejection names the input and echoes the offending value,
    spelling neither the CLI flag nor the tool parameter - it is raised
    on the path both surfaces share (#73)."""
    with pytest.raises(InvalidArgumentError) as exc_info:
        find_symbol("a", -5)
    message = str(exc_info.value)
    assert "-5" in message
    assert "--limit" not in message
    assert "limit=" not in message


def test_find_symbol_negative_limit_raises_before_package_build(
    isolated_cache: Path,
) -> None:
    """The negative-limit rejection precedes the graph build, so the
    `package`-scoped path is bounded too and pays nothing to learn it
    (#73)."""
    with (
        mock.patch("venvaxi._introspect._build_store_for") as build,
        pytest.raises(InvalidArgumentError),
    ):
        find_symbol("a", -1, package="rich")
    build.assert_not_called()


def test_find_symbol_zero_limit_returns_no_results(
    fake_package: str,
) -> None:
    """A limit of zero is a bound the search honours exactly - no rows
    and no rejection. It is well behaved and stays outside the
    negative-limit fix (#73)."""
    show_module(fake_package)
    assert find_symbol("Dog") != []
    assert find_symbol("Dog", 0) == []


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


def test_walk_submodules_contains_base_exception_import(
    fake_package: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A submodule raising a `BaseException` subclass at import time -
    the #64 specimen: `numpy.f2py` raises `_pytest.outcomes.Skipped` -
    is skipped like any other broken submodule and the walk completes
    (previously: it escaped `except Exception` and took the whole
    command down)."""
    with caplog.at_level(logging.WARNING, logger="venvaxi"):
        _, children = show_module(fake_package)
    names = [child.name for child in children]
    assert "module" in names
    assert "base_error" not in names
    assert "Skipping submodule `package.base_error`" in caplog.text


def test_walk_submodules_contains_system_exit_import(
    fake_package: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A submodule raising `SystemExit` at import time is contained at
    the import boundary - the walk completes on its own result, never
    the submodule's exit status (#64)."""
    with caplog.at_level(logging.WARNING, logger="venvaxi"):
        _, children = show_module(fake_package)
    names = [child.name for child in children]
    assert "module" in names
    assert "exit_error" not in names
    assert "Skipping submodule `package.exit_error`" in caplog.text


def test_walk_submodules_reraises_keyboard_interrupt(
    fake_package: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`KeyboardInterrupt` propagates out of the walk unswallowed - a
    long walk must stay abortable (#64)."""
    real_import = importlib.import_module

    def _interrupt(name: str, *args: object, **kwargs: object) -> object:
        if name == "package.module":
            raise KeyboardInterrupt
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("importlib.import_module", _interrupt)
    with pytest.raises(KeyboardInterrupt):
        show_module(fake_package)


def test_build_store_for_base_exception_import_reports_broken(
    isolated_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The requested package itself raising a `BaseException` at import
    time reports `PackageImportError` - broken, exit 1 - never an
    unexpected-error crash (#64)."""

    class ImportCrash(BaseException):
        """A `BaseException` subclass that is not an `Exception`."""

    def _raise(name: str) -> types.ModuleType:
        raise ImportCrash(name)

    monkeypatch.setattr("importlib.import_module", _raise)
    with pytest.raises(PackageImportError):
        get_module_tree("rich")


def test_get_public_api_base_exception_import_reports_broken(
    isolated_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`get_public_api` classes any import-time raise as broken - its
    guard covered only `ImportError` (#64)."""

    class ImportCrash(BaseException):
        """A `BaseException` subclass that is not an `Exception`."""

    def _raise(name: str) -> types.ModuleType:
        raise ImportCrash(name)

    monkeypatch.setattr("importlib.import_module", _raise)
    with pytest.raises(PackageImportError):
        get_public_api("rich")


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


def test_callable_instance_records_call_signature(fake_package: str) -> None:
    """A module-level callable instance records the signature derived
    from its class `__call__` - the `pl.col` shape (#66). Previously
    the kind guard recorded `""` for every attribute."""
    node = get_symbol(f"{fake_package}.constants::col")
    assert node.kind is NodeKind.ATTRIBUTE
    assert "column" in node.signature


def test_callable_instance_failing_signature_records_marker(
    fake_package: str,
) -> None:
    """A callable whose signature introspection raises records
    `(signature unavailable)` - introspection failed, distinct from
    'takes no arguments' and from 'not callable' (#66)."""
    node = get_symbol(f"{fake_package}.constants::opaque")
    assert node.kind is NodeKind.ATTRIBUTE
    assert node.signature == SIGNATURE_UNAVAILABLE


def test_non_callable_attribute_records_empty_signature(
    fake_package: str,
) -> None:
    """A non-callable attribute's `signature` is `""` - the definitive
    'this symbol is not callable' answer, no third marker (#66)."""
    node = get_symbol(f"{fake_package}.constants::MAX_RETRIES")
    assert node.kind is NodeKind.ATTRIBUTE
    assert node.signature == ""


def test_get_public_api_keeps_class_function_filter(
    fake_package: str,
) -> None:
    """`show --api` keeps its class/function filter - callable
    instances gaining signatures must not silently widen the listing
    (#66)."""
    symbols = get_public_api(f"{fake_package}.constants")
    assert [symbol.name for symbol in symbols] == []


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
