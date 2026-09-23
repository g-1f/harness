# Node execution and artifact composition

Status: implemented reference, clarified 2026-09-23. Skills normally contain prose
and links; the agent writes PTC at runtime after observations. An optional bundled
utility script is authored separately. Offline tests select prewritten fragments
and are explicitly distinguished from actual LLM code generation. This is a
single-process implementation.

## 1. Execution contract

A node is a versioned procedure with prose, links, and an implementation. The
runtime admits an invocation; its implementation produces a candidate; the host
validates and publishes a receipt. Agent execution is one implementation of a node.
Code execution is another and makes no model calls. A fresh agent context is a
property of agent-node invocation, not the definition of all node execution.

The primary path is a prose-driven agent node: read the procedure, observe inputs,
generate PTC, execute it, observe the result, and generate the next fragment. The
host executes and supervises this loop; it does not generate or compile the
domain's branch logic. All research, review, and synthesis skills in the example
use this path. A skill does not need an authored execution program to be callable.

```python
from runtime import NodeRequest, Registry, Runtime, Store
from code_runner import CodeRunner
from deepagents_adapter import DeepAgentRunner

runtime = Runtime(registry, Store())
runtime.code_runner = CodeRunner(runtime)
runtime.agent_runner = DeepAgentRunner(runtime, model_factory)
receipt = await runtime.run_node(NodeRequest(
    node="root", task="Investigate the supplied evidence",
    inputs=inputs, refs=(), key="root",
))
```

`registry`, `inputs`, and `model_factory` are supplied by the application; `demo.py`
contains executable wiring. A code-only application needs no agent runner. Code
nodes can invoke other code or agent nodes using the same operation.

## 2. Native capabilities

| Operation | Semantics |
| --- | --- |
| `read_node(node, enter=False)` | Return a bounded packet with the procedure, kind, revision, links, and eligible context. Inspection alone does not activate review obligations. `enter=True` adopts the procedure inline. |
| `run_node(request)` | Admit and await a distinct node invocation. Host-derived parent identity, source revision, grants, and limits apply. Returns a compact artifact receipt. |
| `read_artifact(ref, offset, limit)` | Read an authorized immutable version in bounded slices, recording explicit access. |
| `submit_candidate(summary, content, based_on)` | Stage an output in the current frame. Publication and required review happen after the runner returns. |

All four are available from generated JavaScript as `tools.readNode`, `runNode`,
`readArtifact`, and `submitCandidate`. They also have native tool forms and use
`NodeAPI` internally. The QuickJS PTC `task()` facility is disabled. The remaining
native framework `task` tool dispatches into the same supervised `run_node` API
for compatibility; it cannot create an ungoverned worker.

Node discovery starts with canonical links. The host does not interpret wikilinks
as executable dependencies or compile prose into a branch table. `Promise.all`,
`allSettled`, loops, and data transformations come from JavaScript. A model receives
an observation, reasons with it, then writes its next program fragment. An optional
authored utility can perform a stable computation, but the example's conditional
investigation logic belongs to the agent's generated PTC.

## 3. Prose-driven skills and optional utilities

An agent node has `library.kind: agent` (the default), prose, and wikilinks. All
example nodes except `delta_check` have this form. There is no JavaScript body to
execute from their skill files. `DeepAgentRunner` creates a fresh agent and mutable
interpreter state for every invocation/repair attempt. The model receives its
objective, inputs, selected refs, entry packet, and repair feedback and writes PTC.
It does not inherit the parent's conversation or JavaScript globals. `StateBackend`
provides private scratch, not shared POSIX files or a real shell.

A skill author may optionally bundle a stable utility. The example's delta check
is packaged as a separate code node so it can use the existing `run_node` operation:

```yaml
---
name: delta_check
library:
  kind: code
  script: scripts/observe_delta.js
---
```

The script contains only input validation, numeric subtraction, and output
submission. It contains no fan-out, scenario selection, or decision to investigate.
The agent in `b` writes the invocation code and observes the result before deciding
whether to call `k` and `l`. Packaging a utility this way is optional; it is not a
requirement for writing skills or invoking agent nodes.

`Registry.load` pins both prose and script bytes. A bundled script must be a
JavaScript file within the node's directory; escaping paths and symlinks are
rejected. A code node may alternatively use one inline `node-js` body for backward
compatibility, but cannot declare both sources. No example SKILL.md embeds code.

`CodeRunner` executes the pinned utility with `input`, `refs`, and invocation
`context` bound as data plus the four host capabilities. It provides no OS,
Python evaluation, network, or filesystem access. Memory and execution-time limits
apply, and the session deadline bounds host-call waits. Reading a skill does not
execute its script automatically.

`read_node(..., enter=True)` lets the current agent adopt a linked procedure
inline and accumulate its obligations. It does not start another agent. Separate
execution uses `run_node`.

## 4. Reviews are nodes

`red_team` and `artifact_coherence` use normal node invocation and publication.
Their `profile: critic` restricts evidence access. They are fresh agent nodes in
the demo; deterministic validators could instead be code nodes.

Optional review choreography belongs to the agent's program. In the example,
root audits produced `a`, `b`, and (if present) `c` separately, checks their joint
coherence, and requests a red-team assessment of `a`. Failed verdicts result in a
blocked report without a thesis. The report can be accepted because it truthfully
reports the blocked investigation. Optional findings are not automatically a host
publication veto.

A node may separately declare mandatory reviewers:

```yaml
library:
  kind: agent
  review:
    critics: [red_team]
    max_revisions: 0
```

The host freezes the exact candidate, invokes the same reviewer-node API, and
checks `candidate_ref`, `verdict`, and `findings`. Only a well-formed `pass` without
unresolved findings satisfies a required check. `fail`, `inconclusive`, exceptions,
and malformed output cannot pass. A repair creates a new candidate and requires
new reviews. Reviewer nodes cannot themselves declare mandatory reviewers in this
version, but may make ordinary bounded node calls.

A review's accepted *receipt* means its own execution/publication completed. The
review's `content.verdict` describes the candidate. An accepted review can contain
a failing verdict. Coherence checks bind an exact target set; individual passes
do not imply consistency of a set or of a later synthesis.

## 5. Evidence scope and trace

Normal workers can read accepted artifacts within the current session and receive
eligible one-hop results during node inspection. Drafts require ownership or an
explicit grant. Critic frames and all their descendants additionally require a
grant for accepted artifacts. The entry-context path applies the same restriction
and omits ambient memory notes for critics. Mandatory reviewers receive the exact
draft and its declared `based_on` evidence; they cannot widen those grants by
changing node names or reading another procedure inline.

The host records invocation identity, parent, node kind/revision, input refs,
explicit artifact reads, lifecycle, accepted output, and review receipts. Agent
runners also save returned tool actions and bounded observations at completion.
These records contain no hidden reasoning, but can contain supplied evidence and
should be treated as session data. They are inspection records, not crash-resume
checkpoints. Actions from a runner that fails before returning may lack a complete
agent-action trace; admission and lifecycle events still exist.

`input_refs`, explicitly `observed_refs`, and declared `based_on` remain distinct.
Their presence does not prove that every causal influence was tracked, or make an
LLM invocation a pure cacheable function. Source corrections require a new bound
snapshot and rerun. There is no automatic invalidation engine in this reference.

## 6. Reproducible graph

Choose an execution mode explicitly:

- `python demo.py --model provider:model-name --case a`: the real model reads
  prose and observations and generates PTC for all agent nodes. The scripted
  fixture module is not imported. Provider setup is required.
- `python demo.py --offline --case a`: an offline model double selects prewritten
  PTC fragments after actual observations. This checks mechanics; it does not
  demonstrate new code being generated by an LLM.

Both paths use the same prose skill graph and optional delta utility. Reports
record `execution_mode` and `ptc_origin`; the CLI has no implicit scripted fallback.

| Observation | Example next work |
| --- | --- |
| `b` reads nonzero delta | `k` and `l` concurrently, then return to parent |
| `b` reads unchanged snapshot | Return without `k` or `l` |
| Root reads accelerating-demand narrative from `b` | `c` and `d` concurrently |
| Root reads stable-demand narrative from `b` | `h` |
| Root reads concentration concern from `d` | `f` and `g` concurrently |
| Root reads pending regulation from `h` | `i` |
| Any optional review fails | Blocked report; no thesis |
| Optional reviews pass | `thesis`, then required fresh review of its candidate |

These fixture expectations test paths and observation boundaries. They do not
establish real-model semantic reliability. All data is synthetic. The tests also
exercise missing/incorrect/inconclusive reviews, candidate rebinding, same-session
critic isolation, inherited restrictions, code-only composition, limits,
cancellation, idempotent retries, and source revision changes.

## 7. Migration

From the first node-runtime demo: research leaves are now agent nodes with prose,
not authored code bodies. The only bundled code example is the delta utility,
whose source moved to `skills/delta_check/scripts/observe_delta.js`. The test double
moved to `examples/scripted_model.py`. Add `--offline` to offline demo commands or
choose `--model`; Python callers similarly pass `offline=True` or `model=...`.


| Previous API | Current API |
| --- | --- |
| `kernel.Kernel` | `runtime.Runtime` |
| `Call(skill=...)` | `NodeRequest(node=...)` |
| `Skill` | `Node`, with `kind` and optional pinned code |
| `kernel.call(...)` | `runtime.run_node(...)` |
| `kernel.runner` | `runtime.agent_runner`; code uses `runtime.code_runner` |
| `libraryOpen` | `readNode`; explicit `enter:true` for old inline activation |
| `libraryRead` | `readArtifact` |
| `librarySubmit` | `submitCandidate` |
| RLM-named helper / PTC `task()` | `tools.runNode({request})` |

This refactor intentionally changes the small reference API and artifact envelope
(`skill` becomes `node`). Existing external callers and old persisted records need
migration; use a fresh store for the demo. Prior docs and their benchmark counts
are historical. The provider proxy counts model operations rather than exact
billable attempts or currency. The in-memory job/grant ledger is not recovered
after restart, and there is no cross-session reuse, effect gateway, or production
authorization backend. Required review still returns unresolved status when its
bounded allowance cannot complete the protocol.
