---
status: done
depends: []
specs: []
issues: []
pr: 21
---

# Plan: Roll out the markdown standard and fix the drift

## Scope

Apply `ICM/_config/reference-standard-markdown.md` across every Markdown file the project
authors, and amend the standard where it could not be applied as written.

`specs: []` is deliberate. Documentation typography is not `venvaxi` observable behaviour, so no
`specs/**` file changes meaning and this plan claims no conformance work. Heading text inside
`specs/**` changes, but what those specs declare does not.

## Implements

Nothing in `specs/`. This is a documentation-convention rollout.

## Approach

### (1) Amend the standard before applying it

Three rules could not be executed as written, and a standard that must be violated to be followed
gets ignored. Added to `reference-standard-markdown.md`:

- Acronyms, initialisms and proper nouns keep their casing (§1), without which `## MCP tools` is
  a violation
- An H1 title convention (§1), previously unwritten - `# Standard - [name]` and
  ``# Toolchain - `[tool]` ``, mirroring `reference-standard-naming.md`
- A verbatim-content exemption (§2) covering code spans, fences, YAML frontmatter and documented
  literals, protecting `` `"42"` `` in the TOON cheatsheet and `version: "0.1.0"` in skill
  frontmatter
- Oxford `-ize` promoted from COULD to SHOULD, with a note that Oxford spelling keeps `-our`,
  `-re` and `-ce` forms and changes only the `-ise` family
- A grammatical fragment test (§3) replacing the length-based one, plus a carve-out for items
  opening with a code span or identifier
- A scope section (§5) naming which trees carry `context-hierarchy` frontmatter, and two
  carve-outs: Keep a Changelog reserved section names, and frozen plans

### (2) Fix the drift source, not just the drift

`reference-standard-spec.md` carries the **templates** that generate command and behavior specs,
and they specified `## Data Requirements`, `## Output Rules`, `## Exit Codes` and `## Applies To`.
Sweeping the nine command specs without fixing the templates would have reintroduced Title Case on
the next spec authored. The templates were corrected first.

### (3) Sweeps

- **Headings** - 123 Title-Case headings across 37 files to sentence case, preserving acronyms and
  the structural `Kind: Name` prefixes
- **Quotation** - 122 prose double-quote characters across 23 files to single, with code spans
  protected programmatically
- **Oxford spelling** - nine `-ize` family words; `exercise`, `revise` and `advertise` were left
  alone as they are not `-ize` family
- **List punctuation** - one genuine missing full stop

### Deliberately unchanged

- **`CLAUDE.md`** is a symlink to `AGENTS.md` (git mode `120000`). Edited via `AGENTS.md` only;
  writing it as a file would have replaced the link.
- **Frozen plans.** Four plans at `status: done` carry Title-Case headings and `-ise` spellings.
  `plans/README.md` permits editing a frozen plan 'only to correct the record', and restyling is
  not a correction. Exempted, and the exemption is now written into the standard's §5.
- **`## The 10 AXI Principles`** in `specs/principles.md` is the cited title of an external work
  (`axi.md`), quoted as such on the following line. Hart's retains the capitalization of cited
  titles. Left as-is, along with the seven link texts referencing it.
- **`## Why?` and `## How?`** in `README.md`. §1 forbids full stops and colons in headings;
  a question mark on an interrogative heading is legitimate.
- **`# Technical spec: [slug]`** kept its `Kind: Name` form rather than becoming
  `# Standard - techspec`, because that H1 is a template copied into the generated artifact.

## Validation

- [x] Heading drift recount returns 0 (was 123 across 37 files)
- [x] TOON literals at `reference-standard-toon.md` retain double quotes
- [x] `version: "0.1.0"` intact in all three SKILL.md frontmatter blocks
- [x] `-our` spellings preserved (`behaviour`, `favours`)
- [x] `CLAUDE.md` still resolves as a symlink to `AGENTS.md`
- [x] `uv run prek run --all-files` passes - all eight hooks, no `BadTokenizationError`
- [x] `uv run pytest` holds its pass count - 217 passed
- [x] No files under `src/venvaxi/*.py` modified
- [x] `venvaxi` home view renders and SKILL.md frontmatter still parses

## Risks / unknowns

The quote sweep touched list items across 23 files. `reference-toolchain-pymarkdown.md` documents
a `BadTokenizationError` that fires on pipes in nested list items and names no file or line, so a
failure here needs bisecting by file.

## Notes

The plan estimated a cluster of mixed-punctuation list blocks. That estimate came from a detector
that inspected only each item's **first** line; most flagged items were already correctly
punctuated on their continuation lines. Re-measured against item end-lines, the real drift was a
single missing full stop in `CHANGELOG.md`. The remaining eight flagged blocks are colon-stems
introducing sub-lists, which are correct.

The templates in `reference-standard-spec.md` were the drift's actual source and were not in the
original scope. Sweeping the nine command specs without fixing them would have reintroduced Title
Case on the next spec authored - the sweep would have looked complete and silently regressed. A
rollout of a documentation standard SHOULD fix whatever generates the documents before fixing the
documents.

Measuring drift by regex over headings needs an acronym allowlist, or it reports proper nouns and
cited titles as violations. The allowlist that took the count from 123 to 0 is not reusable as a
gate without being maintained, which is part of why no automated check was added.

Delivered as a single commit, `941afac`, rather than one commit per sweep. The sweeps are
independent and would have bisected more cleanly split apart.

## Follow-ups

- **Tracked as** - no automated gate enforces sentence case, single quotes or Oxford spelling.
  PyMarkdown checks structure (MD022, MD023, line length), not typography, so §1-§4 rely on the
  routing added in this plan being read. A custom linter was considered and rejected under
  `reference-standard-yagni.md`; revisit only if the drift recurs.
