# Delta trace: cross-long-guided-data-s101

6 nodes, 16 cells, 20 stored calls. No model calls were made.

- Replay fidelity: 16 of 16 cells reproduce their recorded output exactly against the unchanged world; 0 wait on the stream and are not replayed.
- Citation coverage: 11 of 59 result lines name a node or data ref.

| Delta | Stored calls moved | Cells touched | Cells whose shown output changed | Nodes woken | Downstream, wait for the child | Untouched | Thesis parts at risk |
|---|---|---|---|---|---|---|---|
| A release that repeats what is already stored | 0 | 0 | 0 | – | – | 6 of 6 | – |
| A new document on a topic no node searched for | 0 | 0 | 0 | – | – | 6 of 6 | – |
| The implied-vol history series has its unit label corrected | 1 | 1 | 0 | – | – | 6 of 6 | – |
| Utility bond spreads for 2026Q3 revised from 165bp to 190bp | 1 | 1 | 1 | n5 | n1, n3 | 3 of 6 | Financing (n3) |
| A new document: Pellham prices a bond (matches an earlier debt search) | 2 | 2 | 2 | n5, n6 | n1, n3 | 2 of 6 | Financing (n3) |

## The implied-vol history series has its unit label corrected

- Moved: `n4.d4` (series vltx_iv_history)
- Cell n4#2: read n4.d4; shown output identical
- Exposed but output identical, not woken: n4
- Claims that name a moved source: none
- Thesis parts: Demand (n2) (holds), Financing (n3) (holds), Pricing (n4) (holds)

## Utility bond spreads for 2026Q3 revised from 165bp to 190bp

- Moved: `n5.d3` (series utility_spreads)
- Cell n5#3: read n5.d3; shown output changed
- Exposed but output identical, not woken: none
- Claims that name a moved source: none
- Thesis parts: Demand (n2) (holds), Financing (n3) (at risk), Pricing (n4) (holds)

## A new document: Pellham prices a bond (matches an earlier debt search)

- Moved: `n5.d1` (search Caldrian utilities capex 2027 debt financing), `n6.d4` (search utility tender calendar 2027 capex amounts Pellha…)
- Cell n5#1: read n5.d1; shown output changed
- Cell n6#3: read n6.d4; shown output changed
- Exposed but output identical, not woken: none
- Claims that name a moved source: none
- Thesis parts: Demand (n2) (holds), Financing (n3) (at risk), Pricing (n4) (holds)
