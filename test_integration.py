"""Offline integration: actual Deep Agents and QuickJS, scripted model, no API calls."""
import json
import unittest
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from deepagents_adapter import DeepAgentRunner, metered_model
from code_runner import CodeRunner
from runtime import NodeRequest, Runtime, Ledger, Registry, Review, Node, Store


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


def eval_response(code):
    return AIMessage(content="", tool_calls=[{"name": "eval", "args": {"code": code}, "id": "eval-1"}])


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_interpreter_review_repair_loop(self):
        registry = Registry([Node("work", "# Work", "v1", review=Review(("critic",), 1)),
                             Node("critic", "# Critic", "v1", critic=True)])
        kernel = Runtime(registry, Store())
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
            return metered_model(ScriptedModel(responses=[eval_response(code), AIMessage(content="Staged")]), kernel.ledger)

        kernel.agent_runner = DeepAgentRunner(kernel, factory, interpreter_timeout=30)
        result = await kernel.run_node(NodeRequest("work", "produce", {}, "root"))
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(attempts, [0, 1])
        self.assertEqual(kernel.ledger.model_calls, 8)
        self.assertEqual(kernel.store.get(result["ref"])["content"]["value"], 1)

    async def test_real_interpreter_recursive_dispatch_and_submission(self):
        registry = Registry([Node("work", "# Work\nProduce a result", "v1")])
        kernel = Runtime(registry, Store(), ledger=Ledger(model_parallelism=1))

        def factory(frame):
            depth = frame.request.inputs["n"]
            if depth:
                child_request = json.dumps({"node": "work", "task": f"depth {depth - 1}",
                                            "inputs": {"n": depth - 1}, "key": "child"})
                code = """
const receipt = await tools.runNode({request: REQUEST});
if (receipt.status !== "accepted") throw new Error("Child did not pass");
await tools.submitCandidate({summary: "Joined child", content: {depth: DEPTH}, based_on: [receipt.ref]});
""".replace("REQUEST", child_request).replace("DEPTH", str(depth))
            else:
                code = "await tools.submitCandidate({summary: 'Leaf', content: {depth: 0}, based_on: []});"
            return metered_model(ScriptedModel(responses=[eval_response(code), AIMessage(content="Staged")]), kernel.ledger)

        kernel.agent_runner = DeepAgentRunner(kernel, factory, interpreter_timeout=30)
        result = await kernel.run_node(NodeRequest("work", "depth 2", {"n": 2}, "root"))
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(kernel.ledger.frames, 3)
        self.assertEqual(kernel.ledger.model_calls, 6)
        record = kernel.store.get(result["ref"])
        self.assertEqual(len(record["based_on"]), 1)
        child = kernel.store.get(record["based_on"][0])
        self.assertEqual(child["parent"], record["frame"])
        self.assertNotEqual(child["frame"], record["frame"])

    async def test_native_run_node_uses_same_supervisor(self):
        kernel = Runtime(Registry([Node("work", "# Work", "v1")]), Store())

        def factory(frame):
            responses = []
            if not frame.parent:
                request = {"node": "work", "task": "child", "inputs": {}, "key": "child"}
                responses.append(AIMessage(content="", tool_calls=[{
                    "name": "run_node", "id": "native-1", "args": {
                        "request": request}}]))
            responses += [eval_response("await tools.submitCandidate({summary:'Result',content:{ok:true},based_on:[]});"),
                          AIMessage(content="Staged")]
            return metered_model(ScriptedModel(responses=responses), kernel.ledger)

        kernel.agent_runner = DeepAgentRunner(kernel, factory, interpreter_timeout=30)
        result = await kernel.run_node(NodeRequest("work", "root", {}, "root"))
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(kernel.ledger.frames, 2)
        self.assertEqual(kernel.ledger.model_calls, 5)

    async def test_code_node_can_invoke_fresh_agent(self):
        parent = Node('program', '# Program', 'v1', kind='code', code="""
globalThis.parentSecret = 'private';
const child = await tools.runNode({request:{node:'worker',task:'fresh worker',inputs:{},key:'child',refs:[]}});
await tools.submitCandidate({summary:'Program joined agent',content:{ok:true},based_on:[child.ref]});
""")
        runtime = Runtime(Registry([parent, Node('worker','# Worker','v1')]), Store())
        runtime.code_runner = CodeRunner(runtime)
        def factory(frame):
            code = """
if (typeof parentSecret !== 'undefined') throw new Error('Context inherited');
await tools.submitCandidate({summary:'Fresh worker',content:{ok:true},based_on:[]});
"""
            return metered_model(ScriptedModel(responses=[eval_response(code),AIMessage(content='Staged')]),runtime.ledger)
        runtime.agent_runner = DeepAgentRunner(runtime,factory)
        result = await runtime.run_node(NodeRequest('program','compose',{},'root'))
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(runtime.ledger.frames,2)
        self.assertEqual(runtime.ledger.model_calls,2)

    async def test_legacy_native_task_still_enters_runtime(self):
        runtime = Runtime(Registry([Node('work','# Work','v1')]),Store())
        def factory(frame):
            responses=[]
            if frame.parent is None:
                request={'node':'work','task':'child','inputs':{},'key':'child'}
                responses.append(AIMessage(content='',tool_calls=[{'name':'task','id':'legacy','args':{
                    'description':json.dumps(request),'subagent_type':'general-purpose'}}]))
            responses += [eval_response("await tools.submitCandidate({summary:'Result',content:{ok:true},based_on:[]});"),AIMessage(content='Staged')]
            return metered_model(ScriptedModel(responses=responses),runtime.ledger)
        runtime.agent_runner=DeepAgentRunner(runtime,factory)
        await runtime.run_node(NodeRequest('work','root',{},'root'))
        admitted=[e for e in runtime.store.events() if e['type']=='admitted']
        self.assertEqual(len(admitted),2)
        self.assertEqual(admitted[1]['parent'],admitted[0]['frame'])


if __name__ == "__main__":
    unittest.main()
