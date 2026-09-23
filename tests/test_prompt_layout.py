"""Cache-compatible prompt boundaries; these tests do not simulate GPU KV reuse."""

import unittest
from copy import deepcopy

from harness import NodeRequest
from harness.runners.agent import node_messages
from harness.runtime import Frame


class PromptLayoutTests(unittest.TestCase):
    def test_task_changes_preserve_procedure_and_evidence_prefix(self):
        context = {"entry": {"node": "b", "revision": "v1", "text": "Inspect evidence"}}
        first = Frame("first", None, NodeRequest("b", "Baseline", {"b": 2, "a": 1}, "a"))
        second = Frame(
            "second", "private-parent", NodeRequest("b", "Capacity", {"a": 1, "b": 2}, "c")
        )
        left, right = node_messages(first, context), node_messages(second, context)
        self.assertEqual(left[:2], right[:2])
        self.assertNotEqual(left[2], right[2])
        self.assertNotIn("private-parent", str(right))

    def test_changed_skill_inputs_and_grants_change_their_prefix_boundary(self):
        context = {"entry": {"node": "b", "revision": "v1", "text": "Inspect evidence"}}
        frame = Frame("one", None, NodeRequest("b", "Baseline", {}, "a", ("allowed-1",)))
        original = node_messages(frame, context)
        for inputs, refs in (({}, ("allowed-2",)), ({"feedback": "Revise"}, ("allowed-1",))):
            frame.request = NodeRequest("b", "Baseline", inputs, "a", refs)
            changed = node_messages(frame, context)
            self.assertEqual(original[0], changed[0])
            self.assertNotEqual(original[1], changed[1])
        changed_skill = deepcopy(context)
        changed_skill["entry"].update(revision="v2", text="Changed procedure")
        self.assertNotEqual(original[0], node_messages(frame, changed_skill)[0])
