"""Logging configuration for `venvaxi`.

NOTE: The TOON block on STDOUT *is* the CLI's report, so the single
handler is a plain stderr `StreamHandler` - logs never interleave with
structured output.
"""

import logging.config
from typing import Any

CONFIG: dict[str, Any] = {
    "version": 1,
    "incremental": False,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(levelname)s: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        }
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stderr",
        }
    },
    "loggers": {
        "venvaxi": {
            "level": "WARNING",
            "handlers": ["stderr"],
            "propagate": False,
        }
    },
}


def configure_cli_logging(level: int = logging.WARNING) -> None:
    """Configure CLI logging on the `venvaxi` logger.

    Args:
        level: The level to set on the `venvaxi` logger.
    """
    logging.config.dictConfig(CONFIG)
    logging.getLogger("venvaxi").setLevel(level)


def configure_pkg_logging() -> None:
    """Configure package logging using a `NullHandler`."""
    logging.getLogger("venvaxi").addHandler(logging.NullHandler())
