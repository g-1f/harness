---
name: g
description: Interpret inventory protection using mix and supplier alternatives
---
# Inventory protection

Read the supplied b reference. Obtain [[delta_check]] using its standard request.
Use that delta ref to request [[l|mix evidence]] with session reuse. Also request
[[f|supplier alternatives]] with its exact standard task, projected snapshot inputs,
the supplied b ref and session reuse. D may still be awaiting the same f operation.

Read both results and interpret `inputs.observations.g` for inventory protection.
Return text/unit/source/scope and `subchecks`, declaring the supplied snapshot,
delta, mix and supplier refs. The shared f execution is not owned exclusively by
either d or g; each caller only owns its wait.
