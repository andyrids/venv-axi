---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: planned
depends:
  - plan-record-repair
specs: []
authors:
  - specs/principles.md
  - specs/behaviors/package-resolution.md
  - specs/commands/find.md
  - specs/commands/home.md
  - specs/commands/inherits.md
  - specs/commands/list.md
  - specs/commands/setup.md
  - specs/commands/tree.md
  - specs/mcp/tools.md
issues: []
pr:
---

# Plan: Principles anchor granularity

## Scope

`specs/principles.md` rendered 'The 10 AXI Principles' as one numbered list under a single
heading. Eight specs linked `#the-10-axi-principles` and then named 'Principle 5' or 'Principle 9'
in prose beside it, so a reader following the link landed on the list and had to find the principle
themselves. No anchor resolved to the thing being cited.

Give each principle its own heading and repoint the eight citations. Absorbs the first Follow-up of
[spec-conformance-sweep](spec-conformance-sweep.md), which flagged this and declined to fix it.

Out of scope: the principle text itself. It is quoted from [axi.md](https://axi.md/) and is not
this project's to reword - only the headings around it are added. Also out of scope: the five
project-local principles below the list, which already carry their own headings and are already
linked by anchor.

## Implements

Nothing. This plan authors the nine files in `authors:` - notation and structure only, no
observable behaviour, no line under `src/` or `tests/`. It sits in `authors:` rather than `specs:`
for the reason `plans/README.md` gives: a spec listed in `specs:` makes stage 03 verify a code
conformance the plan never delivered.

`specs/principles.md` gains ten `###` headings. The other eight files each convert a prose
principle name plus a container-anchor link into a direct link to the principle.

## Approach

1. Flip to `status: in-progress`.
2. Restructure `specs/principles.md`: keep `## The 10 AXI Principles`, its source attribution and
   its design-contract sentence; promote each numbered item to
   `### Principle N, <name>` with the cited wording as its body. Add one sentence recording that
   the headings are this project's and the wording is the source's, so a later reader does not
   read the restructure as an edit to the citation.
3. Keep the container heading. Twenty-three inbound links pointed at it before this work, and an
   external or historical link to `#the-10-axi-principles` should not break to buy the finer
   anchors.
4. Repoint the eight citing specs from `([The 10 AXI Principles](...#the-10-axi-principles))`
   beside a prose name, to a direct link on the principle name itself.
5. `home.md` and `setup.md` each cite two principles in one bullet; give each its own link rather
   than linking the first and leaving the second in prose.
6. Correct `setup.md` while repointing it. It cited 'principle 6, idempotent mutations', which is
   not a principle name - idempotent mutations are declared inside principle 6, structured errors
   and exit codes. The link now names the principle and the prose says where the clause sits.
7. Run the ripple check in `specs/README.md` over the nine amended files.
8. `CHANGELOG.md` entry under `Changed`.

**No stage 02 or 03.** This plan writes no source and no test, so implementation and verification
have no artifact to produce. The skip is announced here rather than discovered at closeout, per the
conditional-checkpoint rule in `ICM/process-plan/CONTEXT.md`.

## Validation

- [ ] Every principle in `## The 10 AXI Principles` shall carry its own heading.
- [ ] The `## The 10 AXI Principles` heading shall still exist, so an inbound link to
      `#the-10-axi-principles` still resolves.
- [ ] No spec under `specs/` shall name a principle in prose without linking to that principle's
      own anchor.
- [ ] Every `principles.md#...` anchor appearing anywhere under `specs/` or `docs/` shall match a
      real heading in `specs/principles.md`.
- [ ] The principle wording under each new heading shall be unchanged from the text this plan
      found there.
- [ ] The markdown gate shall pass over every amended file.

## Risks / unknowns

- Promoting list items to headings changes the file's shape, and `principles.md` is a citation.
  The mitigation is that only the headings are added; every principle's sentence is moved
  verbatim, and the file says so where a reader will meet it.
- Ten new `###` headings could be read as ten new project principles rather than a restructured
  quotation. The retained source attribution and the added sentence are what keep that distinction
  on the page.
- The finer anchors will rot the same way the container anchor did if a future principle is renamed
  without a ripple check. `specs/README.md` already prescribes that check; this plan runs it and
  changes nothing about the process.

## Notes

## Follow-ups
