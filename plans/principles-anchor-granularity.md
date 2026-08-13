---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
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
pr: 34
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

- [x] Every principle in `## The 10 AXI Principles` shall carry its own heading. —
      `grep -c '^### Principle ' specs/principles.md` reports `10`
- [x] The `## The 10 AXI Principles` heading shall still exist, so an inbound link to
      `#the-10-axi-principles` still resolves. —
      `grep -c '^## The 10 AXI Principles$' specs/principles.md` reports `1`
- [x] No spec under `specs/` shall name a principle in prose without linking to that principle's
      own anchor. —
      `grep -rn 'Principle [0-9]\|principle [0-9]' specs/ --include='*.md' | grep -v
      'principles.md#' | grep -v '^specs/principles.md'` reports no match, over 10 citations in
      8 files
- [x] Every `principles.md#...` anchor appearing anywhere under `specs/` or `docs/` shall match a
      real heading in `specs/principles.md`. —
      all 12 anchors from `grep -rho 'principles\.md#[a-z0-9-]*' specs/ docs/ | sort -u` resolve
      against the 16 headings from `grep '^#\{2,3\} ' specs/principles.md`
- [x] The principle wording under each new heading shall be unchanged from the text this plan
      found there. —
      `git diff 5822c58..HEAD -- specs/principles.md` shows each principle's body text carried
      over verbatim. Two presentational changes, both intended and neither a rewording: each
      body is capitalized where it was previously a mid-sentence clause after a dash, and
      principle 6's name reads 'and' rather than '&' in its heading, because an ampersand slugs
      to a doubled hyphen
- [x] The markdown gate shall pass over every amended file. —
      `uv run -m prek run --all-files` reports `Check Markdown [PyMarkdown]......Passed`

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

**Anchor form was the whole design.** `### Principle N, <name>` slugs to `#principle-n-<name>` -
the comma disappears, the digits survive, and the anchor reads as the citation does. Two choices
follow from that and are not cosmetic. Principle 6 is headed 'structured errors and exit codes'
rather than using an ampersand, which would slug to a doubled hyphen. The separator is a comma
rather than a dash, because `Principle 5 - definitive empty states` slugs to
`principle-5---definitive-empty-states`, and the comma form already matched how the citing specs
phrase it in prose - so the eight repoints read naturally instead of being retrofitted.

**The container heading stays deliberately.** Twenty-three inbound links pointed at
`#the-10-axi-principles` before this work. Finer anchors were not worth breaking every one of
them, and an external or historical link should still land somewhere sensible. Nothing under
`specs/` now uses it, but it costs one heading to keep it resolving.

**A content error found while repointing.** `setup.md` cited 'principle 6, idempotent mutations'.
That is not a principle name - idempotent mutations are a clause inside principle 6, structured
errors and exit codes. Writing the anchor forced the question of what the anchor should say, which
is the incidental value of this kind of work: a prose citation can name something that does not
exist, and a link cannot.

**Two citations the first pass missed.** The `## Principles` bullets were the obvious eight. A
grep for principle references in body prose found two more - `list.md`'s minimal-default-schemas
line and `mcp/tools.md`'s explicit-invocation line in `## Out of scope`. Both are now linked. The
lesson is that the criterion had to quantify over prose anywhere in `specs/`, not over the
`## Principles` sections, or it would have passed while leaving the defect in place.

**The wording criterion passed with a qualification, stated in its citation rather than here.**
Each principle's body text carried over verbatim; what changed is that a clause following a dash
became a sentence, so its first word is capitalized. Recorded plainly because 'unchanged' would
otherwise be a slightly stronger claim than the diff supports.

**Stages 02 and 03 were skipped, and announced before the run rather than at closeout.** This plan
writes no source and no test, so both stages had no artifact to produce. Every criterion above is
discharged by inspection and grep, and each cites the command a future reader can re-run.

## Follow-ups

- **Issue** [#20](https://github.com/andyrids/venv-axi/issues/20) - the PyMarkdown tokenizer crash
  stays open with its workaround; untouched here.
- **Deferred to** - none.
- **Tracked as** - the finer anchors will rot exactly as the container anchor did if a principle
  is ever renamed without the ripple check in `specs/README.md`. No plan owns automating that
  check, and none is proposed; the existing process covers it if followed.
