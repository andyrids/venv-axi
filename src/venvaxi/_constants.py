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

NO_PROJECT_ROOT = "(no project root)"
"""Marker emitted when no project root resolves for the binding report.

NOTE: A `venvaxi` emission marker, not part of the adapted TOON subset
above. AXI principle 5 (definitive empty states) - it states that no
`pyproject.toml` was found from the working directory upward nor beside
the venv, which is a fact about the binding rather than a failure.
Distinct from every real path and contains no TOON structural
characters, so the encoder never has to quote it. Applied at emission
only - see `specs/mcp/tools.md`.
"""
