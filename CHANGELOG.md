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

## [0.3.0rc1]

### Added

- `specs/commands/setup.md` declares the installed skill a byte-for-byte copy of the packaged one.
- `tests/test_skill_parity.py` fails when the repo skill copy drifts from `src/venvaxi/SKILL.md`.
- `just skill-sync` regenerates `.claude/skills/venvaxi/SKILL.md` through the real installer.
- The packaged skill gains an Invocation section and gotchas for its documented failure modes.
- The skill eval suite grows from 3 to 9 cases, plus a README recording the manual loop.
- An eval case for the `os error 32` sync failure, so the locked-shim misdiagnosis is a
  specimen rather than folklore.

### Changed

- **Breaking for `setup` callers.** `venvaxi setup` registers the MCP server as
  `<python> -P -m venvaxi serve` instead of the `venvaxi` console script. Entries written by
  an earlier version are replaced on the next `setup` run, which reports `.mcp.json` and
  `.vscode` as modified once. Anything reading the registered command out of `.mcp.json`
  sees an interpreter path and a four-element `args` list.
- **Breaking for `setup` callers.** The `AGENTS.md` key in `venvaxi setup` output still reports
  whether the file was modified, but that is now true on *removal* rather than on write. A repo
  last set up by an earlier version reports `AGENTS.md: true` once, then `false`. The key set is
  unchanged.
- **Breaking for `setup` callers.** `venvaxi setup` installs the Skill by default, overwriting
  any existing copy; `--no-skill` opts out and `--skill` remains accepted, now naming the
  default. The `SKILL.md` key reports whether the file was written - false under `--no-skill`
  and when the installed copy already matches the packaged skill byte-for-byte.
- `venvaxi setup` strips a legacy ambient block instead of writing one, preserving every byte
  outside the `<!-- venvaxi:begin -->`/`<!-- venvaxi:end -->` markers and collapsing the
  separator the injection had added. It never creates `AGENTS.md`.
- The packaged Skill states the scan-first requirement as a MUST, the one normative line the
  removed block carried that it did not.
- `.claude/skills/venvaxi/SKILL.md` is generated output, not a hand-maintained dev-facing fork.
- `docs/architecture.md` documents the single-source skill model and drops the stale advice not
  to run `setup --skill` in this repo.
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

### Removed

- The always-on `AGENTS.md` ambient block, and the `src/venvaxi/ambient.md` that sourced it.
  Ambient context is now the Skill plus the MCP registration. The block duplicated the Skill in
  every session of every consuming repo whether or not the task touched a dependency, and
  `specs/mcp/tools.md` already named MCP registration the primary ambient integration.

### Fixed

- A running `venvaxi serve` no longer blocks `uv` from syncing the project on Windows. The
  server held the `venvaxi.exe` console-script shim open, which `uv` must delete whenever it
  reinstalls `venv-axi`, so an otherwise unrelated `uv run` or `uv sync` failed with
  `os error 32` naming a file the caller was not thinking about. It fired only on the runs
  that reinstall. The registered interpreter is not replaced by a package reinstall.
- `install_skill()` writes bytes, so Windows newline translation cannot fork the installed copy.
- Ambient-block edits to `AGENTS.md` read and write bytes, so hand-authored content outside the
  markers is preserved byte-for-byte as `specs/commands/setup.md` requires, on every platform.
  The fix landed on `inject_agents_md()` and carried into the `strip_agents_md()` that replaced
  it before either shipped.
- The repo skill copy no longer names the nonexistent lowercase `src/venvaxi/skill.md` path.
- `tests/test_cli.py` mocked `setup`'s return value with a `skill` key where the implementation
  returns `SKILL.md`, so the guard its own NOTE described - catching a rename of those keys - was
  never armed.
- The CLI reconfigures STDOUT and STDERR to UTF-8 at entry, so a docstring carrying a character
  the ambient pipe encoding cannot represent - box-drawing tables, Greek letters - no longer
  crashes `inspect --docstring` with a `UnicodeEncodeError` and exit 2 (issue 45).

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
