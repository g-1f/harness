# stage2: timing

Times are seconds from the start of the run.

## Shared need: the slow series, fetched twice

| Run | Fetches (start–end, node) | Second started |
|---|---|---|
| shared-base-s101 | 23.2–32.3 n4, 27.2–37.0 n3 | 4.0s after the first, while it was in flight |
| shared-base-s102 | 16.1–25.4 n2, 18.0–25.4 n3 | 1.9s after the first, while it was in flight |
| shared-base-s103 | 15.8–25.1 n3, 18.4–28.1 n2 | 2.5s after the first, while it was in flight |
| shared-base-s104 | 19.8–27.9 n2, 22.9–33.8 n4 | 3.1s after the first, while it was in flight |
| shared-base-s105 | 19.5–28.3 n4, 20.6–28.3 n2, 30.4–38.7 n6 | 1.1s after the first, while it was in flight |
| shared-guided-s101 | 15.3–24.0 n2, 20.9–24.0 n3 | 5.6s after the first, while it was in flight |
| shared-guided-s102 | 16.9–24.6 n2, 17.2–24.6 n3 | 0.4s after the first, while it was in flight |
| shared-guided-s103 | 11.0–20.6 n3, 14.1–20.6 n2 | 3.1s after the first, while it was in flight |
| shared-guided-s104 | 16.1–24.7 n2, 17.2–24.7 n3 | 1.1s after the first, while it was in flight |
| shared-guided-s105 | 11.9–19.2 n2, 12.3–19.2 n3 | 0.4s after the first, while it was in flight |
| shared-identity-s101 | 18.7–27.4 n3, 25.0–27.4 n4 | 6.3s after the first, while it was in flight |
| shared-identity-s102 | 20.8–29.2 n3, 26.3–29.2 n4 | 5.5s after the first, while it was in flight |
| shared-identity-s103 | 28.0–35.8 n4, 30.5–35.8 n6 | 2.5s after the first, while it was in flight |
| shared-identity-s104 | 13.7–22.8 n3, 28.2–28.2 n2 | 5.4s after the first returned |
| shared-identity-s105 | 17.1–27.5 n2, 19.8–27.5 n3 | 2.7s after the first, while it was in flight |

In flight: 14 of 15 duplicate fetches.

## conflict: the fire release, found by the disclosures branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| conflict-base-s101 | n2, 26.3 | 26.2 | closed 0.1s before |
| conflict-base-s102 | n2, 38.4 | 27.2 | closed 11.2s before |
| conflict-base-s103 | n2, 28.5 | 27.5 | closed 1.0s before |
| conflict-base-s104 | n2, 32.9 | 23.9 | closed 9.0s before |
| conflict-base-s105 | n2, 25.9 | 26.2 | open 0.3s |
| conflict-guided-s101 | n2, 24.6 | 24.2 | closed 0.4s before |
| conflict-guided-s102 | n2, 28.6 | 28.6 | open 0.0s |
| conflict-guided-s103 | n2, 34.3 | 23.0 | closed 11.3s before |
| conflict-guided-s104 | n2, 30.3 | 23.4 | closed 6.9s before |
| conflict-guided-s105 | n2, 24.4 | 24.9 | open 0.5s |
| conflict-identity-s101 | n2, 30.1 | 38.1 | open 8.1s |
| conflict-identity-s102 | n2, 28.8 | 21.8 | closed 7.0s before |
| conflict-identity-s103 | n2, 21.7 | 23.2 | open 1.6s |
| conflict-identity-s104 | n2, 18.6 | 24.4 | open 5.8s |
| conflict-identity-s105 | n2, 13.7 | 26.6 | open 12.9s |

The shipments branch was still running in 7 of 15 runs.

## conflict-long: the fire release, found by the disclosures branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| conflict-long-base-s101 | n2, 58.8 | 90.5 | open 31.7s |
| conflict-long-base-s102 | n2, 47.0 | 57.0 | open 9.9s |
| conflict-long-base-s103 | n2, 45.5 | 53.2 | open 7.7s |
| conflict-long-base-s104 | n2, 44.2 | 94.6 | open 50.4s |
| conflict-long-base-s105 | n2, 46.6 | 76.3 | open 29.7s |
| conflict-long-guided-s101 | n2, 37.1 | 47.4 | open 10.3s |
| conflict-long-guided-s102 | n2, 37.0 | 76.0 | open 39.0s |
| conflict-long-guided-s103 | n2, 45.5 | 31.5 | closed 14.0s before |
| conflict-long-guided-s104 | n2, 32.2 | 67.1 | open 34.9s |
| conflict-long-guided-s105 | n2, 68.2 | 75.3 | open 7.0s |
| conflict-long-identity-s101 | n2, 37.6 | 32.7 | closed 4.8s before |
| conflict-long-identity-s102 | n2, 41.8 | 46.0 | open 4.3s |
| conflict-long-identity-s103 | n2, 46.3 | 41.3 | closed 5.1s before |
| conflict-long-identity-s104 | n2, 43.6 | 45.4 | open 1.7s |
| conflict-long-identity-s105 | n2, 37.2 | 30.9 | closed 6.2s before |

The shipments branch was still running in 11 of 15 runs.

## cross: the offering release, found by the financing branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| cross-base-s101 | n6, 17.7 | 29.0 | open 11.3s |
| cross-base-s102 | n6, 20.1 | 21.8 | open 1.7s |
| cross-base-s103 | n5, 17.9 | 13.8 | closed 4.1s before |
| cross-base-s104 | n6, 21.0 | 30.9 | open 9.9s |
| cross-base-s105 | n8, 23.7 | 32.9 | open 9.2s |
| cross-guided-s101 | n5, 21.7 | 41.6 | open 19.9s |
| cross-guided-s102 | n5, 19.6 | 23.9 | open 4.3s |
| cross-guided-s103 | n6, 26.5 | 21.5 | closed 5.0s before |
| cross-guided-s104 | n6, 27.8 | 23.7 | closed 4.1s before |
| cross-guided-s105 | n6, 21.1 | 21.8 | open 0.7s |
| cross-identity-s101 | n6, 25.2 | 33.2 | open 8.0s |
| cross-identity-s102 | n5, 21.4 | 25.1 | open 3.7s |
| cross-identity-s103 | n7, 26.6 | 31.2 | open 4.5s |
| cross-identity-s104 | n6, 18.0 | 37.4 | open 19.4s |
| cross-identity-s105 | n6, 21.9 | 25.8 | open 3.9s |

The demand branch was still running in 12 of 15 runs.

## cross-long: the offering release, found by the financing branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| cross-long-base-s101 | n8, 26.2 | 83.4 | open 57.2s |
| cross-long-base-s102 | n8, 30.4 | 64.1 | open 33.7s |
| cross-long-base-s103 | n5, 21.5 | 58.5 | open 36.9s |
| cross-long-base-s104 | n6, 26.9 | 65.6 | open 38.6s |
| cross-long-base-s105 | n5, 23.5 | 62.4 | open 38.9s |
| cross-long-guided-s101 | n7, 27.3 | 54.0 | open 26.6s |
| cross-long-guided-s102 | n5, 22.0 | 49.5 | open 27.5s |
| cross-long-guided-s103 | n6, 26.0 | 54.7 | open 28.7s |
| cross-long-guided-s104 | n6, 27.4 | 55.5 | open 28.1s |
| cross-long-guided-s105 | n6, 24.7 | 41.6 | open 16.9s |
| cross-long-identity-s101 | n5, 27.6 | 48.2 | open 20.6s |
| cross-long-identity-s102 | n8, 31.7 | 55.8 | open 24.0s |
| cross-long-identity-s103 | n8, 27.4 | 60.4 | open 33.0s |
| cross-long-identity-s104 | n5, 23.9 | 49.5 | open 25.5s |
| cross-long-identity-s105 | n5, 19.9 | 48.1 | open 28.2s |

The demand branch was still running in 15 of 15 runs.

## Cross-branch finding: lines that mention it

| Run | First line naming Pellham, the offering or the cut |
|---|---|
| cross-base-s101 | none |
| cross-base-s102 | 28.6s: n5.r1 · **Partly. The debt market is open, but it isn't working for Pellham, the largest b |
| cross-base-s103 | none |
| cross-base-s104 | 33.3s: n5.r1 · **Mostly yes for Norvane, but not for Pellham. The debt market is open, but it can |
| cross-base-s105 | 29.9s: n7.r1 · Mostly yes through debt markets, but not fully for Pellham Power. The evidence is  |
| cross-guided-s101 | 22.6s: n6 reused n5.d7 · doc pellham-offering |
| cross-guided-s102 | 21.3s: n6 reused n5.d3 · doc pellham-offering |
| cross-guided-s103 | 23.4s: n5 joined n6.d5 · doc pellham-offering |
| cross-guided-s104 | 28.9s: n5 reused n6.d4 · doc pellham-offering |
| cross-guided-s105 | 20.0s: n5 joined n6.d5 · doc pellham-offering |
| cross-identity-s101 | 22.0s: n12 joined n6.d5 · doc pellham-offering |
| cross-identity-s102 | 20.4s: n6 joined n5.d3 · doc pellham-offering |
| cross-identity-s103 | 24.3s: n8 joined n7.d6 · doc pellham-offering |
| cross-identity-s104 | 18.6s: n5 reused n6.d3 · doc pellham-offering |
| cross-identity-s105 | 21.7s: n5 joined n6.d4 · doc pellham-offering |
| cross-long-base-s101 | 48.0s: n7.r1 · **Partly. Norvane can fund through debt. Pellham looks constrained, and it has alr |
| cross-long-base-s102 | 47.7s: n7.r1 · **Partly. Debt markets are open to Norvane but are shaky for Pellham, the larger u |
| cross-long-base-s103 | 36.2s: n5.r1 · **Partly. The debt market is open to Norvane but not reliably to Pellham, and the  |
| cross-long-base-s104 | none |
| cross-long-base-s105 | none |
| cross-long-guided-s101 | 24.4s: n8 joined n7.d7 · doc pellham-offering |
| cross-long-guided-s102 | 23.9s: n6 reused n5.d6 · doc pellham-offering |
| cross-long-guided-s103 | 21.5s: n5 joined n6.d5 · doc pellham-offering |
| cross-long-guided-s104 | 20.8s: n5 joined n6.d2 · doc pellham-offering |
| cross-long-guided-s105 | 21.3s: n5 joined n6.d5 · doc pellham-offering |
| cross-long-identity-s101 | 21.8s: n6 joined n5.d5 · doc pellham-offering |
| cross-long-identity-s102 | 30.6s: n7 joined n8.d3 · doc pellham-offering |
| cross-long-identity-s103 | 22.1s: n7 joined n8.d3 · doc pellham-offering |
| cross-long-identity-s104 | 23.8s: n6 joined n5.d5 · doc pellham-offering |
| cross-long-identity-s105 | 18.7s: n6 joined n5.d7 · doc pellham-offering |

## Shape of the work

- Cells per leaf node: median 2, max 8 (312 leaves).
- short workflows: median 2 cells per leaf (212 leaves).
- long workflows: median 2 cells per leaf (100 leaves).
- First-level branches finish within 14.6s of each other (median).
- Reads of the run index: 0. Reads of another branch's artifacts: 1.
- Cells that wait on the stream, by node kind: 157 in nodes that opened children, 0 in leaves.
