"""Screen a time-ordered series of eight-value signals for decision changes.

This is a descriptive screen, not a validated change-point test. The exact
classifier is imported so each reported decision can be traced to its source.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np

from fixture.project.pipeline import classify_signal

MAX_WINDOWS = 1_000
MAX_ABS_VALUE = 10.0


@dataclass(frozen=True)
class ScreenedWindow:
    timestamp: str
    ratio: float
    conclusion: str
    intermediate_dtype: str
    delta_from_baseline: float
    flagged: bool


def _parse_timestamp(raw: Any) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ValueError("timestamp must be an ISO 8601 string")
    try:
        timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be an ISO 8601 string") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return timestamp.astimezone(timezone.utc)


def _parse_signal(raw: Any) -> np.ndarray:
    if not isinstance(raw, list) or len(raw) != 8:
        raise ValueError("signal must contain exactly eight numeric values")
    values = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("signal values must be numbers")
        if not math.isfinite(value) or abs(value) > MAX_ABS_VALUE:
            raise ValueError("signal values must be finite and within [-10, 10]")
        values.append(value)
    return np.asarray(values, dtype=np.float32)


def screen_windows(raw_windows: list[dict], *, ratio_alert: float = 0.15) -> dict:
    """Return traceable per-window measurements and decision transitions.

    The first window defines the descriptive reference ratio. A flag marks a
    difference in ratio of at least `ratio_alert`; it is not a statistical
    significance claim. Decisions use the imported classifier unchanged.
    """
    if not isinstance(raw_windows, list) or not 1 <= len(raw_windows) <= MAX_WINDOWS:
        raise ValueError(f"windows must contain 1 to {MAX_WINDOWS} items")
    if not isinstance(ratio_alert, (int, float)) or isinstance(ratio_alert, bool):
        raise ValueError("ratio_alert must be a number")
    if not math.isfinite(ratio_alert) or not 0 < ratio_alert <= 1:
        raise ValueError("ratio_alert must be within (0, 1]")

    results: list[ScreenedWindow] = []
    transitions: list[dict] = []
    previous_time: datetime | None = None
    reference_ratio: float | None = None
    previous_conclusion: str | None = None

    for index, item in enumerate(raw_windows):
        if not isinstance(item, dict):
            raise ValueError(f"window {index} must be an object")
        timestamp = _parse_timestamp(item.get("timestamp"))
        if previous_time is not None and timestamp <= previous_time:
            raise ValueError("timestamps must be strictly increasing")
        signal = _parse_signal(item.get("signal"))
        measured = classify_signal(signal)
        ratio = float(measured["ratio"])
        if not math.isfinite(ratio):
            raise ValueError("classifier returned a non-finite ratio")
        if reference_ratio is None:
            reference_ratio = ratio
        delta = ratio - reference_ratio
        result = ScreenedWindow(
            timestamp=timestamp.isoformat().replace("+00:00", "Z"),
            ratio=ratio,
            conclusion=str(measured["conclusion"]),
            intermediate_dtype=str(measured["intermediate_dtype"]),
            delta_from_baseline=delta,
            flagged=abs(delta) >= ratio_alert,
        )
        if previous_conclusion is not None and result.conclusion != previous_conclusion:
            transitions.append({
                "index": index,
                "timestamp": result.timestamp,
                "from": previous_conclusion,
                "to": result.conclusion,
            })
        results.append(result)
        previous_time = timestamp
        previous_conclusion = result.conclusion

    return {
        "scope": "Descriptive screen of supplied windows; no causal or statistical drift claim",
        "numpy_version": np.__version__,
        "reference_ratio": reference_ratio,
        "ratio_alert": float(ratio_alert),
        "window_count": len(results),
        "flagged_count": sum(item.flagged for item in results),
        "transitions": transitions,
        "windows": [asdict(item) for item in results],
    }
