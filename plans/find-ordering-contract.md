---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends:
  - plan-record-repair
specs: []
authors:
  - specs/commands/find.md
issues: [28]
pr:
---

# Plan: Find result ordering contract

## Scope

Write down the result ordering `find` already implements.
[#28](https://github.com/andyrids/venv-axi/issues/28) - `specs/commands/find.md` declared one
preference, short facade paths over home paths, and said nothing about the four other sort keys the
query actually applies. Two implementations could order ties differently and both conform, and
v0.1.0 freezes `specs/` as the public contract.

The code is already deterministic and already correct; nothing under `src/` changes. What is
missing is the declaration, plus a test that keeps it honest.

Out of scope: changing the order. This plan records what is, and no key moves. Also out of scope:
cross-package relevance weighting, which `## Out of scope` in the spec already rules out.

## Implements

Nothing. This plan authors `specs/commands/find.md`, which is why it sits in `authors:` and not in
`specs:` - listing it in `specs:` would make stage 03 verify a code conformance this plan never
delivers, the trap `plans/README.md` records the methodology walking into on first use.

The amendment declares a five-key total order, and declares one gap in it as unspecified rather
than leaving the whole contract open. The two search paths differ only inside that gap, so both
conform without either being described as the reference implementation.

## Approach

1. Flip to `status: in-progress`.
2. The spec amendment is written and is the stage 01 output; nothing further is authored here.
3. Add a regression test asserting the deterministic keys against a fixture graph built to exercise
   each one - a symbol matching the query exactly, one matching by prefix, one matching only in its
   docstring, a `class` and a non-`class` at equal name distance, and two qualified names differing
   only in length and then only lexically.
4. Assert **repeatability** explicitly: the same query run twice returns identical rows in
   identical order. That is the property key 5 exists for and the one an agent depends on.
5. Do not assert anything about the relevance gap between keys 3 and 4. A test written there would
   pin one backend's behaviour as the contract, which is precisely what the spec declines to do.
6. `CHANGELOG.md` entry under `Changed` - the contract is newly stated, not newly true.

## Validation

- [ ] When a query exactly matches a symbol name, ignoring case, the `find` command shall return
      that symbol before any symbol matching only by prefix.
- [ ] When a query matches one symbol name by prefix and another only within its docstring, the
      `find` command shall return the prefix match first.
- [ ] When two matched symbols differ only in kind, the `find` command shall return the `class` or
      `function` before the other kind.
- [ ] When two matched symbols are tied on name match and kind, the `find` command shall return
      the one with the shorter `qualified_name` first.
- [ ] When two matched symbols are tied on every earlier key, the `find` command shall return them
      ordered by `qualified_name` ascending.
- [ ] When the same query is run twice against an unchanged graph, the `find` command shall return
      identical rows in identical order.
- [ ] The test suite shall pass.

## Risks / unknowns

- Declaring an order freezes it. A future ranking improvement now needs a spec amendment rather
  than a quiet query edit - which is the intended cost, not a side effect, and is what makes the
  declaration worth having.
- A fixture graph that accidentally ties on fewer keys than intended produces tests that pass for
  the wrong reason. Each criterion above names the keys it holds constant, so the fixture is built
  to the criterion rather than the criterion fitted to a convenient fixture.
- The unspecified gap is a real hole a caller could fall into. It is bounded to results tied on
  keys 1 to 3 and equal in `qualified_name` length, and the spec says so in the same paragraph that
  declares it, so the hole is documented rather than latent.

## Notes

## Follow-ups
