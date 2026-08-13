---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: []
pr:
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

- [ ] No file under `.claude/` shall reference a path beneath `ICM/create-feature/`.
- [ ] Where the repository defines a slash command, the workspace `CONTEXT.md` that command
      instructs the agent to read shall exist.
- [ ] The `v0.2.0` section of `CHANGELOG.md` shall record the pipeline split, the
      `specs/architecture.md` split and the `.claude/` tooling move, under the section headings
      `ICM/_config/reference-standard-changelog.md` names.
- [ ] Every relative link in `README.md` that targets a heading anchor shall resolve to a heading
      present in the linked file.
- [ ] Each activity type named under `on.release.types` in `.github/workflows/release.yml` shall
      be one GitHub defines for the `release` event.
- [ ] The test suite and the eight-hook gate shall both pass unchanged over the edited tree.

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

## Follow-ups
