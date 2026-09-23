---
name: i
description: Inspect the evidence assigned to i
library:
  kind: agent
---
# i

Inspect `inputs.observations.i` and any supplied evidence references. Produce
an observation that preserves the source's claim and uncertainty. Distinguish
what the evidence says from your inference; do not invent supporting facts.

Return content with `text`, `unit`, and `source`. Use `inputs.units.i` if
provided, otherwise the synthetic fixture's USD unit; identify the source as
`synthetic/i`. Keep supplied evidence references in `based_on`.

Write whatever PTC is useful after inspecting the input. This node supplies prose,
not an authored execution program or a predetermined next branch.
