# Execution and collaboration — v4 contract

**Status: proposed, unimplemented.** This file narrows [the overview](README.md) into executable behavior. It intentionally retains the six model-facing operations of v3. A task is *not* always a subagent and a citable artifact is *not* always an execution.

## 1. Identifiers and identities

| Name | Identity | Mutation |
|---|---|---|
| `run_id` | One authority and event-log boundary | Stable |
| `task_id` | Logical question, expected outputs and domain; may survive revisions | Stable |
| `work_key` | SHA-256 of canonical work request + world snapshot + source-vintage policy + pinned executor/model/skills + permission domain | Immutable |
| `execution_id` | An admitted producer execution | New for each independent attempt |
| `attempt_id` | Concrete process attempt; distinct from transport retry identity | New for failed/restarted attempt |
| `session_id` | Model context/trajectory associated with a worker; can perform multiple tasks or emit several artifacts | Stable across eligible resumes |
| `handle_id` | Caller-owned hold on an execution | Unique to caller/acquisition |
| `entry_ref` | Immutable model/PTC/host trajectory record | Immutable |
| `artifact_ref` | Exact immutable version and digest | Immutable |
| `branch_id` | Trajectory or evidence-world continuation | Stable; head moves by CAS |
| `decision_id` | Stable logical question/action whose belief and validation history evolve | Stable |

Two different tasks can use the same evidence artifact; one execution can publish multiple artifacts; multiple holders may attach to one running execution.

Canonicalization must specify Unicode normalization, JSON number handling, map-key ordering, input-size bounds and reference ordering. A stable `work_key` is *not* permission to share. Authorization must be checked independently on every join/reuse.

## 2. Core effects and state machine

`openNode({request})` accepts:
- `task` required; `node` optional skill/procedure; `inputs` structured inputs; `refs` ordered explicit evidence;
- `from`: optional immutable `{trailRef, entryRef, worldRef}` fork snapshot;
- `key`: optional intentional independent identity; default exact reuse within a compatible world/scope;
- `worldRef`: explicit source-vintage/availability policy snapshot (may be inherited from run);
- authenticated principal and trusted execution config come from the host, not user-provided JSON.

Return: `{node, handle, disp: "started"|"joined"|"reused", currentResultRef?}`. Repeating the same transport request with the same idempotency key returns the same admitted handle/result; a deliberate `key` forces separate work. A new fork always has a new execution lineage even when sharing a historical prefix.

Producer states: `admitting -> running -> {completed, failed, cancelling}`; `cancelling -> {cancelled, failed}`. `completed` has an immutable result ref. A reopened node enters a **new revision execution** anchored to a previous result, without mutating the previous execution or result. All transitions generate committed events.

A producer with N holders must not be cancelled when 1 of N holders releases. The last holder release initiates cancellation, drains its effects, then makes a replacement eligible. A failed or cancelled producer is not silently joined; an identical request may create another attempt. Detect wait cycles and depth against *all* live handles, including unobserved handles and cancelled-but-not-drained work. The host cannot let a node finalize while it holds unfinished children.

`readNode({node})`: returns pinned procedure prose/resources and records a consultation edge. A missing skill is not fatal to skill-free tasks; a skill revision only invalidates tasks that actually consulted the old procedure.

`readArtifact({ref,offset,limit})`: returns a bounded slice from one immutable content version or a specified immutable snapshot of a virtual view. It records the read and its scope. A bare `n7` is a view of node identity/current state; `n7.r1` is immutable. Do not substitute latest revision for a pinned version.

`publishCheckpoint({content,to?})`: commits artifact payload, validated refs, causal links and event atomically. Directed publication sends an **information message**. A target's ability to read a ref remains separately permission-checked. No message can independently grant a sender power to cancel, reopen, approve, override or spend on behalf of a receiver.

`nextNodeEvent({after,filter?})`: yields authorized event-line projections after a durable cursor; may wait if none eligible. The globally committed journal is never copied per agent. Held-work completion and authorized addressed events are highlighted. Delivered notification != consumption: a node may inspect the original payload with `readArtifact` when it chooses. Cursor acknowledgement is durable. If the process fails after delivery but before acknowledgement, redelivery is allowed and consumers must be idempotent.

`closeNode({handle})`: releases a single hold exactly once and records the release. Releasing one hold never revokes rights that other independent holders possess.

**Final publication:** the committed final agent message becomes the next immutable result version. A partial checkpoint cannot masquerade as a final, validated result.

## 3. PTC wrapper; no new native effects

```ts
// Illustrative wrapper signatures; not yet implemented.
await nodes.run({task, node?, refs?, inputs?, worldRef?});
await nodes.with(request, async op => { await op.next(); return op.result(); });
const op = await nodes.open(request); // asynchronous handle
await nodes.fork({from: {trailRef, entryRef, worldRef}, task});
await nodes.converge({task: "Reconcile evidence", refs: [bullRef, bearRef]});
await nodes.inspect({trailRef, fromEntry?, limit?});
await nodes.next({after: cursor});
```

A wrapper may preserve `try/finally` lease release, compose `Promise.all`, await specific child events or select from a common stream. Host authorization must not depend on wrapper correctness.

**Code mode:** typed tool SDK calls remain permission-checked in the same dispatcher as normal tools. Bounded program output is passed to the LLM; full committed requests/results are retained as evidence artifacts. A prompt-prefix/cache hit is an optimization, never an execution assumption.

## 4. Graph patterns: semantics and limits

- **Fan-out:** caller opens orthogonal tasks concurrently; tasks can use skill prose or none.
- **Join/shared trunk:** two consumers with equivalent work requests and compatible snapshots attach to one in-flight producer; both keep independent holds; neither inherits the other's private context.
- **Publish/consume:** an early immutable checkpoint can feed downstream work without waiting for final result; downstream must record whether it consumed provisional evidence.
- **Steer:** sender publishes an addressed message. Host verifies sender's right to request intervention; receiver may consider the message at a safe turn boundary. Unauthorized peer notes can be observed as evidence but cannot trigger forced recomputation.
- **Fork:** new trajectory from immutable entry; preserve source session model-visible prefix and world manifest, but permit a fork from evidence-only context for independence.
- **Settle:** peers exchange reasoned checkpoints citing their own evidence. They may agree or preserve disagreement. A bounded per-run resource cap prevents infinite debate.
- **Converge:** start a new reconciliation task consuming explicit branch result refs; publish a new artifact with both source links. The parent branch heads do not change unless a separate authorized atomic head update succeeds.
- **Race:** whichever candidate satisfies caller-defined criteria first may be used; losers still release handles safely and committed records remain auditable.
- **Optional workflow:** `readNode` discovers authored links and `openNode` invokes linked procedures. An authored graph is neither mandatory nor the actual execution graph.

### Three different convergences

1. *Computational:* identical live work joins an execution.
2. *Epistemic:* independent positions are compared; a reconciliation artifact cites both and can preserve conflict.
3. *State:* an authorized `commitHead(branch, expectedHead, newHead)` host-internal transaction chooses an accepted research state. This is an internal storage operation, not a seventh model-facing tool. On conflict the candidate remains but the branch head does not move.

Never auto-merge model histories; opposing scenarios can have contradictory worlds and need an explicit new reconciliation task.

## 5. Scheduling and parallelism

The goal is useful, verified research within a deadline, not raw agent count. Scheduling is work-conserving with:
- bounded concurrent models, tool calls, dollars, tokens and depth;
- nonblocking `openNode`, child checkpoints and event waits;
- root responsiveness: it can continue PTC/synthesis or suspend while workers operate;
- fairness and backpressure on event deliveries; priorities are advisory and cannot override authority;
- per-run metrics: critical path, queue delay, idle/model time, checkpoint-to-consumer latency, duplicate execution avoided, context pollution and token expenditure.

The root may retain final thesis decision authority while sibling nodes collaborate directly. No mandatory reviewer roles or fixed depth-specific workflow.

## 6. Independence and failures

Shared evidence is encouraged, but independent evaluations must use a separate work key and, where appropriate, an evidence-only fork (not another agent's reasoning prefix). A join must not accidentally turn an independent adversarial check into the same execution.

On process restart, reconstruct state and durable holds from committed events/checkpoints. A half-completed PTC cell is retried from a safe boundary using a tool-effect ledger. External effects need adapter-specific idempotency or reconciliation; the host **does not promise exactly-once external effects**. See [storage](storage.md).

## 7. Required conformance tests

- Same request/snapshot/scope: one producer; two leases; intermediate checkpoint delivered; one consumer closing does not cancel shared producer.
- Different vintage or permission domain: no reuse; no cross-scope data reads via refs or peer messages.
- Same logical task + independent key: distinct execution and reasoning state.
- Fork from immutable entry and world: deterministic ancestry regardless of later parent updates.
- Concurrent convergence head commits: exactly one expected-head CAS succeeds; both candidate artifacts survive.
- Deadlock/cycle detection including unobserved handles, cancelled drainage and nested awaits.
- Crash just before/after event ack: redelivery without duplicate material effect.
- Root continues while children work; no synchronous barrier introduced by runtime.
- Skill-free and skill-graph cases exercise the same host implementation.
