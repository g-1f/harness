"""Run a pinned package resource with the same supervised host capabilities."""

import asyncio

from quickjs_rs import Runtime as JSRuntime

from harness.api import NodeAPI
from harness.contracts import Candidate, Rejected, RunContext, encode
from harness.runners.ptc import PTC_PRELUDE, bridge_method
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

                def bind(method):
                    async def invoke(args):
                        return await method(**args)

                    return invoke

                capabilities = api.capabilities()
                for name, method in capabilities.items():
                    ctx.register(name, bind(bridge_method(method)))
                prelude = "const tools = {" + ", ".join(capabilities) + "};\n"
                prelude += PTC_PRELUDE + "\n"
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
