---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs: []
authors: []
issues: []
pr: 75
---

# Plan: release-0-3-1

## Scope

Prepare the `0.3.1` release record. `0.3.1` is `v0.3.0rc2` verbatim - no code change - promoted
from prerelease to final because PyPI's `info.version` (latest stable) reads `0.2.0` while both
`0.3.0rc*` stay classified as prereleases, so a plain `pip install venv-axi` today gets `0.2.0`,
which still crashes `tree numpy` (issue 64). `0.3.0` itself can never be re-published - PyPI
reserves an uploaded filename permanently once removed - so `0.3.1` is the first installable
**stable** release since `0.2.0`.

`develop` is exactly two commits ahead of tag `v0.3.0rc2` (`e02eeff`, `818a19e`), both
documentation-only, confirmed by `git diff v0.3.0rc2..develop -- specs/ src/ tests/` reporting no
output. In scope: `CHANGELOG.md` and this plan. Out of scope: the tag, the GitHub release and the
PyPI publish - irreversible steps reserved for the maintainer's explicit authorisation, listed
under Notes rather than performed here.

**Eligibility for express-change.** All three conditions in `ICM/express-change/CONTEXT.md` hold.
No `specs/**` change is required - `git diff v0.3.0rc2..develop -- specs/` is empty, and this
plan changes no behaviour for `specs/**` to describe, so `specs:` and `authors:` both stay empty.
It is one commit's worth of work, with no new dependency and no new public surface - there is no
code delta to introduce either. Every criterion below is evidenced within this run.

## Implements

Nothing in `specs/**`; this plan is release-record maintenance, the same class of work as
[withdraw-0-3-0](withdraw-0-3-0.md). It follows the convention that plan established: each
`CHANGELOG.md` section records what a given published artifact contains, with a `[!NOTE]` block
where the reason is not obvious from the diff alone.

## Approach

1. Open this plan at `status: in-progress`.
2. Add a `## [0.3.1] - 2026-08-22` section at the top of `CHANGELOG.md`, immediately above
   `## [0.3.0rc2]`, carrying a `[!NOTE]` block - precedent: the `[0.3.0rc1]` NOTE at
   `CHANGELOG.md:118` - stating that `0.3.1` promotes `0.3.0rc2` to final with no changes of its
   own, and that it is the first installable stable release since `0.2.0` because `0.3.0` was
   removed rather than yanked. No `### Added`/`### Changed`/`### Fixed` bullets: there is no code
   delta to record, and inventing one would misstate the release.
3. Correct the `[0.3.0]` NOTE (`CHANGELOG.md:50`), which reads "the eventual final release is
   `0.3.1`" in future tense - true when `withdraw-0-3-0` wrote it, stale now that `0.3.1` exists.
   Amend to past/present tense, minimally, in the same voice.
4. Confirm no link-reference block sits at the foot of `CHANGELOG.md` needing a new entry for the
   `[0.3.1]` heading - the file uses inline bracket headings throughout, not reference-style
   links.
5. Run the full test suite and the markdown linter per the toolchain references, capture output
   verbatim, and report each Validation criterion against it.
6. Close the plan out per `plans/README.md`.

## Validation

- [x] The `CHANGELOG.md` file shall contain a `## [0.3.1] - 2026-08-22` section immediately above
      `## [0.3.0rc2]`. — `grep -n '^## \[' CHANGELOG.md` lists `33:## [0.3.1] - 2026-08-22`
      directly above `42:## [0.3.0rc2] - 2026-08-21` (shifted from `19`/`28` by the `## [0.3.2]`
      section #76 and #77 later inserted above this one; re-verified during the 0.3.2 release
      audit, `plans/release-0-3-2.md`)
- [x] The `[0.3.1]` section shall state, via a `[!NOTE]` block, that `0.3.1` promotes `0.3.0rc2`
      to final with no changes of its own, and that it is the first installable stable release
      since `0.2.0` because `0.3.0` was removed rather than yanked. — `CHANGELOG.md:33-40`, the
      `[0.3.1]` `[!NOTE]` block (line numbers re-verified per the note above)
- [x] The `[0.3.1]` section shall carry no `### Added`/`### Changed`/`### Fixed`/`### Removed`
      bullets, matching the zero code delta between `v0.3.0rc2` and this branch. —
      `CHANGELOG.md:33-41`, NOTE block only, no heading below it before `## [0.3.0rc2]`
      (line numbers re-verified per the note above)
- [x] The `[0.3.0]` NOTE shall describe `0.3.1` in past/present tense rather than as "the eventual
      final release". — `CHANGELOG.md:79-80` now reads "its final release is `0.3.1` above"
      (line numbers re-verified per the note above)
- [x] `git diff v0.3.0rc2..HEAD -- src/ tests/ specs/` shall report no output, evidencing this
      release is code-identical to `v0.3.0rc2`. — command run, no output
- [x] The full `pytest` suite shall pass with zero failures. — `uv run pytest -v`: `359 passed in
      28.55s`
- [x] The markdown lint shall pass over the edited `CHANGELOG.md`. — `uv run pkgdx-markdown-hook
      CHANGELOG.md` exits 0; `uv run -m prek run --all-files` reports `Check Markdown
      [PyMarkdown]..............................................Passed` alongside all seven other
      hooks

## Risks / unknowns

- Editing a frozen plan's neighbour section (`[0.3.0]`) rather than a frozen plan itself: the
  `[0.3.0]` CHANGELOG section is not itself a frozen plan, so `plans/README.md`'s freeze rule does
  not gate this edit, but the change is still kept minimal and in the existing voice to avoid
  rewriting settled record.
- New markdown risks the PyMarkdown tokenizer crash in
  [#20](https://github.com/andyrids/venv-axi/issues/20) (a pipe inside a nested list item). No
  pipe characters are placed in nested list items in this change; `or` is used instead where the
  meaning would otherwise need `|`.

## Notes

- **Validation citations repaired during the 0.3.2 audit.** The four `CHANGELOG.md:<line>`
  citations above pointed at `[0.3.1]`'s position when this plan closed (heading at line `19`).
  `#76` and `#77` later inserted a `## [0.3.2]` section above it, shifting every line by `+14`;
  the citations were re-pointed to the current lines by
  [release-0-3-2](release-0-3-2.md), per `plans/README.md`'s "edit only to correct the record"
  allowance for a frozen plan. No claim changed - only the line numbers a future reader would
  re-run to check them.
- **Why no code diff at all.** `develop` sat exactly two commits ahead of `v0.3.0rc2`
  (`e02eeff`, `818a19e`), both documentation-only, before this plan opened - confirmed by
  `git diff v0.3.0rc2..develop -- specs/ src/ tests/` reporting no output. `0.3.1` is therefore
  a pure release-classification promotion: the same tree `v0.3.0rc2` tagged, republished as a
  stable version number so `pip install venv-axi` (no `pre-release` flag) stops resolving to
  `0.2.0`.
- **Why `specs:` and `authors:` are both empty.** This plan changes no behaviour for `specs/**`
  to describe and authors no spec - same reasoning as
  [plan-record-repair](plan-record-repair.md)'s Notes on the same question. Populating either
  field would put a false owner into the Invariant 1 coverage check.
- **`pr:` is [75](https://github.com/andyrids/venv-axi/pull/75)**, set in the last commit before
  merge per `plans/README.md` Closeout, so this plan freezes with its PR recorded rather than
  with the field blank.
- **Out-of-repo release steps - none performed by this run**, listed so the record is explicit
  about what still requires the maintainer's authorisation:
  1. Merge this branch's commit to `develop`.
  2. Tag `v0.3.1` from the merge commit and push the tag.
  3. Publish the tag as a GitHub **release** (not a pre-release) - this is what moves PyPI's
     `info.version` to `0.3.1` once the release workflow runs.
  4. Confirm `https://pypi.org/pypi/venv-axi/json` reports `info.version: "0.3.1"` and that a
     plain `pip install venv-axi` resolves to it.
- Toolchain commands run exactly as `ICM/_config/reference-toolchain-pytest.md`,
  `reference-toolchain-pymarkdown.md` and `reference-toolchain-prek.md` define them; no deviation
  or invocation not named in those references was used.

## Follow-ups

- Tracked as: the four out-of-repo release steps above - external actions on GitHub and PyPI,
  owned by the user, evidenced nowhere in this repo.
- None beyond the above. No issue is opened, no downstream plan absorbs anything from this run,
  and this plan's scope is fully discharged in-repo.
