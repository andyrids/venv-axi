---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: [128]
pr:
---

# Plan: skill gate parser access

## Scope

`tests/test_skill_drift.py` reaches every registered subcommand parser through private argparse
API in three places: the module-level `SUBCOMMAND_PARSERS` comprehension (`PARSER._actions` and
`argparse._SubParsersAction`), `_option_strings` (`parser._actions`), and `_parser_defaults`
(`parser._actions`). The dependence is deliberate and is **not** being reversed - `specs/README.md`
Invariant 4 makes `<cli> <cmd> --help` authoritative, the parser is what `--help` renders *from*,
and there is no public argparse API that enumerates subparsers. #128 states this explicitly.

What is wrong is the failure shape. If a future argparse release moves those internals, the gate
either raises a raw `AttributeError` at collection or walks an empty set of subparsers and passes,
so a broken gate then reads the same as a healthy skill at a glance. #115 will add a 3.11-3.14
matrix, and this unit exists so that axis multiplies a gate whose failure is already legible rather
than a silent one.

**Eligibility for `express-change`.** All three conditions in `ICM/express-change/CONTEXT.md`
hold, restated with reason:

1. **No spec change is required.** How the gate reaches the parser to check it is an
   implementation choice inside the test suite, not observable behaviour of `venvaxi` itself -
   `specs/README.md` -> `## What specs cover` is invocation, inputs, outputs and failure modes of
   the tool, none of which move here. `specs/behaviors/skill-content.md` declares *what* is
   machine-checked (the Commands table, the MCP tool table, exit codes, documented queries); it
   says nothing about *how* the checker reaches the parser, so nothing there is falsified.
2. **One commit's worth**, with no new dependency and no new public surface. `tests/test_skill_drift.py`
   only: one exception class, two accessor functions, two call-site rewires, two new tests.
3. **Every Validation criterion can be evidenced within this run.** All four assert on this test
   file's own behaviour under the interpreter this run has - no CI matrix, no external service.

## Implements

Nothing in `specs/**`; this changes how a test suite reaches the parser it already depends on,
not what `venvaxi` promises a caller. `specs:` and `authors:` are both empty for that reason.

## Approach

1. Open this plan at `status: in-progress`.
2. Add `GateCannotWalkParserError` to `tests/test_skill_drift.py` - a test-local exception whose
   `__init__` builds the message (`the drift gate cannot walk the parser: <problem> (Python
   <version>)`) from `sys.version_info`, so every raise site reports the same shape without
   repeating the interpreter-version formatting.
3. Add `_actions(parser)`, wrapping `parser._actions`: raises the named error on `AttributeError`
   and on an empty result (every real parser carries at least `-h`/`--help`).
4. Add `_subcommand_parsers(parser)`, wrapping the `_SubParsersAction` walk: raises the named error
   when `argparse._SubParsersAction` is unreachable, and when the walk finds no subparsers.
5. Rewire the module-level `SUBCOMMAND_PARSERS` assignment to `_subcommand_parsers(PARSER)`, and
   `_option_strings`/`_parser_defaults` to call `_actions(parser)`, so all three original
   touchpoints go through the two new accessors.
6. Add `test_subcommand_walk_reaches_working_parsers` - a canary independent of `SKILL.md`: the
   walk is non-empty and every walked parser reports `-h`/`--help` through `_option_strings`.
7. Add `test_actions_raises_named_error_when_parser_is_unreadable` - a failure-path test passing a
   stand-in object with no `_actions` attribute, asserting the exception type and that the message
   carries the failing attribute name and the interpreter's full dotted version, not the whole
   string.
8. Add `test_subcommand_parsers_raises_named_error_when_empty` - a failure-path test passing a bare
   `argparse.ArgumentParser()` (carries `_actions` via `-h`, registers no subparsers) straight to
   the shipped, unmodified `_subcommand_parsers`, asserting the named error and its
   `no subparsers found` clause.
9. Demonstrate the canary is not vacuous on its own terms: temporarily make the walk it calls
   yield an empty mapping - bypassing the accessor's own guard, since the guard now raises before
   the canary's own assertion could - run the canary alone, capture the failure verbatim, revert
   completely, run it again and capture the pass. Record both captures in Notes as supporting
   narrative for the canary, not as criterion 2's citation - criterion 2 is evidenced by step 8's
   test, which needs no edit to the shipped file.
10. Run and capture verbatim: `pytest tests/test_skill_drift.py -v`, `pytest -q` (full suite),
    `ruff check` and `ruff format --check` (both with the repo's `--config`), and `pymarkdown scan`
    over this plan and `CHANGELOG.md`.
11. Add the `CHANGELOG.md` entry under `[Unreleased]` -> `Changed`, citing issue #128.
12. Close the plan out per `plans/README.md`.

## Validation

- [x] If the parser does not expose the actions the gate walks, then the drift gate shall raise a
      named error identifying itself and the interpreter version, rather than an `AttributeError`.
      — `tests/test_skill_drift.py::test_actions_raises_named_error_when_parser_is_unreadable`
- [x] If the subparser walk finds no registered subcommands, then the drift gate shall fail rather
      than pass on an empty set. —
      `tests/test_skill_drift.py::test_subcommand_parsers_raises_named_error_when_empty`
- [x] The drift gate shall reach every registered subcommand parser and read its help flags,
      independently of what the packaged skill documents. —
      `tests/test_skill_drift.py::test_subcommand_walk_reaches_working_parsers`
- [x] The test suite shall pass. — `.venv/Scripts/python.exe -m pytest -q`: `622 passed, 32
      deselected` (develop baseline: `619 passed, 32 deselected`)

## Risks / unknowns

- **The stand-in object in the failure-path test is untyped against `argparse.ArgumentParser`.**
  `_actions`'s parameter is annotated `argparse.ArgumentParser`; the test passes an object that
  satisfies neither structurally nor nominally. This is deliberate - the point is to exercise the
  `AttributeError` branch - and carries no risk in practice because `uv run pkgdx-typing-hook
  -p venvaxi` scopes to `src/venvaxi/`, not `tests/`, so nothing in CI type-checks this file.

## Notes

**Why the private-API dependence is kept, not removed.** `specs/README.md` Invariant 4 makes
`<cli> <cmd> --help` authoritative for invocation - the parser is the object `--help` renders
*from*. The only alternative reading available is scraping rendered `--help` text, and that is the
reading that breaks on an argparse formatting change rather than a genuine behaviour change - it
would report a cosmetic diff as skill drift. There is no public argparse API that enumerates a
built parser's actions or its registered subparsers, so `_actions` and
`argparse._SubParsersAction` are the only route to the authoritative object. #128 states this
explicitly and does not ask for it to be reversed; this plan does not attempt to.

**Red-then-green capture, supporting narrative for the canary - not criterion 2's citation.**
Criterion 2 is evidenced by the permanent
`test_subcommand_parsers_raises_named_error_when_empty`, which needs no edit to the shipped file:
a bare `argparse.ArgumentParser()` carries `_actions` (every parser does, for `-h`) but registers
no subparsers, so it lands on `_subcommand_parsers`'s own empty-result branch unmodified, and the
named error is asserted there.

What the capture below evidences instead is that the canary,
`test_subcommand_walk_reaches_working_parsers`, is not vacuous *on its own terms*: its own
`assert subparsers` is capable of catching an empty walk, not merely inheriting a pass from the
accessor's guard underneath it. Since
that guard now raises before the canary could ever see an empty dict, showing the canary's own
assertion fire required exercising it directly: the canary's `_subcommand_parsers(PARSER)` call was
temporarily replaced with `_subcommand_parsers(argparse.ArgumentParser())`, and the guard's own
`if not found: raise ...` in `_subcommand_parsers` was temporarily commented out, so the empty
result reached the canary's own `assert subparsers` rather than being caught one layer down. Both
edits were reverted immediately after the capture below and confirmed identical to the pre-edit
file with `diff` - this narrative is not a re-runnable citation and is not cited as one.

RED:

```text
tests/test_skill_drift.py::test_subcommand_walk_reaches_working_parsers FAILED [100%]
    subparsers = _subcommand_parsers(
        argparse.ArgumentParser()  # TEMP RED-DEMO: no subcommands added
    )
>   assert subparsers
E   assert {}
tests\test_skill_drift.py:461: AssertionError
1 failed in 0.13s
```

GREEN:

```text
tests/test_skill_drift.py::test_subcommand_walk_reaches_working_parsers PASSED [100%]
1 passed in 0.08s
```

**Sequenced before #115.** #115 asks for the declared 3.11-3.14 interpreter range to be exercised
in CI. That is where a difference in argparse's private internals would first surface in practice;
this unit exists so that when it does, the failure names itself and the interpreter version
instead of reading as an opaque collection error or a silent empty pass. Landing this first means
the #115 matrix multiplies a gate whose failure mode is already legible.

## Follow-ups

- **Issue** [#115](https://github.com/andyrids/venv-axi/issues/115) - the downstream unit that
  exercises this gate, and the private-API dependence it wraps, across the declared 3.11-3.14
  interpreter range. This plan does not run that matrix; #115 owns it.
- **Deferred to** - none.
- **Tracked as** - none.
