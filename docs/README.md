# Architecture guide

Read these maintained documents in order to carry the project into another session:

1. [Design](design.md): first principles, skill graph, execution boundaries and decisions.
2. [Runtime and primitives](runtime.md): exact contracts, ownership, sharing, progress,
   cancellation, authority, adapters, limits and source map.
3. [Patterns](patterns.md): nested transformations, converging graphs, streaming,
   audits, bounded repair and safe races with the current API.
4. [Evolution and memory](evolution-and-memory.md): deferred extensions, risks and acceptance gates.
5. [Adversarial review](review-findings.md): findings, accepted/rejected suggestions and verification.

Supporting guides: [skill authoring](authoring-skill-graphs.md) and
[edge cases/KV cache](edge-cases-and-kv-cache.md). The
[two prompts and executed trajectories](../README.md#two-prompts-and-two-executed-trajectories)
show actual offline Deep Agents/QuickJS behavior.

Older document paths redirect to these guides. The original `new_doc.md` proposal
is preserved in [the archive](archive/2026-09-25-proposal.md), explicitly non-normative.
