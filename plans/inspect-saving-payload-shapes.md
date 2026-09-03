---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs: []
authors:
  - specs/principles.md
  - specs/commands/inspect.md
issues: [98]
pr:
---

# Plan: Inspect saving payload shapes

## Scope

`specs/principles.md` published a table of measured TOON savings, sourced by name to
`tests/test_toon_benchmark.py`, whose `inspect` row read `~6%`. That figure's evidencing fixture
(`SYMBOL_OBJECT`) carries a 21-character `doc` value which never takes the encoder's quoting
branch, so one number stood for a command whose payload shape changes under `--docstring`
([#98](https://github.com/andyrids/venv-axi/issues/98)).

Remeasuring settled two things the issue's own prose got wrong, and the spec now states them
rather than the issue's version. Newlines are **not** what costs the encoder anything:
`json.dumps` escapes `\n` to the same two characters TOON does, so a multi-paragraph docstring
encodes no worse than a single line. What the quoting branch costs is exactly the two surrounding
quotes, whatever the value holds. And the saving on a flat object does not scale with content at
all. For symbol mode's four fields it is 14 characters, minus 2 for every value that takes the
quoting branch, so a real symbol lands between 6 and 12 with ~10 the common case. The *percentage*
is therefore a function of payload size alone.

Publish that invariant in the unit it actually has. The `inspect` row becomes a single row reading
`~10 chars` rather than a percentage, the mechanism is stated in prose with real symbols as worked
examples, every published figure gains a rule requiring a named fixture behind it, and
`specs/commands/inspect.md` - which repeated the stale `~6%` - is repointed at the mechanism.

Splitting the row by `--docstring` was the shape this plan first took, and the stage 01 gate
rejected it: the flag is not the variable, symbol size is, and the two rows overlapped in
measurement. See Notes.

Out of scope: the `list` (~45%) and `find` (~27%) rows, which nothing in the issue impeaches and
which this plan leaves untouched. Also out of scope: `src/venvaxi/_toon.py` and the truncation
limit in `specs/behaviors/output-contract.md`. No encoder defect was found, the escaping is
spec-legal, and the complete-body rule under `--docstring` is deliberate - the defect is entirely
in the evidence, not in what the evidence measures.

## Implements

Nothing under `src/`. This plan authors the two files in `authors:` and rebuilds the fixtures that
evidence them; no observable tool behaviour moves, so `venvaxi inspect` emits byte-for-byte what
it emitted before.

It sits in `authors:` rather than `specs:` for the reason `plans/README.md` gives: stage 03
verifies observable behaviour against every `specs:` entry, and a plan that lists a spec it only
wrote produces a false divergence finding. The one clause that might look like a conformance
claim - the new 'every figure MUST be reproducible from a named fixture' rule - is addressed to
whoever edits the table, in the same modal form as the `MUST NOT cite ~40%` rule beside it. It
governs an author, not the software, so there is no code for stage 03 to hold against it.

`specs/principles.md` gains one table row, two paragraphs of mechanism and a sharpened decisive
paragraph. `specs/commands/inspect.md` loses the repeated figure and states the mechanism instead,
so the two files cannot drift apart on a number again.

## Approach

1. Flip to `status: in-progress`.
2. `tests/test_toon_benchmark.py` only. No `src/` change - the encoder is correct and the issue
   found no defect in it.
3. Derive all three symbol-object fixtures from one shared base mapping of `qualified_name`,
   `kind` and `signature`, so that `doc` is structurally the only variable. A convention that only
   says 'keep these keys identical' is one careless edit from being untrue, and the whole point of
   the fixtures is that the measured variable is isolated.
4. Keep `SYMBOL_OBJECT` as the short-first-line fixture. It is still a true measurement of the
   default path for the common symbol, and the issue does not impeach it - it impeaches its
   standing in for the whole command.
5. Add a truncated-path fixture: a first line longer than the 200-character limit, reduced through
   the same truncation the command applies, size-hint suffix included, so the fixture measures the
   string the command would actually emit rather than a hand-written approximation of it.
6. Add a full-docstring fixture: a synthetic multi-paragraph body. **Synthetic by design** - the
   module imports only `venvaxi._toon` and depends on no installed package, and pinning the
   fixture to a real venv docstring would couple a unit test to an installed version, so the
   benchmark would start failing on an upgrade that changed nothing about the encoder.
7. Add the durable guard: a test pinning the **absolute** saving across the fixtures - equal for
   the unquoted ones however long their `doc` grows, exactly two characters lower for the quoted
   one. A percentage band does not survive someone rewording a fixture; the absolute saving does,
   because it is a property of the key set rather than of the values.
8. Add a test isolating the quoting branch on a controlled pair - one value differing from the
   other by a single space-for-newline substitution, identical in length - asserting the saving
   falls by exactly two, and that a value holding many newlines costs no more than one holding a
   single newline.
9. Replace the percentage band with the character count.
   `test_object_encoding_saving_is_marginal` currently asserts `0.0 < saving < 0.20`, a band wide
   enough to pass on payloads the table never described. Assert the published `~10 chars`
   instead - the exact `14 - 2 * quoted` count on each fixture, and the 6-to-12 window any
   emittable symbol object falls in. Percentages leave the test file entirely, which is the
   point: the spec no longer publishes one for this row.
10. Amend the module docstring to name `specs/principles.md` as the table these fixtures feed, so
    the next editor of either file is told the other exists.
11. `CHANGELOG.md` entry under `Changed`.

The ripple check in `specs/README.md` was run in stage 01 over both amended specs. Every hit is
`status: done` and frozen, so no plan was edited; the result is recorded in Notes at closeout.

## Validation

- [x] The TOON encoder shall save the same absolute number of characters over compact JSON on a
      flat symbol object whatever the length of its `doc` value, the object's key set being held
      constant. — `tests/test_toon_benchmark.py::test_object_saving_is_invariant_to_doc_length`
- [x] When a symbol object's `doc` value enters the encoder's quoting branch, the saving over
      compact JSON shall fall by exactly two characters against an otherwise identical object
      whose `doc` does not, whatever number of newlines the quoted value holds.
      — `tests/test_toon_benchmark.py::test_object_quoting_branch_costs_exactly_two_chars`
- [x] The TOON encoder shall save 14 characters over compact JSON on a flat symbol object whose
      four values are all unquoted, less two for each value that takes the quoting branch.
      — `tests/test_toon_benchmark.py::test_object_encoding_saving_is_marginal`
- [x] Where a symbol object is one `venvaxi inspect` could emit, its `qualified_name` always
      carrying `::`, the encoder shall save between 6 and 12 characters over compact JSON.
      — `tests/test_toon_benchmark.py::test_object_encoding_saving_is_marginal`, which asserts
      `6 <= saving <= 12` on each of the three symbol-object fixtures
- [x] The character count published in the `inspect` row of the measured-efficiency table in
      `specs/principles.md` shall be reproduced by a named fixture in
      `tests/test_toon_benchmark.py`. — by inspection: `specs/principles.md:78` publishes
      `~10 chars`, and `SYMBOL_OBJECT` (`tests/test_toon_benchmark.py:83`) re-derives to exactly
      10 through `encode_object`/`json.dumps`; the module docstring's NOTE
      (`tests/test_toon_benchmark.py:8-11`) names it among the fixtures the table cites
- [x] The symbol-object fixtures shall differ from one another in their `doc` value only.
      — `tests/test_toon_benchmark.py::test_symbol_object_fixtures_differ_only_in_doc`
- [x] The benchmark module shall build no fixture from a package installed in the venv.
      — by inspection: the module's complete import list
      (`tests/test_toon_benchmark.py:18-22`) is `json`, `typing.Any`,
      `venvaxi._introspect.truncate` and `venvaxi._toon.encode_object`/`encode_table` - stdlib
      and first-party only, with no installed distribution imported or read
- [x] The markdown gate shall pass over every amended file. — `uv run prek run --all-files`,
      8 hooks passing including `Check Markdown [PyMarkdown]`

## Risks / unknowns

- **A percentage row for `inspect` is falsifiable in both directions, and the first draft was
  falsified in both.** The gate measured real symbols across both paths: `os.path::join` saves
  ~11% on the default path, above the drafted `~2-6%` ceiling, and `rich.console::Console.print`
  saves ~1.5% on the same path, below its floor. The rows also overlapped - `os::getcwd` under
  `--docstring` (~8%) beats `Console.print` on the default path (~1.5%) - so the flag was never
  the variable. Publishing a character count removes the risk rather than mitigating it: there is
  no band left to fall outside. The percentages survive only as worked examples in prose, where
  they are labelled as examples of one invariant.
- **The character count is constant for a *fixed key set*, not universally.** It is 14 less two
  per quoted value, and the 14 itself rises by three characters per additional key. Symbol mode's
  four fields are declared in `specs/commands/inspect.md`, so the count holds for as long as that
  field list does - and a change to that list is a spec change that will reach this table through
  the same ripple check.
- **A synthetic full-docstring fixture cannot notice a change in what real docstrings look like.**
  Accepted deliberately: a fixture that could notice it would also fail on an unrelated upgrade,
  and the quantity being measured is a property of the encoder, not of any package's prose.
- **The 6-to-12 window is the one remaining band, and it is a weak one.** It is bounded by how
  many of four values take the quoting branch, not by anything a fixture chooses, so a reworded
  fixture cannot move it - but it would also not notice the encoder gaining a fifth field. The
  exact `14 - 2 * quoted` criterion above it is what catches that, and the window exists only to
  state what a caller can actually observe.

## Notes

**Re-entry at the stage 01 gate, before any implementation.** The plan first split the `inspect`
row in two - a default-truncated row at `~2-6%` and a `--docstring` row at `<1%` - and the
techspec carried a `[NEEDS CLARIFICATION]` asking whether the range or a `<6%` bound was the right
shape, because the real `Console.print` payload measured below the drafted floor. The gate
answered with neither, on the strength of measurements across more symbols than the draft had
taken: `os.path::join` saves ~11% on the default path and `os::getcwd` ~8% under `--docstring`, so
the drafted range was wrong at its ceiling as well as its floor, and the two rows overlapped. A
small symbol's complete docstring saves a larger share than a large symbol's truncated one, which
means `--docstring` was never the variable - symbol size is. Splitting by the flag would have
reproduced [#98](https://github.com/andyrids/venv-axi/issues/98) in a new form: a second figure
standing for a payload shape it does not describe.

The resolution is to publish the invariant in the unit it has. One `inspect` row, `~10 chars`,
with the percentages moved into prose as labelled worked examples. The third column now mixes
units, and the spec says so rather than forcing the object row into a percentage it does not have.
Two Validation criteria and one Approach step were rewritten to match; the marker is cleared. No
code had been written when this landed, so the re-entry cost one editing pass and nothing else -
which is the argument for the gate sitting where it does.

**The mechanism [#98](https://github.com/andyrids/venv-axi/issues/98) asserts is wrong, and the
issue text will keep suggesting it.** Its prose says each newline "costs one character in JSON and
two in quoted TOON", so a multi-paragraph docstring should encode progressively worse. It does not.
`json.dumps` escapes `\n` to the same two characters TOON does, making newlines exactly
cost-neutral; what entering the quoting branch costs is the two surrounding quotes, once, however
many newlines the value holds. Measured rather than reasoned:
`test_object_quoting_branch_costs_exactly_two_chars` builds a same-length triple - all spaces, one
newline, nineteen newlines - and both newline variants save exactly 2 less than the baseline and
identically to each other. Recorded here because a reader returning to #98 for the rationale will
otherwise re-derive a false mechanism from the issue text; the spec and this plan state the real
one.

**Why the published figure is a character count rather than a percentage.** On a flat object there
is no repeated header to amortize, so nothing about the saving depends on the values: it is
`14 - 2 x quoted` for the four fields symbol mode emits. An emittable symbol always carries `::` in
its `qualified_name`, which forces that value into the quoting branch, so between one and four
values quote and the saving lands in a 6-to-12 window, with ~10 the common case. The percentage is
then a function of payload size alone - which is why the drafted band was falsifiable in both
directions and was falsified in both. Changing the unit removes the failure mode; narrowing the
band would only have moved it.

**Why `authors:` and not `specs:`.** No observable behaviour moved - `git diff develop -- src/` is
empty - so there is no conformance for stage 03 to verify, and listing an authored spec under
`specs:` manufactures a false divergence finding. The full argument is in Implements and is not
repeated here.

**The `truncate()` size-hint suffix carries no TOON structural character.** `truncate()` appends
`... truncated, N chars total - use --docstring to see complete body`, which holds no character in
`_STRUCTURAL_CHARS` (`src/venvaxi/_toon.py:30`) - the one comma is not structural and is not the
active delimiter. So a truncated `doc` enters the quoting branch only if its retained
first-200-character portion carries one itself, and `_LONG_FIRST_LINE` was written with a `:`
inside that portion deliberately. Lose it and `TRUNCATED_SYMBOL_OBJECT`'s quoted count falls from 3
to 2: the fixture stops measuring the quoted path while still looking as though it does. Stage 02
surfaced it and stage 03 confirmed the failure would be loud rather than silent -
`test_object_encoding_saving_is_marginal` asserts `saving == 14 - 2 * quoted` per fixture, so it
would assert 8 against an actual 10. This is exactly the shape of defect #98 was filed about,
caught before it could be written in a second time.

**The `CHANGELOG.md` entry was written at stage 02, one stage early - and this plan caused it.**
Approach step 11 lists the changelog entry as implementation work, so the stage 02 agent wrote it
faithfully; stage 04's contract owns it. The deviation was flagged and accepted, and stage 03
checked the entry's content against what it had verified and found nothing overstated. It is named
here rather than only in a stage report because the plan is the durable artifact a future run
learns from, and the defect is in this plan's own ordering - closeout output does not belong in an
Approach list. Stage 04 verified the entry rather than rewriting it, and found one inaccuracy the
content check had not been looking for: it claimed "three new fixtures" where `SYMBOL_OBJECT`
already existed on `develop` and was rebuilt from the shared base mapping rather than added. Two
fixtures are new. Corrected in place; no second entry was added.

**Ripple check, re-run at closeout over both amended specs.** `grep -l 'specs/principles.md'
plans/*.md` returns eleven plans and `grep -l 'specs/commands/inspect.md' plans/*.md` returns
eight, this plan included in each. Every other hit carries `status: done` and is frozen, so no
downstream plan was edited - confirming the stage 01 result Approach promised to record here.

## Follow-ups

- **Issue** - none. Stage 03 reported no findings: every Validation criterion passed, there was no
  conformance comparison to run under the `authors:`/`specs:` split, and the encoder carried no
  defect (`git diff develop -- src/` empty). Its independent re-derivation reproduced all four
  published worked examples and all 16 quoting combinations. The four issues still open against
  milestone 0.5.0 - [#97](https://github.com/andyrids/venv-axi/issues/97),
  [#110](https://github.com/andyrids/venv-axi/issues/110),
  [#115](https://github.com/andyrids/venv-axi/issues/115) and
  [#122](https://github.com/andyrids/venv-axi/issues/122) - are already tracked, and none is
  touched by this run.
- **Deferred to** - none. Nothing was carried out of scope: the `list` and `find` rows,
  `src/venvaxi/_toon.py` and the truncation limit in `specs/behaviors/output-contract.md` were
  declared out of scope in Scope, and none of them acquired work here.
- **Tracked as** - none.
