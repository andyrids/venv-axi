"""Unit tests for the STDOUT/STDERR encoding contract.

Each test simulates the failing configuration - a captured pipe on a
non-UTF-8 locale - by reconfiguring the captured stream to `cp1252`
before driving `main()`, so the tests discriminate on CI's UTF-8 Linux
runners rather than depending on the platform locale. See
`specs/behaviors/output-contract.md` (Stream discipline).

NOTE: `capsys` (not a `mock.patch` stream swap) - pytest's fd-level
global capture re-asserts `sys.stdout` while the fixture package is
imported, silently bypassing a patched-in stream. The `capsys` capture
object is itself an `io.TextIOWrapper`, so reconfiguring it to cp1252
exercises exactly the guard and reconfigure `main()` performs.
"""

import io
import sys
from unittest import mock

import pytest

from venvaxi import __main__
from venvaxi._core import ExitCode

CLI = "venvaxi._cli"

# Characters `cp1252` cannot represent, as carried by the fixture
# docstring of `render_grid` in `tests/resources/package/module.py`.
GRID_CHARS = ("┌", "│", "α", "→")


def _reconfigure_cp1252(stream: object) -> io.TextIOWrapper:
    """Reconfigure a captured stream to cp1252 & return it narrowed.

    Args:
        stream: `sys.stdout` or `sys.stderr` under `capsys` capture.

    Returns:
        The stream, narrowed to `io.TextIOWrapper` and reporting
        cp1252 - the encoding a captured pipe reports under a Windows
        locale.
    """
    assert isinstance(stream, io.TextIOWrapper)
    stream.reconfigure(encoding="cp1252")
    return stream


def _run_main(argv: list[str]) -> int:
    """Run `venvaxi.__main__.main` with `argv` & return the exit code.

    Mirrors the `_run_main` helper pattern in `tests/test_cli.py`.
    """
    with (
        mock.patch("sys.argv", ["venvaxi", *argv]),
        mock.patch("venvaxi.__main__.configure_cli_logging"),
        pytest.raises(SystemExit) as exc_info,
    ):
        __main__.main()
    return int(exc_info.value.code)


def test_main_reconfigures_stdout_to_utf8(
    capsys: pytest.CaptureFixture,
) -> None:
    """STDOUT is UTF-8 on every run, whatever encoding it reports."""
    stdout = _reconfigure_cp1252(sys.stdout)
    exit_code = _run_main([])
    assert exit_code == ExitCode.EX_OK
    assert stdout.encoding == "utf-8"


def test_main_reconfigures_stderr_to_utf8(
    capsys: pytest.CaptureFixture,
) -> None:
    """STDERR is UTF-8 on every run, whatever encoding it reports."""
    stderr = _reconfigure_cp1252(sys.stderr)
    exit_code = _run_main([])
    assert exit_code == ExitCode.EX_OK
    assert stderr.encoding == "utf-8"


def test_inspect_docstring_emits_non_cp1252_docstring(
    capsys: pytest.CaptureFixture, fake_package: str
) -> None:
    """`inspect --docstring` emits a non-cp1252 docstring in full and
    exits `EX_OK` on a stream reporting cp1252."""
    _reconfigure_cp1252(sys.stdout)
    exit_code = _run_main(
        ["inspect", f"{fake_package}.module::render_grid", "--docstring"]
    )
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_OK
    assert "error: true" not in out
    for char in GRID_CHARS:
        assert char in out


def test_show_api_docstring_emits_non_cp1252_docstring(
    capsys: pytest.CaptureFixture, fake_package: str
) -> None:
    """`show --api --docstring` emits the complete symbol table and
    exits `EX_OK` on a stream reporting cp1252."""
    _reconfigure_cp1252(sys.stdout)
    exit_code = _run_main(
        ["show", f"{fake_package}.module", "--api", "--docstring"]
    )
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_OK
    assert "error: true" not in out
    assert "count:" in out
    assert "render_grid" in out
    for char in GRID_CHARS:
        assert char in out


def test_unexpected_error_survives_non_cp1252_message(
    capsys: pytest.CaptureFixture,
) -> None:
    """An unexpected error whose message carries non-cp1252 characters
    still emits the TOON error block and exits `EX_SYNTAX`."""
    _reconfigure_cp1252(sys.stdout)
    error = RuntimeError("boom ┌ α → ω")
    with mock.patch(f"{CLI}.command_home", side_effect=error):
        exit_code = _run_main([])
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_SYNTAX
    assert "error: true" in out
    assert "Unexpected error" in out
    assert "α → ω" in out
