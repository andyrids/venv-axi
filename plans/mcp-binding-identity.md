---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/mcp/tools.md
  - specs/commands/serve.md
authors:
  - specs/commands/home.md
issues: [46]
pr:
---

# Plan: The MCP surface reports its binding

## Scope

An agent with a `VenvAXI` MCP server connected cannot learn which project root and venv that server
answers from. All eight tools answer as if the binding were self-evident and none names it, so a
server pointed at the wrong environment returns well-formed, plausible, wrong-project signatures -
the exact staleness the AXI exists to eliminate, arriving with no error, no empty state and no
warning.

Observed live in the `0.3.0rc1` agent-perspective evaluation against a consuming project: the
session's working context was `mpctraj` while the connected server was the one this repo's
`.mcp.json` registered, and `listPackagesTool(include_dev=true)` answered with venv-axi's own dev
dependencies. Nothing in the payload signalled the mismatch. The workflow that produces it is
ordinary - developing venv-axi in one checkout with a consuming project open in another, or any
session inheriting an `.mcp.json` from a directory it is not working in.

Add a ninth tool that reports the binding, set the server's initialization instructions to the same
facts, and author the tool's registered description as the call-me-first signal.

Out of scope: what the cached symbol graph holds - built version and built depth - which is a
correct-binding-serving-a-stale-graph failure owned by
[#49](https://github.com/andyrids/venv-axi/issues/49) and now declared in `specs/mcp/tools.md` Out
of scope as landing on this tool; and the CLI error footer leaking onto the MCP surface, a
pre-existing divergence filed as [#60](https://github.com/andyrids/venv-axi/issues/60).

## Implements

`specs/mcp/tools.md` - the ninth tool's full contract, which lives there rather than in
`specs/commands/` because it mirrors no CLI command. The amendment also moves the consolidation
rationale, the tool table, the count, a Divergences entry covering the whole tool, and the cache
state boundary. This plan writes that content and brings code into conformance with it, which
`plans/README.md` resolves in favour of `specs:`.

`specs/commands/serve.md` - the instructions clause and its unresolvable-root failure mode. Note
that [`plans/mcp-registration-module-form.md`](mcp-registration-module-form.md) put this same file
in `authors:`; there the amendment declared an equivalence that already held and no code moved.
Here code moves for it, so `specs:` is correct. The difference is deliberate.

`specs/commands/home.md` is under `authors:`. Its Never on project-root lookup stands and no
behaviour changes; what changes is the reason given for it. The old wording said a root lookup would
break the view's broken-project guarantee, and this plan's own degrading design is a working
counterexample to that claim. The Never is re-founded on the reason that survives - the root tells a
CLI caller something they already know - so the next reader is not left applying a rule whose stated
justification has been falsified next door.

## Approach

1. Flip to `status: in-progress`.
2. Amend `specs/mcp/tools.md`, `specs/commands/serve.md` and `specs/commands/home.md` per
   Implements, and run the ripple check in `specs/README.md`. (Done at authoring: the broad grep
   returns 6 plans for `tools.md`, 2 for `serve.md` and 3 for `home.md`; the frontmatter coverage
   check returns 3, 2 and 2. Every one is `status: done` and frozen, so this is disclosure, not
   edits.)
3. Promote `_format_path` out of `_cli.py` into `_core.py` and call it from both surfaces. It must
   be shared, not reimplemented, or the two surfaces drift on `~/` rendering.
4. Add `describe_binding_tool` to `_mcp.py`, registered first in `_TOOLS` so it heads the advertised
   surface. Resolve the root through a helper that returns the marker on
   `ProjectRootNotFoundError` and lets every other exception through to `_toon_errors`. Author the
   docstring as the registered description per the spec, not as an afterthought.
5. Wire the same helper into `build_server`, passing `instructions=` to the `FastMCP` constructor.
6. Update the count and the tool table at every site: `tests/test_mcp.py` (both the set assertion
   and the docstring that says "eight"), `src/venvaxi/SKILL.md` then `just skill-sync`, and
   `README.md`.
7. Add a wrong-binding gotcha to `src/venvaxi/SKILL.md` and an eval specimen for it.
8. `docs/architecture.md` - one line for the instructions wiring, in the ambient-context section
   that already names tool descriptions as an ambient channel.
9. `CHANGELOG.md` - `Added` for the tool and the instructions.

Implementation for stages 02 to 04 is dispatched to a Fable agent, per the run's standing
direction. Recorded here because the instruction was given in conversation and would otherwise not
survive it.

## Validation

- [ ] When `describeBindingTool` is called with the server's working directory inside a project, the
      tool shall report that project's resolved root, the serving venv and `status`, with both paths
      `~/`-prefixed when under the home directory.
- [ ] If no project root resolves from the server's working directory or from beside the venv, then
      `describeBindingTool` shall report `root: (no project root)` and return no error block.
- [ ] If resolving the root raises anything other than a failure to find one, then
      `describeBindingTool` shall return the `Unexpected error:` block rather than the marker.
- [ ] When `describeBindingTool` succeeds, the payload shall end with a `help[]` footer naming
      next-step tools by their camelCase names and no `venvaxi` shell spelling.
- [ ] When the registered command is spawned as an MCP stdio server, the `serve` command shall
      connect and advertise the nine tools in `specs/mcp/tools.md`.
- [ ] When the server starts, the `serve` command shall carry the bound project root and venv in the
      server's initialization instructions.
- [ ] If no project root resolves when the instructions are built, then the `serve` command shall
      start, serve the full tool surface, and carry the `(no project root)` marker in its
      instructions.
- [ ] When a client spawns the registered command from a second project's directory, the
      `describeBindingTool` shall report the second project's root alongside the registering
      project's venv.
- [ ] The registered description of `describeBindingTool` shall state that it identifies the project
      and venv the server answers from and that it is the tool to call first.

## Risks / unknowns

- **Whether any client shows the instructions to a model cannot be established here.** `fastmcp`
  3.4.6 accepts `instructions: str | None` and serializes it into the `initialize` result - verified
  against the installed version - but the MCP specification leaves client use optional, and neither
  the repo nor the package can answer what a given harness does with it. This is why the spec is
  worded as an obligation to advertise and why the tool, not the instructions, carries the
  guarantee. A verification pass that reports "the instructions reached the agent" has proven
  something about one client, not about this clause.
- **The degraded path is close to diagnostic of a `uvx` registration, which is what makes it
  testable.** `get_project_root` raises only when no ancestor of the working directory holds a
  `pyproject.toml` and the venv's parent holds none either. A conventional in-project `.venv` has
  the project root as its parent and always resolves, so the marker essentially means an ephemeral
  or tool-venv interpreter - the case
  [`plans/mcp-registration-module-form.md`](mcp-registration-module-form.md) handed to #46. Stage 03
  gets a real reproduction rather than a contrived rootless directory.
- **A wide `except` around root resolution would silently eat a real fault.** Only the
  failure-to-find-one may become the marker; an unreadable or deleted working directory must stay
  the `Unexpected error:` block. The two paths are one keyword apart and the wrong one looks
  correct in every ordinary test, so the third Validation criterion exists to discriminate them.
- **The tool count is enumerated in more sites than files.** Six files carry it and
  `specs/mcp/tools.md` alone spelled it four times; `tests/test_mcp.py` carries it in both an
  assertion and a docstring. Updating five of six leaves a green test asserting the old surface,
  which is the failure that would make this change look complete when it is not.
- **The new tool inherits a live spec violation through `_toon_errors`.** `format_error` hardcodes
  a help footer naming `venvaxi --help`, which reaches the MCP surface and contradicts the Hint
  wording rule in `specs/mcp/tools.md`. Filed as
  [#60](https://github.com/andyrids/venv-axi/issues/60) rather than fixed here - it needs an
  amendment to the Error shape block in `specs/behaviors/output-contract.md` first, which is its
  own stage 01. The error-shape criterion above is worded so that it does not enshrine the wrong
  footer as expected output.
- **`inactive` means something different over MCP and the skill does not say so.** On the CLI it is
  a caller who has not activated a venv; over MCP, where `setup` registers the venv's own
  interpreter, it means the registered command names a base interpreter. The spec carries the
  gloss; whether the skill needs it is decided against the earns-its-place bar in
  `specs/behaviors/skill-content.md`, not by default.

## Notes

## Follow-ups
