#!/usr/bin/env python3
"""Public metadata enrichment helpers for UKB DMCA application matching.

This module deliberately reads only repository metadata, README/citation-like
files, archival README snapshots, and public package/archive metadata. It does
not fetch files named in DMCA notices as alleged participant-level data.
"""

from __future__ import annotations

import base64
import html
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Iterable

MAX_TEXT_CHARS = 200_000
MAX_METADATA_FILE_BYTES = 250_000
METADATA_TREE_LIMIT = 25
DIRECT_PACKAGE_LOOKUP_LIMIT = 4
EXACT_RECORD_LOOKUP_LIMIT = 5
METADATA_BASENAMES = {
    ".zenodo.json",
    "citation.bib",
    "citation.cff",
    "codemeta.json",
    "description",
    "package.json",
    "pyproject.toml",
}
EXTRA_REPO_FIELDS = [
    "repository_readme_urls",
    "citation_metadata_urls",
    "metadata_publication_links",
    "package_metadata_sources",
    "package_metadata_urls",
    "public_record_metadata_sources",
    "public_record_metadata_urls",
    "wayback_readme_first_capture",
    "wayback_readme_capture_count",
    "wayback_readme_urls",
    "wayback_readme_fetched_at_utc",
]
EXTRA_LINEAGE_FIELDS = EXTRA_REPO_FIELDS

PUBLICATION_URL = re.compile(
    r"https?://[^\s\])<>'\"]*(?:doi\.org|pubmed|ncbi\.nlm\.nih\.gov|europepmc|"
    r"nature\.com/articles|science\.org/doi|thelancet|jamanetwork|nejm|"
    r"medrxiv|biorxiv|arxiv|zenodo\.org|pypi\.org/project|cran\.r-project\.org|r-project\.org/package=)[^\s\])<>'\"]*",
    re.I,
)
ZENODO_RECORD_URL = re.compile(r"https?://(?:www\.)?zenodo\.org/(?:record|records)/(\d+)", re.I)
PYPI_PROJECT_URL = re.compile(r"https?://pypi\.org/project/([A-Za-z0-9_.-]+)", re.I)
CRAN_PACKAGE_URL = re.compile(
    r"https?://(?:cran\.r-project\.org/(?:web/packages|package=)|.*?r-project\.org/package=)([A-Za-z0-9_.-]+)",
    re.I,
)
GENERIC_PACKAGE_NAMES = {
    "001",
    "analysis",
    "biobank",
    "code",
    "data",
    "dataset",
    "example",
    "examples",
    "gwas",
    "phenotype",
    "project",
    "repo",
    "test",
    "ukb",
    "ukbb",
    "ukbiobank",
}


def extend_fields(base: Any) -> None:
    for field in EXTRA_REPO_FIELDS:
        if field not in base.REPO_FIELDS:
            base.REPO_FIELDS.append(field)
    for field in EXTRA_LINEAGE_FIELDS:
        if field not in base.LINEAGE_FIELDS:
            base.LINEAGE_FIELDS.append(field)


def _uniq(values: Iterable[Any]) -> str:
    out, seen = [], set()
    for value in values:
        for part in str(value or "").split(";"):
            text = part.strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)
    return "; ".join(out)


def _join(values: Iterable[Any], sep: str = "\n") -> str:
    return sep.join(str(v) for v in values if v)


def _json(body: str) -> Any:
    try:
        return json.loads(body or "{}")
    except Exception:
        return {}


def _decode_content(data: dict[str, Any]) -> str:
    if data.get("type") != "file" or int(data.get("size") or 0) > MAX_METADATA_FILE_BYTES:
        return ""
    content = data.get("content", "")
    if data.get("encoding") == "base64" and content:
        return base64.b64decode(content, validate=False).decode("utf-8", "replace")[:MAX_TEXT_CHARS]
    return str(content)[:MAX_TEXT_CHARS]


def _html_to_text(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text or "")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _append_text(row: dict[str, str], key: str, value: str) -> None:
    if value:
        row[key] = _join([row.get(key, ""), value])[:MAX_TEXT_CHARS]


def _append_semicolon(row: dict[str, str], key: str, values: Iterable[Any]) -> None:
    row[key] = _uniq([row.get(key, ""), *values])


def evidence_lines(text: str, limit: int = 12) -> list[str]:
    lines, seen = [], set()
    for raw in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw.strip())
        if len(line) < 8:
            continue
        if not re.search(r"\b(doi|pmid|pubmed|paper|publication|article|preprint|title|author|application|app|project)\b|10\.\d{4,9}/", line, re.I):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(line[:500])
        if len(lines) >= limit:
            break
    return lines


def publication_links_from_text(text: str) -> list[str]:
    return list(dict.fromkeys(url.rstrip(".,;:") for url in PUBLICATION_URL.findall(text or "")))


def metadata_titles(text: str) -> list[str]:
    titles: list[str] = []
    for pattern in (
        r"(?im)^\s*title\s*[:=]\s*['\"]?(.{8,240}?)['\"]?\s*$",
        r"(?im)^\s*Title\s*:\s*(.{8,240}?)\s*$",
    ):
        titles.extend(m.group(1).strip(" '\"") for m in re.finditer(pattern, text or ""))
    for label, url in re.findall(r"\[([^\]]{8,240})\]\((https?://[^)\s]+)\)", text or ""):
        if PUBLICATION_URL.search(url):
            titles.append(label.strip())
    data = _json(text)
    if isinstance(data, dict):
        for key in ("title", "name", "description"):
            value = data.get(key)
            if isinstance(value, str) and 8 <= len(value) <= 240:
                titles.append(value)
        meta = data.get("metadata")
        if isinstance(meta, dict) and isinstance(meta.get("title"), str):
            titles.append(meta["title"])
    return list(dict.fromkeys(t for t in titles if t))


def metadata_authors(text: str) -> list[str]:
    authors: list[str] = []
    for pattern in (
        r"(?im)^\s*(?:authors?|creators?)\s*[:=]\s*(.{3,240}?)\s*$",
        r"(?im)^\s*(?:Author|Maintainer)\s*:\s*(.{3,240}?)\s*$",
        r"(?im)^\s*family-names\s*:\s*(.{2,80}?)\s*$",
        r"(?im)^\s*given-names\s*:\s*(.{2,80}?)\s*$",
    ):
        authors.extend(m.group(1).strip(" '\"") for m in re.finditer(pattern, text or ""))
    data = _json(text)
    if isinstance(data, dict):
        people = data.get("authors") or data.get("creators") or data.get("contributors") or []
        if isinstance(data.get("metadata"), dict):
            people = people or data["metadata"].get("creators", [])
        if isinstance(people, list):
            for person in people[:12]:
                if isinstance(person, str):
                    authors.append(person)
                elif isinstance(person, dict):
                    name = person.get("name") or " ".join(str(person.get(k, "")) for k in ("given", "family")).strip()
                    if name:
                        authors.append(name)
    return list(dict.fromkeys(a for a in authors if a))


def metadata_path_candidates(client: Any, full: str, default_branch: str) -> list[str]:
    paths: list[str] = []
    if default_branch:
        tree_url = f"https://api.github.com/repos/{full}/git/trees/{urllib.parse.quote(default_branch, safe='')}?recursive=1"
        response = client.fetch(tree_url)
        if response.get("status") == 200:
            for item in _json(response.get("body", "")).get("tree", []):
                path = item.get("path", "")
                if item.get("type") == "blob" and Path(path).name.lower() in METADATA_BASENAMES:
                    paths.append(path)
                    if len(paths) >= METADATA_TREE_LIMIT:
                        break
    root = ["CITATION.cff", "CITATION.bib", "codemeta.json", ".zenodo.json", "DESCRIPTION", "pyproject.toml", "package.json"]
    return list(dict.fromkeys([*root, *paths]))


def fetch_public_file(client: Any, full: str, path: str, ref: str) -> dict[str, str]:
    encoded = urllib.parse.quote(path, safe="/")
    query = "?" + urllib.parse.urlencode({"ref": ref}) if ref else ""
    response = client.fetch(f"https://api.github.com/repos/{full}/contents/{encoded}{query}")
    if response.get("status") != 200:
        return {"text": "", "url": ""}
    data = _json(response.get("body", ""))
    return {"text": _decode_content(data), "url": data.get("html_url") or data.get("download_url") or ""}


def citation_metadata(client: Any, full: str, default_branch: str, identifiers: Callable[[str], dict[str, list[str]]]) -> dict[str, str]:
    texts, urls, paths = [], [], []
    for path in metadata_path_candidates(client, full, default_branch):
        item = fetch_public_file(client, full, path, default_branch)
        if not item["text"]:
            continue
        texts.append(item["text"])
        urls.append(item["url"])
        paths.append(path)
    text = _join(texts)
    ids = identifiers(text)
    links = publication_links_from_text(text)
    return {
        "files": _uniq(paths),
        "text": text[:MAX_TEXT_CHARS],
        "urls": _uniq(urls),
        "publication_links": _uniq(links),
        "doi": _uniq(ids.get("doi", [])),
        "pubmed_id": _uniq(ids.get("pubmed_id", [])),
        "app_id": _uniq(ids.get("app_id", [])),
        "paper_title": _uniq(metadata_titles(text)),
        "paper_authors": _uniq(metadata_authors(text)),
        "excerpts": " | ".join(evidence_lines(text)),
    }


def wayback_readme(client: Any, full: str, limit: int, identifiers: Callable[[str], dict[str, list[str]]]) -> dict[str, str]:
    if limit <= 0:
        return {"text": "", "wayback_readme_first_capture": "", "wayback_readme_capture_count": "0", "wayback_readme_urls": "", "wayback_readme_fetched_at_utc": ""}
    patterns = [
        f"raw.githubusercontent.com/{full}/*/README.md",
        f"raw.githubusercontent.com/{full}/*/README.rst",
        f"raw.githubusercontent.com/{full}/*/README",
        f"github.com/{full}/raw/*/README.md",
        f"github.com/{full}/blob/*/README.md",
    ]
    captures: list[tuple[str, str]] = []
    for pattern in patterns:
        q = urllib.parse.urlencode({
            "url": pattern,
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype,digest",
            "filter": "statuscode:200",
            "collapse": "digest",
            "limit": str(max(1, min(limit, 5))),
        })
        response = client.fetch("https://web.archive.org/cdx?" + q, "application/json", timeout=20, retries=0)
        if response.get("status") != 200:
            continue
        try:
            rows = json.loads(response.get("body", "[]"))[1:]
        except Exception:
            rows = []
        captures.extend((row[0], row[1]) for row in rows if len(row) >= 2)
    captures = sorted(dict.fromkeys(captures))
    if not captures:
        return {"text": "", "wayback_readme_first_capture": "", "wayback_readme_capture_count": "0", "wayback_readme_urls": "", "wayback_readme_fetched_at_utc": ""}
    timestamp, original = captures[0]
    memento = f"https://web.archive.org/web/{timestamp}id_/{original}"
    response = client.fetch(memento, "text/plain, text/markdown, text/html;q=0.8", timeout=20, retries=0)
    body = response.get("body", "") if response.get("status") == 200 else ""
    text = _html_to_text(body) if "<html" in body.lower()[:500] else body
    ids = identifiers(text)
    links = publication_links_from_text(text)
    return {
        "text": text[:MAX_TEXT_CHARS],
        "wayback_readme_first_capture": timestamp,
        "wayback_readme_capture_count": str(len(captures)),
        "wayback_readme_urls": _uniq([memento, *[url for _, url in captures[:5]]]),
        "wayback_readme_fetched_at_utc": response.get("fetched_at_utc", ""),
        "publication_links": _uniq(links),
        "doi": _uniq(ids.get("doi", [])),
        "pubmed_id": _uniq(ids.get("pubmed_id", [])),
        "app_id": _uniq(ids.get("app_id", [])),
        "paper_title": _uniq(metadata_titles(text)),
        "paper_authors": _uniq(metadata_authors(text)),
        "excerpts": " | ".join(evidence_lines(text)),
    }


def package_names_from_text(text: str) -> tuple[list[str], list[str], list[str]]:
    zenodo = list(dict.fromkeys(m.group(1) for m in ZENODO_RECORD_URL.finditer(text or "")))
    pypi = list(dict.fromkeys(m.group(1) for m in PYPI_PROJECT_URL.finditer(text or "")))
    cran = list(dict.fromkeys(m.group(1) for m in CRAN_PACKAGE_URL.finditer(text or "")))
    for match in re.finditer(r"(?im)^\s*Package\s*:\s*([A-Za-z0-9_.-]+)\s*$", text or ""):
        cran.append(match.group(1))
    return zenodo, list(dict.fromkeys(pypi)), list(dict.fromkeys(cran))


def _repo_basename(full: str) -> str:
    return urllib.parse.unquote(str(full or "").rstrip("/").rsplit("/", 1)[-1].removesuffix(".git"))


def _useful_package_name(name: str) -> bool:
    clean = re.sub(r"[^a-z0-9]+", "", str(name or "").lower())
    return len(clean) >= 5 and clean not in GENERIC_PACKAGE_NAMES


def package_name_variants(full: str) -> list[str]:
    name = _repo_basename(full)
    if not _useful_package_name(name):
        return []
    normalized_dash = re.sub(r"[-_.]+", "-", name).strip("-")
    normalized_underscore = re.sub(r"[-_.]+", "_", name).strip("_")
    variants = [name, normalized_dash, normalized_underscore, name.lower(), normalized_dash.lower(), normalized_underscore.lower()]
    return [value for value in dict.fromkeys(variants) if _useful_package_name(value)][:DIRECT_PACKAGE_LOOKUP_LIMIT]


def package_metadata(
    client: Any,
    text: str,
    identifiers: Callable[[str], dict[str, list[str]]],
    direct_package_names: Iterable[str] = (),
) -> dict[str, str]:
    texts, urls, sources = [], [], []
    zenodo_ids, pypi_names, cran_names = package_names_from_text(text)
    direct_names = [name for name in direct_package_names if _useful_package_name(name)]
    pypi_names = list(dict.fromkeys([*pypi_names, *direct_names]))
    cran_names = list(dict.fromkeys([*cran_names, *direct_names]))
    for record_id in zenodo_ids[:5]:
        response = client.fetch(f"https://zenodo.org/api/records/{record_id}", "application/json", timeout=20, retries=0)
        if response.get("status") != 200:
            continue
        data = _json(response.get("body", ""))
        meta = data.get("metadata", {}) if isinstance(data, dict) else {}
        related = []
        for item in meta.get("related_identifiers", []) if isinstance(meta, dict) else []:
            if isinstance(item, dict):
                related.extend(str(item.get(k, "")) for k in ("identifier", "resource_type", "relation") if item.get(k))
        creators = [c.get("name", "") for c in meta.get("creators", []) if isinstance(c, dict)]
        texts.append(_join([data.get("doi", ""), meta.get("title", ""), _join(creators, "; "), _join(related, " ")]))
        urls.append(data.get("links", {}).get("html") or f"https://zenodo.org/records/{record_id}")
        sources.append("zenodo")
    for name in pypi_names[:5]:
        response = client.fetch(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json", "application/json", timeout=20, retries=0)
        if response.get("status") != 200:
            continue
        info = _json(response.get("body", "")).get("info", {})
        project_urls = info.get("project_urls") or {}
        texts.append(_join([info.get("name", ""), info.get("summary", ""), info.get("description", ""), info.get("author", ""), info.get("maintainer", ""), _join(project_urls.values())]))
        urls.append(info.get("package_url") or f"https://pypi.org/project/{name}/")
        sources.append("pypi")
    for name in cran_names[:5]:
        response = client.fetch(f"https://crandb.r-pkg.org/{urllib.parse.quote(name)}", "application/json", timeout=20, retries=0)
        if response.get("status") != 200:
            continue
        data = _json(response.get("body", ""))
        texts.append(_join([data.get("Package", ""), data.get("Title", ""), data.get("Description", ""), data.get("Author", ""), data.get("Maintainer", ""), data.get("URL", ""), data.get("BugReports", "")]))
        urls.append(f"https://cran.r-project.org/package={name}")
        sources.append("cran")
    combined = _join(texts)
    ids = identifiers(combined)
    return {
        "text": combined[:MAX_TEXT_CHARS],
        "urls": _uniq(urls),
        "sources": _uniq(sources),
        "publication_links": _uniq(publication_links_from_text(combined)),
        "doi": _uniq(ids.get("doi", [])),
        "pubmed_id": _uniq(ids.get("pubmed_id", [])),
        "app_id": _uniq(ids.get("app_id", [])),
        "paper_title": _uniq(metadata_titles(combined)),
        "paper_authors": _uniq(metadata_authors(combined)),
        "excerpts": " | ".join(evidence_lines(combined)),
    }


def _record_text_from_zenodo(data: dict[str, Any]) -> str:
    meta = data.get("metadata", {}) if isinstance(data, dict) else {}
    related = []
    for item in meta.get("related_identifiers", []) if isinstance(meta, dict) else []:
        if isinstance(item, dict):
            related.extend(str(item.get(k, "")) for k in ("identifier", "resource_type", "relation", "scheme") if item.get(k))
    creators = [c.get("name", "") for c in meta.get("creators", []) if isinstance(c, dict)]
    return _join([
        data.get("doi", ""),
        meta.get("title", ""),
        meta.get("description", ""),
        meta.get("notes", ""),
        _join(creators, "; "),
        _join(related, " "),
        json.dumps(data.get("links", {}), sort_keys=True),
    ])


def _record_text_from_europepmc(item: dict[str, Any]) -> str:
    fields = [
        item.get("title", ""),
        item.get("authorString", ""),
        f"DOI {item.get('doi', '')}" if item.get("doi") else "",
        f"PMID {item.get('pmid', '')}" if item.get("pmid") else "",
        item.get("pmcid", ""),
        item.get("journalTitle", ""),
    ]
    return _join(fields)


def exact_repo_record_metadata(client: Any, full: str, identifiers: Callable[[str], dict[str, list[str]]]) -> dict[str, str]:
    full = str(full or "").strip("/")
    if "/" not in full:
        return {"text": "", "urls": "", "sources": "", "publication_links": "", "doi": "", "pubmed_id": "", "app_id": "", "paper_title": "", "paper_authors": "", "excerpts": ""}
    exact_url = f"github.com/{full}".lower()
    texts, urls, sources, titles, authors = [], [], [], [], []

    zenodo_query = urllib.parse.urlencode({"q": f'"github.com/{full}"', "size": str(EXACT_RECORD_LOOKUP_LIMIT)})
    response = client.fetch(f"https://zenodo.org/api/records?{zenodo_query}", "application/json", timeout=20, retries=0)
    if response.get("status") == 200:
        data = _json(response.get("body", ""))
        hits = ((data.get("hits") or {}).get("hits") or []) if isinstance(data, dict) else []
        for record in hits[:EXACT_RECORD_LOOKUP_LIMIT]:
            record_text = _record_text_from_zenodo(record)
            if exact_url not in record_text.lower():
                continue
            meta = record.get("metadata", {}) if isinstance(record, dict) else {}
            texts.append(record_text)
            urls.append((record.get("links") or {}).get("html") or f"https://zenodo.org/records/{record.get('id', '')}".rstrip("/"))
            sources.append("zenodo_exact_repo_url")
            if isinstance(meta, dict) and meta.get("title"):
                titles.append(meta["title"])
            for creator in meta.get("creators", []) if isinstance(meta, dict) else []:
                if isinstance(creator, dict) and creator.get("name"):
                    authors.append(creator["name"])

    epmc_query = urllib.parse.urlencode({
        "query": f'"github.com/{full}"',
        "format": "json",
        "pageSize": str(EXACT_RECORD_LOOKUP_LIMIT),
        "resultType": "core",
    })
    response = client.fetch(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{epmc_query}", "application/json", timeout=20, retries=0)
    if response.get("status") == 200:
        data = _json(response.get("body", ""))
        results = ((data.get("resultList") or {}).get("result") or []) if isinstance(data, dict) else []
        for item in results[:EXACT_RECORD_LOOKUP_LIMIT]:
            record_text = _record_text_from_europepmc(item)
            texts.append(record_text)
            pmid = item.get("pmid", "")
            doi = item.get("doi", "")
            urls.append(f"https://europepmc.org/article/MED/{pmid}" if pmid else (f"https://doi.org/{doi}" if doi else ""))
            sources.append("europepmc_exact_repo_url")
            if item.get("title"):
                titles.append(item["title"])
            if item.get("authorString"):
                authors.append(item["authorString"])

    combined = _join(texts)
    ids = identifiers(combined)
    return {
        "text": combined[:MAX_TEXT_CHARS],
        "urls": _uniq(urls),
        "sources": _uniq(sources),
        "publication_links": _uniq(publication_links_from_text(combined)),
        "doi": _uniq(ids.get("doi", [])),
        "pubmed_id": _uniq(ids.get("pubmed_id", [])),
        "app_id": _uniq(ids.get("app_id", [])),
        "paper_title": _uniq([*metadata_titles(combined), *titles]),
        "paper_authors": _uniq([*metadata_authors(combined), *authors]),
        "excerpts": " | ".join(evidence_lines(combined)),
    }


def enrich_repo_rows(
    client: Any,
    targets: list[dict[str, str]],
    rows: list[dict[str, str]],
    wayback_limit: int,
    base: Any,
    identifiers: Callable[[str], dict[str, list[str]]],
) -> list[dict[str, str]]:
    api_cache: dict[str, dict[str, Any]] = {}
    citation_cache: dict[tuple[str, str], dict[str, str]] = {}
    wayback_cache: dict[str, dict[str, str]] = {}
    package_cache: dict[str, dict[str, str]] = {}
    exact_record_cache: dict[str, dict[str, str]] = {}

    for target, row in zip(targets, rows):
        full = f"{row.get('repo_owner') or target.get('repo_owner')}/{row.get('repo_name') or target.get('repo_name')}"
        api = api_cache.get(full)
        if api is None:
            response = client.fetch(f"https://api.github.com/repos/{full}")
            api = _json(response.get("body", "")) if response.get("status") == 200 else {}
            api_cache[full] = api
        default_branch = api.get("default_branch", "")
        source = row.get("github_source") or row.get("parent_or_source_repo") or full
        metadata_items: list[dict[str, str]] = []
        if api:
            for repo_full in dict.fromkeys([full, source]):
                key = (repo_full, default_branch)
                if key not in citation_cache:
                    citation_cache[key] = citation_metadata(client, repo_full, default_branch, identifiers)
                metadata_items.append(citation_cache[key])

        public_text = _join([row.get("_readme_text", ""), row.get("_evidence_excerpts", ""), *(m.get("text", "") for m in metadata_items)])
        wayback_meta = {}
        if row.get("repo_status") != "live" and wayback_limit > 0:
            if full not in wayback_cache:
                wayback_cache[full] = wayback_readme(client, full, wayback_limit, identifiers)
            wayback_meta = wayback_cache[full]
            public_text = _join([public_text, wayback_meta.get("text", "")])
        package_names = package_name_variants(full)
        if source and source != full:
            package_names.extend(package_name_variants(source))
        package_names = list(dict.fromkeys(package_names))
        package_key = (public_text[:10_000], tuple(package_names))
        if package_key not in package_cache:
            package_cache[package_key] = package_metadata(client, public_text, identifiers, package_names)
        package_meta = package_cache[package_key]
        record_items: list[dict[str, str]] = []
        for repo_full in dict.fromkeys([full, source]):
            if not repo_full:
                continue
            if repo_full not in exact_record_cache:
                exact_record_cache[repo_full] = exact_repo_record_metadata(client, repo_full, identifiers)
            record_items.append(exact_record_cache[repo_full])

        combined = _join([public_text, package_meta.get("text", ""), *(item.get("text", "") for item in record_items)])
        ids = identifiers(combined)
        _append_semicolon(row, "doi", [*(m.get("doi", "") for m in metadata_items), wayback_meta.get("doi", ""), package_meta.get("doi", ""), *(m.get("doi", "") for m in record_items), *ids.get("doi", [])])
        _append_semicolon(row, "pubmed_id", [*(m.get("pubmed_id", "") for m in metadata_items), wayback_meta.get("pubmed_id", ""), package_meta.get("pubmed_id", ""), *(m.get("pubmed_id", "") for m in record_items), *ids.get("pubmed_id", [])])
        _append_semicolon(row, "_direct_app_ids", [*(m.get("app_id", "") for m in metadata_items), wayback_meta.get("app_id", ""), package_meta.get("app_id", ""), *(m.get("app_id", "") for m in record_items), *ids.get("app_id", [])])
        _append_semicolon(row, "paper_title", [*(m.get("paper_title", "") for m in metadata_items), wayback_meta.get("paper_title", ""), package_meta.get("paper_title", ""), *(m.get("paper_title", "") for m in record_items)])
        _append_semicolon(row, "paper_authors", [*(m.get("paper_authors", "") for m in metadata_items), wayback_meta.get("paper_authors", ""), package_meta.get("paper_authors", ""), *(m.get("paper_authors", "") for m in record_items)])
        _append_semicolon(row, "evidence_urls", [*(m.get("urls", "") for m in metadata_items), wayback_meta.get("wayback_readme_urls", ""), package_meta.get("urls", ""), *(m.get("urls", "") for m in record_items), *(m.get("publication_links", "") for m in metadata_items), wayback_meta.get("publication_links", ""), package_meta.get("publication_links", ""), *(m.get("publication_links", "") for m in record_items)])
        row["repository_readme_urls"] = _uniq([row.get("repository_readme_urls", ""), row.get("evidence_urls", "") if "README" in row.get("evidence_urls", "") else ""])
        row["citation_metadata_urls"] = _uniq(m.get("urls", "") for m in metadata_items)
        row["metadata_publication_links"] = _uniq([*(m.get("publication_links", "") for m in metadata_items), wayback_meta.get("publication_links", ""), package_meta.get("publication_links", ""), *(m.get("publication_links", "") for m in record_items)])
        row["package_metadata_sources"] = package_meta.get("sources", "")
        row["package_metadata_urls"] = package_meta.get("urls", "")
        row["public_record_metadata_sources"] = _uniq(m.get("sources", "") for m in record_items)
        row["public_record_metadata_urls"] = _uniq(m.get("urls", "") for m in record_items)
        for key in ("wayback_readme_first_capture", "wayback_readme_capture_count", "wayback_readme_urls", "wayback_readme_fetched_at_utc"):
            row[key] = wayback_meta.get(key, "")
        _append_text(row, "_readme_text", combined)
        _append_text(row, "_paper_text", _join([row.get("paper_title", ""), row.get("paper_authors", ""), row.get("doi", ""), row.get("pubmed_id", "")]))
        _append_text(row, "_text", combined)
        _append_semicolon(row, "_evidence_excerpts", [*(m.get("excerpts", "") for m in metadata_items), wayback_meta.get("excerpts", ""), package_meta.get("excerpts", ""), *(m.get("excerpts", "") for m in record_items)])
    return rows


def rollup_lineage_fields(lineages: list[dict[str, str]], repo_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_lineage: dict[str, list[dict[str, str]]] = {}
    for row in repo_rows:
        by_lineage.setdefault(row.get("lineage_id", ""), []).append(row)
    for lineage in lineages:
        rows = by_lineage.get(lineage.get("lineage_id", ""), [])
        for key in EXTRA_LINEAGE_FIELDS:
            lineage[key] = _uniq(row.get(key, "") for row in rows)
        for key in ("doi", "pubmed_id", "paper_title", "paper_authors", "evidence_urls", "_direct_app_ids"):
            lineage[key] = _uniq([lineage.get(key, ""), *(row.get(key, "") for row in rows)])
        for key in ("_paper_text", "_readme_text", "_text", "_evidence_excerpts"):
            lineage[key] = _join([lineage.get(key, ""), *(row.get(key, "") for row in rows)])
    return lineages


def summary_counts(lineages: list[dict[str, str]]) -> dict[str, int]:
    return {
        "lineages_with_wayback_readme": sum(1 for l in lineages if l.get("wayback_readme_first_capture")),
        "lineages_with_citation_metadata": sum(1 for l in lineages if l.get("citation_metadata_urls")),
        "lineages_with_package_metadata": sum(1 for l in lineages if l.get("package_metadata_sources")),
        "lineages_with_public_record_metadata": sum(1 for l in lineages if l.get("public_record_metadata_sources")),
        "lineages_with_metadata_publication_links": sum(1 for l in lineages if l.get("metadata_publication_links")),
    }
