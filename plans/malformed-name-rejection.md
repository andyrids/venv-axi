---
status: done
depends: []
specs:
  - specs/behaviors/package-resolution.md
  - specs/behaviors/output-contract.md
  - specs/commands/find.md
  - specs/commands/tree.md
  - specs/commands/show.md
  - specs/commands/inspect.md
  - specs/commands/inherits.md
  - specs/mcp/tools.md
issues: []
pr:
---

# Plan: Reject malformed package names at the boundary

## Scope

Make a package argument that cannot possibly name a package raise `InvalidArgumentError`, so no
user-supplied value produces `EX_SYNTAX` on the CLI or escapes into FastMCP's generic error path
on the MCP surface.

Absorbed from [package-error-taxonomy](package-error-taxonomy.md)'s Follow-ups, which recorded
the crash but deliberately left it: that plan drew the line between two *valid*-name outcomes,
and a third class of guard would have widened it into a different change.

## Implements

`specs/behaviors/package-resolution.md` is authored by this plan and implemented by it - the
three-way malformed/absent/broken taxonomy, previously stated nowhere and enforced only by
`show --api`.

`specs/behaviors/output-contract.md` gains the invariant that no user-supplied argument value may
produce `EX_SYNTAX`; the code currently violates it on four verbs.

`specs/mcp/tools.md` gains 'no exception escapes, not just no `Error`'; `_toon_errors` currently
catches `Error` only.

The five command specs are amended to reference the behaviour spec and to list
`InvalidArgumentError`. Their existing `PackageNotFoundError` / `PackageImportError` bullets stay
as written - PR #23 already brought the code into conformance with those.

## Approach

Two defect classes, probed live at `3d2d9b8`:

```text
$ venvaxi tree .foo
message: "Unexpected error: A distribution name is required."      exit 2 (EX_SYNTAX)

$ venvaxi tree "a b"
message: Package `a b` is not installed in the active venv         exit 1
```

The first is an unhandled `ValueError` from `importlib.metadata`, reached whenever
`_top_level_root` yields an empty string (`.foo`, `...`, `""`, `../etc/passwd`). Through MCP it
escapes `_toon_errors` entirely, so `getModuleTreeTool(".foo")` raises into FastMCP rather than
returning TOON - a live violation of `specs/mcp/tools.md`.

The second reports an impossible name as merely absent, inviting an install that can never
succeed.

### One regex, swept against the venv

`_VALID_NAME_RE` accepts anything built from the legal character set, including a name that is
all dots. Require it to begin and end with an alphanumeric or underscore, leaving dots and dashes
legal internally.

Swept over all 234 distribution and import names installed here: nothing legitimate is rejected.
The only casualties are 34 pywin32 `packages_distributions()` keys carrying path separators
(`win32\lib\win32con`), which are not module names and cannot be used as arguments today either.

```text
accepted : rich.console  detect-secrets  zope.interface  ruamel.yaml  2to3  a.b
rejected : .foo  ...  ""  "a b"  ../etc/passwd  foo/bar  -x  foo-  .
```

### Where it runs

Validate the top-level root **as supplied**, before `_resolve_import_name` - this is boundary
validation of caller input, and resolution can only disguise a malformed name (its fallback is
`name.replace("-", "_")`), never repair one.

The guard belongs immediately before the existing `_ensure_installed` call in the graph builder,
where all four affected verbs already converge, and should read as its sibling. `show --api`
needs no new call site: it already validates with this regex, so tightening the pattern fixes it.

`_toon_errors` gains an `except Exception` arm returning the CLI's `Unexpected error:` block,
with `logger.exception`.

### The trap

**Do not add the guard to `_packages.resolve_package` without widening `_try_resolve_package`.**
The latter catches `PackageNotFoundError` only, and `list` relies on it to skip every
uninstalled declared dependency. An `InvalidArgumentError` raised there crashes `venvaxi list` on
any oddly-spelled `pyproject.toml` entry.

`show` metadata mode MUST keep its existing dotted-name hint, which is a better answer for `.foo`
than a generic malformed-name error - see the Metadata mode section of the behaviour spec.

## Validation

- [x] `venvaxi tree .foo` reports a malformed-name error at exit 1, not `Unexpected error` at
  exit 2
- [x] The same holds for `...`, `""` and `../etc/passwd` across `tree`, `find --package`,
  `inspect` and `inherits`
- [x] `venvaxi tree "a b"` reports `InvalidArgumentError`, not `PackageNotFoundError`
- [x] `getModuleTreeTool(".foo")` returns a TOON error block instead of escaping into FastMCP
- [x] `_toon_errors` returns an `Unexpected error:` block for a non-`Error` exception
- [x] `venvaxi tree rich`, `tree detect-secrets`, `tree json` and `find Console --package rich`
  all still resolve; `show zope.interface` (not installed in this venv) keeps its metadata
  answer rather than being rejected as malformed
- [x] `venvaxi show .foo` keeps its dotted-name hint
- [x] `venvaxi list` is unaffected
- [x] Every command spec's Errors section agrees with observed behaviour
- [x] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green

## Risks / unknowns

- **A tightened regex is a widening of what gets rejected.** The sweep above is evidence for this
  venv, not proof for every venv. A distribution whose top-level import name legitimately starts
  or ends with a dot or dash would now be refused - no such name exists on PyPI's naming rules,
  but the failure mode if one did is a package that cannot be introspected at all.
- **`_toon_errors` catching `Exception` hides bugs from tests.** A tool that starts raising will
  return a TOON block rather than failing loudly. Mitigated by logging the traceback at `ERROR`,
  exactly as the CLI does, and by keeping the arm below the `Error` arm.

## Notes

- **`_ensure_valid_name` took two arguments, not the techspec's one.** Called on the root alone,
  `tree .foo` reported ``Invalid package name ` ` `` - the root of `.foo` is `""`, an empty
  operand the caller cannot act on. The helper now mirrors `_ensure_installed(import_name, name)`:
  validate the first, message the second. No behaviour spec pins the message operand; the
  techspec sketch was corrected in place.
- **Stage 03 re-entry: `specs/commands/show.md` Errors bullet scoped to API mode.** As written it
  implied metadata mode also raises `InvalidArgumentError` for a malformed spelling, while the
  observed (and intended) metadata answer for `show "a b"` is ``Package `a b` is not installed``
  at exit 1 - the carve-out the behaviour spec's Metadata mode section sanctions. The spec was
  amended, not the code.
- `show zope.interface` cannot 'resolve' in this venv - the distribution is not installed, and
  HEAD gave the identical exit 1 metadata answer (checked via `git stash`). The criterion was
  reworded to what is checkable: the name passes the new regex and is not rejected as malformed.
- The `...`/`""`/`../etc/passwd` box is evidenced by live exit-code runs on `tree` for all
  inputs, live runs of the other three verbs on `.foo`, and the parametrized unit tests - all
  four verbs share the single `_build_store_for` guard.
- Regex sweep re-run at implementation time: 97 distributions + 198 import-name keys, 234 union;
  the only rejections are the 34 pywin32 `packages_distributions()` keys carrying path
  separators.
- `pr:` is deliberately unset - this run made no commit and opened no PR.

## Follow-ups

- None. Two regex nits are accepted limitations, recorded here rather than deferred: internal
  consecutive dots (`foo..bar`) pass, and `$` matches before a trailing newline (`"rich\n"`
  passes). Both land in `PackageNotFoundError` at exit 1 downstream - a wrong class, never
  `EX_SYNTAX`, and neither is producible from a shell argument in normal use.
