#!/usr/bin/env python3
"""Match UK Biobank website project start dates to Schema 27 applications.

Input:
- data/intermediate/stage2_universe/stage2_master_projects.csv
- data/raw/ukb_projects_website_listing.csv

The website listing does not expose Application ID directly. It exposes project
title, institution, URL, and start date. This script therefore uses strict,
auditable matching:
1. normalized title uniquely identifies one Schema 27 app_id;
2. if normalized title maps to multiple Schema 27 apps, normalized institution
   must identify exactly one of them.

No fuzzy matching is used here.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START_DATE_DIR = ROOT / "data" / "intermediate" / "start_date_matching"
MASTER = ROOT / "data" / "intermediate" / "stage2_universe" / "stage2_master_projects.csv"
WEBSITE_LISTING = ROOT / "data" / "raw" / "ukb_projects_website_listing.csv"
UNMATCHED_DETAIL_RESULTS = (
    START_DATE_DIR / "stage2_5_website_unmatched_detail_results.csv"
)

OUT_APP_DATES = START_DATE_DIR / "stage2_5_app_start_dates.csv"
OUT_WEBSITE_MATCHES = START_DATE_DIR / "stage2_5_website_listing_matches.csv"
OUT_WEBSITE_UNMATCHED = START_DATE_DIR / "stage2_5_website_unmatched.csv"
OUT_SCHEMA_UNMATCHED = START_DATE_DIR / "stage2_5_schema27_unmatched.csv"
OUT_YEAR_COUNTS = START_DATE_DIR / "stage2_5_start_year_counts.csv"
OUT_SUMMARY = START_DATE_DIR / "stage2_5_start_date_summary.json"
DETAIL_VALIDATION_PLAN = START_DATE_DIR / "stage2_5_detail_validation_plan.csv"
DETAIL_VALIDATION_RESULTS = (
    START_DATE_DIR / "stage2_5_detail_validation_results.csv"
)
REPORT = ROOT / "reports" / "stage2_5_start_dates.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def institution_variants(value: str) -> set[str]:
    """Return conservative website institution variants.

    UKB website institutions usually add a trailing country after a comma. We
    retain the full string and all comma-prefix variants so that institutions
    with internal commas can still match Schema 27 when possible.
    """
    parts = [p.strip() for p in (value or "").split(",")]
    variants = {normalize_text(value)}
    for i in range(1, len(parts) + 1):
        variants.add(normalize_text(", ".join(parts[:i])))
    if len(parts) > 1:
        variants.add(normalize_text(", ".join(parts[:-1])))
    return {v for v in variants if v}


def institution_matches(schema_institution: str, website_institution: str) -> bool:
    schema_norm = normalize_text(schema_institution)
    website_variants = institution_variants(website_institution)
    if not schema_norm:
        return False
    if schema_norm in website_variants:
        return True
    # Conservative containment handles suffixes such as country names and a
    # few punctuation/corporate suffix differences without using fuzzy scores.
    return any(schema_norm.startswith(v) or v.startswith(schema_norm) for v in website_variants)


def iso_date_from_datetime(value: str) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", value or "")
    return match.group(1) if match else ""


ADMIN_LIKE_RE = re.compile(
    r"\b(internal|test|testing|dummy|shadow|sample|training|basket|"
    r"RAP|DNAnexus|WGS|WES|Research Analysis Platform|exome verification|"
    r"vanguard|parabricks)\b",
    re.IGNORECASE,
)


def main() -> None:
    apps = read_csv(MASTER)
    web_rows = read_csv(WEBSITE_LISTING)
    unmatched_detail_by_url = {}
    if UNMATCHED_DETAIL_RESULTS.exists():
        unmatched_detail_by_url = {
            row["website_url"]: row for row in read_csv(UNMATCHED_DETAIL_RESULTS)
        }

    apps_by_title: dict[str, list[dict[str, str]]] = defaultdict(list)
    apps_by_id: dict[str, dict[str, str]] = {}
    for app in apps:
        apps_by_id[app["app_id"]] = app
        apps_by_title[normalize_text(app["title"])].append(app)

    website_match_rows: list[dict[str, object]] = []
    website_unmatched_rows: list[dict[str, object]] = []
    app_matches: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in web_rows:
        title_norm = normalize_text(row["title"])
        candidates = apps_by_title.get(title_norm, [])
        match_method = ""
        match_status = ""
        matched_app_id = ""
        matched_title = ""
        matched_institution = ""
        candidate_app_ids = "|".join(app["app_id"] for app in candidates)

        if len(candidates) == 1:
            match_status = "matched"
            match_method = "unique_normalized_title"
            matched = candidates[0]
            matched_app_id = matched["app_id"]
            matched_title = matched["title"]
            matched_institution = matched["institution"]
        elif len(candidates) > 1:
            institution_candidates = [
                app for app in candidates if institution_matches(app["institution"], row["institution"])
            ]
            if len(institution_candidates) == 1:
                match_status = "matched"
                match_method = "duplicate_title_resolved_by_institution"
                matched = institution_candidates[0]
                matched_app_id = matched["app_id"]
                matched_title = matched["title"]
                matched_institution = matched["institution"]
            else:
                match_status = "ambiguous_duplicate_title"
        else:
            match_status = "no_schema27_title_match"

        detail = unmatched_detail_by_url.get(row["url"])
        if not matched_app_id and detail:
            detail_app_id = detail.get("detail_app_id", "")
            if detail_app_id in apps_by_id:
                match_status = "matched"
                match_method = "detail_page_app_id_after_title_unmatched_or_ambiguous"
                matched = apps_by_id[detail_app_id]
                matched_app_id = matched["app_id"]
                matched_title = matched["title"]
                matched_institution = matched["institution"]
            elif detail_app_id:
                match_status = "website_detail_app_id_not_in_schema27"
                candidate_app_ids = detail_app_id

        output_row = {
            "website_page": row["page"],
            "website_index_on_page": row["index_on_page"],
            "website_start_date": iso_date_from_datetime(row["start_date_datetime"]),
            "website_start_date_text": row["start_date_text"],
            "website_title": row["title"],
            "website_institution": row["institution"],
            "website_url": row["url"],
            "match_status": match_status,
            "match_method": match_method,
            "matched_app_id": matched_app_id,
            "schema27_title": matched_title,
            "schema27_institution": matched_institution,
            "candidate_app_ids": candidate_app_ids,
        }
        website_match_rows.append(output_row)
        if matched_app_id:
            app_matches[matched_app_id].append(output_row)
        else:
            website_unmatched_rows.append(output_row)

    app_date_rows: list[dict[str, object]] = []
    for app in apps:
        matches = app_matches.get(app["app_id"], [])
        unique_dates = sorted({m["website_start_date"] for m in matches if m["website_start_date"]})
        unique_urls = sorted({m["website_url"] for m in matches if m["website_url"]})
        unique_website_titles = sorted({m["website_title"] for m in matches if m["website_title"]})
        match_methods = sorted({m["match_method"] for m in matches if m["match_method"]})
        if len(matches) == 0:
            status = "unmatched_schema27"
        elif len(unique_dates) == 1 and len(unique_urls) == 1:
            status = "matched_one_website_record"
        else:
            status = "matched_multiple_website_records_or_dates"
        app_date_rows.append(
            {
                "app_id": app["app_id"],
                "schema27_title": app["title"],
                "schema27_institution": app["institution"],
                "schema27_pi": app["pi"],
                "website_match_status": status,
                "website_match_count": len(matches),
                "start_date": unique_dates[0] if len(unique_dates) == 1 else "",
                "start_dates_all": "|".join(unique_dates),
                "website_url": unique_urls[0] if len(unique_urls) == 1 else "",
                "website_urls_all": "|".join(unique_urls),
                "website_titles_all": "|".join(unique_website_titles),
                "match_methods": "|".join(match_methods),
            }
        )

    schema_unmatched_rows = [row for row in app_date_rows if row["website_match_status"] == "unmatched_schema27"]
    matched_app_rows = [row for row in app_date_rows if row["website_match_status"] != "unmatched_schema27"]
    apps_with_start_date = [row for row in app_date_rows if row["start_date"]]

    year_counts = Counter(row["start_date"][:4] for row in apps_with_start_date if row["start_date"])
    year_count_rows = [
        {"start_year": year, "applications": count} for year, count in sorted(year_counts.items())
    ]

    website_status_counts = Counter(row["match_status"] for row in website_match_rows)
    app_status_counts = Counter(row["website_match_status"] for row in app_date_rows)

    schema_unmatched_admin_like = [
        row
        for row in schema_unmatched_rows
        if row["schema27_institution"] in {"UK Biobank Ltd", "University of Oxford"}
        or ADMIN_LIKE_RE.search(str(row["schema27_title"]))
    ]
    schema_unmatched_non_admin_like = [
        row for row in schema_unmatched_rows if row not in schema_unmatched_admin_like
    ]

    validation_summary = {}
    if DETAIL_VALIDATION_RESULTS.exists():
        validation_rows = read_csv(DETAIL_VALIDATION_RESULTS)
        validation_matched = [row for row in validation_rows if row.get("matched_app_id")]
        validation_summary = {
            "detail_validation_rows": len(validation_rows),
            "detail_validation_fetch_errors": sum(
                1 for row in validation_rows if row.get("detail_fetch_status") != "ok"
            ),
            "detail_validation_matched_rows": len(validation_matched),
            "detail_validation_id_mismatches": sum(
                1 for row in validation_matched if row.get("id_matches_matched_app_id") == "false"
            ),
            "detail_validation_start_date_mismatches": sum(
                1
                for row in validation_rows
                if row.get("start_date_matches_listing") == "false"
            ),
        }

    summary = {
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "schema27_unique_applications": len(apps),
        "website_listing_rows": len(web_rows),
        "website_listing_unique_urls": len({row["url"] for row in web_rows}),
        "website_listing_rows_with_start_date": sum(1 for row in web_rows if row["start_date_datetime"]),
        "website_match_status_counts": dict(website_status_counts),
        "schema27_app_match_status_counts": dict(app_status_counts),
        "schema27_apps_matched_to_website": len(matched_app_rows),
        "schema27_apps_with_single_start_date": len(apps_with_start_date),
        "schema27_apps_unmatched_to_website": len(schema_unmatched_rows),
        "website_unmatched_detail_results_used": UNMATCHED_DETAIL_RESULTS.exists(),
        "schema27_unmatched_admin_or_service_like": len(schema_unmatched_admin_like),
        "schema27_unmatched_other": len(schema_unmatched_non_admin_like),
        **validation_summary,
        "start_year_min": min(year_counts) if year_counts else "",
        "start_year_max": max(year_counts) if year_counts else "",
        "start_year_counts": dict(sorted(year_counts.items())),
    }

    write_csv(
        OUT_WEBSITE_MATCHES,
        website_match_rows,
        [
            "website_page",
            "website_index_on_page",
            "website_start_date",
            "website_start_date_text",
            "website_title",
            "website_institution",
            "website_url",
            "match_status",
            "match_method",
            "matched_app_id",
            "schema27_title",
            "schema27_institution",
            "candidate_app_ids",
        ],
    )
    write_csv(
        OUT_WEBSITE_UNMATCHED,
        website_unmatched_rows,
        [
            "website_page",
            "website_index_on_page",
            "website_start_date",
            "website_start_date_text",
            "website_title",
            "website_institution",
            "website_url",
            "match_status",
            "match_method",
            "matched_app_id",
            "schema27_title",
            "schema27_institution",
            "candidate_app_ids",
        ],
    )
    write_csv(
        OUT_APP_DATES,
        app_date_rows,
        [
            "app_id",
            "schema27_title",
            "schema27_institution",
            "schema27_pi",
            "website_match_status",
            "website_match_count",
            "start_date",
            "start_dates_all",
            "website_url",
            "website_urls_all",
            "website_titles_all",
            "match_methods",
        ],
    )
    write_csv(
        OUT_SCHEMA_UNMATCHED,
        schema_unmatched_rows,
        [
            "app_id",
            "schema27_title",
            "schema27_institution",
            "schema27_pi",
            "website_match_status",
            "website_match_count",
            "start_date",
            "start_dates_all",
            "website_url",
            "website_urls_all",
            "website_titles_all",
            "match_methods",
        ],
    )
    write_csv(OUT_YEAR_COUNTS, year_count_rows, ["start_year", "applications"])
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    report = f"""# Stage 2.5 Project Start Dates

Goal: recover `app_id -> start_date` from the UK Biobank Existing projects website.

## Scraping Route

- Listing route: `https://www.ukbiobank.ac.uk/projects/?_paged=N`
- The page is server-rendered and exposes project start date, title, URL, and
  institution in each listing card.
- The listing page reports `{len(web_rows):,}` results.
- Direct command-line requests to the UKB main website are blocked by Cloudflare,
  and WordPress REST URLs were not usable in the browser environment. The
  server-rendered paged listing is the stable route used here.

## Matching Rule

- Match website listing rows to Schema 27 by normalized title when the title is
  unique in Schema 27.
- If a normalized title maps to multiple Schema 27 applications, resolve only
  when normalized institution uniquely identifies one candidate.
- For rows still unmatched or ambiguous after title/institution matching, use
  the project detail page `ID` when available. This was applied only to the
  small boundary set, not to every already-matched row.
- No fuzzy matching is used.

## Summary

- Schema 27 unique applications: {len(apps):,}
- Website listing rows: {len(web_rows):,}
- Website listing rows with start date: {sum(1 for row in web_rows if row["start_date_datetime"]):,}
- Schema 27 applications matched to website: {len(matched_app_rows):,}
- Schema 27 applications with a single recovered start date: {len(apps_with_start_date):,}
- Schema 27 applications unmatched to website: {len(schema_unmatched_rows):,}
- Start year range among recovered dates: {summary["start_year_min"]}-{summary["start_year_max"]}

## Validation

- Detail validation rows: {validation_summary.get("detail_validation_rows", 0):,}
- Detail validation fetch errors: {validation_summary.get("detail_validation_fetch_errors", 0):,}
- Matched validation rows with detail `ID`: {validation_summary.get("detail_validation_matched_rows", 0):,}
- Detail `ID` mismatches against matched Schema 27 app_id: {validation_summary.get("detail_validation_id_mismatches", 0):,}
- Detail/listing start-date mismatches: {validation_summary.get("detail_validation_start_date_mismatches", 0):,}

## Remaining Unmatched Pattern

- Schema 27 unmatched applications: {len(schema_unmatched_rows):,}
- Admin/service-like unmatched applications: {len(schema_unmatched_admin_like):,}
- Other unmatched applications: {len(schema_unmatched_non_admin_like):,}
- Website projects not in current Schema 27 after detail-page ID check: {len(website_unmatched_rows):,}

## Produced Files

- `{OUT_APP_DATES.relative_to(ROOT)}`
- `{OUT_WEBSITE_MATCHES.relative_to(ROOT)}`
- `{OUT_WEBSITE_UNMATCHED.relative_to(ROOT)}`
- `{OUT_SCHEMA_UNMATCHED.relative_to(ROOT)}`
- `{OUT_YEAR_COUNTS.relative_to(ROOT)}`
- `{OUT_SUMMARY.relative_to(ROOT)}`
- `{UNMATCHED_DETAIL_RESULTS.relative_to(ROOT)}`
- `{DETAIL_VALIDATION_PLAN.relative_to(ROOT)}`
- `{DETAIL_VALIDATION_RESULTS.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
