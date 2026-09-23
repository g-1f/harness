---
name: delta_check
description: Optional deterministic snapshot-delta utility
library:
  kind: code
  script: scripts/observe_delta.js
---
# Delta check utility

Compute the difference between the two bound numeric snapshots using the bundled
[observe_delta.js](scripts/observe_delta.js) utility. Return the value and source
metadata without making a model call. This authored utility is the only code node
in this example graph; it does not decide whether to investigate or which nodes
to invoke. The calling agent observes its result and makes those decisions.

A skill author may bundle a utility like this when a stable calculation is useful.
Other skills need only prose and links; bundling code is optional.
