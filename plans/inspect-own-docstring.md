---
status: planned
depends: [spec-driven-icm]
specs:
  - specs/commands/inspect.md
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

Extend the own-doc check to classes and functions. Prefer the object's own `__dict__["__doc__"]`
over `inspect.getdoc`, so inheritance is never consulted - but keep `getdoc`'s whitespace
normalisation for the docstrings that *are* the object's own, or every existing docstring in the
graph gains ragged indentation.

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
- [ ] `inspect --docstring` on an own-docstring class is unchanged
- [ ] `showModuleTool` and `getSymbolTool` show the same corrected behaviour
- [ ] The `fastmcp-instructions-kwarg` eval is updated to expect the corrected output
- [ ] `uv run coverage run -m pytest` green; new unit test covers the inherited-docstring case
- [ ] `uv run -m prek run --all-files` passes
- [ ] Executed end to end through `/create-feature`, all four stages with their checkpoints,
  producing a techspec, a spec reconciliation and a closeout - this closes the criterion
  [spec-driven-icm](spec-driven-icm.md) left unticked
- [ ] Any friction found in the pipeline itself is recorded in Notes at closeout

## Risks / unknowns

- **Blast radius on the cached graph.** Docstrings are stored at walk time, so every cached graph
  built before this change holds inherited docstrings. Users need `--refresh`, or the cache
  schema needs a version bump to force a rebuild. Decide which before implementing.
- **Functions may want different treatment from classes.** A method overriding a documented base
  method arguably should surface nothing; a `functools.wraps`-decorated function legitimately
  carries the wrapped function's docstring via `__doc__` and would be unaffected. Confirm the
  intended behaviour for methods against the spec before coding.
- **Empty `doc` is less useful than a wrong one is harmful.** Worth confirming with the user that
  an empty docstring is preferred over an inherited one; the spec says yes, on the grounds that a
  false fact is worse than a missing one.

## Notes

Populated at closeout.

## Follow-ups

Populated at closeout.
