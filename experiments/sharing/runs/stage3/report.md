# stage3: results

120 runs. Grades are the share of rubric items met, judged blind by Opus 5.5. Evidence items are the facts and connections; judgment items are the final call, which the world does not always force, and are reported apart.

## Evidence grade by condition

| Condition | Shared need | Contradiction | Cross-branch finding | Noise | Contradiction, long | Cross-branch, long | All |
|---|---|---|---|---|---|---|---|
| identity | 0.60 | 0.50 | 0.73 | 0.80 | 0.40 | 0.73 | 0.63 |
| guided | 0.60 | 0.60 | 1.00 | 0.92 | 0.60 | 0.60 | 0.72 |
| identity-data | 0.53 | 0.70 | 0.60 | 0.96 | 0.67 | 0.40 | 0.64 |
| guided-data | 0.73 | 0.70 | 0.47 | 0.96 | 0.33 | 0.47 | 0.61 |

## Judgment items met

| Condition | Shared need | Contradiction | Cross-branch finding | Contradiction, long | Cross-branch, long |
|---|---|---|---|---|---|
| identity | 1/5 | 0/5 | 5/5 | 0/5 | 5/5 |
| guided | 0/5 | 1/5 | 5/5 | 0/5 | 5/5 |
| identity-data | 1/5 | 0/5 | 5/5 | 0/5 | 5/5 |
| guided-data | 2/5 | 0/5 | 5/5 | 1/5 | 5/5 |

## Planted-situation checks (runs passing)

| Condition | Shared need: series fetched by at most one node | Shared need: any join, reuse, cross-branch cite or read | Contradiction: branches cited or messaged each other | Contradiction: shipments branch explains the drop | Cross-branch finding: finding reached the demand branch | Cross-branch finding: demand branch states the Pellham cut | Noise: no cross-branch reads or messages | Contradiction, long: branches cited or messaged each other | Contradiction, long: shipments branch explains the drop | Cross-branch, long: finding reached the demand branch | Cross-branch, long: demand branch states the Pellham cut |
|---|---|---|---|---|---|---|---|---|---|---|---|
| identity | 5/5 | 5/5 | 2/5 | 0/5 | 0/5 | 0/5 | 5/5 | 1/5 | 0/5 | 1/5 | 0/5 |
| guided | 5/5 | 5/5 | 3/5 | 0/5 | 1/5 | 0/5 | 5/5 | 4/5 | 0/5 | 2/5 | 0/5 |
| identity-data | 5/5 | 5/5 | 3/5 | 0/5 | 0/5 | 0/5 | 5/5 | 2/5 | 2/5 | 0/5 | 1/5 |
| guided-data | 5/5 | 5/5 | 5/5 | 0/5 | 0/5 | 0/5 | 5/5 | 5/5 | 1/5 | 3/5 | 1/5 |

## Mechanics and cost (mean per run)

| Measure | identity | guided | identity-data | guided-data |
|---|---|---|---|---|
| Cost per run ($) | 0.111 | 0.100 | 0.104 | 0.099 |
| Wall time (s) | 56 | 57 | 48 | 47 |
| Nodes | 5.4 | 4.6 | 4.6 | 4.5 |
| Nodes opened below the split | 1.5 | 0.8 | 0.8 | 0.7 |
| Model turns | 16.7 | 15.8 | 14.7 | 14.7 |
| Cells | 11.4 | 11.2 | 10.1 | 10.2 |
| World calls | 18.2 | 19.7 | 16.9 | 17.8 |
| Duplicate fetches | 0.00 | 0.00 | 0.00 | 0.00 |
| Calls joined in flight | 1.33 | 1.53 | 1.33 | 1.33 |
| Calls reused | 1.47 | 1.23 | 1.00 | 1.23 |
| Calls shared across branches | 1.77 | 1.93 | 1.60 | 1.73 |
| Data lines | 0.0 | 0.0 | 7.4 | 8.1 |
| Lines delivered per node | 7.7 | 6.8 | 11.5 | 12.1 |
| Lines taken per node (recorded) | 0.0 | 0.0 | 0.0 | 0.0 |
| Data lines taken per node (recorded) | 0.0 | 0.0 | 0.0 | 0.0 |
| Checkpoints published | 0.00 | 0.00 | 0.00 | 0.00 |
| Addressed checkpoints | 0.00 | 0.00 | 0.00 | 0.00 |
| Reopens | 0.00 | 0.00 | 0.00 | 0.00 |
| Node joins | 0.00 | 0.00 | 0.00 | 0.00 |
| Node reuses | 0.00 | 0.00 | 0.00 | 0.00 |
| Cross-branch cites | 0.40 | 0.60 | 0.43 | 1.23 |
| Cross-branch reads | 0.03 | 0.00 | 0.00 | 0.00 |
| Median wall time (s) | 49 | 48 | 41 | 40 |
| Median cost per run ($) | 0.084 | 0.085 | 0.097 | 0.084 |
| Cells that errored (share) | 0.6% | 0.0% | 0.0% | 0.0% |
| Cells that stalled to the 9-minute limit | 0 | 0 | 0 | 0 |
| Runs where a branch opened children | 13/30 | 10/30 | 12/30 | 10/30 |
| Runs that did not answer | 0/30 | 0/30 | 0/30 | 0/30 |

## Shared need: nodes that fetched the slow series (mean)

| Condition | Nodes fetching cma_futures |
|---|---|
| identity | 1.00 |
| guided | 1.00 |
| identity-data | 1.00 |
| guided-data | 1.00 |

## Cost by workflow (mean per run, $)

| Condition | Shared need | Contradiction | Cross-branch finding | Noise | Contradiction, long | Cross-branch, long |
|---|---|---|---|---|---|---|
| identity | 0.118 | 0.066 | 0.166 | 0.080 | 0.079 | 0.159 |
| guided | 0.081 | 0.068 | 0.123 | 0.083 | 0.092 | 0.155 |
| identity-data | 0.104 | 0.077 | 0.140 | 0.090 | 0.077 | 0.133 |
| guided-data | 0.080 | 0.071 | 0.130 | 0.090 | 0.071 | 0.150 |

Total: $16.20 (runs $12.41, grading $3.79), of which $8.26 was spent in an earlier stage on imported runs.
