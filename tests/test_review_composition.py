"""Domain approval belongs to a composition, outside the generic supervisor."""

import asyncio
import unittest

from examples.review import ReviewedTransformation
from harness import Ledger, NodeRequest, Registry, Rejected, Runtime, Store
from tests.support import draft, skill


class ReviewCompositionTests(unittest.IsolatedAsyncioTestCase):
    def runtime(self, runner, *, revisions=0, ledger=None):
        runtime = Runtime(
            Registry([skill("release"), skill("work"), skill("critic"), skill("evidence")]),
            Store(),
            bindings={"release": "reviewed"},
            ledger=ledger,
        )
        self.addCleanup(runtime.store.close)
        self.addAsyncCleanup(runtime.aclose)
        runtime.register_executor("agent", runner(runtime))
        runtime.register_executor(
            "reviewed", ReviewedTransformation(runtime, "work", "critic", revisions)
        )
        return runtime

    async def release(self, runtime):
        receipt = await runtime.run_node(NodeRequest("release", "Make a value of one", {}, "root"))
        self.assertEqual(receipt["status"], "published")
        return runtime.store.get(receipt["ref"])["content"]

    async def test_revision_is_a_fresh_call_with_explicit_feedback_and_new_review(self):
        producers, reviewers = [], []

        def runner(runtime):
            async def run(frame, context):
                self.assertEqual(set(context), {"entry"})
                if frame.request.node == "work":
                    producers.append(frame)
                    if len(producers) == 2:
                        previous, review = frame.request.refs
                        self.assertEqual(runtime.read(frame, previous)["content"]["value"], 0)
                        self.assertEqual(runtime.read(frame, review)["content"]["verdict"], "fail")
                        self.assertIn("Revise artifact", frame.request.task)
                    return draft(len(producers) - 1)
                reviewers.append(frame)
                ref = frame.request.refs[0]
                passed = runtime.read(frame, ref)["content"]["value"] == 1
                return {
                    "summary": "Check",
                    "content": {
                        "candidate_ref": ref,
                        "verdict": "pass" if passed else "fail",
                        "findings": [] if passed else ["Value must be one"],
                    },
                }

            return run

        runtime = self.runtime(runner, revisions=1)
        result = await self.release(runtime)
        self.assertEqual(result["decision"], "approved")
        self.assertEqual(result["result"], {"value": 1})
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(len({f.id for f in producers + reviewers}), 4)
        self.assertTrue(all(f.request.reuse == "fresh" for f in producers + reviewers))
        self.assertNotEqual(reviewers[0].request.refs, reviewers[1].request.refs)
        final_review = runtime.store.get(result["reviews"][0])["content"]
        self.assertEqual(final_review["candidate_ref"], result["candidate_ref"])
        self.assertEqual(runtime.operations.waits, {})
        self.assertTrue(all(not op.waiters for op in runtime.operations.operations.values()))

    async def test_missing_wrong_stale_and_inconclusive_reviews_block(self):
        for payload in (
            {},
            {"candidate_ref": "wrong", "verdict": "pass", "findings": []},
            {"verdict": "inconclusive", "findings": []},
            {"verdict": "pass", "findings": ["Unresolved"]},
            {"verdict": "fail", "findings": []},
        ):
            with self.subTest(payload=payload):

                def runner(runtime, payload=payload):
                    async def run(frame, context):
                        if frame.request.node == "work":
                            return draft()
                        return {
                            "summary": "Check",
                            "content": {"candidate_ref": frame.request.refs[0], **payload},
                        }

                    return run

                result = await self.release(self.runtime(runner))
                self.assertEqual(result["decision"], "blocked")
                self.assertIsNone(result["result"])

    async def test_prior_candidate_review_cannot_approve_revision(self):
        first_ref = None

        def runner(runtime):
            async def run(frame, context):
                nonlocal first_ref
                if frame.request.node == "work":
                    return draft()
                ref = frame.request.refs[0]
                old_ref, first_ref = first_ref, ref
                return {
                    "summary": "Stale check",
                    "content": {
                        "candidate_ref": old_ref or ref,
                        "verdict": "pass" if old_ref else "fail",
                        "findings": [],
                    },
                }

            return run

        result = await self.release(self.runtime(runner, revisions=1))
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(result["attempts"], 2)

    async def test_failed_check_exhausts_bounded_revisions(self):
        def runner(runtime):
            async def run(frame, context):
                if frame.request.node == "work":
                    return draft()
                return {
                    "summary": "Check",
                    "content": {
                        "candidate_ref": frame.request.refs[0],
                        "verdict": "fail",
                        "findings": ["Bad"],
                    },
                }

            return run

        runtime = self.runtime(runner, revisions=1)
        result = await self.release(runtime)
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(runtime.ledger.frames, 5)

    async def test_review_errors_and_budget_exhaustion_fail_composition(self):
        def runner(runtime):
            async def run(frame, context):
                if frame.request.node == "critic":
                    raise ValueError("Reviewer unavailable")
                return draft()

            return run

        for ledger, error in ((None, ValueError), (Ledger(max_frames=2), Rejected)):
            with self.subTest(ledger=ledger):
                runtime = self.runtime(runner, revisions=1, ledger=ledger)
                with self.assertRaises(error):
                    await self.release(runtime)
                self.assertTrue(
                    all(not op.waiters for op in runtime.operations.operations.values())
                )
                self.assertFalse(
                    any(
                        e["type"] == "completed"
                        and runtime.store.get(e["ref"])["node"] == "release"
                        for e in runtime.store.events()
                    )
                )

    async def test_cancelled_review_cannot_approve_or_start_a_revision(self):
        started = asyncio.Event()

        def runner(runtime):
            async def run(frame, context):
                if frame.request.node == "critic":
                    started.set()
                    await asyncio.Event().wait()
                return draft()

            return run

        runtime = self.runtime(runner, revisions=1)
        task = asyncio.create_task(self.release(runtime))
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(runtime.ledger.frames, 3)
        self.assertEqual(runtime.operations.waits, {})
        self.assertTrue(all(not op.waiters for op in runtime.operations.operations.values()))

    async def test_review_cannot_read_ungranted_descendants(self):
        hidden_ref = None

        def runner(runtime):
            async def run(frame, context):
                nonlocal hidden_ref
                if frame.request.node == "evidence":
                    return draft(42)
                if frame.request.node == "work":
                    child = await runtime.run_node(
                        NodeRequest("evidence", "Measure", {}, "e"), frame
                    )
                    hidden_ref = child["ref"]
                    return draft(based_on=[hidden_ref])
                ref = frame.request.refs[0]
                self.assertEqual(runtime.read(frame, ref)["based_on"], [hidden_ref])
                with self.assertRaisesRegex(Rejected, "not visible"):
                    runtime.read(frame, hidden_ref)
                return {
                    "summary": "Insufficient evidence",
                    "content": {"candidate_ref": ref, "verdict": "inconclusive", "findings": []},
                }

            return run

        result = await self.release(self.runtime(runner))
        self.assertEqual(result["decision"], "blocked")

    def test_composition_configuration_stays_outside_runtime(self):
        runtime = self.runtime(lambda runtime: lambda frame, context: draft())
        for revisions in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                ReviewedTransformation(runtime, "work", "critic", revisions)
        with self.assertRaises(ValueError):
            ReviewedTransformation(runtime, "missing", "critic")
