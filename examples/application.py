"""Example host choices. Adding expertise does not add fields to Skill."""

from pathlib import Path

from harness import Registry, ReviewPolicy, Runtime, Store
from harness.runners.agent import DeepAgentRunner
from harness.runners.code import CodeRunner
from harness.runners.metering import metered_model

ROOT = Path(__file__).resolve().parents[1]


def build_runtime(
    *, model: str | None = None, offline: bool = False, store: Store | None = None
) -> Runtime:
    if bool(model) == bool(offline):
        raise ValueError("Choose exactly one: model=provider:model or offline=True")
    runtime = Runtime(
        Registry.load(ROOT / "skills"),
        store if store is not None else Store(),
        bindings={"delta_check": "snapshot_math"},
        reviews={"thesis": ReviewPolicy(("red_team",))},
        deadline_seconds=240,
    )

    def model_factory(frame):
        if model:
            from langchain.chat_models import init_chat_model

            base = init_chat_model(model, max_retries=0)
        else:
            from examples.scripted_model import ScriptedFixtureModel

            base = ScriptedFixtureModel(
                node=frame.request.node,
                task=frame.request.task,
                request_inputs=frame.request.inputs,
                refs=list(frame.request.refs),
            )
        return metered_model(base, runtime.ledger)

    runtime.register_executor(
        "agent", DeepAgentRunner(runtime, model_factory, interpreter_timeout=60)
    )
    runtime.register_executor("snapshot_math", CodeRunner(runtime, "scripts/observe_delta.js"))
    return runtime


def prompt_for(case: str) -> str:
    scenario = "b" if case in ("b", "b-no-proposal", "unchanged") else "a"
    return (
        (ROOT / "examples" / "prompts" / f"scenario_{scenario}.md")
        .read_text(encoding="utf-8")
        .strip()
    )
