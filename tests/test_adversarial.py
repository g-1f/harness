"""Regression cases from the architecture's adversarial review."""

import asyncio
import unittest

from harness import NodeRequest, Registry, Rejected, Runtime, Store
from harness.runners.code import CodeRunner
from tests.support import code_skill, draft, skill


class AdversarialTests(unittest.IsolatedAsyncioTestCase):
    def runtime(self, nodes=None, **kwargs):
        runtime = Runtime(Registry(nodes or [skill("a"), skill("b")]), Store(), **kwargs)
        self.addCleanup(runtime.store.close)
        self.addAsyncCleanup(runtime.aclose)
        return runtime

    async def test_unobserved_open_recursion_respects_depth(self):
        runtime = self.runtime(max_depth=2)
        depths = []
        rejected = asyncio.Event()

        async def run(frame, context):
            depth = frame.request.inputs["depth"]
            depths.append(depth)
            if depth < 6:
                try:
                    opened = await runtime.open_node(
                        NodeRequest("a", "recurse", {"depth": depth + 1}, str(depth)), frame
                    )
                except Rejected:
                    rejected.set()
                else:
                    await rejected.wait()
                    await runtime.close_node(opened["handle"], frame)
            else:
                rejected.set()
            return draft()

        runtime.register_executor("agent", run)
        await asyncio.wait_for(runtime.run_node(NodeRequest("a", "recurse", {"depth": 0}, "a")), 2)
        self.assertEqual(max(depths), 2)
        self.assertEqual(runtime.operations.waits, {})

    async def test_unobserved_ancestor_attachment_is_rejected(self):
        runtime = self.runtime()
        ready = asyncio.Event()
        frames = {}

        async def run(frame, context):
            frames[frame.request.node] = frame
            if len(frames) == 2:
                ready.set()
            await asyncio.Event().wait()

        runtime.register_executor("agent", run)
        a = NodeRequest("a", "work", {}, "a", reuse="session")
        root = await runtime.open_node(a)
        while "a" not in frames:
            await asyncio.sleep(0)
        await runtime.open_node(NodeRequest("b", "work", {}, "b"), frames["a"])
        await asyncio.wait_for(ready.wait(), 2)
        with self.assertRaisesRegex(Rejected, "cycle"):
            await runtime.open_node(a, frames["b"])
        await asyncio.wait_for(runtime.close_node(root["handle"]), 2)
        self.assertEqual(runtime.operations.waits, {})
        self.assertFalse(runtime._handles)

    async def test_cancelled_replay_is_rejected_without_cancelling_consumer(self):
        runtime = self.runtime()

        async def run(frame, context):
            await asyncio.Event().wait()

        runtime.register_executor("agent", run)
        request = NodeRequest("a", "work", {}, "a")
        handle = await runtime.open_node(request)
        await runtime.close_node(handle["handle"])
        with self.assertRaisesRegex(Rejected, "cancelled"):
            await runtime.run_node(request)
        self.assertEqual(asyncio.current_task().cancelling(), 0)

    async def test_rejections_and_cancelled_replays_are_catchable_in_quickjs(self):
        source = """
let messages = [];
try { await tools.readNode({node:'missing'}); }
catch (error) { messages.push(error.name + ':' + error.message); }
const request = {node:'b',task:'work',inputs:{},refs:[],key:'b'};
const op = await nodes.open(request);
await op.close();
try { await nodes.run(request); }
catch (error) { messages.push(error.name + ':' + error.message); }
if (!messages[0]?.includes('Rejected:Unknown skill')) throw new Error(JSON.stringify(messages));
if (!messages[1]?.includes('Rejected:Node operation cancelled')) throw new Error(JSON.stringify(messages));
await tools.submitCandidate({summary:'Handled',content:{messages},based_on:[]});
"""
        runtime = self.runtime([code_skill("a", source), skill("b")], bindings={"a": "code"})

        async def run(frame, context):
            await asyncio.Event().wait()

        runtime.register_executor("agent", run)
        runtime.register_executor("code", CodeRunner(runtime, "run.js"))
        receipt = await runtime.run_node(NodeRequest("a", "test", {}, "a"))
        self.assertEqual(len(runtime.store.get(receipt["ref"])["content"]["messages"]), 2)
        self.assertEqual(runtime.operations.waits, {})
        self.assertFalse(runtime._handles)
