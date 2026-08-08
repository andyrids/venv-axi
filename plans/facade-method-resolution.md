---
status: done
depends: []
specs:
  - specs/commands/inspect.md
  - specs/behaviors/qualified-name-semantics.md
issues: [12, 13]
pr:
---

# Plan: Resolve facade-spelled class members

## Scope

`inspect` resolves a method only under its **home** module spelling. The facade spelling - the
one an agent actually holds after scanning a codebase - returns a not-found:

```console
$ venvaxi inspect fastmcp::Client.call_tool
error: true
message: "Symbol `fastmcp::Client.call_tool` not found"

$ venvaxi inspect fastmcp.client.client::Client.call_tool
qualified_name: "fastmcp.client.client::Client.call_tool"
kind: method
```

Pre-existing, surfaced as a Follow-up from [inspect-own-docstring](inspect-own-docstring.md) and
filed as [#12](https://github.com/andyrids/venv-axi/issues/12). Scheduled now because v0.1.0
freezes `specs/` as the public contract, and shipping this means shipping a documented resolver
that contradicts a documented principle.

Folds in [#13](https://github.com/andyrids/venv-axi/issues/13), a behaviour-neutral tidy in the
same two files. It contributes nothing to `specs:` above.

## Implements

`specs/behaviors/qualified-name-semantics.md` and `specs/commands/inspect.md`, both amended at
stage 01 to carve class members out of the facade-keyed answer rule.

The existing text says `canonical_name` "is applied by `get_inheritors` only", and that
`get_symbol` "deliberately answer[s] with facade-keyed data (rewriting would change the `module`
field agents see)". That parenthetical is the real rule and it survives intact: the objection is
to **rewriting an answer**, not to **resolving a lookup**. A class member has no facade-keyed row
to rewrite - `_walk_class_members` writes members only at `cls.__module__` - so answering from
the home row invents nothing. The amendment states this rather than leaving a reader to infer
that `get_symbol` was exempted by oversight.

This is the principle's own split, not an exception to it: *output favours the facade; resolution
absorbs the difference internally*. Today resolution does not absorb it, and the caller pays.

## Approach

**1. `get_symbol` fallback** (`_introspect.py:750-773`).

Modelled on `get_inheritors` (`_introspect.py:795-810`) but deliberately **not** a copy. That
function resolves an *edge key* for a node it has already found, and still raises if the facade
node is absent. This one resolves a *missing node*. The shapes differ; sharing a helper between
them would be a false abstraction.

Order matters, because each step guards the next:

1. Engage only when `store.get_node(resolved)` is `None`, `resolved` contains `::`, and the tail
   after `::` contains a `.`. Anything else takes today's raise path untouched.
2. Split the tail on the **last** dot - owner `mod::Outer.Inner`, member `method` - because that
   is how member keys are constructed (`Class.member`, member last). Correct by construction
   rather than by observable contrast: stage-01 review established that no stored key carries a
   two-dot tail (see the amended nested-class criterion below), so both splits raise identically
   on those inputs and only the last-dot split mirrors the key shape.
3. `canonical = store.canonical_name(owner)` (`_store.py:275-288`). If `canonical == owner` the
   owner is either absent or already home-keyed, so the miss is genuine: raise
   `SymbolNotFoundError` with today's message.
4. Build the candidate by string concatenation, `f"{canonical}.{member}"`. Do **not** route it
   back through `qualify()` (`_store.py:99-112`), which would emit a second `::`.
5. No depth guard, deliberately - amended at stage 01 from a step that copied the reopen in
   `_introspect.py:804-810`. `get_inheritors` needs it because `INHERITS` edges are written when
   *subclass* modules are walked, so a deeper home can hold edges the built depth never saw.
   Member `CONTAINS` rows have no such dependency: they are written by the same class walk that
   wrote the owner node, keyed at home regardless of build depth - verified empirically before
   implementation (a class homed at offset 3, re-exported at the root, has its member rows
   present in a depth-2 build that never walked the home module). A found owner therefore
   implies its member rows exist, and a candidate miss is definitive: raise.
6. Return the node **as stored**. Do not rewrite `qualified_name` or `module`.

Step 6 is the decision the spec amendment records. The caller gets
`fastmcp.client.client::Client.call_tool` back - the key that exists, the same one `find` already
returns for this symbol. Echoing the caller's spelling would be friendlier and would emit a name
with no row behind it.

**2. `_own_doc` uniformity** (issue #13, behaviour-neutral).

Two module-object call sites still use `inspect.getdoc` rather than the shared helper
[inspect-own-docstring](inspect-own-docstring.md) introduced:

- `_cache.py:152` - the `PACKAGE` node's doc
- `_introspect.py:527` - submodule nodes in `_walk_submodules` (the issue cites 422; the line
  moved under `bd83566` and `f6d01fd`)

Neither can exhibit the inherited-docstring bug, because `inspect._finddoc` returns `None` for
modules. They were left alone under `reference-standard-yagni.md` and that call was right at the
time. The cost is an asymmetry: a future change to `_own_doc` - normalisation, a marker - would
silently not apply to the two node kinds that skip it, and a reader comparing the three sites has
to re-derive the `_finddoc` reasoning to learn why two differ. Route both through
`_introspect._own_doc` (`_introspect.py:132-148`). `_cache.py` already reaches for `_introspect`
privates at lines 81, 118 and 158, so this adds no coupling.

## Validation

- [x] `venvaxi inspect fastmcp::Client.call_tool` returns the method, keyed
      `fastmcp.client.client::Client.call_tool`
- [x] `venvaxi inspect fastmcp::Client.nosuchmethod` still raises `SymbolNotFoundError` at exit 1
- [x] A facade-spelled nested class resolves through the fallback as a member of its outer
      class (`facade::Outer.Inner` answers with the home-keyed `Outer.Inner` attribute row)
- [x] A member-of-nested-class spelling (`mod::Outer.Inner.method`) raises `SymbolNotFoundError`
      under both facade and home spellings - no such row exists in the graph, per the amended
      spec
- [x] A module-level miss (`rich::NoSuchThing`) takes the unchanged raise path - the fallback
      disengages before any owner lookup
- [x] A member whose home module sits deeper than the built depth (offset 3 against a built
      depth of 2) resolves with no deeper rebuild - member rows are written by the class walk at
      home keys regardless of build depth, so the criterion fails if a depth-gated path is ever
      reintroduced in front of it
- [x] Each new test is shown to fail against pre-fix `get_symbol` before the fix is applied
      (ticked with a qualification - see Notes)
- [x] `getSymbolTool` resolves the facade spelling identically - CLI/MCP parity per
      `specs/mcp/tools.md`
- [x] Module `doc` values are unchanged after the `_own_doc` reroute, asserted against a real
      installed package rather than a mock
- [x] `specs/behaviors/qualified-name-semantics.md` and `specs/commands/inspect.md` both state
      the class-member carve-out, and neither still claims `canonical_name` is applied by
      `get_inheritors` only
- [x] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green

## Risks / unknowns

- **The fallback runs on every genuine miss**, adding a `canonical_name` lookup to the
  not-found path. That path already raises, so the cost lands on an error, not on a hot query.
  Step 3's `canonical == owner` short-circuit keeps it to one extra `get_node`.
- ~~**The depth guard is the part most likely to be got wrong.**~~ Resolved at stage 01: the
  guard is not adapted, because for member rows it can never fire - see Approach step 5. The
  deeper-home validation criterion was rewritten from 'the guard is covered by a test' to 'the
  deep-home case resolves with no deeper rebuild'.
- ~~**An `Outer.Inner` owner may itself be facade-keyed at a different module than its
  members.**~~ Resolved at stage 01, empirically: it cannot be. A nested class is recorded as an
  *attribute member row* of its outer class, keyed at the outer class's home module with a
  self-referential `home_qualified_name`, and members of nested classes are never recorded at
  all. No stored key carries a two-dot tail, so the feared owner shape does not exist in the
  graph. The nested-class criterion was rewritten to match, and the fact is now stated in
  `specs/behaviors/qualified-name-semantics.md`.
- **Unknown: whether any other caller depends on `get_symbol` raising for a facade-spelled
  member.** Nothing in `src/` does by inspection; `tests/test_introspect.py:516-526` covers only
  a class and an unknown symbol.

## Notes

**The plan was amended at stage 01, before implementation, after review against the code.** Not
a mid-run re-entry - no later stage had produced output to invalidate - but the Approach and
Validation an approver saw changed, so the deltas are recorded:

- **The adapted depth guard (original step 5) was dropped as unreachable.** `get_inheritors`
  rebuilds deeper because `INHERITS` edges are written when *subclass* modules are walked.
  Member `CONTAINS` rows are written by the same class walk that writes the owner node, keyed at
  home regardless of build depth - verified by probe before implementation: a depth-2 build that
  never walked `probepkg.sub.inner.leaf` as a module still held
  `probepkg.sub.inner.leaf::Deep.deep_method`. A found owner therefore implies its member rows
  exist, and the deeper-home criterion was rewritten from 'guard covered by a test' to 'resolves
  with no deeper rebuild', asserted by a `_build_store_for` call-count spy.
- **The `Outer.Inner` risk resolved as impossible, and the nested-class criterion was
  unsatisfiable as written.** A nested class is recorded as an attribute member row of its outer
  class, keyed at the outer class's home with a self-referential `home_qualified_name`; members
  of nested classes are never recorded. No stored key carries a two-dot tail, so
  `mod::Outer.Inner.method` misses under every spelling - now stated in
  `specs/behaviors/qualified-name-semantics.md` as a definitive answer. Consequence: the
  original step 2 claim that a first-dot split 'silently mis-resolves' nested classes is not
  observable - both splits raise identically on two-dot tails - so the last-dot split is
  justified by key shape (`Class.member`, member last), not by a distinguishing test.

**The fail-first criterion is ticked with a qualification.** The four new-behaviour tests
(facade method, facade nested class, deep home, MCP parity) all failed against pre-fix
`get_symbol` with `SymbolNotFoundError`. The five remaining new tests pin behaviour the fix must
not change - miss paths, fallback disengagement, issue #13's neutrality - and pass pre-fix by
design; a pre-fix failure there would itself have been a bug.

**The helper-sharing question was re-examined and the plan's call stands.** `get_inheritors`
raises when the facade node is absent and uses `canonical_name` only to key the edge query for a
node already found; the fallback resolves a missing node via its owner. After the depth-guard
finding the two share even less than the plan assumed.

**Observation, recorded not fixed:** on a facade-spelled hit, the `help[]` footer echoes the
caller's facade spelling while `qualified_name` reports the home key. Both spellings now
resolve, and no spec rule constrains the footer's spelling, so this is cosmetic.

**Unknown 4 resolved:** no caller depends on `get_symbol` raising for a facade-spelled member -
confirmed by inspection of `src/` and by the full suite (256 tests) passing unmodified apart
from the tests this plan adds.

## Follow-ups

- **None** - no issues filed, nothing deferred to a downstream plan, nothing tracked
  externally. Issues [#12](https://github.com/andyrids/venv-axi/issues/12) and
  [#13](https://github.com/andyrids/venv-axi/issues/13) close with this plan.
