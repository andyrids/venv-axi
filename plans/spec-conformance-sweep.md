---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
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
pr: 33
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

- [x] Every spec file under `specs/` except `README.md` shall carry
      `context-hierarchy: Layer 3`, `context-hierarchy-role: Desired state`, `immutable: false`
      and a `tags:` key. — `for k in 'context-hierarchy: Layer 3' 'context-hierarchy-role:
      Desired state' 'immutable: false' 'tags:'; do grep -rL "^$k" specs --include='*.md' |
      grep -v README.md; done` reports no file, over 16
- [x] No spec file under `specs/` except `README.md` shall carry a `maximum-context-tokens`
      key. — `grep -rln 'maximum-context-tokens' specs --include='*.md' | grep -v README.md`
      reports no file
- [x] Every command spec shall present the interface template headings in template order, and no
      spec shall retain a `## Output rules`, `## Exit codes` or `## Errors` heading. —
      `grep -rn '^## ' specs/commands/ specs/behaviors/` shows the six interface headings in
      order across nine command specs (`setup.md` carrying `## Actions` after
      `## Data requirements`) and the five behavior headings across five; a second pass for the
      three retired headings, `grep -rn '^## Output rules' specs/` and the same for
      `'^## Exit codes'` and `'^## Errors'`, reports no match
- [x] Every spec except `principles.md` shall contain an `## Out of scope` section. —
      `grep -rL '^## Out of scope' specs/commands specs/behaviors specs/mcp --include='*.md'`
      reports no file, over 15
- [x] Every command spec that names a subcommand shall present an `## Invocation / inputs`
      section agreeing with `uv run venvaxi <verb> --help` for that verb. —
      `uv run venvaxi <verb> --help` run for all eight verbs and diffed against each table; every
      positional and flag agrees, and the four documented defaults match `src/venvaxi/_cli.py`
      lines 545, 563, 591 and 610
- [x] The `## Invocation / inputs` section of `home.md` shall agree with `uv run venvaxi --help`,
      the authority for the bare invocation it specs, which takes no subcommand. —
      `uv run venvaxi --help` reports `usage: venvaxi [-h] [-v]` over the eight subcommands,
      agreeing with the spec's `venvaxi [-v|--verbose]`
- [x] The test suite shall pass unchanged (`uv run pytest`). — `uv run pytest -q` reports
      `260 passed in 20.83s`
- [x] No relative link inside `specs/` shall point at `architecture.md`, and every
      `principles.md#...` anchor shall match a real heading in `specs/principles.md`. —
      `grep -rn 'architecture\.md' specs/` reports no match; all 23 inbound anchors found by
      `grep -rho 'principles\.md#[a-z0-9-]*' specs/ | sort -u` resolve against
      `grep '^#\{2,3\} ' specs/principles.md`
- [x] The `_specs/` directory shall no longer exist. — `ls _specs` reports
      `No such file or directory`

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

**Closeout order.** [PR #33](https://github.com/andyrids/venv-axi/pull/33) was opened from the
already-pushed branch *before* this commit was written, so `pr:` carries a real number rather than
a placeholder and this stays what `plans/README.md` calls it - the last commit before merge. The
alternative, committing closeout and patching `pr:` afterwards, ends with a frozen plan whose
final edit lands after the record it freezes.

**Why `specs:` is empty.** The sweep authored 16 specs and changed no line under `src/` or
`tests/`. Listing them in `specs:` would have made stage 03 verify code conformance this plan never
delivered, and would have given every spec a covering plan by `grep` - the exact trap
`plans/README.md` records this methodology walking into on first use, where the coverage check was
built and defeated in the same commit. `authors:` is the honest field and Invariant 1 accepts it.

**Four decisions, taken before the sweep ran.**

1. *`architecture.md` splits by kind.* It mixed observable state with module decomposition, and
   `specs/README.md` rules module names and file paths out of specs entirely. Landing it unchanged
   would have put the tree in drift on day one and made the drift auditor's first run meaningless.
   Observable state promoted to `specs/behaviors/symbol-graph.md` and into `cache-refresh.md`'s
   existing `### Cache identity` subsection - merged rather than appended, to avoid a near-duplicate
   - and the stack, module map and skill-copies note left `specs/` for `docs/architecture.md`.
2. *`mcp/tools.md` stays one file.* Splitting eight tools into eight files would duplicate the nine
   command specs eight times over, which `reference-standard-spec.md` warns against in the same
   breath as its one-file-per-unit rule. The consolidation is recorded in the file itself as a
   deliberate exception, so a future reader meets the reasoning before the rule.
3. *EARS covers normative statements only.* Outputs, Failure modes and behavior Rule/Details take
   EARS; rationale prose stays prose. The subject test in `reference-standard-validation.md`
   decides it - the 'why this rule exists' lines address the reader, not the system, and forcing
   'the system shall' onto them adds ceremony and loses the actor.
4. *Exit-code enums stop being restated.* Each command spec previously carried its own copy of the
   enum; it is declared once at `specs/behaviors/output-contract.md#exit-codes` and classed as
   stack mechanics by the authoring standard. All eight verb specs now link it, and each failure
   criterion still states the exit status the caller observes.

**Gotcha: `home.md` does not spec a verb.** Its subject is the bare invocation - `# Command:
venvaxi`, no subcommand - so `venvaxi home --help` errors with `invalid choice: 'home'`. The
filename is a slug for the landing view, not a verb name.

**Re-entry to stage 01 at closeout.** The original `--help` criterion was written 'for its verb'
and so could not be evaluated for `home.md` - unsatisfiable for one of the nine files it
quantified over, the same defect class the drift auditor caught in the first two criteria while
this plan was still `planned`. It was split into two independently tickable criteria before any
verification report existed, so no report/plan identifier mapping was broken.
`ICM/process-plan/CONTEXT.md` asks for re-entries in Notes and `plans/README.md` holds Notes empty
until closeout; the reference wins over the stage contract, so it is recorded here.

**No techspec was written.** `ICM/process-plan/stages/01-specification/output/` holds only its
`.gitkeep`. The techspec is the *how*, and its section (4) asks for the step-by-step logic to
fulfil the objective - prospective content that would have been fabricated after the fact for work
already committed, in a gitignored file due for deletion. The skip is announced rather than
silent, per the workspace's conditional-checkpoint rule.

**The pipeline was not walked.** The sweep executed and was committed (`b3bd320`, with all 16
specs and this plan in the same commit, which is what satisfies Invariant 1 on the branch) while
the plan still read `status: planned`. Stages 02 and 03 were skipped deliberately at closeout:
this plan authored specs and touched no code, so neither stage had an artifact to produce and
running them would have manufactured two empty reports. A plan reading `planned` over committed
work is precisely the drift the auditor exists to catch, which is why the status was reconciled
rather than left to look tidy.

**Reconciling `specs/` found no divergence owned by this plan.** `specs:` is empty and no code
moved, so closeout step 6 discharges vacuously. The three divergences found while sweeping are
pre-existing, predate this work and are recorded below. No `Deferred to` entries were written, so
there is nothing for deferral absorption to bind.

## Follow-ups

- Tracked as - `specs/principles.md` renders 'The 10 AXI Principles' as one numbered list under a
  single heading, so `find.md`, `home.md`, `list.md`, `setup.md`, `tree.md`, `inherits.md`,
  `package-resolution.md` and `mcp/tools.md` link `#the-10-axi-principles` and then name
  'Principle 5' / 'Principle 9' in prose that no anchor resolves to. It is a citation of an
  external source ([axi.md](https://axi.md/)), so the container heading is defensible; flagged
  here rather than fixed.
- Tracked as - `AmbientContextError` is defined but never raised, so a failed `setup` write
  escapes as exit 2. That contradicts `specs/commands/setup.md` and contradicts
  `specs/behaviors/output-contract.md#exit-codes`, which reserves exit 2 for venvaxi itself being
  broken. Needs a code fix under its own plan, listing `setup.md` in `specs:`.
- Tracked as - the `## Divergences from the CLI` list in `specs/mcp/tools.md` is inaccurate. The
  `getSymbolTool` footer item is in fact parity and should not be listed, while
  `showPackageApiTool` and `showModuleTool` footer behaviour under `docstring=true` is a real
  divergence that is missing. Needs a spec amendment under its own plan - and it is exactly the
  drift that file's own Local principle exists to prevent.
- Tracked as - `list --all` with zero results emits a hint naming `--all`, the flag the caller
  just used, against the suppression rule in `specs/behaviors/output-contract.md`. Needs a code
  fix under its own plan.
- Several specs still name implementation symbols (`SymbolStore.canonical_name`, `_record_symbol`,
  `sys.stdout.write`) that `reference-standard-spec.md` says a spec must not pin. Left in place
  deliberately, as recorded under Risks / unknowns; stripping them risks rewriting the thinking
  rather than the notation. No plan owns this yet.
