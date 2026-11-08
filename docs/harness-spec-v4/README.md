# G-1F Harness v4 — Evidence-Native Async Reasoning

**Status:** Proposed normative specification, **not implemented**.  
**Base:** [v3 specification](../harness-spec-v3/README.md), 2026-11-04, on `kernel-spec-v1`.  
**Scope:** Generic model/agent runtime with an optional investment-research profile.  
**Principle:** *The host owns mechanism, durable history and authority; the model owns decomposition, relevance, interpretation and coordination strategy.*

## Why v4

V3 removes mandatory skill-graph execution and exposes six composable host calls. V4 preserves that design while adding specifications for durable evidence, traceable trajectories, snapshot forks, collaboration/convergence, point-in-time information, incremental research and measurable throughput. **The graph is a record of knowledge and computation; it does not require an agent per artifact or an authored workflow DAG.** An agent may execute several tasks and publish several artifacts. A task may execute in a model session, a deterministic program, or a shared async child.

**North star:** maximize *verified, useful research per unit of wall time*, while maintaining evidence-grounded conclusions that change only when justified and remain reconstructable at historical cutoffs.

## Design invariants

1. **Six native calls; no mandatory graph DSL.** `readNode`, `readArtifact`, `openNode`, `nextNodeEvent`, `closeNode`, `publishCheckpoint`. Fork, join, converge, settle, race, review and skill traversal are wrappers/compositions. A new native effect requires proof it cannot be expressed by these calls without violating authority or atomicity.
2. **Four distinct identities.** Logical task, concrete execution attempt, persistent agent session/trajectory, and immutable artifact or result version are not the same object.
3. **History is append-only.** Correct a claim with an immutable successor and a `supersedes` edge. Advance branch heads atomically; never rewrite an old source vintage, forecast or decision.
4. **Evidence references are native data.** The host enforces resolvability, immutability, scope and exact selectors; a citation is not a host-certified logical entailment. Actual reads, explicit citations, derivation and invalidation edges are separate.
5. **One durable event journal, many views.** Every authorized node may *discover* the run, but unrelated ambient events need not interrupt or fill each model context. Direct messages/held-work events get priority.
6. **Snapshot-consistent execution.** Historical data reads obey source availability and authorization; execution reuse never silently crosses vintage, model/config, fork snapshot or security boundaries.
7. **Fork precise history; converge by artifact.** `from` captures a specific trail cut and evidence world. Reconciliation publishes a new result citing branch outputs; it never merges transcripts or mutates ancestors.
8. **No invisible execution.** Record model-visible context manifests, PTC cells, tool requests/results, explicit published rationale and causal links. Never claim to store hidden model chain-of-thought.
9. **No unnecessary recomputation; no hidden drift.** Exact unchanged dependencies reuse cached results without LLM calls. Changed but immaterial evidence may create a validation record or belief update while the *decision* remains stable. Dependency propagation cuts off only on explicit equivalence of the specific consumed exports.
10. **No unearned stability.** Detect new matches to previous queries, cumulative small changes, stale freshness deadlines and previously unseen sources. Conservatively reassess when relevance cannot be ruled out.
11. **Authority is not information.** Peer messages can carry evidence without granting permission to disclose, interrupt, reopen or authorize action.
12. **Investment schemas are a profile.** The core knows no CPI, instrument, probability or thesis ontology. Typed forecast/decision contracts and grading live outside the kernel.

## Native API compatibility

| Native operation | v4 contract, preserving v3's surface |
|---|---|
| `readNode({node})` | Bounded, pinned optional skill/procedure read; consult does not execute. |
| `readArtifact({ref,offset?,limit?})` | Bounded immutable reads of source/result/artifact, virtual index, node record, evidence timeline, or trajectory projection; records access and enforces grants and historical cutoff. |
| `openNode({request})` | Nonblocking start/join/reuse/fork; returns handle, node and disposition; creates caller lease. Model may omit skill. Exact task identity includes snapshot, authority and configured executor. |
| `nextNodeEvent({after?,filter?})` | Cursor-based ordered view of authorized events; waits when no relevant event; no guaranteed background polling, no dropping committed records. |
| `closeNode({handle})` | Idempotently release one hold; last-holder cancellation drains safely. |
| `publishCheckpoint({content,to?})` | Atomically publish immutable evidence/partial result and optional addressed message; refs validated and event emitted. Delivery need not force a model step. |

A final agent message is the next versioned result; wrappers such as `nodes.run()`, `nodes.with()`, `nodes.fork()` and `nodes.converge()` are ordinary PTC code. The host must supply stable extension points for adapters, observability and context builders without expanding these six model-facing effects.

## Separation of graphs

- **Authorship graph:** optional skills/procedure links, never a required execution plan.
- **Execution/liveness graph:** tasks, attempts, waits, leases, joins, cancellations and resource constraints.
- **Collaboration graph:** addressed checkpoints, steering, knowledge exchange, challenges and settlements.
- **Evidence/provenance graph:** source versions, actual reads, cites, derives, contradicts, supersedes and conditional conclusions.
- **Incremental-dependency graph:** exact inputs/query subscriptions and application-defined consumed output projections. Updated deterministically where possible, judged by the model where necessary.

A child-model call is an *execution choice*, not the only way to produce an atomic, citable artifact.

## Three timelines

- **Evidence timeline:** real-world/valid time, source publication, entitlement-adjusted availability, ingestion, and actual observation.
- **Reasoning timeline:** externally published hypotheses, calculations, rationales, forecasts, validations, counterarguments, decision revisions and outcomes.
- **Execution timeline:** host event sequence and causal parentage, model/tool/PTC operations, joins, messages, forks, resumes and failures.

All are reconstructable, but they are not one chronological list: parallel causality requires explicit edges. The first two are derived projections across immutable artifacts and the canonical journal.

## Recommended architecture

```text
Agent / PTC executor (single session OR async workers; optional skills)
     | six host calls; typed authorized tool SDK
Execution supervisor --- scheduler --- context builder/compactor
     |                    |
Canonical append-only journal + durable operations / leases
     |                         |
Content-addressed artifact store | immutable trajectory entry chains
     |                         |
Rebuildable indexes: run views, provenance, timeline, reads, subscriptions
     |
Optional domain profiles: investment PIT evidence, forecasts, thesis versions
```

**Physical prototype:** SQLite WAL transactions plus content-addressed local blobs; DuckDB/Parquet for analytical market snapshots; extension adapters for data sources. PostgreSQL/object storage are deployment options, not new model primitives. Artifacts are committed only after their blobs are durably staged; missing blobs cannot be published.

## State and safety

- Task identity is separate from retry idempotency; failed attempts, deliberate independent checks and completed-result reuse have explicit semantics.
- Subagents share only authorized, immutable artifacts. In-flight identical work may be joined; forks deliberately create independent trajectories. Default sharing must never silently share time-dependent data across inconsistent snapshots.
- Each event is committed once under a global sequence and causal parent. Node streams are cursor-based views, not physical per-node copies.
- A sender can append an addressed checkpoint. A *steer* intent may prompt a safe turn-boundary wakeup only when authority and rate limits permit. Peer evidence does not automatically force an expensive reopen.
- The model can inspect its own trail, compare branches or query graph projections through bounded `readArtifact` views. A branch inherits an immutable prefix, never a live mutable pointer.
- Recovery guarantees initially stop at recorded model-turn/PTC-cell boundaries; replay uses recorded tool effects and adapter-level idempotency. Live interpreter continuation at arbitrary instruction offsets is **not** promised.
- Full transcripts and tool results remain audit records; compactions are linked, replaceable context projections. They never overwrite originals.
- Runs and artifacts carry label/grant scopes; references alone confer no authority. Enforce information walls, source-license restrictions and retention/redaction duties.

## Documents (normative within this proposal)

1. [Execution and coordination](execution.md) — identity, state machines, six calls, fork/join/settle, scheduling, optional skill graphs.
2. [Storage, trajectories and timelines](storage.md) — event/artifact schema, branch heads, recovery, context projections, retention.
3. [Incremental computation](incremental.md) — stable decisions, subtle belief changes, dirty propagation, early cutoff and update races.
4. [Investment research profile](investment.md) — bitemporal evidence, explicit forecasts and probabilities, scenario worlds and outcomes.
5. [Adversarial review and milestones](review-and-milestones.md) — known risks, required tests, build order and rejection criteria.
6. [IR-30 benchmark protocol](../../benchmarks/ir30/README.md) — reproducible 30-minute four-arm evaluation and executable offline scorer.

## Status and proposed phases

| Phase | Deliverable | Status |
|---|---|---|
| V3 baseline | September callable skill-graph runtime; v3 six-call redesign | September runtime implemented; **v3 redesign specified, not implemented** |
| V4-A | Versioned event/artifact substrate and six-call conformance | Proposed |
| V4-B | PTC runner, precise forks, inspectable trails, async sharing and convergence | Proposed |
| V4-C | Historical evidence/timeline profile and incremental maintenance | Proposed |
| V4-D | Crash/restart, security, point-in-time replay and shadow research | Proposed |
| IR-30 | 40 held-out scenarios × 4 arms × 3 runs | Protocol/scorer only; **no live runs claimed** |

## Borrowed mechanisms, not dependencies

- [Pi](https://github.com/badlogic/pi-mono): branchable sessions, compaction and extension hooks.
- [Dim](https://github.com/arcships/dim): event-sourced timelines, branch lineage and append/steer distinction. No automatic transcript merge is claimed.
- [Factory frontier harness](https://factory.com/news/frontier-harness): compact PTC output, stable prompt prefixes and background completion.
- [Temporal](https://docs.temporal.io/encyclopedia/event-history): durable event histories and replayable operations, with separately handled external side effects.
- [G-1F v1 kernel](../kernel-spec-v1/harness-kernel-spec.md): two clocks, read-tracking, scenario forks and early cutoff.

**Bitter Lesson test:** if models become substantially better, the kernel should keep doing less *judgment* but retain the same history, concurrency, integrity, recovery, and reference guarantees.
