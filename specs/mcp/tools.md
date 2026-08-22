---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: false
tags: [mcp, tools, parity]
---

# MCP: Tools

The MCP surface exposed by `venvaxi serve`, under server name `VenvAXI`.

This file consolidates all nine tools as a deliberate exception to the one-file-per-unit rule in
`ICM/_config/reference-standard-spec.md`. Eight of them mirror a CLI command whose behaviour is
already specified in `specs/commands/`; splitting this file that many ways would duplicate those
specs as many times over, which the same standard warns against.

`describeBindingTool` is the exception to the exception: it mirrors no CLI command, so its full
contract lives here rather than in `specs/commands/`. That is itself a divergence, and it is
enumerated below with the others.

## Contract

Tool functions are defined in snake_case and **registered in camelCase**
(`get_module_tree_tool` -> `getModuleTreeTool`). The registered name is the contract; renaming a
Python function renames an MCP tool.

Every tool shall return **TOON text**, not JSON, and shall mirror the CLI's
[output contract](../behaviors/output-contract.md): `count:` aggregates, definitive empty states
(including the `(no docstring)` marker), truncation at 200 characters, and a `help[]` footer.

If an `Error` is raised inside a tool, then the tool shall catch it and return the TOON error
object the CLI emits - without the CLI's generic `venvaxi --help` footer, per the
surface-addressed [error shape](../behaviors/output-contract.md#error-shape). It shall not
escape into FastMCP's generic error path, which would present a different failure shape to the
agent depending on which surface it happened to be using. If an error carries no error-specific
hint, then the `help[N]:` footer shall be omitted entirely, never padded with a generic
substitute.

**No exception escapes**, not just no `Error`. If an unexpected exception is raised, then the
tool shall catch it at the same boundary, return the `Unexpected error:` block the CLI renders,
and log it to STDERR with its traceback. Catching only `Error` leaves the surfaces divergent in
exactly the case where the agent has least to go on - the CLI reports a fault it can read, the
MCP caller gets a transport error carrying no TOON at all.

'Exception' means `BaseException` here, exactly as the
[error shape](../behaviors/output-contract.md#error-shape) defines it for the CLI entry point,
and the stakes are higher on this surface: an escaping `BaseException` does not merely fail the
call, it drops the whole MCP connection, taking every other tool down with it. A third-party
import can raise one straight through a tool - see
[Import boundaries](../behaviors/output-contract.md#import-boundaries) - so the tool boundary
shall catch `BaseException`, re-raising only `KeyboardInterrupt` and `SystemExit`.

## Tools

| Tool                  | Parameters                          | CLI equivalent            |
| --------------------- | ----------------------------------- | ------------------------- |
| `describeBindingTool` | none                                | none - see below          |
| `listPackagesTool`    | `include_dev=False`                 | `list [--all]`            |
| `showPackageTool`     | `name`                              | `show <package>`          |
| `showPackageApiTool`  | `name`, `docstring=False`           | `show <package> --api`    |
| `showModuleTool`      | `name`, `docstring=False`           | `inspect <module>`        |
| `getSymbolTool`       | `qualified_name`, `docstring=False` | `inspect <symbol>`        |
| `findSymbolTool`      | `query`, `limit=20`, `package=None` | `find <query>`            |
| `getInheritorsTool`   | `qualified_name`                    | `inherits <name>`         |
| `getModuleTreeTool`   | `name`, `max_depth=2`               | `tree <package>`          |

## The binding report

`describeBindingTool` answers which project and which venv this server speaks for. It takes no
parameters, because every input it could take is a thing the caller is asking the server to tell
*it*.

### Why the surface needs it

A connected agent cannot see the server's argv or its working directory, so every other tool on
this surface returns well-formed, plausible results without disclosing what they are results
*about*. The failure is silent: signatures from an unintended venv are indistinguishable from
correct ones, which is the exact staleness the AXI exists to eliminate. The CLI has no equivalent
gap - a caller runs `venvaxi` from a directory it chose, with the venv on its own `PATH`.

### The binding is two axes

The tool shall report both, because they resolve independently and can disagree:

- **venv** - the `sys.prefix` of the interpreter serving this process, which decides what is
  importable and therefore what every symbol answer is drawn from.
- **root** - the consuming project root, resolved as in
  [Cache and refresh](../behaviors/cache-refresh.md#project-root-resolution), which decides which
  `pyproject.toml` declares the dependencies `listPackagesTool` answers with, and which keys the
  symbol cache.

Reporting only the venv would leave a server answering one project's declared dependencies against
another project's installed packages, with the mismatch still invisible.

### Outputs

The `describeBindingTool` shall emit a flat TOON object of `root`, `venv` and `status`, followed by
a `help[]` footer.

Both paths are rendered `~/`-prefixed when under the home directory, else absolute, matching
[the home view](../commands/home.md).

`status` is `active` when `sys.prefix != sys.base_prefix`, else `inactive` - the same computation
the home view makes, but not the same signal. A server registered by `setup` runs the venv's own
interpreter, so `inactive` over MCP means the registered command names a base interpreter and the
symbol answers are being drawn from an environment the project never installed into.

### Failure modes

This tool shall answer in a broken or uninitialized project, because a caller reaching for it has
most likely already been given an answer it distrusts.

If no project root resolves, then the `describeBindingTool` shall report `root: (no project root)`,
emit the remaining fields, and return no error block. The marker is a definitive empty state under
[Output contract](../behaviors/output-contract.md#definitive-empty-states) - it states that no
`pyproject.toml` was found from the working directory upward nor beside the venv, which is a fact
about the binding and precisely what the caller asked for.

That state is not exotic. It is close to diagnostic of an ephemeral or tool-venv registration - a
`uvx`-installed interpreter lives outside any project, while a conventional in-project `.venv` has
the project root as its parent and resolves. The hint shall therefore name the registration as the
thing to check, phrased for the MCP caller per [Hint wording](#hint-wording).

The degrade is scoped to that trigger alone. If resolving the root raises anything other than a
failure to find one, then the tool shall return the `Unexpected error:` block like any other tool.
Widening the catch would convert a genuine fault - an unreadable or deleted working directory -
into a confident report that the project simply does not exist.

**This tool degrades where the other eight raise**, for the identical unresolvable-root state. That
is deliberate and MUST be preserved: for the other eight an unresolvable root means the answer
cannot be computed, and for this one it *is* the answer. Harmonizing the two would either silence
the eight or break the one that has to work when nothing else does.

### The description is part of the contract

The registered tool description is the only channel that reaches an agent without a tool call -
`venvaxi setup` registers the server as the primary ambient integration, and the harness keeps
tool descriptions in context. The `describeBindingTool` description shall state that it identifies
the project and venv the server answers from, and that it is the tool to call first.

A description that merely names the return shape wastes the one ambient slot this surface has, and
leaves the tool discoverable only by an agent that already suspects the problem it exists to
reveal.

## Divergences from the CLI

These are deliberate and MUST be preserved:

- **`describeBindingTool` mirrors no CLI command.** It is the only tool on this surface with no
  entry in `specs/commands/`, and the only one whose behaviour is declared here in full. The
  nearest CLI relative is the bare `venvaxi` [home view](../commands/home.md), and it is a relative
  rather than an equivalent: home reports `bin`, `venv` and `status` and deliberately never
  resolves the project root, while this tool reports `root` and omits `bin`. Neither surface is
  wrong. `bin` identifies the invocation on a CLI where the caller supplied it and can act on it;
  over MCP it names the `__main__.py` inside the venv already reported, so it restates `venv` less
  directly. `root` is the reverse - a CLI caller knows the directory they are standing in, and an
  MCP caller controls neither the spawn directory nor the interpreter.
- **No `refresh` parameter on any tool.** MCP callers get cache-driven rebuilds only. Forcing a
  rebuild is an explicit, potentially slow operation that belongs at the CLI.
- **`inspect` is split into two tools.** The CLI dispatches on whether the argument contains
  `::`; MCP exposes `getSymbolTool` and `showModuleTool` separately, because a typed tool schema
  should not hide two different return shapes behind one parameter. The split's malformed-input
  diagnosis is specified in [Malformed qualified names](#malformed-qualified-names).
- **`show` is split into two tools** for the same reason - `showPackageTool` (metadata) and
  `showPackageApiTool` (API), rather than a boolean `--api` switch.
- **`showPackageTool` returns fixed fields** (`name`, `version`, `location`); there is no
  `--fields` equivalent.

Footer suppression under `docstring=true` is **not** on this list. `getSymbolTool`,
`showPackageApiTool` and `showModuleTool` shall each omit the `help[]` footer when `docstring` is
set, which is exactly what `inspect --docstring` and `show --api --docstring` do - parity, and
already required of both surfaces by the suppression rule in
[Output contract](../behaviors/output-contract.md#contextual-disclosure). It was listed here once
as a `getSymbolTool` divergence; it never was one, and listing parity as divergence is as
misleading as omitting a real one.

## Malformed qualified names

The `inspect` split above leaves `getSymbolTool` symbol-only, so the commonest spelling mistake -
a fully-dotted name where `module::Symbol` was meant - cannot fall through to a module lookup as
it does on the CLI. Answered as a plain symbol miss, `Symbol ... not found` reads as a definitive
negative about the package rather than a malformed-input diagnosis, and an agent that believes it
stops looking for a symbol it had correctly named.

- If `qualified_name` contains no `::`, then `getSymbolTool` shall return the TOON error block
  with a message that diagnoses the input: the tool requires a `module::Symbol` name, the given
  name carries no `::`, and `showModuleTool` is the tool for module lookups. It shall not report
  a bare symbol miss.
- The diagnosis applies before any lookup. If a no-`::` name would resolve as a module, then
  `getSymbolTool` shall still return the diagnosis rather than the module's node - a module
  answer from the symbol tool is exactly the two-shapes-behind-one-parameter collapse the split
  exists to prevent, and `showModuleTool` gives the fuller answer for the same spelling.
- The tool references in the message are next-step hints and take every
  [Hint wording](#hint-wording) rule, including derivation of the camelCase names.

The tool shall not fall back to a module lookup; the split is a deliberate divergence above and
MUST be preserved.

## Hint wording

Empty-state and next-step hints shall be phrased for the MCP caller - 'Call `getSymbolTool` ...',
not 'Run `venvaxi inspect` ...'. A hint naming a shell command is useless to a tool-calling
agent, and mixing the two teaches the wrong invocation surface.

Hints shall reference other tools by deriving the camelCase name from the function, so a rename
cannot leave a stale hint pointing at a tool that no longer exists.

A hint shall name the tool that performs the action its sentence describes. Deriving the name
correctly from the wrong function passes the rule above and still misdirects the caller.

Where a hint mirrors a CLI hint, it shall carry the parameters that make the two **equivalent in
scope**, not merely equivalent in tool. Naming the right tool with the wrong default sends the two
surfaces to differently-scoped answers for the same recovery, which is the harder failure to see -
the caller gets a plausible result and no signal that it was narrower than the one the CLI would
have given.

Truncation suffixes carry the same obligation as footers, and are specified with the truncation
rule in [Output contract](../behaviors/output-contract.md#truncation).

## Error message wording

The [error shape](../behaviors/output-contract.md#error-shape) governs the block; this rule
governs the sentence inside it.

A message raised by logic shared with the CLI reaches both surfaces unaltered, so it shall name
the input it rejects in a spelling that is true on both - the thing being rejected, not the flag
or the parameter that carried it. `--limit` names nothing a tool caller can set and `limit=`
names nothing a shell caller can type, so a message picking either one misdirects half its
readers, and it misdirects them while they are already recovering from an error.

Hints keep the opposite rule, always spelled for the surface, per
[Hint wording](#hint-wording): a hint names a next action, and a next action exists on one
surface at a time, whereas a message names a fact about the input and that fact is the same on
both. Where a message genuinely can only be phrased for one surface, it belongs at that
surface's boundary rather than in the shared path.

- If `findSymbolTool` is called with a negative `limit`, then it shall return the TOON error
  block, carrying neither the CLI footer nor a CLI flag spelling. The rejection is `find`'s, per
  [Bounded results](../commands/find.md#bounded-results); this surface inherits it, which is
  parity rather than a divergence.

### Known exception

One message on the shared path predates this rule and does not conform. `find_symbol` rejects
`refresh` without `package` in the CLI's own flag spelling, naming `--refresh` and `--package`.
No tool exposes `refresh` today - the absence is
[#68](https://github.com/andyrids/venv-axi/issues/68) - so the message reaches no tool caller
and the divergence is latent rather than live.

It stops being latent the moment a refresh parameter reaches this surface. Whichever change adds
one shall bring that message into conformance with this rule in the same move, rather than
shipping a reachable message that contradicts it.

## Out of scope

- **MCP resources and prompts** - the surface is tools only; no resource or prompt is served.
  No future spec is planned.
- **Mutating and lifecycle tools** - the nine tools cover the query surface; `setup` and
  `serve` remain CLI-only. Never - an MCP tool that mutates the consuming repo would run without
  the explicit invocation
  [principle 7, ambient context](../principles.md#principle-7-ambient-context) requires.
- **Cache state** - `describeBindingTool` reports which project and venv the server is bound to,
  never what the symbol graph currently holds. Built version and built depth are a separate
  question with a separate failure mode - a correct binding serving a stale graph - and
  [#49](https://github.com/andyrids/venv-axi/issues/49) owns it. Where it lands is this tool: the
  binding report is the natural home for a cache summary, and a future spec adding one extends
  this contract rather than replacing it.

## Principles

**Inherited** - project principles that especially bite here:

- [Principle 9, contextual disclosure](../principles.md#principle-9-contextual-disclosure)
  - it applies to the MCP
  surface too. `venvaxi setup` registers MCP as the primary ambient integration, so an
  MCP-driven agent MUST see the same quality of next-step hints a CLI-driven one does.

**Local**:

- **Behavioural parity with the CLI is the default; every divergence is listed above.** Two
  surfaces over one symbol graph will drift unless divergence is enumerated rather than
  discovered. A new CLI capability MUST either gain an MCP tool or gain an entry in
  [Divergences](#divergences-from-the-cli) explaining why not.
