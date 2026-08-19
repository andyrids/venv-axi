"""Unit tests for `venvaxi._ambient`."""

import json
from pathlib import Path
from unittest import mock

import pytest

from venvaxi import __main__
from venvaxi._ambient import (
    _update_mcp_json,
    inject_agents_md,
    install_skill,
    setup_ambient_context,
    skill_markdown,
)
from venvaxi._core import ExitCode
from venvaxi.exceptions import AmbientContextError

AMBIENT = "venvaxi._ambient"


def test_inject_agents_md_creates_file(tmp_path: Path) -> None:
    """A missing `AGENTS.md` is created with the axi block."""
    changed = inject_agents_md(tmp_path)
    text = (tmp_path / "AGENTS.md").read_text()
    assert changed is True
    assert "<!-- venvaxi:begin -->" in text
    assert "<!-- venvaxi:end -->" in text
    assert "axi" in text
    assert "venvaxi find" in text
    assert "venvaxi inspect" in text
    assert "venvaxi tree" in text
    assert "venvaxi serve" in text
    assert "venvaxi setup" in text


def test_inject_agents_md_appends_to_existing_file(tmp_path: Path) -> None:
    """An existing `AGENTS.md` without markers gets the block appended."""
    path = tmp_path / "AGENTS.md"
    path.write_text("# My project\n")
    changed = inject_agents_md(tmp_path)
    text = path.read_text()
    assert changed is True
    assert "# My project" in text
    assert "<!-- venvaxi:begin -->" in text


def test_inject_agents_md_idempotent(tmp_path: Path) -> None:
    """Running injection twice makes no further changes."""
    inject_agents_md(tmp_path)
    changed = inject_agents_md(tmp_path)
    assert changed is False


def test_inject_agents_md_replaces_stale_block(tmp_path: Path) -> None:
    """An outdated block between markers is replaced in-place."""
    path = tmp_path / "AGENTS.md"
    path.write_text(
        "# My project\n\n"
        "<!-- venvaxi:begin -->\nstale content\n"
        "<!-- venvaxi:end -->\n"
    )
    changed = inject_agents_md(tmp_path)
    text = path.read_text()
    assert changed is True
    assert "stale content" not in text
    assert "VenvAXI" in text


def test_inject_agents_md_write_failure_raises(tmp_path: Path) -> None:
    """An `OSError` writing `AGENTS.md` raises `AmbientContextError`
    naming the destination path, chained from the `OSError`."""
    with (
        mock.patch.object(Path, "write_bytes", side_effect=OSError("denied")),
        pytest.raises(AmbientContextError) as exc_info,
    ):
        inject_agents_md(tmp_path)
    assert str(tmp_path / "AGENTS.md") in str(exc_info.value)
    assert ".tmp" not in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, OSError)


def test_inject_agents_md_read_failure_raises(tmp_path: Path) -> None:
    """An `OSError` reading an existing `AGENTS.md` raises
    `AmbientContextError`."""
    (tmp_path / "AGENTS.md").write_text("# My project\n", encoding="utf-8")
    with (
        mock.patch.object(Path, "read_bytes", side_effect=OSError("denied")),
        pytest.raises(AmbientContextError) as exc_info,
    ):
        inject_agents_md(tmp_path)
    assert str(tmp_path / "AGENTS.md") in str(exc_info.value)


def test_inject_agents_md_preserves_lf_bytes_outside_markers(
    tmp_path: Path,
) -> None:
    """Hand-authored LF content outside the markers survives verbatim.

    NOTE: `write_text`/`read_text` translate newlines on Windows, so the
    pre-fix implementation rewrote every `\\n` in the hand-authored span
    as `\\r\\n` - a violation of the byte-for-byte clause in
    `specs/commands/setup.md`.
    """
    path = tmp_path / "AGENTS.md"
    hand = b"# My project\n\nLine A\nLine B\n"
    path.write_bytes(hand)
    inject_agents_md(tmp_path)
    written = path.read_bytes()
    assert written.startswith(hand)
    assert b"\r\n" not in written[: len(hand)]


def test_inject_agents_md_preserves_crlf_bytes_outside_markers(
    tmp_path: Path,
) -> None:
    """Hand-authored CRLF content outside the markers survives verbatim.

    NOTE: The mirror of the LF case - `read_text` normalizes CRLF to LF
    on the way in, so writing the result back rewrote the span just as
    surely as the write-side translation did.
    """
    path = tmp_path / "AGENTS.md"
    hand = b"# My project\r\n\r\nLine A\r\nLine B\r\n"
    path.write_bytes(hand)
    inject_agents_md(tmp_path)
    assert path.read_bytes().startswith(hand)


def test_inject_agents_md_preserves_bytes_around_existing_markers(
    tmp_path: Path,
) -> None:
    """Replacing a stale block leaves the spans either side untouched."""
    path = tmp_path / "AGENTS.md"
    head = b"# My project\n\nLine A\n\n"
    tail = b"\n\n## Trailing section\n\nLine B\n"
    # NOTE: A distinctive sentinel, not the word 'stale' - the injected
    # ambient body itself contains 'stale graph', so the obvious
    # spelling of this assertion passes vacuously.
    sentinel = b"SUPERSEDED-BLOCK-BODY"
    path.write_bytes(
        head
        + b"<!-- venvaxi:begin -->\n"
        + sentinel
        + b"\n<!-- venvaxi:end -->"
        + tail
    )
    inject_agents_md(tmp_path)
    written = path.read_bytes()
    assert written.startswith(head)
    assert written.endswith(tail)
    assert sentinel not in written


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
        mock.patch.object(Path, "write_text", side_effect=OSError("denied")),
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
    # NOTE: `mcp_available` is patched so the suite passes with or
    # without the `mcp` extra installed
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
    ):
        changed = setup_ambient_context(tmp_path, skill=True)

    assert set(changed) == {"AGENTS.md", ".vscode", ".mcp.json", "SKILL.md"}
    assert all(changed.values())


def test_setup_ambient_context_skips_skill_by_default(
    tmp_path: Path,
) -> None:
    """Without `skill=True`, no skill file is written but the `skill`
    key is still reported."""
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
    ):
        changed = setup_ambient_context(tmp_path)

    assert changed["SKILL.md"] is False
    assert not (tmp_path / ".claude").exists()


def test_setup_ambient_context_second_run_reports_no_change(
    tmp_path: Path,
) -> None:
    """A second `setup_ambient_context` run reports every artifact as
    unchanged (the `changed` booleans are accurate, not always True)."""
    with (
        mock.patch(f"{AMBIENT}._axi_command", return_value="/bin/venvaxi"),
        mock.patch(f"{AMBIENT}.mcp_available", return_value=True),
    ):
        setup_ambient_context(tmp_path, skill=True)
        changed = setup_ambient_context(tmp_path, skill=True)

    assert not any(changed.values())


def test_setup_ambient_context_skips_mcp_when_unavailable(
    tmp_path: Path,
) -> None:
    """Without `fastmcp`, `AGENTS.md` is still injected but no MCP
    config file is registered."""
    with mock.patch(f"{AMBIENT}.mcp_available", return_value=False):
        changed = setup_ambient_context(tmp_path)

    assert changed == {
        "AGENTS.md": True,
        ".vscode": False,
        ".mcp.json": False,
        "SKILL.md": False,
    }
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / ".vscode" / "mcp.json").exists()
    assert not (tmp_path / ".mcp.json").exists()


def _run_main_setup(root: Path) -> int:
    """Run `venvaxi setup` through the real entry point over `root`.

    Args:
        root: The consuming repo root `get_project_root` resolves to.

    Returns:
        The process exit code raised via `SystemExit`.
    """
    with (
        mock.patch("sys.argv", ["venvaxi", "setup"]),
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
    exit_code = _run_main_setup(tmp_path)
    out = capsys.readouterr().out
    assert exit_code == ExitCode.EX_OK
    assert "AGENTS.md: true" in out
    assert '".vscode": true' in out
    assert '".mcp.json": true' in out
    assert "SKILL.md: false" in out
    assert "error: true" not in out
