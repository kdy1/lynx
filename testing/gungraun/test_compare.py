import json
from pathlib import Path
import tempfile
import unittest

from compare import CASES, read_counts, report


class ComparisonTests(unittest.TestCase):
    def summaries(self, root, counts):
        for case, values in counts.items():
            path = Path(root) / case / "summary.json"
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps({"version": "7", "id": case, "profiles": [{
                "tool": "Callgrind", "data": {"total": {"metrics": {"Ir": {"values": values}}}}
            }]}))

    def test_new_is_head_and_old_is_base(self):
        with tempfile.TemporaryDirectory() as root:
            self.summaries(root, {c: {"new": 9800, "old": 10000} for c in CASES})
            result = report(read_counts(root))
            self.assertEqual(result["performance_gate"], "pass")
            self.assertAlmostEqual(result["portfolio_improvement_percent"], 2)

    def test_missing_baseline_or_case_is_not_a_win(self):
        for counts in ({c: {"new": 1} for c in CASES}, {"push": {"new": 1, "old": 2}}):
            with self.subTest(counts=counts), tempfile.TemporaryDirectory() as root:
                self.summaries(root, counts)
                with self.assertRaises(ValueError):
                    read_counts(root)

    def test_duplicate_case_and_unknown_schema_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.summaries(root, {c: {"new": 1, "old": 2} for c in CASES})
            duplicate = Path(root) / "duplicate"
            duplicate.mkdir()
            original = Path(root) / "push" / "summary.json"
            (duplicate / "summary.json").write_text(original.read_text())
            with self.assertRaises(ValueError):
                read_counts(root)
            (duplicate / "summary.json").unlink()
            data = json.loads(original.read_text())
            data["version"] = "unknown"
            original.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                read_counts(root)

    def test_gate_boundaries_and_regressions(self):
        counts = {c: {"base": 10000, "head": 9900} for c in CASES}
        self.assertEqual(report(counts)["performance_gate"], "pass")
        counts["push"]["head"] = 9901
        self.assertEqual(report(counts)["performance_gate"], "not_passed")
        counts = {c: {"base": 10000, "head": 9000} for c in CASES}
        counts["push"]["head"] = 10100
        self.assertEqual(report(counts)["performance_gate"], "not_passed")


if __name__ == "__main__":
    unittest.main()
