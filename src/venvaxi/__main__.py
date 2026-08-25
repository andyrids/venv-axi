"""Main entry point for the `venvaxi` CLI."""

import argparse
import io
import logging
import sys
from typing import Any, NoReturn

import venvaxi
from venvaxi import _cli, _core, exceptions
from venvaxi._logging import configure_cli_logging
from venvaxi._toon import encode_object, format_error

logger = logging.getLogger(__package__)

__all__: list[str] = ["main"]

# NOTE: CLI spelling, so it lives here rather than in `_toon.py` - the
# formatter is surface-neutral and each surface supplies its own footer
# (`specs/behaviors/output-contract.md`, Error shape).
CLI_ERROR_HINT = "Run `venvaxi --help` for available commands"


class _VersionAction(argparse.Action):
    """Emit `venvaxi`'s version as a TOON line and exit `EX_OK`.

    NOTE: Not argparse's built-in `action="version"` - that prints a bare
    string outside venvaxi's own TOON path, diverging from the
    unconditional output contract on arrival
    (`specs/behaviors/output-contract.md`).
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        """Write the `version:` TOON line and exit `EX_OK`.

        Args:
            parser: The parser this action is registered on.
            namespace: The namespace being populated (unused; `--version`
                short-circuits before any other value is consumed).
            values: The parsed value(s) for this action (unused; `nargs=0`).
            option_string: The option string that triggered this action.

        Returns:
            None - `parser.exit()` raises `SystemExit` before this
            returns.
        """
        version = venvaxi.__version__ or "(no version metadata)"
        sys.stdout.write(f"{encode_object({'version': version})}\n")
        parser.exit(status=_core.ExitCode.EX_OK)


def main() -> NoReturn:
    """Provide the `venvaxi` CLI entrypoint.

    NOTE: The subparsers action is deliberately not `required` - a bare
    `venvaxi` invocation falls through to the home view.
    """
    # NOTE: The payload's character set is the dependency's business - a
    # docstring can carry anything its author wrote - so the stream is moved
    # to UTF-8 rather than the payload being degraded to fit an ambient
    # encoding that is an accident of the caller's shell.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")

    description = "Agent eXperience Interface (AXI)"
    parser = argparse.ArgumentParser(prog=__package__, description=description)

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging [DEBUG]",
    )
    parser.add_argument(
        "--version",
        action=_VersionAction,
        nargs=0,
        help="Show the installed venvaxi version and exit",
    )
    # NOTE: Attribute access (not a module-level `from ... import`) so the
    # bare-invocation default resolves at call time, like every other
    # command registered by `add_subparser`.
    parser.set_defaults(func=_cli.command_home)

    subparsers = parser.add_subparsers(title="commands", dest="command")
    _cli.add_subparser(subparsers)

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
        report = format_error(str(err), hints=[CLI_ERROR_HINT])
        sys.stdout.write(f"{report}\n")
        logger.debug(str(err))
        exit_code = _core.ExitCode.EX_FAILURE
    except (KeyboardInterrupt, SystemExit):
        # NOTE: Neither is a report about the venv - the first is the
        # caller aborting, the second venvaxi itself exiting. A
        # third-party `SystemExit` never reaches here: import
        # boundaries contain it (`specs/behaviors/output-contract.md`).
        raise
    except BaseException as err:
        # NOTE: `BaseException` - a dependency can raise anything at
        # import time, and `except Exception` let `_pytest.outcomes.
        # Skipped` escape as a traceback with a foreign exit (#64).
        report = format_error(
            f"Unexpected error: {err}", hints=[CLI_ERROR_HINT]
        )
        sys.stdout.write(f"{report}\n")
        logger.exception("Unexpected error")
        exit_code = _core.ExitCode.EX_SYNTAX
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
