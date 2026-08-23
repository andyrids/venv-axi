"""Unit tests for `venvaxi._mcp`."""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest

pytest.importorskip("fastmcp")
# ruff: disable[E402]
from venvaxi._cache import CacheState, PackageBuild, get_cache_db_path
from venvaxi._constants import NO_PROJECT_ROOT
from venvaxi._core import resolve_binding
from venvaxi._introspect import (
    MCP_ESCAPE_HATCH,
    PublicAPI,
    RefreshReceipt,
    SymbolInfo,
)
from venvaxi._mcp import build_server
from venvaxi._packages import PackageInfo
from venvaxi._store import NodeKind, SymbolNode
from venvaxi._toon import encode_object
from venvaxi.exceptions import (
    ProjectRootNotFoundError,
    StoreError,
    SymbolNotFoundError,
)

# ruff: enable[E402]
CORE = "venvaxi._core"
MCP = "venvaxi._mcp"

NodeFactory = Callable[..., SymbolNode]
PackageFactory = Callable[..., PackageInfo]


def camel_case(name: str) -> str:
    """Convert a snake_case name to camelCase."""
    import re

    def match_upper(match: re.Match) -> str:
        return match.group(1).upper()

    return re.sub(r"_([a-zA-Z])", match_upper, name)


def test_build_server_registers_tools() -> None:
    """`build_server` registers all ten expected MCP tools."""
    from venvaxi import _mcp

    server = build_server()
    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert names == {
        camel_case(_mcp.describe_binding_tool.__name__),
        camel_case(_mcp.list_packages_tool.__name__),
        camel_case(_mcp.show_package_tool.__name__),
        camel_case(_mcp.show_package_api_tool.__name__),
        camel_case(_mcp.show_module_tool.__name__),
        camel_case(_mcp.get_symbol_tool.__name__),
        camel_case(_mcp.find_symbol_tool.__name__),
        camel_case(_mcp.get_inheritors_tool.__name__),
        camel_case(_mcp.get_module_tree_tool.__name__),
        camel_case(_mcp.refresh_package_graph_tool.__name__),
    }


def test_describe_binding_tool_reports_binding(
    tmp_path: Path, isolated_cache: Path
) -> None:
    """The tool emits the flat `root`/`venv`/`status` object."""
    server = build_server()
    with mock.patch(f"{CORE}.get_project_root", return_value=tmp_path):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "root:" in result
    assert "venv:" in result
    assert "status:" in result


def test_describe_binding_tool_footer_names_camel_case(
    tmp_path: Path, isolated_cache: Path
) -> None:
    """The success footer names next-step tools by camelCase name and
    carries no `venvaxi` shell spelling."""
    server = build_server()
    with mock.patch(f"{CORE}.get_project_root", return_value=tmp_path):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "help[2]:" in result
    assert "listPackagesTool" in result
    assert "include_dev=true" in result
    assert "findSymbolTool" in result
    assert "list_packages_tool" not in result
    assert "venvaxi " not in result


def test_describe_binding_tool_no_root_reports_marker() -> None:
    """No resolvable root degrades to the marker with no error block,
    and the hint names the registration rather than an invocation."""
    server = build_server()
    with mock.patch(
        f"{CORE}.get_project_root",
        side_effect=ProjectRootNotFoundError("nope"),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert f"root: {NO_PROJECT_ROOT}" in result
    assert "venv:" in result
    assert "error: true" not in result
    assert ".mcp.json" in result
    assert "venvaxi " not in result


def test_describe_binding_tool_unexpected_error_returns_error_block() -> None:
    """A non-`ProjectRootNotFoundError` returns the `Unexpected error:`
    block, never the marker - the degrade is scoped to its trigger."""
    server = build_server()
    with mock.patch(f"{CORE}.get_project_root", side_effect=OSError("gone")):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "error: true" in result
    assert "Unexpected error: gone" in result
    assert NO_PROJECT_ROOT not in result


def test_describe_binding_tool_description_is_call_first() -> None:
    """The registered description identifies the binding and carries
    the call-me-first signal (`specs/mcp/tools.md`)."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("describe_binding_tool")))
    description = tool.description or ""
    assert "project" in description
    assert "venv" in description
    assert "answers from" in description
    assert "Call this first" in description


def test_describe_binding_tool_registered_schema_takes_no_parameters() -> None:
    """The registered `describeBindingTool` schema still declares no
    parameters - the cache summary is unconditional on `root`, never a
    new argument (Validation criterion 18)."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("describe_binding_tool")))
    assert tool.parameters.get("properties", {}) == {}


def test_describe_binding_tool_description_states_cache_summary() -> None:
    """The registered description also states that the report includes
    a cache summary - schema version, on-disk size, and which packages
    are indexed at which built version and depth (#49;
    `specs/mcp/tools.md`, The description is part of the contract)."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("describe_binding_tool")))
    description = tool.description or ""
    assert "schema version" in description
    assert "on-disk size" in description
    assert "built version and depth" in description


def test_describe_binding_tool_reports_cache_summary_when_root_resolves(
    tmp_path: Path,
) -> None:
    """When `root` resolves, the object gains `schema_version`,
    `db_path`, `db_size_bytes`, then `count:` and a `builds` table,
    field for field matching `venvaxi cache` (#49)."""
    server = build_server()
    state = CacheState(
        schema_version=7,
        db_path=tmp_path / "cache.db",
        db_size_bytes=1234,
        builds=[
            PackageBuild(package="rich", version="1.0.0", depth=2, symbols=42)
        ],
    )
    with (
        mock.patch(f"{CORE}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.read_cache_state", return_value=state),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "schema_version: 7" in result
    assert "db_size_bytes: 1234" in result
    assert "count: 1" in result
    assert "rich|1.0.0|2|42" in result


def test_describe_binding_tool_cache_summary_empty_omits_table(
    tmp_path: Path,
) -> None:
    """A real, empty cache reports `count: 0` and no `builds` table -
    distinct from the `(cache unreadable)` degrade below."""
    server = build_server()
    state = CacheState(
        schema_version=7,
        db_path=tmp_path / "cache.db",
        db_size_bytes=0,
        builds=[],
    )
    with (
        mock.patch(f"{CORE}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.read_cache_state", return_value=state),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "schema_version: 7" in result
    assert "count: 0" in result
    assert "builds" not in result


def test_describe_binding_tool_cache_summary_not_built_reports_marker(
    tmp_path: Path,
) -> None:
    """A never-built cache reports `schema_version: (not built)`, never
    the literal string stored - it is applied at emission only."""
    server = build_server()
    state = CacheState(
        schema_version=None,
        db_path=tmp_path / "cache.db",
        db_size_bytes=0,
        builds=[],
    )
    with (
        mock.patch(f"{CORE}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.read_cache_state", return_value=state),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "schema_version: (not built)" in result
    assert "count: 0" in result


def test_describe_binding_tool_cache_nonzero_count_appends_third_hint(
    tmp_path: Path,
) -> None:
    """A nonzero `count` appends a third hint naming
    `refreshPackageGraphTool`, additional to the two onboarding hints."""
    server = build_server()
    state = CacheState(
        schema_version=7,
        db_path=tmp_path / "cache.db",
        db_size_bytes=1234,
        builds=[
            PackageBuild(package="rich", version="1.0.0", depth=2, symbols=42)
        ],
    )
    with (
        mock.patch(f"{CORE}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.read_cache_state", return_value=state),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "help[3]:" in result
    assert "refreshPackageGraphTool" in result


def test_describe_binding_tool_cache_zero_count_omits_third_hint(
    tmp_path: Path,
) -> None:
    """A `count: 0` cache summary appends no third hint - both
    onboarding hints already name the way to populate a first entry."""
    server = build_server()
    state = CacheState(
        schema_version=7,
        db_path=tmp_path / "cache.db",
        db_size_bytes=0,
        builds=[],
    )
    with (
        mock.patch(f"{CORE}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.read_cache_state", return_value=state),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "help[2]:" in result
    assert "refreshPackageGraphTool" not in result


def test_describe_binding_tool_no_root_omits_cache_fields() -> None:
    """No resolvable root omits the cache summary entirely - there is
    nothing truthful to say about a cache belonging to no project."""
    server = build_server()
    with mock.patch(
        f"{CORE}.get_project_root",
        side_effect=ProjectRootNotFoundError("nope"),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "schema_version" not in result
    assert "db_path" not in result
    assert "count:" not in result


def test_describe_binding_tool_unreadable_cache_degrades(
    tmp_path: Path, isolated_cache: Path
) -> None:
    """A SQLite-level failure reading the cache degrades that half of
    the object rather than raising - `root`/`venv`/`status` still
    report exactly as on a healthy read, and no error block is
    returned (#49; `specs/mcp/tools.md`, Failure modes)."""
    server = build_server()
    root = tmp_path / "proj"
    root.mkdir()
    db_path = get_cache_db_path(root)
    db_path.write_bytes(b"not a real sqlite file" * 10)
    with (
        mock.patch(f"{CORE}.get_project_root", return_value=root),
        mock.patch(
            f"{MCP}.read_cache_state", side_effect=StoreError("bad schema")
        ),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "root:" in result
    assert "venv:" in result
    assert "status:" in result
    assert "error: true" not in result
    assert "schema_version: (cache unreadable)" in result
    assert f"db_size_bytes: {db_path.stat().st_size}" in result
    # NOTE: A wording-correction/shape assertion checks the wrong form
    # is absent, not merely that the right form is present
    # (`reference-toolchain-pytest.md`) - `count: 0` here would
    # misstate an unreadable database as a real, empty one.
    assert "count:" not in result
    assert "builds" not in result


def test_describe_binding_tool_unreadable_cache_never_emits_count_zero(
    tmp_path: Path, isolated_cache: Path
) -> None:
    """The unreadable-cache degrade never emits `count: 0` - that is
    the positive claim the database opened cleanly and held nothing, a
    different state from 'could not be read at all'."""
    server = build_server()
    root = tmp_path / "proj"
    root.mkdir()
    db_path = get_cache_db_path(root)
    db_path.write_bytes(b"garbage")
    with (
        mock.patch(f"{CORE}.get_project_root", return_value=root),
        mock.patch(
            f"{MCP}.read_cache_state", side_effect=StoreError("bad schema")
        ),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "count: 0" not in result


def test_describe_binding_tool_unreadable_cache_hints_delete(
    tmp_path: Path, isolated_cache: Path
) -> None:
    """The unreadable-cache degrade appends a third hint naming the
    reported `db_path` as safe to delete."""
    server = build_server()
    root = tmp_path / "proj"
    root.mkdir()
    db_path = get_cache_db_path(root)
    db_path.write_bytes(b"garbage")
    with (
        mock.patch(f"{CORE}.get_project_root", return_value=root),
        mock.patch(
            f"{MCP}.read_cache_state", side_effect=StoreError("bad schema")
        ),
    ):
        tool = asyncio.run(
            server.get_tool(camel_case("describe_binding_tool"))
        )
        result = tool.fn()
    assert "help[3]:" in result
    assert "disposable derived data" in result
    assert str(db_path.name) in result


def test_build_server_instructions_carry_binding() -> None:
    """The initialization instructions carry the bound root and venv."""
    with mock.patch(
        f"{CORE}.get_project_root", return_value=Path.home() / "proj"
    ):
        server = build_server()
        _, venv, _ = resolve_binding()
    # NOTE: `~/proj` holds no TOON-escapable characters, so it appears
    # verbatim; the venv line is matched in its encoded form because a
    # Windows path is escaped-and-quoted by the encoder.
    assert "root: ~/proj" in server.instructions
    assert encode_object({"venv": venv}) in server.instructions


def test_build_server_no_root_still_builds_with_marker() -> None:
    """An unresolvable root at startup degrades to the marker - the
    server still builds and serves the full tool surface."""
    with mock.patch(
        f"{CORE}.get_project_root",
        side_effect=ProjectRootNotFoundError("nope"),
    ):
        server = build_server()
    assert NO_PROJECT_ROOT in server.instructions
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert len(names) == 10
    assert camel_case("describe_binding_tool") in names


def test_list_packages_tool_returns_toon(
    tmp_path: Path, make_package_info: PackageFactory
) -> None:
    """The list tool returns a TOON-encoded package table."""
    server = build_server()
    packages = [make_package_info()]
    with (
        mock.patch(f"{MCP}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.list_packages", return_value=packages),
    ):
        tool = asyncio.run(server.get_tool(camel_case("list_packages_tool")))
        result = tool.fn()
    assert "count: 1" in result
    assert "rich|15.0.0" in result


def test_list_packages_tool_hint_describes_metadata_tool(
    tmp_path: Path, make_package_info: PackageFactory
) -> None:
    """The list hint describes what the tool it names actually returns."""
    server = build_server()
    with (
        mock.patch(f"{MCP}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.list_packages", return_value=[make_package_info()]),
    ):
        tool = asyncio.run(server.get_tool(camel_case("list_packages_tool")))
        result = tool.fn()
    assert "showPackageTool" in result
    assert "public API" not in result


def test_list_packages_tool_empty_hint_names_camel_case(
    tmp_path: Path,
) -> None:
    """No packages hints at the tool by its registered camelCase name."""
    server = build_server()
    with (
        mock.patch(f"{MCP}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.list_packages", return_value=[]),
    ):
        tool = asyncio.run(server.get_tool(camel_case("list_packages_tool")))
        result = tool.fn()
    assert result.startswith("count: 0")
    assert "listPackagesTool" in result
    assert "list_packages_tool" not in result


def test_list_packages_tool_empty_hint_names_include_dev(
    tmp_path: Path,
) -> None:
    """Without `include_dev`, the empty-state hint names the parameter
    most likely to produce results."""
    server = build_server()
    with (
        mock.patch(f"{MCP}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.list_packages", return_value=[]),
    ):
        tool = asyncio.run(server.get_tool(camel_case("list_packages_tool")))
        result = tool.fn()
    assert result.startswith("count: 0")
    assert "include_dev=true" in result


def test_list_packages_tool_empty_all_hint_names_pyproject(
    tmp_path: Path,
) -> None:
    """With `include_dev=true`, the empty state is definitive - the hint
    names `pyproject.toml`, never the parameter the caller just passed
    (the suppression rule in `specs/behaviors/output-contract.md`),
    mirroring the CLI's `list --all` branch."""
    server = build_server()
    with (
        mock.patch(f"{MCP}.get_project_root", return_value=tmp_path),
        mock.patch(f"{MCP}.list_packages", return_value=[]),
    ):
        tool = asyncio.run(server.get_tool(camel_case("list_packages_tool")))
        result = tool.fn(include_dev=True)
    assert result.startswith("count: 0")
    assert "pyproject.toml" in result
    assert "include_dev=true" not in result


def test_show_package_tool_returns_toon(
    make_package_info: PackageFactory,
) -> None:
    """The show tool returns TOON-encoded package metadata."""
    server = build_server()
    with mock.patch(
        f"{MCP}.resolve_package", return_value=make_package_info()
    ):
        tool = asyncio.run(server.get_tool(camel_case("show_package_tool")))
        result = tool.fn(name="rich")
    assert "name: rich" in result


def test_show_package_tool_malformed_name_returns_error_block() -> None:
    """A malformed package name returns the domain-error TOON block -
    `InvalidArgumentError` through `_toon_errors`, never the
    `Unexpected error:` shape and never a transport error (#65)."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("show_package_tool")))
    result = tool.fn(name="")
    assert "error: true" in result
    assert "Invalid package name" in result
    assert "Unexpected error" not in result


def test_show_package_api_tool_returns_toon() -> None:
    """The API tool returns TOON-encoded public symbols."""
    server = build_server()
    symbols = [
        SymbolInfo(name="foo", kind="function", signature="()", doc="Foo."),
    ]
    api = PublicAPI(symbols=symbols, max_rows=20)
    with mock.patch(f"{MCP}.get_public_api", return_value=api):
        tool = asyncio.run(
            server.get_tool(camel_case("show_package_api_tool"))
        )
        result = tool.fn(name="rich")
    assert "count: 1" in result
    assert "foo|function" in result


def test_show_package_api_tool_docstring_suppresses_footer() -> None:
    """`docstring=true` returns the bare payload with no `help[]`
    footer, matching `show --api --docstring` on the CLI (#29)."""
    server = build_server()
    symbols = [
        SymbolInfo(name="foo", kind="function", signature="()", doc="Foo."),
    ]
    api = PublicAPI(symbols=symbols, max_rows=20)
    with mock.patch(f"{MCP}.get_public_api", return_value=api):
        tool = asyncio.run(
            server.get_tool(camel_case("show_package_api_tool"))
        )
        result = tool.fn(name="rich", docstring=True)
    assert "count: 1" in result
    assert "help[" not in result


def test_show_package_api_tool_passes_mcp_escape_hatch() -> None:
    """The API tool spells the truncation escape hatch for MCP - its
    payload reaches `truncate` only through `get_public_api` (#30)."""
    server = build_server()
    empty = PublicAPI(symbols=[], max_rows=20)
    with mock.patch(f"{MCP}.get_public_api", return_value=empty) as api:
        tool = asyncio.run(
            server.get_tool(camel_case("show_package_api_tool"))
        )
        tool.fn(name="rich")
    api.assert_called_once_with(
        "rich",
        docstring=False,
        max_rows=20,
        escape_hatch=MCP_ESCAPE_HATCH,
    )


def test_show_package_api_tool_matches_cli_widened_surface(
    fake_package: str,
) -> None:
    """`showPackageApiTool` reports the same widened surface as
    `show <package> --api` for a real package - no mock, so parity is
    `get_public_api`'s, not the test's (`specs/mcp/tools.md`, parity
    principle; #82)."""
    from venvaxi._introspect import get_public_api

    cli_symbols = get_public_api(f"{fake_package}.constants").symbols
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("show_package_api_tool")))
    result = tool.fn(name=f"{fake_package}.constants")

    assert f"count: {len(cli_symbols)}" in result
    assert {symbol.kind for symbol in cli_symbols} == {"attribute"}
    for symbol in cli_symbols:
        assert f"{symbol.name}|{symbol.kind}" in result


def _api_symbols(count: int) -> list[SymbolInfo]:
    """Build `count` distinct API rows."""
    return [
        SymbolInfo(
            name=f"sym_{index}", kind="function", signature="()", doc="Doc."
        )
        for index in range(count)
    ]


def test_show_package_api_tool_default_limit_bounds_rows() -> None:
    """With no `limit` the tool bounds the listing at 20 rows and
    carries the capped-count hint spelled as a tool parameter -
    unbounded, the `numpy` call was refused outright by the transport
    token guard (#67; `specs/mcp/tools.md`, Hint wording)."""
    server = build_server()
    api = PublicAPI(symbols=_api_symbols(20), max_rows=20)
    with mock.patch(f"{MCP}.get_public_api", return_value=api) as patched:
        tool = asyncio.run(
            server.get_tool(camel_case("show_package_api_tool"))
        )
        result = tool.fn(name="numpy")
    assert patched.call_args.kwargs["max_rows"] == 20
    assert "count: 20" in result
    assert "Results capped at limit=20" in result
    assert "higher limit" in result
    assert "--limit" not in result


def test_show_package_api_tool_below_limit_omits_capped_hint() -> None:
    """A count below the active `limit` is definitive - no capped-count
    hint, and the `docstring=true` next step is still correct (#67)."""
    server = build_server()
    api = PublicAPI(symbols=_api_symbols(1), max_rows=20)
    with mock.patch(f"{MCP}.get_public_api", return_value=api):
        tool = asyncio.run(
            server.get_tool(camel_case("show_package_api_tool"))
        )
        result = tool.fn(name="rich")
    assert "Results capped" not in result
    assert "Re-call with docstring=true" in result


def test_show_package_api_tool_capped_omits_docstring_hint() -> None:
    """A capped listing must not offer `docstring=true` as the way to
    see more symbols - it widens each row without lifting the row
    bound, and it is the exact call the transport token guard refuses
    over a wide package (#67; `specs/commands/show.md`, Outputs)."""
    server = build_server()
    api = PublicAPI(symbols=_api_symbols(2), max_rows=2)
    with mock.patch(f"{MCP}.get_public_api", return_value=api):
        tool = asyncio.run(
            server.get_tool(camel_case("show_package_api_tool"))
        )
        result = tool.fn(name="numpy", limit=2)
    assert "docstring=true" not in result
    assert "Results capped at limit=2" in result


def test_show_package_api_tool_zero_limit_returns_count_zero() -> None:
    """`limit=0` is a bound honoured exactly - `count: 0` with the
    capped-count hint rather than the empty-API module-tree hint
    (`specs/behaviors/output-contract.md`, Bounded collections)."""
    server = build_server()
    api = PublicAPI(symbols=[], max_rows=0)
    with mock.patch(f"{MCP}.get_public_api", return_value=api):
        tool = asyncio.run(
            server.get_tool(camel_case("show_package_api_tool"))
        )
        result = tool.fn(name="numpy", limit=0)
    assert "count: 0" in result
    assert "error: true" not in result
    assert "Results capped at limit=0" in result
    assert "getModuleTreeTool" not in result


def test_show_package_api_tool_negative_limit_returns_error_block() -> None:
    """A negative `limit` returns the domain-error TOON block through
    the shared rejection - one rejection site, so this surface inherits
    it rather than re-implementing it. The message is surface-neutral
    and carries no CLI footer (#67; `specs/mcp/tools.md`, Error message
    wording)."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("show_package_api_tool")))
    result = tool.fn(name="numpy", limit=-5)
    assert "error: true" in result
    assert "must not be negative" in result
    assert "count:" not in result
    assert "Unexpected error" not in result
    # The CLI footer names a shell command this caller cannot run (#60)
    assert "help[" not in result
    assert "venvaxi --help" not in result
    # A shared-path message spells neither surface parameter name
    assert "--limit" not in result
    assert "limit=" not in result


def test_show_module_tool_returns_toon(
    make_symbol_node: NodeFactory,
) -> None:
    """The module tool returns the module header plus a children table."""
    server = build_server()
    node = make_symbol_node(
        qualified_name="rich", kind=NodeKind.PACKAGE, name="rich"
    )
    children = [
        make_symbol_node(qualified_name="rich::Console", name="Console")
    ]
    with mock.patch(f"{MCP}.show_module", return_value=(node, children)):
        tool = asyncio.run(server.get_tool(camel_case("show_module_tool")))
        result = tool.fn(name="rich")
    assert "qualified_name: rich" in result
    assert "children count: 1" in result
    assert "Console|class" in result


def test_show_module_tool_empty_children(
    make_symbol_node: NodeFactory,
) -> None:
    """No children still reports the module header and a zero count."""
    server = build_server()
    node = make_symbol_node(
        qualified_name="rich", kind=NodeKind.PACKAGE, name="rich"
    )
    with mock.patch(f"{MCP}.show_module", return_value=(node, [])):
        tool = asyncio.run(server.get_tool(camel_case("show_module_tool")))
        result = tool.fn(name="rich")
    assert "children count: 0" in result


def test_show_module_tool_docstring_suppresses_footer(
    make_symbol_node: NodeFactory,
) -> None:
    """`docstring=true` returns the bare payload with no `help[]`
    footer, matching `inspect --docstring` on the CLI (#29)."""
    server = build_server()
    node = make_symbol_node(
        qualified_name="rich", kind=NodeKind.PACKAGE, name="rich"
    )
    children = [
        make_symbol_node(qualified_name="rich::Console", name="Console")
    ]
    with mock.patch(f"{MCP}.show_module", return_value=(node, children)):
        tool = asyncio.run(server.get_tool(camel_case("show_module_tool")))
        result = tool.fn(name="rich", docstring=True)
    assert "children count: 1" in result
    assert "help[" not in result


def test_show_module_tool_truncation_names_mcp_escape_hatch(
    make_symbol_node: NodeFactory,
) -> None:
    """A truncated child docstring carries the MCP-spelled size hint,
    never the CLI `--docstring` flag (#30)."""
    server = build_server()
    node = make_symbol_node(
        qualified_name="rich", kind=NodeKind.PACKAGE, name="rich"
    )
    children = [
        make_symbol_node(
            qualified_name="rich::Console", name="Console", doc="x" * 500
        )
    ]
    with mock.patch(f"{MCP}.show_module", return_value=(node, children)):
        tool = asyncio.run(server.get_tool(camel_case("show_module_tool")))
        result = tool.fn(name="rich")
    assert "re-call with docstring=true for the complete body" in result
    assert "--docstring" not in result


def test_get_symbol_tool_returns_toon(make_symbol_node: NodeFactory) -> None:
    """The symbol tool returns a TOON-encoded object."""
    server = build_server()
    node = make_symbol_node(qualified_name="rich::Console", name="Console")
    with mock.patch(f"{MCP}.get_symbol", return_value=node):
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        result = tool.fn(qualified_name="rich::Console")
    assert 'qualified_name: "rich::Console"' in result
    assert "kind: class" in result


def test_get_symbol_tool_resolves_facade_spelled_method(
    fake_package: str,
) -> None:
    """`getSymbolTool` resolves a facade-spelled method through the real
    call path, identically to the CLI - no mock, so parity is the
    resolver's, not the test's."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
    result = tool.fn(qualified_name=f"{fake_package}.api::Client.connect")
    assert f'"{fake_package}._impl::Client.connect"' in result
    assert "kind: method" in result


def test_get_symbol_tool_no_separator_diagnoses_before_lookup() -> None:
    """A no-`::` name returns the malformed-input diagnosis before any
    lookup - the message names `module::Symbol`, the missing `::` and
    `showModuleTool` (previously: a bare `Symbol not found` miss)."""
    server = build_server()
    with mock.patch(f"{MCP}.get_symbol") as mock_get_symbol:
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        result = tool.fn(qualified_name="rich.console")
    mock_get_symbol.assert_not_called()
    assert "error: true" in result
    assert "requires a `module::Symbol` name" in result
    assert "`rich.console` has no `::`" in result
    assert "showModuleTool" in result
    assert "show_module_tool" not in result
    assert "not found" not in result
    assert "help[" not in result


def test_get_symbol_tool_module_resolving_name_still_diagnosed(
    fake_package: str,
) -> None:
    """A no-`::` name that resolves as a real module returns the
    diagnosis through the real call path, never the module's node
    (previously: succeeded by accident with the bare module node)."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
    result = tool.fn(qualified_name=f"{fake_package}.api")
    assert "error: true" in result
    assert "requires a `module::Symbol` name" in result
    assert "kind: module" not in result


def test_find_symbol_tool_returns_toon(
    make_symbol_node: NodeFactory,
) -> None:
    """The find tool returns a TOON-encoded symbol table."""
    server = build_server()
    nodes = [make_symbol_node(qualified_name="rich::Console", name="Console")]
    with mock.patch(f"{MCP}.find_symbol", return_value=nodes):
        tool = asyncio.run(server.get_tool(camel_case("find_symbol_tool")))
        result = tool.fn(query="Console")
    assert "count: 1" in result
    assert 'Console|class|"rich::Console"' in result


def test_find_symbol_tool_at_limit_appends_bounded_hint(
    make_symbol_node: NodeFactory,
) -> None:
    """A count equal to the active `limit` gains the bounded-results
    hint, spelled for this surface - the parameter, not the CLI flag
    (#69)."""
    server = build_server()
    nodes = [
        make_symbol_node(qualified_name=f"rich::Sym{i}", name=f"Sym{i}")
        for i in range(2)
    ]
    with mock.patch(f"{MCP}.find_symbol", return_value=nodes):
        tool = asyncio.run(server.get_tool(camel_case("find_symbol_tool")))
        result = tool.fn(query="Sym", limit=2)
    assert "count: 2" in result
    assert "Results capped at limit=2" in result
    assert "higher limit" in result
    assert "--limit" not in result


def test_find_symbol_tool_below_limit_omits_bounded_hint(
    make_symbol_node: NodeFactory,
) -> None:
    """A count below the active `limit` is definitive - no
    bounded-results hint (#69)."""
    server = build_server()
    nodes = [make_symbol_node(qualified_name="rich::Console", name="Console")]
    with mock.patch(f"{MCP}.find_symbol", return_value=nodes):
        tool = asyncio.run(server.get_tool(camel_case("find_symbol_tool")))
        result = tool.fn(query="Console")
    assert "Results capped" not in result
    assert "getSymbolTool" in result


def test_find_symbol_tool_negative_limit_returns_error_block() -> None:
    """A negative `limit` returns the domain-error TOON block through
    `_toon_errors` - previously the whole graph came back and blew the
    transport's token ceiling, the one failure shape this surface is
    built to avoid. The message is surface-neutral and carries no CLI
    footer (#73)."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("find_symbol_tool")))
    result = tool.fn(query="a", limit=-5)
    assert "error: true" in result
    assert "must not be negative" in result
    assert "count:" not in result
    assert "Unexpected error" not in result
    # The CLI footer names a shell command this caller cannot run (#60)
    assert "help[" not in result
    assert "venvaxi --help" not in result
    # A shared-path message spells neither surface's parameter name
    assert "--limit" not in result


def test_find_symbol_tool_empty_without_package_hints_indexing() -> None:
    """No match without a package hints at re-calling with one, and
    names no package list at all.

    NOTE: The `listPackagesTool` absence pins the branch distinction -
    the package-list hint belongs to the `package`-truthy branch only,
    mirroring `venvaxi list --all` on the CLI (#31).
    """
    server = build_server()
    with mock.patch(f"{MCP}.find_symbol", return_value=[]):
        tool = asyncio.run(server.get_tool(camel_case("find_symbol_tool")))
        result = tool.fn(query="nope")
    assert result.startswith("count: 0")
    assert "Re-call with package=<package>" in result
    assert "listPackagesTool" not in result


def test_find_symbol_tool_empty_with_package_names_list_tool() -> None:
    """No match with a package set hints at the package-list tool, with
    `include_dev=true` for scope parity with the CLI's `venvaxi list
    --all` counterpart (#31)."""
    server = build_server()
    with mock.patch(f"{MCP}.find_symbol", return_value=[]):
        tool = asyncio.run(server.get_tool(camel_case("find_symbol_tool")))
        result = tool.fn(query="nope", package="rich")
    assert result.startswith("count: 0")
    assert "No match in `rich`" in result
    assert "listPackagesTool" in result
    assert "include_dev=true" in result
    assert "list_packages_tool" not in result


def test_get_inheritors_tool_returns_toon(
    make_symbol_node: NodeFactory,
) -> None:
    """The inheritors tool returns a TOON-encoded subclass table."""
    server = build_server()
    nodes = [make_symbol_node(qualified_name="rich::Dog", name="Dog")]
    with mock.patch(f"{MCP}.get_inheritors", return_value=nodes):
        tool = asyncio.run(server.get_tool(camel_case("get_inheritors_tool")))
        result = tool.fn(qualified_name="rich::Animal")
    assert "count: 1" in result
    assert 'Dog|class|"rich::Dog"' in result


def test_get_inheritors_tool_empty_hint_names_both_causes() -> None:
    """No subclasses hints at both an unindexed package and depth."""
    server = build_server()
    with mock.patch(f"{MCP}.get_inheritors", return_value=[]):
        tool = asyncio.run(server.get_tool(camel_case("get_inheritors_tool")))
        result = tool.fn(qualified_name="rich::Animal")
    assert result.startswith("count: 0")
    assert "unindexed packages" in result
    assert "built depth" in result
    assert "findSymbolTool" in result
    assert "find_symbol_tool" not in result


def test_tool_axi_error_returns_toon_error_block() -> None:
    """An `AXIError` inside a tool returns a TOON error block.

    NOTE: Also the arm-ordering regression guard - `Error` derives from
    `Exception`, so a broad arm placed first would report every domain
    error in the `Unexpected error:` shape.
    """
    server = build_server()
    with mock.patch(
        f"{MCP}.get_symbol", side_effect=SymbolNotFoundError("nope")
    ):
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        result = tool.fn(qualified_name="rich::Nope")
    assert "error: true" in result
    assert "nope" in result
    assert "Unexpected error" not in result
    # NOTE: The footer is surface-addressed - an MCP tool error with no
    # error-specific hint carries no `help[N]:` footer at all
    # (previously: the CLI's generic `venvaxi --help` footer).
    assert "help[" not in result
    assert "venvaxi --help" not in result


def test_tool_unexpected_error_returns_toon_error_block() -> None:
    """A non-`Error` exception returns the CLI's `Unexpected error:`
    block instead of escaping into FastMCP (previously: raised)."""
    server = build_server()
    with mock.patch(f"{MCP}.get_symbol", side_effect=ValueError("kaboom")):
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        result = tool.fn(qualified_name="rich::Nope")
    assert "error: true" in result
    assert "Unexpected error: kaboom" in result
    # NOTE: An unexpected error has no next step to name, so over MCP
    # it carries no footer at all (previously: `venvaxi --help`).
    assert "help[" not in result
    assert "venvaxi --help" not in result


def test_tool_base_exception_returns_toon_error_block() -> None:
    """A `BaseException` that is not an `Exception` returns the
    `Unexpected error:` block instead of escaping into the transport
    and dropping the MCP connection (#64)."""

    class Crash(BaseException):
        """A `BaseException` subclass that is not an `Exception`."""

    server = build_server()
    with mock.patch(f"{MCP}.get_symbol", side_effect=Crash("kaboom")):
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        result = tool.fn(qualified_name="rich::Nope")
    assert "error: true" in result
    assert "Unexpected error: kaboom" in result
    assert "help[" not in result


def test_tool_reraises_keyboard_interrupt() -> None:
    """`KeyboardInterrupt` propagates through the tool boundary - a
    long walk must stay abortable over MCP too (#64)."""
    server = build_server()
    with (
        mock.patch(f"{MCP}.get_symbol", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        tool.fn(qualified_name="rich::Nope")


def test_tool_unexpected_error_logs_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The unexpected arm logs the traceback at ERROR, so a genuine bug
    fails loudly in the logs rather than vanishing into the TOON payload."""
    server = build_server()
    with caplog.at_level(logging.ERROR, logger="venvaxi"):
        with mock.patch(f"{MCP}.get_symbol", side_effect=ValueError("kaboom")):
            tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
            tool.fn(qualified_name="rich::Nope")
    records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(records) == 1
    # NOTE: `exc_info` is the point - `logger.exception`, not a plain
    # `logger.error`, so the traceback reaches the logs.
    assert records[0].exc_info is not None
    assert "Traceback" in caplog.text
    assert "ValueError: kaboom" in caplog.text


def test_get_module_tree_tool_malformed_name_returns_toon_error() -> None:
    """`getModuleTreeTool(".foo")` returns a TOON error block through the
    real call path - no mock, so the boundary guard itself answers."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("get_module_tree_tool")))
    result = tool.fn(name=".foo")
    assert "error: true" in result
    assert "Invalid package name `.foo`" in result


def test_get_inheritors_tool_missing_base_returns_toon_error() -> None:
    """A missing base class returns an error block, not `count: 0`."""
    server = build_server()
    error = SymbolNotFoundError("Symbol `x::Nope` not found")
    with mock.patch(f"{MCP}.get_inheritors", side_effect=error):
        tool = asyncio.run(server.get_tool(camel_case("get_inheritors_tool")))
        result = tool.fn(qualified_name="x::Nope")
    assert "error: true" in result
    assert "count: 0" not in result


def test_get_module_tree_tool_returns_toon(
    make_symbol_node: NodeFactory,
) -> None:
    """The tree tool returns a TOON-encoded depth-annotated table."""
    server = build_server()
    pairs = [
        (
            0,
            make_symbol_node(
                qualified_name="rich", kind=NodeKind.PACKAGE, name="rich"
            ),
        ),
        (
            1,
            make_symbol_node(
                qualified_name="rich.table",
                kind=NodeKind.MODULE,
                name="table",
            ),
        ),
    ]
    with mock.patch(f"{MCP}.get_module_tree", return_value=pairs):
        tool = asyncio.run(server.get_tool(camel_case("get_module_tree_tool")))
        result = tool.fn(name="rich")
    assert "count: 2" in result
    assert "1|rich.table|module" in result


def test_get_module_tree_tool_empty_hint_names_root_tree(
    fake_package: str,
) -> None:
    """A missing submodule hints at the root package's own tree.

    NOTE: Driven by a real input, not a mock on `get_module_tree` - the
    branch is reached by a dotted name whose root imports but whose tail
    has no node in the graph. See issue #16.
    """
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case("get_module_tree_tool")))
    result = tool.fn(name=f"{fake_package}.nosuchmodule")
    assert result.startswith("count: 0")
    assert "getModuleTreeTool" in result
    assert f"name={fake_package}" in result
    assert "listPackagesTool" not in result
    assert "get_module_tree_tool" not in result


REFRESH_TOOL = "refresh_package_graph_tool"


def test_refresh_package_graph_tool_returns_receipt_object() -> None:
    """The refresh tool emits the flat `package`/`depth`/`symbols`
    object recording the rebuild it performed."""
    server = build_server()
    receipt = RefreshReceipt(package="mpctraj", depth=2, symbols=143)
    with mock.patch(
        f"{MCP}.refresh_package_graph", return_value=receipt
    ) as refresh:
        tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
        result = tool.fn(name="mpctraj")
    refresh.assert_called_once_with("mpctraj")
    assert "package: mpctraj" in result
    assert "depth: 2" in result
    assert "symbols: 143" in result


def test_refresh_package_graph_tool_reports_resolved_import_name() -> None:
    """The object names the import name the graph is keyed by, not the
    distribution name the caller supplied."""
    server = build_server()
    receipt = RefreshReceipt(package="yaml", depth=2, symbols=42)
    with mock.patch(f"{MCP}.refresh_package_graph", return_value=receipt):
        tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
        result = tool.fn(name="PyYAML")
    assert "package: yaml" in result
    assert "package: PyYAML" not in result


def test_refresh_package_graph_tool_footer_scopes_the_search() -> None:
    """The footer names the search tool by its camelCase name and
    carries the package scope, never a `venvaxi` shell spelling."""
    server = build_server()
    receipt = RefreshReceipt(package="mpctraj", depth=2, symbols=143)
    with mock.patch(f"{MCP}.refresh_package_graph", return_value=receipt):
        tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
        result = tool.fn(name="mpctraj")
    assert "help[1]:" in result
    assert "findSymbolTool" in result
    assert "package=mpctraj" in result
    assert "find_symbol_tool" not in result
    assert "venvaxi " not in result


def test_refresh_package_graph_tool_omits_count_line() -> None:
    """The symbol count is a field of the object, never a leading
    `count:` line promising rows that never arrive."""
    server = build_server()
    receipt = RefreshReceipt(package="mpctraj", depth=2, symbols=143)
    with mock.patch(f"{MCP}.refresh_package_graph", return_value=receipt):
        tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
        result = tool.fn(name="mpctraj")
    assert "count:" not in result
    assert result.startswith("package: mpctraj")


def test_refresh_tool_registered_description_states_the_contract() -> None:
    """The registered description says what it rebuilds, names source
    changed with no reinstall, and marks it a rebuild not a read."""
    server = build_server()
    tool = asyncio.run(server.get_tool("refreshPackageGraphTool"))
    description = tool.description or ""
    assert "symbol graph" in description
    assert "reinstall" in description
    assert "rebuild, not a read" in description


def test_build_server_registers_refresh_tool_under_contract_name() -> None:
    """The refresh tool appears in the registered listing under the
    contracted name `refreshPackageGraphTool`."""
    server = build_server()
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert "refreshPackageGraphTool" in names


def test_registered_read_tools_expose_no_refresh_parameter() -> None:
    """The nine read tools each still take no `refresh` parameter - the
    divergence is narrowed to one named tool, not removed."""
    server = build_server()
    tools = asyncio.run(server.list_tools())
    reads = [tool for tool in tools if tool.name != "refreshPackageGraphTool"]
    assert len(reads) == 9
    for tool in reads:
        assert "refresh" not in tool.parameters["properties"]


def test_refresh_package_graph_tool_takes_only_a_name() -> None:
    """The refresh tool's registered schema carries a required `name`
    and no depth parameter."""
    server = build_server()
    tool = asyncio.run(server.get_tool("refreshPackageGraphTool"))
    assert set(tool.parameters["properties"]) == {"name"}
    assert tool.parameters["required"] == ["name"]


def test_refresh_package_graph_tool_malformed_name_returns_error_block(
    isolated_cache: Path,
) -> None:
    """A name that cannot be a package returns the TOON error block."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
    result = tool.fn(name="a b")
    assert "error: true" in result
    assert "Invalid package name" in result


def test_refresh_package_graph_tool_not_installed_returns_error_block(
    isolated_cache: Path,
) -> None:
    """A package absent from the venv returns the TOON error block."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
    result = tool.fn(name="definitely_not_installed_pkg")
    assert "error: true" in result
    assert "not installed" in result


def test_refresh_package_graph_tool_import_error_returns_error_block(
    isolated_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An installed package raising on import returns the TOON error
    block rather than escaping into FastMCP."""

    def _raise(name: str) -> object:
        msg = f"boom: {name}"
        raise ImportError(msg)

    monkeypatch.setattr("importlib.import_module", _raise)
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
    result = tool.fn(name="rich")
    assert "error: true" in result
    assert "Failed to import `rich`" in result


def test_refresh_package_graph_tool_no_project_root_returns_error_block(
    isolated_cache: Path,
) -> None:
    """No resolvable project root returns the TOON error block - this
    tool raises where `describeBindingTool` degrades to the marker."""
    server = build_server()
    with mock.patch(
        f"{CORE}.get_project_root",
        side_effect=ProjectRootNotFoundError("no root"),
    ):
        tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
        result = tool.fn(name="rich")
    assert "error: true" in result
    assert "no root" in result
    assert NO_PROJECT_ROOT not in result


def test_refresh_package_graph_tool_store_error_returns_error_block() -> None:
    """A SQLite-level failure during the rebuild returns the TOON error
    block."""
    server = build_server()
    with mock.patch(
        f"{MCP}.refresh_package_graph",
        side_effect=StoreError("Failed to build symbol store"),
    ):
        tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
        result = tool.fn(name="rich")
    assert "error: true" in result
    assert "Failed to build symbol store" in result


def test_refresh_package_graph_tool_error_omits_help_footer(
    isolated_cache: Path,
) -> None:
    """An error block carries no `help[N]:` footer - no failure here
    leaves a next step the message has not already given."""
    server = build_server()
    tool = asyncio.run(server.get_tool(camel_case(REFRESH_TOOL)))
    result = tool.fn(name="a b")
    assert "error: true" in result
    assert "help[" not in result
    assert "findSymbolTool" not in result
