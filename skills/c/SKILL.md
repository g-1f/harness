---
name: c
description: Interpret capacity evidence for the caller's specific question
---
# Capacity evidence

Read your task first. A baseline check asks whether the starting assumptions are
supported; an acceleration investigation asks whether capacity can meet growing
demand. These are different questions even with identical supplied observations.

Inspect `inputs.observations.c`. Use [[k|volume evidence]] to corroborate capacity
for this specific question, explicitly passing the question in the child's task.
Read the returned observation, preserve uncertainty, and distinguish evidence
from inference. Do not reuse another call just because its node is named c or k.

Return `text`, `unit`, `source`, `scope` (your task), and `subchecks` containing the
volume observation. Use `inputs.units.c` or USD and source `synthetic/c`.
Declare supplied and child refs in `based_on`.
