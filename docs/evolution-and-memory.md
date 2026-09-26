# Evolution, memory and deferred extensions

Status: design constraints and future work. None of the memory, supersession,
artifact-adoption, external-effect or durable-resume APIs below is implemented.
The current contract is [runtime.md](runtime.md). This document deliberately does
not present proposed names as callable tools or claim unexecuted verification.

## 1. Preserve the small transformation boundary

A new model, reviewer or deterministic utility can be an executor binding. A new
review policy can be application composition. A different question can be a new
request over explicit refs. These changes do not require new fields on every node.
Add a host primitive only when enforcing an effect, authority or lifetime cannot be
expressed safely through the existing boundary.

Convenience aliases and parsed bounded reads may be reasonable adapter improvements,
but need a compatibility story and executable examples. Returning an existing ref as
a new node's final result also needs a precise contract: authorization to adopt,
attribution of the new transformation, relationship to the original producer, and
whether a receipt or a new provenance record is produced. The present
`submitCandidate` stages a new candidate object; it cannot adopt `{ref}`.

## 2. Why automatic supersession is deferred

The reviewed draft proposed `repair: {of: bad.ref, because: audit.ref}` and redirecting
future requests for the original value to its repair. That protocol is not adopted.

| Problem | Required design before implementation |
| --- | --- |
| Repair used different task, inputs or refs | Preserve immutable request meaning; define an explicitly versioned alias if desired |
| Any readable non-pass audit authorizes replacement | Separate evidence access from mutation authority; authenticate the repair policy and scope |
| Host reads review verdicts | Keep domain schemas in trusted application composition |
| Missing dependencies | Track all necessary semantic dependencies, including decisions based on receipt summaries and external reads |
| Consumer already running on the old version | Define snapshot/epoch, cancellation and publication rules for in-flight consumers |
| Concurrent corrections | Serialize updates or use compare-and-swap with a visible conflict result |
| Cross-tenant or revoked evidence | Partition identity and validate authority at resolution and delivery |

Current safe behavior is explicit: create a new correction artifact, then issue new
consumer requests with the correction ref. Old artifacts remain evidence of what
was observed. A correction may cite the old result and review without rewriting them.
Recorded `input_refs`, `observed_refs` and `based_on` support investigation but are
not a complete causal graph. Do not advertise a three-of-seven invalidation result
without a committed test and a defined correctness criterion.

## 3. Memory as a versioned data source

Persistent memory should be data made explicit to an invocation, not inherited private
conversation state. A possible adapter would select authorized versions and grant
immutable evidence refs before execution. It would require at least:

- An immutable manifest identifying each source version and the retrieval/projection
  configuration used to select it.
- Separate effective/event time, source publication time and ingestion/knowledge time.
  A query's `as_of` alone cannot prevent retrospective corrections from leaking future
  knowledge; a knowledge cutoff and retained source vintages are also needed.
- Permission scope at retrieval and delivery, revocation semantics, and trust-domain
  partitioning. Possession of a content hash or a pinned registry is not authorization.
- A defined policy for stale, conflicting, absent and retracted evidence. “Latest” is
  a query over versions, not a mutable artifact ref.
- A place for the selected manifest identity in execution equivalence before any
  cross-session result reuse is introduced.

A persistent “head” is only a mutable pointer to immutable snapshots. Advancing it
requires an expected prior version/compare-and-swap or concurrent writers can lose
updates. Historical analyses must pin the intended head and knowledge cutoff rather
than reading whichever head happens to exist during execution.

The current registry snapshot pins procedure/resource bytes inside a session. It is
not a memory snapshot or a general entitlement system. The execution identity does
not fingerprint arbitrary Python closure state, model deployment revisions or live
credentials. Those must not vary invisibly inside a shared session.

## 4. Evolving skills from evidence

A future learning loop could collect outcomes, propose prose/resource changes,
evaluate them on held-out cases, and ask an authorized maintainer to accept a
versioned change. Each step is an ordinary transformation; promotion is an external
write with its own authority boundary.

Artifact lineage can identify available and observed evidence. It cannot assign
causal credit automatically. An observed outcome may reflect noise, exposure,
selection effects or changed conditions. A profitable decision is not necessarily a
sound procedure, and a loss is not proof of a faulty procedure. Keep provenance,
process adherence, prediction calibration and measured outcomes as distinct signals.

Candidate changes need versioned datasets, baseline comparisons, regression gates and
review of executable resource diffs. Protect evaluation data and judge configuration
from the system proposing changes. Do not allow a proposed skill to approve its own
promotion, widen its permissions or rewrite the held-out tests. Record accepted and
rejected changes with reasons; use a deployment rollback path to a pinned version.

There is no implemented memory trust score, promotion API or automatic skill-evolution
pipeline. The existing tests validate runtime behavior and scripted graph scenarios,
not general skill quality or autonomous improvement.

## 5. Failure records and observer timeouts

Failures currently raise; progress published before failure remains immutable.
If a future failure-artifact interface is added, specify redaction, size bounds,
which caller receives which refs, and how cancellation differs from executor failure.
Do not automatically grant all producer progress to final-only callers: that would
change the current least-authority contract. Raw exception strings can contain
sensitive tool inputs and must not be treated as safe publication content.

Per-observer timeouts could be a useful addition, but a local timeout should normally
release that observer, not cancel a producer with other leases. Define the race with
terminal publication and whether a caller can later reattach with the original key.
A producer execution limit is different from an observer timeout and may belong in
work identity. There is no `limits` field in today's NodeRequest.

## 6. External effects and durability

Request memoization does not guarantee exactly-once effects. A producer may perform
an effect, fail before publishing, and repeat it under a new key or after a crash.
An effect adapter needs operation-specific authorization, a stable effect idempotency
key, an outcome ledger and reconciliation for unknown outcomes. Separate “requested,”
“accepted by service,” and “confirmed” states where the remote protocol requires it.
A recorded review event after the action cannot serve as a pre-action gate.

Durable execution would require atomic admission/result publication, persisted call
bindings, generation fencing, recovery ownership, lease expiry, context restoration
and retention policy. It must define behavior during process death and network
partitions. An artifact database alone does not provide any of these guarantees.
Design effect retry and recovery together before deploying effectful resumable work.

## 7. KV-cache work and acceptance gates

Stable prompt layout is implemented; provider cache hits and latency savings are not
measured. See [edge-cases-and-kv-cache.md](edge-cases-and-kv-cache.md) for the three
separate reuse mechanisms and measurement plan. No new graph primitive is needed.
Authorize evidence before prefix construction and separate trust domains; never infer
access from a matching cache key. Different models/templates/tokenizers/tool schemas
can invalidate prefix compatibility. Prefix reuse does not establish audit independence.

Choose future work against concrete applications. Before merging an extension,
require an API contract, authority model, retry/cancellation semantics, adversarial
regressions, compatibility decision and measured benefit where performance is claimed.
Do not treat the old M1–M11 list as an approved migration or switch agent frameworks
merely to reduce a speculative token count.
