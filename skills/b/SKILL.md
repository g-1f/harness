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
numeric difference. If zero, return the supplied b narrative with `changed: false`
and no further investigation. Otherwise call [[k|volume evidence]] and [[l|mix
evidence]] in parallel, using their standard tasks and the delta ref as evidence.
They also support identical session requests by other consumers.

Combine the observations with `inputs.observations.b`. Return `text`, `unit`,
`source`, `scope`, `changed`, `internal` child names and `subchecks`. Declare the
delta and child refs. Calls from a, c and d can await this single operation.
