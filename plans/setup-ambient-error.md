---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends:
  - plan-record-repair
specs:
  - specs/commands/setup.md
  - specs/behaviors/output-contract.md
authors: []
issues: []
pr:
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

- [ ] If a write to `AGENTS.md` fails with an `OSError`, then the `setup` command shall raise
      `AmbientContextError`.
- [ ] If a write to an MCP config file fails with an `OSError`, then the `setup` command shall
      raise `AmbientContextError`.
- [ ] If a write to `SKILL.md` fails with an `OSError` under `--skill`, then the `setup` command
      shall raise `AmbientContextError`.
- [ ] If ambient context cannot be installed, then the `setup` command shall emit the TOON error
      block and exit `1`, not `2`.
- [ ] If ambient context cannot be installed, then the message shall name the path that could not
      be written.
- [ ] When ambient context installs successfully, the `setup` command shall emit the artifact
      mapping and exit `0`, unchanged by this plan.
- [ ] The test suite shall pass.

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

## Follow-ups
