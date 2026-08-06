"""Unit tests for `venvaxi._mcp`."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest

pytest.importorskip("fastmcp")
# ruff: disable[E402]
from venvaxi._introspect import SymbolInfo
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


def test_get_symbol_tool_returns_toon(make_symbol_node: NodeFactory) -> None:
    """The symbol tool returns a TOON-encoded object."""
    server = build_server()
    node = make_symbol_node(qualified_name="rich::Console", name="Console")
    with mock.patch(f"{MCP}.get_symbol", return_value=node):
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        result = tool.fn(qualified_name="rich::Console")
    assert 'qualified_name: "rich::Console"' in result
    assert "kind: class" in result


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


def test_find_symbol_tool_empty() -> None:
    """No matches reports a zero count."""
    server = build_server()
    with mock.patch(f"{MCP}.find_symbol", return_value=[]):
        tool = asyncio.run(server.get_tool(camel_case("find_symbol_tool")))
        result = tool.fn(query="nope")
    assert result.startswith("count: 0")
    assert "help[1]:" in result


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


def test_tool_axi_error_returns_toon_error_block() -> None:
    """An `AXIError` inside a tool returns a TOON error block."""
    server = build_server()
    with mock.patch(
        f"{MCP}.get_symbol", side_effect=SymbolNotFoundError("nope")
    ):
        tool = asyncio.run(server.get_tool(camel_case("get_symbol_tool")))
        result = tool.fn(qualified_name="rich::Nope")
    assert "error: true" in result
    assert "nope" in result


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
