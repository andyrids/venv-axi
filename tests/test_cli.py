"""Unit tests for `venvaxi._cli`."""

import argparse
from collections.abc import Callable
from pathlib import Path
from unittest import mock

import pytest

from venvaxi import __main__, _cli, exceptions
from venvaxi._core import CLIContext, ExitCode
from venvaxi._introspect import SYMBOL_INFO_FIELDS, SymbolInfo
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
    with mock.patch(f"{CLI}.get_public_api", return_value=symbols):
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
    with mock.patch(f"{CLI}.get_public_api", return_value=symbols):
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
    with mock.patch(f"{CLI}.get_public_api", return_value=[]):
        exit_code = _cli.command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 0" in out
    assert "help[1]:" in out


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
        "skill": False,
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
    assert "skill: false" in out
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
        "skill": True,
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
    assert "skill: true" in out
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
        "skill": False,
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
    assert "help[1]:" in out


def test_main_maps_unexpected_error_to_exit_2() -> None:
    """An unexpected exception maps to exit code 2."""
    with mock.patch(f"{CLI}.command_home", side_effect=RuntimeError("oops")):
        exit_code = _run_main([])
    assert exit_code == ExitCode.EX_SYNTAX


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
