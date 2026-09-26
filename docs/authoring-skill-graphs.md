# Authoring skill graphs

The local package contract is `skills/<canonical-name>/SKILL.md` with exactly
`name` and `description` in YAML frontmatter. The name matches the relative package
path. Description and body must be nonempty; duplicate/unknown keys are rejected.
This is this repository's convention, not a claim about every skill ecosystem.

Put the procedure, expected evidence, output schema, limits and conditional routes
in prose. A link such as `[[b|inspect the neutral snapshot]]` points to skill b with
a human-readable label. The parser retains the target before `|` and any `#` anchor;
the full prose retains the label. Labels do not become task text, arguments, keys,
permissions or automatic edges. Wikilinks inside fenced code examples do not add
registry edges. Every derived target must exist in the loaded registry.

A link makes a procedure discoverable. The harness agent decides whether to invoke
it and writes explicit NodeRequests in PTC. Multiple skills can reference the same
skill with different prose. Reuse occurs only if their actual requests opt into
session sharing and match the exact task, inputs and ordered refs. Document neutral
producer questions consistently when convergence is intentional.

Make a real graph where shared evidence is useful: a and c can reference b, b can
reference k/l, and h can also reference l. Nesting directories does not create runtime
parent/child relationships. Cycles in prose are allowed; execution cycles and excessive
active depth are rejected. Describe stopping conditions for recursive decomposition.

Use an optional pinned resource for deterministic computation or supporting data.
Resources are immutable bytes in the registry revision, not hidden mutable programs.
Nested skill packages own their own files. Symlinks, path traversal, duplicate resource
paths and files over the package limit are rejected. Avoid embedding orchestration
programs in every skill: most skills here contain prose and links; the harness writes
live PTC. Scripted model fixtures exist solely to make offline tests reproducible.

Review and coherence skills are ordinary transformations. Define their content schema
in prose and test the application that interprets it. Adding a reviewer or specialized
agent does not require a role, review policy or executor field in frontmatter. Register
executor bindings in the host application. Published status means availability only.

Verify authoring with the actual repository commands:

```sh
python -m unittest tests.test_skills tests.test_review_composition -v
python demo.py --offline --case a --trace outputs/scenario_a.json
python demo.py --offline --case b --trace outputs/scenario_b.json
python -m examples.export_trajectories
```

`Registry.load(Path('skills'))` validates package structure and link targets. Runtime
entry loading additionally enforces the serialized packet limit. The repo does not
provide the proposed `tools/check_skills.py` or `tools/run_skill_cases.py`; no guide
should claim those commands work. Existing demo fixtures cover named scenarios,
not arbitrary prose paraphrases or live-model judgment quality.
