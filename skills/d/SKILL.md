---
name: d
description: Cross-check supply and compose supplier and inventory analyses
---
# Supply cross-check

Read the explicitly supplied baseline and capacity views. Request [[b|common
snapshot evidence]] using its standard neutral task, projected inputs, empty refs
and session reuse. This later call can reuse b's accepted result.

If b indicates accelerating demand and `inputs.observations.d` identifies
concentrated supplier exposure, run [[f|supplier alternatives]] and [[g|inventory
protection]] concurrently. Request f's standard task with session reuse and the
b ref; ask g to interpret inventory protection with supplier alternatives and
pass that same b ref. G can independently request the very same f operation.

Otherwise omit those follow-ups. Return the supplied d observation, `snapshot`,
`investigated`, and the follow-up `subchecks`, with unit/source/scope. Declare the
caller views, b ref and any follow-up refs in `based_on`.
