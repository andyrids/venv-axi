---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---

# Standard - markdown

Markdown documents and project documentation follow typographical and stylistic conventions based
on the *New Oxford Style Manual* (*New Hart's Rules*).

## (1) Headings and capitalization

- MUST use sentence case for all headings and subheadings (capitalize only the first letter of the
  first word and any proper nouns)
- MUST preserve the casing of acronyms, initialisms, proper nouns and product names wherever they
  fall in a heading (`CLI`, `MCP`, `TOON`, `STDOUT`, `STDERR`, `AXI`, `YAGNI`, `PyMarkdown`)
- MUST NOT include terminal punctuation (full stops, colons) at the end of a heading
- MUST leave a single blank line before and after a heading - enforced by PyMarkdown MD022 and
  MD023 via the `pkgdx-markdown` hook, so this needs no manual checking
- SHOULD keep heading lengths concise and descriptive

```markdown
# Standard - markdown file styling

## (1) File headers

This is an example of sentence case capitalization.
```

### H1 title convention

Reference documents take an H1 naming the kind of document, mirroring the filename patterns in
`reference-standard-naming.md`:

| File pattern                    | H1 form                     |
| ------------------------------- | --------------------------- |
| `reference-standard-[name].md`  | `# Standard - [name]`       |
| `reference-toolchain-[tool].md` | ``# Toolchain - `[tool]` `` |

Tracked artifacts keep their own `Kind: Name` prefixes, which are structural rather than
prose - `# Command: venvaxi find`, `# Behavior: Output contract`, `# Plan: [summary]`. Sentence
case applies to the text after the prefix.

## (2) Punctuation and quotation

- MUST use single quotation marks (`' '`) for primary quotes or emphasized terms
- MUST use double quotation marks (`" "`) only for quotes enclosed within quotes
- MUST NOT use full stops for contractions (e.g., Dr, Revd, Ltd, Mr)
- MUST use full stops for abbreviations that cut a word short (e.g., ed., vol., e.g., i.e.)
- MUST use a single space after terminal punctuation (e.g., after a full stop or question mark)
- SHOULD use Oxford spelling conventions (*-ize* and *-ization* suffixes where etymologically
  appropriate, such as *organize* and *normalization*) for consistency with standard academic and
  technical publishing

Oxford spelling is not American spelling. It retains *-our*, *-re* and *-ce* forms - *behaviour*,
*colour*, *centre*, *licence* - and changes only the *-ise* suffix family. Do not 'correct'
those while applying the rule above.

### Verbatim content is exempt

These rules govern prose. Content reproduced verbatim keeps its source characters exactly,
because changing them changes its meaning:

- Code spans and fenced code blocks
- YAML frontmatter values (`version: "0.1.0"`)
- Quoted literals that are part of a syntax being documented (`` `"42"` ``, `` `"-3.14"` ``)
- Command invocations, file paths and configuration snippets

A quotation mark inside backticks is data, not punctuation. Rewriting it breaks the example.

## (3) Bulleted and numbered lists

- MUST start every list item with an initial capital letter, regardless of whether it is a
  fragment or full sentence
- MUST NOT alter the casing of a list item that opens with a code span, file path, command name
  or identifier - the literal spelling of the identifier wins over the capitalization rule
- MUST use a full stop at the end of each list item if the items consist of complete sentences
- MUST NOT use terminal punctuation on list items that cannot stand alone as a sentence
- SHOULD keep list syntax strictly consistent within the same list block (do not mix fragments and
  full sentences)

### The fragment test

Completeness is grammatical, not a matter of length. An item that cannot stand alone as a
sentence takes no terminal full stop however long it runs.

Requirement bullets written with a modal keyword are **fragments**, because the subject is
elided:

```markdown
- MUST use sentence case for all headings and subheadings
```

That reads `[Headings] MUST use sentence case`, which is a dependent clause with no expressed
subject, so it takes no full stop. Contrast the imperative, which carries an implied second-person
subject and *is* a complete sentence:

```markdown
- Use sentence case for all headings.
```

The common failure is not missing stops but mixing both forms inside one block:

```markdown
- `count: <n>` and a `symbols` table of `name`, `kind`   <- noun phrase, no stop
- Footer names `venvaxi inspect <qualified_name>`.       <- sentence, takes one
```

## (4) Numbers, dates, and measurements

- MUST spell out numbers from one to nine in body text
- MUST use numerals for 10 and above
- MUST use numerals for all technical units of measurement, percentages, and ages, regardless of
  the number (e.g., 5%, 8 MB, 2 GB)
- MUST NOT spell out numbers acting as identifiers or enumerators rather than quantities
  (`### (1) Scan`, `Phase 2`, `Table 3`, `Layer 1`, `Principle 5`)
- SHOULD format dates in the logical sequence: Day Month Year (e.g., 8 August 2026) without
  internal commas

## (5) Document headers (frontmatter)

- MUST include a YAML frontmatter block at the very top of standard documents outlining the
  `context-hierarchy`
- MUST follow the existing project spacing and metadata key structures

```yaml
---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---
```

### Scope

This section alone is scoped. Sections 1-4 govern every Markdown file the project authors,
including `.claude/**` - only the frontmatter *schema* there is owned by the harness, not the
prose.

'Standard documents', for the frontmatter requirement above, means:

| Tree                              | In scope | Frontmatter schema                        |
| --------------------------------- | -------- | ----------------------------------------- |
| `ICM/**`                          | Yes      | `context-hierarchy`                       |
| `specs/**`                        | Yes      | `context-hierarchy`                       |
| `plans/*.md`                      | Yes      | `status`, `depends`, `specs`, `issues`, `pr` |
| `AGENTS.md`, `CONTEXT.md`         | Yes      | `context-hierarchy`                       |
| `.claude/**`                      | No       | Harness-owned (`name`, `description`)     |
| `CHANGELOG.md`, `README.md`       | No       | None - format set by Keep a Changelog     |
| `src/venvaxi/SKILL.md`            | No       | Harness-owned skill frontmatter           |

Two carve-outs within the in-scope trees:

- **`CHANGELOG.md` section headings** are reserved names fixed by Keep a Changelog
  (`### Added`, `### Changed`, `### Fixed`, `### Removed`). They are not subject to §1.
- **Plans at `status: done` are frozen.** `plans/README.md` permits editing them 'only to correct
  the record'. Typographical restyling is not a correction, so a frozen plan is left as written
  even where it predates this standard.
