# stage1: results

48 runs. Grades are the share of rubric items met, judged blind by Opus 5.5. Evidence items are the facts and connections; judgment items are the final call, which the world does not always force, and are reported apart.

## Evidence grade by condition

| Condition | Shared need | Contradiction | Cross-branch finding | Noise | All |
|---|---|---|---|---|---|
| scoped | 0.78 | 0.83 | 1.00 | 1.00 | 0.90 |
| broadcast | 0.56 | 0.50 | 1.00 | 1.00 | 0.76 |
| tree | 0.44 | 0.67 | 1.00 | 0.93 | 0.76 |
| index | 0.56 | 0.83 | 1.00 | 0.73 | 0.78 |

## Judgment items met

| Condition | Shared need | Contradiction | Cross-branch finding |
|---|---|---|---|
| scoped | 1/3 | 0/3 | 3/3 |
| broadcast | 0/3 | 0/3 | 3/3 |
| tree | 0/3 | 0/3 | 3/3 |
| index | 1/3 | 0/3 | 3/3 |

## Planted-situation checks (runs passing)

| Condition | Shared need: series fetched by at most one node | Shared need: any join, reuse, cross-branch cite or read | Contradiction: branches cited or messaged each other | Contradiction: shipments branch explains the drop | Cross-branch finding: finding reached the demand branch | Cross-branch finding: demand branch states the Pellham cut | Noise: no cross-branch reads or messages |
|---|---|---|---|---|---|---|---|
| scoped | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 |
| broadcast | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 | 0/3 | 3/3 |
| tree | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 3/3 |
| index | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 | 0/3 | 3/3 |

## Mechanics and cost (mean per run)

| Measure | scoped | broadcast | tree | index |
|---|---|---|---|---|
| Cost per run ($) | 0.143 | 0.098 | 0.151 | 0.102 |
| Wall time (s) | 55 | 44 | 97 | 46 |
| Nodes | 7.2 | 4.8 | 7.7 | 4.5 |
| Nodes opened below the split | 3.2 | 0.8 | 3.7 | 0.5 |
| Model turns | 20.5 | 13.9 | 21.9 | 12.8 |
| Cells | 13.3 | 9.1 | 14.3 | 8.3 |
| World calls | 19.3 | 17.4 | 18.7 | 17.1 |
| Duplicate fetches | 3.67 | 2.42 | 4.17 | 2.25 |
| Calls joined in flight | 0.00 | 0.00 | 0.00 | 0.00 |
| Calls reused | 0.00 | 0.00 | 0.00 | 0.00 |
| Calls shared across branches | 0.00 | 0.00 | 0.00 | 0.00 |
| Lines delivered per node | 1.7 | 5.2 | 1.7 | 1.5 |
| Checkpoints published | 0.00 | 0.00 | 0.00 | 0.00 |
| Addressed checkpoints | 0.00 | 0.00 | 0.00 | 0.00 |
| Reopens | 0.00 | 0.00 | 0.00 | 0.00 |
| Node joins | 0.00 | 0.00 | 0.00 | 0.00 |
| Node reuses | 0.00 | 0.00 | 0.00 | 0.00 |
| Cross-branch cites | 0.00 | 0.08 | 0.00 | 0.08 |
| Cross-branch reads | 0.00 | 0.00 | 0.00 | 0.00 |
| Median wall time (s) | 54 | 44 | 57 | 49 |
| Median cost per run ($) | 0.147 | 0.085 | 0.152 | 0.087 |
| Cells that errored (share) | 0.0% | 0.0% | 1.2% | 0.0% |
| Cells that stalled to the 9-minute limit | 0 | 0 | 1 | 0 |
| Runs where a branch opened children | 10/12 | 4/12 | 9/12 | 3/12 |
| Runs that did not answer | 0/12 | 0/12 | 0/12 | 0/12 |

## Shared need: nodes that fetched the slow series (mean)

| Condition | Nodes fetching cma_futures |
|---|---|
| scoped | 2.00 |
| broadcast | 2.00 |
| tree | 2.00 |
| index | 2.00 |

## Cost by workflow (mean per run, $)

| Condition | Shared need | Contradiction | Cross-branch finding | Noise |
|---|---|---|---|---|
| scoped | 0.147 | 0.083 | 0.152 | 0.190 |
| broadcast | 0.098 | 0.073 | 0.124 | 0.097 |
| tree | 0.169 | 0.067 | 0.146 | 0.220 |
| index | 0.094 | 0.078 | 0.138 | 0.096 |

Total: $7.37 (runs $5.92, grading $1.45).
