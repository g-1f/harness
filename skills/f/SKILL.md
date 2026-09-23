---
name: f
description: Assess supplier alternatives using shared volume and mix evidence
---
# Supplier alternatives

Standard task: **Assess supplier alternatives**. Use the standard snapshot inputs
(`current`, `previous`, `observations`, `units`) and the b snapshot ref supplied by
the caller. D and g may request this exact task with session reuse.

Obtain [[delta_check]] using its standard request, then use its ref to request
[[k|volume evidence]] and [[l|mix evidence]] with their standard tasks and session
reuse. B may already have produced both artifacts. Read them and interpret
`inputs.observations.f` for supplier alternatives. Return text/unit/source/scope
and `subchecks`. Declare the snapshot, delta and child refs.
