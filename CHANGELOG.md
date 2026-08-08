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

- `ICM/_config/reference-standard-markdown.md` - typographical and stylistic conventions

### Fixed

- `find --package`, `tree`, `show --api`, `inspect` and `inherits` now raise:
  - `PackageNotFoundError` for a package that is not installed.
  - `PackageImportError` for one that is installed but cannot be imported.
- `show <name> --api` raises `InvalidArgumentError` rather than `PackageNotFoundError`.

### Changed

- Project documentation brought into conformance with the markdown standard.
- Spec templates in `ICM/_config/reference-standard-spec.md` now specify sentence-case section.
- The `ICM/create-feature` pipeline now gates on decisions rather than on step completion.
- Workspace acceptance criteria now name approval-carrying-changes as a distinct checkpoint.
- `ICM/_config/reference-toolchain-pymarkdown.md` records a `BadTokenizationError`.

### Fixed

- `inspect`, `show --api` and the MCP symbol tools reported an inherited docstring.
- Cached symbol graphs holding the incorrect docstrings are rebuilt automatically.
- MCP next-step hints named the wrong tool or dropped half an explanation.

## [v0.1.0rc2] - 2026-08-08

### Added

- `venvaxi setup --skill` installs a generic `venvaxi` skill into the consuming repo.
- `specs/` - the permanent behavioural contract for spec-driven development.
- `plans/` - the work-in-flight record, with frontmatter, status lifecycle and closeout ritual.
- `ICM/_config/reference-standard-spec.md` - spec authoring bar and templates.
- `icm-spec` skill, `spec-drift-auditor` agent and the `/audit-spec-drift` command.

### Changed

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
