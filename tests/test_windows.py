import unittest

from signal_lab.windows import screen_windows


def window(minute: int, front: float, back: float) -> dict:
    return {
        "timestamp": f"2026-10-01T09:{minute:02d}:00Z",
        "signal": [front] * 4 + [back] * 4,
    }


class WindowScreenTests(unittest.TestCase):
    def test_reports_decision_transition_and_measurements(self):
        report = screen_windows([window(0, 1, 0.5), window(5, 0.5, 1)])
        self.assertEqual(report["window_count"], 2)
        self.assertEqual(len(report["transitions"]), 1)
        self.assertEqual(report["transitions"][0]["index"], 1)
        self.assertEqual(report["windows"][0]["delta_from_baseline"], 0)

    def test_rejects_repeated_or_unsorted_timestamps(self):
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            screen_windows([window(5, 1, 0.5), window(5, 0.5, 1)])

    def test_rejects_nonfinite_out_of_domain_and_boolean_values(self):
        for bad in (float("nan"), 11, True):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "signal values"):
                screen_windows([{"timestamp": "2026-10-01T09:00:00Z", "signal": [bad] * 8}])

    def test_rejects_naive_timestamp_and_invalid_alert(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            screen_windows([{"timestamp": "2026-10-01T09:00:00", "signal": [1] * 8}])
        with self.assertRaisesRegex(ValueError, "ratio_alert"):
            screen_windows([window(0, 1, 0.5)], ratio_alert=0)


if __name__ == "__main__":
    unittest.main()
