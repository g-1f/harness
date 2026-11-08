# Investment research profile — evidence, probabilistic scenarios and outcomes

**Status: optional proposed profile; generic host stays investment-agnostic.**

## 1. Domain boundary

The runtime stores immutable artifacts, events, versioned references, validated access, query projections and executions. Investment-specific extractors and validators may expose `source_observation`, `claim`, `assumption`, `forecast`, `scenario`, `decision`, `validation`, `outcome` and `resolution`. None is a mandatory native host type.

The same generic contracts should support software incident reviews, scientific experiments and legal research. Existing `SKILL.md` procedure graphs remain optional discovery hints and may be traversed through `readNode`/`openNode`.

## 2. Source/evidence contract

```json
{
  "kind": "source_observation",
  "source_ref": "src:vendor/report/v1",
  "locator": {"document": "filing", "section": "Item 7", "span": "p3"},
  "event_time": "2026-10-01T00:00:00Z",
  "published_at": "2026-11-12T13:30:00Z",
  "available_at": "2026-11-12T13:30:03Z",
  "ingested_at": "2026-11-12T13:30:05Z",
  "vintage": "initial",
  "content_hash": "sha256:...",
  "supersedes": null,
  "scope": "public"
}
```

All values above are **fictional schema examples**, not actual economic release dates. The authoritative source version must be pinned to exact bytes/segments, and provider-adjusted availability must be defensible. Historical backtests enforce `available_at <= cutoff`; "what our system knew" additionally requires ingestion/observation checks. Never conflate report period with publication time.

An exact citation is `{artifact_ref, version, selector}` with page, JSON pointer, row ID or text-span locator when available. The host verifies existence, matching digest and authorization; a verifier checks whether the source supports the claim.

## 3. Research artifacts and externalized reasoning

```ts
type ResearchDecision = {
  kind: "research_decision";
  decisionId: string;
  question: string;
  asOfWorldRef: string;
  horizon: string;
  action: string;                 // profile-defined, e.g. maintain/adjust/abstain
  explanationRef: string;         // explicit rationale artifact; NOT hidden CoT
  claims: string[];               // cited versions
  assumptions: string[];
  alternatives: string[];
  disconfirmingEvidence: string[];
  uncertaintyRef?: string;
  revises?: string;               // old decision revision
  validationRef?: string;
};
```

The reasoning timeline is a projection of explicit rationale/assumption/decision artifacts, not the agent's hidden thoughts. Facts, calculations, beliefs and decisions should be distinguishable. A quotation is not sufficient proof of support; semantic checking remains testable.

## 4. Scenario worlds: independent context and evidence

Two fork axes are independent:
- **Reasoning fork:** branch from a pinned trajectory entry; inherits previous analyst framing and may anchor a new investigator.
- **World fork:** copy-on-write hypothesis/evidence snapshot; inherited data fixed as of T0 and amended only by explicitly hypothetical overrides.

To create independently reasoned bull/bear cases, use the same T0 evidence world in **different fresh reasoning contexts**. Fork an existing model history only when a shared reasoning prefix is genuinely intended.

A conditional scenario artifact records `scenario_ref`, `world_ref`, assumption overrides, horizon, condition predicates, versioned resolution rule, and any assigned probability. Multiple scenario assessments can be reconciled into a separate artifact citing all contenders. Convergence never rewrites the underlying scenarios.

## 5. Probability and forecast contracts

```json
{
  "kind": "scenario_forecast",
  "forecast_id": "forecast:synthetic:1",
  "as_of_world_ref": "world:T0",
  "horizon": "12m",
  "scenarios": [
    {"ref": "scenario:bull", "p": 0.50},
    {"ref": "scenario:base", "p": 0.35},
    {"ref": "scenario:bear", "p": 0.15}
  ],
  "resolution_rule_ref": "rule:synthetic:earnings-v1",
  "source_refs": ["src:vintage-a"]
}
```

This is a hypothetical example. If scenario probabilities sum to 1, the scenarios must be explicitly mutually exclusive and collectively exhaustive; otherwise use overlapping event-probability statements with independently defined resolutions. Freeze probability assignments at publication; newer views create revisions and never rewrite prior forecasts.

**When the future event occurs:** append real source evidence, resolve the original probability forecast using its precommitted resolution rules, and create a separate actual-world assessment. A winning hypothetical branch **is not automatically promoted**: some of its assumptions can still be wrong. Reuse conditional calculations only after checking applicability to actual evidence.

### Deferred scenario execution

A "sleeping scenario" is a durable conditional task specification and trigger, not a suspended JavaScript VM. Trigger detection may instantiate a new execution against an authorized updated world, preserving the original T0 assumptions and forecast record. Keep execution costs under budget.

## 6. Timeline read views

Offer PTC-accessible, authorized query adapters such as:

```ts
// Illustrative research helpers, not additional host primitives.
research.timeline({subject, asOfWorldRef, orderBy: "available_at"});
research.sources({query, availableBy, scope});
research.forecasts({thesisRef, horizon, validAt});
research.explainRevision({oldRef, newRef});
```

The views must be anchored to a query spec, evidence snapshot and provenance refs. Index/query semantics must record both positive reads and *negative reads* (the query scope that returned no matching documents) for future incremental invalidation.

## 7. End-to-end synthetic case

1. T0: root thesis uses available economic and issuer releases, creates `decision.r1`.
2. Root creates shared data producers; two distinct analysts fork from the same evidence snapshot into bull and bear worlds.
3. Analysts publish checkpoints, inspect cross-branch calculations, challenge inconsistencies and reconcile into a new result citing both. The underlying forks remain immutable.
4. T1: a revised macro release is ingested; its old vintage remains intact. The evidence timeline records when it occurred, became available and was observed.
5. Rates node reassesses using the delta. Belief probabilities may shift modestly while headline investment action holds; validation records the unchanged decision and newly changed probability export.
6. A later relevant release invalidates a key decision premise. The root publishes `decision.r2` with a precise explanation of changed assumptions/refs. Only dependents of changed exports recompute.
7. At T2, a forecast outcome resolves; the recorded T0 probabilities and source vintages remain available for calibration, irrespective of whether the thesis was right.

## 8. Integrity and policy

Investment output is research, not permission to trade. All data source licenses, entitlement walls, confidential/MNPI labels and source provenance must propagate through reads and outputs as required by policy. Historical evidence cutoffs and access scope are evaluated in tools, not left to prompts. Never assert that an evidence citation or model conclusion proves market profitability.
