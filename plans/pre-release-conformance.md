---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/behaviors/cache-refresh.md
  - specs/commands/show.md
authors: []
issues: [28, 29, 30, 31]
pr: 32
---

# Plan: Close the pre-release conformance gaps

## Scope

A full `specs/` drift audit was run against `develop` at `8c485c8` as a gate on PR #27, which
cuts v0.1.0. It found one code bug and three false statements in `specs/` that would otherwise
freeze as the public contract.

The audit is the gate that mattered and it was nearly skipped: it was listed as a release
verification step, never carried into either plan's Validation checklist, and so never ran. Both
`uv run coverage run -m pytest` and `uv run -m prek run --all-files` pass on every finding below.
Neither gate can see a spec that lies or an answer that depends on cache history.

Four blocking findings, in severity order. The non-blocking remainder is in Follow-ups.

## Implements

`specs/behaviors/cache-refresh.md` - the Validity rule, which finding 1 violates. Also
`specs/commands/show.md`, whose API mode accepts any importable dotted module path and therefore
inherits that rule.

Findings 2-4 are spec corrections, not code conformance, and so contribute nothing to `specs:`
above - per the trap documented in `plans/README.md`, over-listing here is how Invariant 1 stops
being able to fail.

## Approach

**1. `get_public_api` never derives build depth** (`_introspect.py:972`). Code is wrong.

`_build_store_for(name, refresh=refresh)` takes the fixed `DEFAULT_MAX_DEPTH`, while
`show_module` (l.741), `get_symbol` (l.805) and `get_module_tree` (l.877) all pass
`max(DEFAULT_MAX_DEPTH, _module_offset(...))`. So a dotted module deeper than 2 answers from
whatever depth the cache happens to hold. Reproduced live:

```console
$ venvaxi show fastmcp.server.auth.providers.github --api --refresh
count: 0
$ venvaxi inspect fastmcp.server.auth.providers.github    # deepens the cache
$ venvaxi show fastmcp.server.auth.providers.github --api
count: 2
```

The same invocation returns opposite answers depending on what ran before it. `--refresh` makes
it *worse*: it rebuilds at depth 2 and destroys the correct answer, so the documented recovery
for a stale graph is the thing that reintroduces the fault.

This is the failure `cache-refresh.md` Validity exists to prevent - a shallow graph read as a
definitive empty answer - and it breaks the definitive-empty-states principle the whole AXI is
sold on. It propagates identically to `showPackageApiTool`.

Mirror `get_symbol`. One open question for the implementer to settle rather than assume:
`get_public_api` derives its offset from `_resolve_import_name(name)`, which resolves the *whole*
argument, whereas `get_symbol` uses `_resolve_qualified_name`, which resolves only the root
component. For a dotted name `_resolve_import_name` falls through to a dash replacement and
happens to return the name unchanged - correct by accident, not by design. Establish which helper
is right here and say so in Notes.

**2. `specs/commands/inherits.md:25-28` claims a sole consumer.** Spec is wrong.

> Unlike `inspect` and `find`, this command resolves through `SymbolStore.canonical_name` ... It
> is the only consumer of that resolution.

Since [facade-method-resolution](facade-method-resolution.md), `get_symbol` is a second consumer
via `_resolve_facade_member`, and `specs/behaviors/qualified-name-semantics.md:29` states so
explicitly. Two specs now contradict each other about the same resolver.

This is the cross-branch leak that plan's own review predicted and did not catch: it amended the
behaviour spec and `inspect.md`, but not the third file that *restates* the rule. Rewrite the
passage to distinguish the two consumers by shape - `get_inheritors` resolves for every input
because `INHERITS` edges are always home-keyed; `get_symbol` resolves only for the class-member
carve-out.

**3. `specs/behaviors/package-resolution.md:62-65` states one rule for three behaviours.** Spec
is wrong.

> For a dotted or qualified name, only the top-level component is validated ... A malformed tail
> resolves to `SymbolNotFoundError` through the normal lookup.

Observed on `fastmcp.@bad`:

- `inspect` - `SymbolNotFoundError`, exit 1. Matches.
- `show --api` - `InvalidArgumentError`, exit 1. The whole argument is validated, because in API
  mode the whole argument *is* a module path.
- `tree` - `count: 0`, exit 0. A malformed tail is indistinguishable from a submodule with no
  node, which is `tree`'s specified empty state.

Note `specs/commands/show.md`'s own error list already matches the code, so the two specs
disagree with each other rather than both being wrong. The per-command behaviour is defensible;
the cross-cutting rule that claims to cover all of them is not. Amend it to carve out `show --api`
and `tree`, naming why each differs.

Amended at stage 01 on evidence: a live sweep found a fourth shape the audit did not list.
`find --package fastmcp.@bad` matches package-wide - the name only selects the package to index
and scope to, and components below the top level never participate in the search. The amendment
describes that shape too, so the rewritten rule is exhaustive over the commands the spec's
'Applies to' names.

**4. `specs/README.md:38-41` omits `behaviors/package-resolution.md`** from the layout tree.
Spec is wrong. It landed under PR #24 without the index being updated, so an agent enumerating
the contract from the layout misses the error taxonomy entirely. One line.

## Validation

- [x] `venvaxi show <dotted.module> --api --refresh` and the same command without `--refresh`
      return the same answer - the criterion the current code fails
- [x] A regression test pins that answer against a **rebuilt** cache, so it fails if the depth
      derivation is dropped again; it must not pass merely because an earlier test deepened the
      cache
- [x] `showPackageApiTool` returns the same symbols for the same dotted module - the bug reaches
      MCP through the same function
- [x] `show <package> --api` for a top-level package is unchanged, and no unnecessary deeper
      build is triggered for it
- [x] The helper question in Approach 1 is settled and recorded in Notes, not left implicit in
      the diff
- [x] `specs/commands/inherits.md` no longer claims a sole consumer, and distinguishes the two
      consumers by shape
- [x] `grep -rn "only consumer" specs/` returns nothing
- [x] `specs/behaviors/package-resolution.md` describes all observed behaviours - the original
      three plus `find --package`'s scope-only use of the name - and each matches a live run
- [x] `specs/README.md` layout lists all four `behaviors/` files
- [ ] Every new test is shown to fail against the current code before the fix
- [x] `uv run -m prek run --all-files` passes; `uv run coverage run -m pytest` green
- [x] A re-run of the spec drift audit reports zero blocking findings

## Risks / unknowns

- **The depth fix may deepen builds for callers that did not need it.** `show --api` on a
  top-level package has offset 0, so `max(DEFAULT_MAX_DEPTH, 0)` leaves it at today's depth. Only
  dotted arguments build deeper, which is exactly the case that is currently wrong. The fourth
  criterion above exists to catch a regression here.
- **A regression test for finding 1 is easy to write and have pass for the wrong reason.** Test
  order alone can deepen the shared cache, so a naive test passes against the unfixed code. The
  second criterion is written to force a rebuilt cache; treat a test that passes pre-fix as a
  broken test, not as a fixed bug.
- **Finding 3 risks over-correcting.** The temptation is to make all three commands behave alike.
  That would be a behaviour change to two shipped commands on the eve of a release, to satisfy a
  rule that was written after the fact. The spec is the thing that is wrong here.
- **Unknown: whether other cross-file restatements of the same rule exist.** Finding 2 was one
  spec restating another and going stale. The audit found one; nothing establishes it is the only
  one.

## Notes

**The helper question is settled: `_resolve_qualified_name`.** Four reasons, in order of force:
the store is keyed by import names whose *root* is resolved (`_build_store_for` resolves
`_top_level_root(name)`), so the lookup key must be the root-resolved spelling;
`_resolve_import_name` over a whole dotted name falls through to a dash replacement that would
silently repair a dashed *tail* - the exact repair the Ordering rule in
`specs/behaviors/package-resolution.md` forbids resolution to make; a dashed or cased
distribution root carrying a dotted tail (`pillow.Image`) resolves correctly (`PIL.Image`) only
under root resolution; and every sibling query function already uses it. The old code's
correct-by-accident pass-through is gone rather than relied on.

**Depth arithmetic**: the derivation is `max(DEFAULT_MAX_DEPTH, _module_offset(resolved))`
*without* the `+ 1` that `show_module` adds. `_walk_module` records a module's class and
function children at the module's own walk depth; only submodule recursion needs one level more,
and `get_public_api` reads only CLASS/FUNCTION children. Confirmed empirically - the regression
test passes at exactly the derived depth on a rebuilt cache.

**Finding 1 required no spec amendment.** `specs/behaviors/cache-refresh.md` Validity rule 3
already requires the recorded build depth to satisfy the current query, and
`specs/commands/show.md` API mode links to it. This was an Invariant 2 fix-the-code case, which
is why the frontmatter `specs:` field stands unchanged.

**Stage 01 amended finding 3 on evidence, before implementation.** A live sweep found a fourth
malformed-tail shape the audit had not listed: `find --package fastmcp.@bad` matches
package-wide, because the name only selects the package to index and scope to. The spec
amendment describes all four shapes; Approach and the Validation criterion were widened in the
same stage, so this was an in-stage amendment rather than a re-entry.

**How the pre-fix failure was demonstrated**: `git stash push -- src/venvaxi/_introspect.py`,
run the two new tests, `git stash pop`. `test_get_public_api_derives_build_depth` failed
pre-fix, returning `[]` against `["Widget", "ping"]` on a rebuilt (`refresh=True`) isolated
cache - so its pass is not a cache-ordering artefact.

**One Validation box is left unticked, deliberately.** 'Every new test is shown to fail against
the current code before the fix' is true of the bug-reproduction test but not of
`test_get_public_api_top_level_keeps_default_depth`, a no-regression guard for the
fourth criterion: pre-fix, a top-level package also built at `DEFAULT_MAX_DEPTH`, so the guard
passes on both sides by its nature. It was run pre-fix and its pass understood; ticking the box
as written would misstate that.

**Cross-file restatement sweep** (the last Risk): one further restatement found -
`specs/commands/inspect.md:76-77` restates the scope-of-validation rule for itself, and remains
true under the amendment (`inspect` is the default shape). The lazy-depth growth rule appears in
three files (`cache-refresh.md`, `qualified-name-semantics.md`, `inherits.md`), all agreeing and
cross-linked. No other stale restatement found; `specs/mcp/tools.md` restates CLI behaviour by
design, as the divergence ledger.

**Malformed-tail shapes are verified live, not by dedicated unit tests.** The audit re-run noted
the same: existing tests cover malformed roots and nonexistent tails, and a malformed tail takes
the identical code path to a nonexistent one. Coverage observation, not a divergence.

**Checkpoint accounting** (auto mode, decisions recorded in stage outputs): stage 01 gate
recorded with all four findings reproduced; stage 02 gate recorded with the pre-fix failure
demonstration; stage 03 step 3 discharged on evidence (260 passed, 0 failed - no gate), step 7
fired (tests and hooks green, run separately), step 10 fired (no divergence, no re-entry), step
12 discharged (step 10 produced no changes); stage 04 gates recorded in the documentation
report. The audit re-run reported 4/4 prior findings closed and zero new blocking findings.

## Follow-ups

- **Issue** [#28](https://github.com/andyrids/venv-axi/issues/28) - `find`'s result ordering
  contract is unspecified in `specs/commands/find.md` beyond the facade-path preference.
- **Issue** [#29](https://github.com/andyrids/venv-axi/issues/29) - MCP `showPackageApiTool`
  and `showModuleTool` emit a `help[]` footer under `docstring=true` where the CLI emits none,
  unlisted in `specs/mcp/tools.md` Divergences.
- **Issue** [#30](https://github.com/andyrids/venv-axi/issues/30) - the truncation suffix in
  `_introspect.py` `truncate()` hardcodes `--docstring`, a CLI flag spelling, and ships verbatim
  in MCP payloads.
- **Issue** [#31](https://github.com/andyrids/venv-axi/issues/31) - `findSymbolTool`'s empty
  hint names `listPackagesTool` without `include_dev=true`, while the CLI counterpart names
  `venvaxi list --all`.
- **Deferred to** - none.
- **Tracked as** - none.
