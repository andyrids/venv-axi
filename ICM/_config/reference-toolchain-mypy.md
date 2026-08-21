---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [mypy, typing]
---

# Toolchain - `Mypy`

Mypy is used to enforce standards for typing.

## Commands

- `uv run pkgdx-typing-hook -p venvaxi` - Type-check the package
- `uv run prek run --all-files` - Run the `typing` hook alongside all other hooks

## Configuration

The Mypy config ships inside the installed `pkgdx` dev dependency
(`<site-packages>/pkgdx/standards/mypy.ini`) and is applied by the `pkgdx-typing-hook` shim -
prefer the hook over a hand-rolled `mypy` invocation. Enforce the usage of the type hints for
all function/method args and return values.

## Guidance

When something is imported from a dependency, it's resolved to `Any` if Mypy can't resolve the import.

```ini
disallow_any_unimported = true
```

- Missing stubs can sometimes be found at [typeshed/stubs](https://github.com/python/typeshed/tree/main/stubs)
- A type ignore (`# type: ignore[no-any-unimported]`) can be used when stubs are unavailable

```python
from requests import Request


def my_function(request: Request) -> None:  # type: ignore[no-any-unimported]
    ...
```

Explicit is better than implicit - `arg: Optional[str] = None` over `arg: str = None`.

```ini
no_implicit_optional = true
```

It is better to ignore only the specific type of an error. Prefer `# type: ignore[<error-code>]`
over `# type: ignore`.

```ini
show_error_codes = true
warn_unused_ignores = true
```
