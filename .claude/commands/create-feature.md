---
description: Run the ICM create-feature pipeline
---

# Create Feature

Feature request: $ARGUMENTS

Read `ICM/create-feature/CONTEXT.md` and execute the pipeline stage by stage, honouring every
CHECKPOINT that fires and the workspace acceptance criteria.

A checkpoint marked *only if* is conditional. Discharge its condition with evidence in the
visible response rather than passing over it silently - a gate that does not fire is not a gate
you skipped, but an unannounced skip is indistinguishable from one.
