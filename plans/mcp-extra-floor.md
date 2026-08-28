---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/commands/serve.md
authors: []
issues: [96]
pr:
---

# Plan: Bound the `mcp` extra's `fastmcp` range

## Scope

`pyproject.toml` declares the `mcp` extra as `fastmcp>=0.1.0`, the `dev` group repeats the same
floor, and `prek.toml` repeats it a third time as the type-check hook's `additional_dependencies`.
That range admits every `fastmcp` release ever published - four majors, 96 stable versions - and the
code cannot run against most of them.

`build_server` registers each tool by passing the handler positionally alongside a `name` keyword
(`src/venvaxi/_mcp.py`), which requires `FastMCP.tool`'s first parameter to be `name_or_fn`. It also
constructs `FastMCP(..., instructions=...)` and calls `server.run()`. A release that does not
satisfy all three cannot serve.

`uv.lock` hides the exposure by pinning 3.4.6. It is visible to anyone resolving without the lock:
`pip install venv-axi[mcp]` into an environment that already satisfies `>=0.1.0` with something
older, or any resolver working under a constraint that prefers a lower match. Every `fastmcp`
release back to `0.1.0` declares `requires-python >=3.10`, so a modern interpreter does not screen
the old ones out.

`specs/principles.md` Zero runtime dependencies makes this the whole exposure:
`project.dependencies` is empty by design, so the `mcp` extra is the only dependency surface the
project has, and nothing bounded it.

This unit changes the declared range to `fastmcp>=3.4,<4` in all three declarations, re-resolves
the lock, and brings the two documents that state the number in prose into line.

**Out of scope**: verifying the declared floor in CI. Nothing exercises the declared range today -
CI runs only the locked 3.4.6 - so the new number is a declaration checked by review, exactly like
the old one. Closing that is real scope of its own (a job, and a lowest-direct resolution strategy)
and is filed rather than folded in.

## Implements

`specs/commands/serve.md` - the Data requirements section, which states the extra's requirement
verbatim and is what `pyproject.toml` must conform to. The spec is amended in stage 01 and the
packaging metadata is brought into conformance with it, which is why it sits in `specs:` rather
than `authors:`: the conformance claim is the stronger one and subsumes the authorship.

No other spec moves. `specs/principles.md` Zero runtime dependencies already supplies the reasoning
for why a bound matters here and needs no amendment - it is cited by the amended passage, not
changed.

## Approach

1. Amend `specs/commands/serve.md` Data requirements to declare `fastmcp>=3.4,<4`, stating why both
   bounds are load-bearing and adding the `If <trigger>, then` clause for an out-of-range
   environment. Run the ripple check in `specs/README.md`.
2. `pyproject.toml` - `[project.optional-dependencies] mcp` and the `dev` dependency group both move
   to `fastmcp>=3.4,<4`. They are the same package pinned for the same reason; leaving the dev group
   behind would relocate the unbounded range rather than close it.
3. `prek.toml` - the `pkgdx-typing` hook's `additional_dependencies` declares the same package for
   the same reason, and issue #113 has just put that hook into CI. Leaving it unbounded would let
   the type checker resolve a `fastmcp` the project does not declare.
4. Re-resolve `uv.lock` with `uv lock`. Confirm the diff is confined to what the constraint change
   forces - a lock that moves unrelated transitive packages is a second change riding along.
5. `docs/architecture.md` states the floor in its Optional extras line and would otherwise go stale
   against the spec. Update it to match.
6. Demonstrate the defect and the fix at the resolver, not by inspection: show that a constraint
   pinning an old `fastmcp` resolves successfully against the current declaration and is refused
   against the new one.
7. `CHANGELOG.md` under `[Unreleased]`. This is a `Changed` entry that narrows a published
   requirement, so it says so plainly rather than describing only the fix.

## Validation

- [ ] Every declaration of `fastmcp` in the repository's own configuration shall state
      `fastmcp>=3.4,<4` - the `mcp` extra, the `dev` dependency group, and the type-check hook's
      `additional_dependencies`.
- [ ] If a resolver is constrained to a `fastmcp` below the declared floor, then resolving
      `venv-axi[mcp]` shall fail rather than install a version `build_server` cannot call.
- [ ] When the lock is re-resolved, it shall record a `fastmcp` version inside the declared range,
      and shall not move packages the constraint change does not force.
- [ ] When `build_server` runs against the locked `fastmcp`, it shall register every tool without
      raising.
- [ ] The floor stated in `specs/commands/serve.md` and in `docs/architecture.md` shall be the same
      range `pyproject.toml` declares.

## Risks / unknowns

- **This narrows a published requirement, and someone may be relying on the old one.** Anyone whose
  environment resolves `venv-axi[mcp]` to a `fastmcp` below 3.4 will now be refused at install. That
  is the point rather than a side effect - the code could not serve on those versions, so the old
  declaration was false, not permissive - but it is a real behaviour change for a consumer and the
  changelog entry must say so. The project is pre-1.0, which is what makes it affordable now.
- **`3.4` is deliberately higher than the measured lower bound.** Probing all three call shapes in
  isolated environments put the true boundary at `2.11.3`. `3.4` was chosen over it because the
  lock, CI and the conformance tier only ever exercise 3.4.6, and declaring `>=2.11.3` would claim
  support across roughly sixty releases nothing runs. Recorded here so a future reader knows the
  gap is a decision, not an oversight.
- **The cap needs deliberate maintenance.** When `fastmcp` 4 ships, `venv-axi[mcp]` will refuse it
  until someone widens the range, including in the case where the code would have run fine. That
  cost is accepted in exchange for not learning about an incompatible major from a bug report.
- **The declared range is still unverified.** No automated check resolves the extra at its floor.
  This unit replaces a false declaration with a true one; it does not make the declaration
  self-checking.
- **Unknown: whether the `2.4.0` to `2.11.2` band fails on API or on environment.** Those versions
  could not be imported at all in a current resolve (pydantic drift, missing `pydantic_settings`),
  so the `name_or_fn` boundary inside that band was not measurable. It does not affect the chosen
  floor, which sits well above it.

## Notes

**Re-entry to stage 01, recorded per `ICM/process-plan/CONTEXT.md`.** Stage 03 verification found a
third declaration of the same unbounded floor that issue #96, this plan's original Scope and the
techspec had all missed: `prek.toml:22`, the `pkgdx-typing` hook's `additional_dependencies`. It is
a live declaration - it is what installs `fastmcp` into the type-check hook's isolated environment.
Issue #113 put that hook into CI in the immediately preceding unit, so the type check now runs on
every pull request against a `fastmcp` resolved from an unbounded range while the project declares
`>=3.4,<4`. A fresh resolve picks the newest release and the two agree, which is why this would
fail quietly rather than loudly.

The re-entry re-ran only the delta: Scope and Approach widened to three declarations, Validation
criterion 1 reworded to name all three, `prek.toml` amended, and stage 03 re-run. Criterion 1 was
reworded during the re-entry rather than at closeout, which is where
`ICM/_config/reference-standard-validation.md` says a criterion may be reworded without breaking the
mapping between report and plan.

Two false positives were checked and dismissed in the same sweep: `src/venvaxi/_packages.py:43`
uses `"fastmcp>=0.1.0"` as a docstring example of a PEP 508 string, and `tests/test_packages.py:24`
uses it as a parametrize case for name extraction. Neither is a declaration; both correctly stay.

**A spec clause was reworded in the same re-entry.** Stage 01 originally wrote the out-of-range case
as `If the installed fastmcp is outside the declared range, then ...`.
`ICM/_config/reference-standard-validation.md` states that every `If <trigger>, then` in a spec is a
criterion naming a run that must be shown failing safely - and this clause named no observable
response, because it disclaims scope rather than requiring behaviour. It was a scope statement
wearing the unwanted-behaviour grammar, and would have read to a future drift audit as a criterion
that cannot fail. Reworded to plain prose, with the content unchanged.

## Follow-ups
