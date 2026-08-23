"""Lazy FastMCP server exposing `venvaxi` data as MCP tools."""

import functools
import logging
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from venvaxi import _core
from venvaxi._cache import get_cache_db_path, read_cache_state
from venvaxi._constants import NO_PROJECT_ROOT
from venvaxi._core import format_path, get_project_root, resolve_binding
from venvaxi._introspect import (
    DEFAULT_API_ROW_LIMIT,
    MCP_ESCAPE_HATCH,
    SYMBOL_INFO_FIELDS,
    find_symbol,
    get_inheritors,
    get_module_tree,
    get_public_api,
    get_symbol,
    refresh_package_graph,
    show_module,
    summarize_doc,
)
from venvaxi._packages import installed_count, list_packages, resolve_package
from venvaxi._toon import (
    encode_object,
    encode_table,
    format_error,
    format_help,
)
from venvaxi.exceptions import (
    Error,
    InvalidArgumentError,
    ProjectRootNotFoundError,
    StoreError,
)

logger = logging.getLogger(__package__)


def _toon_errors(fn: Callable[..., str]) -> Callable[..., str]:
    """Wrap an MCP tool so no exception escapes into FastMCP.

    NOTE: Mirrors the CLI catch discipline - `Error`s return the TOON
    error object, and anything else returns the `Unexpected error:`
    shape. Both arms pass no hints, so no tool error carries the CLI's
    generic footer - the footer is surface-addressed, and this surface
    has no generic next step to name (`specs/mcp/tools.md`). Without
    the broad arm, a non-`Error` exception escapes into FastMCP's
    generic error path.

    Args:
        fn: The tool function to wrap.

    Returns:
        The wrapped tool function (signature-preserving).
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return fn(*args, **kwargs)
        # NOTE: Ordering is load-bearing - `Error` derives from
        # `Exception`, so the broad arm placed first would swallow
        # every domain error into the unexpected shape.
        except Error as err:
            return format_error(str(err))
        except (KeyboardInterrupt, SystemExit):
            # NOTE: Mirrors `__main__.main` - neither is a tool answer,
            # and import boundaries keep third-party `SystemExit` from
            # ever reaching this arm.
            raise
        except BaseException as err:
            # NOTE: `BaseException`, broad on purpose, mirroring
            # `__main__.main` - an escaping `BaseException` does not
            # merely fail the call, it drops the whole MCP connection
            # (#64). The traceback is logged at ERROR so a genuine bug
            # still fails loudly in the logs rather than vanishing
            # into TOON.
            logger.exception("Unexpected error")
            return format_error(f"Unexpected error: {err}")

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

    def match_upper(match: re.Match[str]) -> str:
        return str(match.group(1)).upper()

    return re.sub(r"_([a-zA-Z])", match_upper, name)


def describe_binding_tool() -> str:
    """Identify the project and venv this server answers from.

    Call this first: every other tool returns results about a binding
    it never names, so a server bound to the wrong project or venv
    returns plausible answers with no warning. Reports the resolved
    project `root`, the serving `venv` and the venv `status`. When
    `root` resolves, the report also includes a summary of the cached
    symbol graph - schema version, on-disk size, and which packages
    are indexed at which built version and depth - so a
    suspected-stale graph can be confirmed or ruled out without
    paying for a rebuild.
    """
    # NOTE: The docstring above is the registered MCP description -
    # FastMCP reads `__doc__` - and `specs/mcp/tools.md` makes it part
    # of the contract: it must state what the tool identifies, that it
    # is the tool to call first, and that the report includes a cache
    # summary. Functional text, not commentary.
    #
    # NOTE: `root` is resolved directly here (via `_core.get_project_root`,
    # module-qualified so it stays mockable through `venvaxi._core`),
    # rather than through `resolve_binding()` - that helper formats
    # `root` for display before returning it, and the cache summary
    # below needs the unformatted `Path`, resolved once and reused, not
    # re-derived by parsing the formatted string back apart.
    root_path: Path | None
    try:
        resolved_root = _core.get_project_root()
        root_path = resolved_root
        root = format_path(resolved_root)
    # NOTE: `ProjectRootNotFoundError` exactly, never a broad arm - a
    # failure to *find* a root is the fact the marker states, while any
    # other exception must keep propagating to `_toon_errors` as the
    # `Unexpected error:` block (`specs/mcp/tools.md`, Failure modes).
    except ProjectRootNotFoundError:
        root_path = None
        root = NO_PROJECT_ROOT
    venv = format_path(Path(sys.prefix).resolve())
    status = "active" if sys.prefix != sys.base_prefix else "inactive"
    fields: dict[str, Any] = {"root": root, "venv": venv, "status": status}

    if root_path is None:
        # NOTE: The degraded hint names the registration, not an
        # invocation - an MCP caller cannot change the server's working
        # directory, and naming a file to inspect is not a shell
        # spelling (`specs/mcp/tools.md`, Hint wording). Without a
        # resolved root there is no project to key a cache to, so the
        # cache summary is omitted entirely rather than marked.
        return _with_help(
            encode_object(fields),
            [
                (
                    "This server is bound to no project - check the"
                    " `VenvAXI` entry in the consuming repository's"
                    " `.mcp.json` and re-register from inside that"
                    " project"
                )
            ],
        )

    list_name = camel_case(list_packages_tool.__name__)
    find_name = camel_case(find_symbol_tool.__name__)
    hints = [
        (
            f"Call `{list_name}` with include_dev=true for the"
            " declared dependencies"
        ),
        f"Call `{find_name}` with a query to search the symbol graph",
    ]

    try:
        state = read_cache_state(root_path)
    except StoreError:
        # NOTE: The cache half degrades rather than raises here, per
        # the maintainer's decision at review - `root`/`venv`/`status`
        # cost no cache I/O and stay knowable regardless of the
        # cache's health. `StoreError` carries no payload, so
        # `db_path`/`db_size_bytes` are recomputed directly rather
        # than threaded through the exception
        # (`specs/mcp/tools.md`, Failure modes).
        db_path = get_cache_db_path(root_path)
        fields["schema_version"] = "(cache unreadable)"
        fields["db_path"] = format_path(db_path)
        fields["db_size_bytes"] = db_path.stat().st_size
        hints.append(
            f"Delete `{format_path(db_path)}` - it is disposable"
            " derived data, and the next command that touches the"
            " cache creates a fresh one"
        )
        return _with_help(encode_object(fields), hints)

    fields["schema_version"] = (
        "(not built)" if state.schema_version is None else state.schema_version
    )
    fields["db_path"] = format_path(state.db_path)
    fields["db_size_bytes"] = state.db_size_bytes
    output = encode_object(fields)

    if state.builds:
        rows = [asdict(build) for build in state.builds]
        table = encode_table(
            "builds", rows, ["package", "version", "depth", "symbols"]
        )
        output = f"{output}\ncount: {len(state.builds)}\n{table}"
        refresh_name = camel_case(refresh_package_graph_tool.__name__)
        hints.append(
            f"Call `{refresh_name}` with the name of a package whose"
            " recorded build looks stale"
        )
    else:
        # NOTE: A real, empty cache - `count: 0` is a positive claim
        # the database opened cleanly, distinct from `StoreError`'s
        # `(cache unreadable)` marker above
        # (`specs/mcp/tools.md`, Cache summary).
        output = f"{output}\ncount: 0"

    return _with_help(output, hints)


def list_packages_tool(include_dev: bool = False) -> str:
    """List venv packages for a consuming repo (TOON format)."""
    root = get_project_root()
    packages = list_packages(root, include_dev=include_dev)
    declared = len(packages)
    # NOTE: `installed` is a second, pre-computed aggregate alongside
    # `count:` - independent of `include_dev` and matching
    # `command_list` field for field (`specs/commands/list.md`,
    # Installed-package visibility; `specs/mcp/tools.md`, parity).
    installed = installed_count()
    if not packages:
        # NOTE: An empty `include_dev=true` answer is definitive - the
        # hint names the file that would have to change rather than the
        # parameter just used, mirroring the CLI's `list --all` branch
        # (`specs/behaviors/output-contract.md`, Contextual disclosure).
        cname = camel_case(list_packages_tool.__name__)
        hint = (
            "Edit `pyproject.toml` to declare dependencies"
            if include_dev
            else f"Call `{cname}` with include_dev=true"
        )
        output = "count: 0"
        # NOTE: Suppressed when declared equals installed (0 == 0) -
        # never emitted as zero, never emitted with a marker.
        if installed != declared:
            output = f"{output}\ninstalled: {installed}"
        return _with_help(output, [hint])
    rows = [asdict(package) for package in packages]
    table = encode_table("packages", rows, ["name", "version"])
    output = f"count: {declared}\n{table}"
    if installed != declared:
        output = f"{output}\ninstalled: {installed}"

    cname = camel_case(show_package_tool.__name__)
    return _with_help(
        output,
        [f"Call `{cname}` for package metadata"],
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


def show_package_api_tool(
    name: str,
    docstring: bool = False,
    limit: int = DEFAULT_API_ROW_LIMIT,
) -> str:
    """Show public API symbols for a package (TOON format)."""
    result = get_public_api(
        name,
        docstring=docstring,
        max_rows=limit,
        escape_hatch=MCP_ESCAPE_HATCH,
    )
    symbols = result.symbols
    # NOTE: Mirrors the CLI capped-count hint in the spelling of this
    # surface - the parameter, not the flag (`specs/mcp/tools.md`, Hint
    # wording).
    capped_hint = (
        f"Results capped at limit={limit}"
        " - re-call with a higher limit to see more"
    )
    if not symbols:
        # NOTE: An empty listing under a bound of `0` is capped, not
        # empty - the module tree is not the next step for it
        # (`specs/behaviors/output-contract.md`, Bounded collections).
        cname = camel_case(get_module_tree_tool.__name__)
        hint = (
            capped_hint
            if result.capped
            else f"Call `{cname}` with name={name}"
        )
        return _with_help("count: 0", [hint])
    rows = [asdict(symbol) for symbol in symbols]
    table = encode_table("symbols", rows, SYMBOL_INFO_FIELDS)
    output = f"count: {len(symbols)}\n{table}"
    hints: list[str] = []
    if result.capped:
        # NOTE: `docstring=true` is deliberately not offered on a
        # capped result - it widens each row without lifting the row
        # bound, and it is the exact call this surface refuses over a
        # large package (#67; `specs/commands/show.md`, Outputs).
        hints.append(capped_hint)
    elif not docstring:
        hints.append("Re-call with docstring=true for complete docstrings")
    if not hints:
        return output
    return _with_help(output, hints)


def show_module_tool(name: str, docstring: bool = False) -> str:
    """Show a module|package node and its direct children (TOON format)."""
    node, children = show_module(name)
    header = encode_object(
        {
            "qualified_name": node.qualified_name,
            "kind": str(node.kind),
            "doc": summarize_doc(
                node.doc, docstring=docstring, escape_hatch=MCP_ESCAPE_HATCH
            ),
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
            "doc": summarize_doc(
                child.doc, docstring=docstring, escape_hatch=MCP_ESCAPE_HATCH
            ),
        }
        for child in children
    ]
    table = encode_table(
        "children", rows, ["name", "kind", "signature", "doc"]
    )
    output = f"{header}\nchildren count: {len(children)}\n{table}"
    if docstring:
        return output
    return _with_help(
        output, ["Re-call with docstring=true for complete docstrings"]
    )


def get_symbol_tool(qualified_name: str, docstring: bool = False) -> str:
    """Show full detail for a single symbol (TOON format)."""
    # NOTE: Diagnosed before any lookup (`specs/mcp/tools.md`, Malformed
    # qualified names) - a no-`::` name that would resolve as a module
    # must get the diagnosis, not the module's node. Tool names are
    # derived, per the Hint wording rule.
    if "::" not in qualified_name:
        gname = camel_case(get_symbol_tool.__name__)
        sname = camel_case(show_module_tool.__name__)
        msg = (
            f"`{gname}` requires a `module::Symbol` name;"
            f" `{qualified_name}` has no `::` - call `{sname}` for a"
            " module, or re-spell with `::`"
        )
        raise InvalidArgumentError(msg)
    node = get_symbol(qualified_name)
    output = encode_object(
        {
            "qualified_name": node.qualified_name,
            "kind": str(node.kind),
            "signature": node.signature,
            "doc": summarize_doc(
                node.doc, docstring=docstring, escape_hatch=MCP_ESCAPE_HATCH
            ),
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
        # NOTE: Scope equivalence (`specs/mcp/tools.md`, Hint wording) -
        # the CLI counterpart names `venvaxi list --all`, so the mirrored
        # hint carries `include_dev=true` or it sends the caller to a
        # narrower package list for the same recovery.
        cname = camel_case(list_packages_tool.__name__)
        hint = (
            f"No match in `{package}` - call `{cname}` with"
            " include_dev=true to check the package name"
            if package
            else "Re-call with package=<package> to index it and search"
        )
        return _with_help("count: 0", [hint])
    rows = [node.as_row() for node in nodes]
    table = encode_table("symbols", rows, ["name", "kind", "qualified_name"])

    cname = camel_case(get_symbol_tool.__name__)
    hints = [f"Call `{cname}` with a qualified_name for full detail"]
    if len(nodes) == limit:
        # NOTE: Mirrors the CLI's bounded-results hint in the spelling
        # of this surface - the parameter, not the flag (#69;
        # `specs/commands/find.md`, Bounded results).
        hints.append(
            f"Results capped at limit={limit}"
            " - re-call with a higher limit to see more"
        )
    return _with_help(f"count: {len(nodes)}\n{table}", hints)


def get_inheritors_tool(qualified_name: str) -> str:
    """Show classes that directly inherit from a class (TOON format)."""
    nodes = get_inheritors(qualified_name)
    if not nodes:
        cname = camel_case(find_symbol_tool.__name__)
        return _with_help(
            "count: 0",
            [
                (
                    "Subclasses may live in unindexed packages or below"
                    f" the built depth - call `{cname}` with"
                    " package=<package> to index one"
                )
            ],
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
        # NOTE: Reached only by a dotted name whose tail has no graph
        # node - a bad *package* raises upstream, so the root's own tree
        # is the hint that shows what exists. See `specs/commands/tree.md`.
        root = name.split(".", 1)[0]
        cname = camel_case(get_module_tree_tool.__name__)
        return _with_help(
            "count: 0",
            [
                (
                    f"Call `{cname}` with name={root} for the"
                    " submodules that exist"
                )
            ],
        )
    rows = [{"depth": depth, **node.as_row()} for depth, node in pairs]
    table = encode_table("tree", rows, ["depth", "qualified_name", "kind"])

    cname = camel_case(show_module_tool.__name__)
    return _with_help(
        f"count: {len(pairs)}\n{table}",
        [f"Call `{cname}` with a module name for its symbols"],
    )


def refresh_package_graph_tool(name: str) -> str:
    """Rebuild one package's cached symbol graph (TOON format).

    This is a rebuild, not a read: it re-imports and re-walks the
    package's modules, so it is not a cheap precondition to put in
    front of every lookup. Call it when a package's source changed
    with no reinstall - an editable or local install edited in place -
    because the installed version does not move, nothing else on this
    surface detects it, and every read tool keeps answering from the
    graph as last built. Reports the resolved package name, the build
    depth recorded and the number of symbol nodes recorded.
    """
    # NOTE: The docstring above is the registered MCP description -
    # FastMCP reads `__doc__` - and `specs/mcp/tools.md` makes it part
    # of the contract: it must state what it rebuilds, name the
    # source-changed-with-no-reinstall situation, and mark it a rebuild
    # rather than a read. Functional text, not commentary.
    receipt = refresh_package_graph(name)
    # NOTE: `symbols` is a field of the object, never a leading
    # `count:` line - `count:` fronts a collection and none follows
    # (`specs/behaviors/output-contract.md`, Aggregates).
    output = encode_object(
        {
            "package": receipt.package,
            "depth": receipt.depth,
            "symbols": receipt.symbols,
        }
    )
    # NOTE: Scope equivalence (`specs/mcp/tools.md`, Hint wording) -
    # the hint carries `package=` or it sends the caller to a search
    # across every indexed package for a recovery that is about one.
    cname = camel_case(find_symbol_tool.__name__)
    return _with_help(
        output,
        [
            (
                f"Call `{cname}` with a query and"
                f" package={receipt.package} to search the rebuilt"
                " graph"
            )
        ],
    )


_TOOLS: tuple[Callable[..., str], ...] = (
    describe_binding_tool,
    list_packages_tool,
    show_package_tool,
    show_package_api_tool,
    show_module_tool,
    get_symbol_tool,
    find_symbol_tool,
    get_inheritors_tool,
    get_module_tree_tool,
    refresh_package_graph_tool,
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

    # NOTE: Computed once, at startup - nothing in the server changes
    # its working directory afterwards, so the instructions stay equal
    # to what `describe_binding_tool` resolves per call. Going through
    # `resolve_binding` means the unresolvable-root case degrades to
    # the same `(no project root)` marker instead of raising, so the
    # server starts anyway (`specs/commands/serve.md`, Failure modes).
    root, venv, status = resolve_binding()
    binding = encode_object({"root": root, "venv": venv, "status": status})
    cname = camel_case(describe_binding_tool.__name__)
    instructions = (
        "This server answers from the binding below - a wrong `root` or"
        " `venv` means every tool answers about the wrong project.\n"
        f"{binding}\n"
        f"Call `{cname}` to re-check the binding at any time."
    )
    server = FastMCP("VenvAXI", instructions=instructions)
    for fn in _TOOLS:
        # get_module_tree_tool -> getModuleTreeTool etc. (camelCase)
        server.tool(_toon_errors(fn), name=camel_case(fn.__name__))
    return server


def serve() -> None:
    """Start the `VenvAXI` MCP server over stdio."""
    build_server().run()
