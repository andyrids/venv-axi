"""Argparse CLI for `venvaxi`."""

import argparse
import logging
import sys
from dataclasses import asdict
from enum import StrEnum
from pathlib import Path
from typing import Any

from venvaxi._ambient import mcp_available, setup_ambient_context
from venvaxi._cache import read_cache_state
from venvaxi._core import (
    CLIContext,
    ExitCode,
    format_path,
    get_project_root,
)
from venvaxi._introspect import (
    DEFAULT_API_ROW_LIMIT,
    SYMBOL_INFO_FIELDS,
    find_symbol,
    get_inheritors,
    get_module_tree,
    get_public_api,
    get_symbol,
    show_module,
    summarize_doc,
)
from venvaxi._packages import (
    PACKAGE_INFO_FIELDS,
    list_packages,
    resolve_package,
)
from venvaxi._toon import encode_object, encode_table, format_help
from venvaxi.exceptions import InvalidArgumentError

logger = logging.getLogger(__package__)


def _emit(text: str) -> None:
    """Write a line of structured output to STDOUT.

    NOTE: Uses `sys.stdout.write` (instead of `print`) so structural
    TOON output is never subject to Rich console line-wrapping.

    Args:
        text: The text to write, without a trailing newline.
    """
    sys.stdout.write(f"{text}\n")


def _parse_fields(raw: str) -> list[str]:
    """Parse and validate a comma-separated `--fields` argument value.

    Args:
        raw: The raw `--fields` value, e.g. `"name,version"`.

    Raises:
        InvalidArgumentError: On any field not in `PACKAGE_INFO_FIELDS`.

    Returns:
        The parsed field names.
    """
    fields = [field.strip() for field in raw.split(",") if field.strip()]
    invalid = [field for field in fields if field not in PACKAGE_INFO_FIELDS]
    if invalid:
        msg = (
            f"Invalid field(s): {', '.join(invalid)}"
            f" - valid fields: {', '.join(PACKAGE_INFO_FIELDS)}"
        )
        raise InvalidArgumentError(msg)
    return fields


def _add_refresh_argument(parser: "argparse.ArgumentParser") -> None:
    """Register the shared `--refresh` flag on a subcommand parser.

    Args:
        parser: The subcommand parser to extend.
    """
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Rebuild the cached symbol graph before querying",
    )


def command_home(_: CLIContext) -> int:
    """Print live status and next-step hints (the content-first home view).

    Args:
        _: The CLI context.

    Returns:
        The process exit code.
    """
    bin_path = Path(sys.argv[0]).resolve()
    venv_path = Path(sys.prefix).resolve()
    active = sys.prefix != sys.base_prefix

    fields = {
        "description": "Fetch dependency API info from a project's venv",
        "bin": format_path(bin_path),
        "venv": format_path(venv_path),
        "status": "active" if active else "inactive",
    }
    _emit(encode_object(fields))
    _emit(
        format_help(
            [
                "Run `venvaxi list` for the venv package list",
                "Run `venvaxi show <package>` for metadata information",
                "Run `venvaxi show <package> --api` for public API symbols",
                (
                    "Run `venvaxi find <query> --package <package>` to"
                    " resolve a bare symbol name"
                ),
                "Run `venvaxi tree <package>` for a nested module tree",
                "Run `venvaxi inspect <qualified_name>` for symbol detail",
                "Run `venvaxi inherits <qualified_name>` for subclasses",
                "Run `venvaxi cache` for this project's cache state",
                "Run `venvaxi serve` to start the MCP server over stdio",
                "Run `venvaxi setup` to install ambient context",
            ]
        )
    )
    return ExitCode.EX_OK


def command_list(ctx: CLIContext) -> int:
    """List the consuming repo's declared, installed venv packages.

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    root = get_project_root()
    packages = list_packages(root, include_dev=ctx.args.all)
    fields = _parse_fields(ctx.args.fields)

    if not packages:
        # NOTE: An empty `list --all` is definitive - no broader query
        # exists, so the hint names the file that would have to change
        # rather than the flag just used (`specs/commands/list.md`).
        help_txt = (
            "Edit `pyproject.toml` to declare dependencies"
            if ctx.args.all
            else "Run `venvaxi list --all` to include all dependencies"
        )

        _emit("count: 0")
        _emit(format_help([help_txt]))
        return ExitCode.EX_OK

    rows = [asdict(package) for package in packages]

    _emit(f"count: {len(packages)}")
    _emit(encode_table("packages", rows, fields))
    _emit(format_help(["Run `venvaxi show <package>` for package info"]))
    return ExitCode.EX_OK


def _command_show_api(ctx: CLIContext) -> int:
    """Show public, top-level API symbols for a package.

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    result = get_public_api(
        ctx.args.package,
        docstring=ctx.args.docstring,
        max_rows=ctx.args.limit,
        refresh=ctx.args.refresh,
    )
    symbols = result.symbols
    # NOTE: Spelled here rather than in `get_public_api` - a hint names
    # a next action, and a next action exists on one surface at a time,
    # so a single spelling reaching both would teach one of them an
    # invocation it cannot make (`specs/mcp/tools.md`, Hint wording).
    capped_hint = (
        f"Results capped at --limit {ctx.args.limit}"
        " - re-run with a higher --limit to see more"
    )
    if not symbols:
        # NOTE: An empty listing under a bound of `0` is capped, not
        # empty - the package's surface is unknown rather than absent,
        # so `tree` is not the next step
        # (`specs/behaviors/output-contract.md`, Bounded collections).
        _emit("count: 0")
        _emit(
            format_help(
                [
                    capped_hint
                    if result.capped
                    else (
                        f"Run `venvaxi tree {ctx.args.package}`"
                        " for the nested module tree"
                    )
                ]
            )
        )
        return ExitCode.EX_OK

    rows = [asdict(symbol) for symbol in symbols]
    _emit(f"count: {len(symbols)}")
    _emit(encode_table("symbols", rows, SYMBOL_INFO_FIELDS))

    hints: list[str] = []
    if result.capped:
        # NOTE: A count equal to the bound means 'at least', not
        # 'exactly'. `--docstring` is deliberately not offered here: it
        # widens each row rather than lifting the row bound, and over
        # MCP it is the exact call the token-limit guard refuses (#67;
        # `specs/commands/show.md`, Outputs).
        hints.append(capped_hint)
    elif not ctx.args.docstring:
        hints.append(
            f"Run `venvaxi show {ctx.args.package} "
            "--api --docstring` for complete docstrings"
        )
    if hints:
        _emit(format_help(hints))
    return ExitCode.EX_OK


def _command_show_metadata(ctx: CLIContext) -> int:
    """Show a package's installed metadata.

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    fields = _parse_fields(ctx.args.fields)
    package = resolve_package(ctx.args.package)
    data = asdict(package)
    selected = {field: data[field] for field in fields}

    _emit(encode_object(selected))
    _emit(
        format_help(
            [f"Run `venvaxi show {ctx.args.package} --api` for public API"]
        )
    )
    return ExitCode.EX_OK


def command_show(ctx: CLIContext) -> int:
    """Show a package's metadata or public API (dispatches on `--api`).

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    if ctx.args.api:
        return _command_show_api(ctx)
    return _command_show_metadata(ctx)


def command_find(ctx: CLIContext) -> int:
    """Search cached symbols by name/doc text.

    NOTE: `--package` indexes that package if needed and scopes the
    search to it, so a symbol found by scanning the codebase resolves
    to its qualified name without a separate `show --api`/`tree`
    warm-up step.

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    package = ctx.args.package
    nodes = find_symbol(
        ctx.args.query, ctx.args.limit, package, refresh=ctx.args.refresh
    )
    if not nodes:
        _emit("count: 0")
        _emit(
            format_help(
                [
                    (
                        f"No match in `{package}`"
                        " - run `venvaxi list --all` to check the"
                        " package name"
                    )
                    if package
                    else (
                        "Run `venvaxi find <query> --package <package>`"
                        " to index a package and search it"
                    )
                ]
            )
        )
        return ExitCode.EX_OK

    rows = [node.as_row() for node in nodes]
    _emit(f"count: {len(nodes)}")
    _emit(encode_table("symbols", rows, ["name", "kind", "qualified_name"]))
    hints = ["Run `venvaxi inspect <qualified_name>` for complete metadata"]
    if len(nodes) == ctx.args.limit:
        # NOTE: A count equal to the cap means 'at least', not 'exactly'
        # - without the hint a truncated answer reads as definitive
        # (#69; `specs/commands/find.md`, Bounded results).
        hints.append(
            f"Results capped at --limit {ctx.args.limit}"
            " - re-run with a higher --limit to see more"
        )
    _emit(format_help(hints))
    return ExitCode.EX_OK


class TreeField(StrEnum):
    """The fields for the `axi tree` tabular output."""

    DEPTH = "depth"
    QUALIFIED_NAME = "qualified_name"
    KIND = "kind"


def command_tree(ctx: CLIContext) -> int:
    """Show a package's nested module tree.

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    pairs = get_module_tree(
        ctx.args.package, ctx.args.max_depth, refresh=ctx.args.refresh
    )
    if not pairs:
        # NOTE: Reached only by a dotted name whose tail has no graph
        # node (nonexistent, private or failed-import submodule) - a bad
        # *package* raises upstream, so the root's own tree is the hint
        # that shows what exists. See `specs/commands/tree.md`.
        root = ctx.args.package.split(".", 1)[0]
        _emit("count: 0")
        _emit(
            format_help(
                [f"Run `venvaxi tree {root}` for the submodules that exist"]
            )
        )
        return ExitCode.EX_OK

    rows = [{"depth": depth, **node.as_row()} for depth, node in pairs]
    _emit(f"count: {len(pairs)}")
    _emit(encode_table("tree", rows, [item.value for item in TreeField]))
    _emit(
        format_help(["Run `venvaxi inspect <module>` for a module's symbols"])
    )
    return ExitCode.EX_OK


def command_inherits(ctx: CLIContext) -> int:
    """Show classes that directly inherit from a base class.

    NOTE: AXI principle 5 (definitive empty states) - an unresolvable
    name raises `SymbolNotFoundError` upstream, so `count: 0` always
    means the base resolved with zero *indexed* subclasses.

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    nodes = get_inheritors(ctx.args.qualified_name, refresh=ctx.args.refresh)
    if not nodes:
        _emit("count: 0")
        _emit(
            format_help(
                [
                    (
                        "Subclasses may live in unindexed packages or"
                        " below the built depth - run `venvaxi find"
                        " <name> --package <package>` to index one"
                    )
                ]
            )
        )
        return ExitCode.EX_OK

    rows = [node.as_row() for node in nodes]
    _emit(f"count: {len(nodes)}")
    _emit(encode_table("inheritors", rows, ["name", "kind", "qualified_name"]))
    _emit(
        format_help(
            ["Run `venvaxi inspect <qualified_name>` for complete metadata"]
        )
    )
    return ExitCode.EX_OK


def _command_inspect_module(ctx: CLIContext) -> int:
    """Show a module/package node and its direct children.

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    docstring = ctx.args.docstring
    node, children = show_module(
        ctx.args.qualified_name, refresh=ctx.args.refresh
    )
    _emit(
        encode_object(
            {
                "qualified_name": node.qualified_name,
                "kind": str(node.kind),
                "doc": summarize_doc(node.doc, docstring=docstring),
            }
        )
    )
    if not children:
        _emit("children count: 0")
        _emit(
            format_help(
                [
                    (
                        f"Run `venvaxi tree {ctx.args.qualified_name}`"
                        " for the nested module tree"
                    )
                ]
            )
        )
        return ExitCode.EX_OK

    rows = [
        {
            **child.as_row(),
            "doc": summarize_doc(child.doc, docstring=docstring),
        }
        for child in children
    ]
    _emit(f"children count: {len(children)}")
    _emit(encode_table("children", rows, ["name", "kind", "signature", "doc"]))
    if not docstring:
        _emit(
            format_help(
                [
                    (
                        f"Run `venvaxi inspect {ctx.args.qualified_name}"
                        " --docstring` for complete docstrings"
                    )
                ]
            )
        )
    return ExitCode.EX_OK


def command_inspect(ctx: CLIContext) -> int:
    """Show complete information for a symbol or module name.

    NOTE: Qualified symbol names always contain `::`; bare or dotted
    module names never do - dispatch on the argument shape.

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    if "::" not in ctx.args.qualified_name:
        return _command_inspect_module(ctx)

    node = get_symbol(ctx.args.qualified_name, refresh=ctx.args.refresh)
    _emit(
        encode_object(
            {
                "qualified_name": node.qualified_name,
                "kind": str(node.kind),
                "signature": node.signature,
                "doc": summarize_doc(node.doc, docstring=ctx.args.docstring),
            }
        )
    )
    if not ctx.args.docstring:
        _emit(
            format_help(
                [
                    (
                        f"Run `venvaxi inspect {ctx.args.qualified_name}"
                        " --docstring` for the complete docstring"
                    )
                ]
            )
        )
    return ExitCode.EX_OK


def command_cache(ctx: CLIContext) -> int:
    """Show this project's cache state without changing it.

    NOTE: `read_cache_state` opens SQLite read-only, directly on the
    cache database, so a stale recorded schema version is reported as
    a fact, never corrected by the act of asking about it
    (`specs/commands/cache.md`, Local principle).

    Args:
        ctx: The CLI context.

    Returns:
        The process exit code.
    """
    root = get_project_root()
    state = read_cache_state(root)

    fields = {
        "schema_version": (
            "(not built)"
            if state.schema_version is None
            else state.schema_version
        ),
        "db_path": format_path(state.db_path),
        "db_size_bytes": state.db_size_bytes,
    }
    _emit(encode_object(fields))

    if not state.builds:
        # NOTE: Two situations both report no builds - never built, and
        # built but empty - kept apart by `schema_version` alone; both
        # carry the identical next step (`specs/commands/cache.md`).
        _emit("count: 0")
        _emit(
            format_help(
                [
                    (
                        "Run `venvaxi show <package> --api` to index a"
                        " package into this project's cache"
                    )
                ]
            )
        )
        return ExitCode.EX_OK

    rows = [asdict(build) for build in state.builds]
    _emit(f"count: {len(state.builds)}")
    _emit(
        encode_table(
            "builds", rows, ["package", "version", "depth", "symbols"]
        )
    )
    _emit(
        format_help(
            [
                (
                    "Run `venvaxi show <package> --api --refresh` to"
                    " rebuild a package whose recorded build looks stale"
                )
            ]
        )
    )
    return ExitCode.EX_OK


def command_serve(_: CLIContext) -> int:
    """Serve a dedicated AXI MCP server over STDIO.

    NOTE: Availability is checked up front so a genuine `ImportError`
    raised mid-serve propagates as an unexpected error instead of being
    misreported as a missing extra.

    Args:
        _: The CLI context.

    Returns:
        The process exit code.
    """
    if not mcp_available():
        logger.error("`venvaxi serve` requires the `venv-axi[mcp]` extra")
        return ExitCode.EX_FAILURE

    from venvaxi import _mcp

    _mcp.serve()
    return ExitCode.EX_OK


def command_setup(context: CLIContext) -> int:
    """Install `venvaxi` ambient context into the consuming repo.

    Args:
        context: The CLI context.

    Returns:
        The process exit code.
    """
    root = get_project_root()
    changed = setup_ambient_context(root, skill=context.args.skill)

    _emit(encode_object(changed))
    hints = ["Run `venvaxi` to confirm ambient context is live"]
    if not mcp_available():
        hints.append("Run `uv add venv-axi[mcp]` to enable the MCP server")
    _emit(format_help(hints))
    return ExitCode.EX_OK


def add_subparser(subparsers: "argparse._SubParsersAction[Any]") -> None:
    """Register every `venvaxi` command on the top-level CLI parser.

    Args:
        subparsers: The parent parser's subparsers action.
    """

    # `list` command
    parser_list = subparsers.add_parser(
        "list", help="Show installed venv packages"
    )

    parser_list.add_argument(
        "--all",
        action="store_true",
        help="Include dev|optional dependency groups",
    )
    parser_list.add_argument(
        "--fields",
        default="name,version",
        help="Comma-separated fields to display",
    )
    parser_list.set_defaults(func=command_list)

    # `show` command
    parser_show = subparsers.add_parser(
        "show", help="Show package metadata|API information"
    )
    parser_show.add_argument(
        "package",
        help=(
            "Package (distribution) name for metadata; any importable"
            " dotted module path with --api"
        ),
    )
    parser_show.add_argument(
        "--fields",
        default="name,version,location",
        help="Comma-separated display fields",
    )
    parser_show.add_argument(
        "--api",
        action="store_true",
        help="Show public API symbols instead of metadata",
    )
    parser_show.add_argument(
        "--docstring",
        action="store_true",
        help="Show complete docstrings (with --api)",
    )
    parser_show.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_API_ROW_LIMIT,
        help="Maximum number of symbol rows (with --api)",
    )
    _add_refresh_argument(parser_show)
    parser_show.set_defaults(func=command_show)

    # `find` command
    parser_find = subparsers.add_parser(
        "find",
        help="Search cached symbols by name|docstring text",
    )
    parser_find.add_argument(
        "query",
        help="Free-text search query",
    )
    parser_find.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of results",
    )
    parser_find.add_argument(
        "--package",
        default=None,
        help="Package to index and scope the search to",
    )
    _add_refresh_argument(parser_find)
    parser_find.set_defaults(func=command_find)

    # `tree` command
    parser_tree = subparsers.add_parser(
        "tree", help="Show nested module tree for a package"
    )
    parser_tree.add_argument("package", help="Package or dotted module name")
    parser_tree.add_argument(
        "--max-depth",
        type=int,
        default=2,
        dest="max_depth",
        help="Maximum submodule recursion depth",
    )
    _add_refresh_argument(parser_tree)
    parser_tree.set_defaults(func=command_tree)

    # `inspect` command
    parser_inspect = subparsers.add_parser(
        "inspect",
        help="Show complete details for a qualified symbol|module name",
    )
    parser_inspect.add_argument(
        "qualified_name",
        help=(
            "Qualified symbol name (module::Symbol |"
            " module::Class.method) or a bare|dotted module name"
        ),
    )
    parser_inspect.add_argument(
        "--docstring",
        action="store_true",
        help="Show complete docstrings instead of truncated first lines",
    )
    _add_refresh_argument(parser_inspect)
    parser_inspect.set_defaults(func=command_inspect)

    # `inherits` command
    parser_inherits = subparsers.add_parser(
        "inherits",
        help="Show classes that directly inherit from a base class",
    )
    parser_inherits.add_argument(
        "qualified_name",
        help="Qualified base class name (module::Class)",
    )
    _add_refresh_argument(parser_inherits)
    parser_inherits.set_defaults(func=command_inherits)

    # `cache` command
    parser_cache = subparsers.add_parser(
        "cache", help="Show this project's cache state"
    )
    parser_cache.set_defaults(func=command_cache)

    # `serve` command
    parser_serve = subparsers.add_parser(
        "serve",
        help="Run a dedicated AXI MCP server (requires venv-axi[mcp])",
    )
    parser_serve.set_defaults(func=command_serve)

    # `setup` command
    parser_setup = subparsers.add_parser(
        "setup",
        help=" ".join(
            [
                "Install AXI ambient context into the repo",
                "(MCP config & skill)",
            ]
        ),
    )
    parser_setup.add_argument(
        "--skill",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=" ".join(
            [
                "Install the venvaxi Claude Code Skill",
                "(.claude/skills/venvaxi/SKILL.md) - overwrites any",
                "existing copy",
            ]
        ),
    )
    parser_setup.set_defaults(func=command_setup)
