---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# MCP: Tools

The MCP surface exposed by `venvaxi serve`, under server name `VenvAXI`.

## Contract

Tool functions are defined in snake_case and **registered in camelCase**
(`get_module_tree_tool` -> `getModuleTreeTool`). The registered name is the contract; renaming a
Python function renames an MCP tool.

Every tool returns **TOON text**, not JSON, and mirrors the CLI's
[output contract](../behaviors/output-contract.md): `count:` aggregates, definitive empty states
(including the `(no docstring)` marker), truncation at 200 characters, and a `help[]` footer.

`Error` is caught per tool and returned as the same TOON error block the CLI emits. It MUST NOT
escape into FastMCP's generic error path, which would present a different failure shape to the
agent depending on which surface it happened to be using.

## Tools

| Tool                 | Parameters                          | CLI equivalent            |
| -------------------- | ----------------------------------- | ------------------------- |
| `listPackagesTool`   | `include_dev=False`                 | `list [--all]`            |
| `showPackageTool`    | `name`                              | `show <package>`          |
| `showPackageApiTool` | `name`, `docstring=False`           | `show <package> --api`    |
| `showModuleTool`     | `name`, `docstring=False`           | `inspect <module>`        |
| `getSymbolTool`      | `qualified_name`, `docstring=False` | `inspect <symbol>`        |
| `findSymbolTool`     | `query`, `limit=20`, `package=None` | `find <query>`            |
| `getInheritorsTool`  | `qualified_name`                    | `inherits <name>`         |
| `getModuleTreeTool`  | `name`, `max_depth=2`               | `tree <package>`          |

## Divergences from the CLI

These are deliberate and MUST be preserved:

- **No `refresh` parameter on any tool.** MCP callers get cache-driven rebuilds only. Forcing a
  rebuild is an explicit, potentially slow operation that belongs at the CLI.
- **`inspect` is split into two tools.** The CLI dispatches on whether the argument contains
  `::`; MCP exposes `getSymbolTool` and `showModuleTool` separately, because a typed tool schema
  should not hide two different return shapes behind one parameter.
- **`show` is split into two tools** for the same reason - `showPackageTool` (metadata) and
  `showPackageApiTool` (API), rather than a boolean `--api` switch.
- **`showPackageTool` returns fixed fields** (`name`, `version`, `location`); there is no
  `--fields` equivalent.
- **`getSymbolTool` omits the `help[]` footer when `docstring=True`**, since the only hint it
  would offer is the flag already set.

## Hint wording

Empty-state and next-step hints are phrased for the MCP caller - "Call `getSymbolTool` ...", not
"Run `venvaxi inspect` ...". A hint naming a shell command is useless to a tool-calling agent,
and mixing the two teaches the wrong invocation surface.

Hints reference other tools by deriving the camelCase name from the function, so a rename cannot
leave a stale hint pointing at a tool that no longer exists.

A hint MUST name the tool that performs the action its sentence describes. Deriving the name
correctly from the wrong function passes the rule above and still misdirects the caller.

## Principles

**Inherited** - project principles that especially bite here:

- Principle 9, contextual disclosure
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - it applies to the MCP
  surface too. `venvaxi setup` registers MCP as the primary ambient integration, so an
  MCP-driven agent MUST see the same quality of next-step hints a CLI-driven one does.

**Local**:

- **Behavioural parity with the CLI is the default; every divergence is listed above.** Two
  surfaces over one symbol graph will drift unless divergence is enumerated rather than
  discovered. A new CLI capability MUST either gain an MCP tool or gain an entry in
  [Divergences](#divergences-from-the-cli) explaining why not.
