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
