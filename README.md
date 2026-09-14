# Library harness reference implementation

This package makes the proposed boundary executable: graph-aware skill entry,
recursive supervised agent calls, external intermediate state, and mandatory
bounded reviews before acceptance. Read `../library-harness-design.md` for the
complete architecture, migration decisions, and deployment contracts.

## Run the offline integration

Use Python 3.11 or later in a virtual environment:

```shell
python -m pip install -r requirements.txt
python -m unittest -v test_kernel test_integration
```

The integration uses the actual Deep Agents and QuickJS packages with scripted
models. It needs no API credentials and makes no model API requests. It verifies
nested interpreter dispatch, native task dispatch, and host publication.

## Connect a model

```python
from pathlib import Path
from langchain.chat_models import init_chat_model
from kernel import Call, Kernel, Registry, Store
from deepagents_adapter import DeepAgentRunner, metered_model

kernel = Kernel(Registry.load(Path('.')), Store('session.sqlite'))

def model_factory(frame):
    # Select an approved provider/model in your deployment configuration.
    base = init_chat_model(APPROVED_MODEL_ID, max_retries=0)
    return metered_model(base, kernel.ledger)

kernel.runner = DeepAgentRunner(kernel, model_factory)
receipt = await kernel.call(Call(
    skill='decision', task='Assess the supplied evidence',
    inputs={'as_of': '2026-09-13', 'scope': 'example'}, key='root',
))
```

`APPROVED_MODEL_ID` is application configuration, not a supplied model choice.
Provider adapters may use different timeout, output-token, and retry parameters.
Validate the proxy against your provider's tool binding, profile, streaming,
structured output, usage, and prompt-caching behavior before live deployment.
The current runner uses staged tool output instead of model structured output.

## Interpreter surface

```javascript
async function rlm(request) {
  const raw = await task({
    subagentType: "general-purpose",
    description: JSON.stringify(request)
  });
  return typeof raw === "string" ? JSON.parse(raw) : raw;
}

const settled = await Promise.allSettled(items.map((item, i) => rlm({
  skill: "evidence-check",
  task: `Check this bounded item: ${item.text}`,
  inputs: item.scope,
  key: `evidence:${i}`,
  refs: []
})));
const accepted = settled.filter(x =>
  x.status === "fulfilled" && x.value.status === "accepted"
).map(x => x.value);
// Decide explicitly whether missing results permit a partial conclusion.
await tools.librarySubmit({
  summary: "Evidence assessment with explicit coverage",
  content: {covered: accepted.length, total: items.length},
  based_on: accepted.map(x => x.ref)
});
```

`items` is a previously obtained working set, not a built-in global. The adapter
installs `libraryOpen`, `libraryRead`, and `librarySubmit` as PTC-only functions.
`task()` is the native Deep Agents bridge. Do not pass `responseSchema`: a
compiled subagent has a fixed output contract in the pinned version.

## Implemented guarantees

- Every invocation has fresh state and host-assigned parent identity.
- Native and interpreter dispatch share the same admission and review code.
- Model-call permits cover inference only, so waiting parents do not block children.
- Skill entry injects authored text, bounded notes, and eligible one-hop artifacts.
- Inline skill entry registers additional review obligations in the current frame.
- Reviews are bound to immutable candidate references and rerun after repairs.
- Failed, malformed, missing, or wrong-candidate reviews cannot accept a candidate.
- Artifact access checks session identity and draft ownership or explicit grants.
- Exact request retries within this process share one task; conflicting keys fail.
- Parent cancellation closes descendants; session deadlines bound execution.

`accepted` means the configured protocol completed. It is not a guarantee that an
LLM's conclusion is true. The demonstration review validator checks structure and
candidate identity; it does not independently validate findings' scientific truth.

## Deliberate implementation limits

This is a high-level, single-process reference, not a deployed enterprise service.
SQLite retains immutable records and events, but the in-flight task map, ledger,
frame grants, and session identity are not recovered after process restart.
There is no crash-resume or distributed exactly-once claim. The store scans records
for clarity; production retrieval needs indexed manifests and paged queries.

The reference enforces frame counts, model operation counts, depth and a shared
deadline. A model operation can contain provider retries: this count is not an
exact request-attempt, token, or currency bound. Production needs a shared
inference gateway with reservation before every billable attempt, retry control,
usage reconciliation, and accounting for summarization and other hidden calls.

Generated JavaScript runs in the packaged interpreter. The adapter's filesystem
is private scratch in StateBackend; governed skills and published artifacts are
accessible only through the host services. Real shell execution, network tools,
OS isolation, tool authorization, external mutation idempotency, and process
termination need the deployment adapters described in the design.

Registry loading expects a trusted, reviewed skill repository. Add complete
frontmatter schema validation, signed snapshots, symlink policy, authorization,
and token-aware context packing for production. The reference uses conservative
character budgets and exact equality of all inputs for reuse. It does not
implement semantic search, input projection, taxonomy migration, or invalidation
on a source update that keeps the same input timestamp.

Critics cannot themselves require critics in this version. They can perform
ordinary bounded subcalls. Different reviewer skills are separate executions;
statistical independence requires evaluation and potentially different models or
evidence methods. Tool-based deterministic validators are a production extension.

Outer-loop memory consolidation, maintenance identities, effect gateways,
long-running job recovery, an interactive server, and live-provider evaluations
are specified in the design but are not implemented here.

## Files

| File | Purpose |
| --- | --- |
| `kernel.py` | Registry, artifact store, graph entry, supervision, review state machine |
| `deepagents_adapter.py` | PTC functions, supervised compiled worker, model proxy |
| `skills/` | Small governed skill graph with a required critic |
| `test_kernel.py` | Boundary and failure tests without framework dependencies |
| `test_integration.py` | Real framework and interpreter tests with scripted models |
| `requirements.txt` | Direct dependency pins |
| `requirements-lock.txt` | Exact installed Python environment used for verification |

Source inspection baseline: Deep Agents 0.7.13 and langchain-quickjs 0.3.5,
checked September 13, 2026. APIs used by the adapter are public. The package does
not import Deep Agents or QuickJS private helpers.
