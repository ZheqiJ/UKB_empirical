import base64
import json
import unittest

from scripts import ukb_dmca_pipeline as base
from scripts import ukb_dmca_public_metadata_runner as public_runner
from scripts import ukb_public_metadata_enrichment as public_meta


class PublicMetadataEnrichmentTests(unittest.TestCase):
    def test_nested_citation_metadata_yields_publication_identifier(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if "/git/trees/main" in url:
                    return {"status": 200, "body": json.dumps({"tree": [{"type": "blob", "path": "docs/CITATION.cff"}]})}
                if "/contents/docs/CITATION.cff" in url:
                    body = {
                        "type": "file",
                        "encoding": "base64",
                        "size": 80,
                        "content": base64.b64encode(b"title: Heart MRI prediction paper\ndoi: 10.1111/citation\n").decode(),
                        "html_url": "https://github.com/example/repo/blob/main/docs/CITATION.cff",
                    }
                    return {"status": 200, "body": json.dumps(body)}
                return {"status": 404, "body": "{}"}

        meta = public_meta.citation_metadata(FakeClient(), "example/repo", "main", public_runner.runner.identifiers)

        self.assertIn("10.1111/citation", meta["doi"])
        self.assertIn("Heart MRI prediction paper", meta["paper_title"])
        self.assertIn("docs/CITATION.cff", meta["files"])

    def test_wrapper_enriches_live_repo_from_zenodo_pypi_and_cran_metadata(self):
        public_runner.install()

        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if url == "https://api.github.com/repos/example/repo":
                    return {
                        "status": 200,
                        "body": json.dumps(
                            {
                                "id": 1,
                                "description": "UKB public metadata repo",
                                "fork": False,
                                "created_at": "2020-01-01T00:00:00Z",
                                "default_branch": "main",
                            }
                        ),
                    }
                if url.endswith("/readme"):
                    body = {
                        "encoding": "base64",
                        "content": base64.b64encode(
                            b"https://zenodo.org/records/1234 https://pypi.org/project/ukb-heart-model/"
                        ).decode(),
                        "html_url": "https://github.com/example/repo/blob/main/README.md",
                    }
                    return {"status": 200, "body": json.dumps(body)}
                if "/git/trees/main" in url:
                    return {"status": 200, "body": json.dumps({"tree": [{"type": "blob", "path": "DESCRIPTION"}]})}
                if "/contents/DESCRIPTION" in url:
                    body = {
                        "type": "file",
                        "encoding": "base64",
                        "size": 80,
                        "content": base64.b64encode(b"Package: ukbRisk\nTitle: UKB risk package\n").decode(),
                        "html_url": "https://github.com/example/repo/blob/main/DESCRIPTION",
                    }
                    return {"status": 200, "body": json.dumps(body)}
                if "zenodo.org/api/records/1234" in url:
                    return {
                        "status": 200,
                        "body": json.dumps(
                            {
                                "doi": "10.3333/zenodo",
                                "metadata": {
                                    "title": "Heart model paper",
                                    "creators": [{"name": "Ada Smith"}],
                                    "related_identifiers": [{"scheme": "doi", "identifier": "10.4444/article"}],
                                },
                            }
                        ),
                    }
                if "pypi.org/pypi/ukb-heart-model/json" in url:
                    return {
                        "status": 200,
                        "body": json.dumps({"info": {"summary": "Heart model package", "description": "Paper DOI 10.2222/pypi", "author": "Ada Smith"}}),
                    }
                if "crandb.r-pkg.org/ukbRisk" in url:
                    return {
                        "status": 200,
                        "body": json.dumps({"Package": "ukbRisk", "Title": "Risk prediction article package", "Description": "Publication DOI: 10.5555/cranpaper"}),
                    }
                return {"status": 404, "body": "{}"}

        repos = base.repo_enrich(
            FakeClient(),
            [
                {
                    "repo_url": "https://github.com/example/repo",
                    "repo_owner": "example",
                    "repo_name": "repo",
                    "offending_file_path": "data/file.csv",
                    "offending_file_name": "file.csv",
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
        lineages = base.make_lineages(repos)

        self.assertIn("10.3333/zenodo", repos[0]["doi"])
        self.assertIn("10.4444/article", repos[0]["doi"])
        self.assertIn("10.2222/pypi", repos[0]["doi"])
        self.assertIn("10.5555/cranpaper", repos[0]["doi"])
        self.assertIn("zenodo", lineages[0]["package_metadata_sources"])
        self.assertIn("pypi", lineages[0]["package_metadata_sources"])
        self.assertIn("cran", lineages[0]["package_metadata_sources"])

    def test_direct_repo_package_name_lookup_yields_public_metadata(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if url == "https://api.github.com/repos/example/UKBAnalytica":
                    return {"status": 200, "body": json.dumps({"default_branch": "main"})}
                if "/git/trees/main" in url:
                    return {"status": 200, "body": json.dumps({"tree": []})}
                if "crandb.r-pkg.org/UKBAnalytica" in url:
                    return {
                        "status": 200,
                        "body": json.dumps({
                            "Package": "UKBAnalytica",
                            "Title": "UKBAnalytica package",
                            "Description": "Public metadata for UK Biobank Application Number 822932 and DOI 10.1234/pkg",
                        }),
                    }
                return {"status": 404, "body": "{}"}

        rows = public_meta.enrich_repo_rows(
            FakeClient(),
            [{"repo_owner": "example", "repo_name": "UKBAnalytica"}],
            [{
                "repo_owner": "example",
                "repo_name": "UKBAnalytica",
                "repo_status": "live",
                "repo_urls": "https://github.com/example/UKBAnalytica",
                "evidence_urls": "",
                "_readme_text": "",
                "_evidence_excerpts": "",
            }],
            wayback_limit=0,
            base=base,
            identifiers=public_runner.runner.identifiers,
        )

        self.assertIn("10.1234/pkg", rows[0]["doi"])
        self.assertIn("822932", rows[0]["_direct_app_ids"])
        self.assertIn("cran", rows[0]["package_metadata_sources"])

    def test_exact_repo_record_metadata_yields_publication_identifiers(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if "zenodo.org/api/records?" in url:
                    return {
                        "status": 200,
                        "body": json.dumps({
                            "hits": {
                                "hits": [{
                                    "id": 123,
                                    "doi": "10.5281/zenodo.123",
                                    "links": {"html": "https://zenodo.org/records/123"},
                                    "metadata": {
                                        "title": "Exact tool archive",
                                        "description": "Source: https://github.com/example/tool",
                                        "creators": [{"name": "Ada Smith"}],
                                        "related_identifiers": [{"identifier": "10.5555/article", "scheme": "doi"}],
                                    },
                                }]
                            }
                        }),
                    }
                if "europepmc" in url:
                    return {
                        "status": 200,
                        "body": json.dumps({
                            "resultList": {
                                "result": [{
                                    "title": "Exact repo article",
                                    "authorString": "Ada Smith",
                                    "doi": "10.6666/epmc",
                                    "pmid": "12345678",
                                }]
                            }
                        }),
                    }
                return {"status": 404, "body": "{}"}

        meta = public_meta.exact_repo_record_metadata(FakeClient(), "example/tool", public_runner.runner.identifiers)

        self.assertIn("10.5281/zenodo.123", meta["doi"])
        self.assertIn("10.5555/article", meta["doi"])
        self.assertIn("10.6666/epmc", meta["doi"])
        self.assertEqual(meta["pubmed_id"], "12345678")
        self.assertIn("zenodo_exact_repo_url", meta["sources"])
        self.assertIn("europepmc_exact_repo_url", meta["sources"])

    def test_wayback_readme_is_read_only_for_deleted_repo(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if "web.archive.org/cdx" in url and "README.md" in url:
                    return {
                        "status": 200,
                        "body": json.dumps(
                            [
                                ["timestamp", "original", "statuscode", "mimetype", "digest"],
                                ["20200101000000", "https://raw.githubusercontent.com/example/deleted/main/README.md", "200", "text/plain", "d1"],
                            ]
                        ),
                    }
                if "web.archive.org/cdx" in url:
                    return {"status": 200, "body": json.dumps([["timestamp", "original", "statuscode", "mimetype", "digest"]])}
                if "web.archive.org/web/20200101000000id_" in url:
                    return {
                        "status": 200,
                        "body": "Public README links https://pubmed.ncbi.nlm.nih.gov/12345678/",
                        "fetched_at_utc": "2026-08-12T00:00:00+00:00",
                    }
                return {"status": 404, "body": "{}"}

        meta = public_meta.wayback_readme(FakeClient(), "example/deleted", 1, public_runner.runner.identifiers)

        self.assertEqual(meta["pubmed_id"], "12345678")
        self.assertEqual(meta["wayback_readme_first_capture"], "20200101000000")
        self.assertIn("web.archive.org/web/20200101000000id_", meta["wayback_readme_urls"])


if __name__ == "__main__":
    unittest.main()
