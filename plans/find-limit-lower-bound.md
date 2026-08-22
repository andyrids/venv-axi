---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/find.md
  - specs/mcp/tools.md
authors: []
issues: [73]
pr:
---

# Plan: find-limit-lower-bound

## Scope

A negative `find` limit is neither clamped nor rejected, so it defeats the result cap entirely
([#73](https://github.com/andyrids/venv-axi/issues/73)). `venvaxi find "a" --limit -5` returns
the whole graph - 64,384 rows, 5.2 MB - at exit 0, and `findSymbolTool(query="a", limit=-1,
package="numba")` fails with a transport-level 'exceeds maximum allowed tokens' refusal, which
is the one error shape `specs/behaviors/output-contract.md` exists to keep off this surface.

The value travels from the argument parser to the query untouched, and a negative `LIMIT` is
read as unbounded. The #69 cap hint cannot save the caller either: it fires on
`len(nodes) == limit`, which a negative limit never satisfies, so the largest possible answer
arrives with the one signal that would have questioned it suppressed.

In scope: a lower bound on the limit, declared in `specs/commands/find.md` and
`specs/mcp/tools.md` and enforced once in the shared search entry point, plus the message-wording
rule that keeps a shared-path error legible on both surfaces.

Out of scope: `--limit 0`, which is well behaved today and stays so - zero is a bound the command
honours exactly; a bound for `show --api`'s collection
([#67](https://github.com/andyrids/venv-axi/issues/67)), which is 0.4.0 work and is what still
keeps the bounded-results rule local to `find.md` rather than in `output-contract.md`; and any
patch to the #69 hint gate, which the rejection removes the need for rather than fixes.

## Implements

- `specs/commands/find.md` - Bounded results now declares the floor as well as the cap: a
  negative limit is rejected rather than clamped, with the reason recorded next to the #67
  parking note; `--limit 0` is declared a result, not a malformed argument. Failure modes gains
  the matching `If <trigger>, then` criterion alongside the command's other argument rejections.
- `specs/mcp/tools.md` - a new Error message wording rule: a message raised by logic shared with
  the CLI shall name the input it rejects in a spelling true on both surfaces, naming neither
  the flag nor the parameter. `findSymbolTool` inherits the rejection from `find` as parity, so
  it is stated as an inherited criterion and not added to Divergences.

## Approach

- Validate the limit once, in the shared search entry point both surfaces route through,
  following the `refresh`-without-`package` guard a few lines below it - the same
  `InvalidArgumentError`, raised before any store is opened, so the unscoped and the
  package-scoped paths are both covered by one check.
- Leave the argument parser and the tool schema untouched. A duplicated bound in three places
  is three places to drift; the CLI and the MCP tool already render an `InvalidArgumentError`
  correctly for their own surface, so both inherit the fix.
- Phrase the message surface-neutrally and echo the offending value, mirroring the sibling
  `Search query must be non-empty` in the same function.
- Tests at all three levels: the raise in `tests/test_introspect.py`, exit 1 and the TOON error
  block in `tests/test_cli.py`, the surface-addressed block in `tests/test_mcp.py`, and a pin on
  `limit=0` so the well-behaved case cannot be broken by a later tightening.

## Validation

- [x] If the shared symbol search is called with a negative limit, then it shall raise
      `InvalidArgumentError` before any symbol store is opened. —
      `tests/test_introspect.py::test_find_symbol_negative_limit_raises` and
      `tests/test_introspect.py::test_find_symbol_negative_limit_raises_before_package_build`
- [x] If `find` is invoked with a negative `--limit`, then the command shall emit the TOON error
      block and exit `EX_FAILURE`. —
      `tests/test_cli.py::test_main_find_negative_limit_maps_to_exit_1`; live venv,
      `uv run venvaxi find "a" --limit -5` -> the TOON error block reporting
      'Search limit -5 must not be negative', exit 1
- [x] If `findSymbolTool` is called with a negative `limit`, then it shall return the TOON error
      block without the CLI `venvaxi --help` footer. —
      `tests/test_mcp.py::test_find_symbol_tool_negative_limit_returns_error_block`
- [x] If a negative limit is rejected, then the message shall name neither the CLI flag nor the
      tool parameter, so it reads correctly on either surface. —
      `tests/test_introspect.py::test_find_symbol_negative_limit_message_suits_both_surfaces`
- [x] When `find` is invoked with `--limit 0`, the command shall emit `count: 0` and exit
      `EX_OK`. — `tests/test_introspect.py::test_find_symbol_zero_limit_returns_no_results` and
      `tests/test_cli.py::test_command_find_zero_limit_prints_empty_state`; live venv,
      `uv run venvaxi find "a" --limit 0` -> `count: 0`, exit 0
- [x] When `find` is invoked with no `--limit`, the command shall return no more rows than the
      documented default of 20 and exit `EX_OK`. — live venv,
      `uv run venvaxi find "a"` -> `count: 20` with the issue-69 cap hint, exit 0;
      `tests/test_cli.py::test_add_subparser_find_defaults` pins the default itself

## Risks / unknowns

- The rejection is on negative values only. `0` stays a result, which reads oddly beside a
  parameter documented as a maximum, and is the position the issue itself takes - `--limit 0` is
  named there as well behaved and outside the bug.
- The message is raised in shared code, so its wording is now load-bearing on two surfaces at
  once. That is what the new `specs/mcp/tools.md` rule exists to pin.

## Notes

- Track verdict: `process-plan`, not express-change. Express fails on its first eligibility
  condition - neither `specs/commands/find.md` nor `specs/mcp/tools.md` declared any lower bound
  on the limit, so new normative text was required before code could conform. The same blocker
  issue 60 hit.
- Why reject rather than clamp. Clamping to the default was considered and rejected: it rewrites
  the caller's argument without telling them, and the reply to the substituted question is
  indistinguishable from the reply to theirs. That is the direction issues 47, 60 and 65 moved
  this project away from. Clamping to `0` was rejected for the same reason issue 47 exists - an
  empty result for a bad limit reads as 'no matches', a definitive negative that is false.
- Why one guard, not three. The issue proposed validating at both entry points, in the argument
  parser and in the tool schema. Both surfaces route through the same search entry point, so one
  guard covers the CLI, MCP, and both the unscoped and the package-scoped search paths - and a
  bound written in three places is three places to drift. The argument parser and the tool schema
  are deliberately unchanged.
- Why the guard sits where it does. Above the `package is None` branch, so no store is opened and
  no graph is built before a negative limit is rejected; below the empty-query check, so an
  invocation malformed in both ways reports the first argument the caller reads. Pinned by
  `tests/test_introspect.py::test_find_symbol_negative_limit_raises_before_package_build`.
- Design decision: the message is spelled for neither surface. It is raised on the shared path,
  so a CLI flag in it would misdirect a tool caller and a tool parameter would misdirect a shell
  caller. That is now a rule, in `specs/mcp/tools.md` under Error message wording, rather than a
  habit - it is the first shared-path message reachable on both surfaces where the natural
  spelling differs.
- The issue-69 cap hint gate was left alone on purpose. It no-ops on a negative limit because
  a count never equals one; rejecting the input removes that path rather than patching it, and
  the gate is still correct for every limit that now reaches it. Confirmed still firing:
  `find "a"` returns `count: 20` with `Results capped at --limit 20`.
- Gotcha: `--limit 0` is a result, not a rejection. The bound is on negatives only. Zero is
  something the search honours exactly, and the issue names it as well behaved and outside the
  bug, so tightening it to `limit < 1` would be a behaviour change this plan never declared.
  Both surfaces carry a pin against that.
- Reproduced locally before fixing, at a smaller scale than the issue's: with `fastmcp` indexed,
  `find "a" --limit -5` returned `count: 2704` in 219,060 bytes at exit 0, with `help[1]` and no
  cap hint - both halves of the defect, on this machine.
- Stage 02 wrote the tests, not stage 03. The 02 contract makes unit test coverage its own
  output; 03 executed them, mapped them to criteria and reported. No re-entry occurred at any
  stage - nothing decided after 01 changed observable behaviour.
- The changelog entry opens a new `## [0.3.2] - 2026-08-22` section. There is no `## [0.3.1]`
  section on `develop` to sit above; the newest section on the file is `## [0.3.0rc2]`, and
  `[0.3.2]` is placed immediately above it.
- `pr:` is left blank: this run committed locally on `find-limit-lower-bound` and opened no PR.

## Follow-ups

- Issue [#67](https://github.com/andyrids/venv-axi/issues/67) - `show --api --docstring` still
  has no row-count bound at all. It is 0.4.0 work, and it remains the reason the bounded-results
  rule stays local to `specs/commands/find.md` rather than being generalized into
  `specs/behaviors/output-contract.md`. When #67 lands, the floor added here generalizes with the
  cap, as one move.
- Issue [#68](https://github.com/andyrids/venv-axi/issues/68) - the Error message wording rule
  added here has one non-conforming message on the shared path, `find_symbol`'s
  ``"`--refresh` requires `--package` to name the graph to rebuild"`` at
  `src/venvaxi/_introspect.py:955`, which names CLI flags. It is unreachable over MCP today
  because no tool exposes `refresh`, so the divergence is latent, and it is recorded as a Known
  exception in [`specs/mcp/tools.md`](../specs/mcp/tools.md). #68 adds the parameter that makes
  it reachable, so #68 owns rewording it. Left unfixed here deliberately - correcting it would
  widen this plan past the scope stage 01 set.
- Tracked as an open question for whoever revisits #67 - `--limit 0` returning `count: 0` while a
  negative limit is rejected is defensible but not obvious, and a single collection-bounds rule
  covering both commands is the right place to settle whether zero stays a result.
