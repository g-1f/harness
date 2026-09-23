---
name: c
description: Interpret capacity and conditionally investigate policy
---
# Capacity interpretation

Read your caller's question and `inputs.observations.c`. If
`inputs.capacity_requires_snapshot` is false, return the supplied observation and
no snapshot ref. Otherwise request [[b|common snapshot evidence]] with b's standard
neutral task, projected inputs, no refs, and session reuse. B might be absent,
running under a, or already completed. The runtime resolves those states atomically.
Open this operation and observe its published measurement checkpoint, replaying it
even if b has already finished. If capacity needs an aspect the neutral checkpoint
does not answer, call b again with its distinct capacity-focused task and that
checkpoint as an explicit ref. Read the focused result, then await b's final result.

Interpret the common snapshot for the capacity question here. If the snapshot's
narrative indicates stable rather than accelerating demand, investigate [[h|policy
outlook]] with the b ref. Read the result before forming your view.

Return `text`, `unit`, `source`, `scope`, `snapshot`, `policy` and `subchecks`.
Use the supplied c observation and `inputs.units.c` or USD; source `synthetic/c`.
Declare the checkpoint, focused view, snapshot and policy evidence refs. Your view remains a distinct output
from a even when both consume the same b artifact.
