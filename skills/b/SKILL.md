---
name: b
description: Produce neutral snapshot evidence for several consuming procedures
---
# Shared snapshot evidence

Standard task: **Produce snapshot evidence**. Standard inputs are the JSON object
with `current`, `previous`, `observations` and `units`; omit consumer-specific flags.
This task needs no input artifact refs. Callers may use session reuse for this
identical request. No caller-specific interpretation is part of the artifact.

Use [[delta_check]] with its standard task and the same projected inputs. Read the
numeric difference. Publish a checkpoint containing the measurement, unit and source
based on the delta ref. This checkpoint is independently reviewed and can be consumed
while subsequent work runs. If zero, return the supplied b narrative with `changed: false`
and no further investigation. Otherwise call [[k|volume evidence]] and [[l|mix
evidence]] in parallel, using their standard tasks and the delta ref as evidence.
They also support identical session requests by other consumers.

Combine the observations with `inputs.observations.b`. Return `text`, `unit`,
`source`, `scope`, `changed`, `internal` child names and `subchecks`. Declare the
checkpoint, delta and child refs. Calls from a, c and d can await this single operation.

A different task, **Assess capacity from snapshot checkpoint**, accepts that
checkpoint as its sole input ref and the same projected inputs. Inspect it and
return a capacity-focused text/unit/source/scope view with the checkpoint in
`based_on`. This is a separate fresh execution of the same skill, not a reuse of
the neutral snapshot task; its result can inform c while the neutral task runs.
