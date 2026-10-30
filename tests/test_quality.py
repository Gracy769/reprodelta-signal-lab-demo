import unittest

from signal_lab.quality import EXPECTED_COLUMNS, audit_csv_text


def csv_rows(*rows: str) -> str:
    return ",".join(EXPECTED_COLUMNS) + "\n" + "\n".join(rows) + "\n"


class QualityTests(unittest.TestCase):
    def test_accepts_finite_in_domain_signal(self):
        result = audit_csv_text(csv_rows("sample-a,1,1,1,1,0.5,0.5,0.5,0.5"))
        self.assertEqual(result.summary()["accepted_rows"], 1)
        self.assertEqual(result.records[0].values[4], 0.5)

    def test_rejects_duplicate_and_out_of_domain_rows(self):
        result = audit_csv_text(csv_rows(
            "sample-a,1,1,1,1,1,1,1,1",
            "sample-a,1,1,1,1,1,1,1,1",
            "sample-b,11,1,1,1,1,1,1,1",
        ))
        self.assertEqual(result.rejected_rows, 2)
        self.assertEqual({i.code for i in result.issues}, {"duplicate_id", "out_of_domain"})

    def test_rejects_nonfinite_and_malformed_rows(self):
        result = audit_csv_text(csv_rows(
            "sample-a,nan,1,1,1,1,1,1,1",
            "sample-b,1,1,1,1,1,1,1",
        ))
        self.assertEqual(result.rejected_rows, 2)
        self.assertEqual({i.code for i in result.issues}, {"not_finite", "column_count"})

    def test_requires_exact_header(self):
        with self.assertRaisesRegex(ValueError, "columns must be"):
            audit_csv_text("sample_id,s0\na,1\n")


if __name__ == "__main__":
    unittest.main()
