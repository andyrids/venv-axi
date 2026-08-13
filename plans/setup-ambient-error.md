---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends:
  - plan-record-repair
specs:
  - specs/commands/setup.md
  - specs/behaviors/output-contract.md
authors: []
issues: []
pr: 34
---

# Plan: Setup ambient-context error taxonomy

## Scope

`AmbientContextError` is declared in `src/venvaxi/exceptions.py` and raised nowhere. `_ambient.py`
contains no `raise` statement at all, so any `OSError` from a write - a read-only checkout, a
permission denial, a full disk, a path the process cannot create - escapes as an unexpected
exception and exits `2`.

Bring the code into conformance with the failure mode `specs/commands/setup.md` already declares.
Absorbs the second Follow-up of [spec-conformance-sweep](spec-conformance-sweep.md).

Out of scope: the `json.JSONDecodeError` path in `_update_mcp_json`, which is deliberately
tolerated and logged as a warning rather than raised - a malformed pre-existing config is not a
failure to install; and `ProjectRootNotFoundError`, which already raises correctly from
`get_project_root()`.

## Implements

`specs/commands/setup.md` Failure modes - 'If ambient context cannot be installed, then the
`setup` command shall raise `AmbientContextError`, emit the TOON error block and exit
`EX_FAILURE`.' The spec is already correct and needs no amendment; this is Invariant 2 resolved in
the code's direction, so the spec delta for this plan is empty by design rather than by omission.

`specs/behaviors/output-contract.md` exit codes - 'Exit 2 is reserved for venvaxi being broken, so
a caller can treat it as a bug report rather than a prompt to retype.' A read-only checkout is not
venvaxi being broken, and today it is reported as though it were. This is the criterion that makes
the defect observable rather than cosmetic.

## Approach

1. Flip to `status: in-progress`.
2. Raise `AmbientContextError` from the write boundary in `_ambient.py`, chaining the underlying
   `OSError` (`raise ... from exc`) and naming the path in the message, so the caller learns which
   artifact failed rather than that something did.
3. Cover the operations that can fail on a hostile filesystem: the temp-write and rename in
   `_atomic_write_text`, the two `parent.mkdir(parents=True, exist_ok=True)` calls, and the
   `read_text` calls in `inject_agents_md` and `install_skill`. Leave the `json` decode path as it
   is.
4. Reuse the existing hierarchy. `AmbientContextError` already subclasses `Error`, and the entry
   point already renders any `Error` as a TOON block and exits `1`; nothing in `_cli.py` changes.
5. Tests: simulate a write failure and assert the exception, the rendered TOON block and exit `1`.
   The existing setup tests cover only success paths, which is why the gap survived a green suite.
6. `CHANGELOG.md` entry under `Fixed`.

## Validation

- [x] If a write to `AGENTS.md` fails with an `OSError`, then the `setup` command shall raise
      `AmbientContextError`. —
      `tests/test_ambient.py::test_inject_agents_md_write_failure_raises`, with
      `test_inject_agents_md_read_failure_raises` covering the read boundary
- [x] If a write to an MCP config file fails with an `OSError`, then the `setup` command shall
      raise `AmbientContextError`. —
      `tests/test_ambient.py::test_update_mcp_json_write_failure_raises`
- [x] If a write to `SKILL.md` fails with an `OSError` under `--skill`, then the `setup` command
      shall raise `AmbientContextError`. —
      `tests/test_ambient.py::test_install_skill_write_failure_raises`, with
      `test_install_skill_read_failure_raises` covering the read boundary
- [x] If ambient context cannot be installed, then the `setup` command shall emit the TOON error
      block and exit `1`, not `2`. —
      `tests/test_ambient.py::test_main_setup_write_failure_emits_toon_and_exits_1`,
      driving the real entry point
- [x] If ambient context cannot be installed, then the message shall name the path that could not
      be written. —
      `tests/test_ambient.py::test_main_setup_write_failure_names_path`, which also pins
      that the destination is named rather than the `.tmp` file
- [x] When ambient context installs successfully, the `setup` command shall emit the artifact
      mapping and exit `0`, unchanged by this plan. —
      `tests/test_ambient.py::test_main_setup_success_unchanged`, plus the four pre-existing
      `test_setup_ambient_context_*` tests passing unmodified
- [x] The test suite shall pass. —
      `uv run coverage run -m pytest` reports `293 passed in 28.73s`

## Risks / unknowns

- Catching `OSError` too broadly could swallow a genuine internal fault and misreport it as an
  installation failure. The scope is bounded to the filesystem calls listed in Approach step 3;
  nothing wraps a whole function body.
- Simulating a write failure portably is the awkward part. Monkeypatching `Path.write_text` (or
  `os.replace`) to raise is preferred over `chmod`, which behaves differently on Windows - the
  project's primary development platform - than on POSIX.
- The last criterion is a characterization check over unchanged behaviour. It is there because the
  fix touches the shared write helper every artifact goes through, so the success path is exactly
  what a careless `try` would break.

## Notes

**The spec delta was empty by design.** `specs/commands/setup.md` has declared
`AmbientContextError` for a failed install since it was written, and
`output-contract.md#exit-codes` has always reserved exit `2` for venvaxi being broken. Nothing
needed amending - Invariant 2 admits fixing the code or the spec, and here the spec was already
right. Recorded because an empty spec delta at stage 01 normally means something was missed, and
this one did not.

**Why the exclusions are exclusions.** Two things were deliberately left raising as they were, and
both would look like gaps to a later reader:

1. `json.JSONDecodeError` in `_update_mcp_json` still warns and continues. A malformed
   pre-existing config is not a failure to install, and treating it as one would make `setup`
   refuse to run against a repo whose `.mcp.json` some other tool had mangled.
2. The `read_text` calls against the packaged resources `ambient_markdown` and `skill_markdown`
   are unwrapped. Failing to read installed package data genuinely *is* venvaxi being broken, so
   exit `2` is the correct classification. Wrapping them would have re-emptied the very
   distinction this plan exists to restore.

**Bound tightness was the design constraint.** A single `try` around `setup_ambient_context` would
have satisfied every criterion here and been wrong: it would convert any `OSError` from anywhere
below, including ones that are not installation failures, and the message could name no path. The
`_install_boundary(path)` helper wraps one filesystem call per site, which is what lets the error
name the artifact that failed rather than reporting that something did.

**Windows drove two implementation choices.** Failure is simulated by monkeypatching
`Path.write_text` / `Path.read_text` rather than by `chmod`, which does not deny writes the same
way here as on POSIX; and the path assertion reverses TOON's backslash escaping before comparing.
Both are recorded so a future contributor does not "simplify" them back.

**Test placement is a known compromise.** The CLI-level assertions live in `tests/test_ambient.py`
rather than `tests/test_cli.py`, because a parallel agent owned that file during this run. They
drive `venvaxi.__main__.main` directly, so coverage is equivalent, but the natural home is
`test_cli.py` and moving them is free whenever that file is next open.

**This gap survived a full release.** The existing setup tests covered only success paths, so a
declared-but-never-raised exception sat behind a green suite. That pattern - a spec's failure mode
with no test standing behind it - is worth grepping for elsewhere.

## Follow-ups

- **Issue** [#20](https://github.com/andyrids/venv-axi/issues/20) - the PyMarkdown tokenizer crash
  stays open with its workaround; untouched here.
- **Deferred to** - none.
- **Tracked as** - the two CLI-level tests noted above sit in `tests/test_ambient.py` rather than
  `tests/test_cli.py`. No plan owns relocating them and none is proposed; it is a tidy-up, not a
  defect.
