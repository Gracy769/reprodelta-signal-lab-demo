"""Run one ordinary signal through the constructed classifier."""

import json

import numpy as np

from fixture.project.pipeline import classify_signal


if __name__ == "__main__":
    signal = np.array([1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    print(json.dumps(classify_signal(signal), indent=2, sort_keys=True))
