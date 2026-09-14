---
name: counterexample-review
description: Challenge a candidate against its evidence and binding inputs
library:
  profile: critic
---
# Counterexample Review

Read the granted candidate. Look for counterexamples, missing constraints,
contradictory evidence, scope mismatches, and unsupported conclusions.
Check evidence independently where the available tools allow it.
Submit candidate_ref, verdict, and findings in content. Use pass only when there
are no unresolved findings. Cite evidence and concrete reproduction steps in
findings. If evidence is inaccessible, return fail with that limitation.
