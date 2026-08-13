---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs: []
authors: []
issues: []
pr: 35
---

# Plan: Repair the pre-release record

## Scope

Close four defects found by a pre-release review of `develop` at `c2f8b8e`, run as the gate on
the v0.2.0 merge into `main`: a repo-local slash command citing a deleted workspace, a v0.2.0
CHANGELOG section that documents one of the two merged PRs, a README link to a heading that no
longer exists, and an invalid GitHub activity type in the release workflow.

Out of scope, both raised by the same review and both deliberately left:

- `specs/README.md` naming the `spec-drift-auditor` agent, now supplied by the `icm@icm-spec`
  plugin rather than by `.claude/agents/`. The reference still resolves, and the file is
  `immutable: true` - amending the factory configuration on the way past a release is exactly what
  that flag exists to stop.
- `ci.yml` running two of the eight hooks in `prek.toml`. PyMarkdown, Mypy and detect-secrets are
  local-only, so a regression in any of them lands green. Real, but it is a workflow change with
  its own risk surface and it wants its own plan.

**Eligibility for express-change.** All three conditions in `ICM/express-change/CONTEXT.md` hold.
No `specs/**` file changes - the one item that would have moved a spec is excluded above - so the
first condition passes on its 'touches nothing specs cover' branch, which is why `specs:` is
empty rather than populated. It is one commit's worth, with no new dependency and no new public
surface. Every criterion below is evidenced within this run.

## Implements

Nothing. This plan implements no spec and authors none. It repairs the tracked record and two
pieces of configuration that reference deleted paths, ahead of the v0.2.0 release.

## Approach

1. Open this plan at `status: in-progress`.
2. Delete `.claude/commands/create-feature.md`. `ICM/create-feature/` was replaced by
   `ICM/process-plan/` and `ICM/express-change/` in
   [spec-conformance-sweep](spec-conformance-sweep.md); the command still instructs the agent to
   read the deleted `ICM/create-feature/CONTEXT.md`. `CONTEXT.md` already routes to both new
   workspaces and the plugin supplies the entry points, so nothing replaces it.
3. Backfill the v0.2.0 CHANGELOG section. It carries `Changed` and `Fixed` for
   [PR #34](https://github.com/andyrids/venv-axi/pull/34) and nothing for
   [PR #33](https://github.com/andyrids/venv-axi/pull/33), the larger of the two merges in
   `main..develop`. Add `Added`, extend `Changed`, and add `Removed` per
   `ICM/_config/reference-standard-changelog.md`.
4. Retarget the `README.md` link that points at `AGENTS.md#routing`. That heading was removed when
   `AGENTS.md` was rewritten; the surrounding sentence is directing the reader to `CONTEXT.md`, so
   the link should be `CONTEXT.md` and the sentence should stop naming a section.
5. Correct `types: [published, prerelease]` in `.github/workflows/release.yml`. GitHub's `release`
   event has no `prerelease` activity type - the real one is `prereleased` - so the entry is inert
   and the comment above it claims a trigger that does not exist.

## Validation

- [x] No file under `.claude/` shall reference a path beneath `ICM/create-feature/`. —
      `grep -rn "ICM/create-feature" .claude/` reports no match
- [x] Where the repository defines a slash command, the workspace `CONTEXT.md` that command
      instructs the agent to read shall exist. — `git ls-files .claude/commands/` lists only
      `.gitkeep`, so the condition holds vacuously; the two workspace files a command could name,
      `ICM/process-plan/CONTEXT.md` and `ICM/express-change/CONTEXT.md`, both exist
- [x] The `v0.2.0` section of `CHANGELOG.md` shall record the pipeline split, the
      `specs/architecture.md` split and the `.claude/` tooling move, under the section headings
      `ICM/_config/reference-standard-changelog.md` names. — the section now carries `Added`,
      `Changed`, `Removed` and `Fixed`; the split is under `Changed`, and both the
      `specs/architecture.md` split and the plugin move under `Removed`
- [x] Every relative link in `README.md` that targets a heading anchor shall resolve to a heading
      present in the linked file. — `grep -oE '\]\([^)h][^)]*#[^)]*\)' README.md` reports no
      match; the four remaining relative links target `AGENTS.md`, `CONTEXT.md`,
      `specs/README.md` and `plans/README.md`, all of which exist
- [x] Each activity type named under `on.release.types` in `.github/workflows/release.yml` shall
      be one GitHub defines for the `release` event. — the list reads
      `types: [published, prereleased]`, both defined for the `release` event
- [x] The test suite and the eight-hook gate shall both pass unchanged over the edited tree. —
      `uv run coverage run -m pytest` reports `293 passed`, coverage `98%`, unchanged from
      `c2f8b8e`; `uv run -m prek run --all-files` passes all eight hooks

## Risks / unknowns

- Deleting the only tracked slash command leaves `.claude/commands/` empty but for its `.gitkeep`.
  That is the correct end state while the pipeline entry points come from the plugin, and it is
  recorded in the CHANGELOG so a consumer meets the removal rather than discovering it.
- Backfilling a CHANGELOG section for a PR that merged three commits ago risks describing the
  change from the diff rather than from its intent. Each entry added here traces to a decision
  recorded in [spec-conformance-sweep](spec-conformance-sweep.md), not to the diff alone.
- New markdown risks the PyMarkdown tokenizer crash in
  [#20](https://github.com/andyrids/venv-axi/issues/20). No pipe characters were placed in nested
  list items.

## Notes

**Why a plan at all for four one-line fixes.** `plans/README.md` is explicit that skipping the
plan because a change is quick is what hollows the record out, and the express pipeline exists so
the fast path is a shorter pipeline rather than a plan-free one. Three of the four defects here
were themselves record defects - a command citing a deleted path, a CHANGELOG section missing a
PR, a link to a removed heading - so landing them without a record would have been the failure
mode reproducing itself.

**The review that found these ran wider than its findings.** Test suite, coverage, the eight-hook
gate, remote sync, merge topology, plan statuses, `specs/` Invariant 1 and a CLI smoke test all
passed. That matters for the release gate: the four defects below are the whole delta, not the
first four found. The Invariant 1 check was computed from `specs:` and `authors:` frontmatter
only - a whole-file grep passes falsely, which `plans/README.md` records as the trap the
methodology walked into on first use.

**`.claude/commands/` keeps a `.gitkeep`.** Deleting the only tracked command would otherwise
delete the directory. `.claude/agents/` and `.claude/skills/` were left with `.gitkeep` files when
[spec-conformance-sweep](spec-conformance-sweep.md) emptied them, and this follows that
convention rather than inventing a second one.

**The `prereleased` fix changes no observable behaviour today.** `published` already fires for a
prerelease, which is why v0.1.0 shipped with the typo in place. It is corrected because a workflow
whose comment claims a trigger it does not have is a trap for whoever next edits it, not because
the release is currently broken.

**Why `specs:` and `authors:` are both empty.** The change conforms to nothing under `specs/` -
`.claude/`, `CHANGELOG.md`, `README.md` and `.github/` are not surfaces specs cover. Populating
either field to look complete would put a false owner into the Invariant 1 coverage check, which
reads exactly these two fields. The same reasoning as
[plan-record-repair](plan-record-repair.md).

**Closeout order.** This plan held at `in-progress` with every box ticked until
[PR #35](https://github.com/andyrids/venv-axi/pull/35) existed, so `pr:` carries a real number and
this stays the last commit before merge - the order the five plans in PR #34 used, for the same
reason.

## Follow-ups

- **Issue** - none filed. The two defects left unfixed are recorded in Scope and named below
  rather than filed, because both are owned by the release sequence rather than left ownerless.
- **Deferred to** - none. Neither excluded item has an unstarted downstream plan to absorb it, so
  neither is written as a deferral; a `Deferred to` with no plan to bind is the defect
  [plan-record-repair](plan-record-repair.md) was opened to correct.
- **Tracked as** - two items, both deliberate exclusions from Scope. `ci.yml` runs two of the
  eight hooks in `prek.toml`, leaving PyMarkdown, Mypy and detect-secrets local-only; and
  `specs/README.md` names the `spec-drift-auditor` agent now supplied by the `icm@icm-spec`
  plugin. Neither blocks v0.2.0. The first wants its own plan after the release; the second is an
  `immutable: true` amendment and should be taken deliberately.
- **Tracked as** - issues [#28](https://github.com/andyrids/venv-axi/issues/28) to
  [#31](https://github.com/andyrids/venv-axi/issues/31) are fixed on `develop` but still open.
  PR #34's closing keywords did not fire because it merged into `develop`, and GitHub only
  auto-closes on a merge into the default branch. The `develop` to `main` release PR body must
  carry them, or the four close by hand after the release.
