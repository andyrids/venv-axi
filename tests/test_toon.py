"""Unit tests for `venvaxi._toon`."""

import math
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from venvaxi._constants import COMMA
from venvaxi._toon import (
    encode_key,
    encode_object,
    encode_primitive,
    encode_table,
    format_help,
)


def test_encode_primitive_none() -> None:
    """None encodes as the `null` token."""
    assert encode_primitive(None) == "null"


def test_encode_primitive_bool() -> None:
    """Booleans encode as the `true`/`false` tokens."""
    assert encode_primitive(True) == "true"
    assert encode_primitive(False) == "false"


def test_encode_primitive_number() -> None:
    """Numbers encode as bare tokens."""
    assert encode_primitive(42) == "42"
    assert encode_primitive(3.14) == "3.14"


def test_encode_primitive_non_finite_float_is_null() -> None:
    """NaN and infinite floats encode as the `null` token."""
    assert encode_primitive(math.nan) == "null"
    assert encode_primitive(math.inf) == "null"
    assert encode_primitive(-math.inf) == "null"


def test_encode_primitive_path_encodes_as_string() -> None:
    """A `PurePath` value encodes as its platform string form, with
    backslash separators quoted and escaped like any other string."""
    assert encode_primitive(PurePosixPath("a/b/c")) == "a/b/c"
    assert encode_primitive(PureWindowsPath("a/b/c")) == '"a\\\\b\\\\c"'


def test_encode_primitive_plain_string() -> None:
    """A plain string encodes without quotes."""
    assert encode_primitive("rich") == "rich"


def test_encode_primitive_quotes_empty_string() -> None:
    """An empty string is quoted."""
    assert encode_primitive("") == '""'


def test_encode_primitive_quotes_numeric_like_string() -> None:
    """A numeric-looking string is quoted to disambiguate it."""
    assert encode_primitive("123") == '"123"'


def test_encode_primitive_quotes_reserved_words() -> None:
    """Strings matching `true`/`false`/`null` are quoted."""
    assert encode_primitive("true") == '"true"'
    assert encode_primitive("null") == '"null"'


def test_encode_primitive_quotes_active_delimiter_only() -> None:
    """Only the active delimiter character forces quoting."""
    assert encode_primitive("a|b") == '"a|b"'
    assert encode_primitive("a,b") == "a,b"
    assert encode_primitive("a,b", delimiter=COMMA) == '"a,b"'
    assert encode_primitive("a|b", delimiter=COMMA) == "a|b"


def test_encode_primitive_quotes_leading_hyphen() -> None:
    """A string starting with a hyphen is quoted."""
    assert encode_primitive("-x") == '"-x"'


def test_encode_primitive_escapes_special_chars() -> None:
    """Backslashes, quotes and newlines are escaped inside quotes."""
    assert encode_primitive('a"b\\c\nd') == '"a\\"b\\\\c\\nd"'


def test_encode_primitive_rejects_nested_dict() -> None:
    """A `dict` value raises `TypeError`."""
    with pytest.raises(TypeError, match="Nested values"):
        encode_primitive({"a": 1})


def test_encode_primitive_rejects_nested_list() -> None:
    """A `list` value raises `TypeError`."""
    with pytest.raises(TypeError, match="Nested values"):
        encode_primitive([1, 2])


def test_encode_key_plain_identifier_unchanged() -> None:
    """A valid bare identifier key is left unquoted."""
    assert encode_key("name") == "name"
    assert encode_key("qualified_name") == "qualified_name"


def test_encode_key_quotes_invalid_identifier() -> None:
    """A key with spaces/symbols is quoted."""
    assert encode_key("has space") == '"has space"'
    assert encode_key("1leading") == '"1leading"'


def test_encode_object() -> None:
    """A flat mapping encodes as one `key: value` line per field."""
    result = encode_object({"name": "rich", "version": "15.0.0"})
    assert result == "name: rich\nversion: 15.0.0"


def test_encode_object_quotes_invalid_key() -> None:
    """A field name that is not a valid bare key is quoted."""
    result = encode_object({"has space": "x"})
    assert result == '"has space": x'


def test_encode_table_default_pipe_delimiter() -> None:
    """By default, rows encode pipe-delimited with a `|` header suffix."""
    rows = [{"name": "rich", "version": "15.0.0"}]
    result = encode_table("packages", rows, ["name", "version"])
    assert result == "packages[1|]{name|version}:\n  rich|15.0.0"


def test_encode_table_comma_delimiter_has_no_suffix() -> None:
    """Explicitly requesting the comma delimiter omits the suffix marker."""
    rows = [{"name": "rich", "version": "15.0.0"}]
    result = encode_table(
        "packages", rows, ["name", "version"], delimiter=COMMA
    )
    assert result == "packages[1]{name,version}:\n  rich,15.0.0"


def test_encode_table_empty() -> None:
    """An empty row list encodes a zero-length header with no rows."""
    result = encode_table("packages", [], ["name", "version"])
    assert result == "packages[0|]{name|version}:"


def test_encode_table_length_marker() -> None:
    """A `length_marker` prefixes the row count in the header."""
    result = encode_table(
        "packages", [], ["name", "version"], length_marker="#"
    )
    assert result == "packages[#0|]{name|version}:"


def test_encode_table_rejects_nested_row_value() -> None:
    """A nested `dict`/`list` row value raises `TypeError`."""
    rows = [{"name": "rich", "meta": {"nested": True}}]
    with pytest.raises(TypeError, match="Nested values"):
        encode_table("packages", rows, ["name", "meta"])


def test_format_help() -> None:
    """The help footer numbers and indents each suggestion."""
    result = format_help(["do this", "do that"])
    assert result == "help[2]:\n  do this\n  do that"
