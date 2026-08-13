---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state
immutable: false
tags: [behavior, package, resolution]
---

# Behavior: Package resolution

## Rule

A package argument fails in exactly one of three ways, and the exception says which:

| The name is | Meaning | Error |
| ----------- | ------- | ----- |
| **Malformed** | Not a possible package name at all | `InvalidArgumentError` |
| **Absent** | A possible name, but nothing in the venv provides it | `PackageNotFoundError` |
| **Broken** | Provided, but will not import | `PackageImportError` |

If a user-supplied argument value cannot be honoured, then the command shall raise an `Error` and
exit `EX_FAILURE`, never `EX_SYNTAX`. Exit 2 means venvaxi is broken; it MUST NOT mean the caller
typed something odd.

## Applies to

Every command taking a package, module or qualified name - `show`, `find --package`, `tree`,
`inspect`, `inherits` - and the MCP tools mirroring them.

## Details

### Why three classes and not two

The classes exist because the caller's recovery differs, and a wrong class sends an agent down
the wrong path:

- Malformed - fix the spelling. Installing is impossible.
- Absent - install it, or check the name against `venvaxi list --all`.
- Broken - investigate it. Reinstalling usually will not help.

Collapsing absent into malformed invites an agent to retype a name that was already correct.
Collapsing malformed into absent invites it to install something that can never exist.

### Availability is decided by the import system

'Absent' means *nothing importable answers to this name*, not *no distribution claims it*. A
stdlib module, a namespace package and a local module on `sys.path` are all importable with no
distribution at all, and if one of those is supplied, then the resolver shall not report it as
needing installation - that would be a false statement about the venv.

If a distribution *is* installed but its module cannot be located, then the resolver shall report
it as **broken**, not absent - the caller has the package and something about it is wrong.

### Ordering

Validation shall run before resolution. A name is checked as the caller supplied it, because
distribution-to-import-name resolution can only disguise a malformed name, never repair one.

Resolution of dashes and case (`detect-secrets` -> `detect_secrets`) shall happen after
validation and before the availability check, so a legitimate distribution name is never reported
as absent merely because its import name differs. See
[Qualified name semantics](qualified-name-semantics.md).

### Scope of the malformed check

For a dotted or qualified name, only the **top-level component** shall be validated - it is the
part that has to name something installable. What a malformed tail reports then differs by
command, because each asks its lookup a different question:

- `inspect` and `inherits` resolve the tail through the normal symbol lookup, so a malformed
  tail raises `SymbolNotFoundError` - already the correct answer for 'that symbol is not there'.
- `show --api` validates the **whole** argument and raises `InvalidArgumentError`, because in
  API mode the whole argument *is* the module path under inspection - there is no symbol tail
  for a lookup to answer about. The failure modes in [show](../commands/show.md) state this.
- `tree` reports `count: 0` and exits `EX_OK` - a malformed tail is indistinguishable from a
  submodule with no node, which is its specified definitive empty state (see
  [tree](../commands/tree.md)).
- `find --package` uses the name only to select the package to index and scope the search to;
  components below the top level do not participate in the search, so a malformed tail changes
  nothing.

### Metadata mode

`show <package>` without `--api` reads distribution metadata rather than the import system, so
its 'absent' answer is about the metadata database. Where a name looks like a dotted module path
rather than a distribution name, the `show` command shall say so and name `--api` - a more useful
answer than the generic malformed-name error, and one that MUST be preserved.

## Out of scope

- **Spelling suggestion** - no 'did you mean' recovery; each error reports the class of failure,
  not a corrected name. Never - a guessed correction is a recommendation, and the class alone is
  the fact the caller can act on.
- **Installation** - the resolver reports that a package is absent; it never installs, and no
  error suggests a specific install command beyond checking `venvaxi list --all`. No future spec
  is planned.

## Principles

**Inherited** - project principles that especially bite here:

- Principle 5, definitive empty states
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - the same reasoning that
  separates `count: 0` from a lookup failure separates these three. An answer an agent cannot act
  on is not an answer.
- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - each error reports a fact about the venv. It does not recommend a fix, which is why the class
  has to be right: the class *is* the information.
