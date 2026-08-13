---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends:
  - plan-record-repair
specs: []
authors:
  - specs/commands/find.md
issues: [28]
pr: 34
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

- [x] When a query exactly matches a symbol name, ignoring case, the `find` command shall return
      that symbol before any symbol matching only by prefix. —
      `tests/test_find_ordering.py::test_find_orders_exact_name_match_before_prefix_match`
      on both backends; the query differs in case from the name, so 'ignoring case' is exercised
- [x] When a query matches one symbol name by prefix and another only within its docstring, the
      `find` command shall return the prefix match first. —
      `tests/test_find_ordering.py::test_find_orders_prefix_match_before_docstring_only_match`.
      FTS path only - the `LIKE` backend never matches docstring text, so the criterion is
      vacuous there rather than uncovered
- [x] When two matched symbols differ only in kind, the `find` command shall return the `class` or
      `function` before the other kind. —
      `tests/test_find_ordering.py::test_find_orders_class_kind_before_module_kind` on both
      backends
- [x] When two matched symbols are tied on name match and kind, the `find` command shall return
      the one with the shorter `qualified_name` first. —
      `tests/test_find_ordering.py::test_find_orders_shorter_qualified_name_first` on both
      backends
- [x] When two matched symbols are tied on every earlier key, the `find` command shall return them
      ordered by `qualified_name` ascending. —
      `tests/test_find_ordering.py::test_find_breaks_final_ties_on_qualified_name_ascending`
      on both backends
- [x] When the same query is run twice against an unchanged graph, the `find` command shall return
      identical rows in identical order. —
      `tests/test_find_ordering.py::test_find_repeats_identical_rows_in_identical_order` on
      both backends
- [x] The test suite shall pass. —
      `uv run coverage run -m pytest` reports `293 passed in 28.73s`

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

**Why one gap is declared unspecified rather than closed.** The two search paths share four of the
five keys; the FTS backend interposes a `bm25()` relevance score between kind and length, and the
substring backend has none to offer. Three answers were available: declare the FTS order as the
contract and make the fallback non-conforming, strip relevance to force agreement, or write the
gap down. The third was chosen because the first two both change behaviour to make a document
tidier. 'Unspecified' is a safe answer only where it is recorded as a decision - left silent, a
caller discovers it as a bug.

**Declaring an order freezes it.** A future ranking improvement now needs a spec amendment rather
than a quiet query edit. That is the intended cost. The alternative - the state this plan found -
is a contract an agent cannot rely on and an implementation nobody may change confidently either,
which is the worst of both.

**`authors:`, not `specs:`, and it matters.** The code already conformed; the spec was written to
describe it. Listing `find.md` in `specs:` would have made stage 03 verify a code conformance this
plan never delivered, and verification duly discharged its spec-comparison step vacuously - which
is announced in the report rather than left to read as a clean pass.

**The tests were shown to discriminate.** Each query was re-run with its targeted `ORDER BY` key
removed, and all six orders flip. Without that check a fixture can pass because an unrelated key
happens to sort it correctly, which is the failure mode the Risks section names. The scratch
harness was not retained - the property it established is recorded here instead.

**The unspecified gap is routed around, not asserted.** The key-4 and key-5 fixtures carry
identical FTS token statistics, so `bm25` ties exactly and the key under test breaks the tie on
that path too. This was the constraint most likely to be violated invisibly: a test reading order
inside the gap would have made one backend's behaviour the contract by the back door, silently
undoing the decision above.

**Key 2 is FTS-only, and that is a property of the criterion.** The `LIKE` backend matches `name`
and `qualified_name` and never docstring text, so a docstring-only hit cannot exist there. Not a
coverage gap - a criterion with no observable form on one path.

**Fixtures are seeded through `SymbolStore.upsert_node`.** That is the production write API, and
the read path under test is the shipped SQL, so nothing about the ordering is simulated. Walking
an on-disk fake package would not give per-key control of `name`, `kind`, `doc` and
`qualified_name`, which is what isolating one sort key at a time requires.

## Follow-ups

- **Issue** [#20](https://github.com/andyrids/venv-axi/issues/20) - the PyMarkdown tokenizer crash
  stays open with its workaround; untouched here.
- **Deferred to** - none.
- **Tracked as** - none.
