# Dynamic skill execution with runtime PTC

Status: proposed architecture, September 2026. This document extends [the Library harness design](library-harness-design.md). It describes the intended end-to-end behavior and identifies gaps in the current reference implementation; it is not a claim that the full design already runs.

Implementation decision: read the [red-team assessment and implementation plan](node-composition-red-team-plan.md) before implementing this proposal. It documents synthetic failure probes, narrows the guarantees around review and isolation, and supersedes the rollout sequence below with a smaller experiment using the existing interpreter and recursive call surface. In particular, a dedicated `runScript` service is optional, and a fresh frame does not currently restrict access to accepted session artifacts.

## 1. Design thesis

A skill is a reusable unit of expertise that an agent can enter or invoke. It can contain prose, links to other skills, and a reviewed script or other local resource. The agent observes results and writes programmatic tool calls (PTC) incrementally. The resulting program can invoke skills in parallel, inspect artifacts, return early, and continue after new observations. The host supplies execution, authority, and durable records. It does not compile natural-language conditions into a fixed workflow.

The useful split is:

| Owner | Responsibility |
| --- | --- |
| Skill author | Explain objective and semantics; link useful skills; optionally supply a reviewed local script and its contract. |
| Agent in a frame | Choose what to inspect, run, delegate, reuse, and synthesize after seeing observations; write the next PTC fragment. |
| PTC interpreter | Run ordinary code, including `await`, `Promise.all`, loops, and early returns; expose only authorized host functions. |
| Supervisor | Bind identity and capabilities; enforce budgets, access, script isolation, child joins, artifact validation, review obligations, and publication. |

An LLM judgment need not become a dedicated typed `decide()` call before every branch. The next PTC fragment is itself an inspectable action. Schemas remain useful at stable interfaces (skill inputs, result receipts, scripts, artifacts, external actions), and a typed decision can be used voluntarily for a durable categorical finding.

## 2. The three different graphs

| Graph | Meaning | When established |
| --- | --- | --- |
| Skill links | Potential procedures and local resources. `[[x]]` is a discoverable reference, not an edge the scheduler must execute. | At a reviewed skill revision. |
| Invocation trace | Actual calls, entry events, early returns, branches, failures, and joins. | During a run, as the agent acts. |
| Artifact lineage | Exact inputs, scripts, evidence, and accepted outputs used to produce a result. | At publication and subsequent consumption. |

The trace can be a tree of nested frames with events and cross-frame references. Lineage can be a DAG, even when control flow contains loops or repeated invocations. Neither is a static execution DAG inferred from prose. The agent may open a linked skill without invoking it, and a linked skill may never be visited. A repeated skill invocation with different binding inputs is a distinct computation.

## 3. A skill node

The authored unit may look like this (illustrative syntax, not a schema already implemented):

```text
skills/b/
  SKILL.md
  scripts/observe_delta.py
  references/...
```

```yaml
---
name: b
description: Assess the present state and investigate material changes
library:
  scripts:
    observe_delta:
      path: scripts/observe_delta.py
      input_schema: delta-input-v1
      output_schema: delta-observation-v1
      profile: readonly-data
  review:
    critics: [artifact-coherence]
    max_revisions: 1
---
```

```markdown
# B

Run the local `observe_delta` script against the bound snapshots first. Inspect
its result. When the change warrants deeper work, investigate with [[k]] and
[[l]]; otherwise return a concise observation with its evidence. Explain the
reason for the chosen course in the resulting artifact.
```

`observe_delta` may be deterministic code, or an approved adapter that gathers observations. Its output can include a computed delta, source references, and limitations. If “material” is contextual, the script does not have to encode a universal threshold. After observing it, the agent may issue a new PTC fragment to invoke `k` and `l`, or submit the early result. A script that *does* implement a fixed, reviewed threshold can return that evaluation explicitly; the host still does not invent the threshold.

At invocation, the parent sees an opaque call to `b` and a small receipt. `b` gets a new frame, its own agent loop, its own working interpreter state, and access only to granted inputs and references. Its internal script and child calls remain inspectable in the trace. Entering `b` inline instead of invoking it activates its applicable obligations in the current frame; that is a different choice from asking for an independently published `b` artifact.

Skill versions pin prose, script bytes, script contracts, and linked resources as one reviewed snapshot. Plain prose wikilinks can remain navigation hints. Required scripts and review contracts must be declared in validated metadata; do not infer enforcement obligations from ambiguous wording. Links in fenced code examples should not silently become executable dependencies.

## 4. Minimal runtime surface

The conceptual host capabilities are:

```ts
openSkill(id): Promise<BoundedSkillPacket>       // enter/inspect a skill
readArtifact(ref, slice?): Promise<BoundedRead>  // authorized evidence
invokeSkill(request): Promise<Receipt>           // supervised child frame
runScript(skillId, scriptId, input): Promise<ScriptReceipt>
submitCandidate(candidate): Promise<StageReceipt>
```

Discovery can start with canonical links in `openSkill` and a small catalog. Search is a retrieval feature to add when traversal is insufficient, not a separate control-flow system. The current adapter calls these `libraryOpen`, `libraryRead`, `task()` and `librarySubmit`; `runScript` is proposed. Avoid a host `fanOut`, `ifElse`, `walkGraph`, or mandatory `decide`: the interpreter already expresses those patterns. `Promise.all` is concurrency syntax, while admission control still limits the actual concurrency. Use `Promise.allSettled` when partial results need explicit treatment.

Every child request carries a canonical skill, task, binding inputs, selected artifact references, and a parent-scoped stable operation key. The host derives the parent identity, principal, permissions, deadline, and source snapshot. A receipt reports the status (`accepted`, `needs_review`, failed/cancelled as appropriate), reference, and bounded summary. A script receipt likewise identifies the script version, input refs, output ref, exit status, and diagnostics. Large payloads remain behind bounded reads. Submission stages a candidate; only the supervisor can accept it.

The model's PTC code cannot import supervisor internals or treat a filesystem path as a capability. Scripts run in an isolated execution profile with declared inputs, output limits, timeouts, and an allowlist of effects. A script that requires network or mutable actions needs separate host authorization. Whether invoked by the agent, a native tool, or another script, the same effect gateway applies.

## 5. End-to-end example

The parent skill says, in prose:

> Generate `[[a]]` and `[[b]]`. Observe `[[b]]`; in scenario A, run `[[c]]` and `[[d]]` concurrently. If `[[d]]` raises concern E, investigate with `[[f]]` and `[[g]]`. In scenario B, run `[[h]]`; investigate with `[[i]]` when `[[h]]` raises concern J. Audit the available outputs with `[[artifact-coherence]]`, then use `[[thesis]]` to synthesize a supported conclusion. Each linked skill may have its own local procedure.

This is guidance for an agent, not code for the harness to parse into a branch table. A possible run is:

1. The launcher authenticates the request and pins the skill revision, source snapshots, user scope, and budget. It admits a root frame and enters the parent skill. The entry packet contains the authored instructions, links, and eligible prior receipts, with scope and freshness labels.
2. The root issues one PTC fragment to invoke `a` and `b` concurrently, with distinct stable operation keys. `b` runs its embedded `observe_delta` script, reads its observation, and either returns early or invokes `k` and `l` concurrently. The root waits for both receipts and inspects the relevant slices.
3. Having observed `b`, the root decides the next fragment. If it judges scenario A relevant, it invokes `c` and `d` concurrently. After reading `d`, it may invoke `f` and `g`; scenario B instead leads through `h` and perhaps `i`. The code for the later fragment does not exist until the observation has been made. A fixed threshold in `observe_delta` and the agent's contextual judgment can coexist.
4. The root invokes `artifact-coherence` for each *produced and applicable* artifact. For example, in scenario B there may be no `c`; an audit request for `c` is not silently fabricated. A cross-artifact consistency check is a distinct invocation with all relevant references. Review findings can trigger targeted repair or a narrowed claim within the allowed budget.
5. The root invokes `thesis` with the accepted evidence and audit refs, or writes its own synthesis and submits a candidate. It records missing branches, failed checks, and uncertain judgments. The supervisor verifies actual references and any mandatory review policy, then publishes an accepted artifact or `needs_review` status.

An illustrative sequence of *separate* model-written fragments is:

```js
// After entry, before observing b:
const [a, b] = await Promise.all([
  invokeSkill({skill: "a", task: "...", inputs, refs: [], key: "a:1"}),
  invokeSkill({skill: "b", task: "...", inputs, refs: [], key: "b:1"})
]);
// Return compact summaries or selected reads to the model before choosing more work.
```

```js
// Example fragment the model could choose after seeing b in scenario A:
const [c, d] = await Promise.all([
  invokeSkill({skill: "c", task: "...", inputs, refs: [b.ref], key: "c:1"}),
  invokeSkill({skill: "d", task: "...", inputs, refs: [b.ref], key: "d:1"})
]);
// Observe d before writing a later fragment that may invoke f and g.
```

The example does not require a `scenarioA(b)` function or a `semanticMatch(d, "e")` primitive. The model observes the material and writes the next action. If a branch conclusion must be retained for evaluation, publish a short rationale with evidence references as part of the trace or a decision artifact. That makes the decision auditable without forcing every branch through a fixed classifier.

## 6. Observation and context boundaries

The agent's code can process large working sets and show the model only selected slices. Data in an interpreter variable is not automatically an observation by the model. The result of a PTC execution must expose enough of the script result, artifact summary, and evidence for the agent to make a sound next decision. Preserve source spans and reasons for uncertainty; truncate with an explicit continuation cursor. A source document, script stdout, or prior artifact is evidence, never instruction authority.

Parallel siblings do not share mutable interpreter state. One sibling's result becomes available to another only through an explicit authorized reference or a deliberate subsequent call. A parent can inspect child progress as a trace if policy permits, but must not rely on uncommitted sibling scratch as a validated dependency. Join or cancel children before finalizing the parent. Failure or partial completion is represented as such, not coerced into an accepted artifact.

Reuse requires matching binding inputs and source revisions, valid scope, producer revision, freshness, and accepted status. Reusing an old artifact skips computation, not the new run's obligation to establish why it applies. A changed upstream source invalidates downstream eligibility by lineage. Exact content hashes help identify versions but cannot prove semantic equivalence or correctness. The root may still choose to recompute because the context calls for it.

## 7. What the supervisor must enforce

| Boundary | Invariant |
| --- | --- |
| Identity | A nested call cannot choose its own parent or escalate its principal. |
| Invocation | Stable parent-scoped keys deduplicate exact retries and reject conflicting reuse. Repeated active subproblems, depth, fan-out, deadlines, and inference budgets are bounded. |
| Scripts | Execute only pinned and permitted script versions; validate declared inputs/outputs and cap runtime, memory, stdout, and effects. |
| References | Reads and child grants are authorized; accepted dependencies are exact immutable refs. A draft is visible only to its producer or explicitly granted reviewers. |
| Publication | Stage first; validate dependencies, output contract, provenance, and required reviews against the exact candidate revision. Unresolved checks cannot yield `accepted`. |
| Actions | Side effects use authenticated, idempotent action gateways and required approvals regardless of which execution route called them. |
| Recovery | Persist admission, events, receipts, and effect keys before claiming resumable unattended execution. Interpreter state alone does not provide crash recovery. |

Mandatory review is a narrow host rule, not a general orchestration language. An author may say “audit `a`, `b`, and `c` where applicable”; the agent chooses calls and records coverage. If a domain requires an unconditional acceptance gate, declare the validator or critic in policy. If an audit depends on branch-specific existence, the policy must define applicability or require an explicit coverage attestation. Merely mentioning `[[artifact-coherence]]` in prose does not establish that the review happened.

## 8. Relationship to the current repository

The existing `kernel.py` and `deepagents_adapter.py` implement supervised recursive calls, inline skill entry, bounded artifact reads, candidate staging, immutable records, and required critics. The QuickJS path can issue native `task()` calls and join them in ordinary JavaScript. The small sample skills and offline tests demonstrate that boundary with scripted models.

Important gaps before treating this document as implemented:

1. There is no versioned local-script manifest or `runScript` host function. `StateBackend` scratch is not a governed script store. Add a pinned registry for reviewed scripts and an execution gateway with explicit profiles and receipt publication.
2. The registry indexes wikilinks outside fenced blocks, but has no explicit link roles, script metadata, or output contracts. Extend validation without converting ordinary prose references into automatic execution edges.
3. The adapter returns compact child receipts, but there is no first-class persisted log of model-issued PTC fragments, branch rationale, script invocations, and reads. Add redacted event records and preserve a stable run/frame/operation identity.
4. The reference's in-process ledger, frame grants, and idempotency map are not crash recoverable; retrieval is a conservative scan with exact input matching. Add durable admission, indexed eligibility, source revision invalidation, and recovery before depending on long unattended chains.
5. Required critics currently check structural review binding and verdict shape. Domain truth, branch coverage, and script result validity need specific validators and evaluation. Do not equate an `accepted` label with correctness.

## 9. Implementation sequence and evaluation

1. Define script manifests, immutable script digests, sandbox profiles, and script receipts; test a `b` that returns early or fans out to `k` and `l` after an embedded delta observation.
2. Add trace events for PTC fragments, script runs, explicit observations, child status, join, and publication. Keep private data redacted and store evidence references for later inspection.
3. Exercise both scenario branches, the optional `f`/`g` and `i` paths, missing `c` audits, failed children, cancellation, stale artifacts, repeated call keys, and a mandatory review failure. Verify that unchosen branches never execute and that the accepted thesis depends only on authorized accepted references.
4. Measure real-model task quality and cost against a files-and-code baseline, ordinary delegation, and this dynamic PTC path. Evaluate branch choice and coverage from external evidence; a plausible trace or reviewer pass rate alone is not evidence of a correct thesis.

The target is a small, capable host that lets the agent repeatedly **observe, write code, execute, and observe again**, while each skill can do the same inside its own frame. The graph supplies discoverable expertise; the execution trace records the path taken; artifact lineage explains what supported the result.
