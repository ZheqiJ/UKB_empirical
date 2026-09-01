import importlib.util
import sys
import unittest
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "analyses" / "interrupted_time_series" / "publications" / "scripts" / "publication_its_analysis.py"


def load_module():
    spec = importlib.util.spec_from_file_location("publication_its_analysis", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PublicationITSAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = load_module()

    def test_publication_outputs_validate(self):
        self.analysis.validate_outputs()

    def test_system_monthly_aggregation_and_fractional_reconciliation(self):
        events = self.analysis.read_csv(self.analysis.Outputs().clean_events)
        system = self.analysis.read_csv(self.analysis.Outputs().system_monthly)
        by_month = defaultdict(lambda: {"links": 0, "pubs": set(), "frac": 0.0})
        pub_weights = defaultdict(float)
        for event in events:
            by_month[event["publication_month"]]["links"] += 1
            by_month[event["publication_month"]]["pubs"].add(event["pub_id"])
            by_month[event["publication_month"]]["frac"] += float(event["fractional_weight"])
            pub_weights[event["pub_id"]] += float(event["fractional_weight"])
            self.assertGreaterEqual(int(event["project_age_months"]), 0)
            self.assertGreaterEqual(event["publication_date"], event["project_start_date"])
        self.assertTrue(all(abs(weight - 1.0) < 1e-5 for weight in pub_weights.values()))
        for row in system:
            observed = by_month[row["month_start"]]
            self.assertEqual(int(row["publication_app_links"]), observed["links"])
            self.assertEqual(int(row["unique_publication_ids"]), len(observed["pubs"]))
            self.assertAlmostEqual(float(row["fractional_publication_count"]), observed["frac"], places=2)
            self.assertAlmostEqual(float(row["fractional_publication_count"]), float(row["unique_publication_ids"]), places=2)

    def test_july_2024_level_shift_coding(self):
        months = [self.analysis.date(2024, 6, 1), self.analysis.date(2024, 7, 1), self.analysis.date(2024, 8, 1)]
        x, names = self.analysis.design_rows(months)
        post = names.index("PostJuly2024")
        time_after = names.index("TimeAfterJuly2024")
        self.assertEqual([row[post] for row in x], [0.0, 1.0, 1.0])
        self.assertEqual([row[time_after] for row in x], [0.0, 0.0, 1.0])

    def test_calendar_and_project_cohort_indicators_are_distinct(self):
        system = self.analysis.read_csv(self.analysis.Outputs().system_monthly)
        self.assertEqual(next(r for r in system if r["month"] == "2024-06")["calendar_post_july_2024"], "0")
        self.assertEqual(next(r for r in system if r["month"] == "2024-07")["calendar_post_july_2024"], "1")
        self.assertIn("jul_sep_2024_window", system[0])
        self.assertTrue(all(not key.startswith("transition_pause") for key in system[0]))
        followup = self.analysis.read_csv(self.analysis.Outputs().project_followup)
        for row in followup:
            expected = "1" if row["project_start_date"] >= self.analysis.BREAK_DATE.isoformat() else "0"
            self.assertEqual(row["project_cohort_post_rap"], expected)

    def test_followup_outcomes_exclude_right_censored_projects(self):
        followup = self.analysis.read_csv(self.analysis.Outputs().project_followup)
        events = self.analysis.read_csv(self.analysis.Outputs().clean_events)
        by_project = defaultdict(list)
        for event in events:
            by_project[event["app_id"]].append(event)
        for row in followup:
            if row["followup_eligible_18m"] == "0":
                self.assertEqual(row["pub18_fractional"], "")
                self.assertEqual(row["anypub18"], "")
            if row["followup_eligible_24m"] == "0":
                self.assertEqual(row["pub24_fractional"], "")
                self.assertEqual(row["anypub24"], "")
            for h in [12, 18, 24]:
                if row[f"followup_eligible_{h}m"] == "1":
                    cutoff = self.analysis.add_months_exact(self.analysis.parse_date(row["project_start_date"]), h)
                    expected = sum(float(e["fractional_weight"]) for e in by_project[row["app_id"]] if self.analysis.parse_date(e["publication_date"]) <= cutoff)
                    self.assertAlmostEqual(float(row[f"pub{h}_fractional"]), expected, places=5)
        cohort = self.analysis.read_csv(self.analysis.Outputs().cohort_summary)
        post18 = next(r for r in cohort if r["project_cohort"] == "post_rap_project_start" and r["followup_horizon_months"] == "18")
        post24 = next(r for r in cohort if r["project_cohort"] == "post_rap_project_start" and r["followup_horizon_months"] == "24")
        self.assertEqual(post18["eligible_projects"], "0")
        self.assertEqual(post24["eligible_projects"], "0")

    def test_project_start_contributions_reconcile_to_system_output(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().cohort_contributions)
        for row in rows:
            total = float(row["pre_transition_start_contribution"]) + float(row["post_transition_start_contribution"])
            self.assertAlmostEqual(total, float(row["aggregate_fractional_publication_count"]), places=5)
            self.assertAlmostEqual(total, float(row["unique_publication_ids"]), places=5)

    def test_new_y1_contrast_and_sensitivity_tables_exist(self):
        contrasts = self.analysis.read_csv(self.analysis.Outputs().fitted_contrasts)
        self.assertEqual([r["horizon_months_after_july_2024"] for r in contrasts], ["3", "6", "12", "18"])
        self.assertIn("absolute_difference_per_month", contrasts[0])
        cumulative = self.analysis.read_csv(self.analysis.Outputs().cumulative_pretrend_gaps)
        self.assertEqual({r["period"] for r in cumulative}, {"July_2024_to_June_2025", "July_2024_to_December_2025"})
        transition = self.analysis.read_csv(self.analysis.Outputs().transition_lag_sensitivity)
        self.assertIn("lagged_response_3_months", {r["specification"] for r in transition})
        self.assertIn("transition_window_6_months_excluded", {r["specification"] for r in transition})
        endpoint = self.analysis.read_csv(self.analysis.Outputs().endpoint_sensitivity)
        self.assertEqual({r["window"] for r in endpoint}, {"2019-01_to_2025-06", "2019-01_to_2025-09", "2019-01_to_2025-12"})

    def test_pipeline_benchmark_uses_only_pre_transition_profile_and_reconciles(self):
        profile = self.analysis.read_csv(self.analysis.Outputs().pipeline_age_profile)
        self.assertTrue(all(r["estimated_using_calendar_months_before"] == self.analysis.BREAK_MONTH.isoformat() for r in profile))
        self.assertIn("project_age_months", profile[0])
        self.assertIn("smoothed_monthly_fractional_publications_per_project", profile[0])
        pipeline = self.analysis.read_csv(self.analysis.Outputs().pipeline_gap)
        self.assertIn("pipeline_gap_ci_low", pipeline[0])
        self.assertIn("trend_adjusted_pipeline_gap", pipeline[0])
        cumulative = 0.0
        for row in [r for r in pipeline if r["calendar_post_july_2024"] == "1"]:
            cumulative += float(row["pipeline_gap_actual_minus_expected"])
            self.assertAlmostEqual(cumulative, float(row["cumulative_pipeline_gap_since_july_2024"]), places=2)
        sensitivity = self.analysis.read_csv(self.analysis.Outputs().pipeline_benchmark_sensitivity)
        self.assertIn("trend_adjusted_gap", sensitivity[0])

    def test_hac_lag_changes_only_uncertainty(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().hac_sensitivity)
        for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
            estimates = {row["estimate"] for row in rows if row["term"] == term}
            self.assertEqual(len(estimates), 1)

    def test_report_uses_revised_hierarchy_and_cautions(self):
        report = self.analysis.Outputs().results_report.read_text()
        self.assertIn("Y1 monthly unique UKB-linked publication output is the primary H2 publication outcome", report)
        self.assertIn("## 1. How Did Total Publication Output Change Around And After July 2024?", report)
        self.assertIn("## 2. Who Generated The Post-July Publication Output?", report)
        self.assertIn("## 3. Can Lifecycle And Pipeline Composition Account For The Pattern?", report)
        self.assertIn("## 4. How Do Post-Transition Project-Start Cohorts Perform At Comparable Early Ages?", report)
        self.assertIn("At the aggregate system-month level, `fractional_publication_count` equals `unique_publication_ids` by construction", report)
        self.assertIn("`PostJuly2024` directly represents the fitted July level shift", report)
        self.assertIn("specification-sensitive across the linear and Poisson functional forms", report)
        self.assertIn("descriptive pre-trend benchmark differences, not causal counterfactual effects", report)
        self.assertIn("not RAP-to-publication lag", report)
        self.assertIn("cannot establish that RAP caused publications", report)
        self.assertIn("Total publication growth is not the same object as project-level productivity growth", report)
        self.assertIn("does not separately identify unrestricted age, period, and cohort effects", report)
        self.assertIn("Completion Checklist", report)

    def test_y8_lifecycle_adjusted_project_month_regressions_exist(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().project_month_regression)
        self.assertEqual({r["model"] for r in rows}, {"Lifecycle-adjusted project-month PPML", "Lifecycle-adjusted project-month LPM"})
        self.assertTrue(all(int(r["project_clusters"]) > 100 for r in rows))
        self.assertTrue(all(r["project_cluster_p_value"] != "" for r in rows))
        self.assertTrue(all("no saturated age-period-cohort design" in r["identifying_restriction"] for r in rows))

    def test_time_to_first_outputs_include_km_and_legacy_age_share(self):
        timing = self.analysis.read_csv(self.analysis.Outputs().first_pub_timing)
        self.assertIn("share_with_first_publication_by_age_among_projects_observable_to_age_percent", timing[0])
        old_metric = "cumulative_first_publication_" + "probability_percent"
        self.assertNotIn(old_metric, timing[0])
        km = self.analysis.read_csv(self.analysis.Outputs().first_pub_km)
        self.assertIn("Kaplan-Meier 1 minus survival", {r["estimator"] for r in km})
        self.assertIn("number_at_risk", km[0])
        risk = self.analysis.read_csv(self.analysis.Outputs().first_pub_risk_table)
        self.assertIn("number_at_risk", risk[0])
        report = self.analysis.Outputs().results_report.read_text()
        self.assertIn("Y7 now reports Kaplan-Meier `1 - S(age)` curves", report)

    def test_pub12_start_cohort_outputs_exist(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().start_cohort_summary)
        self.assertEqual([r["start_cohort"] for r in rows], ["2021H1", "2021H2", "2022H1", "2022H2", "2023H1", "2023H2", "2024H1", "2024H2"])
        self.assertTrue(all("pub12_mean_fractional" in r for r in rows))
        self.assertEqual(next(r for r in rows if r["start_cohort"] == "2024H2")["project_start_cohort_post_transition"], "1")

    def test_stata_style_output_is_report_ready(self):
        output = self.analysis.Outputs().stata_style_output.read_text()
        self.assertIn("Publication total-output segmented ITS, primary model", output)
        self.assertIn("Outcome: monthly number of unique UKB-linked publications", output)
        self.assertIn("Number of obs = 84", output)
        self.assertIn("P>|z|", output)
        self.assertIn("Aggregate-output measurement sensitivity", output)
        self.assertIn("Newey-West HAC lag sensitivity", output)
        self.assertIn("Prais-Winsten AR(1)", output)
        self.assertIn("Poisson QMLE count robustness", output)
        self.assertIn("Descriptive pre-trend benchmark fitted differences", output)
        self.assertIn("Transition-window and lagged-response sensitivity", output)
        self.assertIn("Lifecycle-adjusted project-month models", output)
        self.assertIn("Fixed-follow-up pooled project-cohort comparisons", output)
        self.assertIn("Right-edge endpoint sensitivity", output)
        report = self.analysis.Outputs().results_report.read_text()
        self.assertIn("Stata-Style Output For Reporting", report)
        self.assertIn("publication_stata_style_results.txt", report)


if __name__ == "__main__":
    unittest.main()
