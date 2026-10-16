"""Fixture nested subpackage (depth 2)."""

import re


class Registry:
    """A class holding a module as a public member."""

    # NOTE: A module on a class is no member of it, so the walk records
    # no `Registry.codec` node (`specs/behaviors/symbol-graph.md`,
    # Module bindings; #130).
    codec = re
