---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: planned
depends: []
specs:
  - specs/commands/inspect.md
authors: []
issues: [95]
pr:
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

- [ ] Where the `inspect` argument carries no `::` and at least one `.`, and its top-level root is
      not installed, the `inspect` command shall state that the argument was read as a dotted
      module path and that a symbol lookup requires `module::Symbol`, and shall exit `EX_FAILURE`.
- [ ] Where the `inspect` argument carries no `::` and at least one `.`, and no module is indexed
      at that path, the `inspect` command shall state that the argument was read as a dotted module
      path and that a symbol lookup requires `module::Symbol`, and shall exit `EX_FAILURE`.
- [ ] Where the `inspect` argument carries no `.`, the `inspect` command shall report the failure
      unchanged, naming no dotted-module reading.
- [ ] Where the `inspect` argument names a private submodule, the `inspect` command shall emit the
      private-and-never-indexed message unchanged.
- [ ] When `inspect` is given a dotted module name that resolves, the `inspect` command shall
      return the module node and its direct children as it did before this change.
- [ ] When `inspect` is given a name containing `::`, the `inspect` command shall behave as it did
      before this change, on both a resolving name and a missing one.
- [ ] The `inspect` command shall propose no corrected spelling of the caller's argument.
- [ ] When `tree`, `inherits`, `find` or `show` is given a name whose top-level root is not
      installed, each command shall emit the package-not-found message unchanged.
- [ ] If the `inspect` argument's top-level root is not a possible package name, then the `inspect`
      command shall raise `InvalidArgumentError` with its message unchanged.
- [ ] The MCP tools shall return the same answers as before this change.
- [ ] The test suite and the conformance tier shall pass.

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

## Follow-ups
