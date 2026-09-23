"""Frame-bound capabilities shared by generated code and native calls."""

from harness.contracts import Candidate, NodeRequest, Receipt, Rejected, candidate
from harness.runtime import Frame, Runtime


class NodeAPI:
    def __init__(self, runtime: Runtime, frame: Frame):
        self.runtime, self.frame = runtime, frame
        self.candidate: Candidate | None = None

    async def run_node(self, request: dict) -> Receipt:
        return await self.runtime.run_node(NodeRequest.parse(request), self.frame)

    async def open_node(self, request: dict) -> dict:
        return await self.runtime.open_node(NodeRequest.parse(request), self.frame)

    async def next_node_event(self, handle: str, after: int) -> dict:
        return await self.runtime.next_node_event(handle, after, self.frame)

    async def close_node(self, handle: str) -> dict:
        return await self.runtime.close_node(handle, self.frame)

    async def publish_checkpoint(self, summary: str, content: dict, based_on: list[str]) -> Receipt:
        return await self.runtime.publish_checkpoint(
            self.frame, {"summary": summary, "content": content, "based_on": based_on}
        )

    async def read_node(self, node: str, enter: bool = False) -> dict:
        return self.runtime.read_node(self.frame, node, enter=enter)

    async def read_artifact(self, ref: str, offset: int = 0, limit: int = 4000) -> dict:
        return self.runtime.slice(self.frame, ref, offset, limit)

    async def submit_candidate(self, summary: str, content: dict, based_on: list[str]) -> dict:
        self.runtime.check_live(self.frame)
        self.candidate = candidate({"summary": summary, "content": content, "based_on": based_on})
        return {"staged": True}

    def result(self) -> Candidate:
        if self.candidate is None:
            raise Rejected("Node ended without staging a candidate")
        return self.candidate
