"""Cache-compatible prompt boundaries; these tests do not simulate GPU KV reuse."""

import unittest
from copy import deepcopy

from harness import NodeRequest
from harness.runners.agent import node_messages
from harness.runtime import Frame


class PromptLayoutTests(unittest.TestCase):
    def test_repair_feedback_and_task_do_not_mutate_procedure_or_evidence_prefix(self):
        context = {
            "entry": {"node": "b", "revision": "v1", "text": "Inspect evidence"},
            "attempt": 0,
            "feedback": [],
            "previous": None,
        }
        first = Frame("first", None, NodeRequest("b", "Baseline", {"b": 2, "a": 1}, "a"))
        second = Frame(
            "second", "private-parent", NodeRequest("b", "Capacity", {"a": 1, "b": 2}, "c")
        )
        repaired = {
            **context,
            "attempt": 1,
            "feedback": [{"finding": "Missing evidence"}],
            "previous": "draft-ref",
        }
        left, right = node_messages(first, context), node_messages(second, repaired)
        self.assertEqual(left[:2], right[:2])
        self.assertNotEqual(left[2], right[2])
        self.assertNotIn("private-parent", str(right))
        self.assertNotIn("draft-ref", str(right[:2]))

    def test_changed_skill_and_grants_change_the_corresponding_prefix_boundary(self):
        context = {
            "entry": {"node": "b", "revision": "v1", "text": "Inspect evidence"},
            "attempt": 0,
            "feedback": [],
            "previous": None,
        }
        frame = Frame("one", None, NodeRequest("b", "Baseline", {}, "a", ("allowed-1",)))
        original = node_messages(frame, context)
        frame.request = NodeRequest("b", "Baseline", {}, "a", ("allowed-2",))
        changed_grant = node_messages(frame, context)
        self.assertEqual(original[0], changed_grant[0])
        self.assertNotEqual(original[1], changed_grant[1])
        changed_skill = deepcopy(context)
        changed_skill["entry"].update(revision="v2", text="Changed procedure")
        self.assertNotEqual(original[0], node_messages(frame, changed_skill)[0])
