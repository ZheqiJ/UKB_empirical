#!/usr/bin/env python3
"""Regression checks for the within-High comparative ITS outputs."""

from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
SCRIPT = PACKAGE / "scripts" / "new_comparative_its.py"
DATA = PACKAGE / "data"
FIGURES = PACKAGE / "figures"
REPORTS = PACKAGE / "reports"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class NewComparativeITSTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(["python3", str(SCRIPT)], check=True, cwd=ROOT)

    def test_group_definition_and_set_relations(self) -> None:
        rows = read_csv(DATA / "group_definition_audit.csv")
        self.assertEqual(len(rows), 1048)
        treatment = {row["app_id"] for row in rows if row["treatment"] == "1"}
        strict = {row["app_id"] for row in rows if row["control_strict"] == "1"}
        broad = {row["app_id"] for row in rows if row["control_broad"] == "1"}
        self.assertEqual(len(treatment), 589)
        self.assertEqual(len(strict), 427)
        self.assertEqual(len(broad), 459)
        self.assertFalse(treatment & strict)
        self.assertFalse(treatment & broad)
        self.assertTrue(strict < broad)
        excluded = [row for row in rows if row["app_id"] in broad - strict]
        self.assertEqual(len(excluded), 32)
        self.assertTrue(all(row["hs_s3_text"] == "1" and row["hs_s3_direct"] == "0" for row in excluded))
        self.assertEqual(sum(row["treatment"] == "1" and row["in_analysis_window"] == "1" for row in rows), 380)
        self.assertEqual(sum(row["control_strict"] == "1" and row["in_analysis_window"] == "1" for row in rows), 231)
        self.assertEqual(sum(row["control_broad"] == "1" and row["in_analysis_window"] == "1" for row in rows), 255)

    def test_month_window_and_indexing(self) -> None:
        for specification in ["strict", "broad"]:
            rows = read_csv(DATA / f"monthly_{specification}.csv")
            self.assertEqual(len(rows), 55)
            self.assertEqual(rows[0]["month"], "2021-10")
            self.assertEqual(rows[-1]["month"], "2026-04")
            july = next(row for row in rows if row["month"] == "2024-07")
            august = next(row for row in rows if row["month"] == "2024-08")
            self.assertEqual(july["time_after_july2024"], "0")
            self.assertEqual(august["time_after_july2024"], "1")
            self.assertTrue(any(row["treatment_count"] == "0" for row in rows))
            self.assertTrue(any(row["control_count"] == "0" for row in rows))
            self.assertNotIn("treatment_index_pre_mean", rows[0])
            self.assertEqual(len(read_csv(DATA / f"stacked_{specification}.csv")), 110)
            regression_rows = read_csv(DATA / f"regression_results_{specification}.csv")
            self.assertTrue(all(row["sample_dates"] == "2021-10 through 2026-04" for row in regression_rows))
            self.assertTrue(all(row["outcome_scale"] == "raw" for row in regression_rows))
            self.assertTrue(all("index" not in row["outcome"] for row in regression_rows))

    def test_required_reports_and_figures(self) -> None:
        for name in ["new_comparative_its_results.md", "new_comparative_its_stata_style_results.txt", "group_definition_audit.md"]:
            self.assertTrue((REPORTS / name).exists())
        for name in [
            "figure_strict_observed_monthly_counts.svg",
            "figure_strict_fitted_monthly_counts.svg",
            "figure_broad_observed_monthly_counts.svg",
            "figure_broad_fitted_monthly_counts.svg",
        ]:
            content = (FIGURES / name).read_text(encoding="utf-8")
            self.assertIn("Jul 2024", content)
            self.assertNotIn("Through Apr 2026", content)
            self.assertNotIn("delta3 =", content)
            self.assertIn("Monthly Counts", content)
        for name in [
            "figure_strict_observed_entry_index.svg",
            "figure_strict_fitted_entry_index.svg",
            "figure_broad_observed_entry_index.svg",
            "figure_broad_fitted_entry_index.svg",
            "figure_strict_segmented_trends.svg",
            "figure_broad_segmented_trends.svg",
        ]:
            self.assertFalse((FIGURES / name).exists())
        self.assertFalse((DATA / "raw_partition_results_strict.csv").exists())
        self.assertFalse((DATA / "raw_partition_results_broad.csv").exists())

    def test_independent_pre_shock_pretrend_diagnostic(self) -> None:
        for specification in ["strict", "broad"]:
            component_rows = read_csv(DATA / f"pretrend_regression_results_{specification}.csv")
            self.assertTrue(all(row["sample_dates"] == "2021-10 through 2024-06" for row in component_rows))
            self.assertTrue(all(row["n_obs"] == "66" for row in component_rows))
            self.assertEqual(len(component_rows), 15)
            self.assertTrue(all(row["inference"] == "Calendar-month clustered Newey-West HAC (lag 3)" for row in component_rows))
            self.assertIn("Treated", {row["term"] for row in component_rows})
            self.assertIn("Treated x Time", {row["term"] for row in component_rows})
            self.assertNotIn("Treated x month_02", {row["term"] for row in component_rows})
            results = {row["parameter"]: row for row in read_csv(DATA / f"pretrend_results_{specification}.csv")}
            self.assertEqual(set(results), {"gamma_pre", "delta1_pre", "joint_treated_and_time"})
            self.assertEqual(results["gamma_pre"]["restrictions"], "1")
            self.assertEqual(results["delta1_pre"]["restrictions"], "1")
            self.assertEqual(results["joint_treated_and_time"]["restrictions"], "2")
            self.assertEqual(results["joint_treated_and_time"]["distribution"], "chi2(2)")
            self.assertEqual(results["joint_treated_and_time"]["estimate"], "")
            self.assertGreater(float(results["delta1_pre"]["estimate"]), 0.0)
            self.assertLess(float(results["delta1_pre"]["p_value"]), 0.05)
        report = (REPORTS / "new_comparative_its_results.md").read_text(encoding="utf-8")
        stata = (REPORTS / "new_comparative_its_stata_style_results.txt").read_text(encoding="utf-8")
        self.assertIn("Independent Pre-Shock Pretrend Diagnostic", report)
        self.assertIn("Joint Wald", report)
        self.assertIn("Pre-shock diagnostic", stata)
        self.assertIn("Treated x Month FE             = No", stata)


if __name__ == "__main__":
    unittest.main()
