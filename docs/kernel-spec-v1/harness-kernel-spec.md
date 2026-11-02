# Investment research harness: kernel specification v1

Status: draft for build, 2026-11-02.

How to read the status markers:
- **Verified** means the behavior ran in the reference kernel (`kernel.py`, 566 lines) and passed `spec_test.py`. All 24 of its checks pass, stable across repeated runs.
- **Verified earlier** means an earlier prototype or test in this design thread showed it, but the reference kernel does not implement it yet.
- **Designed** means specified here but not built.

The reference kernel is single-process and in-memory. Its agent programs are scripted coroutines that stand in for model-written code. It proves semantics, not model quality or production scale.

---

## 0. The design on one screen

- **Five verbs:** `spawn`, `query`, `commit`, `wait`, `close`. Everything else is library code over them.
  - `spawn` never blocks.
  - `wait` is the only verb that blocks, and one `wait` covers any mix of sources.
- **One data model.** Everything an agent can see or change is a versioned database:
  - theses, sources, the skill library, inboxes
  - each computation's output
  - the kernel's own tables (read-only)
- **Three structures, kept separate:**
  - Authority is a tree: who owns, steers, budgets and stops what.
  - Liveness is a DAG: work stays alive while anyone holds it.
  - Information is a graph: who read what, at which version. Cycles across versions are allowed.
- **Relevance belongs to the model.** The model decides what to read, what to wait on and whether to revise. The kernel records reads automatically and wakes an agent only when a result it read actually changed. The graph is never authored; it is the record of reads.
- **Deltas are cheap.** When a source changes (a CPI release, a rate decision, a filing), the kernel re-runs only computations whose recorded reads changed. It stops wherever an output comes out unchanged (early cutoff), and explains every output change by the reads that moved.
- **Scenarios and backtests reuse the same machinery.** Forks give scenarios. A second clock gives honest backtests.
- **Skills are optional.** A skill is a row in a library database, read like any other data. Editing one invalidates only the computations that read it. With no library at all, the same work runs as free calls.
- **RLM is a pattern, not a primitive.** PTC is one way to drive the verbs, alongside native tool calls.

---

## 1. Requirements and how they are met

| # | Requirement | How the spec meets it | Status |
|---|---|---|---|
| 1 | Works with the skill graph, and without one | Skills are rows in `lib/skills`. `spawn({skill})` reads the skill as a recorded read. Links in skill prose are hints. Free calls are first-class | Verified |
| 2 | Async background execution first; parallel and recursive as needed; each parent decides how to decompose | `spawn` returns a handle immediately. `wait` multiplexes over children, data changes, inbox and timeouts. Recursion uses the parent's own criterion. Budgets are visible and flow down | Verified |
| 3 | A person can always talk to the root and steer any subagent | Every computation has an inbox. People can write to any inbox they own. Owners can steer anything below them. Messages arrive at the next turn boundary and are recorded with their cause | Verified (preemption is Designed) |
| 4 | Graph-shaped operations between subagents, not just fan-out and fan-in | Recorded reads form the information graph. The catalog below covers sharing, streaming, convergence and feedback, all expressed in the five verbs | Verified |
| 5 | Trajectories easy to track and store; recompute only the pieces a change affects; the model decides what is relevant | Every verb call lands in `sys/trajectory`. Refresh re-checks recorded reads with early cutoff, `explain` attributes output changes to inputs, and forks run scenarios | Verified |

Section 6 catalogs the graph operations for requirement 4.

---

## 2. Principles: the bitter lesson, distilled from this design thread

**P1. Hand-design the physics, never the behavior.** As models improve, behavior we design by hand gets deleted, while physics matters more, because more autonomy needs more audit. The test for any feature is: if models were ten times better, would we delete it?

| Physics: the kernel owns it | Behavior: the model owns it |
|---|---|
| Versions, two clocks, immutability | What to read, what to remember, schema of its own databases |
| Recording every read, write, spawn, message and wake | How to decompose a task, and how far to recurse |
| Waking only on changed results; early cutoff | What counts as relevant; whether a change merits revision |
| Authority, budgets, cancellation, grants, labels | Whom to spawn, what to share, when to converge |
| Scoring claims against reality | Hypotheses, linkages, theses |

**P2. Observe, don't ask.** Provenance, labels, dependencies and relevance signals are computed from what agents actually did. Declared provenance (`based_on`) becomes an optional citation only.

**P3. Async first.** Only `wait` blocks. A waiting agent costs nothing. In production it is durable, survives restarts, and is resumed by events.

**P4. Authority is a tree, liveness is a DAG, information is a graph.** Keeping these apart is what makes graph-shaped collaboration safe. Accountability, budgets and stopping stay simple, while information moves freely.

**P5. One data model.** Theses, sources, skills, messages, outputs and the kernel's own state are all versioned databases. One verb reads them all, and one verb writes them all.

**P6. Early cutoff everywhere.** An unchanged commit creates no version and wakes no one. A refresh stops at the first computation whose output does not change.

**P7. Honest about time by construction.** There are two clocks:
- transaction time, on every version: when we learned it
- available time, on source versions: when the world could have known it

Backtests read only by available time.

**P8. Ablation decides what stays.** Skills, memory and patterns earn their place by beating no-skill and no-memory baselines on claims that resolve.

---

## 3. Object model

### 3.1 Databases and versions

A **database** is a named, append-only sequence of immutable versions. A **version** has these fields:

| Field | Meaning |
|---|---|
| `db`, `number` | Name and 1-based version number |
| `tx` | Transaction time: a global, monotonic commit counter |
| `available_at` | Available time. Set by sources; null for derived data |
| `rows` | The full row set (production may store diffs with periodic snapshots) |
| `diff` | `{key: [old, new]}` against the previous version |
| `writer` | Handle of the computation that committed it, or null for people and sources |
| `read_set` | `(db, version)` pairs the writer had read: the observed provenance |
| `labels` | Information-flow labels inherited from everything the writer read. Verified earlier |

A commit that changes nothing creates no version. That rule is the physics behind early cutoff.

Reserved namespaces:

| Namespace | Written by | Purpose |
|---|---|---|
| `src/*` | Ingestors and people | Market data, CPI, rates, filings, news, with `available_at` |
| `thesis/*` | Agents | One database per thesis. The agent chooses the schema |
| `board/*` | Agents | Shared coordination: open questions, answers, debates |
| `out/<handle>` | The computation itself | Its results and streamed progress |
| `inbox/<handle>` | People and owners, via `tell` | Steering and messages |
| `lib/skills` | People | The skill library. Optional |
| `sys/agents` | Kernel (read-only) | Status, owner, revision and budget of your descendants |
| `sys/trajectory` | Kernel (read-only) | Every verb call by every computation |

### 3.2 Computations, handles and runs

A **computation** is a named piece of work. Its handle is the identity digest:

```
handle = digest(task, inputs, skill, model)     // + a nonce when share = false
```

The handle is stable across revisions. A **run** is one execution of a computation. Refreshing a computation creates revision n+1 under the same handle, and the new run writes new versions of the same `out/<handle>`. Consumers therefore depend on a stable name, and early cutoff works across revisions.

Each computation records:
- `owner`: the authority tree
- `holders`: the liveness DAG
- `budget`
- its current run

Each run records:
- its reads, with the version, keys, result hash and the writer of the version read
- its children
- the delta that triggered it
- its state: running, done, failed or cancelled

### 3.3 Principals

There are three kinds of principal:
- **people**, such as a PM or analyst
- **computations**
- **sources**, meaning ingestors

People sit at the root of the authority tree. Sources write only `src/*`. Computations write their own `out/`, the databases they are granted, and inboxes below them in the tree, via `tell`.

---

## 4. The five verbs

The JavaScript signatures below match the reference bridge, which is tested under QuickJS. Native tool calls use the same names and fields.

### 4.1 `spawn({task, inputs?, skill?, model?, share?, budget?, priority?}) → handle`

Starts or attaches to a computation and returns immediately.

| Disposition | When | Effect |
|---|---|---|
| `started` | No computation with this handle exists | Creates it. The caller becomes owner and holder, and the budget is carved from the caller's |
| `joined` | An identical computation is running | The caller becomes a holder. One execution serves all holders |
| `verifying` | An identical computation has finished | Re-checks its recorded reads, refreshing their writers first. Reuses the result if nothing moved, otherwise runs a new revision with the delta |

Details:
- **`skill`** names a row in `lib/skills`. The run's first act is a recorded read of that row, so the procedure enters context as data.
- **`share`** defaults to `true`. Pass `false` for deliberately independent samples, such as ensemble members or red-team passes.
- **`model`** routes to an executor and is part of the identity, so two models never share a result by accident.
- **`budget`** sets the child's spawn allowance. It costs the caller `1 + budget`, and exceeding it raises `Rejected`.
- **`priority`** is Designed. It sets a scheduling priority, and work inherits the priority of the highest-priority computation waiting on it.

Spawning an existing finished computation again is how an agent refreshes it. No separate refresh verb exists.

Verified: dispositions and joins; budget refusal and visibility; skill reads; re-spawning to verify.

### 4.2 `query({db, keys?, as_of?, available_by?, similar?, top?}) → {db, version, rows}`

Reads a database and records the read.

Recorded fields:
- `db`, `keys`, `version`
- the result hash
- the result rows
- the writer of the version read
- a `volatile` flag

Volatile reads are kept in the trajectory but never used to judge staleness. They are:
- similarity searches
- `as_of` and `available_by` reads
- system tables
- the inbox

Options:
- **`as_of`** reads by transaction time. **`available_by`** reads by available time. Both are Verified.
- **`similar: text`** ranks rows by similarity. Its job is to help a model find an existing question that means the same thing. The reference kernel uses word overlap; production uses embeddings. The model decides what counts as the same.
- **SQL** is Designed: `query({db, sql, params})`, with the result-set hash as the read hash. This fits one SQL database per thesis, as in the firm build.

### 4.3 `commit({db, changes, if_absent?, if_version?, available_at?}) → {version, diff, noop} | {conflict, existing}`

Writes a new version.

- `changes` maps keys to values. A null value deletes the key.
- No diff means no version (`noop: true`), and nothing is woken.
- The writer's latest non-volatile reads are attached as `read_set`. Labels propagate from everything it read (Verified earlier).
- **`if_absent: [keys]`** makes the commit conditional: first writer wins. That is enough to build claims, queues and boards without a lock verb. `if_version` is Designed: optimistic concurrency on the whole database.
- Commits to `out/<self>` are the computation's result and its streamed progress. There is no separate checkpoint or submit verb.
- `sys/*` is never writable. `inbox/*` is written only through `tell`.

### 4.4 `wait({sources, timeout?}) → event`

The only blocking verb. It returns the first event that is ready.

| Source | Ready when | Event |
|---|---|---|
| `handle` | The computation is up to date | `{kind: done \| failed \| cancelled, rows, version}`; reading the rows is a recorded read |
| `{db, keys, after}` | The result of `keys` at the latest version differs from its result at version `after` | `{kind: change, version, rows, was}` |
| `{inbox: after}` | Messages with sequence numbers above `after` exist | `{kind: inbox, messages}` |
| `{progress: handle, after}` | `out/<handle>` has a version above `after` | `{kind: progress, version, rows}` |
| `timeout` | Time runs out | `{kind: timeout}`; nothing is left pending |

Rules:
- **Cursors are explicit.** Every data source carries the version the caller last saw, so a change between a read and a wait is never missed. Abandoning a wait leaves nothing stuck.
- **Completion cycles are refused.** If A waits on B's completion while B waits on A's, the second wait raises `Rejected`. Data waits cannot deadlock: a loop across theses advances through versions. Whether it settles depends on the agents, so damping and budgets cap it.
- **Designed extensions:**
  - `guard`: a model-written predicate over `(was, now)`, evaluated by the kernel in the sandbox with no model call. For example, wake only if core CPI moved by at least 0.1.
  - `debounce`: batch a burst of changes into one wake.
  - `durable`: suspend the agent across turns and restarts.

### 4.5 `close(handle)`

Releases the caller's hold. Work that no one holds is cancelled, and cancellation cascades to everything only it held. Work held by others continues. A run's holds are released automatically when it ends, so a long-lived child must be held by a long-lived owner. Verified.

### 4.6 Library sugar (not kernel)

These are plain code over the verbs:
- `tell(handle, message)`: a commit to `inbox/<handle>`, after the kernel checks that the sender is a person or an owner up the tree
- `result(handle)`
- `wait_all(handles)`
- `parallel(tasks)`
- `race(tasks)`
- `map(items, fn)`

Sugar can be deleted without losing capability. `parallel` must return errors rather than `null`: the old helper lost the reason, which was verified earlier.

---

## 5. Execution model

### 5.1 Async background execution

Every computation runs as a background task from the moment it is spawned. A parent keeps working while its children run.

Verified:
- A parent wrote its plan at 0.00 s while three 0.30 s children ran. The whole job took 0.30 s.
- A recursive sum split itself by the parent's own criterion, at most two items per leaf. It produced 15 runs with 8 concurrent leaves and took 0.05 s, against 0.40 s for leaves run in series.

### 5.2 The agent loop, turn boundaries and steering

An agent is a model loop over the verbs: native tool calls, code, or both. Its context is assembled at each turn:
1. A stable prefix: task, skill, policies. It is laid out for prompt caching.
2. What the agent chooses to query, usually its own thesis database rather than its transcript.
3. The event that woke it.
4. For a revision run, the delta and the previous output.

Steering:
- **Messages** are delivered at the target's next turn boundary: its next `wait`, or its next tool result in a model loop. The trajectory records the chain with its cause: person → root inbox → `tell` → worker inbox → worker read. Verified: the worker kept all sectors before the steer, then only banks after it.
- **Preemption** is Designed. `tell(handle, {text, preempt: true})` from an owner or person cancels the target's in-flight model call at the next safe point, never in the middle of a commit, and starts a turn with the message. The interruption is recorded.
- **The root never blocks.** Its loop waits on its children and its inbox together, so a person always gets an answer. Verified: a status reply came at 0.10 s while the worker ran until 0.40 s.

### 5.3 Authority, liveness, cancellation

- **The owner** is set at `started`. It holds authority: who may `tell` and who is charged for the work.
- **Holders** are everyone who spawned or joined the work. Work stays alive while any holder remains.
- **Cancellation** follows holders, not owners. Closing A cancelled A, but its shared dependency survived because B still held it. Closing D cancelled D and the private child only D held. Verified.

### 5.4 Budgets

Budgets are hierarchical. A spawn carves its child's budget out of the parent's, and `sys/agents` shows every descendant's remaining budget, so parents can size their own fan-out. The reference kernel budgets spawns (Verified). Production adds tokens, dollars and wall time (Designed). The model decides how to allocate; the kernel enforces it.

### 5.5 Scheduling and performance

All of these are Designed except where marked.
- **Rate limits.** Model-call concurrency is capped per provider and queued by priority.
- **Priority inheritance.** Work inherits the priority of the highest-priority computation waiting on it.
- **Cheap reactivity.** Guards run without a model. Debouncing batches news bursts.
- **Early cutoff.** Verified.
- **Speculative spawns.** Start likely-needed work early and `close` it if unneeded; cancellation returns the budget.
- **Streaming.** Consumers start from partial output, which beat both sequential and parallel schedules (verified earlier: 0.70 s against 1.00 s and 1.30 s).

### 5.6 Executors and model routing

`model` selects the executor. Executors:
- `agent`: a model loop with the verbs as tools plus a QuickJS sandbox for PTC
- `code`: runs a skill's deterministic script, with no model call
- `compute`: Designed. A Python sandbox for pandas and statistics work, which the current harness lacks

The model is part of identity. That gives ensembles of different models and point-in-time model twins for backtests without collisions. Verified by construction of the handle.

### 5.7 Long-lived agents and memory

A standing thesis agent may live for months. Its working memory is its thesis database, not its transcript. On each wake its context is rebuilt from:
- the stable prefix
- a query of its own database
- the waking event and delta

Transcripts are trajectory, kept for audit and learning, never replayed as memory. Compaction is therefore the agent's own job: it decides what to commit to its database. That is policy. The kernel only guarantees versions, reads and wakes. Designed.

### 5.8 Durability and recovery (production)

Designed. The store is versions and rows in Postgres, or per-thesis SQLite with change tables, plus an object store for large blobs and an append-only trajectory.
- Commits are idempotent through request ids and conditional writes.
- Wakes are delivered at least once. Agents treat a repeated event as a no-op through cursors.
- After a crash, waiting agents resume from their registered waits and their databases. No model call is replayed to reconstruct state.

---

## 6. Graph operations catalog

| Operation | Recipe in the five verbs | Shape | Status |
|---|---|---|---|
| Fan-out and fan-in | `spawn` many, then `wait` on them | Tree | Verified |
| Shared dependency by name | Identical `spawn`: `joined` or `verifying` | DAG | Verified: shared `d` and `e` each ran once |
| Shared dependency by meaning | Claim on `board/questions` with `if_absent`, then `query(similar)` for earlier claims. Yield to an earlier one by waiting on its answer row, or run it and commit the answer | DAG | Verified with both starting at once: 1 run. Word overlap stood in for the model's judgment |
| Lateral streaming | Pass a sibling's handle; `wait({progress: handle, after})` | Graph | Verified: the consumer saw partial 1 at 0.10 s; the producer finished at 0.40 s; no parent relay |
| Peer convergence | Each commits its own view first, waits on the other's row, then commits a revision | Graph, cyclic over time | Verified: 3.0 and 5.0 both revised to 4.0 |
| Feedback across theses | Two standing agents, each waiting on the other's row | Graph, cyclic over versions | Verified: settled at cut path 2.5 and bank stress 0.25 after 6 wakes |
| Mutual completion waits | Two `wait(handle)`s on each other | Refused | Verified: one refused as a cycle |
| Red-team a trajectory | `query("sys/trajectory", [handle])` | Graph | Verified: counts match the kernel's own log |
| Incremental refresh | Re-`spawn` or `refresh` the root; writers are refreshed first; early cutoff | Graph | Verified |
| Scenario fork | Run in a forked world; diff against the base | Graph | Verified |
| Steering down the tree | `tell` from a person or owner | Tree | Verified |

A tree of subagents can express only the first and last rows. Everything between them depends on the information graph being recorded, versioned and readable across branches. That is the core innovation, and it costs no new verbs: it falls out of recorded reads plus cursor-based waits.

Example programs for the main operations are in Appendix A.

---

## 7. Trajectories and deltas

### 7.1 What is recorded

Every verb call appends a row to `sys/trajectory`:

```
{seq, t, key: handle, rev, verb, ...detail}
verb ∈ spawn(handle, task, disposition) | query(db, keys, version) | commit(db, version, diff, noop | conflict)
     | wait(sources, timeout) | wake(cause, source) | tell(handle, seq, text, cause) | close(handle)
     | run_start(task, because) | run_end(state, error) | reuse(handle) | cancel(handle, reason)
```

Production adds, all Designed:
- the model id and a hash of the prompt per model call
- token and cost counts
- tool calls and their recorded results
- labels

### 7.2 Refresh: recompute only what moved

`refresh(h)` runs the following for computation `h`:

```
ensure(h):
  run ← current run of h
  if run is not done: re-run h; return
  for each writer w of a version that run read (excluding h and the current chain):
      ensure(w)                                   # bring upstream up to date first
  stale ← reads whose result hash differs now     # verifying trace
  if stale is empty: record reuse; return         # early cutoff
  re-run h as revision n+1 with delta = stale (was, now)
```

The revision's own spawns go through `verifying`, so it reuses every child that is still fresh. Results from the sample graph (`index` → `a`, `b`; `a` → `d`, `e`; `b` → `c`, `d`; `d` → `e`), all Verified:

| Change | Computations re-run (of 6) | What happened |
|---|---|---|
| CPI 0.3 → 0.4 | 5 | Filings reused. Review became "macro hawkish, bank trough Q2" |
| CPI 0.3 → 0.32 | 3 (inflation, rates path, macro) | The rates path came out unchanged, so bank and review stopped there |
| Edit skill `c` | 1 (`c`) | Its output was unchanged, so nothing else ran. The current kernel re-identifies every call on any skill edit (verified earlier) |
| Re-ask a shared call after its inputs changed | Fresh revision | The current kernel reused a stale answer, 2 cuts while the database said 1 (verified earlier). Verifying reuse returned 1 |

Refresh deliberately does not recurse through data cycles. Standing agents settle those by iterating through versions, as in the feedback row of section 6.

### 7.3 What a revision run sees

Designed. A revision run receives:
- `delta`: each stale read with its `was` and `now` rows
- its previous output
- optionally, a summary of its previous trajectory

The model can then revise rather than redo. In the reference kernel the scripted programs recompute in full. Whether models revise well from a delta must be measured, and the fallback is a full re-run.

### 7.4 Explain

`explain(h)` returns the revision, the reads that moved and the output diff. Verified: macro changed from `neutral` to `hawkish` because `thesis/inflation` moved from 0.3 to 0.4, and the rates and inflation outputs moved with it. This is attribution for research outputs, analogous to P&L attribution.

### 7.5 Scenario forks

A fork copies the world (copy-on-write in production). A hypothetical commit in the fork, followed by a refresh, runs only the affected graph, and the base world is untouched. Verified: in a fork with CPI at 0.6, 5 computations re-ran and the rates path went to 1 cut. The base CPI history stayed 0.3, 0.4. Use forks for stress tests, pre-mortems and scenario books.

### 7.6 Two clocks and honest backtests

Sources commit with `available_at`. A backtest at time T reads with `available_by: T`, runs in a fork, and uses point-in-time model twins through `model`. Verified: by t = 150 the read returned 0.3; by t = 250 it returned 0.4. A hermetic flag that refuses non-`available_by` reads inside backtest worlds is Designed.

### 7.7 Where relevance comes from

The kernel never judges relevance. The model decides at five points:

1. **What to read.** Reads define the dependency graph.
2. **What to wait on, and with what guard.**
3. **Whether to revise when woken.** "No change" ends propagation.
4. **Router agents** (Designed). For information no thesis has read yet, such as a news item, a model reads the firehose and decides which theses should hear about it. It posts to a shared board that those thesis agents watch, or opens a board question. It does not `tell`, because it holds no authority over them.
5. **Staleness sweeps.** The kernel can list computations whose recorded reads have moved, even unwatched ones. The owner decides whether to refresh. Verified earlier: a macro read that nobody watched was still flagged stale.

### 7.8 Three kinds of replay

| Kind | Purpose | Mechanism |
|---|---|---|
| Audit replay | What exactly happened | Read `sys/trajectory` plus versions; no re-execution |
| Refresh | Bring outputs up to date after changes | Section 7.2 |
| Re-execution | Evaluate a new model, prompt or skill | Run in a fork, `available_by` as needed, new `model`; diff the outputs |

---

## 8. Skill graph compatibility

Skills load into `lib/skills` from the existing `SKILL.md` format, with wikilinks derived from prose. The sample graph loaded unchanged.
- `spawn({skill})` makes the skill's text part of the run's context through a recorded read.
- Links in the prose remain hints. The model may follow or ignore them.
- **Identity.** The whole-registry snapshot is no longer part of identity. A skill edit invalidates exactly the computations that read that skill. Verified: 1 re-run instead of all.
- **Code resources.** A skill's deterministic scripts run under the `code` executor.
- **Running without skills.** The same programs run as free calls and produced the same review. Verified.
- **Agents writing skills** is Designed. If agents ever write skills, they commit candidate rows that a person promotes. That is just another commit with authority checks.

---

## 9. Compliance and audit

- **Grants.** A computation reads its own databases, what it was granted (handles passed in are grants), and public namespaces. The current kernel enforces grants on records, verified earlier. The reference kernel omits them, so they are Designed there.
- **Labels.** Labels such as MNPI, expert-network or restricted-list attach to source rows. They propagate through reads to every commit, and policy can block writing labeled content to less-restricted databases or readers. Verified earlier: restricted filings tainted the bank thesis and the review, but not macro.
- **Steering authority.** Only people and owners up the tree may `tell`. Peers coordinate through shared databases, which grants govern.
- **Immutability.** Versions and trajectory rows are append-only and content-addressed. A decision can be reconstructed at its transaction time with `as_of`. That serves SR 11-7-style model risk review and post-trade inquiry.

---

## 10. Performance layer for state of the art in investing

The kernel is necessary, not sufficient. Performance comes from the loop around it, specified in the earlier design document. Each piece maps onto kernel features:

| Piece | Kernel features it uses |
|---|---|
| An honest evaluation environment: masked tasks, point-in-time twins, post-cutoff periods, live shadow book, PM plus agent | `available_by`, forks, `model` routing |
| Claims and ideas with resolution rules: the only fixed schema | A `claims` database with a fixed schema and a resolver writing outcomes as a source |
| Factor-neutral shadow book; deflated metrics using the recorded trial count | Trajectory counts every trial |
| Compute allocated by value of information | Budgets, priority, `sys/agents` |
| Independent views before consensus; multi-model ensembles | `share: false`, `model`, commit-then-converge |
| Learning in order of return: recalibration, then verifiers and rerankers, then RL on resolved outcomes | Trajectories joined to outcomes through the read graph give credit assignment: which reads and theses fed a claim that resolved |
| Centaur scoring | People are principals; their decisions are commits |

North-star metrics:
- excess log score against consensus on resolved claims
- residual IC by horizon
- calibration error
- centaur uplift
- cost per resolved claim
- hours from event to first revised view, which refresh and early cutoff exist to shrink
- the share of runs that pass the hermetic check

---

## 11. What earns its place

The current harness exposes 31 implemented names:

| Layer | Names | Where |
|---|---|---|
| Kernel capabilities | 8 | `main` |
| JS wrappers | 7 | `main` |
| Capabilities | 2 | `rlm-surgery` branch |
| Helpers | 9 | `rlm-surgery` branch |
| Database tools | 5 | Scratchpad prototype |

All 31 fold into five verbs.

| Today | Verdict | Becomes | Why |
|---|---|---|---|
| `runNode`, `nodes.run`, `spawn` (helper) | Folded | `spawn` + `wait` | Blocking is a choice the caller makes, not a kind of call |
| `openNode`, `nodes.open`, `nodes.with`, `spawn.open`, `spawn.with` | Folded | `spawn` | Every spawn returns a handle |
| `nextNodeEvent`, `op.next`, `op.result`, `op.checkpoints`, `watch`, `waitFor` | Folded | `wait` | One multiplexed, cursor-based wait. No pending-read wedge |
| `closeNode`, `op.close` | Kept | `close` | Liveness release with cascade |
| `readNode`, `readArtifact`, `readValue`, `read` | Folded | `query` | Skills, artifacts and slices are all database reads |
| `publishCheckpoint`, `submitCandidate`, `putArtifact`, `put`, `publish`, `submit`, `claim` | Folded | `commit` | Progress and results are versions of `out/<self>`; claims are `if_absent` |
| `query`, `commit` (prototype tools) | Kept | `query`, `commit` | Already in final form |
| `parallel`, `pipeline` | Library | sugar | One line of code; must return errors |
| `NodeRequest.node` required | Dropped | `skill?` optional | Requirement 1 |
| Exact request join and reuse | Kept, demoted | `joined` / `verifying` | Cheap special case. Meaning-level sharing uses the board |
| Caller-key replay | Kept | idempotency | Physics, needed for crash recovery |
| Leases and cancel-when-unheld | Kept | holders | The liveness DAG |
| "Join or close every child before returning" | Changed | release on run end | Children nobody else holds stop when the run ends; parents never block to join |
| Wait-cycle refusal | Kept, narrowed | completion waits only | Data cycles are legitimate |
| Depth limit | Demoted | safety cap | Budgets govern recursion |
| Call-count ledger | Replaced | hierarchical budgets in `sys/agents` | The program must see its own budget |
| Session store and deadline | Replaced | a persistent world and per-computation budgets | Long horizon |
| Registry snapshot in identity | Dropped | recorded skill reads | A skill edit invalidates only its readers |
| Executor binding per skill | Replaced | `model` on spawn, part of identity | Ensembles, twins, routing |
| `observed_refs`, `consulted` | Generalized | recorded reads with versions and result hashes | Observe, don't ask |
| `based_on` | Demoted | optional citation | Declared provenance is not trusted |
| `put_input` | Folded | commits by a person or source principal | One write path |
| Grants on refs | Kept | grants on handles and databases | Authority physics |

---

## 12. Where RLM and PTC sit

**RLM is not a kernel primitive.** It is a pattern: context lives outside the prompt, and the model writes code that calls sub-models recursively over it. The kernel already supplies the three things the pattern needs:
- databases hold the context
- `spawn` can be called from code
- recursion is bounded only by budget and a safety cap

The difference is the default. In RLM's basic form, a sub-call returns a value to the caller's code. Here, every sub-call is a background computation with a handle, and awaiting it is a choice. The branch's helpers become optional sugar.

**PTC is a driver, not the design center.** A turn can drive the verbs by native tool calls or by code in the QuickJS sandbox. Code wins for loops over many items, for building contexts, and for filtering large data without flooding the context. Verified: the five verbs ran unchanged from QuickJS.

A design rule follows: a code cell may wait briefly. Long waits end the turn and suspend the agent durably, which is Designed.

---

## 13. Verification record

### 13.1 Reference kernel: `spec_test.py`, 24/24, stable across repeated runs

| Req | Check | Result |
|---|---|---|
| R1 | The sample skill graph runs on five verbs; shared `d` and `e` each run once | 6 runs for 6 skills, two joins |
| R1 | Each skill enters a run as a recorded read | One read per skill |
| R1 | Editing one skill re-runs only its readers | Only `c` re-ran |
| R1 | The same work runs with no skill library | Same review |
| R2 | `spawn` never blocks | Plan at 0.00 s; three 0.30 s children; 0.30 s in total |
| R2 | Recursion by the parent's criterion; leaves concurrent | 15 runs; 0.05 s against 0.40 s in series |
| R2 | One `wait` over many sources; timeouts leave nothing stuck | `timeout`, `done:A`, `done:B` |
| R2 | Budgets flow down and are visible | Third spawn refused; parent sees `budget_left = 0` |
| R3 | A person talks to the root while children run | Reply at 0.10 s; worker ran until 0.40 s |
| R3 | The root steers a running worker | All sectors before; banks only after |
| R3 | The steering chain is recorded with its cause | person → root → worker, cause `inbox/<root>#2` |
| R3 | Close cascades; shared work survives | A cancelled while its shared leaf finished for B; D and its private leaf cancelled |
| R4 | Shared work by meaning, both starting at once | 1 run; the later claim yielded |
| R4 | Peers converge through data | Both revised to 4.0 |
| R4 | A sibling consumes another sibling's stream | Partial 1 at 0.10 s; producer done at 0.40 s |
| R4 | A feedback loop across theses settles | 2.5 and 0.25 after 6 wakes |
| R4 | Mutual completion waits are refused | One refused as a cycle |
| R5 | The trajectory is queryable by another agent | Counts match the kernel's log |
| R5 | A CPI release re-runs only affected work | 5 of 6; filings reused |
| R5 | Output changes explain themselves | `neutral` → `hawkish` because inflation moved 0.3 → 0.4 |
| R5 | A small print cuts off early | 3 of 6; bank and review reused |
| R5 | Scenario fork | Fork CPI 0.3, 0.6; base 0.3, 0.4 |
| R5 | Reads by available time | 0.3 by t = 150; 0.4 by t = 250 |
| PTC | All five verbs from QuickJS | Correct result; the closed child was cancelled |

### 13.2 Earlier checks in this thread

These motivated the changes above:

| Suite | Result | What it found |
|---|---|---|
| `graph_test.py` | 18/18 | Thesis databases layered on the current kernel. Stale shared reuse; label propagation; watch chains; blast radius |
| `skillfree_test.py` | 12/12 | Exact-text joins duplicate work; handles cannot be passed; a raced read wedges the handle; 64 frames per session in total; `parallel` loses errors; the free-call prompt omits handles, checkpoints and watches |
| `generic_test.py` | 5/5 | No downward messages; mutual watching through handles is a cycle |
| `fit_test.py` | 11/11 | No memo across sessions; identity ignores the model; any skill edit re-identifies every call; no labels on records |
| Repo unit tests | 94 pass | Run on the `rlm-surgery` checkout, unchanged by this work |

---

## 14. Known gaps, risks and open questions

1. **Model judgment is untested here.** Every program was scripted. Before investing months, three questions need real models on three or four research questions, with and without skills:
   - Does sharing by meaning work with real embeddings and real model judgment?
   - Do models revise well from a delta?
   - Do parents decompose well with budgets visible?
2. **Scale.** The reference kernel re-checks every waiting source on every commit. Production must index waits by database and key, re-verify lazily, and debounce bursts.
3. **Refresh over data cycles** relies on standing agents iterating to a fixed point. Convergence needs damping, and budgets cap runaway loops.
4. **Read granularity.** Key-level reads are precise. SQL reads hash whole result sets, so a broad query re-triggers too often. Agents should be guided to narrow reads, which is a policy and prompt matter.
5. **Missed relevance.** The kernel only knows reads that happened. Unread information reaches theses only through router agents and staleness sweeps, and how well that works must be measured.
6. **Context for months-long agents.** Database-as-memory is the bet. Measure it against transcript compaction.
7. **Durability** is most of the remaining engineering: durable waits, idempotent commits, recovery, multi-process scheduling.
8. **Gaps not yet in the reference kernel:** grants, labels, guards, debounce, preemption, priority inheritance, SQL reads and a compute sandbox.

---

## 15. Build plan

| Phase | Weeks | Deliverable | Exit test |
|---|---|---|---|
| 0 | 1–2 | Freeze this spec. Port `spec_test.py` as the conformance suite | 24/24 against the new kernel API |
| 1 | 3–8 | Kernel core in the harness repo: store with versions, recorded reads, conditional commits and two clocks; the five verbs; background scheduler with durable waits; inboxes and steering; hierarchical budgets; QuickJS and native-tool bridges; skill library loader | Conformance suite plus the sample graph on real models |
| 2 | 9–12 | Refresh, early cutoff and explain; forks; trajectory queries; guards and debounce; grants and labels; preemption; priority inheritance | CPI and rates deltas on live data re-run only affected theses |
| 3 | 13–18 | Investment layer: ingestion with `available_at` (CPI, rates, filings, news); claims database and resolver; shadow book; standing thesis agents; router agents; point-in-time backtest worlds | Post-cutoff backtest with no leakage; first resolved-claim scores against baselines |
| 4 | ongoing | Performance loop: value-of-information budgets, ensembles, recalibration, verifiers, RL on resolved claims; centaur pilots with one macro PM and one fundamental PM | Measured centaur uplift |

---

## Appendix A. Example programs (JavaScript, as a model would write them)

**Root that stays responsive and steers.** Verified in Python form.

```js
const worker = await spawn({task: 'Screen the coverage list', inputs: {items}, share: false});
let after = 0;
for (;;) {
  const ev = await wait({sources: [worker, {inbox: after}]});
  if (ev.kind !== 'inbox') break;                          // the worker finished
  for (const [seq, msg] of ev.messages) {
    after = seq;
    if (msg.text === 'status?') {
      const kids = (await query({db: 'sys/agents'})).rows;
      await commit({db: OUT, changes: {['reply' + seq]: Object.keys(kids).length + ' tracked'}});
    } else if (msg.text.startsWith('steer:')) {
      await tell(worker, {text: msg.text.slice(6), cause: seq});
    }
  }
}
```

**Shared work by meaning.** Verified in Python form; the similarity judgment is the model's.

```js
const mine = 'q:' + SELF.slice(0, 6);
await commit({db: 'board/questions', changes: {[mine]: {question}}, if_absent: [mine]});
const similar = (await query({db: 'board/questions', similar: question})).rows;
const earlier = Object.entries(similar).find(([k, v]) =>
  k !== mine && v.tx < similar[mine].tx && sameQuestion(question, v.question));   // model judgment
let answer;
if (earlier) {                                            // someone already asked: wait on their answer row
  const got = await query({db: 'board/answers', keys: [earlier[0]]});
  answer = got.rows[earlier[0]] ??
    (await wait({sources: [{db: 'board/answers', keys: [earlier[0]], after: got.version}]})).rows[earlier[0]];
} else {                                                  // first to ask: do the work and post the answer
  answer = (await result(await spawn({task: question}))).answer;
  await commit({db: 'board/answers', changes: {[mine]: answer}});
}
await commit({db: OUT, changes: {answer}});
```

**Standing thesis agent with a guard.** Guard and durable wait are Designed.

```js
let seen = await query({db: 'src/cpi', keys: ['core_cpi']});
let lastSeq = 0;
for (;;) {
  const ev = await wait({sources: [
      {db: 'src/cpi', keys: ['core_cpi'], after: seen.version,
       guard: '(was, now) => Math.abs(now.core_cpi - was.core_cpi) >= 0.1'},
      {inbox: lastSeq}],
    durable: true});
  if (ev.kind === 'inbox') lastSeq = ev.messages.at(-1)[0];
  if (ev.kind === 'change') {
    seen = ev;
    // revise the thesis from the diff; commit only if the view actually changes
  }
}
```

**Commit, then converge.** Verified in Python form.

```js
await commit({db: 'board/debate', changes: {[me + ':1']: est}});
const got = await query({db: 'board/debate', keys: [other + ':1']});
const theirs = got.rows[other + ':1'] ??
  (await wait({sources: [{db: 'board/debate', keys: [other + ':1'], after: got.version}]})).rows[other + ':1'];
await commit({db: 'board/debate', changes: {[me + ':2']: (est + theirs) / 2}});
```

**Recursive decomposition by the parent's own criterion.** Verified in Python form.

```js
if (xs.length <= k) { await commit({db: OUT, changes: {sum: xs.reduce((a, b) => a + b, 0)}}); }
else {
  const left = await spawn({task, inputs: {xs: xs.slice(0, xs.length / 2), k}});
  const right = await spawn({task, inputs: {xs: xs.slice(xs.length / 2), k}});
  const [l, r] = [await result(left), await result(right)];
  await commit({db: OUT, changes: {sum: l.sum + r.sum}});
}
```

## Appendix B. Compared with Claude Code subagents and agent teams

Claude Code facts below come from its documentation, checked 2026-11-02.

| | Claude Code | This kernel |
|---|---|---|
| Orchestrator | A conversation; each spawn is a model tool call; summaries return into context | A program or a model loop; results stay in databases; handles come back |
| Nesting | Up to 3 layers below the main conversation by default | Bounded by budget, with a safety cap |
| Peer communication | Named subagents message each other; teams use mailbox files and a shared task list | Shared versioned databases plus cursor-based waits; steering through inboxes up the tree |
| Durability | The team directory, including mailboxes, is removed at session end (task lists persist); teams are not available in headless or Agent SDK sessions | A persistent world; designed for unattended, months-long runs |
| Reuse | Not described in the docs | Identical computations join or verify; meaning-level sharing through boards |
| Provenance | Separate transcript per agent | Recorded reads with versions and result hashes on every write |
| Change propagation | Not described in the docs | Refresh with early cutoff; explain; forks; two clocks |

Claude Code is ahead today on interactive collaboration polish and tooling maturity. The case for this kernel is the information graph and the delta machinery, which software engineering gets for free from git, compilers and tests, and which investment research does not have.
