"""Export actual execution DAGs, call dispositions, PTC and observations."""

import asyncio
import json
from collections import Counter

from demo import run_demo
from examples.application import ROOT, prompt_for
from examples.fixtures import fixture
from examples.scripted_model import HELPERS
from harness import Runtime

INVESTIGATION = {"root", "a", "b", "c", "d", "f", "g", "h", "i", "k", "l", "delta_check"}
COMPOSITE = {"root", "a", "b", "c", "d", "f", "g", "h"}


def render(case: str, runtime: Runtime, receipt: dict) -> str:
    events = runtime.store.events()
    admissions = [event for event in events if event["type"] == "admitted"]
    calls = [event for event in events if event["type"] == "call_acquired"]
    ids = {event["frame"]: f"E{index}" for index, event in enumerate(admissions, 1)}
    nodes = {event["frame"]: event["node"] for event in admissions}
    aliases = {frame: f"{ids[frame]}:{node}" for frame, node in nodes.items()}
    records = {}
    for event in events:
        if event["type"] == "checkpoint_published":
            aliases[event["ref"]] = aliases[event["operation"]] + f"/checkpoint:{event['cursor']}"
        if event["type"] in ("accepted", "needs_review"):
            record = runtime.store.get(event["ref"])
            records[event["frame"]] = record
            aliases[event["ref"]] = aliases[event["frame"]] + "/result"
            for ref in record["input_refs"]:
                target = runtime.store.get(ref)
                if target["status"] == "draft":
                    aliases[ref] = aliases[target["frame"]] + "/draft"

    def normalize(value: str) -> str:
        for identifier, label in aliases.items():
            value = value.replace(identifier, label)
        return value

    def label(frame: str | None) -> str:
        return aliases[frame] if frame else "launcher"

    if runtime.operations.waits or any(op.waiters for op in runtime.operations.operations.values()):
        raise ValueError("Cannot document an unfinished session as fully released")
    report = runtime.store.get(receipt["ref"])["content"]
    counts = Counter(call["disposition"] for call in calls)
    lines = [
        f"# Scenario {case.upper()}: prompt and executed graph",
        "",
        "**Offline scripted fixture.** These are actual Deep Agents/QuickJS calls and "
        "supervisor events. PTC fragments are prewritten and selected from observed results; "
        "this is not evidence of live-model code generation.",
        "",
        f"Reproduce: `python demo.py --offline --case {case} --trace outputs/scenario_{case}.json`.",
        "",
        "Regenerate both documents: `python -m examples.export_trajectories`.",
        "",
        f"Outcome: `{report['outcome']}`. **{runtime.ledger.calls} calls, "
        f"{runtime.ledger.frames} executions**, {counts['joined']} in-flight joins, "
        f"{counts['reused']} completed-result reuses. "
        f"{runtime.ledger.model_calls} scripted model operations; zero model API calls. "
        "All acquired leases were released; no active wait edges remain.",
        "",
        "## Prompt",
        "",
        f"Source: [scenario_{case}.md](../prompts/scenario_{case}.md).",
        "",
        prompt_for(case),
        "",
        "Bound synthetic inputs:",
        "",
        "```json",
        json.dumps(fixture(case), indent=2),
        "```",
        "",
        "The [root procedure](../../skills/root/SKILL.md) and shared "
        "[execution prompt](../../harness/runners/node_agent.md) also enter the initial context. "
        "The fixture supports these documented scenarios, not arbitrary prompt paraphrases.",
        "",
        "## Executed investigation graph",
        "",
        "Each vertex is one actual execution. Edges come from `call_acquired` events, "
        "including joins and completed-result reuse. First arrival can be either parallel "
        "branch. Audit/synthesis vertices are omitted from this diagram and included in "
        "the complete tables below.",
        "",
        "```mermaid",
        "flowchart TD",
    ]
    included = {frame for frame, node in nodes.items() if node in INVESTIGATION}
    for frame in ids:
        if frame in included:
            display = (
                "b focus"
                if nodes[frame] == "b"
                and next(e for e in admissions if e["frame"] == frame)["task"]
                == "Assess capacity from snapshot checkpoint"
                else nodes[frame]
            )
            lines.append(f'    {ids[frame]}["{display} ({ids[frame]})"]')
    edges = set()
    for call in calls:
        source, target = call["caller"], call["operation"]
        edge = (source, target, call["disposition"])
        if source in included and target in included and edge not in edges:
            edges.add(edge)
            lines.append(f"    {ids[source]} -->|{call['disposition']}| {ids[target]}")
    lines += [
        "```",
        "",
        "## Executions",
        "",
        "Each row has one context and one produced result. `origin` in the raw trace "
        "records who first caused creation; it does not give that caller exclusive ownership.",
        "",
        "| Execution | Task | Executor | Input refs |",
        "| --- | --- | --- | --- |",
    ]
    for event in admissions:
        task = "Prompt above" if event["origin"] is None else normalize(event["task"])
        task = " ".join(task.split()).replace("|", "\\|")
        refs = ", ".join(f"`{normalize(ref)}`" for ref in event["refs"]) or "None"
        lines.append(f"| `{label(event['frame'])}` | {task} | `{event['executor']}` | {refs} |")
    lines += [
        "",
        "## Calls and ownership",
        "",
        "Every successful acquisition has its own lease. Multiple rows can target "
        "the same execution. A pending observation adds a temporary wait edge. The "
        "runtime releases each lease on completion, close, error or cancellation; "
        "callers never lock/unlock a skill themselves.",
        "",
        "| Caller | Target execution | Caller key | Dispatch | Reuse policy |",
        "| --- | --- | --- | --- | --- |",
    ]
    for call in calls:
        lines.append(
            f"| `{label(call['caller'])}` | `{label(call['operation'])}` | "
            f"`{call['key']}` | {call['disposition']} | {call['reuse']} |"
        )
    lines += [
        "",
        "## Checkpoints and observation order",
        "",
        "Each row is an accepted, immutable checkpoint from a producer. The reads "
        "are observed grants, ordered by the session event log; 'before final' "
        "means the consumer obtained it while the producer was still running. "
        "A late subscriber can replay the same checkpoint after completion.",
        "",
        "| Producer | Checkpoint | Subscriber reads |",
        "| --- | --- | --- |",
    ]
    for position, event in enumerate(events):
        if event["type"] != "checkpoint_published":
            continue
        final_at = next(
            (
                i
                for i, item in enumerate(events)
                if i > position
                and item["type"] in ("accepted", "needs_review", "failed", "cancelled")
                and item.get("frame") == event["operation"]
            ),
            None,
        )
        reads = [
            f"`{label(item['frame'])}` ({'before final' if final_at is None or i < final_at else 'after final'})"
            for i, item in enumerate(events)
            if i > position
            and item["type"] == "artifact_read"
            and item["ref"] == event["ref"]
            and item["frame"] != event["operation"]
        ]
        lines.append(
            f"| `{label(event['operation'])}` | `{normalize(event['ref'])}` "
            f"(cursor {event['cursor']}) | {', '.join(reads) or 'None'} |"
        )
    lines += [
        "",
        "## Captured PTC and observations",
        "",
        "The shared-request fixture helper is shown once. It encodes the standard "
        "producer tasks described in skill prose. Consumer interpretations are separate "
        "a/c/d/f/g outputs. Live agents write their own equivalent requests.",
        "",
        "```js",
        HELPERS[HELPERS.index("async function run(") : HELPERS.index("function evidence(")].strip(),
        "```",
        "",
        "The following cells cover every composite investigation execution. Full leaf "
        "and reviewer actions remain in the JSON trace. IDs are relabeled; repeated "
        "first-cell bindings (`input`, `suppliedRefs`, `assignedTask`) and "
        "[helper definitions](../ptc_helpers.js) are omitted. Other code and tool "
        "observations are copied from execution. Output capture is bounded to "
        "16,000 characters. Cells preserve order within each execution; they are not "
        "a global serial schedule or hidden model reasoning.",
        "",
    ]
    for admission in admissions:
        if admission["node"] not in COMPOSITE:
            continue
        lines += [f"### {label(admission['frame'])}", ""]
        first = True
        for event in events:
            if event.get("frame") != admission["frame"]:
                continue
            if event["type"] == "agent_actions":
                for call in event["calls"]:
                    if call["name"] != "eval":
                        continue
                    code = call["args"]["code"]
                    if first:
                        prefix = (
                            "var input = "
                            + json.dumps(records[admission["frame"]]["inputs"])
                            + ";\n"
                            + HELPERS
                        )
                        prefix += "var suppliedRefs = " + json.dumps(admission["refs"]) + ";\n"
                        prefix += "var assignedTask = " + json.dumps(admission["task"]) + ";\n"
                        if not code.startswith(prefix):
                            raise ValueError(
                                "Unexpected fixture prelude; update the exporter explicitly"
                            )
                        code = code[len(prefix) :]
                        first = False
                    lines += ["```js", normalize(code.strip()), "```", ""]
            elif event["type"] == "agent_observation":
                lines += ["Observed:", "", "```text", normalize(event["content"]), "```", ""]
    lines += [
        "## Final output",
        "",
        "```json",
        normalize(json.dumps(report, indent=2)),
        "```",
        "",
        "Accepted publication and review verdicts are separate. The thesis's mandatory "
        "review targets its frozen candidate in fresh context. Hashes mentioned inside "
        "a view do not themselves grant access to those artifacts. These offline "
        "outcomes verify execution mechanics, not live-model reasoning quality.",
        "",
    ]
    return "\n".join(lines)


async def main() -> None:
    for case in ("a", "b"):
        runtime, receipt = await run_demo(case, offline=True)
        try:
            path = ROOT / "examples" / "trajectories" / f"scenario_{case}.md"
            path.parent.mkdir(exist_ok=True)
            path.write_text(render(case, runtime, receipt), encoding="utf-8")
            trace_path = ROOT / "outputs" / f"scenario_{case}.json"
            trace_path.parent.mkdir(exist_ok=True)
            trace_path.write_text(
                json.dumps(
                    {"case": case, "receipt": receipt, "events": runtime.store.events()}, indent=2
                )
                + "\n"
            )
            print(
                f"Wrote {path.relative_to(ROOT)} ({runtime.ledger.calls} calls, {runtime.ledger.frames} executions)"
            )
        finally:
            runtime.store.close()


if __name__ == "__main__":
    asyncio.run(main())
