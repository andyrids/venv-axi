"""Agent eXperience Interface (AXI) ambient-context installation.

AXI principle 7 (`specs/principles.md`): Make visible to an agent from an
explicit setup command so that every conversation starts with relevant state
already visible - before the agent takes any action.

- Inject a marked block into the `AGENTS.md` of a consuming repo
- Register an MCP server entry in `.vscode/mcp.json`
- Register an MCP server entry in a `.mcp.json`
- Install `.claude/skills/venvaxi/SKILL.md` (opt-in, `--skill`)

NOTE: The above steps are idempotent - running `venvaxi setup` multiple
times has no adverse effect.
"""

import importlib.util
import json
import logging
import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Any

from venvaxi.exceptions import AmbientContextError

logger = logging.getLogger(__package__)

ambient_markdown = Path(__file__).parent.joinpath("ambient.md")
skill_markdown = Path(__file__).parent.joinpath("SKILL.md")


class Text(StrEnum):
    """Ambient-context text components."""

    BEGIN = "<!-- venvaxi:begin -->"
    END = "<!-- venvaxi:end -->"
    GAP = "\n\n"
    BODY = ambient_markdown.read_text(encoding="utf-8").strip()


@contextmanager
def _install_boundary(path: Path) -> Generator[None]:
    """Reraise an `OSError` at a filesystem call as an install failure.

    NOTE: The bound stays visible at the call site - only the wrapped
    filesystem call sits inside the `with` block, never a whole function
    body - so an `OSError` raised anywhere else still escapes as an
    unexpected error (exit 2, venvaxi being broken).

    Args:
        path: The destination artifact path named in the error message.

    Yields:
        Control to the wrapped filesystem call.

    Raises:
        AmbientContextError: If the wrapped call raises `OSError`.
    """
    try:
        yield
    except OSError as exc:
        msg = f"Cannot install ambient context: {path}"
        raise AmbientContextError(msg) from exc


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically write text via a same-directory temp file + rename.

    NOTE: An interrupted write leaves `path` untouched (the `.tmp` file
    is simply overwritten on the next run).

    Args:
        path: The destination file path.
        text: The full file content to write.

    Raises:
        AmbientContextError: If the temp-file write or the rename fails
            with an `OSError`.
    """
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    with _install_boundary(path):
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, path)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically write bytes via a same-directory temp file + rename.

    NOTE: Bytes bypass newline translation, so the destination is a
    byte-for-byte copy of the source on every platform - `write_text`
    would fork an LF source into a CRLF copy on Windows.

    Args:
        path: The destination file path.
        data: The full file content to write.

    Raises:
        AmbientContextError: If the temp-file write or the rename fails
            with an `OSError`.
    """
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    with _install_boundary(path):
        tmp_path.write_bytes(data)
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

    Raises:
        AmbientContextError: If an existing `AGENTS.md` cannot be read,
            or the write fails with an `OSError`.
    """
    path = root / "AGENTS.md"
    block = f"{Text.BEGIN}{Text.GAP}{Text.BODY}{Text.GAP}{Text.END}"

    if not path.exists():
        _atomic_write_bytes(path, f"{block}\n".encode())
        logger.debug("Created `AGENTS.md` with axi block")
        return True

    # NOTE: Read as bytes and decoded, never `read_text` - universal
    # newlines would normalize an existing CRLF file to LF, and writing
    # that back rewrites the hand-authored span the spec requires
    # preserved byte-for-byte. Splicing stays on decoded text.
    with _install_boundary(path):
        original = path.read_bytes().decode("utf-8")
    text = original

    if Text.BEGIN in text and Text.END in text:
        start = text.index(Text.BEGIN)
        end = text.index(Text.END) + len(Text.END)
        updated = text[:start] + block + text[end:]
    else:
        # NOTE: Counts line terminators, not `\n` bytes, so a CRLF file
        # is not read as having one fewer trailing blank line than it
        # has - `rstrip("\n")` alone leaves the `\r` behind.
        stripped = text.rstrip("\r\n")
        trailing = text[len(stripped) :].count("\n") if text else 2
        separator = "\n" * max(2 - trailing, 0)
        updated = f"{text}{separator}{block}\n"

    if updated == original:
        logger.debug("`AGENTS.md` axi block is up-to-date")
        return False
    _atomic_write_bytes(path, updated.encode())
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

    Raises:
        AmbientContextError: If the config directory cannot be created
            or the write fails with an `OSError`.
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
    with _install_boundary(path):
        path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(data, indent=2) + "\n")
    return True


def install_skill(root: Path) -> bool:
    """Install the AXI Claude Code Skill (idempotent).

    NOTE: `SKILL.md` is entirely `venvaxi`-owned content - the whole
    file is overwritten, so hand-edits to a previously installed copy
    are lost (no marker block, no backup).

    Args:
        root: The consuming repo's root path.

    Returns:
        True if `SKILL.md` was created or modified.

    Raises:
        AmbientContextError: If an existing `SKILL.md` cannot be read,
            the skill directory cannot be created, or the write fails
            with an `OSError`.
    """
    # NOTE: Read, compared and written as raw bytes - the bytes on disk
    # *are* the file, and text mode's newline translation would fork an
    # LF source into a CRLF copy on Windows.
    data = skill_markdown.read_bytes()
    path = root / ".claude" / "skills" / "venvaxi" / "SKILL.md"

    if path.exists():
        with _install_boundary(path):
            installed = path.read_bytes()
        if installed == data:
            logger.debug("`SKILL.md` is up-to-date")
            return False

    with _install_boundary(path):
        path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(path, data)
    logger.debug("Installed `SKILL.md` skill")
    return True


def setup_ambient_context(
    root: Path, *, skill: bool = False
) -> dict[str, bool]:
    """Install AXI ambient context into the consuming repo.

    NOTE: MCP registration is gated on `fastmcp` availability - the
    `AGENTS.md` CLI guidance is valid either way, so it is not.

    Args:
        root: The consuming repo root path.
        skill: Whether to also install the Claude Code Skill.

    Returns:
        A mapping of which artifacts were created or modified:
        `AGENTS.md`, `.vscode`, `.mcp.json` and `skill` - the last of
        which is always present, but only ever True when `skill` was
        requested.

    Raises:
        AmbientContextError: If any artifact cannot be read, created or
            written because of an `OSError`.
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
        "SKILL.md": install_skill(root) if skill else False,
    }
