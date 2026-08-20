"""Fixture package submodule."""


def util() -> str:
    """Return a utility function."""
    return __name__


def render_grid() -> str:
    """Render a rendered-table example, as a docstring carries it.

    ┌───────┬───────┐
    │ α → ω │ x ± y │
    └───────┴───────┘
    """
    return __name__
