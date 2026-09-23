# PTC wrapper audit and contract

The harness supplies `nodes` before every agent eval and code-resource execution.
The implementation is `harness/runners/ptc.js`; both adapters load those exact
bytes. There are no new host tools, skill fields or authorization mechanisms.
The existing `NodeAPI` and runtime continue to own grants, review, leases and budgets.

## Audit findings and changes

| Finding | Change |
| --- | --- |
| Progress helpers existed only in the scripted fixture | A shared harness prelude supplies the wrapper to both real execution adapters |
| Callers manually passed handle IDs and checkpoint cursors | Operation objects own the cursor and expose receipts |
| Completion loops were duplicated and assumed a checkpoint always exists | One implementation handles zero, one or several checkpoints, and caches terminal results |
| Helpers lacked scoped cleanup after callback exceptions or early return | `nodes.with` closes in `finally`; failure of both callback and cleanup preserves both errors |
| Concurrent reads could consume the same logical stream ambiguously | One pending next/result read per operation; the host independently enforces the same constraint |
| Receipt mutation could change a wrapper's remembered result | Cached receipt is private; each result returns a copy |
| CodeRunner repeated eight forwarding functions and a second tool-name list | One capability map and one argument-binding helper register native bridges and construct `tools` |
| Demo bounded-read helper checked size after returning the final slice | Size is checked before the final return |

## Default use: scope the observation

```js
const view = await nodes.with(request, async operation => {
  for await (const checkpoint of operation.checkpoints()) {
    const evidence = await tools.readArtifact({ref: checkpoint.ref});
    // Interpret evidence, call another skill, or break when enough is available.
  }
  const result = await operation.result();
  if (result.status !== 'accepted') throw new Error('Publication needs review');
  return result;
});
```

`request` is the existing node/task/inputs/refs/key/reuse contract. The wrapper
neither generates retry keys nor changes sharing policy. `nodes.run(request)` is
the ordinary final-result call; it preserves the existing runNode budget/lifetime
behavior instead of adding unnecessary progress polls.

| Operation method | Behavior |
| --- | --- |
| `next()` | Next accepted checkpoint receipt, or null when the final receipt is received |
| `checkpoints()` | Async iterator over remaining checkpoint receipts |
| `result()` | Consume remaining events, return final receipt; repeated calls return copies of the remembered receipt |
| `close()` | Release this consumer early; repeat calls are safe. Other consumers keep their own leases |

The wrapper never turns `needs_review` into `accepted`. Producer errors propagate.
The native QuickJS bridge presents Python exceptions inside JS as a generic
HostError; an uncaught error is restored to the original exception at the Python
boundary. JS callers must not rely on seeing the producer's Python exception text.
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

## Work spanning model turns

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

## Verification

`tests/test_ptc.py` executes the wrapper through real QuickJS and Deep Agents.
It covers checkpoint iteration, zero checkpoints, repeated/copy-safe results,
overlapping reads, early break, callback failure, producer failure, another live
consumer, needs_review, automatic injection, and operation state across eval cells.
Both graph trajectories use scoped observations from the harness wrapper. The
scripted fixture retains only application-specific request and interpretation helpers.

The middleware injects the wrapper into eval execution; the model-facing trace
retains the authored code. Full wrapper source is linked here rather than copied
into every trajectory cell. Stable prompt layout and native tool contracts remain
intact; this change does not claim provider KV-cache hits or speedups.
