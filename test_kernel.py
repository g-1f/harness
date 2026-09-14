import asyncio
import time
import unittest
from dataclasses import replace

from kernel import Call, Frame, Kernel, Ledger, Registry, Rejected, Review, Skill, Store, encode


def skill(name, **kwargs):
    return Skill(name, f"# {name}", f"revision-{name}", **kwargs)


def draft(value=1, **kwargs):
    return {"summary": "Test result", "content": {"value": value}, **kwargs}


def call(name="work", task="Do work", key="one", inputs=None, refs=()):
    return Call(name, task, inputs or {"region": "US", "as_of": "2026-09-13"}, key, refs)


class KernelTests(unittest.IsolatedAsyncioTestCase):
    async def test_recursive_parallel_join_with_one_model_slot(self):
        kernel = Kernel(Registry([skill("work")]), Store(), ledger=Ledger(model_parallelism=1))

        async def run(frame, context):
            n = frame.call.inputs["n"]
            await kernel.ledger.model_call(lambda: asyncio.sleep(0))
            if n:
                receipts = await asyncio.gather(*(
                    kernel.call(call(task=f"part-{i}", key=str(i), inputs={"n": n - 1}), frame)
                    for i in range(2)))
                return draft(sum(kernel.read(frame, x["ref"])["content"]["value"] for x in receipts),
                             based_on=[x["ref"] for x in receipts])
            return draft()

        kernel.runner = run
        result = await asyncio.wait_for(kernel.call(call(inputs={"n": 2})), 3)
        self.assertEqual(kernel.store.get(result["ref"])["content"]["value"], 4)
        self.assertEqual(kernel.ledger.frames, 7)
        self.assertEqual(kernel.ledger.model_calls, 7)

    async def test_review_repairs_and_binds_to_new_candidate(self):
        registry = Registry([skill("work", review=Review(("critic",), 1)), skill("critic", critic=True)])
        kernel = Kernel(registry, Store())
        seen = []

        async def run(frame, context):
            if frame.call.skill == "critic":
                ref = frame.call.refs[0]
                value = kernel.read(frame, ref)["content"]["value"]
                seen.append(ref)
                return {"summary": "Independent check", "content": {
                    "candidate_ref": ref, "verdict": "pass" if value else "fail",
                    "findings": [] if value else ["Value is missing"],
                }}
            return draft(context["attempt"])

        kernel.runner = run
        receipt = await kernel.call(call())
        result = kernel.store.get(receipt["ref"])
        self.assertEqual(receipt["status"], "accepted")
        self.assertEqual(result["content"]["value"], 1)
        self.assertEqual(len(set(seen)), 2)
        final_review = kernel.store.get(result["reviews"][0])["content"]
        self.assertEqual(final_review["candidate_ref"], seen[-1])

    async def test_missing_malformed_or_wrong_candidate_review_cannot_pass(self):
        for verdict in ({}, {"candidate_ref": "wrong", "verdict": "pass", "findings": []},
                        {"candidate_ref": "wrong", "verdict": "fail", "findings": ["bad"]}):
            with self.subTest(verdict=verdict):
                kernel = Kernel(Registry([skill("work", review=Review(("critic",), 0)),
                                          skill("critic", critic=True)]), Store())

                async def run(frame, context):
                    return {"summary": "Result", "content": verdict} if frame.call.skill == "critic" else draft()

                kernel.runner = run
                result = await kernel.call(call())
                self.assertEqual(result["status"], "needs_review")

    async def test_inline_open_activates_review(self):
        kernel = Kernel(Registry([skill("work", links=("checked",)),
                                  skill("checked", review=Review(("critic",), 0)),
                                  skill("critic", critic=True)]), Store())

        async def run(frame, context):
            if frame.call.skill == "critic":
                raise RuntimeError("Reviewer unavailable")
            kernel.open(frame, "checked")
            return draft()

        kernel.runner = run
        result = await kernel.call(call())
        self.assertEqual(result["status"], "needs_review")

    async def test_reuse_filters_inputs_freshness_snapshot_and_status(self):
        kernel = Kernel(Registry([skill("work", links=("evidence",)), skill("evidence")]), Store())
        frame = Frame("parent", None, call(), ())
        base = {"session": kernel.session, "frame": "child", "skill": "evidence", "status": "accepted",
                "snapshot": kernel.registry.snapshot, "inputs": call().inputs,
                "created_at": time.time(), "summary": "Match", "content": {}}
        accepted = kernel.store.put(base)
        for change in ({"inputs": {"region": "JP"}}, {"created_at": 0}, {"snapshot": "old"},
                       {"status": "draft"}, {"session": "other"}):
            kernel.store.put({**base, **change})
        packet = kernel.open(frame, "work")
        self.assertEqual([v["ref"] for v in packet["candidates"]], [accepted])
        self.assertEqual(packet["missing"], [])

    async def test_context_packet_is_bounded_and_skill_bytes_preserved(self):
        kernel = Kernel(Registry([skill("work")], {"memory/notes/skills/work.md": "x" * 10000}), Store())
        packet = kernel.open(Frame("f", None, call(), ()), "work", limit=512)
        self.assertLessEqual(len(encode(packet)), 512)
        self.assertEqual(packet["text"], "# work")
        self.assertEqual(packet["omitted"], 1)

    async def test_concurrent_idempotency_and_key_conflict(self):
        kernel = Kernel(Registry([skill("work")]), Store())

        async def run(frame, context):
            await asyncio.sleep(0.01)
            return draft()

        kernel.runner = run
        a, b = await asyncio.gather(kernel.call(call()), kernel.call(call()))
        self.assertEqual(a, b)
        self.assertEqual(kernel.ledger.frames, 1)
        with self.assertRaisesRegex(Rejected, "Idempotency"):
            await kernel.call(call(task="different"))

    async def test_cycle_and_depth_limits(self):
        kernel = Kernel(Registry([skill("work")]), Store(), max_depth=0)

        async def run(frame, context):
            with self.assertRaisesRegex(Rejected, "Repeated active"):
                await kernel.call(call(key="cycle"), frame)
            with self.assertRaisesRegex(Rejected, "depth"):
                await kernel.call(call(task="narrower", key="depth"), frame)
            return draft()

        kernel.runner = run
        await kernel.call(call())

    async def test_global_budget_admission_is_atomic(self):
        ledger = Ledger(max_model_calls=2, model_parallelism=8)
        results = await asyncio.gather(*(ledger.model_call(lambda: asyncio.sleep(0)) for _ in range(8)),
                                       return_exceptions=True)
        self.assertEqual(sum(isinstance(x, Rejected) for x in results), 6)
        self.assertEqual(ledger.model_calls, 2)

    async def test_cancel_propagates_and_closes_children(self):
        kernel = Kernel(Registry([skill("work")]), Store())
        child_started = asyncio.Event()
        cancelled = asyncio.Event()

        async def run(frame, context):
            if frame.parent:
                child_started.set()
                try:
                    await asyncio.sleep(10)
                finally:
                    cancelled.set()
            return await kernel.call(call(task="child", key="child"), frame)

        kernel.runner = run
        root = asyncio.create_task(kernel.call(call()))
        await child_started.wait()
        root.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await root
        self.assertTrue(cancelled.is_set())
        self.assertTrue(all(job.done() for _, job in kernel.jobs.values()))

    async def test_session_deadline(self):
        kernel = Kernel(Registry([skill("work")]), Store(), deadline_seconds=0.02)

        async def run(frame, context):
            await asyncio.sleep(1)

        kernel.runner = run
        with self.assertRaises(TimeoutError):
            await kernel.call(call())

    async def test_draft_visibility_and_cross_session_denial(self):
        kernel = Kernel(Registry([skill("work")]), Store())
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
        with self.assertRaisesRegex(Rejected, "Critic skills"):
            Registry([skill("critic", critic=True, review=Review(("critic",), 1))])


if __name__ == "__main__":
    unittest.main()
