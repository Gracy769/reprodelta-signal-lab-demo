import json
import tempfile
import unittest
from pathlib import Path

from signal_lab.report import build_report, verify_report, write_report


def batch():
    return {
        "experiment_id": "trial-1",
        "samples": [
            {"id": "low", "signal": [1] * 4 + [0.5] * 4},
            {"id": "high", "signal": [0.5] * 4 + [1] * 4},
        ],
    }


class ReportTests(unittest.TestCase):
    def test_report_is_repeatable_and_detects_tampering(self):
        first = build_report(batch())
        second = build_report(batch())
        self.assertEqual(first, second)
        self.assertTrue(verify_report(first))
        first["decision_counts"]["above_threshold"] += 1
        self.assertFalse(verify_report(first))

    def test_changed_input_changes_content_hash(self):
        original = build_report(batch())
        modified = batch()
        modified["samples"][0]["signal"][0] = 0.8
        self.assertNotEqual(original["input_sha256"], build_report(modified)["input_sha256"])

    def test_rejects_duplicate_and_invalid_signal(self):
        duplicate = batch()
        duplicate["samples"][1]["id"] = "low"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_report(duplicate)
        bad = batch()
        bad["samples"][0]["signal"][0] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite"):
            build_report(bad)

    def test_atomic_output_round_trip(self):
        report = build_report(batch())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.json"
            write_report(target, report)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)
            self.assertEqual(list(Path(directory).iterdir()), [target])


if __name__ == "__main__":
    unittest.main()
