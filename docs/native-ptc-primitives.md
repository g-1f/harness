# Native PTC boundary: what earns its keep

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
| `nextNodeEvent({handle, after})` | Await/replay an ordered checkpoint or terminal result; grant delivered refs | The host owns event order, wait-cycle checks, liveness, handle ownership and artifact authority |
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

## Derived operations stay in code

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

## Composition example

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

## Adapter and wrapper cleanup

[`NodeAPI.capabilities`](../harness/api.py) is the single list of bridge names,
method order and descriptions. Deep Agents builds its native tools from those
bound methods; CodeRunner registers the same methods in QuickJS. Both install
[`ptc.js`](../harness/runners/ptc.js). The wrapper owns only local cursor/cache/scope
state and cannot bypass host checks.

Deep Agents also exposes its framework `task` compatibility route. This adapter
replaces the framework's default worker with a dispatcher into `NodeRequest` and
the same supervisor. It is not another node primitive or an unsupervised agent pool.
Private scratch tools supplied by the framework are not artifact publication APIs.

Removed in this cleanup: the core `ReviewPolicy`, automatic review/repair lifecycle,
review-specific context fields and artifact metadata, `accepted`/`needs_review`
receipt states, and `readNode`'s obligation-activation flag. Application review
schemas now live only in the example composition, its skill prose and tests.

## Migration from the previous contract

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
