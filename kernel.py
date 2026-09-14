"""Reference Library supervisor. Single process, one event loop, no model credentials.

The adapter supplies inference. SQLite stores immutable results; this module does
not execute generated Python or shell code. See README for production boundaries.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable


def encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(encode(value).encode()).hexdigest()


class Rejected(ValueError):
    pass


@dataclass(frozen=True)
class Call:
    skill: str
    task: str
    inputs: dict[str, Any]
    key: str
    refs: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: dict[str, Any]) -> "Call":
        if not isinstance(value, dict) or set(value) - {"skill", "task", "inputs", "key", "refs"}:
            raise Rejected("Invalid call fields")
        if any(not isinstance(value.get(k), str) or not value[k].strip()
               for k in ("skill", "task", "key")):
            raise Rejected("skill, task and key must be nonempty strings")
        refs = value.get("refs", [])
        if not isinstance(value.get("inputs"), dict) or not isinstance(refs, (list, tuple)):
            raise Rejected("inputs must be an object; refs must be an array")
        if any(not isinstance(ref, str) for ref in refs) or len(encode(value)) > 32000:
            raise Rejected("Invalid or oversized request")
        return cls(**{**value, "refs": tuple(refs)})


@dataclass(frozen=True)
class Review:
    critics: tuple[str, ...] = ()
    max_revisions: int = 0


@dataclass(frozen=True)
class Skill:
    name: str
    text: str
    revision: str
    links: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    review: Review = Review()
    critic: bool = False
    ttl_seconds: int = 3600


class Registry:
    def __init__(self, skills: list[Skill], notes: dict[str, str] | None = None):
        self.skills = {s.name: s for s in skills}
        self.notes = dict(notes or {})
        if len(self.skills) != len(skills):
            raise Rejected("Duplicate skill ID")
        for s in skills:
            if not re.fullmatch(r"[a-z0-9_-]+(?:/[a-z0-9_-]+)*", s.name):
                raise Rejected("Invalid canonical skill ID")
            if len(s.text.encode()) > 24000:
                raise Rejected("Split skills exceeding the entry size budget")
            if not 0 <= s.review.max_revisions <= 3 or s.ttl_seconds <= 0:
                raise Rejected("Invalid review or freshness bound")
            for linked in (*s.links, *s.review.critics):
                if linked not in self.skills:
                    raise Rejected(f"Broken link: {s.name} -> {linked}")
            if s.critic and s.review.critics:
                raise Rejected("Critic skills cannot recursively require reviews")
            if any(not self.skills[c].critic for c in s.review.critics):
                raise Rejected("Review policies must reference critic skills")
        self.snapshot = digest({s.name: s.revision for s in skills})

    @classmethod
    def load(cls, root: Path) -> "Registry":
        import yaml
        skills = []
        for path in sorted((root / "skills").rglob("SKILL.md")):
            text = path.read_text(encoding="utf-8")
            match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
            meta = yaml.safe_load(match[1]) if match else {}
            name = path.parent.relative_to(root / "skills").as_posix()
            body = text[match.end():] if match else text
            prose = re.sub(r"```.*?```", "", body, flags=re.S)
            links = tuple(dict.fromkeys(x.split("|", 1)[0].split("#", 1)[0]
                                        for x in re.findall(r"\[\[([^\]]+)\]\]", prose)))
            policy = meta.get("library", {})
            review = policy.get("review", {})
            skills.append(Skill(
                name, text, hashlib.sha256(text.encode()).hexdigest(),
                tuple(x for x in links if not x.startswith("memory/")),
                tuple(x for x in links if x.startswith("memory/")),
                Review(tuple(review.get("critics", [])), review.get("max_revisions", 0)),
                policy.get("profile") == "critic", policy.get("ttl_seconds", 3600),
            ))
        notes = {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
                 for p in (root / "memory").rglob("*.md")
                 if "observations" not in p.relative_to(root).parts}
        return cls(skills, notes)


class Store:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL)")

    def put(self, value: dict[str, Any]) -> str:
        body = encode(value)
        if len(body.encode()) > 1_000_000:
            raise Rejected("Reference store limit is 1 MB per record; use external blobs")
        ref = hashlib.sha256(body.encode()).hexdigest()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO records VALUES (?,?)", (ref, body))
        return ref

    def get(self, ref: str) -> dict[str, Any]:
        row = self.db.execute("SELECT body FROM records WHERE id=?", (ref,)).fetchone()
        if row is None:
            raise Rejected("Unknown artifact")
        if hashlib.sha256(row[0].encode()).hexdigest() != ref:
            raise Rejected("Artifact integrity failure")
        return json.loads(row[0])

    def all(self):
        for ref, body in self.db.execute("SELECT id, body FROM records ORDER BY rowid DESC"):
            yield ref, json.loads(body)

    def event(self, **value):
        with self.db:
            self.db.execute("INSERT INTO events(body) VALUES (?)", (encode(value),))


@dataclass
class Frame:
    id: str
    parent: "Frame | None"
    call: Call
    lineage: tuple[str, ...]
    active: set[str] = field(default_factory=set)
    grants: set[str] = field(default_factory=set)
    children: set[asyncio.Task] = field(default_factory=set)
    closed: bool = False


class Ledger:
    """Hard call-count admission in this process, not a currency cost ledger."""
    def __init__(self, max_frames=64, max_model_calls=256, model_parallelism=8):
        if min(max_frames, max_model_calls, model_parallelism) < 1:
            raise Rejected("Ledger limits must be positive")
        self.max_frames = max_frames
        self.max_model_calls = max_model_calls
        self.frames = 0
        self.model_calls = 0
        self.slots = asyncio.Semaphore(model_parallelism)

    def admit_frame(self):
        if self.frames >= self.max_frames:
            raise Rejected("Session frame budget exhausted")
        self.frames += 1

    async def model_call(self, invoke: Callable[[], Awaitable[Any]]) -> Any:
        # Never hold this permit around an entire agent or while it awaits children.
        async with self.slots:
            if self.model_calls >= self.max_model_calls:
                raise Rejected("Session model-call budget exhausted")
            self.model_calls += 1
            return await invoke()


Runner = Callable[[Frame, dict[str, Any]], Awaitable[dict[str, Any]]]


class Kernel:
    def __init__(self, registry: Registry, store: Store, runner: Runner | None = None,
                 ledger: Ledger | None = None, *, max_depth=5, deadline_seconds=180,
                 max_revisions=2):
        if max_depth < 0 or max_revisions < 0 or deadline_seconds <= 0:
            raise Rejected("Invalid supervisor limits")
        self.registry, self.store, self.runner = registry, store, runner
        self.ledger = ledger or Ledger()
        self.session = uuid.uuid4().hex
        self.max_depth, self.max_revisions = max_depth, max_revisions
        self.deadline = time.monotonic() + deadline_seconds
        self.jobs: dict[tuple[str, str], tuple[str, asyncio.Task]] = {}

    def _live(self, frame: Frame):
        if frame.closed or time.monotonic() >= self.deadline:
            raise Rejected("Frame closed or session deadline exceeded")

    def read(self, frame: Frame, ref: str) -> dict[str, Any]:
        self._live(frame)
        value = self.store.get(ref)
        if value["session"] != self.session:
            raise Rejected("Cross-session access denied")
        if value["status"] != "accepted" and value["frame"] != frame.id and ref not in frame.grants:
            raise Rejected("Draft is not visible to this frame")
        return value

    def slice(self, frame: Frame, ref: str, offset=0, limit=4000):
        if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 16000:
            raise Rejected("Invalid slice")
        text = encode(self.read(frame, ref))
        return {"ref": ref, "text": text[offset:offset + limit],
                "next_offset": min(len(text), offset + limit), "total_chars": len(text)}

    def open(self, frame: Frame, skill_name: str, *, limit=16000):
        self._live(frame)
        if not 512 <= limit <= 32000 or skill_name not in self.registry.skills:
            raise Rejected("Unknown skill or invalid entry budget")
        skill = self.registry.skills[skill_name]
        if self.registry.skills[frame.call.skill].critic and skill.review.critics:
            raise Rejected("Critics read candidate evidence; they cannot activate producer reviews")
        packet = {"skill": skill.name, "revision": skill.revision, "text": skill.text,
                  "notes": [], "candidates": [], "links": list(skill.links),
                  "missing": list(skill.links), "omitted": 0}
        if len(encode(packet)) > limit - 64:
            raise Rejected("Entry exceeds budget; split the skill or request a larger bounded packet")
        note_ids = (f"memory/notes/skills/{skill_name}.md", *skill.notes)
        for name in dict.fromkeys(note_ids):
            if name not in self.registry.notes:
                continue
            note = {"ref": name, "authority": "evidence", "text": self.registry.notes[name]}
            packet["notes"].append(note)
            if len(encode(packet)) > limit - 64:
                packet["notes"].pop()
                packet["omitted"] += 1
        for ref, value in self.store.all():
            linked = self.registry.skills.get(value["skill"])
            if (value["status"] != "accepted" or value["session"] != self.session
                    or value["skill"] not in skill.links or not linked
                    or value["snapshot"] != self.registry.snapshot
                    or value["inputs"] != frame.call.inputs
                    or time.time() - value["created_at"] > linked.ttl_seconds):
                continue
            item = {"ref": ref, "skill": value["skill"], "inputs": value["inputs"],
                    "created_at": value["created_at"], "summary": value["summary"]}
            packet["candidates"].append(item)
            if len(encode(packet)) > limit - 64:
                packet["candidates"].pop()
                packet["omitted"] += 1
            elif value["skill"] in packet["missing"]:
                packet["missing"].remove(value["skill"])
        frame.active.add(skill_name)
        self.store.event(type="skill_enter", session=self.session, frame=frame.id,
                         skill=skill_name, revision=skill.revision)
        return packet

    async def call(self, request: Call, parent: Frame | None = None) -> dict[str, Any]:
        request = Call.parse(asdict(request))
        if parent:
            self._live(parent)
        if request.skill not in self.registry.skills:
            raise Rejected("Unknown skill")
        signature = digest({"skill": request.skill, "inputs": request.inputs,
                            "task": request.task, "refs": request.refs})
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
                raise Rejected("Root artifact grants must come from an authenticated launcher")
            self.read(parent, ref)
        self.ledger.admit_frame()
        frame = Frame(uuid.uuid4().hex, parent, request, (*lineage, signature),
                      grants=set(request.refs))
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

    def _record(self, frame, draft, status, reviews=()):
        for ref in draft.get("based_on", []):
            value = self.read(frame, ref)
            if status == "accepted" and value["status"] != "accepted":
                raise Rejected("Accepted results cannot depend on unaccepted artifacts")
        return self.store.put({
            "session": self.session, "frame": frame.id,
            "parent": frame.parent.id if frame.parent else None,
            "skill": frame.call.skill, "snapshot": self.registry.snapshot,
            "consulted": sorted(frame.active), "inputs": frame.call.inputs,
            "status": status, "created_at": time.time(), "summary": draft["summary"],
            "content": draft["content"], "based_on": draft.get("based_on", []),
            "reviews": list(reviews),
        })

    async def _run(self, frame: Frame):
        self.store.event(type="started", session=self.session, frame=frame.id)
        try:
            async with asyncio.timeout(max(0, self.deadline - time.monotonic())):
                packet = self.open(frame, frame.call.skill)
                feedback, previous = [], None
                for attempt in range(self.max_revisions + 1):
                    assert self.runner is not None
                    draft = await self.runner(frame, {"entry": packet, "attempt": attempt,
                                                      "feedback": feedback, "previous": previous})
                    if (not isinstance(draft, dict) or not isinstance(draft.get("summary"), str)
                            or not draft["summary"].strip() or len(draft["summary"]) > 600
                            or "content" not in draft or not isinstance(draft.get("based_on", []), list)):
                        raise Rejected("Worker must return summary, content and optional based_on")
                    unfinished = [t for t in frame.children if not t.done()]
                    if unfinished:
                        raise Rejected("Join children before returning a draft")
                    draft_ref = self._record(frame, draft, "draft")
                    policies = [self.registry.skills[s].review for s in sorted(frame.active)
                                if self.registry.skills[s].review.critics]
                    critics = tuple(dict.fromkeys(c for p in policies for c in p.critics))
                    round_limit = min([self.max_revisions, *(p.max_revisions for p in policies)])
                    reviews, feedback = [], []

                    async def review_one(critic):
                        return await self.call(Call(
                            critic, f"Review candidate {draft_ref}; independently test claims. "
                            "Return content with candidate_ref, verdict pass or fail, and findings array.",
                            frame.call.inputs, f"review:{attempt}:{critic}", (draft_ref,)), frame)

                    # Keep candidate reviews separate; a new revision invalidates all prior verdicts.
                    results = await asyncio.gather(*(review_one(c) for c in critics), return_exceptions=True)
                    for critic, result in zip(critics, results):
                        if isinstance(result, BaseException):
                            feedback.append({"critic": critic, "error": type(result).__name__})
                            continue
                        reviews.append(result["ref"])
                        verdict = self.read(frame, result["ref"])["content"]
                        valid = (isinstance(verdict, dict) and verdict.get("candidate_ref") == draft_ref
                                 and verdict.get("verdict") in ("pass", "fail")
                                 and isinstance(verdict.get("findings"), list))
                        if result["status"] != "accepted" or not valid or verdict["verdict"] != "pass" or verdict["findings"]:
                            feedback.append({"critic": critic, "ref": result["ref"], "verdict": verdict})
                    if not feedback:
                        ref = self._record(frame, draft, "accepted", reviews)
                        self.store.event(type="accepted", session=self.session, frame=frame.id, ref=ref)
                        return {"ref": ref, "status": "accepted", "summary": draft["summary"]}
                    if attempt >= round_limit:
                        ref = self._record(frame, draft, "needs_review", reviews)
                        self.store.event(type="needs_review", session=self.session, frame=frame.id, ref=ref)
                        return {"ref": ref, "status": "needs_review", "summary": draft["summary"]}
                    previous = draft_ref
                raise AssertionError("Unreachable revision bound")
        except asyncio.CancelledError:
            self.store.event(type="cancelled", session=self.session, frame=frame.id)
            raise
        except Exception as error:
            self.store.event(type="failed", session=self.session, frame=frame.id, error=type(error).__name__)
            raise
        finally:
            frame.closed = True
            for child in frame.children:
                if not child.done():
                    child.cancel()
            if frame.children:
                await asyncio.gather(*frame.children, return_exceptions=True)
            self.store.event(type="closed", session=self.session, frame=frame.id)
