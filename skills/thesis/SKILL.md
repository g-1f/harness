---
name: thesis
description: Produce a thesis with an explicit application approval decision.
---

Compose [[thesis_draft]] with a fresh [[red_team]] of that exact output. In this
example the host binds this skill to the application composition in
examples/review.py. It can request at most one revision and a new review.

Return a decision artifact containing decision, candidate_ref, reviews, attempts,
history and result. An approved decision contains the reviewed thesis in result;
a blocked decision has result null. Callers must inspect decision before using it
as an approved thesis. Review execution errors fail the composition.
