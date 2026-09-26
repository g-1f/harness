"""One-process supervisor for node work, explicit artifact grants and publication."""

from __future__ import annotations

import asyncio
import math
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
from harness.operations import Lease, OperationPool
from harness.skills import Registry
from harness.storage import Store


@dataclass(slots=True)
class Frame:
    """One execution context; origin records creation, not cancellation ownership."""

    id: str
    origin: str | None
    request: NodeRequest
    executor: str = "agent"
    consulted: set[str] = field(default_factory=set)
    grants: set[str] = field(default_factory=set)
    children: set[asyncio.Task] = field(default_factory=set)
    handles: set[str] = field(default_factory=set)
    closed: bool = False
    observed: set[str] = field(default_factory=set)


class Runner(Protocol):
    async def __call__(self, frame: Frame, context: RunContext) -> Candidate: ...


class Ledger:
    """Call-count admission; inference permits are released before child joins."""

    def __init__(
        self,
        max_frames: int = 64,
        max_model_calls: int = 256,
        model_parallelism: int = 8,
        max_calls: int = 512,
        max_checkpoints: int = 128,
    ):
        if any(
            type(n) is not int or n < 1
            for n in (max_frames, max_model_calls, model_parallelism, max_calls, max_checkpoints)
        ):
            raise Rejected("Ledger limits must be positive integers")
        self.max_frames = max_frames
        self.max_model_calls = max_model_calls
        self.max_calls = max_calls
        self.max_checkpoints = max_checkpoints
        self.calls = 0
        self.checkpoints = 0
        self.frames = 0
        self.model_calls = 0
        self.slots = asyncio.Semaphore(model_parallelism)

    def admit_call(self) -> None:
        if self.calls >= self.max_calls:
            raise Rejected("Session call budget exhausted")
        self.calls += 1

    def admit_frame(self) -> None:
        if self.frames >= self.max_frames:
            raise Rejected("Session frame budget exhausted")
        self.frames += 1

    def admit_checkpoint(self) -> int:
        if self.checkpoints >= self.max_checkpoints:
            raise Rejected("Session checkpoint budget exhausted")
        self.checkpoints += 1
        return self.checkpoints

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
        default_executor: str = "agent",
        max_depth: int = 5,
        deadline_seconds: float = 180,
    ):
        if (
            type(max_depth) is not int
            or max_depth < 0
            or type(deadline_seconds) not in (int, float)
            or not math.isfinite(deadline_seconds)
            or deadline_seconds <= 0
        ):
            raise Rejected("Invalid supervisor limits")
        self.registry, self.store = registry, store
        self.bindings = MappingProxyType(dict(bindings or {}))
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
        self.max_depth = max_depth
        self.deadline = time.monotonic() + deadline_seconds
        self.operations = OperationPool(max_depth=max_depth, emit=self._operation_event)
        self._call_tasks: set[asyncio.Task[Receipt]] = set()
        self._handles: dict[str, tuple[Frame | None, Lease]] = {}
        self._closed_handles: dict[str, Frame | None] = {}
        self._closed = False
        self._execution_identity = digest(
            {
                "snapshot": registry.snapshot,
                "bindings": dict(self.bindings),
                "default_executor": default_executor,
            }
        )

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

    def _operation_event(self, **event: Any) -> None:
        self.store.event(session=self.session, **event)

    def check_live(self, frame: Frame) -> None:
        if self._closed or frame.closed or time.monotonic() >= self.deadline:
            raise Rejected("Frame closed or session deadline exceeded")
        operation = self.operations.operations.get(frame.id)
        if operation is not None and operation.stopping:
            raise Rejected("Frame is stopping; new work and artifact access are closed")

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

    def read_node(self, frame: Frame, node: str, *, limit: int = 32_000) -> dict:
        self.check_live(frame)
        if type(limit) is not int or not 512 <= limit <= 32_000 or node not in self.registry.nodes:
            raise Rejected("Unknown skill or invalid entry budget")
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
        frame.consulted.add(node)
        self.store.event(
            type="node_read",
            session=self.session,
            frame=frame.id,
            node=node,
            revision=skill.revision,
        )
        return packet

    async def run_node(self, request: NodeRequest, caller: Frame | None = None) -> Receipt:
        request, identity = self._prepare_request(request, caller)
        # The caller owns this wait, not the producer it may share with others.
        waiting = asyncio.create_task(self._call(request, caller, identity))
        self._call_tasks.add(waiting)
        waiting.add_done_callback(self._call_tasks.discard)
        if caller:
            caller.children.add(waiting)
            waiting.add_done_callback(caller.children.discard)
        return await waiting

    def _prepare_request(
        self, request: NodeRequest, caller: Frame | None
    ) -> tuple[NodeRequest, str]:
        request = NodeRequest.parse(asdict(request))
        if request.node not in self.registry.nodes:
            raise Rejected("Unknown skill")
        self._seal()
        self._validate_call(request, caller)
        self.ledger.admit_call()
        return request, digest(
            {
                "execution": self._execution_identity,
                "node": request.node,
                "task": request.task,
                "inputs": request.inputs,
                "refs": request.refs,
            }
        )

    async def open_node(self, request: NodeRequest, caller: Frame | None = None) -> dict:
        """Attach a caller-scoped lease without waiting for the producer's result."""
        request, identity = self._prepare_request(request, caller)
        lease = await self.operations.acquire(
            caller=caller.id if caller else None,
            key=request.key,
            identity=identity,
            reuse=request.reuse,
            start=lambda operation_id: self._start(operation_id, request, caller),
            validate=lambda: self._validate_call(request, caller),
        )
        self._handles[lease.id] = (caller, lease)
        if caller:
            caller.handles.add(lease.id)
        return {"handle": lease.id}

    def _owned_handle(
        self, handle: str, caller: Frame | None, *, require_live: bool = True
    ) -> Lease:
        if type(handle) is not str or handle not in self._handles:
            raise Rejected("Unknown or closed node handle")
        owner, lease = self._handles[handle]
        if owner is not caller:
            raise Rejected("Node handle belongs to another caller")
        if not require_live:
            return lease
        if caller:
            self.check_live(caller)
        elif self._closed or time.monotonic() >= self.deadline:
            raise Rejected("Session closed or deadline exceeded")
        return lease

    def _release_handle(self, handle: str) -> asyncio.Task[Receipt] | None:
        owner, lease = self._handles.pop(handle)
        self._closed_handles[handle] = owner
        if owner:
            owner.handles.discard(handle)
        return self.operations.release(lease)

    async def close_node(self, handle: str, caller: Frame | None = None) -> dict:
        """Release this caller's lease early; the producer survives other leases."""
        if type(handle) is not str:
            raise Rejected("Unknown or closed node handle")
        if handle in self._closed_handles and self._closed_handles[handle] is caller:
            return {"closed": True}
        self._owned_handle(handle, caller, require_live=False)
        draining = self._release_handle(handle)
        if draining is not None:
            await asyncio.gather(asyncio.shield(draining), return_exceptions=True)
        return {"closed": True}

    async def next_node_event(self, handle: str, after: int, caller: Frame | None = None) -> dict:
        """Replay progress or await one event. Terminal delivery releases the handle."""
        lease = self._owned_handle(handle, caller)
        if lease.observing:
            raise Rejected("A read is already pending on this node handle")
        lease.observing = True
        try:
            event = await self.operations.next_event(lease, after)
            if event["kind"] == "checkpoint":
                self._owned_handle(handle, caller)
                if caller:
                    caller.grants.add(event["receipt"]["ref"])
                return event
            try:
                self._owned_handle(handle, caller)
                receipt = await lease.operation.settled()
                if caller:
                    caller.grants.add(receipt["ref"])
                return {"kind": "complete", "cursor": event["cursor"], "receipt": dict(receipt)}
            finally:
                await self.close_node(handle, caller)
        finally:
            lease.observing = False

    async def publish_checkpoint(self, frame: Frame, value: Candidate) -> Receipt:
        """Publish an immutable intermediate artifact; content is application-defined."""
        self.check_live(frame)
        output = candidate(value)
        sequence = self.ledger.admit_checkpoint()
        ref = self._record(frame, output, kind="checkpoint", checkpoint_sequence=sequence)
        receipt: Receipt = {"ref": ref, "status": "published", "summary": output["summary"]}
        self.operations.publish(frame.id, receipt)
        return receipt

    def _validate_call(self, request: NodeRequest, caller: Frame | None) -> None:
        if self._closed or time.monotonic() >= self.deadline:
            raise Rejected("Session closed or deadline exceeded")
        if caller:
            self.check_live(caller)
        for ref in request.refs:
            if caller is None:
                raise Rejected("Root artifact grants need an authenticated launcher")
            self._authorized_record(caller, ref)

    def _start(self, operation_id: str, request: NodeRequest, caller: Frame | None):
        self.ledger.admit_frame()
        frame = Frame(
            operation_id,
            caller.id if caller else None,
            request,
            executor=self.bindings.get(request.node, self.default_executor),
            grants=set(request.refs),
        )
        self.store.event(
            type="admitted",
            session=self.session,
            frame=frame.id,
            origin=caller.id if caller else None,
            node=request.node,
            executor=frame.executor,
            task=request.task,
            key=request.key,
            refs=list(request.refs),
            reuse=request.reuse,
        )
        return self._run(frame)

    async def _call(self, request: NodeRequest, caller: Frame | None, identity: str) -> Receipt:
        lease = await self.operations.acquire(
            caller=caller.id if caller else None,
            key=request.key,
            identity=identity,
            reuse=request.reuse,
            start=lambda operation_id: self._start(operation_id, request, caller),
            validate=lambda: self._validate_call(request, caller),
        )
        try:
            result = await lease.operation.settled()
            if caller:
                self.check_live(caller)
                caller.grants.add(result["ref"])
            return dict(result)
        finally:
            draining = self.operations.release(lease)
            if draining is not None:
                await asyncio.gather(asyncio.shield(draining), return_exceptions=True)

    async def aclose(self) -> None:
        """End the session, cancelling all caller waits and outstanding producers."""
        self._closed = True
        waiting = list(self._call_tasks)
        for task in waiting:
            task.cancel()
        for handle in list(self._handles):
            self._release_handle(handle)
        await self.operations.close()
        await asyncio.gather(*waiting, return_exceptions=True)

    def _record(
        self,
        frame: Frame,
        draft: Candidate,
        *,
        kind: str = "result",
        checkpoint_sequence: int | None = None,
    ) -> str:
        self.check_live(frame)
        for ref in draft["based_on"]:
            value = self._authorized_record(frame, ref)
            if value["status"] != "published":
                raise Rejected("Published artifacts cannot depend on unpublished records")
        return self.store.put(
            {
                "session": self.session,
                "frame": frame.id,
                "origin": frame.origin,
                "node": frame.request.node,
                "task": frame.request.task,
                "executor": frame.executor,
                "snapshot": self.registry.snapshot,
                "consulted": sorted(frame.consulted),
                "inputs": frame.request.inputs,
                "node_revision": self.registry.nodes[frame.request.node].revision,
                "input_refs": list(frame.request.refs),
                "observed_refs": sorted(frame.observed),
                "status": "published",
                "created_at": time.time(),
                **(
                    {"kind": kind, "checkpoint_sequence": checkpoint_sequence}
                    if kind == "checkpoint"
                    else {}
                ),
                **draft,
            }
        )

    async def _run(self, frame: Frame) -> Receipt:
        self.store.event(type="started", session=self.session, frame=frame.id)
        try:
            async with asyncio.timeout(max(0, self.deadline - time.monotonic())):
                packet = self.read_node(frame, frame.request.node)
                context: RunContext = {"entry": packet}
                output = await self._executors[frame.executor](frame, context)
                if (task := asyncio.current_task()) is not None and task.cancelling():
                    raise asyncio.CancelledError
                value = candidate(output)
                if any(not task.done() for task in frame.children) or frame.handles:
                    raise Rejected("Join or close all child calls before returning an output")
                ref = self._record(frame, value)
                self.store.event(type="completed", session=self.session, frame=frame.id, ref=ref)
                return {"ref": ref, "status": "published", "summary": value["summary"]}
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
            draining = [self._release_handle(handle) for handle in list(frame.handles)]
            for child in frame.children:
                if not child.done():
                    child.cancel()
            tasks = [*frame.children, *(task for task in draining if task is not None)]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            self.store.event(type="closed", session=self.session, frame=frame.id)
