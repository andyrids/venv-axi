---
name: venvaxi
description: >-
  This skill should be used before writing or reviewing code that calls into a dependency
  installed in the project venv, whenever an exact signature, docstring, return type or class
  hierarchy needs verifying against the installed version rather than memory recall. Also use
  when debugging observed misbehaviour - a wrong return value or dtype, an unexpected default
  taking effect, a `TypeError` from a call that looks valid - where the cause may be a signature
  fact in the installed version, even before it has been identified as one. Also use
  when setting up, refreshing or troubleshooting the `venvaxi` CLI or its MCP server - a stale
  symbol graph, MCP registration, or a missing `fastmcp` extra.
metadata:
  version: "0.2.0"
---

# Driving the `venvaxi` CLI

## Overview

`venvaxi` is an Agent eXperience Interface (AXI), which answers 'does this exist, and what is its
exact shape in the version I have installed?'

The AXI imports the venv package, introspects it, caches the result as a per-project SQLite symbol
graph and prints TOON - a compact tabular text format.

You SHOULD prefer `venvaxi` over API recall from memory, which drifts from the installed version,
whereas this AXI cannot.

You SHOULD also prefer it over executing the dependency to observe it (`python -c ...`). Not
because execution is wrong, but because it is narrow and costly: it answers only the question you
thought to ask, needs a fresh snippet each time, and runs code with whatever side effects it
has - and it cannot answer 'what else is on this class' or 'what subclasses it'. Reach for
execution when you need a runtime **value**; reach for the AXI when you need the **shape**.

You MUST not use `venvaxi` to explain usage - signatures, kinds, docstrings and inheritance edges
are in scope; tutorials, worked recipes and migration guides are not.

## Invocation

`venvaxi` is a console script installed inside the project venv. If it is not on `PATH`, run it
through the project's runner (for example `uv run venvaxi ...`) or activate the venv first. The
bare `venvaxi ...` spelling used throughout this file and in the `help[]` footers assumes the
console script is reachable on `PATH`.

## Workflow

`venvaxi` is keyed by *qualified* name (`rich.console::Console.print`), but the codebase references
a *bare* one (`Console.print`). The three steps bridge that gap

You MUST scan the codebase with your own tools and use those findings to drive the AXI. Querying
it from a remembered symbol name skips the step that grounds the lookup in what the code actually
imports, and a name recalled rather than read is the same staleness this AXI exists to remove.

### (1) Scan

Locate the import and call sites of the dependency symbol you are working on with your own tools.
This gives you a bare symbol name (`Console.print`) and its owning package (`rich`).

### (2) Resolve

`venvaxi find Console.print --package rich` converts the bare name into a qualified name
(`rich.console::Console.print`), indexing the package if needed.

Output example:

```text
count: 3
symbols[3|]{name|kind|qualified_name}:
  print|method|"rich.console::Console.print"
  print_json|method|"rich.console::Console.print_json"
  print_exception|method|"rich.console::Console.print_exception"
help[1]:
  Run `venvaxi inspect <qualified_name>` for complete metadata
```

### (3) Inspect

`venvaxi inspect rich.console::Console.print --docstring` returns the real signature and docstring
for the installed version. Adding `--docstring` prints the full docstring.

```text
qualified_name: "rich.console::Console.print"
kind: method
signature: "(self, *objects: Any, sep: str = ' ', end: str = '\\n',
style: Union[rich.style.Style, str, NoneType] = None,
justify: Optional[Literal['default', 'left', 'center', 'right',
'full']] = None, overflow: Optional[Literal['fold', 'crop',
'ellipsis', 'ignore']] = None, no_wrap: Optional[bool] = None,
emoji: Optional[bool] = None, markup: Optional[bool] = None,
highlight: Optional[bool] = None, width: Optional[int] = None,
height: Optional[int] = None, crop: bool = True,
soft_wrap: Optional[bool] = None,
new_line_start: bool = False) -> None"
doc: Print to the console.
help[1]:
  Run `venvaxi inspect rich.console::Console.print --docstring` for
  the complete docstring
```

A follow-up query could include `inspect rich.console` for direct children discovery, or
`inherits` to enumerate subclasses: `inherits rich.progress::ProgressColumn` returns `count: 11`
(`BarColumn`, `SpinnerColumn`, `TextColumn`, `TimeRemainingColumn` and seven more).

## Commands

Verified against `venvaxi --help` output; defaults shown in parentheses.

| Command | Flags | Purpose |
| --- | --- | --- |
| `venvaxi` | - | Home view: bin/venv paths, active status, next-step hints |
| `venvaxi --version` | - | Installed venvaxi version, then exits - no bin/venv/status |
| `venvaxi list` | `--all`, `--fields` (`name,version`) | Declared; `installed:` names the gap |
| `venvaxi show <pkg>` | `--fields` (`name,version,location`) | Installed package metadata |
| `venvaxi show <pkg> --api` | `--docstring`, `--limit` (`20`), `--refresh` | Public API symbols |
| `venvaxi find <query>` | `--package`, `--limit` (`20`), `--refresh` | Search cached symbols |
| `venvaxi tree <pkg>` | `--max-depth` (`2`), `--refresh` | Nested module tree |
| `venvaxi inspect <name>` | `--docstring`, `--refresh` | Symbol detail, or module children |
| `venvaxi inherits <qname>` | `--refresh` | Classes directly subclassing a base |
| `venvaxi cache` | - | This project's cache/build state - schema, path/size, per-package build |
| `venvaxi serve` | - | Run the MCP server over stdio |
| `venvaxi setup` | `--skill`, `--no-skill` | Install ambient context (MCP config & skill) |

Notes on the positional arguments and shared flags:

- `--fields` accepts any of `name`, `version`, `location`, `summary`; anything else is a hard
  error listing the valid set. It applies to `list` and to `show` *without* `--api` only;
  passed together with `--api` it is **silently ignored**, not an error - `--api` dispatches
  before `--fields` is parsed.
- `-v` / `--verbose` is a global flag enabling DEBUG logging on STDERR - reach for it when a
  `setup` or `serve` failure produced no useful message.
- `--limit` bounds the rows a collection command returns, and is `20` on both `find` and
  `show --api`. A `count:` equal to the active limit means *at least* that many, and says so
  in a `help[]` hint; below it the count is definitive. `--limit 0` is a bound honoured
  exactly (`count: 0`, exit `0`); a negative `--limit` is a hard error. It applies to
  `show` *with* `--api` only; passed without it, it is **silently ignored**, not an error.
- `show <pkg> --api` takes a distribution name or any importable dotted module path, and
  emits the columns `name|kind|signature|doc`.
- `inspect` takes either a qualified symbol name (`module::Symbol`, `module::Class.method`)
  or a bare/dotted module name - it dispatches on the presence of `::`.
- `--refresh` exists on `show`, `find`, `tree`, `inspect` and `inherits`; it forces a graph
  rebuild before the query.
- `setup` (re)installs this skill at `.claude/skills/venvaxi/SKILL.md` by default, overwriting
  any existing copy; `--no-skill` suppresses it.

Output contract, common to every command:

- Structured TOON goes to **stdout**, including errors: `error: true` plus a `message:` line.
  `0` is success, including a definitive empty result - `count: 0` exits `0`, never `1`. `1`
  means venvaxi caught and reported an `Error`: fix the query or the environment the message
  names. `2` has two causes, told apart by stdout. Argparse rejecting an unknown flag or a
  missing positional prints usage to **stderr** and no TOON at all - retype the command. A TOON
  block prefixed `Unexpected error:` on stdout means venvaxi itself is broken - that invocation
  was fine, so file a bug rather than retyping it.
- Two package failures read differently, and the recovery differs: `is not installed in the
  active venv` means the venv has nothing by that name, so install it or check the spelling;
  `Failed to import` means it is installed and broken, so investigate it rather than
  reinstalling.
- Collection commands lead with `count: N`, then the table.
- Most commands close with a `help[]` block of concrete next-step commands - follow them
  rather than guessing at a spelling.

## MCP tools

`venvaxi serve` exposes the same surface over stdio MCP under the server name `VenvAXI`. Tool
names are a camelCase version of the underlying `venvaxi` MCP functions. Every tool returns a
TOON string with the same `count:`/`help[]` contract as the CLI, and any `Error` presents a TOON
error block instead of an MCP transport error.

| Tool | Parameters | CLI equivalent |
| --- | --- | --- |
| `describeBindingTool` | none | none |
| `listPackagesTool` | `include_dev=False` | `venvaxi list [--all]` |
| `showPackageTool` | `name` | `venvaxi show <pkg>` |
| `showPackageApiTool` | `name`, `docstring=False`, `limit=20` | `venvaxi show <pkg> --api` |
| `showModuleTool` | `name`, `docstring=False` | `venvaxi inspect <module>` |
| `getSymbolTool` | `qualified_name`, `docstring=False` | `venvaxi inspect <qname>` |
| `findSymbolTool` | `query`, `limit=20`, `package=None` | `venvaxi find <query>` |
| `getInheritorsTool` | `qualified_name` | `venvaxi inherits <qname>` |
| `getModuleTreeTool` | `name`, `max_depth=2` | `venvaxi tree <pkg>` |
| `refreshPackageGraphTool` | `name` | `venvaxi <cmd> ... --refresh` |

Types are `str` for names|queries, `bool` for `include_dev`|`docstring`, `int` for
`limit`|`max_depth`, and `str | None` for `package`.

`describeBindingTool` leads with `version` - venvaxi's own version, resolved once and unaffected
by either degrade below - then additionally reports this project's cache state whenever `root`
resolves - `schema_version`, `db_path`, `db_size_bytes`, then `count:` and a `builds` table of
`package`/`version`/`depth`/`symbols`, field for field the same as `venvaxi cache`. If the cache
database cannot be read, those fields degrade to `schema_version: (cache unreadable)` with
`count`/`builds` omitted (never `count: 0`) and a third hint naming the `db_path` as safe to
delete, rather than raising - `version`/`root`/`venv`/`status` still report normally either way.

Notable CLI differences:

- The CLI `inspect` splits into `getSymbolTool` (qualified names, with `::`) and
  `showModuleTool` (module names) - pick by argument shape yourself.
- `getSymbolTool` does not mirror `inspect`'s module fallback: any name without `::` - even
  one naming a real module - is rejected before lookup with a diagnosis pointing at
  `showModuleTool`. Send module names straight to `showModuleTool` rather than spending the
  round trip.
- **No *read* tool takes a `refresh` parameter.** The nine read tools answer from the cache
  and cannot force a rebuild; `refreshPackageGraphTool` is the single exception and the way a
  rebuild is started over MCP. Call it with the package name, then carry on over MCP - it is a
  rebuild, not a cheap precondition, so do not prefix every lookup with it.

## Gotchas

- **Qualified-name form.** The separator is `::`, not a dot: `rich.console::Console` and
  `rich.console::Console.print`. A fully dotted spelling like `rich.console.Console.print`
  has no `::`, so `inspect` treats it as a *module* name and it fails to resolve.
- **`find` without `--package` only searches what is already cached.** On a cold cache that
  is nothing, and you get `count: 0`. Always pass `--package` on the first lookup for a
  package - it indexes and scopes in one step. `--refresh` without `--package` is a hard
  error ('A rebuild must name the package to rebuild').
- **`count: 0` is a definitive empty state, not a failure.** Unresolvable names raise, so a
  zero count means the query resolved and genuinely matched nothing. For `inherits`
  specifically it means the base class resolved with zero *indexed* subclasses - subclasses
  living in an unindexed package, or below the built depth, are simply invisible until you
  index that package (`find <name> --package <pkg>`) or rebuild deeper (`tree <pkg>
  --max-depth N`).
- **`list`'s `installed:` footer, not `count:`, says whether more is queryable.** `count:`
  reports only what the project declares, so an installed-but-undeclared distribution never
  shows up in it - `count: 0` can still sit on a venv holding dozens of packages. Check
  `installed: <m>` (present whenever it differs from the declared count, including on
  `count: 0`) before concluding a package 'isn't available' - it almost certainly still
  resolves through `show <package>`.
- **`inherits` answers 'what subclasses X', never 'what does X subclass'.** There is no
  bases-of query, so running `inherits` on the class you just resolved returns `count: 0` and
  reads as a dead end. To find a parent, guess the likely base and run `inherits` on *that*,
  checking your class appears among its children.
- **Dunders are not indexed.** `find RichHandler.__init__ --package rich` returns `count: 0`
  even though the constructor exists; the constructor signature lives on the class symbol
  instead - `inspect rich.logging::RichHandler` returns the full `__init__` signature. That
  route covers `__init__` only: no non-constructor dunder (`__getitem__`, `__eq__`, and the
  like) has any AXI path today, so a `count: 0` there is not a gap to work around.
- **Docstrings are truncated to a first line by default.** Add `--docstring` to `inspect` or
  to `show --api` when the parameter semantics matter, not just the signature.
- **`doc: (no docstring)` is a definitive answer.** It means the symbol defines no docstring of
  its own - not that the lookup failed. Do not retry, and do not substitute a base class's
  docstring or your own recall; the signature is still authoritative.
- **Namespace accessors inspect empty.** A registered accessor such as polars' `Series.struct`
  inspects as `kind: attribute` with an empty signature and a generic one-line doc, and nothing
  in the output links it to its implementing class. Resolve that class by name - `find
  StructNameSpace --package polars` - and inspect it instead. This affects every `.dt`, `.str`,
  `.list` and `.struct` style accessor.
- **Decorators introspect as passthroughs.** `inspect numba::njit --docstring` reports
  `(*args, **kws)`, and the fully qualified spelling reports the same. Follow the docstring's
  pointer to the real API instead - `njit`'s docstring names `jit()`, which does document
  `inline`. The hard boundary: compiler and runtime semantics (does `cache=True` compose with
  `parallel=True`; is `break` legal in a `prange`) live in no `__doc__` and no signature, so no
  `venvaxi` command reaches them - that is a question for the project's own documentation. This
  is the concrete face of the Overview's 'MUST not use `venvaxi` to explain usage'.
- **When to rebuild.** The cache lives at `~/.venvaxi/<project-hash>.db` and already
  invalidates itself when a package's installed version changes, or when a query needs more
  depth than was built. Reach for a rebuild when the version string cannot move but the
  code did - editable/local installs, a package patched in place - or when a build was
  interrupted. Over the CLI that is `--refresh`; over MCP it is `refreshPackageGraphTool`
  with the package name, which is the only route an MCP-driven agent has. A rebuild is
  package-scoped and walks to the default depth, so a graph previously built deeper is reset
  with it - most queries deepen it again on demand, but `inherits` does not, and subclasses
  below the default depth go invisible until some query builds that deep. The hash is a
  SHA-256 digest of the **resolved project-root path**, so two checkouts of the same project
  at different paths hold independent caches - a rebuild in one is invisible to the other.
- **`tree` defaults to `--max-depth 2`.** Deep packages are silently shallow at the default;
  raise it when you are hunting for a submodule rather than surveying.
- **MCP needs the extra.** `serve` requires `fastmcp` (`uv add venv-axi[mcp]`) and exits `1`
  with a 'requires the `venv-axi[mcp]` extra' log line without it. `setup` deliberately *omits*
  the MCP entry from `.mcp.json` / `.vscode/mcp.json` when `fastmcp` is missing, so an absent
  server entry after `setup` means the extra is not installed. The availability check runs up
  front, at startup - a traceback *after* `fastmcp` is confirmed installed is a different
  failure entirely: investigate it, do not re-run `setup`.
- **`os error 32` on a `uv` sync names `venvaxi.exe`, not a broken venv.** On Windows a
  running MCP server registered by an older `setup` holds the `venvaxi` console-script shim
  open. When `uv` has to reinstall `venv-axi` - on any dependency change - it cannot delete
  that file, and an otherwise unrelated `uv run` or `uv sync` fails with 'The process cannot
  access the file because it is being used by another process'. It fires only on the runs
  that reinstall, so the same command succeeding earlier does not mean the registration is
  fine. Nothing is corrupted - do not rebuild the venv, and retrying without stopping the
  server only defers it. Stop the server, re-run `venvaxi setup` to move the registration to
  `<python> -P -m venvaxi serve`, and start it again; the failure does not recur.
- **A wrongly bound MCP server returns plausible answers, not errors.** The server answers
  from whichever project and venv it was registered in, not the one the session is working
  in - an `.mcp.json` inherited from another checkout returns well-formed, wrong-project
  signatures and dependency lists with no warning. When an MCP answer contradicts the project
  in front of you, call `describeBindingTool` first and compare its `root` against the project
  you are editing; a mismatch is a registration problem, so fix the `VenvAXI` entry in the
  repo's `.mcp.json` by re-running `venvaxi setup` from inside that project - `--refresh`
  cannot help, because the server is bound elsewhere. Over MCP, `status: inactive` means the
  registered command names a base interpreter, so answers are drawn from an environment the
  project never installed into - re-register, do not activate anything. `describeBindingTool`
  is also the way to check a *suspected-stale* graph without spending a rebuild to find out -
  its cache summary reports each indexed package's built version and depth, so a rebuild via
  `refreshPackageGraphTool` is spent only when the recorded build actually looks behind, not on
  a hunch.
- **`setup` writes files - it is not a diagnostic command.** It rewrites
  `.mcp.json`/`.vscode/mcp.json` every time it runs, it overwrites
  `.claude/skills/venvaxi/SKILL.md` wholesale unless `--no-skill` is given, and it deletes a
  legacy ambient block from `AGENTS.md` if it finds one. 'Idempotent' here only means repeated
  runs converge on the same result, not that a run is side-effect-free - it still touches
  tracked files. Diagnosing *whether* `fastmcp` is available is a read-only question: answer it
  with `venvaxi show fastmcp` (raises `PackageNotFoundError` if absent) rather than running
  `setup` to see what it does. Only run `setup` when you actually mean to (re-)register the MCP
  server - e.g. right after installing the extra, or when told to fix a stale registration -
  never as a way to confirm or explain a fix while investigating. Note also that `setup` reports
  only `SKILL.md: true|false` with no diff, so a `true` after a hand-edit of the installed copy
  means those edits were just discarded, not that an update arrived.
- **Token savings scale with row count and collapse on single-object output** - so prefer a
  table-shaped query where either would answer, and on the `inspect` path efficiency comes from
  truncation. The measured figures live in the venv-axi project's `specs/principles.md`.

## Pointers

- `venvaxi <cmd> --help` is the authoritative flag source. If the table above ever disagrees
  with it, `--help` wins.
- **This file is the ambient context.** Earlier versions also injected an always-on summary into
  `AGENTS.md` between `<!-- venvaxi:begin -->`/`<!-- venvaxi:end -->` markers; that block
  duplicated this file in every session whether or not the task touched a dependency, and is no
  longer written. `setup` now strips one it finds, so `AGENTS.md: true` on a repo last set up by
  an older `venvaxi` means the block was removed, not refreshed. Nothing outside those markers is
  touched.
- This file is installed by `venvaxi setup` (by default; `--no-skill` opts out) and
  overwritten wholesale on every run - edit the packaged source (`src/venvaxi/SKILL.md` in the
  venv-axi project), never the installed copy.
