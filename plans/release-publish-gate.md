---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: [110]
pr:
---

# Plan: Release publish gate

## Scope

`.github/workflows/release.yml` triggers `build` -> `publish` on a GitHub Release event, entirely
independent of `.github/workflows/ci.yml`. Nothing in `release.yml` consults CI's result, so a
release can publish a commit CI is still validating, never ran on, or went red on. Verified in
this run against the Actions API:

| Tag | CI run | Sequence |
| --- | --- | --- |
| v0.4.0 (`858c943`) | success, ended `22:31:42Z` | Release at `22:31:29Z` - 13s before CI finished |
| v0.3.2 (`a3f1c593`) | success, run `32575536666` | CI concluded 2m38s earlier |
| v0.3.1 (`0d4e002`) | success | CI concluded 11m earlier |
| v0.2.0 (`1ad19d49`) | **none at all** | Published with nothing having validated it |

This unit adds a `verify-ci` job to `release.yml` that `build` now `needs` (`publish` already
`needs: build`, so it is gated transitively). The job resolves the newest `ci.yml` run for the
released commit's SHA, fails naming the SHA if none exists, waits for an in-flight run to
conclude, and fails unless it concluded `success`.

**Eligibility for `express-change`.** All three conditions in `ICM/express-change/CONTEXT.md`
hold.

1. **No spec change is required.** `specs/README.md` -> `## What specs cover` is observable
   behaviour of the tool - invocation, inputs, outputs, failure modes. This unit is CI/release
   configuration, the same class of change as the three preceding units in this sequence
   (`ci-platform-matrix`, `ci-conformance-tier`, `ci-static-typing`), none of which touched
   `specs/**`. Issue #110's own Scope section reaches the same conclusion, having checked
   `specs/commands/serve.md` and `docs/architecture.md`.
2. **One commit's worth**, with no new dependency and no new public surface. One new job in one
   file, using `gh` and `actions: read` permissions already available to the workflow token - no
   new action pinned, no source or test change.
3. **Every Validation criterion can be evidenced within this run.** Criteria 1-3 assert on the
   `verify-ci` script body run directly against real Actions API data (a SHA with no CI run, a
   cancelled run, a successful run) and are evidenced locally. Criterion 4 needs the branch pushed
   so `ci.yml` runs on it, which this run does not do (hard constraint: no push); it is evidenced
   in a follow-up pass once the branch is pushed and a run is in flight. Criterion 5 needs a real
   GitHub Release event and is not evidenceable by any run of this kind - it stays permanently
   unticked with the reason recorded in Notes, per the identical precedent
   `plans/ci-platform-matrix.md` set for its own un-triggered boxes.

## Implements

Nothing in `specs/**`; this is CI/release-configuration work, the same class of change as
`ci-platform-matrix`, `ci-conformance-tier` and `ci-static-typing`. `specs:` and `authors:` are
both empty for that reason.

## Approach

1. Open this plan at `status: in-progress`.
2. Add `verify-ci` to `.github/workflows/release.yml`: `runs-on: ubuntu-latest`,
   `timeout-minutes: 30`, `permissions: { contents: read, actions: read }`, no `checkout` and no
   `setup-uv` - it calls `gh api` only. One step resolves
   `repos/${GITHUB_REPOSITORY}/actions/workflows/ci.yml/runs?head_sha=${GITHUB_SHA}`'s
   `.workflow_runs[0].id`, fails naming `${GITHUB_SHA}` if empty, then polls
   `repos/${GITHUB_REPOSITORY}/actions/runs/${run_id}` for `.status == "completed"` (120 x 15s,
   matching `timeout-minutes: 30`) before reading `.conclusion` and failing unless it is
   `success`. `build` gains `needs: verify-ci`; `publish`'s existing `needs: build` gates it
   transitively. A comment above the job states why it exists.
3. **Deviation from the design as given.** The design handed to this run used
   `gh run watch "$run_id" --exit-status`. Mid-run, the coordinator flagged that `gh run watch`
   does not support fine-grained PATs for the `checks:read` permission it needs, per its own
   `--help` text, and that this cannot be checked locally: a developer's `gh` token is a
   broad-scope user token, so `gh run watch` would pass locally whether or not `actions: read`
   alone is sufficient for a workflow `GITHUB_TOKEN` on the runner. Replaced with an explicit poll
   over `GET /repos/{owner}/{repo}/actions/runs/{run_id}`, an endpoint `actions: read` is already
   known to cover, bounded to 120 iterations of 15s to match `timeout-minutes: 30`, and fail-closed
   on timeout (`.conclusion` is `null` while a run is not `completed`, and `null != "success"`).
4. Run the `verify-ci` step's script body locally, extracted from the committed YAML (not
   retyped), against: the no-CI SHA (criterion 1); run `34165306857`, cancelled (criterion 2); run
   `32575536666`, success (criterion 3). Capture exit codes and output verbatim.
5. Validate the YAML parses and that `build.needs == verify-ci`.
6. Add the `CHANGELOG.md` entry under `[Unreleased]` -> `Changed`, citing issue #110.
7. Report to the human that criterion 4 needs the branch pushed, which this run does not do
   (hard constraint). Stop with `status: in-progress`; criteria 1-3 ticked, 4 and 5 unticked.

## Validation

- [x] If no CI workflow run exists for the released commit, then the release workflow shall fail
      before building and shall name the commit it found nothing for. — script body run with
      `GITHUB_SHA=1ad19d49939547dd38b6303873d878186002054a`: exit 1,
      `::error::No CI run exists for 1ad19d49939547dd38b6303873d878186002054a - nothing has
      validated this commit`
- [x] If the CI workflow run for the released commit concluded anything other than success, then
      the release workflow shall fail before building. — poll+conclusion portion of the script
      run with `run_id=34165306857` (a real cancelled run): exit 1,
      `::error::CI run 34165306857 for 34165306857-sha-placeholder concluded cancelled`
- [x] When the CI workflow run for the released commit concluded success, the release workflow
      shall proceed to build. — poll+conclusion portion of the script run with
      `run_id=32575536666` (a real successful run): exit 0, `gate passed`
- [ ] While a CI workflow run for the released commit is still in progress, the release workflow
      shall wait for it to conclude rather than building alongside it.
- [ ] If the gate job fails, then the build and publish jobs shall not run.

## Risks / unknowns

- **Criterion 4 needs the branch pushed.** This run makes no commit and no push (hard
  constraint). Evidencing it requires running the gate against the branch head while `ci.yml` is
  in flight on it, which can only happen after a human pushes. Stays unticked until that pass.
- **Criterion 5 needs a real GitHub Release event.** No run of this kind - local script execution,
  or even a pushed branch's CI run - produces a `release` event. It is not deferred to a specific
  future plan; the next real release is what evidences it, tracked in Follow-ups.
- **The gate's own permission surface is asserted, not tested.** `actions: read` is believed
  sufficient for `GET /repos/{owner}/{repo}/actions/runs/{run_id}` on a workflow `GITHUB_TOKEN`,
  reasoning from GitHub's REST API documentation for that endpoint's minimum scope. Nothing in
  this run exercises the gate under an actual `GITHUB_TOKEN` with exactly `{contents: read,
  actions: read}` - a developer's `gh` token is broader and cannot distinguish a correct
  permission set from an insufficient one. This is the same blind spot as criterion 5: only a
  real workflow run, on this job, on the runner, closes it.
- **`continue-on-error` on a CI job could let a run conclude `success` with a failing job.** The
  gate reads the run's overall `conclusion`, which GitHub computes as `success` only when every
  job succeeded - unless a job in `ci.yml` is marked `continue-on-error: true`, in which case its
  failure does not flip the run's conclusion. No job in `ci.yml` carries that flag today; the risk
  is against a future edit to that file, which this plan does not touch.

## Notes

**Why the gate reads the workflow run's conclusion rather than naming individual check runs.**
Three frozen plans in this sequence left a follow-up for #110 predicting it would need to name
check runs by string: `ci-platform-matrix` (`pytest (ubuntu-latest)` / `pytest (windows-latest)`),
`ci-conformance-tier` (adding `conformance (ubuntu-latest)` / `conformance (windows-latest)`), and
`ci-static-typing` (renaming `ruff-lint` to `static`) - each one warning that the published names
would keep drifting under the gate. `verify-ci` names none of them. It asks the Actions API for
`ci.yml`'s own run against the released SHA and reads that run's `conclusion`, which GitHub
computes as `success` only when every job in the run succeeded. A job renamed, added or removed in
`ci.yml` changes nothing the gate reads, so those three follow-ups are discharged by being made
unnecessary rather than by being separately actioned. The concrete cases this closes are the two
recorded in Scope: the v0.4.0 race, where the release event fired 13 seconds before CI's own run
for that commit had concluded, and v0.2.0, published with no CI run for its commit at all - both
are exactly what "no run found" and "run not yet `completed`" catch. Conservative-by-construction:
`.workflow_runs[0]` is the newest run for the SHA (the API returns newest-first), so a re-run after
an initial failure is what the gate sees, never a stale earlier attempt. The residual risk -
`continue-on-error` masking a failing job inside an otherwise-`success` conclusion - is recorded
above rather than guarded against, since nothing in `ci.yml` uses it today and guarding a
hypothetical would be scope this plan was not chartered to take on.

**Design deviation: `gh run watch --exit-status` replaced with an explicit poll, mid-run.** The
design handed to this run used `gh run watch`. The coordinator flagged, before this plan closed,
that `gh run watch --help` states it does not support fine-grained PATs because a PAT cannot carry
`checks:read`, and that the job's `permissions:` block grants exactly `{contents: read, actions:
read}` - no `checks: read`. If `gh run watch` reaches the Checks API rather than staying on the
Actions API, the gate would fail closed on every release, which is safe but also means nothing
would ever publish and nobody would find out until the next real release attempted it - exactly
the case criterion 5 cannot evidence in advance. Critically, this could not have been settled by
testing locally: a developer's `gh` token (mine, or the coordinator's) is a broad-scope user
token, so `gh run watch` passes locally regardless of whether `actions: read` alone would suffice
for a workflow `GITHUB_TOKEN` on the runner - local evidence cannot distinguish the two
mechanisms. Replaced with an explicit poll of `GET
/repos/{owner}/{repo}/actions/runs/{run_id}`, the same endpoint the criterion-2 and -3 evidence
above already exercises `--jq '.status'` / `.conclusion` against, documented as covered by
`actions: read`. Bounded to 120 iterations at 15s to match the job's `timeout-minutes: 30`, and
fail-closed on timeout: a run that never reaches `completed` leaves `.conclusion` at `null`, and
`null != "success"` fails the step rather than falling through. Criteria 2 and 3 above are now
evidenced by running this poll logic directly - extracted verbatim from the committed YAML -
against real run ids, which exercises the code that ships rather than a hand-typed approximation
of it.

**Job needs no `checkout` and no `setup-uv`.** It calls `gh api` only, which is preinstalled on
GitHub-hosted runners and authenticates from `GH_TOKEN: ${{ github.token }}`; nothing it does
touches the repository checkout or the Python toolchain.

## Follow-ups

- **Issue** [#136](https://github.com/andyrids/venv-axi/issues/136) - `pypi` environment
  protection rules are empty (`gh api repos/andyrids/venv-axi/environments`), `main` has no
  branch protection (404 on `branches/main/protection`), and the repository's one ruleset (id
  `20529102`) enforces only `deletion` and `non_fast_forward` with no required status checks.
  `verify-ci` is the mechanical half of #110's two resolutions; this is the settings half, filed
  separately because it changes GitHub configuration rather than a file in the repository.
- **Tracked as** - the next real GitHub Release is what evidences criterion 5 (`If the gate job
  fails, then the build and publish jobs shall not run`) and, alongside it, whether `actions:
  read` is in fact sufficient for the poll endpoint under a real `GITHUB_TOKEN` (see Risks /
  unknowns). Neither can be produced by any run short of an actual release event.
- **Deferred to** - none. No downstream plan needs editing for this unit.
