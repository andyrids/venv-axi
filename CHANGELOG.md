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

- `installed: <m>` on `list` and `listPackagesTool`, a footer count of every distribution the
  active venv holds, appended after `count:`/the `packages` table (or after `count: 0`) and before
  the `help[]` footer, suppressed when it equals the declared count. `list` answers what a project
  **declares**, which is correct and deliberate, but nothing said the venv held more - in this repo
  the default `venvaxi list` reports a definitive-looking `count: 0` against 100 installed
  distributions, all fully queryable via `show`. The issue measured 95 of 103 installed
  distributions (92%) on `mpctraj` queryable via `show` yet invisible to `list --all`. `installed`
  is a count, never a listing by name - the 'declared, not merely installed' contract is unchanged,
  and resolving *why* a gap exists (declared-transitive versus genuinely unrelated) stays out of
  scope, as does a diagnostic against a project's actual source imports (issue 50).
- `venvaxi cache`, reporting this project's cache schema version, database path and size, plus a
  `builds` table of every package with a recorded build - its built version, built depth and
  current symbol count. Nothing on either surface previously reported what the cache held, only
  what a package's installed metadata said - the only way to detect a stale or dropped cache was
  diffing printed symbol lists by eye, or a file mtime the tool surface never exposed. The read
  never opens the cache through `SymbolStore`, whose `__init__` drops and rebuilds every table on
  a schema-version mismatch as a side effect of merely connecting - proved empirically by hashing
  a stale-schema cache file before and after a read (byte-identical) and, as a failing-first
  demonstration, showing a `SymbolStore`-based read silently reports the freshly-rebuilt current
  version and an emptied `builds` table instead of the stale recorded one. `--refresh` is
  deliberately absent - this is the one command guaranteed never to touch the cache it reports on
  - and the collection is unbounded, matching `list` (issue 49).
- `describeBindingTool` extends its report with the same cache summary, field-for-field, whenever
  `root` resolves - `schema_version`, `db_path`, `db_size_bytes`, `count:` and the `builds` table -
  plus a third hint naming `refreshPackageGraphTool` when `count` is nonzero. An unreadable cache
  degrades rather than raises: `root`/`venv`/`status` still report normally, `schema_version`
  reads `(cache unreadable)`, `db_path`/`db_size_bytes` still report, `count`/`builds` are omitted
  entirely (never `count: 0`), and a third hint names the database path as safe to delete. On
  `venvaxi cache` the cache is the whole answer, so a read failure raises; here it is half of one,
  and `root`/`venv`/`status` cost no file I/O, so withholding them to match a cache-read failure
  would break the one promise this tool exists to keep (issue 49).

- `refreshPackageGraphTool`, a tenth MCP tool taking a package name and rebuilding that package's
  cached symbol graph. A cached graph is invalidated by installed version plus build depth, and an
  editable install edited in place moves neither - so for an ordinary edit-and-verify loop nothing
  on the MCP surface could make an agent's own edits visible, and the CLI's `--refresh` was a shell
  an MCP-driven agent cannot reach. Reproduced against an editable install: a public-named module
  was indexed, then deleted from disk, and all three read tools kept serving it - `getSymbolTool` a
  full signature and docstring, `showModuleTool` a `children` row, `findSymbolTool` `count: 1`. The
  tool reports the resolved import name the graph is keyed by, the build depth recorded and the
  number of symbol nodes recorded, and is a rebuild rather than a cheap precondition to put in
  front of every lookup (issue 68).
- `--limit` on `show <package> --api` (and `limit` on `showPackageApiTool`), defaulting to 20 -
  the same bound `find` carries, so one number covers both collection commands. A count equal to
  the limit carries a hint naming a higher one; below it the count is definitive. `--limit 0`
  returns `count: 0` at exit 0, and a negative value is rejected rather than clamped (issue 67).
- A marker-gated conformance test tier that walks real installed dependencies (`numpy`, `polars`,
  `pydantic`, `fastmcp`) rather than only the hand-written `tests/resources/package/` fixture.
  Every introspection test walked that fixture, so the six defects found by dogfooding `0.3.0`
  failed no test before or after. Excluded from the default run and from CI; opt in with
  `uv run pytest -m conformance` (issue 71).

### Changed

- The packaged skill's `venvaxi list` row names the `installed` aggregate instead of restating
  'Declared, installed venv packages' - phrasing that predates the aggregate and undersold it - and
  a new gotcha names `installed`, not `count:`, as the way to tell whether more is queryable than
  `list` declares, before concluding a package "isn't available" (issue 50).
- The packaged skill's CLI command table gains a `venvaxi cache` row, its MCP tool prose states
  `describeBindingTool`'s cache-summary fields and the unreadable-cache degrade shape, and the
  wrongly-bound-server gotcha gains a sentence naming `describeBindingTool` as the way to check a
  suspected-stale graph without paying for a rebuild (issue 49).
- `show <package> --api` is now bounded, returning at most 20 rows where it previously emitted a
  package's entire public surface. `show numpy --api --docstring` went from 1,023,453 bytes to
  34,245 - over MCP the unbounded call was refused outright by the token-limit guard, and the
  truncated view's own footer suggested it as the next step. That footer now names a higher
  `--limit` when the count is capped (issue 67).
- The rejection of a negative limit now reads `Result limit ... must not be negative` rather than
  `Search limit ...`. The guard is shared by `find` and `show --api`, and only one of those is a
  search (issue 67).
- A rebuild requested with no package to scope it now reports `A rebuild must name the package to
  rebuild`. The old wording named the `--refresh` and `--package` flag spellings, but the guard
  sits on the shared path both surfaces reach, so it was the last message still spelled for the
  CLI alone. It was also the message `specs/mcp/tools.md` held a documented Known exception for;
  that exception is now discharged (issue 68).
- The packaged skill describes the ten-tool surface. Its MCP tool table carries a
  `refreshPackageGraphTool` row, the *Notable CLI differences* entry narrows to 'No *read* tool
  takes a `refresh` parameter' with the new tool as the single named exception, the `find` gotcha
  quotes the rejection message the code now raises, and the rebuild gotcha names the MCP route
  beside `--refresh` - it previously told an MCP-driven agent that a stale graph can only be
  rebuilt from a shell it cannot reach. That entry also now states the cost of a rebuild: it is
  package-scoped and walks to the default depth, so a graph built deeper is reset with it, and
  `inherits` is the one query that does not deepen it again on demand (issue 68).

### Fixed

- `show <package> --api` now reports every public top-level symbol a package declares, not only
  its classes and functions. Every export that is an attribute - a module-level instance, a
  namespace object, a constant - was dropped after the walk had already recorded it, so
  `show pytest --api` answered `count: 77` against an 88-entry `__all__` and stated, with the
  definitiveness a count below the limit carries, that `pytest.skip` does not exist. Submodules
  stay excluded; nested module structure is `tree`'s job (issue 82).
- An attribute whose class its own package defines now reports that class's docstring instead of
  `(no docstring)`. `inspect pytest::fail --docstring` returned the empty marker while the real
  docstring sat on `_pytest.outcomes._Fail`. A type from the standard library is still not
  treated as documentation for a value - `version_tuple` does not report *Built-in immutable
  sequence* (issue 82).
- The cache schema version moves to 7, so every cached graph is rebuilt on first query after
  upgrade. The docstring change above is recorded at walk time and frozen into the store, and
  neither the distribution version nor the build depth moves for a change like it (issue 82).
- `find` now searches docstring text on the `LIKE` fallback path, not just `name` and
  `qualified_name`. On a SQLite build without FTS5 a query matching only a docstring returned
  `count: 0` - which the issue-69 contract makes a definitive answer, so the narrowing read as
  'no such symbol' rather than 'docstrings were not searched'. Both fallback sites log at debug
  level, so nothing in the output distinguished the two. Measured against the 0.3.2 store, ten
  docstring-only terms reached 8,538 distinct symbols through FTS5 and none through the fallback
  (issue 79).

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
