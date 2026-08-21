"""A package fixture submodule raising `SystemExit` on import.

NOTE: Third-party `SystemExit` at import time is contained at the
import boundary, never treated as venvaxi exiting (#64).
"""

raise SystemExit(3)
