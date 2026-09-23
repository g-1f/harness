# Scenario A: prompt and executed PTC trajectory

**Execution: offline scripted fixture.** Actual Deep Agents, QuickJS and supervisor; prewritten PTC selected from tool observations. This is not an LLM-generated trajectory.

Reproduce: `python demo.py --offline --case a --trace outputs/scenario_a.json`.

Regenerate both documents: `python -m examples.export_trajectories`.

Outcome: `complete`; 21 fresh invocations; 62 scripted model operations; zero model API calls.

## Prompt

Source: [scenario_a.md](../prompts/scenario_a.md). The same task is passed to the offline fixture and live runner. The fixture only models the documented scenarios; it does not interpret arbitrary prompt changes.

Use the root skill to investigate the supplied synthetic snapshot. Establish the
baseline through a while b interprets the change. Let each skill follow its own
linked procedures and pass a specific question to each child. If the observations
warrant an acceleration investigation, revisit c for that question even if a
already used c to test the baseline. Track those calls separately. Inspect the
relevant artifacts, run fresh coherence and red-team checks, and produce a reviewed
thesis only when the checks pass. Explain the branches taken and preserve evidence
references. Generate your PTC incrementally from the prose and tool observations.

Bound synthetic inputs:

```json
{
  "current": 105,
  "previous": 100,
  "units": {},
  "observations": {
    "a": "Source evidence supports the baseline claim.",
    "b": "Demand is accelerating while supply remains constrained.",
    "c": "Capacity additions lag demand.",
    "d": "Concentrated supplier exposure warrants further investigation.",
    "f": "Alternative suppliers require lead time.",
    "g": "Inventory limits near-term exposure.",
    "h": "A pending regulatory change warrants investigation.",
    "i": "The proposed rule takes effect next quarter.",
    "k": "Volume increased in the supplied snapshot.",
    "l": "Mix is stable in the supplied snapshot."
  }
}
```

The shared [execution prompt](../../harness/runners/node_agent.md) and [root skill](../../skills/root/SKILL.md) complete the initial context. Each child receives its own task, skill entry, inputs and explicit refs.

## Every invocation

Scopes are display labels for fresh frames. Repeated skill names share authored prose and revision, not conversations or interpreter state. Rows follow admission order; siblings may execute concurrently.

| Invocation scope | Task | Executor | Granted refs |
| --- | --- | --- | --- |
| `root` | Scenario prompt above | `agent` | None |
| `root/a` | Establish the baseline claim and test its assumptions | `agent` | None |
| `root/b` | Assess the snapshot change before choosing follow-up work | `agent` | None |
| `root/b/delta_check` | Compute the observed snapshot difference | `snapshot_math` | None |
| `root/a/c` | Test capacity assumptions for the baseline claim; do not assume acceleration | `agent` | None |
| `root/a/l` | Check whether mix stability supports the baseline comparison | `agent` | None |
| `root/a/c/k` | Corroborate volume for this capacity question: Test capacity assumptions for the baseline claim; do not assume acceleration | `agent` | None |
| `root/b/k` | Explain volume against the measured snapshot delta | `agent` | `root/b/delta_check/result` |
| `root/b/l` | Explain mix against the measured snapshot delta | `agent` | `root/b/delta_check/result` |
| `root/c` | Assess whether capacity can meet accelerating demand | `agent` | `root/b/result` |
| `root/d` | Investigate supplier concentration after the demand observation | `agent` | `root/b/result` |
| `root/c/k` | Corroborate volume for this capacity question: Assess whether capacity can meet accelerating demand | `agent` | `root/b/result` |
| `root/f` | Assess supplier alternatives for the identified concentration | `agent` | `root/d/result` |
| `root/g` | Assess inventory protection against the identified concentration | `agent` | `root/d/result` |
| `root/artifact_coherence` | Audit this artifact | `agent` | `root/a/result` |
| `root/artifact_coherence[2]` | Audit this artifact | `agent` | `root/b/result` |
| `root/artifact_coherence[3]` | Audit this artifact | `agent` | `root/c/result` |
| `root/artifact_coherence[4]` | Audit joint coherence | `agent` | `root/a/result`, `root/b/result`, `root/c/result` |
| `root/red_team` | Challenge candidate root/a/result | `agent` | `root/a/result` |
| `root/thesis` | Synthesize the investigated evidence and audit findings | `agent` | `root/a/result`, `root/b/result`, `root/c/result`, `root/d/result`, `root/f/result`, `root/g/result`, `root/artifact_coherence/result`, `root/artifact_coherence[2]/result`, `root/artifact_coherence[3]/result`, `root/artifact_coherence[4]/result`, `root/red_team/result` |
| `root/thesis/red_team` | Review candidate root/thesis/draft; independently test claims. Return content with candidate_ref, verdict pass/fail/inconclusive, and findings array. | `agent` | `root/thesis/draft`, `root/a/result`, `root/b/result`, `root/c/result`, `root/d/result`, `root/f/result`, `root/g/result`, `root/artifact_coherence/result`, `root/artifact_coherence[2]/result`, `root/artifact_coherence[3]/result`, `root/artifact_coherence[4]/result`, `root/red_team/result` |

## Captured PTC and observations

The cells below cover root and the nested a/b/c invocations. Leaf and review calls remain visible in the complete invocation table and JSON trace. These are tool actions and observations, not hidden reasoning.

Artifact/frame IDs are relabeled above. The repeated first-cell bindings (`input`, `suppliedRefs`, `assignedTask`) and [helper definitions](../ptc_helpers.js) are omitted for readability. All remaining PTC is copied from executed `eval` calls. Observations are the captured tool output; output capture is bounded to 16,000 characters. Cells are grouped by frame, preserving order within each frame.

### root

```js
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
```

Observed:

```text
<stdout>
OBS:{"stage":"b","value":{"changed":true,"internal":["k","l"],"observations":[{"scope":"Explain volume against the measured snapshot delta","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"scope":"Explain mix against the measured snapshot delta","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Demand is accelerating while supply remains constrained.","unit":"USD"}}
</stdout>
<result>null</result>
```

```js
const branch = ["c", "d"];
state.decisions.push({after: 'b', run: branch, reason: "Demand is accelerating while supply remains constrained."});
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
```

Observed:

```text
<stdout>
OBS:{"stage":"investigation","value":{"node":"d","body":{"scope":"Investigate supplier concentration after the demand observation","source":"synthetic/d","text":"Concentrated supplier exposure warrants further investigation.","unit":"USD"}}}
</stdout>
<result>null</result>
```

```js
const extra = ["f", "g"];
state.decisions.push({after: "d", run: extra, reason: "concentrated supplier exposure warrants further investigation."});
const source = state.artifacts[state.artifacts.length - 1].receipt.ref;
const questions = {
  f: 'Assess supplier alternatives for the identified concentration',
  g: 'Assess inventory protection against the identified concentration',
  i: 'Check the timeline of the identified regulatory proposal'
};
const investigations = await Promise.all(extra.map(n => run(n, [source], questions[n])));
state.artifacts.push(...investigations.map((receipt, i) => ({name: extra[i], receipt})));
state.auditTargets = [
  state.a,
  state.b,
  ...state.artifacts.filter(item => item.name === 'c').map(item => item.receipt)
];
state.audits = await Promise.all([
  ...state.auditTargets.map(target => run('artifact_coherence', [target.ref], 'Audit this artifact')),
  run('artifact_coherence', state.auditTargets.map(target => target.ref), 'Audit joint coherence'),
  run('red_team', [state.a.ref], 'Challenge candidate ' + state.a.ref)
]);
const auditBodies = await Promise.all(state.audits.map(audit => read(audit.ref)));
observe('audits', auditBodies);
```

Observed:

```text
<stdout>
OBS:{"stage":"audits","value":[{"coverage":1,"findings":[],"targets":["root/a/result"],"verdict":"pass"},{"coverage":1,"findings":[],"targets":["root/b/result"],"verdict":"pass"},{"coverage":1,"findings":[],"targets":["root/c/result"],"verdict":"pass"},{"coverage":3,"findings":[],"targets":["root/a/result","root/b/result","root/c/result"],"verdict":"pass"},{"candidate_ref":"root/a/result","findings":[],"verdict":"pass"}]}
</stdout>
<result>null</result>
```

```js
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
```

Observed:

```text
<result>{staged: true}</result>
```

### root/a

```js
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
```

Observed:

```text
<stdout>
OBS:{"stage":"composed_evidence","value":{"text":"Source evidence supports the baseline claim.","unit":"USD","source":"synthetic/a","scope":"Establish the baseline claim and test its assumptions","subchecks":[{"scope":"Test capacity assumptions for the baseline claim; do not assume acceleration","source":"synthetic/c","subchecks":[{"scope":"Corroborate volume for this capacity question: Test capacity assumptions for the baseline claim; do not assume acceleration","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"}],"text":"Capacity additions lag demand.","unit":"USD"},{"scope":"Check whether mix stability supports the baseline comparison","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}]}}
</stdout>
<result>null</result>
```

```js
await tools.submitCandidate({
  summary: 'Contextual evidence', content: observation,
  based_on: [...suppliedRefs, ...parts.map(part => part.ref)]
});
```

Observed:

```text
<result>{staged: true}</result>
```

### root/b

```js
var delta = await run('delta_check', suppliedRefs, 'Compute the observed snapshot difference');
observe('delta', await read(delta.ref));
```

Observed:

```text
<stdout>
OBS:{"stage":"delta","value":{"delta":5,"source":"synthetic snapshot pair","text":"Computed delta observation","unit":"USD"}}
</stdout>
<result>null</result>
```

```js
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
```

Observed:

```text
<result>{staged: true}</result>
```

### root/a/c

```js
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
```

Observed:

```text
<stdout>
OBS:{"stage":"composed_evidence","value":{"text":"Capacity additions lag demand.","unit":"USD","source":"synthetic/c","scope":"Test capacity assumptions for the baseline claim; do not assume acceleration","subchecks":[{"scope":"Corroborate volume for this capacity question: Test capacity assumptions for the baseline claim; do not assume acceleration","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"}]}}
</stdout>
<result>null</result>
```

```js
await tools.submitCandidate({
  summary: 'Contextual evidence', content: observation,
  based_on: [...suppliedRefs, ...parts.map(part => part.ref)]
});
```

Observed:

```text
<result>{staged: true}</result>
```

### root/c

```js
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
```

Observed:

```text
<stdout>
OBS:{"stage":"composed_evidence","value":{"text":"Capacity additions lag demand.","unit":"USD","source":"synthetic/c","scope":"Assess whether capacity can meet accelerating demand","subchecks":[{"scope":"Corroborate volume for this capacity question: Assess whether capacity can meet accelerating demand","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"}]}}
</stdout>
<result>null</result>
```

```js
await tools.submitCandidate({
  summary: 'Contextual evidence', content: observation,
  based_on: [...suppliedRefs, ...parts.map(part => part.ref)]
});
```

Observed:

```text
<result>{staged: true}</result>
```

## Final output

```json
{
  "audited": [
    "root/a/result",
    "root/b/result",
    "root/c/result"
  ],
  "decisions": [
    {
      "after": "b",
      "reason": "Demand is accelerating while supply remains constrained.",
      "run": [
        "c",
        "d"
      ]
    },
    {
      "after": "d",
      "reason": "concentrated supplier exposure warrants further investigation.",
      "run": [
        "f",
        "g"
      ]
    }
  ],
  "executed": [
    "a",
    "b",
    "c",
    "d",
    "f",
    "g"
  ],
  "omitted_c_audit": false,
  "outcome": "complete",
  "thesis": "root/thesis/result"
}
```

`accepted` describes completion of the publication protocol. Review verdicts are separate content fields; the thesis's mandatory review targets its exact frozen draft. Offline checks establish these fixture outcomes and execution mechanics, not live-model reasoning quality.
