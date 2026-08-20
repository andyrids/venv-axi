"""Agent eXperience Interface (AXI) ambient-context installation.

AXI principle 7 (`specs/principles.md`): Make visible to an agent from an
explicit setup command so that every conversation starts with relevant state
already visible - before the agent takes any action.

- Register an MCP server entry in `.vscode/mcp.json`
- Register an MCP server entry in a `.mcp.json`
- Install `.claude/skills/venvaxi/SKILL.md` (default; `--no-skill` opts out)
- Remove the legacy marked block from the `AGENTS.md` of a consuming repo

NOTE: The above steps are idempotent - running `venvaxi setup` multiple
times has no adverse effect.

NOTE: The `AGENTS.md` block is no longer written. It duplicated the skill
in every session of every consuming repo whether or not the task touched a
dependency, so the guidance moved to the artifact that loads on demand.
`setup` strips a block left by an earlier version so a consumer stops
paying for it, rather than leaving an orphan nothing will ever refresh.
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

skill_markdown = Path(__file__).parent.joinpath("SKILL.md")


class Text(StrEnum):
    """Legacy ambient-block markers, retained for removal."""

    BEGIN = "<!-- venvaxi:begin -->"
    END = "<!-- venvaxi:end -->"


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


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically write bytes via a same-directory temp file + rename.

    NOTE: An interrupted write leaves `path` untouched (the `.tmp` file
    is simply overwritten on the next run).

    NOTE: Every caller encodes at the call site rather than handing text
    to a second helper. Bytes bypass newline translation, so the
    destination is a byte-for-byte copy on every platform - `write_text`
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


def strip_agents_md(root: Path) -> bool:
    """Remove a legacy ambient block from `AGENTS.md` (idempotent).

    NOTE: This never creates `AGENTS.md`. An absent file, or one
    carrying no marker pair, is left alone and reported as unchanged -
    there is nothing to remove, and writing to say so would be a
    mutation the caller did not ask for.

    Args:
        root: The consuming repo's root path.

    Returns:
        True if a block was found and removed.

    Raises:
        AmbientContextError: If an existing `AGENTS.md` cannot be read,
            or the write fails with an `OSError`.
    """
    path = root / "AGENTS.md"
    if not path.exists():
        return False

    # NOTE: Read as bytes and decoded, never `read_text` - universal
    # newlines would normalize an existing CRLF file to LF, and writing
    # that back rewrites the hand-authored span the spec requires
    # preserved byte-for-byte. Splicing stays on decoded text.
    with _install_boundary(path):
        original = path.read_bytes().decode("utf-8")

    if Text.BEGIN not in original or Text.END not in original:
        logger.debug("No `AGENTS.md` axi block to remove")
        return False

    start = original.index(Text.BEGIN)
    end = original.index(Text.END) + len(Text.END)

    # NOTE: The injection this undoes wrote a two-newline separator
    # ahead of the block and one after it, so cutting the marked span
    # alone strands a blank line at each seam. Terminators are trimmed
    # back off both sides and the join is rebuilt, which returns the
    # file to the shape the injection was applied to.
    #
    # NOTE: The rebuilt join follows the terminator the prefix already
    # ends with, so removing the block from a CRLF file does not splice
    # a lone LF into it. Everything inside the prefix and suffix is
    # untouched.
    head = original[:start]
    terminator = "\r\n" if head.endswith("\r\n") else "\n"
    prefix = head.rstrip("\r\n")
    suffix = original[end:].lstrip("\r\n")

    if prefix and suffix:
        updated = f"{prefix}{terminator * 2}{suffix}"
    elif prefix:
        updated = f"{prefix}{terminator}"
    else:
        updated = suffix

    _atomic_write_bytes(path, updated.encode())
    logger.debug("Removed `AGENTS.md` axi block")
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
        _atomic_write_bytes(path, (json.dumps(data, indent=2) + "\n").encode())
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
    _atomic_write_bytes(path, (json.dumps(data, indent=2) + "\n").encode())
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
    root: Path, *, skill: bool = True
) -> dict[str, bool]:
    """Install AXI ambient context into the consuming repo.

    NOTE: MCP registration is gated on `fastmcp` availability - the
    skill covers the CLI as well as the MCP surface, so it is not.

    NOTE: The `AGENTS.md` entry reports a *removal*. The block is no
    longer written; a copy left by an earlier version is stripped, so
    True there means the file shrank rather than grew.

    Args:
        root: The consuming repo root path.
        skill: Whether to install the Claude Code Skill.

    Returns:
        A mapping of which artifacts were created, modified or removed:
        `AGENTS.md`, `.vscode`, `.mcp.json` and `SKILL.md` - the last of
        which is always present, but True only when the skill file was
        written.

    Raises:
        AmbientContextError: If any artifact cannot be read, created or
            written because of an `OSError`.
    """
    available = mcp_available()
    return {
        "AGENTS.md": strip_agents_md(root),
        ".vscode": _update_mcp_json(
            root / ".vscode" / "mcp.json", "servers", available
        ),
        ".mcp.json": _update_mcp_json(
            root / ".mcp.json", "mcpServers", available
        ),
        "SKILL.md": install_skill(root) if skill else False,
    }
