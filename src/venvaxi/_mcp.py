"""Lazy FastMCP server exposing `venvaxi` data as MCP tools."""

import functools
import logging
import re
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from venvaxi._core import get_project_root
from venvaxi._introspect import (
    SYMBOL_INFO_FIELDS,
    find_symbol,
    get_inheritors,
    get_module_tree,
    get_public_api,
    get_symbol,
    show_module,
    summarize_doc,
)
from venvaxi._packages import list_packages, resolve_package
from venvaxi._toon import (
    encode_object,
    encode_table,
    format_error,
    format_help,
)
from venvaxi.exceptions import Error

logger = logging.getLogger(__package__)


def _toon_errors(fn: Callable[..., str]) -> Callable[..., str]:
    """Wrap an MCP tool so `Error`s return a TOON error block.

    NOTE: Mirrors the CLI error contract - without this, `Error`s
    escape into FastMCP's generic error path instead of the same
    `format_error` block the CLI emits on stdout.

    Args:
        fn: The tool function to wrap.

    Returns:
        The wrapped tool function (signature-preserving).
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return fn(*args, **kwargs)
        except Error as err:
            return format_error(str(err))

    return wrapper


def _with_help(output: str, hints: list[str]) -> str:
    """Append a TOON `help[]` footer to a tool's output.

    NOTE: AXI principle 9 (contextual disclosure) applies to the MCP
    surface too - `venvaxi setup` registers the MCP server as the primary
    ambient integration, so an MCP-driven agent must see the same
    next-step hints a CLI-driven one does.

    Args:
        output: The tool's TOON output.
        hints: The next-step hint lines.

    Returns:
        `output` with a `help[]` footer appended.
    """
    return f"{output}\n{format_help(hints)}"


def camel_case(name: str) -> str:
    """Convert a snake_case name to camelCase."""
    import re

    def match_upper(match: re.Match) -> str:
        return match.group(1).upper()

    return re.sub(r"_([a-zA-Z])", match_upper, name)


def list_packages_tool(include_dev: bool = False) -> str:
    """List venv packages for a consuming repo (TOON format)."""
    root = get_project_root()
    packages = list_packages(root, include_dev=include_dev)
    if not packages:
        return _with_help(
            "count: 0", ["Call `list_packages_tool` with include_dev=true"]
        )
    rows = [asdict(package) for package in packages]
    table = encode_table("packages", rows, ["name", "version"])

    cname = camel_case(show_package_tool.__name__)
    return _with_help(
        f"count: {len(packages)}\n{table}",
        [f"Call `{cname}` for a package's public API"],
    )


def show_package_tool(name: str) -> str:
    """Show metadata for a single package (TOON format)."""
    package = resolve_package(name)
    cname = camel_case(show_package_api_tool.__name__)
    return _with_help(
        encode_object(
            {
                "name": package.name,
                "version": package.version,
                "location": package.location,
            }
        ),
        [f"Call `{cname}` with name={package.name}"],
    )


def show_package_api_tool(name: str, docstring: bool = False) -> str:
    """Show public API symbols for a package (TOON format)."""
    symbols = get_public_api(name, docstring=docstring)
    if not symbols:
        cname = camel_case(get_module_tree_tool.__name__)
        return _with_help(
            "count: 0", [f"Call `{cname}` with name={name}"]
        )
    rows = [asdict(symbol) for symbol in symbols]
    table = encode_table("symbols", rows, SYMBOL_INFO_FIELDS)
    cname = camel_case(get_symbol_tool.__name__)
    hint = (
        f"Call `{cname}` for one symbol's full detail"
        if docstring
        else "Re-call with docstring=true for complete docstrings"
    )
    return _with_help(f"count: {len(symbols)}\n{table}", [hint])


def show_module_tool(name: str, docstring: bool = False) -> str:
    """Show a module|package node and its direct children (TOON format)."""
    node, children = show_module(name)
    header = encode_object(
        {
            "qualified_name": node.qualified_name,
            "kind": str(node.kind),
            "doc": summarize_doc(node.doc, docstring=docstring),
        }
    )
    if not children:
        cname = camel_case(get_module_tree_tool.__name__)
        return _with_help(
            f"{header}\nchildren count: 0",
            [f"Call `{cname}` with name={name}"],
        )
    rows = [
        {
            **child.as_row(),
            "doc": summarize_doc(child.doc, docstring=docstring),
        }
        for child in children
    ]
    table = encode_table(
        "children", rows, ["name", "kind", "signature", "doc"]
    )
    cname = camel_case(get_symbol_tool.__name__)
    hint = (
        f"Call `{cname}` for one symbol's full detail"
        if docstring
        else "Re-call with docstring=true for complete docstrings"
    )
    return _with_help(
        f"{header}\nchildren count: {len(children)}\n{table}", [hint]
    )


def get_symbol_tool(qualified_name: str, docstring: bool = False) -> str:
    """Show full detail for a single symbol (TOON format)."""
    node = get_symbol(qualified_name)
    output = encode_object(
        {
            "qualified_name": node.qualified_name,
            "kind": str(node.kind),
            "signature": node.signature,
            "doc": summarize_doc(node.doc, docstring=docstring),
        }
    )
    if docstring:
        return output
    return _with_help(
        output, ["Re-call with docstring=true for the complete docstring"]
    )


def find_symbol_tool(
    query: str, limit: int = 20, package: str | None = None
) -> str:
    """Search cached symbols by name|doc text (TOON format)."""
    nodes = find_symbol(query, limit, package)
    if not nodes:
        cname = camel_case(list_packages_tool.__name__)
        hint = (
            f"No match in `{package}` - call `{cname}`"
            " to check the package name"
            if package
            else "Re-call with package=<package> to index it and search"
        )
        return _with_help("count: 0", [hint])
    rows = [node.as_row() for node in nodes]
    table = encode_table("symbols", rows, ["name", "kind", "qualified_name"])

    cname = camel_case(get_symbol_tool.__name__)
    return _with_help(
        f"count: {len(nodes)}\n{table}",
        [f"Call `{cname}` with a qualified_name for full detail"],
    )


def get_inheritors_tool(qualified_name: str) -> str:
    """Show classes that directly inherit from a class (TOON format)."""
    nodes = get_inheritors(qualified_name)
    if not nodes:
        cname = camel_case(find_symbol_tool.__name__)
        return _with_help(
            "count: 0",
            [f"Call `{cname}` to locate a base class's name"],
        )
    rows = [node.as_row() for node in nodes]
    table = encode_table(
        "inheritors", rows, ["name", "kind", "qualified_name"]
    )
    cname = camel_case(get_symbol_tool.__name__)
    return _with_help(
        f"count: {len(nodes)}\n{table}",
        [f"Call `{cname}` with a qualified_name for full detail"],
    )


def get_module_tree_tool(name: str, max_depth: int = 2) -> str:
    """Show nested module tree for a module|package (TOON format)."""
    pairs = get_module_tree(name, max_depth)
    if not pairs:
        cname = camel_case(show_module_tool.__name__)
        return _with_help(
            "count: 0", [f"Call `{cname}` for the venv package list"]
        )
    rows = [{"depth": depth, **node.as_row()} for depth, node in pairs]
    table = encode_table("tree", rows, ["depth", "qualified_name", "kind"])

    cname = camel_case(show_module_tool.__name__)
    return _with_help(
        f"count: {len(pairs)}\n{table}",
        [f"Call `{cname}` with a module name for its symbols"],
    )


_TOOLS: tuple[Callable[..., str], ...] = (
    list_packages_tool,
    show_package_tool,
    show_package_api_tool,
    show_module_tool,
    get_symbol_tool,
    find_symbol_tool,
    get_inheritors_tool,
    get_module_tree_tool,
)


def build_server() -> Any:
    """Build the `venvaxi` FastMCP server instance.

    Raises:
        ImportError: If `fastmcp` is not installed (requires the
            `venv-axi[mcp]` extra).

    Returns:
        A configured `FastMCP` server exposing package listing,
        metadata, symbol-graph and public-API tools.
    """
    from fastmcp import FastMCP

    server = FastMCP("VenvAXI")
    for fn in _TOOLS:
        # get_module_tree_tool -> getModuleTreeTool etc. (camelCase)
        server.tool(_toon_errors(fn), name=camel_case(fn.__name__))
    return server


def serve() -> None:
    """Start the `VenvAXI` MCP server over stdio."""
    build_server().run()
