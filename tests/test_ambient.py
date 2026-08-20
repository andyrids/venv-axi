"""Unit tests for `venvaxi._ambient`."""

import json
from pathlib import Path
from unittest import mock

import pytest

from venvaxi import __main__
from venvaxi._ambient import (
    _update_mcp_json,
    install_skill,
    setup_ambient_context,
    skill_markdown,
    strip_agents_md,
)
from venvaxi._core import ExitCode
from venvaxi.exceptions import AmbientContextError

AMBIENT = "venvaxi._ambient"


# NOTE: A distinctive sentinel for the legacy block body, never a word
# the removal path could plausibly emit. A previous spelling of these
# tests asserted `b"stale" not in written` and failed against correct
# code, because the injected body itself contained 'stale graph'. Had
# the substring been rarer the assertion would have passed vacuously,
# which is the more dangerous direction.
SENTINEL = b"SUPERSEDED-BLOCK-BODY"


def _legacy_block(body: bytes = SENTINEL) -> bytes:
    """Build a block in the shape the removed injection wrote."""
    return b"<!-- venvaxi:begin -->\n" + body + b"\n<!-- venvaxi:end -->"


def _seed_legacy_agents_md(root: Path) -> Path:
    """Write an `AGENTS.md` carrying a block an earlier version left.

    Args:
        root: The consuming repo root to seed.

    Returns:
        The seeded `AGENTS.md` path.
    """
    path = root / "AGENTS.md"
    path.write_bytes(b"# My project\n\n" + _legacy_block() + b"\n")
    return path


def test_strip_agents_md_absent_file_is_noop(tmp_path: Path) -> None:
    """A missing `AGENTS.md` is reported unchanged and never created."""
    changed = strip_agents_md(tmp_path)
    assert changed is False
    assert not (tmp_path / "AGENTS.md").exists()


def test_strip_agents_md_without_markers_is_noop(tmp_path: Path) -> None:
    """An `AGENTS.md` carrying no block is left byte-identical."""
    path = tmp_path / "AGENTS.md"
    hand = b"# My project\n\nLine A\nLine B\n"
    path.write_bytes(hand)
    changed = strip_agents_md(tmp_path)
    assert changed is False
    assert path.read_bytes() == hand


def test_strip_agents_md_removes_block(tmp_path: Path) -> None:
    """A legacy block is removed and reported as a change."""
    path = tmp_path / "AGENTS.md"
    path.write_bytes(b"# My project\n\n" + _legacy_block() + b"\n")
    changed = strip_agents_md(tmp_path)
    written = path.read_bytes()
    assert changed is True
    assert SENTINEL not in written
    assert b"venvaxi:begin" not in written
    assert b"venvaxi:end" not in written
    assert written == b"# My project\n"


def test_strip_agents_md_idempotent(tmp_path: Path) -> None:
    """A second run over an already-stripped file changes nothing."""
    path = tmp_path / "AGENTS.md"
    path.write_bytes(b"# My project\n\n" + _legacy_block() + b"\n")
    strip_agents_md(tmp_path)
    stripped = path.read_bytes()
    changed = strip_agents_md(tmp_path)
    assert changed is False
    assert path.read_bytes() == stripped


def test_strip_agents_md_leaves_no_residual_blank_line(
    tmp_path: Path,
) -> None:
    """Removing a mid-file block collapses both seams to one blank line.

    NOTE: The injection wrote a two-newline separator ahead of the block
    and one after it. Cutting only the marked span strands a blank line
    at each seam, which accumulates every time a consumer upgrades.
    """
    path = tmp_path / "AGENTS.md"
    path.write_bytes(
        b"# My project\n\n"
        + _legacy_block()
        + b"\n\n## Trailing section\n\nLine B\n"
    )
    strip_agents_md(tmp_path)
    written = path.read_bytes()
    assert written == b"# My project\n\n## Trailing section\n\nLine B\n"
    assert b"\n\n\n" not in written


def test_strip_agents_md_block_only_file_empties(tmp_path: Path) -> None:
    """A file holding nothing but the block is emptied, not deleted."""
    path = tmp_path / "AGENTS.md"
    path.write_bytes(_legacy_block() + b"\n")
    changed = strip_agents_md(tmp_path)
    assert changed is True
    assert path.exists()
    assert path.read_bytes() == b""


def test_strip_agents_md_write_failure_raises(tmp_path: Path) -> None:
    """An `OSError` writing `AGENTS.md` raises `AmbientContextError`
    naming the destination path, chained from the `OSError`."""
    path = tmp_path / "AGENTS.md"
    path.write_bytes(b"# My project\n\n" + _legacy_block() + b"\n")
    with (
        mock.patch.object(Path, "write_bytes", side_effect=OSError("denied")),
        pytest.raises(AmbientContextError) as exc_info,
    ):
        strip_agents_md(tmp_path)
    assert str(path) in str(exc_info.value)
    assert ".tmp" not in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, OSError)


def test_strip_agents_md_read_failure_raises(tmp_path: Path) -> None:
    """An `OSError` reading an existing `AGENTS.md` raises
    `AmbientContextError`."""
    (tmp_path / "AGENTS.md").write_bytes(b"# My project\n")
    with (
        mock.patch.object(Path, "read_bytes", side_effect=OSError("denied")),
        pytest.raises(AmbientContextError) as exc_info,
    ):
        strip_agents_md(tmp_path)
    assert str(tmp_path / "AGENTS.md") in str(exc_info.value)


def test_strip_agents_md_preserves_lf_bytes_outside_markers(
    tmp_path: Path,
) -> None:
    """Hand-authored LF content outside the markers survives verbatim.

    NOTE: `write_text`/`read_text` translate newlines on Windows, so a
    text-mode implementation would rewrite every `\\n` in the
    hand-authored span as `\\r\\n` - a violation of the byte-for-byte
    clause in `specs/commands/setup.md`. Removal has to hold the line
    the injection did.
    """
    path = tmp_path / "AGENTS.md"
    hand = b"# My project\n\nLine A\nLine B\n"
    path.write_bytes(hand + b"\n" + _legacy_block() + b"\n")
    strip_agents_md(tmp_path)
    written = path.read_bytes()
    assert written == hand
    assert b"\r\n" not in written


def test_strip_agents_md_preserves_crlf_bytes_outside_markers(
    tmp_path: Path,
) -> None:
    """Hand-authored CRLF content outside the markers survives verbatim.

    NOTE: The mirror of the LF case - `read_text` normalizes CRLF to LF
    on the way in, so writing the result back rewrites the span just as
    surely as write-side translation does. This case is the one that
    discriminates on Linux, where CI runs.
    """
    path = tmp_path / "AGENTS.md"
    hand = b"# My project\r\n\r\nLine A\r\nLine B\r\n"
    path.write_bytes(hand + b"\r\n" + _legacy_block() + b"\r\n")
    strip_agents_md(tmp_path)
    written = path.read_bytes()
    assert written == hand
    assert b"\n" not in written.replace(b"\r\n", b"")


def test_strip_agents_md_preserves_bytes_around_markers(
    tmp_path: Path,
) -> None:
    """Removing the block leaves the spans either side untouched."""
    path = tmp_path / "AGENTS.md"
    head = b"# My project\n\nLine A"
    tail = b"## Trailing section\n\nLine B\n"
    path.write_bytes(head + b"\n\n" + _legacy_block() + b"\n\n" + tail)
    strip_agents_md(tmp_path)
    written = path.read_bytes()
    assert written.startswith(head)
    assert written.endswith(tail)
    assert SENTINEL not in written


def test_update_mcp_json_creates_file(tmp_path: Path) -> None:
    """A missing MCP config file is created with a VenvAXI entry."""
    path = tmp_path / ".vscode" / "mcp.json"
    with mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"):
        changed = _update_mcp_json(path, "servers", available=True)

    data = json.loads(path.read_text())
    assert changed is True
    assert data["servers"]["VenvAXI"]["command"] == "/bin/venvaxi"
    assert data["servers"]["VenvAXI"]["args"] == ["serve"]


def test_update_mcp_json_idempotent(tmp_path: Path) -> None:
    """Running the update twice makes no further changes."""
    path = tmp_path / "mcp.json"
    with mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"):
        _update_mcp_json(path, "mcpServers", available=True)
        changed = _update_mcp_json(path, "mcpServers", available=True)
    assert changed is False


def test_update_mcp_json_preserves_other_keys(tmp_path: Path) -> None:
    """Existing unrelated servers/keys are preserved."""
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    with mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"):
        _update_mcp_json(path, "mcpServers", available=True)

    data = json.loads(path.read_text())
    assert "other" in data["mcpServers"]
    assert "VenvAXI" in data["mcpServers"]


def test_update_mcp_json_recovers_from_malformed_json(
    tmp_path: Path,
) -> None:
    """Malformed existing JSON is replaced rather than raising."""
    path = tmp_path / "mcp.json"
    path.write_text("{not valid json")
    with mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"):
        changed = _update_mcp_json(path, "mcpServers", available=True)

    data = json.loads(path.read_text())
    assert changed is True
    assert "VenvAXI" in data["mcpServers"]


def test_update_mcp_json_unavailable_skips_creation(tmp_path: Path) -> None:
    """Without `fastmcp`, a missing MCP config file is not created."""
    path = tmp_path / ".vscode" / "mcp.json"
    changed = _update_mcp_json(path, "servers", available=False)
    assert changed is False
    assert not path.exists()


def test_update_mcp_json_unavailable_removes_entries(tmp_path: Path) -> None:
    """Without `fastmcp`, the `VenvAXI` entry is removed and other
    entries are preserved."""
    path = tmp_path / "mcp.json"
    path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "VenvAXI": {"command": "x"},
                    "other": {"command": "y"},
                }
            }
        )
    )
    changed = _update_mcp_json(path, "mcpServers", available=False)

    data = json.loads(path.read_text())
    assert changed is True
    assert "VenvAXI" not in data["mcpServers"]
    assert "other" in data["mcpServers"]


def test_update_mcp_json_unavailable_idempotent(tmp_path: Path) -> None:
    """Without `fastmcp`, an already-clean config is left untouched."""
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {"other": {"command": "y"}}}))
    changed = _update_mcp_json(path, "mcpServers", available=False)
    assert changed is False
    assert "other" in json.loads(path.read_text())["mcpServers"]


def test_update_mcp_json_write_failure_raises(tmp_path: Path) -> None:
    """An `OSError` writing an MCP config file raises
    `AmbientContextError` naming the destination path."""
    path = tmp_path / ".vscode" / "mcp.json"
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch.object(Path, "write_bytes", side_effect=OSError("denied")),
        pytest.raises(AmbientContextError) as exc_info,
    ):
        _update_mcp_json(path, "servers", available=True)
    assert str(path) in str(exc_info.value)
    assert ".tmp" not in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, OSError)


def test_skill_markdown_has_frontmatter() -> None:
    """The packaged `SKILL.md` is a valid skill file."""
    text = skill_markdown.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: venvaxi" in text


def test_install_skill_creates_file(tmp_path: Path) -> None:
    """A missing `SKILL.md` is created verbatim from the packaged copy."""
    changed = install_skill(tmp_path)
    path = tmp_path / ".claude" / "skills" / "venvaxi" / "SKILL.md"

    assert changed is True
    # NOTE: Byte-for-byte - the whole file is `venvaxi`-owned, so the
    # round-trip must match for the idempotence check to hold
    assert path.read_text(encoding="utf-8") == skill_markdown.read_text(
        encoding="utf-8"
    )


def test_install_skill_idempotent(tmp_path: Path) -> None:
    """Running the install twice makes no further changes."""
    install_skill(tmp_path)
    changed = install_skill(tmp_path)
    assert changed is False


def test_install_skill_overwrites_stale_copy(tmp_path: Path) -> None:
    """An existing, edited `SKILL.md` is overwritten wholesale."""
    path = tmp_path / ".claude" / "skills" / "venvaxi" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("stale content\n", encoding="utf-8")
    changed = install_skill(tmp_path)

    assert changed is True
    assert "stale content" not in path.read_text(encoding="utf-8")


def test_install_skill_write_failure_raises(tmp_path: Path) -> None:
    """An `OSError` writing `SKILL.md` raises `AmbientContextError`
    naming the destination path."""
    path = tmp_path / ".claude" / "skills" / "venvaxi" / "SKILL.md"
    with (
        mock.patch.object(Path, "write_bytes", side_effect=OSError("denied")),
        pytest.raises(AmbientContextError) as exc_info,
    ):
        install_skill(tmp_path)
    assert str(path) in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, OSError)


def test_install_skill_read_failure_raises(tmp_path: Path) -> None:
    """An `OSError` reading an existing `SKILL.md` raises
    `AmbientContextError` (the packaged copy is read untouched)."""
    path = tmp_path / ".claude" / "skills" / "venvaxi" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("stale content\n", encoding="utf-8")
    real_read_bytes = Path.read_bytes

    def deny(self: Path) -> bytes:
        """Deny reads of the installed copy only, not package data."""
        if self == path:
            raise OSError("denied")
        return real_read_bytes(self)

    with (
        mock.patch.object(Path, "read_bytes", deny),
        pytest.raises(AmbientContextError) as exc_info,
    ):
        install_skill(tmp_path)
    assert str(path) in str(exc_info.value)


def test_setup_ambient_context_reports_all_artifacts(
    tmp_path: Path,
) -> None:
    """`setup_ambient_context` reports all four artifact statuses."""
    # NOTE: A legacy block is seeded so the `AGENTS.md` key has
    # something to report. Without one the removal pass is a no-op and
    # this test would assert a False it had itself arranged.
    _seed_legacy_agents_md(tmp_path)
    # NOTE: `mcp_available` is patched so the suite passes with or
    # without the `mcp` extra installed
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
    ):
        changed = setup_ambient_context(tmp_path, skill=True)

    assert set(changed) == {"AGENTS.md", ".vscode", ".mcp.json", "SKILL.md"}
    assert all(changed.values())


def test_setup_ambient_context_never_creates_agents_md(
    tmp_path: Path,
) -> None:
    """`setup` no longer writes an ambient block, so a repo without an
    `AGENTS.md` does not gain one."""
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
    ):
        changed = setup_ambient_context(tmp_path, skill=True)

    assert changed["AGENTS.md"] is False
    assert not (tmp_path / "AGENTS.md").exists()


def test_setup_ambient_context_installs_skill_by_default(
    tmp_path: Path,
) -> None:
    """Without a `skill` argument, the skill file is written and the
    `SKILL.md` key reports True."""
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
    ):
        changed = setup_ambient_context(tmp_path)

    assert changed["SKILL.md"] is True
    path = tmp_path / ".claude" / "skills" / "venvaxi" / "SKILL.md"
    assert path.read_bytes() == skill_markdown.read_bytes()


def test_setup_installs_skill_without_fastmcp(tmp_path: Path) -> None:
    """Where `fastmcp` is not importable, a bare `setup` still installs
    the skill while dropping both MCP entries (principle 7 - the ungated
    artifact is not also withheld)."""
    with mock.patch(f"{AMBIENT}.mcp_available", return_value=False):
        changed = setup_ambient_context(tmp_path)

    assert changed["SKILL.md"] is True
    assert changed[".vscode"] is False
    assert changed[".mcp.json"] is False
    path = tmp_path / ".claude" / "skills" / "venvaxi" / "SKILL.md"
    assert path.read_bytes() == skill_markdown.read_bytes()
    assert not (tmp_path / ".vscode" / "mcp.json").exists()
    assert not (tmp_path / ".mcp.json").exists()


def test_setup_reports_false_when_skill_unchanged(tmp_path: Path) -> None:
    """While the installed skill matches the packaged copy
    byte-for-byte, a bare `setup` reports `SKILL.md` as False."""
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
    ):
        first = setup_ambient_context(tmp_path)
        changed = setup_ambient_context(tmp_path)

    assert first["SKILL.md"] is True
    assert changed["SKILL.md"] is False


def test_setup_ambient_context_second_run_reports_no_change(
    tmp_path: Path,
) -> None:
    """A second `setup_ambient_context` run reports every artifact as
    unchanged (the `changed` booleans are accurate, not always True)."""
    _seed_legacy_agents_md(tmp_path)
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
    ):
        first = setup_ambient_context(tmp_path, skill=True)
        changed = setup_ambient_context(tmp_path, skill=True)

    assert first["AGENTS.md"] is True
    assert not any(changed.values())


def test_setup_ambient_context_skips_mcp_when_unavailable(
    tmp_path: Path,
) -> None:
    """Without `fastmcp`, the legacy block is still stripped but no MCP
    config file is registered."""
    path = _seed_legacy_agents_md(tmp_path)
    with mock.patch(f"{AMBIENT}.mcp_available", return_value=False):
        changed = setup_ambient_context(tmp_path)

    assert changed == {
        "AGENTS.md": True,
        ".vscode": False,
        ".mcp.json": False,
        "SKILL.md": True,
    }
    assert b"venvaxi:begin" not in path.read_bytes()
    assert not (tmp_path / ".vscode" / "mcp.json").exists()
    assert not (tmp_path / ".mcp.json").exists()


def _run_main_setup(root: Path, *args: str) -> int:
    """Run `venvaxi setup` through the real entry point over `root`.

    Args:
        root: The consuming repo root `get_project_root` resolves to.
        args: Extra CLI arguments appended after `setup`.

    Returns:
        The process exit code raised via `SystemExit`.
    """
    with (
        mock.patch("sys.argv", ["venvaxi", "setup", *args]),
        mock.patch("venvaxi.__main__.configure_cli_logging"),
        mock.patch("venvaxi._cli.get_project_root", return_value=root),
        mock.patch("venvaxi._cli.mcp_available", return_value=True),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        pytest.raises(SystemExit) as exc_info,
    ):
        __main__.main()
    return int(exc_info.value.code)


def test_main_setup_write_failure_emits_toon_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A failed install emits the TOON error block and exits 1 (an
    `Error` reported), not 2 (venvaxi being broken)."""
    # NOTE: Seeded so the first write is still the `AGENTS.md` one.
    # Without a block to strip that write never happens and the failure
    # silently relocates to `.vscode/mcp.json` - which is how this test
    # kept passing against a defect once before.
    _seed_legacy_agents_md(tmp_path)
    with mock.patch.object(Path, "write_bytes", side_effect=OSError("denied")):
        exit_code = _run_main_setup(tmp_path)
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_FAILURE
    assert "error: true" in out
    assert "help[1]:" in out
    assert "Unexpected error" not in out


def test_main_setup_write_failure_names_path(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """The failed-install message names the path that could not be
    written."""
    _seed_legacy_agents_md(tmp_path)
    with mock.patch.object(Path, "write_bytes", side_effect=OSError("denied")):
        exit_code = _run_main_setup(tmp_path)
    # NOTE: TOON quotes the message and escapes backslashes, so the
    # escaping is reversed before comparing against a Windows path
    out = capsys.readouterr().out.replace("\\\\", "\\")
    assert exit_code == ExitCode.EX_FAILURE
    assert "Cannot install ambient context" in out
    assert str(tmp_path / "AGENTS.md") in out


def test_main_setup_success_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A successful `setup` still emits the artifact mapping and exits
    0 - the failure bound must not disturb the success path."""
    path = _seed_legacy_agents_md(tmp_path)
    exit_code = _run_main_setup(tmp_path)
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_OK
    assert "AGENTS.md: true" in out
    assert b"venvaxi:begin" not in path.read_bytes()
    assert '".vscode": true' in out
    assert '".mcp.json": true' in out
    assert "SKILL.md: true" in out
    assert "error: true" not in out


def test_setup_no_skill_suppresses_install(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`setup --no-skill` writes no skill file and reports
    `SKILL.md: false`."""
    exit_code = _run_main_setup(tmp_path, "--no-skill")
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_OK
    assert "SKILL.md: false" in out
    assert "SKILL.md: true" not in out
    assert not (tmp_path / ".claude").exists()


def test_setup_skill_flag_matches_default(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """`setup --skill` produces the same result as a bare `setup`."""
    bare_root = tmp_path / "bare"
    flag_root = tmp_path / "flag"
    bare_root.mkdir()
    flag_root.mkdir()

    bare_code = _run_main_setup(bare_root)
    bare_out = capsys.readouterr().out
    flag_code = _run_main_setup(flag_root, "--skill")
    flag_out = capsys.readouterr().out

    assert bare_code == flag_code == ExitCode.EX_OK
    assert bare_out == flag_out
    bare_skill = bare_root / ".claude" / "skills" / "venvaxi" / "SKILL.md"
    flag_skill = flag_root / ".claude" / "skills" / "venvaxi" / "SKILL.md"
    assert bare_skill.read_bytes() == flag_skill.read_bytes()
