---
context-hierarchy: Layer 1
context-hierarchy-role: Workspace task routing
maximum-context-tokens: 300
---

# Workspace Routing

## Routing

Each task category heading details necessary context and locations.

### Create Feature

Consolidated (with Create Unit Test & Code Refactor) into the same `ICM/create-feature` workspace.

- **Navigate to**: `ICM/create-feature`
- **Read**: `CONTEXT.md`
- **Exclude**: * in `.gitignore`

### Create Unit Test

Consolidated (with Create Feature & Code Refactor) into the same `ICM/create-feature` workspace.

- **Navigate to**: `ICM/create-feature`
- **Read**: `CONTEXT.md`
- **Exclude**: * in `.gitignore`

### Code Refactor

Consolidated (with Create Feature & Create Unit Test) into the same `ICM/create-feature` workspace.

- **Navigate to**: `ICM/create-feature`
- **Read**: `CONTEXT.md`
- **Exclude**: * in `.gitignore`

### Create Documentation

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
      - `reference-toolchain-pymarkdown.md`
- **Exclude**: * in `.gitignore`

### Code Review

- **Navigate to**:
  - `src/`
    - **Read**: `venvaxi/*`
  - `tests/`
    - **Read**: `*`
  - `ICM/_config/`
    - **Read**:
      - `reference-toolchain-logging`
      - `reference-toolchain-mypy`
      - `reference-toolchain-ruff`
- **Exclude**: * in `.gitignore`
