---
context-hierarchy: Layer 3
context-hierarchy-role: Work in flight
---

# Plans

`specs/` describes **state** - what should be true, forever. `plans/` describes **motion** - how
we are getting there next.

One file per unit of work, `plans/<slug>.md`, using the same kebab-case slug the ICM stage
artifacts share (`ICM/_config/reference-standard-naming.md`).

Plans are temporal. Once merged they **freeze** as historical record: the merged PR link plus the
completed validation checklist is the project's working memory of what got built, how, and what
was deferred.

## This is the Planning System

`plans/` is not a substitute for, and is not substituted by, an agent's built-in plan mode. An
ephemeral plan evaporates when the turn ends, leaving no record. If a scratchpad is used to
think, the artifact still lands here.

The classic failure: drafting an ad-hoc plan of "write spec X, then build it", doing exactly
that, and leaving behind neither a reviewed spec change nor a plan file. Split it - the spec
change goes through `specs/`, and the work to execute it gets a file here.

Even small work leaves a plan. Skipping it because a change is "quick" is what hollows the record
out.

No DAG drawing or status table is maintained in this file - both rot the moment someone forgets
to update them. Query the frontmatter instead:

```sh
grep -l 'status: planned' plans/*.md            # what could be started
grep -l 'specs/commands/<verb>.md' plans/*.md   # what a spec change ripples into
```

Use a placeholder when documenting these queries - a real spec path written into prose here
makes this file a false positive in every ripple check that greps for it.

## Frontmatter

```yaml
---
status: planned        # planned | in-progress | done | blocked | cancelled
depends: []            # other plan slugs that must land first
specs:                 # spec files this plan brings code into conformance with
  - specs/commands/<verb>.md
issues: []             # issue numbers
pr:                    # PR number, set at closeout
---
```

## Body

Fixed section order: **Scope**, **Implements**, **Approach**, **Validation**, **Risks /
unknowns**, **Notes**, **Follow-ups**.

`Validation` is load-bearing - it is the checkbox list that converts `in-progress` to `done`, and
it supplies the requirement identifiers the ICM verification stage reports against. `Notes` and
`Follow-ups` stay empty until closeout.

## Status Lifecycle

```text
planned -> in-progress -> done      (frozen; edit only to correct the record)
                       -> blocked
                       -> cancelled
```

## Closeout

The last commit before merge:

1. Flip `status` to `done` and add `pr:`.
2. Tick validation boxes **only where verified**. Leave unverified boxes unticked and say why in
   Notes - a ticked box that was not checked is worse than an unticked one.
3. Populate Notes: decisions, gotchas, version pins.
4. Populate Follow-ups using the taxonomy below.
5. Absorb any deferrals (see below).
6. Reconcile `specs/` - if the implementation diverged, fix the code or amend the spec.

## Follow-ups Taxonomy

- **Issue `[#N](link)`** - actionable, but owned by no current plan.
- **Deferred to `[<plan>](<plan>.md)`** - work an unstarted downstream plan will absorb.
- **Tracked as** - external dependencies that are neither issue nor plan.
- **None** - state this explicitly. Silence is ambiguous.

## Deferral Absorption

A `Deferred to` entry MUST, **in the same commit**, edit the named downstream plan to absorb it -
typically a bullet in its Approach plus a new Validation criterion, cross-linked back.

Without this the deferral is a non-binding pointer the downstream plan can ignore, and the work
is silently lost between two documents that each assume the other owns it.
