---
context-hierarchy: Layer 4
context-hierarchy-role: Working artifact
immutable: false
status: in-progress
depends: []
specs:
  - specs/commands/home.md
  - specs/mcp/tools.md
  - specs/behaviors/skill-content.md
authors: []
issues: [81]
pr:
---

# Plan: version-probe

## Scope

Neither surface reports `venvaxi`'s own version, and the conventional probe an agent reaches for
makes the gap worse than a plain missing flag: `-v` is `--verbose`, so `venvaxi -v` parses, enables
DEBUG logging, falls through to the home view, and exits `0` with a plausible-looking block that
contains no version - byte-identical to bare `venvaxi`. Nothing in that output tells the caller its
question went unanswered. [Issue #81](https://github.com/andyrids/venv-axi/issues/81) files this,
found while evaluating `0.3.2` from the `mpctraj` testbed; it is not a `0.3.2` regression and
predates the release.

**Decision: resolutions 1 and 2 from the issue, together** - a CLI `--version` flag and a `version`
field on `describeBindingTool`. They serve different callers - a human or a bug reporter reaches
for `--version`; an MCP-only agent has no shell to fall back to - and neither substitutes for the
other. **Resolution 3 - adding version to the home command's output block - is explicitly declined**
for this plan; see `specs/commands/home.md`'s new Out of scope entry for why.

**`--version` emits TOON, not bare text.**
[`specs/behaviors/output-contract.md`](../specs/behaviors/output-contract.md)'s Rule is
unconditional - 'Every command writes TOON to STDOUT and nothing else' - applying to 'Every CLI
command'. Argparse's built-in `action="version"` prints a bare string and exits without going
through venvaxi's own output path, which would diverge from the contract on arrival. The declared
output is exactly:

```text
$ venvaxi --version
version: 0.5.0
-> EXIT:0
```

No `help[]` footer - there is no next step to disclose, and manufacturing one to keep the shape
constant is exactly what
[Contextual disclosure](../specs/behaviors/output-contract.md#contextual-disclosure) forbids. No
exemption clause is added to `output-contract.md`; the contract stays unconditional, and
`--version` is shown to conform to it rather than carved out of it.

**`-v` stays `--verbose`, unchanged.** Issue #81 is explicit that the flag letter is not the
defect - `-v` is wired correctly to `--verbose` today. No `-V` short form is added; it was not
asked for and is not needed to close the issue. See `specs/commands/home.md`'s new Out of scope
entries.

**No new spec file.** `specs/commands/home.md` and `specs/mcp/tools.md` are amended in place.
Considered and rejected: a new `specs/behaviors/*.md` file. `specs/behaviors/` is for invariants
spanning several commands, and the promotion trigger in
[`reference-standard-spec.md`](../ICM/_config/reference-standard-spec.md) is a *second* spec
needing the same shape, not the first - this is the identical reasoning
[`installed-package-visibility`](installed-package-visibility.md) used declining to amend
`output-contract.md` for its own second-aggregate shape, applied here to declining a whole new
file for a two-surface capability that fits cleanly inside the two files it already touches.

**A load-bearing edge case: unavailable package metadata.** `src/venvaxi/__init__.py` currently
binds `__version__` **inside** `contextlib.suppress(metadata.PackageNotFoundError)`. From an
uninstalled source tree the name is undefined - `venvaxi.__version__` raises `AttributeError`, not
`""` - and it is absent from `__all__`. Both surfaces must survive this without crashing. Decision:
each surface reports the definitive empty state marker `version: (no version metadata)` rather than
raising, matching the house pattern (`(no project root)` in `specs/mcp/tools.md`, `(no docstring)`
in `specs/behaviors/output-contract.md`). See both specs' new Failure modes clauses.

**The MCP parity obligation.** `specs/mcp/tools.md`'s Local principle - 'a new CLI capability MUST
either gain an MCP tool or gain an entry in Divergences explaining why not' - is triggered by
`--version`. The `version` field on `describeBindingTool` discharges it, reported **first**, ahead
of `root`, `venv` and `status`, because the server identifies itself before naming the binding it
speaks for. The existing `## Divergences from the CLI` entry for `describeBindingTool` called the
cache summary 'the one exception to no CLI counterpart of any shape' - true when written, false the
moment `version` gains a real CLI equivalent too. That sentence is rewritten to name both
exceptions rather than deleted, the same repair
[`cache-state-report`](cache-state-report.md)'s Notes made to the Failure modes 'scoped to that
trigger alone' sentence when a second degrade trigger appeared.

**The registered `describeBindingTool` description is amended too.** Its docstring is the
registered MCP description and `specs/mcp/tools.md` makes it part of the contract; the description
already states the report includes the cache summary, and `version` is a comparable new capability
by the same reasoning - it is the field the report now leads with. `specs/mcp/tools.md`'s
`### The description is part of the contract` gains a one-line requirement to match.

Out of scope, stated so the boundary is not assumed: a `-V` short flag (above); `version` on the
home view's output block (above, resolution 3); `--version` on any subcommand parser - the issue
and both resolutions concern the top-level probe only; a build timestamp or commit hash alongside
the version string - `importlib.metadata.version("venv-axi")` reports the installed distribution
version and nothing else, and neither resolution asked for more.

## Implements

`specs/commands/home.md` - `## Invocation / inputs` gains `--version` in the usage line and a
sentence stating it short-circuits every other input ahead of subcommand dispatch. `## Outputs`
gains the `--version` short-circuit paragraph: a single `version: <version>` TOON line, no
`description`/`bin`/`venv`/`status` object, no `help[]` footer. `## Failure modes` gains the
unavailable-metadata `If <trigger>, then` clause. `## Out of scope` gains two entries: a `-V` short
flag, declined; `version` on the home output block, declined (resolution 3).

`specs/mcp/tools.md` - `## The binding report` → `### Outputs` reorders the flat object to
`version`, `root`, `venv`, `status`, with `version` first and the one-line reason why.
`### Failure modes` gains the unavailable-metadata clause, stated as applying across both existing
degrades since `version` is resolved before either. `### The description is part of the contract`
gains the one-line requirement that the registered description states the report includes
venvaxi's own version. `## Divergences from the CLI`'s `describeBindingTool` entry is rewritten:
the cache summary was the *first* exception to 'no CLI counterpart of any shape', `version` is the
*second*, and the tool now carries three different relationships to the CLI at once rather than
two.

Both **amended** specs are in `specs:`, not `authors:`. This plan amends both files **and** brings
`src/venvaxi/__init__.py`, `src/venvaxi/__main__.py` and `src/venvaxi/_mcp.py` into conformance
with the amended text - per `plans/README.md`, 'if the same plan writes a spec *and* implements it,
that is `specs:` - the code conformance is the stronger claim and subsumes the authorship.' Neither
field would be correct alone: `authors:` alone would assert this plan writes the spec text and
changes no behaviour, which is false; `specs:` is the complete, honest answer to 'who owns this
spec, and does the code conform.'

`specs/behaviors/skill-content.md` is listed in `specs:` alongside the other two, matching both
directly analogous precedents - [`cache-state-report`](cache-state-report.md) (#49) and
[`installed-package-visibility`](installed-package-visibility.md) (#50) each added a field across
two surfaces plus the packaged skill, and each listed it.

A stage-01 draft excluded it, reasoning that no existing SKILL.md sentence becomes false here and
that the CLI table row is a completeness improvement rather than a correction. That does not
survive contact with the file. `src/venvaxi/SKILL.md` line 189 ends '`root`/`venv`/`status` still
report normally either way' - an explicit enumeration of which fields survive a
`describeBindingTool` degrade. `version` survives both degrades as well, which the amended
`specs/mcp/tools.md` now states outright, so that sentence becomes false by omission the moment the
field lands. That is precisely the stale claim `skill-content.md`'s Rule obliges the skill to
correct: 'where the skill and a spec disagree, the skill is what is wrong and the skill is what
changes.'

Listing it is also what puts the skill edit inside stage 03's conformance sweep, which reads
`specs:` and nothing else.

## Approach

1. Open this plan at `status: planned`; stage 02 flips it to `in-progress`.
2. `src/venvaxi/__init__.py` - bind `__version__` **unconditionally**, replacing the current
   `contextlib.suppress(metadata.PackageNotFoundError)` guard with a `try`/`except` that falls back
   to an empty string on `PackageNotFoundError`, so the name is always defined - never absent, never
   raising `AttributeError` - from both an installed and an uninstalled source tree. Add
   `__version__` to `__all__`. The `(no version metadata)` marker itself is **not** bound here: per
   the house convention (`schema_version` in `_cache.py`/`_cli.py`, `(no docstring)` in
   `_introspect.py`), a marker is applied at the emission site in each surface, not baked into the
   stored/resolved value - so `__version__` stays a plain string (possibly empty), and each surface
   decides how to render an empty one.
3. `src/venvaxi/__main__.py` - register a custom `argparse.Action` for `--version` alongside the
   existing `-v`/`--verbose` registration, so it emits TOON via the same `_toon.encode_object` path
   every other command uses (never argparse's own `action="version"`, which prints bare text) and
   exits `EX_OK` before subparsers or logging configuration run. Render `venvaxi.__version__` or
   `"(no version metadata)"` if it is falsy.
4. `src/venvaxi/_mcp.py` - add `version` to the `fields` dict `describe_binding_tool` builds,
   ahead of `root`, resolved the same way and rendered the same marker on a falsy `__version__`.
   Amend the registered docstring to state the report includes venvaxi's own version.
5. `src/venvaxi/SKILL.md` - the `venvaxi` row of the CLI command table gains `--version`; the
   `describeBindingTool` row/prose reflects the new `version` field. Run `just skill-sync` and
   confirm the installed copy stays byte-identical
   (`tests/test_skill_parity.py`).
6. Tests: `tests/test_cli.py` - `--version` emits the TOON line and exits `EX_OK`; short-circuits
   ahead of `-v`/`--verbose` and subcommand dispatch; the unavailable-metadata marker path (mock
   `venvaxi.__version__` as falsy); `venvaxi --help` lists `--version`. `tests/test_mcp.py` -
   `describe_binding_tool` emits `version` first, on both the healthy path and both existing
   degrades (no root, unreadable cache); the unavailable-metadata marker path; the registered
   description states the version claim. New tests use `capsys`, never `mock.patch` on
   `sys.stdout`/`sys.stderr`, per `ICM/_config/reference-toolchain-pytest.md`.
7. Verify both surfaces, run the suite, coverage and hooks.

**No `SCHEMA_VERSION` bump.** This unit adds no new walk-time recording and touches no cached
symbol graph.

## Validation

- [x] Where `--version` is given, the bare invocation shall emit a single `version: <version>`
      TOON line and exit `EX_OK`, short-circuiting the home view - no `description`/`bin`/`venv`/
      `status` object and no `help[]` footer are emitted.
      — `tests/test_cli.py::test_version_flag_emits_version_and_exits_ok`,
      `::test_version_flag_short_circuits_subcommand_dispatch`,
      `::test_version_flag_short_circuits_regardless_of_order[version-then-verbose]` and
      `[verbose-then-version]`; live `venvaxi --version` and both flag orderings, 1 line/16 bytes
      on stdout, 0 bytes on stderr, exit `0`
- [x] If package metadata is unavailable when `--version` is given, then the bare invocation shall
      emit `version: (no version metadata)` rather than raising, and still exit `EX_OK`.
      — `tests/test_cli.py::test_version_flag_unavailable_metadata_reports_marker`; in-process
      live with `venvaxi.__version__` mocked falsy (`EXIT CODE: 0`,
      `STDOUT: 'version: (no version metadata)\n'`)
- [x] The `describeBindingTool` shall emit `version` as the first field of its flat object, ahead
      of `root`, `venv` and `status`.
      — `tests/test_mcp.py::test_describe_binding_tool_version_is_first_field`; live
      `describe_binding_tool()` on this repo's real binding, first line `version: 0.4.0`
- [x] If package metadata is unavailable, then `describeBindingTool` shall report
      `version: (no version metadata)`.
      — `tests/test_mcp.py::test_describe_binding_tool_healthy_path_unavailable_metadata_marker`
- [x] While `describeBindingTool` degrades for any trigger - no project root, or an unreadable
      cache - it shall still report `version` unaffected by the degrade.
      — `tests/test_mcp.py::test_describe_binding_tool_no_root_reports_version`,
      `::test_describe_binding_tool_no_root_unavailable_metadata_marker`,
      `::test_describe_binding_tool_unreadable_cache_reports_version`,
      `::test_describe_binding_tool_unreadable_cache_unavailable_metadata_marker`
- [x] When the MCP server is built, the registered `describeBindingTool` description shall state
      that the report includes venvaxi's own version.
      — `tests/test_mcp.py::test_describe_binding_tool_description_states_version`; live via
      `build_server()` + `get_tool()`, description ends "...The report also includes venvaxi's
      own version."
- [x] The top-level `venvaxi --help` output shall list `--version` alongside `-v`/`--verbose`.
      — `tests/test_cli.py::test_help_lists_version_flag`; live `venvaxi --help` usage line
      `usage: venvaxi [-h] [-v] [--version]`
- [x] When the packaged skill tables the CLI command surface, it shall carry a
      `venvaxi --version` row whose stated purpose is reporting the installed version and
      exiting, rather than the home view that row's flag would otherwise sit beside.
      — `src/venvaxi/SKILL.md:111`
- [x] Where the packaged skill enumerates the fields surviving a `describeBindingTool` degrade, it
      shall name `version` among them.
      — `src/venvaxi/SKILL.md:185-191`
- [x] After `src/venvaxi/SKILL.md` is edited, `.claude/skills/venvaxi/SKILL.md` shall remain
      byte-identical to it.
      — `tests/test_skill_parity.py::test_installed_skill_matches_packaged`; `diff` and
      `sha256sum` identical between both copies

## Risks / unknowns

- **The `contextlib.suppress` → `try`/`except` rewrite in `__init__.py` is the one change this
  plan makes to a file with no prior touch history in this area.** It changes `__version__` from
  sometimes-absent to always-present-and-possibly-empty, a public-attribute contract change for
  anything importing `venvaxi` directly rather than through the CLI or MCP surface. No spec governs
  the Python import API, so this is not a Validation criterion, but stage 02 should grep for any
  existing `hasattr(venvaxi, "__version__")`-shaped guard elsewhere in the codebase or its tests
  that the always-present attribute could silently change the meaning of.
- **Whether a custom `argparse.Action` correctly short-circuits ahead of `-v`/`--verbose` and the
  subparsers action has not been verified against this project's actual parser wiring.** Argparse
  actions fire in the order arguments are parsed, not the order they are registered, so `venvaxi -v
  --version` and `venvaxi --version -v` need to be checked to behave identically - stage 02 should
  test both orderings explicitly.

## Notes

**Why TOON rather than argparse's `action="version"`.**
[`specs/behaviors/output-contract.md`](../specs/behaviors/output-contract.md)'s Rule is
unconditional and applies to every CLI command - 'Every command writes TOON to STDOUT and nothing
else.' Argparse's built-in `action="version"` prints a bare string via `sys.stdout.write` and
calls `parser.exit()` directly, outside venvaxi's own output path, which would diverge from the
contract on arrival. No exemption clause was added to `output-contract.md`; `--version` conforms
to the contract via a custom `argparse.Action` (`_VersionAction` in `__main__.py`) that renders
through `_toon.encode_object` like every other command, rather than being carved out of it.

**Why `version` is the first field on `describeBindingTool`.** `specs/mcp/tools.md`'s `### Outputs`
reorders the flat object to `version`, `root`, `venv`, `status` - the server identifies itself
before naming the binding it speaks for, so a caller comparing two servers' answers reads which
build answered before which project it answered about.

**The stage-02 re-entry.** Per `ICM/process-plan/CONTEXT.md`'s re-entry rule, stage 03 passed
10/10 Validation criteria, then surfaced two non-blocking findings the maintainer ruled on:

1. `src/venvaxi/__init__.py`'s `except metadata.PackageNotFoundError:` arm was unreachable in the
   dev environment (`venv-axi` installed editable) and therefore uncovered. Closed with a new
   `tests/test_init.py`, which forces `importlib.metadata.version` to raise and
   `importlib.reload()`s the real module so the `except` arm executes for real.
2. `src/venvaxi/SKILL.md`'s bare `venvaxi` row named `--version` in its Flags column while its
   Purpose column still described the home view `--version` bypasses entirely - the two columns
   disagreed about which command the row described. Split into its own
   `venvaxi --version` row, the same shape the table already uses for `venvaxi show <pkg>` /
   `venvaxi show <pkg> --api`.

Only this delta was re-run; neither finding reopened a stage-01 decision or touched `specs/**`.

**The criterion-8 rewording during that re-entry.** The delta above moved `--version` out of the
bare `venvaxi` row into its own row, which made the original box text ('the `venvaxi` row shall
name `--version`') false - `--version` is no longer named on that row at all. Ticking it unchanged
would have ticked a false statement, so the box was reworded during the re-entry (never at
closeout, per `reference-standard-validation.md`) to state what is actually true post-split: a
dedicated `venvaxi --version` row exists, whose Purpose matches what the flag returns.

**A bound on `tests/test_init.py`.** It proves the `except` arm binds `""` on *reload* - it forces
`importlib.metadata.version` to raise and reloads the already-imported `venvaxi` module in its
existing namespace. It cannot reproduce a true first import of an uninstalled tree, where the old
`contextlib.suppress` form left `__version__` undefined entirely: `importlib.reload()` re-executes
in the module's existing namespace and cannot unbind a name that a prior successful import already
bound. The code path exercised - the `except` arm itself - is identical either way, so the
coverage is real, but the limit is stated rather than left tacit. The pre-fix failure was
therefore `AssertionError: assert '0.4.0' == ''` (a stale value left in place by the suppressed
statement), not the `AttributeError` a fresh import would give.

**`__version__` was added to `__all__`.** `venvaxi show venvaxi --api` now lists it as a public
export - a visible surface change that follows directly from the binding becoming unconditional
and public, recorded here so it is a decision rather than a surprise.

**Why `specs/behaviors/skill-content.md` is in `specs:`.** `SKILL.md:191`'s degrade-survivor
sentence ('`version`/`root`/`venv`/`status` still report normally either way') would otherwise
have become false by omission once `version` survived both `describeBindingTool` degrades -
`skill-content.md`'s Rule obliges the skill to correct exactly that kind of stale-by-omission
claim. This matches the `cache-state-report` (#49) and `installed-package-visibility` (#50)
precedents, which each listed the same spec when a field crossed both surfaces plus the packaged
skill.

## Follow-ups

None. Issue [#97](https://github.com/andyrids/venv-axi/issues/97) (the piped-stdin transport
defect) was deliberately avoided as a probing method during stage-03 verification - MCP checks
were driven in-process rather than by piping JSON-RPC into `venvaxi serve` - but fixing it is not
this plan's work. [#49](https://github.com/andyrids/venv-axi/issues/49)'s note that the cache
cannot report indexed versions is adjacent to `describeBindingTool`'s cache summary but is owned
by that plan, not this one.
