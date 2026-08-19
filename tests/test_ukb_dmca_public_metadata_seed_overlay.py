import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import ukb_dmca_public_metadata_seed_overlay as overlay


class PublicMetadataSeedOverlayTests(unittest.TestCase):
    def test_a1_seed_uses_direct_application_evidence_component(self):
        candidate = overlay._candidate_from_seed(
            {"lineage_id": "lineage_a1", "evidence_urls": ""},
            {
                "app_id": "28784",
                "title": "A statistical framework for personalized nutrition recommendations based on genetic and anthropometric data",
                "pi": "Eran Segal",
                "institution": "Weizmann Institute of Science",
            },
            {
                "repo_or_project": "https://github.com/yochaiedlitz/T2DM_UKB_predictions",
                "evidence_class": "A1_DIRECT_APP_ID",
                "match_grade": "confirmed",
                "candidate_app_id": "28784",
                "doi": "10.7554/elife.71862",
                "pubmed_id": "35731045",
                "publication_title": "Prediction of type 2 diabetes mellitus onset using logistic regression-based scorecards",
                "authors": "Yochai Edlitz; Eran Segal",
                "evidence_urls": "https://elifesciences.org/articles/71862",
                "source_relation": "Article links the exact repository and UKB application number.",
            },
        )

        components = candidate["evidence_components"]
        self.assertIn("A1_DIRECT_APP_ID", components)
        self.assertIn("direct_application_id", components)
        self.assertNotIn("exact_publication_identifier", components)
        self.assertEqual(candidate["deterministic_evidence_present"], "true")

    def test_overlay_promotes_seeded_lineage_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "evidence/logs").mkdir(parents=True)
            (root / "evidence/lineages").mkdir(parents=True)

            apps = root / "data/applications.tsv"
            apps.write_text(
                "app_id\ttitle\tpi\tinstitution\tnotes\n"
                "45761\tGenetics of cancer risk and therapy response\tProfessor Moritz Gerstung\tEBI\t\n",
                encoding="utf-8",
            )
            (root / "data/public_metadata_seeds.tsv").write_text(
                "lineage_id\trepo_or_project\tevidence_class\tmatch_grade\tcandidate_app_id\tdoi\tpubmed_id\tpublication_title\tauthors\tapplication_title\tapplication_pi\tapplication_institution\tevidence_urls\tsource_relation\tnotes\n"
                "lineage_seeded\thttps://github.com/gerstung-lab/CancerRisk\tA4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN\tconfirmed\t45761\t10.1016/s2589-7500(24)00062-1\t38789140\tMulti-cancer risk stratification based on national health data: a retrospective modelling and validation study\tMoritz Gerstung\tGenetics of cancer risk and therapy response\tProfessor Moritz Gerstung\tEBI\thttps://www.medrxiv.org/content/10.1101/2022.10.12.22280908v1\tExact public repo-publication-application chain\tSeed test\n",
                encoding="utf-8",
            )

            match_fields = [
                "notice_id", "notice_date", "notice_path", "repo_url", "repo_owner", "repo_name", "lineage_id",
                "paper_title", "doi", "pubmed_id", "paper_authors", "repo_linked_doi", "repo_linked_pmid",
                "repo_linked_publication_title", "crosswalk_pub_ids", "crosswalk_app_ids",
                "crosswalk_application_count", "crosswalk_identifier_type", "crosswalk_evidence",
                "candidate_app_id", "application_title", "application_pi", "application_institution",
                "application_linked_to_dmca_targeted_repository_lineage", "match_grade", "match_score",
                "evidence_class", "evidence_components", "deterministic_evidence_present",
                "identity_evidence_present", "contextual_evidence_present", "match_reason", "evidence_urls",
                "manual_review_needed",
            ]
            candidate_fields = [
                "lineage_id", "candidate_rank", "candidate_app_id", "application_title", "application_pi",
                "application_institution", "match_grade", "match_score", "evidence_level", "evidence_class",
                "evidence_components", "score_details", "deterministic_evidence_present",
                "identity_evidence_present", "contextual_evidence_present", "crosswalk_pub_ids",
                "crosswalk_app_ids", "crosswalk_application_count", "crosswalk_identifier_type",
                "crosswalk_evidence", "match_reason", "evidence_urls", "manual_review_needed",
            ]
            evidence_fields = [
                "lineage_id", "candidate_app_id", "evidence_class", "evidence_type", "evidence_value",
                "evidence_source", "evidence_url", "deterministic_or_fuzzy", "strength_level",
            ]

            self._write_csv(root / "ukb_dmca_lineages.csv", [
                "lineage_id", "source_repo", "repo_urls", "doi", "pubmed_id", "paper_title", "paper_authors",
                "repo_linked_doi", "repo_linked_pmid", "repo_linked_publication_title", "crosswalk_pub_ids",
                "crosswalk_app_ids", "crosswalk_application_count", "crosswalk_identifier_type",
                "crosswalk_evidence", "evidence_urls", "evidence_file",
            ], [{
                "lineage_id": "lineage_seeded",
                "source_repo": "gerstung-lab/CancerRisk",
                "repo_urls": "https://github.com/gerstung-lab/CancerRisk",
                "evidence_file": "evidence/lineages/lineage_seeded.md",
            }])
            self._write_csv(root / "ukb_dmca_repositories.csv", match_fields[:7] + match_fields[7:19] + ["evidence_urls"], [{
                "notice_id": "n1",
                "notice_date": "2025-11-25",
                "notice_path": "2025/11/foo.md",
                "repo_url": "https://github.com/gerstung-lab/CancerRisk",
                "repo_owner": "gerstung-lab",
                "repo_name": "CancerRisk",
                "lineage_id": "lineage_seeded",
            }])
            self._write_csv(root / "ukb_dmca_application_candidates.csv", candidate_fields, [{
                "lineage_id": "lineage_seeded",
                "match_grade": "unresolved",
                "match_score": "0",
                "manual_review_needed": "true",
            }])
            self._write_csv(root / "ukb_dmca_application_matches.csv", match_fields, [])
            self._write_csv(root / "ukb_dmca_unresolved.csv", match_fields, [{
                "lineage_id": "lineage_seeded",
                "match_grade": "unresolved",
                "manual_review_needed": "true",
            }])
            self._write_csv(root / "ukb_dmca_manual_review.csv", match_fields, [{
                "lineage_id": "lineage_seeded",
                "match_grade": "unresolved",
                "manual_review_needed": "true",
            }])
            self._write_csv(root / "ukb_dmca_application_match_evidence.csv", evidence_fields, [])
            (root / "evidence/logs/result_summary.json").write_text(
                '{"cases_needing_extra_data": ["lineage_seeded"], "match_grade_counts": {"unresolved": 1}}',
                encoding="utf-8",
            )
            (root / "evidence/lineages/lineage_seeded.md").write_text("# lineage_seeded\n", encoding="utf-8")

            summary = overlay.apply_public_metadata_seeds(root, apps)

            matches = self._read_csv(root / "ukb_dmca_application_matches.csv")
            unresolved = self._read_csv(root / "ukb_dmca_unresolved.csv")
            candidates = self._read_csv(root / "ukb_dmca_application_candidates.csv")
            evidence = self._read_csv(root / "ukb_dmca_application_match_evidence.csv")
            lineages = self._read_csv(root / "ukb_dmca_lineages.csv")

            self.assertEqual(matches[0]["candidate_app_id"], "45761")
            self.assertEqual(matches[0]["match_grade"], "confirmed")
            self.assertEqual(matches[0]["application_linked_to_dmca_targeted_repository_lineage"], "true")
            self.assertEqual(unresolved, [])
            self.assertEqual(candidates[0]["candidate_rank"], "1")
            self.assertEqual(candidates[0]["manual_review_needed"], "false")
            self.assertEqual(lineages[0]["repo_linked_doi"], "10.1016/s2589-7500(24)00062-1")
            self.assertTrue(any(row["evidence_type"] == "public_metadata_seed" for row in evidence))
            self.assertTrue(any(row["evidence_type"] == "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN" for row in evidence))
            self.assertEqual(summary["match_grade_counts"]["confirmed"], 1)
            self.assertEqual(summary["public_metadata_seed_matched_lineages"], 1)
            self.assertEqual(summary["cases_needing_extra_data"], [])
            self.assertEqual(summary["lineages_with_doi"], 1)
            self.assertEqual(summary["lineages_with_pmid"], 1)
            self.assertIn("Public Metadata Seed Audit", (root / "evidence/lineages/lineage_seeded.md").read_text(encoding="utf-8"))

            persisted_summary = json.loads((root / "evidence/logs/result_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted_summary["unique_application_count"], 1)

    def test_overlay_derives_probable_project_family_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "evidence/logs").mkdir(parents=True)
            (root / "evidence/lineages").mkdir(parents=True)

            apps = root / "data/applications.tsv"
            apps.write_text(
                "app_id\ttitle\tpi\tinstitution\tnotes\n"
                "66995\tPrediction of haplotypes, genotypes, parental-of-origin and applications in biobanks.\t\tUniversity of Lausanne\t\n",
                encoding="utf-8",
            )
            (root / "data/public_metadata_seeds.tsv").write_text(
                "lineage_id\trepo_or_project\tevidence_class\tmatch_grade\tcandidate_app_id\tdoi\tpubmed_id\tpublication_title\tauthors\tapplication_title\tapplication_pi\tapplication_institution\tevidence_urls\tsource_relation\tnotes\n"
                "lineage_odelaneau_shapeit5\thttps://github.com/odelaneau/shapeit5\tA4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN\tconfirmed\t66995\t10.1038/s41588-023-01415-w\t37386248\tAccurate rare variant phasing of whole-genome and whole-exome sequencing data in the UK Biobank\tOlivier Delaneau\tPrediction of haplotypes, genotypes, parental-of-origin and applications in biobanks.\t\tUniversity of Lausanne\thttps://www.nature.com/articles/s41588-023-01415-w\tExact public repo-publication-application chain\tAnchor\n",
                encoding="utf-8",
            )

            match_fields = [
                "notice_id", "notice_date", "notice_path", "repo_url", "repo_owner", "repo_name", "lineage_id",
                "paper_title", "doi", "pubmed_id", "paper_authors", "repo_linked_doi", "repo_linked_pmid",
                "repo_linked_publication_title", "crosswalk_pub_ids", "crosswalk_app_ids",
                "crosswalk_application_count", "crosswalk_identifier_type", "crosswalk_evidence",
                "candidate_app_id", "application_title", "application_pi", "application_institution",
                "application_linked_to_dmca_targeted_repository_lineage", "match_grade", "match_score",
                "evidence_class", "evidence_components", "deterministic_evidence_present",
                "identity_evidence_present", "contextual_evidence_present", "match_reason", "evidence_urls",
                "manual_review_needed",
            ]
            candidate_fields = [
                "lineage_id", "candidate_rank", "candidate_app_id", "application_title", "application_pi",
                "application_institution", "match_grade", "match_score", "evidence_level", "evidence_class",
                "evidence_components", "score_details", "deterministic_evidence_present",
                "identity_evidence_present", "contextual_evidence_present", "crosswalk_pub_ids",
                "crosswalk_app_ids", "crosswalk_application_count", "crosswalk_identifier_type",
                "crosswalk_evidence", "match_reason", "evidence_urls", "manual_review_needed",
            ]
            evidence_fields = [
                "lineage_id", "candidate_app_id", "evidence_class", "evidence_type", "evidence_value",
                "evidence_source", "evidence_url", "deterministic_or_fuzzy", "strength_level",
            ]

            self._write_csv(root / "ukb_dmca_lineages.csv", [
                "lineage_id", "source_repo", "repo_urls", "doi", "pubmed_id", "paper_title", "paper_authors",
                "repo_linked_doi", "repo_linked_pmid", "repo_linked_publication_title", "crosswalk_pub_ids",
                "crosswalk_app_ids", "crosswalk_application_count", "crosswalk_identifier_type",
                "crosswalk_evidence", "evidence_urls", "evidence_file",
            ], [
                {
                    "lineage_id": "lineage_odelaneau_shapeit5",
                    "source_repo": "odelaneau/shapeit5",
                    "repo_urls": "https://github.com/odelaneau/shapeit5",
                    "evidence_file": "evidence/lineages/lineage_odelaneau_shapeit5.md",
                },
                {
                    "lineage_id": "lineage_toseph_shapeit5",
                    "source_repo": "Toseph/shapeit5",
                    "repo_urls": "https://github.com/Toseph/shapeit5",
                    "evidence_file": "evidence/lineages/lineage_toseph_shapeit5.md",
                },
            ])
            self._write_csv(root / "ukb_dmca_repositories.csv", match_fields[:7] + match_fields[7:19] + ["evidence_urls"], [
                {
                    "notice_id": "n1",
                    "notice_date": "2025-11-13",
                    "notice_path": "2025/11/foo.md",
                    "repo_url": "https://github.com/odelaneau/shapeit5",
                    "repo_owner": "odelaneau",
                    "repo_name": "shapeit5",
                    "lineage_id": "lineage_odelaneau_shapeit5",
                },
                {
                    "notice_id": "n1",
                    "notice_date": "2025-11-13",
                    "notice_path": "2025/11/foo.md",
                    "repo_url": "https://github.com/Toseph/shapeit5",
                    "repo_owner": "Toseph",
                    "repo_name": "shapeit5",
                    "lineage_id": "lineage_toseph_shapeit5",
                },
            ])
            self._write_csv(root / "ukb_dmca_application_candidates.csv", candidate_fields, [])
            self._write_csv(root / "ukb_dmca_application_matches.csv", match_fields, [])
            self._write_csv(root / "ukb_dmca_unresolved.csv", match_fields, [
                {"lineage_id": "lineage_odelaneau_shapeit5", "match_grade": "unresolved", "manual_review_needed": "true"},
                {"lineage_id": "lineage_toseph_shapeit5", "match_grade": "unresolved", "manual_review_needed": "true"},
            ])
            self._write_csv(root / "ukb_dmca_manual_review.csv", match_fields, [
                {"lineage_id": "lineage_odelaneau_shapeit5", "match_grade": "unresolved", "manual_review_needed": "true"},
                {"lineage_id": "lineage_toseph_shapeit5", "match_grade": "unresolved", "manual_review_needed": "true"},
            ])
            self._write_csv(root / "ukb_dmca_application_match_evidence.csv", evidence_fields, [])
            (root / "evidence/logs/result_summary.json").write_text(
                '{"cases_needing_extra_data": ["lineage_odelaneau_shapeit5", "lineage_toseph_shapeit5"]}',
                encoding="utf-8",
            )
            (root / "evidence/lineages/lineage_odelaneau_shapeit5.md").write_text("# odelaneau\n", encoding="utf-8")
            (root / "evidence/lineages/lineage_toseph_shapeit5.md").write_text("# toseph\n", encoding="utf-8")

            summary = overlay.apply_public_metadata_seeds(root, apps)

            matches = self._read_csv(root / "ukb_dmca_application_matches.csv")
            evidence = self._read_csv(root / "ukb_dmca_application_match_evidence.csv")
            by_lineage = {row["lineage_id"]: row for row in matches}

            self.assertEqual(by_lineage["lineage_odelaneau_shapeit5"]["match_grade"], "confirmed")
            self.assertEqual(by_lineage["lineage_toseph_shapeit5"]["match_grade"], "probable")
            self.assertIn("B2_PROJECT_FAMILY_NAME_PROPAGATION", by_lineage["lineage_toseph_shapeit5"]["evidence_class"])
            self.assertTrue(any(row["evidence_type"] == "B2_PROJECT_FAMILY_NAME_PROPAGATION" for row in evidence))
            self.assertEqual(summary["project_family_seed_rows"], 1)
            self.assertEqual(summary["project_family_seed_matched_lineages"], 1)

    def test_overlay_derives_probable_content_fingerprint_from_existing_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "evidence/logs").mkdir(parents=True)
            (root / "evidence/lineages").mkdir(parents=True)

            apps = root / "data/applications.tsv"
            apps.write_text(
                "app_id\ttitle\tpi\tinstitution\tnotes\n"
                "66995\tPrediction of haplotypes, genotypes, parental-of-origin and applications in biobanks.\t\tUniversity of Lausanne\t\n",
                encoding="utf-8",
            )
            match_fields = [
                "notice_id", "notice_date", "notice_path", "repo_url", "repo_owner", "repo_name", "lineage_id",
                "paper_title", "doi", "pubmed_id", "paper_authors", "repo_linked_doi", "repo_linked_pmid",
                "repo_linked_publication_title", "crosswalk_pub_ids", "crosswalk_app_ids",
                "crosswalk_application_count", "crosswalk_identifier_type", "crosswalk_evidence",
                "candidate_app_id", "application_title", "application_pi", "application_institution",
                "application_linked_to_dmca_targeted_repository_lineage", "match_grade", "match_score",
                "evidence_class", "evidence_components", "deterministic_evidence_present",
                "identity_evidence_present", "contextual_evidence_present", "match_reason", "evidence_urls",
                "manual_review_needed",
            ]
            candidate_fields = [
                "lineage_id", "candidate_rank", "candidate_app_id", "application_title", "application_pi",
                "application_institution", "match_grade", "match_score", "evidence_level", "evidence_class",
                "evidence_components", "score_details", "deterministic_evidence_present",
                "identity_evidence_present", "contextual_evidence_present", "crosswalk_pub_ids",
                "crosswalk_app_ids", "crosswalk_application_count", "crosswalk_identifier_type",
                "crosswalk_evidence", "match_reason", "evidence_urls", "manual_review_needed",
            ]
            evidence_fields = [
                "lineage_id", "candidate_app_id", "evidence_class", "evidence_type", "evidence_value",
                "evidence_source", "evidence_url", "deterministic_or_fuzzy", "strength_level",
            ]
            fingerprint_url = (
                "https://github.com/JosephLalli/shapeit5/blob/"
                "0b40edb8ef2678fd4ef0f0286dffe9ef0ba9b254/tasks/phasingUKB/data/1k_samples_wbi.txt"
            )
            clone_url = fingerprint_url.replace("JosephLalli/shapeit5", "example/reupload")

            self._write_csv(root / "ukb_dmca_lineages.csv", [
                "lineage_id", "source_repo", "repo_urls", "doi", "pubmed_id", "paper_title", "paper_authors",
                "repo_linked_doi", "repo_linked_pmid", "repo_linked_publication_title", "crosswalk_pub_ids",
                "crosswalk_app_ids", "crosswalk_application_count", "crosswalk_identifier_type",
                "crosswalk_evidence", "evidence_urls", "evidence_file",
            ], [
                {
                    "lineage_id": "lineage_josephlalli_shapeit5",
                    "source_repo": "JosephLalli/shapeit5",
                    "repo_urls": "https://github.com/JosephLalli/shapeit5",
                    "evidence_urls": fingerprint_url,
                    "evidence_file": "evidence/lineages/lineage_josephlalli_shapeit5.md",
                },
                {
                    "lineage_id": "lineage_example_reupload",
                    "source_repo": "example/reupload",
                    "repo_urls": "https://github.com/example/reupload",
                    "evidence_urls": clone_url,
                    "evidence_file": "evidence/lineages/lineage_example_reupload.md",
                },
            ])
            self._write_csv(root / "ukb_dmca_repositories.csv", match_fields[:7] + match_fields[7:19] + ["evidence_urls"], [
                {
                    "notice_id": "n1",
                    "notice_date": "2025-11-13",
                    "notice_path": "2025/11/foo.md",
                    "repo_url": "https://github.com/JosephLalli/shapeit5",
                    "repo_owner": "JosephLalli",
                    "repo_name": "shapeit5",
                    "lineage_id": "lineage_josephlalli_shapeit5",
                    "evidence_urls": fingerprint_url,
                },
                {
                    "notice_id": "n1",
                    "notice_date": "2025-11-13",
                    "notice_path": "2025/11/foo.md",
                    "repo_url": "https://github.com/example/reupload",
                    "repo_owner": "example",
                    "repo_name": "reupload",
                    "lineage_id": "lineage_example_reupload",
                    "evidence_urls": clone_url,
                },
            ])
            anchor_match = {
                "lineage_id": "lineage_josephlalli_shapeit5",
                "repo_url": "https://github.com/JosephLalli/shapeit5",
                "repo_owner": "JosephLalli",
                "repo_name": "shapeit5",
                "candidate_app_id": "66995",
                "application_title": "Prediction of haplotypes, genotypes, parental-of-origin and applications in biobanks.",
                "application_institution": "University of Lausanne",
                "application_linked_to_dmca_targeted_repository_lineage": "true",
                "match_grade": "confirmed",
                "match_score": "100",
                "evidence_class": "A2_DOI_UKB_CROSSWALK",
                "evidence_components": "A2_DOI_UKB_CROSSWALK; exact_publication_identifier",
                "repo_linked_doi": "10.1038/s41588-023-01415-w",
                "repo_linked_publication_title": "Accurate rare variant phasing of whole-genome and whole-exome sequencing data in the UK Biobank",
                "evidence_urls": fingerprint_url,
                "manual_review_needed": "false",
            }
            self._write_csv(root / "ukb_dmca_application_candidates.csv", candidate_fields, [])
            self._write_csv(root / "ukb_dmca_application_matches.csv", match_fields, [anchor_match])
            self._write_csv(root / "ukb_dmca_unresolved.csv", match_fields, [
                {"lineage_id": "lineage_example_reupload", "match_grade": "unresolved", "manual_review_needed": "true"},
            ])
            self._write_csv(root / "ukb_dmca_manual_review.csv", match_fields, [
                anchor_match,
                {"lineage_id": "lineage_example_reupload", "match_grade": "unresolved", "manual_review_needed": "true"},
            ])
            self._write_csv(root / "ukb_dmca_application_match_evidence.csv", evidence_fields, [])
            (root / "evidence/logs/result_summary.json").write_text(
                '{"cases_needing_extra_data": ["lineage_example_reupload"]}',
                encoding="utf-8",
            )
            (root / "evidence/lineages/lineage_josephlalli_shapeit5.md").write_text("# anchor\n", encoding="utf-8")
            (root / "evidence/lineages/lineage_example_reupload.md").write_text("# target\n", encoding="utf-8")

            summary = overlay.apply_public_metadata_seeds(root, apps)

            matches = self._read_csv(root / "ukb_dmca_application_matches.csv")
            evidence = self._read_csv(root / "ukb_dmca_application_match_evidence.csv")
            by_lineage = {row["lineage_id"]: row for row in matches}

            self.assertEqual(by_lineage["lineage_example_reupload"]["match_grade"], "probable")
            self.assertIn("B3_EXACT_TARGET_CONTENT_FINGERPRINT_PROPAGATION", by_lineage["lineage_example_reupload"]["evidence_class"])
            self.assertTrue(any(row["evidence_type"] == "B3_EXACT_TARGET_CONTENT_FINGERPRINT_PROPAGATION" for row in evidence))
            self.assertEqual(summary["content_fingerprint_seed_rows"], 1)
            self.assertEqual(summary["content_fingerprint_seed_matched_lineages"], 1)

    @staticmethod
    def _write_csv(path, fields, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fields)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _read_csv(path):
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
