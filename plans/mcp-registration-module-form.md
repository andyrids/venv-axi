---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/setup.md
  - specs/behaviors/skill-content.md
authors:
  - specs/commands/serve.md
issues: [55]
pr: 59
---

# Plan: MCP registration uses the module form

## Scope

`venvaxi setup` registers the `venvaxi` console-script shim as the MCP stdio command. On Windows a
running `venvaxi serve` holds that shim open, so `uv`'s reinstall of `venv-axi` on the next
dependency change cannot delete it and the sync fails with `os error 32` naming a file the caller
was not thinking about. Nothing is corrupted; the cost is a confusing hard failure at an unrelated
moment, in a repo where an agent session is open.

The condition is created by `setup` itself, and after
[`plans/ambient-collapse-to-skill.md`](ambient-collapse-to-skill.md) an MCP registration is the
intended default integration, so it reproduces for any contributor on Windows with the server
registered. `specs/commands/setup.md` declared *that* the server is registered but never *what
command* - the shim spelling was an implementation choice with no spec behind it.

Register the running interpreter invoking the package as a module instead. The interpreter is not
replaced by a package reinstall, so the sync is unobstructed.

Out of scope: what the served surface exposes, owned by `specs/mcp/tools.md`; identifying which
project and venv the server is bound to, owned by
[#46](https://github.com/andyrids/venv-axi/issues/46); and any migration hook that rewrites a
consuming repo's `.mcp.json` outside a `setup` run, now declared Never in
`specs/commands/setup.md` Out of scope.

## Implements

`specs/commands/setup.md` Actions, as amended by this plan - the registered command is
`<python> -P -m venvaxi serve`, the interpreter path is registered unresolved, and an entry naming
anything else is replaced on the next run. The same plan amends the spec and brings the code into
conformance, which `plans/README.md` resolves in favour of `specs:`.

`specs/behaviors/skill-content.md` - the clause requiring an entry for each observed failure mode
that costs an agent a wasted query or a wrong conclusion. `os error 32` is such a mode and the
packaged skill does not carry it, so the skill is brought into conformance with a spec already on
the default branch. No amendment to that spec.

`specs/commands/serve.md` is under `authors:`, not `specs:`. The module form already works; the
amendment declares an equivalence that was previously assumed, and no code changes for it.

## Approach

1. Flip to `status: in-progress`.
2. Amend `specs/commands/setup.md` and `specs/commands/serve.md` per Implements, and run the ripple
   check in `specs/README.md`. (Done at authoring: 7 plans cite `setup.md` and 1 cites `serve.md`,
   all `status: done` and frozen.)
3. Rename `_axi_command()` to `_axi_interpreter()` in `_ambient.py`, returning `sys.executable`
   **verbatim**, and change the registered entry's `args` to `["-P", "-m", "venvaxi", "serve"]`.
   The `.resolve()` the old helper applied to `sys.argv[0]` MUST NOT be carried over - see Risks.
4. Repoint the 11 `mock.patch` sites in `tests/test_ambient.py`, update the command and args
   assertions, and add two tests: an entry naming the shim is replaced, and - unmocked - the
   registered command equals `sys.executable` exactly.
5. Add the `os error 32` gotcha to `src/venvaxi/SKILL.md`, then `just skill-sync`. Add an eval case
   for the misdiagnosis.
6. Amend `ICM/_config/reference-toolchain-uv.md` with the recovery move. It is `immutable: true`;
   this is a deliberate amendment, not a passing edit.
7. `README.md` and `docs/architecture.md`.
8. `CHANGELOG.md` - `Fixed` for the sync failure, `Changed` for the registered command's new shape.

## Validation

- [x] Where `fastmcp` is importable, when `setup` runs, the `setup` command shall write a `VenvAXI`
      entry whose command is the running interpreter and whose args are
      `["-P", "-m", "venvaxi", "serve"]`.
      — `tests/test_ambient.py::test_update_mcp_json_creates_file`, and a live
      `venvaxi setup` in a throwaway project whose written `command` was the venv's
      `python.exe` with `args` exactly `["-P", "-m", "venvaxi", "serve"]`
- [x] Where the interpreter path is a symlink, when `setup` runs, the `setup` command shall register
      that path unresolved.
      — `tests/test_ambient.py::test_axi_interpreter_does_not_resolve_symlinks`, shown failing
      against a deliberately reintroduced `Path(...).resolve()`; synthetic symlink, no live
      POSIX venv (see Notes)
- [x] While an entry naming the `venvaxi` console-script shim is present, when `setup` runs, the
      `setup` command shall replace it and report the file as modified.
      — `tests/test_ambient.py::test_update_mcp_json_replaces_console_script_entry`, and a live
      run over a planted shim entry reporting `".mcp.json": true` with an unrelated `other`
      server preserved
- [x] While an entry already names the module form, when `setup` runs, the `setup` command shall
      report the file unmodified.
      — `tests/test_ambient.py::test_update_mcp_json_idempotent`, and a second consecutive live
      `venvaxi setup` reporting `".vscode": false` and `".mcp.json": false`
- [x] When the registered command is spawned as an MCP stdio server, the `serve` command shall
      connect and advertise the eight tools in `specs/mcp/tools.md`.
      — a `fastmcp` `StdioTransport` client spawning the `command`/`args` read back out of the
      written `.mcp.json`, listing all eight tool names
- [x] While a module named `logging` sits in the working directory, when the registered command is
      spawned, the `serve` command shall start unaffected.
      — the same client spawned with `logging.py` and `json.py` planted, identical eight-tool
      surface; the control without `-P` failed with `RuntimeError: shadowed json imported!`
- [x] Where the platform is Windows, while a server started from the registered command is running,
      when `uv` syncs the project, the sync shall succeed.
      — `uv sync --reinstall-package venv-axi` with a module-form server alive (PID 37304)
      exiting 0, against `os error 32` exit 2 for the same command with shim-form servers up
- [x] Where `fastmcp` is not importable, when `setup` runs, the `setup` command shall write no
      `VenvAXI` entry and shall remove one already present.
      — a purpose-built venv without the `mcp` extra, where `setup` reported `".mcp.json": true`,
      removed the planted entry, created no `.vscode/` and exited `EX_OK`
- [x] The packaged skill shall carry a gotcha naming the `os error 32` sync failure and the recovery
      move, rather than the symptom alone.
      — `src/venvaxi/SKILL.md` Gotchas, with `tests/test_skill_parity.py` confirming the
      installed copy byte-identical

## Risks / unknowns

- **`.resolve()` would break POSIX silently.** The helper being replaced ends
  `Path(sys.argv[0]).resolve()`. Carrying that habit onto `sys.executable` resolves
  `.venv/bin/python` through its symlink to the base interpreter, which has none of the venv's
  packages, so the registered server dies with `ModuleNotFoundError: venvaxi`. Every existing test
  mocks the helper, so nothing would catch it - hence the unmocked assertion in step 4 and the
  second Validation criterion.
- **Why `-P` and not a bare `-m`.** The issue proposed `python -m venvaxi serve`. That fixes the
  lock but adds a failure vector: `-m` puts the working directory on `sys.path[0]` and the shim
  does not, so a consuming repo with a top-level `logging.py`, `types.py` or `json.py` would break
  a server the shim form started fine, presenting as an import traceback with no obvious link to
  `setup`. `-P` removes that entry and nothing else, and `requires-python = ">=3.11"` makes it
  always available. Without it, `serve.md`'s equivalence claim would ship with a known
  counterexample.
- **The home view's `bin` reads as a module path under the module form.** Reproduced: a bare
  `python -m venvaxi` emits a `bin` naming the package's `__main__.py`. It does not affect this
  change - the registration always passes `serve`, never the home view - and
  `specs/commands/home.md` already declares `bin` as the resolved path of `sys.argv[0]`, which
  stays true under both spellings. No divergence, so no amendment. This is the one open question
  the issue raised, and it is answered.
- **`uvx` / `uv tool run venvaxi setup`** registers an ephemeral or tool-venv interpreter that
  serves the wrong environment. Pre-existing with `sys.argv[0]` and not a regression, but more
  legible under the module form. [#46](https://github.com/andyrids/venv-axi/issues/46) is where a
  bound-environment report would land.
- **Chicken-and-egg on first application.** Applying the fix requires running `setup`, which may
  itself be blocked by the currently-registered shim-form server. Stop the server once before the
  first `setup`; every run after that is unobstructed.
- **No diff will show the migration.** `.mcp.json` and `.vscode/` are gitignored, so this repo's
  own rewritten registrations produce no reviewable diff. Every check reads the files directly.
- **The eval case is a specimen, not a gate** - [#40](https://github.com/andyrids/venv-axi/issues/40)
  means the suite runs nowhere.

## Notes

**The issue's option 1 was not quite right, and the fix is `-P -m`, not `-m`.** The issue proposed
`python -m venvaxi serve`. That removes the lock but adds a failure the shim never had: `-m` puts
the working directory on `sys.path[0]`, an MCP client spawns the server with the consuming repo's
root as cwd, and any top-level module there shadows one the server imports at startup. Verified
rather than reasoned - in a directory holding `logging.py` and `json.py`, bare `-m` died with
`RuntimeError: shadowed json imported!` while `-P -m` and the old console script both ran clean.
`requires-python = ">=3.11"` makes `-P` free. Without it `specs/commands/serve.md` would have
shipped an equivalence claim with a live counterexample, which is what forced the decision.

**`sys.executable` is returned verbatim, and that is load-bearing.** The helper this replaced ended
`Path(sys.argv[0]).resolve()`. Carrying that habit over would break POSIX silently: `.venv/bin/python`
resolves through its symlink to the base interpreter, which has none of the venv's packages, so the
registered server would die with `ModuleNotFoundError: venvaxi`. Every pre-existing test in the
module mocks the helper, so nothing would have caught it. The `NOTE` in `_ambient.py` exists so the
next reader does not tidy the missing `.resolve()` back in.

**Only one of the two interpreter tests discriminates on Windows.** The plain
`_axi_interpreter() == sys.executable` assertion cannot fail here - `.venv\Scripts\python.exe` is a
real file, so `resolve()` is a no-op. `test_axi_interpreter_does_not_resolve_symlinks` was added
during implementation for that reason and proven by reintroducing the regression: it failed, the
plain one passed. Do not read the two as independent proofs. Neither ran against a live POSIX venv;
the symlink is synthetic and `sys.executable` is monkeypatched, so the real
`.venv/bin/python` shape is still unexercised.

**The failure is intermittent, and that is why it took a forced reinstall to reproduce.** `uv` only
deletes the shim when it actually reinstalls `venv-axi`. A plain `uv run python -c "print('sync ok')"`
succeeded with three shim-form servers running; `uv sync --reinstall-package venv-axi` was needed to
trigger it. Recorded because a contributor who runs one command, sees it pass and concludes the
registration is fine has drawn the wrong conclusion - the skill gotcha and the CHANGELOG entry were
both tightened at closeout to say so.

**No migration code was written, and none was needed.** `_update_mcp_json` already compares the
built entry against what is on disk, so an old shim entry is unequal, gets overwritten and is
reported modified. The idempotent rewrite *is* the migration. A repo that never re-runs `setup`
keeps the old entry, which `specs/commands/setup.md` Out of scope now declares deliberate.

**A discarded verification run looked like a pass.** The first planted shim entry was written with
unescaped Windows backslashes, so `setup` correctly rejected it as malformed and replaced it
wholesale - exercising the malformed-recovery path, not replacement, while producing exactly the
`".mcp.json": true` a passing run produces. Redone with valid JSON. Worth remembering: for this
command, "the file changed" is not evidence of *which* path changed it.

**`docs/architecture.md` called the skill "opt-in".** Stale since PR 57 made it the default, in the
paragraph this run amended and contradicted 14 lines below. Corrected here; outside this plan's
stated scope, so it is disclosed rather than folded in silently.

**Issue #43 was already closed before this plan opened.** It was raised as a possible coupling.
`plans/setup-skill-by-default.md` had already discharged it and recorded that #55 would rebase onto
its wording - which is what happened. Nothing was left over.

## Follow-ups

- **Issue [#46](https://github.com/andyrids/venv-axi/issues/46)** - the MCP surface still cannot say
  which project and venv it is bound to. This run sharpened the case: the registered command is now
  an interpreter path, so a `uvx` or `uv tool run venvaxi setup` would register an interpreter
  serving an environment the caller did not mean. Pre-existing with `sys.argv[0]` and not a
  regression, but more legible now, and a bound-environment report is where it would surface.
- **Issue [#40](https://github.com/andyrids/venv-axi/issues/40)** - eval case 11
  (`axi-uv-sync-locked-shim-misdiagnosis`) was added and, like the other ten, never executed. The
  suite is now 11 specimens and still runs nowhere.
- **Tracked as** - no live POSIX evidence for the unresolved-interpreter criterion. The symlink test
  is synthetic; a WSL2 or Linux run of `venvaxi setup` inside a real venv would close it. No issue
  filed: the unit test discriminates, and the gap is recorded in Notes rather than pretended shut.
- **None deferred** - no `Deferred to` entries, so no downstream plan required absorption in this
  commit.
