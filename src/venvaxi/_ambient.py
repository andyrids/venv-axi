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
from pathlib import Path
from typing import Any

logger = logging.getLogger(__package__)

_BEGIN = "<!-- venvaxi:begin -->"
_END = "<!-- venvaxi:end -->"

# NOTE: Pre-extraction (`pkgdx axi`) markers - migrated on setup
_OLD_BEGIN = "<!-- pkgdx:axi:begin -->"
_OLD_END = "<!-- pkgdx:axi:end -->"

_BLOCK_BODY = """
## AXI

`venvaxi` reports the **installed truth** about this repo's
dependencies - the exact signatures present in this venv, at the exact
versions pinned here. Prefer it over recalling an API from memory:
memory drifts from the installed version, `axi` cannot.

It does not read the codebase of a consuming repo or need to - scan the
codebase with your tools and use any findings to drive `axi`:

1. Scan - locate the import and call sites of the dependency symbol
   you are working on with your own file-search tools. This gives you a
   bare symbol name (`Console.print`) and its owning package (`rich`).
2. Resolve - `venvaxi find Console.print --package rich` turns
   that bare name into a qualified one (`rich.console::Console.print`),
   indexing the package if needed.
3. Inspect - `venvaxi inspect rich.console::Console.print` returns
   the real signature and docstring for the installed version.

Docstrings are truncated to a first line by default; add `--docstring`
for complete bodies. Add `--refresh` to any query to rebuild a stale
graph after changing a dependency version (`find` requires `--package`
alongside `--refresh`).

`axi` reports what a symbol *is*, not how to use it - for guides,
examples and migration notes, reach for documentation instead.

Other commands:

- `venvaxi` - live status and next-step hints.
- `venvaxi list [--all]` - declared, installed dependencies.
- `venvaxi show <package> [--api]` - metadata, or public API symbols.
- `venvaxi tree <package> [--max-depth N]` - nested module tree.
- `venvaxi inspect <module>` - a module's direct children.
- `venvaxi inherits <qualified_name>` - direct subclasses.
- `venvaxi serve` - the same tools over MCP (stdio).
- `venvaxi setup` - re-register MCP config and refresh this block.

"""


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

    NOTE: A pre-extraction `pkgdx:axi` block is tool-owned content - it
    is sliced out first, so migrating repos neither keep a stale
    duplicate nor drift.

    Args:
        root: The consuming repo's root path.

    Returns:
        True if `AGENTS.md` was created or modified.
    """
    path = root / "AGENTS.md"
    block = f"{_BEGIN}\n{_BLOCK_BODY}\n{_END}"

    if not path.exists():
        _atomic_write_text(path, f"{block}\n")
        logger.debug("Created `AGENTS.md` with axi block")
        return True

    original = path.read_text(encoding="utf-8")
    text = original
    if _OLD_BEGIN in text and _OLD_END in text:
        start = text.index(_OLD_BEGIN)
        end = text.index(_OLD_END) + len(_OLD_END)
        text = text[:start] + text[end:]

    if _BEGIN in text and _END in text:
        start = text.index(_BEGIN)
        end = text.index(_END) + len(_END)
        updated = text[:start] + block + text[end:]
    else:
        separator = "\n\n" if text and not text.endswith("\n\n") else ""
        updated = f"{text}{separator}{block}\n"

    if updated == original:
        logger.debug("`AGENTS.md` axi block is up-to-date")
        return False
    _atomic_write_text(path, updated)
    logger.debug("Updated `AGENTS.md` axi block")
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
        if servers.pop("axi", None) is None:
            return False
        _atomic_write_text(path, json.dumps(data, indent=2) + "\n")
        return True

    entry = {
        "type": "stdio",
        "command": _axi_command(),
        "args": ["serve"],
    }

    # NOTE: A pre-extraction entry's `args` (`["axi", "serve"]`) can
    # never equal the new entry's, so migration is detected for free.
    if servers.get("axi") == entry:
        return False

    servers["axi"] = entry
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
