import importlib.util
import sys
import unittest
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

    def test_incumbent_breakpoint_definition(self):
        projects, pubs, links = self.analysis.load_inputs()
        events, all_clean_events, audit = self.analysis.build_events(projects, pubs, links)
        self.assertEqual(audit["all_cleaned_publication_app_events"], 12568)
        self.assertTrue(all(e["project_start_date"] < self.analysis.BREAK_DATE for e in events))
        self.assertTrue(all(e["publication_date"] >= e["project_start_date"] for e in all_clean_events))

    def test_publication_lag_matches_documented_distribution(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().lag)
        shares = {row["lag_bin"]: row["share_percent"] for row in rows}
        self.assertEqual(rows[0]["median_lag_months_all_events"], "41.000")
        self.assertEqual(shares["0_6_months"], "1.15")
        self.assertEqual(shares["7_12_months"], "4.04")
        self.assertEqual(shares["13_24_months"], "15.73")
        self.assertEqual(shares["25_48_months"], "38.78")
        self.assertEqual(shares["49_plus_months"], "40.30")

    def test_hac_point_estimates_are_invariant(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().hac_sensitivity)
        for term in ["PostJuly2024", "TimeAfterJuly2024"]:
            estimates = {row["estimate"] for row in rows if row["term"] == term}
            self.assertEqual(len(estimates), 1)

    def test_report_contains_required_cautions(self):
        report = self.analysis.Outputs().results_report.read_text()
        self.assertIn("not RAP-to-publication lag", report)
        self.assertIn("cannot establish that RAP caused publications", report)
        self.assertIn("not the verified individual RAP-exposure date", report)
        self.assertIn("Classification: C. Gradual post-transition increase", report)


if __name__ == "__main__":
    unittest.main()
