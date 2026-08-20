---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/behaviors/output-contract.md
authors: []
issues: [45]
pr:
---

# Plan: STDOUT encoding contract

## Scope

`venvaxi inspect <qualified_name> --docstring` raises an unhandled `UnicodeEncodeError` and exits
`EX_SYNTAX` whenever a docstring carries a character the ambient stream encoding cannot represent.
It was found during an agent-perspective evaluation of the published `0.3.0rc1` wheel against a
consuming project, where two of eight agents hit it independently on ordinary `polars` docstrings:
`Series.rle`, whose docstring embeds a rendered DataFrame example built from box-drawing
characters, and `DateTimeNameSpace.epoch`, which uses the micro sign.

The failure is shell-dependent, and the dependency is what makes it matter. Modern CPython uses
UTF-8 for a real console and falls back to `locale.getpreferredencoding()` only when STDOUT is a
pipe, so the crashing configuration is a captured pipe on a non-UTF-8 locale - which is exactly how
an agent harness reads the CLI. Under Git Bash on Windows `sys.stdout.encoding` is `cp1252` and the
command dies; under PowerShell it is `utf-8` and the same command succeeds.

Declare the STDOUT and STDERR character encoding in `specs/behaviors/output-contract.md`, which
governs stream discipline, exit codes and error shape but has never stated an encoding, then bring
the entry point into conformance.

Out of scope: the exit code, which is correct and stays - the spec reserves `EX_SYNTAX` for venvaxi
being broken, and venvaxi is broken here. Also out of scope is every packaged-skill change the same
evaluation surfaced, which [#52](https://github.com/andyrids/venv-axi/issues/52) owns.

## Implements

`specs/behaviors/output-contract.md` Stream discipline, as amended by this plan - structured output
is written as UTF-8 whatever the ambient console or pipe reports, STDERR is held to the same rule,
and a character the ambient encoding cannot represent never turns into an `EX_SYNTAX` exit. The
same plan amends the spec and brings the code into conformance with it, which `plans/README.md`
resolves in favour of `specs:`.

The amendment also renames the `## Out of scope` entry 'Alternative encodings' to 'Alternative
payload formats'. That bullet has always meant TOON versus JSON; the new clauses give 'encoding'
a second, character-level sense in the same file, and one word carrying both is how a future
reader reads a payload-format exclusion as licence to emit cp1252.

## Approach

1. Flip to `status: in-progress`.
2. Amend `specs/behaviors/output-contract.md` per Implements, and run the ripple check in
   `specs/README.md` over the plans naming it.
3. Reconfigure STDOUT and STDERR to UTF-8 as the first statements in `main()`, before
   `parse_args()` and before `configure_cli_logging()`. The ordering is load-bearing: the logging
   `dictConfig` resolves `ext://sys.stderr` when it runs, so a later reconfigure would leave the
   `StreamHandler` bound to the original stream.
4. Add `tests/test_stdout_encoding.py`, driving `main()` with `sys.stdout` swapped for a
   `TextIOWrapper` over a `BytesIO` at `cp1252`. CI runs `ubuntu-latest` only, so the failing
   configuration has to be simulated rather than inherited from the platform, or the fix ships
   with tests that would pass equally well without it.
5. `CHANGELOG.md` entry under `Fixed`.

## Validation

- [ ] The CLI shall write STDOUT as UTF-8 on every run, whatever encoding the stream reports.
- [ ] The CLI shall write STDERR as UTF-8 on every run, whatever encoding the stream reports.
- [ ] While STDOUT reports an encoding that cannot represent the payload, when
      `inspect <qualified_name> --docstring` runs against a symbol whose docstring contains such a
      character, the CLI shall emit the complete TOON block and exit `EX_OK`.
- [ ] While STDOUT reports an encoding that cannot represent the payload, when
      `show <package> --api --docstring` runs, the CLI shall emit the complete symbol table and
      exit `EX_OK`.
- [ ] If an unexpected exception is reported while STDOUT reports an encoding that cannot
      represent the message, then the CLI shall emit the TOON error block and exit `EX_SYNTAX`.

## Risks / unknowns

- The last criterion covers a path the crash itself exposed. `main()` renders its error block with
  a bare `sys.stdout.write` too, so an `Error` whose message carried a non-encodable symbol name
  would fault inside the handler that exists to report faults.
- Callers decoding venvaxi output as cp1252 would now receive UTF-8 bytes. That is the intended
  correction and no spec promised the old behaviour, but it is a behaviour change rather than a
  pure repair.
- The change is inert under `serve`, where the MCP SDK wraps `sys.stdout.buffer` in its own UTF-8
  `TextIOWrapper` before the protocol stream starts. Verified by reading the installed
  `mcp/server/stdio.py` rather than assumed, but stage 03 should still confirm the server starts.
- Reconfiguring is guarded on the stream being a `TextIOWrapper`. A harness that replaces
  `sys.stdout` with something else keeps whatever encoding it brought, so the guarantee is
  strictly about streams the CLI can actually reconfigure.

## Notes

Populated at closeout.

## Follow-ups

Populated at closeout.
