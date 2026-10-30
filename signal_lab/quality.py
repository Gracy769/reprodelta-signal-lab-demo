"""Validate a batch of eight-value signal observations before analysis.

The audit is deliberately separate from the trusted ReproDelta fixture. It
checks input quality; it makes no claim about the classifier's conclusion.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import asdict, dataclass

SIGNAL_COLUMNS = tuple(f"s{i}" for i in range(8))
EXPECTED_COLUMNS = ("sample_id", *SIGNAL_COLUMNS)
MAX_BYTES = 2_000_000
MAX_ROWS = 10_000
MAX_REPORTED_ISSUES = 100


@dataclass(frozen=True)
class SignalRecord:
    sample_id: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class QualityIssue:
    row: int
    code: str
    field: str
    message: str


@dataclass(frozen=True)
class AuditResult:
    records: tuple[SignalRecord, ...]
    total_rows: int
    rejected_rows: int
    issue_count: int
    issues: tuple[QualityIssue, ...]

    def summary(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "accepted_rows": len(self.records),
            "rejected_rows": self.rejected_rows,
            "issue_count": self.issue_count,
            "issues_truncated": self.issue_count > len(self.issues),
            "issues": [asdict(issue) for issue in self.issues],
        }


def audit_csv_text(text: str) -> AuditResult:
    """Audit CSV text and return accepted records and bounded diagnostics.

    Headers and size limits are hard failures. Bad rows are reported and skipped
    so a caller can choose whether to discard or repair the source data.
    """
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError(f"CSV exceeds the {MAX_BYTES}-byte limit")

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
        raise ValueError("CSV columns must be: " + ", ".join(EXPECTED_COLUMNS))

    records: list[SignalRecord] = []
    issues: list[QualityIssue] = []
    seen_ids: set[str] = set()
    total_rows = rejected_rows = issue_count = 0

    def issue(row: int, code: str, field: str, message: str) -> None:
        nonlocal issue_count
        issue_count += 1
        if len(issues) < MAX_REPORTED_ISSUES:
            issues.append(QualityIssue(row, code, field, message))

    for row_number, row in enumerate(reader, start=2):
        total_rows += 1
        if total_rows > MAX_ROWS:
            raise ValueError(f"CSV exceeds the {MAX_ROWS}-row limit")
        before = issue_count
        if None in row or any(value is None for value in row.values()):
            issue(row_number, "column_count", "row", "Expected exactly nine fields")
            rejected_rows += 1
            continue

        sample_id = row["sample_id"].strip()
        if not sample_id:
            issue(row_number, "missing_id", "sample_id", "Sample ID is required")
        elif len(sample_id) > 80:
            issue(row_number, "long_id", "sample_id", "Sample ID exceeds 80 characters")
        elif sample_id in seen_ids:
            issue(row_number, "duplicate_id", "sample_id", "Sample ID is repeated")
        else:
            seen_ids.add(sample_id)

        values: list[float] = []
        for column in SIGNAL_COLUMNS:
            raw = row[column].strip()
            try:
                value = float(raw)
            except ValueError:
                issue(row_number, "not_numeric", column, "Expected a numeric signal value")
                continue
            if not math.isfinite(value):
                issue(row_number, "not_finite", column, "NaN and infinity are not valid")
            elif not -10.0 <= value <= 10.0:
                issue(row_number, "out_of_domain", column, "Value must be within [-10, 10]")
            else:
                values.append(value)

        if issue_count != before:
            rejected_rows += 1
        else:
            records.append(SignalRecord(sample_id, tuple(values)))

    return AuditResult(tuple(records), total_rows, rejected_rows, issue_count, tuple(issues))
