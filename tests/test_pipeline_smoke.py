"""Smoke tests for the baseline classifier, independent of either pin."""

import math
import unittest

import numpy as np

from fixture.project.pipeline import classify_signal


class PipelineSmokeTests(unittest.TestCase):
    def test_result_has_a_finite_ratio_and_declared_conclusion(self):
        signal = np.array([1, 1, 1, 1, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        result = classify_signal(signal)
        self.assertTrue(math.isfinite(result["ratio"]))
        self.assertIn(result["conclusion"], {"above_threshold", "below_threshold"})
        self.assertEqual(result["threshold"], 0.5)
        self.assertEqual(result["numpy_version"], np.__version__)


if __name__ == "__main__":
    unittest.main()
