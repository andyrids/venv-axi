---
status: done
depends: [spec-driven-icm]
specs:
  - specs/commands/inspect.md
  - specs/behaviors/cache-refresh.md
issues: [12, 13]
pr: 11
---

# Plan: Report a class's own docstring, never an inherited one

## Scope

Make `inspect` (and the MCP `getSymbolTool` / `showModuleTool`) report a class's **own**
docstring, emitting a definitive `(no docstring)` marker when it defines none, instead of falling
back up the MRO.

Surfaced by `specs/commands/inspect.md`, which declares the own-docstring rule that the
implementation does not currently satisfy. This plan exists so that spec is covered motion rather
than an invariant violation.

## Implements

`specs/commands/inspect.md` - the rule that `doc` MUST be the target's own docstring, and MUST
NOT inherit a base class's, metaclass's or type's.

## Approach

The bug is in `_doc_of` (`src/venvaxi/_introspect.py`):

```python
doc = inspect.getdoc(obj) or ""
if kind is not NodeKind.ATTRIBUTE:
    return doc
```

`inspect.getdoc` walks the MRO. The existing guard covers `NodeKind.ATTRIBUTE` only - added
because an instance constant would otherwise carry its builtin type's docstring - so classes and
functions still inherit.

Reproduction, against `fastmcp` in this venv:

```text
$ uv run venvaxi inspect fastmcp::FastMCP
doc: Utility provider that combines multiple providers into one.
```

`FastMCP.__doc__` is `None`; the text belongs to `AggregateProvider`, its `__mro__[1]`.

Replace `inspect.getdoc` with `inspect.cleandoc(obj.__doc__)`. `getdoc` is exactly
`cleandoc(own __doc__)` plus a `_finddoc` fallback that walks the MRO; dropping only the fallback
fixes the bug while preserving whitespace normalisation, without which every multi-line docstring
in the graph would gain ragged indentation.

Stage 01 resolved the open question about methods empirically - no spec change was needed, and
one uniform rule covers every kind:

| Case                             | `__doc__` | `getdoc` | Correct source |
| -------------------------------- | --------- | -------- | -------------- |
| Class, no docstring              | `None`    | base's   | `__doc__`      |
| Method overriding, no docstring  | `None`    | base's   | `__doc__`      |
| Method inherited, not overridden | base's    | base's   | either         |

The third row is not inheritance: `B.n is A.n` is `True`, so the base's docstring is genuinely
that object's own and both sources agree.

Normal attribute lookup does not inherit `__doc__` for classes or override methods; only
`getdoc`'s fallback does. So "never call `_finddoc`" is the whole rule.

The `NodeKind.ATTRIBUTE` guard MUST be kept. An instance's `__doc__` *is* its type's docstring by
normal attribute lookup (`re.compile("x").__doc__ is type(...).__doc__` -> `True`), so switching
to `__doc__` does not remove the need for it - only the comparison target changes.

**Cache invalidation** - `_doc_of` runs at walk time, so docstrings are frozen into the store and
every existing cache keeps serving inherited ones. The mechanism to fix this already exists:
`_store.SCHEMA_VERSION` is stored as `PRAGMA user_version`, and `_ensure_schema` drops and
rebuilds on mismatch. Bump `SCHEMA_VERSION` from 4 to 5. `specs/behaviors/cache-refresh.md` is
amended in the same change to state that this version tracks *what a walk records*, not only the
table shape - the rule that makes this bump discoverable next time.

Note `.claude/skills/venvaxi/evals/evals.json` currently encodes this bug **as an expectation**
(`fastmcp-instructions-kwarg`). That eval must be updated in the same change, or it will fail
once the bug is fixed.

**Absorbed from [spec-driven-icm](spec-driven-icm.md)**: drive this plan through the full
`/create-feature` pipeline rather than fixing it directly. That plan closed with one Validation
criterion unticked - no end-to-end pipeline run had been performed - and this is the designated
first exercise of it. Every stage gate applies: 01 amends `specs/commands/inspect.md` if the
method/function question below changes the rule, opens the plan; 02 implements; 03 checks
conformance against the spec and exercises the CLI live; 04 closes this plan out. Treat a stage
that feels awkward as a finding about the pipeline, and record it in Notes at closeout.

## Validation

Two criteria were reworded at stage 04, when the empty-string output was replaced by a marker -
see Notes.

- [x] `venvaxi inspect fastmcp::FastMCP` emits `(no docstring)`, not `AggregateProvider`'s text
- [x] A class that *does* define a docstring still reports it, whitespace-normalised as before
- [x] A method overriding a documented base method without its own docstring reports the marker
- [x] A method inherited without override still reports the base's docstring - it is the same
  function object, so that text is genuinely its own
- [x] A module-level constant is not *recorded* with its type's docstring
  (the `NodeKind.ATTRIBUTE` guard is preserved)
- [x] The marker is emission-only - `_doc_of` still records `""`, so `find` does not match every
  undocumented symbol on the marker's wording
- [x] `inspect --docstring` on an own-docstring class is unchanged
- [x] `showModuleTool` and `getSymbolTool` show the same corrected behaviour
- [x] `SCHEMA_VERSION` bumped to 5, and an existing cache built at 4 is dropped and rebuilt on
  first query rather than serving stale docstrings
- [x] The `fastmcp-instructions-kwarg` eval is updated to expect the corrected output
- [x] `uv run coverage run -m pytest` green; new unit test covers the inherited-docstring case
- [x] `uv run -m prek run --all-files` passes
- [x] Executed end to end through `/create-feature`, all four stages with their checkpoints,
  producing a techspec, a spec reconciliation and a closeout - this closes the criterion
  [spec-driven-icm](spec-driven-icm.md) left unticked
- [x] Any friction found in the pipeline itself is recorded in Notes at closeout

## Risks / unknowns

- ~~**Blast radius on the cached graph.**~~ Resolved in stage 01: bump `SCHEMA_VERSION`, which
  already drives a drop-and-rebuild via `PRAGMA user_version`. No new mechanism, no migration.
- ~~**Functions may want different treatment from classes.**~~ Resolved in stage 01 by
  experiment - one rule covers every kind, and no spec change was needed. See the table in
  Approach. A `functools.wraps`-decorated function carries the wrapped function's `__doc__` as
  its own attribute and is unaffected either way.
- **Empty `doc` is less useful than a wrong one is harmful.** The spec takes this position
  explicitly, on the grounds that a false fact is worse than a missing one - and this tool exists
  precisely so an agent is not told false things about installed packages. Called out here
  because the visible effect of this fix is that some symbols get *less* output than before, and
  that can read as a regression to someone who has not read the spec.
- **Every project pays one full rebuild** on first query after upgrading. One-time, and the
  alternative is indefinite silent staleness.

## Notes

**The whole fix is "never call `inspect._finddoc`".** `getdoc` is `cleandoc(own __doc__)` plus a
fallback that walks the MRO. Reading `__doc__` directly and keeping `cleandoc` drops only the
fallback. Normal attribute lookup does not inherit `__doc__` for classes or override methods, so
one rule covers every kind and no method-specific carve-out was needed - which was stage 01's
open question, settled by experiment rather than reasoning.

**Cache invalidation needed no new mechanism.** The plan anticipated building one; `_store.py`
already had `SCHEMA_VERSION` behind a `PRAGMA user_version` drop-and-rebuild. The real gap was
that nothing said it must be bumped when *derived content* changes, only when the table shape
does - a reader changing `_doc_of` would never have thought to touch it. That rule now lives in
`specs/behaviors/cache-refresh.md` and in the constant's own docstring. Bumped 4 -> 5; the graph
rebuilt with no `--refresh`.

**The marker decision arrived at stage 04, after implementation and verification.** The original
spec said an undocumented symbol reports an empty `doc`; review replaced that with a
`(no docstring)` marker, by analogy with the existing `SIGNATURE_UNAVAILABLE`. Consequences:

- Four spec files changed rather than two - the rule is cross-cutting, so it went in
  `specs/behaviors/output-contract.md`, with `inspect.md`, `show.md` and `mcp/tools.md`
  referencing it.
- **The marker is applied at emission, never recorded.** `doc` is FTS-indexed, so storing
  `"(no docstring)"` would make `find docstring` match every undocumented symbol in the graph.
  Verified after the change: that search returns 7 genuine matches, not hundreds. This mirrors
  truncation, which is already emission-only for the same class of reason.
- Two Validation criteria above were reworded, since they asserted the superseded behaviour. A
  frozen record stating the wrong desired state is worse than an edited one.

**`(no docstring)` states a different fact from `(signature unavailable)`.** The signature marker
means introspection failed; this one means the symbol genuinely defines none. The names differ
deliberately so the distinction survives.

**No test was written for the `SCHEMA_VERSION` bump.** `tests/test_store.py` already has
`test_schema_version_mismatch_rebuilds_tables`, exercising the identical
`version != SCHEMA_VERSION` branch. A copy using `4` instead of `999` would assert nothing new.
Verified live instead.

### Pipeline friction

First end-to-end `/create-feature` run. It held together, and two stage boundaries earned their
keep: deferring the test run to 03 forced the 02 report's honest "unverified at this stage"
section, and stage 04's "consider a new reference doc" prompt produced a real convention. The
friction:

- **Checkpoint 5 is vacuous when nothing breaks.** It gates step 4, "fix any broken tests", which
  was a no-op. The gate should be conditional on that step having changed something.
- **Checkpoints 11 and 13 review the same findings twice** - 11 gates conformance results, 13
  gates the report restating them. Stage 03 asks for five approvals where two would do.
- **A stage-04 design decision has no defined route back.** Replacing `""` with a marker rewrote
  a spec, source, tests and two Validation criteria *after* stage 03 signed off. The pipeline is
  linear and offers no re-entry, so verification was redone informally. Worth an explicit rule:
  a stage-04 decision that changes behaviour returns to 01.
- **No stage claims `evals.json`.** It is behaviour-expectation, not source. Updated in 03 on the
  reasoning that a stale expectation is a failing test; the guidance should say so. It then
  needed updating twice, because of the item above.

## Follow-ups

- **Issue** [#12](https://github.com/andyrids/venv-axi/issues/12) -
  `venvaxi inspect fastmcp::Client.call_tool` raises `SymbolNotFoundError`; only the home
  spelling `fastmcp.client.client::Client.call_tool` resolves, because class members are keyed at
  the class's home module. Consistent with `specs/behaviors/qualified-name-semantics.md`, but in
  tension with
  [the agent's spelling wins](../specs/principles.md#the-agents-spelling-wins-over-the-internally-correct-one):
  an agent that read `from fastmcp import Client` gets a not-found. Needs either a resolver
  change or a spec amendment making the asymmetry explicit in `inspect.md`. Pre-existing, not
  introduced here.
- **Issue** [#13](https://github.com/andyrids/venv-axi/issues/13) - `inspect.getdoc` remains at
  `_cache.py:152` and `_introspect.py:422`, both on module objects, which cannot inherit
  docstrings. Behaviour-neutral to change, so left under YAGNI; filed so the asymmetry does not
  read as an oversight and so a future `_own_doc` change is known not to reach them.
- **Tracked as** - the pipeline friction above. Acting on it means editing the stage `CONTEXT.md`
  files, which is `spec-driven-icm`'s territory rather than this plan's.
