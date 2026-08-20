import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage3_control_expansion as expansion


class Stage3ControlExpansionTests(unittest.TestCase):
    def _write_csv(
        self,
        path: Path,
        rows: list[dict[str, str]],
        fieldnames: list[str],
        delimiter: str = ",",
    ) -> None:
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
        title: str,
        notes: str = "",
        classification: str = "NEWLY_RAP_BOUND",
        start_date: str = "2022-01-01",
    ) -> dict[str, str]:
        return {
            "app_id": app_id,
            "project_start_date": start_date,
            "policy_period": "before_policy" if start_date < "2024-07-05" else "after_policy",
            "classification": classification,
            "confidence": "HIGH" if classification != "UNCLEAR" else "LOW",
            "manual_review_recommended": "no",
            "review_reasons": "",
            "already_rap_modalities": "WES" if classification == "ALREADY_RAP_BOUND" else "",
            "legacy_route_modalities": "GENOTYPING_IMPUTATION"
            if classification == "NEWLY_RAP_BOUND"
            else "",
            "ambiguous_modality_signals": "",
            "matched_terms": "",
            "evidence_source_fields": "",
            "source_text_evidence": title,
            "strict_already_rap_control_candidate": "no",
            "broader_already_rap_candidate": "yes"
            if classification == "ALREADY_RAP_BOUND"
            else "no",
            "any_already_rap_modality_candidate": "yes"
            if classification == "ALREADY_RAP_BOUND"
            else "no",
            "schema27_title": title,
            "schema27_notes": notes,
            "website_excerpt": notes[:120],
            "website_url": f"https://example.test/projects/{app_id}",
            "schema27_institution": "Example",
            "schema27_pi": "PI",
        }

    def test_builds_incremental_layers_without_replacing_c0(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage3_path = root / "stage3.csv"
            schema19_path = root / "schema19.tsv"
            schema24_path = root / "schema24.tsv"

            rows = [
                self._stage3_row(
                    str(i),
                    f"Baseline exome project {i}",
                    classification="ALREADY_RAP_BOUND",
                    start_date="2022-01-01",
                )
                for i in range(1, 43)
            ]
            rows.extend(
                [
                    self._stage3_row(
                        "43",
                        "Whole genome sequencing predictors",
                        "We will use whole genome sequencing data from UK Biobank.",
                    ),
                    self._stage3_row(
                        "44",
                        "LoF variant burden project",
                        "We will test loss-of-function variants and variant burden signals.",
                    ),
                    self._stage3_row(
                        "45",
                        "OMOP health data project",
                        "We will use OMOP common data model tables.",
                        classification="MIXED",
                        start_date="2025-01-01",
                    ),
                    self._stage3_row("46", "Methods project", "Statistical genetics methods."),
                    self._stage3_row("47", "Vague retinal project", "Retinal structure analysis."),
                    self._stage3_row(
                        "48",
                        "External sequence project",
                        (
                            "We will use UK Biobank data and a second dataset with "
                            "gene expression and genome sequence data."
                        ),
                    ),
                ]
            )
            self._write_csv(stage3_path, rows, list(rows[0].keys()))
            self._write_csv(
                schema19_path,
                [
                    {
                        "pub_id": "p1",
                        "title": "RAP methods",
                        "keywords": "",
                        "authors": "",
                        "journal": "",
                        "year_pub": "2022",
                        "date_pub": "2022-11-29",
                        "abstract": (
                            "<p>We processed UK Biobank whole-genome sequence data "
                            "on the cloud-based UK Biobank Research Analysis Platform.</p>"
                        ),
                        "pubmed_id": "",
                        "doi": "10.example/rap",
                        "url": "https://doi.org/10.example/rap",
                        "cite_total": "",
                        "cite_recent": "",
                        "cite_updated": "",
                    },
                    {
                        "pub_id": "p2",
                        "title": "Retinal structure",
                        "keywords": "",
                        "authors": "",
                        "journal": "",
                        "year_pub": "2023",
                        "date_pub": "2023-06-01",
                        "abstract": (
                            "<p>UK Biobank participants with OCT and exome sequencing "
                            "data were included.</p>"
                        ),
                        "pubmed_id": "",
                        "doi": "10.example/exome",
                        "url": "https://doi.org/10.example/exome",
                        "cite_total": "",
                        "cite_recent": "",
                        "cite_updated": "",
                    },
                ],
                [
                    "pub_id",
                    "title",
                    "keywords",
                    "authors",
                    "journal",
                    "year_pub",
                    "date_pub",
                    "abstract",
                    "pubmed_id",
                    "doi",
                    "url",
                    "cite_total",
                    "cite_recent",
                    "cite_updated",
                ],
                delimiter="\t",
            )
            self._write_csv(
                schema24_path,
                [{"app_id": "46", "pub_id": "p1"}, {"app_id": "47", "pub_id": "p2"}],
                ["app_id", "pub_id"],
                delimiter="\t",
            )

            summary = expansion.build_control_expansion_outputs(
                stage3_classification_path=stage3_path,
                schema19_path=schema19_path,
                schema24_path=schema24_path,
                output_dir=root,
                expected_working=len(rows),
                source_commit="abc123",
            )

            paths = expansion.output_paths(root)
            counts = {
                row["layer"]: row
                for row in self._read_csv(paths.layer_counts)
            }
            self.assertEqual(counts["C0"]["new_projects"], "42")
            self.assertEqual(counts["C1"]["new_projects"], "1")
            self.assertEqual(counts["C3"]["new_projects"], "1")
            self.assertEqual(counts["C4"]["new_projects"], "1")
            self.assertEqual(counts["C5"]["new_projects"], "1")
            self.assertEqual(counts["C6"]["new_projects"], "1")
            self.assertEqual(summary["cumulative_control_candidate_projects"], 47)

            review = {
                row["app_id"]: row
                for row in self._read_csv(paths.project_review)
            }
            self.assertEqual(review["46"]["expansion_layer"], "C5")
            self.assertEqual(review["46"]["source_timing"], "pre_policy_publication")
            self.assertEqual(review["47"]["expansion_layer"], "C6")
            self.assertNotIn("48", review)

    def test_requires_fixed_c0_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage3_path = root / "stage3.csv"
            rows = [
                self._stage3_row(
                    "1",
                    "Only one baseline",
                    classification="ALREADY_RAP_BOUND",
                )
            ]
            self._write_csv(stage3_path, rows, list(rows[0].keys()))
            with self.assertRaisesRegex(ValueError, "fixed C0 baseline of 42"):
                expansion.build_control_expansion_outputs(
                    stage3_classification_path=stage3_path,
                    schema19_path=root / "missing19.tsv",
                    schema24_path=root / "missing24.tsv",
                    output_dir=root,
                    expected_working=1,
                    source_commit="abc123",
                )


if __name__ == "__main__":
    unittest.main()
