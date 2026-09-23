"""Explicit OFFLINE fixture: selects authored PTC from actual tool observations.

No live-model trajectory is claimed. The examples exercise the real interpreter,
node API and operation coordinator. No semantic branch logic lives in the harness.
"""

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

HELPERS = Path(__file__).with_name("ptc_helpers.js").read_text(encoding="utf-8")
AUDIT = Path(__file__).with_name("ptc_audits.js").read_text(encoding="utf-8")


def action(code):
    return AIMessage(
        content="", tool_calls=[{"name": "eval", "args": {"code": code}, "id": "step"}]
    )


def submit(summary, content, refs="suppliedRefs"):
    return (
        "await tools.submitCandidate({\n  summary: "
        + json.dumps(summary)
        + ",\n  content: "
        + json.dumps(content, indent=2)
        + ",\n  based_on: "
        + refs
        + "\n});"
    )


class ScriptedFixtureModel(BaseChatModel):
    node: str
    task: str
    request_inputs: dict[str, Any]
    refs: list[str]

    @property
    def _llm_type(self):
        return "offline-scripted-fixture"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tool_messages = [message for message in messages if message.type == "tool"]
        if not tool_messages:
            prelude = "var input = " + json.dumps(self.request_inputs) + ";\n" + HELPERS
            prelude += "var suppliedRefs = " + json.dumps(self.refs) + ";\n"
            prelude += "var assignedTask = " + json.dumps(self.task) + ";\n"
            message = action(prelude + self.first())
        else:
            output = str(tool_messages[-1].content)
            match = re.search(r"OBS:(\{[^\n]+\})", output)
            if match:
                observation = json.loads(match[1])
                message = action(self.next(observation["stage"], observation["value"]))
            elif "Error" in output or "error" in output:
                raise RuntimeError("Demo PTC failed: " + output[:1000])
            else:
                message = AIMessage(content="Candidate staged")
        return ChatResult(generations=[ChatGeneration(message=message)])

    def first(self):
        if self.node == "root":
            calls = (
                """
const [a, c] = await Promise.all([
  run('a', [], 'Interpret baseline assumptions'),
  run('c', [], 'Interpret capacity and the policy outlook')
]);
"""
                if not self.request_inputs["sequence_baseline"]
                else """
const a = await run('a', [], 'Interpret baseline assumptions');
const c = await run('c', [], 'Interpret capacity after the baseline is complete');
"""
            )
            return (
                "var rootPrivate = 'not inherited by reviewers';\n"
                + calls
                + """
var state = {a, c, artifacts: [{name: 'a', receipt: a}, {name: 'c', receipt: c}]};
observe('views', await Promise.all([read(a.ref), read(c.ref)]));
"""
            )
        if self.node == "a":
            return """
const shared = input.baseline_requires_snapshot
  ? await nodes.with(sharedRequest('b'), async operation => {
      const progress = await operation.next();
      if (!progress) throw new Error('Expected snapshot measurement');
      const measured = await read(progress.ref);
      const b = await operation.result();
      if (b.status !== 'published') throw new Error('Snapshot unpublished');
      return {progress, measured, b};
    }) : {progress: null, measured: null, b: null};
const {progress, measured, b} = shared;
var evidenceRefs = [...suppliedRefs,
  ...(progress ? [progress.ref] : []), ...(b ? [b.ref] : [])];
var observation = evidence('a', {
  snapshot: b?.ref || null, checkpoint: progress?.ref || null,
  subchecks: b ? [measured, await read(b.ref)] : []
});
observe('evidence', observation);
"""
        if self.node == "c":
            if not self.request_inputs["capacity_requires_snapshot"]:
                return """
var evidenceRefs = suppliedRefs;
var observation = evidence('c', {snapshot: null, policy: null});
observe('evidence', observation);
"""
            return """
var shared = await nodes.with(sharedRequest('b'), async operation => {
  const progress = await operation.next();
  if (!progress) throw new Error('Expected snapshot measurement');
  const measured = await read(progress.ref);
  const focused = await run('b', [progress.ref],
    'Assess capacity from snapshot checkpoint', 'fresh', sharedInputs());
  const snapshot = await operation.result();
  if (snapshot.status !== 'published') throw new Error('Snapshot unpublished');
  return {progress, measured, focused, snapshot};
});
var {progress, measured, focused, snapshot} = shared;
observe('capacity_snapshot', {
  snapshot: await read(snapshot.ref), focus: await read(focused.ref), checkpoint: measured
});
"""
        if self.node == "b":
            if self.task == "Assess capacity from snapshot checkpoint":
                return """
var measured = await read(suppliedRefs[0]);
observe('focused', measured);
"""
            return """
var delta = await share('delta_check');
var measurement = await read(delta.ref);
var checkpoint = await tools.publishCheckpoint({
  summary: 'Measured snapshot evidence for other interpretations',
  content: {delta: measurement.delta, unit: measurement.unit,
    source: measurement.source, text: 'Snapshot measurement'},
  based_on: [delta.ref]
});
if (checkpoint.status !== 'published') throw new Error('Snapshot checkpoint unpublished');
observe('delta', await read(delta.ref));
"""
        if self.node == "d":
            return """
var views = await Promise.all(suppliedRefs.map(read));
var snapshot = await share('b');
observe('supplier_snapshot', await read(snapshot.ref));
"""
        if self.node == "f":
            return """
var suppliedEvidence = await Promise.all(suppliedRefs.map(read));
var delta = await share('delta_check');
var parts = await Promise.all([share('k', [delta.ref]), share('l', [delta.ref])]);
var evidenceRefs = [...suppliedRefs, delta.ref, ...parts.map(part => part.ref)];
var observation = evidence('f', {subchecks: await Promise.all(parts.map(part => read(part.ref)))});
observe('evidence', observation);
"""
        if self.node == "g":
            return """
var suppliedEvidence = await Promise.all(suppliedRefs.map(read));
var delta = await share('delta_check');
var parts = await Promise.all([share('l', [delta.ref]), share('f', suppliedRefs)]);
var evidenceRefs = [...suppliedRefs, delta.ref, ...parts.map(part => part.ref)];
var observation = evidence('g', {subchecks: await Promise.all(parts.map(part => read(part.ref)))});
observe('evidence', observation);
"""
        if self.node == "h":
            return "observe('policy', input.observations.h);"
        if self.node in ("i", "k", "l"):
            return """
var suppliedEvidence = await Promise.all(suppliedRefs.map(read));
var evidenceRefs = suppliedRefs;
var observation = evidence(NODE, {evidence_count: suppliedEvidence.length});
observe('evidence', observation);
""".replace("NODE", json.dumps(self.node))
        if self.node in ("red_team", "artifact_coherence"):
            return """
if (typeof rootPrivate !== 'undefined') throw new Error('Inherited parent globals');
var targets = await Promise.all(suppliedRefs.map(read));
observe('review', targets);
"""
        if self.node == "thesis_draft":
            return "observe('synthesis', await Promise.all(suppliedRefs.map(read)));"
        raise RuntimeError("No fixture for " + self.node)

    def next(self, stage, value):
        if stage == "evidence":
            return """
await tools.submitCandidate({
  summary: 'Evidence interpreted for this question', content: observation, based_on: evidenceRefs
});
"""
        handlers = {
            ("root", "views"): self.root_views,
            ("root", "audits"): self.root_audits,
            ("b", "delta"): self.snapshot,
            ("b", "focused"): self.focused,
            ("c", "capacity_snapshot"): self.capacity,
            ("d", "supplier_snapshot"): self.supplier,
            ("h", "policy"): self.policy,
            ("red_team", "review"): self.red_team,
            ("artifact_coherence", "review"): self.coherence,
            ("thesis_draft", "synthesis"): self.synthesis,
        }
        handler = handlers.get((self.node, stage))
        if handler is None:
            raise RuntimeError(f"Unexpected observation {self.node}/{stage}")
        return handler(value)

    def root_views(self, value):
        return (
            """
const d = await run('d', [state.a.ref, state.c.ref], 'Cross-check supply against the completed views');
state.artifacts.push({name: 'd', receipt: d});
var completedViews = await Promise.all(state.artifacts.map(item => read(item.receipt.ref)));
state.snapshots = completedViews.map(view => view.snapshot).filter(Boolean);
"""
            + AUDIT
        )

    def root_audits(self, value):
        if any(result.get("verdict") != "pass" for result in value):
            return """
await tools.submitCandidate({
  summary: 'Investigation blocked by failed audit',
  content: {outcome: 'blocked', audits: state.audits.map(audit => audit.ref)},
  based_on: [...state.artifacts.map(item => item.receipt.ref), ...state.audits.map(audit => audit.ref)]
});
"""
        return """
const evidence = [...state.artifacts.map(item => item.receipt.ref), ...state.audits.map(audit => audit.ref)];
const thesis = await run('thesis', evidence, 'Synthesize the independently interpreted views and audit findings');
const decision = await read(thesis.ref);
await tools.submitCandidate({
  summary: 'Graph investigation with a thesis decision',
  content: {
    outcome: decision.decision === 'approved' ? 'complete' : 'blocked', thesis: thesis.ref,
    views: state.artifacts.map(item => ({node: item.name, ref: item.receipt.ref})),
    snapshot_refs: state.snapshots, audited: state.artifacts.map(item => item.receipt.ref)
  },
  based_on: [thesis.ref, ...evidence]
});
"""

    def snapshot(self, value):
        if value["delta"] == 0:
            return """
await tools.submitCandidate({
  summary: 'Snapshot unchanged', content: evidence('b', {changed: false, internal: []}),
  based_on: [checkpoint.ref, delta.ref]
});
"""
        return """
const parts = await Promise.all([share('k', [delta.ref]), share('l', [delta.ref])]);
await tools.submitCandidate({
  summary: 'Shared snapshot evidence',
  content: evidence('b', {changed: true, internal: ['k', 'l'],
    subchecks: await Promise.all(parts.map(part => read(part.ref)))}),
  based_on: [checkpoint.ref, delta.ref, ...parts.map(part => part.ref)]
});
"""

    def focused(self, value):
        return """
await tools.submitCandidate({
  summary: 'Capacity-specific follow-up on measured evidence',
  content: {text: input.observations.c, unit: measured.unit,
    source: 'synthetic/b:capacity', scope: assignedTask,
    delta: measured.delta, checkpoint: suppliedRefs[0]},
  based_on: suppliedRefs
});
"""

    def capacity(self, value):
        inspect_policy = "accelerating" not in value["snapshot"]["text"].lower()
        code = (
            "const policy = await run('h', [snapshot.ref], 'Investigate the policy outlook');"
            if inspect_policy
            else "const policy = null;"
        )
        return (
            code
            + """
var evidenceRefs = [...suppliedRefs, progress.ref, focused.ref, snapshot.ref,
  ...(policy ? [policy.ref] : [])];
var observation = evidence('c', {
  snapshot: snapshot.ref, checkpoint: progress.ref,
  focus: focused.ref, policy: policy?.ref || null,
  subchecks: [measured, await read(focused.ref), await read(snapshot.ref),
    ...(policy ? [await read(policy.ref)] : [])]
});
observe('evidence', observation);
"""
        )

    def supplier(self, value):
        investigate = (
            "accelerating" in value["text"].lower()
            and "concentrated supplier" in self.request_inputs["observations"]["d"].lower()
        )
        code = (
            """
var parts = await Promise.all([
  share('f', [snapshot.ref]),
  run('g', [snapshot.ref], 'Interpret inventory protection with supplier alternatives')
]);
"""
            if investigate
            else "var parts = [];\n"
        )
        return (
            code
            + """
var evidenceRefs = [...suppliedRefs, snapshot.ref, ...parts.map(part => part.ref)];
var observation = evidence('d', {
  snapshot: snapshot.ref, investigated: parts.length > 0,
  subchecks: await Promise.all(parts.map(part => read(part.ref)))
});
observe('evidence', observation);
"""
        )

    def policy(self, value):
        pending = "pending regulatory change" in value.lower()
        code = """
var delta = await share('delta_check');
var mix = await share('l', [delta.ref]);
"""
        code += (
            "var timeline = await run('i', suppliedRefs, 'Inspect the proposal timeline');"
            if pending
            else "var timeline = null;"
        )
        return (
            code
            + """
var evidenceRefs = [...suppliedRefs, delta.ref, mix.ref, ...(timeline ? [timeline.ref] : [])];
var observation = evidence('h', {
  subchecks: [await read(mix.ref), ...(timeline ? [await read(timeline.ref)] : [])]
});
observe('evidence', observation);
"""
        )

    def red_team(self, value):
        unsupported = "UNSUPPORTED" in value[0].get("text", "")
        return submit(
            "Red-team assessment",
            {
                "candidate_ref": self.refs[0],
                "verdict": "fail" if unsupported else "pass",
                "findings": ["Unsupported assertion in candidate"] if unsupported else [],
            },
        )

    def coherence(self, value):
        units = {result["unit"] for result in value if result.get("unit")}
        findings = []
        if len(units) > 1:
            findings.append("Conflicting currency units across target artifacts")
        if any("INCONSISTENT" in result.get("text", "") for result in value):
            findings.append("Internal inconsistency")
        return submit(
            "Coherence assessment",
            {
                "targets": self.refs,
                "verdict": "fail" if findings else "pass",
                "findings": findings,
                "coverage": len(value),
            },
        )

    def synthesis(self, value):
        texts = [result["text"] for result in value if "text" in result]
        return submit(
            "Synthetic thesis candidate",
            {
                "text": "Synthetic thesis: " + " ".join(texts),
                "evidence_count": len(texts),
                "limitations": ["Synthetic observations; not an investment recommendation"],
            },
        )
