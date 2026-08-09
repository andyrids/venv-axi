---
status: done
depends: []
specs: []
issues: []
pr: 10
---

# Plan: Adopt spec-driven development into ICM

## Scope

Introduce the two artifact layers ICM lacked - a permanent `specs/` contract and a durable
`plans/` record - and rewire the `create-feature` pipeline to produce and close them.

Closes the `README.md` TODO: *"Research spec-driven development integration & ICM suitability"*.

In scope: `specs/`, `plans/`, the four ICM stage `CONTEXT.md` files, three `_config` references,
the `icm-spec` skill, the spec-drift auditor, and the `AGENTS.md` hook block.

Out of scope: any change to `src/venvaxi/`. This plan is documentation and agent configuration
only, so the test suite must be green before and after with no delta.

Also out of scope: a `venvaxi plans` / `venvaxi next` CLI query layer. specops ships one because
a team cannot compute a multi-repo plan DAG by eye. A solo project with a handful of plans can,
and `reference-standard-yagni.md` forbids building it before it is needed. Revisit past roughly a
dozen open plans with real `depends:` chains; `grep` over frontmatter covers it until then.

## Implements

The state/motion split from
[JarvusInnovations/specops](https://github.com/JarvusInnovations/specops), adapted to ICM.

The diagnosis: `01-specification/output/[slug]-spec.md` is named "spec" but is structurally a
specops **plan** - it describes what to change in a module, not what must always be true. And
`.gitignore`'s `ICM/**/output/*` destroys it on the next run. ICM therefore had only motion, and
threw that away too.

Most of `specs/` is relocation rather than authoring. `reference-standard-axi.md` already held
the 10 AXI principles and the qualified-name invariants - desired state mis-filed as a toolchain
convention.

## Approach

1. **`specs/`** - seed from existing content: principles and the measured token table from
   `reference-standard-axi.md`, the qualified-name invariants from the same file, the module map
   from `AGENTS.md`, and one command spec per CLI verb read off `_cli.py`.
2. **`reference-standard-axi.md`** - reduce to a pointer stub rather than delete. It has eight
   inbound references, four of them in shipped source docstrings; deleting it would drag this
   plan into `src/`, which is out of scope.
3. **`plans/`** - protocol in `plans/README.md`, seeded by this file.
4. **ICM stages** - 01 emits spec change + plan + techspec; 03 validates against the specs named
   in the plan's `specs:` field; 04 becomes the closeout.
5. **`_config`** - new `reference-standard-spec.md`; retarget sections (1) and (6) of
   `reference-standard-techspec.md`; add spec/plan rows to `reference-standard-naming.md`.
6. **Agent surface** - `icm-spec` skill, `spec-drift-auditor` agent, `/audit-spec-drift` command,
   and an always-loaded `AGENTS.md` block.

## Validation

- [x] `git check-ignore -v specs plans` returns nothing; stage `output/` dirs still ignored
- [x] Every `specs/commands/*.md` invocation table matches `_cli.py` argparse definitions
- [x] `reference-standard-axi.md` stub keeps all eight inbound references resolvable
- [x] `AGENTS.md` block sits outside the `venvaxi:begin/end` markers
- [x] `uv run -m prek run --all-files` passes on every new and modified file
- [x] `uv run coverage run -m pytest` is green, with no delta against the pre-change run
  (201 passed)
- [x] `uv run venvaxi setup` regenerates the ambient block without disturbing the new
  `AGENTS.md` section - reported all-`false`, nothing rewritten
- [x] Every spec on `develop` is implemented or carries a plan - verified by audit, after
  correcting this plan's own `specs:` field (see Notes)
- [x] `/audit-spec-drift` runs and reports the `fastmcp::FastMCP` docstring conflict in Table 3 -
  reported it, plus seven further conflicts
- [ ] One end-to-end `/create-feature` run produces a spec amendment, a plan, and a closeout -
  not done; deferred, see Follow-ups

## Risks / unknowns

- **`AGENTS.md` token budget.** The file declares `maximum-context-tokens: 800` and the new block
  pushes it. Offset by trimming `## Navigation`, whose module map now lives in
  `specs/architecture.md`. The budget key is declarative - nothing measures it - so this is a
  hygiene risk, not a functional one.
- **Two methodologies claiming feature work.** The `icm-spec` skill and
  `ICM/create-feature/CONTEXT.md` could each present as the owner. Mitigated by an explicit scope
  boundary in the skill: it teaches how to write a spec or plan; the pipeline owns the stages.
- **Spec drift in the specs themselves.** Command specs transcribed from `_cli.py` will rot as
  the CLI changes. Mitigated by the invariant that `--help` is authoritative, and by the auditor.
- **PyMarkdown line length.** New files wrap at ~95 columns to match existing `_config` files. If
  the vendored `pkgdx` config enforces something narrower, reflow is required.

## Notes

**This plan's `specs:` field started out listing all 16 spec files, which made the invariant it
introduced unenforceable.** The first audit caught it: a mechanical
`grep -l '<spec>' plans/*.md` then found a covering plan for every spec, so Table 1 could never
report a violation. The check was built and defeated in the same commit.

Corrected to `specs: []`. The field means *"specs this plan brings **code** into conformance
with"*, not *"specs this plan authored"* - and this plan changed no code. Spec tree coverage is
now honest: most specs are satisfied by existing code, and the ones that are not each carry their
own plan. `plans/README.md` should be read with that meaning in mind.

**`reference-standard-axi.md` became a pointer stub rather than being deleted.** It carried eight
inbound references, four of them in shipped source docstrings (`_introspect.py`, `_toon.py`,
`_ambient.py`) plus one in `tests/`. Deleting it would have pulled this plan into `src/`, which
its own Scope rules out. The stub redirects to the three new locations and keeps all eight
resolving. Principle numbers were kept stable so "AXI principle 3" still means the same thing.

**`plans/inspect-own-docstring.md` was forced into existence by the invariant**, not planned up
front. Writing `specs/commands/inspect.md` created a spec declaring behaviour the code does not
implement, which would have been a violation on the first commit. That the methodology produced
this pressure unprompted is the best evidence so far that it works.

**The first audit found eight conflicts, not one.** The Validation checklist above originally
asserted the docstring bug was the only drift the new specs surfaced. That was wrong. Six of the
eight were errors in the specs themselves - transcription mistakes made while reading `_cli.py` -
and were corrected in this same commit:

- `setup.md` claimed the output key was `skill`; it is `SKILL.md`
- `architecture.md` listed five node kinds and two edge kinds; there are six and five
- `architecture.md` stated a `MUST NOT` for `setup --skill` that nothing enforces - softened to
  operational caution
- `inspect.md` and `inherits.md` omitted the reachable `PackageImportError`
- `output-contract.md` named an `EXCEPTION` log level, which does not exist in Python

The remaining two are genuine code bugs and keep their specs unchanged, since the specs state the
desired state correctly. They are owned by the plans listed under Follow-ups.

**A test is asserting a shape production never returns.** `tests/test_cli.py:589-651` mocks
`setup_ambient_context` with a `"skill"`-keyed dict and a comment claiming it mirrors the real
return value. It does not - `_ambient.py:215` returns `"SKILL.md"`. The test passes green against
fiction. Not fixed here (this plan does not touch `src/` or its tests); recorded below.

**Timing.** Closeout is the last commit before merge, so `status: done` and `pr: 10` land *in*
PR #10 rather than after it. A plan flipped post-merge would leave the merge commit containing a
record that claims to still be in flight.

## Follow-ups

- **Deferred to [package-error-taxonomy](package-error-taxonomy.md)** - `find`, `tree` and
  `show --api` raise `PackageImportError` for a package that is not installed, where their specs
  require `PackageNotFoundError`. Specs are correct and unchanged; the code diverges.
- **Deferred to [mcp-hint-parity](mcp-hint-parity.md)** - three `_mcp.py` empty-state hint bugs:
  a hardcoded snake_case tool name, a hint naming the wrong tool, and an `inherits` hint that
  drops one of the two causes it is required to name.
- **Deferred to [inspect-own-docstring](inspect-own-docstring.md)** - the inherited-docstring
  bug, and the end-to-end `/create-feature` run that closes the last unticked Validation
  criterion above. That plan absorbs both.
- **Issue** - `tests/test_cli.py` mocks `setup_ambient_context` with a key production never
  returns, and comments that it mirrors reality. Fix alongside any `setup` work. No plan owns
  this yet; it is too small to warrant one on its own.
- **Tracked as** - `EdgeKind.DEPENDS_ON` is declared but never written or read, and
  `EXPORTS`/`IMPORTS_FROM` are written but never queried. Now documented in
  `specs/architecture.md` as the re-export record with no current consumer. Decide later whether
  to build the provenance feature they anticipate or remove them under YAGNI.
