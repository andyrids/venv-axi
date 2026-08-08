---
status: in-progress
depends: []
specs:
  - specs/README.md
  - specs/principles.md
  - specs/architecture.md
  - specs/commands/home.md
  - specs/commands/list.md
  - specs/commands/show.md
  - specs/commands/find.md
  - specs/commands/tree.md
  - specs/commands/inspect.md
  - specs/commands/inherits.md
  - specs/commands/serve.md
  - specs/commands/setup.md
  - specs/behaviors/output-contract.md
  - specs/behaviors/qualified-name-semantics.md
  - specs/behaviors/cache-refresh.md
  - specs/mcp/tools.md
issues: []
pr:
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
- [x] Every spec on `develop` is implemented or carries a plan - the one gap introduced by
  `specs/commands/inspect.md` is covered by [inspect-own-docstring](inspect-own-docstring.md)
- [ ] `/audit-spec-drift` runs and reports the `fastmcp::FastMCP` docstring conflict in Table 3.
  The conflict itself is confirmed by hand; the auditor agent has not yet been exercised
- [ ] One end-to-end `/create-feature` run produces a spec amendment, a plan, and a closeout

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

Populated at closeout.

## Follow-ups

Populated at closeout.
