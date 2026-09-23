---
name: b
description: Demo b node
library:
  kind: agent
---
# b

First run [[delta_check]]: its embedded script computes a factual change.
Observe the output. If unchanged, return the supplied narrative and the delta
without further work. Otherwise run [[k]] and [[l]] concurrently and combine their
observations with the supplied narrative. Return evidence refs. The host does not
know what changed means; interpret the local instruction in this node.
