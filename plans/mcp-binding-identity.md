---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: done
depends: []
specs:
  - specs/mcp/tools.md
  - specs/commands/serve.md
authors:
  - specs/commands/home.md
issues: [46]
pr: 61
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

- [x] When `describeBindingTool` is called with the server's working directory inside a project, the
      tool shall report that project's resolved root, the serving venv and `status`, with both paths
      `~/`-prefixed when under the home directory.
      — `tests/test_core.py::test_resolve_binding_reports_root_venv_and_status`,
      `::test_format_path_prefixes_paths_under_home`,
      `::test_format_path_keeps_paths_outside_home_absolute`,
      `tests/test_mcp.py::test_describe_binding_tool_reports_binding`, and a live
      `StdioTransport` session where a root under `$HOME` rendered `~/`-prefixed and a venv on
      `D:` rendered absolute - both directions of the path rule observed
- [x] If no project root resolves from the server's working directory or from beside the venv, then
      `describeBindingTool` shall report `root: (no project root)` and return no error block.
      — `tests/test_core.py::test_resolve_binding_no_root_returns_marker`,
      `tests/test_mcp.py::test_describe_binding_tool_no_root_reports_marker`, and a live session
      from a rootless directory under an ephemeral tool venv, emitting the marker with the
      remaining fields and no `error: true` in the payload
- [x] If resolving the root raises anything other than a failure to find one, then
      `describeBindingTool` shall return the `Unexpected error:` block rather than the marker.
      — `tests/test_core.py::test_resolve_binding_unexpected_error_propagates`,
      `tests/test_mcp.py::test_describe_binding_tool_unexpected_error_returns_error_block`, both
      shown failing against a deliberately widened `except Exception` (`2 failed, 37 passed`)
      while every marker test still passed - see Notes
- [x] When `describeBindingTool` succeeds, the payload shall end with a `help[]` footer naming
      next-step tools by their camelCase names and no `venvaxi` shell spelling.
      — `tests/test_mcp.py::test_describe_binding_tool_footer_names_camel_case`, and the live
      session's `help[2]:` naming `listPackagesTool` with `include_dev=true` and `findSymbolTool`
- [x] When the registered command is spawned as an MCP stdio server, the `serve` command shall
      connect and advertise the nine tools in `specs/mcp/tools.md`.
      — a `fastmcp` `StdioTransport` client spawning the `command`/`args` read out of this repo's
      `.mcp.json`, whose live listing returned exactly the nine names in the spec's table with
      `describeBindingTool` first; unit
      `tests/test_mcp.py::test_build_server_registers_tools`
- [x] When the server starts, the `serve` command shall carry the bound project root and venv in the
      server's initialization instructions.
      — the `initialize` result's `instructions` read off a live client session, carrying `root:`
      and `venv:`; unit `tests/test_mcp.py::test_build_server_instructions_carry_binding`
- [x] If no project root resolves when the instructions are built, then the `serve` command shall
      start, serve the full tool surface, and carry the `(no project root)` marker in its
      instructions.
      — a live server started from a rootless directory under an ephemeral tool venv, serving all
      nine tools with the marker in its instructions; unit
      `tests/test_mcp.py::test_build_server_no_root_still_builds_with_marker`
- [x] When a client spawns the registered command from a second project's directory, the
      `describeBindingTool` shall report the second project's root alongside the registering
      project's venv.
      — a live `StdioTransport` session spawning the registered command with `cwd` in a throwaway
      second project, reporting that project's `root` beside
      the registering project's own `.venv`; in the same session
      `listPackagesTool(include_dev=true)` answered a plausible `count: 1` assembled from both
      halves with no signal of the mismatch
- [x] The registered description of `describeBindingTool` shall state that it identifies the project
      and venv the server answers from and that it is the tool to call first.
      — the description read off the live tool listing, not `__doc__`: "Identify the project and
      venv this server answers from." plus "Call this first: ..."; unit
      `tests/test_mcp.py::test_describe_binding_tool_description_is_call_first`

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

**The binding is two axes, and the issue only saw one.** #46 framed this as a single binding.
Reading `_core.py` and `_packages.py` showed two that resolve independently: `venv` is the serving
interpreter's `sys.prefix`, fixed when the client spawns the process; `root` is walked from that
process's working directory, which the client also chooses, and decides both which
`pyproject.toml` declares dependencies and which cache key the symbol graph lands under. Reporting
only the venv - which mirroring the home view would have done - leaves the half that selects the
answer invisible. Verified at stage 03 rather than argued: spawning the registered command with
`cwd` in a second project reports that project's `root` beside this one's `venv`, and
`listPackagesTool` then answers a confident `count: 1` assembled from both halves.

Worth recording that the *observed* `mpctraj` incident never showed this. There both axes agreed,
and the failure was simply that neither was stated. The divergence case was derived from the code
and only reproduced afterwards. Had the design followed the observation rather than the source, it
would have shipped a tool reporting one axis and would have looked correct.

**Why option 2 was rejected, honestly.** The issue offered a `project:`/`venv:` line on
`listPackagesTool`. The argument used against it at stage 01 - that it only helps a caller who
thought to call `list` - is symmetric and does not survive contact: option 1 only helps a caller
who thought to call the ninth tool, and option 2 is the one option that would have caught the
observed incident with the agent doing nothing differently. It was rejected on
[principle 2, minimal default schemas](../specs/principles.md#principle-2-minimal-default-schemas)
and because identity on one of eight tools protects only that tool. The guaranteed-ambient channel
turned out to be neither option: it is the registered tool description, which the harness keeps in
context without a call, and which `docs/architecture.md` already named. Authoring it deliberately
is why the spec makes it contract rather than leaving it a docstring.

**The degrade is one keyword wide, and that keyword is the whole feature.** `resolve_binding`
catches `ProjectRootNotFoundError` exactly. A broad `except Exception` passes every other test in
the suite and converts an unreadable or deleted working directory into a confident
`(no project root)` - a wrong answer wearing the shape of a right one, which is the failure class
this plan exists to remove. Both discriminating tests were shown failing against the widened arm
before being trusted, at stage 02 and again independently at stage 03.

**The marker is close to diagnostic of a `uvx` registration.** `get_project_root` falls back to
`sys.prefix.parent`, and a conventional in-project `.venv` has the project root as its parent - so
for a normally installed venv-axi the marker is unreachable from *any* working directory,
confirmed by running `resolve_binding` from a verified rootless directory and still getting the
repo back. Reaching it live needed an ephemeral tool venv. That is the case
[`plans/mcp-registration-module-form.md`](mcp-registration-module-form.md) handed to #46, so the
degraded path is not a contrived edge - it is the shape of the misregistration the report exists
to expose.

**`serve` degrades through the same helper, and that was a late catch.** The first draft specified
the degrade for the tool only. Building the instructions calls the same resolution at server
construction, so an unresolvable root would have killed `venvaxi serve` at startup - in precisely
the misconfiguration the feature exists to diagnose, presenting as a server that will not connect
rather than a server bound to nothing. Caught in stage 01 review before any code existed.

**The instructions clause is worded as an obligation to advertise, not to be read.** `fastmcp`
3.4.6 takes `instructions: str | None` and serializes it into the `initialize` result - checked
against the installed version through the AXI itself, and read back off a live client. Whether any
client puts that string in front of a model cannot be established from this repo, the package or
the MCP specification, which leaves client use optional. So the tool carries the guarantee and the
instructions are the half that costs nothing when it happens to work. A future verification
reporting "the instructions reached the agent" has proven something about one client.

**`home.md` kept its Never but lost its reason.** The old wording said reaching for the project
root would break the view's broken-project guarantee. The degrading design is a working
counterexample. Rather than leave a rule standing on a falsified justification - the decay
`reference-standard-spec.md` warns about - the entry was split and re-founded: the root is
derivable from a CLI caller's own working directory, so it tells them nothing, while an MCP caller
chose neither the directory nor the interpreter. Also worth knowing: no CLI command reports the
resolved root either, so the issue's claim that the binding is fully discoverable via the CLI
holds for the venv axis only.

**Five tests were moved out of `test_mcp.py` after the stage 02 gate.** `format_path` and
`resolve_binding` are plain `_core` helpers, but their tests were written into a module opening
with `pytest.importorskip("fastmcp")` - gating them, and the criterion-3 discriminator among them,
on an unrelated extra. Not an active gap, since `fastmcp` sits in the `dev` group and CI always
installs it, but the reasoning that made it safe is the reasoning that leaves gaps. Moved to
`tests/test_core.py` and proven with `fastmcp` made unfindable: 5 pass there, `test_mcp.py` skips
wholesale. Before the move all five went with it.

**A `git checkout --` during verification briefly wiped this branch's uncommitted `_core.py`.**
Restoring the widened-catch experiment that way reverts to HEAD, and stage 02 was still
uncommitted. The file was restored from a capture and checked three ways. Nothing was lost, but
the run carried uncommitted work across three stages, which is what made a routine revert
dangerous. Commit at the stage boundary next time.

## Follow-ups

- **Issue [#60](https://github.com/andyrids/venv-axi/issues/60)** - opened during this run.
  `format_error` hardcodes a `Run venvaxi --help` footer that `_toon_errors` routes onto the MCP
  surface, contradicting the Hint wording rule in the same spec this plan amended. The new tool
  inherits it. Pre-existing and orthogonal, so it was filed rather than folded in; the
  criterion-3 tests assert on `error: true` and `Unexpected error:` only, never the footer, so
  they do not enshrine it. Fixing it needs the Error shape block in
  `specs/behaviors/output-contract.md` amended first, which is its own stage 01.
- **Issue [#49](https://github.com/andyrids/venv-axi/issues/49)** - cache state remains unowned.
  `specs/mcp/tools.md` Out of scope now names this tool as where it lands, so a future spec
  extends the binding report rather than adding a tenth tool.
- **Tracked as** - no live evidence that any MCP client surfaces `instructions` to a model. The
  server advertises it and that is what the spec obliges; the gap is recorded here rather than
  pretended shut. No issue filed - it is a fact about clients, not a defect in this repo.
- **Tracked as** - `get_project_root`'s fallback and raise (`_core.py:47-52`) have no direct test
  coverage, which is why `_core.py` sits at 88% against a 98% total. Pre-existing: from any
  working directory inside the repo the first loop returns before reaching them. Not this plan's
  scope, noted because this run is what made the lines interesting.
- **None deferred** - no `Deferred to` entries, so no downstream plan required absorption in this
  commit.
