---
name: artifact_coherence
description: Demo artifact_coherence node
library:
  kind: agent
  profile: critic
---
# artifact_coherence

Read every supplied target reference. Check units, scope, and internal consistency.
For a single target assess internal consistency; for a set assess compatibility.
Return the exact targets, verdict pass/fail/inconclusive, findings, and coverage.
The offline fixture includes incompatible currency units and INCONSISTENT markers.
Never claim to have audited c if no c was supplied. Published refs only.
