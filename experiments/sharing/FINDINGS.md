# Findings

## Stage 1: delivery

There were 48 runs: four designs × four workflows × three seeds. All nodes ran at v3 defaults, meaning lifecycle and checkpoint lines, data shared only by publishing it, and a node wakes only when its own code waits. The numbers are in [runs/stage1/report.md](runs/stage1/report.md) and [runs/stage1/timing.md](runs/stage1/timing.md).

### Result

**The delivery design made no measurable difference to whether anything crossed between branches.**

| Workflow | Check | Result |
|---|---|---|
| `shared` | The slow series is fetched by at most one node | Failed in every design |
| `shared` | Any join or reuse happens | Failed in every design |
| `conflict` | The shipments branch explains the drop | Failed in every design |
| `cross` | The demand branch learns the Pellham cut | Failed in every design |
| `noise` | No cross-branch traffic | Passed in every design |
| `conflict` | The two branches cited each other | 1/3 runs in `broadcast` and in `index`, and in no other design |

Answer quality ran from 0.68 to 0.81 of rubric items, which is within noise at three seeds.

Rescored with judgment items set apart, the evidence grade is 0.90 for `scoped`, 0.78 for `index`, and 0.76 for both `broadcast` and `tree`.
- The gap comes from two places:
  - **The contradiction's fire item**, explaining the shipment drop by the fire. It passed in 2 of 3 runs for `scoped` and `index`, 1 for `tree`, and 0 for `broadcast`.
  - **The shared need's two rates items.**
- At three seeds per cell, none of these differences is reliable.
- The judgment items stay near zero in every design.

### Why: nothing worth delivering exists until the end, and the end comes all at once

1. **Leaves finish in two cells.** A leaf runs one search cell, then one cell that reads everything and computes in parallel: the median is 2 cells across 193 leaves, and the most any leaf used was 4. A leaf therefore has about one turn boundary mid-run at which a line can reach it.
2. **Branches finish together.** First-level branches finish within 12.8 s of each other (median).
3. **Nothing is published mid-run.** None of the following happened in any of the 48 runs:
   - a checkpoint, join, reuse or addressed message
   - a read of the run index
   - a read of another branch's artifacts

   Only nodes that hold children ever wait on the stream (104 cells). Leaves never do.
4. **A line carries a verdict, not the finding.** A result's line is its first line, which is the node's answer to its own question rather than the fact another branch needs. In `cross`, a line named Pellham in 2 of 12 runs, and one of those was the root's final answer.
5. **Duplicate fetches overlap in flight.** In all 12 `shared` runs, the second fetch of the slow series started 0.1–9.7 s after the first, while the first was still running. Reusing a finished data ref could not have prevented any of these duplicates; only joining the call in flight could have.
6. **Evidence windows are seconds long.** In `conflict`, the disclosures branch read the fire release in all 12 runs, at 23–38 s. The shipments branch was still running at that point in only 5 of the 12, and it finished 1.6–24 s later. In `cross`, the demand branch was still running when the offering release was read in 10 of 12 runs, but the finding never reached it.

### The root does the cross-branch work, and the result depends on what the branches hand it

- **`cross`: the root connects the findings.** Every final answer met every rubric item, 48 of 48, because the root read both branch results and made the connection itself.
- **`conflict`: the root often misses the link.** The fire appears in the disclosures branch's result in 12 of 12 runs, yet the final answer explains the shipment drop by it in only 5 of 12.
  - When the disclosures branch itself tied the fire to shipments, the root kept the link.
  - When that branch only listed the fire under operations, the root mostly failed to connect it to the shipment drop the other branch reported.
- **What helps is reaching the right node.** Delivering evidence to the root is not the problem. What would help here is getting it to the node whose question it answers.

### Cost comes from decomposition, not delivery

Median cost per run was about $0.085 for `broadcast` and `index`, against about $0.15 for `tree` and `scoped`.

The reason is decomposition: branches opened children in 3–4 of 12 runs under `broadcast` and `index`, and in 9–10 of 12 under `tree` and `scoped`.

The likely cause is the starting index that `broadcast` and `index` give each child, which lists its siblings. If so, the cost difference is a confound, not an effect of delivery.

### Grader

Two rubric items judge a call that the world does not force, and they almost never pass in any design:

| Workflow | Item | Passed |
|---|---|---|
| `conflict` | Concludes that Voltaris will likely meet guidance | 0/12 |
| `shared` | Concludes that adding now is reasonable | 2/12 |

From Stage 2 on, each workflow's final-call item counts as a judgment item and is reported apart from the evidence grade. Stage 1 is rescored the same way.

### Decisions for Stage 2

| Topic | Decision |
|---|---|
| Delivery | `broadcast` is held fixed, as the rule picks |
| Data reuse | Refs plus call identity: an identical call joins the one in flight or reuses its stored output. The output is marked with its source, and a line records the sharing |
| Guided arm | One arm adds a paragraph on when to share. Every other prompt states mechanics only |
| Long variants | `conflict` and `cross` get long variants |
| Seeds | 5 seeds |
| Stage 4 | Dropped |

## Stage 2: data reuse

Stage 2 held delivery at `broadcast` and compared three conditions, 30 runs each:
- `base`: Stage 1's broadcast
- `identity`: identical world calls join or reuse
- `guided`: `identity` plus the sharing paragraph

The runs covered six workflows (the four short ones and two long variants) at 5 seeds. `base`'s 12 short-workflow runs for seeds 101–103 are Stage 1's broadcast runs, imported rather than rerun.

The numbers are in [runs/stage2/report.md](runs/stage2/report.md) and [runs/stage2/timing.md](runs/stage2/timing.md).

### Result

**Call identity removes duplicate work at no cost to answers.**

| Measure | `base` | `identity` | `guided` |
|---|---|---|---|
| Duplicate fetches per run | 3.4 | 0 | 0 |
| Nodes fetching the slow series | 2.2 | 1.0 | 1.0 |
| World calls per run | 22.8 | 18.2 | 19.7 |
| Median cost per run | $0.101 | $0.084 | $0.085 |
| Calls shared across branches per run | 0 | 1.8 | 1.9 |

- Shared calls never needed a model decision: they happen inside the call.
- The evidence grade is lower for `identity`: 0.63, against 0.76 for `base`. Paired by workflow and seed, the difference is −0.13, with a 95% CI of −0.27 to 0.00.
- That gap does not track sharing. The 5 `identity` runs with no shared call at all fell further (−0.20) than the 25 runs with shared calls (−0.12).
- The misses are in how the root wrote its answer, for example:
  - stating orders and shipments separately without contrasting them
  - compressing the children's outlooks, in a noise run with no shared calls

**The sharing paragraph changes how results cite each other, not what gets published.**
- Across 30 `guided` runs there were no checkpoints, no addressed checkpoints and no reopens. No guided cell even mentions publishing.
- Cross-branch cites in results rose to 0.60 per run, from 0.40 under `identity` and 0.27 under `base`.
- So the contradiction's branches cited each other more often:

  | Workflow | `base` | `identity` | `guided` |
  |---|---|---|---|
  | Short contradiction | 1/5 | 2/5 | 3/5 |
  | Long contradiction | 0/5 | 1/5 | 4/5 |

- These cites are what put `guided` first by the stage rule: 25 of 55 checks, against 19 for `identity` and 8 for `base`.

**No condition got a finding to the node whose question it answers.**
- The shipments branch never explained the drop by the fire, in any contradiction run: 10 per condition, short and long.
- The demand branch never stated the Pellham cut, in any cross-branch run: again 10 per condition.

**In the long variants, the window is open, delivery happens, and nothing follows.**
- **Long cross-branch.**
  - The demand branch was still running when the financing branch read the Pellham release in 15 of 15 runs, with a median of 28 s left.
  - A line naming Pellham reached a running demand node in 13 of 15 runs. It was either a financing result or a call-identity line such as `n6 joined n5.d5 · doc pellham-offering`.
  - The demand nodes had cells left after those lines arrived, yet no demand node read the ref (cross-branch reads: 1 in 90 runs).
  - Their results mention Pellham's plans, never its cut.
- **Long contradiction.**
  - The shipments branch was still running in 11 of 15 runs, with a median window of 8 s.
  - No line naming the fire went out before it finished, because the disclosures branch published nothing until its result.
- **What this means.** Once the windows open, delivery is not the bottleneck. Lines arrive, but a line that only points at a ref is not followed. Evidence crosses only when the line itself states the fact.

### Decisions for Stage 3

| Decision | Detail |
|---|---|
| Stage 2 winner | `guided` wins by the rule |
| What Stage 3 varies | Data lines: whether each fetched document or series becomes a line whose text carries its content |
| Design | A 2×2 of data lines × guidance. The `identity` and `guided` runs are imported from Stage 2, so only the two data-line conditions are new |
| Budget | About $30.7 of the $60 cap is left |


### Cost

| Item | Cost |
|---|---|
| Stage 1 (48 runs: $5.92 runs, $1.45 grading) | $7.37 |
| Experiment so far (of the $60 cap) | about $17 |

The experiment total includes the pilots ($2.69), the voided first pass ($6.99) and Stage 1.
