import csv
import tempfile
import unittest
from pathlib import Path

from scripts import stage3_classify_rap_exposure as stage3


class Stage3RapExposureClassificationTests(unittest.TestCase):
    def _write_csv(self, path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_classifies_specific_modalities_without_using_tiers(self):
        base = {
            "app_id": "1",
            "schema27_institution": "Example University",
            "schema27_pi": "Dr Example",
            "start_date": "2022-01-01",
            "website_url": "https://example.test/project",
            "website_match_status": "matched_one_website_record",
            "website_match_count": "1",
            "match_methods": "test",
        }

        already = stage3.classify_project(
            {**base, "schema27_title": "Whole exome sequencing of cardiomyopathy"},
            {"notes": "Analyse UK Biobank exome sequencing data."},
            {"excerpt": ""},
        )
        self.assertEqual(already["classification"], "ALREADY_RAP_BOUND")
        self.assertEqual(already["confidence"], "HIGH")
        self.assertEqual(already["strict_already_rap_control_candidate"], "yes")

        newly = stage3.classify_project(
            {**base, "schema27_title": "Genome-wide association study of blood pressure"},
            {"notes": "Use GWAS, imputed genotype data, and blood pressure fields."},
            {"excerpt": ""},
        )
        self.assertEqual(newly["classification"], "NEWLY_RAP_BOUND")
        self.assertIn("GENOTYPING_IMPUTATION", newly["legacy_route_modalities"])

        mixed = stage3.classify_project(
            {**base, "schema27_title": "WGS and MRI predictors of disease"},
            {"notes": "Combine whole genome sequencing with MRI image-derived phenotypes."},
            {"excerpt": ""},
        )
        self.assertEqual(mixed["classification"], "MIXED")
        self.assertEqual(mixed["manual_review_recommended"], "yes")

        unclear = stage3.classify_project(
            {**base, "schema27_title": "Genetic factors in common disease"},
            {"notes": "Study genetic and genomic risk factors."},
            {"excerpt": ""},
        )
        self.assertEqual(unclear["classification"], "UNCLEAR")
        self.assertIn("GENERIC_GENETIC_LANGUAGE", unclear["ambiguous_modality_signals"])
        self.assertNotIn("WGS", unclear["already_rap_modalities"])
        self.assertEqual(unclear["manual_review_recommended"], "yes")

    def test_build_stage3_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            working_path = root / "timing_working_research_project_universe.csv"
            master_path = root / "stage2_master_projects.csv"
            website_path = root / "ukb_projects_website_listing.csv"
            working_fields = [
                "app_id",
                "schema27_title",
                "schema27_institution",
                "schema27_pi",
                "start_date",
                "website_url",
                "website_match_status",
                "website_match_count",
                "match_methods",
            ]
            master_fields = ["app_id", "title", "pi", "institution", "notes"]
            website_fields = [
                "page",
                "index_on_page",
                "start_date_text",
                "start_date_datetime",
                "title",
                "url",
                "institution",
                "excerpt",
                "counts_text",
            ]
            working_rows = [
                {
                    "app_id": "1",
                    "schema27_title": "Whole genome sequencing of rare disease",
                    "schema27_institution": "A",
                    "schema27_pi": "PI A",
                    "start_date": "2022-01-01",
                    "website_url": "https://example.test/a/",
                    "website_match_status": "matched_one_website_record",
                    "website_match_count": "1",
                    "match_methods": "test",
                },
                {
                    "app_id": "2",
                    "schema27_title": "Retinal OCT imaging study",
                    "schema27_institution": "B",
                    "schema27_pi": "PI B",
                    "start_date": "2024-07-05",
                    "website_url": "https://example.test/b/",
                    "website_match_status": "matched_one_website_record",
                    "website_match_count": "1",
                    "match_methods": "test",
                },
                {
                    "app_id": "3",
                    "schema27_title": "WES and primary care records",
                    "schema27_institution": "C",
                    "schema27_pi": "PI C",
                    "start_date": "2025-01-01",
                    "website_url": "https://example.test/c/",
                    "website_match_status": "matched_one_website_record",
                    "website_match_count": "1",
                    "match_methods": "test",
                },
                {
                    "app_id": "4",
                    "schema27_title": "Broad health risk factors",
                    "schema27_institution": "D",
                    "schema27_pi": "PI D",
                    "start_date": "2020-01-01",
                    "website_url": "https://example.test/d/",
                    "website_match_status": "matched_one_website_record",
                    "website_match_count": "1",
                    "match_methods": "test",
                },
            ]
            master_rows = [
                {
                    "app_id": row["app_id"],
                    "title": row["schema27_title"],
                    "pi": row["schema27_pi"],
                    "institution": row["schema27_institution"],
                    "notes": "",
                }
                for row in working_rows
            ]
            website_rows = [
                {
                    "page": "1",
                    "index_on_page": str(i),
                    "start_date_text": "",
                    "start_date_datetime": row["start_date"] + " 00:00:00",
                    "title": row["schema27_title"],
                    "url": row["website_url"],
                    "institution": row["schema27_institution"],
                    "excerpt": "",
                    "counts_text": "",
                }
                for i, row in enumerate(working_rows, start=1)
            ]
            self._write_csv(working_path, working_rows, working_fields)
            self._write_csv(master_path, master_rows, master_fields)
            self._write_csv(website_path, website_rows, website_fields)

            summary = stage3.build_stage3_outputs(
                working_universe_path=working_path,
                master_path=master_path,
                website_listing_path=website_path,
                output_dir=root,
                expected_working=4,
                source_commit="abc123",
            )

            paths = stage3.output_paths(root)
            self.assertTrue(paths.report.exists())
            self.assertTrue(paths.project_classification.exists())
            self.assertEqual(summary["working_universe_projects"], 4)
            counts = {
                row["classification"]: row["projects"]
                for row in self._read_csv(paths.class_counts)
            }
            self.assertEqual(counts["ALREADY_RAP_BOUND"], "1")
            self.assertEqual(counts["NEWLY_RAP_BOUND"], "1")
            self.assertEqual(counts["MIXED"], "1")
            self.assertEqual(counts["UNCLEAR"], "1")
            periods = {
                row["classification"]: row
                for row in self._read_csv(paths.period_counts)
            }
            self.assertEqual(periods["NEWLY_RAP_BOUND"]["after_policy_projects"], "1")
            self.assertEqual(periods["UNCLEAR"]["before_policy_projects"], "1")

    def test_rejects_non_fixed_working_universe_rows(self):
        with self.assertRaisesRegex(ValueError, "unique website matches"):
            stage3.validate_working_universe(
                [
                    {
                        "app_id": "1",
                        "start_date": "",
                        "website_match_status": "unmatched_schema27",
                    }
                ],
                expected_working=1,
            )


if __name__ == "__main__":
    unittest.main()
