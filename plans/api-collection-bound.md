---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/output-contract.md
  - specs/commands/show.md
  - specs/mcp/tools.md
authors:
  - specs/commands/find.md
issues: [67]
pr: 86
---

# Plan: api-collection-bound

## Scope

`show --api` has no row bound, so a package's whole public surface is emitted in one payload and
the truncated view's own footer suggests the call that makes it worse. Measured on `develop` at
the head of this plan, after issue 82 widened the reported surface:

| Package | `--api` | `--api --docstring` | rows |
| ------- | ------- | ------------------- | ---- |
| numpy | 67,516 B | 1,023,453 B | 496 |
| polars | 46,100 B | 382,765 B | 203 |
| pydantic | 23,300 B | 108,478 B | 151 |
| fastmcp | 2,601 B | 7,229 B | 6 |

Over MCP the numpy call does not merely arrive large - it is refused outright by the token-limit
guard, so the tool's own suggested next step reliably fails (issue 67).

This is not a numpy pathology. `polars` and `pydantic` are ordinary dependencies and both exceed
any usable context budget; the threshold is a couple of hundred public symbols. The conformance
tier records all three as `xfail(strict=True)`.

In scope: a caller-settable bound on `show --api` and `showPackageApiTool`, the promotion of the
bounded-results rule out of `find.md` into `output-contract.md`, the footer correction, and the
removal of the three conformance `xfail` marks the bound makes obsolete.

Out of scope: anything owned by issues 68, 49 or 50. Also out of scope: a byte-based bound - the
rule this project already has is row-based, and two bound kinds on one command is two things to
reason about.

## Implements

`specs/behaviors/output-contract.md`, **Bounded collections** - a new Details section, promoted
from `find.md`, declaring what a bound means for any collection command: the capped-count hint,
the definitive count below it, `0` honoured exactly, and a negative value rejected rather than
clamped.

`specs/commands/show.md` - `--limit` in the invocation table at a default of 20, the bound
applying in both modes, the footer naming a higher `--limit` rather than `--docstring` on a capped
result, and the negative-limit rejection in Failure modes.

`specs/mcp/tools.md` - `showPackageApiTool` gains `limit=20`; the negative-limit rejection under
Error message wording now names both tools that carry a bound.

`specs/commands/find.md` is in `authors:`, not `specs:`. `find` already conforms - it has carried
this behaviour since issue 73 - and this plan only rewrites the section to cite the promoted rule
instead of holding it. No `find` behaviour changes, so claiming conformance there would assert a
verification this plan does not perform.

## Approach

1. Open this plan at `status: planned`; stage 02 flips it to `in-progress`.
2. Extract the negative-limit rejection already in `find_symbol`
   (`src/venvaxi/_introspect.py`, the `if limit < 0` guard) into a shared helper, and call it from
   both `find_symbol` and `get_public_api`. One rejection site, not two.
3. Add a row bound to `get_public_api`. Its existing `limit` parameter is
   `DEFAULT_TRUNCATE_LIMIT` - a per-docstring *character* truncation length, not a row cap - so
   the new bound needs a distinct name on both surfaces. Do not overload it.
4. Thread `--limit` through the CLI (`src/venvaxi/_cli.py`) and `limit` through
   `show_package_api_tool` (`src/venvaxi/_mcp.py`), defaulting to 20 on both.
5. Emit the capped-count hint when the returned count equals the bound, spelled for the surface,
   and stop the footer suggesting `--docstring` as the way to see more symbols.
6. Remove the three `xfail(strict=True)` marks in `tests/test_conformance.py` and the
   `_UNBOUNDED_PAYLOAD_TODAY` set they read from.
7. Verify both surfaces, run the suite, coverage and hooks.

**Why 20, and why the same number as `find`.** One bound across both collection commands is one
number for a caller to remember, and the capped-count hint reads identically on each. It is also
the only value that discharges this unit's own gate: the conformance tier's `SANE_PAYLOAD_BYTES`
is 50,000, and numpy costs roughly 2,063 bytes per row with `--docstring`, so a bound of 20 lands
near 41 KB and a bound of 50 near 102 KB. At 50 the tier's payload test would keep failing, the
three `xfail` marks would stay pinned, and this unit would not satisfy the invariant it exists to
satisfy.

**Why the bound applies to the truncated view too.** A truncated row is cheap and a surface is
not: numpy's truncated table is 67 KB before a single complete docstring is asked for. Bounding
only `--docstring` would leave the command with an unbounded collection and force the promoted
rule to carve out an exception in the same breath as declaring itself general.

**This unit starts from a failing suite, by design.** The conformance tier pins numpy, polars and
pydantic as `xfail(strict=True)` against issue 67. The moment the bound lands, all three pass
unexpectedly and the suite goes red - that is the gate
[real-dependency-conformance](real-dependency-conformance.md) built, firing correctly. Removing
those marks is step 6 here, not a workaround.

## Validation

- [x] When `show <package> --api` is invoked with no `--limit`, the `show` command shall return no
  more than 20 symbol rows. —
  `tests/test_introspect.py::test_get_public_api_default_bound_caps_rows_at_twenty` and
  `tests/test_cli.py::test_add_subparser_show_defaults`; live venv,
  `uv run venvaxi show numpy --api` -> `count: 20` against 496 public symbols
- [x] When `show <package> --api` returns a count equal to the active `--limit`, the `show`
  command shall emit a hint naming a higher `--limit`. —
  `tests/test_cli.py::test_command_show_api_at_limit_appends_capped_hint`; live venv,
  `Results capped at --limit 20 - re-run with a higher --limit to see more`
- [x] When `show <package> --api` returns a count below the active `--limit`, the `show` command
  shall not emit the bounded-results hint. —
  `tests/test_cli.py::test_command_show_api_below_limit_omits_capped_hint` and
  `tests/test_introspect.py::test_get_public_api_below_bound_is_not_capped`; live venv,
  `show fastmcp --api` -> `count: 6` with no capped hint
- [x] When `show <package> --api` returns a count equal to the active `--limit`, the `show`
  command shall not suggest `--docstring` as the means of seeing further symbols. —
  `tests/test_cli.py::test_command_show_api_capped_omits_docstring_suggestion` and its counterpart
  `::test_command_show_api_below_limit_keeps_docstring_suggestion`; live venv, the capped `numpy`
  footer carries one hint and it is not the `--docstring` suggestion
- [x] When `show <package> --api --limit 0` is invoked, the `show` command shall emit `count: 0`
  and exit `EX_OK`. — `tests/test_cli.py::test_command_show_api_zero_limit_prints_empty_state` and
  `tests/test_introspect.py::test_get_public_api_zero_bound_returns_no_rows`; live venv,
  `show numpy --api --limit 0` -> `count: 0`, exit 0, carrying the bounded-results hint rather
  than the `tree` hint
- [x] If `show <package> --api --limit` is given a negative value, then the `show` command shall
  emit the TOON error block and exit `EX_FAILURE`. —
  `tests/test_cli.py::test_main_show_api_negative_limit_maps_to_exit_1`,
  `tests/test_mcp.py::test_show_package_api_tool_negative_limit_returns_error_block` and
  `tests/test_introspect.py::test_get_public_api_negative_bound_raises_before_resolution`; live
  venv, exit 1 on the CLI with the `venvaxi --help` footer and no footer over MCP
- [x] If a negative bound is rejected, then the message shall name neither the CLI flag nor the
  tool parameter, so it reads correctly on either surface. —
  `tests/test_introspect.py::test_get_public_api_negative_bound_message_suits_both_surfaces`,
  which asserts `Search` absent as well as `Result limit` present; live venv, both
  `show numpy --api --limit -5` and `find "a" --limit -5` report
  ``Result limit `-5` must not be negative``
- [x] When `showPackageApiTool` is called with no `limit`, the tool shall return no more than 20
  symbol rows and shall carry the capped-count hint spelled as a tool parameter. —
  `tests/test_mcp.py::test_show_package_api_tool_default_limit_bounds_rows`; in-process call,
  `count: 20` with `Results capped at limit=20 - re-call with a higher limit to see more`
- [x] When the conformance tier runs, the payload-bound assertion shall pass for every specimen
  with no `xfail` mark. — `uv run pytest -m conformance -k payload` -> `4 passed`, no xfail and no
  xpass; per specimen at the default bound, numpy 34,245 B, polars 16,475 B, pydantic 9,948 B and
  fastmcp 7,221 B, all under `SANE_PAYLOAD_BYTES = 50,000`

## Risks / unknowns

- **The default changes what every caller sees.** `show numpy --api` goes from 496 rows to 20.
  This is a deliberate behaviour change, not a regression: the count is capped, the hint says so,
  and a caller wanting the whole surface passes `--limit`. It will still surprise anyone who had
  learned the unbounded shape.
- **20 is generous for `find` and tight for an API listing.** A package's public API is a
  meaningful whole in a way a search result set is not, so a bound that hides 476 of numpy's 496
  symbols is a real cost. It is accepted for the consistency and for the tier gate above, and the
  hint makes the ceiling visible rather than silent.
- **The conformance tier's bound and this default are now coupled.** `SANE_PAYLOAD_BYTES` at
  50,000 and a default of 20 both hold today because numpy costs ~2,063 bytes per row. A future
  package with far larger docstrings could exceed the tier bound at 20 rows. Recorded rather than
  guarded; the tier is meant to fail when a real dependency does something new.
- **`get_public_api` carries two things called a limit.** The existing character-truncation
  `limit` and the new row bound. Naming them apart is the whole guard against a future reader
  wiring one to the other.

## Notes

**Stage 02 re-entered stage 01 twice**, per the re-entry rule in `ICM/process-plan/CONTEXT.md`.
Both were spec statements that were true before this unit and became too broad once a second kind
of hint existed on the same command.

1. **Footer suppression under `docstring`.** `specs/mcp/tools.md` said the three docstring-bearing
   tools "shall omit the `help[]` footer when `docstring` is set". Read literally, a capped
   `showPackageApiTool(numpy, docstring=true)` would return twenty of 496 symbols with no signal
   that it was capped - the confidently-wrong truncated answer this unit exists to prevent. The
   sentence now says what its own cited authority already said: the *hint* is suppressed, and the
   footer is omitted only where suppression leaves nothing. A hint naming a step the caller has
   not taken survives.
2. **`count: 0` from `--limit 0`.** `specs/commands/show.md` sent every empty API result to a hint
   naming `tree`. That is right for a package that exposes nothing at this level and wrong for a
   caller who asked for nothing: the two zeroes mean opposite things, and `tree` would read as a
   claim about the package. The empty-state hint is now conditioned on which zero it is.

Neither was caught by stage 01 because both only become wrong in the presence of a second hint
kind on the same command, which is what this unit introduced.

**Stage 03 sent it back a third time**, for two findings of its own.

**The promoted rule over-reached.** Its opening sentence read "A collection command shall bound
its row count", a universal obligation `list`, `tree` and `inherits` do not meet - verified
against `--help` on each. It would have declared three commands divergent the moment it landed,
which is precisely the manufactured divergence `find.md` held the rule back to avoid, and it
contradicted this section's own closing sentence four paragraphs later. The rule now governs
commands that *carry* a bound. Whether the other three should carry one is a separate question
with its own evidence.

**The shared message called the value a *search* limit.** True when `find` was the only bounded
command, false the moment `show --api` reached the same guard. `specs/mcp/tools.md` Error message
wording now says the obligation runs across commands and not only surfaces, and the message reads
`Result limit ... must not be negative` on both. No test pinned the old word, so none had to
change - but the neutrality test now asserts `Search` is *absent* as well as the new form present,
per the pytest conventions' rule that a one-way wording assertion passes on a substring.

That last change edits a frozen plan: `find-limit-lower-bound.md` quoted the old message in a
Validation citation. The claim and the test it cites are unchanged, so the citation was annotated
rather than rewritten - the record of what was verified then stays intact, and a future reader
re-running it is told why the string differs.

**`get_public_api` returns `PublicAPI`, not a list.** The bound has to travel with the rows, or
every call site recomputes `len(symbols) == max_rows` and the rule lives in as many places as
there are surfaces. A frozen dataclass with a `capped` property puts it in one. It also gives
`--limit 0` the right answer for free - `0 == 0` is capped - which is what lets the empty branch
choose between the two hints above without a second condition.

**The default lives in `get_public_api`, not only at the surfaces.** Placing it at the CLI and the
tool alone would let any future internal caller reintroduce an unbounded listing by omission. The
cost is that the conformance tier's `test_public_api_surface_not_narrowed_by_kind` now has to opt
out explicitly, since it compares against the walk's whole child set.

**The bound is lighter than estimated.** The plan projected ~41 KB for `show numpy --api
--docstring` from a 2,063 B/row average; the measured figure is 34,245 B, because the
alphabetically-first twenty numpy symbols are lighter than the mean. The estimate was load-bearing
for choosing 20 over 50, and it erred in the safe direction.

**Three re-entries, one pattern.** Every one was a spec statement that was true when written and
became too broad as the system grew a second case: footer suppression written when `--docstring`
was the only hint, the empty-state hint written when `count: 0` had one cause, the promoted bound
written when `find` was the only bounded command, and the rejection message written when `find`
was the only command that raised it. The implementation was never wrong in any of the four. Worth
remembering when promoting any rule: a sentence that generalises correctly today is not thereby
general, and the cheapest time to notice is while a second case is being added.

**No user-facing documentation needed changing at this stage.** `src/venvaxi/SKILL.md` was
corrected during implementation, because its flag tables would otherwise have stated a falsehood -
`show --api` without `--limit`, `showPackageApiTool` without `limit=20` - which
`specs/behaviors/skill-content.md` forbids. The installed copy was regenerated with
`just skill-sync` and `tests/test_skill_parity.py` enforces byte parity. `README.md`'s one-line
example (`venvaxi show rich --api - Public API symbols`) remains true: the answer is still public
API symbols, now bounded and saying so.

## Follow-ups

- **Whether `list`, `tree` and `inherits` should carry a row bound** - stage 03 found all three
  are unbounded collection commands, which is why the promoted rule was narrowed to govern what a
  bound means rather than mandate one. Each needs its own evidence: `list` is bounded in practice
  by a project's declared dependencies, `tree` has `--max-depth` as a different kind of ceiling,
  and `inherits` is bounded by a class's real subclass count. Owned by no issue.
- **The conformance bound and this default are coupled.** `SANE_PAYLOAD_BYTES` at 50,000 and a
  bound of 20 both hold because numpy averages ~2,063 bytes per row with `--docstring`. A future
  dependency with far larger docstrings could breach the tier bound at 20 rows. Not guarded - the
  tier is meant to fail when a real dependency does something new. Owned by no issue.
- **Issue [#68](https://github.com/andyrids/venv-axi/issues/68)** - the next unit. It amends the
  `specs/mcp/tools.md` divergence list that this unit also edited (Error message wording), and it
  carries a standing obligation from that file: whichever change adds a refresh parameter must
  bring `find_symbol`'s `--refresh`/`--package` message into conformance in the same move. That
  message is now the only one on the shared path still spelled for one surface.
- **`--limit` is silently ignored in metadata mode**, matching `--fields` under `--api`. Covered
  by `tests/test_cli.py::test_command_show_metadata_ignores_limit`. Deliberate and specified;
  recorded because silence is the kind of behaviour a later reader assumes was an oversight.
