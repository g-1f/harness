# Node execution and artifact composition

Status: implemented reference, 2026-09-23. This document supersedes the earlier
RLM-oriented API and the initial proposed runtime-PTC surface. The code under test
is the authority for current behavior; this is a single-process implementation.

## 1. Execution contract

A node is a versioned procedure with prose, links, and an implementation. The
runtime admits an invocation; its implementation produces a candidate; the host
validates and publishes a receipt. Agent execution is one implementation of a node.
Code execution is another and makes no model calls. A fresh agent context is a
property of agent-node invocation, not the definition of all node execution.

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
an observation, reasons with it, then writes its next program fragment. If a node's
local script already defines deterministic control flow, that script executes it.

## 3. Code versus agent nodes

```yaml
---
name: delta_check
library:
  kind: code
---
```

A code node must contain exactly one `node-js` block. `Registry.load` pins the full
skill text, including code, into its revision. `CodeRunner` starts a new QuickJS
runtime with `input`, `refs`, and invocation `context` bound as data, plus the four
host capabilities. It provides no OS, Python evaluation, network, or filesystem
access. Memory and execution-time limits apply; the session deadline also bounds
host-call waits. The runner closes the interpreter when the invocation ends.

An agent node has `library.kind: agent` (the default). `DeepAgentRunner` creates a
fresh agent and mutable interpreter state for every invocation/repair attempt.
The model sees its own objective, inputs, selected refs, entry packet, and repair
feedback. It does not inherit the parent's conversation or JavaScript globals.
`StateBackend` provides private scratch, not shared POSIX files or a real shell.

`read_node(..., enter=True)` lets the current agent use a linked procedure inline.
That does not start another agent. The current frame accumulates the entered
procedure's obligations; opening a code node does not run its body automatically.
Separate execution uses `run_node`.

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

The executable example is `python demo.py --case a`. Its skills express the graph
in prose; the fixture model selects PTC fragments based on actual observations.
It is a model double, not runtime branching logic. `--model provider:model-name`
replaces that double with a real model, subject to provider setup.

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
