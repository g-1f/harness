# Graph edge cases and KV-cache reuse

Tests verify runtime behavior and messages delivered through Deep Agents. They do
not run a GPU KV cache or establish provider latency, cost or cache-hit improvements.
These cases require no additional host primitives or skill attributes.

## Verified behavior

| Case | Contract and solution | Executable evidence |
| --- | --- | --- |
| a/c request identical b concurrently; d requests it later | One producer, separate leases, then completed-result reuse | `tests/test_operations.py`, both graph trajectories |
| Session expires with an open handle | Ownership still controls release; cleanup does not require liveness | `test_expired_session_still_allows_owner_to_release` |
| Two readers use one handle concurrently | Reject the second pending read; separate consumers use separate handles | `test_one_pending_read_per_handle_and_cancelled_read_can_retry` |
| Event read is cancelled | Retain its lease and dependency edge for retry or explicit close | Same test, observation-cycle test |
| Producer fails after useful progress | Previous checkpoints remain replayable on the original caller/key; terminal read raises and releases | `test_failed_producer_preserves_checkpoint_and_retry_generation` |
| x/y subscribe to each other | Unfinished handles are dependencies; the second cyclic acquisition is rejected | `test_observation_cycle_across_existing_branches` |
| Concurrent work finishes in another order | Cursors follow publication order, not semantic/source freshness | `test_concurrent_checkpoint_cursors_follow_publication_order` |
| Close races with a waiting read; another consumer remains | Wake/reject the closed read; preserve the other consumer's producer | `test_early_close_wakes_pending_observer_without_stopping_other_caller` |
| Final-only caller sees checkpoint hashes inside the result | It receives only the final ref grant; nested hashes confer no authority | `test_final_only_call_does_not_grant_unobserved_checkpoints` |
| Checkpoint says verdict fail | Publish it as evidence; no implicit reviewer or repair runs | `test_negative_domain_checkpoint_is_published_without_implicit_review` |
| Completed shared result says blocked | Reuse it for exact session requests; a new key plus fresh requests another execution | `test_negative_domain_decision_is_reused_until_caller_requests_fresh_work` |
| Reviewer returns missing, stale or inconclusive content | Application composition blocks approval | `tests/test_review_composition.py` |
| Review fails, is cancelled, or exhausts the budget | Composition fails/cancels without approving or silently restarting | Same composition tests |
| Revision produces a different candidate | New execution, explicit feedback refs, fresh check bound to that exact artifact | Composition tests, `test_real_interpreter_review_repair_loop` |
| Candidate mentions evidence unavailable to reviewer | Access stays non-transitive; the reviewer may report insufficient evidence | `test_review_cannot_read_ungranted_descendants` |
| Same procedure/evidence, different question | Preserve earlier prompt packets; new task packet and fresh history | `tests/test_prompt_layout.py`, `test_fresh_agent_calls_share_stable_prefix_without_sharing_history` |

Concurrency tests use events/barriers to force the required interleavings.
`asyncio.sleep(0)` yields a scheduling turn; it does not estimate model duration.
The full suite also covers cancellation draining before replacement, duplicate
keys, reference access on cache hits, active-depth limits and shared budgets.

## Remaining boundaries and possible extensions

| Pressure | Current behavior | Solution if required |
| --- | --- | --- |
| Later evidence contradicts a checkpoint | Publication is availability, not permanent truth. Downstream outputs are not invalidated | Publish a correction with source version and affected refs; explicitly rerun affected consumers. Automatic invalidation is not implemented |
| Lost checkpoint-publication response is retried | Another call can append another record | Add publication identity only when transport retries require it. Observation replay is not exactly-once publication |
| Subscriber never reads or closes | Its lease retains the producer until cleanup/deadline; the session bounds checkpoints | Service-level lease expiry, retention budgets and durable resume require additional design |
| Artifact is useful but insufficient for a different task | Host does not infer usefulness or rerun automatically | Caller/model requests another aspect with explicit evidence, or application code makes that decision |
| Same explicit inputs hide changed external state | Session reuse may return old work | Include a source snapshot/version or choose fresh. The host does not infer freshness |
| Retried node repeats an external effect | Node identity is not an external exactly-once guarantee | Use effect-level idempotency and authorization in the external adapter |
| Many different aspects create expensive fan-out | Different tasks remain distinct executions | Existing call/frame/model budgets bound work; coalesce only exact requests explicitly eligible for sharing |
| Process crashes while work runs | Stored records/events survive; active leases, keys and contexts do not | Durable scheduling needs transactional acquisition, lease expiry and generation fencing; replacing a dictionary alone is insufficient |
| Model misreads an approval artifact | Core still treats content as opaque | Enforce required product decisions in a trusted application boundary; test model judgment separately |

## Three different forms of reuse

| Reuse | What is reused | Does another execution reason? |
| --- | --- | --- |
| Shared operation | Running producer or completed result | No new execution for that matching caller |
| Artifact evidence | Authorized immutable checkpoint/result | Yes, when passed to a new task |
| KV prefix | Model computation for matching prior tokens in a compatible serving configuration | Yes; the changed suffix and decoding still execute |

Fresh context is compatible with caching identical public procedure tokens and
explicitly authorized evidence. It does not import an earlier worker's assistant
messages, private reasoning, tool state or decisions. Caching does not make reviews
statistically independent; model biases can remain correlated.

## Implemented prompt layout

`harness/runners/agent.py::node_messages` creates these user packets after the
adapter's system instructions and tool definitions:

1. Immutable skill entry with revision and prose.
2. Explicit inputs and ordered granted refs.
3. Task text.

Canonical serialization keeps object-key order stable. Session/frame IDs and local
keys are absent. Changing only the task preserves the first two packets. Changed
inputs or grants change the second; a changed procedure changes the first.
Repair feedback is ordinary task/input/ref data: if repair adds refs, the evidence
packet must change. There is no hidden repair suffix that bypasses evidence identity.

Integration tests capture actual model input after middleware. They check matching
prefixes for different questions, distinct executions and no inherited assistant/tool
history. Unit tests verify changes at the procedure, input and grant boundaries.
These are layout tests, not measurements of token-level cache hits.

Different skills generally share only the common system/tool prefix. Neutral b
and a focused b share procedure tokens but different refs may end the match at
the evidence packet. Two calls to b with identical inputs/refs and different tasks
can share both earlier packets while still getting fresh conversations.

Refs do not automatically materialize artifact bodies. A later readArtifact result
comes after the task, so it is not automatically a reusable evidence prefix across
different tasks. If long evidence dominates prefill, a future adapter can place a
bounded authorized deterministic evidence projection before the task. It must
validate grants before rendering. This optimization is not implemented here.

## Serving and measurement

Use a provider's prompt cache or a serving engine's prefix cache; do not transport
opaque GPU KV blocks through artifact APIs. Model/tokenizer/template compatibility,
tool schemas, trust-domain partitioning and cache options belong in deployment or
executor configuration. Skill names and artifact hashes are not universal KV keys.
See [vLLM prefix caching](https://docs.vllm.ai/en/latest/design/prefix_caching/) and
[Claude prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
for provider-specific mechanisms; no provider configuration is implemented by this repo.

Keep tool definitions and ordering stable. Cache-local scheduling must respect a
latency budget rather than serializing all branches merely to warm a prefix.
Concurrent cold requests, eviction and expiry can reduce reuse. Any warm-up strategy
needs measured benefit relative to its latency and extra requests.

Before claiming a speedup, measure cold/warm requests for the selected provider,
including fan-out, changed task/skill/refs, expiry and separate trust domains.
Record reported cache-read/write tokens, input/output tokens, time to first token,
total latency and cost. Missing telemetry means unknown, not zero. Compare output
quality as well as latency. The local scripted model provides none of these metrics.
Prefix caching reduces repeated prompt processing; it does not remove decoding or
tool latency. Stable layout is implemented; serving gains still need measurement.
