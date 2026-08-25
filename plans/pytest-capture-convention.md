---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs: []
authors: []
issues: [56]
pr: 99
---

# Plan: Pytest capture convention

## Scope

**Eligibility for express-change.** All three conditions in `ICM/express-change/CONTEXT.md` hold.

1. **No spec change is required.** `specs/**` describes observable CLI behaviour; this change is a
   testing convention, not a behaviour the tool promises. `ICM/_config/reference-toolchain-pytest.md`
   is amended, which is an `immutable: true` Layer 3 reference and therefore a deliberate amendment
   rather than a passing one, but it is configuration of the factory and not a spec.
2. **One commit's worth**, with no new dependency and no new public surface. A single bullet is
   appended to one reference file; nothing under `src/` or `tests/` changes.
3. **Every Validation criterion is evidenced within this run** - each is a `grep` over a file this
   run touches, or over `tests/` as it stands today.

Fix issue [#56](https://github.com/andyrids/venv-axi/issues/56): pytest's default fd-level capture
re-asserts `sys.stdout`/`sys.stderr` mid-test, so a `mock.patch` swap of either stream receives no
bytes and a test written that way fails identically with and without the fix under test. Surfaced
during the `stdout-encoding-contract` run
([plans/stdout-encoding-contract.md](stdout-encoding-contract.md), #45/#54), where the techspec's
directed `mock.patch` approach had to be abandoned mid-implementation because the resulting tests
asserted nothing. Measured with a throwaway probe driving `venvaxi.__main__.main()`: 0 bytes
captured under the default fd capture, 291 under `--capture=no`.

Record the working pattern - request `capsys` and reconfigure the captured stream, itself a real
`io.TextIOWrapper` - as a bullet in `ICM/_config/reference-toolchain-pytest.md`, next to the
existing show-it-failing rule it complements. `tests/test_stdout_encoding.py` is the worked
example.

Out of scope: any change to `tests/test_stdout_encoding.py` or any other test module - the pattern
is already in use there; this plan documents it, and documents nothing else.

## Implements

Nothing in `specs/**`; this plan is test-strategy work, which is why both `specs:` and `authors:`
are empty. It brings no code into conformance with a spec and authors no spec - the same class of
change as [plans/real-dependency-conformance.md](real-dependency-conformance.md), which amended
the same reference file for the same reason.

## Approach

1. Flip to `status: in-progress`.
2. Append one bullet to `## Conventions` in `ICM/_config/reference-toolchain-pytest.md`, immediately
   after the existing "A test written for a bug fix SHOULD be shown to fail..." bullet, naming
   `sys.stdout`, `sys.stderr`, `capsys`, `reconfigure`, the measured byte counts and
   `tests/test_stdout_encoding.py` as the worked example.
3. Broaden the bullet's scope beyond the issue's own proposed wording: the issue scopes the rule to
   tests that "assert on stream behaviour"; this plan applies it to any test asserting on STDOUT or
   STDERR, because the fd-capture mechanism defeats payload assertions identically to stream-identity
   assertions - the 0-bytes measurement is itself a payload measurement, not a stream-identity one.
4. Run the test/coverage gate and the markdown gate, capturing output verbatim.
5. Close out and add the `CHANGELOG.md` entry under `## [Unreleased]` / `### Changed`.

## Validation

- [x] `## Conventions` in `reference-toolchain-pytest.md` shall carry a bullet naming both
      `sys.stdout` and `sys.stderr` as streams a test must not `mock.patch`. —
      `ICM/_config/reference-toolchain-pytest.md:54`, "A test asserting on STDOUT or STDERR MUST NOT
      replace `sys.stdout` or `sys.stderr` with `mock.patch`."
- [x] That bullet shall name `capsys` and `reconfigure` as the working pattern. —
      `grep -n "capsys" ICM/_config/reference-toolchain-pytest.md` reports line 58; the same bullet
      reads `Request capsys and reconfigure the captured stream`
- [x] That bullet shall cite `tests/test_stdout_encoding.py` as the worked example. —
      `ICM/_config/reference-toolchain-pytest.md:62`, "`tests/test_stdout_encoding.py` is the worked
      example"
- [x] No test module under `tests/` shall replace `sys.stdout` or `sys.stderr` via `mock.patch`. —
      `grep -rn 'mock\.patch(' tests/ | grep -i 'sys\.std'` reports no match
- [x] The markdown gate shall pass over every amended file. —
      `uv run -m prek run --all-files` reports `Check Markdown [PyMarkdown]..............Passed`

## Risks / unknowns

- The broadened wording (STDOUT/STDERR generally, not just "stream behaviour") could in principle
  overreach a future test that has a legitimate reason to patch a stream for some purpose other
  than asserting on it. No such test exists today, and the mechanism the bullet warns about applies
  regardless of what the assertion is checking, so this is accepted rather than hedged in the
  wording.

## Notes

**Deviation from the issue's own proposed wording, kept deliberately.** Issue #56 scopes its
proposed bullet to tests that "assert on stream behaviour" (encoding, buffering, stream identity).
This plan's bullet instead covers any test asserting on STDOUT or STDERR, because pytest's fd-level
capture defeats a patched stream identically whether the assertion checks stream behaviour or
payload content - the issue's own measurement (0 bytes captured) is a payload measurement, not a
stream-identity one. Narrowing the rule to "stream behaviour" would leave a payload-asserting test
just as exposed to the same defeat, so the wider scope is the accurate one.

**A `grep`-over-`tests/` guard test was considered and rejected.** `tests/test_skill_parity.py`
is the precedent for a test that greps the repository for a drift condition. The same shape here -
a test asserting `mock.patch("sys.stdout", ...)` / `mock.patch("sys.stderr", ...)` does not appear
under `tests/` - was considered for this change and rejected: zero violations exist today (see the
fourth Validation gate), so the guard would assert nothing on the day it is added and cannot be
shown failing without first writing a synthetic violation to prove it red. That is speculative
scaffolding for a defect that documentation now makes it easy to avoid - YAGNI
(`ICM/_config/reference-standard-yagni.md`). If a violation is ever introduced, the fourth
Validation gate's `grep` is what a future contributor re-runs to find it.

**Closed out over two commits, not one.** `plans/README.md` closeout step 1 flips `status` to
`done` **and** adds `pr:` in the same edit, and the closeout gate enforces the pair - a plan at
`done` with an empty `pr:` is a record claiming a merge that has not happened. A PR number cannot
exist before the commit it describes, so the work commit lands first and a second commit freezes
the plan against [PR 99](https://github.com/andyrids/venv-axi/pull/99). That is the same two-step
every plan in this repository closes with, and it does not widen the `express-change` eligibility
test, which bounds the work rather than the commit count.

## Follow-ups

- **None.**
