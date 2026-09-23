"""End-to-end paths through real Deep Agents and QuickJS with a model double."""

import asyncio
import unittest
from contextlib import redirect_stderr
from io import StringIO

from quickjs_rs import TimeoutError as JSTimeoutError

from demo import parse_args, run_demo
from harness import NodeRequest, Registry, Runtime, Store
from harness.runners.code import CodeRunner
from tests.support import code_skill


class DemoTests(unittest.IsolatedAsyncioTestCase):
    async def test_example_paths_and_contextual_reuse(self):
        branches = {
            "a": {"a", "b", "c", "d", "f", "g"},
            "a-no-e": {"a", "b", "c", "d"},
            "b": {"a", "b", "h", "i"},
            "b-no-j": {"a", "b", "h"},
            "unchanged": {"a", "b", "h", "i"},
        }
        for case, names in branches.items():
            with self.subTest(case=case):
                runtime, receipt = await run_demo(case, offline=True)
                self.addCleanup(runtime.store.close)
                report = runtime.store.get(receipt["ref"])["content"]
                events = runtime.store.events()
                admitted = [e for e in events if e["type"] == "admitted"]
                root = admitted[0]["frame"]
                research = [e for e in admitted if e["node"] in set("abcdefghijkl")]
                direct = {e["node"] for e in research if e["parent"] == root}
                self.assertEqual(direct, names)
                self.assertEqual(report["outcome"], "complete")
                self.assertEqual(report["omitted_c_audit"], "c" not in names)
                self.assertEqual(len(report["audited"]), 3 if "c" in names else 2)
                self.assertEqual(len({e["frame"] for e in admitted}), len(admitted))
                by_node = {
                    name: [e for e in admitted if e["node"] == name]
                    for name in ("a", "b", "c", "k", "l")
                }
                a, b = by_node["a"][0], by_node["b"][0]
                nested_c = next(e for e in by_node["c"] if e["parent"] == a["frame"])
                self.assertTrue(any(e["parent"] == nested_c["frame"] for e in by_node["k"]))
                self.assertTrue(any(e["parent"] == a["frame"] for e in by_node["l"]))
                self.assertEqual(
                    any(e["parent"] == b["frame"] for e in by_node["k"]), case != "unchanged"
                )
                self.assertEqual(len({e["task"] for e in by_node["k"]}), len(by_node["k"]))
                if "c" in names:
                    self.assertEqual(len(by_node["c"]), 2)
                    self.assertNotEqual(by_node["c"][0]["task"], by_node["c"][1]["task"])
                    c_refs = [
                        e["ref"]
                        for e in events
                        if e["type"] == "accepted"
                        and e["frame"] in {c["frame"] for c in by_node["c"]}
                    ]
                    c_results = [runtime.store.get(ref) for ref in c_refs]
                    self.assertEqual(len({r["content"]["scope"] for r in c_results}), 2)
                    self.assertEqual(len({r["node_revision"] for r in c_results}), 1)
                for entry in admitted:
                    actions = [
                        e
                        for e in events
                        if e["type"] == "agent_actions" and e["frame"] == entry["frame"]
                    ]
                    if entry["executor"] == "snapshot_math":
                        self.assertEqual(entry["node"], "delta_check")
                        self.assertEqual(actions, [])
                    else:
                        self.assertTrue(actions)
                thesis = runtime.store.get(report["thesis"])
                self.assertEqual(len(thesis["reviews"]), 1)
                review = runtime.store.get(thesis["reviews"][0])["content"]
                self.assertEqual(
                    runtime.store.get(review["candidate_ref"])["content"], thesis["content"]
                )
                self.assertEqual(review["verdict"], "pass")

    async def test_failed_optional_audit_blocks_thesis(self):
        for case in ("incoherent", "unsupported"):
            with self.subTest(case=case):
                runtime, result = await run_demo(case, offline=True)
                self.addCleanup(runtime.store.close)
                report = runtime.store.get(result["ref"])["content"]
                self.assertEqual(report["outcome"], "blocked")
                self.assertFalse(
                    any(
                        e["type"] == "admitted" and e["node"] == "thesis"
                        for e in runtime.store.events()
                    )
                )
                self.assertTrue(
                    any(
                        runtime.store.get(ref)["content"]["verdict"] == "fail"
                        for ref in report["audits"]
                    )
                )

    async def test_code_executor_can_compose_with_no_model(self):
        leaf = code_skill(
            "leaf",
            """
await tools.submitCandidate({summary: 'Leaf', content: {value: input.n}, based_on: []});
""",
        )
        parent = code_skill(
            "sum",
            """
const parts = await Promise.all([1, 2].map(n => tools.runNode({request: {
  node: 'leaf', task: 'number', inputs: {n}, key: String(n), refs: []
}})));
const values = await Promise.all(parts.map(p => tools.readArtifact({ref: p.ref})));
await tools.submitCandidate({summary: 'Sum', content: {
  value: values.reduce((n, v) => n + JSON.parse(v.text).content.value, 0)
}, based_on: parts.map(p => p.ref)});
""",
        )
        runtime = Runtime(Registry([leaf, parent]), Store(), default_executor="code")
        self.addCleanup(runtime.store.close)
        runtime.register_executor("code", CodeRunner(runtime, "run.js"))
        result = await runtime.run_node(NodeRequest("sum", "sum", {}, "root"))
        self.assertEqual(runtime.store.get(result["ref"])["content"]["value"], 3)
        self.assertEqual(runtime.ledger.model_calls, 0)
        self.assertEqual(runtime.ledger.frames, 3)

    async def test_code_timeout(self):
        runtime = Runtime(
            Registry([code_skill("loop", "while (true) {}")]), Store(), default_executor="code"
        )
        self.addCleanup(runtime.store.close)
        runtime.register_executor("code", CodeRunner(runtime, "run.js", timeout=0.02))
        with self.assertRaises(JSTimeoutError):
            await asyncio.wait_for(runtime.run_node(NodeRequest("loop", "loop", {}, "root")), 2)
        self.assertFalse(any(e["type"] == "accepted" for e in runtime.store.events()))

    async def test_execution_mode_must_be_explicit(self):
        for argv in ([], ["--offline", "--model", "provider:model"]):
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                parse_args(argv)
        self.assertTrue(parse_args(["--offline"]).offline)
        self.assertEqual(parse_args(["--model", "provider:model"]).model, "provider:model")
        with self.assertRaisesRegex(ValueError, "Choose exactly one"):
            await run_demo()
        with self.assertRaisesRegex(ValueError, "Choose exactly one"):
            await run_demo(model="provider:model", offline=True)
