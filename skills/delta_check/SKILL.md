---
name: delta_check
description: Compute the difference between two numeric snapshots
---
# Snapshot difference

Return `inputs.current - inputs.previous` with source and unit metadata. Do not
choose follow-up investigations. The caller interprets the result.

The package includes an optional [JavaScript utility](scripts/observe_delta.js).
The example application binds this skill to that utility's executor. Execution
bindings are host configuration; this prose does not select or authorize a backend.
