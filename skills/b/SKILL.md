---
name: b
description: Interpret a snapshot change and investigate its drivers
---
# Snapshot investigation

Use [[delta_check]] to compute the numeric change. Read its result. If unchanged,
return the supplied b narrative and delta evidence without further investigation.
Otherwise run [[k|volume evidence]] and [[l|mix evidence]] concurrently. Ask k to
explain volume against the measured delta, and l to explain mix against that delta.
Pass the delta reference explicitly and read their observations.

These are the same k and l procedures used in baseline analysis, with different
questions and evidence. Combine their observations with `inputs.observations.b`.
Return `text`, `unit`, `changed`, and `internal` child names; declare evidence refs.
