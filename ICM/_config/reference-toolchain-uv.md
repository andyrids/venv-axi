---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [uv, package-management]
---

# Toolchain - `uv`

Astral uv is used to manage this project.

## Commands

The `uv run` command should be used to interface with any installed Python dependency or CLI as this
will activate the project virtual environment if necessary.

The project dependencies can be listed with the `uv pip list` command.

### A locked console-script shim on Windows

If `uv run` or `uv sync` fails with `os error 32` naming `.venv\Scripts\venvaxi.exe`, an MCP
server process is holding the shim open and uv cannot delete it to reinstall `venv-axi`. Nothing
is corrupted - the venv survives and the CLI still works.

It means the registration in `.mcp.json` predates the module form. Stop the server, run
`uv run venvaxi setup` to rewrite the entry as `<python> -P -m venvaxi serve`, and start it
again. An interpreter is not replaced by a package reinstall, so the sync is unobstructed from
then on.

The order matters: `setup` is itself run through `uv`, so a server started from the old entry can
block the very command that fixes it.

## Scripts

Scripts can be read from `stdin`:

```bash
uv run - << 'EOF'
print("hello world!")
EOF
```

When using `uv run` in this project, uv will install `venv-axi` before running the script. If the
script does not depend on `venv-axi`, use the `--no-project` option.

Example script with dependencies added into an inline metadata format:

```bash
uv run - << 'EOF'
# /// script
# dependencies = [
#   "requests",
#   "rich",
# ]
# ///

import requests
from rich.pretty import pprint

resp = requests.get("https://peps.python.org/api/peps.json")
data = resp.json()
pprint([(k, v["title"]) for k, v in data.items()][:10])
EOF
```

NOTE: Any dependencies not included with `venv-axi` must be declared in the script.

## Indexes

`pkgdx` (the canonical-standards dev dependency) is not on PyPI - it resolves from the GitLab
project package registry declared as an explicit `[[tool.uv.index]]` in `pyproject.toml`. The
registry is publicly readable, so no credentials are required.
