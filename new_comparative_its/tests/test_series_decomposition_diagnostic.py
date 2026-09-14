#!/usr/bin/env python3
"""Regression checks for the comparative ITS series decomposition."""

from __future__ import annotations

import csv
import hashlib
import subprocess
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
SCRIPT = PACKAGE / "scripts" / "series_decomposition_diagnostic.py"
DATA = PACKAGE / "data"
REPORTS = PACKAGE / "reports"
FIGURES = PACKAGE / "figures"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SeriesDecompositionDiagnosticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        protected = [
            DATA / "monthly_strict.csv",
            DATA / "monthly_broad.csv",
            DATA / "placebo_results.csv",
            REPORTS / "new_comparative_its_results.md",
            REPORTS / "placebo_date_checks.md",
            FIGURES / "figure_strict_fitted_monthly_counts.svg",
            FIGURES / "figure_broad_fitted_monthly_counts.svg",
        ]
        before = {path: digest(path) for path in protected}
        subprocess.run(["python3", str(SCRIPT)], check=True, cwd=ROOT)
        after = {path: digest(path) for path in protected}
        if before != after:
            raise AssertionError("series-decomposition script modified an existing output")

    def test_model_counts_and_support(self) -> None:
        rows = read_csv(DATA / "series_decomposition_results.csv")
        self.assertEqual(len(rows), 48)
        self.assertEqual({row["series_id"] for row in rows}, {"treatment", "strict_control", "broad_control"})
        for series_id in {row["series_id"] for row in rows}:
            actual = [row for row in rows if row["series_id"] == series_id and row["design"] == "actual_full"]
            placebos = [row for row in rows if row["series_id"] == series_id and row["design"] == "placebo_all_pre"]
            matched = [row for row in rows if row["series_id"] == series_id and row["design"] == "placebo_18_12"]
            matched_actual = [row for row in rows if row["series_id"] == series_id and row["design"] == "actual_18_12"]
            self.assertEqual((len(actual), len(placebos), len(matched), len(matched_actual)), (1, 10, 4, 1))
            self.assertEqual((actual[0]["sample_start"], actual[0]["sample_end"]), ("2021-10", "2026-04"))
            self.assertTrue(all(row["sample_end"] == "2024-06" for row in placebos))
            self.assertTrue(all((row["n_obs"], row["k_params"], row["df_resid"]) == ("33", "15", "18") for row in placebos))
            self.assertEqual((placebos[0]["intervention_date"], placebos[-1]["intervention_date"]), ("2022-10", "2023-07"))
            self.assertTrue(all(row["month_of_year_fe"] == "Yes" and row["nw_lag"] == "3" for row in placebos))

    def test_actual_estimates_reproduce_component_models(self) -> None:
        rows = read_csv(DATA / "series_decomposition_results.csv")
        actual = {
            row["series_id"]: row
            for row in rows
            if row["design"] == "actual_full"
        }
        self.assertAlmostEqual(float(actual["treatment"]["slope_change"]), 0.47509957, places=7)
        self.assertAlmostEqual(float(actual["strict_control"]["slope_change"]), 0.24376646, places=7)
        self.assertAlmostEqual(float(actual["broad_control"]["slope_change"]), 0.31247812, places=7)
        self.assertAlmostEqual(
            float(actual["treatment"]["slope_change"]) - float(actual["strict_control"]["slope_change"]),
            0.23133310,
            places=7,
        )
        self.assertAlmostEqual(
            float(actual["treatment"]["slope_change"]) - float(actual["broad_control"]["slope_change"]),
            0.16262145,
            places=7,
        )

    def test_placebo_diagnosis(self) -> None:
        summary = {row["object_id"]: row for row in read_csv(DATA / "series_decomposition_summary.csv")}
        self.assertEqual(len(summary), 5)
        treatment = summary["treatment"]
        strict = summary["strict_control"]
        broad = summary["broad_control"]
        self.assertEqual((treatment["placebo_negative_n"], treatment["placebo_positive_n"]), ("10", "0"))
        self.assertEqual(treatment["placebo_slope_p_lt_0_05_n"], "10")
        self.assertEqual(treatment["placebo_slope_holm_p_lt_0_05_n"], "10")
        self.assertEqual(strict["placebo_slope_p_lt_0_05_n"], "0")
        self.assertEqual(broad["placebo_slope_p_lt_0_05_n"], "0")
        self.assertEqual(summary["treatment_minus_strict_control"]["placebo_slope_p_lt_0_05_n"], "10")
        self.assertEqual(summary["treatment_minus_broad_control"]["placebo_slope_p_lt_0_05_n"], "9")
        self.assertTrue(all(row["actual_above_all_placebos"] == "1" for row in summary.values()))

    def test_report_and_figures(self) -> None:
        report = (REPORTS / "series_decomposition_diagnostic.md").read_text(encoding="utf-8")
        stata = (REPORTS / "series_decomposition_stata_style_results.txt").read_text(encoding="utf-8")
        self.assertIn("generated mainly by instability in the treatment series", report)
        self.assertIn("not causal estimates or randomized placebo tests", report)
        self.assertIn("Treatment minus strict control", report)
        self.assertIn("Actual July 2024 ITS: Treatment only", stata)
        self.assertIn("Holm slope p", stata)
        self.assertIn("Stata executed: No", stata)
        for stem in ("treatment_only", "strict_control_only", "broad_control_only"):
            figure = FIGURES / f"figure_{stem}_its_placebos.svg"
            content = figure.read_text(encoding="utf-8")
            self.assertIn("Actual Jul 2024 slope change", content)
            self.assertIn("Artificial slope changes", content)
            self.assertIn("Jul 2024", content)
            self.assertNotIn("Through Apr 2026", content)


if __name__ == "__main__":
    unittest.main()
