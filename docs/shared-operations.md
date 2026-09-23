# Shared node operations: identity, ownership and lifecycle

Status: implemented single-session, single-event-loop coordination. The
[parallel trajectory](../examples/trajectories/scenario_a.md) records the actual
converging execution graph, not an unrolled creation tree.

## 1. Four things that must not be conflated

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

## 2. Exact shared-work identity

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

## 3. Atomic acquisition and state resolution

Acquisition reserves `(caller, key)` for the request's identity and reuse policy.
Conflicting requests are rejected even while the first call waits for cleanup.
Once bound, that caller/key remains attached to the selected execution, including
failure. A cancelled pending acquisition that never selected an execution can be
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
only report their own operation's state; they do not overwrite the shared index.
A replacement cannot start before the cancelling task finishes, so old cleanup
cannot race a new producer for the same shared request. A newly arriving caller
revalidates access and liveness after waiting for cleanup.

## 4. What locking means here

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

## 5. Release, cancellation and shutdown

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

The lifetime of an published artifact is separate from its wait leases. No lease is
needed merely to retain or read an immutable published result. The session retains
completed operation results until shutdown; there is no independent TTL policy.
Sharing assumes the explicit inputs describe a stable snapshot. For changed external
state, change the inputs/version or request fresh work.

## 6. The active wait graph prevents deadlocks

Each wait adds an execution edge `caller → producer`. Multiple concurrent waits
between the same pair are reference-counted. An acquisition waiting for old cleanup
adds an edge without acquiring a lease on the cancelling producer. Last-lease release
removes its dependency edge and closes the producer to new work before draining it.

Before adding an edge:

1. Reject it if the producer can already reach the caller. This includes cycles
   formed by operations initially created under different parallel branches.
2. Check the maximum active dependency depth after the proposed attachment. The
   first creator's lineage is insufficient: joining an existing operation can
   lengthen a different caller's path.

The graph is updated atomically with acquisition/release. Edges disappear when their
wait ends. Authored skill links can contain cycles; active waits cannot deadlock in
a cycle. Fresh recursive execution is bounded by active depth and shared budgets.
A detected cycle is a request error that the caller may handle or propagate.

An open observation holds a lease but adds **no active wait edge** until its caller
actually awaits a new event. Each pending `next_node_event` temporarily adds an edge
and checks cycle/depth bounds. A returned checkpoint removes the edge while the
lease persists. This distinguishes a live subscriber from a blocked caller.

## 7. Artifact access and publication

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

## 8. Executable evidence

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
