---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/setup.md
authors: []
issues: [43]
pr: 57
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

- [x] When `setup` runs with no flags, the `setup` command shall install
      `.claude/skills/venvaxi/SKILL.md` and report `SKILL.md: true`.
      — `tests/test_ambient.py::test_setup_ambient_context_installs_skill_by_default`, and a
      live cold `venvaxi setup` in a throwaway project emitting `SKILL.md: true` with the file
      present on disk
- [x] Where `fastmcp` is not importable, when `setup` runs with no flags, the `setup` command shall
      still install the skill and report `.vscode: false` and `.mcp.json: false`.
      — `tests/test_ambient.py::test_setup_installs_skill_without_fastmcp`, shown failing
      against the pre-change default with `assert False is True` on `changed["SKILL.md"]`
- [x] When `setup --no-skill` runs, the `setup` command shall not write the skill and shall report
      `SKILL.md: false`.
      — `tests/test_ambient.py::test_setup_no_skill_suppresses_install`, with `.claude/` absent
      after a live run
- [x] When `setup --skill` runs, the `setup` command shall produce the same result as a bare
      `setup`.
      — `tests/test_ambient.py::test_setup_skill_flag_matches_default`
- [x] While an installed skill already matches the packaged skill byte-for-byte, when `setup` runs,
      the `setup` command shall report `SKILL.md: false`.
      — `tests/test_ambient.py::test_setup_reports_false_when_skill_unchanged`, and a second
      live bare `setup` emitting `SKILL.md: false`

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

**This was a conformance fix, not a preference.** Issue 43 framed it as 'is the default too
thin?', which reads as taste. `specs/principles.md` principle 7 makes it decidable: ambient context
is 'installed into the agent's session/hooks via an explicit setup command'. With MCP registration
gated on `fastmcp` and the skill gated on a flag, the explicit setup command had nothing to install
in a repo without the extra, and said so with four false values and `EX_OK`. The ungated artifact
being the withheld one was the defect. Recorded because the framing is what made the decision
straightforward, and a future reader will otherwise re-open it as taste.

**Only one Validation criterion discriminates.** All five tests fail against the pre-change source,
but criteria 1, 3, 4 and 5 fail because they are phrased against the bare-run default, which is
what moved; the behaviour they guard - `--skill` handling, and `install_skill()` returning `False`
on an identical copy - already held. Criterion 2 is the only one whose asserted behaviour did not
previously exist. Do not read the five ticks as five independent proofs that the defect was fixed;
`test_setup_installs_skill_without_fastmcp` carries that weight alone.

**The techspec was wrong about `argparse`.** It stated the module was already imported in
`_cli.py`. It was, but only under `if TYPE_CHECKING:`, so `argparse.BooleanOptionalAction` raised
`NameError` at runtime. Implementation promoted the import, and stage 03 reproduced the failure
directly to confirm the deviation was necessary rather than cosmetic. The string annotation
`"argparse._SubParsersAction[Any]"` resolves either way, so removing the emptied `TYPE_CHECKING`
guard was safe.

**Why `BooleanOptionalAction` over a hand-rolled `--no-skill`.** The stdlib action renders
`usage: venvaxi setup [-h] [--skill | --no-skill]` and one shared help entry. A hand-rolled pair
renders `[--skill] [--no-skill]`, which implies the two combine meaningfully, and gives two help
entries that can drift apart. `specs/README.md` Invariant 4 makes `--help` authoritative for
invocation, so the generated form *is* the contract - picking the action that generates the right
contract is cheaper than maintaining prose to match a hand-rolled one.

**A version concern was raised and did not reproduce.** Implementation flagged that argparse
appends `(default: True)` to a `BooleanOptionalAction` help entry on older interpreters. Rendered
on Python 3.11.16, 3.12.14 and 3.13.7 the output is identical and carries no such suffix. The
behaviour existed in earlier CPython patch releases and was removed; it does not apply to what
`requires-python >=3.11` resolves to today. Three patch levels were checked, not every 3.11.x.

**Why this plan edited `SKILL.md` even though issue 52 owns that file.** The skill documented the
flag this plan changed, in five places. Leaving it would have shipped a skill telling every agent
the skill is opt-in - wrong ambient context riding along inside the very change that falsified it.
The edit was confined to flag references and the `setup` row; the gotcha substance, the
token-savings paragraph and the exit-code claim were untouched, so issue 52's scope is intact and
the rebase cost is one mechanical `just skill-sync`.

**One live failure mode was not exercised.** Stage 03 tried to trigger `ProjectRootNotFoundError`
from a directory with no `pyproject.toml` and did not get it: `get_project_root` falls back to
`Path(sys.prefix).parent`, which for a development venv is this repo, so the run resolved here and
reported every key false. Documented behaviour, no repo change, and the failure modes remain
covered in `tests/test_ambient.py` - recorded so the gap in the live sweep is visible rather than
implied to have passed.

## Follow-ups

- **Issue [#52](https://github.com/andyrids/venv-axi/issues/52)** - still owns the skill's gotchas
  and its exit-code overclaim. One item from this run rides with it: the skill's command table now
  lists only `--no-skill` in the Flags column while `--help` advertises `--skill, --no-skill`,
  mildly at odds with that table's own 'Verified against `venvaxi --help`' preamble. Defensible as
  written, since `--no-skill` is the flag that changes behaviour, but worth a deliberate decision
  rather than an inherited one.
- **Issue [#55](https://github.com/andyrids/venv-axi/issues/55)** - amends
  `specs/commands/setup.md` as well, to change what `setup` registers as the MCP command. It now
  rebases onto this plan's wording rather than the other way round.
- **Tracked as** - the wholesale-overwrite default. No plan or issue owns a diff or refuse mode; it
  stays parked in `specs/commands/setup.md` Out of scope, to be revisited only if a diverged
  installed copy ever proves to hold work worth protecting. The blast radius grew with this
  change, which is the condition under which that parking deserves re-examination.
