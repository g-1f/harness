# Incremental reasoning, stable conclusions and subtle updates

**Status:** Design specification; neither the graph-based refresh algorithm nor its empirical gains are implemented. **Goal:** repeated runs with the same authorized data return an identical existing decision *without model calls*; new observations are never erased; only decision-relevant changes propagate.

## 1. Separate four clocks/states

A thesis holds four independently advancing records:

1. **Source/evidence history:** immutable new records, revisions, contradictions, provenance and availability.
2. **Belief history:** changes in assumptions, forecasts, uncertainty, confidence, distributions and scenario probabilities; changes may be subtle but cumulatively important.
3. **Decision history:** material action/risk/position recommendation or conditional decision premise versions.
4. **Validation history:** explicit checks of an existing decision against a newer evidence-world snapshot, including the last fully validated baseline, reviewed changes and a coverage watermark.

A validated unchanged decision **keeps the same decision ref** (e.g. `n7.r1`), but appends a validation artifact. A revised probability may produce a new belief artifact even while the action stays stable. Consumers depending on that probability must be eligible for refresh. Do not globally interpret "same action" as "all outputs unchanged."

## 2. Dependence is explicit and fine-grained

At runtime record:
- actual reads (`observed`) with exact source vintage and selectors;
- explicit `cited` evidence edges, distinct from semantic support;
- `derived_from` for executed calculations and output artifacts;
- *negative/collection dependencies*: recorded query terms, predicate, scope, available-by cutoff, permission filter, source index and result-set fingerprint (so **newly matching documents** invalidate a formerly empty or incomplete query);
- application-defined downstream **consumed exports** (specific forecast, probability, assumption, or decision field), with immutable output signatures;
- temporal dependencies: expiry and refresh deadlines, even when no source changed.

Read and cited edges should remain separate: unquoted evidence can affect reasoning, while a citation does not prove entailment.

## 3. Algorithm: red-green with semantic checks

```text
refresh(task, desired_world):
  prior = last_validated(task)
  if canonical_inputs_and_dependency_versions_equal(prior, desired_world)
     and not expired(prior) and not query_scope_invalidated(prior):
       return prior.decision_ref             // 0 model calls, no new decision

  changed = gather_changed_source_versions_and_query_deltas(prior, desired_world)
  refresh_dirty_upstream_in_dependency_order(changed)
  delta = compare_exact_consumed_exports_and_cumulative_baseline(prior, desired_world)

  if delta.proven_empty and no_temporal_expiry:
       append_cheap_validation_if_needed()
       return prior.decision_ref

  // Do not guess economic immateriality from small numeric differences.
  candidate = model_reassess(previous_decision, previous_beliefs,
                             delta, available_sources, uncertainty, cutoff)

  validate_citations_source_vintages_and_contract(candidate)
  append_evidence_and_belief_records_if_changed(candidate)
  append_validation_record(prior.decision_ref, desired_world,
                           coverage=what_was_actually_checked)

  changed_exports = compare_consumed_exports(prior, candidate)
  if changed_exports.empty:
       return prior.decision_ref             // early cutoff for each downstream consumer
  else:
       new_decision_ref = publish_versioned_decision_if_material(candidate)
       invalidate_only_dependents_consuming(changed_exports)
       return new_decision_ref_or_prior_with_changed_beliefs
```

The early-cutoff check must compare **outputs consumed by each downstream dependent**, not raw natural-language text, not merely action category, and not a universal semantic similarity threshold. If declared exports are absent or equivocal, mark dirty and run a conservative assessment. This is a computational optimization, not a blanket license to hide changes.

The external `latest_validated_world` moves forward only on a completed, committed validation. If one process crashes midway, pending deltas remain and are reconsidered on recovery.

## 4. Cumulative delta and baselines

**Critical failure mode:** 68% → 65% → 61% → 57% → 53% may leave the same action on every adjacent step, but the cumulative change is economically meaningful.

Maintain:
```ts
type ValidationState = {
  decisionRef: string;
  lastFullyValidatedWorldRef: string;
  currentWorldRef: string;
  pendingChangedRefs: string[];
  reviewedQueryScopes: string[];
  lastValidationRef?: string;
  nextReviewAt?: string;
};
```

Compare pending changes against the last full validation anchor and, where necessary, the last *material decision* anchor; never reset pending changes merely because a latest adjacent change was individually small. Revisions in distributions, uncertainty and risk must be carried to consumers that depend on those exports even if the recommendation does not change.

## 5. Materiality is consumer-relative

The runtime can prove byte/value equality and dependency reachability. It cannot universally decide whether a 0.1% change alters an investment thesis. A tiny change may cross a covenant or liquidity threshold.

Therefore:
- The **domain profile** may publish named exports, confidence bounds, conditional decisions and decision invariants.
- The **model** decides how evidence changes an interpretation and may emit a justification for no material decision revision.
- The **host** verifies exact ref identity, output equality where specified, version/authority correctness, and which dependents consumed which fields.
- An optional **verifier** can challenge the support and completeness of a no-change assessment.
- Lack of reliable equivalence should trigger additional reasoning, not silent suppression.

This respects the Bitter Lesson without treating LLM random wording as a meaningful thesis revision.

## 6. Concurrent changes and out-of-order events

Every refresh pins a `world_ref`. If new evidence arrives while a refresh runs, its result may be committed as validation of that **older** world, but cannot blindly certify the latest world. Store the new pending delta and schedule another targeted refresh as needed. Commit decision changes with CAS on expected decision head; concurrent losing candidates remain auditable.

On bursty updates, coalesce *notification scheduling*, not source events. Batch within an explicit window and preserve timestamps/vintages. Handle withdrawn/revised data as distinct source versions. A late ingestion must never overwrite a more recent correction or rewrite a historical forecast.

## 7. Three restartable refresh outcomes

- **Exact/effective no-op:** no new source data, no deadline or query invalidation; zero model calls, no result/version changes.
- **Validation/no decision revision:** emit validation and optionally belief update; keep material decision ref; avoid unnecessary downstream work except dependents of changed belief exports.
- **Material revision:** publish new decision version with changed field refs, cause/evidence links; selectively invalidate dependent outputs. A consumer may then reaffirm its own output and stop further propagation.

A new discovery process must detect evidence nobody previously read, and a time deadline must re-evaluate expiring claims even without a source update. Avoid a system that looks stable merely because it misses news.

## 8. Evidence audit requirements

Every update decision answers: What changed? Since which baseline? Which new sources and vintages were available? Which were read? Which conclusions were revisited and why? Which exports moved? What did not move? What query scopes were rechecked? Where did propagation stop? Could the previous conclusion be reconstructed at its historical cutoff?

Material forecasts and prior probabilities are immutable. An outcome-resolution event must never rewrite the forecast that preceded it.

## 9. Tests and metrics

- 100 repeated refreshes with identical frozen world: exactly 0 additional model invocations and 0 decision versions.
- New unrelated source with no matching read/query subscription: no task invalidation; source still recorded.
- New document matching a previous empty search: invalidates affected query result set.
- Same recommendation but revised probability: belief version emitted; probability-consuming descendants notified.
- Sequential small changes accumulate and eventually cause evaluation against the last validated anchor.
- Parent upstream decision unchanged after targeted recompute: halt at affected export edge.
- In-flight update during refresh: no false validation through latest world.
- Time expiry without new data: appropriate reassessment.
- Forced independent reruns with identical evidence: report stochastic conclusion flips; do not confuse with ordinary cached refreshes.

Track wasted model calls, latency to justified revision, missed material changes, evidence freshness, stability, and false-positive invalidation separately.
