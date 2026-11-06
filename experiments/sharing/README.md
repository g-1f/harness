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

Stages run one at a time. Each stage varies one mechanism and keeps the rest at the previous stage's winner, where the winner is the condition that passes the most checks, with ties going to the lowest cost. Each stage uses 3 seeds, and the whole experiment is capped at $60.

| Stage | Varies |
|---|---|
| 1 | Delivery: `tree`, `broadcast`, `scoped`, `index` |
| 2 | Data reuse |
| 3 | What a line carries |
| 4 | What wakes a waiting node |

Stage definitions are in `lib/stages.mjs`, and findings are in [FINDINGS.md](FINDINGS.md).

## Running

```sh
node stage.mjs stage1 --cap 25 --parallel 4   # resumable; skips recorded runs, regrades failed grades
node report.mjs stage1                        # runs/stage1/report.md
node timing.mjs stage1                        # runs/stage1/timing.md
node run_one.mjs conflict broadcast 101 runs/try   # one run
```

Each run directory holds the following:
- `summary.json`
- `state.json`, which has every node, line, artifact, edge, read, world call and cell
- `events.jsonl`
- `nodes/<id>.prompts.txt`
- `nodes/<id>.exits.jsonl`, which has each session's final JSON

The pilot runs and the first Stage 1 pass are kept locally but not committed. That first pass lost 13% of its cells to a bug in the cell wrapper, which is now fixed.
