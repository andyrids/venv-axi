---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/mcp/tools.md
  - specs/behaviors/skill-content.md
authors:
  - specs/behaviors/cache-refresh.md
issues: [68]
pr:
---

# Plan: mcp-cache-refresh

## Scope

No MCP tool can rebuild the symbol cache, so an agent working through the surface `venvaxi setup`
registers as its primary ambient integration has no way to make its own edits visible. The CLI has
`--refresh` on five commands; the MCP surface has nothing.

The cache is invalidated by installed version plus build depth, and an editable install edited in
place moves neither. The recorded version is the frozen `Version` field of the installed
distribution's metadata, so for an ordinary edit-and-verify loop with no reinstall, version-based
invalidation never fires - that is the default outcome for any editable-installed project, not a
corner case.

The failure is worse than an outdated docstring. Verified against `mpctraj` on 0.3.2 (issue 68,
second owner comment): a public-named probe module was indexed via CLI `--refresh`, then deleted
from disk entirely, and all three read tools kept serving a complete signature and docstring for
the deleted symbol - `getSymbolTool` a full node, `showModuleTool` a `children` row,
`findSymbolTool` `count: 1`. An agent has no way, on this surface, to tell that from a correct
answer.

In scope: a tenth MCP tool, `refreshPackageGraphTool`, taking a required package name and
rebuilding that package's cached graph; its output, footer, failure modes and registered
description; the ripple through `specs/mcp/tools.md`'s tool count and its Divergences, Out of
scope and Error message wording sections; the discharge of that file's Known exception; and the
four places the packaged skill describes the MCP surface or the rebuild route in terms a tenth
tool falsifies.

Out of scope, and stated so the boundaries are not assumed: a `refresh` parameter on the nine read
tools (the divergence is narrowed to one named exception, not removed); a bare 'refresh
everything' form on either surface; a staleness signal carried by read answers or a cache summary
on the binding report, which is issue [#49](https://github.com/andyrids/venv-axi/issues/49); a
depth parameter on the new tool (see Approach); any change to what a walk records, and therefore
any schema-version bump.

## Implements

`specs/mcp/tools.md` - the tenth tool's full contract. A new `## The refresh tool` section
declaring its output object (`package`, `depth`, `symbols`), why the symbol count is not the
`count:` aggregate, which output-contract clauses reach nothing here and why, its footer, its seven
failure modes, and its registered description as part of the contract. The tool count moves from
nine to ten in three places. `## Divergences from the CLI` narrows 'No `refresh` parameter on any
tool' to 'on any read tool', with the dedicated tool as the single named exception. `## Out of
scope` renames the mutating-tools Never to *repo*-mutating and states why a cache rebuild is not
one, and draws the line against #49's cache-state territory. `## Error message wording` loses its
`### Known exception` and gains the criterion that discharges it.

`specs/behaviors/skill-content.md` - no amendment; the plan brings `src/venvaxi/SKILL.md` back into
conformance with its existing rules. Three claims go false when this lands: the nine-row MCP tool
table, which asserts the whole surface and would assert a surface that is not the surface; 'No tool
takes a `refresh` parameter. A stale graph can only be rebuilt from the CLI'; and the verbatim
quotation of the unscoped-refresh rejection message, whose string changes. A fourth entry, the
*When to `--refresh`* gotcha, stays true but stops being sufficient: it is the entry an agent reads
to learn how to rebuild, and it names only a shell an MCP-driven agent cannot reach, which is the
wasted-query failure mode the same spec obliges the skill to name the correct move for.

`specs/behaviors/cache-refresh.md` is in `authors:`, not `specs:`. It gains a new
`### Rebuild scope and depth` Details section, a paragraph in `### Rebuild` making the
failed-refresh outcome explicit, a sharpened editable-install paragraph, a generalized
package-scope sentence, and an Out of scope entry for the per-read staleness signal. Every clause
declares behaviour the code already exhibits - `find --package X --refresh` has rebuilt
package-scoped at the default depth since the flag existed - so claiming conformance here would
assert a verification this plan does not perform. The new tool's conformance is verified against
`specs/mcp/tools.md`.

## Approach

1. Open this plan at `status: planned`; stage 02 flips it to `in-progress`.
2. Add `refresh_package_graph` to `src/venvaxi/_introspect.py` alongside the other entry points. It
   validates and resolves the name the way `_build_store_for` already does, opens the store with a
   forced rebuild, and returns the resolved package name, the depth walked and the count of nodes
   recorded for that package. `SymbolStore` needs one new read for the count.
3. Add `refresh_package_graph_tool(name)` to `src/venvaxi/_mcp.py` and append it to `_TOOLS`. It
   registers as `refreshPackageGraphTool` through the existing camelCase conversion, and inherits
   `_toon_errors` unchanged - every failure mode in the spec is already covered by that wrapper.
4. Write the registered description as the tool's docstring, the way `describe_binding_tool` does,
   and for the same contracted reason.
5. Bring the unscoped-rebuild rejection in `find_symbol` into conformance with Error message
   wording, following the `Search limit` -> `Result limit` precedent from
   [api-collection-bound](api-collection-bound.md). No test pins the current string; the
   replacement test asserts the flag spellings are *absent* as well as the new wording present, per
   the one-way-assertion rule that unit found.
6. Update `src/venvaxi/SKILL.md` in four places and regenerate the installed copy, since
   `specs/behaviors/skill-content.md` forbids a skill claim `specs/**` does not declare. The
   nine-row MCP tool table needs a tenth row, or it asserts a surface that is not the surface. The
   'No tool takes a `refresh` parameter' bullet under *Notable CLI differences* goes false
   outright. The `find` gotcha quotes the unscoped-rebuild rejection verbatim, and that string
   changes at step 5. The *When to `--refresh`* gotcha names only the CLI route, so an MCP-driven
   agent reading the entry written to tell it how to rebuild is sent to a shell it cannot reach -
   the wasted-query failure mode that spec obliges the skill to name the correct move for.
7. Verify both surfaces, run the suite, coverage and hooks.
8. Record for stage 04: `README.md` enumerates the nine tool names in prose (lines 79 to 81) and
   will be incomplete. No spec governs README content - `specs/behaviors/skill-content.md` applies
   to `src/venvaxi/SKILL.md` alone - so it carries no Validation criterion and is documentation
   work, not implementation. It is written down here so stage 04 does not have to rediscover it.

**No depth parameter, and the reasoning is the depth reset rather than an appeal to YAGNI alone.**
A forced rebuild clears the package and re-walks it at whatever depth the caller asked for, so a
scope-only refresh resets a graph previously built deeper. That is already true of
`find --package X --refresh`, which rebuilds at the default depth today. A depth parameter would
be the first place on either surface where a caller sets build depth with no query attached, and
the lazy-depth model already supplies the lever: a `getModuleTreeTool` call at a greater depth
finds the recorded depth insufficient and rebuilds to what it needs. The one answer that does not
repair itself is `inherits`, which requests only the depth its own name implies - that cost is
declared in `cache-refresh.md` and reported by the tool's `depth` field rather than left silent.
Adding a parameter to pre-empt it would buy a caller the ability to choose a number it has no
basis for choosing.

**Three fields, and why not four.** `package` because the graph is keyed by an import name the
caller may not have supplied. `depth` because the reset above must be visible. `symbols` because it
is the one field separating a rebuild that produced a graph from one that walked almost nothing.
`version` is deliberately absent: in the editable-install case that motivates this tool the version
has not moved by definition, so reporting it invites the reader to conclude nothing was rebuilt -
and built version paired with built depth is exactly the staleness summary #49 owns.

**Why a dedicated tool rather than a `refresh` parameter.** Settled by the maintainer before this
unit opened. It narrows the standing divergence to one named exception instead of widening nine
schemas, and it keeps a slow operation explicitly invoked: a parameter on nine read tools is
reachable by any caller that guesses it should be set, and a named tool is not reached by accident.

**Why the Known exception is discharged here.** Read literally, its trigger is 'the moment a
refresh parameter reaches this surface', and a dedicated tool is not a parameter -
`findSymbolTool` still has none, so the message still reaches no tool caller. It is discharged
anyway, on the maintainer's instruction and for a reason that survives the literal reading: after
[api-collection-bound](api-collection-bound.md) it is the only message on the shared path still
spelled for one surface, this is the change its own text names as its trigger, and leaving it is
how a documented exception becomes permanent. The honest framing is that this discharges a
standing obligation rather than fixing a live divergence, and it is recorded that way.

**No `SCHEMA_VERSION` bump.** The bump trigger is a change to the *content* a walk records. This
unit exposes the existing rebuild path over a second surface and changes nothing about what
`_walk_module` writes, so no cached graph is left holding a value computed the old way.

## Validation

- [x] When `refreshPackageGraphTool` is called with the name of an installed package, the tool
  shall rebuild that package's cached symbol graph and emit a TOON object naming the resolved
  package, the recorded build depth and the number of symbol nodes recorded. —
  `tests/test_mcp.py::test_refresh_package_graph_tool_returns_receipt_object`,
  `tests/test_introspect.py::test_refresh_package_graph_reports_the_rebuilt_walk`,
  `tests/test_store.py::test_count_nodes_counts_only_the_named_package`; live in this venv,
  `refreshPackageGraphTool('rich')` returned `package: rich` / `depth: 2` / `symbols: 1572`
- [x] When `refreshPackageGraphTool` is called with a distribution name whose import name differs,
  the tool shall report the resolved import name the graph is keyed by. —
  `tests/test_introspect.py::test_refresh_package_graph_reports_resolved_import_name`,
  `tests/test_mcp.py::test_refresh_package_graph_tool_reports_resolved_import_name`; live,
  `refreshPackageGraphTool('dnspython')` returned `package: dns` against real installed metadata
- [x] When `refreshPackageGraphTool` completes, the tool shall emit a `help[]` footer naming the
  tool that searches the rebuilt graph, carrying the package scope. —
  `tests/test_mcp.py::test_refresh_package_graph_tool_footer_scopes_the_search`; live,
  ``help[1]: Call `findSymbolTool` with a query and package=dns to search the rebuilt graph``
- [x] When `refreshPackageGraphTool` completes, the tool shall not emit a leading `count:`
  line. — `tests/test_mcp.py::test_refresh_package_graph_tool_omits_count_line`; live, neither
  the `rich` nor the `dns` output contains a `count:` substring anywhere
- [x] When `refreshPackageGraphTool` rebuilds a package whose graph was last built deeper than the
  default build depth, the tool shall report the default build depth as the recorded depth. —
  `tests/test_introspect.py::test_refresh_package_graph_resets_depth_to_default`; live, the real
  `rich` graph recorded `('15.0.0', 4)` after `get_module_tree("rich", max_depth=4)` and
  `('15.0.0', 2)` after the refresh, whose receipt read `depth=2`
- [x] When a public-named module is deleted from an editable-installed project's source and
  `refreshPackageGraphTool` is called for that package, `getSymbolTool` shall report the deleted
  symbol as not found on its next call. — mediator-run on the scratch `axitestbed` testbed and
  **not on `mpctraj`**, the project issue 68 was filed against; transcript steps 3 and 5 in
  `ICM/process-plan/stages/03-verification/output/mcp-cache-refresh-test.md`. Before the refresh a
  full node carrying ``signature: "(alpha: int, beta: str = 'x') -> bool"``; after it,
  ``message: "Symbol `axitestbed.axi_probe::axi_probe_sentinel` not found"``
- [x] When a public-named module is deleted from an editable-installed project's source and
  `refreshPackageGraphTool` is called for that package, `findSymbolTool` shall return `count: 0`
  for the deleted symbol's name on its next call. — mediator-run on the scratch `axitestbed`
  testbed and **not on `mpctraj`**; same transcript, steps 3 and 5: `count: 1` before the refresh,
  `count: 0` with the `Re-call with package=<package> to index it and search` hint after
- [x] When a public-named module is deleted from an editable-installed project's source and
  `refreshPackageGraphTool` is called for that package, `showModuleTool` shall return the TOON
  error block for the deleted module on its next call. — mediator-run on the scratch `axitestbed`
  testbed and **not on `mpctraj`**; same transcript, steps 3 and 5: a module node with
  `children count: 1` before the refresh, ``message: Module `axitestbed.axi_probe` not found``
  after
- [x] When the MCP server is built, the registered `refreshPackageGraphTool` description shall
  state what it rebuilds, name source changed with no reinstall as the situation calling for it,
  and mark it as a rebuild rather than a read. —
  `tests/test_mcp.py::test_refresh_tool_registered_description_states_the_contract`; live, read
  off `tool.description` in the registered listing - "one package's cached symbol graph", "when a
  package's source changed with no reinstall" and "This is a rebuild, not a read"
- [x] When the MCP server is built, the refresh tool shall appear in the registered tool listing
  under the name `refreshPackageGraphTool`. —
  `tests/test_mcp.py::test_build_server_registers_refresh_tool_under_contract_name`,
  `tests/test_mcp.py::test_build_server_registers_tools`,
  `tests/test_mcp.py::test_build_server_no_root_still_builds_with_marker`; live,
  `server.list_tools()` returned ten names with `refreshPackageGraphTool` among them
- [x] When the MCP server is built, the nine read tools shall each still expose no `refresh`
  parameter. — `tests/test_mcp.py::test_registered_read_tools_expose_no_refresh_parameter`, which
  asserts `len(reads) == 9` as well as the per-tool absence; live, a per-tool
  `tool.parameters["properties"]` audit of all ten registered schemas
- [x] If `refreshPackageGraphTool` is called with a name that is not a possible package name, then
  the tool shall return the TOON error block. —
  `tests/test_mcp.py::test_refresh_package_graph_tool_malformed_name_returns_error_block`; live,
  `refreshPackageGraphTool('not a package')` returned `error: true` /
  ``message: Invalid package name `not a package` ``
- [x] If `refreshPackageGraphTool` is called with a package not installed in the venv, then the
  tool shall return the TOON error block. —
  `tests/test_mcp.py::test_refresh_package_graph_tool_not_installed_returns_error_block`; live,
  `refreshPackageGraphTool('definitelynotinstalledpkg')` returned `error: true` /
  ``message: Package `definitelynotinstalledpkg` is not installed in the active venv``
- [x] If the named package cannot be imported, then `refreshPackageGraphTool` shall return the TOON
  error block. —
  `tests/test_mcp.py::test_refresh_package_graph_tool_import_error_returns_error_block`, which
  monkeypatches `importlib.import_module` to raise for a genuinely installed package. Not
  live-probed: a real import failure means breaking an installed package on disk
- [x] If no project root resolves, then `refreshPackageGraphTool` shall return the TOON error block
  rather than degrading to a `(no project root)` marker. —
  `tests/test_mcp.py::test_refresh_package_graph_tool_no_project_root_returns_error_block`, which
  asserts `error: true` present **and** `NO_PROJECT_ROOT` absent
- [x] If a submodule raises at import time during the rebuild, then `refreshPackageGraphTool` shall
  skip that submodule and report a completed rebuild. —
  `tests/test_introspect.py::test_refresh_package_graph_skips_unimportable_submodule`, which logs
  three real skips from the fixture package and asserts `receipt.symbols > 0` with the skipped
  submodule absent from the package's children
- [x] If the rebuild raises after the package's existing nodes have been cleared, then the package
  shall be left unindexed, so the next query for it rebuilds rather than answering from a
  half-built graph. —
  `tests/test_introspect.py::test_refresh_package_graph_failed_rebuild_leaves_it_unindexed`, which
  asserts both `store.count_nodes(pkg) == 0` and `store.get_build(pkg) is None`
- [x] If a SQLite-level failure occurs during the rebuild, then `refreshPackageGraphTool` shall
  return the TOON error block. —
  `tests/test_introspect.py::test_refresh_package_graph_sqlite_failure_raises_store_error` (the
  raise, against the real build path) and
  `tests/test_mcp.py::test_refresh_package_graph_tool_store_error_returns_error_block` (the
  rendering through `_toon_errors`). Not live-probed, and deliberately not corroborated by the
  `axitestbed` reproduction, which induced no SQLite fault - stage 03 finding F4
- [x] If `refreshPackageGraphTool` returns an error block, then it shall omit the `help[N]:`
  footer. — `tests/test_mcp.py::test_refresh_package_graph_tool_error_omits_help_footer`; live,
  the exact returned bytes were
  ``'error: true\nmessage: Invalid package name `not a package`'`` - no footer, no padding
- [x] If a rebuild is requested with no package to scope it, then the rejection message shall name
  neither the CLI flag spellings nor a tool parameter spelling, so it reads correctly from either
  surface. —
  `tests/test_introspect.py::test_find_symbol_unscoped_refresh_names_the_package_scope`, which
  asserts the new string present and `--refresh`, `--package`, `package=` and `refresh=` each
  absent; live, `uv run venvaxi find "Console" --refresh` exited 1 with
  `message: A rebuild must name the package to rebuild`. Demonstrated on the CLI surface and on
  the shared path only - `findSymbolTool` exposes no `refresh`, so no tool call can reach the
  guard (stage 03 finding F3)
- [x] When the packaged skill describes the MCP tool surface, it shall name
  `refreshPackageGraphTool` as the way to rebuild a stale graph over MCP. — review citation, not
  a test identifier: `src/venvaxi/SKILL.md` lines 191-194, the *Notable CLI differences* bullet -
  "`refreshPackageGraphTool` is the single exception and the way a rebuild is started over MCP"
- [x] When the packaged skill quotes the unscoped-rebuild rejection, it shall quote the message the
  code raises. — review citation, not a test identifier: `src/venvaxi/SKILL.md` line 204 -
  `A rebuild must name the package to rebuild`, byte-compared against the literal in
  `src/venvaxi/_introspect.py` and against the live CLI raise cited two boxes above
- [x] When the packaged skill tables the MCP tool surface, the table shall carry a row for every
  registered tool. — review citation, not a test identifier: `src/venvaxi/SKILL.md` lines 169-178
  carry ten rows, equal name for name to the ten-entry registered listing, the tenth added at line
  178 as `` | `refreshPackageGraphTool` | `name` | `venvaxi <cmd> ... --refresh` | ``
- [x] When the packaged skill says when to reach for a rebuild, it shall name the MCP route
  alongside the CLI flag. — review citation, not a test identifier: `src/venvaxi/SKILL.md` lines
  237-247, the **When to rebuild** gotcha - "Over the CLI that is `--refresh`; over MCP it is
  `refreshPackageGraphTool` with the package name, which is the only route an MCP-driven agent
  has"

## Risks / unknowns

- **A dedicated tool is not literally what the Known exception names as its trigger.** Its text
  says 'a refresh parameter', and after this unit `findSymbolTool` still has none, so the message
  remains unreachable from a tool caller. It is discharged on the maintainer's instruction. If a
  future reader concludes the trigger was never tripped, the record here is the answer: it was
  discharged as a standing obligation, and the alternative was a documented exception with no
  remaining trigger.
- **The refresh receipt sits close to #49's territory.** `depth` and `symbols` are facts about the
  walk that just ran, not about the graph as the caller found it, and the tool is silent unless a
  rebuild was asked for. The line is drawn in `specs/mcp/tools.md` Out of scope, but it is thin,
  and a future #49 spec adding a cache summary to the binding report must not read this tool as
  precedent for answering the same question by mutating.
- **A failed refresh costs the cached graph.** Clearing is committed before the walk, so a rebuild
  that raises leaves the package unindexed rather than stale. That is the safe direction and it is
  now declared, but a caller whose refresh fails on a broken package loses answers it had a moment
  earlier, and gets them back only by fixing the package.
- **The `inherits` shrink is real and is being accepted, not fixed.** A scope-only rebuild resets
  the recorded depth, and `inherits` never asks for more than its own name implies, so subclasses
  found under a previously deeper build disappear until some query builds that deep again. It is
  pre-existing CLI behaviour that this unit exposes to a second surface and writes down for the
  first time.
- **The reproduction cannot be discharged by a fixture.** It requires an editable-installed project
  whose source is deleted on disk; `D:\Projects\github\mpctraj` is the testbed every 0.4.0 issue
  was raised against. The probe module must be **public-named**: `_walk_submodules` skips
  underscore-prefixed submodules unconditionally, so an `_`-prefixed probe reads 'not found'
  whether the graph is stale or fresh and demonstrates nothing.
- **The underscore-submodule skip is declared in no spec.** It is real behaviour that the
  reproduction depends on, and issue 68's second comment attributes it to
  `specs/behaviors/qualified-name-semantics.md`, which does not contain it. Flagged, not fixed
  here - it is not this unit's change to make.

## Notes

**A dedicated tool, not a `refresh` parameter on the nine read tools.** Settled by the maintainer
before the unit opened, and the reasoning is worth keeping because the cheaper-looking option is
the parameter. A parameter would have widened nine schemas to narrow one divergence; the tool
narrows the divergence to a single named exception and leaves the nine read tools alone, which is
what criterion 11 now pins. It also keeps a slow operation explicitly invoked: a `refresh=true` on
nine read tools is reachable by any caller that guesses it should be set, and the registered
description has to spend its words talking an agent out of prefixing every lookup with it. A named
tool is not reached by accident. The description still carries the warning - "This is a rebuild,
not a read" - but as a caution rather than as the only guard.

**No depth parameter, and the reason is the depth reset rather than YAGNI.** A forced rebuild
clears the package and re-walks it at whatever depth the caller asked for, so a scope-only refresh
resets a graph previously built deeper. This is not new - `find --package X --refresh` has done it
since the flag existed - but the new tool exposes it to a surface that never had it. A depth
parameter would have been the first place on either surface where a caller sets build depth with
no query attached, and the lazy-depth model already supplies the lever: a `getModuleTreeTool` call
at a greater depth finds the recorded depth insufficient and rebuilds to what it needs.

**What the `inherits` shrink costs, stated plainly.** `inherits` requests only the depth its own
name implies and never deepens the graph on demand, so it is the one query that does not repair
itself after a rebuild. A subclass homed below the default build depth becomes invisible again
until some other query builds that deep. That cost is accepted, not fixed: it is declared in
`specs/behaviors/cache-refresh.md` `### Rebuild scope and depth`, reported rather than hidden by
the receipt's `depth` field, and named in the skill's **When to rebuild** gotcha. Adding a depth
parameter to pre-empt it would have bought a caller the ability to choose a number it has no basis
for choosing.

**Three receipt fields, and why not four.** `package` because the graph is keyed by an import name
the caller may not have supplied - `refreshPackageGraphTool('dnspython')` answers `package: dns`.
`depth` because the reset above must be visible. `symbols` because it is the one field separating
a rebuild that produced a graph from one that walked almost nothing; the reproduction's
`symbols: 1` is what proved the deleted probe was genuinely unimportable rather than resurrected
from `__pycache__`. `version` is deliberately absent, for two reasons that point the same way: in
the editable-install case that motivates this tool the version has not moved by definition, so
reporting it invites the reader to conclude nothing was rebuilt; and built version paired with
built depth is exactly the staleness summary
[#49](https://github.com/andyrids/venv-axi/issues/49) owns.

**The Known exception was discharged as a standing obligation, not as a live divergence.** Read
literally, `specs/mcp/tools.md`'s `### Known exception` named its own trigger as 'the moment a
refresh parameter reaches this surface', and a dedicated tool is not a parameter - `findSymbolTool`
still exposes none, so the reworded message still reaches no tool caller. It was discharged anyway,
on the maintainer's instruction, for a reason that survives the literal reading: after
[api-collection-bound](api-collection-bound.md) it was the only message on the shared path still
spelled for one surface, this is the change its own text names as its trigger, and leaving it is
how a documented exception becomes permanent. A future reader concluding the trigger was never
tripped has the answer here: it was not, in the letter; the alternative was a documented exception
with no remaining trigger. Stage 03 recorded the same point independently as finding F3.

**`specs/behaviors/cache-refresh.md` is in `authors:`, not `specs:`, and that was not a filing
convenience.** Every clause it gained declares behaviour the code already exhibits -
`find --package X --refresh` has rebuilt package-scoped at the default depth since the flag
existed - so listing it in `specs:` would have claimed a conformance this unit never verified, and
stage 03 would have had to report against clauses no code moved for. It is the `specs:`/`authors:`
split doing its job: the new tool's conformance is verified against `specs/mcp/tools.md`, and
`cache-refresh.md` is written down rather than chased. Stage 03 respected the boundary and cited
the file only where `specs/behaviors/skill-content.md`'s own rule - no skill claim `specs/**` does
not declare - pointed at it as the declaring spec.

**No `SCHEMA_VERSION` bump, deliberately.** The bump trigger is a change to the *content* a walk
records. This unit exposes the existing rebuild path over a second surface and changes nothing
about what `_walk_module` writes, so no cached graph is left holding a value computed the old way.
The three preceding 0.4.0 units each bumped it for a real content change; this one would have
forced a rebuild on every user for nothing.

**A failed refresh costs the cached graph, and that is the safe direction.** Clearing is committed
before the walk, so a rebuild that raises leaves the package unindexed rather than half-built -
the next query rebuilds instead of trusting a zero-node graph. Criterion 17's test asserts both
halves (`count_nodes == 0` **and** `get_build() is None`), because emptiness alone would still let
a later query answer from it. The cost: a caller whose refresh fails on a broken package loses
answers it had a moment earlier, and gets them back only by fixing the package.

**The rejection message was shortened after the stage 02 review.** The first implemented form was
`A rebuild must name the package whose graph to rebuild`; the 'whose graph' clause was dropped on
the maintainer's approval. No spec change and no stage 01 re-entry followed - `specs/mcp/tools.md`
Error message wording requires the message to name the missing package scope rather than the flags
that spell it on the CLI, and the shorter form still does.

**Stage 03 findings worth remembering.**

- **F1 - review-citation line numbers drift.** Stage 02's four `src/venvaxi/SKILL.md` citations
  were two lines off in two of four cases. Stage 03 re-read the file and the corrected spans are
  what the four review-citation boxes above carry: table row 178, divergence bullet 191-194,
  quoted rejection 204, rebuild gotcha 237-247. The content was exactly as stage 02 described in
  every case; only the spans moved. The general lesson is the one stage 03 drew - cite the file,
  not the report - and it is why a line-span citation is worth less than a test identifier and
  should be paired with the quoted text, as these four are.
- **F3 - the reworded message is unreachable from any MCP tool caller.** Recorded above under the
  Known exception. Criterion 20's MCP-side demonstration is a call on the shared path, not a tool
  call, because no tool call can reach the guard. Not a defect and not new; flagged so the frozen
  record does not overstate what was observed.
- **F4 - evidence filed under the criterion it serves.** The reproduction's footer-free error
  blocks were offered as corroboration of criterion 18 (a SQLite fault) and belong to criterion 19
  (footer omission); nothing in the reproduction induced a SQLite fault. Stage 03 re-filed them
  rather than accepting them, and recorded a second caveat at 19: those blocks came from sibling
  read tools, so they corroborate the shared error-shape rule rather than being a second
  observation of `refreshPackageGraphTool`.
- **The `ruff format --check` trap.** `uv run ruff format --check` reports files 'would be
  reformatted' against this tree and that is **not** a divergence. `pyproject.toml` declares no
  `[tool.ruff]` section; the `pkgdx-format` hook supplies its own configuration, and the project's
  style is a 79-column wrap where bare ruff defaults to 88. `prek run --all-files` is the
  authority and it passes. The same trap as a bare `pymarkdown scan`, and it cost stage 03 a
  probe.

**The reproduction ran on a scratch testbed, not on the project issue 68 was filed against.**
Criteria 6, 7 and 8 were run by the mediator on `axitestbed`, a throwaway editable-installed
project with a frozen `Version` in its `.dist-info` metadata, authorized by the maintainer in place
of `D:\Projects\github\mpctraj`. It reproduces the mechanism faithfully - version-based
invalidation cannot fire, and the probe module is public-named so `_walk_submodules`' unconditional
underscore skip cannot make it read 'not found' for the wrong reason - so it evidences the
behaviour the three criteria declare. It does not re-run issue 68's own specimen; that is a
follow-up below.

**The rebuild gotcha was renamed, not only extended.** Stage 02 deviated from the techspec here and
declared it: **When to `--refresh`** became **When to rebuild**, because an entry titled after a
CLI flag keeps the exact defect the edit exists to fix - an MCP-driven agent scanning gotcha titles
for how to rebuild sees only a flag it cannot type. Stage 03 independently reproduced the grep
showing no spec, source or test depends on the old title. The same entry gained the depth-reset and
`inherits` sentences, both declared in `specs/behaviors/cache-refresh.md`.

**No user-facing documentation needed changing beyond `README.md`.** `src/venvaxi/SKILL.md` was
corrected during implementation, because `specs/behaviors/skill-content.md` forbids a skill claim
`specs/**` does not declare and three of its claims went false when the tenth tool landed; the
installed copy was regenerated and `tests/test_skill_parity.py` enforces byte parity.
`docs/architecture.md` names no tool count and needed no edit.

## Follow-ups

- **Issue [#49](https://github.com/andyrids/venv-axi/issues/49)** - cache state, the next unit. Two
  things hand over to it. First, the boundary: this tool's `depth` and `symbols` are facts about
  the walk that just ran, not about the graph as the caller found it, and the tool is silent unless
  a rebuild was asked for. A #49 spec adding a cache summary to the binding report **must not**
  read the refresh receipt as precedent for answering 'what does the graph hold' by mutating - the
  line is drawn in `specs/mcp/tools.md` Out of scope, and it is thin. Second, the omission:
  `version` was deliberately left off the receipt because built version paired with built depth is
  the staleness summary #49 owns. Not deferred - #49 has no plan file yet to absorb a deferral.
- **Issue [#87](https://github.com/andyrids/venv-axi/issues/87)** - the underscore-submodule skip
  is declared in no spec. `_walk_submodules` skips `_`-prefixed submodules unconditionally
  (`src/venvaxi/_introspect.py:609`), regardless of cache state. It is real behaviour that the
  reproduction depends on - an underscore-prefixed probe reads 'not found' whether the graph is
  stale or fresh - and issue 68's second comment attributes it to
  `specs/behaviors/qualified-name-semantics.md`, which does not contain it. Filed while closing
  this plan; it belongs to neither #49 nor #50. Owned by no current plan.
- **The reproduction has not been re-run on `mpctraj`.** Criteria 6, 7 and 8 are evidenced on the
  `axitestbed` scratch testbed, which reproduces the editable-install mechanism but is not the
  project issue 68 was filed against. A reader wanting the issue's own specimen reconfirmed still
  needs `mpctraj`; the fix is verified, the original report is not re-observed. Owned by no issue.
- **`_resolve_import_name` does not resolve `venv-axi` to `venvaxi`.** The fallback normalises the
  hyphen to `venv_axi`, which is not importable, so this project's own editable self-install cannot
  be queried by its distribution name. `refresh_package_graph` reaches `_resolve_import_name`
  through the same path `_build_store_for` already takes, so it inherits the behaviour rather than
  introducing it: `uv run venvaxi show venv-axi --api` on this tree returns the identical
  ``error: true`` / ``message: Failed to import `venv_axi` (from `venv-axi`)``. Parity with
  existing behaviour, not a regression from this unit - and it is why the reproduction needed a
  testbed whose distribution and import names agree. Not #50's subject either, which is `list`
  visibility. Actionable, owned by no issue.
- **No `Deferred to` entries.** Neither `cache-state-report` (#49) nor
  `installed-package-visibility` (#50) has a plan file, so a deferral could not be absorbed in
  this commit as `plans/README.md` requires. Both items that would have gone to #49 are filed
  against the issue above instead.
