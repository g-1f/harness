# Runtime and native PTC reference

Status: implemented single-process reference runtime. This document describes the
checked-in source, including the adversarial-review fixes. Proposed memory,
automatic supersession, artifact adoption and failure-as-artifact APIs are not
available. See [review findings](review-findings.md) for decisions and evidence.

Read the [design](design.md) first, then [patterns](patterns.md) for composition.

## Native PTC boundary: what earns its keep

PTC means writing ordinary code that calls host capabilities. It is not a new
workflow language. In this repository, `eval` is the interpreter entry point;
`NodeAPI` is the domain-independent boundary exposed inside it. Python executors
use the same supervisor. The API below is a local design, not a universal PTC standard.

A capability earns a native implementation when JavaScript alone cannot enforce
its lifetime, authority, or publication effect. **Seven host operations express
the essential effects; an eighth, `runNode`, is a deliberate final-only fast path.**
No host operation interprets a review verdict or decides what a useful answer is.

| Native endpoint | Host responsibility | Why it remains |
| --- | --- | --- |
| `readNode({node})` | Load a bounded, pinned procedure packet and record consultation | Dynamic graph discovery needs access to the registry; model globals cannot supply or validate pinned package bytes |
| `openNode({request})` | Admit a request; atomically start/join/reuse work; acquire a caller-owned lease | Fresh contexts, shared work identity and ownership span multiple interpreters |
| `nextNodeEvent({handle, after})` | Await/replay an ordered checkpoint or terminal result; grant delivered refs | The host owns event order, dependency checks, liveness, handle ownership and artifact authority |
| `closeNode({handle})` | Release this consumer; cancel/drain only when the last consumer leaves | A local promise cannot safely decide whether another branch still needs the producer |
| `readArtifact({ref, offset, limit})` | Read bounded immutable evidence after checking grants and integrity | Knowing a hash is not authority; neither the wrapper nor artifact content grants access |
| `publishCheckpoint({summary, content, based_on})` | Freeze intermediate output, check refs/budget, announce it to subscribers | Progress must outlive a producer's private context and remain replayable to late subscribers |
| `submitCandidate({summary, content, based_on})` | Stage the final return value across the tool/agent boundary | This is the adapter's return channel; the runtime validates and publishes only after execution and child cleanup complete |
| `runNode({request})` | Await one final receipt with a scoped lease | Derivable in control flow, but retained to avoid fetching/granting every checkpoint when only the final artifact is requested |

`runNode` uses the same operation pool as `openNode`; it introduces no alternative
identity, retry, cancellation or approval semantics. Its concrete benefit is fewer
bridge round trips and narrower artifact grants. `nodes.open(...).result()` consumes
progress and therefore grants those delivered checkpoints too. The regression
`test_final_only_call_does_not_grant_unobserved_checkpoints` verifies this distinction.
No latency benchmark is claimed.

`submitCandidate` does not approve a proposal. “Candidate” means a staged return
value awaiting structural checks. Ordinary Python runners simply return that same
`{summary, content, based_on}` object. It could be a review, number, report, failure
assessment or another application-defined transformation result.

### Derived operations stay in code

| Operation | Implementation |
| --- | --- |
| Function application and nesting | Normal functions and `await nodes.run(request)` |
| Parallel fan-out and joining | `Promise.all` or `Promise.allSettled`; runtime leases still govern each call |
| Progress cursor and terminal-result loop | `operation.next()`, `.checkpoints()`, `.result()` in the shared JS wrapper |
| Scoped cleanup | `nodes.with(request, callback)` using `try/finally` |
| Early release | `operation.close()` forwarding the native release capability |
| Review, red teaming, coherence | Ordinary named skills returning ordinary artifacts |
| Approval and repair | Application code reads the chosen content schema and issues bounded fresh calls |
| Another aspect of the same evidence | New task plus explicit evidence refs; use fresh execution when needed |
| Model KV reuse | Adapter/provider configuration and stable prompt layout; no graph primitive |

There are no `reviewNode`, `needs_review`, `approve`, `repair`, `lock`, `unlock`,
`joinNode`, `forkContext`, or RLM primitives. A new execution already starts a
fresh context. `[[b|text]]` is a prose link to b with a display label, not a call,
argument, task override or sharing key.

### Composition example

This is the shape verified through real QuickJS in
[`test_nested_ptc_transformations`](../tests/test_integration.py):

```js
// invoke is an ordinary local helper assembling a NodeRequest.
const [a, c, d, e] = await Promise.all([
  invoke('a'), invoke('c'), invoke('d'), invoke('e')
]);
const [reviewed, challenged, combined] = await Promise.all([
  invoke('review', [a]),
  invoke('red_team', [a]),
  invoke('coherence', [c, d, e]).then(value => invoke('node_a', [value]))
]);
```

The values here are receipts. The helper passes their refs explicitly, and each
transformation reads the artifacts it needs. A review that says `verdict: fail`
can complete successfully. Whether to continue belongs to the caller's application.
Nothing adds role-specific fields to a skill, request or execution frame.

### Adapter and wrapper cleanup

[`NodeAPI.capabilities`](../harness/api.py) is the single list of bridge names,
method order and descriptions. Deep Agents builds its native tools from those
bound methods; CodeRunner registers the same methods in QuickJS. Both install
[`ptc.js`](../harness/runners/ptc.js). The wrapper owns only local cursor/cache/scope
state and cannot bypass host checks.

Deep Agents also exposes its framework `task` compatibility route. This adapter
replaces the framework's default worker with a dispatcher into `NodeRequest` and
the same supervisor. It is not another node primitive or an unsupervised agent pool.
Private scratch tools supplied by the framework are not artifact publication APIs.

Earlier cleanup removed the core `ReviewPolicy`, automatic review/repair lifecycle,
review-specific context fields and artifact metadata, `accepted`/`needs_review`
receipt states, and `readNode`'s obligation-activation flag. Application review
schemas now live only in the example composition, its skill prose and tests.

### Migration from the previous contract

| Previous behavior | Current call-site change |
| --- | --- |
| `Runtime(reviews=..., max_revisions=...)` | Register an application composition as an ordinary executor |
| `context.attempt`, `feedback`, `previous` | Put revision instructions and explicit refs in a new NodeRequest |
| `readNode({node, enter:true})` | Use `readNode({node})`; consultation never activates policy |
| Receipt `accepted` / `needs_review` | Receipt is `published`; read the application's decision content |
| Trace `accepted` / `needs_review` event | Successful execution emits `completed` |
| Record-level `reviews` metadata | Review refs/history are fields of the composition's content |
| Implicitly checked progress | Explicitly compose any required checker before publishing the application's progress decision |

These are intentional API changes. Legacy receipt states and core review configuration
are not retained as compatibility aliases.

## Shared node operations: identity, ownership and lifecycle

Status: implemented single-session, single-event-loop coordination. The
[parallel trajectory](../examples/trajectories/scenario_a.md) records the actual
converging execution graph, not an unrolled creation tree.

### 1. Four things that must not be conflated

| Object | Identity/lifetime | Responsibility |
| --- | --- | --- |
| Skill | Canonical name and immutable revision | Describes a procedure |
| Call binding | Caller execution ID plus local request key | Reserves one exact request and, once selected, its execution |
| Operation | Unique execution ID; optional shared-work identity | Owns the producer task and its eventual result |
| Wait lease | One active `run_node` await or open observation handle | Keeps an unfinished producer needed by this caller |

A and c can each have a call binding and wait lease pointing to one b operation.
B's first caller ID is recorded as its `origin`; origin is diagnostic, not ownership.
The execution context does not retain the origin's frame or private state.
The producer belongs to the session coordinator. A completed artifact records one
producer execution; call events record every consumer edge.

No lock/release attributes are added to skills. `NodeRequest` has one optional
call-level choice: `reuse: "fresh" | "session"`, default `"fresh"`. Joining and
release are automatic within `await run_node(...)`. `open_node` adds a caller-owned
observation handle for progress; it releases on terminal event, explicit close or
frame cleanup. This handle is not a lock token and cannot block other callers.
Each handle permits one pending event read. Cancelling a read retains its handle
for retry; closing is allowed after deadline expiry because it only releases
resources and still checks ownership. Cursors follow publication order, which may differ from the order work began.
Source versions and semantic freshness belong in artifact content.

### 2. Exact shared-work identity

Within one runtime session:

```text
execution_config = hash(skill_snapshot, executor_bindings, default_executor)
work_identity = hash(execution_config, node, task, inputs, ordered_refs)
call_identity = (caller_execution_id, local_key)
```

Canonical JSON sorts object keys and rejects nonfinite/non-JSON data. Task text and
reference order are preserved. Caller ID and local key are intentionally absent
from work identity. Two `reuse: "session"` requests with the same work identity can
share even when issued by different branches with different local keys.

The pool is session-local. Configuration seals before execution, and the registry
pins skill/resource bytes. Executor instances must treat configuration as immutable.
Shared executors must derive behavior from the explicit request and that configured
execution environment; origin/caller identity must not secretly select different
models, entitlements or semantics. The supplied agent adapter sends only the explicit
request and skill entry to the model.

Different tasks, inputs, evidence or configuration do not share. Similar wording is
not automatically considered equivalent. A caller's interpretation belongs in its
own task/output; a reusable producer should have a neutral request. In the example,
a and c interpret b differently but both request **Produce snapshot evidence** with
the same projected inputs and empty refs.

Fresh operations never populate or join the shared index. Repeating the exact same
caller/key still replays its original execution: retry identity and sharing scope
are separate concepts. Applications requesting independent review use fresh calls. This is a request
choice, not a reviewer role understood by the pool.

### 3. Atomic acquisition and state resolution

Acquisition reserves `(caller, key)` for the request's identity and reuse policy.
Conflicting requests are rejected even while the first call waits for cleanup.
Once bound, that caller/key remains attached to the selected execution, including
failure. Replaying a cancelled producer raises `Rejected`; cancelling the current
caller still propagates `asyncio.CancelledError`. A cancelled pending acquisition that never selected an execution can be
retried with its reserved, identical request.

For a new call binding using session reuse:

| Matching operation state | Action |
| --- | --- |
| Absent | Admit and create one producer, index it, acquire a lease |
| Running | Acquire another lease and await that task |
| Completed | Return the published receipt and grant its artifact, regardless of domain decision |
| Cancelling | Await cleanup without keeping the dying producer alive; revalidate and resolve again |
| Failed or cancelled | Create a new generation under a new execution ID |

An existing bound caller/key bypasses replacement and replays its selected execution.
Intentional retries after failure need a new key. To rerun a completed negative
decision with identical inputs, use a new key and fresh execution. There is no automatic unbounded
retry loop. Exact-request hits still consume the call budget; new executions also
consume the frame budget.

The shared index points to the latest selected operation object. Completion callbacks
unlink incoming dependencies and report their own operation's state; they do not overwrite the shared index.
A replacement cannot start before the cancelling task finishes, so old cleanup
cannot race a new producer for the same shared request. A newly arriving caller
revalidates access and liveness after waiting for cleanup.

### 4. What locking means here

All pool access occurs on one event loop. The resolve/check/create/index/acquire
sequence has **no await**. Release/remove-edge/decrement/cancel also has **no await**.
Those synchronous regions are the metadata critical sections: two coroutines cannot
interleave halfway through one of them.

There is no mutex held while a model runs, a node awaits children, or cleanup drains.
A waiting parent therefore cannot hold the lock needed by its child. Different
requests for the same skill may execute concurrently; the exclusion unit is exact
opted-in work, not the skill name.

This is an explicit implementation boundary, not a distributed-lock claim. Sharing
this pool across threads, loops, processes or hosts is unsupported. A distributed
backend would require transactional acquisition, lease expiry/recovery and fencing
of producer generations; merely replacing the dictionary with SQLite is insufficient.

### 5. Release, cancellation and shutdown

`run_node` creates a caller-owned waiting task. That task acquires a lease, shields
the producer while awaiting it, and releases its lease in `finally`.

- Success or failure releases that caller's lease.
- Cancelling a caller cancels its wait, not the shared producer directly.
- Cancelling the first creator is no different from cancelling another consumer.
- If another lease remains, the producer continues with its own context and grants.
- If the last lease leaves unfinished work, request producer cancellation and await
  cleanup. Mark it stopping immediately so new shared calls cannot attach as owners.
- Repeated cancellation of a waiting caller does not undo its synchronous release
  or permit a replacement to overlap the draining producer.
- A stopping execution cannot initiate new node work or artifact access. Executor
  cleanup must be cooperative; it cannot start a new investigation while closing.

`Runtime.aclose()` ends the entire session, cancels all remaining caller waits and
producers, and awaits their completion. Liveness checks also prevent a stopping
producer from suppressing cancellation and publishing a final output.
Records already published before cancellation remain immutable session evidence.

The lifetime of a published artifact is separate from its wait leases. No lease is
needed merely to retain or read an immutable published result. The session retains
completed operation results until shutdown; there is no independent TTL policy.
Sharing assumes the explicit inputs describe a stable snapshot. For changed external
state, change the inputs/version or request fresh work.

### 6. The live dependency graph prevents deadlocks

Each lease on unfinished work adds an execution edge `caller → producer`. Multiple
concurrent leases between the same pair are reference-counted. An acquisition waiting for old cleanup
adds an edge without acquiring a lease on the cancelling producer. Last-lease release
removes its dependency edge and closes the producer to new work before draining it.

Before adding an edge:

1. Reject it if the producer can already reach the caller. This includes cycles
   formed by operations initially created under different parallel branches.
2. Check the maximum active dependency depth after the proposed attachment. The
   first creator's lineage is insufficient: joining an existing operation can
   lengthen a different caller's path.

The graph is updated atomically with acquisition/release. Edges disappear when the
lease is released or the producer settles. Receiving a checkpoint or cancelling an
event read does not release its lease. Authored skill links can contain cycles;
live dependencies cannot form a cycle. Fresh recursive execution is bounded by active depth and shared budgets.
A detected cycle is a request error that the caller may handle or propagate.

An open observation is a dependency even before the caller reads an event. The
parent must join or close the handle before completing, and its lease keeps the
producer alive. Ignoring that edge permits ancestor attachment and lets unobserved
recursive opens bypass depth limits. Event reads use the already checked lease;
they do not temporarily create another edge. Edges use reference counts so two
handles between the same pair can be released independently. Completion unlinks
remaining incoming leases; a completed producer cannot prolong an active path.

### 7. Artifact access and publication

Before inspecting any shared index entry, the runtime checks the caller's liveness
and authorization for every input ref. Knowing another branch's hash does not grant
access. Cache hits do not bypass this check. Every successful waiter receives a
separate grant to the returned result; the receipt is copied so one consumer cannot
mutate another consumer's cached receipt.

Grants are not transitive. Sharing b does not automatically grant every artifact
mentioned inside b. Consumers can request compatible shared producers themselves or
receive explicit grants from their caller. A review and its candidate are ordinary
artifacts; fresh reviewer context and pass/fail schemas are application choices.
Published status says nothing about a domain verdict.

Checkpoint publications are bounded by the session-wide `max_checkpoints` budget.
Each publication freezes content and assigns the next operation cursor starting
at 1. Structural/access failures never advance the cursor. There is no implicit
review before publication. Subscribers receive grants when they consume events;
a late subscriber can replay earlier progress in the same session. On terminal
failure the read raises and releases its handle; previous checkpoints remain
independent records. The final-only run path grants no unobserved checkpoints.
A new question and explicit refs can start a separate transformation while the
original producer runs. The host does not assess semantic usefulness.

### 8. Executable evidence

`tests/test_operations.py` forces the relevant interleavings with events/barriers.

| Case | Invariant checked |
| --- | --- |
| a/c converge on running b; d calls later | One producer, two simultaneous consumers, later identical result |
| a skips b | c creates b normally |
| First creator cancels | Remaining consumer finishes; producer is not cancelled |
| Duplicate caller/key awaits; one cancels | Other waiter and retry identity survive |
| Last waiter cancels; replacement arrives | Cleanup finishes before replacement starts |
| Conflicting key during cleanup; repeated caller cancellation | Reservation remains consistent; no lease leak or overlapping generation |
| Executor clears its cancellation flag | Stopping context cannot create work, read procedures or publish |
| Execution failure | Same key replays; a new key permits another execution |
| Negative domain decision | Completed result is reusable; a new key plus fresh requests another execution |
| Different task/input/ref or explicit fresh calls | No unintended sharing |
| Guessed evidence hash | Shared lookup does not bypass grants |
| x/y await each other across branches | Cycle is rejected instead of hanging |
| Joining independently created work makes a deeper chain | Active graph depth, not creation lineage, is enforced |
| Full execution budget and repeated cache hits | Reuse avoids new execution admission; call admission remains bounded |

End-to-end tests use the real interpreter and scripted model to verify the converging
b/f/k/l graph, optional dependencies, fresh audits and failure outcomes. The exported
two prompt/trajectory pairs show observed results, not hypothetical execution traces.
They do not validate live-model reasoning quality or distributed/durable operation.

`tests/test_progress.py` covers two simultaneous subscribers receiving the same
checkpoint, distinct follow-up tasks before final completion, late replay, failed
producers, owner-scoped handles, budgets, publication order and cleanup.

## PTC wrapper audit and contract

The harness supplies `nodes` before every agent eval and code-resource execution.
The implementation is `harness/runners/ptc.js`; both adapters load those exact
bytes. There are no new host tools, skill fields or authorization mechanisms.
The existing `NodeAPI` and runtime continue to own grants, leases, publication and budgets.

### Audit findings and changes

| Finding | Change |
| --- | --- |
| Progress helpers existed only in the scripted fixture | A shared harness prelude supplies the wrapper to both real execution adapters |
| Callers manually passed handle IDs and checkpoint cursors | Operation objects own the cursor and expose receipts |
| Completion loops were duplicated and assumed a checkpoint always exists | One implementation handles zero, one or several checkpoints, and caches terminal results |
| Helpers lacked scoped cleanup after callback exceptions or early return | `nodes.with` closes in `finally`; failure of both callback and cleanup preserves both errors |
| Concurrent reads could consume the same logical stream ambiguously | One pending next/result read per operation; the host independently enforces the same constraint |
| Receipt mutation could change a wrapper's remembered result | Cached receipt is private; each result returns a copy |
| Adapters repeated forwarding functions and tool lists | NodeAPI defines the methods, descriptions and bridge order once; both adapters use that map |
| Demo bounded-read helper checked size after returning the final slice | Size is checked before the final return |

### Default use: scope the observation

```js
const view = await nodes.with(request, async operation => {
  for await (const checkpoint of operation.checkpoints()) {
    const evidence = await tools.readArtifact({ref: checkpoint.ref});
    // Interpret evidence, call another skill, or break when enough is available.
  }
  const result = await operation.result();
  // Inspect the artifact's application-specific decision if your task requires one.
  return result;
});
```

`request` is the existing node/task/inputs/refs/key/reuse contract. The wrapper
neither generates retry keys nor changes sharing policy. `nodes.run(request)` is
the ordinary final-result call; it preserves the existing runNode budget/lifetime
behavior instead of adding unnecessary progress polls.

| Operation method | Behavior |
| --- | --- |
| `next()` | Next published checkpoint receipt, or null when the final receipt is received |
| `checkpoints()` | Async iterator over remaining checkpoint receipts |
| `result()` | Consume remaining events, return final receipt; repeated calls return copies of the remembered receipt |
| `close()` | Release this consumer early; repeat calls are safe. Other consumers keep their own leases |

The wrapper returns published receipts without interpreting artifact content.
A negative application decision is a completed result; producer errors propagate.
Expected `Rejected` errors cross the adapter bridge as a reserved response envelope
and the shared prelude throws a JavaScript `Error` named `Rejected` with its reason.
This includes cancelled-producer replay and access/contract rejection. Direct native
Python API calls still raise `Rejected`; agent-native tools return the envelope.
Other executor exceptions remain subject to the interpreter's generic host-error
transport. They are not failure artifacts or stable domain error schemas. Real
caller cancellation is never converted into a retryable rejection.
Checkpoint publication still uses `tools.publishCheckpoint`; final publication
still uses `tools.submitCandidate`. Grants are supplied by the host, not the wrapper.

Do not run next(), result() or iterator reads concurrently on one operation. Distinct
consumers use distinct operation objects. result() consumes checkpoints that have not
yet been read; it does not retain an unbounded duplicate history in JS memory.
Early close prevents further reads unless the final receipt was already received.

Breaking an iterator leaves the operation available for result(). With `nodes.with`,
leaving the enclosing callback closes it. If the last consumer leaves unfinished
work, the host cancels and drains that producer. This is an explicit consequence
of scope exit, including normal early return.

### Work spanning model turns

An async callback cannot pause to ask the model to author its continuation. For
incremental PTC across eval cells, save an operation from `await nodes.open(request)`
in a REPL variable, read/interpret progress in later cells, and await result() or
close() before submitting. The installed prelude is idempotent and existing operation
objects survive interpreter snapshots. Host frame cleanup releases forgotten handles
after failure/cancellation. `await using` was a proposed syntax, not an implemented
contract, and is not required here.

The JS wrapper is a convenience interface, not a security boundary. Replacing a JS
global or bypassing the wrapper cannot bypass host ownership or evidence checks.
It does not resume state after process crashes or repair lost interpreter snapshots.

### Verification

`tests/test_ptc.py` executes the wrapper through real QuickJS and Deep Agents.
It covers checkpoint iteration, zero checkpoints, repeated/copy-safe results,
overlapping reads, early break, callback failure, producer failure, another live
consumer, opaque domain decisions, automatic injection, and operation state across eval cells.
Both graph trajectories use scoped observations from the harness wrapper. The
scripted fixture retains only application-specific request and interpretation helpers.

The middleware injects the wrapper into eval execution; the model-facing trace
retains the authored code. Full wrapper source is linked here rather than copied
into every trajectory cell. Stable prompt layout and native tool contracts remain
intact; this change does not claim provider KV-cache hits or speedups.

## Limits and failure boundaries

| Boundary | Default or contract |
| --- | --- |
| Runtime deadline | 180 seconds from runtime construction, checked by liveness and execution timeouts |
| Active dependency depth | 5 edges; the external launcher adds no frame edge |
| Session calls / executions | 512 / 64; hits consume calls, only new producers consume frames |
| Model calls / inference parallelism | 256 / 8; inference permits are released before child tool waits |
| Checkpoint publications | 128 per session |
| NodeRequest | 32 KB of encoded finite JSON; unknown fields rejected |
| Candidate | 500 KB of encoded JSON; summary 1–600 characters, content object |
| Skill prose plus description | 24 KB before packet serialization |
| Procedure packet | Up to 32 KB, including JSON encoding, links and resource paths |
| Resource file | Immutable package bytes, at most 1 MB per file |
| Artifact read slice | 4,000 characters by default, at most 16,000 per request |
| CodeRunner | 64 MB QuickJS memory; 5-second execution timeout by default |
| Agent interpreter | Thread mode; 64 PTC calls, 12,000 result characters, 64 MB memory, 4 MB snapshot, 180-second timeout |
| Agent graph | 80 steps by default; the demo chooses a 60-second interpreter timeout and 240-second session |

A call is charged after request/access validation and before pool acquisition.
Consequently a key conflict or dependency rejection can consume a call. This bounds
attempted work; there is no promise that every rejection is free. A closed/expired
owner may still release its own handles. There are no per-request observer timeouts
or token/currency budgets in the public contract. Native callers can time out a wait
with `asyncio.wait_for`; cancellation still follows lease ownership.

Limits count different resources. A checkpoint budget is not a byte-retention budget;
canonical JSON serialization can expand Unicode; arbitrarily large evidence must be
bounded before loading it into the model. Persistent storage needs deployment quotas.

SQLite retains artifact records and events if given a persistent file. It does not
persist operation tasks, retry bindings, open handles, interpreter snapshots, grants
or the session coordinator. A restarted process cannot resume an old operation or
import an old artifact by merely knowing its hash. New root calls cannot inject refs;
an authenticated importer would be a separately designed host capability.

## Records, provenance and authority

A publication freezes candidate content with session, frame, node revision, task,
input refs, executor, consulted procedures, observed refs and `based_on` information.
The hash covers the whole stored record, including execution metadata and timestamp;
it is not a semantic content hash. Two equivalent outputs can therefore have distinct
refs. Store reads verify integrity; runtime reads also check same-session authority.

`input_refs` means available input evidence, `observed_refs` means a recorded artifact
read, and `based_on` means declared output dependence. None alone proves causality,
correctness or complete attribution. A receipt summary may influence a caller without
an artifact read. Trusted native executors can use data outside these recorded paths.
Do not use this metadata as a complete automatic invalidation or credit-assignment
index. The call event graph records consumers separately from the producer's origin.

Python executors, registration, storage access and deployment credentials are trusted
host code. The runtime is not an isolation boundary against a malicious Python plugin.
The JS wrapper is also not an authority boundary: changing it cannot grant a ref or
bypass host admission. Applications must authorize any future external-effect tool at
its own boundary. A published decision artifact is not an effect authorization token.

## Source map and verification

| Source | Responsibility |
| --- | --- |
| `harness/contracts.py` | Strict finite-JSON request, candidate, receipt and context contracts |
| `harness/skills.py` | Minimal frontmatter, pinned package bytes, links and revisions |
| `harness/operations.py` | Sticky calls, shared generations, leases and dependency safety |
| `harness/runtime.py` | Frames, admission, deadlines, grants, publication and cleanup |
| `harness/storage.py` | Immutable hash-addressed records and append-only events |
| `harness/api.py` | One canonical capability inventory |
| `harness/runners/ptc.py`, `ptc.js` | Expected-rejection transport and scoped operation convenience |
| `harness/runners/code.py`, `agent.py`, `metering.py` | Execution adapters and inference metering |
| `examples/review.py` | Application-specific approval and bounded revision |
| `tests/test_adversarial.py` | Unobserved depth/cycles, cancelled replay and catchable JS rejection |
| `tests/test_patterns.py` | Race success, partial admission failure and all-producer failure |

Run `python -m unittest discover -s tests -v`, `ruff check .`, and
`ruff format --check .`. Reproduce both full graphs with
`python -m examples.export_trajectories`. See [review findings](review-findings.md)
for the executed verification record and remaining limits.
