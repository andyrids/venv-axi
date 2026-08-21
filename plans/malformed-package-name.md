---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/package-resolution.md
authors: []
issues: [65]
pr: 70
---

# Plan: malformed-package-name

## Scope

`show ""` - and any malformed package name in metadata mode - crashes with an unhandled
`importlib.metadata` `ValueError`, a traceback and exit 2
([#65](https://github.com/andyrids/venv-axi/issues/65)). Exit 2 is reserved for venvaxi being
broken; a caller's typo must report as `InvalidArgumentError` and exit 1.

Express-change: `specs/behaviors/package-resolution.md` already declares the behaviour on the
default branch - 'Malformed -> `InvalidArgumentError`', 'Validation shall run before
resolution', and its Applies to names `show` - so no spec moves; the code is brought into
conformance in one commit.

In scope: validation before metadata resolution, the `list` skip staying a skip for malformed
requirement strings, and the MUST-preserved dotted-name hint. Out of scope: any new
validator - the existing one is reused - and any change to the PEP 508 requirement-name
extractor, which is an extractor, not a validator, and must stay unanchored.

## Implements

- `specs/behaviors/package-resolution.md` - the malformed class for metadata mode: validation
  runs before resolution in the resolver `show` uses; the Metadata mode carve-out (dotted
  module path answers 'not installed' with the `--api` hint) is preserved byte-identical; the
  `list` skip covers unresolvable, not merely uninstalled, dependencies. The MCP
  `showPackageTool` inherits the fix through the shared tool error boundary; no separate
  change.

## Approach

- Move the name validator and its regex into the package-resolution module the spec names,
  and import it back into the introspection module for qualified-name roots - no second
  validator, no import cycle.
- Validate the caller's spelling at the top of metadata resolution, before the distribution
  lookup. Dotted names remain possible names, so they still fall through to the preserved
  'metadata mode takes a distribution name' hint.
- Widen the resolve-or-skip helper to skip `InvalidArgumentError` alongside
  `PackageNotFoundError`, so a malformed requirement string in `pyproject.toml` cannot turn
  `list` into a failure.
- Tests on the resolver, the CLI boundary (exit 1 + `Invalid package name`) and the MCP tool
  (domain-error TOON block).

## Validation

- [x] If a malformed name is supplied to the resolver, then it shall raise
      `InvalidArgumentError`, never report the name as not installed. —
      `tests/test_packages.py::test_resolve_package_malformed_raises`
- [x] If a malformed package name is supplied to `show` in metadata mode, then the command
      shall emit the TOON error block and exit `EX_FAILURE`, never `EX_SYNTAX`. —
      `tests/test_cli.py::test_main_show_malformed_name_maps_to_exit_1`
- [x] If `showPackageTool` is called with a malformed name, then it shall return the TOON
      error block naming the invalid name, never the `Unexpected error:` shape. —
      `tests/test_mcp.py::test_show_package_tool_malformed_name_returns_error_block`
- [x] When a dotted module path is supplied in metadata mode, the resolver shall answer 'not
      installed' with the `--api` hint, byte-identical to before. —
      `tests/test_packages.py::test_resolve_package_dotted_name_keeps_api_hint`
- [x] If a declared dependency's requirement string is malformed, then the `list` command
      shall skip it and report the remaining dependencies. —
      `tests/test_packages.py::test_list_packages_skips_malformed`

## Risks / unknowns

- The validator moves modules, and the introspection module re-imports it; existing callers
  and tests import it from the old home, so the re-import is load-bearing until they migrate.
- The validator accepts a leading underscore (legal import name, illegal distribution name);
  metadata mode therefore reports `_foo` as not installed rather than malformed. Accepted:
  reusing the single validator outweighs distribution-grade strictness, and 'not installed'
  is true.

## Notes

- Express eligibility held to the end: no `specs/**` file moved, one commit's worth, no new
  surface. `specs/behaviors/package-resolution.md` had already declared every rule this
  change implements.
- Design decision: the validator moved to `venvaxi._packages` - the module the spec names as
  the resolution boundary - and `_introspect` re-imports it. The re-import is load-bearing:
  `tests/test_introspect.py` still imports `_ensure_valid_name` from `_introspect`.
- Design decision: validation runs on the caller's spelling (`_ensure_valid_name(name,
  name)`) before `metadata.distribution`, so dotted names - valid spellings - still fall
  through to the MUST-preserved 'metadata mode takes a distribution name' hint, byte-
  identical.
- Gotcha: `_NAME_RE` (unanchored PEP 508 extractor) and `_VALID_NAME_RE` (anchored
  validator) now sit side by side in `_packages.py` with role comments - reusing the
  extractor as a validator would accept any string with a valid prefix.
- Accepted looseness (recorded in Risks): the shared validator accepts a leading underscore,
  a legal import name but an illegal distribution name, so `show _foo` reports 'not
  installed' rather than malformed - which is true.
- The changelog entry lives under `[0.3.0rc2]` in `CHANGELOG.md`, written by
  `plans/withdraw-0-3-0.md`'s release-record edit - this fix is part of that release.
- `status` stays `in-progress` with `pr:` empty. `plans/README.md` puts the flip to `done`
  plus the PR number in the last commit *before merge*, and no PR exists yet. Closeout is
  otherwise complete: boxes ticked with citations, Notes and Follow-ups populated.

## Follow-ups

- None - #65 closes with this plan, and no adjacent work was uncovered.
