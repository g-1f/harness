"""Regenerate the two documented trajectories from actual offline executions."""

import asyncio
import json
from collections import Counter

from demo import run_demo
from examples.application import ROOT, prompt_for
from examples.fixtures import fixture
from examples.scripted_model import HELPERS
from harness import Runtime


def render(case: str, runtime: Runtime, receipt: dict) -> str:
    events = runtime.store.events()
    admissions = [event for event in events if event["type"] == "admitted"]
    scopes, counts = {}, Counter()
    for event in admissions:
        parent = scopes.get(event["parent"], "")
        base = f"{parent}/{event['node']}" if parent else event["node"]
        counts[base] += 1
        scopes[event["frame"]] = base if counts[base] == 1 else f"{base}[{counts[base]}]"

    # Friendly labels replace immutable hashes, without changing PTC control flow.
    aliases = dict(scopes)
    records = {}
    for event in events:
        if event["type"] in ("accepted", "needs_review"):
            aliases[event["ref"]] = scopes[event["frame"]] + "/result"
            record = runtime.store.get(event["ref"])
            records[event["frame"]] = record
            for ref in record["input_refs"]:
                target = runtime.store.get(ref)
                if target["status"] == "draft":
                    aliases[ref] = scopes[target["frame"]] + "/draft"

    def normalize(value: str) -> str:
        for identifier, label in aliases.items():
            value = value.replace(identifier, label)
        return value

    report = runtime.store.get(receipt["ref"])["content"]
    lines = [
        f"# Scenario {case.upper()}: prompt and executed PTC trajectory",
        "",
        "**Execution: offline scripted fixture.** Actual Deep Agents, QuickJS and supervisor; "
        "prewritten PTC selected from tool observations. This is not an LLM-generated trajectory.",
        "",
        f"Reproduce: `python demo.py --offline --case {case} --trace outputs/scenario_{case}.json`.",
        "",
        "Regenerate both documents: `python -m examples.export_trajectories`.",
        "",
        f"Outcome: `{report['outcome']}`; {runtime.ledger.frames} fresh invocations; "
        f"{runtime.ledger.model_calls} scripted model operations; zero model API calls.",
        "",
        "## Prompt",
        "",
        f"Source: [scenario_{case}.md](../prompts/scenario_{case}.md). "
        "The same task is passed to the offline fixture and live runner. The fixture only "
        "models the documented scenarios; it does not interpret arbitrary prompt changes.",
        "",
        prompt_for(case),
        "",
        "Bound synthetic inputs:",
        "",
        "```json",
        json.dumps(fixture(case), indent=2),
        "```",
        "",
        "The shared [execution prompt](../../harness/runners/node_agent.md) and "
        "[root skill](../../skills/root/SKILL.md) complete the initial context. "
        "Each child receives its own task, skill entry, inputs and explicit refs.",
        "",
        "## Every invocation",
        "",
        "Scopes are display labels for fresh frames. Repeated skill names share authored "
        "prose and revision, not conversations or interpreter state. Rows follow admission "
        "order; siblings may execute concurrently.",
        "",
        "| Invocation scope | Task | Executor | Granted refs |",
        "| --- | --- | --- | --- |",
    ]
    for event in admissions:
        task = "Scenario prompt above" if event["parent"] is None else normalize(event["task"])
        task = " ".join(task.split()).replace("|", "\\|")
        refs = ", ".join(f"`{normalize(ref)}`" for ref in event["refs"]) or "None"
        lines.append(f"| `{scopes[event['frame']]}` | {task} | `{event['executor']}` | {refs} |")

    lines += [
        "",
        "## Captured PTC and observations",
        "",
        "The cells below cover root and the nested a/b/c invocations. Leaf and review "
        "calls remain visible in the complete invocation table and JSON trace. "
        "These are tool actions and observations, not hidden reasoning.",
        "",
        "Artifact/frame IDs are relabeled above. The repeated first-cell bindings "
        "(`input`, `suppliedRefs`, `assignedTask`) and "
        "[helper definitions](../ptc_helpers.js) are omitted for readability. "
        "All remaining PTC is copied from executed `eval` calls. Observations are "
        "the captured tool output; output capture is bounded to 16,000 characters. "
        "Cells are grouped by frame, preserving order within each frame.",
        "",
    ]
    for admission in admissions:
        if admission["node"] not in ("root", "a", "b", "c"):
            continue
        lines += [f"### {scopes[admission['frame']]}", ""]
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
                        # Drop exactly the fixture prelude, retaining executable node work.
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
        "`accepted` describes completion of the publication protocol. Review verdicts "
        "are separate content fields; the thesis's mandatory review targets its exact "
        "frozen draft. Offline checks establish these fixture outcomes and execution "
        "mechanics, not live-model reasoning quality.",
        "",
    ]
    return "\n".join(lines)


async def main() -> None:
    for case in ("a", "b"):
        runtime, receipt = await run_demo(case, offline=True)
        try:
            text = render(case, runtime, receipt)
            path = ROOT / "examples" / "trajectories" / f"scenario_{case}.md"
            path.parent.mkdir(exist_ok=True)
            path.write_text(text, encoding="utf-8")
            trace_path = ROOT / "outputs" / f"scenario_{case}.json"
            trace_path.parent.mkdir(exist_ok=True)
            trace_path.write_text(
                json.dumps(
                    {"case": case, "receipt": receipt, "events": runtime.store.events()}, indent=2
                )
                + "\n"
            )
            print(f"Wrote {path.relative_to(ROOT)} ({runtime.ledger.frames} invocations)")
        finally:
            runtime.store.close()


if __name__ == "__main__":
    asyncio.run(main())
