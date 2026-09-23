# Callable node harness

Run a linked skill node as code or as an agent in fresh context. The parent uses
ordinary JavaScript and programmatic tool calls to inspect nodes, compose work,
observe artifacts, and choose its next action. Red teaming and coherence audits
are ordinary nodes. `run_node` is the execution primitive; no recursive-language-
model abstraction or graph compiler is required.

## Run the reproducible example

Python 3.11+:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt
python demo.py --case a
python demo.py --case b
python demo.py --case unchanged
python demo.py --case incoherent
python -m unittest -v test_runtime test_integration test_demo
```

The default example uses actual Deep Agents, QuickJS, and the host runtime with an
observation-driven model double. It needs no API credentials and makes no model
API calls. The fixture model reads actual tool observations before choosing its
next PTC fragment. Its small rules live only in `examples/demo_model.py`; they are
not a semantic reasoning engine or a claim about real-model quality.

The graph follows the example discussed in the design:

- Root runs `a` and `b` concurrently.
- Inside `b`, the code node `delta_check` computes the change. The agent observes
  it, returns early if unchanged, or runs `k` and `l` concurrently.
- After observing `b`, root chooses `c`/`d` or `h`. After observing `d` or `h`, it
  may run `f`/`g` or `i`.
- Fresh `artifact_coherence` calls inspect `a`, `b`, and `c` when present, plus
  their joint consistency. A fresh `red_team` node challenges `a`.
- Passing audits lead to `thesis`, whose exact final candidate has its own
  mandatory `red_team` check. Failed optional audits produce a blocked report.

| Case | Expected path / result |
| --- | --- |
| `a` | `b -> delta_check -> k/l`; root chooses `c/d -> f/g`; reviewed thesis |
| `a-no-e` | `c/d` with no `f/g`; reviewed thesis |
| `b` | `h -> i`; no fabricated `c` audit |
| `b-no-j` | `h` without `i` |
| `unchanged` | `b` omits `k/l`; root continues through `h/i` |
| `incoherent` | Joint audit finds USD/JPY mismatch; blocked report, no thesis |
| `unsupported` | Red team finds a seeded unsupported claim; blocked report |

To save the executed PTC and observations, use `--trace outputs/trace.json`.
Artifacts have immutable refs, so their identifiers vary across runs. `accepted`
means an artifact completed its publication protocol. A blocked investigation
report, or a review with `verdict: "fail"`, can itself be accepted.

## Four host capabilities

```js
// Inspect without executing; enter:true adopts the procedure in this frame.
const node = await tools.readNode({node: "b"});

// Agent nodes use fresh context; code nodes execute without a model call.
const result = await tools.runNode({request: {
  node: "b", task: "Assess the supplied state", inputs,
  key: "b:initial", refs: []
}});

const observation = await tools.readArtifact({ref: result.ref, limit: 4000});

await tools.submitCandidate({
  summary: "Conclusion", content: { /* result */ }, based_on: [result.ref]
});
```

These functions are also native tools (`read_node`, `run_node`, `read_artifact`,
`submit_candidate`) and share the same frame-bound `NodeAPI`. `Promise.all`, loops,
conditionals, and transformations are ordinary code. The framework's legacy native
`task` route remains a supervised compatibility path; the PTC task bridge is off.

A code node is a `SKILL.md` with `library.kind: code` and one `node-js` fenced body.
That body runs in its own QuickJS context with `input`, `refs`, `context`, and the
same four `tools` capabilities. Its source is part of the node revision. See
[`skills/delta_check/SKILL.md`](skills/delta_check/SKILL.md). Agent nodes use
`library.kind: agent`, ordinary prose and wikilinks. Reading links never runs them.

## Real model execution

```sh
python demo.py --case a --model provider:model-name
```

Install the chosen LangChain provider integration if needed and configure its
credentials. This option makes billable model calls. The same skill prose,
code nodes, runtime, and publication gates are used; the fixture model is replaced.
The CLI path is provided, but live-provider behavior and semantic performance have
not been validated by the offline suite. Provider retry, usage, streaming, and
budget behavior require deployment-specific checks.

## Code map

| File | Responsibility |
| --- | --- |
| `runtime.py` | Node registry, invocation frames, admission, artifact access, lineage, required reviews |
| `node_api.py` | Shared frame-bound inspection, execution, reads, and candidate submission |
| `code_runner.py` | Pinned JavaScript node execution with zero model calls |
| `deepagents_adapter.py` | Fresh agent contexts, PTC/native tools, model-operation metering |
| `demo.py` | CLI wiring for offline or live-model demonstration |
| `examples/` | Synthetic inputs and observation-driven model double |
| `skills/` | The complete example graph, including code and review nodes |
| `test_runtime.py` | Lifecycle, idempotency, grants, budgets, review failures |
| `test_integration.py` | Real interpreter and native execution through the same API |
| `test_demo.py` | Branch coverage, audit failures, code composition, source pinning, timeout |

The current [execution contract and migration guide](docs/dynamic-skill-ptc-design.md)
is the implementation reference. Earlier [design](docs/library-harness-design.md)
and [red-team assessment](docs/node-composition-red-team-plan.md) are historical
context. Their old API examples are superseded. The obsolete Windows document
renderer, generated diagram, old test logs, and old three-node example were retired.
`python tools/package_deliverables.py` packages the current source and documentation.

## Scope

This is a single-process reference. Immutable records and trace events persist in
SQLite, but active frames, grants, budgets, and operation-key state are not restored
after a crash. There is no cross-session cache, automatic dependency invalidation,
production effects gateway, or OS shell backend. Normal workers can consult eligible
accepted results in their session; critics and their descendants can access only
explicitly granted artifacts and their own outputs. New knowledge is pinned at
registry load; the registry expects a trusted skill repository.

The model-operation ledger is not an exact token/currency budget, and fresh context
does not establish statistically independent reviews. Observed reads and declared
`based_on` refs are recorded separately; neither proves complete semantic lineage.
The interpreter and application APIs enforce the documented local boundaries;
production authorization, external effects, and durable recovery need deployment
adapters. No claim of task correctness follows from an accepted receipt alone.
