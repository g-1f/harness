"""Checkpoint replay, focused calls and lifetime rules across graph branches."""

import asyncio
import unittest

from harness import Ledger, NodeRequest, Registry, Rejected, Runtime, Store
from tests.support import draft, skill


def request(node="b", task="Collect shared evidence", *, key="b", refs=(), reuse="session"):
    return NodeRequest(node, task, {"snapshot": 1}, key, refs, reuse)


class ProgressTests(unittest.IsolatedAsyncioTestCase):
    def runtime(self, names=("root", "a", "b", "c"), **kwargs):
        runtime = Runtime(Registry([skill(name) for name in names]), Store(), **kwargs)
        self.addCleanup(runtime.store.close)
        self.addAsyncCleanup(runtime.aclose)
        return runtime

    async def test_parallel_consumers_reuse_checkpoint_for_different_aspects(self):
        runtime = self.runtime()
        checkpoint_seen, finish_b = asyncio.Event(), asyncio.Event()
        views = {}

        async def run(frame, context):
            node, task = frame.request.node, frame.request.task
            if node == "root":
                a, c = await asyncio.gather(
                    *(
                        runtime.run_node(
                            request(name, f"Interpret {name}", key=name, reuse="fresh"), frame
                        )
                        for name in ("a", "c")
                    )
                )
                return draft(based_on=[a["ref"], c["ref"]])
            if node == "b" and task == "Collect shared evidence":
                checkpoint = await runtime.publish_checkpoint(
                    frame, {"summary": "Source evidence", "content": {"value": 42}, "based_on": []}
                )
                await finish_b.wait()
                return draft(
                    value="A deliberately short final summary", based_on=[checkpoint["ref"]]
                )
            if node == "b":
                source = runtime.read(frame, frame.request.refs[0])
                return draft(
                    value=f"{task}: {source['content']['value']}", based_on=list(frame.request.refs)
                )

            opened = await runtime.open_node(request(key="shared-b"), frame)
            self.assertIn(frame.id, runtime.operations.waits)
            event = await runtime.next_node_event(opened["handle"], 0, frame)
            self.assertIn(frame.id, runtime.operations.waits)
            self.assertEqual(event["kind"], "checkpoint")
            self.assertEqual(runtime.read(frame, event["receipt"]["ref"])["content"]["value"], 42)
            focus = await runtime.run_node(
                request(
                    "b",
                    f"Investigate {node} from this checkpoint",
                    key=f"focus:{node}",
                    refs=(event["receipt"]["ref"],),
                    reuse="fresh",
                ),
                frame,
            )
            views[node] = {"checkpoint": event["receipt"]["ref"], "focused": focus["ref"]}
            if len(views) == 2:
                checkpoint_seen.set()
            terminal = await runtime.next_node_event(opened["handle"], event["cursor"], frame)
            self.assertEqual(terminal["kind"], "complete")
            return draft(
                based_on=[event["receipt"]["ref"], focus["ref"], terminal["receipt"]["ref"]]
            )

        runtime.register_executor("agent", run)
        root = asyncio.create_task(
            runtime.run_node(request("root", "Start", key="root", reuse="fresh"))
        )
        await asyncio.wait_for(checkpoint_seen.wait(), 2)
        self.assertEqual(views["a"]["checkpoint"], views["c"]["checkpoint"])
        self.assertNotEqual(views["a"]["focused"], views["c"]["focused"])
        self.assertEqual(
            sum(e["type"] == "admitted" and e["node"] == "b" for e in runtime.store.events()), 3
        )
        self.assertEqual(
            runtime.operations.shared[next(iter(runtime.operations.shared))].state, "running"
        )
        finish_b.set()
        self.assertEqual((await root)["status"], "published")
        self.assertEqual(runtime.operations.waits, {})
        self.assertEqual(runtime._handles, {})
        self.assertTrue(all(not op.waiters for op in runtime.operations.operations.values()))

    async def test_late_join_replays_ordered_checkpoints_before_terminal(self):
        runtime = self.runtime(names=("b",))
        two_published, finish = asyncio.Event(), asyncio.Event()

        async def run(frame, context):
            for n in (1, 2):
                await runtime.publish_checkpoint(
                    frame, {"summary": f"Step {n}", "content": {"value": n}, "based_on": []}
                )
            two_published.set()
            await finish.wait()
            return draft()

        runtime.register_executor("agent", run)
        first = await runtime.open_node(request(key="first"))
        await asyncio.wait_for(two_published.wait(), 2)
        second = await runtime.open_node(request(key="second"))
        one = await runtime.next_node_event(second["handle"], 0)
        two = await runtime.next_node_event(second["handle"], one["cursor"])
        self.assertEqual([one["cursor"], two["cursor"]], [1, 2])
        self.assertEqual(
            [runtime.store.get(e["receipt"]["ref"])["content"]["value"] for e in (one, two)],
            [1, 2],
        )
        with self.assertRaisesRegex(Rejected, "ahead"):
            await runtime.next_node_event(second["handle"], 3)
        await runtime.close_node(first["handle"])
        self.assertEqual(await runtime.close_node(first["handle"]), {"closed": True})
        self.assertEqual(next(iter(runtime.operations.operations.values())).state, "running")
        finish.set()
        terminal = await runtime.next_node_event(second["handle"], two["cursor"])
        self.assertEqual(terminal["kind"], "complete")
        self.assertEqual(runtime._handles, {})
        self.assertEqual(runtime.ledger.frames, 1)

    async def test_early_close_wakes_pending_observer_without_stopping_other_caller(self):
        runtime = self.runtime(names=("b",))
        finish = asyncio.Event()

        async def run(frame, context):
            await finish.wait()
            return draft()

        runtime.register_executor("agent", run)
        first = await runtime.open_node(request(key="first"))
        second = await runtime.open_node(request(key="second"))
        pending = asyncio.create_task(runtime.next_node_event(first["handle"], 0))
        await asyncio.sleep(0)
        self.assertTrue(runtime.operations.waits == {})  # Launcher has no frame edge.
        await runtime.close_node(first["handle"])
        with self.assertRaisesRegex(Rejected, "closed"):
            await asyncio.wait_for(pending, 2)
        self.assertEqual(next(iter(runtime.operations.operations.values())).state, "running")
        finish.set()
        self.assertEqual((await runtime.next_node_event(second["handle"], 0))["kind"], "complete")

    async def test_negative_domain_checkpoint_is_published_without_implicit_review(self):
        runtime = self.runtime(names=("b", "review"))

        async def run(frame, context):
            self.assertEqual(frame.request.node, "b")
            progress = await runtime.publish_checkpoint(
                frame, {"summary": "Failed assessment", "content": {"verdict": "fail"}}
            )
            return draft(based_on=[progress["ref"]])

        runtime.register_executor("agent", run)
        opened = await runtime.open_node(request())
        event = await runtime.next_node_event(opened["handle"], 0)
        self.assertEqual(event["kind"], "checkpoint")
        record = runtime.store.get(event["receipt"]["ref"])
        self.assertEqual(record["content"]["verdict"], "fail")
        self.assertEqual(record["status"], "published")
        final = await runtime.next_node_event(opened["handle"], 1)
        self.assertEqual(final["kind"], "complete")
        self.assertEqual(runtime.ledger.frames, 1)
        self.assertEqual(
            runtime.store.get(final["receipt"]["ref"])["based_on"], [event["receipt"]["ref"]]
        )

    async def test_open_handle_ownership_budget_and_auto_release(self):
        runtime = self.runtime(names=("root", "b"), ledger=Ledger(max_checkpoints=1))
        ready = asyncio.Event()

        async def run(frame, context):
            if frame.request.node == "root":
                opened = await runtime.open_node(request(), frame)
                fake = type(frame)(frame.id, frame.origin, frame.request)
                with self.assertRaisesRegex(Rejected, "another caller"):
                    await runtime.next_node_event(opened["handle"], 0, fake)
                event = await runtime.next_node_event(opened["handle"], 0, frame)
                self.assertEqual(event["kind"], "checkpoint")
                self.assertEqual(event["receipt"]["status"], "published")
                # An unclosed handle cannot be forgotten at publication.
                return draft()
            await runtime.publish_checkpoint(
                frame, {"summary": "One", "content": {"value": 1}, "based_on": []}
            )
            with self.assertRaisesRegex(Rejected, "checkpoint budget"):
                await runtime.publish_checkpoint(
                    frame, {"summary": "Two", "content": {"value": 2}, "based_on": []}
                )
            ready.set()
            await asyncio.Event().wait()

        runtime.register_executor("agent", run)
        with self.assertRaisesRegex(Rejected, "Join or close"):
            await runtime.run_node(request("root", "Start", key="root", reuse="fresh"))
        await asyncio.wait_for(ready.wait(), 2)
        self.assertEqual(runtime._handles, {})
        self.assertTrue(all(not op.waiters for op in runtime.operations.operations.values()))

    async def test_final_only_call_does_not_grant_unobserved_checkpoints(self):
        runtime = self.runtime(names=("root", "b"))
        checkpoint = None

        async def run(frame, context):
            nonlocal checkpoint
            if frame.request.node == "b":
                checkpoint = await runtime.publish_checkpoint(frame, draft(1))
                return draft(2, based_on=[checkpoint["ref"]])
            final = await runtime.run_node(request(), frame)
            record = runtime.read(frame, final["ref"])
            self.assertEqual(record["based_on"], [checkpoint["ref"]])
            self.assertEqual(frame.grants, {final["ref"]})
            with self.assertRaisesRegex(Rejected, "not visible"):
                runtime.read(frame, checkpoint["ref"])
            self.assertEqual(frame.handles, set())
            return draft(based_on=[final["ref"]])

        runtime.register_executor("agent", run)
        await runtime.run_node(request("root", "Use final", key="root", reuse="fresh"))
        self.assertEqual(runtime.ledger.calls, 2)
        self.assertEqual(runtime.operations.waits, {})

    async def test_expired_session_still_allows_owner_to_release(self):
        runtime = self.runtime(names=("b",))

        async def run(frame, context):
            await asyncio.Event().wait()

        runtime.register_executor("agent", run)
        opened = await runtime.open_node(request())
        runtime.deadline = 0
        await runtime.close_node(opened["handle"])
        self.assertEqual(runtime._handles, {})
        self.assertTrue(all(not op.waiters for op in runtime.operations.operations.values()))

    async def test_concurrent_checkpoint_cursors_follow_publication_order(self):
        runtime = self.runtime(names=("b",))
        first_started, release_first = asyncio.Event(), asyncio.Event()

        async def run(frame, context):
            async def first_checkpoint():
                first_started.set()
                await release_first.wait()
                return await runtime.publish_checkpoint(frame, draft(1))

            first = asyncio.create_task(first_checkpoint())
            await first_started.wait()
            second = await runtime.publish_checkpoint(frame, draft(2))
            release_first.set()
            first_receipt = await first
            return draft(3, based_on=[first_receipt["ref"], second["ref"]])

        runtime.register_executor("agent", run)
        opened = await runtime.open_node(request())
        one = await runtime.next_node_event(opened["handle"], 0)
        two = await runtime.next_node_event(opened["handle"], one["cursor"])
        self.assertEqual([one["cursor"], two["cursor"]], [1, 2])
        self.assertEqual(
            [runtime.store.get(e["receipt"]["ref"])["content"]["value"] for e in (one, two)], [2, 1]
        )
        await runtime.next_node_event(opened["handle"], two["cursor"])

    async def test_deadline_failure_during_pending_read_releases_terminal_handle(self):
        runtime = self.runtime(names=("b",))

        async def run(frame, context):
            runtime.deadline = 0
            return draft()

        runtime.register_executor("agent", run)
        opened = await runtime.open_node(request())
        with self.assertRaisesRegex(Rejected, "deadline"):
            await runtime.next_node_event(opened["handle"], 0)
        self.assertEqual(runtime._handles, {})

    async def test_one_pending_read_per_handle_and_cancelled_read_can_retry(self):
        runtime = self.runtime(names=("b",))
        finish = asyncio.Event()

        async def run(frame, context):
            await finish.wait()
            await runtime.publish_checkpoint(frame, draft(42))
            return draft()

        runtime.register_executor("agent", run)
        opened = await runtime.open_node(request())
        pending = asyncio.create_task(runtime.next_node_event(opened["handle"], 0))
        await asyncio.sleep(0)
        with self.assertRaisesRegex(Rejected, "already"):
            await asyncio.wait_for(runtime.next_node_event(opened["handle"], 0), 0.1)
        pending.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await pending
        self.assertIn(opened["handle"], runtime._handles)
        finish.set()
        event = await runtime.next_node_event(opened["handle"], 0)
        self.assertEqual(event["kind"], "checkpoint")
        await runtime.next_node_event(opened["handle"], event["cursor"])

    async def test_failed_producer_preserves_checkpoint_and_retry_generation(self):
        runtime = self.runtime(names=("b",))

        async def run(frame, context):
            await runtime.publish_checkpoint(frame, draft(42))
            raise RuntimeError("producer failed")

        runtime.register_executor("agent", run)
        refs = []
        for key in ("original", "original", "new-attempt"):
            opened = await runtime.open_node(request(key=key))
            event = await runtime.next_node_event(opened["handle"], 0)
            refs.append(event["receipt"]["ref"])
            with self.assertRaisesRegex(RuntimeError, "producer failed"):
                await runtime.next_node_event(opened["handle"], event["cursor"])
            self.assertNotIn(opened["handle"], runtime._handles)
            self.assertEqual(runtime.store.get(refs[-1])["status"], "published")
        self.assertEqual(refs[0], refs[1])
        self.assertNotEqual(refs[1], refs[2])
        self.assertEqual(runtime.ledger.frames, 2)

    async def test_observation_cycle_across_existing_branches(self):
        runtime = self.runtime(names=("x", "y"))
        ready, finish = asyncio.Event(), asyncio.Event()
        frames = {}

        async def run(frame, context):
            frames[frame.request.node] = frame
            if len(frames) == 2:
                ready.set()
            await finish.wait()
            return draft()

        runtime.register_executor("agent", run)
        roots = [await runtime.open_node(request(name, key=name)) for name in ("x", "y")]
        await asyncio.wait_for(ready.wait(), 2)
        xy = await runtime.open_node(request("y", key="xy"), frames["x"])
        with self.assertRaisesRegex(Rejected, "Wait cycle"):
            await runtime.open_node(request("x", key="yx"), frames["y"])
        await runtime.close_node(xy["handle"], frames["x"])
        self.assertEqual(runtime.operations.waits, {})
        finish.set()
        for opened in roots:
            await runtime.next_node_event(opened["handle"], 0)


if __name__ == "__main__":
    unittest.main()
