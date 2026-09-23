"""Deep Agents executes agent nodes; run_node is the application primitive.

Both PTC and native tool calls use NodeAPI. The optional framework task bridge is
retained only as a supervised compatibility route, never an unsupervised worker.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import tool
from langchain_quickjs import CodeInterpreterMiddleware

from harness.api import NodeAPI
from harness.contracts import Candidate, Rejected, RunContext, encode
from harness.runners.ptc import PTC_PRELUDE
from harness.runtime import Frame, Runtime

RUNTIME_PROMPT = Path(__file__).with_name("node_agent.md").read_text(encoding="utf-8")


def node_messages(frame: Frame, context: RunContext) -> list[dict[str, str]]:
    """Stable procedure/evidence prefix followed by this execution's changing task.

    This is prompt layout, not a KV store or a promise of provider cache hits.
    References stay explicit; no parent messages or private state are copied.
    """
    packets = (
        {"entry": context["entry"]},
        {"inputs": frame.request.inputs, "refs": frame.request.refs},
        {
            "task": frame.request.task,
            "context": {key: value for key, value in context.items() if key != "entry"},
        },
    )
    return [{"role": "user", "content": encode(packet)} for packet in packets]


class PTCWrapperMiddleware(AgentMiddleware):
    async def awrap_tool_call(self, request, handler):
        if request.tool_call["name"] == "eval":
            call = request.tool_call
            args = dict(call["args"])
            args["code"] = PTC_PRELUDE + "\n" + args["code"]
            request = request.override(tool_call={**call, "args": args})
        return await handler(request)


class DeepAgentRunner:
    def __init__(
        self,
        runtime: Runtime,
        model_factory: Callable[[Frame], Any],
        *,
        interpreter_timeout: float = 180.0,
        graph_steps: int = 80,
        instructions: str = RUNTIME_PROMPT,
    ):
        self.runtime, self.model_factory = runtime, model_factory
        self.instructions = instructions
        self.interpreter_timeout, self.graph_steps = interpreter_timeout, graph_steps

    def build(self, frame: Frame):
        api = NodeAPI(self.runtime, frame)

        @tool
        async def run_node(request: dict) -> dict:
            """Run, join or reuse node work through the supervised execution contract."""
            return await api.run_node(request)

        @tool
        async def open_node(request: dict) -> dict:
            """Attach to node work and return a handle for ordered checkpoints."""
            return await api.open_node(request)

        @tool
        async def next_node_event(handle: str, after: int) -> dict:
            """Read the next checkpoint or wait for completion; terminal closes the handle."""
            return await api.next_node_event(handle, after)

        @tool
        async def close_node(handle: str) -> dict:
            """Release a caller's interest in a node before it completes."""
            return await api.close_node(handle)

        @tool
        async def publish_checkpoint(summary: str, content: dict, based_on: list[str]) -> dict:
            """Publish a separately reviewed immutable checkpoint from this node."""
            return await api.publish_checkpoint(summary, content, based_on)

        @tool
        async def read_node(node: str, enter: bool = False) -> dict:
            """Inspect a node and links; enter=True activates inline obligations."""
            return await api.read_node(node, enter)

        @tool
        async def read_artifact(ref: str, offset: int = 0, limit: int = 4000) -> dict:
            """Read a bounded slice of an authorized immutable artifact."""
            return await api.read_artifact(ref, offset, limit)

        @tool
        async def submit_candidate(summary: str, content: dict, based_on: list[str]) -> dict:
            """Stage a candidate for host validation and required review."""
            return await api.submit_candidate(summary, content, based_on)

        async def dispatch(state: dict, config: dict):
            messages = state.get("messages", [])
            if len(messages) != 1 or not isinstance(messages[0].content, str):
                raise Rejected("Expected a fresh JSON node request")
            receipt = await api.run_node(json.loads(messages[0].content))
            return {"messages": [AIMessage(content=encode(receipt))]}

        supervised_worker = {
            "name": "general-purpose",
            "description": "Compatibility dispatch. description is a JSON run_node request.",
            "runnable": RunnableLambda(dispatch),
        }
        functions = [
            read_node,
            run_node,
            open_node,
            next_node_event,
            close_node,
            read_artifact,
            publish_checkpoint,
            submit_candidate,
        ]
        interpreter = CodeInterpreterMiddleware(
            ptc=functions,
            mode="thread",
            subagents=False,
            max_ptc_calls=64,
            max_result_chars=12000,
            memory_limit=64 * 1024 * 1024,
            max_snapshot_bytes=4 * 1024 * 1024,
            timeout=self.interpreter_timeout,
        )
        agent = create_deep_agent(
            model=self.model_factory(frame),
            system_prompt=self.instructions,
            tools=functions,
            backend=StateBackend(),
            subagents=[supervised_worker],
            middleware=[PTCWrapperMiddleware(), interpreter],
        )
        return agent, api

    async def __call__(self, frame: Frame, context: RunContext) -> Candidate:
        agent, api = self.build(frame)
        messages = node_messages(frame, context)
        result = await agent.ainvoke(
            {"messages": messages},
            config={
                "configurable": {
                    "thread_id": f"{self.runtime.session}:{frame.id}:{context['attempt']}"
                },
                "recursion_limit": self.graph_steps,
            },
        )
        if (task := asyncio.current_task()) is not None and task.cancelling():
            raise asyncio.CancelledError
        # Explicit model actions and tool observations, not hidden model reasoning.
        for message in result["messages"][len(messages) :]:
            if getattr(message, "tool_calls", None):
                self.runtime.store.event(
                    type="agent_actions",
                    session=self.runtime.session,
                    frame=frame.id,
                    attempt=context["attempt"],
                    calls=message.tool_calls,
                )
            elif message.type == "tool":
                self.runtime.store.event(
                    type="agent_observation",
                    session=self.runtime.session,
                    frame=frame.id,
                    attempt=context["attempt"],
                    content=str(message.content)[:16000],
                )
        return api.result()
