---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [mcp, tools, parity]
---

# MCP: Tools

The MCP surface exposed by `venvaxi serve`, under server name `VenvAXI`.

This file consolidates all ten tools as a deliberate exception to the one-file-per-unit rule in
`ICM/_config/reference-standard-spec.md`. Eight of them mirror a CLI command whose behaviour is
already specified in `specs/commands/`; splitting this file that many ways would duplicate those
specs as many times over, which the same standard warns against.

Two are exceptions to the exception, and both declare their behaviour here in full rather than in
`specs/commands/`. `describeBindingTool` mirrors no CLI command at all.
`refreshPackageGraphTool` mirrors a CLI **flag** rather than a command - `--refresh` is a modifier
five commands accept, and there is no `venvaxi refresh` for it to mirror. Both are divergences,
and both are enumerated below with the others.

## Contract

Tool functions are defined in snake_case and **registered in camelCase**
(`get_module_tree_tool` -> `getModuleTreeTool`). The registered name is the contract; renaming a
Python function renames an MCP tool.

Every tool shall return **TOON text**, not JSON, and shall mirror the CLI's
[output contract](../behaviors/output-contract.md): `count:` aggregates, definitive empty states
(including the `(no docstring)` marker), truncation at 200 characters, and a `help[]` footer.

If an `Error` is raised inside a tool, then the tool shall catch it and return the TOON error
object the CLI emits - without the CLI's generic `venvaxi --help` footer, per the
surface-addressed [error shape](../behaviors/output-contract.md#error-shape). It shall not
escape into FastMCP's generic error path, which would present a different failure shape to the
agent depending on which surface it happened to be using. If an error carries no error-specific
hint, then the `help[N]:` footer shall be omitted entirely, never padded with a generic
substitute.

**No exception escapes**, not just no `Error`. If an unexpected exception is raised, then the
tool shall catch it at the same boundary, return the `Unexpected error:` block the CLI renders,
and log it to STDERR with its traceback. Catching only `Error` leaves the surfaces divergent in
exactly the case where the agent has least to go on - the CLI reports a fault it can read, the
MCP caller gets a transport error carrying no TOON at all.

'Exception' means `BaseException` here, exactly as the
[error shape](../behaviors/output-contract.md#error-shape) defines it for the CLI entry point,
and the stakes are higher on this surface: an escaping `BaseException` does not merely fail the
call, it drops the whole MCP connection, taking every other tool down with it. A third-party
import can raise one straight through a tool - see
[Import boundaries](../behaviors/output-contract.md#import-boundaries) - so the tool boundary
shall catch `BaseException`, re-raising only `KeyboardInterrupt` and `SystemExit`.

## Tools

| Tool                  | Parameters                          | CLI equivalent            |
| --------------------- | ----------------------------------- | ------------------------- |
| `describeBindingTool` | none                                | none - see below          |
| `listPackagesTool`    | `include_dev=False`                 | `list [--all]`            |
| `showPackageTool`     | `name`                              | `show <package>`          |
| `showPackageApiTool`  | `name`, `docstring=False`, `limit=20` | `show <package> --api`  |
| `showModuleTool`      | `name`, `docstring=False`           | `inspect <module>`        |
| `getSymbolTool`       | `qualified_name`, `docstring=False` | `inspect <symbol>`        |
| `findSymbolTool`      | `query`, `limit=20`, `package=None` | `find <query>`            |
| `getInheritorsTool`   | `qualified_name`                    | `inherits <name>`         |
| `getModuleTreeTool`   | `name`, `max_depth=2`               | `tree <package>`          |
| `refreshPackageGraphTool` | `name`                          | `--refresh` - see below   |

## The binding report

`describeBindingTool` answers which project and which venv this server speaks for. It takes no
parameters, because every input it could take is a thing the caller is asking the server to tell
*it*.

### Why the surface needs it

A connected agent cannot see the server's argv or its working directory, so every other tool on
this surface returns well-formed, plausible results without disclosing what they are results
*about*. The failure is silent: signatures from an unintended venv are indistinguishable from
correct ones, which is the exact staleness the AXI exists to eliminate. The CLI has no equivalent
gap - a caller runs `venvaxi` from a directory it chose, with the venv on its own `PATH`.

### The binding is two axes

The tool shall report both, because they resolve independently and can disagree:

- **venv** - the `sys.prefix` of the interpreter serving this process, which decides what is
  importable and therefore what every symbol answer is drawn from.
- **root** - the consuming project root, resolved as in
  [Cache and refresh](../behaviors/cache-refresh.md#project-root-resolution), which decides which
  `pyproject.toml` declares the dependencies `listPackagesTool` answers with, and which keys the
  symbol cache.

Reporting only the venv would leave a server answering one project's declared dependencies against
another project's installed packages, with the mismatch still invisible.

### Outputs

The `describeBindingTool` shall emit a flat TOON object of `version`, `root`, `venv` and `status`,
followed by a `help[]` footer. `version` comes first because the server identifies itself before
naming the binding it speaks for - a caller comparing two servers' answers reads which build
answered before which project it answered about.

Both paths are rendered `~/`-prefixed when under the home directory, else absolute, matching
[the home view](../commands/home.md).

`status` is `active` when `sys.prefix != sys.base_prefix`, else `inactive` - the same computation
the home view makes, but not the same signal. A server registered by `setup` runs the venv's own
interpreter, so `inactive` over MCP means the registered command names a base interpreter and the
symbol answers are being drawn from an environment the project never installed into.

### Cache summary

When `root` resolves, `describeBindingTool` shall also report the state of this project's cached
symbol graph, extending the object above with `schema_version`, `db_path` and `db_size_bytes`, then
`count: <n>` and a `builds` table of `package`, `version`, `depth`, `symbols` - field for field the
same shape [`venvaxi cache`](../commands/cache.md) reports, read the same way: directly, without
opening the graph-build path that would rebuild a schema-mismatched cache as a side effect of
inspecting it. See [`venvaxi cache`](../commands/cache.md#data-requirements) for what each field
means and how the two empty states it shares with this tool - no cache built yet, and a cache
built but empty - stay distinguishable. This tool alone carries a third state - the cache database
could not be read at all - specified under [Failure modes](#failure-modes) below, since
`venvaxi cache` answers that same trigger by raising rather than by reporting a state.

This closes the gap [#49](https://github.com/andyrids/venv-axi/issues/49) raised: an MCP-only
caller had no remedy and no diagnosis for a suspected-stale graph, because refresh reaches this
surface only through [`refreshPackageGraphTool`](#the-refresh-tool), and nothing reported what the
graph held before a rebuild was spent finding out. [Out of scope](#out-of-scope) below draws the
line between the two.

The `builds` table carries no row bound, for the same reason
[`venvaxi cache`](../commands/cache.md#out-of-scope) does not: a project's cache holds one row per
package a query has actually touched, which stays small in practice without needing a ceiling.

When `count` is nonzero, the tool shall append a third hint naming
[`refreshPackageGraphTool`](#the-refresh-tool) as the way to rebuild a package whose recorded build
looks stale. This is additional to, not a replacement for, the two onboarding hints under
[Outputs](#outputs) above. When `count` is zero, no third hint is added - both onboarding hints
already name the way to populate a first entry.

### Failure modes

`version` is resolved before either degrade below and is unaffected by both: it is a fact about
the server itself, not about the project or venv it is bound to. If package metadata is
unavailable - an uninstalled source checkout, for example - then `describeBindingTool` shall
report `version: (no version metadata)` on every path, including the no-root and unreadable-cache
degrades - the same definitive-empty-state marker
[the home view](../commands/home.md#failure-modes) reports for the identical trigger.

This tool shall answer in a broken or uninitialized project, because a caller reaching for it has
most likely already been given an answer it distrusts.

If no project root resolves, then the `describeBindingTool` shall report `root: (no project root)`,
emit the remaining fields, and return no error block. The marker is a definitive empty state under
[Output contract](../behaviors/output-contract.md#definitive-empty-states) - it states that no
`pyproject.toml` was found from the working directory upward nor beside the venv, which is a fact
about the binding and precisely what the caller asked for.

That state is not exotic. It is close to diagnostic of an ephemeral or tool-venv registration - a
`uvx`-installed interpreter lives outside any project, while a conventional in-project `.venv` has
the project root as its parent and resolves. The hint shall therefore name the registration as the
thing to check, phrased for the MCP caller per [Hint wording](#hint-wording).

Without a resolved `root` there is no project to key a cache to, so the degrade shall omit the
[cache summary](#cache-summary) entirely rather than reporting a marker for it - there is nothing
truthful to say about a cache belonging to no project.

If the cache database exists but cannot be read due to a SQLite-level failure, then the tool shall
degrade the cache half of the object rather than raise. `root`, `venv` and `status` are emitted
exactly as on a healthy read - they cost no file I/O into the cache and a cache fault is no reason
to withhold them. `schema_version` shall be reported as `(cache unreadable)`. `db_path` and
`db_size_bytes` shall still be reported: both are filesystem facts about the database file, not its
contents, so they stay knowable when the contents cannot be read, and a caller wanting to delete
the offending file needs the path regardless of why it could not be opened. `count` and the
`builds` table shall be omitted entirely.

The tool shall **not** report `count: 0` here. `count: 0` is the positive claim that the database
opened cleanly and recorded no builds - the state [Cache summary](#cache-summary) already reserves
for a real, empty database. Reusing it for 'could not be read at all' would collapse two different
facts into one marker, which is the same
[Principle 5](../principles.md#principle-5-definitive-empty-states) trap 'never built' and 'built
but empty' are already kept apart from - a third state, 'could not ask', needs its own marker
rather than borrowing either existing one.

The tool shall append a third hint naming the reported `db_path` as safe to delete - it is
disposable derived data, per [Cache and refresh](../behaviors/cache-refresh.md#cache-identity) -
after which the next command that touches the cache creates a fresh one, the same bootstrap every
project's first query already performs.

[`venvaxi cache`](../commands/cache.md#failure-modes) makes the opposite choice on the identical
trigger, deliberately: there the cache **is** the whole answer, so a read that cannot produce it
fails honestly. Here the cache summary is only half the object - `root`, `venv` and `status` are
the other half, and they are exactly what a caller already distrusting its binding needs most.
Withholding them to match `venvaxi cache`'s raise would break the one promise this tool exists to
keep: answering in a broken or uninitialized project.

Each degrade is scoped to its own trigger, and neither absorbs a failure outside it. If resolving
the root raises anything other than a failure to find one, then the tool shall return the
`Unexpected error:` block like any other tool - widening that catch would convert a genuine fault,
an unreadable or deleted working directory, into a confident report that the project simply does
not exist. Likewise, once `root` resolves, only a SQLite-level failure reading the cache degrades
the cache summary; any other exception raised while reading it still returns the
`Unexpected error:` block.

**This tool degrades where the other nine raise**, for the identical unresolvable-root state. That
is deliberate and MUST be preserved: for the other nine an unresolvable root means the answer
cannot be computed, and for this one it *is* the answer. Harmonizing the two would either silence
the nine or break the one that has to work when nothing else does.

### The description is part of the contract

The registered tool description is the only channel that reaches an agent without a tool call -
`venvaxi setup` registers the server as the primary ambient integration, and the harness keeps
tool descriptions in context. The `describeBindingTool` description shall state that it identifies
the project and venv the server answers from, and that it is the tool to call first.

It shall also state that the report includes a summary of the cached symbol graph - schema
version, on-disk size, and which packages are indexed at which built version and depth - so an
agent holding a suspected-stale answer knows this is the tool that can confirm or rule it out
without paying for a rebuild.

It shall also state that the report includes venvaxi's own version, since `version` is the field
the report leads with.

A description that merely names the return shape wastes the one ambient slot this surface has, and
leaves the tool discoverable only by an agent that already suspects the problem it exists to
reveal.

## The refresh tool

`refreshPackageGraphTool` rebuilds one package's cached symbol graph, exactly as
[Rebuild](../behaviors/cache-refresh.md#rebuild) specifies a rebuild. The package to rebuild is a
required input, per
[Rebuild scope and depth](../behaviors/cache-refresh.md#rebuild-scope-and-depth); there is no
unscoped 'refresh everything' form on either surface.

### Why the surface needs a rebuild

The cache is invalidated by installed version plus build depth
([Validity](../behaviors/cache-refresh.md#validity)), and an editable install edited in place
moves neither. Every read tool then answers from the graph as last built, with no signal that it
is stale.

The failure is not confined to an outdated docstring. A symbol whose source file has been deleted
outright is still served with a complete, plausible signature and docstring, and the search tools
still count it - a fully-formed answer about something that no longer exists anywhere in the
project. That is the drift
[Report what a symbol is](../principles.md#report-what-a-symbol-is-not-how-to-use-it) exists to
prevent, arriving through the cache instead of through recall, and an agent has nothing on this
surface to distinguish it from a correct answer.

Nothing in the server holds the cache open - each call opens and closes its own connection - so a
rebuild started anywhere is visible to the next tool call, with no restart. The gap this tool
closes is only that no tool could start one, while `venvaxi setup` registers this surface as the
primary ambient integration and the agent is told to work through it.

### The rebuild receipt

The `refreshPackageGraphTool` shall emit a flat TOON object recording the rebuild it performed,
followed by a `help[]` footer:

- `package` - the resolved import name whose graph was rebuilt. It is not always the name the
  caller supplied - a distribution name resolves to an import name - and the caller needs the
  spelling the graph is keyed by to phrase its next query.
- `depth` - the build depth this rebuild recorded, which is the depth the walk was permitted to
  reach rather than the nesting it happened to find, so the depth reset in
  [Rebuild scope and depth](../behaviors/cache-refresh.md#rebuild-scope-and-depth) is visible
  rather than silent. It is the value later queries are tested against under
  [Validity](../behaviors/cache-refresh.md#validity).
- `symbols` - the number of symbol nodes this rebuild recorded, which is what distinguishes a
  rebuild that produced a graph from one that walked almost nothing.

The symbol count shall **not** be emitted as a leading `count:` line.
[Aggregates](../behaviors/output-contract.md#aggregates) puts `count:` in front of a collection so
a caller can decide whether to page or refine; this tool returns no collection, and a leading
`count:` would promise rows that never arrive.

Three clauses of the [output contract](../behaviors/output-contract.md) reach nothing here, which
is a fact about this tool rather than an exemption from the contract:

- **Definitive empty states.** There is no empty result to mark. A rebuild either completes and is
  reported, or raises; the object is emitted on every completing call, so nothing is left silent.
- **Truncation.** No docstring or free text is returned, so the 200-character limit reaches
  nothing.
- **Bounded collections.** There is no collection to bound, so this tool carries no row bound and
  no capped-count hint.

The footer shall name the tool that searches the rebuilt graph, carrying the package scope, so the
caller's next step lands in the graph just rebuilt rather than across every indexed package - the
scope-equivalence obligation in [Hint wording](#hint-wording).

### Refresh failure modes

This tool raises where `describeBindingTool` degrades, including for the identical
unresolvable-root state: without a project root there is no cache to key, so the rebuild cannot be
performed at all.

- If no project root resolves, then the `refreshPackageGraphTool` shall return the TOON error
  block.
- If `name` is not a possible package name, then the `refreshPackageGraphTool` shall return the
  TOON error block.
- If `name` names a package not installed in the venv, then the `refreshPackageGraphTool` shall
  return the TOON error block.
- If the named package cannot be imported, then the `refreshPackageGraphTool` shall return the
  TOON error block.
- If a submodule raises at import time during the walk, then the rebuild shall skip that submodule
  and complete, per
  [Import boundaries](../behaviors/output-contract.md#import-boundaries). One unimportable
  submodule is not a failed refresh.
- If the rebuild raises after the package's existing nodes have been cleared, then the
  `refreshPackageGraphTool` shall return the TOON error block and the package shall be left
  unindexed rather than half-built, so the next query for it rebuilds. This is
  [Rebuild](../behaviors/cache-refresh.md#rebuild) observed from this surface: a failed refresh
  costs the cached graph, and that is the safe direction to fail in.
- If a SQLite-level failure occurs during the rebuild, then the `refreshPackageGraphTool` shall
  return the TOON error block.

None of these carries a `help[N]:` footer. No error above leaves a next step this surface can name
beyond what the message already says, and the
[error shape](../behaviors/output-contract.md#error-shape) omits the footer entirely rather than
padding it.

### The refresh description is part of the contract

The registered description carries the weight it does for
[`describeBindingTool`](#the-description-is-part-of-the-contract), for a sharper reason. Staleness
is silent, so an agent never forms the suspicion that would send it looking for this tool. A
description that does not say when to call it will not be read at the moment it is worth anything.

The `refreshPackageGraphTool` description shall state what it rebuilds, name the situation calling
for it - source changed with no reinstall, which no other tool on this surface can detect - and
mark it as a rebuild rather than a read.

The last clause is not padding. A rebuild imports and walks a package's modules, and a description
reading like a cheap precondition invites an agent to prefix every lookup with it - the cost the
[refresh divergence](#divergences-from-the-cli) was withholding the capability to avoid.

## Divergences from the CLI

These are deliberate and MUST be preserved:

- **`describeBindingTool` mirrors no CLI command.** It is the only tool on this surface with no CLI
  counterpart of any shape - `refreshPackageGraphTool` at least mirrors a flag. The
  nearest CLI relative is the bare `venvaxi` [home view](../commands/home.md), and it is a relative
  rather than an equivalent: home reports `bin`, `venv` and `status` and deliberately never
  resolves the project root, while this tool reports `root` and omits `bin`. Neither surface is
  wrong. `bin` identifies the invocation on a CLI where the caller supplied it and can act on it;
  over MCP it names the `__main__.py` inside the venv already reported, so it restates `venv` less
  directly. `root` is the reverse - a CLI caller knows the directory they are standing in, and an
  MCP caller controls neither the spawn directory nor the interpreter.

  The [cache summary](#cache-summary) [#49](https://github.com/andyrids/venv-axi/issues/49) added
  was the first exception to 'no CLI counterpart of any shape'; `version`
  ([#81](https://github.com/andyrids/venv-axi/issues/81)) is the second - it mirrors the CLI's
  `--version` line exactly, resolved once and reported first, ahead of `root`. This tool now
  carries three different relationships to the CLI at once: a genuine equivalent for the version
  field, a genuine equivalent for the half describing the cache, and no equivalent at all for the
  half describing the binding (`root`, `venv`, `status`).
- **No `refresh` parameter on any read tool.** The nine read tools answer from the cache and take
  no `refresh` parameter; refresh reaches this surface only through the dedicated
  [`refreshPackageGraphTool`](#the-refresh-tool). The reason the parameter was refused still
  holds - forcing a rebuild is an explicit, potentially slow operation - and the dedicated tool is
  what keeps it explicitly invoked. A `refresh` parameter on nine schemas makes a slow rebuild
  reachable by setting a flag on a read, and it would then be set by whichever caller guessed it
  should be; one named tool cannot be reached by accident.
- **`inspect` is split into two tools.** The CLI dispatches on whether the argument contains
  `::`; MCP exposes `getSymbolTool` and `showModuleTool` separately, because a typed tool schema
  should not hide two different return shapes behind one parameter. The split's malformed-input
  diagnosis is specified in [Malformed qualified names](#malformed-qualified-names).
- **`show` is split into two tools** for the same reason - `showPackageTool` (metadata) and
  `showPackageApiTool` (API), rather than a boolean `--api` switch.
- **`showPackageTool` returns fixed fields** (`name`, `version`, `location`); there is no
  `--fields` equivalent.

Footer suppression under `docstring=true` is **not** on this list. `getSymbolTool`,
`showPackageApiTool` and `showModuleTool` shall each suppress the `docstring` hint when
`docstring` is set, and shall omit the `help[]` footer entirely where that leaves no hint to
emit - which is exactly what `inspect --docstring` and `show --api --docstring` do - parity, and
already required of both surfaces by the suppression rule in
[Output contract](../behaviors/output-contract.md#contextual-disclosure). It was listed here once
as a `getSymbolTool` divergence; it never was one, and listing parity as divergence is as
misleading as omitting a real one.

What is suppressed is **that hint, not the footer**. A hint naming a step the caller has not
taken survives `docstring=true`: a capped `showPackageApiTool` result carries its bounded-results
hint under
[Bounded collections](../behaviors/output-contract.md#bounded-collections) whether or not
docstrings were asked for, because the two answer different questions - one widens each row, the
other lifts the bound on rows. Suppressing it would return twenty of a package's several hundred
symbols with no signal that the answer was capped, which is the confidently-wrong truncated
result the bound exists to prevent.

## Malformed qualified names

The `inspect` split above leaves `getSymbolTool` symbol-only, so the commonest spelling mistake -
a fully-dotted name where `module::Symbol` was meant - cannot fall through to a module lookup as
it does on the CLI. Answered as a plain symbol miss, `Symbol ... not found` reads as a definitive
negative about the package rather than a malformed-input diagnosis, and an agent that believes it
stops looking for a symbol it had correctly named.

- If `qualified_name` contains no `::`, then `getSymbolTool` shall return the TOON error block
  with a message that diagnoses the input: the tool requires a `module::Symbol` name, the given
  name carries no `::`, and `showModuleTool` is the tool for module lookups. It shall not report
  a bare symbol miss.
- The diagnosis applies before any lookup. If a no-`::` name would resolve as a module, then
  `getSymbolTool` shall still return the diagnosis rather than the module's node - a module
  answer from the symbol tool is exactly the two-shapes-behind-one-parameter collapse the split
  exists to prevent, and `showModuleTool` gives the fuller answer for the same spelling.
- The tool references in the message are next-step hints and take every
  [Hint wording](#hint-wording) rule, including derivation of the camelCase names.

The tool shall not fall back to a module lookup; the split is a deliberate divergence above and
MUST be preserved.

## Hint wording

Empty-state and next-step hints shall be phrased for the MCP caller - 'Call `getSymbolTool` ...',
not 'Run `venvaxi inspect` ...'. A hint naming a shell command is useless to a tool-calling
agent, and mixing the two teaches the wrong invocation surface.

Hints shall reference other tools by deriving the camelCase name from the function, so a rename
cannot leave a stale hint pointing at a tool that no longer exists.

A hint shall name the tool that performs the action its sentence describes. Deriving the name
correctly from the wrong function passes the rule above and still misdirects the caller.

Where a hint mirrors a CLI hint, it shall carry the parameters that make the two **equivalent in
scope**, not merely equivalent in tool. Naming the right tool with the wrong default sends the two
surfaces to differently-scoped answers for the same recovery, which is the harder failure to see -
the caller gets a plausible result and no signal that it was narrower than the one the CLI would
have given.

Truncation suffixes carry the same obligation as footers, and are specified with the truncation
rule in [Output contract](../behaviors/output-contract.md#truncation).

## Error message wording

The [error shape](../behaviors/output-contract.md#error-shape) governs the block; this rule
governs the sentence inside it.

A message raised by logic shared with the CLI reaches both surfaces unaltered, so it shall name
the input it rejects in a spelling that is true on both - the thing being rejected, not the flag
or the parameter that carried it. `--limit` names nothing a tool caller can set and `limit=`
names nothing a shell caller can type, so a message picking either one misdirects half its
readers, and it misdirects them while they are already recovering from an error.

The same obligation runs across **commands**, not only surfaces. A message on a path shared by
more than one command shall name the input in a spelling true of every command that reaches it: a
rejection raised by both `find` and `show --api` cannot call the value a *search* limit, because
one of the two is not a search. This is the same rule, not a second one - when it was written
there was a single bounded command, so its examples are all about surfaces.

Hints keep the opposite rule, always spelled for the surface, per
[Hint wording](#hint-wording): a hint names a next action, and a next action exists on one
surface at a time, whereas a message names a fact about the input and that fact is the same on
both. Where a message genuinely can only be phrased for one surface, it belongs at that
surface's boundary rather than in the shared path.

- If `findSymbolTool` or `showPackageApiTool` is called with a negative `limit`, then it shall
  return the TOON error block, carrying neither the CLI footer nor a CLI flag spelling. The
  rejection is
  [Bounded collections](../behaviors/output-contract.md#bounded-collections)'; this surface
  inherits it, which is parity rather than a divergence.
- If a rebuild is requested with no package to scope it, then the rejection message shall name the
  missing package scope rather than the flags that spell it on the CLI. The rejection sits on the
  path both surfaces share, and `--refresh` and `--package` name nothing a tool caller can set.

One rejection, written once on the shared path, is the point. Each surface that re-implements a
bound is a place for the two to drift, and a bound written twice is a bound that will be raised
once.

Moving the unscoped-rebuild rejection to the CLI boundary would also satisfy this section's
one-surface escape hatch, and is deliberately not taken. The guard on the shared path is what
stops a rebuild request carrying no scope from being silently ignored, and a guard existing at one
surface only is a guard the other surface does not have.

## Out of scope

- **MCP resources and prompts** - the surface is tools only; no resource or prompt is served.
  No future spec is planned.
- **Repo-mutating and lifecycle tools** - `setup` and `serve` remain CLI-only. Never - an MCP tool
  that mutates the consuming repo would run without the explicit invocation
  [principle 7, ambient context](../principles.md#principle-7-ambient-context) requires.
  [`refreshPackageGraphTool`](#the-refresh-tool) is not an exception to this Never, and the
  distinction has to be stated or it lands looking like one. What it mutates is the symbol cache:
  disposable derived data, living outside the consuming repo, safe to delete at any moment and
  rebuilt by the next query that needs it
  ([Cache and refresh](../behaviors/cache-refresh.md#cache-identity)). The rebuild is idempotent,
  as [Non-interactive](../behaviors/output-contract.md#non-interactive) requires of any mutation,
  and it writes nothing the project owns. Principle 7 guards against a tool changing the caller's
  work without the caller choosing it; a rebuilt cache changes only how current the same answer
  is.
- **A staleness signal on every read answer.** [#49](https://github.com/andyrids/venv-axi/issues/49)
  settled where a cache summary lands: `describeBindingTool`'s [Cache summary](#cache-summary),
  reporting schema version, on-disk size, and each indexed package's built version, depth and
  symbol count - the diagnostic gap the issue raised, closed without adding an eleventh tool. What
  stays out of scope is the wider question: no *other* tool's read answer carries an inline
  staleness annotation of its own. The cache summary is checked separately, on the one tool built
  for it, rather than folded into every symbol answer - which would put the same fact in ten
  places instead of one.
  [`refreshPackageGraphTool`](#the-refresh-tool) answers neither question, and the line between it
  and the cache summary is drawn deliberately because it is thin. It reports the outcome of a
  rebuild it has just performed, for the one package it was given; it is silent about every other
  package, and it reports nothing at all unless a rebuild was asked for. 'What does the graph
  currently hold?' is a question a caller must be able to ask without mutating anything, and
  answering it by rebuilding is the most expensive possible reading of it. That the refresh receipt
  names a depth and a symbol count does not make it a cache summary - those are facts about the
  walk that just ran, not about the graph as the caller found it before asking.
- **Cache eviction** - not this tool's job. See
  [Cache and refresh](../behaviors/cache-refresh.md#out-of-scope) Out of scope.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 9, contextual disclosure](../principles.md#principle-9-contextual-disclosure)
  - it applies to the MCP
  surface too. `venvaxi setup` registers MCP as the primary ambient integration, so an
  MCP-driven agent MUST see the same quality of next-step hints a CLI-driven one does.

**Local**:

- **Behavioural parity with the CLI is the default; every divergence is listed above.** Two
  surfaces over one symbol graph will drift unless divergence is enumerated rather than
  discovered. A new CLI capability MUST either gain an MCP tool or gain an entry in
  [Divergences](#divergences-from-the-cli) explaining why not.
