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

## [v0.1.0] - 2026-08-09

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

## [v0.1.0rc1] - 2026-08-06

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
