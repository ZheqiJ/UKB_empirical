import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import ukb_dmca_enriched_appid_runner as runner


class EnrichedAppIdRunnerTests(unittest.TestCase):
    def test_normalize_doi_and_pmid(self):
        self.assertEqual(runner.normalize_doi("https://doi.org/10.1234/ABC."), "10.1234/abc")
        self.assertEqual(runner.normalize_pmid("PMID: 12345678"), "12345678")

    def test_identifiers_extract_public_pubmed_urls(self):
        ids = runner.identifiers(
            "Cited at https://pubmed.ncbi.nlm.nih.gov/33568818/ and "
            "https://europepmc.org/article/MED/12345678"
        )

        self.assertEqual(ids["pubmed_id"], ["33568818", "12345678"])

    def test_identifiers_extract_deterministic_nature_article_doi(self):
        ids = runner.identifiers("Paper page: https://www.nature.com/articles/s41588-023-01415-w")

        self.assertEqual(ids["doi"], ["10.1038/s41588-023-01415-w"])

    def test_identifiers_do_not_guess_ambiguous_nature_article_doi(self):
        ids = runner.identifiers("Older article URL: https://www.nature.com/articles/ng2012190")

        self.assertEqual(ids["doi"], [])

    def test_schema_crosswalk_doi_to_single_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema19 = root / "schema19.tsv"
            schema24 = root / "schema24.tsv"
            schema19.write_text("publication_id\tdoi\ttitle\tauthors\nP100\t10.1234/example\tPaper\tA Smith\n", encoding="utf-8")
            schema24.write_text("publication_id\tapp_id\nP100\t1001\n", encoding="utf-8")

            crosswalk = runner.load_schema_crosswalk(str(schema19), str(schema24))
            hits = runner._crosswalk_hits({"doi": "10.1234/example", "pubmed_id": ""}, crosswalk)

            self.assertEqual(hits["pub_ids"], ["100"])
            self.assertEqual(hits["app_ids"], ["1001"])
            self.assertEqual(hits["evidence_classes"], ["A2_DOI_UKB_CROSSWALK"])

    def test_schema_crosswalk_reads_zipped_txt_uploads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema19 = root / "schema19.txt.zip"
            schema24 = root / "schema24.txt.zip"
            with zipfile.ZipFile(schema19, "w") as archive:
                archive.writestr("schema19.txt", "publication_id\tdoi\ttitle\tauthors\nP200\t10.5555/zipped\tZip paper\tA Lee\n")
            with zipfile.ZipFile(schema24, "w") as archive:
                archive.writestr("schema24.txt", "publication_id\tapp_id\nP200\t2002\n")

            crosswalk = runner.load_schema_crosswalk(str(schema19), str(schema24))
            hits = runner._crosswalk_hits({"doi": "10.5555/zipped", "pubmed_id": ""}, crosswalk)

            self.assertTrue(crosswalk["loaded"])
            self.assertEqual(hits["pub_ids"], ["200"])
            self.assertEqual(hits["app_ids"], ["2002"])

    def test_schema_crosswalk_exact_publication_title_to_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema19 = root / "schema19.tsv"
            schema24 = root / "schema24.tsv"
            title = "Population Modeling and Mental Health Prediction Replication Paper Code"
            schema19.write_text(f"publication_id\tdoi\ttitle\tauthors\nP300\t\t{title}\tA Lee\n", encoding="utf-8")
            schema24.write_text("publication_id\tapp_id\nP300\t3003\n", encoding="utf-8")

            crosswalk = runner.load_schema_crosswalk(str(schema19), str(schema24))
            hits = runner._crosswalk_hits({"paper_title": f"Repo for paper: {title}. Extra README text."}, crosswalk)

            self.assertEqual(hits["pub_ids"], ["300"])
            self.assertEqual(hits["app_ids"], ["3003"])
            self.assertEqual(hits["evidence_classes"], ["A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN"])

    def test_short_publication_title_is_not_crosswalked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema19 = root / "schema19.tsv"
            schema24 = root / "schema24.tsv"
            schema19.write_text("publication_id\tdoi\ttitle\tauthors\nP400\t\tUKB GWAS\tA Lee\n", encoding="utf-8")
            schema24.write_text("publication_id\tapp_id\nP400\t4004\n", encoding="utf-8")

            crosswalk = runner.load_schema_crosswalk(str(schema19), str(schema24))
            hits = runner._crosswalk_hits({"paper_title": "This repository performs UKB GWAS analysis."}, crosswalk)

            self.assertEqual(hits["app_ids"], [])

    def test_lineage_evidence_text_adds_repo_linked_doi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evidence/lineages").mkdir(parents=True)
            evidence = root / "evidence/lineages/lineage-1.md"
            evidence.write_text("README cites DOI https://doi.org/10.7777/evidence.", encoding="utf-8")
            lineage = {"evidence_file": "evidence/lineages/lineage-1.md", "doi": "", "pubmed_id": ""}

            runner._enrich_lineage_from_evidence(root, lineage)

            self.assertEqual(lineage["repo_linked_doi"], "10.7777/evidence")

    def test_lineage_evidence_urls_add_publication_url_doi_without_evidence_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            lineage = {
                "evidence_file": "evidence/lineages/missing.md",
                "doi": "",
                "pubmed_id": "",
                "evidence_urls": "https://www.nature.com/articles/s41588-023-01415-w",
            }

            runner._enrich_lineage_from_evidence(Path(tmp), lineage)

            self.assertEqual(lineage["repo_linked_doi"], "10.1038/s41588-023-01415-w")

    def test_postprocess_confirms_unique_crosswalk_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evidence/logs").mkdir(parents=True)
            (root / "evidence/lineages").mkdir(parents=True)

            apps = root / "applications.tsv"
            apps.write_text("app_id\ttitle\tpi\tinstitution\tnotes\n1001\tHeart paper\tA Smith\tOxford\tLinked DOI 10.1234/example\n", encoding="utf-8")
            schema19 = root / "schema19.tsv"
            schema24 = root / "schema24.tsv"
            schema19.write_text("publication_id\tdoi\ttitle\tauthors\nP100\t10.1234/example\tHeart paper\tA Smith\n", encoding="utf-8")
            schema24.write_text("publication_id\tapp_id\nP100\t1001\n", encoding="utf-8")

            self._write_csv(root / "ukb_dmca_lineages.csv", ["lineage_id", "source_repo", "repo_urls", "doi", "pubmed_id", "evidence_urls", "evidence_file"], [
                {"lineage_id": "lineage-1", "source_repo": "alice/repo", "repo_urls": "https://github.com/alice/repo", "doi": "10.1234/example", "pubmed_id": "", "evidence_urls": "https://doi.org/10.1234/example", "evidence_file": "evidence/lineages/lineage-1.md"}
            ])
            self._write_csv(root / "ukb_dmca_repositories.csv", ["notice_id", "notice_date", "notice_path", "repo_url", "repo_owner", "repo_name", "lineage_id"], [
                {"notice_id": "n1", "notice_date": "2020-01-01", "notice_path": "2020/01/foo.md", "repo_url": "https://github.com/alice/repo", "repo_owner": "alice", "repo_name": "repo", "lineage_id": "lineage-1"}
            ])
            self._write_csv(root / "ukb_dmca_application_candidates.csv", ["lineage_id", "candidate_app_id", "match_score", "match_grade"], [])
            (root / "evidence/logs/result_summary.json").write_text("{}", encoding="utf-8")
            (root / "evidence/lineages/lineage-1.md").write_text("# lineage-1\n", encoding="utf-8")

            runner.postprocess_outputs([
                "--output-dir", str(root),
                "--applications", str(apps),
                "--schema19", str(schema19),
                "--schema24", str(schema24),
            ])

            with (root / "ukb_dmca_application_matches.csv").open() as handle:
                matches = list(csv.DictReader(handle))
            with (root / "ukb_dmca_application_match_evidence.csv").open() as handle:
                evidence = list(csv.DictReader(handle))
            self.assertEqual(matches[0]["candidate_app_id"], "1001")
            self.assertEqual(matches[0]["match_grade"], "confirmed")
            self.assertTrue(any(row["evidence_type"] == "A2_DOI_UKB_CROSSWALK" for row in evidence))

    def test_postprocess_confirms_public_metadata_seed_application_without_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir(parents=True)
            (root / "evidence/logs").mkdir(parents=True)
            (root / "evidence/lineages").mkdir(parents=True)

            apps = root / "applications.tsv"
            apps.write_text(
                "app_id\ttitle\tpi\tinstitution\tnotes\n"
                "45761\tGenetics of cancer risk and therapy response\tProfessor Moritz Gerstung\tEBI\t\n",
                encoding="utf-8",
            )
            seed = root / "data/public_metadata_seeds.tsv"
            seed.write_text(
                "lineage_id\trepo_or_project\tevidence_class\tmatch_grade\tcandidate_app_id\tdoi\tpubmed_id\tpublication_title\tauthors\tapplication_title\tapplication_pi\tapplication_institution\tevidence_urls\tsource_relation\tnotes\n"
                "lineage_seeded\thttps://github.com/gerstung-lab/CancerRisk\tA4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN\tconfirmed\t45761\t10.1016/s2589-7500(24)00062-1\t38789140\tMulti-cancer risk stratification based on national health data: a retrospective modelling and validation study\tMoritz Gerstung\tGenetics of cancer risk and therapy response\tProfessor Moritz Gerstung\tEBI\thttps://www.medrxiv.org/content/10.1101/2022.10.12.22280908v1\tExact public repo-publication-application chain\tSeed test\n",
                encoding="utf-8",
            )

            self._write_csv(root / "ukb_dmca_lineages.csv", ["lineage_id", "source_repo", "repo_urls", "doi", "pubmed_id", "evidence_urls", "evidence_file"], [
                {"lineage_id": "lineage_seeded", "source_repo": "gerstung-lab/CancerRisk", "repo_urls": "https://github.com/gerstung-lab/CancerRisk", "doi": "", "pubmed_id": "", "evidence_urls": "", "evidence_file": "evidence/lineages/lineage_seeded.md"}
            ])
            self._write_csv(root / "ukb_dmca_repositories.csv", ["notice_id", "notice_date", "notice_path", "repo_url", "repo_owner", "repo_name", "lineage_id"], [
                {"notice_id": "n1", "notice_date": "2025-11-25", "notice_path": "2025/11/foo.md", "repo_url": "https://github.com/gerstung-lab/CancerRisk", "repo_owner": "gerstung-lab", "repo_name": "CancerRisk", "lineage_id": "lineage_seeded"}
            ])
            self._write_csv(root / "ukb_dmca_application_candidates.csv", ["lineage_id", "candidate_app_id", "match_score", "match_grade"], [])
            (root / "evidence/logs/result_summary.json").write_text("{}", encoding="utf-8")
            (root / "evidence/lineages/lineage_seeded.md").write_text("# lineage_seeded\n", encoding="utf-8")

            runner.postprocess_outputs(["--output-dir", str(root), "--applications", str(apps)])

            with (root / "ukb_dmca_application_matches.csv").open() as handle:
                matches = list(csv.DictReader(handle))
            with (root / "ukb_dmca_application_candidates.csv").open() as handle:
                candidates = list(csv.DictReader(handle))
            with (root / "ukb_dmca_application_match_evidence.csv").open() as handle:
                evidence = list(csv.DictReader(handle))

            self.assertEqual(matches[0]["candidate_app_id"], "45761")
            self.assertEqual(matches[0]["match_grade"], "confirmed")
            self.assertEqual(matches[0]["application_linked_to_dmca_targeted_repository_lineage"], "true")
            self.assertTrue(any(row["evidence_type"] == "public_metadata_seed" for row in evidence))
            self.assertTrue(any(row["evidence_type"] == "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN" for row in evidence))
            self.assertTrue(all(row["evidence_source"] == "public_metadata_seed" for row in evidence if row["lineage_id"] == "lineage_seeded"))
            self.assertEqual(candidates[0]["manual_review_needed"], "false")

    @staticmethod
    def _write_csv(path, fields, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fields)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
