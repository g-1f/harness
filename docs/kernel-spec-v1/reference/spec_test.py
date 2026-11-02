"""Check the five-verb kernel against the five design requirements.

Agent programs are Python coroutines standing in for model-written code. Where a program
stands in for a model *judgment* (is this the same question?), the comment says so.
"""

import asyncio
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = os.environ.get("HARNESS", "/home/claude/harness")
SKILLS = Path(os.environ.get("SKILLS", HERE / "skills" if (HERE / "skills").exists() else HERE.parent / "graphdemo" / "skills"))
sys.path.insert(0, HARNESS)
sys.path.insert(0, str(HERE))

from kernel import Kernel, Rejected  # noqa: E402

P = {}


def program(task, *skills):
    def register(fn):
        for skill in skills or (None,):
            P[skill, task] = fn
        if skills:
            P[None, task] = fn  # the same work runs as a free call without a skill graph
        return fn
    return register


# --- The sample skill graph: index -> a, b; a -> d, e; b -> c, d; d -> e -------------------

def sk(ax, name):
    return name if ax.comp.skill else None  # follow skills when the run has them


@program("Review the rates-sensitive theses", "index")
async def p_index(ax):
    ha = ax.spawn("Form the macro view", skill=sk(ax, "a"))
    hb = ax.spawn("Form the bank view", skill=sk(ax, "b"))
    await ax.wait_all([ha, hb])
    m = ax.query("thesis/macro", ["stance"])["rows"]
    k = ax.query("thesis/bank", ["nim_trough"])["rows"]
    ax.commit(ax.out, {"review": f"macro {m['stance']}, bank trough {k['nim_trough']}"})


@program("Form the macro view", "a")
async def p_a(ax):
    hd = ax.spawn("Update the rates path", skill=sk(ax, "d"))
    he = ax.spawn("Read the latest inflation print", skill=sk(ax, "e"))
    await ax.wait_all([hd, he])
    i = ax.query("thesis/inflation", ["core_cpi"])["rows"]
    r = ax.query("thesis/rates", ["term_premium"])["rows"]
    stance = "hawkish" if i["core_cpi"] >= 0.4 else "neutral"
    ax.commit("thesis/macro", {"stance": stance, "term_premium": r["term_premium"]})
    ax.commit(ax.out, {"stance": stance})


@program("Form the bank view", "b")
async def p_b(ax):
    hc = ax.spawn("Extract deposit beta", skill=sk(ax, "c"))
    hd = ax.spawn("Update the rates path", skill=sk(ax, "d"))
    await ax.wait_all([hc, hd])
    f = ax.query("thesis/filings", ["deposit_beta"])["rows"]
    r = ax.query("thesis/rates", ["cut_path"])["rows"]
    trough = "Q1" if r["cut_path"] >= 2 else "Q2"
    ax.commit("thesis/bank", {"nim_trough": trough, "deposit_beta": f["deposit_beta"]})
    ax.commit(ax.out, {"nim_trough": trough})


@program("Extract deposit beta", "c")
async def p_c(ax):
    await asyncio.sleep(0.04)
    ax.commit("thesis/filings", {"deposit_beta": 0.42})
    ax.commit(ax.out, {"deposit_beta": 0.42})


@program("Update the rates path", "d")
async def p_d(ax):
    he = ax.spawn("Read the latest inflation print", skill=sk(ax, "e"))
    await ax.result(he)
    i = ax.query("thesis/inflation", ["core_cpi"])["rows"]
    cut = 1 if i["core_cpi"] >= 0.4 else 2
    ax.commit("thesis/rates", {"cut_path": cut, "term_premium": 0.5})
    ax.commit(ax.out, {"cut_path": cut})


@program("Read the latest inflation print", "e")
async def p_e(ax):
    await asyncio.sleep(0.06)
    core = ax.query("src/cpi", ["core_cpi"])["rows"]["core_cpi"]
    ax.commit("thesis/inflation", {"core_cpi": core})
    ax.commit(ax.out, {"core_cpi": core})


# --- Async-first building blocks --------------------------------------------------------------

@program("Slow leaf")
async def p_slow(ax):
    await asyncio.sleep(ax.inputs.get("ms", 100) / 1000)
    ax.commit(ax.out, {"i": ax.inputs.get("i"), "at": ax.k.now()})


@program("Plan while children work")
async def p_busy(ax):
    hs = [ax.spawn("Slow leaf", {"ms": 300, "i": i}) for i in range(3)]
    ax.commit(ax.out, {"plan": "three leaves started", "plan_at": ax.k.now()})
    await ax.wait_all(hs)
    ax.commit(ax.out, {"done_at": ax.k.now()})


@program("Sum this list")
async def p_sum(ax):
    xs, k = ax.inputs["xs"], ax.inputs["k"]  # k is the parent's own decomposition criterion
    if len(xs) <= k:
        await asyncio.sleep(0.05)
        ax.commit(ax.out, {"sum": sum(xs)})
        return
    mid = len(xs) // 2
    parts = await ax.wait_all([ax.spawn("Sum this list", {"xs": xs[:mid], "k": k}),
                               ax.spawn("Sum this list", {"xs": xs[mid:], "k": k})])
    ax.commit(ax.out, {"sum": parts[0]["sum"] + parts[1]["sum"]})


@program("Multiplex waits")
async def p_mux(ax):
    ha = ax.spawn("Slow leaf", {"ms": 100, "i": "A"})
    hb = ax.spawn("Slow leaf", {"ms": 250, "i": "B"})
    seen = []
    e = await ax.wait([ha, hb], timeout=0.03)
    seen.append(e["kind"])
    e = await ax.wait([ha, hb])
    seen.append(f"{e['kind']}:{e['rows']['i']}")
    e = await ax.wait([hb])
    seen.append(f"{e['kind']}:{e['rows']['i']}")
    ax.commit(ax.out, {"seen": seen})


@program("Budgeted parent")
async def p_budget_parent(ax):
    hc = ax.spawn("Budgeted child", budget=2)
    await ax.wait([hc])
    ax.commit(ax.out, {"view": ax.query("sys/agents")["rows"][hc]})


@program("Budgeted child")
async def p_budget_child(ax):
    made, refused = [], None
    for i in range(3):
        try:
            made.append(ax.spawn("Slow leaf", {"ms": 10, "i": f"b{i}"}))
        except Rejected as error:
            refused = str(error)
    await ax.wait_all(made)
    ax.commit(ax.out, {"made": len(made), "refused": refused})


# --- Steering -------------------------------------------------------------------------------

ITEMS = [{"name": n, "sector": s} for n, s in [
    ("Alder", "bank"), ("Birch", "tech"), ("Cedar", "bank"), ("Dogwood", "energy"),
    ("Elm", "bank"), ("Fir", "tech"), ("Gum", "bank"), ("Hazel", "energy")]]


@program("Steerable root")
async def p_root(ax):
    hw = ax.spawn("Screen the list", {"items": ITEMS}, share=False)
    hs = ax.spawn("Slow leaf", {"ms": 600, "i": "background"}, share=False)
    after, worker_done = 0, False
    while not worker_done:
        event = await ax.wait([hw, {"inbox": after}])  # wakes for people and for children
        if event["kind"] != "inbox":
            worker_done = True
            continue
        for seq, msg in event["messages"]:
            after = seq
            if msg["text"] == "status?":
                running = [v["task"] for v in ax.query("sys/agents")["rows"].values() if v["state"] == "running"]
                ax.commit(ax.out, {f"reply{seq}": f"{len(running)} running", f"reply{seq}_at": ax.k.now()})
            elif msg["text"].startswith("steer:"):
                ax.tell(hw, {"text": msg["text"][6:], "cause": f"inbox/{ax.key}#{seq}"})
    await ax.result(hs)
    ax.commit(ax.out, {"finished_at": ax.k.now()})


@program("Screen the list")
async def p_screen(ax):
    focus, after, kept = None, 0, []
    for item in ax.inputs["items"]:
        event = await ax.wait([{"inbox": after}], timeout=0)  # a turn boundary picks up steering
        if event["kind"] == "inbox":
            for seq, msg in event["messages"]:
                after, focus = seq, msg["text"]
        await asyncio.sleep(0.05)
        if focus is None or item["sector"] == focus:
            kept.append(f"{item['name']}{'' if focus is None else '*'}")
    ax.commit(ax.out, {"kept": kept, "done_at": ax.k.now()})


@program("Hold shared work")
async def p_holder(ax):
    shared = ax.spawn("Slow leaf", {"ms": 300, "i": "shared"})
    rows = await ax.result(shared)
    ax.commit(ax.out, {"got": rows["i"]})


@program("Hold private work")
async def p_private(ax):
    mine = ax.spawn("Slow leaf", {"ms": 300, "i": "private"}, share=False)
    ax.commit(ax.out, {"child": mine})
    await ax.result(mine)


@program("Close one holder")
async def p_closer(ax):
    ha = ax.spawn("Hold shared work", {"who": "A"})
    hb = ax.spawn("Hold shared work", {"who": "B"})
    hd = ax.spawn("Hold private work")
    await asyncio.sleep(0.05)
    ax.close(ha)
    ax.close(hd)
    rows = await ax.result(hb)
    await asyncio.sleep(0.02)
    ax.commit(ax.out, {"b_got": rows["got"], "a": ax.k.state(ha), "d": ax.k.state(hd)})


# --- Graph operations -----------------------------------------------------------------------

@program("Ask on the board")
async def p_asker(ax):
    q = ax.inputs["question"]
    mine = "q:" + ax.key[:6]
    ax.commit("board/questions", {mine: {"question": q}}, if_absent=[mine])
    similar = ax.query("board/questions", similar=q)["rows"]
    my_tx = similar.get(mine, {}).get("tx")
    # Stand-in for the model's judgment: an earlier, similar enough open question is mine too.
    earlier = [k for k, v in similar.items() if k != mine and v["score"] >= 0.25 and v["tx"] < my_tx]
    if earlier:
        owner = earlier[0]
        got = ax.query("board/answers", [owner])
        answer = got["rows"].get(owner)
        if answer is None:
            answer = (await ax.wait([{"db": "board/answers", "keys": [owner], "after": got["version"]}]))["rows"][owner]
        ax.commit(ax.out, {"answer": answer, "via": "watched " + owner})
        return
    rows = await ax.result(ax.spawn("Slow leaf", {"ms": 200, "i": q}))
    ax.commit("board/answers", {mine: "2 cuts"})
    ax.commit(ax.out, {"answer": "2 cuts", "via": "ran it", "leaf": rows["i"]})


@program("Two askers at once")
async def p_two(ax):
    ha = ax.spawn("Ask on the board", {"question": "Forecast the Fed cut path for the next 12 months"})
    hb = ax.spawn("Ask on the board", {"question": "What is the Fed cut path over the coming year"})
    a, b = await ax.wait_all([ha, hb])
    ax.commit(ax.out, {"a": a, "b": b})


@program("Estimate and converge")
async def p_converge(ax):
    me, other, est = ax.inputs["me"], ax.inputs["other"], ax.inputs["est"]
    ax.commit("debate/est", {f"{me}:1": est})  # commit independently, before reading anything
    got = ax.query("debate/est", [f"{other}:1"])
    seen = got["rows"][f"{other}:1"]
    if seen is None:
        seen = (await ax.wait([{"db": "debate/est", "keys": [f"{other}:1"], "after": got["version"]}]))["rows"][f"{other}:1"]
    ax.commit("debate/est", {f"{me}:2": (est + seen) / 2})
    ax.commit(ax.out, {"saw": seen, "revised": (est + seen) / 2})


@program("Converge two estimates")
async def p_conv_root(ax):
    a, b = await ax.wait_all([ax.spawn("Estimate and converge", {"me": "a", "other": "b", "est": 3.0}),
                              ax.spawn("Estimate and converge", {"me": "b", "other": "a", "est": 5.0})])
    ax.commit(ax.out, {"a": a, "b": b})


@program("Stream partial results")
async def p_producer(ax):
    for n in range(1, 4):
        await asyncio.sleep(0.1)
        ax.commit(ax.out, {"partial": n, f"at{n}": ax.k.now()})
    await asyncio.sleep(0.1)


@program("Consume a sibling's stream")
async def p_consumer(ax):
    producer, after, seen = ax.inputs["producer"], 0, []
    while True:
        event = await ax.wait([{"progress": producer, "after": after}, producer])
        if event["kind"] == "progress":
            after = event["version"]
            seen.append([event["rows"]["partial"], ax.k.now()])
        else:
            break
    ax.commit(ax.out, {"seen": seen})


@program("Wire two siblings")
async def p_wire(ax):
    hp = ax.spawn("Stream partial results", share=False)
    hc = ax.spawn("Consume a sibling's stream", {"producer": hp}, share=False)  # the handle is the grant
    seen = (await ax.result(hc))["seen"]
    await ax.result(hp)
    ax.commit(ax.out, {"seen": seen, "producer_done_at": ax.k.now()})


async def _live(ax, mine, theirs, compute, start):
    value, wakes = None, 0
    for _ in range(20):
        got = ax.query(theirs[0], [theirs[1]])
        other = got["rows"][theirs[1]]
        value = compute(start if other is None else other)
        ax.commit(mine[0], {mine[1]: value})
        event = await ax.wait([{"db": theirs[0], "keys": [theirs[1]], "after": got["version"]}], timeout=0.3)
        if event["kind"] == "timeout":
            break
        wakes += 1
    ax.commit(ax.out, {"value": value, "wakes": wakes})


@program("Rates thesis, live")
async def p_rates_live(ax):
    await _live(ax, ("thesis/rates_live", "cut_path"), ("thesis/bank_live", "stress"),
                lambda s: round(2 + 2 * s, 2), 0.0)


@program("Bank thesis, live")
async def p_bank_live(ax):
    await _live(ax, ("thesis/bank_live", "stress"), ("thesis/rates_live", "cut_path"),
                lambda c: round(max(0.0, 0.5 - 0.1 * c), 2), 2.0)


@program("Feedback loop")
async def p_loop(ax):
    r, b = await ax.wait_all([ax.spawn("Rates thesis, live"), ax.spawn("Bank thesis, live")])
    ax.commit(ax.out, {"rates": r, "bank": b})


@program("Wait on my peer")
async def p_peer(ax):
    ax.commit("board/peers", {ax.inputs["me"]: ax.key})
    while True:
        other = ax.query("board/peers", [ax.inputs["other"]])["rows"][ax.inputs["other"]]
        if other:
            break
        await asyncio.sleep(0.01)
    try:
        await ax.wait([other], timeout=0.5)
        outcome = "waited"
    except Rejected as error:
        outcome = str(error)
    ax.commit(ax.out, {"outcome": outcome})


@program("Mutual completion waits")
async def p_mutual(ax):
    a, b = await ax.wait_all([ax.spawn("Wait on my peer", {"me": "a", "other": "b"}),
                              ax.spawn("Wait on my peer", {"me": "b", "other": "a"})])
    ax.commit(ax.out, {"a": a["outcome"], "b": b["outcome"]})


@program("Red-team a trajectory")
async def p_redteam(ax):
    rows = ax.query("sys/trajectory", [ax.inputs["target"]])["rows"].values()
    verbs = Counter(r["verb"] for r in rows)
    ax.commit(ax.out, {"queries": verbs["query"], "commits": verbs["commit"], "spawns": verbs["spawn"]})


JS_SOURCE = """
const h = await spawn({task: 'Slow leaf', inputs: {ms: 50, i: 'from js'}});
const other = await spawn({task: 'Slow leaf', inputs: {ms: 80, i: 'second'}});
const first = await wait({sources: [h, other]});
const cpi = await query({db: 'src/cpi', keys: ['core_cpi']});
const extra = await spawn({task: 'Slow leaf', inputs: {ms: 500, i: 'extra'}, share: false});
await close(extra);
await commit({db: OUT, changes: {first: first.rows.i, cpi: cpi.rows.core_cpi, closed: extra}});
await wait({sources: [other]});
"""


@program("Run a JavaScript program")
async def p_js(ax):
    from quickjs_rs import Runtime as JSRuntime

    async def js_spawn(a):
        return ax.spawn(a["task"], a.get("inputs"), share=a.get("share", True))

    async def js_wait(a):
        return await ax.wait(a["sources"], a.get("timeout"))

    async def js_query(a):
        return ax.query(a["db"], a.get("keys"))

    async def js_commit(a):
        return ax.commit(a["db"], a["changes"])

    async def js_close(handle):
        ax.close(handle)
        return {"closed": True}

    with JSRuntime(memory_limit=32 * 1024 * 1024) as js:
        with js.new_context(timeout=10) as ctx:
            for name, fn in {"spawn": js_spawn, "wait": js_wait, "query": js_query, "commit": js_commit, "close": js_close}.items():
                ctx.register(name, fn)
            await ctx.eval_async("const OUT = " + json.dumps(ax.out) + ";\n" + JS_SOURCE)


# --- Checks ----------------------------------------------------------------------------------

RESULTS = []


def check(req, name, ok, detail=""):
    RESULTS.append((req, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  [{req}] {name}" + (f"  ({detail})" if detail else ""))


def load_skills():
    from harness import Registry
    registry = Registry.load(SKILLS)
    return {n: {"description": s.description, "text": s.instructions, "links": list(s.links)}
            for n, s in registry.nodes.items()}


def runs_since(k, mark):
    return [r for r in k.traj[mark:] if r["verb"] == "run_start"]


def task_of(k, key):
    return k.comps[key].task


async def sample(skills):
    k = Kernel(P, skills)
    k.source_commit("src/cpi", {"core_cpi": 0.3}, available_at=100)
    root = k.start("Review the rates-sensitive theses", skill="index" if skills else None)
    out = await k.result(root)
    return k, root, out


async def main():
    skills = load_skills()
    stats = {}

    # R1 - skill graph compatible, and runs without one -------------------------------------
    k, root, out = await sample(skills)
    starts = Counter(task_of(k, r["key"]) for r in k.traj if r["verb"] == "run_start")
    disp = Counter((task_of(k, r["handle"]), r["disposition"]) for r in k.traj if r["verb"] == "spawn")
    check("R1", "the sample skill graph runs on the five verbs; shared d and e each run once",
          starts["Update the rates path"] == 1 and starts["Read the latest inflation print"] == 1
          and disp[("Update the rates path", "joined")] == 1 and disp[("Read the latest inflation print", "joined")] == 1,
          f"{sum(starts.values())} runs for 6 skills; review: {out['review']}")
    skill_reads = Counter(r["keys"][0] for r in (x for run in k.runs.values() for x in run.reads)
                          if r["db"] == "lib/skills")
    check("R1", "each skill enters a run as a recorded read of the library", sorted(skill_reads) == list("abcde") + ["index"],
          f"skill reads {dict(skill_reads)}")
    mark = len(k.traj)
    k.edit_skill("c", {**skills["c"], "text": skills["c"]["text"] + "\nPrefer the latest 10-Q."})
    await k.refresh(root)
    rerun = [task_of(k, r["key"]) for r in runs_since(k, mark)]
    check("R1", "editing one skill re-runs only the calls that read it",
          rerun == ["Extract deposit beta"], f"re-ran {rerun}; the old kernel re-identifies every call on any edit")
    k2, root2, out2 = await sample(None)
    check("R1", "the same work runs as free calls with no skill library", out2 == out and "lib/skills" not in k2.world.dbs,
          f"review: {out2['review']}")

    # R2 - async background first, recursive by the parent's criterion ---------------------
    k = Kernel(P)
    t0 = time.monotonic()
    out = await k.result(k.start("Plan while children work"))
    wall = time.monotonic() - t0
    leaf_done = min(c["rows"]["at"] for c in
                    ({"rows": k.out_rows(key)} for key, comp in k.comps.items() if comp.task == "Slow leaf"))
    check("R2", "spawn never blocks: the parent keeps working while children run",
          out["plan_at"] < leaf_done and wall < 0.45,
          f"parent wrote its plan at {out['plan_at']:.3f}s, first child finished {leaf_done:.3f}s, total {wall:.2f}s for 3x0.30s")
    k = Kernel(P)
    t0 = time.monotonic()
    out = await k.result(k.start("Sum this list", {"xs": list(range(1, 17)), "k": 2}))
    wall = time.monotonic() - t0
    leaves = [r for r in k.traj if r["verb"] == "run_start"]
    check("R2", "recursion follows the parent's own criterion; all leaves run at once",
          out["sum"] == 136 and len(leaves) == 15 and wall < 0.4,
          f"15 runs (8 leaves of <=2 items), sum {out['sum']}, {wall:.2f}s against 0.40s if leaves ran in series")
    k = Kernel(P)
    out = await k.result(k.start("Multiplex waits"))
    check("R2", "one wait covers many sources; a timeout leaves nothing stuck",
          out["seen"] == ["timeout", "done:A", "done:B"], f"{out['seen']}")
    k = Kernel(P)
    out = await k.result(k.start("Budgeted parent"))
    child = next(key for key, c in k.comps.items() if c.task == "Budgeted child")
    check("R2", "budgets flow down the tree and the parent can see them",
          k.out_rows(child)["made"] == 2 and "budget" in k.out_rows(child)["refused"] and out["view"]["budget_left"] == 0,
          f"child made {k.out_rows(child)['made']}, third spawn: {k.out_rows(child)['refused']}; parent sees budget_left={out['view']['budget_left']}")

    # R3 - always talk to the root, steer any subagent -------------------------------------
    k = Kernel(P)
    root = k.start("Steerable root")

    async def person():
        await asyncio.sleep(0.10)
        k.human_tell(root, "status?")
        await asyncio.sleep(0.08)
        k.human_tell(root, "steer:bank")

    await asyncio.gather(person(), k.result(root))
    out = k.out_rows(root)
    worker = next(key for key, c in k.comps.items() if c.task == "Screen the list")
    w = k.out_rows(worker)
    check("R3", "a person can talk to the root while its children run",
          out["reply1"].endswith("running") and out["reply1_at"] < w["done_at"],
          f"reply '{out['reply1']}' at {out['reply1_at']:.2f}s; worker finished {w['done_at']:.2f}s")
    before = [x for x in w["kept"] if not x.endswith("*")]
    after = [x for x in w["kept"] if x.endswith("*")]
    names = {i["name"]: i["sector"] for i in ITEMS}
    check("R3", "the root steers a running subagent; it changes course at its next turn boundary",
          before and after and all(names[x[:-1]] == "bank" for x in after) and any(names[x] != "bank" for x in before),
          f"kept before steering {before}; after (bank only) {after}")
    tells = [r for r in k.traj if r["verb"] == "tell"]
    check("R3", "the steering chain is in the trajectory: person -> root -> worker, with its cause",
          [r["key"] for r in tells][-1] == root and tells[-1]["cause"] == f"inbox/{root}#2",
          f"{[(r['key'][:6], r['handle'][:6], r.get('cause')) for r in tells]}")
    k = Kernel(P)
    out = await k.result(k.start("Close one holder"))
    shared = next(key for key, c in k.comps.items() if c.task == "Slow leaf" and c.inputs.get("i") == "shared")
    private = next(key for key, c in k.comps.items() if c.task == "Slow leaf" and c.inputs.get("i") == "private")
    check("R3", "closing stops a branch and everything only it held; work others hold survives",
          out["a"] == "cancelled" and out["d"] == "cancelled" and k.state(private) == "cancelled"
          and k.state(shared) == "done" and out["b_got"] == "shared",
          f"A {out['a']}, its shared leaf {k.state(shared)} (B still held it), D {out['d']} and its private leaf {k.state(private)}")

    # R4 - graph operations between subagents ------------------------------------------------
    k = Kernel(P)
    out = await k.result(k.start("Two askers at once"))
    leaf_runs = sum(1 for r in k.traj if r["verb"] == "run_start" and task_of(k, r["key"]) == "Slow leaf")
    check("R4", "shared work by meaning, both starting at once: the later claim yields to the earlier one",
          leaf_runs == 1 and out["a"]["answer"] == out["b"]["answer"],
          f"1 run; vias: {out['a']['via']} / {out['b']['via']} (the similarity judgment is word overlap standing in for the model)")
    k = Kernel(P)
    out = await k.result(k.start("Converge two estimates"))
    check("R4", "peers converge through data: commit, read the other, revise",
          out["a"]["saw"] == 5.0 and out["b"]["saw"] == 3.0 and out["a"]["revised"] == out["b"]["revised"] == 4.0,
          f"a saw {out['a']['saw']}, b saw {out['b']['saw']}, both revised to {out['a']['revised']}")
    k = Kernel(P)
    out = await k.result(k.start("Wire two siblings"))
    first_seen = out["seen"][0][1]
    check("R4", "a sibling consumes another sibling's stream directly, before it finishes",
          [s[0] for s in out["seen"]] == [1, 2, 3] and first_seen < out["producer_done_at"] - 0.2,
          f"consumer saw partial 1 at {first_seen:.2f}s; producer finished {out['producer_done_at']:.2f}s; no parent relay")
    k = Kernel(P)
    out = await k.result(k.start("Feedback loop"))
    wakes = out["rates"]["wakes"] + out["bank"]["wakes"]
    check("R4", "a feedback loop across two theses settles at a fixed point, with no deadlock",
          out["rates"]["value"] == 2.5 and out["bank"]["value"] == 0.25 and wakes <= 10,
          f"cut path {out['rates']['value']}, bank stress {out['bank']['value']}, {wakes} wakes in total")
    k = Kernel(P)
    out = await k.result(k.start("Mutual completion waits"))
    outcomes = sorted([out["a"], out["b"]])
    check("R4", "waiting for each other's completion is still refused as a cycle",
          sum("cycle" in o for o in outcomes) == 1, f"{outcomes}")

    # R5 - trajectories and deltas -------------------------------------------------------------
    k, root, out = await sample(skills)
    a_key = next(key for key, c in k.comps.items() if c.task == "Form the macro view")
    rt = await k.result(k.start("Red-team a trajectory", {"target": a_key}))
    own = Counter(r["verb"] for r in k.traj if r["key"] == a_key)
    check("R5", "the trajectory is a database any granted agent can query",
          rt["queries"] == own["query"] and rt["commits"] == own["commit"] and rt["spawns"] == own["spawn"],
          f"red team counted {rt} in a's trajectory, matching the kernel's own log")
    fork = k.fork()
    mark = len(k.traj)
    k.source_commit("src/cpi", {"core_cpi": 0.4}, available_at=200)
    new = await k.refresh(root)
    big = [task_of(k, r["key"]) for r in runs_since(k, mark)]
    check("R5", "a CPI release re-runs only computations whose reads changed",
          len(big) == 5 and "Extract deposit beta" not in big and new["review"] == "macro hawkish, bank trough Q2",
          f"{len(big)} of 6 re-ran, filings reused; review now: {new['review']}")
    why = k.explain(a_key)
    moved = {d["db"]: (d["was"], d["now"]) for d in why["because"]}
    check("R5", "every output change explains itself through the reads that moved",
          moved.get("thesis/inflation") == ({"core_cpi": 0.3}, {"core_cpi": 0.4}) and why["output_diff"] == {"stance": ["neutral", "hawkish"]},
          f"macro changed {why['output_diff']} because {sorted(moved)}")
    k3, root3, _ = await sample(skills)
    mark = len(k3.traj)
    k3.source_commit("src/cpi", {"core_cpi": 0.32}, available_at=200)
    small_out = await k3.refresh(root3)
    small = [task_of(k3, r["key"]) for r in runs_since(k3, mark)]
    check("R5", "a small print stops early: once outputs don't change, nothing downstream re-runs",
          sorted(small) == sorted(["Read the latest inflation print", "Update the rates path", "Form the macro view"])
          and small_out["review"] == "macro neutral, bank trough Q1",
          f"re-ran {small}; bank and the review were reused")
    fmark = len(fork.traj)
    fork.source_commit("src/cpi", {"core_cpi": 0.6}, available_at=300, who="scenario")
    scen = await fork.refresh(root)
    base_hist = [v["rows"]["core_cpi"] for v in k.world.history("src/cpi")]
    fork_hist = [v["rows"]["core_cpi"] for v in fork.world.history("src/cpi")]
    fork_rates = fork.world.at("thesis/rates")["rows"]["cut_path"]
    check("R5", "a scenario fork runs the affected graph under a hypothetical print; the real world is untouched",
          scen["review"] == "macro hawkish, bank trough Q2" and len(runs_since(fork, fmark)) == 5
          and base_hist == [0.3, 0.4] and fork_hist == [0.3, 0.6],
          f"fork CPI history {fork_hist}, rates cut path {fork_rates}; base CPI history {base_hist}")
    then = k.query(None, "src/cpi", ["core_cpi"], available_by=150)["rows"]["core_cpi"]
    later = k.query(None, "src/cpi", ["core_cpi"], available_by=250)["rows"]["core_cpi"]
    check("R5", "reads can be limited to what was available at a time (backtests stay honest)",
          then == 0.3 and later == 0.4, f"available by t=150: {then}; by t=250: {later}")
    stats["refresh"] = {"big": big, "small": small}

    # PTC bridge ---------------------------------------------------------------------------------
    k = Kernel(P)
    k.source_commit("src/cpi", {"core_cpi": 0.3})
    out = await k.result(k.start("Run a JavaScript program"))
    await asyncio.sleep(0.01)
    closed = k.state(out.get("closed", "")) if out.get("closed") in k.comps else None
    check("PTC", "all five verbs run unchanged from QuickJS",
          out.get("first") == "from js" and out.get("cpi") == 0.3 and closed == "cancelled",
          f"first done: {out.get('first')}, cpi {out.get('cpi')}, closed child {closed}")

    by = Counter(req for req, ok in RESULTS if ok)
    total = Counter(req for req, _ in RESULTS)
    print("\n" + ", ".join(f"{r} {by[r]}/{total[r]}" for r in total))
    print(f"{sum(by.values())}/{len(RESULTS)} checks behaved as stated")
    (HERE / "spec_results.json").write_text(json.dumps(
        {"results": [{"req": r, "ok": ok} for r, ok in RESULTS], **stats}, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
