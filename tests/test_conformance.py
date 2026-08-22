"""Marker-gated conformance tier: walks real installed dependencies.

Every other introspection test walks `tests/resources/package/`, a
fixture this repository wrote - small, well-behaved, pure Python. Issues
#64, #65, #66, #67, #68 and #69 were all found by dogfooding a published
release of another project; none of them failed the 370-test suite that
walks only the hand-written fixture (issue #71).

NOTE: Assertions here are surface-level invariants only, never a
version-pinned fact about a specimen's public API. The property under
test is that the symbol-graph walk survives arbitrary third-party code,
not that `numpy` has a particular symbol - an assertion like
`"ndarray" in result` would be exactly wrong here.

NOTE: Specimens are unpinned on purpose - a pinned specimen tests a
snapshot, and the property under test is survival of whatever
third-party code is actually installed. See `plans/real-dependency-
conformance.md` (Risks: Version drift).

Opt in with `uv run pytest -m conformance`; the default run (and CI's
`uv run coverage run -m pytest`) excludes this tier via `addopts`.
"""

import argparse
from collections.abc import Callable
from pathlib import Path

import pytest

from venvaxi._cli import command_find, command_show, command_tree
from venvaxi._core import CLIContext
from venvaxi._introspect import show_module
from venvaxi._store import NodeKind

pytestmark = pytest.mark.conformance

ContextFactory = Callable[..., CLIContext]

SPECIMENS = ["numpy", "polars", "pydantic", "fastmcp"]
"""Issue #71's own proven specimens (`numpy`, `polars`) plus `pydantic`
and `fastmcp`, already installed here and used as extra specimens at
zero install cost."""

SANE_PAYLOAD_BYTES = 50_000
"""The byte bound a single CLI command payload must clear.

NOTE: Chosen, not measured backwards from a passing case - roughly
12,500 tokens at a 4-bytes/token heuristic, which is already a lot for
one AXI response in an interface built for token efficiency
(`specs/principles.md`). `fastmcp`'s current `show --api --docstring`
payload (~7.2 KB) clears it with a wide margin, evidencing the bound
accepts a genuinely reasonable payload rather than a strawman; `numpy`
(~737 KB), `polars` (~380 KB) and `pydantic` (~105 KB) all exceed it by
2x-14x - the unbounded-payload defect issue #67 exists to fix.
"""

# NOTE: `fastmcp` is the live regression guard - its payload already
# clears `SANE_PAYLOAD_BYTES` today, so it asserts normally. The other
# three are pinned `xfail(strict=True)`, named to issue #67: none of
# them bound `--api --docstring` yet, confirmed by direct measurement
# against the versions resolved into this venv, not by the issue's own
# (differently-versioned) numbers.
_UNBOUNDED_PAYLOAD_TODAY = {"numpy", "polars", "pydantic"}


def _payload_case(specimen: str) -> object:
    """Wrap a specimen in a strict `xfail` when its payload is known
    unbounded today (issue #67), leaving a conformant specimen bare."""
    if specimen not in _UNBOUNDED_PAYLOAD_TODAY:
        return pytest.param(specimen)
    return pytest.param(
        specimen,
        marks=pytest.mark.xfail(
            strict=True,
            reason="unbounded --api --docstring payload, issue #67",
        ),
    )


@pytest.mark.parametrize("specimen", SPECIMENS)
def test_tree_completes_over_real_package(
    isolated_cache: Path,
    make_cli_context: ContextFactory,
    specimen: str,
) -> None:
    """`tree` exits 0 over a real installed dependency - any submodule
    raising at import time, including a bare `BaseException`, must not
    abort the walk (#64)."""
    pytest.importorskip(specimen)
    ctx = make_cli_context(
        args=argparse.Namespace(package=specimen, max_depth=2)
    )
    exit_code = command_tree(ctx)
    assert exit_code == 0


def test_tree_completes_over_numpy_f2py_base_exception_specimen(
    isolated_cache: Path, make_cli_context: ContextFactory
) -> None:
    """`tree` exits 0 walking deep enough into `numpy.f2py` to reach
    `numpy.f2py.tests.util`, the confirmed live specimen for #64: it
    raises a bare `BaseException` (`_pytest.outcomes.Skipped`) at import
    time on Windows ("No Fortran tests on Windows"). The walk must
    survive on every platform; only the exit code is asserted, never
    which submodule raised - the pathology is Windows-conditional (see
    `plans/real-dependency-conformance.md`, Risks: Platform-conditional
    pathologies), and on any other platform this is simply a deeper
    walk that also must not crash."""
    pytest.importorskip("numpy")
    ctx = make_cli_context(
        args=argparse.Namespace(package="numpy.f2py", max_depth=2)
    )
    exit_code = command_tree(ctx)
    assert exit_code == 0


@pytest.mark.parametrize("specimen", SPECIMENS)
def test_no_callable_symbol_has_empty_signature(
    isolated_cache: Path, specimen: str
) -> None:
    """No callable top-level symbol records an empty signature -
    callability, not kind, decides the signature (#66). A module-level
    instance whose class defines `__call__` (the confirmed `polars.col`
    shape) classifies as `attribute`, not `class`/`function`, and must
    record a real signature or the definitive `(signature unavailable)`
    marker - never the `""` reserved for a genuinely non-callable
    attribute.

    NOTE: `module`/`package` children are excluded - a submodule shares
    its bare name with anything the parent module's namespace
    re-exports under that name (e.g. `polars.sql` the submodule vs.
    `polars.sql` the re-exported function), so a live `getattr` on the
    parent module does not reliably name the module node's own object.
    """
    live_module = pytest.importorskip(specimen)
    _, children = show_module(specimen)
    violations = [
        child.name
        for child in children
        if child.kind not in (NodeKind.MODULE, NodeKind.PACKAGE)
        and callable(getattr(live_module, child.name, None))
        and child.signature == ""
    ]
    assert violations == []


@pytest.mark.parametrize("specimen", SPECIMENS)
def test_find_count_at_limit_carries_bounded_hint(
    isolated_cache: Path,
    make_cli_context: ContextFactory,
    capsys: pytest.CaptureFixture,
    specimen: str,
) -> None:
    """A `find` result count equal to the active `--limit` carries the
    bounded-results hint - a truncated answer must never read as
    definitive (#69)."""
    pytest.importorskip(specimen)
    ctx = make_cli_context(
        args=argparse.Namespace(query="a", limit=1, package=specimen)
    )
    exit_code = command_find(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "count: 1" in out
    assert "Results capped at --limit 1" in out


@pytest.mark.parametrize("specimen", [_payload_case(s) for s in SPECIMENS])
def test_show_api_docstring_payload_stays_bounded(
    isolated_cache: Path,
    make_cli_context: ContextFactory,
    capsys: pytest.CaptureFixture,
    specimen: str,
) -> None:
    """A single `show --api --docstring` payload stays under a sane
    byte bound (#67).

    `numpy`, `polars` and `pydantic` are pinned `xfail(strict=True)`
    today - `strict=True` is load-bearing: it keeps this tier green now,
    and the moment issue #67 bounds the payload the assertion passes
    unexpectedly and fails the suite, forcing that unit to flip the
    mark rather than let the bug pass unnoticed. `fastmcp` carries no
    such mark and must keep passing - the live regression guard for
    this invariant.
    """
    pytest.importorskip(specimen)
    ctx = make_cli_context(
        args=argparse.Namespace(package=specimen, api=True, docstring=True)
    )
    exit_code = command_show(ctx)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert len(out.encode("utf-8")) <= SANE_PAYLOAD_BYTES
