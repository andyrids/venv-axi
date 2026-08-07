"""Agent eXperience Interface (AXI) ambient-context installation.

AXI principle 7 (`ICM/_config/reference-standard-axi.md`): Make visible to an
agent from an explicit setup command so that every conversation starts with
relevant state already visible - before the agent takes any action.

- Inject a marked block into the `AGENTS.md` of a consuming repo
- Register an MCP server entry in `.vscode/mcp.json`
- Register an MCP server entry in a `.mcp.json`

NOTE: The above steps are idempotent - running `venvaxi setup` multiple
times has no adverse effect.
"""

import importlib.util
import json
import logging
import os
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__package__)

ambient_markdown = Path(__file__).parent.joinpath("ambient.md")


class Text(StrEnum):
    """Ambient-context text components."""

    BEGIN = "<!-- venvaxi:begin -->"
    END = "<!-- venvaxi:end -->"
    GAP = "\n\n"
    BODY = ambient_markdown.read_text(encoding="utf-8").strip()


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically write text via a same-directory temp file + rename.

    NOTE: An interrupted write leaves `path` untouched (the `.tmp` file
    is simply overwritten on the next run).

    Args:
        path: The destination file path.
        text: The full file content to write.
    """
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def _axi_command() -> str:
    """Resolve absolute path of the `venvaxi` executable.

    Returns:
        The absolute path of the invoked `venvaxi` script.
    """
    return str(Path(sys.argv[0]).resolve())


def mcp_available() -> bool:
    """Check `fastmcp` availability without importing it.

    NOTE: `importlib.util.find_spec` has no import side effects, so this
    is safe on a plain `venv-axi` install (no `mcp` extra).

    Returns:
        True if the `fastmcp` module is importable.
    """
    return importlib.util.find_spec("fastmcp") is not None


def inject_agents_md(root: Path) -> bool:
    """Inject ambient-context block into `AGENTS.md` (idempotent).

    Args:
        root: The consuming repo's root path.

    Returns:
        True if `AGENTS.md` was created or modified.
    """
    path = root / "AGENTS.md"
    block = f"{Text.BEGIN}{Text.GAP}{Text.BODY}{Text.GAP}{Text.END}"

    if not path.exists():
        _atomic_write_text(path, f"{block}\n")
        logger.debug("Created `AGENTS.md` with axi block")
        return True

    original = path.read_text(encoding="utf-8")
    text = original

    if Text.BEGIN in text and Text.END in text:
        start = text.index(Text.BEGIN)
        end = text.index(Text.END) + len(Text.END)
        updated = text[:start] + block + text[end:]
    else:
        trailing = len(text) - len(text.rstrip("\n")) if text else 2
        separator = "\n" * max(2 - trailing, 0)
        updated = f"{text}{separator}{block}\n"

    if updated == original:
        logger.debug("`AGENTS.md` axi block is up-to-date")
        return False
    _atomic_write_text(path, updated)
    logger.debug("Updated `AGENTS.md` AXI block")
    return True


def _update_mcp_json(path: Path, servers_key: str, available: bool) -> bool:
    """Register AXI MCP server in a config file (idempotent).

    NOTE: A registered server that `venvaxi serve` cannot start would
    die on every agent session - without `fastmcp` the entry is dropped
    instead of written.

    Args:
        path: The MCP config JSON file path.
        servers_key: The top-level key holding server entries
            (`"servers"` for VS Code, `"mcpServers"` elsewhere).
        available: Whether `fastmcp` is importable in this venv.

    Returns:
        True if `path` was created or modified.
    """
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Ignoring malformed `%s`", path)
            data = {}

    servers = data.setdefault(servers_key, {})

    if not available:
        if servers.pop("VenvAXI", None) is None:
            return False
        _atomic_write_text(path, json.dumps(data, indent=2) + "\n")
        return True

    entry = {
        "type": "stdio",
        "command": _axi_command(),
        "args": ["serve"],
    }

    if servers.get("VenvAXI") == entry:
        return False

    servers["VenvAXI"] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(data, indent=2) + "\n")
    return True


def setup_ambient_context(root: Path) -> dict[str, bool]:
    """Install AXI ambient context into the consuming repo.

    NOTE: MCP registration is gated on `fastmcp` availability - the
    `AGENTS.md` CLI guidance is valid either way, so it is not.

    Args:
        root: The consuming repo root path.

    Returns:
        A mapping of which artifacts were created or modified:
        `AGENTS.md`, `.vscode` and `.mcp.json`.
    """
    available = mcp_available()
    return {
        "AGENTS.md": inject_agents_md(root),
        ".vscode": _update_mcp_json(
            root / ".vscode" / "mcp.json", "servers", available
        ),
        ".mcp.json": _update_mcp_json(
            root / ".mcp.json", "mcpServers", available
        ),
    }
