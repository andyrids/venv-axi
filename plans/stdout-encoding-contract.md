---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/output-contract.md
authors: []
issues: [45]
pr: 54
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

- [x] The CLI shall write STDOUT as UTF-8 on every run, whatever encoding the stream reports.
      — `tests/test_stdout_encoding.py::test_main_reconfigures_stdout_to_utf8`, and
      `PYTHONIOENCODING=cp1252 venvaxi inspect rich.box::Box --docstring` exiting 0 with the
      complete payload where the pre-fix build exits 2
- [x] The CLI shall write STDERR as UTF-8 on every run, whatever encoding the stream reports.
      — `tests/test_stdout_encoding.py::test_main_reconfigures_stderr_to_utf8`
- [x] While STDOUT reports an encoding that cannot represent the payload, when
      `inspect <qualified_name> --docstring` runs against a symbol whose docstring contains such a
      character, the CLI shall emit the complete TOON block and exit `EX_OK`.
      — `tests/test_stdout_encoding.py::test_inspect_docstring_emits_non_cp1252_docstring`, shown
      failing against the pre-fix entry point
- [x] While STDOUT reports an encoding that cannot represent the payload, when
      `show <package> --api --docstring` runs, the CLI shall emit the complete symbol table and
      exit `EX_OK`.
      — `tests/test_stdout_encoding.py::test_show_api_docstring_emits_non_cp1252_docstring`, shown
      failing against the pre-fix entry point
- [x] If an unexpected exception is reported while STDOUT reports an encoding that cannot
      represent the message, then the CLI shall emit the TOON error block and exit `EX_SYNTAX`.
      — `tests/test_stdout_encoding.py::test_unexpected_error_survives_non_cp1252_message`, whose
      pre-fix failure raises `UnicodeEncodeError` from inside the `except Exception` handler

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

**Why the stream rather than `_emit()`.** The obvious fix is to harden the one function that
writes TOON, and it is the wrong one. `main()` renders its own error blocks with a bare
`sys.stdout.write`, outside `_emit` entirely, so an exception whose message carried a
non-encodable character would fault inside the handler that exists to report faults. Verification
demonstrated exactly that: the fifth criterion's pre-fix failure raises `UnicodeEncodeError` from
within the `except Exception` clause. Fixing the stream covers both writers and the 40 `_emit`
call sites at once, and leaves the payload untouched - nine commands captured pre- and post-fix on
a UTF-8 stream are byte-identical, exit codes included.

**The techspec's reasoning for omitting `errors=` was wrong; the decision was right.** It asserted
that 'under UTF-8 an error handler can never fire'. That is not strictly true - a lone surrogate
smuggled into a docstring would still raise. The omission stands on YAGNI regardless, because no
`errors=` value produces a better outcome: `surrogatepass` would emit invalid UTF-8, and
`backslashreplace` cannot fire on the path that would need it. Recorded here because the techspec
is deleted with the run's scratch, and an inaccurate rationale left on record gets inherited.

**`isinstance`, not `hasattr`.** `sys.stdout` is typed `TextIO` and `reconfigure` lives on
`TextIOWrapper`, so `isinstance` narrows for mypy without a `cast` or a `type: ignore`. It is also
the more honest guard: a stream replaced with something that is not a `TextIOWrapper` has no
reconfigure contract to rely on, and skipping it silently is correct.

**The guarantee is bounded, and the wording is deliberately broader.** The two 'on every run'
criteria read unconditionally while the implementation is guarded. They agree for every observable
CLI invocation, because a CLI process's `sys.stdout` is a `TextIOWrapper` whether attached to a
console, a pipe or a redirect - which is the subject the spec names, 'the ambient console or pipe'.
An in-process harness substituting some other object is not a CLI invocation. Stage 03 reported
this as a bound rather than a divergence, so the decision to leave it is on the record rather than
tacit.

**A test-harness deviation that would otherwise have shipped a vacuous suite.** The techspec
directed `mock.patch("sys.stdout", TextIOWrapper(BytesIO(), encoding="cp1252"))`. Under pytest's
default fd-level capture, `sys.stdout` is re-asserted to pytest's own `EncodedFile` while the
fixture package is imported, so the patched stream receives **0 bytes** - proved in verification
with a throwaway probe: 0 bytes under default capture, 291 under `--capture=no`. Tests written
that way fail identically with and against the fix, which is the failure mode
`reference-toolchain-pytest.md` warns about in its own words: a regression test that passes both
before and after the fix asserts nothing. The tests instead reconfigure `capsys`'s stream, itself
a real `TextIOWrapper`, so the guard and the reconfigure are exercised on the type the CLI meets
in production.

**Every new test was shown failing pre-fix, twice.** Once by the implementation stage, once
independently in verification by reverting `src/venvaxi/__main__.py` to develop's version. CI runs
`ubuntu-latest` only, so this defect cannot reproduce there naturally and an unsimulated test
would have passed on CI whether or not the fix worked.

**Operational gotcha.** A running `venvaxi.exe` MCP server process holds the console-script shim
and blocks `uv run`'s environment sync on Windows. It has to be stopped before the gate can run,
and respawns on next MCP use. Nothing about this change causes it; it will recur for any
contributor with the MCP server registered.

## Follow-ups

- **Issue [#52](https://github.com/andyrids/venv-axi/issues/52)** - the packaged skill carries a
  gotcha describing this crash and the `PYTHONIOENCODING=utf-8` workaround, added from the same
  evaluation. It should be dropped once this merges, and the skill's claim that errors carry exit
  code `1` 'common to every command' corrected in the same edit - an unexpected exception exits
  `2`, which this plan's fifth criterion exercises directly.
- **Tracked as** - `venvaxi serve` inherits no encoding fix from this change and needs none, since
  the MCP SDK wraps its own UTF-8 stream. Confirmed live at closeout rather than owned by a plan;
  if the SDK ever stops doing so, the served stream becomes an unfixed instance of this defect.
