---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs: []
authors: []
issues: []
pr:
---

# Plan: release-0-3-2

## Scope

Audit `develop` for release readiness ahead of tagging `v0.3.2` - the patch already recorded at
`## [0.3.2]` in `CHANGELOG.md`, carrying #76 (reject a negative `find` limit) and #77 (correct two
packaged-skill gotchas) - and fix only what the audit finds defective. This is a verification pass
before an irreversible publish: PyPI reserves an uploaded filename permanently, so a defect caught
here is cheap and one caught after publish is not.

**Eligibility for express-change.** All three conditions in `ICM/express-change/CONTEXT.md` hold.
No `specs/**` change is required - both defects found are a stale plan citation and a build/VCS
configuration gap, neither of which `specs/**` covers. It is one commit's worth of work, with no
new dependency and no new public surface. Every Validation criterion below is evidenced within
this run.

Two defects were found and are in scope to fix:

1. **Stale Validation citations in [release-0-3-1](release-0-3-1.md).** Its four
   `CHANGELOG.md:<line>` citations pointed at `[0.3.1]`'s position when that plan closed (heading
   at line 19). `#76` and `#77` each inserted content above it - a new `## [0.3.2]` section - and
   together shifted every line below by `+14`. A stale citation is exactly the "ticked box that
   was not checked" failure `plans/README.md` warns about, so it is repaired here rather than left
   for the next reader to discover mid-verification.
2. **The published sdist bundles stray local content.** `.claude/worktrees/` and
   `.claude/scheduled_tasks.lock` are Claude Code runtime artifacts excluded only via
   `.git/info/exclude` - a local, unshared file `hatch-vcs`/`hatchling`'s sdist builder does not
   consult. The tracked `.gitignore` has no equivalent entry, so `uv build` on this checkout
   bundled two full stray worktree copies into the sdist: 305 of 457 files, ballooning it from
   roughly 400 KB to 1.2 MB. This is a systemic gap, not an artifact of one machine's mess: any
   clone or CI runner that has accumulated the same ordinary Claude Code runtime state at build
   time reproduces it, because the root cause is the tracked `.gitignore` never having named these
   paths.

One additional finding was investigated and is **out of scope**, left unfixed deliberately: the
`search_like.sql` fallback path (used when SQLite's FTS5 extension is unavailable) matches `name`
and `qualified_name` only, never `doc`, silently narrowing `specs/commands/find.md`'s "searched
over name and docstring text" data requirement whenever FTS5 is off. It is a real, pre-existing
Invariant 2 divergence - confirmed live, not latent, since `_store.py` deliberately catches
`sqlite3.OperationalError` on FTS5 schema creation and falls back - but it predates every unit in
this release, is untracked by any existing issue, and is a behavioural SQL change with its own
test surface, not a release-record fix. Widening this plan to carry it would repeat the mistake
`plans/find-limit-lower-bound.md`'s Notes names for issue #68: "correcting it would widen this
plan past the scope stage 01 set." It is filed below as a Follow-up instead.

Out of scope, per the task's own boundary: anything belonging to issues #67, #68, #49, #50 or
#71 - 0.4.0 work - and any change to `pyproject.toml`'s version configuration, a tag, a GitHub
release, or a PyPI publish, all of which remain the maintainer's explicit authorisation to take.

## Implements

Nothing in `specs/**`; this plan is release-record and build-hygiene maintenance, the same class
of work as [plan-record-repair](plan-record-repair.md) and [release-0-3-1](release-0-3-1.md).

## Approach

1. Open this plan at `status: in-progress`.
2. Re-read `CHANGELOG.md`'s `[0.3.2]` section against the real diffs of `997622d` (#76) and
   `0c516f2` (#77), and confirm the `[0.3.1]` section beneath it is untouched by the merge - no
   defect found; both bullets match their commits and the `[0.3.1]` section is byte-identical to
   its content at `0d4e002`.
3. Recompute `release-0-3-1.md`'s four stale `CHANGELOG.md:<line>` Validation citations against
   the file's current state and correct them in place, per `plans/README.md`'s "edit only to
   correct the record" allowance for a frozen plan - no claim in any citation changes, only the
   line numbers a future reader would re-run to check them.
4. Reproduce the sdist leak (`uv build`, inspect the `.tar.gz` with `tarfile`), trace it to the
   tracked `.gitignore` lacking the Claude Code runtime paths `.git/info/exclude` already carries
   locally, and add the missing entries to `.gitignore`.
5. Rebuild and confirm the sdist no longer carries `.claude/worktrees/` or
   `.claude/scheduled_tasks.lock`, and that the wheel's `venvaxi/SKILL.md` remains byte-identical
   to `src/venvaxi/SKILL.md` (the #77 fix reaching the shipped artifact, unaffected by this
   change).
6. Run the full toolchain - `uv run pytest -v`, `uv run coverage run -m pytest` /
   `uv run coverage report`, `uv run prek run --all-files` - and capture output verbatim.
7. Delete the build artifacts this run produced from `dist/` (untracked; `dist/` is gitignored
   and not part of any commit).
8. Close this plan out per `plans/README.md`.

## Validation

- [x] `plans/release-0-3-1.md`'s four `CHANGELOG.md:<line>` Validation citations shall resolve to
      the content they claim to evidence, at `CHANGELOG.md`'s current state. —
      `grep -n '^## \[' CHANGELOG.md` returns `33:## [0.3.1] - 2026-08-22` and
      `42:## [0.3.0rc2] - 2026-08-21`; `sed -n '33,41p' CHANGELOG.md` shows the `[0.3.1]` heading
      and `[!NOTE]` block with no `###` heading before the blank line at 41; `sed -n '79,80p'
      CHANGELOG.md` reads "...and its final release\n> is `0.3.1` above."
- [x] The `[0.3.2]` `CHANGELOG.md` section shall accurately describe #76 and #77, in merge order,
      matching house style. — `git show 997622d -- CHANGELOG.md` and
      `git show 0c516f2 -- CHANGELOG.md` compared line-by-line against the `[0.3.2]` bullets;
      issue 73 (#76) precedes issue 74 (#77), matching commit order `997622d` before `0c516f2`;
      wording, `(issue N)` citation style and line width (91-97 chars) match the `[0.3.0rc2]`
      section immediately below
- [x] The `[0.3.1]` `CHANGELOG.md` section shall be unchanged by the `[0.3.2]` merge. —
      `diff <(sed -n '33,40p' CHANGELOG.md) <(git show 0d4e002:CHANGELOG.md | sed -n '19,26p')`
      reports no difference
- [x] Every spec under `specs/**` shall be covered by a committed plan's `specs:` or `authors:`
      frontmatter field (Invariant 1). — for each of the 17 spec files,
      `grep -l -- "- specs/<path>" plans/*.md` returns at least one plan; all 17 covered
- [x] `specs/mcp/tools.md`'s Known exception (the `find_symbol` `--refresh`/`--package` message
      not conforming to Error message wording) shall remain recorded as intentional and owned by
      #68, not "fixed". — `specs/mcp/tools.md` `### Known exception` section read in full;
      unedited by this plan; `src/venvaxi/_introspect.py:955` still names `--refresh` and
      `--package` in the message, matching the exception's own description
- [x] `uv build` shall produce one wheel and one sdist. —
      `dist/venv_axi-0.3.2.dev6-py3-none-any.whl` and `dist/venv_axi-0.3.2.dev6.tar.gz` built
- [x] The wheel's `venvaxi/SKILL.md` shall be byte-identical to `src/venvaxi/SKILL.md`, carrying
      #77's corrected gotcha text. — Python `zipfile` read of `venvaxi/SKILL.md` from the built
      wheel compared byte-for-byte equal to `src/venvaxi/SKILL.md` (18127 bytes both); lines
      208-212 (dunder) and 223-229 (decorator) inspected directly, matching the corrected text
- [x] The sdist shall not bundle `.claude/worktrees/` or `.claude/scheduled_tasks.lock`. — before
      the `.gitignore` fix: `tar tzf dist/venv_axi-0.3.2.dev6.tar.gz | wc -l` -> 457, 305 of which
      matched `worktrees`; after: rebuilt sdist -> 151 files, `grep -c worktrees` and
      `grep -c scheduled_tasks` both 0
- [x] No hardcoded version string shall contradict `hatch-vcs`. —
      `grep -rn "__version__\s*=" src/` and `grep -rln '0\.3\.[12]' src/ tests/` both empty;
      `uv build` stamped `0.3.2.dev6` (`git describe --tags --long` reports
      `v0.3.1-6-ge8995d6` - 6 commits past the `v0.3.1` tag, `guess-next-dev` scheme, as expected
      for a build not itself tagged)
- [x] The full `pytest` suite shall pass with zero failures. — `uv run pytest -v`: `366 passed in
      31.55s`, matching the plan's expected baseline
- [x] `uv run coverage report` shall run over the full suite with no error. — `uv run coverage
      run -m pytest` (366 passed) then `uv run coverage report`: `TOTAL 1142 20 98%`
- [x] The markdown lint and every other `prek` hook shall pass over the full tree. —
      `uv run prek run --all-files`: all 8 hooks (`Lint [Ruff]`, `Format [Ruff]`,
      `Check Markdown [PyMarkdown]`, `Typing [Mypy]`, `Detect Secrets`, `Check TOML`,
      `Check YAML`, `Detect PEM`) report `Passed`
- [x] No untracked build artifact this run produced shall remain in `dist/` afterward. —
      `dist/venv_axi-0.3.2.dev6.whl` and `.tar.gz`, both produced by this run's `uv build` calls,
      deleted; `dist/` is gitignored, so nothing here is tracked regardless

## Risks / unknowns

- The `.gitignore` fix widens what `hatchling` excludes from the sdist beyond the two paths that
  happened to be present on this machine (`.claude/worktrees/`, `.claude/scheduled_tasks.lock`),
  mirroring the full Claude Code runtime section already in `.git/info/exclude`
  (`.claude/routines/.state/`, `.claude/checkpoints/`, `.claude/mailbox/`,
  `.claude/agent-registry.json`, `.claude/agent-memory-local`, `.claude/first-run`,
  `.claude/assistant-daemon-state.json`, `.claude/scheduled_tasks.json`). The wider set was not
  individually reproduced leaking - only the two present on disk were - but the same root cause
  (untracked-only exclusion, unread by hatchling) applies to all of them equally, so fixing only
  the two observed paths would leave the rest to leak the next time a build happens to catch one
  present.
- `plans/release-0-3-1.md` is a frozen (`status: done`) plan. Editing it is permitted only "to
  correct the record" (`plans/README.md`); this run's edit changes four citation line numbers and
  adds one Notes paragraph explaining why, and asserts no new claim about what `0.3.1` is or does.
- The `search_like.sql` docstring-search gap (Scope, above) is left unfixed. It is a genuine
  Invariant 2 divergence and is recorded as a Follow-up rather than silently absorbed, per
  `specs/README.md` Invariant 2 ("fix the code, or amend the spec - never work around a spec in
  code") - filing it, rather than fixing or ignoring it, is the honest middle path when a real
  defect is found outside a plan's declared scope.

## Notes

- **Track verdict: `express-change`.** Stated per `ICM/express-change/CONTEXT.md`'s Acceptance
  criteria, before any fix was written: no `specs/**` change needed (a stale citation and a build
  config gap, neither in `specs/README.md`'s coverage), one commit's worth of work, no new
  dependency, no new public surface, every criterion evidenced within this run.
- **The `[0.3.2]` CHANGELOG section and both merged plans (`find-limit-lower-bound`,
  `skill-gotcha-corrections`) needed no fix.** Checked against the real diffs of `997622d` and
  `0c516f2`; both plans' own Validation citations (SKILL.md line ranges, test identifiers,
  `_introspect.py:955`) still resolve to their current locations because no commit after their
  closeout touched the files they cite. Only `release-0-3-1.md` was stale, because `[0.3.2]`'s
  insertion point sits structurally above `[0.3.1]` in `CHANGELOG.md`.
- **Why the sdist leak is worth a `.gitignore` fix rather than a shrug.** The wheel - the artifact
  most callers actually install - was already clean; only the sdist leaked. But PyPI publishes
  both, the sdist is what `pip install --no-binary` and reproducible-build tooling fetch, and
  "305 of 457 files are a stray copy of two unrelated agent sessions" is the kind of thing that
  is silent until someone opens the tarball - exactly the failure mode this audit exists to catch
  before it is irreversible.
- **Reproduced before fixing.** `uv build` on the unmodified checkout produced a 1.2 MB sdist
  (`venv_axi-0.3.2.dev6.tar.gz`, 457 files, 305 under `.claude/worktrees/`); after the
  `.gitignore` fix, a rebuild produced a 400 KB sdist (151 files, 0 under `worktrees` or
  `scheduled_tasks`). Both builds' wheels carried a byte-identical, correct `venvaxi/SKILL.md`.
- **No code, test or spec file changed.** This plan's diff is `.gitignore`,
  `plans/release-0-3-1.md` and this file - no behaviour observable to a `venvaxi` caller moved.

## Follow-ups

- **Issue** - not yet filed; recommended for the maintainer to open - `search_like.sql`'s `WHERE`
  clause omits `doc`, so the FTS5-unavailable fallback path silently searches `name` and
  `qualified_name` only, narrowing `specs/commands/find.md`'s "searched over name and docstring
  text" data requirement whenever SQLite's FTS5 extension is not compiled in. Confirmed reachable,
  not dead code (`_store.py` catches `sqlite3.OperationalError` on FTS5 schema creation and
  degrades `_fts_enabled` to `False`); no existing test exercises docstring matching under the
  `LIKE` fallback (`test_search_symbols_like_fallback_when_fts_disabled` asserts name matching
  only). Unowned by this plan and by issues #67/#68/#49/#50/#71.
- **None deferred** - no `Deferred to` entries, so no downstream plan required absorption in the
  closeout commit.
