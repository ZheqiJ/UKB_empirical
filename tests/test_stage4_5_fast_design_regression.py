import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage4_5_fast_design_regression as fast


class Stage45FastDesignRegressionTests(unittest.TestCase):
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

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _stage3_row(
        self,
        app_id: str,
        start_date: str,
        classification: str,
        title: str,
    ) -> dict[str, str]:
        return {
            "app_id": app_id,
            "project_start_date": start_date,
            "policy_period": "after_policy" if start_date >= "2024-07-05" else "before_policy",
            "classification": classification,
            "confidence": "HIGH",
            "manual_review_recommended": "no",
            "review_reasons": "",
            "already_rap_modalities": "WES" if classification == "ALREADY_RAP_BOUND" else "",
            "legacy_route_modalities": "GENOTYPING_IMPUTATION" if classification == "NEWLY_RAP_BOUND" else "",
            "ambiguous_modality_signals": "",
            "matched_terms": "",
            "evidence_source_fields": "",
            "source_text_evidence": title,
            "strict_already_rap_control_candidate": "no",
            "broader_already_rap_candidate": "no",
            "any_already_rap_modality_candidate": "no",
            "schema27_title": title,
            "schema27_notes": "",
            "website_excerpt": "",
            "website_url": f"https://example.test/{app_id}",
            "schema27_institution": "Example",
            "schema27_pi": "PI",
        }

    def test_builds_fast_outputs_from_stage3_fixed_universe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage3_path = root / "stage3.csv"
            control_path = root / "control.csv"
            schema19_path = root / "schema19.tsv"
            schema24_path = root / "schema24.tsv"
            dmca_path = root / "dmca.csv"

            stage3_rows = [
                self._stage3_row("103356", "2023-01-01", "NEWLY_RAP_BOUND", "Treated DMCA"),
                self._stage3_row("66995", "2023-02-01", "ALREADY_RAP_BOUND", "C0 DMCA"),
                self._stage3_row("3", "2024-08-01", "NEWLY_RAP_BOUND", "Post starter"),
                self._stage3_row("4", "2023-03-01", "MIXED", "Mixed"),
                self._stage3_row("5", "2023-04-01", "UNCLEAR", "Unclear"),
            ]
            self._write_csv(stage3_path, stage3_rows, list(stage3_rows[0].keys()))
            control_rows = [
                {
                    "app_id": "66995",
                    "start_date": "2023-02-01",
                    "policy_period": "before_policy",
                    "expansion_layer": "C0",
                    "previous_classification": "ALREADY_RAP_BOUND",
                    "previous_confidence": "HIGH",
                    "proposed_new_classification": "CONTROL_CANDIDATE_C0",
                    "evidence_type": "current_conservative_classifier",
                    "evidence_source": "",
                    "source_timing": "",
                    "supporting_text_excerpt": "",
                    "inferred_underlying_data_product_or_rap_use": "",
                    "matched_term_or_expression": "",
                    "evidence_dictionary_term_id": "",
                    "confidence": "HIGH",
                    "manual_review_flag": "no",
                    "manual_review_reason": "",
                    "source_pub_id": "",
                    "source_pub_date": "",
                    "source_doi": "",
                    "previous_already_rap_modalities": "",
                    "previous_legacy_route_modalities": "",
                    "schema27_title": "C0 DMCA",
                    "website_url": "",
                }
            ]
            self._write_csv(control_path, control_rows, list(control_rows[0].keys()))
            schema19_rows = [
                {
                    "pub_id": "p1",
                    "title": "Pre publication",
                    "keywords": "",
                    "authors": "",
                    "journal": "J",
                    "year_pub": "2023",
                    "date_pub": "2023-08-01",
                    "abstract": "",
                    "pubmed_id": "",
                    "doi": "10.test/pre",
                    "url": "",
                    "cite_total": "",
                    "cite_recent": "",
                    "cite_updated": "",
                },
                {
                    "pub_id": "p2",
                    "title": "Post publication",
                    "keywords": "",
                    "authors": "",
                    "journal": "J",
                    "year_pub": "2025",
                    "date_pub": "2025-08-01",
                    "abstract": "",
                    "pubmed_id": "",
                    "doi": "10.test/post",
                    "url": "",
                    "cite_total": "",
                    "cite_recent": "",
                    "cite_updated": "",
                },
            ]
            self._write_csv(schema19_path, schema19_rows, list(schema19_rows[0].keys()), delimiter="\t")
            self._write_csv(
                schema24_path,
                [{"app_id": "103356", "pub_id": "p1"}, {"app_id": "66995", "pub_id": "p2"}],
                ["app_id", "pub_id"],
                delimiter="\t",
            )
            dmca_rows = [
                {
                    "candidate_app_id": "103356",
                    "notice_id": "n1",
                    "lineage_id": "l1",
                    "notice_date": "2025-10-01",
                    "repo_url": "https://github.com/example/repo",
                    "evidence_class": "A1_DIRECT_APP_ID",
                    "match_grade": "confirmed",
                }
            ]
            self._write_csv(dmca_path, dmca_rows, list(dmca_rows[0].keys()))

            summary = fast.build_fast_outputs(
                stage3_path=stage3_path,
                timing_metadata_path=root / "missing_timing.csv",
                control_expansion_path=control_path,
                schema19_path=schema19_path,
                schema24_path=schema24_path,
                dmca_manual_review_path=dmca_path,
                output_dir=root,
                expected_universe=5,
                source_commit="abc123",
            )

            paths = fast.output_paths(root)
            self.assertEqual(summary["working_universe_projects"], 5)
            self.assertTrue(paths.application_outcomes.exists())
            self.assertTrue(paths.regression_results.exists())
            self.assertTrue(paths.publication_did_figure.exists())

            apps = {row["app_id"]: row for row in self._read_csv(paths.application_outcomes)}
            self.assertEqual(apps["66995"]["cumulative_control_C0"], "1")
            self.assertEqual(apps["103356"]["regression_group_CONTROL_C0"], "treated")
            self.assertEqual(apps["3"]["p1_existing_project_sample"], "0")
            self.assertEqual(apps["103356"]["dmca_strict_21"], "1")

            unmatched = self._read_csv(paths.dmca_unmatched_apps)
            self.assertGreater(len(unmatched), 0)
            self.assertIn("47267", {row["app_id"] for row in unmatched})


if __name__ == "__main__":
    unittest.main()
