---
name: evidence-check
description: Check one bounded piece of evidence
library:
  ttl_seconds: 3600
---
# Evidence Check

Inspect the supplied evidence and scope. Separate observations from inferences.
Return the finding, evidence references, and limitations. For independent parts,
call this skill recursively with a narrower objective and a distinct operation key.
