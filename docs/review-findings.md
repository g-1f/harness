# Adversarial review and resolution

Reviewed 2026-09-26 against `g-1f/harness` main at `a5764c2` (parent runtime cleanup
`40aceff`), the user-authored `new_doc.md`, and the supplied README/design/runtime/
patterns/evolution documents and consolidation patch. The patch was treated as a
proposal, not blindly applied. Separate review passes examined execution semantics,
concurrency, authority, composition examples, provenance, and performance claims.

## Findings and decisions

| ID | Severity | Finding and consequence | Resolution |
| --- | --- | --- | --- |
| R1 | High | Unobserved open handles kept producers alive but added no dependency edge. Recursive opens bypassed max depth; descendant attachment could form a cleanup cycle. | Fixed: every unfinished lease adds a reference-counted dependency edge at acquisition. Release or producer completion removes it. Pending reads use the existing edge. |
| R2 | High | Replaying a cancelled producer leaked `CancelledError` into a live consumer; this could terminate JS execution instead of permitting recovery. | Fixed: shielded settlement distinguishes producer cancellation from cancellation of the current caller. The former raises `Rejected`; the latter propagates cancellation. |
| R3 | Medium | Expected host rejections arrived in JS as opaque host errors, preventing callers from understanding a recoverable contract failure. | Fixed in both adapters: serialize only `Rejected` in a reserved response envelope and rethrow a named JS error in the shared prelude. Direct Python APIs still raise. |
| R4 | High | Proposed supersession redirected the original request to a repair made with different inputs and let a non-pass review confer mutation authority. | Rejected this protocol. Immutable refs, explicit correction calls and application review remain. Future invalidation needs version semantics, authorization, complete enough dependencies and concurrent-consumer rules. |
| R5 | High | A bounded self-review example could produce a final revision after the last review and submit it without approval. | Replaced with the existing tested `ReviewedTransformation` algorithm: approve only the exact reviewed candidate; otherwise revise within the budget or return blocked. |
| R6 | Medium | Race examples lacked cleanup after partial acquisition, all failures or consumer exceptions. Promise races alone do not release leases. | Added `examples/patterns/race.js`, an ordinary helper that tracks every acquisition and closes all handles in `finally`, preserving cleanup errors. Tested through QuickJS. |
| R7 | Medium | Most proposed snippets omitted the required key and assumed automatic identity-only sharing. They would reject or behave differently from the current runtime. | Retained explicit keys and reuse policy; corrected snippets and documented the distinction between retry identity and sharing identity. No silent request-contract migration. |
| R8 | Medium | Proposed parsed reads, memory reads, failure artifacts, adoption and observer limits appeared alongside implemented APIs. | Removed runnable claims for unavailable capabilities. Future interfaces are isolated in `evolution-and-memory.md`, with prerequisites. |
| R9 | Medium | Documents cited `7e46345`, `d120ee6`, a review-fixes branch, 87/92 passing tests and missing checker tools as verified implementation. | These were not in the fetched main history or advertised remote branches. Reproduced relevant bugs locally, implemented fixes here, and replaced unsupported claims with actual commands/results. Historical text is preserved with a warning. |
| R10 | High for deployment | Final-only failure was proposed to grant every progress artifact, weakening the explicit grant contract; failure strings were treated as publishable records. | Retained delivery-scoped progress grants and final-only isolation. Failure records require an explicit authority/redaction design before implementation. |
| R11 | Medium | Provenance was described as complete causal lineage suitable for invalidation and automated credit assignment. Available refs, reads and declared dependence do not establish causality. | Defined the three categories, call graph and blind spots. Removed unverified partial-recomputation claims. |
| R12 | High for deployment | Effect replay and session memoization were conflated with exactly-once actions and durable recovery. | Documented effect-level idempotency, authorization, outcome reconciliation and durable generation fencing as prerequisites, not current guarantees. |
| R13 | Medium | A memory `as_of` cutoff alone was presented as protection against look-ahead leakage. Retrospective corrections and concurrent head updates were underspecified. | Added source vintages, knowledge time, immutable manifests, permission/revocation scope and compare-and-swap requirements. No memory implementation claimed. |
| R14 | Medium | KV savings, fixed-prefix token counts and independent judgment were implied without provider measurements. | Kept verified prompt-layout behavior separate from provider cache metrics; fresh context and model diversity do not prove independence. |
| R15 | Low | Deadline origin, rejected-call budget charging, fresh-key replay and error transport were misstated. | Runtime reference now follows code: deadline starts at construction; admission can charge later rejections; same-key replay remains sticky even with fresh; transport scope is explicit. |
| R16 | Low | Multiple competing long documents obscured which architecture was authoritative. | Consolidated maintained guides, retained old paths as redirects, archived the original user draft, updated README and trajectory exporter links/lifecycle wording. |

## Reproductions and regression coverage

Before the fix, the unobserved-recursion test reached depth **6 with max_depth=2**.
The cancelled-replay test raised `asyncio.CancelledError` where a catchable rejection
was required. Both are recorded as executable regressions in `tests/test_adversarial.py`.
The ancestor-cycle regression checks rejection at acquisition and verifies that
closing the root drains the graph without leaked handles or dependency edges.

| Regression | Evidence |
| --- | --- |
| Unobserved recursion obeys depth | `test_unobserved_open_recursion_respects_depth` |
| Ancestor cannot acquire a descendant-owned live lease cycle | `test_unobserved_ancestor_attachment_is_rejected` |
| Cancelled replay leaves a live consumer uncancelled | `test_cancelled_replay_is_rejected_without_cancelling_consumer` |
| JS can catch the reason for rejection and cancelled replay | `test_rejections_and_cancelled_replays_are_catchable_in_quickjs` |
| Agent adapter preserves rejections and operation state across eval cells | `test_agent_wrapper_is_injected_and_survives_multiple_eval_cells` |
| Shared work survives one consumer's real cancellation | `test_cancelling_first_branch_does_not_cancel_shared_producer` |
| Replacement waits for cleanup; old key remains bound | `test_replacement_waits_for_last_waiter_cleanup_and_preserves_retry_identity` |
| Cycles reject before event reads | `test_observation_cycle_across_existing_branches` |
| Fastest success releases unfinished loser | `test_race_winner_releases_loser` |
| Partial race admission and all failures release handles | `test_race_partial_admission_and_all_producer_failures_release_every_handle` |
| Exact candidate approval, bounded revision and blocking | `tests/test_review_composition.py` and real-interpreter integration tests |
| Final-only delivery does not grant unseen progress | `test_final_only_call_does_not_grant_unobserved_checkpoints` |

Existing tests that asserted no dependency edge for an unobserved handle or expected
cancelled replay to cancel its caller were updated to the corrected contract. The
changes are intentional behavior corrections, not new primitives. The eight native
endpoints, NodeRequest fields and two frontmatter fields remain unchanged.

## Verification record

The final checked-in revision is verified with the following commands; results are
recorded after execution, not inferred from the proposal:

```sh
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python -m pip check
python -m examples.export_trajectories
python tools/package_deliverables.py
```

Results: **85 tests passed**; Ruff lint and formatting passed; `pip check` reported
no broken requirements; all maintained local Markdown links resolved. Both trajectories
were regenerated: A completed with 27 calls / 19 executions / 2 running joins / 6
completed reuses; B completed with 23 calls / 19 executions / 0 running joins / 4
completed reuses. Every lease was released and no live dependency edges remained.
The source package was created and its ZIP integrity check passed.

The suite, trajectory regeneration and source-package checks are local offline
verification. GitHub CI separately runs on push. No live model API calls, external
effects, distributed races, provider KV-cache measurements or durable recovery tests
are represented as having run. The examples use real Deep Agents and QuickJS with
scripted model outputs; they verify execution contracts, not model judgment quality.

## What this review did not approve

No identity-only memoization migration, core review/supersession semantics, new node
attributes, hidden code orchestration in skills, memory primitive, framework switch,
cross-session cache or production durability was adopted. The proposals are retained
as design questions with explicit acceptance conditions. Cooperative Python executors
remain trusted; an executor that ignores cancellation indefinitely can still prevent
prompt draining. Native resource isolation and distributed recovery require a separate
architecture rather than a stronger claim about these in-process tests.
