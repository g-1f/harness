# stage2: results

90 runs. Grades are the share of rubric items met, judged blind by Opus 5.5. Evidence items are the facts and connections; judgment items are the final call, which the world does not always force, and are reported apart.

## Evidence grade by condition

| Condition | Shared need | Contradiction | Cross-branch finding | Noise | Contradiction, long | Cross-branch, long | All |
|---|---|---|---|---|---|---|---|
| base | 0.53 | 0.50 | 1.00 | 1.00 | 0.73 | 0.80 | 0.76 |
| guided | 0.60 | 0.60 | 1.00 | 0.92 | 0.60 | 0.60 | 0.72 |
| identity | 0.60 | 0.50 | 0.73 | 0.80 | 0.40 | 0.73 | 0.63 |

## Judgment items met

| Condition | Shared need | Contradiction | Cross-branch finding | Contradiction, long | Cross-branch, long |
|---|---|---|---|---|---|
| base | 0/5 | 0/5 | 5/5 | 0/5 | 5/5 |
| guided | 0/5 | 1/5 | 5/5 | 0/5 | 5/5 |
| identity | 1/5 | 0/5 | 5/5 | 0/5 | 5/5 |

## Planted-situation checks (runs passing)

| Condition | Shared need: series fetched by at most one node | Shared need: any join, reuse, cross-branch cite or read | Contradiction: branches cited or messaged each other | Contradiction: shipments branch explains the drop | Cross-branch finding: finding reached the demand branch | Cross-branch finding: demand branch states the Pellham cut | Noise: no cross-branch reads or messages | Contradiction, long: branches cited or messaged each other | Contradiction, long: shipments branch explains the drop | Cross-branch, long: finding reached the demand branch | Cross-branch, long: demand branch states the Pellham cut |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 0/5 | 1/5 | 1/5 | 0/5 | 0/5 | 0/5 | 5/5 | 0/5 | 0/5 | 1/5 | 0/5 |
| guided | 5/5 | 5/5 | 3/5 | 0/5 | 1/5 | 0/5 | 5/5 | 4/5 | 0/5 | 2/5 | 0/5 |
| identity | 5/5 | 5/5 | 2/5 | 0/5 | 0/5 | 0/5 | 5/5 | 1/5 | 0/5 | 1/5 | 0/5 |

## Mechanics and cost (mean per run)

| Measure | base | guided | identity |
|---|---|---|---|
| Cost per run ($) | 0.113 | 0.100 | 0.111 |
| Wall time (s) | 61 | 57 | 56 |
| Nodes | 5.2 | 4.6 | 5.4 |
| Nodes opened below the split | 1.4 | 0.8 | 1.5 |
| Model turns | 16.7 | 15.8 | 16.7 |
| Cells | 11.4 | 11.2 | 11.4 |
| World calls | 22.8 | 19.7 | 18.2 |
| Duplicate fetches | 3.40 | 0.00 | 0.00 |
| Calls joined in flight | 0.00 | 1.53 | 1.33 |
| Calls reused | 0.00 | 1.23 | 1.47 |
| Calls shared across branches | 0.00 | 1.93 | 1.77 |
| Lines delivered per node | 5.4 | 6.8 | 7.7 |
| Checkpoints published | 0.00 | 0.00 | 0.00 |
| Addressed checkpoints | 0.00 | 0.00 | 0.00 |
| Reopens | 0.00 | 0.00 | 0.00 |
| Node joins | 0.00 | 0.00 | 0.00 |
| Node reuses | 0.00 | 0.00 | 0.00 |
| Cross-branch cites | 0.27 | 0.60 | 0.40 |
| Cross-branch reads | 0.00 | 0.00 | 0.03 |
| Median wall time (s) | 48 | 48 | 49 |
| Median cost per run ($) | 0.101 | 0.085 | 0.084 |
| Cells that errored (share) | 0.6% | 0.0% | 0.6% |
| Cells that stalled to the 9-minute limit | 0 | 0 | 0 |
| Runs where a branch opened children | 13/30 | 10/30 | 13/30 |
| Runs that did not answer | 0/30 | 0/30 | 0/30 |

## Shared need: nodes that fetched the slow series (mean)

| Condition | Nodes fetching cma_futures |
|---|---|
| base | 2.20 |
| guided | 1.00 |
| identity | 1.00 |

## Cost by workflow (mean per run, $)

| Condition | Shared need | Contradiction | Cross-branch finding | Noise | Contradiction, long | Cross-branch, long |
|---|---|---|---|---|---|---|
| base | 0.124 | 0.070 | 0.134 | 0.093 | 0.093 | 0.165 |
| guided | 0.081 | 0.068 | 0.123 | 0.083 | 0.092 | 0.155 |
| identity | 0.118 | 0.066 | 0.166 | 0.080 | 0.079 | 0.159 |

Total: $12.60 (runs $9.74, grading $2.87), of which $1.54 was spent in an earlier stage on imported runs.
