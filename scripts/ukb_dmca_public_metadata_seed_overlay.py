#!/usr/bin/env python3
"""Apply hand-curated public metadata seeds to UKB DMCA matching outputs."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SEED_FILENAMES = ("public_metadata_seeds.tsv", "public_metadata_seeds.csv")
PROJECT_FAMILY_EVIDENCE_CLASS = "B2_PROJECT_FAMILY_NAME_PROPAGATION"
CONTENT_FINGERPRINT_EVIDENCE_CLASS = "B3_EXACT_TARGET_CONTENT_FINGERPRINT_PROPAGATION"
GENERIC_PROJECT_KEYS = {
    "001",
    "biobank",
    "data",
    "dataset",
    "example",
    "examples",
    "gwas",
    "phenotype",
    "ukb",
    "ukbb",
    "ukbbdata",
    "ukbiobank",
    "ukbiobankdata",
}
TARGET_CONTENT_LINK = re.compile(
    r"github\.com/[^/\s]+/[^/\s]+/(?:blob|tree|raw)/([0-9a-f]{7,40})/([^#?\s]+)"
    r"|raw\.githubusercontent\.com/[^/\s]+/[^/\s]+/([0-9a-f]{7,40})/([^#?\s]+)",
    re.I,
)
SEED_REASON = {
    "confirmed": "Public metadata seed records a unique repository-publication-application evidence chain.",
    "probable": "Public metadata seed records strong but non-deterministic repository-publication-application evidence.",
    "ambiguous": "Public metadata seed records multiple plausible application links that require manual review.",
    "not_application_attributable": "Public metadata seed indicates third-party propagation without attributable original UKB application evidence.",
    "unresolved": "Public metadata seed was retained for audit but is insufficient for assignment.",
}


def _norm_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")


def _parts(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split(";") if x.strip()]


def _uniq(values) -> str:
    out, seen = [], set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return "; ".join(out)


def _normalize_doi(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    text = text.strip(" \t\r\n<>[](){}.,;:")
    return text if re.match(r"^10\.\d{4,9}/", text) else ""


def _normalize_pmid(value: str) -> str:
    match = re.search(r"\d{6,9}", str(value or ""))
    return match.group(0) if match else ""


def _repo_basename(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", text, re.I)
    if match:
        return match.group(2).strip()
    if "/" in text:
        return text.rstrip("/").rsplit("/", 1)[-1]
    return text


def _project_key(value: str) -> str:
    name = urllib_unquote(_repo_basename(value))
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    key = re.sub(r"[^a-z0-9]+", "", name.lower())
    if len(key) < 6 or key in GENERIC_PROJECT_KEYS:
        return ""
    return key


def urllib_unquote(value: str) -> str:
    try:
        from urllib.parse import unquote

        return unquote(str(value or ""))
    except Exception:
        return str(value or "")


def _lineage_project_keys(lineage: dict[str, str]) -> set[str]:
    keys: set[str] = set()
    for field in ("source_repo", "repo_urls", "evidence_urls"):
        for value in _parts(lineage.get(field, "")):
            key = _project_key(value)
            if key:
                keys.add(key)
    lineage_id = lineage.get("lineage_id", "")
    if "_" in lineage_id:
        key = _project_key(lineage_id.rsplit("_", 1)[-1])
        if key:
            keys.add(key)
    return keys


def _seed_project_keys(seed: dict[str, str]) -> set[str]:
    keys: set[str] = set()
    for field in ("repo_or_project", "repository_url", "project_name", "evidence_urls"):
        for value in _parts(seed.get(field, "")):
            key = _project_key(value)
            if key:
                keys.add(key)
    return keys


def _seed_fingerprint_values(lineage: dict[str, str]) -> set[str]:
    fingerprints: set[str] = set()
    for field in ("evidence_urls", "repository_readme_urls", "metadata_publication_links"):
        for value in _parts(lineage.get(field, "")):
            for match in TARGET_CONTENT_LINK.finditer(value):
                sha = (match.group(1) or match.group(3) or "").lower()
                path = urllib_unquote(match.group(2) or match.group(4) or "")
                path = re.sub(r"/+", "/", path.strip("/")).lower()
                if sha and path:
                    fingerprints.add(f"{sha}/{path}")
    return fingerprints


def _derived_linkage_seed(
    lineage: dict[str, str],
    anchor_lineage_id: str,
    anchor_seed: dict[str, str],
    app_id: str,
    evidence_class: str,
    relation_value: str,
    ambiguous: bool,
) -> dict[str, str]:
    row = dict(anchor_seed)
    if evidence_class == PROJECT_FAMILY_EVIDENCE_CLASS:
        relation = (
            f"DMCA-targeted lineage has the same normalized public repository/package name "
            f"'{relation_value}' as seeded/matched lineage {anchor_lineage_id}; no GitHub-displayed "
            "fork/source proof is asserted."
        )
        derived_type = "project_family_name"
        derived_note = "Auto-derived project-family metadata only; use as probable empirical linkage, not attribution or legal finding."
    else:
        relation = (
            f"DMCA-targeted lineage shares the same GitHub target content fingerprint "
            f"'{relation_value}' as seeded/matched lineage {anchor_lineage_id}; this uses public notice/repository URL "
            "metadata only and does not assert who created or disclosed the original content."
        )
        derived_type = "target_content_fingerprint"
        derived_note = "Auto-derived target-content fingerprint metadata only; use as probable empirical linkage, not attribution or legal finding."
    row.update({
        "lineage_id": lineage["lineage_id"],
        "repo_or_project": lineage.get("repo_urls") or lineage.get("source_repo", ""),
        "candidate_app_id": app_id,
        "match_grade": "ambiguous" if ambiguous else "probable",
        "evidence_class": evidence_class,
        "source_relation": relation,
        "notes": _uniq([
            _seed_value(anchor_seed, "notes"),
            derived_note,
        ]),
        "_derived_seed_type": derived_type,
        "_anchor_lineage_id": anchor_lineage_id,
        "_derived_relation_value": relation_value,
    })
    row["evidence_urls"] = _uniq([lineage.get("evidence_urls", ""), _seed_value(anchor_seed, "evidence_urls")])
    return row


def _derive_project_family_seeds(
    lineages: list[dict[str, str]],
    anchor_seeds: dict[str, list[dict[str, str]]],
    target_exclude_lineage_ids: set[str],
) -> dict[str, list[dict[str, str]]]:
    """Propagate existing public metadata seeds across exact project-name families.

    This is intentionally a B-level empirical linkage. It never creates a
    confirmed match and never asserts a GitHub fork/source relation.
    """
    anchors_by_key: dict[str, list[tuple[str, dict[str, str], str]]] = defaultdict(list)
    for lineage_id, rows in anchor_seeds.items():
        for row in rows:
            app_id = _seed_app_id(row)
            if not app_id or row.get("evidence_class") in (PROJECT_FAMILY_EVIDENCE_CLASS, CONTENT_FINGERPRINT_EVIDENCE_CLASS):
                continue
            for key in _seed_project_keys(row):
                anchors_by_key[key].append((lineage_id, row, app_id))

    out: dict[str, list[dict[str, str]]] = {}
    for lineage in lineages:
        lineage_id = lineage.get("lineage_id", "")
        if not lineage_id or lineage_id in target_exclude_lineage_ids:
            continue
        matches: list[tuple[str, dict[str, str], str, str]] = []
        for key in _lineage_project_keys(lineage):
            for anchor_lineage_id, anchor_seed, app_id in anchors_by_key.get(key, []):
                if anchor_lineage_id != lineage_id:
                    matches.append((key, anchor_seed, app_id, anchor_lineage_id))
        if not matches:
            continue
        by_app: dict[str, tuple[str, dict[str, str], str]] = {}
        for key, seed, app_id, anchor_lineage_id in matches:
            by_app.setdefault(app_id, (key, seed, anchor_lineage_id))
        ambiguous = len(by_app) > 1
        out[lineage_id] = [
            _derived_linkage_seed(lineage, anchor_lineage_id, seed, app_id, PROJECT_FAMILY_EVIDENCE_CLASS, key, ambiguous)
            for app_id, (key, seed, anchor_lineage_id) in sorted(by_app.items())
        ]
    return out


def _derive_content_fingerprint_seeds(
    lineages: list[dict[str, str]],
    anchor_seeds: dict[str, list[dict[str, str]]],
    target_exclude_lineage_ids: set[str],
) -> dict[str, list[dict[str, str]]]:
    anchors_by_fingerprint: dict[str, list[tuple[str, dict[str, str], str]]] = defaultdict(list)
    lineage_by_id = {row.get("lineage_id", ""): row for row in lineages}
    for lineage_id, rows in anchor_seeds.items():
        anchor_lineage = lineage_by_id.get(lineage_id, {})
        for row in rows:
            app_id = _seed_app_id(row)
            if not app_id or row.get("evidence_class") in (PROJECT_FAMILY_EVIDENCE_CLASS, CONTENT_FINGERPRINT_EVIDENCE_CLASS):
                continue
            for fingerprint in _seed_fingerprint_values(anchor_lineage):
                anchors_by_fingerprint[fingerprint].append((lineage_id, row, app_id))

    out: dict[str, list[dict[str, str]]] = {}
    for lineage in lineages:
        lineage_id = lineage.get("lineage_id", "")
        if not lineage_id or lineage_id in target_exclude_lineage_ids:
            continue
        matches: list[tuple[str, dict[str, str], str, str]] = []
        for fingerprint in _seed_fingerprint_values(lineage):
            for anchor_lineage_id, anchor_seed, app_id in anchors_by_fingerprint.get(fingerprint, []):
                if anchor_lineage_id != lineage_id:
                    matches.append((fingerprint, anchor_seed, app_id, anchor_lineage_id))
        if not matches:
            continue
        by_app: dict[str, tuple[str, dict[str, str], str]] = {}
        for fingerprint, seed, app_id, anchor_lineage_id in matches:
            by_app.setdefault(app_id, (fingerprint, seed, anchor_lineage_id))
        ambiguous = len(by_app) > 1
        out[lineage_id] = [
            _derived_linkage_seed(lineage, anchor_lineage_id, seed, app_id, CONTENT_FINGERPRINT_EVIDENCE_CLASS, fingerprint, ambiguous)
            for app_id, (fingerprint, seed, anchor_lineage_id) in sorted(by_app.items())
        ]
    return out


def _merge_derived_seeds(*seed_sets: dict[str, list[dict[str, str]]]) -> dict[str, list[dict[str, str]]]:
    merged: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for seed_set in seed_sets:
        for lineage_id, rows in seed_set.items():
            for row in rows:
                app_id = _seed_app_id(row)
                if not app_id:
                    continue
                current = merged[lineage_id].get(app_id)
                if current is None:
                    merged[lineage_id][app_id] = dict(row)
                    continue
                current["evidence_class"] = _uniq([current.get("evidence_class", ""), row.get("evidence_class", "")])
                current["source_relation"] = _uniq([current.get("source_relation", ""), row.get("source_relation", "")])
                current["notes"] = _uniq([current.get("notes", ""), row.get("notes", "")])
                current["evidence_urls"] = _uniq([current.get("evidence_urls", ""), row.get("evidence_urls", "")])
                current["_derived_seed_type"] = _uniq([current.get("_derived_seed_type", ""), row.get("_derived_seed_type", "")])
                current["_anchor_lineage_id"] = _uniq([current.get("_anchor_lineage_id", ""), row.get("_anchor_lineage_id", "")])
                current["_derived_relation_value"] = _uniq([current.get("_derived_relation_value", ""), row.get("_derived_relation_value", "")])
                if current.get("match_grade") != row.get("match_grade"):
                    current["match_grade"] = "ambiguous"
    return {lineage_id: list(by_app.values()) for lineage_id, by_app in merged.items()}


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def _write_csv(path: Path, rows: list[dict[str, Any]], preferred: list[str]) -> None:
    fields = list(preferred)
    for row in rows:
        for key in row:
            if key not in fields and not key.startswith("_"):
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def _table_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    delimiter = "\t" if text[:4096].count("\t") >= text[:4096].count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def _seed_paths(output_dir: Path) -> list[Path]:
    paths, seen = [], set()
    for base_dir in (output_dir / "data", Path("data")):
        for name in SEED_FILENAMES:
            path = base_dir / name
            if not path.exists():
                continue
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                paths.append(path)
    return paths


def _load_seeds(output_dir: Path) -> dict[str, list[dict[str, str]]]:
    rows_by_lineage: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in _seed_paths(output_dir):
        for raw in _table_rows(path):
            row = {_norm_col(key): str(value or "").strip() for key, value in raw.items()}
            lineage_id = row.get("lineage_id", "")
            if not lineage_id:
                continue
            row["_seed_file"] = str(path)
            row["doi"] = _normalize_doi(row.get("doi", ""))
            row["pubmed_id"] = _normalize_pmid(row.get("pubmed_id") or row.get("pmid", ""))
            row["match_grade"] = (row.get("match_grade") or row.get("grade") or "candidate").lower()
            row["evidence_class"] = row.get("evidence_class") or row.get("matching_rule") or "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN"
            rows_by_lineage[lineage_id].append(row)
    return dict(rows_by_lineage)


def _parse_applications(path: Path) -> dict[str, dict[str, str]]:
    apps: dict[str, dict[str, str]] = {}
    if not path.exists():
        return apps
    cur: dict[str, str] | None = None
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for raw in handle:
            line = raw.rstrip("\r\n")
            if line.startswith("app_id\t"):
                continue
            if re.match(r"^\d+\t", line):
                parts = line.split("\t", 4)
                parts += [""] * (5 - len(parts))
                cur = {
                    "app_id": parts[0].strip(),
                    "title": parts[1].strip(),
                    "pi": parts[2].strip(),
                    "institution": parts[3].strip(),
                    "notes": parts[4].strip(),
                }
                apps[cur["app_id"]] = cur
            elif cur:
                cur["notes"] = (cur["notes"] + "\n" + line.strip()).strip()
    return apps


def _seed_value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(_norm_col(key), "")
        if value:
            return value
    return ""


def _seed_app_id(row: dict[str, str]) -> str:
    for key in ("candidate_app_id", "application_id", "app_id", "ukb_application_id", "ukb_app_id"):
        values = re.findall(r"\d{2,8}", row.get(key, ""))
        if len(values) == 1:
            return values[0]
    return ""


def _seed_like_rows_from_existing_matches(
    lineages: list[dict[str, str]],
    result_rows: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    lineage_by_id = {row.get("lineage_id", ""): row for row in lineages}
    anchors: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for raw in result_rows:
        lineage_id = raw.get("lineage_id", "")
        app_id = raw.get("candidate_app_id", "")
        grade = (raw.get("match_grade") or "").lower()
        if not lineage_id or not app_id or grade not in ("confirmed", "probable"):
            continue
        lineage = lineage_by_id.get(lineage_id, {})
        evidence_class = raw.get("evidence_class") or raw.get("matching_rule") or ""
        if evidence_class in (PROJECT_FAMILY_EVIDENCE_CLASS, CONTENT_FINGERPRINT_EVIDENCE_CLASS):
            continue
        seed = {
            "lineage_id": lineage_id,
            "repo_or_project": lineage.get("repo_urls") or raw.get("repo_url") or lineage.get("source_repo", ""),
            "evidence_class": evidence_class or ("A1_DIRECT_APP_ID" if "direct_application_id" in raw.get("evidence_components", "") else "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN"),
            "match_grade": grade,
            "candidate_app_id": app_id,
            "doi": _uniq(_normalize_doi(value) for value in _parts(raw.get("repo_linked_doi") or raw.get("doi", ""))),
            "pubmed_id": _uniq(_normalize_pmid(value) for value in _parts(raw.get("repo_linked_pmid") or raw.get("pubmed_id", ""))),
            "ukb_publication_id": raw.get("crosswalk_pub_ids", ""),
            "publication_title": raw.get("repo_linked_publication_title") or raw.get("paper_title", ""),
            "authors": raw.get("paper_authors", ""),
            "application_title": raw.get("application_title", ""),
            "application_pi": raw.get("application_pi", ""),
            "application_institution": raw.get("application_institution", ""),
            "evidence_urls": _uniq([lineage.get("evidence_urls", ""), raw.get("evidence_urls", "")]),
            "source_relation": (
                f"Existing pipeline {grade} match for {lineage_id} is used as a public metadata anchor "
                "for probable project-family/content-fingerprint propagation."
            ),
            "notes": "Auto-generated anchor from existing non-derived application matching output.",
            "_seed_file": "existing_pipeline_match",
        }
        current = anchors[lineage_id].get(app_id)
        if current is None:
            anchors[lineage_id][app_id] = seed
            continue
        current["evidence_class"] = _uniq([current.get("evidence_class", ""), seed.get("evidence_class", "")])
        current["doi"] = _uniq([current.get("doi", ""), seed.get("doi", "")])
        current["pubmed_id"] = _uniq([current.get("pubmed_id", ""), seed.get("pubmed_id", "")])
        current["publication_title"] = _uniq([current.get("publication_title", ""), seed.get("publication_title", "")])
        current["evidence_urls"] = _uniq([current.get("evidence_urls", ""), seed.get("evidence_urls", "")])
    return {lineage_id: list(by_app.values()) for lineage_id, by_app in anchors.items()}


def _merge_anchor_seed_rows(
    seed_rows: dict[str, list[dict[str, str]]],
    extra_anchor_rows: dict[str, list[dict[str, str]]],
) -> dict[str, list[dict[str, str]]]:
    merged = {lineage_id: [dict(row) for row in rows] for lineage_id, rows in seed_rows.items()}
    for lineage_id, rows in extra_anchor_rows.items():
        merged.setdefault(lineage_id, []).extend(dict(row) for row in rows)
    return merged


def _seed_urls(row: dict[str, str]) -> list[str]:
    urls: list[str] = []
    for key in ("evidence_urls", "evidence_url", "repository_url", "publication_url", "project_url", "doi_url"):
        urls.extend(_parts(row.get(key, "")))
    if row.get("doi"):
        urls.append(f"https://doi.org/{row['doi']}")
    return list(dict.fromkeys(urls))


def _identifier_types(row: dict[str, str]) -> str:
    values = []
    if row.get("doi"):
        values.append("doi")
    if row.get("pubmed_id"):
        values.append("pmid")
    if _seed_value(row, "publication_title", "paper_title", "title"):
        values.append("title")
    return "; ".join(values)


def _evidence_payload(row: dict[str, str], app_id: str) -> str:
    payload = [{
        "identifier_type": _identifier_types(row) or "public_metadata_seed",
        "identifier": row.get("doi") or row.get("pubmed_id") or _seed_value(row, "publication_title", "paper_title", "title"),
        "pub_id": _seed_value(row, "ukb_publication_id", "publication_id", "pub_id"),
        "app_id": app_id,
        "evidence_class": row.get("evidence_class", ""),
        "source_relation": _seed_value(row, "source_relation"),
        "evidence_urls": "; ".join(_seed_urls(row)),
    }]
    return json.dumps(payload, sort_keys=True)


def _merge_seed_metadata(row: dict[str, str], seed: dict[str, str], app_id: str) -> None:
    title = _seed_value(seed, "publication_title", "paper_title", "title")
    authors = _seed_value(seed, "authors", "paper_authors", "publication_authors")
    if seed.get("doi"):
        row["doi"] = _uniq([*_parts(row.get("doi", "")), seed["doi"]])
        row["repo_linked_doi"] = _uniq([*_parts(row.get("repo_linked_doi", "")), seed["doi"]])
    if seed.get("pubmed_id"):
        row["pubmed_id"] = _uniq([*_parts(row.get("pubmed_id", "")), seed["pubmed_id"]])
        row["repo_linked_pmid"] = _uniq([*_parts(row.get("repo_linked_pmid", "")), seed["pubmed_id"]])
    if title:
        row["paper_title"] = _uniq([*_parts(row.get("paper_title", "")), title])
        row["repo_linked_publication_title"] = _uniq([*_parts(row.get("repo_linked_publication_title", "")), title])
    if authors:
        row["paper_authors"] = _uniq([*_parts(row.get("paper_authors", "")), authors])
    row["crosswalk_pub_ids"] = _uniq([*_parts(row.get("crosswalk_pub_ids", "")), _seed_value(seed, "ukb_publication_id", "publication_id", "pub_id")])
    row["crosswalk_app_ids"] = _uniq([*_parts(row.get("crosswalk_app_ids", "")), app_id])
    row["crosswalk_application_count"] = "1"
    row["crosswalk_identifier_type"] = _uniq([*_parts(row.get("crosswalk_identifier_type", "")), *_parts(_identifier_types(seed))])
    row["crosswalk_evidence"] = _evidence_payload(seed, app_id)
    row["evidence_urls"] = _uniq([*_parts(row.get("evidence_urls", "")), *_seed_urls(seed)])


def _candidate_from_seed(lineage: dict[str, str], app: dict[str, str], seed: dict[str, str]) -> dict[str, Any]:
    app_id = app["app_id"]
    grade = seed.get("match_grade") or "candidate"
    evidence_class = seed.get("evidence_class") or "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN"
    component_values = ["public_metadata_seed", evidence_class]
    if evidence_class == "A1_DIRECT_APP_ID":
        component_values.append("direct_application_id")
    if evidence_class.startswith(("A2_", "A3_", "A4_")):
        component_values.append("exact_publication_identifier")
    components = _uniq(component_values)
    score = "100" if grade == "confirmed" else "85" if grade == "probable" else "70"
    details = {
        "public_metadata_seed": {
            "doi": seed.get("doi", ""),
            "pubmed_id": seed.get("pubmed_id", ""),
            "publication_title": _seed_value(seed, "publication_title", "paper_title", "title"),
            "authors": _seed_value(seed, "authors", "paper_authors", "publication_authors"),
            "repo_or_project": _seed_value(seed, "repo_or_project", "repository_url", "project_name"),
            "source_relation": _seed_value(seed, "source_relation"),
            "notes": _seed_value(seed, "notes"),
            "evidence_urls": _seed_urls(seed),
        }
    }
    return {
        "lineage_id": lineage["lineage_id"],
        "candidate_rank": "1",
        "candidate_app_id": app_id,
        "application_title": app.get("title") or _seed_value(seed, "application_title"),
        "application_pi": app.get("pi") or _seed_value(seed, "application_pi"),
        "application_institution": app.get("institution") or _seed_value(seed, "application_institution", "institution"),
        "match_grade": grade,
        "match_score": score,
        "evidence_level": "A" if grade in ("confirmed", "ambiguous") else "B",
        "evidence_class": evidence_class,
        "evidence_components": components,
        "score_details": json.dumps(details, sort_keys=True),
        "deterministic_evidence_present": "true" if evidence_class.startswith("A") else "false",
        "identity_evidence_present": "false",
        "contextual_evidence_present": "false",
        "crosswalk_pub_ids": _seed_value(seed, "ukb_publication_id", "publication_id", "pub_id"),
        "crosswalk_app_ids": app_id,
        "crosswalk_application_count": "1",
        "crosswalk_identifier_type": _identifier_types(seed),
        "crosswalk_evidence": _evidence_payload(seed, app_id),
        "match_reason": SEED_REASON.get(grade, "Public metadata seed retained for audit."),
        "evidence_urls": _uniq([*_parts(lineage.get("evidence_urls", "")), *_seed_urls(seed)]),
        "manual_review_needed": "false" if grade == "confirmed" else "true",
    }


def _result_rows_for_seed(repos: list[dict[str, str]], candidate: dict[str, Any], grade: str) -> list[dict[str, Any]]:
    rows = []
    for repo in repos:
        row = dict(repo)
        row.update({
            "candidate_app_id": candidate.get("candidate_app_id", ""),
            "application_title": candidate.get("application_title", ""),
            "application_pi": candidate.get("application_pi", ""),
            "application_institution": candidate.get("application_institution", ""),
            "application_linked_to_dmca_targeted_repository_lineage": "true" if grade in ("confirmed", "probable") else "false",
            "match_grade": grade,
            "match_score": candidate.get("match_score", "0"),
            "evidence_class": candidate.get("evidence_class", ""),
            "evidence_components": candidate.get("evidence_components", ""),
            "deterministic_evidence_present": candidate.get("deterministic_evidence_present", "false"),
            "identity_evidence_present": candidate.get("identity_evidence_present", "false"),
            "contextual_evidence_present": candidate.get("contextual_evidence_present", "false"),
            "match_reason": candidate.get("match_reason", ""),
            "manual_review_needed": candidate.get("manual_review_needed", "true"),
        })
        rows.append(row)
    return rows


def _rerank_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_lineage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_lineage[row.get("lineage_id", "")].append(dict(row))
    out = []
    for lineage_id in sorted(by_lineage):
        ranked = sorted(by_lineage[lineage_id], key=lambda r: (-float(r.get("match_score", 0) or 0), str(r.get("candidate_app_id", ""))))
        for idx, row in enumerate(ranked, 1):
            row["candidate_rank"] = str(idx)
            if idx > 1:
                row["match_grade"] = "candidate"
                row["match_reason"] = "Alternative candidate retained for audit."
                row["manual_review_needed"] = "true"
            out.append(row)
    return out


def _append_seed_audit(output_dir: Path, lineage: dict[str, str], seeds: list[dict[str, str]], candidate: dict[str, Any]) -> None:
    rel = lineage.get("evidence_file") or f"evidence/lineages/{lineage['lineage_id']}.md"
    path = output_dir / rel
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace").split("## Public Metadata Seed Audit")[0].rstrip()
    urls = _uniq(url for seed in seeds for url in _seed_urls(seed))
    audit = [
        "",
        "## Public Metadata Seed Audit",
        f"- seed_rows: {len(seeds)}",
        f"- candidate_app_id: {candidate.get('candidate_app_id', '')}",
        f"- evidence_class: {candidate.get('evidence_class', '')}",
        f"- evidence_components: {candidate.get('evidence_components', '')}",
        f"- evidence_urls: {urls}",
        f"- match_reason: {candidate.get('match_reason', '')}",
    ]
    path.write_text(text + "\n" + "\n".join(audit) + "\n", encoding="utf-8")


def _usable_publication_title(value: str) -> bool:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return len(text) >= 25 and len(text.split()) >= 5


def _summary_update(output_dir: Path, manual_rows: list[dict[str, Any]], evidence_rows: list[dict[str, Any]], seeds: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    grade_by_lineage = {}
    app_by_lineage = {}
    row_by_lineage = {}
    for row in manual_rows:
        lineage_id = row.get("lineage_id", "")
        if not lineage_id:
            continue
        grade_by_lineage[lineage_id] = row.get("match_grade", "unresolved")
        app_by_lineage[lineage_id] = row.get("candidate_app_id", "")
        row_by_lineage[lineage_id] = row
    grades = Counter(grade_by_lineage.values())
    unique_apps = {
        app_by_lineage[lineage_id]
        for lineage_id, grade in grade_by_lineage.items()
        if grade in ("confirmed", "probable") and app_by_lineage.get(lineage_id)
    }
    lineage_rows, _ = _read_csv(output_dir / "ukb_dmca_lineages.csv")
    summary_path = output_dir / "evidence/logs/result_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    existing_cases = summary.get("cases_needing_extra_data", [])
    if not isinstance(existing_cases, list):
        existing_cases = sorted(lineage_id for lineage_id, grade in grade_by_lineage.items() if grade not in ("confirmed", "probable"))
    summary.update({
        "fixed_notice_count": 110,
        "repository_lineage_total": len(grade_by_lineage),
        "cases_needing_extra_data": [
            lineage_id
            for lineage_id in existing_cases
            if grade_by_lineage.get(lineage_id, "unresolved") not in ("confirmed", "probable")
        ],
        "lineages_with_doi": sum(1 for row in lineage_rows if row.get("doi") or row.get("repo_linked_doi")),
        "lineages_with_pmid": sum(1 for row in lineage_rows if row.get("pubmed_id") or row.get("repo_linked_pmid")),
        "lineages_with_publication_title": sum(
            1
            for row in lineage_rows
            if _usable_publication_title(row.get("repo_linked_publication_title") or row.get("paper_title", ""))
        ),
        "lineages_mapped_through_schema19_24": sum(1 for row in lineage_rows if row.get("crosswalk_app_ids")),
        "match_grade_counts": dict(grades),
        "confirmed": grades.get("confirmed", 0),
        "probable": grades.get("probable", 0),
        "ambiguous": grades.get("ambiguous", 0),
        "unresolved": grades.get("unresolved", 0),
        "not_application_attributable": grades.get("not_application_attributable", 0),
        "unique_application_count": len(unique_apps),
        "unique_application_match_ratio": round((grades.get("confirmed", 0) + grades.get("probable", 0)) / len(grade_by_lineage), 4) if grade_by_lineage else 0,
        "direct_app_id_confirmed_matches": sum(
            1
            for lineage_id, row in row_by_lineage.items()
            if grade_by_lineage.get(lineage_id) == "confirmed" and "direct_application_id" in row.get("evidence_components", "")
        ),
        "doi_crosswalk_confirmed_matches": sum(
            1
            for lineage_id, row in row_by_lineage.items()
            if grade_by_lineage.get(lineage_id) == "confirmed" and "A2_DOI_UKB_CROSSWALK" in row.get("evidence_class", "")
        ),
        "pmid_crosswalk_confirmed_matches": sum(
            1
            for lineage_id, row in row_by_lineage.items()
            if grade_by_lineage.get(lineage_id) == "confirmed" and "A3_PMID_UKB_CROSSWALK" in row.get("evidence_class", "")
        ),
        "title_crosswalk_confirmed_matches": sum(
            1
            for lineage_id, row in row_by_lineage.items()
            if grade_by_lineage.get(lineage_id) == "confirmed" and "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN" in row.get("evidence_class", "")
        ),
        "public_metadata_seed_rows": sum(len(rows) for rows in seeds.values()),
        "lineages_with_public_metadata_seeds": len(seeds),
        "public_metadata_seed_matched_lineages": sum(1 for lineage_id in seeds if grade_by_lineage.get(lineage_id) in ("confirmed", "probable")),
        "matching_layer_contributions": {
            "A1_DIRECT_APP_ID": sum(1 for row in evidence_rows if row.get("evidence_type") == "direct_application_id"),
            "A2_DOI_UKB_CROSSWALK": sum(1 for row in evidence_rows if row.get("evidence_type") == "A2_DOI_UKB_CROSSWALK"),
            "A3_PMID_UKB_CROSSWALK": sum(1 for row in evidence_rows if row.get("evidence_type") == "A3_PMID_UKB_CROSSWALK"),
            "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN": sum(1 for row in evidence_rows if row.get("evidence_type") == "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN"),
            "B1_AUTHOR_LAB_PROJECT_NAME_TOPIC_CONSISTENCY": sum(1 for row in evidence_rows if row.get("evidence_type") == "B1_AUTHOR_LAB_PROJECT_NAME_TOPIC_CONSISTENCY"),
            PROJECT_FAMILY_EVIDENCE_CLASS: sum(1 for row in evidence_rows if row.get("evidence_type") == PROJECT_FAMILY_EVIDENCE_CLASS),
            CONTENT_FINGERPRINT_EVIDENCE_CLASS: sum(1 for row in evidence_rows if row.get("evidence_type") == CONTENT_FINGERPRINT_EVIDENCE_CLASS),
        },
        "project_family_seed_rows": sum(1 for rows in seeds.values() for row in rows if "project_family_name" in row.get("_derived_seed_type", "")),
        "lineages_with_project_family_seeds": sum(
            1
            for rows in seeds.values()
            if any("project_family_name" in row.get("_derived_seed_type", "") for row in rows)
        ),
        "project_family_seed_matched_lineages": sum(
            1
            for lineage_id, rows in seeds.items()
            if any("project_family_name" in row.get("_derived_seed_type", "") for row in rows)
            and grade_by_lineage.get(lineage_id) in ("confirmed", "probable")
        ),
        "content_fingerprint_seed_rows": sum(1 for rows in seeds.values() for row in rows if "target_content_fingerprint" in row.get("_derived_seed_type", "")),
        "lineages_with_content_fingerprint_seeds": sum(
            1
            for rows in seeds.values()
            if any("target_content_fingerprint" in row.get("_derived_seed_type", "") for row in rows)
        ),
        "content_fingerprint_seed_matched_lineages": sum(
            1
            for lineage_id, rows in seeds.items()
            if any("target_content_fingerprint" in row.get("_derived_seed_type", "") for row in rows)
            and grade_by_lineage.get(lineage_id) in ("confirmed", "probable")
        ),
    })
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def apply_public_metadata_seeds(output_dir: Path, applications: Path) -> dict[str, Any]:
    seeds = _load_seeds(output_dir)
    apps = _parse_applications(applications)
    lineages, lineage_fields = _read_csv(output_dir / "ukb_dmca_lineages.csv")
    repos, repo_fields = _read_csv(output_dir / "ukb_dmca_repositories.csv")
    candidates, candidate_fields = _read_csv(output_dir / "ukb_dmca_application_candidates.csv")
    matches, match_fields = _read_csv(output_dir / "ukb_dmca_application_matches.csv")
    unresolved, unresolved_fields = _read_csv(output_dir / "ukb_dmca_unresolved.csv")
    manual, manual_fields = _read_csv(output_dir / "ukb_dmca_manual_review.csv")
    evidence, evidence_fields = _read_csv(output_dir / "ukb_dmca_application_match_evidence.csv")

    existing_anchor_seeds = _seed_like_rows_from_existing_matches(lineages, [*matches, *manual])
    if not seeds and not existing_anchor_seeds:
        return {"public_metadata_seed_rows": 0, "lineages_with_public_metadata_seeds": 0}
    target_exclude_lineage_ids = set(seeds) | set(existing_anchor_seeds)
    anchor_seeds = _merge_anchor_seed_rows(seeds, existing_anchor_seeds)
    derived_seeds = _merge_derived_seeds(
        _derive_project_family_seeds(lineages, anchor_seeds, target_exclude_lineage_ids),
        _derive_content_fingerprint_seeds(lineages, anchor_seeds, target_exclude_lineage_ids),
    )
    for lineage_id, rows in derived_seeds.items():
        seeds.setdefault(lineage_id, []).extend(rows)

    lineage_by_id = {row.get("lineage_id", ""): row for row in lineages}
    repos_by_lineage: dict[str, list[dict[str, str]]] = defaultdict(list)
    for repo in repos:
        repos_by_lineage[repo.get("lineage_id", "")].append(repo)

    applied_lineages: set[str] = set()
    seed_candidates: list[dict[str, Any]] = []
    seed_result_rows: list[dict[str, Any]] = []

    for lineage_id, rows in seeds.items():
        lineage = lineage_by_id.get(lineage_id)
        if not lineage:
            continue
        for seed in rows:
            app_id = _seed_app_id(seed)
            if not app_id:
                continue
            app = apps.get(app_id) or {
                "app_id": app_id,
                "title": _seed_value(seed, "application_title"),
                "pi": _seed_value(seed, "application_pi"),
                "institution": _seed_value(seed, "application_institution", "institution"),
            }
            _merge_seed_metadata(lineage, seed, app_id)
            for repo in repos_by_lineage.get(lineage_id, []):
                _merge_seed_metadata(repo, seed, app_id)
            candidate = _candidate_from_seed(lineage, app, seed)
            seed_candidates.append(candidate)
            seed_result_rows.extend(_result_rows_for_seed(repos_by_lineage.get(lineage_id, []), candidate, candidate["match_grade"]))
            evidence = [
                row for row in evidence
                if not (row.get("lineage_id") == lineage_id and row.get("candidate_app_id") == app_id and row.get("evidence_source") == "public_metadata_seed")
            ]
            for component in _parts(candidate["evidence_components"]):
                deterministic = component.startswith("A") or component == "direct_application_id"
                evidence.append({
                    "lineage_id": lineage_id,
                    "candidate_app_id": app_id,
                    "evidence_class": candidate["evidence_class"],
                    "evidence_type": component,
                    "evidence_value": candidate["score_details"],
                    "evidence_source": "public_metadata_seed",
                    "evidence_url": candidate["evidence_urls"],
                    "deterministic_or_fuzzy": "deterministic" if deterministic else "fuzzy",
                    "strength_level": candidate["evidence_level"],
                })
            _append_seed_audit(output_dir, lineage, rows, candidate)
            applied_lineages.add(lineage_id)

    if not seed_candidates:
        return {"public_metadata_seed_rows": sum(len(rows) for rows in seeds.values()), "applied_public_metadata_seed_rows": 0}

    seeded_pairs = {(row["lineage_id"], row["candidate_app_id"]) for row in seed_candidates}
    candidates = [
        row for row in candidates
        if not (
            row.get("lineage_id") in applied_lineages
            and (not row.get("candidate_app_id") or (row.get("lineage_id"), row.get("candidate_app_id")) in seeded_pairs)
        )
    ]
    candidates.extend(seed_candidates)
    candidates = _rerank_candidates(candidates)

    matches = [row for row in matches if row.get("lineage_id") not in applied_lineages]
    unresolved = [row for row in unresolved if row.get("lineage_id") not in applied_lineages]
    manual = [row for row in manual if row.get("lineage_id") not in applied_lineages]
    for row in seed_result_rows:
        if row.get("match_grade") in ("confirmed", "probable"):
            matches.append(row)
        else:
            unresolved.append(row)
        manual.append(row)

    _write_csv(output_dir / "ukb_dmca_lineages.csv", lineages, lineage_fields)
    _write_csv(output_dir / "ukb_dmca_repositories.csv", repos, repo_fields)
    _write_csv(output_dir / "ukb_dmca_application_candidates.csv", candidates, candidate_fields)
    _write_csv(output_dir / "ukb_dmca_application_matches.csv", matches, match_fields)
    _write_csv(output_dir / "ukb_dmca_unresolved.csv", unresolved, unresolved_fields or match_fields)
    _write_csv(output_dir / "ukb_dmca_manual_review.csv", manual, manual_fields or match_fields)
    _write_csv(output_dir / "ukb_dmca_application_match_evidence.csv", evidence, evidence_fields)
    return _summary_update(output_dir, manual, evidence, seeds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--applications", default="data/applications.tsv")
    args = parser.parse_args(argv)
    apply_public_metadata_seeds(Path(args.output_dir), Path(args.applications))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
