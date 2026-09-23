"""Four frame-bound capabilities shared by code and agent execution."""
from runtime import Frame, NodeRequest, Rejected, Runtime, encode


class NodeAPI:
    def __init__(self, runtime: Runtime, frame: Frame):
        self.runtime, self.frame = runtime, frame
        self.candidate = None

    async def run_node(self, request: dict) -> dict:
        return await self.runtime.run_node(NodeRequest.parse(request), self.frame)

    async def read_node(self, node: str, enter: bool = False) -> dict:
        return self.runtime.read_node(self.frame, node, enter=enter)

    async def read_artifact(self, ref: str, offset: int = 0, limit: int = 4000) -> dict:
        return self.runtime.slice(self.frame, ref, offset, limit)

    async def submit_candidate(self, summary: str, content: dict, based_on: list[str]) -> dict:
        self.runtime._live(self.frame)
        candidate = {"summary": summary, "content": content, "based_on": based_on}
        if len(encode(candidate)) > 500_000:
            raise Rejected("Candidate too large; use external artifact references")
        self.candidate = candidate
        return {"staged": True}

    def result(self) -> dict:
        if self.candidate is None:
            raise Rejected("Node ended without staging a candidate")
        return self.candidate
