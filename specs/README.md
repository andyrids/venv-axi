---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Specifications

`specs/` declares what MUST be true of `venvaxi`. It is the source of truth for behaviour.

This is not documentation of what was built - it is specification of what should exist.
Implementation is brought into conformance with these files, not the other way round.

## State vs motion

The project keeps three distinct artifact kinds. Confusing them is the failure mode this tree
exists to prevent.

| Layer    | Answers                     | Location            | Lifetime                     |
| -------- | --------------------------- | ------------------- | ---------------------------- |
| Spec     | What MUST be true, forever  | `specs/**`          | Permanent, changed by review |
| Plan     | What we are doing about it  | `plans/<slug>.md`   | Frozen at `status: done`     |
| Techspec | How, in implementation terms | ICM stage `output/` | Ephemeral scratch           |

A spec with no implementation is a known gap, and on `develop` a known gap MUST carry a committed
plan. That invariant is what makes `/audit-spec-drift` meaningful - see
[Invariants](#invariants) below.

## Layout

```text
specs/
├── README.md                          <- this file
├── principles.md                      <- decisive, project-wide rules
├── architecture.md                    <- module map & foundational decisions
├── commands/                          <- one file per CLI verb
│   ├── home.md      list.md      show.md      find.md
│   └── tree.md      inspect.md   inherits.md  serve.md   setup.md
├── behaviors/                         <- cross-cutting invariants
│   ├── output-contract.md
│   ├── qualified-name-semantics.md
│   └── cache-refresh.md
└── mcp/
    └── tools.md                       <- MCP tool contracts
```

- **`commands/`** - one file per CLI verb. What the agent invokes and what comes back.
- **`behaviors/`** - rules spanning several commands. When a command spec says "truncated", the
  output contract defines what truncation means.
- **`mcp/`** - the MCP surface, which MUST stay behaviourally aligned with the CLI.

## What specs cover

Invocation, data requirements, output rules, exit codes, errors, and principles.

## What specs do NOT cover

Module decomposition, function and variable names, file paths inside `src/venvaxi/`, and test
cases. Those are implementation decisions that change freely; a spec that pins them rots on the
first refactor. Authoring guidance and templates are in
`ICM/_config/reference-standard-spec.md`.

## Invariants

1. Every spec on `develop` is either implemented or named by a committed plan's `specs:` field.
2. Spec/code divergence is a bug, not debt. Fix the code, or amend the spec - never work around a
   spec in code.
3. A spec whose desired state is still being negotiated stays off `develop`, on a branch, until
   its plan rides along with it. Absence is the only unambiguous marker; a `draft` field on
   `develop` would still pollute greps and reading context.
4. `venvaxi <cmd> --help` is authoritative for invocation. If a command spec disagrees with it,
   `--help` wins and the spec needs updating.

## Changing a spec

A spec edit can strand work already planned against the old desired state. After editing, find
the plans chasing it and offer to update them:

```sh
grep -l 'specs/commands/<verb>.md' plans/*.md
```

A `planned` plan may need its scope, approach or validation revised. Flag - do not silently
rewrite - an `in-progress` plan.
