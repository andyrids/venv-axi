"""Unit tests for `venvaxi._mcp`."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest

pytest.importorskip("fastmcp")
# ruff: disable[E402]
from venvaxi._introspect import MCP_ESCAPE_HATCH, SymbolInfo
from venvaxi._mcp import build_server
from venvaxi._packages import PackageInfo
from venvaxi._store import NodeKind, SymbolNode
from venvaxi.exceptions import SymbolNotFoundError

# ruff: enable[E402]
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
    """`build_server` registers all eight expected MCP tools."""
    from venvaxi import _mcp

    server = build_server()
    names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert names == {
        camel_case(_mcp.list_packages_tool.__name__),
        camel_case(_mcp.show_package_tool.__name__),
        camel_case(_mcp.show_package_api_tool.__name__),
        camel_case(_mcp.show_module_tool.__name__),
        camel_case(_mcp.get_symbol_tool.__name__),
        camel_case(_mcp.find_symbol_tool.__name__),
        camel_case(_mcp.get_inheritors_tool.__name__),
        camel_case(_mcp.get_module_tree_tool.__name__),
    }


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


def test_show_package_api_tool_returns_toon() -> None:
    """The API tool returns TOON-encoded public symbols."""
    server = build_server()
    symbols = [
        SymbolInfo(name="foo", kind="function", signature="()", doc="Foo."),
    ]
    with mock.patch(f"{MCP}.get_public_api", return_value=symbols):
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
    with mock.patch(f"{MCP}.get_public_api", return_value=symbols):
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
    with mock.patch(f"{MCP}.get_public_api", return_value=[]) as api:
        tool = asyncio.run(
            server.get_tool(camel_case("show_package_api_tool"))
        )
        tool.fn(name="rich")
    api.assert_called_once_with(
        "rich", docstring=False, escape_hatch=MCP_ESCAPE_HATCH
    )


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


def test_tool_unexpected_error_returns_toon_error_block() -> None:
    """A non-`Error` exception returns the CLI's `Unexpected error:`
    block instead of escaping into FastMCP (previously: raised)."""
    server = build_server()
    with mock.patch(f"{MCP}.get_symbol", side_effect=ValueError("kaboom")):
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        result = tool.fn(qualified_name="rich::Nope")
    assert "error: true" in result
    assert "Unexpected error: kaboom" in result


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
