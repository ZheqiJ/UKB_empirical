import base64
import json
import unittest

from scripts import ukb_dmca_enriched_pipeline as enriched
from scripts import ukb_dmca_enriched_appid_runner as appid_runner
from scripts import ukb_dmca_pipeline as base
from scripts import ukb_public_metadata_enrichment as public_meta


class EnrichedMatchingTests(unittest.TestCase):
    def setUp(self):
        enriched.install_enrichment()

    def test_readme_application_id_becomes_confirmed(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if url.endswith("/readme"):
                    body = {
                        "encoding": "base64",
                        "content": base64.b64encode(b"This repository uses UK Biobank application 123 for cardiac MRI.").decode(),
                        "html_url": "https://github.com/example/repo/blob/main/README.md",
                    }
                    return {"status": 200, "body": json.dumps(body)}
                return {
                    "status": 200,
                    "body": json.dumps(
                        {
                            "id": 1,
                            "description": "Cardiac MRI model",
                            "fork": False,
                            "created_at": "2020-01-01T00:00:00Z",
                        }
                    ),
                }

        repos = base.repo_enrich(
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
        lineages = base.make_lineages(repos)
        _, final = base.candidate_tables(
            lineages,
            [
                {
                    "app_id": "123",
                    "title": "Cardiac MRI model",
                    "pi": "Dr Ada Smith",
                    "institution": "Example University",
                    "notes": "UK Biobank imaging",
                }
            ],
            limit=10,
        )

        self.assertEqual(final[lineages[0]["lineage_id"]]["grade"], "confirmed")

    def test_concatenated_app_id_becomes_confirmed(self):
        appid_runner.install()

        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if url.endswith("/readme"):
                    body = {
                        "encoding": "base64",
                        "content": base64.b64encode(b"Running on database app103356 for cardiac MRI.").decode(),
                        "html_url": "https://github.com/example/repo/blob/main/README.md",
                    }
                    return {"status": 200, "body": json.dumps(body)}
                return {
                    "status": 200,
                    "body": json.dumps({"id": 1, "description": "Cardiac MRI model", "fork": False}),
                }

        repos = base.repo_enrich(
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
        lineages = base.make_lineages(repos)
        _, final = base.candidate_tables(
            lineages,
            [
                {
                    "app_id": "103356",
                    "title": "Cardiac MRI model",
                    "pi": "Dr Ada Smith",
                    "institution": "Example University",
                    "notes": "UK Biobank imaging",
                }
            ],
            limit=10,
        )

        self.assertEqual(final[lineages[0]["lineage_id"]]["grade"], "confirmed")

    def test_paper_identifier_plus_public_text_scores_probable(self):
        appid_runner.install()

        lineage = {
            "lineage_id": "lineage_example",
            "_direct_app_ids": "",
            "_repo_text": "https://github.com/example/repo data/cardiac_mri.csv imaging",
            "_paper_text": "Cardiac MRI risk prediction Ada Smith 10.1234/example",
            "_readme_text": "Publication: Cardiac MRI risk prediction by Ada Smith at Example University",
            "doi": "10.1234/example",
            "pubmed_id": "",
            "alleged_data_types": "imaging",
            "evidence_urls": "https://doi.org/10.1234/example",
        }
        app = {
            "app_id": "456",
            "title": "Cardiac MRI risk prediction",
            "pi": "Ada Smith",
            "institution": "Example University",
            "notes": "UK Biobank cardiac imaging",
        }
        indexed = dict(app)
        indexed.update(
            {
                "_title": base.tokens(app["title"]),
                "_pi": base.tokens(app["pi"]),
                "_inst": base.tokens(app["institution"]),
                "_notes": base.tokens(app["notes"]),
            }
        )

        score, components, _, level = base.score(lineage, indexed)
        top = {"candidate_app_id": "456", "match_score": score, "evidence_components": base.uniq(components)}
        grade, _, _ = base.final_label(top, None, [])

        self.assertEqual(level, "B")
        self.assertEqual(grade, "probable")

    def test_application_note_doi_is_retained_as_strong_candidate_evidence(self):
        appid_runner.install()
        lineage = {
            "lineage_id": "lineage_example",
            "_direct_app_ids": "",
            "_repo_text": "https://github.com/example/repo phenotype",
            "_paper_text": "10.1234/example",
            "_readme_text": "Replication code for Example disease prediction",
            "paper_title": "Example disease prediction in UK Biobank",
            "doi": "10.1234/example",
            "pubmed_id": "",
            "alleged_data_types": "phenotype",
            "evidence_urls": "https://doi.org/10.1234/example",
        }
        app = {
            "app_id": "789",
            "title": "Disease prediction in UK Biobank",
            "pi": "Dr Ada Smith",
            "institution": "Example University",
            "notes": "Publication DOI: 10.1234/example. Example disease prediction in UK Biobank.",
        }
        indexed = dict(app)
        indexed.update(
            {
                "_title": base.tokens(app["title"]),
                "_pi": base.tokens(app["pi"]),
                "_inst": base.tokens(app["institution"]),
                "_notes": base.tokens(app["notes"]),
            }
        )

        score, components, details, level = base.score(lineage, indexed)

        self.assertGreaterEqual(score, 45)
        self.assertEqual(level, "B")
        self.assertIn("application_note_doi", components)
        self.assertEqual(details["application_note_doi"], ["10.1234/example"])

    def test_citation_metadata_discovers_nested_public_metadata(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if "/git/trees/main" in url:
                    return {
                        "status": 200,
                        "body": json.dumps({"tree": [{"type": "blob", "path": "docs/CITATION.cff"}]}),
                    }
                if "/contents/docs/CITATION.cff" in url:
                    body = {
                        "type": "file",
                        "encoding": "base64",
                        "size": 90,
                        "content": base64.b64encode(
                            b"title: Deep heart MRI prediction paper\ndoi: 10.1111/citation\n"
                        ).decode(),
                        "html_url": "https://github.com/example/repo/blob/main/docs/CITATION.cff",
                    }
                    return {"status": 200, "body": json.dumps(body)}
                return {"status": 404, "body": "{}"}

        meta = public_meta.citation_metadata(FakeClient(), "example/repo", "main", appid_runner.identifiers)

        self.assertIn("docs/CITATION.cff", meta["files"])
        self.assertIn("Deep heart MRI prediction paper", meta["paper_title"])
        self.assertIn("docs/CITATION.cff", meta["urls"])

    def test_deleted_repo_wayback_readme_adds_publication_identifier(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if "api.github.com/repos/example/deleted" in url:
                    return {"status": 404, "body": "{}"}
                if "web.archive.org/cdx" in url:
                    params = urllib_parse_qs(url)
                    target = params.get("url", [""])[0]
                    if target.startswith("raw.githubusercontent.com/example/deleted/"):
                        return {
                            "status": 200,
                            "body": json.dumps(
                                [
                                    ["timestamp", "original", "statuscode", "mimetype", "digest"],
                                    ["20200101000000", "https://raw.githubusercontent.com/example/deleted/main/README.md", "200", "text/plain", "d1"],
                                ]
                            ),
                        }
                    return {"status": 200, "body": json.dumps([["timestamp", "original", "statuscode", "mimetype", "digest"]])}
                if "web.archive.org/web/20200101000000id_" in url:
                    return {
                        "status": 200,
                        "body": "README for [Heart GWAS paper](https://pubmed.ncbi.nlm.nih.gov/12345678/).",
                        "fetched_at_utc": "2026-08-12T00:00:00+00:00",
                    }
                if "esummary.fcgi" in url:
                    return {
                        "status": 200,
                        "body": json.dumps(
                            {
                                "result": {
                                    "12345678": {
                                        "title": "Heart GWAS paper",
                                        "authors": [{"name": "Ada Smith"}],
                                        "articleids": [],
                                    }
                                }
                            }
                        ),
                    }
                return {"status": 404, "body": "{}"}

        repos = base.repo_enrich(
            FakeClient(),
            [
                {
                    "repo_url": "https://github.com/example/deleted",
                    "repo_owner": "example",
                    "repo_name": "deleted",
                    "offending_file_path": "data/file.csv",
                    "offending_file_name": "file.csv",
                    "target_scope": "single_file",
                    "alleged_data_type": "gwas",
                    "direct_app_ids": "",
                    "notice_id": "n1",
                    "notice_date": "2024-01-01",
                    "notice_path": "2024/01/notice.md",
                }
            ],
            wayback_limit=1,
        )

        self.assertEqual(repos[0]["pubmed_id"], "12345678")
        self.assertIn("Heart GWAS paper", repos[0]["paper_title"])
        self.assertIn("web.archive.org/web/20200101000000id_", repos[0]["wayback_readme_urls"])

    def test_repo_enrich_uses_zenodo_and_pypi_public_metadata(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if url == "https://api.github.com/repos/example/repo":
                    return {
                        "status": 200,
                        "body": json.dumps(
                            {
                                "id": 1,
                                "description": "UKB heart model",
                                "fork": False,
                                "created_at": "2020-01-01T00:00:00Z",
                                "default_branch": "main",
                                "owner": {"login": "example"},
                            }
                        ),
                    }
                if url.endswith("/readme"):
                    body = {
                        "encoding": "base64",
                        "content": base64.b64encode(
                            b"Package https://pypi.org/project/ukb-heart-model/ archive https://zenodo.org/records/1234"
                        ).decode(),
                        "html_url": "https://github.com/example/repo/blob/main/README.md",
                    }
                    return {"status": 200, "body": json.dumps(body)}
                if "/git/trees/main" in url or "/contents/" in url or "api.github.com/users/example" in url:
                    return {"status": 404, "body": "{}"}
                if "zenodo.org/api/records/1234" in url:
                    return {
                        "status": 200,
                        "body": json.dumps(
                            {
                                "doi": "10.3333/zenodo",
                                "metadata": {
                                    "title": "Heart model paper",
                                    "creators": [{"name": "Ada Smith"}],
                                    "related_identifiers": [
                                        {"scheme": "doi", "identifier": "10.4444/article", "relation": "isSupplementTo"}
                                    ],
                                },
                            }
                        ),
                    }
                if "pypi.org/pypi/ukb-heart-model/json" in url:
                    return {
                        "status": 200,
                        "body": json.dumps({"info": {"summary": "Heart model package", "description": "Paper DOI 10.2222/pypi", "author": "Ada Smith"}}),
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

        self.assertIn("10.2222/pypi", repos[0]["repo_linked_doi"])
        self.assertIn("10.3333/zenodo", repos[0]["repo_linked_doi"])
        self.assertIn("10.4444/article", repos[0]["repo_linked_doi"])
        self.assertIn("Heart model paper", repos[0]["paper_title"])
        self.assertIn("zenodo", repos[0]["package_metadata_sources"])
        self.assertIn("pypi", repos[0]["package_metadata_sources"])

    def test_repo_enrich_uses_cran_description_metadata(self):
        class FakeClient:
            def fetch(self, url, *args, **kwargs):
                if url == "https://api.github.com/repos/example/rpkg":
                    return {
                        "status": 200,
                        "body": json.dumps(
                            {
                                "id": 1,
                                "description": "R package",
                                "fork": False,
                                "default_branch": "main",
                                "owner": {"login": "example"},
                            }
                        ),
                    }
                if url.endswith("/readme"):
                    return {"status": 404, "body": "{}"}
                if "/git/trees/main" in url:
                    return {"status": 200, "body": json.dumps({"tree": [{"type": "blob", "path": "DESCRIPTION"}]})}
                if "/contents/DESCRIPTION" in url:
                    body = {
                        "type": "file",
                        "encoding": "base64",
                        "size": 120,
                        "content": base64.b64encode(b"Package: ukbRisk\nTitle: UKB risk package\n").decode(),
                        "html_url": "https://github.com/example/rpkg/blob/main/DESCRIPTION",
                    }
                    return {"status": 200, "body": json.dumps(body)}
                if "crandb.r-pkg.org/ukbRisk" in url:
                    return {
                        "status": 200,
                        "body": json.dumps(
                            {
                                "Package": "ukbRisk",
                                "Title": "Risk prediction article package",
                                "Description": "Publication DOI: 10.5555/cranpaper",
                                "Author": "Ada Smith",
                            }
                        ),
                    }
                return {"status": 404, "body": "{}"}

        repos = base.repo_enrich(
            FakeClient(),
            [
                {
                    "repo_url": "https://github.com/example/rpkg",
                    "repo_owner": "example",
                    "repo_name": "rpkg",
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

        self.assertIn("10.5555/cranpaper", repos[0]["repo_linked_doi"])
        self.assertIn("cran", repos[0]["package_metadata_sources"])


def urllib_parse_qs(url):
    from urllib.parse import parse_qs, urlparse

    return parse_qs(urlparse(url).query)


if __name__ == "__main__":
    unittest.main()
