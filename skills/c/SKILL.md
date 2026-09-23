---
name: c
description: Interpret capacity and conditionally investigate policy
---
# Capacity interpretation

Read your caller's question and `inputs.observations.c`. If
`inputs.capacity_requires_snapshot` is false, return the supplied observation and
no snapshot ref. Otherwise request [[b|common snapshot evidence]] with b's standard
neutral task, projected inputs, no refs, and session reuse. B might be absent,
running under a, or already accepted. The runtime resolves those states atomically.

Interpret the common snapshot for the capacity question here. If the snapshot's
narrative indicates stable rather than accelerating demand, investigate [[h|policy
outlook]] with the b ref. Read the result before forming your view.

Return `text`, `unit`, `source`, `scope`, `snapshot`, `policy` and `subchecks`.
Use the supplied c observation and `inputs.units.c` or USD; source `synthetic/c`.
Declare the snapshot and policy evidence refs. Your view remains a distinct output
from a even when both consume the same b artifact.
