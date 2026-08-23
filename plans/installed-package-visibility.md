---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/list.md
  - specs/behaviors/skill-content.md
  - specs/mcp/tools.md
authors: []
issues: [50]
pr: 91
---

# Plan: installed-package-visibility

## Scope

`venvaxi list` answers what a project **declares**, per
[`specs/commands/list.md`](../specs/commands/list.md)'s deliberate 'declared, not merely installed'
contract - and issue [#50](https://github.com/andyrids/venv-axi/issues/50) does not dispute that
contract. The gap it raises is different: `list` gives no signal that the venv's installed set is
larger, even though every installed distribution is fully queryable via `show <package>`. An agent
seeing a complete-looking `list` answer has no way to tell 'this project declares three packages'
from 'this project declares three packages and forty more are installed and queryable, unnamed'.

**Re-measured against this repo**, not the issue's `mpctraj` figures, and the reproduction is
sharper here because venv-axi declares zero runtime dependencies by principle
([`specs/principles.md`](../specs/principles.md), 'Zero runtime dependencies'):

```text
$ venvaxi list          -> count: 0
$ venvaxi list --all    -> count: 6   (coverage, fastmcp, numpy, pkgdx, polars, pytest)
$ python -c "from importlib import metadata; print(len(list(metadata.distributions())))"
100
```

`venvaxi show pydantic` and `venvaxi show fastmcp` both return full metadata at exit `0`, and
neither is declared by the bare `list`; `pydantic` is additionally absent from `list --all`'s
six-package answer. `rich` is not used as the reproduction here - the issue's second comment notes
`mpctraj` now declares `rich` directly, which stopped that repro for a reason unrelated to
venv-axi. 100 distributions were counted with `importlib.metadata.distributions()`, checked for
duplicate names (none found), and every one resolves through `venvaxi show <name>` because that is
the identical metadata lookup `resolve_package` performs. The issue's own second comment ran the
same check by hand against `mpctraj` - 103 `*.dist-info` directories, 95 absent from `list --all`,
95/95 resolving through `show` - so this repo's 100/0/6 is a smaller instance of the same shape,
not a different one.

**Decision: option 1 from the issue** - a footer aggregate, `installed: <m>`, alongside the
existing `count: <n>` (which continues to mean 'declared'). It costs one line, changes nothing
about what `count:` or the `packages` table report, and turns a silent omission into a stated
boundary. Rejected, with the issue's own reasoning: **option 2** (`--installed`, or a third `--all`
tier) puts two different questions on one command - what the project declares, and what the venv
holds - and the second is already answerable per-package via `show`, without a listing. **Option
4** (flagging undeclared-but-imported packages against actual source imports) is a packaging
linter, out of scope for an AXI. **Option 3** (skill-only) leaves the misleading impression in the
tool's own output unchanged - the skill is not loaded on every `list` call, so a caller who never
reaches for it never sees the caveat.

**What 'installed' counts, decided deliberately.** `installed` is every distribution
`importlib.metadata.distributions()` reports in the active venv, deduplicated by name, with no
filtering by role - venv-axi's own distribution, `pytest`, build tooling, all of it counts. There
is no principled cut between a 'meaningfully queryable' distribution and any other: every one
resolves through the identical `metadata.distribution(name)` lookup `show <package>` performs, so
excluding any category would be excluding names `show` can still answer about. `pip` happens not
to be installed in this venv (checked: `'pip' not in` the distribution names), which is itself
evidence the count needs no special-casing - whatever the import system reports is the honest
answer.

**The footer appears on the empty result too - the sharpest case, and the one the empty-state
hints do not reach.** `venvaxi list`'s own `count: 0` today gives no further signal; a caller reads
it as 'this venv has nothing'. The existing `--all`-conditional empty-state hints
([`specs/commands/list.md`](../specs/commands/list.md#outputs)) stay exactly as specified - they
are load-bearing and this plan does not touch their logic - but `installed` is not one of those
hints. It is a second pre-computed aggregate, independent of the `--all`-conditional branch,
appended after `count: 0` (or after the `packages` table) and before `help[]` on every path where
it is not suppressed.

**The footer is suppressed when declared equals installed.** `6 declared, 6 installed` states no
gap and is noise - the same reasoning
[Contextual disclosure](../specs/behaviors/output-contract.md#contextual-disclosure) already
applies to a `help[]` hint naming a step the caller does not need.

**`listPackagesTool` needs no separate spec edit.**
[`specs/mcp/tools.md`](../specs/mcp/tools.md) states its own default: eight tools, `listPackagesTool`
among them, mirror a CLI command already specified in `specs/commands/`, and only genuine
divergences are enumerated in that file's `## Divergences from the CLI`. `installed` carries no
command or tool reference of any kind - it is a bare number - so there is no CLI-vs-MCP wording to
diverge on, and `include_dev` already scopes the declared count identically on both surfaces. This
was considered and rejected as a `specs/mcp/tools.md` edit, not overlooked: adding a
non-divergence entry there would assert a false claim needs correcting where none currently exists,
which is spec bloat the file's own philosophy (`ICM/_config/reference-standard-spec.md`, 'Out of
scope') argues against. `listPackagesTool`'s code is still in scope for this plan - it inherits
`specs/commands/list.md`'s new Outputs clause exactly as `command_list` does, by the same default
that already governs its eight siblings.

**No edit to `specs/behaviors/output-contract.md`.** Considered and rejected: the 'second
pre-computed aggregate' shape used here is new to this one spec, and
[`ICM/_config/reference-standard-spec.md`](../ICM/_config/reference-standard-spec.md)'s promotion
trigger for lifting a pattern into a shared behavior spec is a *second* spec needing the same
shape, not the first. `list.md` states and justifies the shape locally, citing
[Aggregates](../specs/behaviors/output-contract.md#aggregates) as precedent rather than amending
it. If a future command needs the same second-aggregate pattern, that is the promotion trigger, not
this plan.

Out of scope, stated so the boundary is not assumed: enumerating the installed-but-undeclared set
by name, on either surface - `installed` is a count, never a listing, which keeps the 'declared,
not merely installed' contract intact and is exactly what option 2 was rejected for; a diagnostic
comparing installed packages against a project's actual source imports (option 4's packaging
linter, explicitly out of scope for an AXI); any change to `count: <n>`'s existing meaning, which
stays 'the declared, resolved answer' unchanged; a `--fields`-selectable `installed` value - it is
not a `PackageInfo` field and carries no per-package detail to select.

## Implements

`specs/commands/list.md` - a new `### Installed-package visibility` subsection under `## Outputs`:
the `installed: <m>` aggregate's emission (populated and `count: 0` branches), its suppression when
declared equals installed, and its independence from the existing `--all`-conditional empty-state
hints. `## Data requirements` gains a paragraph naming the source (`importlib.metadata.distributions()`,
the same resolution [Package resolution](../specs/behaviors/package-resolution.md) uses) and the
no-filtering-by-role decision. `## Out of scope` gains two entries - naming the installed-but-
undeclared set, and flagging undeclared-but-imported packages - plus a clarifying sentence on the
unchanged Transitive dependencies entry. `## Principles` gains
[principle 4, pre-computed aggregates](../specs/principles.md#principle-4-pre-computed-aggregates)
and [principle 5, definitive empty states](../specs/principles.md#principle-5-definitive-empty-states).

`specs/behaviors/skill-content.md` is in `specs:` and is **not** amended - its existing rule (the
skill shall carry an entry for each observed failure mode that costs an agent a wasted query or a
wrong conclusion) is what obliges `src/venvaxi/SKILL.md` to change once `list`'s contract grows: the
CLI command table's `venvaxi list` row currently reads 'Declared, installed venv packages', which
undersells the new footer, and issue #50's own failure mode - an agent concluding an installed
package 'isn't available' because `list` omitted it - is exactly the class of entry that spec
obliges the skill to name a correct move for.

`specs/mcp/tools.md` is in `specs:` and is **not** amended - no text changes. Its existing parity
rule ('Behavioural parity with the CLI is the default... a new CLI capability MUST either gain an
MCP tool or gain an entry in Divergences explaining why not') now covers an aggregate that did not
exist when it was written, so `listPackagesTool`'s implementation gains the `installed` aggregate to
stay in conformance with that rule - the identical shape
[cache-state-report](cache-state-report.md) used for `specs/commands/home.md`: 'Listed in `specs:`
because code (not spec text) is what has to move.' A `## Divergences from the CLI` entry was
considered and rejected: that section names exceptions to parity, and this is parity being met, not
diverged from - an entry there would assert a divergence that does not exist.

## Approach

1. Open this plan at `status: planned`; stage 02 flips it to `in-progress`.
2. Add an `installed_count()` (or equivalently named) helper to `src/venvaxi/_packages.py`,
   alongside `list_packages`, returning the number of distinct distribution names
   `importlib.metadata.distributions()` reports in the active venv. No new dataclass or module -
   one function, reused by both surfaces.
3. Wire it into `command_list` in `src/venvaxi/_cli.py`: after emitting `count:`/the `packages`
   table (or `count: 0`), compute the installed count, compare it against the declared count just
   emitted, and emit `installed: <m>` only when the two differ, before the existing `help[]` call.
   No change to the `--all`-conditional hint-selection logic already in place.
4. Wire the identical shape into `list_packages_tool` in `src/venvaxi/_mcp.py`, following the same
   comparison and suppression, matching `command_list` field for field.
5. Update `src/venvaxi/SKILL.md` and regenerate the installed copy: the CLI command table's
   `venvaxi list` row description, and a new gotcha naming the `installed` aggregate as the way to
   tell whether more packages are queryable than `list` declares - the direct answer to the failure
   mode issue #50 raised (an agent concluding an installed-but-undeclared package is unavailable).
6. Verify both surfaces, run the suite, coverage and hooks.
7. Record for stage 04: this is the final 0.4.0 unit. `CHANGELOG.md`'s `## [Unreleased]` heading
   flips to a dated `## [0.4.0]` once, at release, by the maintainer - not by stage 04 of this
   plan. No Approach or Validation item here does that flip.

**No `SCHEMA_VERSION` bump.** This unit adds no new walk-time recording and touches no cached
symbol graph; `installed_count()` reads distribution metadata directly, the same source `show`
already reads, never the symbol cache.

## Validation

- [x] When `list` returns one or more packages and the declared count differs from the venv's
  installed-distribution count, the `list` command shall append an `installed: <m>` line after the
  `packages` table and before the `help[]` footer. — `tests/test_cli.py::test_command_list_installed_appears_when_declared_differs`
  (asserts `out.index("installed: 100") < out.index("help[")`); live, `uv run venvaxi list --all` ->
  `installed: 100` after the `packages[6|]` table and before `help[1]:`
- [x] When `list` returns `count: 0` and the active venv holds at least one importable
  distribution, the `list` command shall append an `installed: <m>` line between `count: 0` and the
  `help[]` footer. — `tests/test_cli.py::test_command_list_empty_installed_appears_between_count_and_help`
  (asserts strict ordering `count: 0` < `installed: 100` < `help[`); live, `uv run venvaxi list` ->
  `count: 0` / `installed: 100` / `help[1]:`
- [x] If the declared count equals the installed count, then the `list` command shall omit the
  `installed:` line. — this repo cannot exercise this naturally (0 declared / 100 installed at bare
  `list`, 6 / 100 at `--all`), so stage 03 drove it directly by patching `list_packages` and
  `installed_count` on `venvaxi._cli` to force equality, for both the populated
  (`declared==installed==1`) and empty (`declared==installed==0`) branches, confirming `installed:`
  genuinely absent in both, not merely unequal to something else; test coverage:
  `tests/test_cli.py::test_command_list_installed_suppressed_when_equal`,
  `::test_command_list_empty_installed_suppressed_when_zero` (both assert `"installed:" not in out`)
- [x] The `installed: <m>` value shall equal the number of distinct distribution names
  `importlib.metadata.distributions()` reports in the active venv, unaffected by `--all` or
  `--fields`. — independently re-measured in this venv: 100 raw entries, 100 distinct
  case-sensitive, 100 distinct lower-cased; live, `venvaxi list` / `venvaxi list --all` / `venvaxi
  list --all --fields name` all report `installed: 100` unchanged; unit coverage:
  `tests/test_packages.py::test_installed_count_counts_distinct_names`,
  `::test_installed_count_dedups_by_name`, `::test_installed_count_empty_venv`
- [x] When `listPackagesTool` returns one or more packages and the declared count differs from the
  installed count, the tool shall append an `installed: <m>` line after the `packages` table and
  before the `help[]` footer, matching `venvaxi list` field for field. — in-process
  `list_packages_tool(include_dev=True)` field-for-field identical to `venvaxi list --all` (same six
  rows, same `installed: 100`, same relative position); unit coverage:
  `tests/test_mcp.py::test_list_packages_tool_installed_appears_when_declared_differs`
- [x] When `listPackagesTool` returns `count: 0` and the active venv holds at least one importable
  distribution, the tool shall append an `installed: <m>` line between `count: 0` and the `help[]`
  footer. — in-process `list_packages_tool(include_dev=False)` -> `count: 0` / `installed: 100` /
  `help[1]:`; unit coverage: `tests/test_mcp.py::test_list_packages_tool_empty_installed_between_count_and_help`
- [x] If the declared count equals the installed count, then `listPackagesTool` shall omit the
  `installed:` line. — suppression could not occur naturally in this repo either, so stage 03 drove
  it directly by patching `list_packages` and `installed_count` on `venvaxi._mcp`, both branches
  (`declared==installed==1` and `declared==installed==0`), confirming `installed:` absent in both;
  test coverage: `tests/test_mcp.py::test_list_packages_tool_installed_suppressed_when_equal`,
  `::test_list_packages_tool_empty_installed_suppressed_when_zero` (both assert `"installed:" not
  in result`)
- [x] When the packaged skill tables `venvaxi list`, the description shall name the `installed`
  aggregate. — review citation, not a test identifier: `src/venvaxi/SKILL.md:111`, the `venvaxi
  list` row of the CLI command table, description cell reads "Declared; `installed:` names the gap"
- [x] When the packaged skill names a gotcha for `list`, it shall name the `installed` aggregate as
  the way to tell whether an installed-but-undeclared package is queryable, addressing the
  wrong-conclusion failure mode issue #50 raised. — review citation, not a test identifier:
  `src/venvaxi/SKILL.md:219-224`, the Gotchas bullet naming `installed:`, not `count:`, as the way
  to tell whether more is queryable before concluding a package "isn't available", addressing
  issue #50's exact failure mode

## Risks / unknowns

- **The suppression rule (`installed` omitted when declared equals installed) has no precedent
  elsewhere in the codebase to compare against.** Every other suppression in
  `specs/behaviors/output-contract.md` (`--docstring`-style hint suppression) governs a `help[]`
  hint conditioned on a flag the caller already set; this suppression is conditioned on two derived
  counts being numerically equal, which is a different kind of trigger stage 02 has not implemented
  before. Worth a close look at whether the comparison is cheap enough to run unconditionally (it
  is: `installed_count()` is one `importlib.metadata.distributions()` pass, already paid for by
  `show`'s own resolution path) rather than only when `count` looks suspiciously small.
- **Deduplication by distribution name is asserted, not yet proven against every possible venv
  layout.** This repo's own venv shows zero duplicate names among 100 distributions, which is
  evidence for the common case, not a guarantee that `importlib.metadata.distributions()` never
  yields two entries for one name (e.g. a distribution installed in two `sys.path` locations
  simultaneously). Stage 02 should decide and test the dedup key explicitly rather than assume the
  measured venv generalizes.
- **`installed` is silent about *why* the gap exists.** It cannot distinguish 'these are all
  transitive dependencies of declared packages' from 'these are unrelated packages installed for
  something else entirely' - both produce the same number. That ambiguity is accepted, not solved:
  resolving it is exactly option 4's packaging-linter territory, ruled out in Scope.

## Notes

**Why a footer count and not `--installed`.** Option 2 from the issue - a `--installed` flag, or a
third `--all` tier - was rejected because it puts two different questions on one command: what the
project declares, and what the venv holds. The second question is already answerable per-package
via `show <package>`, without a listing, so a new flag would duplicate an answer `show` already
gives rather than close a real gap. Option 4 (flagging undeclared-but-imported packages against a
project's actual source imports) was rejected as a packaging linter - out of scope for an AXI
altogether, not merely a larger version of this unit. The contract `specs/commands/list.md` already
states - `list` answers what a project **declares** - was never in dispute; this unit adds a count
beside it, not a rival meaning for `count:`.

**Why it appears on the empty branch.** `venvaxi list`'s own `count: 0` gave no further signal
before this unit - a caller reads it as "this venv has nothing." That is the sharpest case and the
reason the unit exists: in this repo, the bare `venvaxi list` reports `count: 0` against 100
installed distributions, a definitive-looking empty answer sitting on a fully queryable venv. The
existing `--all`-conditional empty-state hints stay untouched and load-bearing; `installed` is a
second, independent aggregate that reaches the empty branch precisely because that branch is where
the omission is most misleading.

**Why it is suppressed when declared equals installed.** `6 declared, 6 installed` states no gap
and is noise - the same reasoning `specs/behaviors/output-contract.md`'s Contextual disclosure
already applies to a `help[]` hint naming a step the caller does not need. The suppression could not
be exercised naturally against this repo's own venv (0 declared / 100 installed at bare `list`, 6 /
100 at `--all`), so stage 03 drove both branches directly by patching `list_packages` and
`installed_count` on `venvaxi._cli` and `venvaxi._mcp` to force equality, confirming `installed:`
genuinely absent rather than merely unequal to something else.

**Why a second aggregate rather than a `help[]` hint, and why it was not promoted into
`output-contract.md`.** `installed` names no runnable next step - there is no command that turns
"more is installed" into a narrower answer, because `show <package>` already answers per-package
without needing to be told a name first. A `help[]` hint exists to suggest a next command; `installed`
is a fact about current state, which is what the existing `## Aggregates` pattern in
`output-contract.md` already covers for `count:` itself. The second-aggregate shape is justified
locally in `list.md`'s own new subsection, citing `output-contract.md#aggregates` as precedent
rather than amending it - the promotion trigger in `ICM/_config/reference-standard-spec.md` is a
*second* spec needing the same shape, not the first, and no second spec needs it yet.

**Why `specs/mcp/tools.md` is in `specs:` with no text change.** Its existing parity rule -
"Behavioural parity with the CLI is the default... a new CLI capability MUST either gain an MCP tool
or gain an entry in Divergences explaining why not" - already obliged `listPackagesTool` to gain the
`installed` aggregate the moment `list`'s contract grew; code has to move, spec text does not. This
follows the identical shape [cache-state-report](cache-state-report.md) used for
`specs/commands/home.md`: listed in `specs:` because code, not spec text, is what has to move. A
`## Divergences from the CLI` entry was considered and rejected - that section names exceptions to
parity, and `installed` carries no CLI-vs-MCP wording to diverge on, so an entry there would assert
a divergence that does not exist. Stage 03 verified the obligation is actually met, not merely
assumed: `listPackagesTool` mirrors `command_list` field for field on both the populated and
suppressed branches, confirmed by direct output comparison, and no `installed`-related entry exists
anywhere in `## Divergences from the CLI` on re-read.

**The dedup key.** `installed_count()` deduplicates by a bare lower-cased distribution name, matching
`_requirement_name`'s existing normalization, rather than full PEP 503 normalisation (which
additionally collapses runs of `-`, `_` and `.`). This is adequate in practice, not a shortcut: a
Python packaging installer will not let two distributions differing only by separator coexist in one
venv, since PEP 503 normalisation is exactly what makes such names collide at the installer level -
so the narrower key cannot under-count in the cases that can actually occur. The duplicate path is
proven against a mock (`tests/test_packages.py::test_installed_count_dedups_by_name`, two synthetic
entries `"Rich"`/`"rich"`), not against a live duplicate, because this venv holds none: 100 raw
entries, 100 distinct case-sensitive, 100 distinct lower-cased, independently re-measured by both
stage 02 and stage 03.

**Stage 02's one latitude note.** The techspec's directive read "after the existing `count:`/table
emission ..., compute the installed count"; both implementations instead compute `declared` and
`installed` once, ahead of the branch, and reuse the values in whichever branch executes. This is one
`installed_count()` call per command invocation either way - never memoized across the branch - so
the `installed: <m>` value and its position in the output are identical to a literal reading of the
directive; the reordering only avoids duplicating the `installed_count()` call site across the CLI's
two `_emit` sites and the MCP tool's two `output =` sites. Stage 03 confirmed this by reading the
source directly (`src/venvaxi/_cli.py:132-176`, `src/venvaxi/_mcp.py:237-274`) rather than assuming
it from stage 02's own description.

## Follow-ups

- **None.** `installed` cannot say *why* a gap exists - declared-transitive dependencies and
  genuinely unrelated installs both produce the same number. Accepted, not solved: the only way to
  answer *why* is a diagnostic against a project's actual source imports, which is exactly option
  4's packaging-linter territory, rejected in Scope as categorically out of scope for an AXI. This
  is a permanent design boundary rather than work awaiting an owner, so no issue is filed.
- **None.** The dedup duplicate path - `installed_count()`'s behaviour against a venv that genuinely
  holds two entries for one distribution name - remains proven only against a mock
  (`tests/test_packages.py::test_installed_count_dedups_by_name`), not against a live
  duplicate-yielding venv; this repo has none to exercise it against (100 raw / 100 distinct
  case-sensitive / 100 distinct lower-cased, re-measured by both stage 02 and stage 03). This
  mirrors [cache-state-report](cache-state-report.md)'s own unfiled "a crash-corrupted WAL was not
  reproduced" and [mcp-cache-refresh](mcp-cache-refresh.md)'s "the reproduction has not been re-run
  on `mpctraj`" follow-ups - an acknowledged gap in what could be observed live, not a defect. No
  issue is filed.
- **None.** Whether the second-aggregate shape (`installed:` beside `count:`) should later be
  promoted into `specs/behaviors/output-contract.md`'s `## Aggregates` section is not decided here -
  the promotion trigger (`ICM/_config/reference-standard-spec.md`) is a *second* spec needing the
  same shape, not the first, and no second spec needs it yet. Nothing to track until that trigger
  fires; whoever authors that future spec change owns the decision then.
- **None of the above is deferred.** This is the final unit of 0.4.0 - no open sibling plan exists
  to absorb a `Deferred to` entry, matching the precedent both
  [cache-state-report](cache-state-report.md) and [mcp-cache-refresh](mcp-cache-refresh.md) set when
  closing with no downstream plan yet open.
