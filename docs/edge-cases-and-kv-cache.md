# Graph edge cases and KV-cache reuse

This update adds no host tools or skill fields. It tightens observation lifetime
rules and changes the agent's initial message layout. Tests verify local runtime
behavior and the actual messages delivered through Deep Agents. They do not run
a GPU KV cache or establish provider latency, cost or cache-hit improvements.

## Verified edge cases

| Case | Contract and solution | Executable evidence |
| --- | --- | --- |
| Session expires while a handle is open | Ownership still controls release, but cleanup does not require a live session. Reads and new work still require liveness. Previously close was rejected after expiry; fixed. | `test_expired_session_still_allows_owner_to_release` |
| Two coroutines read one handle concurrently | One pending read per handle; reject the second immediately. Separate consumers acquire separate handles. Previously reads could race to close on terminal delivery; fixed. | `test_one_pending_read_per_handle_and_cancelled_read_can_retry` |
| An event read is cancelled | Cancel that read and remove its temporary wait edge. Retain the handle for retry; explicit close or frame cleanup releases its lease. A cancelled read is not a cancellation of the producer. | Same test, plus observation-cycle test |
| Producer fails after publishing useful progress | Already accepted checkpoints remain immutable and replayable on the original caller/key. Terminal read raises the producer error and releases the handle. A new key can create another generation. | `test_failed_producer_preserves_checkpoint_and_retry_generation` |
| Existing x and y acquire observation handles for each other | Handles alone create no wait cycle; blocking x on y then y on x is rejected. Cleanup removes all wait edges and leases. | `test_observation_cycle_across_existing_branches` |
| Two checkpoints undergo reviews concurrently and the first review is slower | Cursors order accepted publication, not when work began or which finding is logically newer. Consumers must not equate largest cursor with freshest source data. Sequentially await publication when phase order matters; source versions belong in content. | `test_concurrent_checkpoint_cursors_follow_acceptance_order` |
| Handle closes while an event read waits, but another consumer still needs the producer | Wake and reject the closed read; keep the other consumer's operation running. | `test_early_close_wakes_pending_observer_without_stopping_other_caller` |
| Same skill, different question or repair feedback | Keep the stable procedure/input prefix identical while changing the final task packet. Each call still creates a fresh agent conversation. | `tests/test_prompt_layout.py` and `test_fresh_agent_calls_share_stable_prefix_without_sharing_history` |

Progress tests are in `tests/test_progress.py`; the adapter test is in
`tests/test_integration.py`. `asyncio.sleep(0)` yields a scheduling turn in race
tests; it does not estimate how long a model or producer takes.

## Further boundaries and solutions

| Pressure | Current behavior | Next solution if required |
| --- | --- | --- |
| Later evidence contradicts an accepted checkpoint | Acceptance means policy passed at publication, not permanent truth. Existing downstream results are not invalidated. | Publish a correction with explicit source version and affected refs; rerun affected consumers. Automatic invalidation needs a dependency policy and is not implemented. |
| Retry a checkpoint publication after losing its response | Publication has no idempotency key, so another call can append another record. | Treat observation as replayable, not exactly-once delivery. Add publication identity only if transport retries require it; do not confuse it with node request identity. |
| Subscriber never reads or closes | Its lease retains the producer until frame/session cleanup or deadline; publications are bounded by the shared checkpoint-attempt budget. | For long-running services add subscriber deadlines/lease expiry and retention budgets. This runtime has no durable resume or per-subscriber backpressure. |
| Reference to a checkpoint is useful but insufficient | Grants are non-transitive; a child cannot read every ref mentioned inside it. | Pass the particular accepted artifacts it needs explicitly. Do not open the whole producer transcript. |
| Same task/inputs hide changed external state | Session reuse may return a prior accepted result. | Include source snapshot/version in inputs or request fresh work. Semantic freshness is not inferred. |
| A retry repeats an external side effect | Runtime keys identify executions, not exactly-once external writes. | Enforce effect-level idempotency and authorization in the external tool adapter. |
| Too many consumers request different aspects of one checkpoint | Distinct tasks remain distinct executions. | Bound fan-out with existing call/frame/model budgets; optionally coalesce only exact, explicitly shareable requests. Avoid fuzzy task equivalence. |

## Three different forms of reuse

| Reuse | What is reused | Does new reasoning run? |
| --- | --- | --- |
| Shared operation | One running producer or its accepted result | No additional execution for the matching caller |
| Artifact evidence | An authorized immutable checkpoint/result | Yes, when passed to a new task |
| KV prefix | Model computation for identical preceding tokens under compatible serving configuration | Yes; decoding and the changed suffix still execute |

Fresh context is compatible with reusing the KV for an identical public procedure
and explicitly authorized evidence. It does not mean importing an earlier worker's
assistant messages, private reasoning, tool state or outcome. Nor does caching
make reviews statistically independent; model biases can remain correlated.

## Implemented prompt layout

`harness/runners/agent.py::node_messages` creates these user packets, after the
adapter's system instructions and tool definitions:

1. Immutable skill entry, including its revision and prose.
2. Explicit inputs and ordered granted artifact refs.
3. This task, attempt number, repair feedback and previous candidate ref.

Canonical serialization keeps object key order stable. Session/frame IDs and caller
keys are not placed in these packets. Changed task or repair feedback preserves the
first two packets; changed evidence changes the second; changed procedure changes
the first. Skill text stays in a user packet, preserving its existing authority.

The integration test captures actual model input after Deep Agents middleware.
It verifies identical prefixes for two different questions, different task suffixes,
two executions, and no inherited assistant/tool history. Unit tests verify revision,
grant and repair boundaries. They test cache eligibility, not token-level hits.

For a and c, different skill entries generally limit cross-node reuse to common
system/tool prefixes. For neutral b and a focused b, the skill prefix matches but
different refs may end matching at the evidence packet. Two focused b calls with
the same explicit evidence and different questions can share both earlier packets.

The packet contains refs, not automatically materialized artifact bodies. A later
`readArtifact` result occurs after the task and is not automatically a reusable
prefix across different tasks. If long evidence dominates prefill, a future adapter
can place a bounded, authorized, deterministic evidence projection before the task.
It must validate grants before rendering and preserve provenance separately; this
optimization is not implemented here. A reference hash alone is not cached KV.

## Serving strategy and measurement

Primary references checked on 2026-09-23:

- [vLLM prefix caching](https://docs.vllm.ai/en/latest/design/prefix_caching/): block
  identity includes preceding context; `cache_salt` can partition reuse by trust domain.
- [Claude prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching):
  caching follows tools, system and messages, with provider-specific cache controls.

Use provider caching or the serving engine's prefix cache. Do not store or transport
opaque GPU KV blocks through `readArtifact`. Provider options, model/tokenizer/chat
template, tool schemas and tenant routing belong in executor/deployment configuration.
Do not use skill name or an artifact hash as a universal KV-cache key.

Keep tool definitions and ordering stable. Group compatible requests for cache
locality only within a latency budget; do not serialize all graph branches merely
to warm a prefix. Concurrent cold requests may duplicate prefill, and eviction or
expiry may remove reuse. A warm-up strategy needs measured benefit to justify its
latency and extra request cost.

Before claiming a speedup, run cold and warm requests against the actual selected
provider/model, with concurrent fan-out, changed task, changed skill, changed refs,
expiry and separate tenant cases. Capture reported cache-read/cache-write tokens,
input/output tokens, time to first token, total latency and cost. Missing cache
telemetry means unknown, not zero. Compare completed task quality as well as latency.
The current local suite uses a scripted model and provides no such measurements.

Cache reuse mainly targets repeated prompt processing; it does not eliminate output
decoding or tool latency. Large GPU caches also trade memory against concurrency.
The first practical optimization here is stable prompt layout, then authorized
evidence layout and measured provider configuration—not another graph primitive.
