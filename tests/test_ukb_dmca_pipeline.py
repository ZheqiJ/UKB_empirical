import tempfile
import unittest
from pathlib import Path

from scripts.ukb_dmca_pipeline import (
    candidate_tables,
    extract_github_targets,
    make_lineages,
    matched_notice_terms,
    normalize_target,
    notice_matches,
    parse_applications_tsv,
    parse_notice_date,
    repo_enrich,
)
from scripts import ukb_dmca_enriched_pipeline as enriched


class PipelineParserTests(unittest.TestCase):
    def test_multiline_application_parser(self):
        text = (
            "app_id\ttitle\tpi\tinstitution\tnotes\n"
            "123\tHeart imaging\tDr Ada Smith\tExample University\tFirst line\n"
            "continued notes\n"
            "456\tGenetics\tProf Ben Jones\tExample Institute\tSingle line\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "apps.tsv"
            path.write_text(text, encoding="utf-8")
            rows = parse_applications_tsv(path)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["app_id"], "123")
        self.assertIn("continued notes", rows[0]["notes"])
        self.assertEqual(rows[1]["pi"], "Prof Ben Jones")

    def test_parse_notice_date_with_suffix(self):
        self.assertEqual(
            parse_notice_date("2025/11/2025-11-13-uk-biobank-5.md"),
            "2025-11-13",
        )

    def test_notice_match_requires_ukb_signal_in_notice_text(self):
        text = "# UK Biobank\nReported content includes a UKB phenotype file."

        self.assertTrue(notice_matches("2025/11/2025-11-13-uk-biobank.md", text))
        self.assertIn("UK Biobank", matched_notice_terms(text))
        self.assertIn("UKB", matched_notice_terms(text))

    def test_notice_match_rejects_unrelated_notice(self):
        text = "# JetBrains\nReported content includes cracked software keys."

        self.assertFalse(notice_matches("2015/2015-07-06-jetbrains.md", text))
        self.assertEqual(matched_notice_terms(text), "")

    def test_notice_match_does_not_match_ukb_inside_longer_token(self):
        text = "# Unrelated\nThis text mentions a token like aukbzz but not the acronym."

        self.assertFalse(notice_matches("2025/05/2025-05-29-packt.md", text))
        self.assertEqual(matched_notice_terms(text), "")

    def test_extract_file_target_from_blob_url(self):
        text = (
            "Reported content: "
            "https://github.com/example/repo/blob/main/data/ukb_fields.csv"
        )
        targets = extract_github_targets(text)

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["repo_owner"], "example")
        self.assertEqual(targets[0]["repo_name"], "repo")
        self.assertEqual(targets[0]["offending_file_path"], "data/ukb_fields.csv")
        self.assertEqual(targets[0]["target_scope"], "single_file")
        self.assertEqual(targets[0]["target_ref"], "main")
        self.assertEqual(targets[0]["target_commit_sha"], "")

    def test_exact_commit_sha_extraction_from_blob_url(self):
        sha = "0123456789abcdef0123456789abcdef01234567"
        target = normalize_target(f"https://github.com/example/repo/blob/{sha}/data/ukb_fields.csv")

        self.assertIsNotNone(target)
        self.assertEqual(target["target_ref"], sha)
        self.assertEqual(target["target_commit_sha"], sha)
        self.assertEqual(target["offending_file_name"], "ukb_fields.csv")

    def test_branch_ref_is_not_commit_sha(self):
        for ref in ("main", "master", "feature-0123456789abcdef"):
            target = normalize_target(f"https://github.com/example/repo/blob/{ref}/data/ukb_fields.csv")
            self.assertEqual(target["target_ref"], ref)
            self.assertEqual(target["target_commit_sha"], "")

    def test_direct_application_id_extraction_forms(self):
        ids = enriched.identifiers(
            "UK Biobank application 12345; project number 23456; app #34567; app45678"
        )

        self.assertEqual(ids["app_id"], ["12345", "23456", "34567", "45678"])

    def test_doi_and_pmid_normalization(self):
        self.assertEqual(enriched.normalize_doi("https://doi.org/10.1234/ABC."), "10.1234/abc")
        self.assertEqual(enriched.normalize_doi("doi:10.5555/Thing)"), "10.5555/thing")
        self.assertEqual(enriched.normalize_pmid("PMID: 12345678"), "12345678")

    def test_repo_enrich_handles_null_github_description(self):
        class FakeClient:
            def fetch(self, url):
                if url.endswith("/readme"):
                    return {"status": 404, "body": ""}
                return {
                    "status": 200,
                    "body": (
                        '{"id": 1, "description": null, "fork": false, '
                        '"created_at": "2020-01-01T00:00:00Z", '
                        '"pushed_at": "2020-01-02T00:00:00Z"}'
                    ),
                }

        rows = repo_enrich(
            FakeClient(),
            [
                {
                    "repo_url": "https://github.com/example/repo",
                    "repo_owner": "example",
                    "repo_name": "repo",
                    "offending_file_path": "data/ukb.csv",
                    "offending_file_name": "ukb.csv",
                    "target_scope": "single_file",
                    "alleged_data_type": "phenotype",
                    "direct_app_ids": "",
                    "notice_id": "n1",
                    "notice_date": "2024-01-01",
                    "notice_path": "2024/01/notice.md",
                }
            ],
            wayback_limit=0,
        )

        self.assertEqual(rows[0]["repo_status"], "live")
        self.assertIn("https://github.com/example/repo", rows[0]["_text"])

    def test_readme_application_id_confirms_candidate(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if url.endswith("/readme"):
                    return {
                        "status": 200,
                        "body": (
                            '{"encoding": "base64", '
                            '"content": "VGhpcyByZXBvIHVzZXMgVUsgQmlvYmFuayBhcHBsaWNhdGlvbiAxMjMu", '
                            '"html_url": "https://github.com/example/repo/blob/main/README.md"}'
                        ),
                    }
                return {
                    "status": 200,
                    "body": (
                        '{"id": 1, "description": "Heart imaging model", '
                        '"fork": false, "created_at": "2020-01-01T00:00:00Z"}'
                    ),
                }

        repos = repo_enrich(
            FakeClient(),
            [
                {
                    "repo_url": "https://github.com/example/repo",
                    "repo_owner": "example",
                    "repo_name": "repo",
                    "offending_file_path": "README.md",
                    "offending_file_name": "README.md",
                    "target_scope": "repository",
                    "alleged_data_type": "imaging",
                    "direct_app_ids": "",
                    "notice_id": "n1",
                    "notice_date": "2024-01-01",
                    "notice_path": "2024/01/notice.md",
                }
            ],
            wayback_limit=0,
        )
        lineages = make_lineages(repos)
        _, final = candidate_tables(
            lineages,
            [
                {
                    "app_id": "123",
                    "title": "Heart imaging model",
                    "pi": "Dr Ada Smith",
                    "institution": "Example University",
                    "notes": "UK Biobank imaging",
                }
            ],
            limit=10,
        )

        self.assertEqual(final[lineages[0]["lineage_id"]]["grade"], "confirmed")
        self.assertEqual(final[lineages[0]["lineage_id"]]["candidate"]["candidate_app_id"], "123")

    def _write_crosswalk(self, tmp: str, schema24_apps: str = "123"):
        schema19 = Path(tmp) / "schema19.tsv"
        schema24 = Path(tmp) / "schema24.tsv"
        schema19.write_text(
            "publication_id\tdoi\tpmid\ttitle\tauthors\n"
            "p1\t10.1234/ukb.paper\t12345678\tA distinctive UKB paper\tAda Smith; Ben Jones\n",
            encoding="utf-8",
        )
        schema24.write_text(
            "publication_id\tapplication_id\n"
            f"p1\t{schema24_apps}\n",
            encoding="utf-8",
        )
        return schema19, schema24

    def test_schema19_doi_pmid_to_pub_lookup_and_schema24_app_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema19, schema24 = self._write_crosswalk(tmp)
            crosswalk = enriched.load_publication_crosswalk(str(schema19), str(schema24))

        self.assertEqual(crosswalk["publications_by_doi"]["10.1234/ukb.paper"], ["p1"])
        self.assertEqual(crosswalk["publications_by_pmid"]["12345678"], ["p1"])
        self.assertEqual(crosswalk["apps_by_pub_id"]["p1"], ["123"])

    def test_one_publication_one_application_confirms(self):
        enriched.install_enrichment()
        with tempfile.TemporaryDirectory() as tmp:
            schema19, schema24 = self._write_crosswalk(tmp)
            crosswalk = enriched.load_publication_crosswalk(str(schema19), str(schema24))
            lineages = enriched.apply_publication_crosswalk(
                [
                    {
                        "lineage_id": "lineage_example",
                        "repo_linked_doi": "10.1234/ukb.paper",
                        "repo_linked_pmid": "",
                        "doi": "",
                        "pubmed_id": "",
                        "paper_title": "",
                        "paper_authors": "",
                        "repo_linked_publication_title": "",
                        "evidence_urls": "https://github.com/example/repo",
                        "_text": "",
                        "_paper_text": "",
                        "_repo_text": "",
                        "_readme_text": "",
                        "_direct_app_ids": "",
                        "alleged_data_types": "",
                    }
                ],
                crosswalk,
            )
            _, final = candidate_tables(
                lineages,
                [
                    {"app_id": "123", "title": "Any", "pi": "Ada Smith", "institution": "Example", "notes": ""},
                    {"app_id": "999", "title": "Other", "pi": "Other", "institution": "Other", "notes": ""},
                ],
                limit=10,
            )

        self.assertEqual(final["lineage_example"]["grade"], "confirmed")
        self.assertIn("A2_DOI_UKB_CROSSWALK", final["lineage_example"]["candidate"]["evidence_components"])

    def test_one_publication_multiple_applications_is_ambiguous(self):
        enriched.install_enrichment()
        with tempfile.TemporaryDirectory() as tmp:
            schema19, schema24 = self._write_crosswalk(tmp, "123; 456")
            crosswalk = enriched.load_publication_crosswalk(str(schema19), str(schema24))
            lineages = enriched.apply_publication_crosswalk(
                [
                    {
                        "lineage_id": "lineage_example",
                        "repo_linked_doi": "10.1234/ukb.paper",
                        "repo_linked_pmid": "",
                        "doi": "",
                        "pubmed_id": "",
                        "paper_title": "",
                        "paper_authors": "",
                        "repo_linked_publication_title": "",
                        "evidence_urls": "https://github.com/example/repo",
                        "_text": "",
                        "_paper_text": "",
                        "_repo_text": "",
                        "_readme_text": "",
                        "_direct_app_ids": "",
                        "alleged_data_types": "",
                    }
                ],
                crosswalk,
            )
            _, final = candidate_tables(
                lineages,
                [
                    {"app_id": "123", "title": "Any", "pi": "Ada Smith", "institution": "Example", "notes": ""},
                    {"app_id": "456", "title": "Other", "pi": "Other", "institution": "Other", "notes": ""},
                ],
                limit=10,
            )

        self.assertEqual(final["lineage_example"]["grade"], "ambiguous")

    def test_label_rules_do_not_upgrade_weak_similarity(self):
        grade, _, _ = enriched.final_label(
            {"candidate_app_id": "1", "match_score": "90", "evidence_components": "data_type; repo_path_similarity"},
            None,
            [],
        )

        self.assertEqual(grade, "unresolved")

    def test_deleted_repository_fallback_leaves_missing_dates_blank(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                return {"status": 404, "body": ""}

        rows = enriched.repo_enrich(
            FakeClient(),
            [
                {
                    "repo_url": "https://github.com/missing/repo",
                    "repo_owner": "missing",
                    "repo_name": "repo",
                    "target_ref": "",
                    "target_commit_sha": "",
                    "offending_file_path": "data/ukb.csv",
                    "offending_file_name": "ukb.csv",
                    "target_scope": "single_file",
                    "alleged_data_type": "phenotype",
                    "direct_app_ids": "",
                    "notice_id": "n1",
                    "notice_date": "2024-01-01",
                    "notice_path": "2024/01/notice.md",
                }
            ],
            wayback_limit=0,
        )

        self.assertEqual(rows[0]["repo_status"], "not_found_or_removed")
        self.assertEqual(rows[0]["first_observed_repo_date"], "")
        self.assertEqual(rows[0]["targeted_commit_author_date"], "")

    def test_lineage_merging_requires_strong_lineage_id_evidence(self):
        rows = []
        for owner in ("team-a", "team-b"):
            row = {f: "" for f in enriched.base.REPO_FIELDS}
            row.update(
                {
                    "lineage_id": f"lineage_{owner}_similar-ukb",
                    "repo_url": f"https://github.com/{owner}/similar-ukb",
                    "repo_owner": owner,
                    "repo_name": "similar-ukb",
                    "notice_id": f"n-{owner}",
                    "repo_role": "unknown",
                    "first_observed_repo_date": "2020-01-01T00:00:00Z",
                }
            )
            rows.append(row)

        lineages = enriched.make_lineages(rows)

        self.assertEqual(len(lineages), 2)


if __name__ == "__main__":
    unittest.main()
