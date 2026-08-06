"""Token-efficiency benchmark for `venvaxi._toon`.

Substantiates (or refutes) AXI principle 1 - see
`ICM/_config/reference-standard-axi.md`. The headline "~40% savings over
JSON" is an external claim; these tests measure the encoder against the
payload shapes `axi` actually emits, so the README can cite a number
this repo owns.

NOTE: Measures characters, not tokens - a stand-in that avoids a
tokenizer dependency. The two track closely for ASCII structural text,
and the ratio is what matters here.
"""

import json
from typing import Any

from venvaxi._toon import encode_object, encode_table

# The tabular payloads `axi list`/`find`/`tree` emit - many rows, short
# cells, where TOON amortises the repeated JSON keys across a header.
PACKAGE_ROWS = [
    {"name": "detect-secrets", "version": "1.5.0"},
    {"name": "mypy", "version": "2.3.0"},
    {"name": "prek", "version": "0.4.10"},
    {"name": "pymarkdownlnt", "version": "0.9.39"},
    {"name": "rich", "version": "15.0.0"},
    {"name": "ruff", "version": "0.16.0"},
    {"name": "tomlkit", "version": "0.15.1"},
]

SYMBOL_ROWS = [
    {
        "name": "print",
        "kind": "method",
        "qualified_name": "rich.console::Console.print",
    },
    {
        "name": "print_json",
        "kind": "method",
        "qualified_name": "rich.console::Console.print_json",
    },
    {
        "name": "rule",
        "kind": "method",
        "qualified_name": "rich.console::Console.rule",
    },
]

# The single-object payload `axi inspect <qualified_name>` emits - one
# large string value, where TOON has no repeated keys to amortise.
SYMBOL_OBJECT = {
    "qualified_name": "rich.console::Console.print",
    "kind": "method",
    "signature": (
        "(self, *objects: Any, sep: str = ' ', end: str = '\\n') -> None"
    ),
    "doc": "Print to the console.",
}


def _json_size(payload: Any) -> int:
    """Return the compact-JSON character count for `payload`."""
    return len(json.dumps(payload, separators=(",", ":")))


def _saving(toon: str, payload: Any) -> float:
    """Return the fractional character saving of `toon` over JSON."""
    json_size = _json_size(payload)
    return (json_size - len(toon)) / json_size


def test_table_encoding_beats_json_on_package_rows() -> None:
    """`axi list`-shaped output is materially smaller than JSON."""
    toon = encode_table("packages", PACKAGE_ROWS, ["name", "version"])
    assert _saving(toon, PACKAGE_ROWS) > 0.30


def test_table_encoding_beats_json_on_symbol_rows() -> None:
    """`axi find`-shaped output is smaller than JSON despite quoting.

    NOTE: Every `qualified_name` contains `::`, so every cell in that
    column is quoted - this pins the saving that survives it.
    """
    toon = encode_table(
        "symbols", SYMBOL_ROWS, ["name", "kind", "qualified_name"]
    )
    assert _saving(toon, SYMBOL_ROWS) > 0.15


def test_object_encoding_saving_is_marginal() -> None:
    """A flat object has no repeated keys for TOON to amortise.

    Guards the pitch as much as the encoder: `axi inspect` is the path
    where TOON buys least, so token efficiency there has to come from
    truncation (principle 3), not the encoding.
    """
    toon = encode_object(SYMBOL_OBJECT)
    saving = _saving(toon, SYMBOL_OBJECT)
    assert 0.0 < saving < 0.20


def test_table_saving_grows_with_row_count() -> None:
    """TOON's advantage scales with rows, since the header is paid once."""
    small = _saving(
        encode_table("packages", PACKAGE_ROWS[:2], ["name", "version"]),
        PACKAGE_ROWS[:2],
    )
    large = _saving(
        encode_table("packages", PACKAGE_ROWS, ["name", "version"]),
        PACKAGE_ROWS,
    )
    assert large > small
