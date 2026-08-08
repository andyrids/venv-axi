---
context-hierarchy: Layer 3
context-hierarchy-role: Rules, conventions and guidelines
---

# Standard - Naming Conventions

## References

| Reference      | Pattern                           | Example                          |
| -------------- | --------------------------------- | --------------------------------- |
| Toolchain      | `reference-toolchain-[tool].md`   | `reference-toolchain-mypy.md`    |
| Cookbook       | `reference-cookbook-[package].md` | `reference-cookbook-rich.md`     |
| Standard       | `reference-standard-[name].md`    | `reference-standard-techspec.md` |

## Tracked Artifacts

Permanent, version-controlled. See `specs/README.md` for the state vs motion split.

| Artifact  | Pattern                      | Example                       |
| --------- | ---------------------------- | ----------------------------- |
| Command   | `specs/commands/[verb].md`   | `specs/commands/find.md`      |
| Behavior  | `specs/behaviors/[name].md`  | `specs/behaviors/cache-refresh.md` |
| Plan      | `plans/[slug].md`            | `plans/rich-progress-bar.md`  |

## Output

Ephemeral stage scratch, gitignored. The `[slug]` is shared across all four stages and is the
only thing correlating a run's artifacts - it MUST match the plan slug.

| Output                | Pattern          | Example                       |
| --------------------- | ---------------- | ------------------------------ |
| Technical spec        | `[slug]-spec.md` | `rich-progress-bar-spec.md`   |
| Implementation report | `[slug]-code.md` | `rich-progress-bar-code.md`   |
| Verification report   | `[slug]-test.md` | `rich-progress-bar-test.md`   |
| Documentation report  | `[slug]-docs.md` | `rich-progress-bar-docs.md`   |
