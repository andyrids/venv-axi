"""Minimal TOON (Token-Oriented Object Notation) encoder for `axi`.

Implements a narrow, spec-compliant subset of the TOON specification
(https://github.com/toon-format/spec), which is sufficient for flat
key-value objects and uniform tabular arrays.

NOTE: Nesting and folding have not been implemented - row/field values
must be primitives (str/int/float/bool/None/`pathlib.PurePath`) only.
"""

import math
import re
from collections.abc import Mapping, Sequence
from pathlib import PurePath
from typing import Any, Literal

from venvaxi._constants import (
    COMMA,
    DEFAULT_DELIMITER,
    ESCAPES,
    FALSE_LITERAL,
    NULL_LITERAL,
    NUMERIC_REGEX,
    TRUE_LITERAL,
    VALID_KEY_REGEX,
)

_NUMERIC_RE = re.compile(NUMERIC_REGEX)
_CONTROL_RE = re.compile(r"[\x00-\x1f]")
_STRUCTURAL_CHARS = ':"\\[]{}'
_VALID_KEY_RE = re.compile(VALID_KEY_REGEX)


def _needs_quoting(value: str, delimiter: str) -> bool:
    """Determine whether a string value must be quoted.

    Args:
        value: The raw string value.
        delimiter: The active delimiter character.

    Returns:
        True if `value` must be wrapped in double quotes.
    """
    if value == "" or value != value.strip():
        return True
    if value in (TRUE_LITERAL, FALSE_LITERAL, NULL_LITERAL):
        return True
    if _NUMERIC_RE.match(value):
        return True
    if delimiter in value or any(ch in value for ch in _STRUCTURAL_CHARS):
        return True
    if _CONTROL_RE.search(value):
        return True
    return value == "-" or value.startswith("-")


def _escape(value: str) -> str:
    """Escapes a string value for use inside TOON double quotes.

    Args:
        value: The raw string value.

    Returns:
        The escaped string, without surrounding quotes.
    """

    def match_char(ch: str) -> str:
        """Match & escape a single character for TOON."""
        match ch:
            case ch if ch in ESCAPES:
                return ESCAPES[ch]
            case _ if ord(ch) < 0x20:
                return f"\\u{ord(ch):04x}"
            case _:
                return ch

    chars = [match_char(ch) for ch in value]
    return "".join(chars)


def _reject_nested(value: Any) -> None:
    """Raise if `value` is a nested container.

    Args:
        value: The candidate field/row value.

    Raises:
        TypeError: If `value` is a `dict` or `list` - this narrow TOON
            encoder subset supports flat objects/tables only, with no
            nested YAML-style fallback.
    """
    if isinstance(value, (dict, list)):
        msg = f"Nested values are not supported: {value!r}"
        raise TypeError(msg)


def encode_primitive(value: Any, delimiter: str = DEFAULT_DELIMITER) -> str:
    """Encode a single primitive value as a TOON token.

    Args:
        value: A string, number, boolean, None, or `PurePath` value.
        delimiter: The active delimiter character, used to decide
            whether quoting is required. Defaults to `DEFAULT_DELIMITER`.

    Raises:
        TypeError: If `value` is a `dict` or `list`.

    Returns:
        The TOON-encoded token.
    """
    _reject_nested(value)
    if value is None:
        return NULL_LITERAL
    if isinstance(value, bool):
        return TRUE_LITERAL if value else FALSE_LITERAL
    if isinstance(value, float) and not math.isfinite(value):
        return NULL_LITERAL
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, PurePath):
        value = str(value)

    text = str(value)
    if _needs_quoting(text, delimiter):
        return f'"{_escape(text)}"'
    return text


def encode_key(key: str) -> str:
    """Encode an object/table field key, quoting when necessary.

    Args:
        key: The raw key string.

    Returns:
        `key` unchanged if it matches `VALID_KEY_REGEX`, else the
        quoted, escaped key.
    """
    if _VALID_KEY_RE.match(key):
        return key
    return f'"{_escape(key)}"'


def encode_object(
    fields: Mapping[str, Any], *, delimiter: str = DEFAULT_DELIMITER
) -> str:
    """Encode a flat mapping as TOON `key: value` lines.

    Args:
        fields: An ordered mapping of field names to primitive values.
        delimiter: The active delimiter character, used for value
            quoting decisions. Defaults to `DEFAULT_DELIMITER`.

    Returns:
        The TOON-encoded object, one field per line.
    """
    return "\n".join(
        f"{encode_key(key)}: {encode_primitive(value, delimiter)}"
        for key, value in fields.items()
    )


def _format_header(
    key: str,
    length: int,
    fields: Sequence[str],
    delimiter: str,
    length_marker: str | Literal[False],
) -> str:
    """Format a TOON array/table header line.

    Args:
        key: The array/table field name.
        length: The number of rows.
        fields: The ordered tabular field names (empty for a plain
            array header).
        delimiter: The active delimiter character.
        length_marker: An optional marker prefix for the length (e.g.
            `"#"`), or `False` to omit it.

    Returns:
        The formatted header line, e.g. `key[N|]{f1|f2}:`.
    """
    marker_prefix = length_marker if length_marker else ""
    fields_str = ""
    if fields:
        encoded_fields = delimiter.join(encode_key(field) for field in fields)
        fields_str = f"{{{encoded_fields}}}"
    delim_suffix = "" if delimiter == COMMA else delimiter
    length_str = f"[{marker_prefix}{length}{delim_suffix}]"
    return f"{encode_key(key)}{length_str}{fields_str}:"


def encode_table(
    key: str,
    rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
    *,
    delimiter: str = DEFAULT_DELIMITER,
    length_marker: str | Literal[False] = False,
) -> str:
    """Encode a uniform list of objects as a TOON tabular array.

    Args:
        key: The array field name.
        rows: The row objects for each item in `fields`.
        fields: The ordered field names forming the tabular header.
        delimiter: The delimiter used between header fields and row
            cells. Defaults to `DEFAULT_DELIMITER`.
        length_marker: An optional marker prefix for the row count
            (e.g. `"#"`). Defaults to `False` (omitted).

    Raises:
        TypeError: If any selected row value is a `dict` or `list`.

    Returns:
        A TOON-encoded tabular array, with a header and indented,
        delimiter-joined rows per field item.
    """
    header = _format_header(key, len(rows), fields, delimiter, length_marker)
    lines = [header]
    for row in rows:
        cells = delimiter.join(
            encode_primitive(row.get(field), delimiter) for field in fields
        )
        lines.append(f"  {cells}")
    return "\n".join(lines)


def format_help(lines: Sequence[str]) -> str:
    """Format the contextual-disclosure `help[]` footer.

    NOTE: AXI principle 9 (contextual disclosure, see `specs/principles.md`):
    concrete next-step commands are surfaced instead of a static usage
    summary.

    Args:
        lines: Concrete next-step command suggestions.

    Returns:
        A `help[N]:` block, with indented lines for each suggestion.

        ```
        help[2]:
            Run `venvaxi list` for the venv package list
            Run `venvaxi show <package>` for package info
        ```
    """
    body = "\n".join(f"  {line}" for line in lines)
    return f"help[{len(lines)}]:\n{body}"


def format_error(message: str) -> str:
    """Format a structured TOON error object and help footer.

    Args:
        message: The human-readable error message.

    Returns:
        The TOON-encoded error object, followed by a help footer.
    """
    body = encode_object({"error": True, "message": message})
    footer = format_help(["Run `venvaxi --help` for available commands"])
    return f"{body}\n{footer}"
