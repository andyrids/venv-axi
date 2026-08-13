---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs: []
authors: []
issues: []
pr:
---

# Plan: Repair the plan record

## Scope

Restore `plans/pre-release-conformance.md`, deleted from `develop` as undeclared collateral of the
spec conformance sweep, and correct two defects in the frozen
[spec-conformance-sweep](spec-conformance-sweep.md) record: four Follow-ups labelled `Tracked as`
with no target, and a Notes paragraph asserting there was nothing for deferral absorption to bind.

Out of scope: the other nine plan files commit `b3bd320` deleted. They stay deleted, by decision -
the restoration here is scoped to the one plan the open issues cite.

**Eligibility for express-change.** All three conditions in `ICM/express-change/CONTEXT.md` hold.
No `specs/**` file changes; `plans/` is not a surface `specs/README.md` covers, so the first
condition passes on its 'touches nothing specs cover' branch rather than on spec conformance -
which is why `specs:` is empty rather than populated. It is one commit's worth, with no dependency
and no public surface. Every criterion below is evidenced within this run.

## Implements

Nothing. This plan implements no spec and authors none. It repairs the tracked record two other
documents depend on: `plans/README.md`'s freeze rule, and issues #28 to #31, each of which cites
`pre-release-conformance.md` as its origin.

## Approach

1. Open this plan at `status: in-progress`.
2. Restore `plans/pre-release-conformance.md` from `main`, where it survives at its merged
   content. Normalize only its frontmatter to the current contract in `plans/README.md` -
   `context-hierarchy`, `context-hierarchy-role`, `immutable` and `authors:` did not exist when it
   froze. The body is restored byte-for-byte; a restoration that rewrites the record it restores
   defeats itself.
3. Relabel the four `Tracked as` Follow-ups in `spec-conformance-sweep.md` to the taxonomy form
   their content requires - `Deferred to` for the three now absorbed by downstream plans, `Issue`
   plus `Deferred to` for the one that also has a filed issue (#29).
4. Correct that plan's Notes: strike the sentence claiming no `Deferred to` entries were written,
   and record the collateral plan deletion with the reason it matters.
5. Discharge deferral absorption. `plans/README.md` requires each `Deferred to` entry to edit the
   named downstream plan in the same commit. The three named plans -
   [hint-surface-parity](hint-surface-parity.md), [setup-ambient-error](setup-ambient-error.md)
   and [principles-anchor-granularity](principles-anchor-granularity.md) - are authored in this
   same change, each carrying an Approach bullet and Validation criterion cross-linked back.

## Validation

- [x] The `plans/` directory shall contain `pre-release-conformance.md` at `status: done`,
      carrying every frontmatter key `plans/README.md` contracts. — `ls plans/` lists it; its
      frontmatter carries `context-hierarchy`, `context-hierarchy-role`, `immutable`, `status`,
      `depends`, `specs`, `authors`, `issues` and `pr`
- [x] The restored body of `pre-release-conformance.md` shall be identical to its content on
      `main` below the frontmatter block. — `diff <(git show
      main:plans/pre-release-conformance.md | tail -n +9) <(tail -n +13
      plans/pre-release-conformance.md)` reports no difference
- [x] No Follow-up entry in `plans/spec-conformance-sweep.md` shall carry a `Tracked as` label
      with no target following it. — `grep -n '^- Tracked as -' plans/spec-conformance-sweep.md`
      reports no match; the four entries now read `Deferred to`, one of them alongside
      `Issue [#29]`
- [x] Where a Follow-up in `plans/spec-conformance-sweep.md` names a downstream plan, that plan
      shall exist under `plans/` and shall cross-link back to the deferring plan. — all three
      named plans exist (`hint-surface-parity.md`, `setup-ambient-error.md`,
      `principles-anchor-granularity.md`) and each names
      `[spec-conformance-sweep](spec-conformance-sweep.md)` in its Scope
- [x] The markdown gate shall pass over every file this plan touches. — `uv run -m prek run
      --all-files` reports `Check Markdown [PyMarkdown]..........Passed`, alongside Ruff, Mypy and
      the remaining five hooks

## Risks / unknowns

- Editing a frozen plan is the thing the freeze rule exists to prevent. The rule admits one
  exception - 'edit only to correct the record' - and both edits are corrections of statements
  that were false when written, not revisions of the work. Each is attributed to this plan inside
  `spec-conformance-sweep.md` so a reader meets the amendment rather than discovering it in
  `git log`.
- Restoring one plan and not the other nine leaves the record partial. That is the decision, not
  an oversight, and it is stated in Scope so a later reader does not read the nine as never having
  existed.
- New markdown risks the PyMarkdown tokenizer crash in
  [#20](https://github.com/andyrids/venv-axi/issues/20). No pipe characters were placed in nested
  list items.

## Notes

**Status is `in-progress`, not `done`, and that is deliberate.** `plans/README.md` calls closeout
'the last commit before merge' and asks for `pr:` at the same moment. Every Validation criterion
above is evidenced and ticked, but no PR exists yet, so flipping to `done` would freeze a record
whose `pr:` is empty. The status flips when the PR number is real.

**Why `specs:` and `authors:` are both empty.** Express asks for `specs:` to name what the change
conforms to, and this change conforms to nothing under `specs/` - `plans/` is not a surface specs
cover. Populating either field to look complete would put a false owner into the Invariant 1
coverage check, which reads exactly these two fields.

**Restoration is one plan, not ten.** `b3bd320` deleted ten. Restoring only
`pre-release-conformance.md` was a decision taken before this plan opened, on the grounds that it
is the one four open issues cite by name. The other nine are recorded in
`spec-conformance-sweep.md`'s Notes so their absence is documented rather than silent, and any
later decision to restore them starts from that list rather than from `git log`.

**Frontmatter was normalized; the body was not touched.** `pre-release-conformance.md` froze before
`context-hierarchy`, `context-hierarchy-role`, `immutable` and `authors:` entered the contract, so
a verbatim restore would have failed the current frontmatter rules on arrival. Those four keys were
added and nothing else changed - `authors: []` because that plan brought code into conformance and
authored no spec. The body diff against `main` is empty, which is the criterion above.

**Deferral absorption is discharged in this same change.** The three `Deferred to` entries this
plan wrote into `spec-conformance-sweep.md` each name a plan authored alongside it, and each of
those plans carries the deferred item in its Scope with a link back. `plans/README.md` requires
that binding in the same commit, and it holds only if all six plan files land together.

## Follow-ups

- **Issue** [#20](https://github.com/andyrids/venv-axi/issues/20) - the PyMarkdown tokenizer crash
  is untouched by this work and stays open with the workaround in place. It is listed here because
  every plan authored in this change adds markdown, and it is the gate most likely to bite.
- **Deferred to** - none. The three deferrals this plan *wrote* are absorbed, as recorded in Notes;
  it defers nothing of its own.
- **Tracked as** - the nine plan files left deleted from `develop`. They survive on `main`, so the
  record is recoverable, but no plan owns restoring them and none is proposed.
