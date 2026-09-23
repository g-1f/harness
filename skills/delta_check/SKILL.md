---
name: delta_check
description: Compute the difference between two numeric snapshots
---
# Snapshot difference

Standard task: **Compute snapshot difference**. Standard inputs contain `current`,
`previous`, `observations`, `units`; no artifact refs are required. Identical requests
can use session reuse from b, f, g or h.

Return `inputs.current - inputs.previous` with source and unit metadata. Do not
choose follow-up investigations. The caller interprets the result. The package
includes an optional [JavaScript utility](scripts/observe_delta.js); the application
binds this procedure to that resource executor outside frontmatter.
