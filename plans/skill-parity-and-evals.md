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
pr: 41
---

# Plan: Skill parity, robustness and evals

## Scope

The project ships two copies of the same Claude Code skill: `src/venvaxi/SKILL.md`, packaged in
the wheel and installed into consuming repos by `venvaxi setup --skill`, and
`.claude/skills/venvaxi/SKILL.md`, the copy this repo's own agents load. They have drifted: the
repo copy is missing the package-error-taxonomy bullet, and it names the installer source as
`src/venvaxi/skill.md` - a lowercase path that does not exist. No test compares them.

Make the packaged file the single source of truth, regenerate the repo copy through the real
installer, add a parity test that fails on any byte of drift, fill the gaps in the packaged skill
text, and grow the eval suite from three cases to nine so the skill's documented hazards are
exercised.

Stage 03 found the same newline defect one function away, in `inject_agents_md`, where it breaks
a clause of the same spec: hand-authored `AGENTS.md` content outside the markers is rewritten
LF to CRLF on Windows. Absorbed here on re-entry rather than deferred - the spec already forbids
it, and `specs/README.md` Invariant 2 makes a known divergence a bug, not debt.

Out of scope: any change to `install_skill()` *policy* (a diff or refuse mode on divergence is
recorded in `specs/commands/setup.md` Out of scope), and detecting drift between the skill text
and actual CLI behaviour.

## Implements

`specs/commands/setup.md` Actions item 4, as amended by this plan - the installed skill is a
byte-for-byte copy of the packaged skill, with no merge, marker block or per-repo variation
point, and a diverged copy is replaced wholesale. The parity test and the regenerated repo copy
bring the tree into conformance with that clause; the same plan amends the spec and implements
it, which `plans/README.md` resolves in favour of `specs:`.

Also `specs/commands/setup.md` Actions item 1, unamended - "The `setup` command shall preserve
content outside the markers **byte-for-byte**." The code has never satisfied it on Windows. No
spec change is needed here; the code is brought into conformance instead, per
`specs/README.md` Invariant 2.

## Approach

1. Flip to `status: in-progress`.
2. Amend `specs/commands/setup.md` Actions item 4 to declare byte-identity, and add the per-repo
   variation point and diff/refuse mode to its Out of scope.
3. Make `install_skill()` read, compare and write raw bytes. Text mode's newline translation
   forks the LF packaged source into a CRLF installed copy on Windows, so without this the
   byte-for-byte clause cannot hold on the project's primary development platform and
   regeneration churns every line of the tracked repo copy.
4. Edit `src/venvaxi/SKILL.md` only - a generalized `## Invocation` section, gotchas for
   `doc: (no docstring)`, the path-keyed cache, the two `serve` failure classes and the
   `SKILL.md: true` report after a discarded hand-edit, a note that `--fields` is silently
   ignored under `--api`, the `-v`/`--verbose` global flag, and a Pointers bullet naming the
   packaged source as the edit surface.
5. Regenerate `.claude/skills/venvaxi/SKILL.md` via a new `just skill-sync` recipe that calls
   `install_skill(Path('.'))` directly, so the repo dogfoods its own installer without `setup`
   touching `AGENTS.md` or `.mcp.json`.
6. Add `tests/test_skill_parity.py` - byte-parity with a unified diff on failure, the installer
   as a no-op against the repo copy in `tmp_path`, and a guard on the literal lowercase
   `src/venvaxi/skill.md` path.
7. Grow `.claude/skills/venvaxi/evals/evals.json` from three cases to nine, one per previously
   unexercised gotcha, and add `.claude/skills/venvaxi/evals/README.md` recording the manual
   improvement loop - no automated rewrite exists, by design.
8. `CHANGELOG.md` entry.
9. Re-entry from stage 03: make `inject_agents_md` read and write raw bytes for the same reason
   as step 3. Both halves matter - `read_text` normalizes an existing CRLF file to LF and
   `_atomic_write_text` translates LF back to CRLF, so hand-authored content outside the markers
   is rewritten either way. Splicing stays on decoded text; only the file boundary changes.
   `_update_mcp_json` is left on the text write: its JSON is regenerated wholesale and no spec
   clause claims byte preservation for it.

## Validation

- [x] When `setup --skill` runs against a repo whose installed skill differs from the packaged
      skill, then the `setup` command shall replace it byte-for-byte and report `SKILL.md: true`.
      — `tests/test_ambient.py::test_install_skill_overwrites_stale_copy`, and a live
      `venvaxi setup --skill` against a seeded diverged copy emitting `SKILL.md: true` with
      `cmp` reporting no difference
- [x] The test suite shall fail when `.claude/skills/venvaxi/SKILL.md` and `src/venvaxi/SKILL.md`
      differ by any byte. — `tests/test_skill_parity.py::test_installed_skill_matches_packaged`,
      shown failing on a single appended byte
- [x] When `just skill-sync` runs on a tree whose repo copy already matches the packaged skill,
      the recipe shall print `False` and leave the tree unmodified. — `just skill-sync` printing
      `False` with `git diff --stat` reporting no change to the repo copy
- [x] The packaged skill shall state that `--fields` is silently ignored when `--api` is set.
      — `src/venvaxi/SKILL.md:111`
- [x] The packaged skill shall state that the symbol cache is keyed by the resolved project-root
      path. — `src/venvaxi/SKILL.md:189`
- [x] The packaged skill shall state that `doc: (no docstring)` is a definitive answer.
      — `src/venvaxi/SKILL.md:182`
- [x] The eval suite shall contain nine cases with unique ids, including a case in which the
      correct behaviour is not to query the AXI. — parsed `evals.json` reporting 9 cases with
      ids `[1..9]` unique, case 9 `tutorial-request-out-of-scope`
- [x] When `setup` injects the ambient block into an existing `AGENTS.md`, the `setup` command
      shall leave every byte outside the markers unchanged, whatever line endings that content
      uses. — `tests/test_ambient.py::test_inject_agents_md_preserves_lf_bytes_outside_markers`,
      shown failing against the pre-fix implementation

## Risks / unknowns

- The `## Invocation` section must stay repo-agnostic. It is the one place the old dev copy was
  genuinely more useful; if the generalized wording reads as weaker for this repo, the fix is
  better wording, not a second file.
- Byte-identity is enforced, correctness is not. The parity test catches the two files
  disagreeing; it cannot catch both going stale together against `_cli.py`.
- `install_skill()` writes. Any test that calls it must target `tmp_path`, never the working
  tree; the `skill-sync` recipe is the only sanctioned in-repo invocation.
- Nine eval cases cost more to run than three; nothing runs them in CI today, and this plan does
  not add that.

## Notes

**Why byte-identity rather than a dev-facing fork.** Three shapes were considered: byte-identical
with the packaged file winning; a shared common body plus a marker-delimited repo overlay; and
hand-syncing both files with no enforcement. The second was argued for on the grounds that this
repo genuinely needs the `uv run` prefix and pointers into `specs/` and `_mcp.py`. Both reasons
dissolved on inspection - the `uv run` note generalizes into a PATH note true in any consuming
repo, and the ICM hierarchy already routes contributors to `specs/`, so that bullet was redundant
rather than homeless. Byte-identity was chosen because it is the only shape a test can enforce by
construction; an overlay is single-sourcing plus an allowlist of exceptions, which is a rule
someone has to remember at every edit.

**Why the newline fix was in scope.** `install_skill` used `write_text`, whose newline
translation forks an LF packaged source into a CRLF installed copy on Windows. Byte-identity was
therefore unachievable on the project's primary platform, and regeneration churned all 215 lines
of the tracked copy. The function's own comment already claimed the behaviour it now has - 'the
bytes on disk *are* the file'. This is mechanics implementing the settled decision, not the
diff/refuse policy change the Scope excludes.

**Re-entered at stage 01 once.** Stage 03 reported a divergence against `specs/commands/setup.md`
Actions item 1: `inject_agents_md` rewrote hand-authored `AGENTS.md` content from LF to CRLF on
Windows, violating the byte-for-byte preservation clause. Pre-existing, but the same defect class
step 3 had just fixed one function away, so it was absorbed rather than deferred - Approach step 9
and the eighth Validation criterion. No spec amendment was needed; the clause already forbade the
behaviour, so `specs/README.md` Invariant 2 directed the fix at the code.

**Both halves of that fix are load-bearing.** The write side was the visible defect, but
`read_text` normalizes an existing CRLF file to LF on the way in, so a correct write alone would
still have rewritten the span. Only two of the three new preservation tests discriminate on
Windows: the pre-fix code round-tripped a CRLF file unchanged by accident, normalizing on read and
translating back on write. The CRLF case discriminates on Linux, where CI runs. It was kept for
that reason rather than deleted as redundant.

**`_update_mcp_json` deliberately stays on the text write.** Its JSON is regenerated wholesale
from a parsed object and no spec clause claims byte preservation for it, so `_atomic_write_text`
survives with one caller.

**A test that tested its own fixture.** The first spelling of
`test_inject_agents_md_preserves_bytes_around_existing_markers` asserted `b"stale" not in written`
and failed against correct code - the injected ambient body contains 'stale graph'. Rewritten
against a `SUPERSEDED-BLOCK-BODY` sentinel. Had the substring been rarer, the same assertion would
have passed vacuously instead, which is the more dangerous direction.

**Two failure-path tests were asserting less than they read.**
`test_main_setup_write_failure_emits_toon_and_exits_1` and `test_main_setup_write_failure_names_path`
mocked `Path.write_text`, which stopped intercepting the `AGENTS.md` write once that moved to
bytes. The first kept passing while the failure it observed had silently moved to
`.vscode/mcp.json`. Both now mock `write_bytes`.

**MindStudio self-improving-skill guidance, evaluated and mostly rejected.** The unattended
rewrite loop conflicts with the review gates `AGENTS.md` calls load-bearing; its eval schema of
`exact`/`contains`/`regex` string assertions suits classification tasks with one short
deterministic answer and would be a regression against the rubric-style `expectations` list
skill-creator already documents. Adopted: growing the suite past three cases, applied as six cases
seeded from real gotchas rather than the article's 20-50 quota.

**No stage 02 output artifact was produced.** `stages/02-implementation/output/` is empty; the
implementation deviation was recorded in the plan and the stage 01 techspec instead, and stage 03
verified it directly rather than through the missing report.

## Follow-ups

- **Issue [#39](https://github.com/andyrids/venv-axi/issues/39)** - skill text vs code drift is
  undetected. `tests/test_skill_parity.py` catches the two copies disagreeing; nothing catches
  both going stale together against `_cli.py` or `venvaxi --help`. Named as a Risk in this plan
  and deliberately out of scope.
- **Issue [#40](https://github.com/andyrids/venv-axi/issues/40)** - the eval suite runs nowhere.
  Nine cases exist and CI does not execute them, so the suite only has teeth when a human runs it
  via the loop in `.claude/skills/venvaxi/evals/README.md`.
- **Tracked as** - a diff or refuse mode on skill divergence is declared Out of scope in
  `specs/commands/setup.md`, to be revisited only if a diverged copy ever proves to hold work
  worth protecting. No plan or issue owns it by design.
