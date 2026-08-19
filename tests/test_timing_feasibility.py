import csv
import tempfile
import unittest
from pathlib import Path

from scripts import timing_feasibility as timing


class TimingFeasibilityTests(unittest.TestCase):
    def _write_stage2_5_rows(self, path: Path) -> None:
        fieldnames = [
            "app_id",
            "schema27_title",
            "schema27_institution",
            "schema27_pi",
            "website_match_status",
            "website_match_count",
            "start_date",
            "start_dates_all",
            "website_url",
            "website_urls_all",
            "website_titles_all",
            "match_methods",
        ]
        rows = [
            {
                "app_id": "1",
                "schema27_title": "Before window",
                "schema27_institution": "A",
                "schema27_pi": "PI A",
                "website_match_status": "matched_one_website_record",
                "website_match_count": "1",
                "start_date": "2024-04-05",
                "start_dates_all": "2024-04-05",
                "website_url": "https://example.test/a",
                "website_urls_all": "https://example.test/a",
                "website_titles_all": "Before window",
                "match_methods": "unique_normalized_title",
            },
            {
                "app_id": "2",
                "schema27_title": "Policy date",
                "schema27_institution": "B",
                "schema27_pi": "PI B",
                "website_match_status": "matched_one_website_record",
                "website_match_count": "1",
                "start_date": "2024-07-05",
                "start_dates_all": "2024-07-05",
                "website_url": "https://example.test/b",
                "website_urls_all": "https://example.test/b",
                "website_titles_all": "Policy date",
                "match_methods": "unique_normalized_title",
            },
            {
                "app_id": "3",
                "schema27_title": "After window",
                "schema27_institution": "C",
                "schema27_pi": "PI C",
                "website_match_status": "matched_one_website_record",
                "website_match_count": "1",
                "start_date": "2024-10-05",
                "start_dates_all": "2024-10-05",
                "website_url": "https://example.test/c",
                "website_urls_all": "https://example.test/c",
                "website_titles_all": "After window",
                "match_methods": "unique_normalized_title",
            },
            {
                "app_id": "4",
                "schema27_title": "Audit only",
                "schema27_institution": "D",
                "schema27_pi": "PI D",
                "website_match_status": "unmatched_schema27",
                "website_match_count": "0",
                "start_date": "",
                "start_dates_all": "",
                "website_url": "",
                "website_urls_all": "",
                "website_titles_all": "",
                "match_methods": "",
            },
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_build_timing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "stage2_5_app_start_dates.csv"
            self._write_stage2_5_rows(source)

            summary = timing.build_timing_outputs(
                input_path=source,
                output_dir=root,
                expected_working=3,
                expected_audit=1,
                source_commit="abc123",
            )

            paths = timing.output_paths(root)
            self.assertEqual(summary["working_universe_projects"], 3)
            self.assertEqual(summary["unmatched_schema27_audit_records"], 1)
            self.assertTrue(paths.report.exists())
            self.assertTrue(paths.figure.exists())
            self.assertEqual(len(self._read_csv(paths.working_universe)), 3)
            self.assertEqual(len(self._read_csv(paths.unmatched_audit)), 1)

            monthly = {row["month"]: row["new_projects"] for row in self._read_csv(paths.monthly_counts)}
            self.assertEqual(monthly["2024-04"], "1")
            self.assertEqual(monthly["2024-07"], "1")
            self.assertEqual(monthly["2024-10"], "1")
            self.assertEqual(monthly["2023-01"], "0")

            quarterly = {row["quarter"]: row["new_projects"] for row in self._read_csv(paths.quarterly_counts)}
            self.assertEqual(quarterly["2024Q2"], "1")
            self.assertEqual(quarterly["2024Q3"], "1")
            self.assertEqual(quarterly["2024Q4"], "1")

            windows = self._read_csv(paths.window_counts)
            three_month = next(row for row in windows if row["window_months"] == "3")
            self.assertEqual(three_month["before_projects"], "1")
            self.assertEqual(three_month["after_projects"], "2")
            self.assertEqual(three_month["policy_date_counted_with"], "after")

    def test_rejects_unexpected_universe_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "stage2_5_app_start_dates.csv"
            self._write_stage2_5_rows(source)
            with self.assertRaisesRegex(ValueError, "Expected 4 working projects"):
                timing.build_timing_outputs(
                    input_path=source,
                    output_dir=Path(tmp),
                    expected_working=4,
                    expected_audit=1,
                    source_commit="abc123",
                )


if __name__ == "__main__":
    unittest.main()
