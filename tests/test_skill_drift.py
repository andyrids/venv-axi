"""Drift gate: the packaged skill's checkable claims vs. the code.

`tests/test_skill_parity.py` pins the two `SKILL.md` copies to each
other; both go stale together, byte-identical and green. This module
diffs the packaged skill against the thing it describes.

`specs/behaviors/skill-content.md` (What is machine-checked) declares
what is in reach: the Commands table's flags and defaults, that table's
completeness against each command's real flags, the MCP tool table
against the registered signatures, the exit codes against
[Output contract](../specs/behaviors/output-contract.md), and a
documented query run against the venv the project installs for itself.
A claim naming no flag, no exit code, no MCP tool and no runnable query
is declared residue there and is not reached from here (#39).

Two tiers:

- **Tier 1** (default) introspects `build_parser()` and `_mcp._TOOLS`.
  It needs no third-party package, so it runs on every `pytest`.
- **Tier 2** (`pytest.mark.conformance`) executes the documented
  queries against real `rich` and `polars`, the same reasoning
  `plans/real-dependency-conformance.md` sets out for that tier.

NOTE: A failure names the skill claim first and the code fact second,
so the reader knows which side to change without opening both files.

NOTE: Every parse here raises rather than yielding an empty result. A
table parser silently matching zero rows passes each assertion below
vacuously, which is why the row-count tests are tests and not an
implementation detail (`plans/skill-drift-gate.md`, Risks).
"""

import argparse
import bisect
import contextlib
import inspect
import io
import re
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

from venvaxi.__main__ import build_parser
from venvaxi._ambient import skill_markdown
from venvaxi._core import CLIContext, ExitCode
from venvaxi._mcp import _TOOLS, camel_case

SKILL_TEXT = skill_markdown.read_text(encoding="utf-8")

PARSER = build_parser()

SUBCOMMAND_PARSERS: dict[str, argparse.ArgumentParser] = {
    name: subparser
    for action in PARSER._actions
    if isinstance(action, argparse._SubParsersAction)
    for name, subparser in action.choices.items()
}
"""Every registered subcommand, keyed by the name argparse dispatches on.

NOTE: The real parser object - the one `--help` renders from - not a
reconstruction of it. `plans/skill-drift-gate.md` (Out of scope)
rejected scraping `--help` text for the same reason: this is the
authority that does not move when argparse changes its formatting.
"""

GLOBAL_OPTION_STRINGS = frozenset({"-v", "--verbose", "--version"})
"""Flags the skill documents in prose rather than in the Commands table.

NOTE: An explicit name list, never a heuristic over the top-level
parser. A heuristic would silently absorb a third global the table then
never documents, which is the completeness direction failing open
(`specs/behaviors/skill-content.md`, What is machine-checked).
"""

HELP_OPTION_STRINGS = frozenset({"-h", "--help"})
"""argparse's own flag: on every parser, in no table row."""

EXIT_CODE_HEADING = "Output contract, common to every command:"
"""The line the skill's exit-code prose opens with."""

ARGPARSE_CARVE_OUT = (
    "Argparse rejecting an unknown flag or a missing positional prints"
    " usage to **stderr** and no TOON at all"
)
"""The carve-out `specs/behaviors/output-contract.md` states under its
exit-code table.

NOTE: A literal substring, in the style of
`test_skill_parity.py::test_no_bases_two_cause_claim`. The exit-code
paragraph was wrong three times inside one run (#58) and this clause is
the part of it a set-equality check cannot see: argparse's own status
is not a `venvaxi.ExitCode` value.
"""

_SEPARATOR_ROW = re.compile(r"[\s|:-]+")
_FLAG_SPAN = re.compile(r"`(--?[\w-]+)`(?:\s*\(`([^`]*)`\))?")
_PARAMETER_SPAN = re.compile(r"`(\w+)(?:=([^`]+))?`")
_BACKTICK_SPAN = re.compile(r"`([^`]*)`")
_PROSE_COUNT_SPAN = re.compile(r"`?count:\s*(\d+)`?")
_TOON_TABLE_HEADER = re.compile(r"^\w+\[\d+\|?\]\{[^}]*\}:$")
_TOON_COUNT_LINE = re.compile(r"^count: (\d+)$", re.MULTILINE)


def _section_lines(heading: str) -> list[str]:
    """Return the skill lines under a `##` heading.

    Args:
        heading: The heading text, without its leading `## `.

    Returns:
        The section body, up to the next `## ` heading.

    Raises:
        AssertionError: If the skill carries no such heading.
    """
    lines = SKILL_TEXT.splitlines()
    if f"## {heading}" not in lines:
        msg = f"SKILL.md carries no `## {heading}` section"
        raise AssertionError(msg)
    body = lines[lines.index(f"## {heading}") + 1 :]
    for offset, line in enumerate(body):
        if line.startswith("## "):
            return body[:offset]
    return body


def _table_rows(heading: str) -> list[list[str]]:
    """Return the markdown table body rows under a `##` heading.

    Args:
        heading: The heading text, without its leading `## `.

    Returns:
        One list of stripped cell strings per body row; the header and
        separator rows are dropped.

    Raises:
        AssertionError: If the section holds no table body rows.
    """
    table = [
        line.strip()
        for line in _section_lines(heading)
        if line.strip().startswith("|")
    ]
    rows = [
        [cell.strip() for cell in row.strip("|").split("|")]
        for row in table
        if not _SEPARATOR_ROW.fullmatch(row)
    ][1:]
    if not rows:
        msg = f"SKILL.md `## {heading}` parsed to zero table rows"
        raise AssertionError(msg)
    return rows


def _resolve_command(cell: str) -> tuple[str | None, list[str]]:
    """Resolve a Commands-table command cell to a subcommand.

    NOTE: A flag named in the command cell counts as named - `--api`
    appears there and nowhere else
    (`specs/behaviors/skill-content.md`, What is machine-checked).

    Args:
        cell: The row's first cell, e.g. `` `venvaxi show <pkg> --api` ``.

    Returns:
        The subcommand the row resolves to - `None` for a row naming
        only the top-level parser - and the flags the cell itself names.
    """
    tokens = cell.strip("`").split()[1:]
    command = next(
        (token for token in tokens if not token.startswith(("-", "<"))),
        None,
    )
    return command, [token for token in tokens if token.startswith("-")]


class DocumentedCommand(NamedTuple):
    """A subcommand as the skill's Commands table documents it.

    NOTE: Rows are grouped by resolved subcommand and their Flags cells
    unioned. `show` occupies two rows backed by one parser, so checking
    either row alone reports a false failure
    (`specs/behaviors/skill-content.md`, What is machine-checked).

    Attributes:
        flags: Every flag named for the command across its rows.
        defaults: The default each row states as a parenthesised code
            span, keyed by flag. A `store_true` flag states none.
    """

    flags: set[str]
    defaults: dict[str, str]


def _documented_commands() -> dict[str | None, DocumentedCommand]:
    """Parse the skill's Commands table, grouped by subcommand.

    Returns:
        Each resolved subcommand - `None` for the top-level parser -
        mapped to the union of the flags and defaults its rows state.
    """
    grouped: dict[str | None, DocumentedCommand] = {}
    for cells in _table_rows("Commands"):
        command, inline = _resolve_command(cells[0])
        entry = grouped.setdefault(command, DocumentedCommand(set(), {}))
        entry.flags.update(inline)
        for flag, default in _FLAG_SPAN.findall(cells[1]):
            entry.flags.add(flag)
            if default:
                entry.defaults[flag] = default
    return grouped


DOCUMENTED_COMMANDS = _documented_commands()
COMMAND_IDS = sorted(DOCUMENTED_COMMANDS, key=str)


def _label(command: str | None) -> str:
    """Return the command line a Commands-table row documents.

    Args:
        command: A resolved subcommand, or `None` for the top level.

    Returns:
        The command line as the skill spells it, for a failure message.
    """
    return f"venvaxi {command}" if command else "venvaxi"


def _parser_for(command: str | None) -> argparse.ArgumentParser:
    """Return the parser a Commands-table row is checked against.

    Args:
        command: A resolved subcommand, or `None` for the top level.

    Returns:
        The registered parser for that command.
    """
    if command is None:
        return PARSER
    return SUBCOMMAND_PARSERS[command]


def _option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Return every flag spelling the parser accepts.

    Args:
        parser: A top-level or subcommand parser.

    Returns:
        The union of every action's option strings, `-h`/`--help`
        included.
    """
    return {
        option
        for action in parser._actions
        for option in action.option_strings
    }


def _parser_defaults(parser: argparse.ArgumentParser) -> dict[str, str]:
    """Return each flag's own default, rendered as the table renders it.

    Args:
        parser: A top-level or subcommand parser.

    Returns:
        Every flag spelling mapped to `str()` of its action's default.
    """
    return {
        option: str(action.default)
        for action in parser._actions
        for option in action.option_strings
    }


@pytest.mark.parametrize("command", COMMAND_IDS, ids=str)
def test_documented_flag_is_accepted(command: str | None) -> None:
    """Every flag the Commands table names is accepted by the command
    it is listed against."""
    named = DOCUMENTED_COMMANDS[command].flags
    accepted = _option_strings(_parser_for(command))
    missing = sorted(named - accepted)
    assert missing == [], (
        f"SKILL.md Commands table names {missing} for"
        f" `{_label(command)}`; the parser accepts {sorted(accepted)}"
    )


@pytest.mark.parametrize("command", COMMAND_IDS, ids=str)
def test_documented_default_is_the_parser_default(
    command: str | None,
) -> None:
    """Every default the Commands table states is that command's own."""
    stated = DOCUMENTED_COMMANDS[command].defaults
    actual = _parser_defaults(_parser_for(command))
    wrong = {
        flag: (value, actual.get(flag))
        for flag, value in stated.items()
        if actual.get(flag) != value
    }
    assert wrong == {}, (
        f"SKILL.md Commands table states {wrong} for"
        f" `{_label(command)}`, as (documented, parser default)"
    )


@pytest.mark.parametrize("command", COMMAND_IDS, ids=str)
def test_every_non_global_flag_is_documented(command: str | None) -> None:
    """The completeness direction: a command accepting a non-global flag
    the Commands table does not name is drift too.

    NOTE: Naming a flag that does not exist and omitting one that does
    are different failures, and only the second survives a reader
    checking the table against the tool
    (`specs/behaviors/skill-content.md`).
    """
    named = DOCUMENTED_COMMANDS[command].flags
    accepted = _option_strings(_parser_for(command))
    accepted -= HELP_OPTION_STRINGS | GLOBAL_OPTION_STRINGS
    undocumented = sorted(accepted - named)
    assert undocumented == [], (
        f"`{_label(command)}` accepts {undocumented}; the SKILL.md"
        " Commands table names none of them"
    )


def test_commands_table_covers_every_registered_subcommand() -> None:
    """The Commands table resolves to exactly the registered
    subcommands - the anti-vacuity check.

    NOTE: A table parser matching zero rows otherwise passes every
    assertion above (`plans/skill-drift-gate.md`, Validation).
    """
    resolved = {name for name in DOCUMENTED_COMMANDS if name is not None}
    assert resolved == set(SUBCOMMAND_PARSERS)


def test_commands_table_states_at_least_one_default() -> None:
    """The default-parsing direction is not vacuous either.

    NOTE: `_FLAG_SPAN`'s optional default group makes every stated
    default silently skippable - a regex that stopped matching the
    `` `--limit` (`20`) `` spelling would leave
    `test_documented_default_is_the_parser_default` green over an empty
    mapping.
    """
    stated = sum(len(entry.defaults) for entry in DOCUMENTED_COMMANDS.values())
    assert stated > 0


class DocumentedTool(NamedTuple):
    """An MCP tool as the skill's `## MCP tools` table documents it.

    Attributes:
        name: The camelCase tool name the table's first cell carries.
        parameters: The parameter names the table states, in order.
        defaults: The default each parameter states, keyed by name.
    """

    name: str
    parameters: list[str]
    defaults: dict[str, str]


def _documented_tools() -> tuple[DocumentedTool, ...]:
    """Parse the skill's MCP tool table.

    Returns:
        One record per body row. A `none` parameters cell carries no
        code spans and yields no parameters.
    """
    tools = []
    for cells in _table_rows("MCP tools"):
        spans = _PARAMETER_SPAN.findall(cells[1])
        tools.append(
            DocumentedTool(
                name=cells[0].strip("`"),
                parameters=[name for name, _ in spans],
                defaults={name: default for name, default in spans if default},
            )
        )
    return tuple(tools)


DOCUMENTED_TOOLS = _documented_tools()

REGISTERED_TOOLS = {camel_case(fn.__name__): fn for fn in _TOOLS}
"""The registry keyed by the exact transform `build_server` applies."""


def test_mcp_tool_names_match_the_registry() -> None:
    """The table's tool names are exactly the registered names.

    NOTE: Set equality, so a tool added without a row fails as loudly
    as a row naming no tool (`specs/behaviors/skill-content.md`).
    """
    assert {tool.name for tool in DOCUMENTED_TOOLS} == set(REGISTERED_TOOLS)


def test_mcp_tool_table_row_count_matches_the_registry() -> None:
    """The MCP table parses to one row per registered tool - the
    anti-vacuity check for this table."""
    assert len(DOCUMENTED_TOOLS) == len(_TOOLS)


@pytest.mark.parametrize(
    "tool", DOCUMENTED_TOOLS, ids=[tool.name for tool in DOCUMENTED_TOOLS]
)
def test_mcp_tool_signature_matches(tool: DocumentedTool) -> None:
    """Each row's parameters and defaults are the ones the tool is
    registered with."""
    assert tool.name in REGISTERED_TOOLS
    signature = inspect.signature(REGISTERED_TOOLS[tool.name])
    assert tool.parameters == list(signature.parameters), (
        f"SKILL.md states {tool.parameters} for `{tool.name}`;"
        f" it is registered as {list(signature.parameters)}"
    )
    actual = {
        name: str(signature.parameters[name].default) for name in tool.defaults
    }
    assert tool.defaults == actual, (
        f"SKILL.md states {tool.defaults} for `{tool.name}`;"
        f" it is registered with {actual}"
    )


def _exit_code_prose() -> str:
    """Return the skill's exit-code paragraph.

    Returns:
        The slice from the `Output contract...` line to the next `##`
        heading.

    Raises:
        AssertionError: If the opening line is absent.
    """
    lines = SKILL_TEXT.splitlines()
    opening = [
        index
        for index, line in enumerate(lines)
        if line.strip() == EXIT_CODE_HEADING
    ]
    if not opening:
        msg = f"SKILL.md carries no `{EXIT_CODE_HEADING}` line"
        raise AssertionError(msg)
    body = lines[opening[0] + 1 :]
    for offset, line in enumerate(body):
        if line.startswith("## "):
            body = body[:offset]
            break
    return "\n".join(body)


EXIT_CODE_PROSE = _exit_code_prose()

NAMED_EXIT_CODES = {
    int(span)
    for span in _BACKTICK_SPAN.findall(EXIT_CODE_PROSE)
    if span.isdigit()
}
"""Every backticked span in the exit-code prose that is a bare integer.

NOTE: `` `count: 0` `` is not a bare integer and is correctly excluded -
it is the definitive empty state, not an exit code.
"""

DECLARED_EXIT_CODES: set[int] = {
    value for name, value in vars(ExitCode).items() if name.startswith("EX_")
}


def test_named_exit_codes_match_the_output_contract() -> None:
    """The skill names exactly the codes `ExitCode` declares.

    NOTE: Both directions. What recurred across the three #58 failures
    was *how many outcomes there are*, which is countable
    (`specs/behaviors/output-contract.md`, Exit codes).
    """
    assert NAMED_EXIT_CODES == DECLARED_EXIT_CODES, (
        f"SKILL.md names exit codes {sorted(NAMED_EXIT_CODES)};"
        f" `ExitCode` declares {sorted(DECLARED_EXIT_CODES)}"
    )


def test_argparse_carve_out_is_still_stated() -> None:
    """The exit-code prose still carves argparse's own status out.

    NOTE: Whitespace-collapsed before matching - the sentence wraps
    across two source lines, and a literal substring over the raw text
    would assert only that the wrap point has not moved.
    """
    collapsed = " ".join(EXIT_CODE_PROSE.split())
    assert ARGPARSE_CARVE_OUT in collapsed


def _prose() -> tuple[str, list[int], list[int]]:
    """Collapse the skill's non-fenced lines into one searchable string.

    NOTE: One collapse serves both prose checks, because both were
    defeated by the same thing: a backtick span split across a line
    wrap. `SKILL.md` wraps at 100 columns, so the split spelling is a
    routine edit rather than a contrivance - it hid a non-zero `count:`
    from the third limit's check and hid a documented query from the
    registry's completeness check, in the same file, at the same time
    (stage 03 findings D3 and D4).

    Returns:
        The collapsed text, the character offset each source line
        starts at, and those lines' 1-based numbers.
    """
    offsets: list[int] = []
    numbers: list[int] = []
    parts: list[str] = []
    cursor = 0
    fenced = False
    for number, line in enumerate(SKILL_TEXT.splitlines(), start=1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        offsets.append(cursor)
        numbers.append(number)
        parts.append(line)
        cursor += len(line) + 1
    return " ".join(parts), offsets, numbers


PROSE, _PROSE_OFFSETS, _PROSE_NUMBERS = _prose()


def _prose_line(offset: int) -> int:
    """Return the source line a collapsed-prose offset falls on.

    Args:
        offset: A character offset into `PROSE`.

    Returns:
        The 1-based line number in `SKILL.md`.
    """
    return _PROSE_NUMBERS[bisect.bisect_right(_PROSE_OFFSETS, offset) - 1]


def test_no_non_zero_result_count_in_prose() -> None:
    """No prose line states a non-zero result count.

    NOTE: Scoped twice, and both scopings are load-bearing
    (`specs/behaviors/skill-content.md`, third limit). Non-fenced lines
    only: a fenced block reproducing real output is a specimen of the
    TOON shape and keeps what it recorded. Non-zero only: `count: 0` is
    a declared empty state rather than a measurement of an installed
    version, and appears in prose eleven times legitimately.

    NOTE: Matched over the collapsed prose with the backticks optional.
    The limit the spec states is form-agnostic, and the earlier pattern
    reached only a backticked span on one line - a wrapped span and an
    unbackticked count both passed green (stage 03 findings D3).
    """
    offenders = [
        f"line {_prose_line(match.start())}: {match.group(0).strip()}"
        for match in _PROSE_COUNT_SPAN.finditer(PROSE)
        if int(match.group(1)) != 0
    ]
    assert offenders == [], (
        "SKILL.md states a non-zero result count in prose; name the"
        f" results the example teaches by instead: {offenders}"
    )


def _toon_count(out: str) -> int | None:
    """Return a collection payload's `count:` value.

    Args:
        out: A command's complete stdout.

    Returns:
        The reported count, or `None` when the payload carries no
        `count:` line.
    """
    match = _TOON_COUNT_LINE.search(out)
    return int(match.group(1)) if match else None


def _toon_rows(out: str) -> list[list[str]]:
    """Split a TOON table's data rows into unquoted cells.

    Args:
        out: A command's complete stdout.

    Returns:
        One list of cell strings per row of the payload's table, empty
        when it carries none (`count: 0`).
    """
    rows: list[list[str]] = []
    lines = out.splitlines()
    headers = [
        index
        for index, line in enumerate(lines)
        if _TOON_TABLE_HEADER.match(line)
    ]
    if not headers:
        return rows
    for line in lines[headers[0] + 1 :]:
        if not line.startswith("  ") or "|" not in line:
            break
        rows.append([cell.strip('"') for cell in line.strip().split("|")])
    return rows


def _toon_field(out: str, field: str) -> str:
    """Return a single-object payload's field value.

    Args:
        out: A command's complete stdout.
        field: The field name, as the payload spells it.

    Returns:
        The value with any wrapping quotes removed, or `""` when the
        payload carries no such field.
    """
    prefix = f"{field}: "
    for line in out.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip('"')
    return ""


def _check_find_console_print(out: str, exit_code: int) -> None:
    """Assert the bare name leads, on the class it is asked for.

    Args:
        out: The command's stdout.
        exit_code: The command's exit code.
    """
    assert exit_code == ExitCode.EX_OK
    rows = _toon_rows(out)
    assert rows, out
    assert rows[0][0] == "print"
    assert rows[0][2] == "rich.console::Console.print"
    assert {row[2].rsplit(".", 1)[0] for row in rows} == {
        "rich.console::Console"
    }


def _check_inspect_console_print(out: str, exit_code: int) -> None:
    """Assert `inspect` answers a method's real shape and its doc.

    Args:
        out: The command's stdout.
        exit_code: The command's exit code.
    """
    assert exit_code == ExitCode.EX_OK
    assert _toon_field(out, "kind") == "method"
    assert _toon_field(out, "signature").startswith("(self,")
    assert _toon_field(out, "doc")


def _check_inherits_progress_column(out: str, exit_code: int) -> None:
    """Assert the exemplar columns are reported, `count:` the rows.

    Args:
        out: The command's stdout.
        exit_code: The command's exit code.
    """
    assert exit_code == ExitCode.EX_OK
    rows = _toon_rows(out)
    taught = {
        "BarColumn",
        "SpinnerColumn",
        "TextColumn",
        "TimeRemainingColumn",
    }
    assert taught <= {row[0] for row in rows}
    assert _toon_count(out) == len(rows)


def _check_inherits_rich_handler_bases(out: str, exit_code: int) -> None:
    """Assert `--bases` reaches a base its own package never indexed.

    Args:
        out: The command's stdout.
        exit_code: The command's exit code.
    """
    assert exit_code == ExitCode.EX_OK
    assert "logging::Handler" in {row[2] for row in _toon_rows(out)}


def _check_find_dunder_is_empty(out: str, exit_code: int) -> None:
    """Assert the unindexed dunder answers empty, and succeeds.

    Args:
        out: The command's stdout.
        exit_code: The command's exit code.
    """
    assert exit_code == ExitCode.EX_OK
    assert _toon_count(out) == 0


def _check_inspect_rich_handler(out: str, exit_code: int) -> None:
    """Assert the class symbol carries the constructor signature.

    Args:
        out: The command's stdout.
        exit_code: The command's exit code.
    """
    assert exit_code == ExitCode.EX_OK
    signature = _toon_field(out, "signature")
    assert signature.startswith("(")
    assert signature[1 : signature.index(")")].strip()


def _check_find_struct_namespace(out: str, exit_code: int) -> None:
    """Assert the accessor's implementing class resolves by name.

    Args:
        out: The command's stdout.
        exit_code: The command's exit code.
    """
    assert exit_code == ExitCode.EX_OK
    classes = [
        row
        for row in _toon_rows(out)
        if row[0] == "StructNameSpace" and row[1] == "class"
    ]
    assert classes, out
    assert classes[0][2].endswith("::StructNameSpace")


def _check_show_fastmcp(out: str, exit_code: int) -> None:
    """Assert the availability probe resolves an installed package.

    NOTE: The skill offers this as the *read-only* answer to "is the
    extra installed", against running `setup` to find out. What it
    teaches is that the probe resolves and reports, raising only when
    the package is absent - so the property is a resolved name at
    `EX_OK`, not the `PackageNotFoundError` branch, which this venv
    cannot reach for a package it installs.

    Args:
        out: The command's stdout.
        exit_code: The command's exit code.
    """
    assert exit_code == ExitCode.EX_OK
    assert _toon_field(out, "name") == "fastmcp"
    assert _toon_field(out, "version")


class WorkedExample(NamedTuple):
    """A query the skill documents, with the property it teaches.

    NOTE: `check` asserts the *taught* property, never equality against
    a recorded block. A recorded `count:` is what one version of a
    dependency returns; an assertion pinned to a frozen string reports
    a dependency upgrade as skill drift
    (`specs/behaviors/skill-content.md`, first limit).

    Attributes:
        command: The command line, as the skill spells it.
        claim: The SKILL.md claim this example evidences.
        check: Asserts the taught property over the command's stdout
            and exit code; `None` for an unexecutable entry.
        unexecutable: Why the entry cannot be run here; empty for an
            executable one.
    """

    command: str
    claim: str
    check: Callable[[str, int], None] | None = None
    unexecutable: str = ""


WORKED_EXAMPLES: tuple[WorkedExample, ...] = (
    WorkedExample(
        command="venvaxi find Console.print --package rich",
        claim="Workflow (2) Resolve, and its fenced output block",
        check=_check_find_console_print,
    ),
    WorkedExample(
        command="venvaxi inspect rich.console::Console.print --docstring",
        claim="Workflow (3) Inspect, and its fenced output block",
        check=_check_inspect_console_print,
    ),
    WorkedExample(
        command="venvaxi inherits rich.progress::ProgressColumn",
        claim="Workflow (3) Inspect - the follow-up `inherits` query",
        check=_check_inherits_progress_column,
    ),
    WorkedExample(
        command="venvaxi inherits rich.logging::RichHandler --bases",
        claim="Gotchas - `inherits --bases` answers 'what does X subclass'",
        check=_check_inherits_rich_handler_bases,
    ),
    WorkedExample(
        command="venvaxi find RichHandler.__init__ --package rich",
        claim="Gotchas - dunders are not indexed",
        check=_check_find_dunder_is_empty,
    ),
    WorkedExample(
        command="venvaxi inspect rich.logging::RichHandler",
        claim="Gotchas - the constructor signature lives on the class symbol",
        check=_check_inspect_rich_handler,
    ),
    WorkedExample(
        command="venvaxi find StructNameSpace --package polars",
        claim="Gotchas - namespace accessors inspect empty",
        check=_check_find_struct_namespace,
    ),
    WorkedExample(
        command="venvaxi show fastmcp",
        claim="Gotchas - `setup` writes files, it is not a diagnostic command",
        check=_check_show_fastmcp,
    ),
    WorkedExample(
        command="venvaxi inspect numba::njit --docstring",
        claim="Gotchas - decorators introspect as passthroughs",
        unexecutable="`numba` is not installed and is not proposed for"
        " the dev group: a compiler toolchain to check one gotcha is"
        " the wrong trade (`plans/skill-drift-gate.md`, Out of scope)",
    ),
)
"""Every query the packaged skill documents together with a result.

NOTE: An explicit registry rather than queries scraped from the skill's
prose. A scraper reaches the command but not the property the example
teaches, and the property is the whole of what is asserted here.
"""

_TABLE_ROW = "Commands table row - names a purpose, not a result"

NOT_AN_EXAMPLE: dict[str, str] = {
    "venvaxi list": _TABLE_ROW,
    "venvaxi cache": _TABLE_ROW,
    "venvaxi serve": _TABLE_ROW,
    "venvaxi setup": _TABLE_ROW,
    "venvaxi inspect rich.console": "named as a follow-up query to try;"
    " the skill records no result for it",
    "venvaxi inspect pkg.api": "`pkg` is a placeholder package in the"
    " private-submodule gotcha, not one this venv installs",
}
"""Concrete invocations the skill names without documenting a result.

NOTE: The third arm of the triage. Rule 5 covers a query documented
*with* its result; these are documented without one, and the reason is
recorded rather than the invocation being silently dropped - the same
discipline `unexecutable` applies to an example the gate cannot run
(`specs/behaviors/skill-content.md`, What is machine-checked).
"""


def _documented_invocations() -> dict[str, int]:
    """Return every concrete `venvaxi` invocation the skill names.

    A span counts as concrete when the real parser accepts it: that
    rejects a bare verb (`inherits`), a spelling carrying a
    `<placeholder>`, and `--help`/`--version`, which exit rather than
    parse.

    Returns:
        Each invocation in its canonical `venvaxi ...` spelling, mapped
        to the `SKILL.md` line it is named on.
    """
    found: dict[str, int] = {}
    for match in re.finditer(r"`([^`]+)`", PROSE):
        tokens = match.group(1).split()
        if not tokens:
            continue
        if tokens[0] == "venvaxi":
            rest = tokens[1:]
        elif tokens[0] in SUBCOMMAND_PARSERS:
            rest = tokens
        else:
            continue
        spelling = " ".join(rest)
        if not rest or any(c in spelling for c in "<>[]") or "..." in spelling:
            continue
        sink = io.StringIO()
        try:
            with (
                contextlib.redirect_stderr(sink),
                contextlib.redirect_stdout(sink),
            ):
                PARSER.parse_args(rest)
        except SystemExit:
            continue
        found.setdefault(f"venvaxi {spelling}", _prose_line(match.start()))
    return found


DOCUMENTED_INVOCATIONS = _documented_invocations()


def test_every_documented_invocation_is_triaged() -> None:
    """No concrete invocation the skill names is unaccounted for.

    NOTE: The registry is the one hand-written surface in this module,
    and it was the only one with no anti-vacuity check - so an example
    added to the skill and forgotten here would have passed green,
    which is the "four examples of five" the third limit forbids
    (stage 03 finding D4). Every concrete invocation must be run,
    recorded as unexecutable, or recorded as documenting no result.
    """
    accounted = {example.command for example in WORKED_EXAMPLES}
    accounted |= set(NOT_AN_EXAMPLE)
    untriaged = sorted(
        f"line {line}: {command}"
        for command, line in DOCUMENTED_INVOCATIONS.items()
        if command not in accounted
    )
    assert untriaged == [], (
        "SKILL.md names invocations the gate neither runs nor records;"
        " add each to WORKED_EXAMPLES or to NOT_AN_EXAMPLE with a"
        f" reason: {untriaged}"
    )


def test_triage_lists_name_only_invocations_the_skill_makes() -> None:
    """The triage lists do not carry entries the skill no longer names.

    NOTE: The other direction, and the one that rots quietly - a
    registry entry for a query deleted from the skill goes on passing
    while testing nothing the skill claims.
    """
    stale = sorted(
        (set(NOT_AN_EXAMPLE) | {e.command for e in WORKED_EXAMPLES})
        - set(DOCUMENTED_INVOCATIONS)
    )
    assert stale == [], (
        f"triage lists name invocations SKILL.md does not: {stale}"
    )


EXECUTABLE_EXAMPLES = [
    example for example in WORKED_EXAMPLES if example.check is not None
]


@pytest.mark.conformance
@pytest.mark.parametrize(
    "example",
    EXECUTABLE_EXAMPLES,
    ids=[example.command for example in EXECUTABLE_EXAMPLES],
)
def test_documented_query_teaches_what_it_claims(
    isolated_cache: Path,
    capsys: pytest.CaptureFixture[str],
    example: WorkedExample,
) -> None:
    """Each documented query, run against the venv the project installs
    for itself, holds the property its example teaches.

    NOTE: Dispatched through `build_parser()` and the `_cli.command_*`
    function it resolves, with a `CLIContext` - the same in-process
    route `tests/test_conformance.py` takes. Parsing the documented
    command line rather than hand-building a `Namespace` also asserts
    the spelling in the skill is one the CLI accepts.
    """
    args = PARSER.parse_args(shlex.split(example.command)[1:])
    exit_code = int(args.func(CLIContext(args=args)))
    out = capsys.readouterr().out
    assert example.check is not None
    example.check(out, exit_code)


def test_unexecutable_example_records_why() -> None:
    """An example the gate cannot run is visible in the registry with a
    reason, rather than absent from it.

    NOTE: Tier 1, not tier 2. The registry is a plain data structure and
    reading it needs no installed dependency, so the check that the gate
    declares its own gaps must not itself be opt-in - that would leave
    the honesty guard behind the same flag as the thing it guards.

    NOTE: A check that silently covers seven examples of eight reports
    the same green as one that covers all eight
    (`specs/behaviors/skill-content.md`, third limit).
    """
    gaps = [
        example.command
        for example in WORKED_EXAMPLES
        if example.check is None and not example.unexecutable
    ]
    assert gaps == []
