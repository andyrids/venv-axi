---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/inspect.md
authors: []
issues: [95]
pr: 126
---

# Plan: Inspect dotted module diagnosis

## Scope

`inspect` dispatches on whether the argument contains `::`
(`src/venvaxi/_cli.py`, `command_inspect`). A fully-dotted, symbol-shaped argument therefore takes
the module path - which is the **specified** behaviour and not a mis-dispatch. What is wrong is
what the failure then says. Reproduced against this checkout at stage 01:

| Argument | Root | Message today |
| --- | --- | --- |
| `not.a.symbol` | absent | ``Package `not` is not installed in the active venv`` |
| `rich.console.Console` | resolves | ``Module `rich.console.Console` not found`` |
| `rich.nosuchmodule` | resolves | ``Module `rich.nosuchmodule` not found`` |

The first names a package the caller never typed - `not` is an artefact of taking the first
component of a name meant as a whole, and read literally it says *go install or rename `not`*. The
second is a definitive negative about a module the caller never meant, and it is
**indistinguishable from the third**, which is a genuine module miss. Both are literally true, and
both send an agent somewhere it should not go.

This is the shape [#47](https://github.com/andyrids/venv-axi/issues/47) found in `getSymbolTool`
and [#62](https://github.com/andyrids/venv-axi/issues/62) fixed there by sharpening the message
rather than widening the fallback. `specs/mcp/tools.md` Malformed qualified names reasons about
this command directly, but its contrast - the CLI falls through to a module lookup, MCP cannot -
only established that the CLI produces *an* answer instead of a bare miss. It never established
that the answer is a good one. The CLI's own fix for this class was never written
([#95](https://github.com/andyrids/venv-axi/issues/95)).

**Both failing shapes are in scope, where #95 names only the first.** The second is the commoner
one: it is what an agent produces when it drops the separator from a name it formed correctly
against an *installed* package, which is the ordinary case. Fixing only the first would close the
issue's literal reproduction and leave the case an agent actually hits.

Out of scope, each with where it went:

- **A corrected spelling.** `specs/behaviors/package-resolution.md` rules out 'did you mean'
  recovery outright, and this unit does not argue with it. The statement reports the reading the
  command applied, never the input it thinks was meant.
- **The MCP surface.** `showModuleTool` answers the same shape without the statement. Recorded in
  `specs/commands/inspect.md` Out of scope with the reason - `getSymbolTool` refuses a no-`::` name
  before any lookup, so the mistyped-symbol spelling is caught there, and `showModuleTool` is
  named for modules and reached deliberately.
- **The `::` dispatch rule itself.** Unchanged. `inspect rich.console` is ordinary, correct usage
  that must keep returning the module node, and every change here has to leave the fallback
  running.

## Implements

`specs/commands/inspect.md`, in `specs:` because this plan changes code until it conforms.
**Failure modes** gains three bullets: the statement itself, on both failure classes and only for
an argument carrying no `::` and at least one `.`; the prohibition on proposing a corrected
spelling, citing `package-resolution.md`; and the two carve-outs that must reach the old message
unchanged - a bare name, which has no dropped-separator reading, and a private submodule, which
already carries a more specific diagnosis this must not bury. **Out of scope** gains the MCP
asymmetry.

**Read at stage 01 and deliberately not amended**, recorded rather than assumed:

- `specs/behaviors/package-resolution.md` - the three-way classification stays correct. `not` is a
  possible package name that nothing provides, so `PackageNotFoundError` is the right class; this
  unit is about what the message says *on top of* a correct class. Its no-spelling-suggestion rule
  is the binding constraint on this unit and is cited, not moved.
- `specs/mcp/tools.md` - nothing in Malformed qualified names becomes false. Its claim that a
  no-`::` name "cannot fall through to a module lookup as it does on the CLI" still holds; the
  fallback still runs, it just describes itself now.
- `specs/behaviors/output-contract.md` - the failure keeps its exception class, so the TOON error
  block and `EX_FAILURE` are unchanged. No output shape moves.
- `specs/behaviors/skill-content.md` and `src/venvaxi/SKILL.md` - the Qualified-name form gotcha
  already states that a fully dotted spelling has no `::`, so `inspect` treats it as a module name
  and it fails to resolve. That stays true, so nothing is non-conformant and this spec is **not**
  in `specs:`. Deliberately not sharpened: an agent discovers the statement by reading the error it
  already receives, and editing `SKILL.md` costs a three-copy byte-parity risk for no conformance
  gain.

## Approach

1. Flip to `status: in-progress` at the start of stage 02.
2. **Write the two failing tests first.** Criteria 1 and 2 assert against behaviour that exists
   today and is wrong, so they are shown failing before the fix lands.
3. `src/venvaxi/_cli.py` - `_command_inspect_module` wraps its `show_module` call and re-raises the
   **same exception class** with the statement appended. Same class keeps the exit code and the
   TOON error block exactly as they are, so no new failure mode is introduced. Catch
   `PackageNotFoundError` and `SymbolNotFoundError` **by name** - never a broad `except Error`,
   which would wrap `InvalidArgumentError` and `PackageImportError` too.
4. The statement is appended only when the argument contains a `.` **and** is not a private
   submodule. `is_private_submodule` is already imported in `_cli.py` for `command_tree`; reuse it
   rather than re-deriving the test.
5. **`_ensure_installed`'s message is not touched.** It is emitted from one call site inside
   `_build_store_for` that `show_module`, `get_symbol`, `get_inheritors`, `get_bases`,
   `get_module_tree`, `get_public_api` and `search_symbols` all share. Rewriting it in place would
   attach the dotted-path reading to `venvaxi tree nonexistent` and `venvaxi inherits
   nonexistent::X`, where no such misreading occurred and the plain message is already correct.
6. Tests in `tests/test_cli.py`, beside the three existing `command_inspect` cases.
7. `CHANGELOG.md` entry under `Changed` - the answers were true, not wrong.

## Validation

- [x] Where the `inspect` argument carries no `::` and at least one `.`, and its top-level root is
      not installed, the `inspect` command shall state that the argument was read as a dotted
      module path and that a symbol lookup requires `module::Symbol`, and shall exit `EX_FAILURE`.
      —
      `tests/test_cli.py::test_command_inspect_module_dotted_absent_root_states_reading`
- [x] Where the `inspect` argument carries no `::` and at least one `.`, and no module is indexed
      at that path, the `inspect` command shall state that the argument was read as a dotted module
      path and that a symbol lookup requires `module::Symbol`, and shall exit `EX_FAILURE`.
      —
      `tests/test_cli.py::test_command_inspect_module_dotted_resolving_root_states_reading`
- [x] Where the `inspect` argument carries no `.`, the `inspect` command shall report the failure
      unchanged, naming no dotted-module reading.
      — `tests/test_cli.py::test_command_inspect_module_bare_name_message_unchanged`
- [x] Where the `inspect` argument names a private submodule, the `inspect` command shall emit the
      private-and-never-indexed message unchanged.
      — `tests/test_cli.py::test_command_inspect_module_private_submodule_message_unchanged`
- [x] When `inspect` is given a dotted module name that resolves, the `inspect` command shall
      return the module node and its direct children as it did before this change.
      —
      `tests/test_cli.py::test_command_inspect_module_prints_header_and_children` (pre-existing,
      unaffected by the new `try`/`except`, whose mocked `show_module` never raises)
- [x] When `inspect` is given a name containing `::`, the `inspect` command shall behave as it did
      before this change, on both a resolving name and a missing one.
      — `tests/test_cli.py::test_command_inspect_prints_symbol_detail` and
      `tests/test_cli.py::test_command_inspect_propagates_not_found` (pre-existing; the `::`
      dispatch never reaches `_command_inspect_module`)
- [x] The `inspect` command shall propose no corrected spelling of the caller's argument.
      — `tests/test_cli.py::test_command_inspect_module_reading_proposes_no_spelling`
- [x] When `tree`, `inherits`, `find` or `show` is given a name whose top-level root is not
      installed, each command shall emit the package-not-found message unchanged.
      —
      `tests/test_cli.py::test_absent_root_ensure_installed_message_reaches_a_non_inspect_command`
      (the real, unmocked `_ensure_installed` path via `tree`, proven discriminating by the
      criterion-8 mutation trial in the stage 03 report) and
      `tests/test_cli.py::test_absent_root_other_commands_do_not_wrap_handed_exception`
- [x] If the `inspect` argument's top-level root is not a possible package name, then the `inspect`
      command shall raise `InvalidArgumentError` with its message unchanged.
      — `tests/test_cli.py::test_command_inspect_module_malformed_root_unchanged`, and live:
      `venvaxi inspect .bad.thing` and `venvaxi inspect "bad!.thing"` both unchanged
- [x] The MCP tools shall return the same answers as before this change.
      — `uv run pytest tests/test_mcp.py -v` — `94 passed`; `src/venvaxi/_mcp.py` untouched by
      this unit's commits (`git show 6e1d896 --stat`, `git show d95909f --stat`)
- [x] The test suite and the conformance tier shall pass.
      — `uv run coverage run -m pytest` — `558 passed, 21 deselected`; `uv run pytest -m
      conformance -v` — `21 passed, 558 deselected`

## Risks / unknowns

- **Rewriting the shared message is the obvious wrong fix.** It is one string, it looks like the
  natural place, and it would pass every `inspect` test written for this unit while corrupting the
  errors of four other commands. #95 names this trap explicitly. Validation criterion 8 is the only
  thing standing in front of it, and it must exercise the *other* commands rather than `inspect`.
- **The statement must not drift into a spelling suggestion.** Naming `module::Symbol` as the
  required form is a statement about the command's own contract; naming `rich.console::Console` as
  what the caller probably meant is the recovery `package-resolution.md` forbids. The line is
  report-what-happened versus guess-what-was-meant, and it is easy to cross while making the
  message more helpful.
- **A genuine module miss now carries the same statement.** `inspect rich.nosuchmodule` is a real
  module that does not exist, and it will say the argument was read as a dotted module path -
  because it was. Accepted and correct: the command cannot distinguish it from a dropped separator,
  and saying so is honest. Any attempt to discriminate - a capitalised last segment, a known
  module prefix - would be a guess about intent wearing a heuristic's clothes.
- **Two exception classes, one conditional, two carve-outs.** The conditional has more ways to be
  wrong than the fix has lines. Criteria 3, 4 and 9 each name an input that must reach the old
  message, and they are the guard rails rather than nice-to-haves.

## Notes

- **Why both failure shapes were taken when #95 named only one.** The issue's own reproduction
  (`not.a.symbol`) needs the top-level root absent, naming a package the caller never typed
  (`not`, an artefact of splitting on `.`). The commoner shape an agent actually hits is the
  other one: a name formed correctly against an *installed* package with the `::` dropped,
  giving a bare module-not-found answer indistinguishable from a genuine module miss (`inspect
  rich.nosuchmodule`). Both are literally
  true and both send an agent somewhere it never asked to go. Fixing only the issue's literal
  reproduction would have closed #95 on paper and left the case an agent forms by mistake, not by
  reading the issue, unaddressed.
- **Why the fix lives in the CLI and not in `_ensure_installed`.** `_ensure_installed`
  (`src/venvaxi/_introspect.py`) builds its message at one call site inside `_build_store_for`,
  shared by `show_module`, `get_symbol`, `get_inheritors`, `get_bases`, `get_module_tree`,
  `get_public_api` and `search_symbols`. Editing that string in place is the obvious wrong fix
  the plan's Risks section names: it would attach the dotted-path reading to `venvaxi tree
  nonexistent` and `venvaxi inherits nonexistent::X`, where no misreading of a `::`-carrying or
  bare argument ever occurred. The guard instead wraps only `_command_inspect_module`'s call to
  `show_module`, catching `PackageNotFoundError` and `SymbolNotFoundError` by name and re-raising
  the same class with the message extended - the other six callers of the shared message are
  never touched.
- **The stage 02 correction, and what it teaches.** The first criterion-8 test
  (`test_absent_root_message_unchanged_on_other_commands`, as originally written) mocked each
  command's own introspect entry point (`get_module_tree`, `get_inheritors`, `find_symbol`,
  `resolve_package`) with `side_effect`. That proves a real but different property - the CLI
  commands do not wrap an exception handed to them - but the call never reaches
  `_ensure_installed`, so editing that shared message in place would not be caught. The suite
  stayed green at `557 passed` with the message corrupted, and a live `venvaxi tree nonexistent`
  under the mutation carried the `inspect` clause it must never carry. Review caught this before
  stage 03; the fix added `test_absent_root_ensure_installed_message_reaches_a_non_inspect_command`,
  which drives `_ensure_installed` for real (no mock) via `command_tree` against a genuinely
  absent root, and proved it discriminating with the same mutation trial, repeated again
  independently at stage 03. The lesson: the guard against this unit's central risk - rewriting
  the shared message and passing every `inspect` test anyway - was itself unguarded by a mocked
  test, and only a mutation run surfaced that. A green suite asserts the assertions written down
  still hold; it does not by itself prove a test can fail for the reason it was written to catch.
- **No corrected spelling.** The appended statement names `module::Symbol` as the required form -
  a fact about `inspect`'s own contract, true for every caller regardless of what they typed.
  Naming a rewritten form of the caller's specific argument (`rich.console::Console` as "did you
  mean") would be the 'did you mean' recovery `specs/behaviors/package-resolution.md` forbids
  outright: a guess about intent instead of a report of what happened. Criterion 7's test
  (`test_command_inspect_module_reading_proposes_no_spelling`) asserts the specific rewritten
  spelling is absent, not merely that some help text is present, so the distinction is tested,
  not just documented.
- **Why the private-submodule and bare-name carve-outs exist.** A bare name (`inspect
  nonexistent`) has no `.` in it and therefore no dropped-separator reading to describe -
  appending the statement would assert a reading that was never applied. A private submodule
  (`inspect rich._loop`) already carries a more specific diagnosis - "private and never indexed"
  - that pre-dates this unit and pins down exactly why the lookup failed; burying it under the
  generic dotted-path statement would replace a precise answer with a vaguer one covering the
  same ground. Both carve-outs are guarded by `is_private_submodule` (reused from
  `command_tree`, not re-derived) and the `"." in name` check, verified unchanged by criteria 3
  and 4.

## Follow-ups

- **Issue** - None filed. Two candidates were considered at this closeout and neither is
  actionable-but-unowned:
  - The `1bad.thing` example in criterion 9's test
    (`test_command_inspect_module_malformed_root_unchanged`). Stage 03 found that `1bad` is not
    actually malformed - `_VALID_NAME_RE` permits a leading digit, so live it takes the
    `PackageNotFoundError` path with the dotted-path statement appended, not
    `InvalidArgumentError` unchanged as the test's name suggests. The test still correctly
    asserts what it is written to assert, because it mocks `show_module` to raise
    `InvalidArgumentError` directly rather than relying on `1bad.thing` reaching that exception
    through the real validation regex - so this is a misleading example in a working test, not a
    coverage hole. Genuinely malformed roots (`.bad.thing`, `bad!.thing`) were verified live at
    stage 03 and criterion 9 holds on the real code path. Renaming the test's fixture value to a
    genuinely malformed root is a one-line, zero-risk cleanup, but this stage does not edit
    tests, and the mislabelling is now recorded here and in the stage 03 report for whoever next
    touches this test.
  - The `showModuleTool` asymmetry - `showModuleTool` answers a module-mode miss without the
    dotted-path statement `inspect` now carries. This is not a new finding: it is already
    recorded, with its reason, in `specs/commands/inspect.md` Out of scope ("Filed if the shape
    turns up against it in use"), which is the durable record for a deliberately-conditional
    follow-up. Restating it as a plan Follow-up would duplicate that record without adding
    anything - the spec is where a future reader who hits the asymmetry in practice will look,
    and where the trigger for filing an issue is already stated.
- **Deferred to** - None. This unit found nothing that an unstarted downstream plan needs to
  absorb, so no downstream plan was edited at this closeout.
- **Tracked as** - None. No external dependency, upstream fix or release gates anything here.
