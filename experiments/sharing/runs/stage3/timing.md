# stage3: timing

Times are seconds from the start of the run.

## Shared need: the slow series, fetched twice

| Run | Fetches (start–end, node) | Second started |
|---|---|---|
| shared-guided-data-s101 | 14.8–23.5 n3, 16.1–23.5 n2 | 1.3s after the first, while it was in flight |
| shared-guided-data-s102 | 14.7–24.1 n3, 18.0–24.1 n2 | 3.3s after the first, while it was in flight |
| shared-guided-data-s103 | 10.9–18.2 n3, 11.5–18.2 n2 | 0.6s after the first, while it was in flight |
| shared-guided-data-s104 | 10.8–20.2 n3, 11.7–20.2 n2 | 0.9s after the first, while it was in flight |
| shared-guided-data-s105 | 13.7–21.0 n2, 15.8–21.0 n3 | 2.2s after the first, while it was in flight |
| shared-guided-s101 | 15.3–24.0 n2, 20.9–24.0 n3 | 5.6s after the first, while it was in flight |
| shared-guided-s102 | 16.9–24.6 n2, 17.2–24.6 n3 | 0.4s after the first, while it was in flight |
| shared-guided-s103 | 11.0–20.6 n3, 14.1–20.6 n2 | 3.1s after the first, while it was in flight |
| shared-guided-s104 | 16.1–24.7 n2, 17.2–24.7 n3 | 1.1s after the first, while it was in flight |
| shared-guided-s105 | 11.9–19.2 n2, 12.3–19.2 n3 | 0.4s after the first, while it was in flight |
| shared-identity-data-s101 | 15.9–25.3 n2, 24.2–25.3 n4 | 8.2s after the first, while it was in flight |
| shared-identity-data-s102 | 16.8–27.1 n2, 17.7–27.1 n3 | 0.8s after the first, while it was in flight |
| shared-identity-data-s103 | 14.7–24.2 n4, 15.4–24.2 n2 | 0.7s after the first, while it was in flight |
| shared-identity-data-s104 | 11.2–22.1 n2, 14.6–22.1 n3 | 3.5s after the first, while it was in flight |
| shared-identity-data-s105 | 11.9–19.2 n2, 15.0–19.2 n3 | 3.1s after the first, while it was in flight |
| shared-identity-s101 | 18.7–27.4 n3, 25.0–27.4 n4 | 6.3s after the first, while it was in flight |
| shared-identity-s102 | 20.8–29.2 n3, 26.3–29.2 n4 | 5.5s after the first, while it was in flight |
| shared-identity-s103 | 28.0–35.8 n4, 30.5–35.8 n6 | 2.5s after the first, while it was in flight |
| shared-identity-s104 | 13.7–22.8 n3, 28.2–28.2 n2 | 5.4s after the first returned |
| shared-identity-s105 | 17.1–27.5 n2, 19.8–27.5 n3 | 2.7s after the first, while it was in flight |

In flight: 19 of 20 duplicate fetches.

## conflict: the fire release, found by the disclosures branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| conflict-guided-data-s101 | n2, 24.6 | 24.6 | closed 0.1s before |
| conflict-guided-data-s102 | n2, 21.4 | 26.0 | open 4.6s |
| conflict-guided-data-s103 | n2, 29.9 | 24.6 | closed 5.3s before |
| conflict-guided-data-s104 | n2, 29.5 | 17.4 | closed 12.1s before |
| conflict-guided-data-s105 | n2, 20.9 | 25.1 | open 4.1s |
| conflict-guided-s101 | n2, 24.6 | 24.2 | closed 0.4s before |
| conflict-guided-s102 | n2, 28.6 | 28.6 | open 0.0s |
| conflict-guided-s103 | n2, 34.3 | 23.0 | closed 11.3s before |
| conflict-guided-s104 | n2, 30.3 | 23.4 | closed 6.9s before |
| conflict-guided-s105 | n2, 24.4 | 24.9 | open 0.5s |
| conflict-identity-data-s101 | n2, 21.9 | 23.7 | open 1.8s |
| conflict-identity-data-s102 | n2, 20.9 | 20.2 | closed 0.7s before |
| conflict-identity-data-s103 | n2, 26.6 | 24.6 | closed 2.0s before |
| conflict-identity-data-s104 | n2, 20.8 | 20.9 | open 0.1s |
| conflict-identity-data-s105 | n2, 17.8 | 23.5 | open 5.7s |
| conflict-identity-s101 | n2, 30.1 | 38.1 | open 8.1s |
| conflict-identity-s102 | n2, 28.8 | 21.8 | closed 7.0s before |
| conflict-identity-s103 | n2, 21.7 | 23.2 | open 1.6s |
| conflict-identity-s104 | n2, 18.6 | 24.4 | open 5.8s |
| conflict-identity-s105 | n2, 13.7 | 26.6 | open 12.9s |

The shipments branch was still running in 11 of 20 runs.

## conflict-long: the fire release, found by the disclosures branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| conflict-long-guided-data-s101 | n2, 34.4 | 41.1 | open 6.7s |
| conflict-long-guided-data-s102 | n2, 66.0 | 37.5 | closed 28.4s before |
| conflict-long-guided-data-s103 | n2, 33.2 | 29.3 | closed 3.9s before |
| conflict-long-guided-data-s104 | n2, 31.9 | 34.6 | open 2.7s |
| conflict-long-guided-data-s105 | n2, 35.7 | 48.3 | open 12.6s |
| conflict-long-guided-s101 | n2, 37.1 | 47.4 | open 10.3s |
| conflict-long-guided-s102 | n2, 37.0 | 76.0 | open 39.0s |
| conflict-long-guided-s103 | n2, 45.5 | 31.5 | closed 14.0s before |
| conflict-long-guided-s104 | n2, 32.2 | 67.1 | open 34.9s |
| conflict-long-guided-s105 | n2, 68.2 | 75.3 | open 7.0s |
| conflict-long-identity-data-s101 | n2, 35.0 | 50.0 | open 15.1s |
| conflict-long-identity-data-s102 | n2, 33.3 | 41.3 | open 8.0s |
| conflict-long-identity-data-s103 | n2, 37.1 | 39.7 | open 2.6s |
| conflict-long-identity-data-s104 | n2, 38.7 | 31.4 | closed 7.3s before |
| conflict-long-identity-data-s105 | n2, 32.0 | 25.3 | closed 6.7s before |
| conflict-long-identity-s101 | n2, 37.6 | 32.7 | closed 4.8s before |
| conflict-long-identity-s102 | n2, 41.8 | 46.0 | open 4.3s |
| conflict-long-identity-s103 | n2, 46.3 | 41.3 | closed 5.1s before |
| conflict-long-identity-s104 | n2, 43.6 | 45.4 | open 1.7s |
| conflict-long-identity-s105 | n2, 37.2 | 30.9 | closed 6.2s before |

The shipments branch was still running in 12 of 20 runs.

## cross: the offering release, found by the financing branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| cross-guided-data-s101 | n6, 21.4 | 22.0 | open 0.7s |
| cross-guided-data-s102 | n5, 23.2 | 18.5 | closed 4.7s before |
| cross-guided-data-s103 | n6, 21.6 | 24.6 | open 3.0s |
| cross-guided-data-s104 | n6, 18.4 | 22.1 | open 3.7s |
| cross-guided-data-s105 | n6, 15.9 | 18.9 | open 3.0s |
| cross-guided-s101 | n5, 21.7 | 41.6 | open 19.9s |
| cross-guided-s102 | n5, 19.6 | 23.9 | open 4.3s |
| cross-guided-s103 | n6, 26.5 | 21.5 | closed 5.0s before |
| cross-guided-s104 | n6, 27.8 | 23.7 | closed 4.1s before |
| cross-guided-s105 | n6, 21.1 | 21.8 | open 0.7s |
| cross-identity-data-s101 | n6, 23.6 | 21.8 | closed 1.9s before |
| cross-identity-data-s102 | n6, 25.9 | 17.3 | closed 8.6s before |
| cross-identity-data-s103 | n6, 23.3 | 23.9 | open 0.6s |
| cross-identity-data-s104 | n5, 14.9 | 17.0 | open 2.1s |
| cross-identity-data-s105 | n5, 19.5 | 18.6 | closed 0.9s before |
| cross-identity-s101 | n6, 25.2 | 33.2 | open 8.0s |
| cross-identity-s102 | n5, 21.4 | 25.1 | open 3.7s |
| cross-identity-s103 | n7, 26.6 | 31.2 | open 4.5s |
| cross-identity-s104 | n6, 18.0 | 37.4 | open 19.4s |
| cross-identity-s105 | n6, 21.9 | 25.8 | open 3.9s |

The demand branch was still running in 14 of 20 runs.

## cross-long: the offering release, found by the financing branch

| Run | Found by, at | Branch that needs it ended | Window |
|---|---|---|---|
| cross-long-guided-data-s101 | n6, 26.5 | 39.9 | open 13.4s |
| cross-long-guided-data-s102 | n5, 26.1 | 71.8 | open 45.7s |
| cross-long-guided-data-s103 | n5, 21.8 | 38.4 | open 16.6s |
| cross-long-guided-data-s104 | n6, 23.5 | 41.8 | open 18.3s |
| cross-long-guided-data-s105 | n6, 24.5 | 37.9 | open 13.3s |
| cross-long-guided-s101 | n7, 27.3 | 54.0 | open 26.6s |
| cross-long-guided-s102 | n5, 22.0 | 49.5 | open 27.5s |
| cross-long-guided-s103 | n6, 26.0 | 54.7 | open 28.7s |
| cross-long-guided-s104 | n6, 27.4 | 55.5 | open 28.1s |
| cross-long-guided-s105 | n6, 24.7 | 41.6 | open 16.9s |
| cross-long-identity-data-s101 | n6, 22.7 | 42.7 | open 20.0s |
| cross-long-identity-data-s102 | n6, 27.5 | 49.4 | open 21.9s |
| cross-long-identity-data-s103 | n5, 21.5 | 45.5 | open 23.9s |
| cross-long-identity-data-s104 | n5, 21.1 | 42.7 | open 21.6s |
| cross-long-identity-data-s105 | n5, 26.7 | 52.5 | open 25.8s |
| cross-long-identity-s101 | n5, 27.6 | 48.2 | open 20.6s |
| cross-long-identity-s102 | n8, 31.7 | 55.8 | open 24.0s |
| cross-long-identity-s103 | n8, 27.4 | 60.4 | open 33.0s |
| cross-long-identity-s104 | n5, 23.9 | 49.5 | open 25.5s |
| cross-long-identity-s105 | n5, 19.9 | 48.1 | open 28.2s |

The demand branch was still running in 20 of 20 runs.

## Cross-branch finding: lines that mention it

| Run | First line naming Pellham, the offering or the cut |
|---|---|
| cross-guided-data-s101 | 17.1s: n2.d3 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-guided-data-s102 | 14.9s: n2.d4 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-guided-data-s103 | 17.2s: n2.d5 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-guided-data-s104 | 15.8s: n2.d4 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-guided-data-s105 | 11.5s: n2.d4 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-guided-s101 | 22.6s: n6 reused n5.d7 · doc pellham-offering |
| cross-guided-s102 | 21.3s: n6 reused n5.d3 · doc pellham-offering |
| cross-guided-s103 | 23.4s: n5 joined n6.d5 · doc pellham-offering |
| cross-guided-s104 | 28.9s: n5 reused n6.d4 · doc pellham-offering |
| cross-guided-s105 | 20.0s: n5 joined n6.d5 · doc pellham-offering |
| cross-identity-data-s101 | 17.6s: n2.d3 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-identity-data-s102 | 12.5s: n2.d4 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-identity-data-s103 | 18.9s: n2.d5 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-identity-data-s104 | 12.4s: n2.d5 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-identity-data-s105 | 13.4s: n2.d4 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power pla |
| cross-identity-s101 | 22.0s: n12 joined n6.d5 · doc pellham-offering |
| cross-identity-s102 | 20.4s: n6 joined n5.d3 · doc pellham-offering |
| cross-identity-s103 | 24.3s: n8 joined n7.d6 · doc pellham-offering |
| cross-identity-s104 | 18.6s: n5 reused n6.d3 · doc pellham-offering |
| cross-identity-s105 | 21.7s: n5 joined n6.d4 · doc pellham-offering |
| cross-long-guided-data-s101 | 16.6s: n2.d2 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-guided-data-s102 | 25.6s: n2.d3 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-guided-data-s103 | 12.6s: n2.d2 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-guided-data-s104 | 20.3s: n6.d2 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-guided-data-s105 | 19.3s: n2.d4 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-guided-s101 | 24.4s: n8 joined n7.d7 · doc pellham-offering |
| cross-long-guided-s102 | 23.9s: n6 reused n5.d6 · doc pellham-offering |
| cross-long-guided-s103 | 21.5s: n5 joined n6.d5 · doc pellham-offering |
| cross-long-guided-s104 | 20.8s: n5 joined n6.d2 · doc pellham-offering |
| cross-long-guided-s105 | 21.3s: n5 joined n6.d5 · doc pellham-offering |
| cross-long-identity-data-s101 | 19.1s: n2.d4 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-identity-data-s102 | 21.9s: n5.d2 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-identity-data-s103 | 18.8s: n2.d4 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-identity-data-s104 | 20.5s: n6 joined n5.d5 · doc pellham-offering |
| cross-long-identity-data-s105 | 18.3s: n2.d2 · doc utility-capex-2027 · Caldrian utilities: 2027 capital plans: Pellham Power and |
| cross-long-identity-s101 | 21.8s: n6 joined n5.d5 · doc pellham-offering |
| cross-long-identity-s102 | 30.6s: n7 joined n8.d3 · doc pellham-offering |
| cross-long-identity-s103 | 22.1s: n7 joined n8.d3 · doc pellham-offering |
| cross-long-identity-s104 | 23.8s: n6 joined n5.d5 · doc pellham-offering |
| cross-long-identity-s105 | 18.7s: n6 joined n5.d7 · doc pellham-offering |

## Shape of the work

- Cells per leaf node: median 2, max 8 (398 leaves).
- short workflows: median 2 cells per leaf (272 leaves).
- long workflows: median 3 cells per leaf (126 leaves).
- First-level branches finish within 13.3s of each other (median).
- Reads of the run index: 0. Reads of another branch's artifacts: 1.
- Cells that wait on the stream, by node kind: 203 in nodes that opened children, 0 in leaves.
