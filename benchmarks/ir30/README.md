# IR-30 — 30-minute investment research benchmark

**Status: reproducible protocol proposal, not a completed study.** `score_anytime.py` is an **offline metric aggregator**, not an investment-answer grader. The 40 held-out cases, provider adapters and live four-arm runners are **not included**; completion of those items is a milestone, not a claimed result.

**Design question:** Under a hard 1,800-second deadline, does v4 async, evidence-backed graph execution produce higher-quality and more timely research than strong single-agent PTC, serial delegation or synchronous parallel workers? Does selective refresh maintain stability without missing material evidence?

See [v4 spec](../../docs/harness-spec-v4/README.md) and [incremental contract](../../docs/harness-spec-v4/incremental.md).

## 1. Pre-registered hypotheses

- **H1 primary:** v4 **D** exceeds synchronous-parallel **C** on *anytime evidence-grounded quality* (0–30 minute area under quality curve).
- **H2:** D's terminal quality at 30 minutes is noninferior to C by no more than **5/100 points**.
- **H3:** D exceeds strong single-agent PTC **A** on unique supported evidence/claim throughput in parallelizable cases.
- **H4:** On no-op/immaterial source changes, D avoids wasted model calls and unnecessary material decision revisions; on material updates, missed-revision rate is not worse.
- **H5:** D offers a favorable quality/cost frontier rather than winning solely by using more parallel model tokens.

H1 is one primary analysis, pre-register all remaining tests as secondary/exploratory. Do not count false or duplicated claims as throughput.

## 2. Four arms on one shared substrate

| Arm | Model execution | Allowed patterns |
|---|---|---|
| **A Single agent + PTC** | One model session | Parallel tool calls, code, artifacts, citations, compaction, self-inspection; **no model subagents** |
| **B Serial subagents** | Root plus children but at most one active model session | Delegate and await final child before next; parallel tool calls still allowed |
| **C Synchronous parallel** | Up to 4 workers | Root launches batch and awaits **all final results** before resuming; no intermediate steering or peer collaboration |
| **D V4 async graph** | Up to 4 workers | Nonblocking root, intermediate checkpoints, same-work join, peer reference inspection, addressed steering, selective fork and convergence |

All arms use the *same* model/provider build, instruction quality, PTC tooling, retrieval index, time-cutoff enforcement, immutable artifact store, source corpus, citation checker, output schema, authentication policy and source license. Restrict only the execution/communication topology. A must not be hamstrung by inferior data access. B/C may share artifacts as allowed by their topology; D's advantage is asynchronous orchestration and graph collaboration, not secretly better tools.

**Optional exploratory ablations:** D minus peer messages; D minus intermediate checkpoints; D minus in-flight work sharing; D minus fork; D with summary-only handoffs; D with full artifact refs; A without artifact graph. These are not substitutes for the four primary arms.

## 3. Clocks and controls

Each episode begins at monotonic `elapsed_s=0` on initial task and source portal release. Hard stop at **1,800 seconds**, including model queuing, tool/SQL executions, retries, provider wait, context rebuilding, worker boot, messaging and all compaction. Any work finishing later gets no research credit. Human scoring occurs after stop.

A separate historical **information cutoff** determines which source vintages are allowed. Tool/data adapters enforce `available_at <= as_of` and all entitlement/snapshot constraints. For "what the agent actually knew", use ingested/observed evidence. Historical source time must never be inferred from event period alone. Synthetic cases must have precise release clocks; real cases must document conservative or unknown publication availability. A point-in-time violation is a critical reliability failure.

Freeze model build, temperature/sampling parameters, prompts (except allowed topology switches), tool versions, rate limits, price table (including cache token tiers), infrastructure sizes and retry policy. Model usage/cost is aggregate over **all** workers. Provider outages and block reruns require written rules *before* inspecting held-out scores.

## 4. Suite and randomization

- **Development:** 12 calibration cases, used for prompt, retrieval and quota setup; never enter primary statistical claims.
- **Held-out:** 40 cases, four task families × 10 cases, each family 5 archival real-data + 5 deterministic synthetic cases.
- **Replications:** 3 independent calls per arm and case; 40 × 4 × 3 = **480 episodes**, up to **240 execution-hours** total before campaign parallelism.
- **Blocked randomization:** within each case/repetition, randomize order of arms; never starve one arm with another arm's provider requests.
- **Blind grading:** remove all topology identifiers from thesis artifacts presented to human graders.

Families:
1. **Breadth:** many orthogonal investment facts, filings, macro or supply-chain questions where parallel evidence gathering could help.
2. **Depth:** sequential financial accounting/model construction where delegation may harm; designed as a negative-control task class.
3. **Convergence:** branches independently require one common immutable data producer or calculation; tests duplicate execution and handoff loss.
4. **Standing-thesis delta:** start with identical pre-seeded versioned thesis; inject a duplicate/irrelevant event, a relevant-but-non-material event, and a material decision-changing event.

Cases must have uniquely graded facts and calculations, pre-specified source locators, resolvable claims and alternatives. Gold answers and hidden event labels are sealed from tested agents. A deterministic case builder should write immutable source/version manifests with SHA-256 checksums and permissions; license terms control redistribution. A research protocol without published case manifests/source snapshots is **not** fully reproducible.

## 5. Matched resource ceilings

| Parameter | Initial fixed ceiling |
|---|---:|
| Deadline | 1,800 s |
| Aggregate model dollars | $25 |
| Input tokens | 300,000 |
| Output tokens | 60,000 |
| Model concurrency infrastructure | 4 slots |
| Concurrent tool operations | 12 |
| Tool calls | 300 |
| Active task nodes | 24 |

A/B topology restricts model concurrency to one without preventing parallel tool execution. C/D may use up to four model slots. These initial limits are **proposals**; calibrate on development cases then freeze. Record provider inference queueing, cached token accounting, actual dollars, retries, per-node active time and source fetch work.

Primary study is **fixed deadline under common ceilings**. This intentionally allows multiagent systems to spend more tokens per minute. Report secondary **matched-realized-cost and token-budget sweeps** to disentangle quality/latency from parallel compute spending.

## 6. Episode timeline and updates

Checkpoints `t = 0, 300, 600, 900, 1200, 1500, 1800` seconds. Each is a **read-only snapshot** of already committed artifacts. The grader must not generate a new agent continuation at scoring time. If no current thesis is published, decision-related score is 0; objective intermediate artifacts are counted separately in evidence-throughput metrics.

For family 4:
- `t=0`: frozen original thesis and as-of snapshot `world:T0`.
- `t=480` (8m): duplicate or unrelated event; a byte-identical duplicate should cause **0 new model calls**.
- `t=900` (15m): relevant but not decision-changing evidence. Validation or belief update may be justified; a new material decision must not be forced.
- `t=1320` (22m): material, independently graded evidence requiring at least one specified decision-relevant revision by 30m.

Do **not** tell agents the event labels, times or gold revision criteria. Include adversarial cases with large immaterial updates and small threshold-crossing updates. An update is delivered according to both the episode elapsed clock and historical evidence availability gate. Source corrections create additional immutable versions. Score both missed revisions and unnecessary changes.

## 7. Required output and evidence contracts

Each provisional/final thesis must be serializable to a stable schema, validated before grader ingestion:

```json
{
  "case_id": "masked-case-id",
  "as_of_world_ref": "world:T0",
  "decision_ref": "n1.r1",
  "conclusion": {
    "action": "hold",
    "rationale": "Short explicit explanation",
    "confidence": 0.65
  },
  "claims": [{
    "claim_id": "c1",
    "statement": "Hypothetical claim",
    "citations": [{
      "artifact_ref": "src:example@v1",
      "selector": {"section": "table-1"}
    }]
  }],
  "alternatives": [],
  "limitations": [],
  "provenance": {
    "model_version": "pinned",
    "source_snapshot": "world:T0",
    "trajectory_ref": "n1.trail"
  }
}
```

If the agent cannot justify an answer, an explicit abstention with evidence gaps is better than an unsupported claim. Commit intermediate material assessments as versioned artifacts during the episode; the benchmark cannot credit uncommitted drafts after timeout.

A forecast record must include mutually exclusive and exhaustive scenarios if probabilities sum to one, a resolution rule frozen at forecast creation, as-of world and horizon. Forecasts are never retroactively edited after outcomes.

## 8. Scoring, objective gates and blinded review

Score 0–100 for each published thesis snapshot, using **only sources released by that snapshot time**:

| Category | Weight | Measurement |
|---|---:|---|
| Financial facts and calculations | 30 | Precomputed gold values, periods, units and reconciliations |
| Evidence provenance and citations | 25 | Source/vintage correctness, locator validity, support and required coverage |
| Decision quality | 25 | Pre-registered case-specific inference/action rubric |
| Alternatives / disconfirmation | 10 | Key sensitivities and counterevidence identified |
| Audit / reproducibility | 10 | Exact reference, tool/snapshot/version lineage reconstructable |

Facts, arithmetic, source version and citation span validity should be deterministic when possible. Qualitative support/decision checks require **two independent blinded graders** and a pre-registered reconciliation rule. Include an adjudication record; if graders disagree beyond a threshold, escalate rather than cherry-pick.

**Reliability gates:** A future source used before authorized availability, an unauthorized data read, fabricated source reference, or critical material unsupported conclusion is separately counted and can trigger a pre-registered disqualification/penalty. Don't bury safety failures inside a weighted score.

### Primary anytime quality

Define `Q(t)` as the 0–100 grade of the **most recent committed current thesis** at minute `t`, not the best retrospective output. Integrate `Q(t)` over 0–30 and normalize:

```text
AUC_Q_30 = (1/30) * integral_0^30 Q(t) dt
```

For version 0.1 use a declared **left-step interval** approximation on minutes `[0, 5, 10, 15, 20, 25, 30]`, so scores on the first six checkpoints contribute duration 5 minutes each; the last is terminal quality. Reports must state this convention and not reinterpret it as continuous-time integration.

### Other outcomes

- `Q30`, first defensible thesis time, time-to-material-correct-revision and post-update staleness duration;
- unique **verified** claim/evidence coverage per minute (deduplicate by source/claim equivalence adjudicated before report);
- duplicate live producers avoided, work reuse, time spent awaiting dependencies, root blocking, event fan-out cost;
- handoff evidence recall when critical evidence is accessible upstream vs present in final assessment;
- PTC/tool/model invocations, tokens in/out/cache read/write, all-in USD, provider wait and retries;
- unnecessary model calls on no-op delta, unchanged-recommendation rate, belief-change tracking, missed material revision;
- unsupported citation rate, point-in-time violations, security violations and audit replay completeness.

No model or agent receives the grading rubric beyond generic disclosure that accuracy, evidence and supported reasoning matter.

## 9. Statistical plan

**Primary effect:** paired per-case difference `AUC_Q_30(D) - AUC_Q_30(C)`. Average three repetitions per case and perform paired, stratified bootstrap resampling **cases**, stratified by family (not independent model outputs), for a 95% confidence interval. Pre-register bootstrap seed, replicate count and multiplicity handling for secondary outcomes.

**Terminal noninferiority:** lower bound on `Q30(D)-Q30(C)` exceeds −5/100. Also report D versus A and interaction by task family, particularly whether D degrades tightly coupled sequential cases.

**Cost control:** besides fixed deadline, report budget-sweep curves and quality at realized cost, transparent provider pricing, cache discounts and runner overhead. If D wins only by consuming substantially more dollars and has no attractive quality-cost frontier, classify the result as mixed.

**Decision thresholds:** Positive if primary CI lower bound >0 and terminal noninferiority holds with no critical reliability regression. Strong if D also outperforms A on parallelizable families and offers a favorable cost-adjusted frontier; neutral/mixed/negative findings are first-class outcomes.

## 10. Reproducibility requirements

Freeze and publish:
- dataset case/source manifests, license/access instructions, content digests, historical availability conventions;
- evaluator source and grading keys after holdout completion; grader inter-rater agreement;
- prompts, models, provider build, sampling, PTC/tool versions, code runner, search indexes, pricing, quota and resource ceilings;
- randomized arm order, independent sample IDs, exact monotonic clock, runtime events, per-agent billing, all intermediate published snapshots;
- case revision/change event feed, source corpus and all admitted tool result refs;
- report generator and checksum ledger; publish every failure and timeout, not only successful cases.

Suggested fixture schema in [case_schema.json](case_schema.json). Config in [benchmark.json](benchmark.json), sample scored snapshots in [example_scored_checkpoints.jsonl](example_scored_checkpoints.jsonl), and an offline sanity checker in [score_anytime.py](score_anytime.py).

### Offline scorer

```bash
python benchmarks/ir30/score_anytime.py \
    benchmarks/ir30/example_scored_checkpoints.jsonl
```

This aggregates **already graded** scores and cannot judge financial fact correctness. It is not a substitute for real model runners, point-in-time source gating, source entailment grading, and calibrated benchmark data.

## 11. Explicit limitations and anti-gaming rules

- No claim of measured v4 speedup, accuracy or dollars until experiments run.
- Do not count artifacts alone as useful work; score correctness and supporting evidence.
- Don't infer improved investment returns from attractive thesis text or benchmark QA.
- Do not let "same recommendation" erase probability/risk revisions relevant to downstream consumers.
- A system that suppresses all updates is penalized by hidden material-change cases.
- A system that repeatedly regenerates a report gets no extra credit unless the current committed quality improves.
- Any published tentative answer must be versioned and subject to the same point-in-time and citation checks.
