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

### Cost

| Item | Cost |
|---|---|
| Stage 1 (48 runs: $5.92 runs, $1.45 grading) | $7.37 |
| Experiment so far (of the $60 cap) | about $17 |

The experiment total includes the pilots ($2.69), the voided first pass ($6.99) and Stage 1.
