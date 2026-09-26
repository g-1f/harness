"""Exercise the installed wrapper through real JS and host lifetimes."""

import asyncio
import unittest

from langchain_core.messages import AIMessage

from harness import NodeRequest, Registry, Runtime, Store
from harness.runners.agent import DeepAgentRunner
from harness.runners.code import CodeRunner
from tests.support import code_skill, draft, skill
from tests.test_integration import ScriptedModel, eval_response

REQUEST = "{node:'b',task:'producer',inputs:{},refs:[],key:'b',reuse:'session'}"


class PTCWrapperTests(unittest.IsolatedAsyncioTestCase):
    def runtime(self, source, producer):
        runtime = Runtime(
            Registry([code_skill("root", source), skill("b")]), Store(), bindings={"root": "code"}
        )
        self.addCleanup(runtime.store.close)
        self.addAsyncCleanup(runtime.aclose)
        runtime.register_executor("code", CodeRunner(runtime, "run.js"))
        runtime.register_executor("agent", producer)
        return runtime

    async def run_root(self, runtime):
        receipt = await runtime.run_node(NodeRequest("root", "test", {}, "root"))
        self.assertEqual(receipt["status"], "published")
        self.assertEqual(runtime._handles, {})
        self.assertEqual(runtime.operations.waits, {})
        self.assertTrue(all(not op.waiters for op in runtime.operations.operations.values()))
        return runtime.store.get(receipt["ref"])

    async def test_iteration_and_repeated_result_do_not_reopen_or_mutate_cached_receipt(self):
        async def producer(frame, context):
            for value in (1, 2):
                await runtime.publish_checkpoint(frame, draft(value))
            return draft(3)

        source = """
const refsSeen = await nodes.with(REQUEST, async operation => {
  const refs = [];
  for await (const checkpoint of operation.checkpoints()) refs.push(checkpoint.ref);
  if (refs.length !== 2) throw new Error('Missing checkpoints');
  const first = await operation.result();
  first.status = 'corrupted';
  const second = await operation.result();
  if (second.status !== 'published') throw new Error('Mutable cached receipt');
  if (await operation.next() !== null) throw new Error('Expected end of checkpoints');
  return [...refs, second.ref];
});
await tools.submitCandidate({summary:'Done',content:{ok:true},based_on:refsSeen});
""".replace("REQUEST", REQUEST)
        runtime = self.runtime(source, producer)
        result = await self.run_root(runtime)
        self.assertEqual(len(result["based_on"]), 3)
        self.assertEqual(runtime.ledger.frames, 2)

    async def test_no_checkpoint_returns_null_and_final_is_still_available(self):
        async def producer(frame, context):
            return draft()

        source = """
const final = await nodes.with(REQUEST, async operation => {
  if (await operation.next() !== null) throw new Error('Unexpected checkpoint');
  return operation.result();
});
await tools.submitCandidate({summary:'Done',content:{ok:true},based_on:[final.ref]});
""".replace("REQUEST", REQUEST)
        await self.run_root(self.runtime(source, producer))

    async def test_scope_releases_on_early_break_and_callback_exception(self):
        for action in ("break;", "throw new Error('consumer failed');"):
            with self.subTest(action=action):
                owner = {}

                async def producer(frame, context, owner=owner):
                    await owner["runtime"].publish_checkpoint(frame, draft())
                    await asyncio.Event().wait()

                source = (
                    """
let failed = false;
try {
  await nodes.with(REQUEST, async operation => {
    for await (const checkpoint of operation.checkpoints()) { ACTION }
  });
} catch (error) {
  if (!String(error).includes('consumer failed')) throw error;
  failed = true;
}
if (failed !== EXPECTED) throw new Error('Exception swallowed');
await tools.submitCandidate({summary:'Done',content:{ok:true},based_on:[]});
""".replace("REQUEST", REQUEST)
                    .replace("ACTION", action)
                    .replace("EXPECTED", "true" if "throw" in action else "false")
                )
                runtime = self.runtime(source, producer)
                owner["runtime"] = runtime
                await self.run_root(runtime)
                operation = next(
                    op for op in runtime.operations.operations.values() if op.task.cancelled()
                )
                self.assertEqual(operation.state, "cancelled")

    async def test_overlapping_reads_reject_without_losing_the_first_read(self):
        async def producer(frame, context):
            await runtime.publish_checkpoint(frame, draft())
            return draft()

        source = """
await nodes.with(REQUEST, async operation => {
  const first = operation.next();
  let rejected = false;
  try { await operation.result(); }
  catch (error) { rejected = String(error).includes('already pending'); }
  if (!rejected) throw new Error('Overlapping read accepted');
  if (!(await first).ref) throw new Error('First read lost');
  await operation.result();
});
await tools.submitCandidate({summary:'Done',content:{ok:true},based_on:[]});
""".replace("REQUEST", REQUEST)
        runtime = self.runtime(source, producer)
        await self.run_root(runtime)

    async def test_agent_wrapper_is_injected_and_survives_multiple_eval_cells(self):
        runtime = Runtime(Registry([skill("root"), skill("b")]), Store(), bindings={"b": "native"})
        self.addCleanup(runtime.store.close)
        self.addAsyncCleanup(runtime.aclose)

        async def producer(frame, context):
            await runtime.publish_checkpoint(frame, draft())
            return draft()

        runtime.register_executor("native", producer)

        def factory(frame):
            return ScriptedModel(
                responses=[
                    eval_response(
                        """
try { await tools.readNode({node:'missing'}); throw new Error('Expected rejection'); }
catch (error) {
  if (error.name !== 'Rejected' || !error.message.includes('Unknown skill')) throw error;
}
var operation = await nodes.open("""
                        + REQUEST
                        + ");"
                    ),
                    eval_response("var progress = await operation.next();"),
                    eval_response("""
const final = await operation.result();
await operation.close();
await tools.submitCandidate({summary:'Done',content:{ok:true},based_on:[progress.ref,final.ref]});
"""),
                    AIMessage(content="Staged"),
                ]
            )

        runtime.register_executor("agent", DeepAgentRunner(runtime, factory))
        await self.run_root(runtime)

    async def test_scope_exit_keeps_a_shared_producer_needed_by_another_caller(self):
        finish = asyncio.Event()

        async def producer(frame, context):
            await runtime.publish_checkpoint(frame, draft())
            await finish.wait()
            return draft()

        source = """
await nodes.with(REQUEST, async operation => { await operation.next(); });
await tools.submitCandidate({summary:'Done',content:{ok:true},based_on:[]});
""".replace("REQUEST", REQUEST)
        runtime = self.runtime(source, producer)
        keeper = await runtime.open_node(NodeRequest("b", "producer", {}, "keep", (), "session"))
        await runtime.run_node(NodeRequest("root", "test", {}, "root"))
        operation = runtime._handles[keeper["handle"]][1].operation
        self.assertEqual(operation.state, "running")
        self.assertEqual(len(operation.waiters), 1)
        finish.set()
        checkpoint = await runtime.next_node_event(keeper["handle"], 0)
        await runtime.next_node_event(keeper["handle"], checkpoint["cursor"])
        self.assertEqual(runtime._handles, {})

    async def test_producer_failure_survives_scope_cleanup(self):
        async def producer(frame, context):
            raise ValueError("producer failed")

        source = "await nodes.with(REQUEST, operation => operation.result());".replace(
            "REQUEST", REQUEST
        )
        runtime = self.runtime(source, producer)
        with self.assertRaisesRegex(ValueError, "producer failed"):
            await runtime.run_node(NodeRequest("root", "test", {}, "root"))
        self.assertEqual(runtime._handles, {})
        self.assertTrue(all(not op.waiters for op in runtime.operations.operations.values()))

    async def test_result_keeps_domain_decisions_in_artifact_content(self):
        source = """
const result = await nodes.with(REQUEST, operation => operation.result());
if (result.status !== 'published') throw new Error('Unexpected receipt status');
const record = JSON.parse((await tools.readArtifact({ref: result.ref})).text);
if (record.content.decision !== 'blocked') throw new Error('Decision changed');
await tools.submitCandidate({summary:'Blocked child handled',content:{ok:true},based_on:[result.ref]});
""".replace("REQUEST", REQUEST)

        async def producer(frame, context):
            return {"summary": "Assessment", "content": {"decision": "blocked", "verdict": "fail"}}

        runtime = self.runtime(source, producer)
        await self.run_root(runtime)
