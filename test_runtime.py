import asyncio
import time
import unittest
from dataclasses import replace

from runtime import NodeRequest, Frame, Runtime, Ledger, Registry, Rejected, Review, Node, Store, encode


def skill(name, **kwargs):
    return Node(name, f"# {name}", f"revision-{name}", **kwargs)


def draft(value=1, **kwargs):
    return {"summary": "Test result", "content": {"value": value}, **kwargs}


def call(name="work", task="Do work", key="one", inputs=None, refs=()):
    return NodeRequest(name, task, inputs or {"region": "US", "as_of": "2026-09-13"}, key, refs)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_recursive_parallel_join_with_one_model_slot(self):
        kernel = Runtime(Registry([skill("work")]), Store(), ledger=Ledger(model_parallelism=1))

        async def run(frame, context):
            n = frame.request.inputs["n"]
            await kernel.ledger.model_call(lambda: asyncio.sleep(0))
            if n:
                receipts = await asyncio.gather(*(
                    kernel.run_node(call(task=f"part-{i}", key=str(i), inputs={"n": n - 1}), frame)
                    for i in range(2)))
                return draft(sum(kernel.read(frame, x["ref"])["content"]["value"] for x in receipts),
                             based_on=[x["ref"] for x in receipts])
            return draft()

        kernel.agent_runner = run
        result = await asyncio.wait_for(kernel.run_node(call(inputs={"n": 2})), 3)
        self.assertEqual(kernel.store.get(result["ref"])["content"]["value"], 4)
        self.assertEqual(kernel.ledger.frames, 7)
        self.assertEqual(kernel.ledger.model_calls, 7)

    async def test_review_repairs_and_binds_to_new_candidate(self):
        registry = Registry([skill("work", review=Review(("critic",), 1)), skill("critic", critic=True)])
        kernel = Runtime(registry, Store())
        seen = []

        async def run(frame, context):
            if frame.request.node == "critic":
                ref = frame.request.refs[0]
                value = kernel.read(frame, ref)["content"]["value"]
                seen.append(ref)
                return {"summary": "Independent check", "content": {
                    "candidate_ref": ref, "verdict": "pass" if value else "fail",
                    "findings": [] if value else ["Value is missing"],
                }}
            return draft(context["attempt"])

        kernel.agent_runner = run
        receipt = await kernel.run_node(call())
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
                kernel = Runtime(Registry([skill("work", review=Review(("critic",), 0)),
                                          skill("critic", critic=True)]), Store())

                async def run(frame, context):
                    return {"summary": "Result", "content": verdict} if frame.request.node == "critic" else draft()

                kernel.agent_runner = run
                result = await kernel.run_node(call())
                self.assertEqual(result["status"], "needs_review")

    async def test_inline_open_activates_review(self):
        kernel = Runtime(Registry([skill("work", links=("checked",)),
                                  skill("checked", review=Review(("critic",), 0)),
                                  skill("critic", critic=True)]), Store())

        async def run(frame, context):
            if frame.request.node == "critic":
                raise RuntimeError("Reviewer unavailable")
            kernel.read_node(frame, "checked", enter=True)
            return draft()

        kernel.agent_runner = run
        result = await kernel.run_node(call())
        self.assertEqual(result["status"], "needs_review")

    async def test_reuse_filters_inputs_freshness_snapshot_and_status(self):
        kernel = Runtime(Registry([skill("work", links=("evidence",)), skill("evidence")]), Store())
        frame = Frame("parent", None, call(), ())
        base = {"session": kernel.session, "frame": "child", "node": "evidence", "status": "accepted",
                "snapshot": kernel.registry.snapshot, "inputs": call().inputs,
                "created_at": time.time(), "summary": "Match", "content": {}}
        accepted = kernel.store.put(base)
        for change in ({"inputs": {"region": "JP"}}, {"created_at": 0}, {"snapshot": "old"},
                       {"status": "draft"}, {"session": "other"}):
            kernel.store.put({**base, **change})
        packet = kernel.read_node(frame, "work")
        self.assertEqual([v["ref"] for v in packet["candidates"]], [accepted])
        self.assertEqual(packet["missing"], [])

    async def test_context_packet_is_bounded_and_skill_bytes_preserved(self):
        kernel = Runtime(Registry([skill("work")], {"memory/notes/skills/work.md": "x" * 10000}), Store())
        packet = kernel.read_node(Frame("f", None, call(), ()), "work", limit=512)
        self.assertLessEqual(len(encode(packet)), 512)
        self.assertEqual(packet["text"], "# work")
        self.assertEqual(packet["omitted"], 1)

    async def test_concurrent_idempotency_and_key_conflict(self):
        kernel = Runtime(Registry([skill("work")]), Store())

        async def run(frame, context):
            await asyncio.sleep(0.01)
            return draft()

        kernel.agent_runner = run
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

        kernel.agent_runner = run
        await kernel.run_node(call())

    async def test_global_budget_admission_is_atomic(self):
        ledger = Ledger(max_model_calls=2, model_parallelism=8)
        results = await asyncio.gather(*(ledger.model_call(lambda: asyncio.sleep(0)) for _ in range(8)),
                                       return_exceptions=True)
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

        kernel.agent_runner = run
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

        kernel.agent_runner = run
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
        with self.assertRaisesRegex(Rejected, "Critic skills"):
            Registry([skill("critic", critic=True, review=Review(("critic",), 1))])

    async def test_inspection_does_not_activate_review(self):
        runtime = Runtime(Registry([skill('work'), skill('checked', review=Review(('critic',), 0)),
                                    skill('critic', critic=True)]), Store())
        frame = Frame('f', None, call(), ())
        runtime.read_node(frame, 'checked')
        self.assertEqual(frame.active, set())
        runtime.read_node(frame, 'checked', enter=True)
        self.assertEqual(frame.active, {'checked'})

    async def test_reviewer_grants_cover_reads_entry_and_descendants(self):
        runtime = Runtime(Registry([skill('work'), skill('evidence'),
                                    skill('critic', critic=True, links=('evidence',))]), Store())
        secret = runtime.store.put({'session':runtime.session, 'frame':'other', 'node':'evidence',
            'status':'accepted', 'inputs':{}, 'snapshot':runtime.registry.snapshot,
            'created_at':time.time(), 'summary':'Unrelated reviewer conclusion', 'content':{}})
        seen=[]
        async def run(frame, context):
            if frame.request.node=='work' and frame.parent is None:
                return await root(frame)
            seen.append(frame.restricted)
            with self.assertRaisesRegex(Rejected, 'not visible'):
                runtime.read(frame, secret)
            self.assertEqual(runtime.read_node(frame,'critic')['candidates'], [])
            if frame.request.node=='critic':
                await runtime.run_node(NodeRequest('work','narrow evidence check',{},'sub'),frame)
            return draft()
        async def root(frame):
            result=await runtime.run_node(NodeRequest('critic','check',{},'critic'),frame)
            return draft(based_on=[result['ref']])
        runtime.agent_runner=run
        await runtime.run_node(NodeRequest('work','root',{},'root'))
        self.assertEqual(seen,[True,True])

    async def test_inconclusive_required_review_blocks_acceptance(self):
        runtime=Runtime(Registry([skill('work',review=Review(('critic',),0)),
                                  skill('critic',critic=True)]),Store())
        async def run(frame,context):
            if frame.request.node=='critic':
                return {'summary':'Insufficient evidence','content':{
                    'candidate_ref':frame.request.refs[0],'verdict':'inconclusive','findings':[]}}
            return draft()
        runtime.agent_runner=run
        result=await runtime.run_node(call())
        self.assertEqual(result['status'],'needs_review')

    async def test_code_runner_dispatch_without_agent(self):
        async def code(frame, context):
            return draft(value=7)
        runtime=Runtime(Registry([skill('calculate',kind='code',code='body')]),Store(),code_runner=code)
        result=await runtime.run_node(NodeRequest('calculate','calculate',{},'root'))
        self.assertEqual(runtime.store.get(result['ref'])['content']['value'],7)
        self.assertEqual(runtime.ledger.model_calls,0)


if __name__ == "__main__":
    unittest.main()
