"""CLI for deterministic signal CSV quality checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from signal_lab.quality import MAX_BYTES, audit_csv_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit eight-value signal CSV rows")
    parser.add_argument("csv_file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.csv_file.stat().st_size > MAX_BYTES:
            raise ValueError(f"CSV exceeds the {MAX_BYTES}-byte limit")
        result = audit_csv_text(args.csv_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result.summary(), indent=2, sort_keys=True))
    return 1 if result.rejected_rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
