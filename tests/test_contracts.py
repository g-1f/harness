import unittest

from harness import NodeRequest, Rejected
from harness.contracts import candidate


class ContractTests(unittest.TestCase):
    def test_request_detaches_nested_data(self):
        data = {"node": "a", "task": "baseline", "inputs": {"nested": []}, "key": "a"}
        request = NodeRequest.parse(data)
        data["inputs"]["nested"].append("changed")
        self.assertEqual(request.inputs, {"nested": []})

    def test_request_rejects_execution_overrides_and_non_json_inputs(self):
        base = {"node": "a", "task": "baseline", "inputs": {}, "key": "a"}
        for extra in (
            {"executor": "admin"},
            {"model": "other"},
            {"task": " "},
            {"inputs": {"value": float("nan")}},
            {"refs": [None]},
            {"reuse": "automatic"},
        ):
            with self.subTest(extra=extra), self.assertRaises(Rejected):
                NodeRequest.parse({**base, **extra})

    def test_candidate_validates_the_same_boundary_for_all_executors(self):
        base = {"summary": "Observation", "content": {"value": 1}}
        self.assertEqual(candidate(base)["based_on"], [])
        for extra in ({"status": "accepted"}, {"content": []}, {"based_on": [1]}, {"summary": " "}):
            with self.subTest(extra=extra), self.assertRaises(Rejected):
                candidate({**base, **extra})
