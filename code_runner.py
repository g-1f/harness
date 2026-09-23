"""Run a pinned node-js body with no model and the same four host capabilities."""
import asyncio

from quickjs_rs import Runtime as JSRuntime

from node_api import NodeAPI
from runtime import Frame, Runtime, encode


class CodeRunner:
    def __init__(self, runtime: Runtime, timeout: float = 5):
        self.runtime, self.timeout = runtime, timeout

    async def __call__(self, frame: Frame, context: dict) -> dict:
        api = NodeAPI(self.runtime, frame)
        node = self.runtime.registry.nodes[frame.request.node]
        with JSRuntime(memory_limit=64 * 1024 * 1024) as js:
            with js.new_context(timeout=self.timeout) as ctx:
                async def run(args):
                    return await api.run_node(**args)

                async def inspect(args):
                    return await api.read_node(**args)

                async def read(args):
                    return await api.read_artifact(**args)

                async def submit(args):
                    return await api.submit_candidate(**args)

                for name, fn in [("runNode", run), ("readNode", inspect),
                                 ("readArtifact", read), ("submitCandidate", submit)]:
                    ctx.register(name, fn)
                prelude = "const tools = {runNode, readNode, readArtifact, submitCandidate};\n"
                prelude += "const input = " + encode(frame.request.inputs) + ";\n"
                prelude += "const refs = " + encode(frame.request.refs) + ";\n"
                prelude += "const context = " + encode(context) + ";\n"
                self.runtime.store.event(type="code_execution", session=self.runtime.session,
                                         frame=frame.id, node=node.name, revision=node.revision)
                await ctx.eval_async(prelude + node.code)
                # The JS bridge can surface a caught cancellation as a value.
                if asyncio.current_task().cancelling():
                    raise asyncio.CancelledError
        return api.result()
