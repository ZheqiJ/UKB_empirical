import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage6_panel_regression as stage6


class Stage6PanelRegressionTests(unittest.TestCase):
    def _write_csv(
        self,
        path: Path,
        rows: list[dict[str, str]],
        fieldnames: list[str],
        delimiter: str = ",",
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(rows)

    def _app_row(self, app_id: str, start: str, group: str) -> dict[str, str]:
        return {
            "app_id": app_id,
            "project_start_date": start,
            "project_start_year": start[:4],
            "post_policy_start": "1" if start >= "2024-07-05" else "0",
            "original_stage3_classification": "NEWLY_RAP_BOUND" if group == "treated" else "ALREADY_RAP_BOUND",
            "stage3_confidence": "HIGH",
            "control_layer": "C0" if group == "control" else "",
            "cumulative_control_C0": "1" if group == "control" else "0",
            "cumulative_control_C01": "1" if group == "control" else "0",
            "cumulative_control_C03": "1" if group == "control" else "0",
            "cumulative_control_C05": "1" if group == "control" else "0",
            "cumulative_control_C06": "1" if group == "control" else "0",
            "regression_group_CONTROL_C0": group,
            "regression_group_CONTROL_C01": group,
            "regression_group_CONTROL_C03": group,
            "regression_group_CONTROL_C05": group,
            "schema27_title": f"Project {app_id}",
            "schema27_pi": "PI",
            "schema27_institution": "Institution",
        }

    def test_publication_audit_and_risk_set_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apps = [
                self._app_row("1", "2024-08-15", "treated"),
                self._app_row("2", "2022-07-01", "control"),
            ]
            pubs = [
                {
                    "pub_id": "p_before",
                    "title": "Before start",
                    "keywords": "",
                    "authors": "",
                    "journal": "",
                    "year_pub": "2024",
                    "date_pub": "2024-07-01",
                    "abstract": "",
                    "pubmed_id": "",
                    "doi": "",
                    "url": "",
                    "cite_total": "",
                    "cite_recent": "",
                    "cite_updated": "",
                },
                {
                    "pub_id": "p_exact",
                    "title": "Exact",
                    "keywords": "",
                    "authors": "",
                    "journal": "",
                    "year_pub": "2024",
                    "date_pub": "2024-09-01",
                    "abstract": "",
                    "pubmed_id": "",
                    "doi": "",
                    "url": "",
                    "cite_total": "",
                    "cite_recent": "",
                    "cite_updated": "",
                },
                {
                    "pub_id": "p_year",
                    "title": "Year only",
                    "keywords": "",
                    "authors": "",
                    "journal": "",
                    "year_pub": "2024",
                    "date_pub": "2024",
                    "abstract": "",
                    "pubmed_id": "",
                    "doi": "",
                    "url": "",
                    "cite_total": "",
                    "cite_recent": "",
                    "cite_updated": "",
                },
                {
                    "pub_id": "p_late",
                    "title": "Late",
                    "keywords": "",
                    "authors": "",
                    "journal": "",
                    "year_pub": "2026",
                    "date_pub": "2026-07-16",
                    "abstract": "",
                    "pubmed_id": "",
                    "doi": "",
                    "url": "",
                    "cite_total": "",
                    "cite_recent": "",
                    "cite_updated": "",
                },
            ]
            links = [
                {"app_id": "1", "pub_id": "p_before"},
                {"app_id": "1", "pub_id": "p_exact"},
                {"app_id": "1", "pub_id": "p_year"},
                {"app_id": "1", "pub_id": "p_late"},
                {"app_id": "1", "pub_id": "p_late"},
            ]

            app_path = root / "apps.csv"
            schema19 = root / "schema19.tsv"
            schema24 = root / "schema24.tsv"
            self._write_csv(app_path, apps, list(apps[0].keys()))
            self._write_csv(schema19, pubs, list(pubs[0].keys()), delimiter="\t")
            self._write_csv(schema24, links, ["app_id", "pub_id"], delimiter="\t")

            app_rows, apps_by_id = stage6.load_applications(app_path, expected_universe=2)
            events, audit, summary = stage6.build_publication_events(apps_by_id, schema19, schema24)
            issue_types = [row["issue_type"] for row in audit]

            self.assertEqual(summary["year_only_date_pub"], 1)
            self.assertIn("publication_before_project_start", issue_types)
            self.assertIn("non_exact_or_missing_publication_date", issue_types)
            self.assertIn("duplicate_app_pub_pair", issue_types)
            self.assertIn("after_main_complete_panel_window", issue_types)

            quarter_counts, month_counts = stage6.index_events(events)
            quarter_panel = stage6.build_quarter_panel(app_rows, quarter_counts)
            month_panel = stage6.build_month_panel(app_rows, month_counts)

            app1_quarters = [row for row in quarter_panel if row["app_id"] == "1"]
            self.assertEqual(app1_quarters[0]["quarter"], "2024Q3")
            self.assertEqual(app1_quarters[0]["partial_first_quarter"], 1)
            self.assertTrue(all(row["quarter"] != "2024Q2" for row in app1_quarters))
            self.assertTrue(all(not str(row["quarter"]).startswith("2026Q3") for row in quarter_panel))
            self.assertTrue(all(row["month"] != "2026-07" for row in month_panel))
            self.assertEqual(sum(row["publication_count"] for row in app1_quarters if row["quarter"] == "2024Q3"), 1)


if __name__ == "__main__":
    unittest.main()
