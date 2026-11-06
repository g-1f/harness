# stage1: results

48 runs. Grade is the share of rubric items met, judged blind by Opus 5.5.

## Answer quality by design

| Design | Shared need | Contradiction | Cross-branch finding | Noise | All |
|---|---|---|---|---|---|
| scoped | 0.67 | 0.56 | 1.00 | 1.00 | 0.81 |
| broadcast | 0.42 | 0.33 | 1.00 | 1.00 | 0.69 |
| tree | 0.33 | 0.44 | 1.00 | 0.93 | 0.68 |
| index | 0.50 | 0.56 | 1.00 | 0.73 | 0.70 |

## Planted-situation checks (runs passing)

| Design | Shared need: series fetched by at most one node | Shared need: any join, reuse, cross-branch cite or read | Contradiction: branches cited or messaged each other | Contradiction: shipments branch explains the drop | Cross-branch finding: finding reached the demand branch | Cross-branch finding: demand branch states the Pellham cut | Noise: no cross-branch reads or messages |
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
| World calls | 19.3 | 17.4 | 18.7 | 17.1 |
| Lines delivered per node | 1.7 | 5.2 | 1.7 | 1.5 |
| Joins | 0.00 | 0.00 | 0.00 | 0.00 |
| Reuses | 0.00 | 0.00 | 0.00 | 0.00 |
| Cross-branch cites | 0.00 | 0.08 | 0.00 | 0.08 |
| Cross-branch reads | 0.00 | 0.00 | 0.00 | 0.00 |
| Addressed checkpoints | 0.00 | 0.00 | 0.00 | 0.00 |
| Checkpoints published | 0.00 | 0.00 | 0.00 | 0.00 |
| Median wall time (s) | 54 | 44 | 57 | 49 |
| Median cost per run ($) | 0.147 | 0.085 | 0.152 | 0.087 |
| Cells that errored (share) | 0.0% | 0.0% | 1.2% | 0.0% |
| Cells that stalled to the 9-minute limit | 0 | 0 | 1 | 0 |
| Runs where a branch opened children | 10/12 | 4/12 | 9/12 | 3/12 |

## Shared need: fetchers of the slow series (mean)

| Design | Nodes fetching cma_futures |
|---|---|
| scoped | 2.00 |
| broadcast | 2.00 |
| tree | 2.00 |
| index | 2.00 |

Total spent: $7.37 (runs $5.92, grading $1.45).
