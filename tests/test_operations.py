"""Deterministic graph/lifecycle races, coordinated by events rather than sleeps."""

import asyncio
import unittest

from harness import Ledger, NodeRequest, Registry, Rejected, ReviewPolicy, Runtime, Store
from tests.support import draft, skill


def shared(node="b", *, key="b", task="Produce snapshot evidence", inputs=None, refs=()):
    return NodeRequest(node, task, inputs or {}, key, refs, reuse="session")


class ObservedStore(Store):
    def __init__(self):
        super().__init__()
        self.notifications = []

    def when(self, **fields):
        event = asyncio.Event()
        self.notifications.append((fields, event))
        return event

    def event(self, **value):
        super().event(**value)
        for fields, event in self.notifications:
            if all(value.get(key) == expected for key, expected in fields.items()):
                event.set()


class OperationTests(unittest.IsolatedAsyncioTestCase):
    def runtime(self, names=("root", "a", "b", "c", "d"), **kwargs):
        store = ObservedStore()
        runtime = Runtime(Registry([skill(name) for name in names]), store, **kwargs)
        self.addCleanup(store.close)
        self.addAsyncCleanup(runtime.aclose)
        return runtime

    async def wait(self, event):
        await asyncio.wait_for(event.wait(), 2)

    def assert_released(self, runtime):
        self.assertEqual(runtime.operations.waits, {})
        self.assertTrue(all(not op.waiters for op in runtime.operations.operations.values()))
        self.assertTrue(all(op.task.done() for op in runtime.operations.operations.values()))

    async def test_diamond_starts_once_joins_running_and_reuses_completed_result(self):
        runtime = self.runtime()
        started, finish = asyncio.Event(), asyncio.Event()
        joined = runtime.store.when(type="call_acquired", disposition="joined")
        runs = 0

        async def run(frame, context):
            nonlocal runs
            node = frame.request.node
            if node == "root":
                branches = await asyncio.gather(
                    *(
                        runtime.run_node(NodeRequest(n, f"Interpret as {n}", {}, n), frame)
                        for n in ("a", "c")
                    )
                )
                later = await runtime.run_node(NodeRequest("d", "Later check", {}, "d"), frame)
                return draft(based_on=[*(r["ref"] for r in branches), later["ref"]])
            if node == "b":
                runs += 1
                started.set()
                await finish.wait()
                return draft(value=7)
            if node == "c":
                await started.wait()
            result = await runtime.run_node(shared(key=f"{node}:b"), frame)
            return draft(based_on=[result["ref"]])

        runtime.register_executor("agent", run)
        root = asyncio.create_task(runtime.run_node(NodeRequest("root", "Investigate", {}, "root")))
        await self.wait(joined)
        self.assertEqual(runs, 1)
        finish.set()
        result = await root
        branches = [runtime.store.get(ref) for ref in runtime.store.get(result["ref"])["based_on"]]
        refs = [record["based_on"][0] for record in branches]
        self.assertEqual(len(set(refs)), 1)
        b = runtime.store.get(refs[0])
        calls = [
            e
            for e in runtime.store.events()
            if e["type"] == "call_acquired" and e["operation"] == b["frame"]
        ]
        self.assertEqual([e["disposition"] for e in calls], ["started", "joined", "reused"])
        self.assertEqual(len({e["caller"] for e in calls}), 3)
        self.assertEqual(runtime.ledger.frames, 5)
        self.assert_released(runtime)

    async def test_conditional_branch_can_be_the_first_requester(self):
        runtime = self.runtime()

        async def run(frame, context):
            if frame.request.node == "root":
                a, c = await asyncio.gather(
                    *(runtime.run_node(NodeRequest(n, "Inspect", {}, n), frame) for n in ("a", "c"))
                )
                return draft(based_on=[a["ref"], c["ref"]])
            if frame.request.node == "c":
                b = await runtime.run_node(shared(), frame)
                return draft(based_on=[b["ref"]])
            return draft()

        runtime.register_executor("agent", run)
        await runtime.run_node(NodeRequest("root", "Investigate", {}, "root"))
        admissions = [e for e in runtime.store.events() if e["type"] == "admitted"]
        b = next(e for e in admissions if e["node"] == "b")
        c = next(e for e in admissions if e["node"] == "c")
        self.assertEqual(b["origin"], c["frame"])
        self.assert_released(runtime)

    async def test_cancelling_first_branch_does_not_cancel_shared_producer(self):
        runtime = self.runtime()
        started, finish = asyncio.Event(), asyncio.Event()
        joined = runtime.store.when(type="call_acquired", disposition="joined")
        branches = {}
        producer_cancelled = False

        async def run(frame, context):
            nonlocal producer_cancelled
            if frame.request.node == "root":
                for name in ("a", "c"):
                    branches[name] = asyncio.create_task(
                        runtime.run_node(NodeRequest(name, name, {}, name), frame)
                    )
                results = await asyncio.gather(*branches.values(), return_exceptions=True)
                return draft(based_on=[r["ref"] for r in results if isinstance(r, dict)])
            if frame.request.node == "b":
                started.set()
                try:
                    await finish.wait()
                except asyncio.CancelledError:
                    producer_cancelled = True
                    raise
                return draft()
            if frame.request.node == "c":
                await started.wait()
            receipt = await runtime.run_node(shared(), frame)
            return draft(based_on=[receipt["ref"]])

        runtime.register_executor("agent", run)
        root = asyncio.create_task(runtime.run_node(NodeRequest("root", "Investigate", {}, "root")))
        await self.wait(joined)
        branches["a"].cancel()
        with self.assertRaises(asyncio.CancelledError):
            await branches["a"]
        b = next(op for op in runtime.operations.shared.values())
        self.assertEqual(b.state, "running")
        self.assertEqual(len(b.waiters), 1)
        finish.set()
        self.assertEqual((await root)["status"], "accepted")
        self.assertFalse(producer_cancelled)
        self.assert_released(runtime)

    async def test_duplicate_key_waiters_are_independently_released(self):
        runtime = self.runtime(names=("b",))
        finish = asyncio.Event()
        replayed = runtime.store.when(type="call_acquired", disposition="replayed")

        async def run(frame, context):
            await finish.wait()
            return draft()

        runtime.register_executor("agent", run)
        first = asyncio.create_task(runtime.run_node(shared()))
        second = asyncio.create_task(runtime.run_node(shared()))
        await self.wait(replayed)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertEqual(len(next(iter(runtime.operations.shared.values())).waiters), 1)
        finish.set()
        receipt = await second
        receipt["status"] = "tampered"
        self.assertEqual((await runtime.run_node(shared()))["status"], "accepted")
        self.assertEqual(runtime.ledger.frames, 1)
        self.assert_released(runtime)

    async def test_replacement_waits_for_last_waiter_cleanup_and_preserves_retry_identity(self):
        runtime = self.runtime(names=("b",))
        started, cleaning, finish_cleanup = asyncio.Event(), asyncio.Event(), asyncio.Event()
        draining = runtime.store.when(type="operation_draining")
        runs = 0

        async def run(frame, context):
            nonlocal runs
            runs += 1
            if runs == 1:
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cleaning.set()
                    await finish_cleanup.wait()
            return draft(value=runs)

        runtime.register_executor("agent", run)
        old = asyncio.create_task(runtime.run_node(shared(key="old")))
        await self.wait(started)
        old.cancel()
        await self.wait(cleaning)
        replacement = asyncio.create_task(runtime.run_node(shared(key="new")))
        await self.wait(draining)
        self.assertEqual(runs, 1)
        with self.assertRaisesRegex(Rejected, "Idempotency"):
            await runtime.run_node(shared(key="new", task="Conflicting task during cleanup"))
        # A second cancellation can interrupt the caller's cleanup wait, but must
        # not interrupt the producer's cleanup or leak its already released lease.
        old.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await old
        finish_cleanup.set()
        with self.assertRaises(asyncio.CancelledError):
            await old
        receipt = await replacement
        self.assertEqual(runtime.store.get(receipt["ref"])["content"]["value"], 2)
        with self.assertRaises(asyncio.CancelledError):
            await runtime.run_node(shared(key="old"))
        self.assertEqual((await runtime.run_node(shared(key="later")))["ref"], receipt["ref"])
        self.assertEqual(runs, 2)
        self.assert_released(runtime)

    async def test_failure_requires_a_new_call_key_and_can_start_a_new_generation(self):
        runtime = self.runtime(names=("b",))
        runs = 0

        async def run(frame, context):
            nonlocal runs
            runs += 1
            if runs == 1:
                raise RuntimeError("Transient producer failure")
            return draft()

        runtime.register_executor("agent", run)
        for key in ("first", "first"):
            with self.assertRaisesRegex(RuntimeError, "Transient"):
                await runtime.run_node(shared(key=key))
        self.assertEqual(runs, 1)
        self.assertEqual((await runtime.run_node(shared(key="retry")))["status"], "accepted")
        self.assertEqual(runs, 2)
        self.assert_released(runtime)

    async def test_stopping_executor_cannot_start_work_read_or_publish_after_uncancel(self):
        runtime = self.runtime(names=("b",))
        started, cleaned = asyncio.Event(), asyncio.Event()

        async def run(frame, context):
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                # A trusted custom executor may catch cancellation for cleanup.
                # Even clearing the task flag cannot reopen its runtime context.
                asyncio.current_task().uncancel()
                with self.assertRaisesRegex(Rejected, "stopping"):
                    await runtime.run_node(shared(key="cleanup-child"), frame)
                with self.assertRaisesRegex(Rejected, "stopping"):
                    runtime.read_node(frame, "b")
                cleaned.set()
                return draft()

        runtime.register_executor("agent", run)
        caller = asyncio.create_task(runtime.run_node(shared()))
        await self.wait(started)
        caller.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await caller
        await self.wait(cleaned)
        operation = next(iter(runtime.operations.operations.values()))
        self.assertIsInstance(operation.task.exception(), Rejected)
        self.assertEqual(runtime.store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0], 0)
        self.assertEqual(runtime.ledger.frames, 1)
        self.assert_released(runtime)

    async def test_unaccepted_result_is_not_a_shared_cache_hit(self):
        runtime = self.runtime(names=("b", "review"), reviews={"b": ReviewPolicy(("review",))})
        reviews = 0

        async def run(frame, context):
            nonlocal reviews
            if frame.request.node == "review":
                reviews += 1
                return {
                    "summary": "Review",
                    "content": {
                        "candidate_ref": frame.request.refs[0],
                        "verdict": "fail" if reviews == 1 else "pass",
                        "findings": ["Not ready"] if reviews == 1 else [],
                    },
                }
            return draft()

        runtime.register_executor("agent", run)
        self.assertEqual((await runtime.run_node(shared(key="first")))["status"], "needs_review")
        self.assertEqual((await runtime.run_node(shared(key="retry")))["status"], "accepted")
        self.assertEqual(reviews, 2)
        self.assertTrue(
            all(
                e["reuse"] == "fresh"
                for e in runtime.store.events()
                if e["type"] == "admitted" and e["node"] == "review"
            )
        )
        self.assert_released(runtime)

    async def test_different_work_and_explicit_fresh_calls_do_not_share(self):
        runtime = self.runtime(names=("b",))

        async def run(frame, context):
            return draft()

        runtime.register_executor("agent", run)
        requests = [
            shared(key="one"),
            shared(key="same"),
            shared(key="question", task="Different question"),
            shared(key="input", inputs={"version": 2}),
            NodeRequest("b", "Produce snapshot evidence", {}, "fresh-one"),
            NodeRequest("b", "Produce snapshot evidence", {}, "fresh-two"),
        ]
        results = [await runtime.run_node(request) for request in requests]
        self.assertEqual(results[0], results[1])
        self.assertEqual(len({r["ref"] for r in results}), 5)
        self.assertEqual(runtime.ledger.frames, 5)
        with self.assertRaisesRegex(Rejected, "Idempotency"):
            await runtime.run_node(NodeRequest("b", "Produce snapshot evidence", {}, "one"))
        self.assert_released(runtime)

    async def test_different_evidence_does_not_share_and_hash_knowledge_is_not_a_grant(self):
        runtime = self.runtime(names=("root", "a", "b", "c", "evidence"))
        finished = asyncio.Event()
        stolen = []

        async def run(frame, context):
            node = frame.request.node
            if node == "root":
                results = await asyncio.gather(
                    *(runtime.run_node(NodeRequest(n, n, {}, n), frame) for n in ("a", "c"))
                )
                return draft(based_on=[r["ref"] for r in results])
            if node == "a":
                evidence = [
                    await runtime.run_node(NodeRequest("evidence", "Read", {}, str(i)), frame)
                    for i in range(2)
                ]
                stolen.append(evidence[0]["ref"])
                outputs = [
                    await runtime.run_node(shared(key=f"b:{i}", refs=(r["ref"],)), frame)
                    for i, r in enumerate(evidence)
                ]
                self.assertNotEqual(outputs[0]["ref"], outputs[1]["ref"])
                finished.set()
                return draft(based_on=[r["ref"] for r in outputs])
            if node == "c":
                await finished.wait()
                with self.assertRaisesRegex(Rejected, "not visible"):
                    await runtime.run_node(shared(refs=(stolen[0],)), frame)
            return draft(based_on=list(frame.request.refs))

        runtime.register_executor("agent", run)
        await runtime.run_node(NodeRequest("root", "Investigate", {}, "root"))
        self.assertEqual(
            sum(e["node"] == "b" for e in runtime.store.events() if e["type"] == "admitted"), 2
        )
        self.assert_released(runtime)

    async def test_cross_branch_wait_cycle_is_rejected_without_deadlock(self):
        runtime = self.runtime(names=("root", "x", "y"))
        y_started = asyncio.Event()
        joined = runtime.store.when(type="call_acquired", disposition="joined")

        def request(node, key):
            return shared(node, task=f"Evaluate {node}", key=key)

        async def run(frame, context):
            if frame.request.node == "root":
                results = await asyncio.gather(
                    *(runtime.run_node(request(n, n), frame) for n in ("x", "y"))
                )
                return draft(based_on=[r["ref"] for r in results])
            if frame.request.node == "x":
                await y_started.wait()
                result = await runtime.run_node(request("y", "dependency"), frame)
                return draft(based_on=[result["ref"]])
            y_started.set()
            await joined.wait()
            with self.assertRaisesRegex(Rejected, "Wait cycle"):
                await runtime.run_node(request("x", "dependency"), frame)
            return draft()

        runtime.register_executor("agent", run)
        result = await asyncio.wait_for(
            runtime.run_node(NodeRequest("root", "Join", {}, "root")), 2
        )
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(runtime.ledger.frames, 3)
        self.assert_released(runtime)

    async def test_shared_attachment_checks_actual_dependency_depth(self):
        runtime = self.runtime(names=("root", "x", "y", "z"), max_depth=2)
        y_started, z_started, finish_z = asyncio.Event(), asyncio.Event(), asyncio.Event()
        joined = runtime.store.when(type="call_acquired", disposition="joined")

        def request(node, key):
            return shared(node, task=f"Evaluate {node}", key=key)

        async def run(frame, context):
            node = frame.request.node
            if node == "root":
                results = await asyncio.gather(
                    *(runtime.run_node(request(n, n), frame) for n in ("x", "y", "z"))
                )
                return draft(based_on=[r["ref"] for r in results])
            if node == "x":
                await y_started.wait()
                result = await runtime.run_node(request("y", "dependency"), frame)
                return draft(based_on=[result["ref"]])
            if node == "y":
                y_started.set()
                await joined.wait()
                await z_started.wait()
                with self.assertRaisesRegex(Rejected, "depth"):
                    await runtime.run_node(request("z", "dependency"), frame)
                finish_z.set()
            else:
                z_started.set()
                await finish_z.wait()
            return draft()

        runtime.register_executor("agent", run)
        await asyncio.wait_for(runtime.run_node(NodeRequest("root", "Join", {}, "root")), 2)
        self.assertEqual(runtime.ledger.frames, 4)
        self.assert_released(runtime)

    async def test_reuse_is_admitted_when_frame_budget_is_full_but_calls_are_bounded(self):
        runtime = self.runtime(names=("b",), ledger=Ledger(max_frames=1, max_calls=3))

        async def run(frame, context):
            return draft()

        runtime.register_executor("agent", run)
        await runtime.run_node(shared(key="first"))
        await runtime.run_node(shared(key="reuse"))
        with self.assertRaisesRegex(Rejected, "frame budget"):
            await runtime.run_node(NodeRequest("b", "Different work", {}, "fresh"))
        with self.assertRaisesRegex(Rejected, "call budget"):
            await runtime.run_node(shared(key="too-many"))
        self.assert_released(runtime)
