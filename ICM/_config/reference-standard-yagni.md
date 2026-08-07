---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---

# YAGNI

"You Aren't Gonna Need It" - avoid speculative complexity. Implement only what the current task
requires.

## Principles

- MUST implement only what is directly requested or clearly necessary
- MUST NOT add features, abstractions or configuration options beyond current requirements
- MUST NOT add error handling for scenarios that cannot occur - validate only at system boundaries
- SHOULD reuse existing patterns already present in the codebase over inventing new ones
- SHOULD prefer the Standard Library over adding a dependency
- SHOULD prefer an existing dependency over introducing a new one
- SHOULD write the minimum code that satisfies the requirement, favouring a one-liner where it
  stays readable
- SHOULD NOT create a helper or abstraction for a one-time operation

## Technical Decisions

When a decision trades simplicity against development cost:

- Development cost SHOULD carry little weight
- Quality, simplicity, robustness and scalability SHOULD be preferred
