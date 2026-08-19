---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [logging]
---

# Toolchain - `logging`

All logging is handled through the primary package logger. To ensure logs are routed correctly,
always instantiate loggers using the package name:

```python
import logging

logger = logging.getLogger(__package__)
```

## Configuration

Logging configuration lives in `src/venvaxi/_logging.py` as a single `dictConfig` dictionary
(`CONFIG`), separated into two distinct contexts to prevent interference with consuming
applications:

### (1) Package logging (library)

By default, the package is configured with a `NullHandler`. This prevents the library from
polluting output when imported as a dependency.

- Setup: `configure_pkg_logging()` is called in `src/venvaxi/__init__.py`.

### (2) CLI logging (application)

When executed as a CLI, logging is configured from `CONFIG` - a single `logging.StreamHandler`
on STDERR, attached to the `venvaxi` logger with `propagate = false`.

- Setup: `configure_cli_logging(level)` is called in `src/venvaxi/__main__.py` after argument
parsing. The level is `DEBUG` with `--verbose`, otherwise `WARNING`.

## Why STDERR only

The TOON block written to STDOUT *is* the CLI's report. Logs MUST never interleave with it, so
there is no STDOUT handler and no rich-text console layer - a plain `StreamHandler` on STDERR is
the whole logging surface.

This is also why `__main__.main` writes a `format_error(...)` TOON block to STDOUT and only logs
the same message at `DEBUG` - logging it at `ERROR` too would duplicate the report.
