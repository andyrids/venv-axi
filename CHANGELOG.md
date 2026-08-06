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

- `venvaxi` CLI - `list`, `show`, `find`, `tree`, `inspect`, `inherits`, `serve` & `setup`
  commands, plus a bare `venvaxi` home view.
- FastMCP server over STDIO, behind the `venv-axi[mcp]` extra.

### Changed

- Extracted from the `axi` subpackage of
  [`pkgdx`](https://gitlab.com/andyrids/pkgdx) at tag `v0.1.0`, where the code
  originated and its full development history remains.
- CLI surface flattened - `pkgdx axi <command>` becomes `venvaxi <command>`.
- Optional extra renamed - `pkgdx[axi]` becomes `venv-axi[mcp]`.
- Symbol-graph cache relocated - `~/.pkgdx/axi/` becomes `~/.venvaxi/`.
- Ambient context markers renamed - `<!-- pkgdx:axi:begin/end -->` becomes
  `<!-- venvaxi:begin/end -->`. A `venvaxi setup` run migrates the old block
  and the old `.mcp.json` server entry in place.

### Removed

- `rich` runtime dependency - `venv-axi` has no runtime dependencies.
- The `AXIError` exception tier - every `venvaxi` error now derives from
  `venvaxi.exceptions.Error` directly.
