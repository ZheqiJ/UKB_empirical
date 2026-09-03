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

    def test_project_classification_keeps_low_strict_out_of_high(self):
        projects = [
            {"app_id": "1", "start_date": "2024-08-01", "schema27_title": "Questionnaire project"},
            {"app_id": "2", "start_date": "2024-08-01", "schema27_title": "Field linked project"},
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
        self.assertEqual(rows["1"]["HIGH_C05_S3"], 0)
        self.assertEqual(rows["2"]["HIGH_C05_S3"], 1)
        self.assertEqual(rows["2"]["LOW_STRICT"], 0)

    def test_generated_outputs_validate(self):
        self.classifier.validate_outputs()
        self.analysis.validate_outputs()

    def test_regression_output_includes_time_and_month_fixed_effects(self):
        rows = self.analysis.read_csv(self.analysis.Outputs().regression_results)
        terms = {
            row["term"]
            for row in rows
            if row["model_id"] == "test1_primary_high_c05_s3"
        }
        self.assertIn("Time", terms)
        self.assertIn("PostJuly2024", terms)
        self.assertIn("TimeAfterJuly2024", terms)
        self.assertIn("month_12", terms)

    def test_stata_do_file_uses_official_newey(self):
        do_text = self.analysis.Outputs().stata_do.read_text(encoding="utf-8")
        self.assertIn("version 18.0", do_text)
        self.assertIn("newey high_c05_s3_count", do_text)
        self.assertIn("lag(3)", do_text)


if __name__ == "__main__":
    unittest.main()
