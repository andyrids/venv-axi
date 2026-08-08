---
context-hierarchy: Layer 1
context-hierarchy-role: Workspace task routing
maximum-context-tokens: 300
---

# Workspace routing

## Routing

Each task category heading details necessary context and locations.

### Create feature

Consolidated (with Create Unit Test & Code Refactor) into the same `ICM/create-feature` workspace.

- **Navigate to**: `ICM/create-feature`
- **Read**: `CONTEXT.md`
- **Exclude**: * in `.gitignore`

### Create unit test

Consolidated (with Create Feature & Code Refactor) into the same `ICM/create-feature` workspace.

- **Navigate to**: `ICM/create-feature`
- **Read**: `CONTEXT.md`
- **Exclude**: * in `.gitignore`

### Code refactor

Consolidated (with Create Feature & Create Unit Test) into the same `ICM/create-feature` workspace.

- **Navigate to**: `ICM/create-feature`
- **Read**: `CONTEXT.md`
- **Exclude**: * in `.gitignore`

### Create documentation

Multi-location route (unlike the single-workspace sections above); reads reference material from
several directories rather than one `ICM/` workspace.

- **Navigate to**:
  - `.`
    - **Read**:
      - `CHANGELOG.md`
      - `COPYRIGHT`
      - `README.md`
      - `LICENSE`
  - `src/`
    - **Read**: `venvaxi/*`
  - `tests/`
    - **Read**: `*`
  - `ICM/_config/`
    - **Read**:
      - `reference-standard-attribution.md`
      - `reference-standard-changelog.md`
      - `reference-standard-docstrings.md`
      - `reference-standard-markdown.md`
      - `reference-toolchain-pymarkdown.md`
- **Exclude**: * in `.gitignore`

### Code review

Review against `specs/`, not against personal preference - the spec is the acceptance criteria.

- **Navigate to**:
  - `specs/`
    - **Read**: `*` - the behavioural contract the code must conform to
  - `src/`
    - **Read**: `venvaxi/*`
  - `tests/`
    - **Read**: `*`
  - `ICM/_config/`
    - **Read**:
      - `reference-toolchain-logging.md`
      - `reference-toolchain-mypy.md`
      - `reference-toolchain-ruff.md`
- **Exclude**: * in `.gitignore`
