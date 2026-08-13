---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: planned
depends: []
specs: []
authors:
  - specs/commands/find.md
  - specs/commands/home.md
  - specs/commands/inherits.md
  - specs/commands/inspect.md
  - specs/commands/list.md
  - specs/commands/serve.md
  - specs/commands/setup.md
  - specs/commands/show.md
  - specs/commands/tree.md
  - specs/behaviors/cache-refresh.md
  - specs/behaviors/output-contract.md
  - specs/behaviors/package-resolution.md
  - specs/behaviors/qualified-name-semantics.md
  - specs/behaviors/symbol-graph.md
  - specs/mcp/tools.md
  - specs/principles.md
issues: []
pr:
---

# Plan: Spec conformance sweep

## Scope

Migrate the 16 spec files parked at `_specs/` into `specs/`, bringing each into conformance with
the installed `icm-spec` standards (`ICM/_config/reference-standard-spec.md`, `-validation.md`,
`-markdown.md`, `-naming.md`). The sweep normalizes structure and notation only - frontmatter,
section names and order, EARS for normative statements, an `## Out of scope` section per spec -
and preserves every rationale paragraph, link and principle reference as written.

`specs/architecture.md` splits by kind: observable state promotes into `specs/behaviors/`
(a new `symbol-graph.md`, plus cache identity and project root resolution folded into
`cache-refresh.md`); the module map, stack and skill-copies note move to `docs/architecture.md`.
`_specs/README.md` is discarded - the installed template `specs/README.md` supersedes it.

No file under `src/` or `tests/` changes. This sweep alters no observable behaviour, which is why
`specs:` is empty and every file sits in `authors:`.

Out of scope for this plan: `_AGENTS.md` and `_config/` remain parked in the repo root untouched.

## Implements

Nothing - this plan implements no spec. It authors the 16 files listed in `authors:`: the nine
command specs, the five behavior specs (one new), the MCP tool contract and the project
principles. The code they describe already exists and already conforms; the plan claims
authorship, not conformance work.

## Approach

1. Author this plan at `status: planned`.
2. Normalize frontmatter on every migrated file: `context-hierarchy: Layer 3`,
   `context-hierarchy-role: Desired state`, `immutable: false`, `tags: [...]`; no
   `maximum-context-tokens` (specs are unbudgeted per `AGENTS.md`).
3. Restructure the nine command specs to the interface template: `## Invocation / inputs`,
   `## Data requirements`, `## Outputs`, `## Failure modes` (absorbing `## Exit codes` and
   `## Errors`), `## Out of scope`, `## Principles`. Exit-code enums stop being restated - link
   to `specs/behaviors/output-contract.md#exit-codes`; each failure criterion states what the
   caller observes, including the exit status. `setup.md` keeps `## Actions` after
   `## Data requirements`.
4. Convert normative statements to EARS per `reference-standard-validation.md`; rationale prose
   stays prose. Reconcile every `## Invocation / inputs` table against
   `uv run venvaxi <verb> --help` (Invariant 4 - `--help` wins).
5. Write `## Out of scope` fresh for the 15 non-`principles` files, naming genuine adjacent
   capabilities and where each went.
6. Split `architecture.md` as scoped above; delete it; fix the moved principles link in
   `docs/architecture.md`.
7. Restructure `mcp/tools.md` in place, recording the one-file consolidation as a deliberate
   exception to the one-file-per-unit rule.
8. Normalize `principles.md` frontmatter only.
9. Delete `_specs/` once empty.

## Validation

- [ ] Every spec file under `specs/` except `README.md` shall carry
      `context-hierarchy: Layer 3`, `context-hierarchy-role: Desired state`, `immutable: false`
      and a `tags:` key.
- [ ] No spec file under `specs/` except `README.md` shall carry a `maximum-context-tokens`
      key.
- [ ] Every command spec shall present the interface template headings in template order, and no
      spec shall retain a `## Output rules`, `## Exit codes` or `## Errors` heading.
- [ ] Every spec except `principles.md` shall contain an `## Out of scope` section.
- [ ] Every command spec's `## Invocation / inputs` shall agree with
      `uv run venvaxi <verb> --help` for its verb.
- [ ] The test suite shall pass unchanged (`uv run pytest`).
- [ ] No relative link inside `specs/` shall point at `architecture.md`, and every
      `principles.md#...` anchor shall match a real heading in `specs/principles.md`.
- [ ] The `_specs/` directory shall no longer exist.

## Risks / unknowns

- EARS conversion can silently change normative meaning. Mitigation: convert sentence by
  sentence, keeping the original modal strength (`MUST NOT` -> `shall not`) and leaving every
  rationale clause intact.
- The `architecture.md` split could strand content that is neither observable state nor stack
  documentation; anything ambiguous lands in `docs/architecture.md` rather than being dropped.
- Several specs name implementation symbols (`SymbolStore.canonical_name`, `_record_symbol`,
  `sys.stdout.write`) that `reference-standard-spec.md` says specs must not pin. Deliberately
  left: it is outside the six divergence classes this sweep fixes, and stripping them risks
  rewriting the thinking.

## Notes

## Follow-ups

- Tracked as - `specs/principles.md` renders 'The 10 AXI Principles' as one numbered list under a
  single heading, so `find.md`, `home.md`, `list.md`, `setup.md`, `tree.md`, `inherits.md`,
  `package-resolution.md` and `mcp/tools.md` link `#the-10-axi-principles` and then name
  'Principle 5' / 'Principle 9' in prose that no anchor resolves to. It is a citation of an
  external source ([axi.md](https://axi.md/)), so the container heading is defensible; flagged
  here rather than fixed.
