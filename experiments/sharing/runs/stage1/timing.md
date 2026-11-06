# stage1: timing

Times are seconds from the start of the run.

## Shared need: the slow series, fetched twice

| Run | Fetches (start–end, node) | Second started |
|---|---|---|
| shared-broadcast-s101 | 23.2–32.3 n4, 27.2–37.0 n3 | 4.0s after the first, while it was in flight |
| shared-broadcast-s102 | 16.1–25.4 n2, 18.0–25.4 n3 | 1.9s after the first, while it was in flight |
| shared-broadcast-s103 | 15.8–25.1 n3, 18.4–28.1 n2 | 2.5s after the first, while it was in flight |
| shared-index-s101 | 17.8–27.7 n3, 21.6–29.8 n2 | 3.8s after the first, while it was in flight |
| shared-index-s102 | 17.0–24.3 n3, 20.9–30.7 n2 | 3.9s after the first, while it was in flight |
| shared-index-s103 | 15.4–24.6 n3, 18.4–28.1 n2 | 3.1s after the first, while it was in flight |
| shared-scoped-s101 | 18.5–28.9 n2, 25.3–35.7 n4 | 6.8s after the first, while it was in flight |
| shared-scoped-s102 | 17.6–26.4 n3, 24.9–35.6 n4 | 7.2s after the first, while it was in flight |
| shared-scoped-s103 | 24.8–34.4 n6, 24.8–34.7 n4 | 0.1s after the first, while it was in flight |
| shared-tree-s101 | 28.7–35.9 n6, 29.0–38.0 n4 | 0.3s after the first, while it was in flight |
| shared-tree-s102 | 16.6–27.5 n3, 26.3–36.4 n4 | 9.7s after the first, while it was in flight |
| shared-tree-s103 | 27.9–37.4 n4, 28.1–37.3 n6 | 0.1s after the first, while it was in flight |

In flight: 12 of 12 duplicate fetches.

## Contradiction: the fire release, found by the disclosures branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| conflict-broadcast-s101 | n2, 26.3 | 26.2 | closed 0.1s before |
| conflict-broadcast-s102 | n2, 38.4 | 27.2 | closed 11.2s before |
| conflict-broadcast-s103 | n2, 28.5 | 27.5 | closed 1.0s before |
| conflict-index-s101 | n2, 26.6 | 30.6 | open 4.0s |
| conflict-index-s102 | n2, 30.7 | 54.9 | open 24.2s |
| conflict-index-s103 | n2, 31.9 | 24.8 | closed 7.1s before |
| conflict-scoped-s101 | n2, 26.7 | 28.3 | open 1.6s |
| conflict-scoped-s102 | n2, 22.7 | 24.4 | open 1.8s |
| conflict-scoped-s103 | n5, 26.3 | 22.3 | closed 3.9s before |
| conflict-tree-s101 | n2, 26.1 | 23.7 | closed 2.3s before |
| conflict-tree-s102 | n2, 24.4 | 21.8 | closed 2.6s before |
| conflict-tree-s103 | n2, 23.7 | 27.8 | open 4.1s |

The shipments branch was still running in 5 of 12 runs.

## Cross-branch finding: the offering release, found by the financing branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| cross-broadcast-s101 | n6, 17.7 | 29.0 | open 11.3s |
| cross-broadcast-s102 | n6, 20.1 | 21.8 | open 1.7s |
| cross-broadcast-s103 | n5, 17.9 | 13.8 | closed 4.1s before |
| cross-index-s101 | n5, 23.5 | 25.8 | open 2.3s |
| cross-index-s102 | n5, 22.8 | 20.1 | closed 2.7s before |
| cross-index-s103 | n5, 21.5 | 27.4 | open 5.9s |
| cross-scoped-s101 | n5, 15.3 | 44.5 | open 29.2s |
| cross-scoped-s102 | n7, 26.4 | 36.2 | open 9.7s |
| cross-scoped-s103 | n5, 20.0 | 46.8 | open 26.8s |
| cross-tree-s101 | n6, 17.8 | 30.7 | open 13.0s |
| cross-tree-s102 | n8, 19.5 | 30.7 | open 11.2s |
| cross-tree-s103 | n7, 23.3 | 37.7 | open 14.4s |

The demand branch was still running in 10 of 12 runs.

## Cross-branch finding: lines that mention it

| Run | First line naming Pellham, the offering or the cut |
|---|---|
| cross-broadcast-s101 | none |
| cross-broadcast-s102 | 28.6s: n5.r1 · **Partly. The debt market is open, but it isn't working for Pellham, the largest b |
| cross-broadcast-s103 | none |
| cross-index-s101 | none |
| cross-index-s102 | 51.2s: n1.r1 · **Recommendation: don't add this month. Hold your current LEAPS and revisit once P |
| cross-index-s103 | none |
| cross-scoped-s101 | none |
| cross-scoped-s102 | none |
| cross-scoped-s103 | none |
| cross-tree-s101 | none |
| cross-tree-s102 | none |
| cross-tree-s103 | none |

## Shape of the work

- Cells per leaf node: median 2, max 4 (193 leaves).
- First-level branches finish within 12.8s of each other (median).
- Reads of the run index: 0. Reads of another branch's artifacts: 0.
- Cells that wait on the stream, by node kind: 104 in nodes that opened children, 0 in leaves.
