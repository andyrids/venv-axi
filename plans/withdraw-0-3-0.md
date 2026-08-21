---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends:
  - import-crash-containment
  - malformed-package-name
  - definitive-answers
specs: []
authors: []
issues: []
pr: 70
---

# Plan: withdraw-0-3-0

## Scope

Withdraw the `0.3.0` release and record `0.3.0rc2` as its successor. `0.3.0` ships two defects
severe enough to pull rather than supersede: issue 64 crashes `tree numpy` at an ordinary
`max_depth` and drops the MCP connection, and issue 66 withholds the signature on the headline
use case. PyPI reserves an uploaded filename permanently, so `0.3.0` is spent either way -
yanking is chosen over deleting because it is reversible, keeps pinned installs working, and
keeps the record honest. The eventual final release is `0.3.1`.

Express-change: the in-repo work is `CHANGELOG.md` plus this plan, which no spec covers. The
release mechanics - the PyPI yank, the GitHub release demotion, the `v0.3.0rc2` tag - are
manual, out-of-repo steps listed under Notes at closeout; none of them lands in this diff.

In scope: the `[YANKED]` record for `0.3.0`, the `[0.3.0rc2]` section listing rc2's four
fixes (issues 64, 65, 66, 69). Out of scope: the fixes themselves - owned by the three plans
this one depends on - and the `0.3.1` final release.

## Implements

Nothing in `specs/**`; this plan is release-record maintenance. It follows the convention the
`0.3.0` changelog collapse established: each section records what that published artifact
contains, with a NOTE block where it is not obvious.

## Approach

- Suffix the `[0.3.0]` heading with `[YANKED]` (the Keep a Changelog convention), keep its
  content verbatim, and add a NOTE naming the withdrawal reason, the yank, the superseding
  `0.3.0rc2`, and that `0.3.0` is never re-published.
- Add `[0.3.0rc2]` above it, listing only rc2's own fixes - one `Fixed` bullet per issue -
  with a NOTE that it supersedes the yanked `0.3.0` and carries everything that release did.
- This plan's CHANGELOG section doubles as the changelog entry for the three fix plans it
  depends on; it merges only after all three land, and the rc2 date is corrected to the tag
  date at closeout if they differ.

## Validation

- [x] The `[0.3.0]` heading carries the `[YANKED]` suffix and the section's content below its
      NOTE stands verbatim. — `git diff CHANGELOG.md` (heading suffix and NOTE insertion
      only; every 0.3.0 content line untouched)
- [x] The NOTE under `[0.3.0]` names the withdrawal reason (issues 64 and 66), the yank, the
      superseding `0.3.0rc2`, and that `0.3.0` is never re-published. — `CHANGELOG.md`,
      `[0.3.0]` NOTE block
- [x] The `[0.3.0rc2]` section lists only rc2's own fixes - issues 64, 65, 66 and 69 - and
      its NOTE states that it supersedes the yanked `0.3.0` and carries its content. —
      `CHANGELOG.md`, `[0.3.0rc2]`; each bullet verified against the landed tree, with live
      checks `venvaxi show ""` (exit 1, `Invalid package name`) and
      `venvaxi find e --package rich --limit 2` (capped hint present)
- [x] The markdown lint passes over the edited `CHANGELOG.md`. —
      `uv run pkgdx-markdown-hook CHANGELOG.md` (clean)

## Risks / unknowns

- The rc2 section is written ahead of the fixes it describes: this plan depends on the three
  fix plans and must not merge before them, or the record claims fixes the tree does not hold.
- The rc2 date is written as 2026-08-21; if the `v0.3.0rc2` tag is cut later, the date must
  be corrected in the closeout commit.
- Yank state lives on PyPI, not in this repo - nothing here can evidence step completion; the
  out-of-repo checklist lands in Notes at closeout as the durable record of what was done.

## Notes

- The withdrawal was executed as a PyPI **deletion**, not the yank this plan proposed.
  Both spend the version number permanently, so `0.3.1` remains the eventual final
  either way, but deletion is irreversible and breaks anyone who had pinned `0.3.0`.
  The `[0.3.0]` NOTE in `CHANGELOG.md` was corrected from 'Yanked on PyPI' to
  'Removed from PyPI' to match. The `[YANKED]` heading suffix stays: it is Keep a
  Changelog's only marker for a withdrawn release, and no `[DELETED]` convention
  exists.
- The three fix plans this record depends on have all landed in the tree
  (`import-crash-containment`, `malformed-package-name`, `definitive-answers`), so every rc2
  bullet describes behaviour the tree now holds. One bullet was corrected mid-run: #66's
  'pass `--refresh` once' became the schema-bump automatic rebuild after
  `definitive-answers`' re-entry landed `SCHEMA_VERSION = 6`.
- The rc2 date is written as 2026-08-21; correct it in this file and `CHANGELOG.md` if the
  `v0.3.0rc2` tag is cut on a later day.
- `CHANGELOG.md` has no link-reference block at its foot, so the `[YANKED]` and `[0.3.0rc2]`
  bracket forms need no reference definitions; the file-head `<!-- pyml disable MD024 -->`
  pragma still covers the duplicated `### Fixed`/`### Added` headings.
- Out-of-repo release checklist (all manual, none performed by this run), in order:
  1. PyPI -> `venv-axi` -> Manage -> Releases -> `0.3.0` -> **Yank** (not Delete), reason
     naming issue 64.
  2. GitHub release `v0.3.0` -> Edit -> set as pre-release, untick 'latest', retitle as
     withdrawn, prepend a note pointing at `v0.3.0rc2` and issue 64. Keep the `v0.3.0` tag.
  3. Merge the three fix plans and this CHANGELOG commit to `develop`.
  4. Tag `v0.3.0rc2` and publish it as a GitHub **pre-release**; the release workflow fires
     on `prereleased` and publishes to PyPI via Trusted Publishing.
  5. Confirm PyPI shows `0.3.0rc2` and strikes `0.3.0` through as yanked, then re-run the
     four #64-#69 reproductions from the consuming project.
- `pr:` is left empty deliberately: no PR exists yet; the user raises it and fills the field.

## Follow-ups

- Tracked as: the five out-of-repo release steps above - external actions on PyPI and
  GitHub, owned by the user, evidenced nowhere in this repo.
- Issue [#67](https://github.com/andyrids/venv-axi/issues/67),
  issue [#68](https://github.com/andyrids/venv-axi/issues/68) and
  issue [#49](https://github.com/andyrids/venv-axi/issues/49) - actionable, owned by no
  current plan; recommended for the 0.4.0 milestone, with #68 and #49 sharing one design
  question that goes through specification together.
- The eventual `0.3.1` final release - rc2 is this record's deliverable.
