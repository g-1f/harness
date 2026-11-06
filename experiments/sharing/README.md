# Sharing experiment

This experiment asks how nodes in a v3 run should share work in practice: what each node broadcasts, how others hear it, and what they can reference. Every node is a live `claude -p` session on Sonnet 5.5. Each node acts only through PTC code cells, and all nodes run at once.

## Setup

**World.** The world is a fictional sandbox called Caldria (`lib/world.mjs`). It has documents and series, and its search matches key terms only. Each call takes 1–6 s, and the slow series takes 7–11 s. Latency is seeded per run.

**Workflows.** There are four small workflows, each with a fixed first split and planted facts:

| Workflow | The situation it plants |
|---|---|
| `shared` | Both branches need the same slow series (`cma_futures`) |
| `conflict` | Orders rise while shipments fall. A plant fire explains it, but only the disclosures branch can find that release |
| `cross` | The financing branch finds a fact (Pellham withdraws an equity offer and cuts orders 40%) that changes the demand branch's answer |
| `noise` | Five unrelated holdings, where nothing should cross between branches |

**Nodes.** Each node gets one MCP tool, `run_cell` (`ptc_server.mjs`). The tool runs JavaScript in a persistent sandbox, and the sandbox calls the run's harness (`lib/run.mjs`) over HTTP.

**Host calls and lines.**
- The harness implements v3's host calls: `openNode`, `nextNodeEvent`, `closeNode`, `publishCheckpoint` and `readArtifact`.
- It applies identity, holds and the finish rule.
- It writes one line per start, join, reuse, checkpoint, result, close, cancel, fail and reopen.
- Lines a node is due are appended to its next cell's output, which is the push at the turn boundary. A node can also wait for them.

**Prompts.** Prompts state mechanics only (`lib/prompts.mjs`). The one exception is a paragraph on decomposition, without which nodes never open children.

**Scoring.** Scoring has two parts:
- Automatic checks that the logs can prove (`lib/score.mjs`).
- A blind grade by Opus 5.5 against the planted facts (`lib/grade.mjs`). The grader never sees the condition.

**Caps and limits.**
- Each run has caps: 16 nodes, 40 turns and 30 cells per node, and 16 min of wall time.
- A run touched by the plan's usage limit is void. It is logged to `discarded.jsonl`, deleted, and run again after the reset (`lib/limit.mjs`).

## Stages

Stages run one at a time. Each stage varies one mechanism and keeps the rest at the previous stage's winner, where the winner is the condition that passes the most checks, with ties going to the lowest cost. The whole experiment is capped at $60.

| Stage | Varies | Conditions | Seeds |
|---|---|---|---|
| 1 | Delivery | `tree`, `broadcast`, `scoped`, `index` | 3 |
| 2 | Data reuse, under `broadcast` | `base` (Stage 1's `broadcast`), `identity`, `guided` | 5 |
| 3 | What a line carries | Chosen by the rule after Stage 2 | 5 |

Stage 4, which would have varied what wakes a waiting node, was dropped. Only nodes that hold children ever wait on the stream, so the change would have reached parents only.

**Stage 2 conditions.**
- **`base`:** Stage 1's `broadcast`. Data moves only in checkpoints and results.
- **`identity`:** every world call's output is stored as a ref `nK.dJ`.
  - An identical call joins the call still running, or reuses its stored output. "Identical" means the same function and arguments, from any node.
  - The output comes back marked with `ref`, `from` and `joined` or `reused`, and a line records it: `n3 joined n2.d4 · series cma_futures`.
  - `load(ref)` returns a data ref's output.
- **`guided`:** `identity`, plus one paragraph on when to share:
  - publish findings early, with the finding in the first line
  - read refs instead of redoing work
  - before finishing, address a conflicting or explained result, which reopens a finished node

  This is the only condition whose prompt says when to use the mechanisms. The other prompts state the mechanics only.

**Workflows.** Stage 2 adds long variants of `conflict` and `cross` to the four Stage 1 workflows.
- Each document names the next one, and search finds that next document only by its name, so each hop costs a turn.
- Calls take 3–8 s, and series take 6–12 s.
- The planted facts are the same as in the short variants.

**Grading.** Grades are reported in two parts:
- **Evidence:** the facts and connections.
- **Judgment:** the final call, which the world does not always force.

Stage definitions are in `lib/stages.mjs`, and findings are in [FINDINGS.md](FINDINGS.md).

## Running

```sh
node stage.mjs stage1 --cap 25 --parallel 4   # resumable; skips recorded runs, regrades failed grades
node report.mjs stage1                        # runs/stage1/report.md
node timing.mjs stage1                        # runs/stage1/timing.md
node run_one.mjs conflict-long guided 201         # one run, any condition id from lib/stages.mjs
```

Each run directory holds the following:
- `summary.json`
- `state.json`, which has every node, line, artifact, edge, read, world call and cell
- `events.jsonl`
- `nodes/<id>.prompts.txt`
- `nodes/<id>.exits.jsonl`, which has each session's final JSON

The pilot runs and the first Stage 1 pass are kept locally but not committed. That first pass lost 13% of its cells to a bug in the cell wrapper, which is now fixed.
