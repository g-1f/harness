# End-to-end design: callable skill graphs

A node is a transformation of explicit inputs and authorized artifacts into an
artifact. It can call other nodes, publish useful progress and return a final
value. A fresh model context is one way to execute it; a deterministic function
or another registered executor follows the same contract. RLM is not required.

The system separates five things that evolve at different rates:

| Thing | Meaning | Owner |
| --- | --- | --- |
| Skill | A named, versioned procedure described in prose | Skill author |
| Request | This caller's task, inputs, evidence and reuse choice | Caller |
| Execution | One running transformation with context, grants and budget | Supervisor |
| Artifact | Immutable output plus provenance | Store and supervisor |
| Composition | Branching, review, approval, repair and downstream decisions | Application or generated PTC |

An authored skill graph is a set of possible references. The execution graph is
formed by actual calls. Artifact dependencies form a third graph through `based_on`.
These graphs need not have the same edges. A link may be inspected without being
called; many callers may join one execution; one artifact can feed several new
transformations. The active wait graph, used for deadlock checks, is transient.

## 1. Author procedures, not workflow metadata

```yaml
---
name: b
description: Produce neutral snapshot evidence for several consumers
---
```

This repo permits exactly `name` and `description` in frontmatter. This is a local
loader convention, not a proposed universal skill schema. `name` matches the
package path under `skills/`. The body contains prose. Optional references/scripts
are pinned package resources. Links, resource paths and revisions are derived.

`[[b]]` refers to canonical skill b. `[[b|capacity evidence]]` resolves to the same
b and retains “capacity evidence” as prose display text. It supplies no task,
arguments, executor, condition or cache key. This local wikilink convention also
strips a `#section` from the target when resolving a skill; the section is not an
execution boundary. Fenced code examples do not add graph edges. Broken targets
and duplicate/unknown frontmatter keys are rejected. Cyclic authored links are legal.

Different expertise belongs in prose. A different model, tool set or backend is
configured in an executor. Neither adds attributes to each node. The immutable
Python `Skill` contains `name`, `description`, `instructions`, `resources`, and
derived `links`/`revision`. The registry pins a whole-graph snapshot.

## 2. Bind execution in the host application

```python
runtime = Runtime(
    Registry.load(ROOT / "skills"),
    Store(),
    bindings={"delta_check": "snapshot_math", "thesis": "reviewed_thesis"},
)
runtime.register_executor("agent", DeepAgentRunner(runtime, model_factory))
runtime.register_executor("snapshot_math", CodeRunner(runtime, "scripts/observe_delta.js"))
runtime.register_executor(
    "reviewed_thesis", ReviewedTransformation(runtime, "thesis_draft", "red_team", max_revisions=1)
)
```

See [`examples/application.py`](../examples/application.py) for the runnable setup.
Bindings map a skill name to an executor registration. Registration seals before
the first call. An executor receives `(frame, {"entry": packet})` and returns a
candidate. Core context has no review attempt, feedback or previous-candidate fields.
The application supplies repair instructions and refs through ordinary requests.

A frame contains its execution ID, creation origin, request, executor name,
consulted procedures, granted/observed refs, child waits, handles and closed flag.
These are execution bookkeeping, not skill attributes or role configuration.
`origin` explains creation; it gives that caller no exclusive ownership of shared work.

Trusted executors must keep configured behavior stable and derive shared work from
the explicit request. Choosing hidden behavior by caller ID defeats exact reuse.
Executors are host code, not a sandbox for untrusted Python.

## 3. Invoke a function through an explicit request

| Field | Contract |
| --- | --- |
| `node` | Canonical skill name |
| `task` | Nonempty task text for this invocation |
| `inputs` | Finite JSON object |
| `refs` | Ordered explicitly authorized evidence refs; default empty |
| `key` | Nonempty idempotency key local to this caller execution |
| `reuse` | `fresh` by default, or explicit `session` |

Requests are bounded to 32 KB and detached from caller-owned mutable objects.
There are no per-request model, reviewer, role or executor overrides.

```js
const snapshot = await nodes.run({
  node: 'b', task: 'Produce snapshot evidence',
  inputs: snapshotInputs, refs: [], key: 'snapshot', reuse: 'session'
});
```

Exact identity includes the pinned skill snapshot, sealed bindings/default executor,
node, task, canonical inputs and ordered refs. Caller/key are separate retry identity.
`fresh` avoids the shared index but still replays the original execution for an
identical caller/key. A genuinely new attempt needs a new key; use `fresh` to avoid
reusing a completed identical request.

| Matching session work | New caller/key behavior |
| --- | --- |
| Absent | Create an execution |
| Running | Join it |
| Completed | Reuse its result, including a negative domain assessment |
| Cancelling | Wait for cleanup, then resolve/create replacement |
| Failed or cancelled | Create another execution |

Repeating a bound caller/key replays its selected execution even after failure.
Changed task, inputs or refs do not match; similar prose is not treated as equivalent.
Input authorization runs before lookup, including cache hits. See
[shared operations](shared-operations.md) for the exact lifetime and race rules.

## 4. Execute and publish

The supervisor checks admission, creates a fresh frame, loads the entry and invokes
its executor. A model executor gets stable procedure and evidence packets followed
by the task; no parent transcript or interpreter state is inherited. The model
writes PTC incrementally. A code executor runs a pinned utility with the same API.

PTC has eight host endpoints, with seven essential effects plus a final-only fast
path. [Native PTC primitives](native-ptc-primitives.md) explains why each remains and
which operations are ordinary JS wrappers. Promise joins, functions and branching
are language features. Review and coherence are node names, not special operations.

Outputs have `summary` (1–600 characters), `content` (a JSON object) and `based_on`
(a list of refs; omitted means empty for native runners). The output limit is
500 KB; large payloads need external blob references. The runtime checks structure,
finite JSON, liveness and evidence access. All child calls must be joined or closed
before final publication. The tool `submitCandidate` stages this return value.
It does not certify correctness or cause a hidden reviewer call.

A published receipt is `{ref, status: "published", summary}`. Successful execution
state is `completed`; other states are `running`, `cancelling`, `failed`, `cancelled`.
The receipt status means availability to authorized consumers. `content.verdict`,
`content.decision` and every other domain field are opaque to the runtime.

Stored artifacts include the output plus session/frame/origin, node/task/executor,
snapshot/node revision, explicit inputs and refs, consulted procedures, observed
refs, publication status and timestamp. `based_on` is a producer's declared evidence;
`observed_refs` records actual reads. Neither implies truth or grants access onward.
Records are content-addressed and immutable. SQLite persists records/events, not
live leases, budgets, retry bindings or interpreters.

## 5. Publish progress and ask another question

```js
await nodes.with(sharedRequest, async operation => {
  const progress = await operation.next();
  if (progress) {
    const capacity = await nodes.run({
      node: 'b', task: 'Assess capacity from snapshot checkpoint',
      inputs: snapshotInputs, refs: [progress.ref], key: 'capacity', reuse: 'fresh'
    });
    // Read capacity and interpret it for this caller's task.
  }
  const final = await operation.result();
  // Read and use the final artifact if it is relevant.
});
```

The producer explicitly calls `publishCheckpoint`. Each checkpoint is validated,
immutable and immediately available to subscribers. Publication runs no implicit
reviews. A domain that needs checked progress composes a checker before announcing
its decision. Raw progress must not be interpreted as approval.

Each subscriber has its own cursor and lease. Late subscribers can replay from
zero, including after completion or failure. A failed producer does not retract
previously published evidence. Cursors describe publication order, not source
freshness. A checkpoint can be useful even when the final artifact is insufficient.

An unusable artifact does not trigger an automatic rerun. The caller/model chooses
whether to reinterpret it, obtain more explicit evidence, ask the same skill a
different question, invoke another skill, or stop. An application can implement
that choice deterministically. The host supplies identity, access and lifetime.

## 6. Compose approval explicitly

[`examples/review.py`](../examples/review.py) binds thesis to ordinary function
composition: `thesis_draft(inputs)` followed by `red_team(candidate)` in fresh context.
The checker receives the exact candidate and original granted evidence. Nested
refs mentioned inside the candidate remain ungranted unless explicitly supplied.

This example approves only a matching `candidate_ref`, `verdict: "pass"` and empty
`findings`. Missing, stale, failing or inconclusive reviews block. At most one repair
is configured for the thesis example. Each revision is a new producer call with
explicit prior-output and feedback refs, followed by a fresh review of the new output.
Review execution errors and exhausted host budgets fail the composition.

The composition publishes a decision artifact: `decision`, `candidate_ref`,
`reviews`, `attempts`, `history`, and `result`. Approval includes the candidate's
content in result; a blocked decision has result null. Both decisions are published
artifacts. The root example reads the decision before reporting completion.

This is an application protocol, not a general approval authority. Raw drafts remain
available to callers with grants, and the supervisor does not prevent an application
from using them. A product needing enforced release must consume the trusted
composition's approval output at its release boundary. Fresh contexts remove
inherited conversation, not correlated model bias or the need to inspect findings.

The actual QuickJS test `test_nested_ptc_transformations` also exercises
`review(a)`, `red_team(a)` and `node_a(coherence(c, d, e))` with ordinary artifacts.

## 7. Follow an actual converging graph

Root calls a and c; both can ask b for identical neutral evidence. A late d call
reuses b. C can ask b a different question using its checkpoint while neutral b is
still running. D and g converge on f; b/f/g/h also share lower-level k/l/delta work.
Each caller produces its own interpretation. Fresh audits and the thesis composition
complete the graph. The examples contain conditional edges as well as convergence.

| Scenario | Prompt and captured PTC |
| --- | --- |
| Parallel a/c; progress consumed while b runs | [Prompt A](../examples/prompts/scenario_a.md), [trajectory A](../examples/trajectories/scenario_a.md) |
| Baseline a first; c replays b after completion | [Prompt B](../examples/prompts/scenario_b.md), [trajectory B](../examples/trajectories/scenario_b.md) |

These traces run actual Deep Agents, QuickJS and the supervisor with a scripted
model. The PTC fragments are prewritten test fixtures selected by observed outputs;
they are not evidence of live-model code generation. Skills remain prose, apart
from the explicit deterministic arithmetic resource.

## 8. Verify and extend

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python -m examples.export_trajectories
```

Tests cover converging graphs, optional branches, running/completed/failed work,
lease cancellation, cleanup before replacement, cycles and depth, grants, immutable
progress, wrapper lifecycle, application approval/repair and stable prompt layout.
The [edge-case and KV discussion](edge-cases-and-kv-cache.md) distinguishes verified
local behavior from future durable operation and provider caching work.

To add expertise, author a linked skill. To change execution, register an executor.
To change approval, modify a composition. Add a native capability only for a new
host-owned effect that existing calls, artifacts and ordinary code cannot express.
