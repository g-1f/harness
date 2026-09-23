"""JSON contracts at the application boundary; no agent-specific fields."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal, TypedDict


class Rejected(ValueError):
    """A request violates the local execution contract."""


def encode(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise Rejected("Expected finite JSON data") from error


def digest(value: Any) -> str:
    return hashlib.sha256(encode(value).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class NodeRequest:
    node: str
    task: str
    inputs: dict[str, Any]
    key: str
    refs: tuple[str, ...] = ()
    reuse: Literal["fresh", "session"] = "fresh"

    @classmethod
    def parse(cls, value: dict[str, Any]) -> NodeRequest:
        if not isinstance(value, dict) or set(value) - {
            "node",
            "task",
            "inputs",
            "key",
            "refs",
            "reuse",
        }:
            raise Rejected("Invalid call fields")
        if any(
            not isinstance(value.get(k), str) or not value[k].strip()
            for k in ("node", "task", "key")
        ):
            raise Rejected("node, task and key must be nonempty strings")
        refs = value.get("refs", [])
        if not isinstance(value.get("inputs"), dict) or not isinstance(refs, (list, tuple)):
            raise Rejected("inputs must be an object; refs must be an array")
        if any(not isinstance(ref, str) or not ref for ref in refs):
            raise Rejected("Artifact refs must be nonempty strings")
        if value.get("reuse", "fresh") not in ("fresh", "session"):
            raise Rejected("reuse must be fresh or session")
        body = encode(value)
        if len(body.encode()) > 32_000:
            raise Rejected("Request exceeds 32 KB")
        # Detach nested input objects from the caller before admission.
        clean = json.loads(body)
        return cls(**{**clean, "refs": tuple(refs)})


class Candidate(TypedDict):
    summary: str
    content: dict[str, Any]
    based_on: list[str]


def candidate(value: Any) -> Candidate:
    if (
        not isinstance(value, dict)
        or set(value) - {"summary", "content", "based_on"}
        or not isinstance(value.get("summary"), str)
        or not 1 <= len(value["summary"].strip()) <= 600
        or len(value["summary"]) > 600
        or not isinstance(value.get("content"), dict)
        or not isinstance(value.get("based_on", []), list)
        or any(not isinstance(ref, str) or not ref for ref in value.get("based_on", []))
    ):
        raise Rejected("Candidate needs summary (1–600 chars), content object and based_on refs")
    body = encode({**value, "based_on": value.get("based_on", [])})
    if len(body.encode()) > 500_000:
        raise Rejected("Candidate exceeds 500 KB; use external artifact references")
    return json.loads(body)


class Receipt(TypedDict):
    ref: str
    status: Literal["accepted", "needs_review"]
    summary: str


class RunContext(TypedDict):
    entry: dict[str, Any]
    attempt: int
    feedback: list[dict[str, Any]]
    previous: str | None
