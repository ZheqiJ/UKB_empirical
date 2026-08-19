#!/usr/bin/env python3
"""Application-evidence enrichment layer for the UKB DMCA pipeline.

This wrapper intentionally leaves notice discovery/filtering in
``ukb_dmca_pipeline`` untouched. It patches only repository/public metadata
enrichment, application scoring, and lineage evidence output.
"""

from __future__ import annotations

import base64
import csv
import html
import json
import re
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    import ukb_dmca_pipeline as base
except ImportError:  # unittest imports from the repository root
    from scripts import ukb_dmca_pipeline as base


MD_LINK = re.compile(r"\[([^\]]{3,250})\]\((https?://[^)\s]+)\)")
PUBLIC_URL = re.compile(r"https?://[^\s\]\)<>'\"`{}]+")
NATURE_ARTICLE_URL = re.compile(
    r"(?:https?://)?(?:www\.)?nature\.com/articles/([A-Za-z0-9][A-Za-z0-9._-]*)",
    re.I,
)
PUBMED_URL = re.compile(
    r"(?:https?://)?(?:www\.)?(?:pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov/pubmed)/(\d{6,9})(?:[/?#\s]|$)",
    re.I,
)
EUROPE_PMC_MED_URL = re.compile(
    r"(?:https?://)?(?:www\.)?europepmc\.org/article/MED/(\d{6,9})(?:[/?#\s]|$)",
    re.I,
)
ZENODO_RECORD_URL = re.compile(r"(?:https?://)?(?:www\.)?zenodo\.org/(?:record|records)/(\d+)", re.I)
PYPI_PROJECT_URL = re.compile(r"(?:https?://)?pypi\.org/project/([A-Za-z0-9_.-]+)", re.I)
CRAN_PACKAGE_URL = re.compile(
    r"(?:https?://)?cran\.r-project\.org/(?:web/packages/([A-Za-z0-9_.-]+)|package=([A-Za-z0-9_.-]+))",
    re.I,
)
CITATION_HINT = re.compile(
    r"\b(doi|pmid|pubmed|paper|publication|article|preprint|manuscript|citation|"
    r"code availability|data availability|zenodo|pypi|cran)\b",
    re.I,
)
APP_HINT = re.compile(r"\b(application|app|project)\s*(?:no\.?|number|id|#)?\s*:?\s*\d{2,6}\b", re.I)
DIRECT_APP_ID = re.compile(
    r"\b(?:UK\s*Biobank\s*)?(?:application|project)\s*(?:no\.?|number|id|#)?\s*:?\s*(\d{2,6})\b"
    r"|\bapp\s*#?\s*(\d{2,6})\b"
    r"|\bapp(\d{2,6})\b",
    re.I,
)
MAX_PUBLIC_TEXT_CHARS = 200_000
METADATA_FILES = [
    "CITATION.cff",
    "codemeta.json",
    ".zenodo.json",
    "DESCRIPTION",
    "pyproject.toml",
    "package.json",
    "CITATION.bib",
]
METADATA_BASENAMES = {name.lower() for name in METADATA_FILES}
METADATA_TREE_LIMIT = 25
GENERIC_MATCH_TOKENS = {
    "biobank", "ukb", "data", "dataset", "study", "research", "analysis",
    "cancer", "genetic", "genetics", "genotype", "phenotype", "imaging",
    "risk", "disease", "health", "hospital", "episode", "statistics",
    "using", "based", "participants", "cohort",
}


def _uniq(values: Iterable[Any]) -> str:
    return base.uniq(values)


def _join(values: Iterable[Any], sep: str = "\n") -> str:
    return base.join_text(values, sep)


def markdown_text(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text or "")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_#>]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def evidence_lines(text: str, limit: int = 12) -> list[str]:
    lines, seen = [], set()
    for raw in (text or "").splitlines():
        line = markdown_text(raw)
        if len(line) < 8:
            continue
        if not (APP_HINT.search(line) or CITATION_HINT.search(line) or base.DOI.search(line) or base.PMID.search(line)):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line[:500])
        if len(lines) >= limit:
            break
    return lines


def identifiers(text: str) -> dict[str, list[str]]:
    app_ids = []
    for m in DIRECT_APP_ID.finditer(text or ""):
        app_id = next((x for x in m.groups() if x), "")
        if app_id:
            app_ids.append(app_id)
    doi_values = [normalize_doi(x) for x in base.DOI.findall(text or "")]
    doi_values.extend(publication_url_dois(text or ""))
    pmid_values = [normalize_pmid(x) for x in base.PMID.findall(text or "")]
    pmid_values.extend(publication_url_pmids(text or ""))
    return {
        "doi": list(dict.fromkeys(x for x in doi_values if x)),
        "pubmed_id": list(dict.fromkeys(x for x in pmid_values if x)),
        "app_id": list(dict.fromkeys(app_ids)),
    }


def normalize_doi(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    text = text.strip(" \t\r\n<>[](){}.,;:")
    return text if re.match(r"^10\.\d{4,9}/", text, re.I) else ""


def normalize_pmid(value: str) -> str:
    m = re.search(r"\d{6,9}", str(value or ""))
    return m.group(0) if m else ""


def nature_slug_to_doi(slug: str) -> str:
    clean = str(slug or "").strip(" \t\r\n<>[](){}.,;:").lower()
    if re.match(r"^s\d{4,}[-a-z0-9]+$", clean) or re.match(r"^(?:nature|ncomms|srep)\d+$", clean) or "." in clean:
        return normalize_doi(f"10.1038/{clean}")
    return ""


def publication_url_dois(text: str) -> list[str]:
    dois = [nature_slug_to_doi(m.group(1)) for m in NATURE_ARTICLE_URL.finditer(text or "")]
    return list(dict.fromkeys(doi for doi in dois if doi))


def publication_url_pmids(text: str) -> list[str]:
    values = [m.group(1) for m in PUBMED_URL.finditer(text or "")]
    values.extend(m.group(1) for m in EUROPE_PMC_MED_URL.finditer(text or ""))
    return list(dict.fromkeys(normalize_pmid(v) for v in values if normalize_pmid(v)))


def norm_col(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def find_col(headers: list[str], kind: str) -> str:
    norms = {h: norm_col(h) for h in headers}
    for h, n in norms.items():
        if kind == "doi" and ("doi" in n or "digitalobjectidentifier" in n):
            return h
        if kind == "pmid" and ("pmid" in n or "pubmed" in n):
            return h
        if kind == "title" and "title" in n:
            return h
        if kind == "authors" and "author" in n:
            return h
        if kind == "app_id" and (n in {"appid", "applicationid", "applicationnumber"} or ("application" in n and "id" in n)):
            return h
        if kind == "pub_id" and (n in {"pubid", "publicationid", "publicationeid"} or ("publication" in n and "id" in n)):
            return h
    if kind == "pub_id":
        for h, n in norms.items():
            if n in {"id", "eid"}:
                return h
    return ""


def split_values(value: str) -> list[str]:
    return [x.strip() for x in re.split(r"[;,|]", str(value or "")) if x.strip()]


def normalized_title(value: str) -> str:
    text = markdown_text(value)
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def normalized_name(value: str) -> str:
    text = re.sub(r"\b(dr|prof|professor|mr|mrs|ms|miss)\.?\b", " ", str(value or ""), flags=re.I)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text).lower()
    tokens = [t for t in text.split() if len(t) > 1]
    return " ".join(tokens)


def text_tokens(value: str) -> set[str]:
    return base.tokens(value) - GENERIC_MATCH_TOKENS


def parts(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split(";") if x.strip()]


def earliest(rows: list[dict[str, str]], field: str) -> str:
    return min([r.get(field, "") for r in rows if r.get(field, "")], default="")


def latest(rows: list[dict[str, str]], field: str) -> str:
    return max([r.get(field, "") for r in rows if r.get(field, "")], default="")


def empty_commit_metadata() -> dict[str, str]:
    return {
        "targeted_commit_author_date": "",
        "targeted_commit_committer_date": "",
        "targeted_commit_author_name": "",
        "targeted_commit_author_login": "",
        "targeted_commit_committer_name": "",
        "targeted_commit_committer_login": "",
        "targeted_commit_url": "",
    }


def empty_history_metadata() -> dict[str, str]:
    return {
        "earliest_observed_offending_file_commit_date": "",
        "earliest_observed_offending_file_commit_sha": "",
        "earliest_commit_evidence_url": "",
        "earliest_commit_method": "",
    }


def read_delimited(path: str) -> list[dict[str, str]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    sample = p.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    delimiter = "\t" if sample.count("\t") >= sample.count(",") else ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        delimiter = dialect.delimiter
    except csv.Error:
        pass
    with p.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def load_publication_crosswalk(schema19: str, schema24: str) -> dict[str, Any]:
    """Load optional UKB Schema 19/24 publication-to-application crosswalks."""
    crosswalk: dict[str, Any] = {
        "schema19_path": schema19 or "",
        "schema24_path": schema24 or "",
        "publications_by_doi": defaultdict(list),
        "publications_by_pmid": defaultdict(list),
        "publication_metadata": {},
        "apps_by_pub_id": defaultdict(list),
        "errors": [],
    }
    schema19_rows = read_delimited(schema19)
    schema24_rows = read_delimited(schema24)
    if not schema19_rows or not schema24_rows:
        return crosswalk

    h19 = list(schema19_rows[0].keys())
    h24 = list(schema24_rows[0].keys())
    pub19_col = find_col(h19, "pub_id")
    doi_col = find_col(h19, "doi")
    pmid_col = find_col(h19, "pmid")
    title_col = find_col(h19, "title")
    authors_col = find_col(h19, "authors")
    pub24_col = find_col(h24, "pub_id")
    app_col = find_col(h24, "app_id")
    if not pub19_col:
        crosswalk["errors"].append("Schema 19 publication ID column not found.")
    if not pub24_col or not app_col:
        crosswalk["errors"].append("Schema 24 publication/application ID columns not found.")
    if crosswalk["errors"]:
        return crosswalk

    for row in schema19_rows:
        pub_id = str(row.get(pub19_col, "")).strip()
        if not pub_id:
            continue
        doi_values = [normalize_doi(x) for x in split_values(row.get(doi_col, ""))] if doi_col else []
        if doi_col:
            doi_values.append(normalize_doi(row.get(doi_col, "")))
        pmid_values = [normalize_pmid(x) for x in split_values(row.get(pmid_col, ""))] if pmid_col else []
        if pmid_col:
            pmid_values.append(normalize_pmid(row.get(pmid_col, "")))
        doi_values = [x for x in dict.fromkeys(doi_values) if x]
        pmid_values = [x for x in dict.fromkeys(pmid_values) if x]
        crosswalk["publication_metadata"][pub_id] = {
            "pub_id": pub_id,
            "doi": _uniq(doi_values),
            "pmid": _uniq(pmid_values),
            "title": row.get(title_col, "") if title_col else "",
            "authors": row.get(authors_col, "") if authors_col else "",
        }
        for doi in doi_values:
            crosswalk["publications_by_doi"][doi].append(pub_id)
        for pmid in pmid_values:
            crosswalk["publications_by_pmid"][pmid].append(pub_id)

    for row in schema24_rows:
        pub_id = str(row.get(pub24_col, "")).strip()
        if not pub_id:
            continue
        app_ids = []
        for value in split_values(row.get(app_col, "")) or [row.get(app_col, "")]:
            m = re.search(r"\d{1,7}", str(value or ""))
            if m:
                app_ids.append(m.group(0))
        for app_id in app_ids:
            if app_id and app_id not in crosswalk["apps_by_pub_id"][pub_id]:
                crosswalk["apps_by_pub_id"][pub_id].append(app_id)

    crosswalk["publications_by_doi"] = {k: sorted(set(v)) for k, v in crosswalk["publications_by_doi"].items()}
    crosswalk["publications_by_pmid"] = {k: sorted(set(v)) for k, v in crosswalk["publications_by_pmid"].items()}
    crosswalk["apps_by_pub_id"] = {k: sorted(set(v), key=lambda x: (len(x), x)) for k, v in crosswalk["apps_by_pub_id"].items()}
    return crosswalk


def apply_publication_crosswalk(lineages: list[dict[str, str]], crosswalk: dict[str, Any]) -> list[dict[str, str]]:
    pubs_by_doi = crosswalk.get("publications_by_doi") or {}
    pubs_by_pmid = crosswalk.get("publications_by_pmid") or {}
    apps_by_pub = crosswalk.get("apps_by_pub_id") or {}
    pub_meta = crosswalk.get("publication_metadata") or {}
    if not pubs_by_doi and not pubs_by_pmid:
        return lineages

    out = []
    for lineage in lineages:
        lin = dict(lineage)
        chains = []
        pub_ids: list[str] = []
        app_ids: list[str] = []
        id_types: list[str] = []
        id_values: list[str] = []
        for doi in [normalize_doi(x) for x in parts(lin.get("repo_linked_doi") or lin.get("doi", ""))]:
            if not doi:
                continue
            for pub_id in pubs_by_doi.get(doi, []):
                apps = apps_by_pub.get(pub_id, [])
                chains.append({"identifier_type": "doi", "identifier": doi, "pub_id": pub_id, "app_ids": apps})
                pub_ids.append(pub_id)
                app_ids.extend(apps)
                id_types.append("doi")
                id_values.append(doi)
        for pmid in [normalize_pmid(x) for x in parts(lin.get("repo_linked_pmid") or lin.get("pubmed_id", ""))]:
            if not pmid:
                continue
            for pub_id in pubs_by_pmid.get(pmid, []):
                apps = apps_by_pub.get(pub_id, [])
                chains.append({"identifier_type": "pmid", "identifier": pmid, "pub_id": pub_id, "app_ids": apps})
                pub_ids.append(pub_id)
                app_ids.extend(apps)
                id_types.append("pmid")
                id_values.append(pmid)

        pub_titles = [pub_meta.get(pub_id, {}).get("title", "") for pub_id in pub_ids]
        pub_authors = [pub_meta.get(pub_id, {}).get("authors", "") for pub_id in pub_ids]
        if chains:
            app_ids = sorted(set(app_ids), key=lambda x: (len(x), x))
            pub_ids = sorted(set(pub_ids), key=lambda x: (len(x), x))
            lin.update({
                "paper_title": _uniq([lin.get("paper_title", ""), *pub_titles]),
                "paper_authors": _uniq([lin.get("paper_authors", ""), *pub_authors]),
                "repo_linked_publication_title": _uniq([lin.get("repo_linked_publication_title", ""), *pub_titles]),
                "crosswalk_pub_ids": _uniq(pub_ids),
                "crosswalk_app_ids": _uniq(app_ids),
                "crosswalk_application_count": str(len(app_ids)),
                "crosswalk_identifier_type": _uniq(id_types),
                "crosswalk_evidence": json.dumps(
                    {
                        "chains": chains,
                        "schema19_path": crosswalk.get("schema19_path", ""),
                        "schema24_path": crosswalk.get("schema24_path", ""),
                    },
                    sort_keys=True,
                ),
                "_paper_text": _join([lin.get("_paper_text", ""), _uniq(pub_titles), _uniq(pub_authors), _uniq(id_values)]),
                "_text": _join([lin.get("_text", ""), _uniq(pub_titles), _uniq(pub_authors), _uniq(id_values)]),
            })
        out.append(lin)
    return out


def name_in_text(person: str, text: str) -> bool:
    person_parts = normalized_name(person).split()
    text_parts = set(normalized_name(text).split())
    if not person_parts or not text_parts:
        return False
    if len(person_parts) == 1:
        return person_parts[0] in text_parts and len(person_parts[0]) >= 4
    first, last = person_parts[0], person_parts[-1]
    return last in text_parts and (first in text_parts or any(t.startswith(first[:1]) and len(t) <= 2 for t in text_parts))


def component_strength(component: str) -> tuple[str, str]:
    if component.startswith("A") or component == "direct_application_id":
        return "deterministic", "A"
    if component in {
        "application_note_doi",
        "application_note_pubmed_id",
        "exact_publication_title",
        "normalized_publication_title",
        "paper_author_to_application_pi",
        "repo_owner_to_paper_author",
        "commit_author_to_paper_author",
        "institution_match",
        "paper_identifier",
    }:
        return "deterministic" if component in {"application_note_doi", "application_note_pubmed_id", "exact_publication_title"} else "fuzzy", "B"
    return "fuzzy", "C"


def paper_clues(text: str) -> dict[str, str]:
    titles, urls = [], []
    for label, url in MD_LINK.findall(text or ""):
        if re.search(r"(doi\.org|pubmed|ncbi\.nlm|medrxiv|biorxiv|arxiv|nature\.com|science\.org|thelancet|jamanetwork|nejm)", url, re.I) or CITATION_HINT.search(label):
            title = markdown_text(label)
            if 8 <= len(title) <= 240 and title.lower() not in {"paper", "article", "publication", "preprint", "manuscript"}:
                titles.append(title)
            urls.append(url)
    for line in evidence_lines(text, limit=20):
        if base.DOI.search(line) or base.PMID.search(line) or re.search(r"\b(title|paper|article|publication|preprint)\b", line, re.I):
            cleaned = re.sub(r"\b(doi|pmid|pubmed)\b[:\s].*", "", line, flags=re.I).strip(" -:;")
            if 20 <= len(cleaned) <= 240:
                titles.append(cleaned)
    return {
        "paper_title": _uniq(titles),
        "evidence_urls": _uniq(urls),
        "evidence_excerpts": " | ".join(evidence_lines(text)),
    }


def repo_readme(client: Any, full: str) -> dict[str, str]:
    r = client.fetch(f"https://api.github.com/repos/{full}/readme")
    if r["status"] != 200:
        return {"text": "", "url": ""}
    try:
        data = json.loads(r["body"])
        content = data.get("content", "")
        if data.get("encoding") == "base64" and content:
            raw = base64.b64decode(content, validate=False).decode("utf-8", "replace")
        else:
            raw = str(content)
        return {"text": raw[:MAX_PUBLIC_TEXT_CHARS], "url": data.get("html_url") or data.get("download_url") or ""}
    except Exception:
        return {"text": "", "url": ""}


def crossref_work(client: Any, doi: str) -> dict[str, str]:
    if not doi:
        return {"paper_title": "", "paper_authors": "", "evidence_urls": ""}
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    r = client.fetch(url, "application/json", timeout=15, retries=0)
    if r["status"] != 200:
        return {"paper_title": "", "paper_authors": "", "evidence_urls": f"https://doi.org/{doi}"}
    try:
        msg = json.loads(r["body"]).get("message", {})
        authors = []
        for a in msg.get("author", [])[:12]:
            name = " ".join(x for x in [a.get("given", ""), a.get("family", "")] if x).strip()
            if name:
                authors.append(name)
        return {
            "paper_title": _uniq(msg.get("title", [])[:2]),
            "paper_authors": _uniq(authors),
            "evidence_urls": f"https://doi.org/{doi}",
        }
    except Exception:
        return {"paper_title": "", "paper_authors": "", "evidence_urls": f"https://doi.org/{doi}"}


def pubmed_summary(client: Any, pmid: str) -> dict[str, str]:
    if not pmid:
        return {"paper_title": "", "paper_authors": "", "doi": "", "evidence_urls": ""}
    q = urllib.parse.urlencode({"db": "pubmed", "id": pmid, "retmode": "json"})
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + q
    evidence_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    r = client.fetch(url, "application/json", timeout=15, retries=0)
    if r["status"] != 200:
        return {"paper_title": "", "paper_authors": "", "doi": "", "evidence_urls": evidence_url}
    try:
        item = json.loads(r["body"]).get("result", {}).get(pmid, {})
        authors = [a.get("name", "") for a in item.get("authors", [])[:12] if a.get("name")]
        doi = ""
        for aid in item.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "").lower()
                break
        return {
            "paper_title": item.get("title", ""),
            "paper_authors": _uniq(authors),
            "doi": doi,
            "evidence_urls": evidence_url,
        }
    except Exception:
        return {"paper_title": "", "paper_authors": "", "doi": "", "evidence_urls": evidence_url}


def github_content(client: Any, full: str, path: str, ref: str = "") -> dict[str, str]:
    quoted = urllib.parse.quote(path, safe="/")
    q = f"?ref={urllib.parse.quote(ref, safe='')}" if ref else ""
    r = client.fetch(f"https://api.github.com/repos/{full}/contents/{quoted}{q}")
    if r["status"] != 200:
        return {"text": "", "url": "", "path": path}
    try:
        data = json.loads(r["body"])
        if isinstance(data, list) or data.get("type") != "file":
            return {"text": "", "url": "", "path": path}
        if int(data.get("size") or 0) > 500_000:
            return {"text": "", "url": data.get("html_url", ""), "path": path}
        content = data.get("content", "")
        if data.get("encoding") == "base64" and content:
            text = base64.b64decode(content, validate=False).decode("utf-8", "replace")
        else:
            text = str(content)
        return {"text": text[:MAX_PUBLIC_TEXT_CHARS], "url": data.get("html_url") or data.get("download_url") or "", "path": path}
    except Exception:
        return {"text": "", "url": "", "path": path}


def metadata_path_candidates(client: Any, full: str, default_branch: str) -> list[str]:
    paths = list(METADATA_FILES)
    if not default_branch:
        return paths
    url = f"https://api.github.com/repos/{full}/git/trees/{urllib.parse.quote(default_branch, safe='')}?recursive=1"
    r = client.fetch(url)
    if r["status"] != 200:
        return paths
    try:
        tree = json.loads(r["body"]).get("tree", [])
    except Exception:
        return paths
    for item in tree:
        path = item.get("path", "")
        if item.get("type") != "blob" or not path:
            continue
        if Path(path).name.lower() in METADATA_BASENAMES and path not in paths:
            paths.append(path)
        if len(paths) >= METADATA_TREE_LIMIT:
            break
    return paths


def publication_links_from_text(text: str) -> list[str]:
    urls = []
    for raw in PUBLIC_URL.findall(text or ""):
        url = raw.strip(" \t\r\n.,;:)]}")
        if re.search(
            r"(doi\.org|pubmed|ncbi\.nlm|europepmc|medrxiv|biorxiv|arxiv|nature\.com/articles|"
            r"science\.org|thelancet|jamanetwork|nejm|zenodo\.org|pypi\.org/project|cran\.r-project\.org)",
            url,
            re.I,
        ):
            urls.append(url)
    return list(dict.fromkeys(urls))


def metadata_titles(text: str) -> str:
    titles: list[str] = []
    stripped = (text or "").strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            data = json.loads(stripped)
            titles.extend(json_metadata_values(data, {"title", "publicationtitle", "articletitle"}, limit=8))
        except Exception:
            pass
    for line in (text or "").splitlines():
        m = re.match(r"\s*(?:title|publication[_ -]?title|article[_ -]?title)\s*[:=]\s*[\"']?(.+?)[\"']?\s*,?\s*$", line, re.I)
        if m:
            title = markdown_text(m.group(1)).strip(" ,;")
            if 12 <= len(title) <= 260:
                titles.append(title)
    return _uniq(titles)


def json_metadata_values(obj: Any, keys: set[str], limit: int = 20) -> list[str]:
    out: list[str] = []

    def walk(value: Any) -> None:
        if len(out) >= limit:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                norm = re.sub(r"[^a-z0-9]+", "", str(key).lower())
                if norm in keys:
                    if isinstance(child, str):
                        out.append(child)
                    elif isinstance(child, list):
                        out.extend(str(x) for x in child if isinstance(x, (str, int, float)))
                walk(child)
        elif isinstance(value, list):
            for child in value[:50]:
                walk(child)

    walk(obj)
    return [markdown_text(x)[:260] for x in out if 8 <= len(markdown_text(x)) <= 260]


def json_author_values(obj: Any, limit: int = 20) -> list[str]:
    out: list[str] = []

    def add_name(value: Any) -> None:
        if len(out) >= limit:
            return
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, dict):
            name = value.get("name") or value.get("fullName")
            if not name:
                name = " ".join(str(value.get(k, "")) for k in ("given", "givenName", "family", "familyName")).strip()
            if name:
                out.append(name)

    def walk(value: Any) -> None:
        if len(out) >= limit:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                norm = re.sub(r"[^a-z0-9]+", "", str(key).lower())
                if norm in {"author", "authors", "creator", "creators"}:
                    if isinstance(child, list):
                        for item in child[:limit]:
                            add_name(item)
                    else:
                        add_name(child)
                walk(child)
        elif isinstance(value, list):
            for child in value[:50]:
                walk(child)

    walk(obj)
    return [markdown_text(x)[:160] for x in out if 2 <= len(markdown_text(x)) <= 160]


def metadata_authors(text: str) -> str:
    stripped = (text or "").strip()
    authors: list[str] = []
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            authors.extend(json_author_values(json.loads(stripped)))
        except Exception:
            pass
    for line in (text or "").splitlines():
        m = re.match(r"\s*(?:authors?|creators?|maintainer)\s*[:=]\s*(.+)$", line, re.I)
        if m:
            authors.extend(x.strip(" \"'") for x in re.split(r"\s+and\s+|;", m.group(1)) if x.strip())
    return _uniq(authors[:20])


def pypi_package_names(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(1).strip(" .,/") for m in PYPI_PROJECT_URL.finditer(text or "")))


def cran_package_names(text: str, citation_files: str) -> list[str]:
    names = [next(x for x in m.groups() if x).strip(" .,/") for m in CRAN_PACKAGE_URL.finditer(text or "") if any(m.groups())]
    if "DESCRIPTION" in (citation_files or ""):
        m = re.search(r"(?m)^\s*Package:\s*([A-Za-z0-9_.-]+)\s*$", text or "")
        if m:
            names.append(m.group(1))
    return list(dict.fromkeys(names))


def zenodo_metadata(client: Any, text: str) -> dict[str, str]:
    bodies, urls, titles, authors = [], [], [], []
    for record_id in list(dict.fromkeys(m.group(1) for m in ZENODO_RECORD_URL.finditer(text or "")))[:5]:
        api_url = f"https://zenodo.org/api/records/{record_id}"
        r = client.fetch(api_url, "application/json", timeout=15, retries=0)
        urls.append(f"https://zenodo.org/records/{record_id}")
        if r["status"] != 200:
            continue
        try:
            data = json.loads(r["body"])
        except Exception:
            continue
        meta = data.get("metadata") or {}
        title = meta.get("title") or data.get("title") or ""
        if title:
            titles.append(title)
        creators = []
        for creator in meta.get("creators", [])[:12]:
            name = creator.get("name") or " ".join(x for x in [creator.get("given_name", ""), creator.get("family_name", "")] if x)
            if name:
                creators.append(name)
        authors.extend(creators)
        parts_text = [title, data.get("doi", ""), meta.get("doi", "")]
        for rel in meta.get("related_identifiers", [])[:20]:
            parts_text.extend([rel.get("identifier", ""), rel.get("relation", ""), rel.get("scheme", "")])
        bodies.append(_join(parts_text, "\n"))
    combined = _join(bodies)
    return {
        "text": combined,
        "urls": _uniq(urls),
        "paper_title": _uniq(titles),
        "paper_authors": _uniq(authors),
        "sources": "zenodo",
        "evidence_excerpts": " | ".join(evidence_lines(combined)),
    }


def pypi_metadata(client: Any, text: str) -> dict[str, str]:
    bodies, urls, titles, authors = [], [], [], []
    for package in pypi_package_names(text)[:5]:
        api_url = f"https://pypi.org/pypi/{urllib.parse.quote(package, safe='')}/json"
        r = client.fetch(api_url, "application/json", timeout=15, retries=0)
        urls.append(f"https://pypi.org/project/{package}/")
        if r["status"] != 200:
            continue
        try:
            info = json.loads(r["body"]).get("info", {})
        except Exception:
            continue
        body = _join([
            info.get("name", ""),
            info.get("summary", ""),
            info.get("description", ""),
            info.get("home_page", ""),
            json.dumps(info.get("project_urls", {}), sort_keys=True),
            info.get("author", ""),
            info.get("maintainer", ""),
        ])
        bodies.append(body)
        if info.get("summary"):
            titles.append(info["summary"])
        authors.extend([info.get("author", ""), info.get("maintainer", "")])
    combined = _join(bodies)
    return {
        "text": combined,
        "urls": _uniq(urls),
        "paper_title": _uniq(titles),
        "paper_authors": _uniq(authors),
        "sources": "pypi" if urls else "",
        "evidence_excerpts": " | ".join(evidence_lines(combined)),
    }


def cran_metadata(client: Any, text: str, citation_files: str) -> dict[str, str]:
    bodies, urls, titles, authors = [], [], [], []
    for package in cran_package_names(text, citation_files)[:5]:
        api_url = f"https://crandb.r-pkg.org/{urllib.parse.quote(package, safe='')}"
        r = client.fetch(api_url, "application/json", timeout=15, retries=0)
        urls.append(f"https://cran.r-project.org/package={package}")
        if r["status"] != 200:
            continue
        try:
            data = json.loads(r["body"])
        except Exception:
            continue
        body = _join([
            data.get("Package", ""),
            data.get("Title", ""),
            data.get("Description", ""),
            data.get("URL", ""),
            data.get("BugReports", ""),
            data.get("Author", ""),
            data.get("Maintainer", ""),
        ])
        bodies.append(body)
        if data.get("Title"):
            titles.append(data["Title"])
        authors.extend([data.get("Author", ""), data.get("Maintainer", "")])
    combined = _join(bodies)
    return {
        "text": combined,
        "urls": _uniq(urls),
        "paper_title": _uniq(titles),
        "paper_authors": _uniq(authors),
        "sources": "cran" if urls else "",
        "evidence_excerpts": " | ".join(evidence_lines(combined)),
    }


def public_package_metadata(client: Any, public_text: str, citation_files: str) -> dict[str, str]:
    enrichments = [
        zenodo_metadata(client, public_text),
        pypi_metadata(client, public_text),
        cran_metadata(client, public_text, citation_files),
    ]
    combined = _join(e.get("text", "") for e in enrichments)
    clues = paper_clues(combined)
    return {
        "text": combined,
        "urls": _uniq(e.get("urls", "") for e in enrichments),
        "paper_title": _uniq([*(e.get("paper_title", "") for e in enrichments), clues["paper_title"], metadata_titles(combined)]),
        "paper_authors": _uniq(e.get("paper_authors", "") for e in enrichments),
        "sources": _uniq(e.get("sources", "") for e in enrichments),
        "publication_links": _uniq(publication_links_from_text(_join([public_text, combined]))),
        "evidence_excerpts": _uniq([*(e.get("evidence_excerpts", "") for e in enrichments), clues["evidence_excerpts"]]),
    }


def html_to_text(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", value or "")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def wayback_readme(client: Any, repo_url: str, limit: int) -> dict[str, str]:
    empty = {
        "text": "",
        "wayback_readme_first_capture": "",
        "wayback_readme_capture_count": "0",
        "wayback_readme_urls": "",
        "wayback_readme_fetched_at_utc": "",
        "evidence_excerpts": "",
    }
    if limit <= 0:
        return empty
    parsed = urllib.parse.urlparse(repo_url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return empty
    owner, repo = parts[0], parts[1].removesuffix(".git")
    patterns = [
        f"raw.githubusercontent.com/{owner}/{repo}/*/README.md",
        f"raw.githubusercontent.com/{owner}/{repo}/*/README.rst",
        f"raw.githubusercontent.com/{owner}/{repo}/*/README",
        f"github.com/{owner}/{repo}/raw/*/README.md",
        f"github.com/{owner}/{repo}/blob/*/README.md",
    ]
    captures: list[tuple[str, str]] = []
    for pattern in patterns:
        q = urllib.parse.urlencode({
            "url": pattern,
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype,digest",
            "filter": "statuscode:200",
            "collapse": "digest",
            "limit": str(max(1, limit)),
        })
        r = client.fetch("https://web.archive.org/cdx?" + q, "application/json", timeout=12, retries=0)
        if r["status"] != 200:
            continue
        try:
            rows = json.loads(r["body"])[1:]
        except Exception:
            rows = []
        for row in rows:
            if len(row) >= 2 and row[0] and row[1]:
                captures.append((row[0], row[1]))
    captures = sorted(dict.fromkeys(captures))
    readme_texts, urls, fetched = [], [], []
    for timestamp, original in captures[: max(1, limit)]:
        snap_url = f"https://web.archive.org/web/{timestamp}id_/{original}"
        r = client.fetch(snap_url, "text/plain, text/html;q=0.9, */*;q=0.8", timeout=12, retries=0)
        urls.append(snap_url)
        if r["status"] != 200:
            continue
        body = r.get("body", "")
        text = html_to_text(body) if "<html" in body[:1000].lower() else body
        text = text[:MAX_PUBLIC_TEXT_CHARS]
        if text.strip():
            readme_texts.append(text)
            fetched.append(r.get("fetched_at_utc", ""))
    combined = _join(readme_texts)
    return {
        "text": combined,
        "wayback_readme_first_capture": min([c[0] for c in captures], default=""),
        "wayback_readme_capture_count": str(len(captures)),
        "wayback_readme_urls": _uniq(urls),
        "wayback_readme_fetched_at_utc": _uniq(fetched),
        "evidence_excerpts": " | ".join(evidence_lines(combined)),
    }


def citation_metadata(client: Any, full: str, default_branch: str) -> dict[str, str]:
    texts, files, urls = [], [], []
    for path in metadata_path_candidates(client, full, default_branch):
        item = github_content(client, full, path, default_branch)
        if item.get("text"):
            texts.append(item["text"])
            files.append(path)
        if item.get("url"):
            urls.append(item["url"])
    text = "\n".join(texts)
    clues = paper_clues(text)
    return {
        "text": text,
        "files": _uniq(files),
        "urls": _uniq(urls),
        "paper_title": _uniq([clues["paper_title"], metadata_titles(text)]),
        "paper_authors": metadata_authors(text),
        "publication_links": _uniq(publication_links_from_text(text)),
        "evidence_urls": _uniq([clues["evidence_urls"], *urls, _uniq(publication_links_from_text(text))]),
        "evidence_excerpts": clues["evidence_excerpts"],
    }


def commit_metadata(client: Any, full: str, sha: str) -> dict[str, str]:
    empty = {
        "targeted_commit_author_date": "",
        "targeted_commit_committer_date": "",
        "targeted_commit_author_name": "",
        "targeted_commit_author_login": "",
        "targeted_commit_committer_name": "",
        "targeted_commit_committer_login": "",
        "targeted_commit_url": "",
    }
    if not sha:
        return empty
    r = client.fetch(f"https://api.github.com/repos/{full}/commits/{sha}")
    if r["status"] != 200:
        return empty
    try:
        data = json.loads(r["body"])
        commit = data.get("commit", {})
        author = commit.get("author") or {}
        committer = commit.get("committer") or {}
        empty.update({
            "targeted_commit_author_date": author.get("date", ""),
            "targeted_commit_committer_date": committer.get("date", ""),
            "targeted_commit_author_name": author.get("name", ""),
            "targeted_commit_author_login": (data.get("author") or {}).get("login", ""),
            "targeted_commit_committer_name": committer.get("name", ""),
            "targeted_commit_committer_login": (data.get("committer") or {}).get("login", ""),
            "targeted_commit_url": data.get("html_url", ""),
        })
    except Exception:
        pass
    return empty


def parse_link_last_page(link_header: str) -> int:
    for part in str(link_header or "").split(","):
        if 'rel="last"' not in part:
            continue
        m = re.search(r"[?&]page=(\d+)", part)
        if m:
            return int(m.group(1))
    return 0


def earliest_file_commit(client: Any, full: str, file_path: str, ref: str) -> dict[str, str]:
    empty = {
        "earliest_observed_offending_file_commit_date": "",
        "earliest_observed_offending_file_commit_sha": "",
        "earliest_commit_evidence_url": "",
        "earliest_commit_method": "",
    }
    if not file_path:
        return empty
    params = {"path": file_path, "per_page": "100"}
    if ref:
        params["sha"] = ref
    url = f"https://api.github.com/repos/{full}/commits?" + urllib.parse.urlencode(params)
    r = client.fetch(url)
    if r["status"] != 200:
        return empty
    last_page = parse_link_last_page((r.get("headers") or {}).get("link", ""))
    if last_page and last_page > 1:
        r = client.fetch(url + f"&page={last_page}")
        if r["status"] != 200:
            return empty
    try:
        commits = json.loads(r["body"])
        if not isinstance(commits, list) or not commits:
            return empty
        item = commits[-1]
        commit = item.get("commit", {})
        authored = (commit.get("author") or {}).get("date", "")
        committed = (commit.get("committer") or {}).get("date", "")
        empty.update({
            "earliest_observed_offending_file_commit_date": authored or committed,
            "earliest_observed_offending_file_commit_sha": item.get("sha", ""),
            "earliest_commit_evidence_url": item.get("html_url", ""),
            "earliest_commit_method": "github_commits_path_history",
        })
    except Exception:
        pass
    return empty


def owner_profile(client: Any, login: str) -> dict[str, str]:
    if not login:
        return {"repo_owner_public_name": "", "repo_owner_public_company": ""}
    r = client.fetch(f"https://api.github.com/users/{login}")
    if r["status"] != 200:
        return {"repo_owner_public_name": "", "repo_owner_public_company": ""}
    try:
        data = json.loads(r["body"])
        return {"repo_owner_public_name": data.get("name", "") or "", "repo_owner_public_company": data.get("company", "") or ""}
    except Exception:
        return {"repo_owner_public_name": "", "repo_owner_public_company": ""}


def repo_enrich(client: Any, targets: list[dict[str, str]], wayback_limit: int) -> list[dict[str, str]]:
    meta_cache, way_cache, readme_cache, paper_cache, owner_cache, citation_cache, commit_cache, history_cache, wayback_readme_cache, package_cache, rows = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, []
    for t in targets:
        url, full = t["repo_url"], f"{t['repo_owner']}/{t['repo_name']}"
        if url not in meta_cache:
            r = client.fetch(f"https://api.github.com/repos/{full}")
            meta_cache[url] = {
                "status": "live" if r["status"] == 200 else ("not_found_or_removed" if r["status"] == 404 else f"http_{r['status']}"),
                "data": json.loads(r["body"]) if r["status"] == 200 else {},
            }
        meta, api = meta_cache[url], meta_cache[url]["data"]
        if url not in way_cache:
            way_cache[url] = base.wayback(client, url, wayback_limit)
        way = way_cache[url]
        source = (api.get("source") or {}).get("full_name") or (api.get("parent") or {}).get("full_name") or full
        role = "fork" if api.get("fork") else ("mirror" if "mirror" in (api.get("description") or "").lower() else "unknown")
        if not api and re.search(r"forked repository", _join(t.values(), " "), re.I):
            role = "fork"
        lineage = "lineage_" + base.slug(source.replace("/", "_"))
        lineage_link_method = "github_api_source" if api.get("source") else ("github_api_parent" if api.get("parent") else "self_repository")
        lineage_confidence = "high" if api.get("source") or api.get("parent") else "medium"
        lineage_link_evidence = source

        readmes = []
        citation = {
            "text": "",
            "files": "",
            "urls": "",
            "paper_title": "",
            "paper_authors": "",
            "publication_links": "",
            "evidence_urls": "",
            "evidence_excerpts": "",
        }
        if api:
            for readme_full in dict.fromkeys([full, source]):
                if readme_full not in readme_cache:
                    readme_cache[readme_full] = repo_readme(client, readme_full)
                readmes.append(readme_cache[readme_full])
            default_branch = api.get("default_branch", "")
            if (full, default_branch) not in citation_cache:
                citation_cache[(full, default_branch)] = citation_metadata(client, full, default_branch)
            citation = citation_cache[(full, default_branch)]

        pre_package_text = _join([
            api.get("description"),
            api.get("homepage"),
            _join(api.get("topics", []), " "),
            *(x.get("text", "") for x in readmes),
            citation.get("text", ""),
            t.get("direct_app_ids", ""),
        ])
        wayback_meta = {
            "text": "",
            "wayback_readme_first_capture": "",
            "wayback_readme_capture_count": "0",
            "wayback_readme_urls": "",
            "wayback_readme_fetched_at_utc": "",
            "evidence_excerpts": "",
        }
        if (not api or not pre_package_text.strip()) and wayback_limit > 0:
            if url not in wayback_readme_cache:
                wayback_readme_cache[url] = wayback_readme(client, url, wayback_limit)
            wayback_meta = wayback_readme_cache[url]
            pre_package_text = _join([pre_package_text, wayback_meta.get("text", "")])
        package_key = (full, citation.get("files", ""), pre_package_text)
        if package_key not in package_cache:
            package_cache[package_key] = public_package_metadata(client, pre_package_text, citation.get("files", ""))
        package_meta = package_cache[package_key]
        public_text = _join([pre_package_text, package_meta.get("text", "")])
        ids = identifiers(public_text)
        all_doi = [x for x in _uniq([t.get("doi", ""), *ids["doi"]]).split("; ") if x]
        all_pmid = [x for x in _uniq([t.get("pubmed_id", ""), *ids["pubmed_id"]]).split("; ") if x]
        clues = paper_clues(public_text)
        paper_titles = [
            clues["paper_title"],
            citation.get("paper_title", ""),
            package_meta.get("paper_title", ""),
            wayback_meta.get("paper_title", ""),
        ]
        paper_authors = [citation.get("paper_authors", ""), package_meta.get("paper_authors", "")]
        paper_urls = [
            clues["evidence_urls"],
            citation.get("evidence_urls", ""),
            citation.get("publication_links", ""),
            package_meta.get("urls", ""),
            package_meta.get("publication_links", ""),
        ]
        for doi in all_doi[:5]:
            key = ("doi", doi)
            if key not in paper_cache:
                paper_cache[key] = crossref_work(client, doi)
            paper_titles.append(paper_cache[key].get("paper_title", ""))
            paper_authors.append(paper_cache[key].get("paper_authors", ""))
            paper_urls.append(paper_cache[key].get("evidence_urls", ""))
        for pmid in all_pmid[:5]:
            key = ("pmid", pmid)
            if key not in paper_cache:
                paper_cache[key] = pubmed_summary(client, pmid)
            pmeta = paper_cache[key]
            paper_titles.append(pmeta.get("paper_title", ""))
            paper_authors.append(pmeta.get("paper_authors", ""))
            paper_urls.append(pmeta.get("evidence_urls", ""))
            if pmeta.get("doi") and pmeta["doi"] not in all_doi:
                all_doi.append(pmeta["doi"])

        owner_login = (api.get("owner") or {}).get("login", "") if api else ""
        if owner_login and owner_login not in owner_cache:
            owner_cache[owner_login] = owner_profile(client, owner_login)
        owner_public = owner_cache.get(owner_login, {"repo_owner_public_name": "", "repo_owner_public_company": ""})

        target_sha = t.get("target_commit_sha", "")
        if target_sha and (full, target_sha) not in commit_cache:
            commit_cache[(full, target_sha)] = commit_metadata(client, full, target_sha)
        commit = commit_cache.get((full, target_sha), empty_commit_metadata())

        hist_ref = target_sha or t.get("target_ref", "") or api.get("default_branch", "")
        hist_key = (full, t.get("offending_file_path", ""), hist_ref)
        if api and hist_key not in history_cache:
            history_cache[hist_key] = earliest_file_commit(client, full, t.get("offending_file_path", ""), hist_ref)
        history = history_cache.get(hist_key, empty_history_metadata())

        row = {f: "" for f in base.REPO_FIELDS}
        paper_title, paper_author = _uniq(paper_titles), _uniq(paper_authors)
        row.update({
            **{k: t.get(k, "") for k in ["notice_id", "notice_date", "notice_path", "repo_url", "repo_owner", "repo_name", "target_ref", "target_commit_sha", "offending_file_path", "offending_file_name", "target_scope", "alleged_data_type"]},
            "repo_status": meta["status"],
            "lineage_id": lineage,
            "repo_role": role,
            "parent_or_source_repo": source if source != full else "",
            "first_observed_repo_date": api.get("created_at", "") or way["wayback_first_capture"],
            "first_observed_offending_commit_date": history.get("earliest_observed_offending_file_commit_date", ""),
            **commit,
            **history,
            "removal_or_disable_date": t.get("notice_date", "") if meta["status"] != "live" else "",
            "github_repo_id": str(api.get("id", "")),
            "github_created_at": api.get("created_at", ""),
            "github_updated_at": api.get("updated_at", ""),
            "github_pushed_at": api.get("pushed_at", ""),
            "github_archived": str(bool(api.get("archived"))).lower() if api else "",
            "github_default_branch": api.get("default_branch", ""),
            "github_fork": str(bool(api.get("fork"))).lower() if api else "",
            "github_parent": (api.get("parent") or {}).get("full_name", ""),
            "github_source": (api.get("source") or {}).get("full_name", ""),
            "repository_description": api.get("description", ""),
            "repository_homepage": api.get("homepage", ""),
            "repository_topics": _uniq(api.get("topics", [])),
            "repo_owner_login": owner_login,
            **owner_public,
            "citation_metadata_files": citation.get("files", ""),
            "repository_readme_urls": _uniq(x.get("url", "") for x in readmes),
            "citation_metadata_urls": citation.get("urls", ""),
            "metadata_publication_links": _uniq([citation.get("publication_links", ""), package_meta.get("publication_links", "")]),
            "package_metadata_sources": package_meta.get("sources", ""),
            "package_metadata_urls": package_meta.get("urls", ""),
            "wayback_first_capture": way["wayback_first_capture"],
            "wayback_capture_count": way["wayback_capture_count"],
            "wayback_readme_first_capture": wayback_meta.get("wayback_readme_first_capture", ""),
            "wayback_readme_capture_count": wayback_meta.get("wayback_readme_capture_count", "0"),
            "wayback_readme_urls": wayback_meta.get("wayback_readme_urls", ""),
            "wayback_readme_fetched_at_utc": wayback_meta.get("wayback_readme_fetched_at_utc", ""),
            "lineage_link_method": lineage_link_method,
            "lineage_link_evidence": lineage_link_evidence,
            "lineage_confidence": lineage_confidence,
            "paper_title": paper_title,
            "paper_authors": paper_author,
            "doi": _uniq(all_doi),
            "pubmed_id": _uniq(all_pmid),
            "repo_linked_doi": _uniq(all_doi),
            "repo_linked_pmid": _uniq(all_pmid),
            "repo_linked_publication_title": paper_title,
            "evidence_urls": _uniq([t.get("notice_url", ""), t.get("source_url", ""), url, _uniq(x.get("url", "") for x in readmes), citation.get("urls", ""), way.get("wayback_urls", ""), wayback_meta.get("wayback_readme_urls", ""), package_meta.get("urls", ""), package_meta.get("publication_links", ""), commit.get("targeted_commit_url", ""), history.get("earliest_commit_evidence_url", ""), *paper_urls]),
            "uploader_attribution": "target repository owner/uploader only; not attributed to the UKB application team without independent evidence",
            "manual_review_needed": "true",
            "evidence_file": f"evidence/lineages/{lineage}.md",
            "_text": _join([url, full, t.get("offending_file_path", ""), t.get("alleged_data_type", ""), api.get("description"), owner_public.get("repo_owner_public_name", ""), owner_public.get("repo_owner_public_company", ""), commit.get("targeted_commit_author_name", ""), paper_title, paper_author, public_text]),
            "_repo_text": _join([url, full, t.get("offending_file_path", ""), t.get("alleged_data_type", ""), api.get("description"), api.get("homepage"), _join(api.get("topics", []), " "), owner_public.get("repo_owner_public_name", ""), owner_public.get("repo_owner_public_company", "")]),
            "_paper_text": _join([paper_title, paper_author, _uniq(all_doi), _uniq(all_pmid)]),
            "_readme_text": public_text,
            "_evidence_excerpts": _uniq([clues["evidence_excerpts"], citation.get("evidence_excerpts", ""), package_meta.get("evidence_excerpts", ""), wayback_meta.get("evidence_excerpts", "")]),
            "_direct_app_ids": _uniq([t.get("direct_app_ids", ""), *ids["app_id"]]),
        })
        rows.append(row)
    return rows


def make_lineages(repo_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups = defaultdict(list)
    for r in repo_rows:
        groups[r["lineage_id"]].append(r)
    out = []
    for lid, rows in sorted(groups.items()):
        row = {f: "" for f in base.LINEAGE_FIELDS}
        row.update({
            "lineage_id": lid,
            "source_repo": _uniq(r.get("parent_or_source_repo") or f"{r['repo_owner']}/{r['repo_name']}" for r in rows),
            "repo_urls": _uniq(r["repo_url"] for r in rows),
            "repo_count": str(len({r["repo_url"].lower() for r in rows})),
            "notice_ids": _uniq(r["notice_id"] for r in rows),
            "notice_count": str(len({r["notice_id"] for r in rows})),
            "repo_roles": _uniq(r["repo_role"] for r in rows),
            "parent_or_source_repos": _uniq(r["parent_or_source_repo"] for r in rows),
            "target_ref": _uniq(r.get("target_ref", "") for r in rows),
            "target_commit_sha": _uniq(r.get("target_commit_sha", "") for r in rows),
            "first_observed_repo_date": earliest(rows, "first_observed_repo_date"),
            "first_observed_offending_commit_date": earliest(rows, "first_observed_offending_commit_date"),
            "targeted_commit_author_date": earliest(rows, "targeted_commit_author_date"),
            "targeted_commit_committer_date": earliest(rows, "targeted_commit_committer_date"),
            "earliest_observed_offending_file_commit_date": earliest(rows, "earliest_observed_offending_file_commit_date"),
            "earliest_observed_offending_file_commit_sha": _uniq(r.get("earliest_observed_offending_file_commit_sha", "") for r in rows),
            "earliest_commit_method": _uniq(r.get("earliest_commit_method", "") for r in rows),
            "removal_or_disable_date": earliest(rows, "removal_or_disable_date"),
            "alleged_data_types": _uniq(r["alleged_data_type"] for r in rows),
            "github_created_at": earliest(rows, "github_created_at"),
            "github_updated_at": latest(rows, "github_updated_at"),
            "github_pushed_at": latest(rows, "github_pushed_at"),
            "github_archived": _uniq(r.get("github_archived", "") for r in rows),
            "github_default_branch": _uniq(r.get("github_default_branch", "") for r in rows),
            "github_fork": _uniq(r.get("github_fork", "") for r in rows),
            "github_parent": _uniq(r.get("github_parent", "") for r in rows),
            "github_source": _uniq(r.get("github_source", "") for r in rows),
            "repository_description": _uniq(r.get("repository_description", "") for r in rows),
            "repository_homepage": _uniq(r.get("repository_homepage", "") for r in rows),
            "repository_topics": _uniq(r.get("repository_topics", "") for r in rows),
            "repo_owner_login": _uniq(r.get("repo_owner_login", "") for r in rows),
            "repo_owner_public_name": _uniq(r.get("repo_owner_public_name", "") for r in rows),
            "repo_owner_public_company": _uniq(r.get("repo_owner_public_company", "") for r in rows),
            "citation_metadata_files": _uniq(r.get("citation_metadata_files", "") for r in rows),
            "repository_readme_urls": _uniq(r.get("repository_readme_urls", "") for r in rows),
            "citation_metadata_urls": _uniq(r.get("citation_metadata_urls", "") for r in rows),
            "metadata_publication_links": _uniq(r.get("metadata_publication_links", "") for r in rows),
            "package_metadata_sources": _uniq(r.get("package_metadata_sources", "") for r in rows),
            "package_metadata_urls": _uniq(r.get("package_metadata_urls", "") for r in rows),
            "wayback_first_capture": earliest(rows, "wayback_first_capture"),
            "wayback_capture_count": str(sum(int(r.get("wayback_capture_count") or 0) for r in rows if str(r.get("wayback_capture_count") or "0").isdigit())),
            "wayback_readme_first_capture": earliest(rows, "wayback_readme_first_capture"),
            "wayback_readme_capture_count": str(sum(int(r.get("wayback_readme_capture_count") or 0) for r in rows if str(r.get("wayback_readme_capture_count") or "0").isdigit())),
            "wayback_readme_urls": _uniq(r.get("wayback_readme_urls", "") for r in rows),
            "wayback_readme_fetched_at_utc": _uniq(r.get("wayback_readme_fetched_at_utc", "") for r in rows),
            "lineage_link_method": _uniq(r.get("lineage_link_method", "") for r in rows),
            "lineage_link_evidence": _uniq(r.get("lineage_link_evidence", "") for r in rows),
            "lineage_confidence": "high" if any(r.get("lineage_confidence") == "high" for r in rows) else _uniq(r.get("lineage_confidence", "") for r in rows),
            "doi": _uniq(r["doi"] for r in rows),
            "pubmed_id": _uniq(r["pubmed_id"] for r in rows),
            "paper_title": _uniq(r["paper_title"] for r in rows),
            "paper_authors": _uniq(r["paper_authors"] for r in rows),
            "repo_linked_doi": _uniq(r.get("repo_linked_doi", "") for r in rows),
            "repo_linked_pmid": _uniq(r.get("repo_linked_pmid", "") for r in rows),
            "repo_linked_publication_title": _uniq(r.get("repo_linked_publication_title", "") for r in rows),
            "crosswalk_pub_ids": _uniq(r.get("crosswalk_pub_ids", "") for r in rows),
            "crosswalk_app_ids": _uniq(r.get("crosswalk_app_ids", "") for r in rows),
            "crosswalk_application_count": _uniq(r.get("crosswalk_application_count", "") for r in rows),
            "crosswalk_identifier_type": _uniq(r.get("crosswalk_identifier_type", "") for r in rows),
            "crosswalk_evidence": _uniq(r.get("crosswalk_evidence", "") for r in rows),
            "evidence_urls": _uniq(r["evidence_urls"] for r in rows),
            "manual_review_needed": "true",
            "evidence_file": f"evidence/lineages/{lid}.md",
            "_text": _join(r.get("_text", "") for r in rows),
            "_direct_app_ids": _uniq(r.get("_direct_app_ids", "") for r in rows),
            "_repo_text": _join(r.get("_repo_text", "") for r in rows),
            "_paper_text": _join(r.get("_paper_text", "") for r in rows),
            "_readme_text": _join(r.get("_readme_text", "") for r in rows),
            "_evidence_excerpts": _uniq(r.get("_evidence_excerpts", "") for r in rows),
        })
        out.append(row)
    return out


def score(lineage: dict[str, str], app: dict[str, Any]) -> tuple[float, list[str], dict[str, Any], str]:
    repo_ev = text_tokens(lineage.get("_repo_text", ""))
    paper_ev = text_tokens(lineage.get("_paper_text", ""))
    readme_ev = text_tokens(lineage.get("_readme_text", ""))
    app_title_ev = text_tokens(app.get("title", ""))
    app_inst_ev = text_tokens(app.get("institution", ""))
    app_notes_ev = text_tokens(app.get("notes", ""))
    direct = {x.strip() for x in lineage.get("_direct_app_ids", "").split(";") if x.strip()}
    comps, details, total, level = [], {}, 0.0, "C"
    if app["app_id"] in direct:
        return 100.0, ["direct_application_id"], {"evidence_class": "A1_DIRECT_APP_ID", "direct_application_id": app["app_id"]}, "A"

    crosswalk_apps = set(parts(lineage.get("crosswalk_app_ids", "")))
    crosswalk_classes = []
    if app["app_id"] in crosswalk_apps:
        id_types = set(parts(lineage.get("crosswalk_identifier_type", "")))
        if "doi" in id_types:
            crosswalk_classes.append("A2_DOI_UKB_CROSSWALK")
        if "pmid" in id_types:
            crosswalk_classes.append("A3_PMID_UKB_CROSSWALK")
        if not crosswalk_classes:
            crosswalk_classes.append("A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN")
        count = int(lineage.get("crosswalk_application_count") or len(crosswalk_apps) or 0)
        total += 96.0 if count == 1 else 84.0
        comps.extend(crosswalk_classes)
        details["crosswalk"] = {
            "pub_ids": lineage.get("crosswalk_pub_ids", ""),
            "app_ids": lineage.get("crosswalk_app_ids", ""),
            "application_count": lineage.get("crosswalk_application_count", ""),
            "identifier_type": lineage.get("crosswalk_identifier_type", ""),
        }
        level = "A"

    lineage_ids = {
        "doi": [x for x in dict.fromkeys(normalize_doi(v) for v in [*parts(lineage.get("repo_linked_doi", "")), *parts(lineage.get("doi", ""))]) if x],
        "pubmed_id": [x for x in dict.fromkeys(normalize_pmid(v) for v in [*parts(lineage.get("repo_linked_pmid", "")), *parts(lineage.get("pubmed_id", ""))]) if x],
    }
    app_ids = identifiers(_join([app.get("title", ""), app.get("notes", "")]))
    doi_hits = sorted(set(lineage_ids["doi"]) & set(app_ids["doi"]))
    pmid_hits = sorted(set(lineage_ids["pubmed_id"]) & set(app_ids["pubmed_id"]))
    if doi_hits:
        total += 45.0
        comps.append("application_note_doi")
        details["application_note_doi"] = doi_hits[:5]
    if pmid_hits:
        total += 45.0
        comps.append("application_note_pubmed_id")
        details["application_note_pubmed_id"] = pmid_hits[:5]

    app_notes_norm = normalized_title(_join([app.get("title", ""), app.get("notes", "")]))
    repo_titles = parts(_uniq([lineage.get("repo_linked_publication_title", ""), lineage.get("paper_title", "")]))
    exact_titles, fuzzy_titles = [], []
    for title in repo_titles:
        title_norm = normalized_title(title)
        if len(title_norm) < 25:
            continue
        title_tokens = text_tokens(title)
        if title_norm and title_norm in app_notes_norm:
            exact_titles.append(title[:240])
        elif title_tokens:
            overlap = title_tokens & (app_title_ev | app_notes_ev)
            if len(overlap) >= 5 and len(overlap) / max(1, len(title_tokens)) >= 0.55:
                fuzzy_titles.append(title[:240])
    if exact_titles:
        total += 30.0
        comps.append("exact_publication_title")
        details["exact_publication_title"] = exact_titles[:5]
    elif fuzzy_titles:
        total += 18.0
        comps.append("normalized_publication_title")
        details["normalized_publication_title"] = fuzzy_titles[:5]

    paper_title = app_title_ev & paper_ev
    if paper_title:
        total += min(22.0, 22.0 * len(paper_title) / max(3, len(app_title_ev)))
        comps.append("application_title_topic_overlap")
        details["application_title_topic_tokens"] = sorted(paper_title)[:20]
    readme_title = app_title_ev & readme_ev
    if readme_title:
        total += min(16.0, 16.0 * len(readme_title) / max(3, len(app_title_ev)))
        comps.append("readme_title_topic")
        details["readme_title_tokens"] = sorted(readme_title)[:20]
    repo_title = app_title_ev & repo_ev
    if repo_title:
        total += min(8.0, 8.0 * len(repo_title) / max(3, len(app_title_ev)))
        comps.append("repo_path_similarity")
        details["repo_path_tokens"] = sorted(repo_title)[:10]

    paper_authors = _join([lineage.get("paper_authors", ""), lineage.get("_paper_text", ""), lineage.get("_readme_text", "")])
    if name_in_text(app.get("pi", ""), paper_authors):
        total += 22.0
        comps.append("paper_author_to_application_pi")
        details["paper_author_to_application_pi"] = app.get("pi", "")
    owner_text = _join([lineage.get("repo_owner_public_name", ""), lineage.get("repo_owner_login", "")])
    if owner_text and paper_authors and name_in_text(owner_text, paper_authors):
        total += 12.0
        comps.append("repo_owner_to_paper_author")
        details["repo_owner_to_paper_author"] = owner_text
    commit_text = lineage.get("_text", "")
    if paper_authors and any(name_in_text(name, paper_authors) for name in re.findall(r"[A-Z][A-Za-z.-]+ [A-Z][A-Za-z.-]+", commit_text)[:8]):
        total += 10.0
        comps.append("commit_author_to_paper_author")
    inst = app_inst_ev & (readme_ev | paper_ev | text_tokens(lineage.get("repo_owner_public_company", "")))
    if inst:
        total += min(14.0, 5.0 * len(inst))
        comps.append("institution_match")
        details["institution_tokens"] = sorted(inst)[:10]
    notes = app_notes_ev & (paper_ev | readme_ev)
    if notes:
        total += min(12.0, 1.2 * len(notes))
        comps.append("application_notes_topic_overlap")
        details["application_notes_tokens"] = sorted(notes)[:20]
    if (lineage.get("doi") or lineage.get("pubmed_id")) and any(c in comps for c in ["exact_publication_title", "normalized_publication_title", "paper_author_to_application_pi", "readme_title_topic"]):
        total += 8.0
        comps.append("paper_identifier")
        details["paper_identifiers"] = {"doi": lineage.get("doi", ""), "pubmed_id": lineage.get("pubmed_id", "")}
    dts = [x for x in lineage.get("alleged_data_types", "").split("; ") if x]
    app_text = (app["title"] + " " + app["notes"]).lower()
    hit = [dt for dt in dts if any(p in app_text for p in base.DATA_TYPES.get(dt, [dt]))]
    if hit:
        total += min(8.0, 4.0 * len(hit))
        comps.append("data_type")
        details["data_types"] = hit
    b_components = {c for c in comps if component_strength(c)[1] == "B"}
    if any(c.startswith("A") for c in comps):
        level = "A"
    elif "paper_identifier" in comps and len(b_components) >= 2:
        level = "B"
    elif total >= 55 and len(b_components) >= 2:
        level = "B"
    details["evidence_class"] = _uniq([c for c in comps if c.startswith("A")]) or level
    return round(min(100.0, total), 2), sorted(set(comps)), details, level


def final_label(top: dict[str, Any] | None, second: dict[str, Any] | None, direct: list[str]) -> tuple[str, str, bool]:
    if not top:
        return "unresolved", "No candidate application exceeded the evidence threshold.", True
    if len(direct) == 1 and top["candidate_app_id"] == direct[0]:
        return "confirmed", "Direct UK Biobank application ID appears in repository/notice evidence.", False
    if len(direct) > 1:
        return "ambiguous", "Multiple direct UK Biobank application IDs appear in evidence.", True
    s, s2 = float(top["match_score"]), float(second["match_score"]) if second else 0.0
    comps = [x for x in top.get("evidence_components", "").split("; ") if x]
    deterministic = [x for x in comps if x.startswith("A")]
    b_components = [x for x in comps if component_strength(x)[1] == "B"]
    weak_only = all(component_strength(x)[1] == "C" for x in comps)
    crosswalk_count = int(top.get("crosswalk_application_count") or 0)
    if deterministic and crosswalk_count == 1:
        return "confirmed", "A repository-linked DOI/PMID maps through UKB Schema 19/24 to a unique application.", False
    if deterministic and crosswalk_count > 1:
        if s >= 92 and len(set(b_components)) >= 2 and s - s2 >= 12:
            return "probable", "UKB publication crosswalk maps to multiple applications, but independent identity/context evidence favors this one.", True
        return "ambiguous", "UKB publication crosswalk maps this repository-linked publication to multiple applications.", True
    if s >= 78 and len(set(b_components)) >= 3 and s - s2 >= 15:
        return "probable", "Several independent publication, identity, and context components support this unique candidate.", True
    if s >= 68 and {"application_note_doi", "exact_publication_title"} & set(comps) and len(set(b_components)) >= 2 and s - s2 >= 12:
        return "probable", "Repository-linked publication identifiers or title evidence plus independent context support this candidate.", True
    if s >= 45 and second and s2 >= s - 10:
        return "ambiguous", "Two or more candidate applications have similar evidence scores.", True
    if s >= 50 and not weak_only and len(set(b_components)) >= 2:
        return "ambiguous", "Evidence is suggestive but lacks enough independent support for a unique probable match.", True
    return "unresolved", "Evidence is too generic to assign an application.", True


def match_evidence_rows(candidates: list[dict[str, str]], final: dict[str, dict[str, Any]], lineages: list[dict[str, str]]) -> list[dict[str, str]]:
    lineage_by_id = {l["lineage_id"]: l for l in lineages}
    rows = []
    for c in candidates:
        lineage_id = c.get("lineage_id", "")
        app_id = c.get("candidate_app_id", "")
        if not app_id:
            continue
        lin = lineage_by_id.get(lineage_id, {})
        try:
            details = json.loads(c.get("score_details", "{}"))
        except json.JSONDecodeError:
            details = {}
        for comp in [x.strip() for x in c.get("evidence_components", "").split(";") if x.strip()]:
            det, strength = component_strength(comp)
            if comp == "direct_application_id":
                source = "DMCA notice text or public repository metadata"
                value = details.get("direct_application_id", app_id)
            elif comp.startswith("A"):
                source = "UKB Schema 19/24 publication-application crosswalk"
                value = details.get("crosswalk", lin.get("crosswalk_evidence", ""))
            elif comp.startswith("application_note_"):
                source = "UKB approved application title/notes"
                value = details.get(comp, details)
            elif "author" in comp or "institution" in comp or "owner" in comp:
                source = "Public repository, publication, and UKB application metadata"
                value = details.get(comp, details)
            else:
                source = "Automated public-text comparison"
                value = details.get(comp, details)
            rows.append({
                "lineage_id": lineage_id,
                "candidate_app_id": app_id,
                "evidence_class": c.get("evidence_class", ""),
                "evidence_type": comp,
                "evidence_value": json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value),
                "evidence_source": source,
                "evidence_url": c.get("crosswalk_evidence", "") if comp.startswith("A") else c.get("evidence_urls", ""),
                "deterministic_or_fuzzy": det,
                "strength_level": strength,
            })
    return rows


def write_evidence(out: Path, notices: list[dict[str, str]], notice_text: dict[str, str], lineages: list[dict[str, str]], repos: list[dict[str, str]], cands: list[dict[str, str]], final: dict[str, dict[str, Any]]) -> None:
    (out / "evidence/notices").mkdir(parents=True, exist_ok=True)
    (out / "evidence/lineages").mkdir(parents=True, exist_ok=True)
    for n in notices:
        (out / f"evidence/notices/{base.slug(n['notice_id'])}.md").write_text(
            f"# {n['notice_id']}\n\n- notice_path: {n['notice_path']}\n- notice_url: {n['notice_url']}\n- fetched_at_utc: {n['fetched_at_utc']}\n\n## Public Notice Text\n\n{notice_text.get(n['notice_path'], '')}\n",
            encoding="utf-8",
        )
    by_l, cand_l = defaultdict(list), defaultdict(list)
    for r in repos:
        by_l[r["lineage_id"]].append(r)
    for c in cands:
        cand_l[c["lineage_id"]].append(c)
    for lin in lineages:
        lines = [
            f"# {lin['lineage_id']}",
            "",
            "A match means only that public evidence links a UKB application to this DMCA-targeted repository lineage. It does not establish wrongdoing by the PI, institution, or application team.",
            "",
            f"- source_repo: {lin['source_repo']}",
            f"- repo_urls: {lin['repo_urls']}",
            f"- notice_ids: {lin['notice_ids']}",
            f"- final_match_grade: {final.get(lin['lineage_id'], {}).get('grade', '')}",
            f"- lineage_link_method: {lin.get('lineage_link_method', '')}",
            f"- lineage_confidence: {lin.get('lineage_confidence', '')}",
            f"- target_commit_sha: {lin.get('target_commit_sha', '')}",
            f"- targeted_commit_author_date: {lin.get('targeted_commit_author_date', '')}",
            f"- targeted_commit_committer_date: {lin.get('targeted_commit_committer_date', '')}",
            f"- earliest_observed_offending_file_commit_date: {lin.get('earliest_observed_offending_file_commit_date', '')}",
            f"- earliest_observed_offending_file_commit_sha: {lin.get('earliest_observed_offending_file_commit_sha', '')}",
            f"- paper_title: {lin.get('paper_title', '')}",
            f"- doi: {lin.get('doi', '')}",
            f"- pubmed_id: {lin.get('pubmed_id', '')}",
            f"- paper_authors: {lin.get('paper_authors', '')}",
            f"- citation_metadata_files: {lin.get('citation_metadata_files', '')}",
            f"- metadata_publication_links: {lin.get('metadata_publication_links', '')}",
            f"- package_metadata_sources: {lin.get('package_metadata_sources', '')}",
            f"- package_metadata_urls: {lin.get('package_metadata_urls', '')}",
            f"- wayback_readme_first_capture: {lin.get('wayback_readme_first_capture', '')}",
            f"- wayback_readme_capture_count: {lin.get('wayback_readme_capture_count', '')}",
            f"- wayback_readme_urls: {lin.get('wayback_readme_urls', '')}",
            f"- crosswalk_pub_ids: {lin.get('crosswalk_pub_ids', '')}",
            f"- crosswalk_app_ids: {lin.get('crosswalk_app_ids', '')}",
            f"- crosswalk_application_count: {lin.get('crosswalk_application_count', '')}",
            f"- crosswalk_identifier_type: {lin.get('crosswalk_identifier_type', '')}",
            "",
            "## Repository Evidence",
        ]
        for r in by_l[lin["lineage_id"]]:
            lines += [
                "",
                f"### {r['repo_url']}",
                f"- repo_status: {r['repo_status']}",
                f"- repo_role: {r['repo_role']}",
                f"- parent_or_source_repo: {r.get('parent_or_source_repo', '')}",
                f"- offending_file_path: {r['offending_file_path']}",
                f"- target_ref: {r.get('target_ref', '')}",
                f"- target_commit_sha: {r.get('target_commit_sha', '')}",
                f"- targeted_commit_author_date: {r.get('targeted_commit_author_date', '')}",
                f"- targeted_commit_committer_date: {r.get('targeted_commit_committer_date', '')}",
                f"- earliest_observed_offending_file_commit_date: {r.get('earliest_observed_offending_file_commit_date', '')}",
                f"- github_created_at: {r.get('github_created_at', '')}",
                f"- github_pushed_at: {r.get('github_pushed_at', '')}",
                f"- github_fork: {r.get('github_fork', '')}",
                f"- github_parent: {r.get('github_parent', '')}",
                f"- github_source: {r.get('github_source', '')}",
                f"- repo_owner_public_name: {r.get('repo_owner_public_name', '')}",
                f"- repo_owner_public_company: {r.get('repo_owner_public_company', '')}",
                f"- citation_metadata_files: {r.get('citation_metadata_files', '')}",
                f"- repository_readme_urls: {r.get('repository_readme_urls', '')}",
                f"- citation_metadata_urls: {r.get('citation_metadata_urls', '')}",
                f"- metadata_publication_links: {r.get('metadata_publication_links', '')}",
                f"- package_metadata_sources: {r.get('package_metadata_sources', '')}",
                f"- package_metadata_urls: {r.get('package_metadata_urls', '')}",
                f"- wayback_first_capture: {r.get('wayback_first_capture', '')}",
                f"- wayback_capture_count: {r.get('wayback_capture_count', '')}",
                f"- wayback_readme_first_capture: {r.get('wayback_readme_first_capture', '')}",
                f"- wayback_readme_capture_count: {r.get('wayback_readme_capture_count', '')}",
                f"- wayback_readme_urls: {r.get('wayback_readme_urls', '')}",
                f"- evidence_urls: {r['evidence_urls']}",
            ]
            if r.get("_evidence_excerpts"):
                lines.append(f"- public_metadata_excerpts: {r['_evidence_excerpts']}")
        lines += ["", "## Application Candidates"]
        for c in cand_l[lin["lineage_id"]][:10]:
            lines.append(
                f"- rank {c.get('candidate_rank', '')}: app_id={c.get('candidate_app_id', '')}; "
                f"score={c.get('match_score', '')}; grade={c.get('match_grade', '')}; "
                f"evidence_class={c.get('evidence_class', '')}; components={c.get('evidence_components', '')}; "
                f"title={c.get('application_title', '')}; reason={c.get('match_reason', '')}"
            )
            if c.get("score_details") and c.get("score_details") != "{}":
                lines.append(f"  - score_details: `{c.get('score_details')}`")
        (out / f"evidence/lineages/{lin['lineage_id']}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def install_enrichment() -> None:
    base.identifiers = identifiers
    base.load_publication_crosswalk = load_publication_crosswalk
    base.apply_publication_crosswalk = apply_publication_crosswalk
    base.match_evidence_rows = match_evidence_rows
    base.repo_enrich = repo_enrich
    base.make_lineages = make_lineages
    base.score = score
    base.final_label = final_label
    base.write_evidence = write_evidence


def main(argv: list[str] | None = None) -> int:
    install_enrichment()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
