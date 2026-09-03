<!-- pyml disable MD024 -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> [!NOTE]
> Types of changes:
>
> - `Added` for new features.
> - `Changed` for changes in existing functionality.
> - `Deprecated` for soon-to-be removed features.
> - `Removed` for now removed features.
> - `Fixed` for any bug fixes.
> - `Security` in case of vulnerabilities.

## [Unreleased]

### Added

- `venvaxi inherits <qualified_name> --bases` reports the classes a class directly subclasses,
  reading the same `INHERITS` edges in the opposite direction. A base is reported even when its
  own package was never indexed - the edge is written from the subclass's side. A zero count
  is definitive and names its one cause: the class derives directly from `object`, which is
  never indexed. Over MCP the direction is a separate `getBasesTool`, taking the server to
  eleven tools (issue #48).
- `--version` reports the installed version as a single `version: <version>` TOON line and exits
  (issue #81).
- `describeBindingTool` gains a `version` field, reported first, so an MCP-only caller can also
  identify the server's build.
- `pyproject.toml` `classifiers` gain `Operating System :: Microsoft :: Windows` and
  `Operating System :: POSIX :: Linux`, matching the platforms `docs/architecture.md` claims
  support for (issue #111).
- A drift gate over the packaged skill (`tests/test_skill_drift.py`). Tier 1 runs on every
  `pytest`: it introspects the real parser and asserts the Commands table's flags and stated
  defaults against it, in both directions - a flag named that no command accepts and a
  non-global flag accepted that no row names are both failures - then asserts the MCP tool
  table against the registered signatures and the named exit codes against `ExitCode`. A non-zero
  result count stated in prose is a failure in its own right, backticked or not and whether or not
  the span wraps across a line, while `count: 0` and a count inside a fenced output block stay
  legal. Tier 2 runs under `-m conformance` and executes the skill's documented queries against
  real `rich` and `polars`, asserting the property each example teaches rather than equality
  against the recorded block. `inspect numba::njit` is recorded as unexecutable with its reason
  rather than passed over. Row-count checks on both tables, and a triage check over the
  documented queries, stop a parser that matches nothing - or a hand-maintained list that has
  fallen behind the skill - passing vacuously (issue #39).

### Changed

- `specs/behaviors/symbol-graph.md` gains a `Re-exported symbols` subsection declaring the walk's
  re-export filter, which no spec stated before. The declared rules are the ones the walk already
  applied for a normally-named package - `__all__` is trusted at any depth; a class or function
  whose defining module differs is not recorded at an `__all__`-less module below the root,
  because `dir()` cannot tell a deliberate re-export from an incidental import; the package's own
  root module is exempt, because the root is the spelling an agent imports from; and the filter
  tests classes and functions only, so a module-level constant stays its own module's symbol
  whatever module defines its type. Issue
  [#87](https://github.com/andyrids/venv-axi/issues/87) had declared only the private-submodule
  carve-out, leaving `specs/` stating an exception to a rule it never stated.
  `specs/commands/show.md` gains a cross-reference to the new subsection for the module that
  declares no `__all__`. Four characterization tests pin the facts nothing covered, and one class
  of package the newly declared rules were **not** true for is fixed below
  (issue [#106](https://github.com/andyrids/venv-axi/issues/106)).
- The packaged skill gains a `Below the package root, re-exports are not indexed` Gotchas entry,
  and its `Private submodules are not indexed` neighbour is reconciled against it. The rule
  declared above costs an agent a query or a conclusion two ways, both observed against `rich`:
  `inspect rich.align::Measurement` raises even though that file imports the class, with a
  `help[]` naming no recovery; and `inspect rich.align` succeeds with a children listing that
  omits four classes the module binds, which is definitive under
  `specs/behaviors/output-contract.md` Bounded collections and carries no signal that anything
  was dropped. The entry names the move - `find <name> --package <pkg>`, then `inspect` the
  `qualified_name` it returns - and says the two unaffected cases. The private-submodule sentence
  previously read `Symbols a public module re-exports from a private one are indexed, so query
  the facade`, stating the carve-out with no reference to the rule it is a carve-out from; it now
  reads against that rule and names the excluded public-sibling case.
  `.claude/skills/venvaxi/SKILL.md` is regenerated byte-identically. Three drift-gate rows
  execute the entry's queries under `-m conformance`, reading the re-exported names off the live
  module so a `rich` release does not report as skill drift, and the gate's executor gains an
  `except Error` arm mirroring `main()`'s - without it a documented query whose result is a miss
  could not be executed at all
  (issues [#39](https://github.com/andyrids/venv-axi/issues/39),
  [#106](https://github.com/andyrids/venv-axi/issues/106)).
- `venvaxi __main__` gains `build_parser()`, extracted from `main()`. `main()` calls it and is
  otherwise unchanged; the stream reconfiguration stays there, being process setup rather than
  parser construction. Arguments, defaults and every `--help` rendering are byte-identical - the
  extraction exists so the drift gate introspects the real parser rather than a reconstruction
  of it (issue #39).
- The skill's Workflow section names the columns `inherits rich.progress::ProgressColumn`
  reports instead of stating `count: 11`. A figure only one version of `rich` produces cannot be
  asserted without reporting every dependency upgrade as skill drift, and in prose it carries
  nothing the exemplars do not. `count: 0` in prose is unaffected: it is a declared empty state,
  not a measurement (issue #39).
- `rich` is declared in the `dev` dependency group. It was installed only as a transitive
  dependency of `fastmcp`, so a `fastmcp` release dropping it would have turned the conformance
  tier green by removing what it checks (issue #39).
- `specs/behaviors/skill-content.md` gains a What is machine-checked subsection declaring which of
  its content rules have a counterpart in the code: the command table's flags and stated defaults,
  the table's completeness against each command's real flags, the MCP tool table against the
  registered signatures, the exit-code statement against the output contract, and a documented
  query run against the venv the project installs for itself - with three limits that belong to
  the rule, chiefly that an executed check asserts what an example teaches and never equality
  against a recorded block, because a recorded count is what one version of a dependency returned.
  Its Out of scope bullet is narrowed rather than deleted, and states the residue by surface - a
  claim outside those four surfaces - rather than by vocabulary. An earlier wording made it a
  question of which words a claim used, which excluded from the residue the very `getSymbolTool`
  prose it cited to define the residue, and so reinstated the assumption the bullet exists to
  prevent: that a stale prose line was machine-checked. The MCP and exit-code rules are scoped to
  the table and the paragraph the checks read, so a tool or a code named elsewhere is residue and
  says so (issue #39).
- `venvaxi inspect` on a dotted, no-`::` argument that fails to resolve now states, on top of the
  existing message, that the argument was read as a dotted module path and that a symbol lookup
  requires `module::Symbol`. `inspect not.a.symbol` previously named a package the caller never
  typed (`not`), and `inspect rich.console.Console` was indistinguishable from a genuine module
  miss like `inspect rich.nosuchmodule`. Both answers were true, not wrong - the statement makes
  the reading explicit without proposing a corrected spelling. A bare name and a private submodule
  are unaffected: the first has no dropped-separator reading, and the second already carries a
  more specific diagnosis. `_ensure_installed`'s shared message is untouched, so `tree`, `inherits`,
  `find` and `show` report an absent root exactly as before (issue #95).
- The `inherits` empty-state hint for zero *bases* returns to a single cause and offers no
  recovery: the class derives directly from `object`, which is not indexed. It was widened to
  two causes, naming `--refresh` on the class's own package as a recovery, only because a
  refresh could delete a base edge another walk had recorded; that defect is fixed above, so
  the second cause is now false and the recovery could not change the answer.
  `getBasesTool` mirrors the change. The definitiveness is conditional and the condition is
  recorded in `specs/commands/inherits.md`: any change widening what a refresh deletes returns
  there first (issue #124).
- `SCHEMA_VERSION` 8 to 9. No table shape moved - the bump evicts caches holding the result of
  the old deletion scope, which no rebuild of the package a caller happens to refresh can
  repair, and without which the single-cause hint above could assert `object` over an ancestry
  a previous clear had removed. Every cache rebuilds once on first use after upgrade
  (issue #124).
- The `inherits` empty-state hint for zero subclasses now names three causes instead of two -
  subclasses in an unindexed package, subclasses below the built depth, and the query having
  been pointed the wrong way - naming `venvaxi inherits <qualified_name> --bases`
  (`getBasesTool` over MCP) as the recovery for the third, so an agent that wanted the parent is
  no longer sent to index packages that cannot change the answer (issue #48).
- The `mcp` extra's `fastmcp` requirement narrows from `>=0.1.0` to `>=3.4,<4` in all three
  places it was declared - `project.optional-dependencies`, the `dev` dependency group, and the
  type-check hook's `additional_dependencies` in `prek.toml`. The old floor admitted every
  `fastmcp` release ever published, including majors `build_server` cannot call - `TypeError` on
  the exact tool-registration call shape it uses, confirmed against 1.0, 2.0.0 and 2.3.0. This is
  a narrowing of a published requirement: an environment that previously resolved
  `venv-axi[mcp]` to a `fastmcp` below 3.4 is now refused at install rather than handed a package
  it cannot run (issue #96).
- `ICM/_config/reference-toolchain-pytest.md` records the pytest fd-capture trap that defeats a
  `mock.patch` of `sys.stdout`.
- The `pytest` job in `.github/workflows/ci.yml` now runs on a `ubuntu-latest` / `windows-latest`
  matrix with a pinned Python interpreter, so CI exercises the Windows platform the docs claim to
  support (issue #111).
- `.github/workflows/ci.yml` gains a `conformance` job, parallel to `pytest`, running the same
  `ubuntu-latest` / `windows-latest` matrix with `-m conformance`, so the 21-test tier that walks
  real installed dependencies now runs on every pull request instead of never running in CI. A
  specimen guard step fails the job before pytest runs if a specimen is missing, since every
  conformance test skips rather than fails on that condition (issue #112).
- The first job in `.github/workflows/ci.yml` is renamed from `ruff-lint` to `static` and gains a
  third step, `uv run pkgdx-typing-hook -p venvaxi`, so a type-check regression now fails CI
  instead of depending on a contributor's local `prek` hook having run (issue #113).
- The private-submodule skip - a submodule whose own final name segment starts with `_` is never
  walked - is now declared in `specs/behaviors/symbol-graph.md` and cross-referenced from
  `specs/behaviors/qualified-name-semantics.md` and `specs/commands/tree.md`. The behaviour is
  unchanged; only the contract is newly declared (issue #87).
- The packaged skill gains a gotcha for that rule. It was previously unwritable: the skill may
  restate no claim `specs/**` does not declare, so declaring the behaviour is what allowed
  documenting it where an agent meets it (issue #87).

### Fixed

- A package whose own root name starts with `_` (`_pytest`) no longer keeps public-sibling
  re-exports below its root. The re-export filter's private-home carve-out tested
  `any(segment.startswith("_") ...)` over **every** segment of the home module name, including
  the root, while `is_private_submodule` - which exists to encode that same rule - deliberately
  excludes the root segment, because the top-level package is walked directly rather than
  discovered as one of its own submodules. For an `_`-rooted package every same-root home
  therefore satisfied the carve-out, so a class or function re-exported from a **public** sibling
  was recorded at the re-exporting module as well as at its own home - which
  `specs/behaviors/symbol-graph.md` Re-exported symbols says shall not happen, and which reported
  the same symbol twice as public surface. The carve-out now calls `is_private_submodule`, so one
  predicate answers the question everywhere. Measured on `_pytest` (`pytest==9.1.1`): 326 duplicate
  rows removed from a 2986-row graph, none added; `venvaxi show _pytest.cacheprovider --api` drops
  from 27 symbols to 15. A normally-named root is unaffected - the two spellings can only disagree
  when the root segment itself starts with `_`, and `rich`'s graph is byte-identical before and
  after (issue [#106](https://github.com/andyrids/venv-axi/issues/106)). `SCHEMA_VERSION` moves 9
  to 10 - no table shape moved, but the walk now records fewer rows for an `_`-rooted package, and
  a cache built before the fix would otherwise keep serving the 326 duplicate rows indefinitely,
  until the package's version happened to change or a caller passed `--refresh`. Every cache
  rebuilds once on first use after upgrade.
- Refreshing one package no longer deletes another package's recorded inheritance.
  `clear_package` deleted every edge with the cleared package's node at *either* end, but an
  `INHERITS` edge is recorded by the walk of the **subclass's** package - so refreshing a
  *base's* package removed an edge the cleared package never owned and its own rebuild could
  not restore, leaving the subclass in the graph with its node intact and its ancestry silently
  gone. A clear now deletes an edge by its origin endpoint only, which is the endpoint
  ownership rides. An edge can therefore outlive the node at either end; every read either
  joins a symbol record at the endpoint it reports or reports that endpoint's name, so this is
  harmless by construction and now declared as such (issue #124).
- The recorded build `version` is now resolved from the distribution(s) claiming a package's
  import name, not the import name itself. A package whose import name differs from its
  distribution name (`dns`/`dnspython`, `yaml`/PyYAML, `bs4`/beautifulsoup4, ...) recorded `""`
  and could never invalidate on a version change; it now records the real version, a sorted
  `name=version` composite where two or more distributions claim the same import name, or
  `(no distribution)` where none do (issue #89). The cache schema version moves to 8, so any
  cache holding a `""`-recorded row rebuilds once on first query after upgrading.
- A private submodule's answer gave no sign it was private. On `tree` and `inspect` it read
  identically to a name that does not exist; on `show --api` the two were already distinct - a
  nonexistent name raises there - but the hint named `tree <package>`, which answers `count: 0`
  for that identical name, so the offered recovery confirmed the empty answer a second time.
  Every surface now states the module is private and never indexed: `tree` and
  `getModuleTreeTool` before naming the root's own tree (issue #104), `show --api` and
  `showPackageApiTool` while retargeting to the root's own public API (issue #105), and
  `inspect`'s module-mode miss - shared unaltered with `showModuleTool` - in place of merely
  "not found". A top-level package whose own name starts with `_` (`_pytest`) is unaffected;
  only a non-root segment counts.
- The packaged skill's "Private submodules are not indexed" gotcha is corrected to match: it no
  longer claims `tree`'s and `inspect`'s private-submodule answers read the same as a name that
  does not exist, both false the moment the fix above lands.
- `find` no longer misranks a path-shaped query (`Class.method`, `mod::Class`) below symbols it
  only resembles in docstring prose. A `qualified_name` ending with the query, preceded by `.` or
  `::`, now ranks above the kind tier, and a path-shaped query no longer matches a symbol only in
  its docstring - `venvaxi find Console.print --package rich` now emits `count: 3` (`print`,
  `print_json`, `print_exception`) instead of `count: 9` with three unrelated classes ranked first
  through docstring prose. A bare query is unaffected and still matches docstring text as before
  (issue #94).
- `find` now matches `_`, `%` and `\` in a query as the literal characters they are. The `LIKE`
  fallback's match pattern and both backends' name-prefix ranking key take the escaped query with
  an `ESCAPE` clause, so `find print_json` no longer returns `printXjson` for any `X`, nor ranks
  a wildcard-substituted name as a prefix match (issue #108).

## [0.4.0] - 2026-08-23

### Added

- `installed: <m>` on `list` and `listPackagesTool`, a footer count of every distribution the
  active venv holds.
- `venvaxi cache`, reporting this project's cache schema version, database path and size, plus a
  `builds` table of every package with a recorded build.
- `describeBindingTool` extends its report with the same cache summary.
- `refreshPackageGraphTool`, a tenth MCP tool taking a package name and rebuilding that package's
  cached symbol graph.
- `--limit` on `show <package> --api` (and `limit` on `showPackageApiTool`), defaulting to 20.
- A marker-gated conformance test tier that walks real installed dependencies.

### Changed

- The packaged skill's `venvaxi list` row names the `installed` aggregate.
- The packaged skill's CLI command table gains a `venvaxi cache` row.
- `show <package> --api` is now bounded, returning at most 20 rows.
- The rejection of a negative limit now reads `Result limit ... must not be negative`.
- A rebuild requested with no package to scope reports a message.

### Fixed

- `show <package> --api` now reports every public top-level symbol a package declares.
- An attribute whose class its own package defines now reports that class's docstring.
- The cache schema version moves to 7, so every cached graph is rebuilt on first query.
- `find` now searches docstring text on the `LIKE` fallback path, not just `name` and
  `qualified_name`.

## [0.3.2] - 2026-08-22

### Fixed

- A negative `--limit` (CLI) or `limit` (MCP) on `find` now reports `Search limit ... must not be
  negative` and exits 1, instead of defeating the cap and returning the whole symbol graph at
  exit 0 - which over MCP arrived as a transport token-limit refusal rather than a readable
  error. The value is rejected, not clamped, so a caller that computed a bad limit learns that it
  did; `--limit 0` still returns `count: 0` (issue 73).
- Two gotchas in the packaged skill asserted a fact false in the version they named: the dunder
  entry claimed operator signatures reach the class symbol alongside the constructor, and the
  decorator entry pointed to `jit()`'s docstring for `cache`, which in numba 0.67.0 documents
  `inline` but not `cache`. Both entries now state only what reproduces (issue 74).

## [0.3.1] - 2026-08-22

> [!NOTE]
> Promotes `0.3.0rc2` to final with no changes of its own. PyPI's `info.version` (latest stable)
> stayed `0.2.0` while both `0.3.0rc*` were classified as prereleases, so a plain
> `pip install venv-axi` still resolved to `0.2.0` - which crashes `tree numpy` (issue 64) -
> until this release. `0.3.0` was removed from PyPI rather than yanked and can never be
> re-published, so `0.3.1` is the first installable stable release since `0.2.0`.

## [0.3.0rc2] - 2026-08-21

> [!NOTE]
> Supersedes the withdrawn `0.3.0` and contains everything that release did. This section records
> only rc2's own fixes; the release content it carries forward is under `[0.3.0]` below.

### Fixed

- A third-party submodule raising a `BaseException` at import time - `numpy.f2py` raises
  `_pytest.outcomes.Skipped` - no longer crashes `tree` with a traceback and exit 2, and no
  longer drops the whole MCP connection over `getModuleTreeTool`. Import boundaries now guard
  `BaseException`, not `Exception`: a broken submodule is skipped with a warning, a broken
  requested package reports `PackageImportError` and exit 1, third-party `SystemExit` is
  contained, `KeyboardInterrupt` still aborts, and an aborted build releases the cache database
  instead of leaking a locked half-built store (issue 64).
- `show ""` - and any malformed package name in metadata mode - reports `Invalid package name`
  and exits 1, instead of an unhandled `importlib.metadata` traceback and exit 2;
  `showPackageTool` returns the same TOON error block. A malformed requirement string in
  `pyproject.toml` now leaves `list` a skip rather than a failure. The dotted-name answer
  (`metadata mode takes a distribution name`) is unchanged (issue 65).
- `inspect "polars::col"` reports a real signature - or `(signature unavailable)` where
  introspection fails - instead of an empty `signature:`. Signatures are now computed for every
  callable symbol whatever its kind, not only classes and functions; a non-callable attribute's
  empty signature definitively means 'not callable'. The cache schema version is bumped, so
  graphs recorded by an earlier version rebuild themselves on first use - no `--refresh` needed
  (issue 66).
- A `find` result capped at the limit now says so: when the returned count equals the active
  `--limit` (CLI) / `limit` (MCP), a hint states that further matches may exist and names a
  higher limit in the caller's surface spelling. A count below the limit stays definitive and
  carries no such hint (issue 69).

## [0.3.0] - 2026-08-21 [YANKED]

> [!NOTE]
> Removed from PyPI and superseded by `0.3.0rc2`: issue 64 crashes `tree numpy` at an ordinary
> `max_depth` and drops the MCP connection, and issue 66 withholds the signature on the headline
> use case. The section stands as the record of what the withdrawn wheel contains. `0.3.0` will
> never be re-published - PyPI reserves an uploaded filename permanently - and its final release
> is `0.3.1` above.

### Added

- `describeBindingTool`, a ninth MCP tool reporting the project root, venv and status the
  server answers from - a wrongly bound server previously returned plausible wrong-project
  answers with no signal. Degrades to a `(no project root)` marker instead of raising.
- `venvaxi serve` advertises the bound project root and venv in the MCP initialization
  instructions, computed once at startup; an unresolvable root carries the marker and the
  server starts anyway.
- An eval case for the `os error 32` sync failure, so the locked-shim misdiagnosis is a
  specimen rather than folklore.
- A wrong-binding gotcha in the packaged skill, plus an eval specimen for the
  plausible-wrong-answers misdiagnosis.

### Changed

- **Breaking for `setup` callers.** `venvaxi setup` registers the MCP server as
  `<python> -P -m venvaxi serve` instead of the `venvaxi` console script. Entries written by
  an earlier version are replaced on the next `setup` run, which reports `.mcp.json` and
  `.vscode` as modified once. Anything reading the registered command out of `.mcp.json`
  sees an interpreter path and a four-element `args` list.
- **Breaking for `setup` callers.** `venvaxi setup` installs the Skill by default, overwriting
  any existing copy; `--no-skill` opts out and `--skill` remains accepted, now naming the
  default. The `SKILL.md` key reports whether the file was written - false under `--no-skill`
  and when the installed copy already matches the packaged skill byte-for-byte.
- The packaged skill's content is now governed by `specs/behaviors/skill-content.md`. It corrects
  the exit-code contract, which had claimed every error exits `1`: exit `2` now has both its
  causes named and told apart by stdout - an argparse rejection emits no TOON, a venvaxi fault
  emits an `Unexpected error:` block. It also adds gotchas for four observed failure modes
  (`inherits` direction, unindexed dunders, empty namespace accessors, decorator passthroughs),
  makes the case against executing the dependency, flips the `inherits` worked example to a
  populated result, completes the `setup` row's flag list, and points at `specs/principles.md`
  for the measured token figures it used to carry.
- The skill `description` names debugging framings - observed misbehaviour whose cause is a
  signature fact - and the eval suite grows to 10 cases, one framed as a bug report that never
  names `venvaxi`.

### Fixed

- The CLI reconfigures STDOUT and STDERR to UTF-8 at entry, so a docstring carrying a character
  the ambient pipe encoding cannot represent - box-drawing tables, Greek letters - no longer
  crashes `inspect --docstring` with a `UnicodeEncodeError` and exit 2 (issue 45).
- A running `venvaxi serve` no longer blocks `uv` from syncing the project on Windows. The
  server held the `venvaxi.exe` console-script shim open, which `uv` must delete whenever it
  reinstalls `venv-axi`, so an otherwise unrelated `uv run` or `uv sync` failed with
  `os error 32` naming a file the caller was not thinking about. It fired only on the runs
  that reinstall. The registered interpreter is not replaced by a package reinstall.
- MCP tool errors no longer tell the caller to run `venvaxi --help`. Every error from all nine
  tools carried the CLI's generic `help[1]: Run venvaxi --help` footer - a shell command a
  tool-calling agent cannot run. An MCP error now carries an error-specific hint where one
  exists and otherwise omits the `help[N]:` footer entirely; CLI error output is unchanged,
  byte-for-byte, on both error paths.
- **Breaking for `getSymbolTool` callers.** `getSymbolTool` diagnoses a `qualified_name` with
  no `::` before any lookup - the error names the required `module::Symbol` form, the missing
  `::` and `showModuleTool` - instead of answering `Symbol ... not found`, a definitive-sounding
  negative about the package where the real fault was malformed input. Deliberately breaking:
  a no-`::` name that previously resolved as a module by accident (`rich.console`, `rich`) now
  returns the diagnosis instead of the bare module node; `showModuleTool` returns the fuller
  answer for the same spelling.

## [0.3.0rc1] - 2026-08-20

> [!NOTE]
> This section records only what the published `0.3.0rc1` wheel contains. Work merged after the
> `v0.3.0rc1` tag is under `[0.3.0]` above, even where it was drafted while this heading was the
> unreleased one.

### Added

- `specs/commands/setup.md` declares the installed skill a byte-for-byte copy of the packaged one.
- `tests/test_skill_parity.py` fails when the repo skill copy drifts from `src/venvaxi/SKILL.md`.
- `just skill-sync` regenerates `.claude/skills/venvaxi/SKILL.md` through the real installer.
- The packaged skill gains an Invocation section and gotchas for its documented failure modes.
- The skill eval suite grows from 3 to 9 cases, plus a README recording the manual loop.

### Changed

- **Breaking for `setup` callers.** The `AGENTS.md` key in `venvaxi setup` output still reports
  whether the file was modified, but that is now true on *removal* rather than on write. A repo
  last set up by an earlier version reports `AGENTS.md: true` once, then `false`. The key set is
  unchanged.
- `venvaxi setup` strips a legacy ambient block instead of writing one, preserving every byte
  outside the `<!-- venvaxi:begin -->`/`<!-- venvaxi:end -->` markers and collapsing the
  separator the injection had added. It never creates `AGENTS.md`.
- The packaged Skill states the scan-first requirement as a MUST, the one normative line the
  removed block carried that it did not.
- `.claude/skills/venvaxi/SKILL.md` is generated output, not a hand-maintained dev-facing fork.
- `docs/architecture.md` documents the single-source skill model and drops the stale advice not
  to run `setup --skill` in this repo.

### Removed

- The always-on `AGENTS.md` ambient block, and the `src/venvaxi/ambient.md` that sourced it.
  Ambient context is now the Skill plus the MCP registration. The block duplicated the Skill in
  every session of every consuming repo whether or not the task touched a dependency, and
  `specs/mcp/tools.md` already named MCP registration the primary ambient integration.

### Fixed

- `install_skill()` writes bytes, so Windows newline translation cannot fork the installed copy.
- Ambient-block edits to `AGENTS.md` read and write bytes, so hand-authored content outside the
  markers is preserved byte-for-byte as `specs/commands/setup.md` requires, on every platform.
  The fix landed on `inject_agents_md()` and carried into the `strip_agents_md()` that replaced
  it before either shipped.
- The repo skill copy no longer names the nonexistent lowercase `src/venvaxi/skill.md` path.
- `tests/test_cli.py` mocked `setup`'s return value with a `skill` key where the implementation
  returns `SKILL.md`, so the guard its own NOTE described - catching a rename of those keys - was
  never armed.

## [0.2.0] - 2026-08-13

### Added

- `ICM/_config/reference-standard-validation.md` - EARS authoring bar for Validation criteria.
- `specs/behaviors/symbol-graph.md` - the graph's observable state, promoted out of
  `specs/architecture.md`.
- `docs/architecture.md` - the stack, module map and skill-copies note, moved out of `specs/`.

### Changed

- `find` result ordering is declared in `specs/commands/find.md`.
- `specs/principles.md` gives each AXI principle its own heading.
- An empty `list --all` names `pyproject.toml` instead of the `--all` flag just used.
- The `ICM/create-feature` pipeline is split by whether a spec has to move - `ICM/process-plan`
  carries a spec change through closeout, `ICM/express-change` lands the rest in one commit.
- CI runs on a push to `develop` and on a pull request into either branch, no longer on a push to
  `main`.
- The release workflow publishes on a created GitHub Release; the `v*` tag-push trigger is gone.

### Removed

- `specs/architecture.md`, split by kind into `specs/behaviors/symbol-graph.md` and
  `docs/architecture.md`.
- The repo-local `spec-drift-auditor` agent and `icm-spec` skill, now supplied by the
  `icm@icm-spec` plugin as `icm:spec-drift-auditor` and the `icm:*` pipeline skills.
- The `/audit-spec-drift` and `/create-feature` commands; the plugin skills replace them, and
  `/create-feature` named a workspace that no longer exists.

### Fixed

- Truncation size hints name the escape hatch in the caller's own spelling - `--docstring` on the
  CLI, `docstring=true` over MCP.
- `findSymbolTool` empty hint names `include_dev=true`, matching the CLI's `list --all` scope.
- `showPackageApiTool` and `showModuleTool` omit the `help[]` footer under `docstring=true`.
- An empty `listPackagesTool(include_dev=true)` names `pyproject.toml` not the parameter just used.
- A failed `venvaxi setup` write raises `AmbientContextError` and exits `1`, not `2`.
- `plans/pre-release-conformance.md` restored.
- `plans/spec-conformance-sweep.md` follow-ups relabelled in accordance with `plans/README.md`.

## [0.1.0] - 2026-08-09

### Added

- `ICM/_config/reference-standard-markdown.md` - typographical and stylistic conventions
- `venvaxi setup --skill` installs a generic `venvaxi` skill into the consuming repo.
- `specs/` - the permanent behavioural contract for spec-driven development.
- `plans/` - the work-in-flight record, with frontmatter, status lifecycle and closeout ritual.
- `ICM/_config/reference-standard-spec.md` - spec authoring bar and templates.
- `icm-spec` skill, `spec-drift-auditor` agent and the `/audit-spec-drift` command.

### Fixed

- `find --package`, `tree`, `show --api`, `inspect` and `inherits` now raise:
  - `PackageNotFoundError` for a package that is not installed.
  - `PackageImportError` for one that is installed but cannot be imported.
- `show <name> --api` raises `InvalidArgumentError` rather than `PackageNotFoundError`.
- A package argument that cannot possibly name a package (`.foo`, `a b`, `../etc/passwd`) now
  raises `InvalidArgumentError` at exit 1, instead of `Unexpected error` at exit 2 or a
  misleading not-installed answer.
- MCP tools return the CLI's `Unexpected error:` TOON block for a non-`Error` exception instead
  of letting it escape into FastMCP's generic error path.
- `inspect` and `getSymbolTool` resolve a facade-spelled class member
  (`fastmcp::Client.call_tool`) to its home-keyed row instead of reporting it not found;
  the answer keeps the home spelling, the only qualified name the graph holds for a member.
- An empty `tree` result (CLI and MCP) hinted at the package list, which cannot explain a
  missing submodule; both surfaces now name the root package's own tree, and
  `specs/commands/tree.md` states the real cause - a dotted name whose submodule has no node
  in the graph.
- `tree --help` called `package` a distribution name although dotted module names are accepted;
  the help string and the spec's invocation table now say so.
- `inspect`, `show --api` and the MCP symbol tools reported an inherited docstring.
- Cached symbol graphs holding the incorrect docstrings are rebuilt automatically.
- MCP next-step hints named the wrong tool or dropped half an explanation.
- `show <dotted.module> --api` and `showPackageApiTool` build the symbol graph to the named
  module's own depth. The answer no longer depends on which queries ran before, and `--refresh`
  no longer rebuilds too shallow and destroys a deeper cached answer.
- False spec statements corrected before the v0.1.0 freeze: `specs/commands/inherits.md` no
  longer claims sole consumership of home-module resolution,
  `specs/behaviors/package-resolution.md` states the per-command malformed-tail behaviour, and
  `specs/README.md` lists all four `behaviors/` files.

### Changed

- Project documentation brought into conformance with the markdown standard.
- Spec templates in `ICM/_config/reference-standard-spec.md` now specify sentence-case section.
- The `ICM/create-feature` pipeline now gates on decisions rather than on step completion.
- Workspace acceptance criteria now name approval-carrying-changes as a distinct checkpoint.
- `ICM/_config/reference-toolchain-pymarkdown.md` records a `BadTokenizationError`.
- `PACKAGE` and submodule node docstrings route through the shared own-docstring helper.
- MCP server registration key renamed to `VenvAXI` in JSON config.
- ICM `create-feature` pipeline is now spec-driven:
  - Stage 01 emits a spec change and a plan alongside the techspec.
  - Stage 03 checks conformance against the specs a plan names.
  - Stage 04 closes the plan out.
- Verification requirement identifiers now come from a plan Validation checklist.
- `ICM/_config/reference-standard-axi.md` reduced to a pointer; its content moved into `specs/`.

## [0.1.0rc1] - 2026-08-06

### Added

- `venvaxi` CLI - `list`, `show`, `find`, `tree`, `inspect`, `inherits`, `serve` & `setup`
  commands, plus a bare `venvaxi` home view.
- FastMCP server over STDIO, behind the `venv-axi[mcp]` extra.

### Changed

- Extracted from the `axi` subpackage of [`pkgdx`](https://gitlab.com/andyrids/pkgdx).
- CLI surface flattened - `venvaxi <command>`.
- Optional extra - `venv-axi[mcp]`.
- Symbol-graph cache - `~/.pkgdx/axi/` -> `~/.venvaxi/`.
- Ambient context markers - `<!-- venvaxi:begin/end -->`.
- Exceptions now derive from `venvaxi.exceptions.Error`.

### Removed

- Unused `rich` runtime dependency.
- The `AXIError` exception.
