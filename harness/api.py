"""Four frame-bound capabilities shared by generated code and native calls."""

from harness.contracts import Candidate, NodeRequest, Receipt, Rejected, candidate
from harness.runtime import Frame, Runtime


class NodeAPI:
    def __init__(self, runtime: Runtime, frame: Frame):
        self.runtime, self.frame = runtime, frame
        self.candidate: Candidate | None = None

    async def run_node(self, request: dict) -> Receipt:
        return await self.runtime.run_node(NodeRequest.parse(request), self.frame)

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
