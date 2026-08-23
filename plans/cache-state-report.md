---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/commands/cache.md
  - specs/commands/home.md
  - specs/mcp/tools.md
  - specs/behaviors/skill-content.md
authors:
  - specs/behaviors/cache-refresh.md
issues: [49]
pr: 90
---

# Plan: cache-state-report

## Scope

Nothing on either surface reports what a project's cache currently holds. `venvaxi show <pkg>`
reports the *installed* version; nothing reports the *built* version, the built depth, or whether a
package is indexed at all. The only way to detect that a cache changed was diffing printed symbol
lists by eye - and, reported live against this issue, diffing a cache file's mtime from outside the
tool surface entirely, because venv-axi itself gave no in-band signal.

The sharpest cost of the gap is a hint that names a cause the caller cannot check.
[`specs/commands/inherits.md`](../specs/commands/inherits.md) requires the empty-state hint to name
'subclasses below the built depth' as a possible cause of a zero result - but nothing on either
surface reports what the built depth *is*, so the hint names a fact the caller has no way to verify.
This unit makes it checkable.

In scope: a new read-only CLI command, `venvaxi cache`, reporting this project's cache schema
version, database path and size, and a table of every package with a recorded build - its built
version, built depth and current symbol count. On MCP, the same information extends
`describeBindingTool` rather than adding an eleventh tool -
[`specs/mcp/tools.md`](../specs/mcp/tools.md) Out of scope already commits to this shape: 'the
binding report is the natural home for a cache summary, and a future spec adding one extends this
contract rather than replacing it.' Both surfaces read the cache directly, without opening it
through the path that would rebuild a schema-mismatched cache as a side effect of merely being
asked about it - the central design constraint this unit turns up, discussed under Approach.

**The build-timestamp question is settled here, not deferred.** Option 1 in the issue body reads as
though 'what is indexed, at what version, at what depth' is a single additive query away. Two of
the three are. Verified against the shipped `src/venvaxi/schema.sql`: no table in it - not
`package_builds`, not `nodes`, not `edges` - carries any temporal column at all. Package, built
version, built depth, schema version, db path and db size are all answerable from state already
recorded; 'when was this built' is not, because there is nothing recording it. Adding that would be
a schema change and a `SCHEMA_VERSION` bump, and the honest answer for every row written before the
bump would be `null`, never a backfilled guess - a real migration, not an additive read. The db
file's mtime is not a substitute: it moves on any package's rebuild, so it cannot answer the
question at the granularity the issue asks for, per package. **Decision: the build timestamp is out
of scope for this unit.** The additive read closes the diagnostic gap the issue raised; a timestamp
is a separate, larger unit, recorded as such in
[`specs/commands/cache.md`](../specs/commands/cache.md) Out of scope. No `SCHEMA_VERSION` bump
follows from this plan - nothing about what a walk records changes.

**Two obligations are inherited from [mcp-cache-refresh](mcp-cache-refresh.md) and are respected,
not re-litigated, here.** First, the boundary: `refreshPackageGraphTool`'s `depth` and `symbols`
fields are facts about a walk it just performed, not about the graph as the caller found it before
asking, and this unit's spec text does not read that receipt as precedent for answering 'what does
the graph currently hold' by mutating - the cache summary is read-only on both surfaces, full stop.
Second, `version` was deliberately left off that tool's receipt because built version paired with
built depth is the staleness summary this unit owns; it is reported here, per package.

**Re-measured cache figures**, since issue #49's second comment records 190.97 MiB across five
caches (measured 2026-08-22) and that figure is now stale: this machine currently holds two caches
under `~/.venvaxi/` totalling 38,244,352 bytes (36.5 MiB) - `5aea176019257588.db` at 38,191,104
bytes (36.4 MiB, this project's own cache)
and `e3f7111e6ce43cdf.db` at 53,248 bytes (0.1 MiB, a scratch testbed from mcp-cache-refresh
verification, not a real project cache). `grep -rE 'evict|TTL|max_size|LRU|expire|prune' src`
returns zero matches, confirmed. The bigger figures in the issue's second comment - 102.4 MiB for a
three-dependency project, 190.97 MiB across five caches - stand as the evidence that growth is
unbounded, even though this machine's own caches are currently smaller; both facts are recorded in
[`specs/behaviors/cache-refresh.md`](../specs/behaviors/cache-refresh.md) Out of scope, corrected
there from its previous 'the databases are small' claim.

Out of scope, stated so the boundary is not assumed: a build timestamp (above); cache eviction -
this unit makes growth *observable* in both directions the issue names (per dead project root, per
uninstalled package within one cache), not *bounded*, and an eviction policy is a separate unit; a
`--refresh` flag on `cache` - this is the one command guaranteed never to touch the cache it reports
on; a per-package installed-version comparison - the editable-install case this unit exists to make
checkable is exactly the case where built and installed version never differ, so the comparison
would read as reassurance where it can detect nothing; a row bound on the new collection - decided
unbounded, like `list`, reasoned under Approach.

## Implements

`specs/commands/cache.md` (new) - the full contract for `venvaxi cache`: no arguments, no
`--refresh`; a flat object of `schema_version`, `db_path`, `db_size_bytes`; `count: <n>` and a
`builds` table of `package`, `version`, `depth`, `symbols`; the two distinguishable empty states
(no cache built yet vs. a cache built holding nothing); the two failure modes
(`ProjectRootNotFoundError`, `StoreError`); the unbounded-collection decision and its reasoning; and
a Local principle - observability must not cost the observer a mutation - that is the spec-level
statement of this unit's central constraint.

`specs/commands/home.md` - no text changes; the bare invocation's existing 'every available command'
footer rule now covers a command that did not exist when the current footer list was written, so the
implementation gains one more line to stay in conformance. Listed in `specs:` because code (not
spec text) is what has to move.

`specs/mcp/tools.md` - `describeBindingTool` gains a new `### Cache summary` section under `## The
binding report`, extending its object with the same fields `cache.md` declares, field for field,
plus the unbounded-collection statement and the conditional third hint naming
`refreshPackageGraphTool`. `### Failure modes` gains the root-degrade-omits-cache-summary rule and
a second, independent degrade - an unreadable cache reports `root`/`venv`/`status` normally,
`schema_version: (cache unreadable)`, `db_path`/`db_size_bytes` still, no `count`/`builds`, and a
delete-safe hint - the first failure surface this tool has ever had beyond the root-resolution
degrade, and a degrade rather than a raise per the maintainer's decision at the review gate. The
'degrade is scoped to that trigger alone' sentence is rewritten to cover two triggers without
widening either. `### The description is part of the contract` gains the requirement that
the registered description states the cache summary. `## Divergences from the CLI` notes that the
cache half of this tool now has a genuine CLI equivalent, where the binding half still has none.
`## Out of scope` rewrites the `Cache state` entry: the 'where it lands' question this issue raised
is answered and no longer future work, while the wider question - a staleness signal folded into
every *other* tool's read answer - and the `refreshPackageGraphTool`-is-not-a-cache-summary boundary
both remain explicitly out of scope, preserved from the inherited text rather than re-derived.

`specs/behaviors/skill-content.md` is in `specs:` and is **not** amended - its existing rule ('the
packaged skill shall restate no claim `specs/**` does not declare') is what obliges
`src/venvaxi/SKILL.md` to change once a new command exists and `describeBindingTool`'s contract
grows, exactly as it did for `mcp-cache-refresh`.

`specs/behaviors/cache-refresh.md` is in `authors:`, not `specs:`. Two edits: `## Applies to` gains
a sentence naming `cache` and the MCP cache summary as the paths that read the store directly
without invoking the rebuild-on-open path; `## Out of scope` corrects the `Cache eviction` entry's
'the databases are small' claim against the re-measured figures above, and narrows `A staleness
signal carried by a read answer` now that the binding-report half of that question is answered. No
new `shall` obligation is asserted by either edit beyond what `cache.md` and `tools.md` already
state - both are cross-references, which is why conformance is verified against those two files, not
this one, mirroring the precedent set in `mcp-cache-refresh`.

## Approach

1. Open this plan at `status: planned`; stage 02 flips it to `in-progress`.
2. Add a single read-only cache-state reader, shared by both surfaces, analogous to how
   `resolve_binding()` already serves `describeBindingTool` alone from `_core.py`. It opens a raw
   SQLite connection **directly** on the project's cache database path - never through
   `SymbolStore.__init__`, which drops and rebuilds a schema-mismatched cache's tables as a side
   effect of merely connecting (`_store.py::_ensure_schema`). This is the central finding of this
   unit's design: every existing cached command answers *current* state by keeping the cache
   current as a byproduct of opening it, and this is the first command whose entire job is to
   answer *as-found* state, which the existing open path cannot do without falsifying the very
   thing being asked about.
   - If the database file does not exist, report the not-built empty state without opening SQLite
     at all - opening a nonexistent path in read-only mode raises, and the distinction is exactly
     the one the spec requires.
   - If it exists, read the recorded schema version, the full set of recorded builds (package,
     version, max depth), a symbol count per package, and the file's size, on one read-only
     connection that is opened and closed without ever executing the schema-ensure script.
   - A `sqlite3` failure on this path raises `StoreError`, following the existing rebuild-time
     precedent (`_cache.py`, `store.rollback()`'s sibling arm).
3. Wire `venvaxi cache` into `_cli.py`: a subparser with no arguments, a `command_cache` handler
   emitting the object, the `count:`/`builds` table, and the two footers (populated vs. empty),
   following `command_list`'s shape for the object-then-table-then-footer sequence.
4. Add the matching line to `command_home`'s hand-written footer list -
   `` "Run `venvaxi cache` for this project's cache state" `` alongside the other eight - since
   `specs/commands/home.md`'s existing 'every available command' rule now covers a ninth entry.
5. Extend `describe_binding_tool` in `_mcp.py` to call the same reader when `root` resolves, inside
   a `try`/`except StoreError`. On success, append the cache fields to the existing object, the
   `count:`/`builds` table, and the conditional third hint. On `StoreError`, catch it locally -
   never let it reach the tool's generic error path - and emit the degraded shape instead:
   `schema_version: (cache unreadable)`, `db_path`/`db_size_bytes` still reported (recomputed
   directly, since they are plain filesystem facts the reader's exception carries no payload for),
   no `count`, no `builds`, and a hint naming `db_path` as safe to delete. No change to the no-root
   degrade branch beyond leaving the cache fields out of it entirely.
6. Update `src/venvaxi/SKILL.md` and regenerate the installed copy: the CLI command table gains a
   `venvaxi cache` row; the MCP tool table's `describeBindingTool` row and its surrounding prose
   reflect the wider contract; and the entry that already tells an agent to call
   `describeBindingTool` first for a suspected wrong binding is extended to say it is also the way
   to check a suspected-stale graph without paying for a rebuild - the failure mode this whole issue
   was raised against.
7. Verify both surfaces, run the suite, coverage and hooks.
8. Record for stage 04: `README.md`'s quick-examples list (lines 39-43) is a curated subset that
   already omits `find`, `serve` and `setup`, so it is not an exhaustive enumeration `cache` falsifies
   by omission the way `SKILL.md`'s tables would. No spec governs README content, so this carries no
   Validation criterion and is documentation work, not implementation - written down so stage 04
   does not have to rediscover it.

**Unbounded, deliberately, matching `list` rather than `find`/`show --api`.** A cache row exists only
for a package some query has actually touched, which is a strict subset of a project's declared
dependencies - tighter than `list`'s own reasoning for staying unbounded (declared dependencies,
whether queried or not), which
[api-collection-bound](api-collection-bound.md)'s Follow-ups already accepted without a bound. A row
cap would add a `--limit`/`limit=` surface to a command whose entire purpose is showing the caller
everything the cache currently holds; capping that answer would undercut the reason the command
exists. `specs/behaviors/output-contract.md#bounded-collections` is deliberately not edited to
enumerate this decision - its list is illustrative of the neutral rule, not a closed inventory, and
`list`, `tree` and `inherits` already reached the same unbounded conclusion without being named
there.

**Two failure modes, not five.** `show`, `find`, `tree`, `inspect` and `inherits` each carry the
full three-class package-resolution surface because each takes a package argument this command does
not. `cache` takes none, imports nothing, and validates nothing beyond resolving the project root -
its failure surface is a strict subset by construction, which is itself worth stating plainly rather
than leaving as an unremarked absence.

**No `SCHEMA_VERSION` bump.** The bump trigger is a change to the *content* a walk records; this
unit adds a read over already-recorded state and changes nothing `_walk_module` writes.

## Validation

- [x] When `venvaxi cache` is invoked against a project whose cache holds at least one recorded
  build, the `cache` command shall emit a flat object of `schema_version`, `db_path` and
  `db_size_bytes`, then `count: <n>` and a `builds` table of `package`, `version`, `depth`,
  `symbols`, ordered by `package`. — `tests/test_cli.py::test_command_cache_with_builds`,
  `tests/test_cache.py::test_read_cache_state_reports_builds_and_symbol_counts`,
  `tests/test_cache.py::test_read_cache_state_orders_builds_by_package`; live, `uv run venvaxi
  cache` against this project's real cache
- [x] When this project has never had a cache database created for it, the `cache` command shall
  report `schema_version: (not built)`, `db_size_bytes: 0`, `count: 0`, and `db_path` naming where
  the database would be created. —
  `tests/test_cache.py::test_read_cache_state_not_built_without_opening_sqlite`,
  `tests/test_cli.py::test_command_cache_not_built`; live probe against a throwaway project with
  no cache db present
- [x] When a cache database exists but records zero package builds, the `cache` command shall
  report the real recorded `schema_version` and `count: 0`, distinguishable from the not-built
  state above by that field alone. —
  `tests/test_cache.py::test_read_cache_state_built_but_empty_reports_real_schema_version`,
  `tests/test_cli.py::test_command_cache_built_but_empty`; live probe against an empty `SymbolStore`
- [x] When `venvaxi cache` returns `count: 0`, the command shall end output with a hint naming
  `venvaxi show <package> --api`. —
  `tests/test_cli.py::test_command_cache_empty_hint_names_show_api`; live, both empty-state probes
- [x] When `venvaxi cache` returns a nonzero `count`, the command shall end output with a hint
  naming `venvaxi show <package> --api --refresh`. —
  `tests/test_cli.py::test_command_cache_with_builds_hint_names_refresh`; live, the populated-cache
  run
- [x] When `venvaxi cache` is run against a cache database whose recorded schema version differs
  from venvaxi's current schema version, the command shall report the stale recorded version
  unchanged. — `tests/test_cache.py::test_read_cache_state_stale_schema_reported_unchanged`; live
  probe forcing `PRAGMA user_version = 999`; `command_cache`/`describe_binding_tool` confirmed
  thin pass-throughs by reading `_cli.py` lines 522-527 and `_mcp.py` lines 209-211
- [x] After `venvaxi cache` reads a cache database whose recorded schema version differs from
  venvaxi's current schema version, the database's own recorded schema version and package-build
  rows shall be unchanged. —
  `tests/test_cache.py::test_read_cache_state_does_not_mutate_stale_schema_database`; live
  hash-before/hash-after probe (SHA-256, identical `27baabe3...`) plus stage 02's failing-first
  demonstration against a `SymbolStore`-based read
- [x] If no project root resolves, then the `cache` command shall raise
  `ProjectRootNotFoundError`, emit the TOON error block and exit `EX_FAILURE`. —
  `tests/test_cli.py::test_command_cache_no_project_root_propagates`,
  `tests/test_cli.py::test_main_cache_no_project_root_maps_to_exit_1`; not independently
  live-probed - this session's own venv always resolves a project root, so the mocked unit tests
  are the evidence
- [x] If the cache database exists but cannot be read due to a SQLite-level failure, then the
  `cache` command shall raise `StoreError`, emit the TOON error block and exit `EX_FAILURE`. —
  `tests/test_cache.py::test_read_cache_state_wraps_sqlite_error`,
  `tests/test_cli.py::test_command_cache_store_error_propagates`,
  `tests/test_cli.py::test_main_cache_store_error_maps_to_exit_1`; live, a corrupt non-SQLite file
  planted at a throwaway project's resolved cache path
- [x] When `describeBindingTool` resolves a project root, the tool shall extend its object with
  `schema_version`, `db_path` and `db_size_bytes`, then `count: <n>` and a `builds` table of
  `package`, `version`, `depth`, `symbols`, matching `venvaxi cache` field for field. —
  `tests/test_mcp.py::test_describe_binding_tool_reports_cache_summary_when_root_resolves`,
  `tests/test_mcp.py::test_describe_binding_tool_cache_summary_empty_omits_table`; live, in-process
  `describe_binding_tool()` against this project's real cache, byte-identical to criterion 1's
  `venvaxi cache` output
- [x] If no project root resolves, then `describeBindingTool` shall omit the cache summary
  entirely, reporting no marker in its place. —
  `tests/test_mcp.py::test_describe_binding_tool_no_root_omits_cache_fields`; confirmed by reading
  `_mcp.py` lines 159-176, the `root_path is None` branch returns before `read_cache_state` runs
- [x] If the cache database exists but cannot be read due to a SQLite-level failure, then
  `describeBindingTool` shall still emit `root`, `venv` and `status` exactly as on a healthy read,
  returning no error block. — `tests/test_mcp.py::test_describe_binding_tool_unreadable_cache_degrades`;
  live probe, a corrupt file planted at a throwaway project's cache path, `root`/`venv`/`status`
  present and no `error: true` anywhere
- [x] If the cache database exists but cannot be read due to a SQLite-level failure, then
  `describeBindingTool` shall report `schema_version: (cache unreadable)`, still report `db_path`
  and `db_size_bytes`, and omit `count` and the `builds` table entirely - never `count: 0`. —
  `tests/test_mcp.py::test_describe_binding_tool_unreadable_cache_degrades`,
  `tests/test_mcp.py::test_describe_binding_tool_unreadable_cache_never_emits_count_zero`; same
  live probe, checked programmatically for full-string absence of `count`/`builds`, not merely
  `count: 0`
- [x] When `describeBindingTool`'s cache database cannot be read, the tool shall append a third
  hint naming the reported `db_path` as safe to delete. —
  `tests/test_mcp.py::test_describe_binding_tool_unreadable_cache_hints_delete`; same live probe,
  `help[3]:`'s third line names the exact `db_path` reported above it
- [x] When `describeBindingTool`'s cache summary returns a nonzero `count`, the tool shall append a
  third hint naming `refreshPackageGraphTool` as the way to rebuild a package whose recorded build
  looks stale, additional to the two existing onboarding hints. —
  `tests/test_mcp.py::test_describe_binding_tool_cache_nonzero_count_appends_third_hint`; live, the
  populated-cache in-process call (criterion 10) carries `help[3]:` naming `refreshPackageGraphTool`
- [x] When `describeBindingTool`'s cache summary returns `count: 0`, the tool shall not append a
  third hint. — `tests/test_mcp.py::test_describe_binding_tool_cache_zero_count_omits_third_hint`
- [x] When the MCP server is built, the registered `describeBindingTool` description shall state
  that the report includes a summary of the cached symbol graph - schema version, on-disk size, and
  which packages are indexed at which built version and depth. —
  `tests/test_mcp.py::test_describe_binding_tool_description_states_cache_summary`; confirmed
  reading `src/venvaxi/_mcp.py` lines 118-129, the registered docstring states "schema version,
  on-disk size, and which packages are indexed at which built version and depth"
- [x] When the MCP server is built, `describeBindingTool` shall still accept no parameters. —
  `tests/test_mcp.py::test_describe_binding_tool_registered_schema_takes_no_parameters`; live, the
  registered schema's `properties` is `{}`
- [x] When `venvaxi` is run with no subcommand, the home view's `help[]` footer shall include a
  line naming `venvaxi cache`. — `tests/test_cli.py::test_command_home_footer_names_cache`,
  `tests/test_cli.py::test_command_home_prints_status`; live, `uv run venvaxi` and reading
  `src/venvaxi/_cli.py` lines 109-127 both show `help[10]:` carrying the `venvaxi cache` line
- [x] When the packaged skill tables the CLI command surface, the table shall carry a row for
  `venvaxi cache`. — review citation, not a test identifier: `src/venvaxi/SKILL.md` line 118
- [x] When the packaged skill tables the MCP tool surface or describes `describeBindingTool`, the
  text shall reflect the fields the tool now returns. — review citation, not a test identifier:
  `src/venvaxi/SKILL.md` lines 184-189
- [x] When the packaged skill names how to check a suspected-stale graph, it shall name the cache
  summary as the way to check without paying for a rebuild. — review citation, not a test
  identifier: `src/venvaxi/SKILL.md` lines 282-286

## Risks / unknowns

- **The non-mutating read is the one genuinely new mechanism this unit adds**, and it has no
  precedent in the codebase to copy from - every other command that touches the cache does so
  through the path that keeps it current. Getting the read-only connection wrong in either
  direction is a real risk: too permissive, and a `venvaxi cache` call could silently drop a
  schema-mismatched cache's rows exactly as the caller went looking for them; too defensive, and a
  perfectly healthy cache could be misreported as unreadable. Stage 02 should test both a
  current-schema and a stale-schema database explicitly, asserting the file is byte-identical
  before and after the read where the schema is stale.
- **Whether an unreadable cache should raise or degrade on `describeBindingTool` was an open
  question at the review gate; the maintainer decided it degrades.** The first draft of this plan
  had it raise `StoreError`, reasoning that a corrupt cache is a fault in venvaxi's own store rather
  than a fact about the caller's project. The maintainer overruled that: `root`, `venv` and `status`
  cost no file I/O and stay knowable regardless of the cache's health, and withholding them to match
  a cache-read failure would break the one promise this tool exists to keep - answering in a broken
  or uninitialized project, which is exactly the state a caller reaching for it is usually already
  in. The degrade never emits `count: 0` (a third `schema_version: (cache unreadable)` marker keeps
  it distinct from both other empty states, per Principle 5), still reports `db_path`/`db_size_bytes`
  as plain filesystem facts, and carries a hint naming the database as safe to delete. `venvaxi
  cache` is unaffected and still raises - there the cache is the whole answer, so failing is honest,
  where here it is only half of one.
- **Growth remains unbounded regardless of what this unit ships.** Observability was the issue's
  explicit ask, not a remedy; a cache that keeps growing per dead project root and per uninstalled
  package will keep doing so after this lands. The figures cited in Scope make that visible without
  fixing it, by design - eviction is a separate unit.
- **This machine's own cache figures do not corroborate the issue's largest numbers.** The 102.4
  MiB and 190.97 MiB figures come from the issue's own comments, against project caches (`mpctraj`
  and others) not present on this machine; this machine's own two caches total 36.5 MiB. Both are
  reported in Scope rather than reconciled, because they are not in tension - different projects at
  different dependency counts produce different cache sizes, and the point being evidenced (growth
  is unbounded and has been measured large) does not require reproducing the largest figure locally.

## Notes

**A read-only cache reader must never open a `SymbolStore`.** `SymbolStore.__init__` calls
`_ensure_schema`, which drops every table on a `user_version` mismatch as a side effect of merely
connecting - so any command whose entire job is reporting *as-found* cache state, rather than
keeping the cache current, cannot use the path every other cached command uses to open the store.
Proved empirically twice, by separate constructions: the mediator forced `user_version = 6`, stage
03 forced `user_version = 999`; both hashed the cache file before and after the read and found it
byte-identical either way. This is why `specs/commands/cache.md` carries a Local principle
("Observability MUST NOT cost the observer a mutation") rather than an implementation note - the
constraint is load-bearing enough to be a spec-level obligation, not an incidental detail of how
`read_cache_state` happens to be written.

**Why `describeBindingTool` degrades where `venvaxi cache` raises.** The maintainer decided this
at the stage 01 review gate, overruling the first draft's plan to raise `StoreError` on both
surfaces. On `venvaxi cache` the cache summary *is* the whole answer, so a read failure raising is
honest - there is nothing else to report. On `describeBindingTool` the cache summary is only half
of the answer; `root`, `venv` and `status` cost no file I/O and stay knowable regardless of the
cache's health, and they are exactly what a caller already holding a suspected-wrong binding needs,
so withholding them to match a cache-read failure would break the one promise this tool exists to
keep. The degrade must never emit `count: 0`, because `0` is a real, distinct fact (a cache that
opened cleanly and recorded nothing) that this degrade is not reporting - collapsing 'unreadable'
into 'empty' would let a caller mistake a broken cache for a merely unbuilt one. A third
`schema_version: (cache unreadable)` marker keeps the state distinct from both of the other two
empty states (`(not built)` and a real version with `count: 0`), per Principle 5.

**The "scoped to that trigger alone" sentence in `specs/mcp/tools.md` Failure modes had to be
rewritten, not deleted, once a second degrade trigger existed.** Before this unit,
`describeBindingTool` had exactly one degrade path (no project root); this unit adds a second,
independent one (an unreadable cache). The existing sentence asserting single-trigger scoping
would have been false the moment a second trigger existed, so it was generalized to state that
*each* degrade is scoped to its own trigger and none absorbs a failure outside it, rather than
dropped. This is a recurring milestone pattern worth naming: a rule true when written can
generalize wrongly as the system grows a second case, and the fix is to widen the rule's
statement, not remove it. Stage 03 verified the generalized rule by code inspection - the narrow
`except ProjectRootNotFoundError` and `except StoreError` clauses in `_mcp.py` (lines 144-156 and
188-207) each catch only their own trigger, so any other exception on either path still reaches
the broad `_toon_errors` handler rather than either degrade - not by a live probe forcing an
unrelated exception mid-resolution, which would require a harder repro than this unit needed.

**Timestamp deliberately out of scope.** No table in the shipped `src/venvaxi/schema.sql` - not
`package_builds`, not `nodes`, not `edges` - carries any temporal column at all, so 'when was this
built' is not an additive query the way `schema_version`/`db_path`/`db_size_bytes`/`builds` are.
Answering it needs a schema change and a `SCHEMA_VERSION` bump, and the honest value for every row
written before the bump would be `null`, never a backfilled guess. That is a real migration and a
separate, larger unit - not this one.

**Unbounded, deliberately, matching `list` rather than `find`/`show --api`.** A cache row exists
only for a package some query has actually touched - a strict subset of a project's declared
dependencies, tighter than `list`'s own reasoning for staying unbounded. A row cap would add a
`--limit`/`limit=` surface to a command whose entire purpose is showing the caller everything the
cache currently holds, undercutting the reason the command exists.

**No `SCHEMA_VERSION` bump for this unit.** The bump trigger is a change to the *content* a walk
records; this unit adds a read over already-recorded state and changes nothing `_walk_module`
writes, so no cached graph needs rebuilding because of this change.

**Stage 02's one declared deviation: `describe_binding_tool` inlines root/venv/status resolution
rather than reusing `resolve_binding()`.** The techspec required the reader to hold the
unformatted `Path`, resolved once and reused, not re-derived by parsing it back out of
`resolve_binding()`'s already-`~/`-formatted `root` string. Calling `_core.get_project_root()`
directly (module-qualified, alongside the existing `from venvaxi._core import ...` names) keeps
one real resolution in hand for both the binding report and `read_cache_state`/
`get_cache_db_path`, rather than resolving twice or touching `_core.py` itself, which the
techspec's component architecture table left unchanged. Stage 03 confirmed no observable output
differs: `root`/`venv`/`status` in live probes match the home-view/`resolve_binding()` shape
exactly, and `resolve_binding` is still imported but otherwise unused in `_mcp.py`.

## Follow-ups

- **Issue [#89](https://github.com/andyrids/venv-axi/issues/89)** - `_installed_version` is called
  with the **import** name, so a package whose import name is not also a distribution name records
  `""`, and `is_cache_valid` then compares `"" == ""` and returns `True` permanently -
  version-based invalidation never fires for that class. This unit is the strongest evidence it
  worked: `venvaxi cache` showed `dns|""|2|3314` on its first run, `metadata.version('dns')`
  raises while `metadata.version('dnspython')` returns `2.8.0`, and `yaml`, `bs4`, `dateutil` and
  `PIL` resolve the same way in this venv. Pre-existing, outside this unit's own changes - filed
  from it because `cache` is the first command to print a package's build version in isolation
  rather than alongside other metadata.
- **Cache eviction.** Growth is unbounded in two directions - per project root with nothing
  pruning a dead root, per package with nothing evicting an uninstalled one. This unit makes that
  growth observable, not bounded - `grep -rE 'evict|TTL|max_size|LRU|expire|prune' src` returns
  zero matches, confirmed. Owned by no issue.
- **A build timestamp.** The part of the issue's original ask this unit deliberately did not
  answer - see Notes above for why it is a schema change and a `SCHEMA_VERSION` bump rather than
  an additive read. Owned by no issue.
- **A crash-corrupted WAL was not reproduced.** The common un-checkpointed-but-committed case was
  probed twice (stage 02 and stage 03) and the read-only reader works against it correctly; a
  genuinely torn WAL from a process killed mid-write is a harder repro that neither stage
  attempted. If a real gap exists here it is more likely to surface as a `StoreError` (criteria 9
  and 12-14's degrade paths already handle that on both surfaces) than as a silently wrong read,
  but that is inference, not evidence. Owned by no issue.
- **None of the above belongs to issue [#50](https://github.com/andyrids/venv-axi/issues/50)**
  (`installed-package-visibility`, the next and final 0.4.0 unit, concerned with `list`'s
  visibility of installed-but-undeclared packages). No `Deferred to` entry is filed here for that
  reason - `installed-package-visibility` has no plan file yet to absorb one, and nothing above is
  its subject in any case.
