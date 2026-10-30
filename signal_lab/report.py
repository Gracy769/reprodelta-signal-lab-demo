"""Build a content-addressed report for a bounded batch of signal samples.

The report records measured classifier outputs and provenance. A content hash
detects accidental edits; it is not a signature or proof of scientific truth.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from fixture.project.pipeline import THRESHOLD, classify_signal

MAX_SAMPLES = 1_000
MAX_ID_LENGTH = 80
SIGNAL_LENGTH = 8
BOUND = 10.0
KERNEL = Path(__file__).resolve().parents[1] / "fixture" / "project" / "pipeline.py"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_sample(sample: Any, seen: set[str]) -> tuple[str, np.ndarray]:
    if not isinstance(sample, dict) or set(sample) != {"id", "signal"}:
        raise ValueError("each sample must have exactly id and signal")
    sample_id = sample["id"]
    if not isinstance(sample_id, str) or not sample_id or len(sample_id) > MAX_ID_LENGTH:
        raise ValueError("sample ID must be 1 to 80 characters")
    if sample_id in seen:
        raise ValueError(f"duplicate sample ID: {sample_id}")
    seen.add(sample_id)
    raw_signal = sample["signal"]
    if not isinstance(raw_signal, list) or len(raw_signal) != SIGNAL_LENGTH:
        raise ValueError("each signal must have exactly eight values")
    values: list[float] = []
    for value in raw_signal:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("signal values must be numeric")
        if not math.isfinite(value) or abs(value) > BOUND:
            raise ValueError("signal values must be finite and within [-10, 10]")
        values.append(float(value))
    return sample_id, np.asarray(values, dtype=np.float32)


def build_report(batch: dict, *, boundary_band: float = 1e-4) -> dict:
    """Classify supplied samples and attach explicit, reproducible provenance."""
    if not isinstance(batch, dict) or set(batch) != {"experiment_id", "samples"}:
        raise ValueError("batch must contain exactly experiment_id and samples")
    experiment_id = batch["experiment_id"]
    if not isinstance(experiment_id, str) or not 1 <= len(experiment_id) <= 80:
        raise ValueError("experiment_id must be 1 to 80 characters")
    samples = batch["samples"]
    if not isinstance(samples, list) or not 1 <= len(samples) <= MAX_SAMPLES:
        raise ValueError(f"samples must contain 1 to {MAX_SAMPLES} items")
    if (isinstance(boundary_band, bool) or not isinstance(boundary_band, (int, float))
            or not math.isfinite(boundary_band) or not 0 <= boundary_band <= 0.5):
        raise ValueError("boundary_band must be within [0, 0.5]")

    seen: set[str] = set()
    results = []
    counts = {"above_threshold": 0, "below_threshold": 0}
    for sample in samples:
        sample_id, signal = _validate_sample(sample, seen)
        observation = classify_signal(signal)
        conclusion = observation["conclusion"]
        if conclusion not in counts:
            raise ValueError("classifier returned an unknown conclusion")
        ratio = float(observation["ratio"])
        if not math.isfinite(ratio):
            raise ValueError("classifier returned a non-finite ratio")
        counts[conclusion] += 1
        results.append({
            "id": sample_id,
            "input_sha256": _digest(sample["signal"]),
            "ratio": ratio,
            "margin_from_threshold": ratio - THRESHOLD,
            "near_boundary": abs(ratio - THRESHOLD) <= boundary_band,
            "conclusion": conclusion,
            "intermediate_dtype": observation["intermediate_dtype"],
        })

    report = {
        "schema_version": 1,
        "scope": "Supplied samples only; no search, causal attribution, or repair claim",
        "experiment_id": experiment_id,
        "input_sha256": _digest(batch),
        "kernel_sha256": hashlib.sha256(KERNEL.read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "threshold": THRESHOLD,
        "boundary_band": float(boundary_band),
        "sample_count": len(results),
        "decision_counts": counts,
        "results": results,
    }
    report["report_sha256"] = _digest(report)
    return report


def verify_report(report: dict) -> bool:
    """Check report-byte integrity; this cannot authenticate its author."""
    if not isinstance(report, dict) or not isinstance(report.get("report_sha256"), str):
        return False
    claimed = report["report_sha256"]
    try:
        return _digest({key: value for key, value in report.items() if key != "report_sha256"}) == claimed
    except (TypeError, ValueError):
        return False


def write_report(path: Path, report: dict) -> None:
    """Replace an output file atomically so interruption leaves no half report."""
    if not verify_report(report):
        raise ValueError("report hash does not match its content")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=".signal-report-", suffix=".tmp", delete=False,
        ) as handle:
            temporary = handle.name
            json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
