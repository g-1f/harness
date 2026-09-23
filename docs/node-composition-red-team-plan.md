# Callable skill nodes: red-team assessment and implementation plan

Date: 2026-09-23. Status: design decision and proposed work; no runtime changes in this document commit.

Repository baseline: `10ca4a56990b6bd47fa341d6a9134321feb833a1`. This review qualifies the [dynamic PTC design](dynamic-skill-ptc-design.md), especially its claims about fresh context, artifact lineage, and a dedicated script primitive.

## 1. Decision

Proceed with a small experiment: use the existing supervised recursive call to invoke research, red-team, coherence, and synthesis skills through the same interface. Let the parent generate PTC after each observation. Put a deterministic delta script inside the example skill. Do not build a graph compiler, mandatory branch classifier, graph database, or new script service to demonstrate this idea.

Reject three stronger claims until separately demonstrated:

- A function-like interface does not make a node a pure or automatically cacheable function. Relevant context includes the skill and model revision, evidence snapshot, tool observations, and invocation environment.
- A fresh agent context does not guarantee independent evidence or independent errors. The same model and the same missing source can reproduce the writer's mistake.
- Composing `red_team(a)` does not guarantee a review before publication. An agent can omit the call, ignore a failed verdict, or apply a review to the wrong revision. A required publication check needs a host acceptance condition.

The architecture succeeds if flexible composition improves independently measured task outcomes at an acceptable cost, while a small host preserves the necessary execution invariants. Elegant syntax alone is not the success criterion.

## 2. Formal contract

Treat a skill as an asynchronous, effectful operation:

```text
invoke(skill_revision, task, inputs, artifact_refs, operation_key; host_frame)
    -> receipt or execution error
```

`host_frame` is supplied by the runtime, not by model-written JSON. It holds the authority, scope, lifecycle, budget, and interpreter identity. A new invocation gets a fresh agent/interpreter state. The body may be authored code, an agent loop, or code plus nested agent calls. These implementations need the same observable receipt and provenance boundary, not necessarily the same internal runner.

Keep the current request and receipt shapes for the first experiment. Resolve each skill's output contract when composing it; a shared envelope does not imply every output is a valid input to every other skill. Repeated calls may have different objectives and observations. Recursion is a sequence of new invocations, not a cycle among immutable output versions.

A review artifact has a local, machine-readable result contract:

```ts
type ReviewAssessment = {
  candidate_ref: string;          // exact reviewed version
  verdict: "pass" | "fail" | "inconclusive";
  findings: Finding[];            // claim, evidence refs, missing checks
};
```

This is a proposed extension: the current mandatory validator recognizes only `pass` and `fail`. `inconclusive` is a successfully produced review that cannot justify acceptance. Missing fields and execution exceptions likewise cannot be interpreted as a pass. Criteria are bound to the pinned reviewer procedure for mandatory reviews; caller-written optional review tasks may refine an investigation but cannot weaken a mandatory policy.

There are two different statuses:

- The receipt says whether producing and publishing the review completed under its own protocol.
- `content.verdict` says what the review concluded about its candidate.

The proposed `red_team(node_a).result.state == "pass"` syntax is valid only if the facade clearly distinguishes these. In this repository, inspect the review content; `receipt.status == "accepted"` is insufficient.

Coherence review consumes an explicit set of versioned artifacts and the scope of comparison. Its assessment binds the exact target set, findings, and coverage. When used as a required check of a final synthesis, the supervisor can keep its existing single `candidate_ref` contract: the synthesis candidate's immutable content identifies the exact component refs. Do not overload `candidate_ref` with whichever component happened to finish first.

## 3. Attempts to falsify the design

| Attack or counterexample | What it disproves | Minimum response |
| --- | --- | --- |
| The review returns `fail`, but the parent checks only the accepted receipt. | Publication status means review approval. | Keep execution status separate from verdict; validate the local review contract. |
| Generated PTC omits a required review or catches its exception and continues. | The call pattern itself enforces review. | Retain a host gate only for declared mandatory reviews. Optional review stays ordinary composition. |
| Review `a1`, repair to `a2`, then carry forward the old pass. | Review identity can be attached to a mutable node name. | Bind review to immutable candidate identity and pinned procedure; recheck each repaired revision. |
| `a`, `b`, and `c` each pass separately but use incompatible currencies or dates. | Unary reviews establish coherence of a set or a later synthesis. | Run a set-level check when relevant, and review the final synthesis if its new claims require approval. |
| The root takes the wrong branch and omits `c`; an audit of only produced artifacts passes. | Auditing outputs establishes investigation completeness. | Give the coverage reviewer the objective, governing skill, and executed/omitted paths. Evaluate omitted-work detection separately; do not let this become an automatic prose compiler. |
| A fresh reviewer receives the writer's framing or reads prior favorable reviews. | Fresh transcript means an independent assessment. | Restrict supplied context and retrieval when independent review is requested; test correlated misses against outside ground truth. |
| New evidence appears under the same `as_of` value. | Hashing explicit inputs makes LLM work safely reusable. | Pin source versions or disable automatic reuse. No cross-run caching claim in the MVP. |
| The parent copies evidence into a new string and omits `based_on`. | Artifact-ref arguments automatically capture complete provenance. | Record host-visible reads and inputs separately from declared evidence dependencies. Mark untracked external observations; do not claim complete semantic lineage. |
| A coherence check sees artifacts while siblings are still mutating them. | Ordinary shared files are an adequate concurrent artifact interface. | Share immutable published versions; reviews bind explicit target sets after readiness is established. |
| A failed audit triggers an unbounded regenerate-review loop. | Recursive function composition converges. | Share invocation, inference, and deadline limits; bound mandatory repairs; report unresolved work when exhausted. |

The strongest objection is the completeness problem: the same reasoning process can choose the wrong investigation and then commission reviews that validate only that investigation. A separate coverage review can help, but can share the same blind spots. The architecture cannot solve this merely by adding more nodes. It needs realistic tasks with independently defined omissions and defects.

## 4. What was actually checked in the repository

Two temporary synthetic probes exercised `kernel.py` directly with scripted runners and an in-memory store. They made no external model calls or repository changes:

```json
{
  "review_receipt_status": "accepted",
  "review_verdict": "fail",
  "parent_status_without_mandatory_policy": "accepted",
  "accepted_parent_readable_without_grant": true
}
```

The first behavior is intentional for an optional review, and demonstrates why optional composition cannot support a mandatory-review claim. The existing `_run` required-review path checks the verdict and candidate identity separately and already blocks missing, malformed, or wrong-candidate reviews; preserve that path.

The second probe supplied an accepted artifact reference to another frame with no artifact grant. `Kernel.read` permits this within the same session. This does not mean the reviewer automatically discovers every reference; it means a fresh frame is not an access boundary for accepted session artifacts. `Kernel.open` can also inject eligible accepted neighbor summaries from the session. Both paths need the proposed reviewer visibility rule before claiming a restricted evidence set.

Source inspection also found:

- `_record` checks the declared `based_on` refs but does not establish that all influential observations were declared. Do not use this field alone for automatic dependency invalidation.
- `_run` freezes a draft ref before required review and writes a distinct accepted record afterward. Preserve the exact reviewed draft ref in review receipts; never compare it directly with the later accepted envelope's hash as if they were identical. A future separate content identity could simplify this, but is not required for the first experiment.
- `librarySubmit` stages output without returning a draft artifact ref. Optional red teaming of an already returned child artifact works today. Agent-controlled review of the root's own unpublished draft would need a freeze/read operation or a staging extension; the current host-required review already handles that case. Do not hide this gap behind pseudocode.
- The adapter creates fresh agent state on each runner attempt; interpreter variables are not a durable checkpoint across revisions or process restarts.

## 5. Implementation plan

### Increment 1 — demonstrate composition with existing primitives

Files: `skills/`, `deepagents_adapter.py`, `test_integration.py`.

1. Add small example skills for research, red-team, coherence, and thesis. Reviewers are ordinary supervised skills. Put a small pure JavaScript delta script in the example skill text, executed in the existing interpreter; the existing skill-text revision pins it. This avoids requiring a new Python executor or script registry to demonstrate embedded observations.
2. Use the existing `task()`/`rlm(request)` bridge for child calls. After reading observations, let the parent choose its next PTC fragment. Keep fixed scripts limited to authored computations such as delta extraction.
3. Document receipt status versus review verdict in `RUNTIME_PROMPT`. Add no native `red_team`, `decide`, fan-out, or graph-traversal tool.
4. Demonstrate `b` returning early or calling `k`/`l`, followed by the parent choosing the scenario A or B investigation, optional deeper branches, set coherence review, and synthesis.

Acceptance: real QuickJS and the compiled dispatch bridge run the scripted scenarios; unchosen branches are absent, chosen branches join, the reviewed refs match, and failures remain visible. These tests establish mechanics, not whether a real model chooses the right branch.

### Increment 2 — make review boundaries accurate

Files: `kernel.py`, `deepagents_adapter.py`, `test_kernel.py`, `test_integration.py`.

1. Retain the current required-review supervisor path. Both optional and required reviews invoke the same worker contract. The host decides when a mandatory acceptance condition is satisfied; PTC remains free to request extra investigation.
2. Support `inconclusive` in review content while allowing acceptance only for a well-formed `pass` without unresolved findings. Validate review producer identity, exact target revision, and pinned policy. Required review task/criteria come from the host and procedure.
3. Define restricted artifact visibility for critic frames and descendants. Supply the target and permitted evidence refs explicitly. Apply the same rule to reads and inline-entry candidate summaries; prevent a sibling review's conclusions from being injected automatically. Permit further authorized research where the critic's profile allows it.
4. Reserve enough of the existing bounded work allowance for mandatory review or return unresolved status when reservation cannot be met. A parent awaiting children must not hold the model concurrency permit.

Acceptance: missing review, wrong revision, failed/inconclusive verdict, exhausted review allowance, and unauthorized same-session evidence cannot produce a claimed mandatory pass. Existing normal-worker reuse and optional critique behavior remain explicitly tested.

### Increment 3 — measure decisions, coverage, and review value

Files: evaluation fixtures and runner under `evals/`; small host event additions in `kernel.py` and `deepagents_adapter.py` as needed.

1. Record invocation and skill versions, PTC fragments and outputs, target refs, read refs, exceptions, and review results with appropriate redaction. Preserve enough observations to assess branch decisions; do not require hidden model reasoning. Separate declared dependencies from observed reads.
2. Start with 24 bounded fixtures: 8 branch/early-return tasks, 8 cross-artifact inconsistency tasks, and 8 missing-evidence or invalid-review tasks. Include correct candidates so false-positive reviews are measurable. Have expected defects and acceptable outcomes defined independently of the writer and reviewer.
3. Compare three configurations with the same available evidence, tools, base model, output requirements, and total allowance: ordinary agent/tool execution; runtime PTC composition; runtime PTC plus fresh review nodes. Run each fixture three times initially. This is a diagnostic pilot, not a statistically conclusive benchmark.
4. Measure final factual/decision errors, omitted required investigations, review defect recall, false rejection of correct work, valid repairs versus harmful edits, incomplete runs, latency, tokens, and cost. Keep lifecycle acceptance separate from task correctness. Try a different reviewer model or evidence method only if correlated errors are the measured blocker.

Acceptance: zero host invariant violations across the failure fixtures. For review utility, compare final errors and correction yield at equal total allowance; do not accept a higher pass rate or more calls as improvement. Predeclare a product latency/cost ceiling before running the pilot. If review offers no net quality gain, keep it optional and do not make it the default. If PTC provides no quality, coverage, or efficiency benefit over the simpler baseline, defer expansion. Borderline results justify better fixtures or a larger evaluation, not claims of proven superiority.

## 6. Scope decisions

- No new mandatory decision schema: review verdicts are local output contracts; the rest of the agent's contextual branching remains model-written PTC.
- No mandatory `runScript` primitive in the MVP. Embedded JavaScript can use the current interpreter. A Python script in a deployment with real filesystem execution should use that existing execution capability with pinned inputs and provenance. The current reference uses `StateBackend`, so it cannot claim that Python execution is already available. Add an execution adapter only when a real task needs it.
- No generalized `compose`, `mapNode`, graph DSL, or automatic prose expansion. Ordinary functions and promises suffice for the experiment.
- No automatic cross-run artifact cache or crash-resume claim. Pin evidence for the experiment and preserve the reference's stated limits.
- No generic review-of-review recursion. Current critic policy restrictions and shared limits remain. Nested bounded evidence gathering is sufficient to test recursive reviewer behavior.
- These increments remain proposed work. This publication changes documentation only.

The specific hypothesis worth building is that a capable agent can compose heterogeneous skill functions incrementally, and use fresh review skills to improve selected outcomes. The hypotheses to reject are that composition automatically supplies correctness, complete lineage, independence, or enforcement.
