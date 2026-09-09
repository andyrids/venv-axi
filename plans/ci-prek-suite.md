---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: [117]
pr:
---

# Plan: CI prek suite

## Scope

`prek.toml` declares eight hooks. `.github/workflows/ci.yml`'s `static` job runs three of them, and
not through prek: it calls the `pkgdx` console scripts directly, as `uv run pkgdx-lint-hook`,
`uv run pkgdx-format-hook` and `uv run pkgdx-typing-hook -p venvaxi`. Five hooks therefore run only
where a contributor has run `uv run prek install` on their own machine: `pkgdx-markdown`,
`pkgdx-secrets`, and the three prek builtins `check-toml`, `check-yaml` and `detect-private-key`. A
markdown violation, a committed credential, a malformed `prek.toml` and a malformed workflow file
all reach `develop` unchallenged by anything automated.

This unit replaces the three console-script steps with one step that runs the suite `prek.toml`
declares, `uv run -m prek run --all-files`, preceded by a step that pins prek's hook environments to
`uv.lock` and followed by a failure-only diagnostic step for the one hook whose failure names no
file. Nothing else in the workflow moves.

**Resolution 2 of issue #117 is unworkable, and that is why the whole suite is run instead.** That
resolution proposed adding the two missing `pkgdx` console scripts as further CI steps, spelled the
way the existing three are spelled. It cannot reach the same set of gates, for two separate reasons:

1. The three builtins live inside prek's own Rust binary. `check-toml`, `check-yaml` and
   `detect-private-key` are not `pkgdx` entry points and expose no console script at all, so no
   number of `uv run pkgdx-*-hook` steps ever runs them.
2. `pkgdx-secrets-hook` invoked with no filenames scans nothing and exits 0. Prek supplies each
   hook's file list from git; a console script called argless has no list, so the step would be a
   security gate that is green because it looked at nothing. That is worse than the gap it closes,
   because a vacuously green gate is the reason nobody looks again.

Running the suite through prek answers both: prek supplies the file lists, and the builtins are its
own.

**`UV_CONSTRAINT` is load-bearing, not a tidiness measure.** Prek builds each hook's environment
itself and never reads `uv.lock`, and `pkgdx` constrains its tools with lower bounds only. Measured
this session: `uv.lock` pins ruff 0.16.1 and mypy 2.3.0, and a fresh unconstrained hook environment
resolved ruff 0.16.6 and mypy 2.3.1. Unconstrained, a tool release alone turns `static` red on a
tree nobody has touched, and the commit that fails for it is innocent. Exporting the lock to a
constraints file and pointing `UV_CONSTRAINT` at it makes a fresh environment resolve 0.16.1 and
2.3.0, the versions the project itself resolves, so the only thing that can turn the job red is the
diff under test.

**The format step never gated, and this change fixes that incidentally.**
`uv run pkgdx-format-hook` argless, exactly as `ci.yml` runs it, is `ruff format` with no `--check`:
measured on a misformatted file it reformatted the file in place and exited 0. CI has been reporting
a green format check while silently rewriting a tree nothing reads afterwards, which is to say there
has been no format gate at all. Under prek the same hook carries `--exit-non-zero-on-format` from
its hook definition, so replacing the step converts it into a gate without anything in this unit
being aimed at it. Recorded here rather than left as a pleasant side effect, because it is another
instance of the shape this CI sequence keeps closing: a check reporting success over something it
never examined.

**The file-and-pin rule.** This unit touches `.github/workflows/ci.yml` (the `static` job alone),
three Layer 3 toolchain references, this plan and `CHANGELOG.md`. It does not touch `prek.toml`,
which `ICM/_config/reference-toolchain-prek.md` forbids hand-editing and requires re-running
`pkgdx init` to change, nor `pyproject.toml`, `uv.lock`, `src/`, `tests/`, `specs/`, or the `pytest`
and `conformance` jobs. If a newly-running hook surfaces a defect it is filed and pinned as its own
issue, never repaired here, per the precedent [ci-conformance-tier](ci-conformance-tier.md) set.

**Eligibility for `express-change`.** All three conditions in `ICM/express-change/CONTEXT.md` hold,
restated with reason:

1. **No spec change is required.** Nothing under `specs/` moves. `specs/README.md` scopes specs to
   invocation, inputs, outputs and failure modes of the tool; which hooks CI enforces is
   infrastructure, not behaviour `venvaxi` promises a caller. This is the same class of change as
   the five CI units preceding it in the 0.5.0 sequence
   ([ci-platform-matrix](ci-platform-matrix.md), [ci-conformance-tier](ci-conformance-tier.md),
   [ci-static-typing](ci-static-typing.md), [release-publish-gate](release-publish-gate.md),
   [ci-python-version-matrix](ci-python-version-matrix.md)), none of which touched `specs/`. Three
   Layer 3 references are amended, all `immutable: true`, because this change makes what they say
   false; that is a deliberate act rather than a passing one, following the precedent
   [ci-conformance-tier](ci-conformance-tier.md) set when it amended
   `ICM/_config/reference-toolchain-pytest.md` in the same commit as the job that falsified it.
2. **One commit's worth**, with no new dependency and no new public surface. prek already arrives
   transitively: `pkgdx` declares `Requires-Dist: prek~=0.4.8`, `uv.lock` records `prek==0.4.12`,
   and `uv run -m prek` resolves from the synced environment today. Nothing is added to
   `pyproject.toml`. Three steps are replaced by three steps, in one job.
3. **Every Validation criterion can be evidenced within this run except those needing a real PR.**
   Criterion 1 asserts on GitHub Actions' own scheduling and check-run reporting for a pull request,
   which cannot be produced on this machine; the plan stays `status: in-progress` until that run
   happens, the identical situation [ci-platform-matrix](ci-platform-matrix.md),
   [ci-conformance-tier](ci-conformance-tier.md) and
   [ci-python-version-matrix](ci-python-version-matrix.md) each recorded. The remaining criteria are
   produced locally in this run, under the same `UV_CONSTRAINT` and against an isolated `PREK_HOME`
   so the machine's real hook cache is not consulted or written.

## Implements

Nothing under `specs/`. This is CI configuration plus the three toolchain-reference amendments the
change makes true, the same class of change as the five CI units preceding it, so `specs:` and
`authors:` are both empty.

`ICM/_config/reference-toolchain-prek.md` is amended rather than authored, so it does not belong in
`authors:` either: that field is for `specs/`, and a Layer 3 reference is factory configuration.

## Approach

1. Open this plan at `status: in-progress`.
2. `.github/workflows/ci.yml`, `static` job only - remove the three console-script steps and add
   three in their place. `checkout`, `setup-uv` and `uv sync` are untouched, as are the `pytest` and
   `conformance` jobs.
3. `Pin prek's hook environments to uv.lock` - export the lock's pins to
   `${{ runner.temp }}/constraints.txt` with
   `uv export --frozen --no-hashes --no-emit-project --no-emit-package pkgdx`. The file is written
   to the runner's temp directory, never into the repository, so the tree the hooks then check is
   still the checked-out commit. `--frozen` keeps the export from re-resolving the lock.
   `--no-emit-package pkgdx` is required, not cosmetic: prek clones the hook repository without
   tags, so the version its `hatch-vcs` configuration derives is not the `0.2.0` `uv.lock` records,
   and a constraint pinning `pkgdx==0.2.0` makes the hook environment unsolvable.
4. `Run every prek hook` - `uv run -m prek run --all-files` with `UV_CONSTRAINT` set to that file,
   carrying `id: hooks` so the diagnostic step can read its outcome. Run at prek's default stage,
   which is what includes the `stages: [pre-commit]` secrets hook: `--dry-run` lists eight hooks at
   the default stage and seven under `--stage pre-push`. No `--skip`, and no `continue-on-error`.
5. `Locate a PyMarkdown tokenizer crash` - guarded by `if: failure() && steps.hooks.outcome ==
   'failure'`, running the per-file bisection loop `ICM/_config/reference-toolchain-pymarkdown.md`
   documents and emitting a `::error file=` annotation for each file that reproduces
   `BadTokenizationError`. It ends `exit 0`: it is a diagnostic, and the hook step above it is the
   gate. When the markdown failure was an ordinary rule violation it prints one line saying so and
   annotates nothing, because prek has already named file, line and rule.

   The loop is guarded by one whole-suite `prek run pkgdx-markdown --all-files`, and only runs when
   that reproduces `BadTokenizationError`. Without the guard every ruff or mypy failure - the
   common case, which reproduces no crash - paid the full per-file bisection to conclude nothing.
   Measured: 5.9s to short-circuit against 1m33s to run the loop. The guard deliberately does not
   read the hook step's own output, because capturing it through `tee` would make the gate's exit
   status depend on `pipefail`, and a gate that can pass for a shell reason is the defect this unit
   exists to remove.
6. Amend the three Layer 3 references the change falsifies.
   `ICM/_config/reference-toolchain-prek.md` gains a `## CI` section naming the step that runs the
   suite and the `UV_CONSTRAINT` pin, so the file no longer reads as though a local `prek install`
   were the only enforcement; its Commands list and its `prek.toml` no-hand-edits rule are
   unchanged. `ICM/_config/reference-toolchain-pymarkdown.md` keeps the bisection recipe verbatim,
   since CI now runs that recipe unchanged, and gains a paragraph saying so. Ruff's Commands entry
   for `pkgdx-format-hook` records that it rewrites and exits 0 whatever it finds, so it formats but
   does not gate.
7. Demonstrate each failure criterion by causing it, per the specimen-guard precedent
   [ci-conformance-tier](ci-conformance-tier.md) set, capturing verbatim: a misformatted Python file
   against the argless console script and then against prek; a pipe inside a nested list item
   against prek and then against the diagnostic loop; an over-length markdown line against the loop,
   which must stay silent; a fabricated AWS-style key against the secrets hook. Every experiment
   runs against a scratch `PREK_HOME`. Each induced change is reverted with `git checkout --` and
   re-verified, and `.secrets.baseline` is confirmed unmodified afterwards.
8. Run the repo toolchain gate with this plan staged (`git add -N`), per the trap
   [ci-platform-matrix](ci-platform-matrix.md) recorded: prek reads git-tracked files, so an
   untracked plan is a green that never looked at it.
9. `CHANGELOG.md` `[Unreleased]` and `Changed` - one entry citing issue #117.
10. Stop before closeout. Criterion 1 needs a real PR run; the plan stays `status: in-progress`
    until then.

## Validation

- [ ] When a pull request targets `main` or `develop`, the `static` job shall run every hook
      `prek.toml` declares.
- [ ] While the `static` job runs, each hook environment shall resolve the tool versions `uv.lock`
      pins, so a new tool release cannot turn CI red on an unchanged tree.
- [ ] While the `static` job runs, `detect-secrets` shall execute over the tracked files rather than
      be skipped.
- [ ] If a tracked Python file is misformatted, then the `static` job shall fail rather than
      reformat it and report success.
- [ ] If a tracked markdown file crashes PyMarkdown's tokenizer, then the `static` job shall report
      that file's path rather than a diagnostic naming no file.
- [ ] If the markdown hook fails on an ordinary rule violation, then the diagnostic step shall add
      no annotation, since prek already names file, line and rule.
- [ ] `ICM/_config/reference-toolchain-prek.md` shall name the CI step that runs the suite and shall
      no longer imply the suite is enforced only by a local install.

## Risks / unknowns

- **Criterion 1 needs a real PR run.** It asserts on GitHub Actions' scheduling and check-run
  reporting, which cannot be produced on this machine. The other six are evidenced locally in this
  run, against a scratch `PREK_HOME` under the same `UV_CONSTRAINT` the job sets, so what they
  evidence is the mechanism rather than the runner.
- **The diagnostic loop runs prek once per markdown file.** 107 tracked files, measured at 1m33s
  this session, and only when the guard ahead of it reproduces a crash - a failure that is not a
  tokenizer crash costs 5.9s instead. A green run never pays either. The loop grows with the
  repository, and the point at which it is slower than reading the crash by hand is the point at
  which it should be narrowed to the pull request's changed files rather than every tracked file.
- **prek cold-clones the hook repository and builds its environments**, where the three
  console-script steps ran inside the already-synced project environment. Measured cold against a
  fresh `PREK_HOME` on this machine: 40s for `prek prepare-hooks`, against a `static` job that
  completes in roughly 25s today. No `actions/cache` step is proposed. Measure the real number on
  the first PR run first, and note before anyone adds one that a cache over `PREK_HOME` would freeze
  the resolved tool versions invisibly: `UV_CONSTRAINT` would stop being what decides them, and a
  lock bump would not be picked up until something evicted the cache.
- **The `pkgdx` exclusion from the constraints export is a hand-maintained exception.** It is there
  because prek's clone carries no tags, so the built version disagrees with the lock and the pin is
  unsatisfiable. Any future dependency a hook environment installs from source rather than from an
  index needs the same exception. It announces itself the way this one did, with
  `No solution found when resolving dependencies` at the first hook, which is the failure mode to
  prefer over a silent one.
- **`--skip` fails open.** An unmatched `--skip` selector warns and then runs everything, so a
  design that excluded a hook by name would silently start running it again after any rename. This
  design uses no `--skip` for that reason: the set of enforced hooks is decided in `prek.toml` and
  nowhere else, which is also what keeps this job honest when a hook is added there.
- **`::error file=` carries no line number**, so GitHub anchors the annotation at line 1 of the
  named file. The tokenizer crash supplies no line to carry, which is the whole reason the
  diagnostic exists, so the message says "somewhere in this file" and the annotation cannot be
  misread as pointing at its first line.
- **CI's working tree is no longer the checked-out commit.** prek runs hooks concurrently, and
  `pkgdx-lint` and `pkgdx-format` write. Both are `pass_filenames: false`, so ruff runs over `.` and
  may rewrite anything it dislikes. The job fails when they do, so a rewrite is never mistaken for
  success, and the runner is discarded immediately after. Harmless and ephemeral, but recorded: a
  step added to `static` after the hook step cannot assume it is looking at the commit under test.
- **The gitlab coupling is not new.** `prek.toml` resolves its hooks from
  `gitlab.com/andyrids/pkgdx` at `rev = "v0.2.0"`, and `uv.lock` already resolves `pkgdx` itself
  from the same host, so `uv sync` has depended on gitlab being reachable since well before this
  unit. What is new is that CI performs a clone as well as a wheel resolution. The tag was confirmed
  publicly cold-clonable this session.
- **Eight hooks means eight ways for an unrelated tool to have an opinion.** Three of them have
  never run over this repository in CI, and `check-yaml` in particular now reads every workflow
  file. The baseline run is green, so nothing is filed and pinned, but that dates the result rather
  than guaranteeing it: the hooks are pinned to `uv.lock` now, and the next lock bump is the next
  time their opinions can change.

## Notes

## Follow-ups
