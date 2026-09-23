# Callable skill graph: contracts and end-to-end execution

Status: implemented local reference, with the design choices below made explicit.
The objective is to let the harness turn reusable prose into executable work,
including nested transformations and fresh reviews. RLM is not the primitive.

## 1. Start with the distinctions

A **skill** is a reusable procedure: authored prose, a short description, references
to other procedures, and optional resource files. A **node address** is a skill name
that the application can execute. A **call** is one caller's request. An **operation**
owns an execution and its result; multiple calls may share it. A **wait lease** keeps
unfinished work alive for one awaiting caller. An **executor** supplies the execution
mechanism. A **publication policy** determines required checks.

Conceptually:

```text
run_node(node, task, inputs, evidence_refs, caller_key, reuse) -> await receipt
receipt.ref -> immutable result artifact
```

This resembles function application but is not a pure function. Executions consume
budgets, create artifacts, may call a nondeterministic model and can fail or be
cancelled. Identical inputs are not a promise of equivalent independently generated
results. Session reuse explicitly asks to share one result. The caller key identifies
a request/retry; it does not identify equivalent work across callers.

Three graphs have different meanings:

| Graph | Vertices and edges | Meaning |
| --- | --- | --- |
| Authored skill graph | Skill IDs, linked by prose references | Procedures that may be useful together; cycles are allowed |
| Execution graph | Execution IDs, linked by actual calls | Several branches can join one running producer or reuse its completed result |
| Artifact evidence graph | Immutable records, linked by declared or observed references | What a result declares or reads; sharing is explicit |

The active wait graph is the unfinished subset of the execution dependencies. It
must remain acyclic even though authored links can contain cycles. A creation tree
cannot represent all consumers or determine shared-work cancellation ownership.

There is no YAML workflow graph to compile. In live mode, the agent running inside
the harness reads the prose and observations and writes the next PTC fragment.
The supervisor enforces mechanics without interpreting phrases like “accelerating
demand.” Ordinary JavaScript implements branches, joins and transformations.

## 2. Authored frontmatter: a deliberately small local convention

```yaml
---
name: c
description: Interpret capacity evidence for the caller's specific question
---
```

Only these two fields are accepted in this repository. This is an implementation
choice for the example, not a universal skill format or a compatibility claim for
other skill systems. Unknown, duplicate, missing or malformed fields fail loading;
the runtime must not silently invent their meaning.

| Authored element | Contract | Reason |
| --- | --- | --- |
| `name` | Nonempty lowercase canonical package path, e.g. `c` or `research/c`; must match its directory | Stable lookup identity; no competing path/name namespaces |
| `description` | Nonempty string | States what the procedure is for; included in the entry packet |
| Markdown body | Nonempty prose, preserved as instructions | Describes expertise, questions, use of links and expected application output |
| Resource files | Optional relative files owned by the package | Versioned utility code or data; not an executor declaration |

Names permit lowercase letters, digits, underscores and hyphens, separated by `/`.
Instructions plus description are bounded to 24 KB. Each resource is bounded to
1 MB. These are local admission limits, not claims about an ideal universal format.
Symlinks are rejected. A nested skill owns its resources independently of its parent.

Wikilinks such as `[[c|capacity analysis]]` resolve to canonical skill IDs. Display
labels and anchors do not create new nodes. Links inside fenced code examples are
ignored. The registry validates referenced skills at load time. A link never runs
its target, grants artifact access or authorizes a backend.

The in-memory `Skill` has exactly these fields:

| Field | Origin | Meaning |
| --- | --- | --- |
| `name` | Frontmatter | Canonical ID |
| `description` | Frontmatter | Purpose |
| `instructions` | Markdown body | Procedure prose |
| `resources` | Package files | Immutable tuple of `Resource(path, data)`; `data` is bytes |
| `links` | Derived from prose | Deduplicated canonical linked IDs |
| `revision` | Derived hash | Identity of name, description, instructions and resource bytes |

The registry snapshot hashes all skill revisions. Loading pins resource bytes; later
filesystem edits cannot silently change an already loaded executor's resource.
The entry packet exposes resource paths; resource consumption is currently a host
executor capability. A generic agent resource-reading tool is not implemented.

## 3. Executors and policies belong to the application

There is no `kind`, `critic`, `model`, `tools`, `profile`, `ttl_seconds`, `code` or
`review` field on `Skill`. There is no unvalidated `metadata` dictionary that merely
hides the same problem.

The implemented application wiring is:

```python
runtime = Runtime(
    Registry.load(ROOT / "skills"),
    Store(),
    bindings={"delta_check": "snapshot_math"},
    reviews={"thesis": ReviewPolicy(("red_team",))},
)
runtime.register_executor("agent", DeepAgentRunner(runtime, model_factory))
runtime.register_executor("snapshot_math", CodeRunner(runtime, "scripts/observe_delta.js"))
```

`agent` is the default executor. `bindings` maps existing skill names to registered
executor names. An executor is an async callable accepting `(frame, context)` and
returning a candidate. The runtime dispatches through that interface; it has no
agent-vs-code conditional. Configuration seals at first execution. Requests cannot
select a model, backend or policy override.

| Extension | Where it belongs | Changes to Skill fields |
| --- | --- | --- |
| Different expertise or review question | New prose skill, or a different call task | None |
| Different model or system prompt | Another configured `DeepAgentRunner`, bound by the application | None |
| Different tool capabilities or execution mechanism | Another host executor implementation/configuration | None |
| Mandatory check before publishing an output | `reviews[skill_name] = ReviewPolicy(...)` | None |
| New stable concept shared by all skills | Explicit contract proposal and migration after discussion | Deliberate schema change only if justified |

The bundled agent adapter exposes eight application capabilities. Arbitrary
per-agent tool allowlists are not a YAML feature; an application needing them must
configure or implement a suitable executor. The `instructions` constructor argument
allows a separately configured system prompt.

A `ReviewPolicy` has `reviewers: tuple[str, ...]` and `max_revisions: int = 0`.
These are host publication rules, not authored node attributes. Reviewers name
ordinary skills. A reviewer may itself have a required review if the policy graph
is acyclic; there is no privileged “critic” type. Inline procedure entry also adopts
that procedure's requirements. The global revision bound caps local repair policies.

The shared supervisor owns call-count, execution-count, model-operation, active
dependency depth, deadline and repair bounds. They apply to all executors. Cache
hits consume calls without admitting new executions. Model operations are metered
during inference; a caller waiting for dependencies does not hold an inference permit.

## 4. Calls, sharing and execution context

| `NodeRequest` field | Meaning |
| --- | --- |
| `node` | Registered skill name |
| `task` | Nonempty prose question for this work; part of shared identity |
| `inputs` | JSON object explicitly selected by the caller |
| `refs` | Ordered artifact references to grant; defaults to empty |
| `key` | Nonempty retry key scoped to the caller execution, or launcher scope for roots |
| `reuse` | `"fresh"` by default; `"session"` opts into identical work within this session |

The request is finite JSON, capped at 32 KB. There are no agent-specific fields.
Parsing copies nested input data before admission. The same caller/key reserves
one exact node/task/inputs/refs/reuse request and, once bound, its execution. A
conflicting request is rejected. Retrying a bound key replays that execution even
if it failed or was cancelled; an intentional new attempt needs a new key.

Session sharing uses exact node/task/inputs/ordered-refs plus the pinned skill
snapshot and sealed execution configuration. Caller IDs and keys are excluded.
The runtime starts absent work, joins running work, and reuses accepted work.
Failed, cancelled or `needs_review` work can be replaced under a new caller/key.
A cancelling execution must finish cleanup before its replacement can start.
Different prose questions remain different requests; the runtime does not guess
semantic equivalence. Fresh calls do not use the shared index.

Each waiting call owns a separate lease. An open observation owns a lease until
terminal event, explicit close or frame cleanup. The last lease leaving unfinished work
requests cancellation; another active consumer keeps it alive. Metadata acquisition
and release are synchronous critical sections on one event loop. No mutex is held
while executing, joining or draining work. Active dependency edges are checked for
cycles and depth at attachment time. The detailed state transitions, identity rules
and race tests are in [Shared node operations](shared-operations.md).

The host creates `Frame` state: ID, creation origin, request, selected executor,
entered procedures, artifact grants, owned call-wait tasks, observed reads and closed
state. `origin` records who first requested the execution; it does not own the shared
producer or determine its active dependencies. None of this belongs in frontmatter.
The adapter receives a `RunContext` containing:

| Field | Meaning |
| --- | --- |
| `entry` | Current skill packet: node, description, revision, text, links, resource paths |
| `attempt` | Zero-based execution/repair attempt |
| `feedback` | Failed review outcomes from the preceding attempt |
| `previous` | Previous immutable candidate ref, or null |

Each newly executed agent attempt builds a fresh agent and QuickJS interpreter. Caller messages,
globals and interpreter snapshots are not inherited. The child receives its own
entry, task, inputs and explicitly granted refs. “Fresh” does not mean ignorant of
all prior information: the caller can intentionally include prior evidence in its
inputs and grants.

Joining or reusing an operation does not create another context. Use a fresh call
and a new key when an independently executed review or interpretation is required.
Every required reviewer is fresh by host policy.

All frames use the same artifact access rule: own outputs and explicit grants only.
A successful call grants its result to that caller, including joins and cache hits.
Input refs are authorized before shared lookup. Granting a record does not grant
every reference mentioned inside it. There is no ambient artifact discovery,
cross-session reuse or automatic TTL. Reviewers use the same mechanism; the host
grants a required reviewer the exact candidate and its declared supporting refs.

## 5. Eight capabilities, one publication protocol

| Capability | Effect |
| --- | --- |
| `read_node(node, enter=False)` | Inspect prose and links; `enter=True` activates inline procedure obligations |
| `run_node(request)` | Acquire fresh or explicitly shared work; await a compact receipt |
| `read_artifact(ref, offset, limit)` | Read an authorized immutable record in bounded slices |
| `submit_candidate(summary, content, based_on)` | Stage a candidate; the host controls publication status |
| `open_node(request)` | Acquire a caller-owned observation handle, returning it without final completion |
| `next_node_event(handle, after)` | Replay or await the next accepted checkpoint or terminal result after a cursor |
| `close_node(handle)` | Release a handle early; idempotent for its owner |
| `publish_checkpoint(summary, content, based_on)` | Freeze and review an intermediate artifact independently |

PTC exposes camelCase equivalents on `tools`. Native calls use the same bound
`NodeAPI`. The framework's compatibility `task` route dispatches into the same
supervisor. No unsupervised application child is provided through that route.

A candidate has a nonempty summary of at most 600 characters, a JSON object
`content`, and `based_on` artifact refs. It is limited to 500 KB. These are the same
contracts for model and code executors. Application-specific shapes such as evidence
observations or coherence assessments live inside `content`, not on `Skill`.

Execution proceeds as follows:

1. Validate request, refs and executor registration; admit a call and resolve its key.
2. Acquire a lease on an existing execution, or admit a new frame and enter its
   primary procedure. Existing work follows its own remaining lifecycle below.
3. Run the configured executor. The agent may inspect links, call children, observe
   artifacts and write additional code. Child handles must be joined or closed before returning.
4. Validate and freeze the candidate as an immutable draft.
5. Run every required reviewer in fresh context, granting the exact draft first and
   its declared evidence next. Reviews for the candidate can execute concurrently.
6. Accept only when every required reviewer returns an accepted artifact whose
   content has that exact `candidate_ref`, `verdict: "pass"` and empty `findings`.
7. If allowed, create a fresh repair attempt with feedback. A changed candidate
   receives new reviews; prior verdicts cannot certify it. Otherwise return
   `needs_review`. Close the frame and release any outstanding calls it owns.
8. Return the receipt and grant the result to each successful waiting caller.
   Release each call's lease. Accepted results remain available for exact session
   reuse without a live lease. `Runtime.aclose()` drains the whole session.

Optional reviews are ordinary calls made by the agent. Their result must be read:
`receipt.status == "accepted"` does **not** imply `content.verdict == "pass"`.
The host enforces only configured mandatory reviews. The fixture's choice to stop
on a failed optional audit is behavior of the example procedure.

A receipt has `ref`, `status` (`accepted` or `needs_review`) and `summary`.
Operational errors raise; failure/cancellation events record their category.
The stored record contains the candidate plus session/frame/origin IDs, skill and
executor identity, task and inputs, registry snapshot and skill revision, entered
procedures, input refs, observed refs, review refs, publication status and time.
`observed_refs` records actual reads; `based_on` is the worker's declared lineage.
Neither proves that every semantic dependency was declared or understood.

A checkpoint uses the same candidate shape and evidence validation as a final
artifact. Its accepted receipt is appended to the operation's ordered progress
stream. A subscriber receives it by cursor and gains its ref; a late joiner can
replay from cursor zero even after final completion. Failed checkpoint reviews
produce `needs_review` for the producer, with no subscriber publication. The
final result and each checkpoint have separate frozen drafts and mandatory reviews.
Open handles retain the producer but create wait edges only while awaiting an event.
The ledger bounds publication attempts with `max_checkpoints=128` by default.
Checkpoint records can remain accepted if the producer later fails. The host
validates evidence access and review policy, not semantic fitness for every consumer.

## 6. End-to-end converging example

The [README graph](../README.md#an-actual-converging-graph) has eight composite
investigation procedures: root/a/b/c/d/f/g/h. Multiple branches use the same existing
producers, with distinct prose explaining how each caller should interpret them.

| Consumers | Shared producer | Distinct use of the same artifact |
| --- | --- | --- |
| a, c, later d | b: neutral snapshot evidence | Baseline assumptions, capacity interpretation, supply cross-check |
| d, g | f: supplier alternatives | Supply risk versus inventory protection |
| b, f | k: volume evidence | Snapshot explanation versus supplier lead-time interpretation |
| b, f, g, h | l: mix evidence | Snapshot, alternatives, inventory and policy questions |
| b, f, g, h | delta_check: arithmetic result | The common measured snapshot difference |

The standard producer task is stated in prose. A caller projects stable snapshot
inputs and supplies the same evidence refs, then interprets the returned artifact
inside its own fresh execution. The shared producer is not asked contradictory
caller-specific questions. For example, f receives the exact b artifact from both
d and g; k and l receive the exact delta artifact in each branch.

Scenario A starts a and c concurrently. Both request b, so the second arrival joins
the running execution. Both consume its accepted checkpoint before the neutral b
result finishes. C asks b a different capacity-specific question in a fresh
execution grounded in that checkpoint. D later reuses neutral b. D and g converge
on f, whose nested k/l results already exist. The recorded run has 26 calls and
18 executions, with two running joins and six completed reuses. One execution of
each neutral shared producer supports multiple consumer results; the focused b call
is intentionally separate.

Scenario B runs a before c to exercise completed b reuse and checkpoint replay.
C's capacity-focused b call starts after the neutral b has completed. Its stable-demand result
leads into h, which reuses l and conditionally calls i. The `deferred` fixture lets a
omit b so c creates it. `skip-c` omits c's request. With unchanged snapshots, b omits
k/l but h can later create l when its own procedure needs it.

The [two task prompts](../examples/prompts/) are inputs used by `demo.py`. The
[Scenario A](../examples/trajectories/scenario_a.md) and
[Scenario B](../examples/trajectories/scenario_b.md) trajectories are exported from
actual offline runs, with IDs relabeled and repeated prelude omitted. Each includes
all execution tasks, explicit grants, every caller-to-operation edge and dispatch
disposition, captured PTC, observed outputs and final result. IDs identify executions,
so a join does not duplicate the producer's vertex or transcript.

In live mode the model writes code from these instructions and observations. Offline
mode uses a clearly named scripted model that recognizes fixture observations and
selects prewritten fragments. It checks execution mechanics and expected paths; it
cannot establish whether a real model interprets arbitrary prose correctly.

The optional delta resource performs stable arithmetic without a model. Its code is
written by the utility author; orchestration code is written by the executing agent
in live mode. No skill body embeds an executable orchestration program.

## 7. Migration from the earlier implementation

| Earlier design | Current implementation |
| --- | --- |
| `Node` combined prose, role, execution and policy | `Skill`, executor registration, `ReviewPolicy`, `NodeRequest` and internal `Frame` have separate responsibilities |
| `library.kind` and optional `script` frontmatter | External binding to a configured resource executor |
| `library.profile: critic` / `critic=True` | Ordinary skill; all calls have explicit artifact grants |
| `library.review` | Application-owned publication policy |
| `ttl_seconds`, notes and ambient result discovery | Removed from this reference; callers explicitly pass evidence |
| Inline `node-js` executable block | Removed; optional authored utilities are resource files selected by the host |
| YAML name ignored, description unused, unknown metadata silently ignored | Name/path agreement enforced; description exposed; unknown/duplicate fields rejected |
| Separate hard-coded agent/code dispatch slots | Generic registered runner interface and external bindings |
| Caller-local idempotency treated as sufficient sharing | Caller keys and exact cross-branch work identity are separate |
| Each frame owned its producer children | Call tasks own wait leases; session operations own shared producers |
| `parent`/`lineage` used for topology and cancellation | Diagnostic `origin`, all call edges in events, active wait graph for cycles/depth |
| Only execution admissions bounded repeated work | Separate call and execution budgets also bound reuse |
| Same names obscured different uses | Neutral shared evidence plus separate caller interpretations |
| Fixture names referenced removed e/j gates | `a-diversified` and `b-no-proposal` describe observations in the current graph |
| Root-level runtime/adapter/test modules and conflicting historical docs | Cohesive `harness/` and `tests/`, one end-to-end contract and a focused sharing design |

These are deliberate breaking changes to the reference API. Old code and historical
plans remain in Git history. There is no silent compatibility layer that accepts the
old schema while discarding its policy.

## 8. Red-team the abstraction

The function-like interface is useful for composition. It should be rejected as a
sufficient production design if any of these stronger claims are required:

| Claim or pressure | Failure mode | Current position |
| --- | --- | --- |
| “All nodes are pure transformations” | Models and tools are effectful and nondeterministic | Async supervised operations, not pure-function equivalence |
| “The prose graph is the execution plan” | Links alone do not determine whether or how to call a procedure | Agent-written PTC decides; call and execution traces establish what ran |
| “Lock the skill name” | Different tasks or evidence would block or incorrectly share | Sharing is opt-in and keyed by exact work, not skill name |
| “Same node plus inputs means reusable output” | Different tasks ask different questions; external state may change | Task, evidence and pinned configuration define session work; changed state needs explicit inputs or fresh work |
| “The first caller owns the producer” | Cancelling a would strand c's shared dependency | Per-await leases, last-waiter cancellation, cleanup before replacement |
| “A creation tree prevents deadlocks” | Joins create dependencies across previously separate branches | Active wait-cycle and depth checks at every attachment |
| “Fresh review proves independent correctness” | Same-model correlated errors, incomplete evidence or injected evidence can persist | Fresh transcripts and explicit grants only; no correctness guarantee |
| “A successful optional audit is always enforced” | The agent may omit or misread an optional check | Required checks must be configured in host policy |
| “Prose-only skills scale to every capability” | Tool permissions and external effects need executable enforcement | Host adapters own capability configuration; no frontmatter flags with assumed authority |
| “SQLite means durable orchestration” | Frames, grants, budgets, keys and leases are in memory | Records persist; coordination is one event loop, recovery is not implemented |
| “A passing offline suite proves the agent works” | Scripted programs can take correct branches without reasoning about prose | Separate live-model evaluation is still required |

The repository also lacks an authenticated external-effects gateway, cross-session
artifact grants/cache, automatic invalidation, exact token/currency reservation and
complete crash-time action logging. Agent actions are captured after an invocation
returns; interrupted execution may have incomplete action transcripts. QuickJS and
the private state backend are local execution boundaries, not a comprehensive
multi-tenant security design. The registry assumes a trusted skill repository.

The next useful validation is live execution against these two prompt/input pairs,
followed by changed wording and counterexamples. That can test whether the harness
actually writes distinct contextual programs, rather than merely proving that this
runtime can execute them. No additional universal node attributes are justified by
the current examples.
