"""Read a bounded JSON time series and print a deterministic screening report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from signal_lab.windows import screen_windows

MAX_INPUT_BYTES = 1_000_000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Screen a time series of eight-value signals")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--ratio-alert", type=float, default=0.15)
    args = parser.parse_args(argv)
    try:
        if args.json_file.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("JSON input exceeds the 1 MB limit")
        data = json.loads(args.json_file.read_text(encoding="utf-8"))
        report = screen_windows(data, ratio_alert=args.ratio_alert)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
