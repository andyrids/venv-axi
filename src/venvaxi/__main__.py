"""Main entry point for the `venvaxi` CLI."""

import argparse
import logging
import sys
from typing import NoReturn

from venvaxi import _core, exceptions
from venvaxi._cli import add_subparser, command_home
from venvaxi._logging import configure_cli_logging
from venvaxi._toon import format_error

logger = logging.getLogger(__package__)

__all__: list[str] = ["main"]


def main() -> NoReturn:
    """Provide the `venvaxi` CLI entrypoint.

    NOTE: The subparsers action is deliberately not `required` - a bare
    `venvaxi` invocation falls through to the home view.
    """
    description = "Agent eXperience Interface (AXI)"
    parser = argparse.ArgumentParser(prog=__package__, description=description)

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging [DEBUG]",
    )
    parser.set_defaults(func=command_home)

    subparsers = parser.add_subparsers(title="commands", dest="command")
    add_subparser(subparsers)

    args = parser.parse_args()

    # Configure logging based on verbosity
    is_verbose = args.verbose
    configure_cli_logging(logging.DEBUG if is_verbose else logging.WARNING)

    ctx = _core.CLIContext(args=args, is_verbose=is_verbose)

    try:
        exit_code = int(args.func(ctx))
    except exceptions.Error as err:
        # NOTE: The TOON block on stdout *is* the error report - logging
        # it again at error level would duplicate it on stderr, so the
        # log line is debug-only (`--verbose`).
        sys.stdout.write(f"{format_error(str(err))}\n")
        logger.debug(str(err))
        exit_code = _core.ExitCode.EX_FAILURE
    except Exception as err:
        sys.stdout.write(f"{format_error(f'Unexpected error: {err}')}\n")
        logger.exception("Unexpected error")
        exit_code = _core.ExitCode.EX_SYNTAX
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
