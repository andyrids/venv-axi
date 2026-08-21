---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/setup.md
authors: []
issues: []
pr: 42
---

# Plan: Collapse ambient context to the skill

## Scope

AXI [principle 7](../specs/principles.md#principle-7-ambient-context) is delivered through three
channels today, all written by `venvaxi setup`: an always-on `AGENTS.md` block sourced from
`src/venvaxi/ambient.md`, MCP server registration, and the opt-in skill. The block is largely
redundant with the skill and pays its token cost in every session of every consuming repo,
relevant or not.

Remove the `AGENTS.md` injection, replacing it with a **removal pass** that strips a previously
installed block byte-safely, so a consumer self-heals on its next `setup` run rather than carrying
an orphaned always-on block forever. Fold the one normative statement that loses its home into the
packaged skill, and correct the three places the skill describes the mechanism being removed.

Out of scope: any change to `install_skill()` policy, to MCP registration, to skill/CLI text drift
(issue #39), or to running the eval suite in CI (issue #40).

## Implements

`specs/commands/setup.md`, amended by this plan in two places:

1. **Actions item 1** - inverted. The `setup` command no longer injects the block; it removes one
   if present, still preserving every byte outside the markers.
2. **Out of scope, "Removal"** - currently "artifacts are installed, never uninstalled. Never."
   The removal pass contradicts that clause directly, so it is amended rather than worked around,
   per `specs/README.md` Invariant 2.

The Outputs key set is deliberately **unchanged**. `AGENTS.md` still means "this file was
modified"; it is now true on removal instead of on write.

## Approach

1. Flip to `status: in-progress`.
2. Amend `specs/commands/setup.md`: the artifact count, Actions item 1, the ungated-guidance
   sentence that loses its subject, and the Out of scope "Removal" bullet.
3. Replace `inject_agents_md()` with `strip_agents_md()` in `src/venvaxi/_ambient.py`. It returns
   `False` without writing when `AGENTS.md` is absent or carries no markers, and never creates the
   file. The marker-bounds splice already present is reused to cut the span, collapsing the
   separator the injection introduced. Byte discipline is retained - decode on read,
   `_atomic_write_bytes` on write - because the preservation clause it satisfies is unchanged.
   `Text` keeps `BEGIN`/`END` and drops `BODY`/`GAP`; `ambient_markdown` and
   `src/venvaxi/ambient.md` are deleted.
4. Edit `src/venvaxi/SKILL.md` only: fold in the MUST-scan directive orphaned from `ambient.md`,
   rewrite the three self-references to the removed mechanism, and add a gotcha for the removal
   pass. Regenerate the repo copy with `just skill-sync`.
5. Update the `setup` subparser help in `src/venvaxi/_cli.py`, which names `AGENTS.md`.
6. Retarget rather than delete the `AGENTS.md` byte-preservation tests - they exercise the splice,
   which survives. Delete only the tests for behaviour that no longer exists, and add coverage for
   the three new no-op paths.
7. Fix the mocked-key mismatch in `tests/test_cli.py` found while scoping: the fixtures use
   `"skill"` where `setup_ambient_context` returns `"SKILL.md"`, so the guard their NOTE describes
   is not armed.
8. `docs/architecture.md`, `README.md` and `CHANGELOG.md`.

## Validation

- [x] When `setup` runs against a repo whose `AGENTS.md` contains a `venvaxi:begin`/`venvaxi:end`
      block, then the `setup` command shall delete the marked span, leave every byte outside the
      markers unchanged whatever line endings that content uses, and report `AGENTS.md: true`.
      — `tests/test_ambient.py::test_strip_agents_md_removes_block`,
      `::test_strip_agents_md_preserves_lf_bytes_outside_markers`,
      `::test_strip_agents_md_preserves_crlf_bytes_outside_markers`,
      `::test_strip_agents_md_preserves_bytes_around_markers`, plus a live `venvaxi setup` over a
      seeded LF repo (132 bytes to 66) and a seeded CRLF repo, both emitting `AGENTS.md: true`
      with the hand-authored span unchanged and no terminator swapped
- [x] When `setup` runs against a repo with no `AGENTS.md`, then the `setup` command shall not
      create one and shall report `AGENTS.md: false`.
      — `tests/test_ambient.py::test_strip_agents_md_absent_file_is_noop`,
      `::test_setup_ambient_context_never_creates_agents_md`, and a live run over an empty repo
      emitting `AGENTS.md: false` with no file created
- [x] When `setup` runs against an `AGENTS.md` carrying no markers, then the file shall be
      byte-identical afterwards and the `setup` command shall report `AGENTS.md: false`.
      — `tests/test_ambient.py::test_strip_agents_md_without_markers_is_noop`, and a live run
      with matching `md5sum` either side
- [x] When `setup` runs twice against a repo that had a block, then the second run shall report
      `AGENTS.md: false` and leave the file unmodified.
      — `tests/test_ambient.py::test_strip_agents_md_idempotent`,
      `::test_setup_ambient_context_second_run_reports_no_change`, and a live second run emitting
      `AGENTS.md: false`
- [x] `src/venvaxi/ambient.md` shall not exist, and no module shall reference `ambient_markdown`
      or `inject_agents_md`. — file deleted; a grep over `src/ tests/ docs/ specs/ README.md
      Justfile prek.toml pyproject.toml` returns only the historical `CHANGELOG.md` entries. The
      now-dead `ambient.md` exclude was removed from the markdown hook in `prek.toml`
- [x] The packaged skill shall state the MUST-scan directive as a normative requirement in its
      Workflow section. — `src/venvaxi/SKILL.md:41`
- [x] The packaged skill shall carry no claim that `setup` injects or refreshes an `AGENTS.md`
      block. — `src/venvaxi/SKILL.md:109`, `:206` and `:226` rewritten; `:33`'s pointer at
      `AGENTS.md` as the source of the bare `venvaxi` spelling went with them
- [x] `tests/test_skill_parity.py` shall pass after `just skill-sync`, with no hand-edit to
      `.claude/skills/venvaxi/SKILL.md`. — `just skill-sync` printed `True` (regenerating), then
      3 passed
- [x] The mocked `setup` return values in `tests/test_cli.py` shall use the key `SKILL.md`,
      matching what `setup_ambient_context` returns. — `tests/test_cli.py:694`, `:724`, `:751`
      and the two assertions at `:709`, `:737`
- [x] The full suite shall pass with coverage no lower than before the change. — 302 passed;
      `_ambient.py` at 98%, project total 98%. `mypy` clean on `_ambient.py`; `ruff check` and
      `ruff format` report the same pre-existing findings as the committed baseline (verified by
      running both against `git show HEAD:` copies), none introduced here

## Risks / unknowns

- **Cold discovery for CLI-only agents.** An agent with no MCP transport, no skill-description
  match and no literal `venvaxi` in the prompt now has no way to learn the tool exists. This is
  the real cost of the change. It is bounded: `setup` registers MCP unconditionally (gated only on
  `fastmcp`), and `specs/mcp/tools.md` already names MCP the primary ambient integration. If it
  bites, the fix is a stronger skill `description`, not a second channel.
- **`setup` now deletes content.** Bounded to the marked span and covered by the preservation
  tests, but a genuinely new class of behaviour for this command.
- **`--skill` stays opt-in.** After this change a bare `venvaxi setup` installs nothing
  agent-facing but MCP config. Making `--skill` the default is a defensible follow-on, deliberately
  not taken here because it widens the amendment past the clause this plan owns.
- **Retargeted tests can pass vacuously.** `plans/skill-parity-and-evals.md` records a preservation
  test that asserted against a substring the ambient body happened to contain. With that body
  deleted, assert against an explicit sentinel and confirm each retargeted test fails against the
  pre-change code.

## Notes

**Why the block is the channel to drop.** The project already stopped using it on itself. No
`venvaxi:begin` marker exists anywhere in this repo - the block was removed from `AGENTS.md` in
`b3bd320` and never restored - and `docs/architecture.md` states the reason out loud: `just
skill-sync` exists so the repo dogfoods its own installer "without `setup` also touching
`AGENTS.md` and `.mcp.json`". Routing around the injection is a tracked recipe, not an oversight.
`specs/mcp/tools.md` had already demoted it in writing, naming MCP registration "the primary
ambient integration".

**Why removal rather than leaving orphans.** Deleting `inject_agents_md` alone would leave every
repo that ever ran `setup` carrying a stale always-on block describing a workflow whose canonical
home has moved, with no signal that it is dead - the token cost of the channel without the
maintenance. The removal pass is a small function reusing splice logic that already exists and is
already tested.

**Why not shrink `ambient.md` to a discovery pointer instead.** Considered and rejected. It is the
cheaper change - `express-change`, no spec edit - and it preserves a mid-task nudge for non-MCP
agents at a fraction of the tokens. But it keeps a second delivery mechanism alive, with its enum,
its splice, its tests and its spec clause, for content that is near-entirely redundant. It makes
the tax smaller without removing anything.

**Why principle 7 does not move.** "Installed into the agent's session/hooks via an explicit setup
command" is silent on which session surface. `install_skill` and `_update_mcp_json` satisfy it as
`inject_agents_md` did. Of the four sites citing principle 7 - `specs/commands/setup.md`,
`specs/mcp/tools.md`, `specs/principles.md` and `src/venvaxi/_ambient.py` - only the last needs a
wording touch, and it is a docstring.

**There is no hook to remove.** Despite principle 7's "session/hooks" wording, this project has
never implemented a runtime hook; `.claude/settings.json` configures only `attribution` and
`enabledPlugins`. Ambient context here has always meant static files written once by `setup`.
Recorded because the principle's phrasing invites the opposite assumption.

**No stage output artifacts were produced for this run.** `stages/01-specification/output/`,
`02-implementation/output/` and `03-verification/output/` hold nothing for this slug - the run
went spec amendment straight through to implementation and verification without writing the
intermediate reports. The Validation evidence below was gathered directly (named tests, coverage,
live `setup` runs against seeded repos) and recorded here rather than in a stage 03 report, so
every ticked box cites what was actually executed. The gap is in the paper trail, not the
checking; it is recorded because stage 04's contract reads the stage 03 report as its input, and
a closeout that quietly substitutes its own evidence is the failure mode `plans/README.md` warns
about. `plans/skill-parity-and-evals.md` records the same class of gap at stage 02.

**Delivered as a stacked PR, not on #41.** The work was first aimed at #41, whose branch it was
written on. #41's plan was already `status: done` with that PR recorded, so landing a second
plan there would have made one PR deliver two. Branching from `develop` instead proved
impossible: this change depends on `_atomic_write_bytes`, `just skill-sync`,
`tests/test_skill_parity.py` and `.gitattributes`, none of which existed on `develop` until #41
merged. PR #42 was therefore stacked on `skill-parity-and-evals` and retargeted to `develop`
automatically once #41 landed.

**The plan carried an invalid status mid-run.** It was set to `in-review` between implementation
and closeout, which is the lifecycle for `ICM/*/stages/**/output/*.md`, not for a plan - the plan
lifecycle is `planned | in-progress | done | blocked | cancelled`, with no review state. Corrected
to `done` at closeout. Recorded because the wrong value would have been invisible to the
`status:` frontmatter queries every coverage check depends on.

## Follow-ups

- **Tracked as** - `--skill` as the default, with `--no-skill` to opt out. A bare `setup` now
  installs only MCP config, and whether that is too thin a default is a spec question this plan
  deliberately did not widen into. No issue or plan owns it yet; it needs one before it can be
  scheduled.
- **Tracked as** - a tenth eval case covering the removal pass. Case 8
  (`setup-is-not-a-diagnostic`) still holds - `setup` mutates, and more so now - but nothing in
  `.claude/skills/venvaxi/evals/evals.json` exercises the strip. Unowned.
- **Issue [#39](https://github.com/andyrids/venv-axi/issues/39)** - skill text vs code drift is
  still undetected. This plan edited the skill text again without adding such a check, so the
  risk it names grew slightly.
- **Issue [#40](https://github.com/andyrids/venv-axi/issues/40)** - the eval suite still runs
  nowhere. Unchanged by this plan.
