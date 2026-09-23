# Scenario A: prompt and executed graph

**Offline scripted fixture.** These are actual Deep Agents/QuickJS calls and supervisor events. PTC fragments are prewritten and selected from observed results; this is not evidence of live-model code generation.

Reproduce: `python demo.py --offline --case a --trace outputs/scenario_a.json`.

Regenerate both documents: `python -m examples.export_trajectories`.

Outcome: `complete`. **25 calls, 17 executions**, 2 in-flight joins, 6 completed-result reuses. 51 scripted model operations; zero model API calls. All acquired leases were released; no active wait edges remain.

## Prompt

Source: [scenario_a.md](../prompts/scenario_a.md).

Investigate the synthetic snapshot using the root skill. Run the baseline view a
and capacity view c concurrently, respecting their evidence-requirement flags.
Both may need b's neutral snapshot evidence: use the same explicit producer task,
projected inputs and session reuse, while keeping their interpretations distinct.
After they finish, run d's supply cross-check. Follow its links into supplier and
inventory analyses when warranted, including shared f, k and l work. Inspect actual
results, run fresh independent audits, and synthesize only if the checks pass.
Write PTC incrementally from the skill prose and observations.

Bound synthetic inputs:

```json
{
  "sequence_baseline": false,
  "baseline_requires_snapshot": true,
  "capacity_requires_snapshot": true,
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

The [root procedure](../../skills/root/SKILL.md) and shared [execution prompt](../../harness/runners/node_agent.md) also enter the initial context. The fixture supports these documented scenarios, not arbitrary prompt paraphrases.

## Executed investigation graph

Each vertex is one actual execution. Edges come from `call_acquired` events, including joins and completed-result reuse. First arrival can be either parallel branch. Audit/synthesis vertices are omitted from this diagram and included in the complete tables below.

```mermaid
flowchart TD
    E1["root (E1)"]
    E2["a (E2)"]
    E3["c (E3)"]
    E4["b (E4)"]
    E5["delta_check (E5)"]
    E6["k (E6)"]
    E7["l (E7)"]
    E8["d (E8)"]
    E9["f (E9)"]
    E10["g (E10)"]
    E1 -->|started| E2
    E1 -->|started| E3
    E2 -->|started| E4
    E3 -->|joined| E4
    E4 -->|started| E5
    E4 -->|started| E6
    E4 -->|started| E7
    E1 -->|started| E8
    E8 -->|reused| E4
    E8 -->|started| E9
    E8 -->|started| E10
    E10 -->|reused| E5
    E9 -->|reused| E5
    E9 -->|reused| E6
    E9 -->|reused| E7
    E10 -->|reused| E7
    E10 -->|joined| E9
```

## Executions

Each row has one context and one produced result. `origin` in the raw trace records who first caused creation; it does not give that caller exclusive ownership.

| Execution | Task | Executor | Input refs |
| --- | --- | --- | --- |
| `E1:root` | Prompt above | `agent` | None |
| `E2:a` | Interpret baseline assumptions | `agent` | None |
| `E3:c` | Interpret capacity and the policy outlook | `agent` | None |
| `E4:b` | Produce snapshot evidence | `agent` | None |
| `E5:delta_check` | Compute snapshot difference | `snapshot_math` | None |
| `E6:k` | Report volume evidence | `agent` | `E5:delta_check/result` |
| `E7:l` | Report mix evidence | `agent` | `E5:delta_check/result` |
| `E8:d` | Cross-check supply against the completed views | `agent` | `E2:a/result`, `E3:c/result` |
| `E9:f` | Assess supplier alternatives | `agent` | `E4:b/result` |
| `E10:g` | Interpret inventory protection with supplier alternatives | `agent` | `E4:b/result` |
| `E11:artifact_coherence` | Audit this artifact | `agent` | `E2:a/result` |
| `E12:artifact_coherence` | Audit this artifact | `agent` | `E3:c/result` |
| `E13:artifact_coherence` | Audit this artifact | `agent` | `E8:d/result` |
| `E14:artifact_coherence` | Audit joint coherence | `agent` | `E2:a/result`, `E3:c/result`, `E8:d/result` |
| `E15:red_team` | Challenge candidate E2:a/result | `agent` | `E2:a/result` |
| `E16:thesis` | Synthesize the independently interpreted views and audit findings | `agent` | `E2:a/result`, `E3:c/result`, `E8:d/result`, `E11:artifact_coherence/result`, `E12:artifact_coherence/result`, `E13:artifact_coherence/result`, `E14:artifact_coherence/result`, `E15:red_team/result` |
| `E17:red_team` | Review candidate E16:thesis/draft; independently test claims. Return content with candidate_ref, verdict pass/fail/inconclusive, and findings array. | `agent` | `E16:thesis/draft`, `E2:a/result`, `E3:c/result`, `E8:d/result`, `E11:artifact_coherence/result`, `E12:artifact_coherence/result`, `E13:artifact_coherence/result`, `E14:artifact_coherence/result`, `E15:red_team/result` |

## Calls and ownership

Every successful acquisition has its own wait lease. Multiple rows can target the same execution. The runtime releases each lease on return, error or cancellation; callers never lock/unlock a skill themselves.

| Caller | Target execution | Caller key | Dispatch | Reuse policy |
| --- | --- | --- | --- | --- |
| `launcher` | `E1:root` | `root` | started | fresh |
| `E1:root` | `E2:a` | `a:1` | started | fresh |
| `E1:root` | `E3:c` | `c:2` | started | fresh |
| `E2:a` | `E4:b` | `b:1` | started | session |
| `E3:c` | `E4:b` | `b:1` | joined | session |
| `E4:b` | `E5:delta_check` | `delta_check:1` | started | session |
| `E4:b` | `E6:k` | `k:2` | started | session |
| `E4:b` | `E7:l` | `l:3` | started | session |
| `E1:root` | `E8:d` | `d:3` | started | fresh |
| `E8:d` | `E4:b` | `b:1` | reused | session |
| `E8:d` | `E9:f` | `f:2` | started | session |
| `E8:d` | `E10:g` | `g:3` | started | fresh |
| `E10:g` | `E5:delta_check` | `delta_check:1` | reused | session |
| `E9:f` | `E5:delta_check` | `delta_check:1` | reused | session |
| `E9:f` | `E6:k` | `k:2` | reused | session |
| `E9:f` | `E7:l` | `l:3` | reused | session |
| `E10:g` | `E7:l` | `l:2` | reused | session |
| `E10:g` | `E9:f` | `f:3` | joined | session |
| `E1:root` | `E11:artifact_coherence` | `artifact_coherence:4` | started | fresh |
| `E1:root` | `E12:artifact_coherence` | `artifact_coherence:5` | started | fresh |
| `E1:root` | `E13:artifact_coherence` | `artifact_coherence:6` | started | fresh |
| `E1:root` | `E14:artifact_coherence` | `artifact_coherence:7` | started | fresh |
| `E1:root` | `E15:red_team` | `red_team:8` | started | fresh |
| `E1:root` | `E16:thesis` | `thesis:9` | started | fresh |
| `E16:thesis` | `E17:red_team` | `review:0:red_team` | started | fresh |

## Captured PTC and observations

The shared-request fixture helper is shown once. It encodes the standard producer tasks described in skill prose. Consumer interpretations are separate a/c/d/f/g outputs. Live agents write their own equivalent requests.

```js
async function run(node, refs = [], task = 'Interpret the supplied evidence', reuse = 'fresh', inputs = input) {
  const receipt = await tools.runNode({request: {
    node, task, inputs, refs, reuse, key: node + ':' + (++sequence)
  }});
  if (receipt.status !== 'accepted') throw new Error(node + ': ' + receipt.status);
  return receipt;
}

// These exact neutral tasks also appear in each producer's prose. Consumer
// interpretation stays in a/c/d/f/g; it is not smuggled into shared work identity.
var sharedTasks = {
  b: 'Produce snapshot evidence',
  delta_check: 'Compute snapshot difference',
  k: 'Report volume evidence',
  l: 'Report mix evidence',
  f: 'Assess supplier alternatives'
};
async function share(node, refs = []) {
  const inputs = {
    current: input.current, previous: input.previous,
    observations: input.observations, units: input.units
  };
  return run(node, refs, sharedTasks[node], 'session', inputs);
}
```

The following cells cover every composite investigation execution. Full leaf and reviewer actions remain in the JSON trace. IDs are relabeled; repeated first-cell bindings (`input`, `suppliedRefs`, `assignedTask`) and [helper definitions](../ptc_helpers.js) are omitted. Other code and tool observations are copied from execution. Output capture is bounded to 16,000 characters. Cells preserve order within each execution; they are not a global serial schedule or hidden model reasoning.

### E1:root

```js
var rootPrivate = 'not inherited by reviewers';

const [a, c] = await Promise.all([
  run('a', [], 'Interpret baseline assumptions'),
  run('c', [], 'Interpret capacity and the policy outlook')
]);

var state = {a, c, artifacts: [{name: 'a', receipt: a}, {name: 'c', receipt: c}]};
observe('views', await Promise.all([read(a.ref), read(c.ref)]));
```

Observed:

```text
<stdout>
OBS:{"stage":"views","value":[{"scope":"Interpret baseline assumptions","snapshot":"E4:b/result","source":"synthetic/a","subchecks":[{"changed":true,"internal":["k","l"],"scope":"Produce snapshot evidence","source":"synthetic/b","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Demand is accelerating while supply remains constrained.","unit":"USD"}],"text":"Source evidence supports the baseline claim.","unit":"USD"},{"policy":null,"scope":"Interpret capacity and the policy outlook","snapshot":"E4:b/result","source":"synthetic/c","subchecks":[{"changed":true,"internal":["k","l"],"scope":"Produce snapshot evidence","source":"synthetic/b","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Demand is accelerating while supply remains constrained.","unit":"USD"}],"text":"Capacity additions lag demand.","unit":"USD"}]}
</stdout>
<result>null</result>
```

```js
const d = await run('d', [state.a.ref, state.c.ref], 'Cross-check supply against the completed views');
state.artifacts.push({name: 'd', receipt: d});
var completedViews = await Promise.all(state.artifacts.map(item => read(item.receipt.ref)));
state.snapshots = completedViews.map(view => view.snapshot).filter(Boolean);
state.audits = await Promise.all([
  ...state.artifacts.map(item => run('artifact_coherence', [item.receipt.ref], 'Audit this artifact')),
  run('artifact_coherence', state.artifacts.map(item => item.receipt.ref), 'Audit joint coherence'),
  run('red_team', [state.a.ref], 'Challenge candidate ' + state.a.ref)
]);
observe('audits', await Promise.all(state.audits.map(audit => read(audit.ref))));
```

Observed:

```text
<stdout>
OBS:{"stage":"audits","value":[{"coverage":1,"findings":[],"targets":["E2:a/result"],"verdict":"pass"},{"coverage":1,"findings":[],"targets":["E3:c/result"],"verdict":"pass"},{"coverage":1,"findings":[],"targets":["E8:d/result"],"verdict":"pass"},{"coverage":3,"findings":[],"targets":["E2:a/result","E3:c/result","E8:d/result"],"verdict":"pass"},{"candidate_ref":"E2:a/result","findings":[],"verdict":"pass"}]}
</stdout>
<result>null</result>
```

```js
const evidence = [...state.artifacts.map(item => item.receipt.ref), ...state.audits.map(audit => audit.ref)];
const thesis = await run('thesis', evidence, 'Synthesize the independently interpreted views and audit findings');
await tools.submitCandidate({
  summary: 'Completed graph investigation with a reviewed thesis',
  content: {
    outcome: 'complete', thesis: thesis.ref,
    views: state.artifacts.map(item => ({node: item.name, ref: item.receipt.ref})),
    snapshot_refs: state.snapshots, audited: state.artifacts.map(item => item.receipt.ref)
  },
  based_on: [thesis.ref, ...evidence]
});
```

Observed:

```text
<result>{staged: true}</result>
```

### E2:a

```js
const b = input.baseline_requires_snapshot ? await share('b') : null;
var evidenceRefs = [...suppliedRefs, ...(b ? [b.ref] : [])];
var observation = evidence('a', {
  snapshot: b?.ref || null, subchecks: b ? [await read(b.ref)] : []
});
observe('evidence', observation);
```

Observed:

```text
<stdout>
OBS:{"stage":"evidence","value":{"text":"Source evidence supports the baseline claim.","unit":"USD","source":"synthetic/a","scope":"Interpret baseline assumptions","snapshot":"E4:b/result","subchecks":[{"changed":true,"internal":["k","l"],"scope":"Produce snapshot evidence","source":"synthetic/b","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Demand is accelerating while supply remains constrained.","unit":"USD"}]}}
</stdout>
<result>null</result>
```

```js
await tools.submitCandidate({
  summary: 'Evidence interpreted for this question', content: observation, based_on: evidenceRefs
});
```

Observed:

```text
<result>{staged: true}</result>
```

### E3:c

```js
var snapshot = await share('b');
observe('capacity_snapshot', await read(snapshot.ref));
```

Observed:

```text
<stdout>
OBS:{"stage":"capacity_snapshot","value":{"changed":true,"internal":["k","l"],"scope":"Produce snapshot evidence","source":"synthetic/b","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Demand is accelerating while supply remains constrained.","unit":"USD"}}
</stdout>
<result>null</result>
```

```js
const policy = null;
var evidenceRefs = [...suppliedRefs, snapshot.ref, ...(policy ? [policy.ref] : [])];
var observation = evidence('c', {
  snapshot: snapshot.ref, policy: policy?.ref || null,
  subchecks: [await read(snapshot.ref), ...(policy ? [await read(policy.ref)] : [])]
});
observe('evidence', observation);
```

Observed:

```text
<stdout>
OBS:{"stage":"evidence","value":{"text":"Capacity additions lag demand.","unit":"USD","source":"synthetic/c","scope":"Interpret capacity and the policy outlook","snapshot":"E4:b/result","policy":null,"subchecks":[{"changed":true,"internal":["k","l"],"scope":"Produce snapshot evidence","source":"synthetic/b","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Demand is accelerating while supply remains constrained.","unit":"USD"}]}}
</stdout>
<result>null</result>
```

```js
await tools.submitCandidate({
  summary: 'Evidence interpreted for this question', content: observation, based_on: evidenceRefs
});
```

Observed:

```text
<result>{staged: true}</result>
```

### E4:b

```js
var delta = await share('delta_check');
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
const parts = await Promise.all([share('k', [delta.ref]), share('l', [delta.ref])]);
await tools.submitCandidate({
  summary: 'Shared snapshot evidence',
  content: evidence('b', {changed: true, internal: ['k', 'l'],
    subchecks: await Promise.all(parts.map(part => read(part.ref)))}),
  based_on: [delta.ref, ...parts.map(part => part.ref)]
});
```

Observed:

```text
<result>{staged: true}</result>
```

### E8:d

```js
var views = await Promise.all(suppliedRefs.map(read));
var snapshot = await share('b');
observe('supplier_snapshot', await read(snapshot.ref));
```

Observed:

```text
<stdout>
OBS:{"stage":"supplier_snapshot","value":{"changed":true,"internal":["k","l"],"scope":"Produce snapshot evidence","source":"synthetic/b","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Demand is accelerating while supply remains constrained.","unit":"USD"}}
</stdout>
<result>null</result>
```

```js
var parts = await Promise.all([
  share('f', [snapshot.ref]),
  run('g', [snapshot.ref], 'Interpret inventory protection with supplier alternatives')
]);

var evidenceRefs = [...suppliedRefs, snapshot.ref, ...parts.map(part => part.ref)];
var observation = evidence('d', {
  snapshot: snapshot.ref, investigated: parts.length > 0,
  subchecks: await Promise.all(parts.map(part => read(part.ref)))
});
observe('evidence', observation);
```

Observed:

```text
<stdout>
OBS:{"stage":"evidence","value":{"text":"Concentrated supplier exposure warrants further investigation.","unit":"USD","source":"synthetic/d","scope":"Cross-check supply against the completed views","snapshot":"E4:b/result","investigated":true,"subchecks":[{"scope":"Assess supplier alternatives","source":"synthetic/f","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Alternative suppliers require lead time.","unit":"USD"},{"scope":"Interpret inventory protection with supplier alternatives","source":"synthetic/g","subchecks":[{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"},{"scope":"Assess supplier alternatives","source":"synthetic/f","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Alternative suppliers require lead time.","unit":"USD"}],"text":"Inventory limits near-term exposure.","unit":"USD"}]}}
</stdout>
<result>null</result>
```

```js
await tools.submitCandidate({
  summary: 'Evidence interpreted for this question', content: observation, based_on: evidenceRefs
});
```

Observed:

```text
<result>{staged: true}</result>
```

### E9:f

```js
var suppliedEvidence = await Promise.all(suppliedRefs.map(read));
var delta = await share('delta_check');
var parts = await Promise.all([share('k', [delta.ref]), share('l', [delta.ref])]);
var evidenceRefs = [...suppliedRefs, delta.ref, ...parts.map(part => part.ref)];
var observation = evidence('f', {subchecks: await Promise.all(parts.map(part => read(part.ref)))});
observe('evidence', observation);
```

Observed:

```text
<stdout>
OBS:{"stage":"evidence","value":{"text":"Alternative suppliers require lead time.","unit":"USD","source":"synthetic/f","scope":"Assess supplier alternatives","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}]}}
</stdout>
<result>null</result>
```

```js
await tools.submitCandidate({
  summary: 'Evidence interpreted for this question', content: observation, based_on: evidenceRefs
});
```

Observed:

```text
<result>{staged: true}</result>
```

### E10:g

```js
var suppliedEvidence = await Promise.all(suppliedRefs.map(read));
var delta = await share('delta_check');
var parts = await Promise.all([share('l', [delta.ref]), share('f', suppliedRefs)]);
var evidenceRefs = [...suppliedRefs, delta.ref, ...parts.map(part => part.ref)];
var observation = evidence('g', {subchecks: await Promise.all(parts.map(part => read(part.ref)))});
observe('evidence', observation);
```

Observed:

```text
<stdout>
OBS:{"stage":"evidence","value":{"text":"Inventory limits near-term exposure.","unit":"USD","source":"synthetic/g","scope":"Interpret inventory protection with supplier alternatives","subchecks":[{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"},{"scope":"Assess supplier alternatives","source":"synthetic/f","subchecks":[{"evidence_count":1,"scope":"Report volume evidence","source":"synthetic/k","text":"Volume increased in the supplied snapshot.","unit":"USD"},{"evidence_count":1,"scope":"Report mix evidence","source":"synthetic/l","text":"Mix is stable in the supplied snapshot.","unit":"USD"}],"text":"Alternative suppliers require lead time.","unit":"USD"}]}}
</stdout>
<result>null</result>
```

```js
await tools.submitCandidate({
  summary: 'Evidence interpreted for this question', content: observation, based_on: evidenceRefs
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
    "E2:a/result",
    "E3:c/result",
    "E8:d/result"
  ],
  "outcome": "complete",
  "snapshot_refs": [
    "E4:b/result",
    "E4:b/result",
    "E4:b/result"
  ],
  "thesis": "E16:thesis/result",
  "views": [
    {
      "node": "a",
      "ref": "E2:a/result"
    },
    {
      "node": "c",
      "ref": "E3:c/result"
    },
    {
      "node": "d",
      "ref": "E8:d/result"
    }
  ]
}
```

Accepted publication and review verdicts are separate. The thesis's mandatory review targets its frozen candidate in fresh context. Hashes mentioned inside a view do not themselves grant access to those artifacts. These offline outcomes verify execution mechanics, not live-model reasoning quality.
