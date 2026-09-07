#!/usr/bin/env python3
"""Build an exhaustive DMCA repository-to-application attribution table.

This script starts from the current ukb_dmca state. It does not discover new
notices, fetch repositories, or rerun the matching pipeline. Instead it
consolidates the current curated 52-link application baseline with every
retained application candidate in the existing DMCA candidate/evidence files.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UKB = ROOT / "ukb_dmca"

LINEAGES = UKB / "ukb_dmca_lineages.csv"
REPOSITORIES = UKB / "ukb_dmca_repositories.csv"
CANDIDATES = UKB / "ukb_dmca_application_candidates.csv"
CURATED_APPS = UKB / "curated_dmca_application_links.csv"
CURATED_FAMILIES = UKB / "curated_dmca_repository_family_links.csv"

OUT_CSV = UKB / "exhaustive_dmca_application_attribution.csv"
OUT_FAMILY_CSV = UKB / "exhaustive_dmca_family_attribution_summary.csv"
OUT_REPORT = UKB / "exhaustive_dmca_application_attribution_report.md"
OUT_SUMMARY = UKB / "exhaustive_dmca_application_attribution_summary.json"

GENERIC_REPO_FAMILY_NAMES = {"001", "data", "ukb", "ukbb", "ukbiobank"}
MANUAL_EXCLUDED_AUTOMATED_APP_IDS = {"29256"}


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def split_parts(value: str) -> list[str]:
    parts: list[str] = []
    for chunk in re.split(r";|\|", clean(value)):
        item = clean(chunk)
        if item and item not in parts:
            parts.append(item)
    return parts


def uniq(values: list[str]) -> str:
    out: list[str] = []
    for value in values:
        for part in split_parts(value):
            if part not in out:
                out.append(part)
    return "; ".join(out)


def repo_basename(source_repo: str) -> str:
    value = clean(source_repo).split("/", 1)[-1].lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "unknown"


def family_id_for_lineage(lineage: dict[str, str]) -> str:
    basename = repo_basename(lineage.get("source_repo", ""))
    if basename in GENERIC_REPO_FAMILY_NAMES:
        suffix = clean(lineage["lineage_id"]).removeprefix("lineage_")
        return f"family_{suffix}"
    return f"family_{basename}"


def evidence_type(value: str) -> str:
    parts = set(split_parts(value))
    labels: list[str] = []
    if "A1_DIRECT_APP_ID" in parts:
        labels.append("direct UKB application number")
    if "A2_DOI_UKB_CROSSWALK" in parts or "A3_PMID_UKB_CROSSWALK" in parts:
        labels.append("repository-linked DOI/PMID to UKB publication/application crosswalk")
    if "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN" in parts:
        labels.append("exact repository-publication-application chain")
    if any(part.startswith("B1") for part in parts):
        labels.append("author/lab/project/topic consistency")
    if any(part.startswith("B2") for part in parts):
        labels.append("same project-family propagation")
    if any(part.startswith("B3") for part in parts):
        labels.append("same target-content fingerprint propagation")
    if "B" in parts:
        labels.append("supporting identity/topic evidence")
    if "C" in parts:
        labels.append("weak topic/path/data-type evidence")
    return "; ".join(labels) if labels else clean(value)


def classify_candidate(row: dict[str, str]) -> tuple[str, str, str]:
    raw_grade = clean(row.get("match_grade", ""))
    level = clean(row.get("evidence_level", ""))
    rank = clean(row.get("candidate_rank", ""))
    if raw_grade == "confirmed":
        return "confirmed", "high", "current automated confirmed match"
    if raw_grade == "probable":
        return "probable", "medium_high", "current automated probable match"
    if raw_grade == "ambiguous":
        return "ambiguous", "medium", "current automated ambiguous match"
    if level == "A":
        return "ambiguous", "medium", "A-level alternative retained for exhaustive attribution"
    if level == "B":
        return "candidate", "low_to_medium", "B-level alternative retained for exhaustive attribution"
    if rank == "1":
        return "weak_candidate", "low", "top weak automated candidate retained for transparency"
    return "weak_candidate", "very_low", "lower-ranked weak automated candidate retained for transparency"


def source_repo_parts(value: str) -> tuple[str, str]:
    source = split_parts(value)
    if not source or "/" not in source[0]:
        return "", ""
    return tuple(source[0].split("/", 1))  # type: ignore[return-value]


def build_rows() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    lineages = read_csv(LINEAGES)
    repositories = read_csv(REPOSITORIES)
    candidates = read_csv(CANDIDATES)
    curated_apps = read_csv(CURATED_APPS)
    curated_families = read_csv(CURATED_FAMILIES)

    lineage_by_id = {row["lineage_id"]: row for row in lineages}
    family_by_lineage = {row["lineage_id"]: family_id_for_lineage(row) for row in lineages}
    curated_app_ids = {row["application_id"] for row in curated_apps}
    curated_family_app_pairs: set[tuple[str, str]] = set()
    for row in curated_families:
        for app_id in split_parts(row.get("application_id", "")):
            curated_family_app_pairs.add((row["family_id"], app_id))

    repos_by_lineage: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in repositories:
        repos_by_lineage[row["lineage_id"]].append(row)

    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add_row(row: dict[str, object]) -> None:
        key = (
            clean(row.get("family_id")),
            clean(row.get("lineage_id")),
            clean(row.get("repo_url")),
            clean(row.get("application_id")),
        )
        if key in seen:
            return
        seen.add(key)
        rows.append(row)

    for app in curated_apps:
        app_id = app["application_id"]
        family_ids = split_parts(app.get("linked_repository_family_ids", ""))
        lineage_ids = split_parts(app.get("lineage_ids", ""))
        status = "confirmed" if app["manual_confirmation_status"] == "confirmed_by_researcher" else "probable"
        confidence = "researcher_confirmed" if status == "confirmed" else "manual_review_probable"
        if lineage_ids:
            for lineage_id in lineage_ids:
                lineage = lineage_by_id.get(lineage_id, {})
                family_id = family_by_lineage.get(lineage_id) or (family_ids[0] if family_ids else "")
                repo_urls = split_parts(lineage.get("repo_urls", "")) or split_parts(app.get("linked_repo_urls", ""))
                if not repo_urls:
                    repo_urls = [""]
                owner, repo_name = source_repo_parts(lineage.get("source_repo", ""))
                for repo_url in repo_urls:
                    add_row(
                        {
                            "family_id": family_id,
                            "lineage_id": lineage_id,
                            "repo_url": repo_url,
                            "repo_owner": owner,
                            "repo_name": repo_name,
                            "application_id": app_id,
                            "application_title": app.get("application_title", ""),
                            "matching_status": status,
                            "confidence": confidence,
                            "confidence_group": status,
                            "evidence_level": "manual",
                            "evidence_type": app.get("evidence_classes", ""),
                            "doi": app.get("doi", ""),
                            "pmid": app.get("pmid", ""),
                            "paper_title": app.get("publication_title", ""),
                            "author_pi_institution_evidence": uniq([app.get("application_pi", ""), app.get("application_institution", "")]),
                            "evidence_urls": uniq([app.get("linked_repo_urls", "")]),
                            "reviewer_notes": app.get("reviewer_explanation", ""),
                            "existing_or_new_match": "existing_curated_52",
                            "new_unique_beyond_current_52": 0,
                            "candidate_rank": "",
                            "match_score": "",
                            "raw_match_grade": app.get("match_grades", ""),
                            "lineage_source_repo": lineage.get("source_repo", ""),
                        }
                    )
        else:
            add_row(
                {
                    "family_id": f"application_only_curated_app_{app_id}",
                    "lineage_id": "",
                    "repo_url": "",
                    "repo_owner": "",
                    "repo_name": "",
                    "application_id": app_id,
                    "application_title": app.get("application_title", ""),
                    "matching_status": status,
                    "confidence": confidence,
                    "confidence_group": status,
                    "evidence_level": "manual_application_only",
                    "evidence_type": app.get("evidence_classes", ""),
                    "doi": app.get("doi", ""),
                    "pmid": app.get("pmid", ""),
                    "paper_title": app.get("publication_title", ""),
                    "author_pi_institution_evidence": uniq([app.get("application_pi", ""), app.get("application_institution", "")]),
                    "evidence_urls": app.get("linked_repo_urls", ""),
                    "reviewer_notes": app.get("reviewer_explanation", ""),
                    "existing_or_new_match": "existing_curated_52_application_only",
                    "new_unique_beyond_current_52": 0,
                    "candidate_rank": "",
                    "match_score": "",
                    "raw_match_grade": app.get("match_grades", ""),
                    "lineage_source_repo": "",
                }
            )

    for candidate in candidates:
        app_id = clean(candidate.get("candidate_app_id", ""))
        lineage_id = clean(candidate.get("lineage_id", ""))
        if not app_id or not lineage_id:
            continue
        lineage = lineage_by_id.get(lineage_id, {})
        family_id = family_by_lineage.get(lineage_id, "")
        status, confidence, note = classify_candidate(candidate)
        if app_id in MANUAL_EXCLUDED_AUTOMATED_APP_IDS:
            status = "excluded_false_positive"
            confidence = "manual_exclusion"
            note = "Automated 29256 propagation is retained for audit but excluded from supported attribution by prior manual review."
        existing_or_new = "existing_52_application_candidate_evidence" if app_id in curated_app_ids else "new_exhaustive_attribution_candidate"
        if (family_id, app_id) in curated_family_app_pairs:
            existing_or_new = "existing_curated_52"
        repo_urls = split_parts(lineage.get("repo_urls", ""))
        if not repo_urls:
            repo_urls = [""]
        owner, repo_name = source_repo_parts(lineage.get("source_repo", ""))
        for repo_url in repo_urls:
            add_row(
                {
                    "family_id": family_id,
                    "lineage_id": lineage_id,
                    "repo_url": repo_url,
                    "repo_owner": owner,
                    "repo_name": repo_name,
                    "application_id": app_id,
                    "application_title": candidate.get("application_title", ""),
                    "matching_status": status,
                    "confidence": confidence,
                    "confidence_group": status,
                    "evidence_level": candidate.get("evidence_level", ""),
                    "evidence_type": evidence_type(candidate.get("evidence_class", "")),
                    "doi": uniq([candidate.get("crosswalk_evidence", ""), lineage.get("doi", ""), lineage.get("repo_linked_doi", "")]),
                    "pmid": uniq([lineage.get("pubmed_id", ""), lineage.get("repo_linked_pmid", "")]),
                    "paper_title": uniq([lineage.get("paper_title", ""), lineage.get("repo_linked_publication_title", "")]),
                    "author_pi_institution_evidence": uniq(
                        [
                            candidate.get("application_pi", ""),
                            candidate.get("application_institution", ""),
                            lineage.get("paper_authors", ""),
                            lineage.get("repo_owner_public_name", ""),
                            lineage.get("repo_owner_public_company", ""),
                        ]
                    ),
                    "evidence_urls": uniq([candidate.get("evidence_urls", ""), lineage.get("evidence_urls", "")]),
                    "reviewer_notes": uniq([note, candidate.get("match_reason", "")]),
                    "existing_or_new_match": existing_or_new,
                    "new_unique_beyond_current_52": int(app_id not in curated_app_ids),
                    "candidate_rank": candidate.get("candidate_rank", ""),
                    "match_score": candidate.get("match_score", ""),
                    "raw_match_grade": candidate.get("match_grade", ""),
                    "lineage_source_repo": lineage.get("source_repo", ""),
                }
            )

    all_family_ids = {family_id_for_lineage(row) for row in lineages}
    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if clean(row.get("lineage_id")):
            by_family[clean(row["family_id"])].append(row)

    supported_statuses = {"confirmed", "probable", "ambiguous", "candidate"}
    family_rows: list[dict[str, object]] = []
    for family_id in sorted(all_family_ids):
        fam_rows = by_family.get(family_id, [])
        apps = {clean(row["application_id"]) for row in fam_rows if clean(row.get("application_id"))}
        supported_rows = [row for row in fam_rows if clean(row.get("matching_status")) in supported_statuses]
        supported_apps = {clean(row["application_id"]) for row in supported_rows if clean(row.get("application_id"))}
        status_counts = Counter(clean(row.get("matching_status")) for row in fam_rows)
        if supported_apps:
            family_status = "ambiguous_multi_application" if len(supported_apps) > 1 else clean(supported_rows[0].get("matching_status"))
        elif apps:
            family_status = "weak_candidate_only"
        else:
            family_status = "unresolved_no_candidate"
        source_repos = uniq([clean(lineage_by_id.get(clean(row.get("lineage_id")), {}).get("source_repo", "")) for row in fam_rows])
        lineage_ids = sorted({clean(row["lineage_id"]) for row in fam_rows if clean(row.get("lineage_id"))})
        family_rows.append(
            {
                "family_id": family_id,
                "family_status": family_status,
                "lineage_count": len(lineage_ids),
                "lineage_ids": "; ".join(lineage_ids),
                "source_repositories": source_repos,
                "candidate_application_count": len(apps),
                "supported_or_ambiguous_application_count": len(supported_apps),
                "candidate_application_ids": "; ".join(sorted(apps, key=lambda value: int(value) if value.isdigit() else 10**12)),
                "supported_or_ambiguous_application_ids": "; ".join(sorted(supported_apps, key=lambda value: int(value) if value.isdigit() else 10**12)),
                "confirmed_rows": status_counts["confirmed"],
                "probable_rows": status_counts["probable"],
                "ambiguous_rows": status_counts["ambiguous"],
                "candidate_rows": status_counts["candidate"],
                "weak_candidate_rows": status_counts["weak_candidate"],
                "new_unique_candidate_count_beyond_52": len(apps - curated_app_ids),
            }
        )

    rows.sort(
        key=lambda row: (
            clean(row["family_id"]),
            clean(row["lineage_id"]),
            0 if clean(row["matching_status"]) == "confirmed" else 1 if clean(row["matching_status"]) == "probable" else 2 if clean(row["matching_status"]) == "ambiguous" else 3,
            int(clean(row.get("candidate_rank")) or "999999"),
            clean(row["application_id"]),
        )
    )

    supported_rows = [row for row in rows if clean(row.get("matching_status")) in supported_statuses]
    all_candidate_apps = {
        clean(row["application_id"])
        for row in rows
        if clean(row.get("application_id")) and clean(row.get("matching_status")) != "excluded_false_positive"
    }
    supported_apps = {clean(row["application_id"]) for row in supported_rows if clean(row.get("application_id"))}
    family_status_counts = Counter(clean(row["family_status"]) for row in family_rows)
    summary = {
        "total_dmca_repository_rows": len(repositories),
        "total_dmca_unique_repo_urls": len({row["repo_url"] for row in repositories if clean(row.get("repo_url"))}),
        "total_dmca_lineages": len(lineages),
        "total_repository_families": len(all_family_ids),
        "total_families_reviewed": len(all_family_ids),
        "families_linked_to_at_least_one_application_supported_or_ambiguous": sum(1 for row in family_rows if int(row["supported_or_ambiguous_application_count"]) > 0),
        "families_with_any_retained_candidate_including_weak": sum(1 for row in family_rows if int(row["candidate_application_count"]) > 0),
        "confirmed_links": sum(1 for row in rows if clean(row["matching_status"]) == "confirmed"),
        "probable_links": sum(1 for row in rows if clean(row["matching_status"]) == "probable"),
        "candidate_links": sum(1 for row in rows if clean(row["matching_status"]) == "candidate"),
        "excluded_false_positive_rows": sum(1 for row in rows if clean(row["matching_status"]) == "excluded_false_positive"),
        "ambiguous_multi_application_families": family_status_counts["ambiguous_multi_application"],
        "weak_candidate_only_families": family_status_counts["weak_candidate_only"],
        "unresolved_families_no_candidate": family_status_counts["unresolved_no_candidate"],
        "unresolved_families_without_supported_or_ambiguous_link": family_status_counts["weak_candidate_only"] + family_status_counts["unresolved_no_candidate"],
        "total_unique_applications_identified_supported_or_ambiguous": len(supported_apps),
        "total_unique_applications_identified_including_weak": len(all_candidate_apps),
        "current_curated_application_baseline": len(curated_app_ids),
        "new_unique_applications_beyond_current_52_supported_or_ambiguous": len(supported_apps - curated_app_ids),
        "new_unique_applications_beyond_current_52_including_weak": len(all_candidate_apps - curated_app_ids),
        "attribution_row_count": len(rows),
        "family_status_counts": dict(family_status_counts),
        "row_status_counts": dict(Counter(clean(row["matching_status"]) for row in rows)),
    }
    return rows, family_rows, summary


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |"]
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(clean(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def write_report(family_rows: list[dict[str, object]], summary: dict[str, object]) -> None:
    status_rows = [{"metric": key, "value": value} for key, value in summary.items() if key not in {"family_status_counts", "row_status_counts"}]
    family_counts = [{"status": key, "families": value} for key, value in sorted(summary["family_status_counts"].items())]
    row_counts = [{"status": key, "rows": value} for key, value in sorted(summary["row_status_counts"].items())]
    linked_preview = [
        row
        for row in family_rows
        if clean(row["family_status"]) not in {"weak_candidate_only", "unresolved_no_candidate"}
    ][:40]
    report = f"""# Exhaustive DMCA Application Attribution Report

## Scope

This report expands the application-attribution layer across the full current
DMCA repository universe without restarting the DMCA matching pipeline. It
preserves the existing 52 application-level leakage-risk links and adds an
exhaustive candidate table from the already harvested public README, metadata,
publication, crosswalk, fork/source, and Wayback evidence.

The canonical empirical leakage sample remains
`ukb_dmca/curated_dmca_application_links.csv`. The exhaustive table is broader:
it includes confirmed, probable, ambiguous, B-level candidate, and weak candidate attributions so
coverage can be inspected without hiding uncertainty.

## Summary

{markdown_table(status_rows, ["metric", "value"])}

## Family Status Counts

{markdown_table(family_counts, ["status", "families"])}

## Attribution Row Counts

{markdown_table(row_counts, ["status", "rows"])}

## Strong Or Ambiguous Family Preview

The full family table is saved at
`ukb_dmca/exhaustive_dmca_family_attribution_summary.csv`.

{markdown_table(linked_preview, ["family_id", "family_status", "lineage_count", "supported_or_ambiguous_application_count", "supported_or_ambiguous_application_ids", "candidate_application_count", "new_unique_candidate_count_beyond_52"])}

## Interpretation

- `confirmed`, `probable`, `ambiguous`, and `candidate` rows are the supported
  attribution layer. `candidate` rows retain B-level alternatives without
  promoting them to true probable links.
- `weak_candidate` rows are retained for coverage and auditability, but they
  are not treated as confirmed/probable empirical leakage links.
- Existing 52 curated applications are marked with `existing_curated_52` or
  `existing_curated_52_application_only`.
- New candidate application IDs beyond the 52 are marked with
  `new_unique_beyond_current_52=1`.
- Multiple plausible applications for the same family are preserved rather
  than collapsed to a single forced assignment.
"""
    write_text(OUT_REPORT, report)


def main() -> None:
    rows, family_rows, summary = build_rows()
    row_fields = [
        "family_id",
        "lineage_id",
        "repo_url",
        "repo_owner",
        "repo_name",
        "application_id",
        "application_title",
        "matching_status",
        "confidence",
        "confidence_group",
        "evidence_level",
        "evidence_type",
        "doi",
        "pmid",
        "paper_title",
        "author_pi_institution_evidence",
        "evidence_urls",
        "reviewer_notes",
        "existing_or_new_match",
        "new_unique_beyond_current_52",
        "candidate_rank",
        "match_score",
        "raw_match_grade",
        "lineage_source_repo",
    ]
    family_fields = [
        "family_id",
        "family_status",
        "lineage_count",
        "lineage_ids",
        "source_repositories",
        "candidate_application_count",
        "supported_or_ambiguous_application_count",
        "candidate_application_ids",
        "supported_or_ambiguous_application_ids",
        "confirmed_rows",
        "probable_rows",
        "ambiguous_rows",
        "candidate_rows",
        "weak_candidate_rows",
        "new_unique_candidate_count_beyond_52",
    ]
    write_csv(OUT_CSV, rows, row_fields)
    write_csv(OUT_FAMILY_CSV, family_rows, family_fields)
    write_text(OUT_SUMMARY, json.dumps(summary, indent=2, sort_keys=True))
    write_report(family_rows, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
