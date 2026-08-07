"""Unit tests for `venvaxi._ambient`."""

import json
from pathlib import Path
from unittest import mock

from venvaxi._ambient import (
    _update_mcp_json,
    inject_agents_md,
    install_skill,
    setup_ambient_context,
    skill_markdown,
)

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


def test_skill_markdown_has_frontmatter() -> None:
    """The packaged `skill.md` is a valid skill file."""
    text = skill_markdown.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: venvaxi" in text


def test_install_skill_creates_file(tmp_path: Path) -> None:
    """A missing `SKILL.md` is created verbatim from `skill.md`."""
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
