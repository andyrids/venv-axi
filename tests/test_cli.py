"""Unit tests for `venvaxi._cli`."""

import argparse
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest

from venvaxi import __main__, _cli, exceptions
from venvaxi._core import CLIContext, ExitCode
from venvaxi._introspect import (
    SYMBOL_INFO_FIELDS,
    PublicAPI,
    SymbolInfo,
)
from venvaxi._packages import PackageInfo
from venvaxi._store import NodeKind, SymbolNode

CLI = "venvaxi._cli"

ContextFactory = Callable[..., CLIContext]
NodeFactory = Callable[..., SymbolNode]
PackageFactory = Callable[..., PackageInfo]


def _make_axi_parser() -> argparse.ArgumentParser:
    """Build a parser mirroring `__main__.main`'s command surface."""
    parser = argparse.ArgumentParser(prog="venvaxi")
    parser.set_defaults(func=_cli.command_home)
    subparsers = parser.add_subparsers(title="commands", dest="command")
    _cli.add_subparser(subparsers)
    return parser


def test_add_subparser_defaults_to_home() -> None:
    """A bare `venvaxi` invocation dispatches to `command_home`."""
    parser = _make_axi_parser()
    args = parser.parse_args([])
    assert args.func is _cli.command_home


def test_add_subparser_list_defaults() -> None:
    """The `list` subcommand has the documented default flags."""
    parser = _make_axi_parser()
    args = parser.parse_args(["list"])
    assert args.func is _cli.command_list
    assert args.all is False
    assert args.fields == "name,version"


def test_add_subparser_show_requires_package() -> None:
    """The `show` subcommand requires a positional package name."""
    parser = _make_axi_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["show"])


def test_add_subparser_show_defaults() -> None:
    """The `show` subcommand has the documented default flags - the
    `--limit` default mirrors the `find` spelling, so one number covers
    both collection commands (#67; `specs/commands/show.md`)."""
    parser = _make_axi_parser()
    args = parser.parse_args(["show", "rich"])
    assert args.func is _cli.command_show
    assert args.api is False
    assert args.docstring is False
    assert args.limit == 20


def test_add_subparser_find_defaults() -> None:
    """The `find` subcommand has the documented default flags."""
    parser = _make_axi_parser()
    args = parser.parse_args(["find", "Console"])
    assert args.func is _cli.command_find
    assert args.query == "Console"
    assert args.limit == 20


def test_add_subparser_tree_defaults() -> None:
    """The `tree` subcommand has the documented default flags."""
    parser = _make_axi_parser()
    args = parser.parse_args(["tree", "rich"])
    assert args.func is _cli.command_tree
    assert args.package == "rich"
    assert args.max_depth == 2


def test_add_subparser_inspect_requires_qualified_name() -> None:
    """The `inspect` subcommand requires a positional qualified name."""
    parser = _make_axi_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["inspect"])
    args = parser.parse_args(["inspect", "rich::Console"])
    assert args.func is _cli.command_inspect
    assert args.qualified_name == "rich::Console"


def test_command_home_prints_status(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """The home view prints description, bin, venv and status fields."""
    exit_code = _cli.command_home(make_cli_context())
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "description:" in out
    assert "bin:" in out
    assert "status:" in out
    assert "help[9]:" in out


def test_command_home_status_active_when_prefixes_differ(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """Status is `active` when `sys.prefix != sys.base_prefix`."""
    with (
        mock.patch(f"{CLI}.sys.prefix", "/repo/.venv"),
        mock.patch(f"{CLI}.sys.base_prefix", "/usr"),
    ):
        _cli.command_home(make_cli_context())
    out = capsys.readouterr().out
    assert "status: active" in out


def test_command_home_status_inactive_when_prefixes_match(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """Status is `inactive` when `sys.prefix == sys.base_prefix`."""
    with (
        mock.patch(f"{CLI}.sys.prefix", "/usr"),
        mock.patch(f"{CLI}.sys.base_prefix", "/usr"),
    ):
        _cli.command_home(make_cli_context())
    out = capsys.readouterr().out
    assert "status: inactive" in out


def test_command_list_empty(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
) -> None:
    """A repo with no resolvable dependencies prints the empty state."""
    ctx = make_cli_context(
        args=argparse.Namespace(all=False, fields="name,version")
    )
    with (
        mock.patch(f"{CLI}.get_project_root", return_value=tmp_path),
        mock.patch(f"{CLI}.list_packages", return_value=[]),
    ):
        exit_code = _cli.command_list(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 0" in out


def test_command_list_empty_hint_names_all(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
) -> None:
    """Without `--all`, the empty-state hint names the flag most likely
    to produce results (`specs/commands/list.md`)."""
    ctx = make_cli_context(
        args=argparse.Namespace(all=False, fields="name,version")
    )
    with (
        mock.patch(f"{CLI}.get_project_root", return_value=tmp_path),
        mock.patch(f"{CLI}.list_packages", return_value=[]),
    ):
        exit_code = _cli.command_list(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 0" in out
    assert "venvaxi list --all" in out


def test_command_list_empty_all_hint_names_pyproject(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
) -> None:
    """With `--all`, the empty state is definitive - the hint names
    `pyproject.toml`, never the flag the caller just passed (the
    suppression rule in `specs/behaviors/output-contract.md`)."""
    ctx = make_cli_context(
        args=argparse.Namespace(all=True, fields="name,version")
    )
    with (
        mock.patch(f"{CLI}.get_project_root", return_value=tmp_path),
        mock.patch(f"{CLI}.list_packages", return_value=[]),
    ):
        exit_code = _cli.command_list(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 0" in out
    assert "pyproject.toml" in out
    assert "--all" not in out


def test_command_list_with_packages(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_package_info: PackageFactory,
) -> None:
    """Resolved packages are printed as a TOON table."""
    packages = [make_package_info()]
    ctx = make_cli_context(
        args=argparse.Namespace(all=False, fields="name,version")
    )
    with (
        mock.patch(f"{CLI}.get_project_root", return_value=tmp_path),
        mock.patch(f"{CLI}.list_packages", return_value=packages),
    ):
        exit_code = _cli.command_list(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 1" in out
    assert "rich|15.0.0" in out


def test_command_list_invalid_fields_raises(
    tmp_path: Path,
    make_cli_context: ContextFactory,
    make_package_info: PackageFactory,
) -> None:
    """An unknown `--fields` name raises `InvalidArgumentError`."""
    ctx = make_cli_context(
        args=argparse.Namespace(all=False, fields="name,bogus")
    )
    with (
        mock.patch(f"{CLI}.get_project_root", return_value=tmp_path),
        mock.patch(f"{CLI}.list_packages", return_value=[make_package_info()]),
        pytest.raises(exceptions.InvalidArgumentError, match="bogus"),
    ):
        _cli.command_list(ctx)


def test_command_show_metadata(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_package_info: PackageFactory,
) -> None:
    """Package metadata is printed for a plain `show` invocation."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="rich", fields="name,version", api=False, full=False
        )
    )
    with mock.patch(
        f"{CLI}.resolve_package", return_value=make_package_info()
    ):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "name: rich" in out
    assert "version: 15.0.0" in out


def test_command_show_metadata_invalid_fields_raises(
    make_cli_context: ContextFactory,
) -> None:
    """An unknown `--fields` name raises `InvalidArgumentError`
    (previously: the bad field was silently dropped)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="rich", fields="summary,bogus", api=False, full=False
        )
    )
    with pytest.raises(exceptions.InvalidArgumentError, match="bogus"):
        _cli.command_show(ctx)


def test_command_show_api(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """Public API symbols are printed when `--api` is passed."""
    symbols = [
        SymbolInfo(name="foo", kind="function", signature="()", doc="Foo."),
    ]
    ctx = make_cli_context(
        args=argparse.Namespace(package="rich", api=True, docstring=False)
    )
    api = PublicAPI(symbols=symbols, max_rows=20)
    with mock.patch(f"{CLI}.get_public_api", return_value=api):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 1" in out
    assert "foo|function" in out


def test_command_show_api_header_matches_symbol_info_fields(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """The `--api` TOON table header tracks `SymbolInfo` field order."""
    symbols = [
        SymbolInfo(name="foo", kind="function", signature="()", doc="Foo."),
    ]
    ctx = make_cli_context(
        args=argparse.Namespace(package="rich", api=True, docstring=False)
    )
    api = PublicAPI(symbols=symbols, max_rows=20)
    with mock.patch(f"{CLI}.get_public_api", return_value=api):
        _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert f"{{{'|'.join(SYMBOL_INFO_FIELDS)}}}" in out


def test_command_show_api_empty(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """A package with no public symbols prints the empty state."""
    ctx = make_cli_context(
        args=argparse.Namespace(package="rich", api=True, docstring=False)
    )
    empty = PublicAPI(symbols=[], max_rows=20)
    with mock.patch(f"{CLI}.get_public_api", return_value=empty):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 0" in out
    assert "help[1]:" in out


def test_command_show_api_docstring_suppresses_footer(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """`show --api --docstring` emits no `help[]` footer - the CLI
    baseline the MCP suppression assertions are pinned against (#29).

    NOTE: Characterization of behaviour `hint-surface-parity` does not
    change.
    """
    symbols = [
        SymbolInfo(name="foo", kind="function", signature="()", doc="Foo."),
    ]
    ctx = make_cli_context(
        args=argparse.Namespace(package="rich", api=True, docstring=True)
    )
    api = PublicAPI(symbols=symbols, max_rows=20)
    with mock.patch(f"{CLI}.get_public_api", return_value=api):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 1" in out
    assert "help[" not in out


def test_command_show_api_forwards_limit_as_row_bound(
    make_cli_context: ContextFactory,
) -> None:
    """`--limit` reaches `get_public_api` as the *row* bound, never as
    the character truncation `limit` the same function already carries
    (#67; `specs/commands/show.md`)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="rich", api=True, docstring=False, limit=5
        )
    )
    empty = PublicAPI(symbols=[], max_rows=5)
    with mock.patch(f"{CLI}.get_public_api", return_value=empty) as api:
        _cli.command_show(ctx)
    api.assert_called_once_with(
        "rich", docstring=False, max_rows=5, refresh=False
    )


def _api_symbols(count: int) -> list[SymbolInfo]:
    """Build `count` distinct `--api` rows."""
    return [
        SymbolInfo(
            name=f"sym_{index}", kind="function", signature="()", doc="Doc."
        )
        for index in range(count)
    ]


def test_command_show_api_at_limit_appends_capped_hint(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """A count equal to the active `--limit` gains the capped-count
    hint - the count means "at least", and without the hint a capped
    listing reads as the package whole public API (#67)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="numpy", api=True, docstring=False, limit=2
        )
    )
    api = PublicAPI(symbols=_api_symbols(2), max_rows=2)
    with mock.patch(f"{CLI}.get_public_api", return_value=api):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 2" in out
    assert "Results capped at --limit 2" in out
    assert "higher --limit" in out


def test_command_show_api_below_limit_omits_capped_hint(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """A count below the active `--limit` is definitive - no
    capped-count hint (#67)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="rich", api=True, docstring=False, limit=20
        )
    )
    api = PublicAPI(symbols=_api_symbols(1), max_rows=20)
    with mock.patch(f"{CLI}.get_public_api", return_value=api):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Results capped" not in out


def test_command_show_api_capped_omits_docstring_suggestion(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """A capped listing must not offer `--docstring` as the way to see
    more symbols - it widens each row without lifting the row bound,
    and over MCP it is the exact call that fails. That footer pointing
    at a megabyte payload is the defect #67 exists to remove
    (`specs/commands/show.md`, Outputs)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="numpy", api=True, docstring=False, limit=2
        )
    )
    api = PublicAPI(symbols=_api_symbols(2), max_rows=2)
    with mock.patch(f"{CLI}.get_public_api", return_value=api):
        _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert "for complete docstrings" not in out
    assert "Results capped at --limit 2" in out


def test_command_show_api_below_limit_keeps_docstring_suggestion(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """The `--docstring` suggestion stays correct where the count is
    not capped and `--docstring` is unset - the correction is scoped to
    the capped case, not a removal (`specs/commands/show.md`)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="rich", api=True, docstring=False, limit=20
        )
    )
    api = PublicAPI(symbols=_api_symbols(1), max_rows=20)
    with mock.patch(f"{CLI}.get_public_api", return_value=api):
        _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert "Run `venvaxi show rich --api --docstring`" in out


def test_command_show_api_zero_limit_prints_empty_state(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """`--limit 0` is a bound honoured exactly - `count: 0` at exit 0,
    with the capped-count hint rather than the empty-API `tree` hint:
    the surface is unknown here, not absent
    (`specs/behaviors/output-contract.md`, Bounded collections)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="numpy", api=True, docstring=False, limit=0
        )
    )
    api = PublicAPI(symbols=[], max_rows=0)
    with mock.patch(f"{CLI}.get_public_api", return_value=api):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_OK
    assert "count: 0" in out
    assert "error: true" not in out
    assert "Results capped at --limit 0" in out
    assert "venvaxi tree" not in out


def test_command_show_metadata_ignores_limit(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_package_info: PackageFactory,
) -> None:
    """`--limit` is the argument of API mode; under metadata mode it is
    silently ignored rather than rejected, the treatment `--fields`
    already gets under `--api` (`specs/commands/show.md`)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            package="rich", fields="name,version", api=False, limit=-5
        )
    )
    with mock.patch(
        f"{CLI}.resolve_package", return_value=make_package_info()
    ):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_OK
    assert "name: rich" in out
    assert "error: true" not in out


def test_command_inspect_docstring_suppresses_footer(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """`inspect --docstring` emits no `help[]` footer - the CLI baseline
    the MCP suppression assertions are pinned against (#29).

    NOTE: Characterization of behaviour `hint-surface-parity` does not
    change.
    """
    node = make_symbol_node(qualified_name="rich::Console", name="Console")
    ctx = make_cli_context(
        args=argparse.Namespace(qualified_name="rich::Console", docstring=True)
    )
    with mock.patch(f"{CLI}.get_symbol", return_value=node):
        exit_code = _cli.command_inspect(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert 'qualified_name: "rich::Console"' in out
    assert "help[" not in out


def test_command_serve_reports_missing_extra(
    make_cli_context: ContextFactory,
) -> None:
    """A missing `fastmcp` extra is reported without touching `_mcp`."""
    with (
        mock.patch(f"{CLI}.mcp_available", return_value=False),
        mock.patch("venvaxi._mcp.serve") as serve,
    ):
        exit_code = _cli.command_serve(make_cli_context())
    assert exit_code == 1
    serve.assert_not_called()


def test_command_serve_runs_server_when_available(
    make_cli_context: ContextFactory,
) -> None:
    """An installed `fastmcp` extra starts the MCP server."""
    with (
        mock.patch(f"{CLI}.mcp_available", return_value=True),
        mock.patch("venvaxi._mcp.serve") as serve,
    ):
        exit_code = _cli.command_serve(make_cli_context())
    assert exit_code == 0
    serve.assert_called_once_with()


def test_command_serve_propagates_runtime_import_error(
    make_cli_context: ContextFactory,
) -> None:
    """An `ImportError` raised mid-serve propagates unhandled
    (previously: misreported as a missing `venv-axi[mcp]` extra)."""
    with (
        mock.patch(f"{CLI}.mcp_available", return_value=True),
        mock.patch("venvaxi._mcp.serve", side_effect=ImportError("boom")),
        pytest.raises(ImportError, match="boom"),
    ):
        _cli.command_serve(make_cli_context())


def test_command_find_with_results(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """Search matches are printed as a TOON table with a help footer."""
    nodes = [make_symbol_node(qualified_name="rich::Console", name="Console")]
    ctx = make_cli_context(args=argparse.Namespace(query="Console", limit=20))
    with mock.patch(f"{CLI}.find_symbol", return_value=nodes):
        exit_code = _cli.command_find(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 1" in out
    assert "Console|class" in out
    assert "help[1]:" in out


def test_command_find_at_limit_appends_bounded_hint(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """A count equal to the active `--limit` gains the bounded-results
    hint - the answer may be truncated and must say so (#69)."""
    nodes = [
        make_symbol_node(qualified_name=f"rich::Sym{i}", name=f"Sym{i}")
        for i in range(2)
    ]
    ctx = make_cli_context(args=argparse.Namespace(query="Sym", limit=2))
    with mock.patch(f"{CLI}.find_symbol", return_value=nodes):
        exit_code = _cli.command_find(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 2" in out
    assert "Results capped at --limit 2" in out
    assert "higher --limit" in out


def test_command_find_below_limit_omits_bounded_hint(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """A count below the active `--limit` is definitive - no
    bounded-results hint (#69)."""
    nodes = [make_symbol_node(qualified_name="rich::Console", name="Console")]
    ctx = make_cli_context(args=argparse.Namespace(query="Console", limit=20))
    with mock.patch(f"{CLI}.find_symbol", return_value=nodes):
        exit_code = _cli.command_find(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Results capped" not in out
    assert "venvaxi inspect <qualified_name>" in out


def test_command_find_empty(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """No matches prints the empty state."""
    ctx = make_cli_context(args=argparse.Namespace(query="nope", limit=20))
    with mock.patch(f"{CLI}.find_symbol", return_value=[]):
        exit_code = _cli.command_find(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 0" in out
    assert "help[1]:" in out


def test_command_tree_with_results(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """The module tree is printed as a depth-annotated TOON table."""
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
    ctx = make_cli_context(
        args=argparse.Namespace(package="rich", max_depth=2)
    )
    with mock.patch(f"{CLI}.get_module_tree", return_value=pairs):
        exit_code = _cli.command_tree(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 2" in out
    assert "1|rich.table|module" in out


def test_command_tree_completes_over_broken_submodules(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    fake_package: str,
) -> None:
    """`tree` exits 0 with the remaining modules when submodules raise
    at import time - including `BaseException` raisers, which
    previously crashed the command (#64)."""
    ctx = make_cli_context(
        args=argparse.Namespace(package=fake_package, max_depth=2)
    )
    exit_code = _cli.command_tree(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "base_error" not in out
    assert "exit_error" not in out
    assert "subpkg" in out


@pytest.mark.parametrize("submodule", ["nosuchmodule", "_impl"])
def test_command_tree_empty_hint_names_root_tree(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    fake_package: str,
    submodule: str,
) -> None:
    """A dotted name with no graph node hints at the root's own tree.

    NOTE: Driven by a real input, not a mock on `get_module_tree` - the
    branch is reached by a dotted name whose root imports but whose tail
    has no node (nonexistent or private submodule). See issue #16.
    """
    ctx = make_cli_context(
        args=argparse.Namespace(
            package=f"{fake_package}.{submodule}", max_depth=2
        )
    )
    exit_code = _cli.command_tree(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 0" in out
    assert f"Run `venvaxi tree {fake_package}`" in out
    assert "venvaxi list" not in out


def test_command_inspect_prints_symbol_detail(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """A single symbol's full detail is printed as a TOON object."""
    node = make_symbol_node(qualified_name="rich::Console", name="Console")
    ctx = make_cli_context(
        args=argparse.Namespace(qualified_name="rich::Console")
    )
    with mock.patch(f"{CLI}.get_symbol", return_value=node):
        exit_code = _cli.command_inspect(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert 'qualified_name: "rich::Console"' in out
    assert "kind: class" in out


def test_command_inspect_module_prints_header_and_children(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """A bare module name prints the module header & children table."""
    node = make_symbol_node(
        qualified_name="rich.console",
        kind=NodeKind.MODULE,
        name="console",
        doc="Console module.",
    )
    children = [
        make_symbol_node(
            qualified_name="rich.console::Console", name="Console"
        )
    ]
    ctx = make_cli_context(
        args=argparse.Namespace(qualified_name="rich.console")
    )
    with mock.patch(f"{CLI}.show_module", return_value=(node, children)):
        exit_code = _cli.command_inspect(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "qualified_name: rich.console" in out
    assert "kind: module" in out
    assert "children count: 1" in out
    assert "Console|class" in out


def test_command_inspect_module_empty_children(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """A module with no children prints the empty state & help footer."""
    node = make_symbol_node(
        qualified_name="rich.console", kind=NodeKind.MODULE, name="console"
    )
    ctx = make_cli_context(
        args=argparse.Namespace(qualified_name="rich.console")
    )
    with mock.patch(f"{CLI}.show_module", return_value=(node, [])):
        exit_code = _cli.command_inspect(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "children count: 0" in out
    assert "help[1]:" in out


def test_command_inspect_propagates_not_found(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """A missing symbol propagates `SymbolNotFoundError`."""
    ctx = make_cli_context(
        args=argparse.Namespace(qualified_name="rich::Nope")
    )
    with (
        mock.patch(
            f"{CLI}.get_symbol",
            side_effect=exceptions.SymbolNotFoundError("not found"),
        ),
        pytest.raises(exceptions.SymbolNotFoundError),
    ):
        _cli.command_inspect(ctx)


def test_add_subparser_inherits_requires_qualified_name() -> None:
    """The `inherits` subcommand requires a positional name."""
    parser = _make_axi_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["inherits"])
    args = parser.parse_args(["inherits", "rich::Console"])
    assert args.func is _cli.command_inherits
    assert args.qualified_name == "rich::Console"


def test_command_inherits_with_results(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """Inheritors are printed as a TOON table with a help footer."""
    nodes = [make_symbol_node(qualified_name="pkg::Derived", name="Derived")]
    ctx = make_cli_context(args=argparse.Namespace(qualified_name="pkg::Base"))
    with mock.patch(f"{CLI}.get_inheritors", return_value=nodes):
        exit_code = _cli.command_inherits(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 1" in out
    assert "Derived|class" in out
    assert "help[1]:" in out


def test_command_inherits_empty(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
) -> None:
    """No inheritors prints the empty state & help footer."""
    ctx = make_cli_context(args=argparse.Namespace(qualified_name="pkg::Base"))
    with mock.patch(f"{CLI}.get_inheritors", return_value=[]):
        exit_code = _cli.command_inherits(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 0" in out
    assert "help[1]:" in out


def test_command_inherits_empty_hint_suggests_indexing(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
) -> None:
    """The empty-state hint explains zero *indexed* subclasses and
    suggests indexing another package via `find --package`."""
    ctx = make_cli_context(args=argparse.Namespace(qualified_name="pkg::Base"))
    with mock.patch(f"{CLI}.get_inheritors", return_value=[]):
        _cli.command_inherits(ctx)
    out = capsys.readouterr().out
    assert "unindexed packages" in out
    assert "--package" in out


def test_command_inherits_propagates_not_found(
    make_cli_context: ContextFactory,
) -> None:
    """A missing base class propagates `SymbolNotFoundError`."""
    ctx = make_cli_context(
        args=argparse.Namespace(qualified_name="pkg::NoSuchClass")
    )
    with (
        mock.patch(
            f"{CLI}.get_inheritors",
            side_effect=exceptions.SymbolNotFoundError("not found"),
        ),
        pytest.raises(exceptions.SymbolNotFoundError),
    ):
        _cli.command_inherits(ctx)


def test_add_subparser_inherits_has_refresh() -> None:
    """The `inherits` subcommand accepts the `--refresh` flag."""
    parser = _make_axi_parser()
    args = parser.parse_args(["inherits", "x", "--refresh"])
    assert args.refresh is True


def test_command_inherits_passes_refresh_without_probe(
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
    make_symbol_node: NodeFactory,
) -> None:
    """`--refresh` reaches `get_inheritors` and the discarded
    `get_symbol` probe is gone (a single store cycle)."""
    nodes = [make_symbol_node(qualified_name="pkg::Derived", name="Derived")]
    ctx = make_cli_context(
        args=argparse.Namespace(qualified_name="pkg::Base", refresh=True)
    )
    with (
        mock.patch(f"{CLI}.get_inheritors", return_value=nodes) as inheritors,
        mock.patch(f"{CLI}.get_symbol") as symbol,
    ):
        exit_code = _cli.command_inherits(ctx)
    assert exit_code == 0
    inheritors.assert_called_once_with("pkg::Base", refresh=True)
    symbol.assert_not_called()


def test_command_find_passes_refresh(
    make_cli_context: ContextFactory,
) -> None:
    """`--refresh` and `--package` are forwarded to `find_symbol`."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            query="Console", limit=20, package="rich", refresh=True
        )
    )
    with mock.patch(f"{CLI}.find_symbol", return_value=[]) as find:
        _cli.command_find(ctx)
    find.assert_called_once_with("Console", 20, "rich", refresh=True)


def test_command_setup(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
) -> None:
    """The setup command reports which artifacts changed."""
    # NOTE: Keys mirror `_ambient.setup_ambient_context`'s real return
    # value - a mocked shape that the implementation never emits would
    # let a rename of those keys pass unnoticed.
    changed = {
        "AGENTS.md": True,
        ".vscode": False,
        ".mcp.json": False,
        "SKILL.md": False,
    }
    ctx = make_cli_context(args=argparse.Namespace(skill=False))
    with (
        mock.patch(f"{CLI}.get_project_root", return_value=tmp_path),
        mock.patch(
            f"{CLI}.setup_ambient_context", return_value=changed
        ) as setup,
        mock.patch(f"{CLI}.mcp_available", return_value=True),
    ):
        exit_code = _cli.command_setup(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "AGENTS.md: true" in out
    assert '".mcp.json": false' in out
    assert "SKILL.md: false" in out
    assert "venv-axi[mcp]" not in out
    setup.assert_called_once_with(tmp_path, skill=False)


def test_command_setup_installs_skill(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
) -> None:
    """`--skill` is forwarded and the skill status is reported."""
    changed = {
        "AGENTS.md": True,
        ".vscode": False,
        ".mcp.json": False,
        "SKILL.md": True,
    }
    ctx = make_cli_context(args=argparse.Namespace(skill=True))
    with (
        mock.patch(f"{CLI}.get_project_root", return_value=tmp_path),
        mock.patch(
            f"{CLI}.setup_ambient_context", return_value=changed
        ) as setup,
        mock.patch(f"{CLI}.mcp_available", return_value=True),
    ):
        exit_code = _cli.command_setup(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "SKILL.md: true" in out
    setup.assert_called_once_with(tmp_path, skill=True)


def test_command_setup_hints_missing_extra(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
    make_cli_context: ContextFactory,
) -> None:
    """A missing `fastmcp` extra surfaces an install hint in `help[]`."""
    changed = {
        "AGENTS.md": True,
        ".vscode": False,
        ".mcp.json": False,
        "SKILL.md": False,
    }
    ctx = make_cli_context(args=argparse.Namespace(skill=False))
    with (
        mock.patch(f"{CLI}.get_project_root", return_value=tmp_path),
        mock.patch(f"{CLI}.setup_ambient_context", return_value=changed),
        mock.patch(f"{CLI}.mcp_available", return_value=False),
    ):
        exit_code = _cli.command_setup(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "help[2]:" in out
    assert "uv add venv-axi[mcp]" in out


def _run_main(argv: list[str]) -> int:
    """Run `venvaxi.__main__.main` with `argv` & return the exit code."""
    with (
        mock.patch("sys.argv", ["venvaxi", *argv]),
        mock.patch("venvaxi.__main__.configure_cli_logging"),
        pytest.raises(SystemExit) as exc_info,
    ):
        __main__.main()
    return int(exc_info.value.code)


def test_main_maps_error_to_toon_and_exit_1(
    capsys: pytest.CaptureFixture,
) -> None:
    """An `Error` emits a TOON error block & maps to exit code 1."""
    error = exceptions.PackageNotFoundError("boom")
    with mock.patch(f"{CLI}.command_list", side_effect=error):
        exit_code = _run_main(["list"])
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_FAILURE
    assert "error: true" in out
    assert "boom" in out
    # NOTE: The CLI keeps its generic footer unchanged - the footer is
    # surface-addressed, and this is the CLI surface.
    assert "help[1]:" in out
    assert "Run `venvaxi --help` for available commands" in out


def test_main_show_malformed_name_maps_to_exit_1(
    capsys: pytest.CaptureFixture,
) -> None:
    """`show` with a malformed package name reports
    `InvalidArgumentError` and exits 1 - never exit 2, which is
    reserved for venvaxi being broken (#65)."""
    exit_code = _run_main(["show", ""])
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_FAILURE
    assert "error: true" in out
    assert "Invalid package name" in out


def test_main_find_negative_limit_maps_to_exit_1(
    capsys: pytest.CaptureFixture,
) -> None:
    """`find` with a negative `--limit` reports `InvalidArgumentError`
    and exits 1 (previously: exit 0 with the whole symbol graph, the
    cap defeated by the value meant to set it) (#73)."""
    exit_code = _run_main(["find", "a", "--limit", "-5"])
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_FAILURE
    assert "error: true" in out
    assert "must not be negative" in out
    assert "count:" not in out
    # NOTE: The CLI keeps its generic footer - surface-addressed (#60).
    assert "Run `venvaxi --help` for available commands" in out


def test_main_show_api_negative_limit_maps_to_exit_1(
    capsys: pytest.CaptureFixture,
) -> None:
    """`show --api` with a negative `--limit` reports
    `InvalidArgumentError` and exits 1, and the message names neither
    surface spelling because it is raised on the shared path (#67;
    `specs/mcp/tools.md`, Error message wording)."""
    exit_code = _run_main(["show", "rich", "--api", "--limit", "-5"])
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_FAILURE
    assert "error: true" in out
    assert "must not be negative" in out
    assert "count:" not in out
    assert "limit=" not in out


def test_command_find_zero_limit_prints_empty_state(
    capsys: pytest.CaptureFixture, make_cli_context: ContextFactory
) -> None:
    """A `--limit 0` search is a result, not a rejection - `count: 0`
    at exit 0, which the negative-limit fix leaves alone (#73)."""
    ctx = make_cli_context(
        args=argparse.Namespace(
            query="a", limit=0, package=None, refresh=False
        )
    )
    with mock.patch(f"{CLI}.find_symbol", return_value=[]) as find:
        exit_code = _cli.command_find(ctx)
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_OK
    assert "count: 0" in out
    assert "error: true" not in out
    # The zero is forwarded as given - not clamped to the default (#73)
    find.assert_called_once_with("a", 0, None, refresh=False)


def test_main_maps_unexpected_error_to_exit_2() -> None:
    """An unexpected exception maps to exit code 2."""
    with mock.patch(f"{CLI}.command_home", side_effect=RuntimeError("oops")):
        exit_code = _run_main([])
    assert exit_code == ExitCode.EX_SYNTAX


def test_main_base_exception_maps_to_exit_2(
    capsys: pytest.CaptureFixture,
) -> None:
    """A `BaseException` that is not an `Exception` renders the
    `Unexpected error:` block and exits 2 - previously it escaped
    `except Exception` as a raw traceback (#64)."""

    class Crash(BaseException):
        """A `BaseException` subclass that is not an `Exception`."""

    with mock.patch(f"{CLI}.command_home", side_effect=Crash("boom")):
        exit_code = _run_main([])
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_SYNTAX
    assert "error: true" in out
    assert "Unexpected error: boom" in out


def test_main_reraises_keyboard_interrupt() -> None:
    """`KeyboardInterrupt` propagates through the entry point - the
    caller's abort is not a report about the venv (#64)."""
    with (
        mock.patch("sys.argv", ["venvaxi"]),
        mock.patch("venvaxi.__main__.configure_cli_logging"),
        mock.patch(f"{CLI}.command_home", side_effect=KeyboardInterrupt),
        pytest.raises(KeyboardInterrupt),
    ):
        __main__.main()


def test_main_reraises_system_exit_unrendered(
    capsys: pytest.CaptureFixture,
) -> None:
    """A `SystemExit` reaching the entry point keeps its own code and
    is never rendered as an unexpected error (#64)."""
    with mock.patch(f"{CLI}.command_home", side_effect=SystemExit(5)):
        exit_code = _run_main([])
    out = capsys.readouterr().out
    assert exit_code == 5
    assert "Unexpected error" not in out


def test_main_unexpected_error_emits_toon_on_stdout(
    capsys: pytest.CaptureFixture,
) -> None:
    """An unexpected error keeps the TOON contract on stdout, with the
    traceback on stderr only."""
    with mock.patch(f"{CLI}.command_home", side_effect=RuntimeError("oops")):
        exit_code = _run_main([])
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_SYNTAX
    assert "error: true" in out
    assert "oops" in out
    assert "Traceback" not in out
    assert "Run `venvaxi --help` for available commands" in out


def test_main_verbose_flag_reaches_context() -> None:
    """`venvaxi --verbose` parses & sets `CLIContext.is_verbose`."""
    recorded: dict[str, CLIContext] = {}

    def record(ctx: CLIContext) -> int:
        recorded["ctx"] = ctx
        return ExitCode.EX_OK

    with mock.patch(f"{CLI}.command_home", side_effect=record):
        exit_code = _run_main(["--verbose"])
    assert exit_code == ExitCode.EX_OK
    assert recorded["ctx"].is_verbose is True
    assert recorded["ctx"].args.verbose is True


def test_main_defaults_to_non_verbose() -> None:
    """`venvaxi` without `--verbose` leaves `is_verbose` False."""
    recorded: dict[str, CLIContext] = {}

    def record(ctx: CLIContext) -> int:
        recorded["ctx"] = ctx
        return ExitCode.EX_OK

    with mock.patch(f"{CLI}.command_home", side_effect=record):
        exit_code = _run_main([])
    assert exit_code == ExitCode.EX_OK
    assert recorded["ctx"].is_verbose is False
