# Investment research harness: specification v3

Async nodes that split the *what*, see each other through one stream each, and leave a versioned, cited trail.

Status: design, 2026-11-04. Replaces [v2](../harness-spec-v2/README.md). Nothing here is built yet.

Every behavior below is animated, step by step, on [the patterns page](../skill-graph-patterns.html), including a skill-free walkthrough of one plain question, [Should we add to our XLI LEAPS this month?](../skill-graph-patterns.html#walk). On that page you can select any node at any step to see exactly what it sees.

---

## 0. On one screen

- **A node is one task:** an atomic reasoning trace.
  - It runs a skill from the graph, or none.
  - It does the *how* itself: tool calls and PTC code.
  - It opens child nodes only for the *what*: parts that are separate judgments, orthogonal to their siblings.
- **Six host calls:** `readNode`, `readArtifact`, `openNode`, `nextNodeEvent`, `closeNode` and `publishCheckpoint`.
  - A node's result is its final message.
  - Nothing else is hard-coded: no summaries, no declared provenance, no reuse flags.
- **The request is the identity.** Identical requests share work:
  - a request matching running work joins it
  - a request matching finished work reuses its latest result
  - similar wording is not identical, so the model decides what "the same" means and copies the exact request
- **One stream per node.**
  - Every start, join, checkpoint, result, close and reopen in the run becomes one line in every node's stream.
  - Nothing else enters a node's context. It reads content only when it chooses to.
- **Refs are short and versioned:** `n7`, `n7.c3`, `n7.r2`, `n7.trail`, `you.m1`.
  - Refs written inside content are its links, and they make up the trail.
- **Messages are addressed checkpoints.**
  - A message to a finished node reopens it, and its next result is a new version.
  - Any node can message you, and you can message any node.
- **The run stays open.** News reaches the root, which reopens only what cites the changed results.
- **The harness supplies mechanics and the model supplies judgment.** Nothing sits in between.

---

## 1. What carried over from v1 and v2

The test is the same as before: if models were ten times better, would we delete this feature? Anything we would delete is behavior, and behavior belongs to the model.

**Adopted:**

| Lesson | From | In v3 |
|---|---|---|
| Blocking is the caller's choice, not a kind of call | v1 | `runNode` folds into `openNode`. `nodes.run` is wrapper code |
| One multiplexed wait with an explicit cursor | v1 | One stream per node. `nextNodeEvent` returns everything pending |
| A message is just a write to an inbox | v1 | `to` on `publishCheckpoint` |
| Observe, don't ask | v1 | Reads and trails are recorded by the harness. Links come from refs written in content, not a declared list |
| Patterns are library code | v1 | Join, fork, settle, steer and race are a few lines each, not calls |
| Authority, liveness and information are separate structures | v1 | Opener, holds and cites |
| Early cutoff | v1 | A reopened node whose conclusion holds says so, and the root stops there |
| The program sees its own budget | v1 | Every batch ends with the budget left |
| Opening a node is the claim | v2 | A start line is in every stream before `openNode` returns. No claims board |
| Notes never rewrite shared work | v2 | The request is the identity. Notes steer within a task |
| Caps, not rules | v2 | No thresholds, routing rules or depth settings |
| Visibility inside, walls outside | v2 | Any ref in a run is readable by any node in it. Runs are walled off from each other |

**Dropped:**
- **v2's calls:** `ask`, `join`, `tell`, `find`, `update` and `decide`. Each duplicated something `main` already had.
- **v2's `rests_on` and `sameQuestion`.**
- **v2's automatic propagation notes.**
- **The "fixed question" framing.** A node is a task, and its identity is its request.

---

## 2. The node

A node has:
- **A request**, which is its identity.
- **An opener:** the node or person that opened it.
- **Holders:** everyone keeping it alive.
- **Its own session**, recorded as `nK.trail`. The trail holds everything the node saw and wrote: turns, code cells, tool calls and tool results.
- **A stream of lines.**
- **Checkpoints** `nK.c1, c2, …` and **results** `nK.r1, r2, …`.

The trail is append-only. Any node in the run can read it in slices, and `from` forks from it.

---

## 3. The six calls

| Call | What it does | Why the host owns it |
|---|---|---|
| `readNode({node})` | Loads a skill's procedure, links and resources from the pinned registry. Recorded as consulted; nothing runs | The registry is pinned outside any node |
| `readArtifact({ref, offset, limit})` | Reads a bounded slice of any ref in the run (see the table below) | Integrity, bounds and the record of reads |
| `openNode({request})` | Starts a node, joins identical running work, or reuses its latest result. Returns at once with `{node, disp}`. Failed or cancelled work is never joined | Identity and sharing span every interpreter in the run |
| `nextNodeEvent({after})` | Returns this node's stream: everything pending since the cursor, or waits if nothing is. The same lines are pushed at each turn boundary while the node is busy | Order, delivery and cursors |
| `closeNode({handle})` | Releases this hold. Unfinished work is cancelled only when its last holder leaves | Only the host knows who else holds the work |
| `publishCheckpoint({content, to})` | Publishes free-form content as the next checkpoint. Its first line becomes its line, and refs written in it become its links. `to` addresses a node or `you`, and reopens a finished node | Immutability, numbering and delivery |

What `readArtifact` can read:

| Ref | Contents |
|---|---|
| `n7.c3` | A checkpoint |
| `n7.r2` | A result |
| `n7` | A node record: exact request, opener, state, holders and refs |
| `n7.trail` | A node's trail |
| `you.m1` | A message from you |
| `run` | The index: one line per node |

**The result is not a call.** When a node ends, its final message is stored as its next result.

**A node cannot end while it holds unfinished work.** This rule is kept from `main`. The harness tells the node which children are still open, and the node awaits or closes each one, so the trail records every child's fate.

Node code writes against a small wrapper:

```js
const r  = await nodes.run(request)   // open, then wait: {node, ref, line}
const op = await nodes.open(request)  // {node, disp}: started, joined or reused
await op.next()                       // the next line about that node
await op.result()                     // wait for its result
await op.close()                      // release this hold
await nodes.with(request, async op => {})   // scoped, always released
await nodes.next()                    // the next batch of this node's own stream
```

**The request:**

| Field | Required | Meaning |
|---|---|---|
| `task` | yes | The one task. Refs written in it are links |
| `node` | no | A skill to run. Omit it for a plain node. A fork inherits its source's skill |
| `inputs` | no | Structured inputs, for skills that expect them |
| `refs` | no | An ordered list of refs, for skills that expect one |
| `from` | no | Fork: start from that node's trail as it stands (a snapshot if it is still running), to reuse its prompt cache |
| `key` | no | Forces a deliberate separate copy of otherwise identical work |

**Identity and sharing.** Identity is the pinned registry plus `task`, `node`, `inputs`, `refs`, `from` and `key`. Who asks is not part of it.

| Identical work is | `openNode` | Line |
|---|---|---|
| absent | starts a node | `n3 opened n7 · …` |
| running | joins it: one execution, one more holder | `n4 joined n7` |
| finished | reuses its latest result | `n4 reused n7.r1` |
| failed or cancelled | starts a fresh node | `n1 opened n8 · …` |

On `main`, sharing was opt-in (`reuse: 'session'`). In v3 it is the default, because running byte-identical work twice is pure waste. When independence is the point, a node words the task differently or adds a `key`.

---

## 4. Refs and the trail

- **Grammar:**
  - `nK` is a node.
  - `nK.cJ` is a checkpoint, `nK.rV` a result and `nK.trail` a trail.
  - `you.mJ` is a message from you.
  - `run` is the index.
- **Assignment:** ids follow opening order, and each ref maps to a row in the run's SQLite db.
- **Links are refs written in content.**
  - The harness extracts them, rejects any that don't exist yet, and records them as cites.
  - A citation sits next to the claim it supports, so a delta can be traced claim by claim.
  - The harness also records every read, so a dependency that was read but never cited is still visible.
- **Versions never change.**
  - A citation of `n7.r1` stays valid after `n7.r2` exists.
  - A stale citation is visible by name.

---

## 5. The stream

| Event | Line in every stream |
|---|---|
| start | `n2 opened n5 · snapshot · Produce snapshot evidence` |
| fork | `n4 opened n9 from n7 · Under two 2027 hikes, …` |
| join or reuse | `n3 joined n5` · `n4 reused n5.r1` |
| checkpoint | `n5.c1 · Utilization measured: 91%.` |
| addressed | `n5.c2 → n8 · We conflict on funding: …` |
| message from you | `you.m1 → n4 · $250k of premium at most.` |
| result | `n5.r1 · Hyperscaler 2027 capex is credible … · cites n5.c3` |
| reopen | `n7 reopened · held by n1` |
| close or cancel | `n1 closed n2` · `n2 cancelled · no holders left` |
| failure | `n5 failed · vendor timeout` |

- **Delivery:**
  - Lines are ordered and never dropped.
  - They are pushed at each turn boundary while a node is busy, and returned in batches by `nextNodeEvent` when it is idle.
  - Lines addressed to the node, or about work it holds, are marked.
- **Nothing is injected.** A line carries a first line (about 90 characters) and a ref. Content, records and trails are read only when a node chooses to.
- **Late start:** a node that opens mid-run, or weeks into a standing run, starts from the index (one line per node), then gets lines as they come.
- **Budget:** every batch ends with the budget left, for example `left: 26 of 32 nodes · 41 min`.

[The walkthrough](../skill-graph-patterns.html#walk) shows each node's stream at every step. Select a node there to see it.

---

## 6. How a capable node coordinates

Each item is a few lines of code over the six calls. The model decides when to use which.

| Behavior | What the node does | Animated |
|---|---|---|
| Split the what | Opens one node per separate judgment and goes idle; data pulls stay inside each node | [Fan out](../skill-graph-patterns.html#fanout), [Descent](../skill-graph-patterns.html#descent) |
| Act on progress | Acts on a child's checkpoint line while the child keeps working | [Act on progress](../skill-graph-patterns.html#stream) |
| Join what you see | Sees a start line, reads the node record, and sends the exact request | [Join](../skill-graph-patterns.html#join) |
| Fork from a trail | For a different aspect, opens `{from, task}` instead of bending shared work. The fork reuses the source's prompt cache | [Fork](../skill-graph-patterns.html#fork) |
| Cite across branches | Reads another branch's checkpoint and cites it. No join, because the task stays theirs | [Walkthrough step 5](../skill-graph-patterns.html#walk) |
| Settle by talking | On a contradiction, the nodes read each other's trails and exchange addressed checkpoints. One publishes the settled view citing the exchange; the other's result cites that view. If they can't settle, both publish, citing each other, and whoever consumes both weighs them | [Settle](../skill-graph-patterns.html#settle) |
| Steer while idle | The parent sends a note within the child's task, or closes a branch that stopped mattering | [Steer](../skill-graph-patterns.html#steer) |
| Talk with you | A node asks you and keeps working; your reply is a line addressed to it. You can message any node mid-run | [Ask the user](../skill-graph-patterns.html#ask) |
| Reopen on news | The root traces cites and reopens only what the news touches | [Reopen](../skill-graph-patterns.html#reopen) |

Settlement and the shared trunk are the two forms of the diamond. In a shared trunk, two nodes hold one execution. In a settlement, two trails rest on one shared result.

---

## 7. Lifecycle

- **Holds:**
  - Opening or joining adds a hold, and so does addressing a finished node.
  - Work runs while anyone holds it. The last release cancels it, and the cancellation cascades to work that only it held.
- **Ending:**
  - A node ends with its final message, but not while it holds unfinished work.
  - A result releases the holds on that node.
- **Failure:**
  - Holders get the failure line.
  - Failed work is never joined, so sending the same request again starts fresh.
- **Reopen:**
  - An addressed checkpoint to a finished node reopens its session, with its whole trail.
  - The sender holds it until its next result, `nK.r(V+1)`.
  - Identical requests then reuse the latest version.
- **Standing runs:**
  - A run stays open after the root answers. Sessions, trails and refs persist in the run's SQLite db.
  - The registry stays pinned for the run's life, so a reopened node runs the procedure it ran before.

---

## 8. Deltas

The root decides; nothing propagates by rule.

1. News arrives as a message to the root, which reopens it.
2. The root reads the cites already in its stream. Result lines name what each result rests on.
3. It reopens the source the news touches, then the results that cite the old version.
4. Each reopened node revises in its own session. A conclusion that holds says so in its next version, and the root stops there.
5. The record shows which versions moved, in what order, and why.

In the walkthrough, a hot CPI print moves four of ten nodes, each along a cite the news actually touched. `n8` is never reopened, because `n3` holds.

---

## 9. Mapping to `main`

| `main` | v3 |
|---|---|
| `readNode` | Unchanged |
| `readArtifact` | No per-ref grants inside a run. Also reads node records, trails and the index |
| `runNode` | Removed. `nodes.run` is open, then await the result |
| `openNode` | `node` optional, `key` optional, `reuse` removed (sharing is the default), `from` added; returns `disp` |
| `nextNodeEvent` | One stream per node, batched, also pushed at turn boundaries, with a budget line. `handle` becomes an optional filter |
| `closeNode` | Unchanged |
| `publishCheckpoint` | `{content, to}`. `summary` and `based_on` removed |
| `submitCandidate` | Removed: the final message is the result |
| Kept | Leases and the cascade, the wait-cycle refusal, the depth cap, the finishing rule, the pinned registry, the event log |
| Added in the harness | Trails as artifacts, short versioned refs, node records, the run index, reopen with versions, standing runs |

---

## 10. Compared with Claude Code subagents

From the Claude Code subagent documentation (read 2026-11-04):
- Subagents run in the background and nest up to three levels.
- Only a nested subagent's top-level summary returns.
- `SendMessage` resumes a finished subagent with its history.
- A resumed agent reports to whoever resumed it.

| | Claude Code subagents | v3 |
|---|---|---|
| Unit of work | A task in a prompt | A task whose request is its identity |
| Awareness of other work | Agent names; task lists in agent teams | One stream of lines per node, from every depth |
| Sharing one piece of work | Results go to the spawner or resumer | Identical requests join or reuse: one execution, many holders |
| Resuming finished work | `SendMessage` resumes with history | `to` reopens with history and versions the result |
| What reaches the context | Summaries from one level down | Lines from the whole run; content only on read |
| The trail | Transcripts | Versioned refs with inline cites, plus trails every node can read |

---

## 11. Risks to watch

- **Line volume.** Every node gets every line, which is O(nodes × events). Lines are short, and late starters get the index instead of the history. If runs grow large, the first lever is shorter lines, not filtering by rule.
- **Push while busy.** Lines at every turn boundary could distract a node in the middle of its work. A capable node skims them; watch whether that holds.
- **Default sharing.** Two nodes writing byte-identical tasks will share work. `key` or different wording is the escape when independence is the point.
- **Cold reopens.** Reopening a session days later misses the prompt cache. It is still cheaper than redoing the reasoning, but the trade should be watched.
- **Settlement that doesn't converge.** There are no fixed rounds, so caps bound it. Both nodes publishing with the disagreement explicit is a legitimate outcome.

---

Sources:
- [Claude Code: create custom subagents](https://code.claude.com/docs/en/sub-agents)
