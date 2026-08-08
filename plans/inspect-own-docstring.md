---
status: in-progress
depends: [spec-driven-icm]
specs:
  - specs/commands/inspect.md
  - specs/behaviors/cache-refresh.md
issues: []
pr:
---

# Plan: Report a class's own docstring, never an inherited one

## Scope

Make `inspect` (and the MCP `getSymbolTool` / `showModuleTool`) report a class's **own**
docstring, emitting empty when it defines none, instead of falling back up the MRO.

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

- [ ] `venvaxi inspect fastmcp::FastMCP` emits an empty `doc`, not `AggregateProvider`'s text
- [ ] A class that *does* define a docstring still reports it, whitespace-normalised as before
- [ ] A method overriding a documented base method without its own docstring reports empty
- [ ] A method inherited without override still reports the base's docstring - it is the same
  function object, so that text is genuinely its own
- [ ] A module-level constant still reports empty rather than its type's docstring
  (the `NodeKind.ATTRIBUTE` guard is preserved)
- [ ] `inspect --docstring` on an own-docstring class is unchanged
- [ ] `showModuleTool` and `getSymbolTool` show the same corrected behaviour
- [ ] `SCHEMA_VERSION` bumped to 5, and an existing cache built at 4 is dropped and rebuilt on
  first query rather than serving stale docstrings
- [ ] The `fastmcp-instructions-kwarg` eval is updated to expect the corrected output
- [ ] `uv run coverage run -m pytest` green; new unit test covers the inherited-docstring case
- [ ] `uv run -m prek run --all-files` passes
- [ ] Executed end to end through `/create-feature`, all four stages with their checkpoints,
  producing a techspec, a spec reconciliation and a closeout - this closes the criterion
  [spec-driven-icm](spec-driven-icm.md) left unticked
- [ ] Any friction found in the pipeline itself is recorded in Notes at closeout

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

Populated at closeout.

## Follow-ups

Populated at closeout.
