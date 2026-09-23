"""Offline integration: actual Deep Agents and QuickJS, scripted model, no API calls."""

import json
import unittest
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from examples.review import ReviewedTransformation
from harness import Ledger, NodeRequest, Registry, Runtime, Store
from harness.runners.agent import DeepAgentRunner
from harness.runners.code import CodeRunner
from harness.runners.metering import metered_model
from tests.support import code_skill, skill


class ScriptedModel(BaseChatModel):
    responses: list[Any]
    index: int = 0

    @property
    def _llm_type(self):
        return "scripted-library-test"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        value = self.responses[self.index]
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=value)])


class CapturingModel(ScriptedModel):
    prompts: list[Any] = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts.append([(m.type, m.content) for m in messages])
        return super()._generate(messages, stop, run_manager, **kwargs)


def eval_response(code):
    return AIMessage(
        content="", tool_calls=[{"name": "eval", "args": {"code": code}, "id": "eval-1"}]
    )


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_agent_calls_share_stable_prefix_without_sharing_history(self):
        runtime = Runtime(Registry([skill("work")]), Store())
        self.addCleanup(runtime.store.close)
        self.addAsyncCleanup(runtime.aclose)
        models = []

        def factory(frame):
            model = CapturingModel(
                responses=[
                    eval_response(
                        "await tools.submitCandidate({summary:'Done',content:{ok:true},based_on:[]});"
                    ),
                    AIMessage(content="Private response from " + frame.request.task),
                ]
            )
            models.append(model)
            return metered_model(model, runtime.ledger)

        runtime.register_executor("agent", DeepAgentRunner(runtime, factory))
        for task in ("baseline", "capacity"):
            await runtime.run_node(NodeRequest("work", task, {"snapshot": 42}, task))
        first, second = [model.prompts[0] for model in models]
        self.assertEqual(first[:-1], second[:-1])
        self.assertNotEqual(first[-1], second[-1])
        self.assertFalse(any(kind in ("ai", "tool") for kind, _ in second))
        packets = [json.loads(content) for kind, content in second if kind == "human"]
        self.assertEqual(len(packets), 3)
        self.assertIn("entry", packets[0])
        self.assertEqual(packets[1], {"inputs": {"snapshot": 42}, "refs": []})
        self.assertEqual(packets[2]["task"], "capacity")
        self.assertEqual(runtime.ledger.frames, 2)

    async def test_real_interpreter_review_repair_loop(self):
        registry = Registry([skill("release"), skill("work"), skill("critic")])
        kernel = Runtime(registry, Store(), bindings={"release": "reviewed"})
        self.addCleanup(kernel.store.close)
        self.addAsyncCleanup(kernel.aclose)
        kernel.register_executor(
            "reviewed", ReviewedTransformation(kernel, "work", "critic", max_revisions=1)
        )
        attempts = []

        def factory(frame):
            if frame.request.node == "critic":
                candidate = json.dumps(frame.request.refs[0])
                code = """
const slice = await tools.readArtifact({ref: CANDIDATE, limit: 16000});
const candidate = JSON.parse(slice.text);
const ok = candidate.content.value === 1;
await tools.submitCandidate({summary: 'Checked', content: {
  candidate_ref: CANDIDATE, verdict: ok ? 'pass' : 'fail',
  findings: ok ? [] : ['Expected value one']
}, based_on: []});
""".replace("CANDIDATE", candidate)
            else:
                value = len(attempts)
                attempts.append(value)
                code = f"await tools.submitCandidate({{summary:'Draft',content:{{value:{value}}},based_on:[]}});"
            return metered_model(
                ScriptedModel(responses=[eval_response(code), AIMessage(content="Staged")]),
                kernel.ledger,
            )

        kernel.register_executor("agent", DeepAgentRunner(kernel, factory, interpreter_timeout=30))
        result = await kernel.run_node(NodeRequest("release", "produce", {}, "root"))
        self.assertEqual(result["status"], "published")
        self.assertEqual(attempts, [0, 1])
        self.assertEqual(kernel.ledger.model_calls, 8)
        self.assertEqual(kernel.store.get(result["ref"])["content"]["result"]["value"], 1)

    async def test_real_interpreter_recursive_dispatch_and_submission(self):
        registry = Registry([skill("work")])
        kernel = Runtime(registry, Store(), ledger=Ledger(model_parallelism=1))

        def factory(frame):
            depth = frame.request.inputs["n"]
            if depth:
                child_request = json.dumps(
                    {
                        "node": "work",
                        "task": f"depth {depth - 1}",
                        "inputs": {"n": depth - 1},
                        "key": "child",
                    }
                )
                code = """
const receipt = await tools.runNode({request: REQUEST});
if (receipt.status !== "published") throw new Error("Child did not pass");
await tools.submitCandidate({summary: "Joined child", content: {depth: DEPTH}, based_on: [receipt.ref]});
""".replace("REQUEST", child_request).replace("DEPTH", str(depth))
            else:
                code = "await tools.submitCandidate({summary: 'Leaf', content: {depth: 0}, based_on: []});"
            return metered_model(
                ScriptedModel(responses=[eval_response(code), AIMessage(content="Staged")]),
                kernel.ledger,
            )

        kernel.register_executor("agent", DeepAgentRunner(kernel, factory, interpreter_timeout=30))
        result = await kernel.run_node(NodeRequest("work", "depth 2", {"n": 2}, "root"))
        self.assertEqual(result["status"], "published")
        self.assertEqual(kernel.ledger.frames, 3)
        self.assertEqual(kernel.ledger.model_calls, 6)
        record = kernel.store.get(result["ref"])
        self.assertEqual(len(record["based_on"]), 1)
        child = kernel.store.get(record["based_on"][0])
        self.assertEqual(child["origin"], record["frame"])
        self.assertNotEqual(child["frame"], record["frame"])

    async def test_native_run_node_uses_same_supervisor(self):
        kernel = Runtime(Registry([skill("work")]), Store())

        def factory(frame):
            responses = []
            if not frame.origin:
                request = {"node": "work", "task": "child", "inputs": {}, "key": "child"}
                responses.append(
                    AIMessage(
                        content="",
                        tool_calls=[
                            {"name": "run_node", "id": "native-1", "args": {"request": request}}
                        ],
                    )
                )
            responses += [
                eval_response(
                    "await tools.submitCandidate({summary:'Result',content:{ok:true},based_on:[]});"
                ),
                AIMessage(content="Staged"),
            ]
            return metered_model(ScriptedModel(responses=responses), kernel.ledger)

        kernel.register_executor("agent", DeepAgentRunner(kernel, factory, interpreter_timeout=30))
        result = await kernel.run_node(NodeRequest("work", "root", {}, "root"))
        self.assertEqual(result["status"], "published")
        self.assertEqual(kernel.ledger.frames, 2)
        self.assertEqual(kernel.ledger.model_calls, 5)

    async def test_code_node_can_invoke_fresh_agent(self):
        parent = code_skill(
            "program",
            """
globalThis.parentSecret = 'private';
const child = await tools.runNode({request:{node:'worker',task:'fresh worker',inputs:{},key:'child',refs:[]}});
await tools.submitCandidate({summary:'Program joined agent',content:{ok:true},based_on:[child.ref]});
""",
        )
        runtime = Runtime(
            Registry([parent, skill("worker")]), Store(), bindings={"program": "code"}
        )
        runtime.register_executor("code", CodeRunner(runtime, "run.js"))

        def factory(frame):
            code = """
if (typeof parentSecret !== 'undefined') throw new Error('Context inherited');
await tools.submitCandidate({summary:'Fresh worker',content:{ok:true},based_on:[]});
"""
            return metered_model(
                ScriptedModel(responses=[eval_response(code), AIMessage(content="Staged")]),
                runtime.ledger,
            )

        runtime.register_executor("agent", DeepAgentRunner(runtime, factory))
        result = await runtime.run_node(NodeRequest("program", "compose", {}, "root"))
        self.assertEqual(result["status"], "published")
        self.assertEqual(runtime.ledger.frames, 2)
        self.assertEqual(runtime.ledger.model_calls, 2)

    async def test_nested_ptc_transformations(self):
        root = code_skill(
            "root",
            """
let key = 0;
const invoke = (node, artifacts = []) => nodes.run({
  node, task: 'Apply ' + node, inputs: {}, refs: artifacts.map(x => x.ref), key: String(++key)
});
const [a, c, d, e] = await Promise.all([
  invoke('a'), invoke('c'), invoke('d'), invoke('e')
]);
const [reviewed, challenged, combined] = await Promise.all([
  invoke('review', [a]),
  invoke('red_team', [a]),
  invoke('coherence', [c, d, e]).then(value => invoke('node_a', [value]))
]);
await tools.submitCandidate({summary:'Composed transforms',content:{
  reviewed: reviewed.ref, challenged: challenged.ref, combined: combined.ref
},based_on:[reviewed.ref, challenged.ref, combined.ref]});
""",
        )
        names = ("a", "c", "d", "e", "review", "red_team", "coherence", "node_a")
        runtime = Runtime(
            Registry([root, *(skill(name) for name in names)]), Store(), bindings={"root": "code"}
        )
        self.addCleanup(runtime.store.close)
        self.addAsyncCleanup(runtime.aclose)
        runtime.register_executor("code", CodeRunner(runtime, "run.js"))

        async def transform(frame, context):
            values = [runtime.read(frame, ref)["content"] for ref in frame.request.refs]
            node = frame.request.node
            if node in ("a", "c", "d", "e"):
                content = {"value": {"a": 0, "c": 1, "d": 2, "e": 3}[node]}
            elif node == "review":
                content = {"verdict": "fail", "findings": ["Zero value"]}
            elif node == "red_team":
                content = {"counterexample": values[0]["value"]}
            elif node == "coherence":
                content = {"sum": sum(value["value"] for value in values)}
            else:
                content = {"value": values[0]["sum"] * 10}
            return {"summary": node, "content": content, "based_on": list(frame.request.refs)}

        runtime.register_executor("agent", transform)
        receipt = await runtime.run_node(NodeRequest("root", "Compose", {}, "root"))
        result = runtime.store.get(receipt["ref"])["content"]
        self.assertEqual(runtime.store.get(result["combined"])["content"], {"value": 60})
        review, challenge = [runtime.store.get(result[key]) for key in ("reviewed", "challenged")]
        self.assertEqual(review["content"]["verdict"], "fail")
        self.assertEqual(review["based_on"], challenge["based_on"])
        self.assertEqual(runtime.ledger.frames, 9)
        self.assertEqual(runtime.ledger.model_calls, 0)

    async def test_legacy_native_task_still_enters_runtime(self):
        runtime = Runtime(Registry([skill("work")]), Store())

        def factory(frame):
            responses = []
            if frame.origin is None:
                request = {"node": "work", "task": "child", "inputs": {}, "key": "child"}
                responses.append(
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "task",
                                "id": "legacy",
                                "args": {
                                    "description": json.dumps(request),
                                    "subagent_type": "general-purpose",
                                },
                            }
                        ],
                    )
                )
            responses += [
                eval_response(
                    "await tools.submitCandidate({summary:'Result',content:{ok:true},based_on:[]});"
                ),
                AIMessage(content="Staged"),
            ]
            return metered_model(ScriptedModel(responses=responses), runtime.ledger)

        runtime.register_executor("agent", DeepAgentRunner(runtime, factory))
        await runtime.run_node(NodeRequest("work", "root", {}, "root"))
        admitted = [e for e in runtime.store.events() if e["type"] == "admitted"]
        self.assertEqual(len(admitted), 2)
        self.assertEqual(admitted[1]["origin"], admitted[0]["frame"])


if __name__ == "__main__":
    unittest.main()
