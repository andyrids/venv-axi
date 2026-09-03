"""Token-efficiency benchmark for `venvaxi._toon`.

Substantiates (or refutes) AXI principle 1 - see `specs/principles.md`. The
headline "~40% savings over JSON" is an external claim; these tests measure
the encoder against the payload shapes `axi` actually emits, so the README can
cite a number this repo owns.

NOTE: The measured-efficiency table in `specs/principles.md` cites this
module's fixtures by name (`PACKAGE_ROWS`, `SYMBOL_ROWS`, `SYMBOL_OBJECT`,
`TRUNCATED_SYMBOL_OBJECT`, `COMPLETE_BODY_SYMBOL_OBJECT`) - a change to
either file's figures should be checked against the other.

NOTE: Measures characters, not tokens - a stand-in that avoids a tokenizer
dependency. The two track closely for ASCII structural text and the ratio is
what matters here.
"""

import json
from typing import Any

from venvaxi._introspect import truncate
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
# large string value, where TOON has no repeated keys to amortise. The
# three fields below never vary between fixtures; only `doc` does, so the
# measured variable is isolated rather than merely conventional.
BASE_SYMBOL_FIELDS = {
    "qualified_name": "rich.console::Console.print",
    "kind": "method",
    "signature": (
        "(self, *objects: Any, sep: str = ' ', end: str = '\\n') -> None"
    ),
}


def _symbol_object(doc: str) -> dict[str, Any]:
    """Build a symbol-object fixture from the shared base fields.

    Args:
        doc: The `doc` value - the one field the three module-level
            fixtures below vary.

    Returns:
        A four-field mapping matching what `axi inspect` emits.
    """
    return {**BASE_SYMBOL_FIELDS, "doc": doc}


# Short first line: `doc` does not take the encoder's quoting branch.
# `qualified_name` and `signature` always do (see `test_object_encoding_
# saving_is_marginal`), so this is the two-quoted-value, ~10-char case.
SYMBOL_OBJECT = _symbol_object("Print to the console.")

# A first line longer than the 200-character truncation limit
# (`specs/behaviors/output-contract.md`), reduced through the same
# `truncate()` the command calls - size-hint suffix included - so the
# fixture measures the string the command would actually emit rather
# than a hand-written approximation of it. The retained portion carries
# a `:` of its own, so `doc` takes the quoting branch independently of
# the (colon-free) suffix `truncate()` appends.
_LONG_FIRST_LINE = (
    "Render the given renderables to the console: apply the active "
    "theme, word-wrap each segment to the configured width, and flush "
    "the result to the underlying file object once every argument has "
    "been formatted and joined by the separator supplied to this call."
)
TRUNCATED_SYMBOL_OBJECT = _symbol_object(truncate(_LONG_FIRST_LINE))

# A synthetic multi-paragraph body - representative in *shape* (several
# paragraphs, blank lines between them, a length in the low thousands)
# rather than a copy of any real docstring. Synthetic by design: this
# module imports only `venvaxi._toon`/`venvaxi._introspect`, both
# first-party, and depends on no installed package, so a dependency
# upgrade that reworded a paragraph cannot fail a test about the
# encoder. The embedded newlines put `doc` through the quoting branch
# the same as the truncated fixture above, which is what pins that
# newlines cost no more than any other quoted value.
_COMPLETE_BODY = (
    "Print to the console.\n\n"
    "Each positional argument is converted to its rich renderable form "
    "before being written: strings pass straight to the highlighter, "
    "other objects are pretty-printed. Arguments are joined by `sep` "
    "and the whole line is wrapped to the console's current width "
    "before it reaches the underlying file object.\n\n"
    "Keyword arguments control layout rather than content - `style` "
    "applies a single style across the whole line, `justify` overrides "
    "the console's alignment for this call only, and `overflow` picks "
    "the strategy used when a renderable does not fit the available "
    "width. `no_wrap` and `crop` disable wrapping and cropping "
    "respectively, `soft_wrap` collapses several print options into a "
    "single convenience flag.\n\n"
    "`end` is appended after the line exactly once, and defaults to a "
    "newline; passing an empty string suppresses it. `flush` forces the "
    "underlying file object to flush immediately rather than waiting "
    "for the console's own buffering to do so, which matters for "
    "processes whose output is piped and line-buffered rather than "
    "interactive.\n\n"
    "None of this changes what `_toon.encode_object` does with the "
    "resulting string - a synthetic docstring of this shape is enough "
    "to pin the claim that saving does not depend on `doc` length or "
    "paragraph count, only on whether the encoder's quoting branch is "
    "entered at all."
)
COMPLETE_BODY_SYMBOL_OBJECT = _symbol_object(_COMPLETE_BODY)


def _json_size(payload: Any) -> int:
    """Return the compact-JSON character count for `payload`."""
    return len(json.dumps(payload, separators=(",", ":")))


def _saving(toon: str, payload: Any) -> float:
    """Return the fractional character saving of `toon` over JSON."""
    json_size = _json_size(payload)
    return (json_size - len(toon)) / json_size


def _saving_chars(toon: str, payload: Any) -> int:
    """Return the absolute character saving of `toon` over JSON."""
    return _json_size(payload) - len(toon)


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

    The saving is `14 - 2 * quoted` exactly, where `quoted` counts how
    many of the four values take the encoder's quoting branch -
    `qualified_name` and `signature` always do (`::` and `:`
    respectively), so it never falls below the two-quoted case. Every
    fixture above is an emittable symbol object, so every saving below
    also falls in the 6-to-12 window `specs/principles.md` publishes.
    """
    fixtures = (
        (SYMBOL_OBJECT, 2),
        (TRUNCATED_SYMBOL_OBJECT, 3),
        (COMPLETE_BODY_SYMBOL_OBJECT, 3),
    )
    for payload, quoted in fixtures:
        saving = _saving_chars(encode_object(payload), payload)
        assert saving == 14 - 2 * quoted
        assert 6 <= saving <= 12


def test_object_saving_is_invariant_to_doc_length() -> None:
    """The absolute saving is a property of the key set, not of `doc`.

    An unquoted `doc` orders of magnitude longer than `SYMBOL_OBJECT`'s
    saves the identical number of characters; a `doc` that takes the
    quoting branch saves exactly two characters less, whatever its own
    length. Expressed as a percentage this would move with `doc` size -
    expressed as a character count, per `specs/principles.md`, it does
    not.
    """
    long_doc = ("word " * 2000).strip()
    long_variant = _symbol_object(long_doc)
    assert len(long_doc) > len(SYMBOL_OBJECT["doc"]) * 50

    base_saving = _saving_chars(encode_object(SYMBOL_OBJECT), SYMBOL_OBJECT)
    long_saving = _saving_chars(encode_object(long_variant), long_variant)
    assert long_saving == base_saving

    quoted_saving = _saving_chars(
        encode_object(TRUNCATED_SYMBOL_OBJECT), TRUNCATED_SYMBOL_OBJECT
    )
    assert quoted_saving == base_saving - 2


def test_object_quoting_branch_costs_exactly_two_chars() -> None:
    """Entering the quoting branch costs exactly two characters.

    A controlled pair of `doc` values of identical length, differing
    only in whether a space or a newline sits at one position, isolates
    the branch `_needs_quoting` takes - a newline is a control
    character, so it forces quoting regardless of anything else in the
    value. A second `doc` holding many newlines rather than one costs
    the same two characters, which is what pins that newlines are
    cost-neutral: `json.dumps` escapes `\\n` to the same two characters
    TOON does, so quoting is the only cost, paid once per value however
    many newlines it holds.
    """
    words = ["word"] * 20
    unquoted_doc = " ".join(words)
    single_newline_doc = unquoted_doc[:10] + "\n" + unquoted_doc[11:]
    many_newline_doc = "\n".join(words)
    assert (
        len(unquoted_doc) == len(single_newline_doc) == len(many_newline_doc)
    )

    unquoted = _symbol_object(unquoted_doc)
    single_newline = _symbol_object(single_newline_doc)
    many_newline = _symbol_object(many_newline_doc)

    base_saving = _saving_chars(encode_object(unquoted), unquoted)
    single_saving = _saving_chars(
        encode_object(single_newline), single_newline
    )
    many_saving = _saving_chars(encode_object(many_newline), many_newline)

    assert single_saving == base_saving - 2
    assert many_saving == base_saving - 2


def test_symbol_object_fixtures_differ_only_in_doc() -> None:
    """The three symbol-object fixtures isolate `doc` as a fact.

    Each fixture's non-`doc` fields are compared against
    `BASE_SYMBOL_FIELDS` directly, rather than trusted by convention -
    the whole point of building every fixture through `_symbol_object`
    is that this equality cannot go stale one fixture at a time.
    """
    fixtures = (
        SYMBOL_OBJECT,
        TRUNCATED_SYMBOL_OBJECT,
        COMPLETE_BODY_SYMBOL_OBJECT,
    )
    for fixture in fixtures:
        without_doc = {k: v for k, v in fixture.items() if k != "doc"}
        assert without_doc == BASE_SYMBOL_FIELDS


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
