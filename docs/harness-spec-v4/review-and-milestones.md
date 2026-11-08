# Adversarial review, open decisions and implementation milestones

**Status:** preimplementation design review. Assertions about throughput, stability, latency and quality are **hypotheses until live tests pass**.

## 1. Bitter Lesson / generality test

Native kernel operations should be required **only** for effects ordinary PTC cannot enforce correctly: admission, authority, durable ordered observation, immutable access, publication and cancellation. Do **not** add an LLM-centric `decide`, `review`, `settle`, `converge`, `timeline`, `reflect`, `SQL`, or `recompute` host operation.

The kernel's mechanisms remain useful as models improve: exact data versioning, scoped immutable citations, concurrent leases, event delivery, recovery and artifact integrity. Judgment remains a model/domain choice. Skill graphs are merely optional procedure maps and should not be mandatory for any test.

Counterargument: if one strong PTC agent plus a durable artifact graph performs as well as v4 async graph workers, the subagent orchestration complexity is not justified. Keep both modes using the same substrate and benchmark fairly.

## 2. Adversarial issues and required decisions

| Risk | Failure | Current design decision / adversarial test |
|---|---|---|
| Shared-work staleness | byte-identical task reused with changed market data | Bind work to world/vintage/config/scope; test changed vintage never joins old producer |
| Overaggressive exact sharing | independent bear critic joins bull producer | explicit independent identity and evidence-only forks; evaluate correlated error |
| Peers reopen each other forever | unbounded churn and costs | peer message is information; authority/budget governs wake; test reopen loops |
| Broadcast every line | O(nodes × events) fan-out/context churn | one event journal, indexed lazy views, priority notifications and backpressure |
| False evidence support | cited fact doesn't imply claim | check ref integrity mechanically and semantic entailment separately |
| Hidden future leak | revised macro value appears in historical backtest | enforce available_by in the tool gateway and vintage/snapshot identity |
| Missed unseen news | only previous reads trigger invalidation | record query predicates/negative reads and run discovery subscriptions |
| Small-delta drift | 68→65→61→57→53 never triggers reevaluation | compare cumulative change from last fully validated baseline |
| No-change gaming | model always reaffirms, low cost but wrong thesis | hidden material-update cases and missed-revision penalty |
| Unnecessary decision churn | wording differs though action/exports equal | material decision head separate from belief/validation artifacts |
| Probability misuse | winning branch retroactively promoted as accurate forecast | immutable scenario probabilities/resolution rules and real-world reassessment |
| Transcript-merge illusion | conflicting branch worlds silently mixed | convergence produces *new artifact*; CAS selects accepted head |
| Crash halfway through tool | duplicate external effect | effect ledger and adapter idempotency/reconciliation; fault injection |
| Context compaction loss | source omitted from summary and unrecoverable | raw trajectory immutable; projections retain hashes/anchors and can be regenerated |
| Race on updates | old validation certified as latest world | pin per-refresh world, CAS heads, carry forward pending evidence |
| Security laundering | ref in peer message accesses restricted artifact | non-transitive grants; read authorization at every boundary |
| Storage accumulation | audit history grows unbounded | policy-aware retention/GC; derived index rebuild; tombstones |
| Cost/quality tradeoff | parallelism wins by using many more tokens | fixed-deadline primary plus matched-dollar Pareto analysis |
| Synchronous vs async unfairness | D has better tools, retrieval or source access | same kernel and tools in all benchmark arms; topology-only changes |
| Lossy handoff | child summary omits crucial evidence | exact artifact pointers, selective original reads, handoff recall metric |
| Unverifiable hidden reasoning | audit claims model internal rationale | store only model-visible inputs and externalized explanation, never hidden CoT |

## 3. Remaining decisions: freeze via conformance

- **How to represent consumed exports:** application-declared typed field refs or versioned projections with default conservative invalidation. A generic host cannot infer economic materiality.
- **Who can ask a node to reopen:** user/owner authority, bounded delegated permission and receiver autonomy. Peer evidence alone never forces expenditure.
- **What if raw transcript must be deleted:** retention policies allow tombstoned payload refs, and audit honestly degrades.
- **How much context to fork:** exact trail cut or evidence-only context; no ambiguous live pointers.
- **How to evaluate matching queries:** persist precise predicates and source/version scope; avoid semantic similarity as a deterministic cache key.
- **How to resolve materiality under drift:** explicit previous conclusion and cumulative evidence diff; conservative validation with verifier where critical.
- **What is 'the same decision':** stable action identity alone insufficient. Per-consumer consumed exports determine invalidation.
- **When to attempt distributed execution:** empirical win over single-agent PTC, not one agent per atomic artifact.

## 4. Milestones with exit criteria

### M0 — Freeze contracts and fixtures

- Six API effect contracts, event schemas, canonicalization rules and failure/authority states reviewed.
- Port September main reference tests (previously reported 85 offline passing) and v1 kernel tests (previously reported 24 passing) into new semantics as relevant; these historical counts are **not** v4 pass claims.
- Freeze independent benchmark development/holdout split and source-vintage manifests.

**Exit:** deterministic schema/conformance suite, including negative tests, passes.

### M1 — Event/artifact kernel

- SQLite journal, content-hashed blobs, atomic publish, immutable refs, grants, indexed views, leases, read provenance and branch-head CAS.
- Rebuild projections after restart; test publication fault injection.

**Exit:** no missing committed artifacts, no lost updates, no unauthorized ref access.

### M2 — Live PTC and branching

- Typed tool adapter, stable prompt manifests, PTC tool effect capture, bounded output, fork at exact context/world cuts, self-inspection and compaction projections.
- Single-agent and skill-graph optional paths use the same kernel.

**Exit:** real model can create evidence artifacts, inspect old trail and fork; repeated audit replay reproduces recorded contents without re-invoking effects.

### M3 — Async graph execution and convergence

- Model workers run concurrently; root remains responsive; streaming checkpoints are consumed early; shared producers and per-holder leases; peer message delivery/steering with authority.
- Forked bull/bear perspectives converge into a *new* artifact while both branches remain unchanged.

**Exit:** deterministic contention/failure tests plus live real-model traces; demonstrate overlapping useful work in wall time.

### M4 — Investment evidence and incremental views

- Bitemporal evidence ingestion; historical world snapshots; source correction history; observed/cited/derived indexes; forecasts and resolution rules.
- Exact-reuse stability, cumulative delta tracking, selective invalidation and early cutoff with belief vs decision revisions.

**Exit:** zero look-ahead on synthetic PIT fixtures, no wasted LLM calls on identical worlds, and no hidden missed material revision on test deltas.

### M5 — IR-30 evaluation and production readiness

- Run four benchmark arms on identical data/model/service; report anytime quality, 30-minute quality, evidence support, latency, cost, invalidation and reliability.
- Add crash/recovery, information-wall, retention, source-license, exhaustion and monitoring tests.

**Exit:** only promote to production if research quality/reliability and cost/latency tradeoffs justify complexity; no autonomous trading in this milestone.

## 5. Empirical decision gates

1. **Correctness gate:** no look-ahead leakage or unauthorized cross-scope reads in deterministic fixtures; event and artifact integrity under crash injection.
2. **Incremental gate:** 100 no-op repeats use zero additional model calls; new query matches and cumulative small changes cannot escape validation.
3. **Quality gate:** blind financial grader must show supported conclusions and timely handling of important counterevidence. A pretty audit trail alone does not count.
4. **Throughput gate:** compare v4 async graph against synchronous parallel and single-agent PTC at equal 30-minute deadline *and* matched-dollar analyses.
5. **Negative-case gate:** if async graph underperforms on tightly coupled sequential cases, the runtime must support doing those cases in one session without penalty.

## 6. Links to benchmark

[IR-30](../../benchmarks/ir30/README.md) specifies hypotheses, case generation, randomization, fairness, scoring and reporting. Its example scorer is a plumbing sanity check, not a financial quality judge.
