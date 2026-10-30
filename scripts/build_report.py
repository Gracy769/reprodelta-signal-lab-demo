"""Build or verify a content-addressed signal batch report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from signal_lab.report import build_report, verify_report, write_report

MAX_INPUT_BYTES = 1_000_000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a reproducible signal report")
    parser.add_argument("batch_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--boundary-band", type=float, default=1e-4)
    args = parser.parse_args(argv)
    try:
        if args.batch_json.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("batch JSON exceeds the 1 MB limit")
        batch = json.loads(args.batch_json.read_text(encoding="utf-8"))
        report = build_report(batch, boundary_band=args.boundary_band)
        write_report(args.output_json, report)
        if not verify_report(json.loads(args.output_json.read_text(encoding="utf-8"))):
            raise ValueError("written report failed integrity verification")
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output_json), "report_sha256": report["report_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
