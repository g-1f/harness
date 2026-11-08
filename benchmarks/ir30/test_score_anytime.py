"""Tests for the offline IR-30 aggregator; no model or investment grader needed."""
import unittest
from score_anytime import aggregate, CHECKPOINTS


class TestAnytime(unittest.TestCase):
    def episode(self, arm="A", q=(0, 20, 30, 40, 50, 60, 70)):
        return [{"case_id": "demo", "arm": arm, "rep": 0, "elapsed_s": t,
                 "quality": score, "usd": 1.0 if t == 1800 else 0.1}
                for t, score in zip(CHECKPOINTS, q)]

    def test_left_step_auc_and_terminal(self):
        got = aggregate(self.episode())
        self.assertAlmostEqual(got["arms"]["A"]["mean_auc_q_30"], 200 / 6, places=4)
        self.assertEqual(got["arms"]["A"]["mean_q30"], 70)

    def test_missing_checkpoint_rejected(self):
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            aggregate(self.episode()[:-1])

    def test_duplicate_checkpoint_rejected(self):
        rows = self.episode()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            aggregate(rows + [rows[0]])

    def test_paired_differences(self):
        result = aggregate(self.episode("A") + self.episode("D", (0,30,40,50,60,70,80)))
        self.assertAlmostEqual(result["paired_descriptive"]["D_minus_A"]["mean_auc_difference"], 50 / 6, places=4)


if __name__ == "__main__":
    unittest.main()
