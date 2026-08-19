"""Unit tests for packaged/installed `SKILL.md` parity.

`specs/commands/setup.md` declares the installed skill a byte-for-byte
copy of the packaged skill. The repo's own copy at
`.claude/skills/venvaxi/SKILL.md` is generated output (`just skill-sync`),
so any hand-edit or missed regeneration is drift these tests catch.
"""

import difflib
from pathlib import Path

from venvaxi._ambient import install_skill, skill_markdown

REPO_ROOT = Path(__file__).parents[1]
INSTALLED = REPO_ROOT / ".claude" / "skills" / "venvaxi" / "SKILL.md"


def test_installed_skill_matches_packaged() -> None:
    """The repo copy is byte-for-byte the packaged skill."""
    packaged = skill_markdown.read_bytes()
    installed = INSTALLED.read_bytes()
    if installed == packaged:
        return
    diff = "\n".join(
        difflib.unified_diff(
            packaged.decode("utf-8").splitlines(),
            installed.decode("utf-8").splitlines(),
            fromfile="src/venvaxi/SKILL.md",
            tofile=".claude/skills/venvaxi/SKILL.md",
            lineterm="",
        )
    )
    msg = (
        "Skill copies differ - edit `src/venvaxi/SKILL.md` and run"
        f" `just skill-sync`:\n{diff or '(line endings only)'}"
    )
    raise AssertionError(msg)


def test_install_skill_is_noop_against_repo_copy(tmp_path: Path) -> None:
    """The real installer reports no change against the repo copy."""
    path = tmp_path / ".claude" / "skills" / "venvaxi" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(INSTALLED.read_bytes())
    assert install_skill(tmp_path) is False


def test_no_lowercase_skill_md_path() -> None:
    """Neither copy names a lowercase `src/venvaxi/skill.md` path.

    NOTE: The packaged source binds `SKILL.md` (`_ambient.py`); the
    lowercase spelling was a real documentation bug in the repo copy.
    """
    assert "src/venvaxi/skill.md" not in skill_markdown.read_text(
        encoding="utf-8"
    )
    assert "src/venvaxi/skill.md" not in INSTALLED.read_text(encoding="utf-8")
