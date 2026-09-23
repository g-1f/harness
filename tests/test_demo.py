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
    async def test_example_is_a_converging_execution_graph(self):
        cases = {
            "a": {"f", "g"},
            "a-diversified": set(),
            "b": {"h", "i"},
            "b-no-proposal": {"h"},
            "unchanged": {"h", "i"},
            "deferred": {"f", "g"},
            "skip-c": {"f", "g"},
        }
        for case, followups in cases.items():
            with self.subTest(case=case):
                runtime, receipt = await run_demo(case, offline=True)
                self.addCleanup(runtime.store.close)
                report = runtime.store.get(receipt["ref"])["content"]
                events = runtime.store.events()
                admissions = [e for e in events if e["type"] == "admitted"]
                nodes = {e["frame"]: e["node"] for e in admissions}
                calls = [e for e in events if e["type"] == "call_acquired"]
                self.assertEqual(report["outcome"], "complete")
                self.assertEqual(set(nodes.values()) & {"f", "g", "h", "i"}, followups)
                for name in ("b", "l", "delta_check"):
                    self.assertEqual(list(nodes.values()).count(name), 1)
                self.assertEqual(list(nodes.values()).count("k"), 0 if case == "unchanged" else 1)
                b_calls = [e for e in calls if nodes[e["operation"]] == "b"]
                expected = {"a", "c", "d"} - (
                    {"a"} if case == "deferred" else {"c"} if case == "skip-c" else set()
                )
                self.assertEqual({nodes[e["caller"]] for e in b_calls}, expected)
                self.assertEqual(b_calls[0]["disposition"], "started")
                d_call = next(e for e in b_calls if nodes[e["caller"]] == "d")
                self.assertEqual(d_call["disposition"], "reused")
                if case in ("b", "b-no-proposal", "unchanged"):
                    c_call = next(e for e in b_calls if nodes[e["caller"]] == "c")
                    self.assertEqual(c_call["disposition"], "reused")
                self.assertEqual(len(set(report["snapshot_refs"])), 1)
                if "f" in followups:
                    f_calls = [e for e in calls if nodes[e["operation"]] == "f"]
                    self.assertEqual({nodes[e["caller"]] for e in f_calls}, {"d", "g"})
                    self.assertEqual(list(nodes.values()).count("f"), 1)
                    l_calls = [e for e in calls if nodes[e["operation"]] == "l"]
                    self.assertEqual({nodes[e["caller"]] for e in l_calls}, {"b", "f", "g"})
                for entry in admissions:
                    actions = [
                        e
                        for e in events
                        if e["type"] == "agent_actions" and e["frame"] == entry["frame"]
                    ]
                    self.assertEqual(bool(actions), entry["executor"] != "snapshot_math")
                    if entry["node"] in ("red_team", "artifact_coherence"):
                        self.assertEqual(entry["reuse"], "fresh")
                thesis = runtime.store.get(report["thesis"])
                self.assertEqual(len(thesis["reviews"]), 1)
                review = runtime.store.get(thesis["reviews"][0])["content"]
                self.assertEqual(
                    runtime.store.get(review["candidate_ref"])["content"], thesis["content"]
                )
                self.assertEqual(review["verdict"], "pass")
                self.assertEqual(runtime.operations.waits, {})
                self.assertTrue(
                    all(not op.waiters for op in runtime.operations.operations.values())
                )

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
