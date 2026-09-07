import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = ROOT / "analyses" / "interrupted_time_series" / "project_entry2" / "scripts"
CLASSIFIER = SCRIPT_DIR / "build_high_sensitivity_classification.py"
ANALYSIS = SCRIPT_DIR / "project_entry2_analysis.py"


def load_module(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ProjectEntry2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = load_module("project_entry2_classifier", CLASSIFIER)
        cls.analysis = load_module("project_entry2_analysis", ANALYSIS)

    def test_schema_cost_columns_reconstruct_field_tier_tokens(self):
        row = {"cost_do": "0", "cost_on": "2", "cost_sc": "3"}
        self.assertEqual(self.classifier.tier_tokens(row), ("o2", "s3"))

    def test_field_page_application_parser_validation_case(self):
        html = """
        <div class="tabbertab"><h2>2  Applications</h2>
        <table class="listing" summary="List of applications">
        <tr><th>Application ID</th><th>Title</th></tr>
        <tr class="row_odd" id="a17689"><td><a href="app.cgi?id=17689">17689</a></td><td>Brain predictors</td></tr>
        <tr class="row_even" id="a22783"><td><a href="app.cgi?id=22783">22783</a></td><td>Imaging and genetics</td></tr>
        </table></div>
        """
        parsed = self.classifier.parse_field_applications(html)
        self.assertEqual([row["app_id"] for row in parsed], ["17689", "22783"])
        self.assertEqual(parsed[1]["application_title_from_field_page"], "Imaging and genetics")

    def test_project_classification_uses_single_high_and_complement(self):
        projects = [
            {"app_id": "1", "start_date": "2024-08-01", "schema27_title": "Questionnaire project"},
            {"app_id": "2", "start_date": "2024-08-01", "schema27_title": "Field linked project"},
            {"app_id": "3", "start_date": "2024-08-01", "schema27_title": "Whole exome sequencing project"},
        ]
        stage3 = [
            {
                "app_id": "1",
                "classification": "NEWLY_RAP_BOUND",
                "confidence": "HIGH",
                "legacy_route_modalities": "QUESTIONNAIRES_ASSESSMENT",
                "already_rap_modalities": "",
                "matched_terms": "",
                "source_text_evidence": "",
            },
            {
                "app_id": "2",
                "classification": "UNCLEAR",
                "confidence": "LOW",
                "legacy_route_modalities": "",
                "already_rap_modalities": "",
                "matched_terms": "",
                "source_text_evidence": "",
            },
            {
                "app_id": "3",
                "classification": "UNCLEAR",
                "confidence": "LOW",
                "legacy_route_modalities": "",
                "already_rap_modalities": "",
                "matched_terms": "",
                "source_text_evidence": "",
                "schema27_title": "Whole exome sequencing project",
            },
        ]
        review = []
        field_links = [
            {
                "app_id": "2",
                "field_id": "25749",
                "field_title": "Eprime ed2 file",
                "field_tier": "o2 s3",
                "tier_source": "schema1_cost_do_cost_on_cost_sc",
                "field_private": 0,
                "item_type": "20",
                "main_category": "507",
                "debut": "2015-10-13T00:00:00",
                "version": "",
                "has_s3": 1,
                "has_o2": 1,
            }
        ]
        rows = {
            row["app_id"]: row
            for row in self.classifier.build_project_classification_rows(projects, stage3, review, field_links)
        }
        self.assertEqual(rows["1"]["LOW_STRICT"], 1)
        self.assertEqual(rows["1"]["HIGH_SENSITIVITY"], 0)
        self.assertEqual(rows["1"]["LOWER_SENSITIVITY_COMPARISON"], 1)
        self.assertEqual(rows["2"]["HIGH_SENSITIVITY"], 1)
        self.assertEqual(rows["2"]["hs_s3_direct"], 1)
        self.assertEqual(rows["2"]["LOW_STRICT"], 0)
        self.assertEqual(rows["3"]["HIGH_SENSITIVITY"], 1)
        self.assertEqual(rows["3"]["hs_wes_wgs_sequence"], 1)

    def test_generated_outputs_validate(self):
        self.classifier.validate_outputs()
        self.analysis.validate_outputs()
        self.analysis.validate_extended_outputs()

    def test_regression_output_includes_time_and_month_fixed_effects(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().regression_results)
        terms = {
            row["term"]
            for row in rows
            if row["model_id"] == "test1_high_sensitivity_count"
        }
        self.assertIn("Time", terms)
        self.assertIn("PostJuly2024", terms)
        self.assertIn("TimeAfterJuly2024", terms)
        self.assertIn("month_12", terms)

    def test_generated_regression_n_and_july_segment_convention(self):
        monthly = self.analysis.read_csv(self.analysis.Outputs().monthly)
        by_month = {row["month"]: row for row in monthly}
        self.assertEqual(by_month["2024-07"]["time_after_july2024"], "0")
        self.assertEqual(by_month["2024-08"]["time_after_july2024"], "1")
        self.assertTrue(any(int(row["high_sensitivity_count"]) == 0 for row in monthly))
        self.assertTrue(any(int(row["lower_sensitivity_count"]) == 0 for row in monthly))

        regressions = self.analysis.read_csv(self.analysis.Outputs().regression_results)
        n_by_model = {
            row["model_id"]: int(row["n_obs"])
            for row in regressions
            if row["term"] == "Intercept"
        }
        self.assertEqual(n_by_model["test1_high_sensitivity_count"], 84)
        self.assertEqual(n_by_model["test3_high_index"], 84)
        self.assertEqual(n_by_model["test3_lower_index"], 84)
        self.assertEqual(n_by_model["test3_high_minus_lower_difference"], 84)

    def test_run_model_keeps_zero_and_calendar_time_after_missing_share(self):
        rows = []
        for idx, month in enumerate(
            self.analysis.month_range(self.analysis.PRIMARY_START, self.analysis.PRIMARY_END),
            start=1,
        ):
            time_after = (
                (month.year - self.analysis.BREAK_MONTH.year) * 12
                + month.month
                - self.analysis.BREAK_MONTH.month
                if month >= self.analysis.BREAK_MONTH
                else 0
            )
            rows.append(
                {
                    "month": self.analysis.month_label(month),
                    "month_start": month.isoformat(),
                    "time": idx,
                    "post_july2024": 1 if month >= self.analysis.BREAK_MONTH else 0,
                    "time_after_july2024": time_after,
                    "month_of_year": month.month,
                    "synthetic_share": "0.25",
                }
            )
        for row in rows:
            if row["month"] == "2024-07":
                row["synthetic_share"] = ""
            if row["month"] == "2024-08":
                row["synthetic_share"] = 0

        _, fit = self.analysis.run_model(
            rows,
            "synthetic_share",
            "synthetic_share_model",
            "Synthetic",
            "Synthetic",
            "all",
        )
        included = {row["month"]: i for i, row in enumerate(fit["included_rows"])}
        time_index = fit["names"].index("Time")
        self.assertEqual(fit["n_obs"], 83)
        self.assertIn("2024-08", included)
        self.assertEqual(fit["X"][included["2024-08"]][time_index], 68.0)

    def test_stata_do_file_uses_official_newey(self):
        do_text = self.analysis.Outputs().stata_do.read_text(encoding="utf-8")
        self.assertIn("version 18.0", do_text)
        self.assertIn("args input_csv log_file table_csv tmp_dta end_ym", do_text)
        self.assertIn("if \"`input_csv'\" == \"\" local input_csv \"../data/project_entry2_monthly.csv\"", do_text)
        self.assertIn("if \"`end_ym'\" == \"\" local end_ym \"2025-12\"", do_text)
        self.assertIn("newey high_sensitivity_count", do_text)
        self.assertIn("newey index_lower_pre_mean", do_text)
        self.assertIn("newey index_high_pre_mean", do_text)
        self.assertIn("newey index_diff_pre_mean", do_text)
        self.assertIn("lincom time + time_after_july2024", do_text)
        self.assertIn("test time_after_july2024 = 0", do_text)
        self.assertIn("lag(3)", do_text)
        self.assertNotIn("test3_difference_index_pre_mean", do_text)

    def test_stata_style_regression_output_is_complete(self):
        text = self.analysis.Outputs().stata_style_python_table.read_text(encoding="utf-8")
        self.assertIn("Regression with Newey-West standard errors", text)
        for model_id in [
            "test1_high_sensitivity_count",
            "test2_high_share_all",
            "test3_lower_index",
            "test3_high_index",
            "test3_high_minus_lower_difference",
        ]:
            self.assertIn(model_id, text)
        self.assertIn("high_sensitivity_count", text)
        self.assertIn("monthFE = Yes", text)
        self.assertNotIn("12.month_of_year", text)
        self.assertIn("time_after_july2024", text)

    def test_test3_stacked_partition_outputs(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().test3_stacked)
        self.assertEqual(len(rows), 168)
        groups = {}
        for row in rows:
            groups[row["group"]] = groups.get(row["group"], 0) + 1
        self.assertEqual(groups["High"], 84)
        self.assertEqual(groups["Lower"], 84)
        july = [row for row in rows if row["month"] == "2024-07"]
        self.assertEqual(len(july), 2)
        self.assertTrue(all(row["time_after_july2024"] == "0" for row in july))
        self.assertTrue(any(row["group"] == "High" and int(row["raw_count"]) == 0 for row in rows))
        self.assertTrue(any(row["group"] == "Lower" and int(row["raw_count"]) == 0 for row in rows))

    def test_test3_difference_coefficients_match_high_minus_lower(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().regression_results)

        def estimate(model_id, term):
            return float(
                next(row for row in rows if row["model_id"] == model_id and row["term"] == term)[
                    "estimate"
                ]
            )

        for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
            expected = estimate("test3_high_index", term) - estimate("test3_lower_index", term)
            actual = estimate("test3_high_minus_lower_difference", term)
            self.assertAlmostEqual(actual, expected, places=6)

    def test_extended_monthly_panel_and_2026janapr_audit(self):
        monthly = self.analysis.read_csv(self.analysis.ExtendedOutputs().monthly)
        self.assertEqual(len(monthly), 88)
        by_month = {row["month"]: row for row in monthly}
        for month in ["2026-01", "2026-02", "2026-03", "2026-04"]:
            self.assertIn(month, by_month)
        self.assertNotIn("2026-05", by_month)
        self.assertNotIn("2026-06", by_month)
        self.assertEqual(by_month["2024-07"]["time_after_july2024"], "0")
        self.assertEqual(by_month["2024-08"]["time_after_july2024"], "1")
        self.assertEqual(by_month["2026-04"]["time_after_july2024"], "21")
        for row in monthly:
            high = int(row["high_sensitivity_count"])
            lower = int(row["lower_sensitivity_count"])
            all_count = int(row["all_count"])
            self.assertEqual(high + lower, all_count)
        self.assertTrue(any(int(row["high_sensitivity_count"]) == 0 for row in monthly))
        audit = self.analysis.read_csv(self.analysis.ExtendedOutputs().audit_2026)
        self.assertEqual([row["month"] for row in audit], ["2026-01", "2026-02", "2026-03", "2026-04"])
        self.assertEqual(sum(int(row["all_count"]) for row in audit), 468)
        self.assertEqual(sum(int(row["high_sensitivity_count"]) for row in audit), 95)
        self.assertEqual(sum(int(row["lower_sensitivity_count"]) for row in audit), 373)

    def test_extended_regression_n_and_test3_stack(self):
        regressions = self.analysis.read_csv(self.analysis.ExtendedOutputs().regression_results)
        n_by_model = {
            row["model_id"]: int(row["n_obs"])
            for row in regressions
            if row["term"] == "Intercept"
        }
        self.assertEqual(n_by_model["test1_high_sensitivity_count"], 88)
        self.assertEqual(n_by_model["test3_high_index"], 88)
        self.assertEqual(n_by_model["test3_lower_index"], 88)
        self.assertEqual(n_by_model["test3_high_minus_lower_difference"], 88)
        self.assertIn("test2_high_share_all", n_by_model)
        stacked = self.analysis.read_csv(self.analysis.ExtendedOutputs().test3_stacked)
        self.assertEqual(len(stacked), 176)
        self.assertEqual(sum(row["group"] == "High" for row in stacked), 88)
        self.assertEqual(sum(row["group"] == "Lower" for row in stacked), 88)

    def test_extended_test3_difference_coefficients_match_high_minus_lower(self):
        rows = self.analysis.read_csv(self.analysis.ExtendedOutputs().regression_results)

        def estimate(model_id, term):
            return float(
                next(row for row in rows if row["model_id"] == model_id and row["term"] == term)[
                    "estimate"
                ]
            )

        for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
            expected = estimate("test3_high_index", term) - estimate("test3_lower_index", term)
            actual = estimate("test3_high_minus_lower_difference", term)
            self.assertAlmostEqual(actual, expected, places=6)

    def test_original_baseline_outputs_remain_unchanged(self):
        monthly = self.analysis.read_csv(self.analysis.Outputs().monthly)
        self.assertEqual(len(monthly), 84)
        self.assertEqual(monthly[-1]["month"], "2025-12")
        baseline_report = self.analysis.Outputs().results_report.read_text(encoding="utf-8")
        self.assertNotIn("Project Entry2 Results Through 2026 Jan-Apr", baseline_report)
        baseline_figure = self.analysis.Outputs().test1_figure.read_text(encoding="utf-8")
        self.assertNotIn("Through Apr 2026", baseline_figure)

    def test_test1_figure_exists(self):
        path = self.analysis.Outputs().test1_figure
        self.assertTrue(path.exists(), path)
        self.assertIn("<svg", path.read_text(encoding="utf-8")[:100])


if __name__ == "__main__":
    unittest.main()
