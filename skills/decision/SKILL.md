---
name: decision
description: Synthesize a decision from independent evidence checks
library:
  ttl_seconds: 3600
  review:
    critics: [counterexample-review]
    max_revisions: 1
---
# Decision

Consult [[evidence-check]] for supporting evidence and alternative explanations.
Use independent recursive calls when the evidence can be investigated separately.
Retain the binding inputs and evidence references. State unresolved uncertainty.
Submit a conclusion with accepted supporting artifact references in based_on.
