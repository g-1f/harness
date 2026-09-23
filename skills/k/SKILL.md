---
name: k
description: Report volume evidence for reuse by other procedures
---
# Volume evidence

Standard task: **Report volume evidence**. Standard inputs contain `current`,
`previous`, `observations`, `units`; the ordered refs list contains the delta ref.
Identical requests can use session reuse from b or f.

Read the supplied evidence and report `inputs.observations.k` without interpreting
it for a particular consumer. Return text/unit/source/scope and evidence count;
use `inputs.units.k` or USD and source `synthetic/k`. Declare supplied refs.
