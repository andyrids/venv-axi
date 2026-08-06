[unix]
set shell := ["bash", "-euo", "pipefail", "-c"]

[windows]
set shell := ["cmd.exe", "/c"]

[default]
@_:
    just --list

[doc("Generate a `detect-secrets` baseline for the repository")]
[group("DEV")]
secrets-baseline:
    echo "NOTE: Run this once after initial setup & re-run after intentionally adding secrets to the codebase (e.g. test fixtures)."
    uv run detect-secrets scan --exclude-files "(\.secrets\.baseline|.*\.lock)" > .secrets.baseline

[doc("Setup development environment")]
[group("DEV")]
setup: && secrets-baseline
    uv sync
    uv run -m prek install

[doc("Create `coverage` report")]
[group("DEV")]
coverage *FLAGS:
    @uv run coverage run -m pytest {{FLAGS}}
    @uv run coverage report
    @uv run coverage xml