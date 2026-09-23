"""Run a pinned package resource with the same supervised host capabilities."""

import asyncio

from quickjs_rs import Runtime as JSRuntime

from harness.api import NodeAPI
from harness.contracts import Candidate, Rejected, RunContext, encode
from harness.runtime import Frame, Runtime


class CodeRunner:
    def __init__(self, runtime: Runtime, resource: str, *, timeout: float = 5):
        self.runtime, self.resource, self.timeout = runtime, resource, timeout

    async def __call__(self, frame: Frame, context: RunContext) -> Candidate:
        api = NodeAPI(self.runtime, frame)
        node = self.runtime.registry.nodes[frame.request.node]
        try:
            source = node.resource(self.resource).decode("utf-8")
        except UnicodeError as error:
            raise Rejected("JavaScript resource must be UTF-8") from error
        with JSRuntime(memory_limit=64 * 1024 * 1024) as js:
            with js.new_context(timeout=self.timeout) as ctx:

                async def run(args):
                    return await api.run_node(**args)

                async def open_node(args):
                    return await api.open_node(**args)

                async def next_node_event(args):
                    return await api.next_node_event(**args)

                async def close_node(args):
                    return await api.close_node(**args)

                async def inspect(args):
                    return await api.read_node(**args)

                async def read(args):
                    return await api.read_artifact(**args)

                async def submit(args):
                    return await api.submit_candidate(**args)

                async def checkpoint(args):
                    return await api.publish_checkpoint(**args)

                for name, fn in [
                    ("runNode", run),
                    ("openNode", open_node),
                    ("nextNodeEvent", next_node_event),
                    ("closeNode", close_node),
                    ("readNode", inspect),
                    ("readArtifact", read),
                    ("publishCheckpoint", checkpoint),
                    ("submitCandidate", submit),
                ]:
                    ctx.register(name, fn)
                prelude = (
                    "const tools = {runNode, openNode, nextNodeEvent, closeNode, "
                    "readNode, readArtifact, publishCheckpoint, submitCandidate};\n"
                )
                prelude += "const input = " + encode(frame.request.inputs) + ";\n"
                prelude += "const task = " + encode(frame.request.task) + ";\n"
                prelude += "const refs = " + encode(frame.request.refs) + ";\n"
                prelude += "const context = " + encode(context) + ";\n"
                self.runtime.store.event(
                    type="code_execution",
                    session=self.runtime.session,
                    frame=frame.id,
                    node=node.name,
                    revision=node.revision,
                    resource=self.resource,
                )
                await ctx.eval_async(prelude + source)
                # The JS bridge can surface a caught cancellation as a value.
                if (task := asyncio.current_task()) is not None and task.cancelling():
                    raise asyncio.CancelledError
        return api.result()
