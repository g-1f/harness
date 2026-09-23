"""One-event-loop ownership of shared work and the graph of active waits.

Acquisition and release mutate bookkeeping without awaiting: these are the atomic
critical sections. No lock is held while an executor runs, a caller waits, or a
cancelled generation drains. Sharing never transfers ownership to its first caller.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import Counter
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Literal

from harness.contracts import Receipt, Rejected

Start = Callable[[str], Coroutine[Any, Any, Receipt]]
Emit = Callable[..., None]


@dataclass(slots=True)
class Operation:
    id: str
    identity: str
    task: asyncio.Task[Receipt]
    stopping: bool = False
    waiters: set[str] = field(default_factory=set)
    checkpoints: list[Receipt] = field(default_factory=list)
    changed: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def state(self) -> str:
        if not self.task.done():
            return "cancelling" if self.stopping else "running"
        if self.task.cancelled():
            return "cancelled"
        if self.task.exception() is not None:
            return "failed"
        return self.task.result()["status"]


@dataclass(frozen=True, slots=True)
class Call:
    """Sticky caller/key identity, including unsuccessful completed attempts."""

    identity: str
    reuse: str
    operation: Operation | None = None


@dataclass(slots=True)
class Lease:
    id: str
    caller: str | None
    operation: Operation
    waiting: bool
    released: bool = False
    observing: bool = False


class OperationPool:
    def __init__(self, *, max_depth: int, emit: Emit):
        self.max_depth = max_depth
        self.emit = emit
        self.calls: dict[tuple[str | None, str], Call] = {}
        self.operations: dict[str, Operation] = {}
        self.shared: dict[str, Operation] = {}
        self.waits: dict[str, Counter[str]] = {}
        self.closed = False

    async def acquire(
        self,
        *,
        caller: str | None,
        key: str,
        identity: str,
        reuse: Literal["fresh", "session"],
        start: Start,
        validate: Callable[[], None],
        block_until_complete: bool = True,
    ) -> Lease:
        """Acquire a waiter or wait for a cancelled generation's cleanup first."""
        while True:
            if self.closed:
                raise Rejected("Operation pool is closed")
            validate()
            call_key = (caller, key)
            call = self.calls.get(call_key)
            if call is not None:
                if (call.identity, call.reuse) != (identity, reuse):
                    raise Rejected("Idempotency key reused for a different request")
            else:
                call = Call(identity, reuse)
                self.calls[call_key] = call
            if call.operation is not None:
                operation = call.operation
                disposition = "replayed"
            else:
                operation = self.shared.get(identity) if reuse == "session" else None
                if operation is not None and operation.state == "cancelling":
                    if caller is not None:
                        self._add_wait(caller, operation.id)
                    self.emit(
                        type="operation_draining", caller=caller, operation=operation.id, key=key
                    )
                    # Do not overlap replacement execution with old cleanup. Cancellation
                    # of this waiter leaves the draining producer untouched.
                    try:
                        await asyncio.gather(asyncio.shield(operation.task), return_exceptions=True)
                    finally:
                        if caller is not None:
                            self._remove_wait(caller, operation.id)
                    continue
                if operation is not None and operation.state in ("running", "accepted"):
                    disposition = "joined" if operation.state == "running" else "reused"
                else:
                    operation = None
                    disposition = "started"

            target = operation.id if operation else uuid.uuid4().hex
            if caller == target:
                raise Rejected("An operation cannot attach to itself")
            waiting = block_until_complete and (operation is None or not operation.task.done())
            if caller is not None and waiting:
                self._add_wait(caller, target)
            try:
                if operation is None:
                    # start performs admission and creates the frame synchronously.
                    task = asyncio.create_task(start(target))
                    operation = Operation(target, identity, task)
                    self.operations[target] = operation
                    if reuse == "session":
                        self.shared[identity] = operation
                    task.add_done_callback(lambda task, op=operation: self._finished(op))
                if call.operation is None:
                    self.calls[call_key] = Call(identity, reuse, operation)
                lease = Lease(uuid.uuid4().hex, caller, operation, waiting)
                operation.waiters.add(lease.id)
            except BaseException:
                if caller is not None and waiting:
                    self._remove_wait(caller, target)
                raise
            self.emit(
                type="call_acquired",
                caller=caller,
                operation=operation.id,
                lease=lease.id,
                key=key,
                reuse=reuse,
                disposition=disposition,
                waiters=len(operation.waiters),
            )
            return lease

    def publish(self, operation_id: str, receipt: Receipt) -> int:
        """Announce an independently accepted checkpoint to every current/future caller."""
        operation = self.operations[operation_id]
        if operation.stopping or operation.task.done() or receipt["status"] != "accepted":
            raise Rejected("Only a running operation can publish an accepted checkpoint")
        cursor = len(operation.checkpoints) + 1
        self.emit(
            type="checkpoint_published", operation=operation_id, cursor=cursor, ref=receipt["ref"]
        )
        operation.checkpoints.append(dict(receipt))
        self._signal(operation)
        return cursor

    async def next_event(self, lease: Lease, after: int) -> dict:
        """Replay a checkpoint, or wait for the next one or terminal state."""
        if type(after) is not int or after < 0 or lease.released:
            raise Rejected("Invalid checkpoint cursor or closed handle")
        operation = lease.operation
        while True:
            if lease.released:
                raise Rejected("Node handle closed while awaiting an event")
            if after < len(operation.checkpoints):
                return {
                    "kind": "checkpoint",
                    "cursor": after + 1,
                    "receipt": dict(operation.checkpoints[after]),
                }
            if after > len(operation.checkpoints):
                raise Rejected("Checkpoint cursor is ahead of this operation")
            if operation.task.done():
                return {"kind": "terminal", "cursor": after}
            changed = operation.changed
            if lease.caller is not None:
                self._add_wait(lease.caller, operation.id)
            try:
                await changed.wait()
            finally:
                if lease.caller is not None:
                    self._remove_wait(lease.caller, operation.id)

    @staticmethod
    def _signal(operation: Operation) -> None:
        operation.changed.set()
        operation.changed = asyncio.Event()

    def release(self, lease: Lease) -> asyncio.Task[Receipt] | None:
        """Release once; return the producer to drain when its last waiter leaves."""
        if lease.released:
            return None
        lease.released = True
        operation = lease.operation
        operation.waiters.remove(lease.id)
        self._signal(operation)
        if lease.caller is not None and lease.waiting:
            self._remove_wait(lease.caller, operation.id)
        self.emit(
            type="call_released",
            caller=lease.caller,
            operation=operation.id,
            lease=lease.id,
            waiters=len(operation.waiters),
        )
        if not operation.waiters and not operation.task.done():
            if not operation.stopping:
                operation.stopping = True
                operation.task.cancel()
                self.emit(type="operation_stopping", operation=operation.id, reason="no_waiters")
            return operation.task
        return None

    def _add_wait(self, caller: str, target: str) -> None:
        pending, visited = [target], set()
        while pending:
            node = pending.pop()
            if node == caller:
                raise Rejected("Wait cycle: an operation cannot await its own dependency chain")
            if node not in visited:
                visited.add(node)
                pending.extend(self.waits.get(node, ()))
        self.waits.setdefault(caller, Counter())[target] += 1

        def depth(node: str, memo: dict[str, int]) -> int:
            if node not in memo:
                memo[node] = max(
                    (1 + depth(child, memo) for child in self.waits.get(node, ())), default=0
                )
            return memo[node]

        memo: dict[str, int] = {}
        if any(depth(node, memo) > self.max_depth for node in self.waits):
            self._remove_wait(caller, target)
            raise Rejected("Maximum active dependency depth exceeded")

    def _remove_wait(self, caller: str, target: str) -> None:
        edges = self.waits[caller]
        edges[target] -= 1
        if not edges[target]:
            del edges[target]
        if not edges:
            del self.waits[caller]

    def _finished(self, operation: Operation) -> None:
        # Reading state also consumes exceptions from abandoned task results.
        self.emit(type="operation_finished", operation=operation.id, state=operation.state)
        self._signal(operation)

    async def close(self) -> None:
        self.closed = True
        for operation in self.operations.values():
            if not operation.task.done() and not operation.stopping:
                operation.stopping = True
                operation.task.cancel()
        await asyncio.gather(*(op.task for op in self.operations.values()), return_exceptions=True)
