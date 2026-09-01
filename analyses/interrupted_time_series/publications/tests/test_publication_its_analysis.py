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
        for row in followup:
            if row["followup_eligible_18m"] == "0":
                self.assertEqual(row["pub18_fractional"], "")
                self.assertEqual(row["anypub18"], "")
            if row["followup_eligible_24m"] == "0":
                self.assertEqual(row["pub24_fractional"], "")
                self.assertEqual(row["anypub24"], "")
        cohort = self.analysis.read_csv(self.analysis.Outputs().cohort_summary)
        post18 = next(r for r in cohort if r["project_cohort"] == "post_rap_project_start" and r["followup_horizon_months"] == "18")
        post24 = next(r for r in cohort if r["project_cohort"] == "post_rap_project_start" and r["followup_horizon_months"] == "24")
        self.assertEqual(post18["eligible_projects"], "0")
        self.assertEqual(post24["eligible_projects"], "0")

    def test_pipeline_benchmark_uses_only_pre_transition_profile_and_reconciles(self):
        profile = self.analysis.read_csv(self.analysis.Outputs().pipeline_age_profile)
        self.assertTrue(all(r["estimated_using_calendar_months_before"] == self.analysis.BREAK_MONTH.isoformat() for r in profile))
        pipeline = self.analysis.read_csv(self.analysis.Outputs().pipeline_gap)
        cumulative = 0.0
        for row in [r for r in pipeline if r["calendar_post_july_2024"] == "1"]:
            cumulative += float(row["pipeline_gap_actual_minus_expected"])
            self.assertAlmostEqual(cumulative, float(row["cumulative_pipeline_gap_since_july_2024"]), places=2)

    def test_hac_lag_changes_only_uncertainty(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().hac_sensitivity)
        for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
            estimates = {row["estimate"] for row in rows if row["term"] == term}
            self.assertEqual(len(estimates), 1)

    def test_report_uses_revised_hierarchy_and_cautions(self):
        report = self.analysis.Outputs().results_report.read_text()
        self.assertIn("Y1 total monthly fractional publication output is primary", report)
        self.assertIn("monthly total `fractional_publication_count`, with no incumbent denominator", report)
        self.assertIn("not RAP-to-publication lag", report)
        self.assertIn("cannot establish that RAP caused publications", report)
        self.assertIn("Total publication growth is not the same object as project-level productivity growth", report)


if __name__ == "__main__":
    unittest.main()
