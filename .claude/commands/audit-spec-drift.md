---
description: Audit the specs/ tree against the implementation
---

# Audit spec drift

Scope (optional): $ARGUMENTS

Launch the `spec-drift-auditor` agent to compare `specs/` against the implementation in
`src/venvaxi/` and report gaps, undocumented behaviour and conflicts.

With no arguments, audit the whole tree. With arguments, narrow to the named specs, commands or
modules.
