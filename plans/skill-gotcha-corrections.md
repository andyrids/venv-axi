---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/skill-content.md
authors: []
issues: [74]
pr: 77
---

# Plan: Skill gotcha corrections

## Scope

Two gotchas in the packaged skill (`src/venvaxi/SKILL.md`) assert a fact false in the version they
name, per [issue 74](https://github.com/andyrids/venv-axi/issues/74):

- The dunder gotcha ("Dunders are not indexed") claims the class-symbol workaround surfaces
  "constructor and operator signatures". Only the constructor half reproduces - there is no AXI
  path to any non-constructor dunder at all.
- The decorator gotcha ("Decorators introspect as passthroughs") claims `njit`'s docstring points
  to `jit()`, "which does document `inline` and `cache`". `cache` does not appear in `jit()`'s
  `doc:` body - it occurs once, in the unrelated `signature:` field - and the entry contradicts
  itself three lines later by stating `cache` semantics live in no `__doc__` or signature.

Both entries were introduced by the same run (`plans/skill-earns-its-tokens.md`, issue 52), whose
closing comment records verifying only the first half of each claim.

This ships inside the wheel: `0.3.1` is the first stable release to carry these two gotchas, so
the correction lands as its own patch (`0.3.2`) rather than folding into the `0.3.1` promotion a
parallel unit is running.

Out of scope, per the release plan's unit boundaries: `src/venvaxi/_introspect.py`,
`_cli.py`, `_mcp.py`, `specs/commands/find.md`, `specs/mcp/tools.md` - owned by a parallel unit.
`_introspect.py` is read-only here, to verify the dunder claim structurally. No package is
installed into the venv to chase the decorator claim; numba's absence is reported instead.
Restructuring or "improving" any other gotcha is out of scope (`reference-standard-yagni.md`).

## Implements

`specs/behaviors/skill-content.md`, the rule that "the packaged skill shall restate no claim
about `venvaxi` behaviour that `specs/**` does not declare" and that "an entry earns its place
only if an agent would act differently for having read it". Neither corrected claim was ever
declared in `specs/**` - both were introduced straight into the skill by issue 52 - so this plan
brings `src/venvaxi/SKILL.md` into conformance with the existing rule rather than writing or
amending the spec itself. `specs:` carries `specs/behaviors/skill-content.md`; `authors:` stays
empty.

## Approach

1. Flip to `status: in-progress`.
2. Verify the dunder claim by reading `_walk_class_members` in `src/venvaxi/_introspect.py`
   (read-only): it blanket-skips every `_`-prefixed member name, not `__init__` specifically, and
   the class node's own `signature` is `inspect.signature(cls)`, which CPython resolves to the
   constructor only. Structurally, no non-constructor dunder is reachable.
3. Verify the decorator claim against the installed numba. Confirmed absent from this project's
   venv (`ModuleNotFoundError` on `import numba`) and from the bound MCP binding venv at
   `D:\Projects\github\venv-axi\.venv`; not declared in `pyproject.toml` or `uv.lock` anywhere.
   No package installed to chase this further.
4. Edit `src/venvaxi/SKILL.md`:
   - Narrow the dunder gotcha to state the class-symbol route covers `__init__` only, and that no
     non-constructor dunder has any AXI path today.
   - Drop the unverified `cache` claim from the decorator gotcha, keeping `inline` (not disputed
     by the issue, and not re-verifiable here since numba is absent) and the existing "hard
     boundary" sentence, which already states `cache` semantics are unreachable and now no longer
     contradicts the sentence above it.
5. Regenerate `.claude/skills/venvaxi/SKILL.md` via `just skill-sync`.
6. Run `uv run pytest -v` and `uv run prek run --all-files`; capture output verbatim.
7. Add the `CHANGELOG.md` entry under a new `[0.3.2]` section.
8. Close the plan out per `plans/README.md`.

## Validation

- [x] The packaged skill shall state that the class-symbol workaround for dunders reaches the
      constructor signature only, with no non-constructor dunder reachable by any `venvaxi`
      command. — `src/venvaxi/SKILL.md:208-212`, checked against `_walk_class_members` in
      `src/venvaxi/_introspect.py` (~line 358-359), which blanket-skips every `_`-prefixed member
      name, and `_signature_of(cls)`'s use of `inspect.signature(cls)`, which CPython resolves to
      the constructor only
- [x] The packaged skill shall not claim that `jit()`'s docstring documents `cache`, while
      continuing to state that `inline` is documented there. — `src/venvaxi/SKILL.md:223-229`,
      `grep -n cache src/venvaxi/SKILL.md` returning only the pre-existing, unedited
      `cache=True`/`parallel=True` composition sentence at lines 226-227, with no remaining claim that
      `cache` is documented, and `inline` unchanged on the line above it
- [x] The packaged skill shall no longer point an agent to `jit()`'s docstring for `cache` and
      then state, three lines later, that `cache` semantics live in no `__doc__` or signature -
      the self-contradiction issue 74 names. — same edit as above; the entry now names only
      `inline` as documented, so the "hard boundary" sentence no longer contradicts it
- [x] `.claude/skills/venvaxi/SKILL.md` shall be byte-identical to `src/venvaxi/SKILL.md`. —
      `diff src/venvaxi/SKILL.md .claude/skills/venvaxi/SKILL.md` (no output) after
      `just skill-sync`, and `tests/test_skill_parity.py` 3 passed
- [x] The full test suite, including `tests/test_skill_parity.py`, shall pass. —
      `uv run pytest -v`: 359 passed; `uv run prek run --all-files`: all 8 hooks passed

## Risks / unknowns

- **The decorator fix could not be verified against a live numba.** The project venv carries no
  `numba` install and none is declared anywhere in `pyproject.toml` or `uv.lock`, so `inline`
  survives on the strength of issue 74's own reproduction (against numba 0.67.0) and
  `plans/skill-earns-its-tokens.md`'s prior verification, not a fresh check in this run. Only the
  self-contradiction is corrected; no new unverified claim replaces the removed one.
- **The dunder fix is verified structurally, not empirically.** `polars` is likewise absent from
  this venv, so the fix rests on reading `_walk_class_members` and `_signature_of`'s use of
  `inspect.signature(cls)`, not a live `getSymbolTool` call against `DataFrame.__getitem__`.

## Notes

**"Earns its place" applied to both rewrites.** Per `specs/behaviors/skill-content.md`'s local
principle, an entry earns its place only if an agent would act differently for having read it.

- The dunder gotcha now tells an agent that a `count: 0` or absent-symbol result for a
  non-constructor dunder is not a gap to route around - there is no class-symbol fallback for it.
  Previously an agent debugging `DataFrame.__getitem__` semantics would follow the false pointer,
  query the class, find nothing, and be left unable to tell whether that was a bug in venvaxi's
  index or a bug in the skill's guidance. The corrected text spends that round trip up front
  instead.
- The decorator gotcha now sends an agent to `jit()`'s docstring only for what is actually there
  (`inline`), instead of for `cache` as well. Previously the entry both told an agent `cache` was
  documented in `jit()`'s docstring and, three lines later, that `cache` semantics were
  unreachable by any `venvaxi` command - a direct self-contradiction an agent had to resolve by
  trial. The fix removes the false pointer rather than the correct one.

**numba and polars are both absent from this project's venv**, in the worktree
(`D:\Projects\github\venv-axi\.claude\worktrees\agent-a9772b116ecd97b65\.venv`) and in the bound
main-repo venv (`D:\Projects\github\venv-axi\.venv`) the MCP server targets. Neither is a project
dependency. Per this run's instructions, no package was installed to chase either claim further;
the dunder claim was instead settled by reading `_introspect.py`, and the decorator claim's
`cache` half was removed rather than re-asserted unverified.

**Why `specs:` and not `authors:`.** `plans/README.md` reads `specs:` as "this plan changes code
until it conforms" and `authors:` as "this plan writes the spec". `specs/behaviors/skill-content.md`
already declares the rule both corrections satisfy - that the skill may restate no claim `specs/**`
does not declare, and that an entry earns its place only if it changes what an agent does. Neither
false clause was ever declared anywhere in `specs/**`; both were introduced straight into
`src/venvaxi/SKILL.md` by `plans/skill-earns-its-tokens.md`. This plan edits `SKILL.md` to conform
to the existing rule and does not touch `specs/behaviors/skill-content.md` itself, so `specs:` is
the honest field and `authors:` stays empty.

**Eligibility held throughout.** No `specs/**` file changed; the diff is two sentence-level
corrections in one file plus its generated mirror, one commit's worth, no new dependency, no new
public surface. Every Validation criterion above was evidenced within this run.

## Follow-ups

- **Issue [#39](https://github.com/andyrids/venv-axi/issues/39)** - nothing compares the skill's
  claims against installed packages, which is how both defects shipped silently in the first
  place and how they could drift again. Unowned by this plan; already tracked.
- **None deferred** - no `Deferred to` entries, so no downstream plan required absorption in the
  closeout commit.
