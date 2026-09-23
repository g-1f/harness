import asyncio
import time
import unittest

from harness import Ledger, NodeRequest, Registry, Rejected, ReviewPolicy, Runtime, Store
from harness.contracts import encode
from harness.runtime import Frame
from tests.support import call, draft, skill


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_custom_execution_binding_does_not_change_skill_or_request_schema(self):
        registry = Registry([skill("work"), skill("specialist")])
        runtime = Runtime(registry, Store(), bindings={"specialist": "custom"})
        self.addCleanup(runtime.store.close)

        async def normal(frame, context):
            child = await runtime.run_node(call("specialist", task="Narrow question"), frame)
            return draft(based_on=[child["ref"]])

        async def custom(frame, context):
            return draft(value=42)

        runtime.register_executor("agent", normal)
        runtime.register_executor("custom", custom)
        receipt = await runtime.run_node(call())
        child_ref = runtime.store.get(receipt["ref"])["based_on"][0]
        self.assertEqual(runtime.store.get(child_ref)["executor"], "custom")
        self.assertEqual(runtime.store.get(child_ref)["content"]["value"], 42)
        with self.assertRaisesRegex(Rejected, "sealed"):
            runtime.register_executor("replacement", custom)

    async def test_unregistered_executor_rejected_before_work_starts(self):
        runtime = Runtime(Registry([skill("work")]), Store(), bindings={"work": "missing"})
        self.addCleanup(runtime.store.close)
        with self.assertRaisesRegex(Rejected, "Unregistered"):
            await runtime.run_node(call())
        self.assertEqual(runtime.ledger.frames, 0)

    async def test_recursive_parallel_join_with_one_model_slot(self):
        kernel = Runtime(Registry([skill("work")]), Store(), ledger=Ledger(model_parallelism=1))

        async def run(frame, context):
            n = frame.request.inputs["n"]
            await kernel.ledger.model_call(lambda: asyncio.sleep(0))
            if n:
                receipts = await asyncio.gather(
                    *(
                        kernel.run_node(
                            call(task=f"part-{i}", key=str(i), inputs={"n": n - 1}), frame
                        )
                        for i in range(2)
                    )
                )
                return draft(
                    sum(kernel.read(frame, x["ref"])["content"]["value"] for x in receipts),
                    based_on=[x["ref"] for x in receipts],
                )
            return draft()

        kernel.register_executor("agent", run)
        result = await asyncio.wait_for(kernel.run_node(call(inputs={"n": 2})), 3)
        self.assertEqual(kernel.store.get(result["ref"])["content"]["value"], 4)
        self.assertEqual(kernel.ledger.frames, 7)
        self.assertEqual(kernel.ledger.model_calls, 7)

    async def test_review_repairs_and_binds_to_new_candidate(self):
        registry = Registry([skill("work"), skill("critic")])
        kernel = Runtime(registry, Store(), reviews={"work": ReviewPolicy(("critic",), 1)})
        seen = []

        async def run(frame, context):
            if frame.request.node == "critic":
                ref = frame.request.refs[0]
                value = kernel.read(frame, ref)["content"]["value"]
                seen.append(ref)
                return {
                    "summary": "Independent check",
                    "content": {
                        "candidate_ref": ref,
                        "verdict": "pass" if value else "fail",
                        "findings": [] if value else ["Value is missing"],
                    },
                }
            return draft(context["attempt"])

        kernel.register_executor("agent", run)
        receipt = await kernel.run_node(call())
        result = kernel.store.get(receipt["ref"])
        self.assertEqual(receipt["status"], "accepted")
        self.assertEqual(result["content"]["value"], 1)
        self.assertEqual(len(set(seen)), 2)
        final_review = kernel.store.get(result["reviews"][0])["content"]
        self.assertEqual(final_review["candidate_ref"], seen[-1])

    async def test_missing_malformed_or_wrong_candidate_review_cannot_pass(self):
        for verdict in (
            {},
            {"candidate_ref": "wrong", "verdict": "pass", "findings": []},
            {"candidate_ref": "wrong", "verdict": "fail", "findings": ["bad"]},
        ):
            with self.subTest(verdict=verdict):
                kernel = Runtime(
                    Registry([skill("work"), skill("critic")]),
                    Store(),
                    reviews={"work": ReviewPolicy(("critic",))},
                )

                async def run(frame, context, verdict=verdict):
                    return (
                        {"summary": "Result", "content": verdict}
                        if frame.request.node == "critic"
                        else draft()
                    )

                kernel.register_executor("agent", run)
                result = await kernel.run_node(call())
                self.assertEqual(result["status"], "needs_review")

    async def test_inline_open_activates_review(self):
        kernel = Runtime(
            Registry([skill("work", links=("checked",)), skill("checked"), skill("critic")]),
            Store(),
            reviews={"checked": ReviewPolicy(("critic",))},
        )

        async def run(frame, context):
            if frame.request.node == "critic":
                raise RuntimeError("Reviewer unavailable")
            kernel.read_node(frame, "checked", enter=True)
            return draft()

        kernel.register_executor("agent", run)
        result = await kernel.run_node(call())
        self.assertEqual(result["status"], "needs_review")

    async def test_reading_a_link_does_not_grant_ambient_artifacts(self):
        kernel = Runtime(Registry([skill("work", links=("evidence",)), skill("evidence")]), Store())
        frame = Frame("parent", None, call(), ())
        ref = kernel.store.put(
            {"session": kernel.session, "frame": "sibling", "status": "accepted"}
        )
        packet = kernel.read_node(frame, "work")
        self.assertEqual(packet["links"], ["evidence"])
        with self.assertRaisesRegex(Rejected, "not visible"):
            kernel.read(frame, ref)
        frame.grants.add(ref)
        self.assertEqual(kernel.read(frame, ref)["status"], "accepted")

    async def test_context_packet_is_bounded_and_prose_preserved(self):
        node = skill("work", instructions="é" * 600)
        kernel = Runtime(Registry([node]), Store())
        frame = Frame("f", None, call(), ())
        with self.assertRaisesRegex(Rejected, "Entry exceeds"):
            kernel.read_node(frame, "work", limit=512)
        packet = kernel.read_node(frame, "work")
        self.assertEqual(packet["text"], node.instructions)
        self.assertLessEqual(len(encode(packet).encode()), 32_000)

    async def test_concurrent_idempotency_and_key_conflict(self):
        kernel = Runtime(Registry([skill("work")]), Store())

        async def run(frame, context):
            await asyncio.sleep(0.01)
            return draft()

        kernel.register_executor("agent", run)
        a, b = await asyncio.gather(kernel.run_node(call()), kernel.run_node(call()))
        self.assertEqual(a, b)
        self.assertEqual(kernel.ledger.frames, 1)
        with self.assertRaisesRegex(Rejected, "Idempotency"):
            await kernel.run_node(call(task="different"))

    async def test_cycle_and_depth_limits(self):
        kernel = Runtime(Registry([skill("work")]), Store(), max_depth=0)

        async def run(frame, context):
            with self.assertRaisesRegex(Rejected, "Repeated active"):
                await kernel.run_node(call(key="cycle"), frame)
            with self.assertRaisesRegex(Rejected, "depth"):
                await kernel.run_node(call(task="narrower", key="depth"), frame)
            return draft()

        kernel.register_executor("agent", run)
        await kernel.run_node(call())

    async def test_global_budget_admission_is_atomic(self):
        ledger = Ledger(max_model_calls=2, model_parallelism=8)
        results = await asyncio.gather(
            *(ledger.model_call(lambda: asyncio.sleep(0)) for _ in range(8)), return_exceptions=True
        )
        self.assertEqual(sum(isinstance(x, Rejected) for x in results), 6)
        self.assertEqual(ledger.model_calls, 2)

    async def test_cancel_propagates_and_closes_children(self):
        kernel = Runtime(Registry([skill("work")]), Store())
        child_started = asyncio.Event()
        cancelled = asyncio.Event()

        async def run(frame, context):
            if frame.parent:
                child_started.set()
                try:
                    await asyncio.sleep(10)
                finally:
                    cancelled.set()
            return await kernel.run_node(call(task="child", key="child"), frame)

        kernel.register_executor("agent", run)
        root = asyncio.create_task(kernel.run_node(call()))
        await child_started.wait()
        root.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await root
        self.assertTrue(cancelled.is_set())
        self.assertTrue(all(job.done() for _, job in kernel.jobs.values()))

    async def test_session_deadline(self):
        kernel = Runtime(Registry([skill("work")]), Store(), deadline_seconds=0.02)

        async def run(frame, context):
            await asyncio.sleep(1)

        kernel.register_executor("agent", run)
        with self.assertRaises(TimeoutError):
            await kernel.run_node(call())

    async def test_draft_visibility_and_cross_session_denial(self):
        kernel = Runtime(Registry([skill("work")]), Store())
        parent = Frame("parent", None, call(), ())
        ref = kernel.store.put({"session": kernel.session, "frame": "child", "status": "draft"})
        with self.assertRaises(Rejected):
            kernel.read(parent, ref)
        parent.grants.add(ref)
        self.assertEqual(kernel.read(parent, ref)["status"], "draft")
        foreign = kernel.store.put({"session": "other", "frame": "parent", "status": "accepted"})
        with self.assertRaises(Rejected):
            kernel.read(parent, foreign)

    async def test_policy_graph_rejects_review_recursion(self):
        with self.assertRaisesRegex(Rejected, "Required-review cycle"):
            Runtime(
                Registry([skill("critic")]),
                Store(),
                reviews={"critic": ReviewPolicy(("critic",), 1)},
            )

    async def test_inspection_does_not_activate_review(self):
        runtime = Runtime(
            Registry([skill("work"), skill("checked"), skill("critic")]),
            Store(),
            reviews={"checked": ReviewPolicy(("critic",))},
        )
        frame = Frame("f", None, call(), ())
        runtime.read_node(frame, "checked")
        self.assertEqual(frame.active, set())
        runtime.read_node(frame, "checked", enter=True)
        self.assertEqual(frame.active, {"checked"})

    async def test_reviewer_grants_cover_reads_entry_and_descendants(self):
        runtime = Runtime(
            Registry([skill("work"), skill("evidence"), skill("critic", links=("evidence",))]),
            Store(),
        )
        secret = runtime.store.put(
            {
                "session": runtime.session,
                "frame": "other",
                "node": "evidence",
                "status": "accepted",
                "inputs": {},
                "snapshot": runtime.registry.snapshot,
                "created_at": time.time(),
                "summary": "Unrelated reviewer conclusion",
                "content": {},
            }
        )
        seen = []

        async def run(frame, context):
            if frame.request.node == "work" and frame.parent is None:
                return await root(frame)
            seen.append(frame.request.node)
            with self.assertRaisesRegex(Rejected, "not visible"):
                runtime.read(frame, secret)
            self.assertEqual(runtime.read_node(frame, "critic")["links"], ["evidence"])
            if frame.request.node == "critic":
                await runtime.run_node(
                    NodeRequest("work", "narrow evidence check", {}, "sub"), frame
                )
            return draft()

        async def root(frame):
            result = await runtime.run_node(NodeRequest("critic", "check", {}, "critic"), frame)
            return draft(based_on=[result["ref"]])

        runtime.register_executor("agent", run)
        await runtime.run_node(NodeRequest("work", "root", {}, "root"))
        self.assertEqual(seen, ["critic", "work"])

    async def test_inconclusive_required_review_blocks_acceptance(self):
        runtime = Runtime(
            Registry([skill("work"), skill("critic")]),
            Store(),
            reviews={"work": ReviewPolicy(("critic",))},
        )

        async def run(frame, context):
            if frame.request.node == "critic":
                return {
                    "summary": "Insufficient evidence",
                    "content": {
                        "candidate_ref": frame.request.refs[0],
                        "verdict": "inconclusive",
                        "findings": [],
                    },
                }
            return draft()

        runtime.register_executor("agent", run)
        result = await runtime.run_node(call())
        self.assertEqual(result["status"], "needs_review")

    async def test_code_runner_dispatch_without_agent(self):
        async def code(frame, context):
            return draft(value=7)

        runtime = Runtime(Registry([skill("calculate")]), Store(), default_executor="calculate")
        runtime.register_executor("calculate", code)
        result = await runtime.run_node(NodeRequest("calculate", "calculate", {}, "root"))
        self.assertEqual(runtime.store.get(result["ref"])["content"]["value"], 7)
        self.assertEqual(runtime.ledger.model_calls, 0)


if __name__ == "__main__":
    unittest.main()
