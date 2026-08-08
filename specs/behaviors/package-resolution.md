---
context-hierarchy: Layer 3
context-hierarchy-role: Desired state (specification)
---

# Behavior: Package resolution

## Rule

A package argument fails in exactly one of three ways, and the exception says which:

| The name is | Meaning | Error |
| ----------- | ------- | ----- |
| **Malformed** | Not a possible package name at all | `InvalidArgumentError` |
| **Absent** | A possible name, but nothing in the venv provides it | `PackageNotFoundError` |
| **Broken** | Provided, but will not import | `PackageImportError` |

No user-supplied argument value may produce `EX_SYNTAX`. Exit 2 means venvaxi is broken; it MUST
NOT mean the caller typed something odd.

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
distribution at all, and reporting one of those as needing installation is a false statement
about the venv.

A distribution that *is* installed but whose module cannot be located is **broken**, not absent -
the caller has the package and something about it is wrong.

### Ordering

Validation runs before resolution. A name is checked as the caller supplied it, because
distribution-to-import-name resolution can only disguise a malformed name, never repair one.

Resolution of dashes and case (`detect-secrets` -> `detect_secrets`) happens after validation and
before the availability check, so a legitimate distribution name is never reported as absent
merely because its import name differs. See
[Qualified name semantics](qualified-name-semantics.md).

### Scope of the malformed check

For a dotted or qualified name, only the **top-level component** is validated - it is the part
that has to name something installable. A malformed tail resolves to `SymbolNotFoundError`
through the normal lookup, which is already the correct answer for 'that symbol is not there'.

### Metadata mode

`show <package>` without `--api` reads distribution metadata rather than the import system, so
its 'absent' answer is about the metadata database. Where it can tell that a name looks like a
dotted module path rather than a distribution name, it says so and names `--api` - a more useful
answer than the generic malformed-name error, and it MUST be preserved.

## Principles

**Inherited** - project principles that especially bite here:

- Principle 5, definitive empty states
  ([The 10 AXI Principles](../principles.md#the-10-axi-principles)) - the same reasoning that
  separates `count: 0` from a lookup failure separates these three. An answer an agent cannot act
  on is not an answer.
- [Report what a symbol is, not how to use it](../principles.md#report-what-a-symbol-is-not-how-to-use-it)
  - each error reports a fact about the venv. It does not recommend a fix, which is why the class
  has to be right: the class *is* the information.
