"""An application-owned transformation: draft, check, optionally revise.

The supervisor sees only ordinary node calls and published artifacts. This example
chooses a review schema and what approval means; neither is a runtime protocol.
"""

from dataclasses import dataclass

from harness import NodeRequest, Rejected, Runtime
from harness.contracts import Candidate, RunContext, encode
from harness.runtime import Frame


@dataclass(frozen=True, slots=True)
class ReviewedTransformation:
    runtime: Runtime
    producer: str
    reviewer: str
    max_revisions: int = 0

    def __post_init__(self):
        if type(self.max_revisions) is not int or self.max_revisions < 0:
            raise ValueError("max_revisions must be a nonnegative integer")
        if {self.producer, self.reviewer} - self.runtime.registry.nodes.keys():
            raise ValueError("Composition names an unknown skill")

    async def __call__(self, frame: Frame, context: RunContext) -> Candidate:
        if frame.request.node in (self.producer, self.reviewer):
            raise Rejected("Bind this composition to its own skill")
        task = frame.request.task
        refs = frame.request.refs
        history = []
        for revision in range(self.max_revisions + 1):
            output = await self.runtime.run_node(
                NodeRequest(
                    self.producer,
                    task,
                    frame.request.inputs,
                    f"draft:{revision}",
                    refs,
                    reuse="fresh",
                ),
                frame,
            )
            candidate_ref = output["ref"]
            candidate = self.runtime.read(frame, candidate_ref)["content"]
            # A nested ref is not a grant. Give the checker this output and the
            # original caller's evidence, never all descendants mentioned inside it.
            review = await self.runtime.run_node(
                NodeRequest(
                    self.reviewer,
                    "Review the first referenced artifact against the requested task:\n"
                    + frame.request.task,
                    {},
                    f"review:{revision}",
                    (candidate_ref, *frame.request.refs),
                    reuse="fresh",
                ),
                frame,
            )
            finding = self.runtime.read(frame, review["ref"])["content"]
            history.append({"candidate_ref": candidate_ref, "review_ref": review["ref"]})
            approved = (
                finding.get("candidate_ref") == candidate_ref
                and finding.get("verdict") == "pass"
                and finding.get("findings") == []
            )
            if approved or revision == self.max_revisions:
                return {
                    "summary": "Reviewed transformation " + ("approved" if approved else "blocked"),
                    "content": {
                        "decision": "approved" if approved else "blocked",
                        "candidate_ref": candidate_ref,
                        "reviews": [review["ref"]],
                        "attempts": len(history),
                        "history": history,
                        "result": candidate if approved else None,
                    },
                    "based_on": [ref for step in history for ref in step.values()],
                }
            # Repair is a new ordinary call. Its question and explicit grants
            # change; no hidden repair context or special runtime retry exists.
            task = (
                frame.request.task
                + "\nRevise artifact "
                + candidate_ref
                + " using this review feedback: "
                + encode(finding)
            )
            refs = (*frame.request.refs, candidate_ref, review["ref"])
        raise AssertionError("Bounded composition must return or raise")
