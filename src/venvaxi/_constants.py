"""Constants for the Token-Orientated Object Notation (TOON) encoder.

NOTE: This file is a trimmed, encode-only subset of the official
`toon-format/toon-python` encoding/decoding constants (`constants.py`).

Attribution:
    The regex patterns, structural tokens and constant-extraction patterns in
    this file are directly adapted from the official `toon-python` reference
    implementation.

    Repository: https://github.com/toon-format/toon-python
    License: MIT License - Copyright (c) 2025 TOON Format Organization
"""

COMMA = ","
PIPE = "|"
TAB = "\t"

DELIMITERS = {"comma": COMMA, "tab": TAB, "pipe": PIPE}
DEFAULT_DELIMITER = PIPE

NULL_LITERAL = "null"
TRUE_LITERAL = "true"
FALSE_LITERAL = "false"

NUMERIC_REGEX = r"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$"
VALID_KEY_REGEX = r"^[A-Za-z_][\w.]*$"

ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}
