---
name: a
description: Establish the baseline claim using capacity and mix evidence
---
# Baseline evidence

Inspect `inputs.observations.a` and the refs explicitly supplied by your caller.
Use [[c|capacity analysis]] to test the baseline's capacity assumptions, without
presuming demand is accelerating. In parallel, use [[l|mix analysis]] to check
whether a stable mix makes that baseline comparison meaningful. Give each child
that purpose in its task. Read their results before forming your observation.

Preserve the source claim and its uncertainty. Return `text`, `unit`, `source`,
`scope` (the task you were asked), and `subchecks` containing the child observations.
Use `inputs.units.a` or the fixture's USD default, and source `synthetic/a`.
Declare supplied and child refs in `based_on`. This is a baseline interpretation;
the root may later invoke the same capacity skill for a different question.
