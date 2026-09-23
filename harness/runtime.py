"""One-process supervisor for fresh calls, explicit artifact grants and reviews."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Any, Protocol

from harness.contracts import (
    Candidate,
    NodeRequest,
    Receipt,
    Rejected,
    RunContext,
    candidate,
    digest,
    encode,
)
from harness.policy import ReviewPolicy, validate_policies
from harness.skills import Registry
from harness.storage import Store


@dataclass(slots=True)
class Frame:
    """Invocation state owned by the supervisor, never authored skill attributes."""

    id: str
    parent: Frame | None
    request: NodeRequest
    lineage: tuple[str, ...]
    executor: str = "agent"
    active: set[str] = field(default_factory=set)
    grants: set[str] = field(default_factory=set)
    children: set[asyncio.Task] = field(default_factory=set)
    closed: bool = False
    observed: set[str] = field(default_factory=set)


class Runner(Protocol):
    async def __call__(self, frame: Frame, context: RunContext) -> Candidate: ...


class Ledger:
    """Call-count admission; inference permits are released before child joins."""

    def __init__(
        self, max_frames: int = 64, max_model_calls: int = 256, model_parallelism: int = 8
    ):
        if any(
            type(n) is not int or n < 1 for n in (max_frames, max_model_calls, model_parallelism)
        ):
            raise Rejected("Ledger limits must be positive integers")
        self.max_frames = max_frames
        self.max_model_calls = max_model_calls
        self.frames = 0
        self.model_calls = 0
        self.slots = asyncio.Semaphore(model_parallelism)

    def admit_frame(self) -> None:
        if self.frames >= self.max_frames:
            raise Rejected("Session frame budget exhausted")
        self.frames += 1

    async def model_call(self, invoke: Callable[[], Awaitable[Any]]) -> Any:
        async with self.slots:
            if self.model_calls >= self.max_model_calls:
                raise Rejected("Session model-call budget exhausted")
            self.model_calls += 1
            return await invoke()


class Runtime:
    def __init__(
        self,
        registry: Registry,
        store: Store,
        *,
        ledger: Ledger | None = None,
        bindings: Mapping[str, str] | None = None,
        reviews: Mapping[str, ReviewPolicy] | None = None,
        default_executor: str = "agent",
        max_depth: int = 5,
        deadline_seconds: float = 180,
        max_revisions: int = 2,
    ):
        if (
            type(max_depth) is not int
            or max_depth < 0
            or type(max_revisions) is not int
            or max_revisions < 0
            or deadline_seconds <= 0
        ):
            raise Rejected("Invalid supervisor limits")
        self.registry, self.store = registry, store
        self.bindings = MappingProxyType(dict(bindings or {}))
        self.reviews = MappingProxyType(dict(reviews or {}))
        validate_policies(registry, self.reviews)
        if set(self.bindings) - registry.nodes.keys():
            raise Rejected("Executor binding names an unknown skill")
        if any(
            not isinstance(x, str) or not x for x in (default_executor, *self.bindings.values())
        ):
            raise Rejected("Executor names must be nonempty strings")
        self.default_executor = default_executor
        self._executors: dict[str, Runner] = {}
        self._sealed = False
        self.ledger = ledger or Ledger()
        self.session = uuid.uuid4().hex
        self.max_depth, self.max_revisions = max_depth, max_revisions
        self.deadline = time.monotonic() + deadline_seconds
        self.jobs: dict[tuple[str, str], tuple[str, asyncio.Task[Receipt]]] = {}

    def register_executor(self, name: str, runner: Runner) -> None:
        """Configure trusted adapters before the first invocation seals the session."""
        if self._sealed:
            raise Rejected("Execution configuration is sealed after the first call")
        if not isinstance(name, str) or not name or name in self._executors or not callable(runner):
            raise Rejected("Executor needs a unique name and callable runner")
        self._executors[name] = runner

    def _seal(self) -> None:
        needed = {self.bindings.get(name, self.default_executor) for name in self.registry.nodes}
        if needed - self._executors.keys():
            raise Rejected(f"Unregistered executors: {sorted(needed - self._executors.keys())}")
        self._sealed = True

    def check_live(self, frame: Frame) -> None:
        if frame.closed or time.monotonic() >= self.deadline:
            raise Rejected("Frame closed or session deadline exceeded")

    def _authorized_record(self, frame: Frame, ref: str) -> dict[str, Any]:
        self.check_live(frame)
        value = self.store.get(ref)
        if value["session"] != self.session:
            raise Rejected("Cross-session access denied")
        if value["frame"] != frame.id and ref not in frame.grants:
            raise Rejected("Artifact is not visible to this frame; pass an explicit ref")
        return value

    def read(self, frame: Frame, ref: str) -> dict[str, Any]:
        value = self._authorized_record(frame, ref)
        frame.observed.add(ref)
        self.store.event(type="artifact_read", session=self.session, frame=frame.id, ref=ref)
        return value

    def slice(self, frame: Frame, ref: str, offset: int = 0, limit: int = 4000) -> dict:
        if (
            type(offset) is not int
            or type(limit) is not int
            or offset < 0
            or not 1 <= limit <= 16_000
        ):
            raise Rejected("Invalid slice")
        text = encode(self.read(frame, ref))
        return {
            "ref": ref,
            "text": text[offset : offset + limit],
            "next_offset": min(len(text), offset + limit),
            "total_chars": len(text),
        }

    def read_node(
        self, frame: Frame, node: str, *, enter: bool = False, limit: int = 32_000
    ) -> dict:
        self.check_live(frame)
        if type(limit) is not int or not 512 <= limit <= 32_000 or node not in self.registry.nodes:
            raise Rejected("Unknown skill or invalid entry budget")
        if type(enter) is not bool:
            raise Rejected("enter must be a boolean")
        skill = self.registry.nodes[node]
        packet = {
            "node": skill.name,
            "description": skill.description,
            "revision": skill.revision,
            "text": skill.instructions,
            "links": list(skill.links),
            "resources": [r.path for r in skill.resources],
        }
        if len(encode(packet).encode()) > limit:
            raise Rejected(
                "Entry exceeds budget; split the skill or request a larger bounded packet"
            )
        if enter:
            frame.active.add(node)
        self.store.event(
            type="node_enter" if enter else "node_read",
            session=self.session,
            frame=frame.id,
            node=node,
            revision=skill.revision,
        )
        return packet

    async def run_node(self, request: NodeRequest, parent: Frame | None = None) -> Receipt:
        request = NodeRequest.parse(asdict(request))
        self._seal()
        if parent:
            self.check_live(parent)
        if request.node not in self.registry.nodes:
            raise Rejected("Unknown skill")
        signature = digest(
            {
                "node": request.node,
                "inputs": request.inputs,
                "task": request.task,
                "refs": request.refs,
            }
        )
        lineage = parent.lineage if parent else ()
        if signature in lineage:
            raise Rejected("Repeated active subproblem; refine the task or inputs")
        if len(lineage) > self.max_depth:
            raise Rejected("Maximum child depth exceeded")
        job_key = (parent.id if parent else "root", request.key)
        if job_key in self.jobs:
            old_signature, job = self.jobs[job_key]
            if old_signature != signature:
                raise Rejected("Idempotency key reused for a different request")
            result = await asyncio.shield(job)
            if parent:
                parent.grants.add(result["ref"])
            return result
        for ref in request.refs:
            if parent is None:
                raise Rejected("Root artifact grants need an authenticated launcher")
            self._authorized_record(parent, ref)
        self.ledger.admit_frame()
        frame = Frame(
            uuid.uuid4().hex,
            parent,
            request,
            (*lineage, signature),
            executor=self.bindings.get(request.node, self.default_executor),
            grants=set(request.refs),
        )
        self.store.event(
            type="admitted",
            session=self.session,
            frame=frame.id,
            parent=parent.id if parent else None,
            node=request.node,
            executor=frame.executor,
            task=request.task,
            key=request.key,
            refs=list(request.refs),
        )
        job = asyncio.create_task(self._run(frame))
        self.jobs[job_key] = (signature, job)
        if parent:
            parent.children.add(job)
        try:
            result = await asyncio.shield(job)
            if parent:
                parent.grants.add(result["ref"])
            return result
        except asyncio.CancelledError:
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
            raise

    def _record(
        self, frame: Frame, draft: Candidate, status: str, reviews: tuple | list = ()
    ) -> str:
        for ref in draft["based_on"]:
            value = self._authorized_record(frame, ref)
            if status == "accepted" and value["status"] != "accepted":
                raise Rejected("Accepted results cannot depend on unaccepted artifacts")
        return self.store.put(
            {
                "session": self.session,
                "frame": frame.id,
                "parent": frame.parent.id if frame.parent else None,
                "node": frame.request.node,
                "task": frame.request.task,
                "executor": frame.executor,
                "snapshot": self.registry.snapshot,
                "consulted": sorted(frame.active),
                "inputs": frame.request.inputs,
                "node_revision": self.registry.nodes[frame.request.node].revision,
                "input_refs": list(frame.request.refs),
                "observed_refs": sorted(frame.observed),
                "status": status,
                "created_at": time.time(),
                **draft,
                "reviews": list(reviews),
            }
        )

    async def _review(
        self, frame: Frame, draft: Candidate, draft_ref: str, attempt: int
    ) -> tuple[list[str], list[dict[str, Any]], int]:
        policies = [self.reviews[name] for name in sorted(frame.active) if name in self.reviews]
        reviewers = tuple(dict.fromkeys(name for p in policies for name in p.reviewers))
        round_limit = min([self.max_revisions, *(p.max_revisions for p in policies)])

        async def review_one(name: str) -> Receipt:
            return await self.run_node(
                NodeRequest(
                    name,
                    f"Review candidate {draft_ref}; independently test claims. "
                    "Return content with candidate_ref, verdict pass/fail/inconclusive, and findings array.",
                    frame.request.inputs,
                    f"review:{attempt}:{name}",
                    tuple(dict.fromkeys([draft_ref, *draft["based_on"]])),
                ),
                frame,
            )

        results = await asyncio.gather(
            *(review_one(name) for name in reviewers), return_exceptions=True
        )
        refs, feedback = [], []
        for name, result in zip(reviewers, results, strict=True):
            if isinstance(result, BaseException):
                feedback.append({"reviewer": name, "error": type(result).__name__})
                continue
            refs.append(result["ref"])
            verdict = self._authorized_record(frame, result["ref"])["content"]
            valid = (
                verdict.get("candidate_ref") == draft_ref
                and verdict.get("verdict") == "pass"
                and verdict.get("findings") == []
            )
            if result["status"] != "accepted" or not valid:
                feedback.append({"reviewer": name, "ref": result["ref"], "verdict": verdict})
        return refs, feedback, round_limit

    async def _run(self, frame: Frame) -> Receipt:
        self.store.event(type="started", session=self.session, frame=frame.id)
        try:
            async with asyncio.timeout(max(0, self.deadline - time.monotonic())):
                packet = self.read_node(frame, frame.request.node, enter=True)
                feedback, previous = [], None
                for attempt in range(self.max_revisions + 1):
                    context: RunContext = {
                        "entry": packet,
                        "attempt": attempt,
                        "feedback": feedback,
                        "previous": previous,
                    }
                    draft = candidate(await self._executors[frame.executor](frame, context))
                    if any(not task.done() for task in frame.children):
                        raise Rejected("Join children before returning a draft")
                    draft_ref = self._record(frame, draft, "draft")
                    reviews, feedback, round_limit = await self._review(
                        frame, draft, draft_ref, attempt
                    )
                    if not feedback or attempt >= round_limit:
                        status = "needs_review" if feedback else "accepted"
                        ref = self._record(frame, draft, status, reviews)
                        self.store.event(type=status, session=self.session, frame=frame.id, ref=ref)
                        return {"ref": ref, "status": status, "summary": draft["summary"]}
                    previous = draft_ref
                raise AssertionError("Unreachable revision bound")
        except asyncio.CancelledError:
            self.store.event(type="cancelled", session=self.session, frame=frame.id)
            raise
        except Exception as error:
            self.store.event(
                type="failed", session=self.session, frame=frame.id, error=type(error).__name__
            )
            raise
        finally:
            frame.closed = True
            for child in frame.children:
                if not child.done():
                    child.cancel()
            if frame.children:
                await asyncio.gather(*frame.children, return_exceptions=True)
            self.store.event(type="closed", session=self.session, frame=frame.id)
