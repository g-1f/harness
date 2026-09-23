# Callable skill graph: contracts and end-to-end execution

Status: implemented local reference, with the design choices below made explicit.
The objective is to let the harness turn reusable prose into executable work,
including nested transformations and fresh reviews. RLM is not the primitive.

## 1. Start with the distinctions

A **skill** is a reusable procedure: authored prose, a short description, references
to other procedures, and optional resource files. A **node address** is a skill name
that the application can execute. An **invocation** is one application of that
procedure to a particular task, inputs and evidence. An **executor** supplies its
execution mechanism. A **publication policy** determines required checks.

Conceptually:

```text
invoke(skill_name, task, inputs, evidence_refs) -> await receipt
receipt.ref -> immutable result artifact
```

This resembles function application but is not a pure function. Invocations consume
budgets, create artifacts, may call a nondeterministic model and can fail or be
cancelled. Identical inputs are not a promise of equivalent results. The operation
key provides exact retry identity within one caller; it is not semantic memoization.

Three graphs have different meanings:

| Graph | Vertices and edges | Meaning |
| --- | --- | --- |
| Authored skill graph | Skill IDs, linked by prose references | Procedures that may be useful together; cycles are allowed |
| Invocation tree | Fresh frames, linked by caller/child relationships | Work actually admitted for this session; repeated skills create separate vertices |
| Artifact evidence graph | Immutable records, linked by declared or observed references | What a result declares or reads; sharing is explicit |

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

The bundled agent adapter exposes the same four application capabilities. Arbitrary
per-agent tool allowlists are not a YAML feature; an application needing them must
configure or implement a suitable executor. The `instructions` constructor argument
allows a separately configured system prompt.

A `ReviewPolicy` has `reviewers: tuple[str, ...]` and `max_revisions: int = 0`.
These are host publication rules, not authored node attributes. Reviewers name
ordinary skills. A reviewer may itself have a required review if the policy graph
is acyclic; there is no privileged “critic” type. Inline procedure entry also adopts
that procedure's requirements. The global revision bound caps local repair policies.

The shared supervisor owns frame-count, model-operation, depth, deadline and repair
bounds. They apply to all executors. Model operations are metered during inference;
a parent waiting for children does not hold an inference permit.

## 4. The invocation contract

| `NodeRequest` field | Meaning |
| --- | --- |
| `node` | Registered skill name |
| `task` | Nonempty prose question for this invocation; part of request identity |
| `inputs` | JSON object explicitly selected by the caller |
| `refs` | Ordered artifact references to grant; defaults to empty |
| `key` | Nonempty operation key scoped to the caller frame, or launcher scope for roots |

The request is finite JSON, capped at 32 KB. There are no agent-specific fields.
Parsing copies nested input data before admission. Same caller/key and identical
node/task/inputs/refs share the in-flight or completed operation. A conflicting
request with that key is rejected. A repeated active subproblem is rejected;
narrower recursive tasks remain subject to depth, frame and deadline bounds.

The host creates `Frame` state: ID, parent, request, lineage, selected executor,
entered procedures, artifact grants, child tasks, observed reads and closed state.
None belongs in skill frontmatter. The adapter receives a `RunContext` containing:

| Field | Meaning |
| --- | --- |
| `entry` | Current skill packet: node, description, revision, text, links, resource paths |
| `attempt` | Zero-based execution/repair attempt |
| `feedback` | Failed review outcomes from the preceding attempt |
| `previous` | Previous immutable candidate ref, or null |

Each agent attempt builds a fresh agent and QuickJS interpreter. Parent messages,
globals and interpreter snapshots are not inherited. The child receives its own
entry, task, inputs and explicitly granted refs. “Fresh” does not mean ignorant of
all prior information: the caller can intentionally include prior evidence in its
inputs and grants.

All frames use the same artifact access rule: own outputs and explicit grants only.
A child receipt grants its result to its caller. Granting a record does not grant
every reference mentioned inside it. No ambient session-result cache or TTL-based
reuse remains. Reviewers use the same mechanism; the host grants a required reviewer
the exact candidate and its declared supporting refs.

## 5. Four capabilities, one publication protocol

| Capability | Effect |
| --- | --- |
| `read_node(node, enter=False)` | Inspect prose and links; `enter=True` activates inline procedure obligations |
| `run_node(request)` | Await a fresh supervised call; return a compact receipt |
| `read_artifact(ref, offset, limit)` | Read an authorized immutable record in bounded slices |
| `submit_candidate(summary, content, based_on)` | Stage a candidate; the host controls publication status |

PTC exposes camelCase equivalents on `tools`. Native calls use the same bound
`NodeAPI`. The framework's compatibility `task` route dispatches into the same
supervisor. No unsupervised application child is provided through that route.

A candidate has a nonempty summary of at most 600 characters, a JSON object
`content`, and `based_on` artifact refs. It is limited to 500 KB. These are the same
contracts for model and code executors. Application-specific shapes such as evidence
observations or coherence assessments live inside `content`, not on `Skill`.

Execution proceeds as follows:

1. Validate request, refs and executor registration; enforce idempotency and bounds.
2. Start a fresh frame and enter its primary procedure.
3. Run the configured executor. The agent may inspect links, call children, observe
   artifacts and write additional code. Children must be joined before returning.
4. Validate and freeze the candidate as an immutable draft.
5. Run every required reviewer in fresh context, granting the exact draft first and
   its declared evidence next. Reviews for the candidate can execute concurrently.
6. Accept only when every required reviewer returns an accepted artifact whose
   content has that exact `candidate_ref`, `verdict: "pass"` and empty `findings`.
7. If allowed, create a fresh repair attempt with feedback. A changed candidate
   receives new reviews; prior verdicts cannot certify it. Otherwise return
   `needs_review`. Close the frame and cancel any outstanding descendants.

Optional reviews are ordinary calls made by the agent. Their result must be read:
`receipt.status == "accepted"` does **not** imply `content.verdict == "pass"`.
The host enforces only configured mandatory reviews. The fixture's choice to stop
on a failed optional audit is behavior of the example procedure.

A receipt has `ref`, `status` (`accepted` or `needs_review`) and `summary`.
Operational errors raise; failure/cancellation events record their category.
The stored record contains the candidate plus session/frame/parent IDs, skill and
executor identity, task and inputs, registry snapshot and skill revision, entered
procedures, input refs, observed refs, review refs, publication status and time.
`observed_refs` records actual reads; `based_on` is the worker's declared lineage.
Neither proves that every semantic dependency was declared or understood.

## 6. End-to-end nested example

The authored reuse graph is shown in the [README](../README.md). Links in a and b
reuse existing c/k/l procedures under different prose; there are no duplicate skills
named “baseline-c” and “acceleration-c.”

| Caller | Callee | Task carried by the example invocation |
| --- | --- | --- |
| root | a | Establish the baseline claim and test its assumptions |
| a | c | Test baseline capacity assumptions without presuming acceleration |
| a | l | Check whether mix stability supports the baseline comparison |
| c, inside a | k | Corroborate volume for the baseline capacity question |
| b | k | Explain volume against the measured snapshot delta |
| b | l | Explain mix against the measured snapshot delta |
| root, after observing acceleration | c | Assess whether capacity can meet accelerating demand |
| c, inside root | k | Corroborate volume for that acceleration question |

Scenario A executes both c contexts, then supplier investigation and fresh audits.
Scenario B retains a's nested capacity work but takes the h/i policy branch at root.
Its root does not fabricate an acceleration-specific c result or audit. The unchanged
fixture omits k/l only under b; a still owns its baseline work.

The [two task prompts](../examples/prompts/) are inputs used by `demo.py`. The
[Scenario A](../examples/trajectories/scenario_a.md) and
[Scenario B](../examples/trajectories/scenario_b.md) trajectories are exported from
actual offline runs, with IDs relabeled and repeated prelude omitted. Each includes
all invocation tasks, explicit grants, captured PTC, observed outputs and final result.

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
| Same names obscured different uses | Tasks recorded on admissions and artifacts; contextual reuse tested |
| Root-level runtime/adapter/test modules and conflicting historical docs | Cohesive `harness/`, `tests/` and one current design document |

These are deliberate breaking changes to the reference API. Old code and historical
plans remain in Git history. There is no silent compatibility layer that accepts the
old schema while discarding its policy.

## 8. Red-team the abstraction

The function-like interface is useful for composition. It should be rejected as a
sufficient production design if any of these stronger claims are required:

| Claim or pressure | Failure mode | Current position |
| --- | --- | --- |
| “All nodes are pure transformations” | Models and tools are effectful and nondeterministic | Async supervised operations, not pure-function equivalence |
| “The prose graph is the execution plan” | Links alone do not determine whether or how to call a procedure | Agent-written PTC decides; invocation traces establish what ran |
| “Same node plus inputs means reusable output” | Different tasks ask different questions | No automatic semantic cache; task is part of call identity |
| “Fresh review proves independent correctness” | Same-model correlated errors, incomplete evidence or injected evidence can persist | Fresh transcripts and explicit grants only; no correctness guarantee |
| “A successful optional audit is always enforced” | The agent may omit or misread an optional check | Required checks must be configured in host policy |
| “Prose-only skills scale to every capability” | Tool permissions and external effects need executable enforcement | Host adapters own capability configuration; no frontmatter flags with assumed authority |
| “SQLite means durable orchestration” | Frames, grants, budgets and in-flight keys are in memory | Records persist; recovery is not implemented |
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
