---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/commands/setup.md
authors: []
issues: [43]
pr:
---

# Plan: Setup installs the skill by default

## Scope

Since [`plans/ambient-collapse-to-skill.md`](ambient-collapse-to-skill.md) removed the always-on
`AGENTS.md` block, `venvaxi setup` installs two kinds of ambient context: the MCP registration, and
the skill behind an opt-in `--skill` flag. `specs/principles.md`
[principle 7](../specs/principles.md#principle-7-ambient-context) requires ambient context to be
installed into the agent's session by an explicit setup command, and the current default does not
deliver it.

MCP registration is gated on `fastmcp` being importable, which `specs/commands/setup.md` requires
for a good reason: a registered server that `venvaxi serve` cannot start would die on every agent
session. The skill is gated on a flag. In a consuming repo without the `mcp` extra the documented
invocation `uv run venvaxi setup` therefore installs **nothing at all**, and exits `EX_OK`
reporting four false values. The one artifact that is never gated is withheld by default.

Make the skill the default, with `--no-skill` to opt out, and keep `--skill` accepted so existing
invocations continue to work.

Out of scope: the skill's gotchas and its exit-code overclaim, owned by
[#52](https://github.com/andyrids/venv-axi/issues/52); what `setup` registers as the MCP command,
owned by [#55](https://github.com/andyrids/venv-axi/issues/55), which amends the same spec and
should be sequenced against this plan; and the diff or refuse mode on skill divergence already
parked in `specs/commands/setup.md` Out of scope.

## Implements

`specs/commands/setup.md` Invocation, Actions item 4 and Outputs, as amended by this plan - the
skill is written on every run unless `--no-skill` is given, and the `SKILL.md` key reports whether
the file was written rather than whether the caller asked for it. The same plan amends the spec and
brings the code into conformance, which `plans/README.md` resolves in favour of `specs:`.

The amendment also records, in Out of scope, why the skill is not defaulted off for non-Claude
harnesses. `#43` raised that objection and it deserves an answer in the spec rather than a decision
remembered only in an issue thread.

## Approach

1. Flip to `status: in-progress`.
2. Amend `specs/commands/setup.md` per Implements, and run the ripple check in `specs/README.md`.
3. Change the flag to `argparse.BooleanOptionalAction` with `default=True` in `_cli.py`, and the
   `setup_ambient_context` keyword default to `True` in `_ambient.py`.
4. Update the tests asserting the old default, and add the `fastmcp`-absent regression guard.
5. Correct `src/venvaxi/SKILL.md` where it documents the old behaviour, then regenerate
   `.claude/skills/venvaxi/SKILL.md` with `just skill-sync`. The repo copy is generated output and
   is never hand-edited.
6. `README.md` and `docs/architecture.md`.
7. `CHANGELOG.md` under `Changed`, flagged breaking for `setup` callers.

## Validation

- [ ] When `setup` runs with no flags, the `setup` command shall install
      `.claude/skills/venvaxi/SKILL.md` and report `SKILL.md: true`.
- [ ] Where `fastmcp` is not importable, when `setup` runs with no flags, the `setup` command shall
      still install the skill and report `.vscode: false` and `.mcp.json: false`.
- [ ] When `setup --no-skill` runs, the `setup` command shall not write the skill and shall report
      `SKILL.md: false`.
- [ ] When `setup --skill` runs, the `setup` command shall produce the same result as a bare
      `setup`.
- [ ] While an installed skill already matches the packaged skill byte-for-byte, when `setup` runs,
      the `setup` command shall report `SKILL.md: false`.

## Risks / unknowns

- A wholesale overwrite becomes the default, so a bare `setup` now discards hand edits to the
  installed copy without reporting what it discarded. Nothing legitimate should live there - a
  per-repo variation point is already Out of scope, `tests/test_skill_parity.py` enforces
  byte-identity, and the skill's own Pointers name the packaged source as the edit surface - but
  the blast radius of the existing policy grows, because it now applies to callers who never asked
  for the skill.
- `setup` writes into `.claude/` by default in every consuming repo, including those using no
  Claude harness. The spec records why that trade is accepted.
- This plan and #52 both edit `src/venvaxi/SKILL.md` and both regenerate the repo copy, so
  whichever lands second rebases. This plan touches only the lines describing `setup`.
- Issue #55 amends the same spec file. If it lands first, step 2 rebases onto its wording.
- `--skill` becomes a no-op-equivalent rather than an error. That is deliberate for compatibility,
  but it means a caller cannot tell from the flag alone whether the default changed under them; the
  `SKILL.md` key is the only signal, and it was already the honest one.

## Notes

Populated at closeout.

## Follow-ups

Populated at closeout.
