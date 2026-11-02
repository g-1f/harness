"""Reference prototype of the five-verb kernel: spawn, query, commit, wait, close.

Everything an agent can see or change is a versioned database: theses, sources, skills,
inboxes, each computation's output, and (read-only) the kernel's own tables. Agent programs
here are Python coroutines standing in for model-written code; the same verbs bridge to
QuickJS (one test runs a JavaScript program through them).

Authority is a tree (who owns, steers, budgets and stops what). Liveness is a DAG (work
stays alive while anyone holds it). Information is a graph (recorded reads, cycles allowed
across versions). Relevance is the model's: the kernel only knows what each run read.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:12]


class Rejected(Exception):
    """An expected contract failure the program can catch and act on."""


STOP = {"the", "a", "an", "is", "for", "of", "to", "in", "on"}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if w not in STOP}


# --- World: versioned databases with two clocks -------------------------------------------


class World:
    def __init__(self):
        self.dbs: dict[str, list[dict]] = {}
        self.tx = 0

    def history(self, db):
        return self.dbs.get(db, [])

    def at(self, db, as_of=None, available_by=None):
        found = self.history(db)
        if as_of is not None:
            found = [v for v in found if v["tx"] <= as_of]
        if available_by is not None:
            found = [v for v in found if v["available_at"] is not None and v["available_at"] <= available_by]
        return found[-1] if found else None

    def version(self, db, number):
        return self.dbs[db][number - 1] if number else None

    @staticmethod
    def select(version, keys):
        rows = version["rows"] if version else {}
        return {k: rows.get(k) for k in keys} if keys else dict(rows)

    def first_seen_tx(self, db, key):
        for v in self.history(db):
            if key in v["rows"]:
                return v["tx"]
        return None

    def write(self, db, changes, writer, available_at=None, read_set=()):
        previous = self.at(db)
        old = dict(previous["rows"]) if previous else {}
        new = dict(old)
        for key, value in changes.items():
            if value is None:
                new.pop(key, None)
            else:
                new[key] = value
        diff = {k: [old.get(k), new.get(k)] for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)}
        if not diff and previous is not None:
            return previous, False
        self.tx += 1
        version = {"db": db, "number": len(self.history(db)) + 1, "tx": self.tx, "rows": new,
                   "diff": diff, "writer": writer, "available_at": available_at,
                   "read_set": list(read_set)}
        self.dbs.setdefault(db, []).append(version)
        return version, True


# --- Computations and runs ------------------------------------------------------------------


@dataclass
class Comp:
    """A named computation. Its handle is stable across revisions; its output is out/<key>."""

    key: str
    task: str
    inputs: dict
    skill: str | None
    model: str
    owner: str  # "human" or the owning computation's key: the authority tree
    budget: int | None = None
    holders: set = field(default_factory=set)  # the liveness DAG
    current: str | None = None
    revisions: int = 0


@dataclass
class Run:
    id: str
    key: str
    revision: int
    started: float
    state: str = "running"
    ended: float | None = None
    reads: list = field(default_factory=list)
    children: set = field(default_factory=set)
    delta: list = field(default_factory=list)
    budget: int | None = None
    error: str | None = None
    out_versions: list = field(default_factory=list)


class Kernel:
    def __init__(self, programs, skills=None):
        self.programs = programs
        self.world = World()
        self.comps: dict[str, Comp] = {}
        self.runs: dict[str, Run] = {}
        self.tasks: dict[str, asyncio.Future] = {}
        self.traj: list[dict] = []
        self.t0 = time.monotonic()
        self._changed = asyncio.Event()
        self.waiting: dict[str, set] = {}
        if skills:
            self.world.write("lib/skills", dict(skills), None)

    # -- bookkeeping ----------------------------------------------------------------------
    def now(self):
        return round(time.monotonic() - self.t0, 4)

    def log(self, who, verb, **detail):
        key, rev = (who.key, who.revision) if isinstance(who, Run) else (who or "kernel", None)
        self.traj.append({"seq": len(self.traj) + 1, "t": self.now(), "key": key, "rev": rev,
                          "verb": verb, **detail})

    def _signal(self):
        self._changed.set()
        self._changed = asyncio.Event()

    def _launch(self, key, coro):
        task = asyncio.ensure_future(coro)
        self.tasks[key] = task
        task.add_done_callback(lambda _t: self._signal())
        return task

    @staticmethod
    def _key(task, inputs, skill, model, share):
        body = {"task": task, "inputs": inputs, "skill": skill, "model": model}
        if not share:
            body["nonce"] = uuid.uuid4().hex
        return digest(body)

    def state(self, key):
        task = self.tasks.get(key)
        if task is not None and not task.done():
            return "running"
        comp = self.comps[key]
        return self.runs[comp.current].state if comp.current else "absent"

    # -- people and sources (principals outside the computation tree) ---------------------
    def start(self, task, inputs=None, skill=None, budget=None):
        key = self._key(task, inputs or {}, skill, "default", True)
        comp = self.comps.get(key) or Comp(key, task, inputs or {}, skill, "default", "human", budget)
        self.comps[key] = comp
        comp.holders.add("human")
        self._launch(key, self._run(comp))
        self.log("human", "spawn", handle=key, task=task, disposition="started")
        return key

    async def result(self, key):
        if key in self.tasks:
            await asyncio.shield(self.tasks[key])
        return self.out_rows(key)

    async def refresh(self, key):
        """Bring a computation up to date: re-run only what recorded reads say is stale."""
        await self.refresh_key(key, ())
        return self.out_rows(key)

    def out_rows(self, key):
        return self.world.select(self.world.at(f"out/{key}"), None)

    def source_commit(self, db, changes, available_at=None, who="source"):
        version, changed = self.world.write(db, changes, None, available_at)
        self.log(who, "commit", db=db, version=version["number"], diff=version["diff"] if changed else {})
        if changed:
            self._signal()
        return version["number"]

    def human_tell(self, key, text):
        return self._tell(None, key, {"text": text})

    def edit_skill(self, name, skill):
        return self.source_commit("lib/skills", {name: skill}, who="human")

    def fork(self):
        """A scenario world: copy-on-write in production, a deep copy here."""
        if any(not t.done() for t in self.tasks.values()):
            raise Rejected("Fork a quiescent world")
        other = Kernel.__new__(Kernel)
        other.programs = self.programs
        other.world = copy.deepcopy(self.world)
        other.comps = copy.deepcopy(self.comps)
        other.runs = copy.deepcopy(self.runs)
        other.tasks, other.waiting = {}, {}
        other.traj = list(self.traj)
        other.t0 = self.t0
        other._changed = asyncio.Event()
        return other

    # -- the five verbs ------------------------------------------------------------------
    def spawn(self, run, task, inputs, skill, model, share, budget):
        if skill is not None and skill not in self.world.select(self.world.at("lib/skills"), None):
            raise Rejected(f"Unknown skill {skill!r}")
        key = self._key(task, inputs, skill, model, share)
        comp = self.comps.get(key)
        if comp is None:
            cost = 1 + (budget or 0)
            if run.budget is not None:
                if run.budget < cost:
                    self.log(run, "spawn", task=task, rejected="budget")
                    raise Rejected("Spawn budget exhausted")
                run.budget -= cost
            comp = Comp(key, task, inputs, skill, model, run.key, budget)
            self.comps[key] = comp
            disposition = "started"
            self._launch(key, self._run(comp))
        else:
            task_ = self.tasks.get(key)
            if task_ is not None and not task_.done():
                disposition = "joined"
            else:
                disposition = "verifying"
                self._launch(key, self._ensure(key, ()))
        comp.holders.add(run.key)
        run.children.add(key)
        self.log(run, "spawn", handle=key, task=task, disposition=disposition)
        return key

    def query(self, run, db, keys=None, as_of=None, available_by=None, similar=None, top=3):
        if db == "sys/agents":
            rows = self._agents_view(run)
            return self._recorded(run, db, keys, None, rows, volatile=True)
        if db == "sys/trajectory":
            rows = {str(r["seq"]): r for r in self.traj if keys is None or r["key"] in keys}
            return self._recorded(run, db, keys, None, rows, volatile=True)
        version = self.world.at(db, as_of, available_by)
        if similar is not None:
            target, scored = words(similar), {}
            for k, row in (version["rows"] if version else {}).items():
                text = row.get("question", "") if isinstance(row, dict) else row
                score = len(target & words(text)) / max(1, len(target | words(text)))
                scored[k] = {**(row if isinstance(row, dict) else {"value": row}),
                             "score": round(score, 3), "tx": self.world.first_seen_tx(db, k)}
            rows = dict(sorted(scored.items(), key=lambda kv: -kv[1]["score"])[:top])
            return self._recorded(run, db, None, version, rows, volatile=True)
        rows = self.world.select(version, keys)
        return self._recorded(run, db, keys, version, rows,
                              volatile=as_of is not None or available_by is not None)

    def commit(self, run, db, changes, if_absent=None, available_at=None, _sender=None):
        if db.startswith("sys/"):
            raise Rejected("System databases are written by the kernel")
        if db.startswith("out/") and db != f"out/{run.key}":
            raise Rejected("Only a computation writes its own output")
        if db.startswith("inbox/") and _sender is None:
            raise Rejected("Use tell to write an inbox")
        if if_absent:
            version = self.world.at(db)
            existing = {k: version["rows"][k] for k in if_absent if version and k in version["rows"]}
            if existing:
                self._recorded(run, db, list(if_absent), version, existing)
                self.log(run, "commit", db=db, conflict=sorted(existing))
                return {"conflict": True, "existing": existing, "version": version["number"]}
        read_set = [(r["db"], r["version"]) for r in self._latest_reads(run) if not r["volatile"]]
        version, changed = self.world.write(db, changes, run.key, available_at, read_set)
        if changed and db == f"out/{run.key}":
            run.out_versions.append(version["number"])
        self.log(run, "commit", db=db, version=version["number"], diff=version["diff"] if changed else {},
                 noop=not changed)
        if changed:
            self._signal()
        return {"version": version["number"], "diff": version["diff"] if changed else {}, "noop": not changed}

    async def wait(self, run, sources, timeout=None):
        sources = sources if isinstance(sources, list) else [sources]
        handles = {s for s in sources if isinstance(s, str)}
        for handle in handles:
            if self._reaches(handle, run.key):
                self.log(run, "wait", rejected="cycle", handle=handle)
                raise Rejected("Wait cycle: that computation is already waiting on you")
        self.waiting[run.key] = handles
        deadline = None if timeout is None else time.monotonic() + timeout
        self.log(run, "wait", sources=[self._describe(s) for s in sources], timeout=timeout)
        try:
            while True:
                changed = self._changed
                for source in sources:
                    event = self._ready(run, source)
                    if event is not None:
                        self.log(run, "wake", cause=event["kind"], source=self._describe(source))
                        return event
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self.log(run, "wake", cause="timeout")
                        return {"kind": "timeout"}
                    try:
                        await asyncio.wait_for(changed.wait(), remaining)
                    except TimeoutError:
                        pass
                else:
                    await changed.wait()
        finally:
            self.waiting.pop(run.key, None)

    def close(self, run, handle):
        self._release(run.key, handle)
        run.children.discard(handle)
        self.log(run, "close", handle=handle)

    # -- steering: a commit to an inbox, with authority checked up the tree ---------------
    def _tell(self, run, target, message):
        comp = self.comps.get(target)
        if comp is None:
            raise Rejected("Unknown computation")
        if run is not None and not self._is_ancestor(run.key, target):
            raise Rejected("Only an owner up the tree, or a person, can steer this computation")
        db = f"inbox/{target}"
        version = self.world.at(db)
        seq = len(version["rows"]) + 1 if version else 1
        sender = run.key if run is not None else "human"
        cause = message.pop("cause", None)
        self.world.write(db, {str(seq): {**message, "from": sender, "cause": cause}}, sender)
        self.log(run if run is not None else "human", "tell", handle=target, seq=seq,
                 text=message.get("text"), cause=cause)
        self._signal()
        return seq

    # -- running and refreshing -------------------------------------------------------------
    async def _run(self, comp, delta=None):
        comp.revisions += 1
        run = Run(f"{comp.key}#{comp.revisions}", comp.key, comp.revisions, self.now(),
                  delta=delta or [], budget=comp.budget)
        self.runs[run.id] = run
        comp.current = run.id
        ax = Ax(self, run, comp)
        self.log(run, "run_start", task=comp.task, because=[d["db"] for d in run.delta])
        try:
            if comp.skill:
                ax.query("lib/skills", [comp.skill])  # the procedure enters context as a recorded read
            program = self.programs.get((comp.skill, comp.task)) or self.programs.get((None, comp.task))
            if program is None:
                raise Rejected(f"No program for {comp.task!r}")
            await program(ax)
            run.state = "done"
        except asyncio.CancelledError:
            run.state = "cancelled"
        except Exception as error:  # noqa: BLE001 - recorded, never swallowed silently
            run.state, run.error = "failed", f"{type(error).__name__}: {error}"
        finally:
            run.ended = self.now()
            for child in list(run.children):
                self._release(comp.key, child)
            self.log(run, "run_end", state=run.state, **({"error": run.error} if run.error else {}))

    async def _ensure(self, key, stack):
        """Verifying trace: refresh the writers of everything this run read, then re-check."""
        comp = self.comps[key]
        run = self.runs.get(comp.current)
        if run is None or run.state != "done":
            await self._run(comp)
            return
        reads = self._latest_reads(run)
        writers = {r["writer"] for r in reads
                   if r["writer"] and r["writer"] != key and r["writer"] not in stack}
        if writers:
            await asyncio.gather(*(self.refresh_key(w, stack + (key,)) for w in writers))
        stale = [r for r in reads if not r["volatile"] and self._hash_now(r) != r["hash"]]
        if not stale:
            self.log(run, "reuse", handle=key)
            return
        delta = [{"db": r["db"], "keys": r["keys"], "was": r["rows"], "now": self._rows_now(r)} for r in stale]
        await self._run(comp, delta)

    async def refresh_key(self, key, stack):
        if key in stack:
            return
        task = self.tasks.get(key)
        if task is None or task.done():
            task = self._launch(key, self._ensure(key, stack))
        await asyncio.shield(task)

    def explain(self, key):
        """Why a computation's output changed: the reads that moved, and the output diff."""
        run = self.runs[self.comps[key].current]
        diff = self.world.version(f"out/{key}", run.out_versions[-1])["diff"] if run.out_versions else {}
        return {"revision": run.revision,
                "because": [{"db": d["db"], "was": d["was"], "now": d["now"]} for d in run.delta],
                "output_diff": diff}

    # -- internals ------------------------------------------------------------------------
    def _recorded(self, run, db, keys, version, rows, volatile=False):
        result = {"db": db, "version": version["number"] if version else 0, "rows": rows}
        if run is None:
            return result
        run.reads.append({"db": db, "keys": list(keys or []), "version": result["version"],
                          "hash": digest(rows), "rows": rows, "volatile": volatile,
                          "writer": version["writer"] if version else None})
        self.log(run, "query", db=db, keys=list(keys or []), version=result["version"])
        return result

    @staticmethod
    def _latest_reads(run):
        latest = {}
        for read in run.reads:
            latest[read["db"], tuple(read["keys"])] = read
        return list(latest.values())

    def _rows_now(self, read):
        return self.world.select(self.world.at(read["db"]), read["keys"] or None)

    def _hash_now(self, read):
        return digest(self._rows_now(read))

    def _ready(self, run, source):
        if isinstance(source, str):
            task = self.tasks.get(source)
            if task is not None and not task.done():
                return None
            state = self.state(source)
            if state != "done":
                return {"kind": state, "handle": source, "error": self.runs[self.comps[source].current].error}
            got = self.query(run, f"out/{source}")
            return {"kind": "done", "handle": source, "rows": got["rows"], "version": got["version"]}
        if "db" in source:
            db, keys, after = source["db"], source.get("keys"), source.get("after", 0)
            version = self.world.at(db)
            if version is None:
                return None
            now = self.world.select(version, keys)
            was = self.world.select(self.world.version(db, after), keys) if after else \
                ({k: None for k in keys} if keys else {})
            if digest(now) == digest(was):
                return None
            got = self.query(run, db, keys)
            return {"kind": "change", "db": db, "version": got["version"], "rows": got["rows"], "was": was}
        if "inbox" in source:
            version = self.world.at(f"inbox/{run.key}")
            fresh = sorted(((int(k), m) for k, m in (version["rows"] if version else {}).items()
                            if int(k) > source["inbox"]))
            if not fresh:
                return None
            self._recorded(run, f"inbox/{run.key}", None, version, version["rows"], volatile=True)
            return {"kind": "inbox", "messages": fresh}
        if "progress" in source:
            version = self.world.at(f"out/{source['progress']}")
            if version is None or version["number"] <= source.get("after", 0):
                return None
            got = self.query(run, f"out/{source['progress']}")
            return {"kind": "progress", "handle": source["progress"], "version": got["version"],
                    "rows": got["rows"]}
        raise Rejected(f"Unknown wait source {source!r}")

    def _describe(self, source):
        if isinstance(source, str):
            return f"done:{source[:6]}"
        if "db" in source:
            return f"change:{source['db']}"
        if "inbox" in source:
            return "inbox"
        return f"progress:{source['progress'][:6]}"

    def _reaches(self, start, target):
        pending, seen = [start], set()
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if node not in seen:
                seen.add(node)
                pending.extend(self.waiting.get(node, ()))
        return False

    def _is_ancestor(self, ancestor, key):
        owner = self.comps[key].owner
        while owner not in ("human", None):
            if owner == ancestor:
                return True
            owner = self.comps[owner].owner
        return False

    def _release(self, holder, key):
        comp = self.comps.get(key)
        if comp is None:
            return
        comp.holders.discard(holder)
        task = self.tasks.get(key)
        if not comp.holders and task is not None and not task.done():
            task.cancel()
            self.log("kernel", "cancel", handle=key, reason="no holders left")

    def _agents_view(self, run):
        rows = {}
        for key, comp in self.comps.items():
            if key != run.key and self._is_ancestor(run.key, key):
                current = self.runs.get(comp.current)
                rows[key] = {"task": comp.task, "state": self.state(key), "owner": comp.owner,
                             "revision": comp.revisions,
                             "budget_left": current.budget if current else comp.budget}
        return rows


class Ax:
    """The verbs as one run sees them. Sugar (result, wait_all, tell) is plain code over them."""

    def __init__(self, kernel, run, comp):
        self.k, self.run, self.comp = kernel, run, comp

    key = property(lambda self: self.comp.key)
    out = property(lambda self: f"out/{self.comp.key}")
    inputs = property(lambda self: self.comp.inputs)
    delta = property(lambda self: self.run.delta)

    def spawn(self, task, inputs=None, skill=None, model="default", share=True, budget=None):
        return self.k.spawn(self.run, task, inputs or {}, skill, model, share, budget)

    def query(self, db, keys=None, **options):
        return self.k.query(self.run, db, keys, **options)

    def commit(self, db, changes, **options):
        return self.k.commit(self.run, db, changes, **options)

    async def wait(self, sources, timeout=None):
        return await self.k.wait(self.run, sources, timeout)

    def close(self, handle):
        self.k.close(self.run, handle)

    # sugar ---------------------------------------------------------------------------------
    def tell(self, handle, message):
        return self.k._tell(self.run, handle, dict(message))

    async def result(self, handle):
        event = await self.wait([handle])
        if event["kind"] != "done":
            raise Rejected(f"{handle[:6]} ended {event['kind']}")
        return event["rows"]

    async def wait_all(self, handles):
        return [await self.result(h) for h in handles]
