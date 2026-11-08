# Storage, trajectories, evidence timelines and recovery

**Status: proposed.** The event journal is authoritative for execution transitions; immutable artifact payloads are authoritative for evidence and model/tool results; all graph and timeline views are indexed projections.

## 1. Physical storage and transaction boundaries

Prototype: **one SQLite WAL database** for events, identities, relations, branch heads, visibility labels, read indexes and durable checkpoints; **content-addressed blob files** for payloads; **DuckDB/Parquet** for optional historical analytical data. Keep a provider-neutral storage interface; do not impose a separate database per node. Later PostgreSQL and object storage should preserve the logical contracts.

Transaction for publishing a source/checkpoint/result:
1. Serialize canonically; compute digest and validate references, labels and size.
2. Write large blob to staging, flush, atomically finalize content-addressed location.
3. In one DB transaction: insert artifact metadata, provenance edges and journal event; advance cursor/result pointer or perform expected-head CAS if authorized.
4. Commit transaction. Consumers never see an event whose artifact is missing.

Garbage-collect orphaned *staged* blobs after crash. Do not garbage-collect historical referenced blobs solely because no current branch points at them; retained old heads, forks and audit policies count as roots.

Every event has at minimum: `event_id, seq, run_id, branch_id, actor_id, node_id?, attempt_id?, kind, recorded_at, caused_by[], payload_ref?, schema_version, security_scope`. `seq` orders DB commits; `caused_by` captures actual causality, which timestamp order alone cannot prove.

## 2. Minimal schema, with explicit projections

```sql
CREATE TABLE events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT UNIQUE NOT NULL,
  run_id TEXT NOT NULL,
  branch_id TEXT,
  node_id TEXT,
  attempt_id TEXT,
  event_type TEXT NOT NULL,
  payload_ref TEXT,
  recorded_at TEXT NOT NULL,
  schema_version INTEGER NOT NULL,
  security_scope TEXT NOT NULL
);
CREATE TABLE artifacts (
  artifact_ref TEXT PRIMARY KEY,
  sha256 TEXT NOT NULL,
  kind TEXT NOT NULL,
  payload_location TEXT NOT NULL,
  created_seq INTEGER,
  schema_version INTEGER NOT NULL,
  security_scope TEXT NOT NULL
);
CREATE TABLE relations (
  source_ref TEXT NOT NULL,
  relation TEXT NOT NULL,
  target_ref TEXT NOT NULL,
  observed_seq INTEGER NOT NULL,
  selector_ref TEXT,
  PRIMARY KEY(source_ref, relation, target_ref, observed_seq)
);
CREATE TABLE branches (
  branch_id TEXT PRIMARY KEY,
  parent_branch_id TEXT,
  cut_entry_ref TEXT,
  world_ref TEXT NOT NULL,
  current_head_ref TEXT NOT NULL,
  head_revision INTEGER NOT NULL
);
CREATE TABLE trajectory_entries (
  entry_ref TEXT PRIMARY KEY,
  parent_entry_ref TEXT,
  session_id TEXT NOT NULL,
  branch_id TEXT NOT NULL,
  event_seq INTEGER NOT NULL,
  entry_kind TEXT NOT NULL,
  payload_ref TEXT NOT NULL
);
CREATE TABLE validations (
  validation_ref TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  decision_ref TEXT NOT NULL,
  baseline_world_ref TEXT NOT NULL,
  validated_world_ref TEXT NOT NULL,
  coverage_ref TEXT,
  event_seq INTEGER NOT NULL
);
```

Also implement transactional `attempts`, `leases`, `tool_effects`, `access_grants` and `subscription_indexes` tables; their exact migration schema is an implementation task, not an invitation to elide durable effects. `relations` must carry typed provenance such as `observed`, `cited`, `derived_from`, `supersedes`, `contradicts`, `forked_from`, `reconciles`; a read is not evidence of logical support.

**Virtual artifacts:** `run` (index), `nK` (node record), `nK.trail` (trajectory projection), and a timeline query view are generated from indexed immutable state at a pinned cursor. A view name alone is not immutable; callers recording dependencies must retain the query, cutoff and result-set fingerprint.

## 3. Recorded trajectory

Persist for every model turn:
- model/provider/version, sampling configuration, effective prompt/context **manifest** and hash, model-visible messages (subject to retention), input/output token accounting and cost;
- incoming event cursor and exact addressed/held-work notifications delivered;
- explicit published assumptions/rationale, claims and referenced artifacts (not hidden chain of thought);
- code/PTC source, sandbox/tool bindings, outputs and errors;
- every tool invocation and outcome (including PTC subcalls), idempotency key, evidence read/vintage and artifact ref;
- compaction events: which immutable entries were included, which summary artifact replaced their prompt projection and which refs remain open.

Persist host state transitions, cancellation, join/lease events and context switches as event records. Preserve full tool results as bounded artifact blobs even if model only saw a filtered subset. Mark data the model was **shown** separately from data that a tool or code program **processed**.

A trajectory is a branching chain of immutable entry refs. On fork, the new branch links to its exact immutable parent entry/cursor and world snapshot; it does not copy the physical prefix. On resume, append new entries to the *same* authorized session lineage. An `entry_ref` is never implicitly upgraded to the branch's newest entry.

## 4. Forking: two independent dimensions

- **Context fork:** select exact model-visible trail prefix; can reuse provider prompt prefix and preserve prior analyst framing.
- **World fork:** select exact evidence/assumption snapshot, possibly with new hypothetical scenario inputs; no later source versions may leak into a historical branch.

For truly independent bull/bear analysts, prefer **the same evidence-world snapshot plus separate independent reasoning contexts**. Forking the whole prior reasoning trail carries anchoring. Both modes must be expressible via `openNode({from, task, ...})`, with `from` resolving precise immutable refs.

A scenario may be defined and retained without immediately running its model branch. Such a lazy branch is a versioned scenario specification with a future trigger, not a suspended live JavaScript heap. When the trigger occurs, instantiate a new execution at the pinned historical cut plus newly authorized observations; do not assume the hypothetical assumptions proved true.

## 5. Context post-processing

**Never rewrite the canonical history to compact.** Maintain separately:
1. Raw committed trajectory (audit/recovery authority);
2. Structured projections (current evidence, decisions, unresolved questions, dependencies and indexed search);
3. Replaceable compaction manifests for model context construction.

A compaction artifact records `source_trail_ref, through_entry_ref, source_history_hash, generated_by, prompt_manifest_version, summary_ref, referenced_evidence_refs, unresolved_questions`. Later model requests can reopen original entries via bounded `readArtifact`. Compact at model-turn boundaries, and retain compaction's precise source and scope. New summarizers may regenerate a different context view without rewriting history.

When data is redacted under retention requirements, retain permitted integrity/tombstone metadata and explain that full payload replay is no longer available; content addressability does not waive deletion obligations.

## 6. Recovery and replay

Five distinct operations:
- **Inspect:** display immutable historical record, no effects.
- **Resume:** continue an authorized logical session from a durable boundary and its committed state.
- **Fork:** create independent continuation from a specific history/world cut.
- **Audit replay:** reconstruct what happened using stored records without re-executing the tools or model.
- **Re-execute:** run with a new model, prompt, data snapshot or scenario, compare outputs, never overwrite the old run.

Initial guarantee: durable **model-turn and PTC-cell** boundaries, not arbitrary JavaScript program counter persistence. A recorded tool-effect ledger distinguishes `planned`, `started`, `committed`, `failed` and `reconciled`; replays use completed effects instead of repeating them. Side-effecting tool adapters require idempotency/fencing and explicit crash-gap handling. A failure after external effect but before durable result may require reconciliation and cannot be declared exactly-once.

## 7. Time and revision semantics

**Evidence records:** `event_time` or valid interval, `published_at`, `available_at` (under the stated source/vendor/access policy), `ingested_at`, `observed_at` (per read), `content_hash`, `source_revision`, immutable locator, and `supersedes` edge if corrected.

The following questions have different answers:
- *What was knowable at T?* Filter by source-specific availability and entitlement; missing reliable availability fails closed.
- *What did this system know at T?* Additionally require ingestion and recorded reads/observations.
- *What do we know now about the event at T?* Use latest authorized corrective vintages while preserving original history.

`event_time` cannot substitute for `available_at`. Every backtest/research decision records a frozen `world_ref` or exact cutoff policy. Revised macro observations and filings create new source artifacts, never mutate the old one.

**Timeline edit history:** edits are correction/retraction/reinterpretation events and successor artifacts. The current timeline is a projection over accepted branch heads; the historical timeline at seq S is reconstructed from records committed by S. Branch heads advance via compare-and-swap on `head_revision`; losing concurrent commits remain as unadopted candidates.

## 8. Retention and cleanups

- Never compact away authoritative events to save model context.
- Referential GC first computes reachability from *all retained* branch heads, forecasts, decisions, source contracts, active executions and audit holds, then applies retention policy.
- Remove scratch PTC variables and transient token deltas unless explicitly committed or required by a declared audit policy.
- Rebuild search/graph indexes instead of preserving every obsolete projection.
- Keep metadata tombstones when legitimate deletion removes payloads; historical audit then reports unavailable content rather than fabricating it.
- Use schema-versioned event readers and migration/reprojection tests; never silently rewrite older evidence.

## 9. Acceptance tests

Crash at every publication stage: no committed event refers to a missing artifact. Fork after a parent advances: child retains original cut. Two simultaneous head updates: one CAS wins, no lost candidate. Rebuild all projections from journal+blobs and reproduce hashes. Reconstruct a historical CPI/filing cutoff without future vintage leakage. Recompact a session and verify that raw trajectory refs are unchanged. Detect new results matching a previously recorded query. Redact a payload and verify access denied with explicit audit tombstone.
