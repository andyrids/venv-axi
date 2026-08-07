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

## [v0.1.0rc2]

### Changed

- MCP server registration key renamed to `VenvAXI` in JSON config.

## [v0.1.0rc1]

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
- Exceptions now derive from `venvaxi.exceptions.Error`

### Removed

- Unused `rich` runtime dependency.
- The `AXIError` exception.
