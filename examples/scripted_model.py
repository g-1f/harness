"""OFFLINE TEST FIXTURE: selects prewritten PTC; it does not generate new code.

Only --offline imports this model double. It reads real interpreter observations
and selects authored fragments so tests can reproduce every path without API
credentials. In --model mode, a real model receives skill prose and observations
and writes the PTC itself. No production harness branch logic lives here.
"""

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


def action(code):
    return AIMessage(
        content="", tool_calls=[{"name": "eval", "args": {"code": code}, "id": "step"}]
    )


HELPERS = Path(__file__).with_name("ptc_helpers.js").read_text(encoding="utf-8")
AUDIT = Path(__file__).with_name("ptc_audits.js").read_text(encoding="utf-8")


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
        tool_messages = [m for m in messages if m.type == "tool"]
        if not tool_messages:
            code = "var input = " + json.dumps(self.request_inputs) + ";\n" + HELPERS
            code += "var suppliedRefs = " + json.dumps(self.refs) + ";\n"
            code += "var assignedTask = " + json.dumps(self.task) + ";\n"
            value = action(code + self.first())
        else:
            output = str(tool_messages[-1].content)
            match = re.search(r"OBS:(\{[^\n]+\})", output)
            if match:
                observation = json.loads(match[1])
                value = action(self.next(observation["stage"], observation["value"]))
            elif "Error" in output or "error" in output:
                raise RuntimeError("Demo PTC failed: " + output[:1000])
            else:
                value = AIMessage(content="Candidate staged")
        return ChatResult(generations=[ChatGeneration(message=value)])

    def first(self):
        if self.node == "a":
            return """
const procedure = await tools.readNode({node: 'a'});
var parts = await Promise.all([
  run('c', suppliedRefs, 'Test capacity assumptions for the baseline claim; do not assume acceleration'),
  run('l', suppliedRefs, 'Check whether mix stability supports the baseline comparison')
]);
var observation = {
  text: input.observations.a, unit: input.units?.a || 'USD',
  source: 'synthetic/a', scope: assignedTask,
  subchecks: await Promise.all(parts.map(part => read(part.ref)))
};
observe('composed_evidence', observation);
"""
        if self.node == "c":
            return """
const procedure = await tools.readNode({node: 'c'});
var parts = [await run(
  'k', suppliedRefs, 'Corroborate volume for this capacity question: ' + assignedTask
)];
var observation = {
  text: input.observations.c, unit: input.units?.c || 'USD',
  source: 'synthetic/c', scope: assignedTask,
  subchecks: await Promise.all(parts.map(part => read(part.ref)))
};
observe('composed_evidence', observation);
"""
        if self.node in ("d", "f", "g", "h", "i", "k", "l"):
            return """
const evidence = input.observations[NODE];
if (typeof evidence !== 'string') throw new Error('Missing observation');
var observation = {
  text: evidence, unit: input.units?.[NODE] || 'USD',
  source: 'synthetic/' + NODE, scope: assignedTask
};
observe('evidence', observation);
""".replace("NODE", json.dumps(self.node))
        if self.node == "root":
            return """
var rootPrivate = 'not inherited by reviewers';
const linked = await tools.readNode({node: 'root'});
const [a, b] = await Promise.all([
  run('a', [], 'Establish the baseline claim and test its assumptions'),
  run('b', [], 'Assess the snapshot change before choosing follow-up work')
]);
var state = {
  a, b, artifacts: [{name: 'a', receipt: a}, {name: 'b', receipt: b}], decisions: []
};
observe('b', await read(b.ref));
"""
        if self.node == "b":
            return """
var delta = await run('delta_check', suppliedRefs, 'Compute the observed snapshot difference');
observe('delta', await read(delta.ref));
"""
        if self.node in ("red_team", "artifact_coherence"):
            return """
if (typeof rootPrivate !== 'undefined') throw new Error('Inherited parent globals');
var targets = await Promise.all(suppliedRefs.map(read));
observe('review', targets);
"""
        if self.node == "thesis":
            return """
var sources = await Promise.all(suppliedRefs.map(read));
observe('synthesis', sources);
"""
        raise RuntimeError("No demo agent for " + self.node)

    def next(self, stage, value):
        if stage == "composed_evidence" and self.node in ("a", "c"):
            return """
await tools.submitCandidate({
  summary: 'Contextual evidence', content: observation,
  based_on: [...suppliedRefs, ...parts.map(part => part.ref)]
});
"""
        if stage == "evidence" and self.node in ("d", "f", "g", "h", "i", "k", "l"):
            return """
await tools.submitCandidate({
  summary: 'Evidence observation', content: observation, based_on: suppliedRefs
});
"""
        if self.node == "b" and stage == "delta":
            if value["delta"] == 0:
                return """
await tools.submitCandidate({
  summary: 'No snapshot change; b returns early',
  content: {text: input.observations.b, unit: 'USD', changed: false, internal: []},
  based_on: [delta.ref]
});
"""
            return """
const parts = await Promise.all([
  run('k', [delta.ref], 'Explain volume against the measured snapshot delta'),
  run('l', [delta.ref], 'Explain mix against the measured snapshot delta')
]);
const observations = await Promise.all(parts.map(part => read(part.ref)));
await tools.submitCandidate({
  summary: 'B investigated changed snapshot',
  content: {
    text: input.observations.b, unit: 'USD', changed: true,
    internal: ['k', 'l'], observations
  },
  based_on: [delta.ref, ...parts.map(part => part.ref)]
});
"""
        if self.node == "root" and stage == "b":
            scenario_a = "accelerating" in value["text"].lower()
            nodes = ["c", "d"] if scenario_a else ["h"]
            return """
const branch = NODES;
state.decisions.push({after: 'b', run: branch, reason: REASON});
const questions = {
  c: 'Assess whether capacity can meet accelerating demand',
  d: 'Investigate supplier concentration after the demand observation',
  h: 'Investigate the policy outlook after the stable-demand observation'
};
const branchResults = await Promise.all(branch.map(n => run(n, [state.b.ref], questions[n])));
state.artifacts.push(...branchResults.map((receipt, i) => ({name: branch[i], receipt})));
observe('investigation', {
  node: branch[branch.length - 1],
  body: await read(branchResults[branchResults.length - 1].ref)
});
""".replace("NODES", json.dumps(nodes)).replace("REASON", json.dumps(value["text"]))
        if self.node == "root" and stage == "investigation":
            narrative = value["body"]["text"].lower()
            if value["node"] == "d":
                extra = ["f", "g"] if "concentrated supplier" in narrative else []
            else:
                extra = ["i"] if "pending regulatory change" in narrative else []
            return (
                """
const extra = EXTRA;
state.decisions.push({after: AFTER, run: extra, reason: REASON});
const source = state.artifacts[state.artifacts.length - 1].receipt.ref;
const questions = {
  f: 'Assess supplier alternatives for the identified concentration',
  g: 'Assess inventory protection against the identified concentration',
  i: 'Check the timeline of the identified regulatory proposal'
};
const investigations = await Promise.all(extra.map(n => run(n, [source], questions[n])));
state.artifacts.push(...investigations.map((receipt, i) => ({name: extra[i], receipt})));
""".replace("EXTRA", json.dumps(extra))
                .replace("AFTER", json.dumps(value["node"]))
                .replace("REASON", json.dumps(narrative))
                + AUDIT
            )
        if self.node == "root" and stage == "audits":
            if any(x.get("verdict") != "pass" for x in value):
                return """
await tools.submitCandidate({
  summary: 'Investigation blocked by failed audit',
  content: {
    outcome: 'blocked', executed: state.artifacts.map(item => item.name),
    decisions: state.decisions, audits: state.audits.map(audit => audit.ref),
    limitations: ['No thesis produced after failed audit']
  },
  based_on: [
    ...state.artifacts.map(item => item.receipt.ref),
    ...state.audits.map(audit => audit.ref)
  ]
});
"""
            return """
const evidence = [
  ...state.artifacts.map(item => item.receipt.ref),
  ...state.audits.map(audit => audit.ref)
];
const thesis = await run('thesis', evidence, 'Synthesize the investigated evidence and audit findings');
await tools.submitCandidate({
  summary: 'Completed investigated and reviewed thesis',
  content: {
    outcome: 'complete', thesis: thesis.ref,
    executed: state.artifacts.map(item => item.name),
    decisions: state.decisions, audited: state.auditTargets.map(target => target.ref),
    omitted_c_audit: !state.artifacts.some(item => item.name === 'c')
  },
  based_on: [thesis.ref, ...evidence]
});
"""
        if stage == "review" and self.node == "red_team":
            target = value[0]
            invalid = "UNSUPPORTED" in target.get("text", "")
            findings = ["Unsupported assertion in candidate"] if invalid else []
            assessment = {
                "candidate_ref": self.refs[0],
                "verdict": "fail" if invalid else "pass",
                "findings": findings,
            }
            return (
                "await tools.submitCandidate({summary:'Red-team assessment',content:"
                + json.dumps(assessment)
                + ",based_on:[]});"
            )
        if stage == "review" and self.node == "artifact_coherence":
            units = {x.get("unit") for x in value if x.get("unit")}
            findings = []
            if len(units) > 1:
                findings.append("Conflicting currency units across target artifacts")
            if any("INCONSISTENT" in x.get("text", "") for x in value):
                findings.append("Internal inconsistency")
            assessment = {
                "targets": self.refs,
                "verdict": "fail" if findings else "pass",
                "findings": findings,
                "coverage": len(value),
            }
            return (
                "await tools.submitCandidate({summary:'Coherence assessment',content:"
                + json.dumps(assessment)
                + ",based_on:suppliedRefs});"
            )
        if self.node == "thesis" and stage == "synthesis":
            texts = [x["text"] for x in value if "text" in x]
            content = {
                "text": "Synthetic thesis: " + " ".join(texts),
                "evidence_count": len(texts),
                "limitations": ["Synthetic observations; not an investment recommendation"],
            }
            return (
                "await tools.submitCandidate({summary:'Synthetic thesis candidate',content:"
                + json.dumps(content)
                + ",based_on:suppliedRefs});"
            )
        raise RuntimeError(f"Unexpected observation {self.node}/{stage}")
