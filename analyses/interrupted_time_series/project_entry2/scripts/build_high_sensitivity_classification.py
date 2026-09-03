#!/usr/bin/env python3
"""Build project-level high-sensitivity proxies for project-entry ITS.

The module intentionally keeps this analysis separate from the existing
project_entry and comparative_exposure outputs. It reuses their upstream
project-level inputs but writes only under project_entry2.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA_DIR = PACKAGE / "data"
REPORT_DIR = PACKAGE / "reports"
SNAPSHOT_DIR = DATA_DIR / "source_snapshots"
FIELD_PAGE_DIR = SNAPSHOT_DIR / "field_pages"

PROJECT_UNIVERSE = (
    ROOT
    / "data"
    / "intermediate"
    / "timing_feasibility"
    / "timing_working_research_project_universe.csv"
)
STAGE3_CLASSIFICATION = (
    ROOT
    / "data"
    / "intermediate"
    / "rap_classification"
    / "stage3_project_rap_exposure_classification.csv"
)
CONTROL_EXPANSION_REVIEW = (
    ROOT
    / "data"
    / "intermediate"
    / "control_expansion"
    / "stage3_control_expansion_project_review.csv"
)
CONTROL_EXPANSION_DICTIONARY = (
    ROOT
    / "data"
    / "intermediate"
    / "control_expansion"
    / "stage3_control_expansion_evidence_dictionary.csv"
)

SCHEMA1_URL = "https://biobank.ndph.ox.ac.uk/ukb/scdown.cgi?fmt=txt&id=1"
FIELD_URL_TEMPLATE = "https://biobank.ndph.ox.ac.uk/ukb/field.cgi?id={field_id}"
POLICY_DATE = date(2024, 7, 5)

CONTROL_ORDER = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5, "C6": 6}
C03_LAYERS = {"C0", "C1", "C2", "C3"}
C05_LAYERS = {"C0", "C1", "C2", "C3", "C4", "C5"}
LOW_STRICT_MODALITIES = {
    "QUESTIONNAIRES_ASSESSMENT",
    "PHYSICAL_MEASURES",
    "ENVIRONMENT_GEOSPATIAL",
}
FIELD_FETCH_USER_AGENT = (
    "Mozilla/5.0 (compatible; UKB-empirical-project-entry2/1.0; "
    "research pipeline contact: public-source-audit)"
)


@dataclass(frozen=True)
class Outputs:
    classification: Path = DATA_DIR / "project_high_sensitivity_classification.csv"
    application_field_links: Path = DATA_DIR / "application_field_tier_links.csv"
    field_tier_distribution: Path = DATA_DIR / "field_tier_distribution.csv"
    classification_counts: Path = DATA_DIR / "classification_counts.csv"
    classification_overlap: Path = DATA_DIR / "classification_overlap.csv"
    source_manifest: Path = SNAPSHOT_DIR / "source_manifest.json"
    field_fetch_log: Path = SNAPSHOT_DIR / "field_fetch_log.csv"
    schema_snapshot: Path = SNAPSHOT_DIR / "ukb_schema1_fields.tsv"


def clean(value: object) -> str:
    return str(value or "").strip()


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_date(value: str) -> date | None:
    value = clean(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y"):
        try:
            parsed = datetime.strptime(value[:19] if "T" in value else value[:10], fmt).date()
            return date(parsed.year, 1, 1) if fmt == "%Y" else parsed
        except ValueError:
            continue
    return None


def fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f"{value:.{digits}f}"
    return str(value)


def yes(value: bool) -> int:
    return 1 if value else 0


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fetch_url(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": FIELD_FETCH_USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def ensure_schema_snapshot(path: Path, refresh: bool = False) -> bool:
    if path.exists() and not refresh:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fetch_url(SCHEMA1_URL))
    return True


def strip_tags(fragment: str) -> str:
    text = re.sub(r"(?i)<\s*(br|p|/p|/tr|/td|/th)\b[^>]*>", " ", fragment)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def tier_tokens(row: dict[str, str]) -> tuple[str, ...]:
    if clean(row.get("tier")):
        tokens = re.findall(r"[dos]\d+", clean(row["tier"]).lower())
        return tuple(dict.fromkeys(tokens))
    tokens: list[str] = []
    for prefix, col in [("d", "cost_do"), ("o", "cost_on"), ("s", "cost_sc")]:
        raw = clean(row.get(col))
        if not raw:
            continue
        try:
            value = int(float(raw))
        except ValueError:
            continue
        if value > 0:
            tokens.append(f"{prefix}{value}")
    return tuple(tokens)


def parse_field_schema(schema_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in read_csv(schema_path, delimiter="\t"):
        tokens = tier_tokens(row)
        field_id = clean(row.get("field_id"))
        if not field_id:
            continue
        rows.append(
            {
                "field_id": field_id,
                "field_title": clean(row.get("title")),
                "field_tier": " ".join(tokens),
                "tier_source": "schema1_cost_do_cost_on_cost_sc",
                "has_s3": yes("s3" in tokens),
                "has_o2": yes("o2" in tokens),
                "field_private": yes(clean(row.get("private")) == "1"),
                "item_type": clean(row.get("item_type")),
                "main_category": clean(row.get("main_category")),
                "debut": clean(row.get("debut")),
                "version": clean(row.get("version")),
                "cost_do": clean(row.get("cost_do")),
                "cost_on": clean(row.get("cost_on")),
                "cost_sc": clean(row.get("cost_sc")),
                "num_participants": clean(row.get("num_participants")),
                "item_count": clean(row.get("item_count")),
                "field_notes": strip_tags(clean(row.get("notes"))),
            }
        )
    return rows


def parse_field_applications(page_html: str) -> list[dict[str, str]]:
    """Parse Application IDs from a UKB field page.

    The validation case in the task is field 25749, whose page currently has
    tier "o2 s3" and application links 17689 and 22783.
    """
    application_tab = page_html
    match = re.search(
        r"(?is)<h2>\s*\d+\s+Applications\s*</h2>(?P<body>.*?)(?:</table>|</div>)",
        page_html,
    )
    if match:
        application_tab = match.group("body")

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for row_match in re.finditer(r"(?is)<tr[^>]*>(?P<body>.*?)</tr>", application_tab):
        body = row_match.group("body")
        app_match = re.search(r"app\.cgi\?id=(?P<app_id>\d+)", body)
        if not app_match:
            app_match = re.search(r'id=["\']a(?P<app_id>\d+)["\']', row_match.group(0))
        if not app_match:
            continue
        app_id = app_match.group("app_id")
        if app_id in seen:
            continue
        seen.add(app_id)
        cells = re.findall(r"(?is)<td[^>]*>(.*?)</td>", body)
        title = strip_tags(cells[-1]) if len(cells) >= 2 else ""
        rows.append({"app_id": app_id, "application_title_from_field_page": title})
    return rows


def field_candidate(row: dict[str, object]) -> bool:
    return bool(row["has_s3"] or row["has_o2"] or row["field_private"])


def fetch_field_links(
    fields: list[dict[str, object]],
    out: Outputs,
    refresh_pages: bool = False,
    no_fetch_pages: bool = False,
    sleep_seconds: float = 0.05,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    FIELD_PAGE_DIR.mkdir(parents=True, exist_ok=True)
    links: list[dict[str, object]] = []
    fetch_log: list[dict[str, object]] = []
    now = datetime.now(UTC).isoformat(timespec="seconds")
    candidates = [row for row in fields if field_candidate(row)]

    for idx, field in enumerate(candidates, start=1):
        field_id = str(field["field_id"])
        cache_path = FIELD_PAGE_DIR / f"field_{field_id}.html"
        source_url = FIELD_URL_TEMPLATE.format(field_id=field_id)
        status = "cache"
        error = ""
        if (refresh_pages or not cache_path.exists()) and not no_fetch_pages:
            try:
                cache_path.write_bytes(fetch_url(source_url))
                status = "fetched"
                if sleep_seconds > 0 and idx < len(candidates):
                    time.sleep(sleep_seconds)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                status = "fetch_error"
                error = str(exc)
        elif no_fetch_pages and not cache_path.exists():
            status = "missing_cache_no_fetch"
            error = "field page cache unavailable and --no-fetch-field-pages set"

        applications: list[dict[str, str]] = []
        if cache_path.exists():
            page = cache_path.read_text(encoding="utf-8", errors="replace")
            applications = parse_field_applications(page)
            if field_id == "25749":
                found_ids = {row["app_id"] for row in applications}
                if not {"17689", "22783"}.issubset(found_ids):
                    status = "parser_validation_warning"
                    error = "field 25749 parser did not recover expected applications 17689 and 22783"

        fetch_log.append(
            {
                "field_id": field_id,
                "source_url": source_url,
                "snapshot_path": relpath(cache_path),
                "status": status,
                "application_links_parsed": len(applications),
                "error": error,
                "checked_at_utc": now,
            }
        )
        for app in applications:
            links.append(
                {
                    "app_id": app["app_id"],
                    "field_id": field_id,
                    "field_title": field["field_title"],
                    "field_tier": field["field_tier"],
                    "tier_source": field["tier_source"],
                    "field_private": field["field_private"],
                    "item_type": field["item_type"],
                    "main_category": field["main_category"],
                    "debut": field["debut"],
                    "version": field["version"],
                    "has_s3": field["has_s3"],
                    "has_o2": field["has_o2"],
                    "application_title_from_field_page": app["application_title_from_field_page"],
                    "source_url": source_url,
                    "snapshot_path": relpath(cache_path),
                    "fetched_or_checked_at_utc": now,
                }
            )
    return links, fetch_log


def parse_modalities(value: str) -> set[str]:
    return {part.strip() for part in re.split(r"[|;]", clean(value)) if part.strip()}


def looks_like_wes_wgs(*values: str) -> bool:
    text = " | ".join(clean(value) for value in values)
    return bool(
        re.search(
            r"\b(?:WES|WGS|whole[- ]exome|whole[- ]genome|exome[- ]sequenc|genome[- ]sequenc|"
            r"OQFE|GLnexus|DeepVariant|WeCall|DRAGEN|pVCF|gVCF|CRAM|FASTQ)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def load_control_layers(review_rows: list[dict[str, str]]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    layer_by_app: dict[str, str] = {}
    review_by_app: dict[str, dict[str, str]] = {}
    for row in review_rows:
        app_id = clean(row.get("app_id"))
        layer = clean(row.get("expansion_layer"))
        if app_id and layer in CONTROL_ORDER and (
            app_id not in layer_by_app
            or CONTROL_ORDER[layer] < CONTROL_ORDER[layer_by_app[app_id]]
        ):
            layer_by_app[app_id] = layer
            review_by_app[app_id] = row
    return layer_by_app, review_by_app


def aggregate_field_links(field_links: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    by_app: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in field_links:
        by_app[str(row["app_id"])].append(row)

    out: dict[str, dict[str, object]] = {}
    for app_id, rows in by_app.items():
        unique_fields = {str(row["field_id"]): row for row in rows}
        s3_fields = [row for row in unique_fields.values() if int(row["has_s3"]) == 1]
        o2_fields = [row for row in unique_fields.values() if int(row["has_o2"]) == 1]
        restricted_fields = [row for row in unique_fields.values() if int(row["field_private"]) == 1]
        out[app_id] = {
            "rows": list(unique_fields.values()),
            "linked_field_count": len(unique_fields),
            "linked_s3_field_count": len(s3_fields),
            "linked_o2_field_count": len(o2_fields),
            "linked_restricted_field_count": len(restricted_fields),
            "s3_field_ids": sorted(str(row["field_id"]) for row in s3_fields),
            "o2_field_ids": sorted(str(row["field_id"]) for row in o2_fields),
            "restricted_field_ids": sorted(str(row["field_id"]) for row in restricted_fields),
        }
    return out


def field_timing_counts(
    field_rows: list[dict[str, object]],
    start: date | None,
) -> dict[str, object]:
    s3_current = []
    o2_current = []
    restricted_current = []
    s3_conservative = []
    after_start = []

    for row in field_rows:
        debut = parse_date(clean(row.get("debut")))
        is_after = bool(start and debut and debut > start)
        if is_after:
            after_start.append(str(row["field_id"]))
        if int(row.get("has_s3", 0)) == 1:
            s3_current.append(row)
            if start and debut and debut <= start:
                s3_conservative.append(row)
        if int(row.get("has_o2", 0)) == 1:
            o2_current.append(row)
        if int(row.get("field_private", 0)) == 1:
            restricted_current.append(row)
    return {
        "hs_s3_field": bool(s3_current),
        "hs_o2_field": bool(o2_current),
        "hs_restricted_field": bool(restricted_current),
        "hs_s3_field_timing_conservative": bool(s3_conservative),
        "linked_s3_field_count_timing_conservative": len(s3_conservative),
        "field_debut_after_project_start": bool(after_start),
        "field_debut_after_project_start_ids": after_start,
    }


def evidence_list(values: list[str], max_items: int = 10) -> str:
    kept = [clean(v) for v in values if clean(v)]
    if len(kept) <= max_items:
        return "; ".join(kept)
    return "; ".join(kept[:max_items]) + f"; ... +{len(kept) - max_items} more"


def build_project_classification_rows(
    projects: list[dict[str, str]],
    stage3_rows: list[dict[str, str]],
    control_review_rows: list[dict[str, str]],
    field_links: list[dict[str, object]],
) -> list[dict[str, object]]:
    stage3_by_app = {clean(row.get("app_id")): row for row in stage3_rows}
    layer_by_app, review_by_app = load_control_layers(control_review_rows)
    field_by_app = aggregate_field_links(field_links)

    rows: list[dict[str, object]] = []
    for project in projects:
        app_id = clean(project.get("app_id"))
        start = parse_date(clean(project.get("start_date")))
        st3 = stage3_by_app.get(app_id, {})
        review = review_by_app.get(app_id, {})
        layer = layer_by_app.get(app_id, "")
        fields = field_by_app.get(app_id, {})
        linked_rows = fields.get("rows", [])
        timing = field_timing_counts(linked_rows, start)

        hs_c03 = layer in C03_LAYERS
        hs_c05 = layer in C05_LAYERS
        hs_explicit = looks_like_wes_wgs(
            st3.get("already_rap_modalities", ""),
            st3.get("matched_terms", ""),
            st3.get("source_text_evidence", ""),
            review.get("previous_already_rap_modalities", ""),
            review.get("inferred_underlying_data_product_or_rap_use", ""),
            review.get("matched_term_or_expression", ""),
            review.get("supporting_text_excerpt", ""),
            review.get("evidence_dictionary_term_id", ""),
        )
        hs_s3 = bool(timing["hs_s3_field"])
        hs_o2 = bool(timing["hs_o2_field"])
        hs_restricted = bool(timing["hs_restricted_field"])
        hs_s3_conservative = bool(timing["hs_s3_field_timing_conservative"])

        high_c03_s3 = hs_c03 or hs_explicit or hs_s3
        high_c05_s3 = hs_c05 or hs_explicit or hs_s3
        high_c03_s3_conservative = hs_c03 or hs_explicit or hs_s3_conservative
        high_c05_s3_conservative = hs_c05 or hs_explicit or hs_s3_conservative
        c05_or_s3_or_o2 = hs_c05 or hs_explicit or hs_s3 or hs_o2

        legacy_modalities = parse_modalities(st3.get("legacy_route_modalities", ""))
        low_strict = (
            bool(legacy_modalities)
            and legacy_modalities.issubset(LOW_STRICT_MODALITIES)
            and not high_c05_s3
            and not hs_restricted
        )
        not_high = not high_c05_s3

        sources = []
        details = []
        reasons = []
        if hs_c03:
            sources.append("CONTROL_C03")
            details.append(f"control_layer={layer}")
            reasons.append("existing C03 RAP-intensive comparison evidence")
        if hs_c05:
            sources.append("CONTROL_C05")
            details.append(f"control_layer={layer}")
            reasons.append("existing C05 RAP-intensive comparison evidence")
        if hs_explicit:
            sources.append("WES/WGS evidence")
            details.append(review.get("matched_term_or_expression") or st3.get("already_rap_modalities", ""))
            reasons.append("explicit WES/WGS or sequence-product evidence")
        if hs_s3:
            sources.append("UKB field tier s3")
            details.append("s3_field_ids=" + evidence_list(fields.get("s3_field_ids", [])))
            reasons.append("linked current UKB field page has tier token s3")
        if hs_o2:
            details.append("o2_field_ids=" + evidence_list(fields.get("o2_field_ids", [])))
        if hs_restricted:
            details.append("restricted_field_ids=" + evidence_list(fields.get("restricted_field_ids", [])))
        if low_strict:
            sources.append("Stage 3 low-granularity legacy modality")
            details.append("legacy_modalities=" + "|".join(sorted(legacy_modalities)))
            reasons.append("only strict low-granularity legacy modality evidence and no high flags")
        if not sources:
            sources.append("unclassified by high/strict-low proxy")
            reasons.append("no high evidence and no strict low-sensitivity evidence")

        rows.append(
            {
                "app_id": app_id,
                "start_date": start.isoformat() if start else "",
                "month": start.strftime("%Y-%m") if start else "",
                "pre_post_july_2024": "post_july_2024" if start and start >= POLICY_DATE else "pre_july_2024",
                "title": project.get("schema27_title", "") or st3.get("schema27_title", ""),
                "institution": project.get("schema27_institution", "") or st3.get("schema27_institution", ""),
                "website_url": project.get("website_url", "") or st3.get("website_url", ""),
                "HIGH_C03_S3": yes(high_c03_s3),
                "HIGH_C05_S3": yes(high_c05_s3),
                "HIGH_C03_S3_TIMING_CONSERVATIVE": yes(high_c03_s3_conservative),
                "HIGH_C05_S3_TIMING_CONSERVATIVE": yes(high_c05_s3_conservative),
                "LOW_STRICT": yes(low_strict),
                "NOT_HIGH": yes(not_high),
                "S3_ONLY": yes(hs_s3 and not hs_c05 and not hs_explicit),
                "C05_ONLY": yes(hs_c05 and not hs_s3 and not hs_explicit),
                "C05_OR_S3": yes(hs_c05 or hs_s3 or hs_explicit),
                "C03_OR_S3": yes(hs_c03 or hs_s3 or hs_explicit),
                "C05_OR_S3_OR_O2": yes(c05_or_s3_or_o2),
                "hs_c03": yes(hs_c03),
                "hs_c05": yes(hs_c05),
                "hs_explicit_wes_wgs": yes(hs_explicit),
                "hs_s3_field": yes(hs_s3),
                "hs_o2_field": yes(hs_o2),
                "hs_restricted_field": yes(hs_restricted),
                "hs_s3_field_timing_conservative": yes(hs_s3_conservative),
                "linked_field_count": fields.get("linked_field_count", 0),
                "linked_s3_field_count": fields.get("linked_s3_field_count", 0),
                "linked_s3_field_count_timing_conservative": timing[
                    "linked_s3_field_count_timing_conservative"
                ],
                "linked_o2_field_count": fields.get("linked_o2_field_count", 0),
                "linked_restricted_field_count": fields.get("linked_restricted_field_count", 0),
                "field_debut_after_project_start": yes(bool(timing["field_debut_after_project_start"])),
                "field_debut_after_project_start_ids": evidence_list(
                    timing["field_debut_after_project_start_ids"]
                ),
                "control_layer": layer,
                "previous_classification": st3.get("classification", ""),
                "previous_confidence": st3.get("confidence", ""),
                "legacy_route_modalities": st3.get("legacy_route_modalities", ""),
                "already_rap_modalities": st3.get("already_rap_modalities", ""),
                "evidence_source": evidence_list(sources),
                "evidence_detail": evidence_list(details),
                "classification_reason": evidence_list(reasons),
            }
        )
    return rows


def classification_count_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    definitions = [
        "HIGH_C05_S3",
        "HIGH_C03_S3",
        "HIGH_C05_S3_TIMING_CONSERVATIVE",
        "HIGH_C03_S3_TIMING_CONSERVATIVE",
        "S3_ONLY",
        "C05_ONLY",
        "C05_OR_S3",
        "C03_OR_S3",
        "C05_OR_S3_OR_O2",
        "LOW_STRICT",
        "NOT_HIGH",
        "hs_c03",
        "hs_c05",
        "hs_explicit_wes_wgs",
        "hs_s3_field",
        "hs_o2_field",
        "hs_restricted_field",
    ]
    output = []
    for period in ["all", "pre_july_2024", "post_july_2024"]:
        subset = rows if period == "all" else [r for r in rows if r["pre_post_july_2024"] == period]
        denom = len(subset)
        for definition in definitions:
            count = sum(int(r[definition]) for r in subset)
            output.append(
                {
                    "period": period,
                    "definition": definition,
                    "count": count,
                    "universe_n": denom,
                    "share": fmt(count / denom if denom else math.nan, 6),
                }
            )
    return output


def classification_overlap_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    definitions = [
        "hs_c03",
        "hs_c05",
        "hs_explicit_wes_wgs",
        "hs_s3_field",
        "hs_o2_field",
        "hs_restricted_field",
        "HIGH_C03_S3",
        "HIGH_C05_S3",
        "LOW_STRICT",
        "NOT_HIGH",
    ]
    output = []
    for period in ["all", "pre_july_2024", "post_july_2024"]:
        subset = rows if period == "all" else [r for r in rows if r["pre_post_july_2024"] == period]
        for a in definitions:
            for b in definitions:
                output.append(
                    {
                        "period": period,
                        "definition_a": a,
                        "definition_b": b,
                        "overlap_count": sum(int(r[a]) and int(r[b]) for r in subset),
                    }
                )
        profiles = Counter(
            (
                int(r["hs_c05"]),
                int(r["hs_explicit_wes_wgs"]),
                int(r["hs_s3_field"]),
                int(r["hs_o2_field"]),
                int(r["LOW_STRICT"]),
            )
            for r in subset
        )
        for profile, count in sorted(profiles.items(), key=lambda item: (-item[1], item[0])):
            output.append(
                {
                    "period": period,
                    "definition_a": (
                        "profile:hs_c05|hs_explicit_wes_wgs|hs_s3_field|"
                        "hs_o2_field|LOW_STRICT"
                    ),
                    "definition_b": "|".join(str(value) for value in profile),
                    "overlap_count": count,
                }
            )
    return output


def field_tier_distribution_rows(
    fields: list[dict[str, object]],
    links: list[dict[str, object]],
) -> list[dict[str, object]]:
    links_by_field = defaultdict(list)
    for row in links:
        links_by_field[str(row["field_id"])].append(row)

    rows = []
    for grouping, label_fn in [
        ("tier_combo", lambda f: str(f["field_tier"]) or "none"),
        ("tier_token", None),
        ("private", lambda f: f"private={f['field_private']}"),
        ("main_category", lambda f: str(f["main_category"]) or "missing"),
    ]:
        counts: dict[str, dict[str, object]] = defaultdict(lambda: {"fields": 0, "links": 0, "apps": set()})
        for field in fields:
            labels: list[str]
            if grouping == "tier_token":
                labels = str(field["field_tier"]).split() or ["none"]
            else:
                labels = [label_fn(field)]  # type: ignore[misc]
            field_links = links_by_field.get(str(field["field_id"]), [])
            for label in labels:
                counts[label]["fields"] += 1
                counts[label]["links"] += len(field_links)
                counts[label]["apps"].update(str(row["app_id"]) for row in field_links)  # type: ignore[union-attr]
        for label, payload in sorted(counts.items(), key=lambda item: item[0]):
            rows.append(
                {
                    "grouping": grouping,
                    "value": label,
                    "field_count": payload["fields"],
                    "application_field_link_count": payload["links"],
                    "distinct_application_count": len(payload["apps"]),  # type: ignore[arg-type]
                }
            )
    return rows


def write_design_note() -> None:
    design_dir = PACKAGE / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    text = """# Project Entry2 Design

## Question

Following the July 2024 RAP transition, did recorded UKB project entry shift toward projects using higher-sensitivity or higher-granularity data?

This is a descriptive interrupted time-series and comparative composition analysis. It does not estimate a causal RAP treatment effect.

## Sample

The project-entry2 pipeline uses the same full public project-start universe as `project_entry`: 6,935 projects with exact public Start dates. It does not impose the earlier publication DID restriction that projects must have started before July 2024.

Primary estimation window: 2019-01 through 2025-12.

Breakpoint: July 2024, anchored to the 2024-07-05 UKB RAP transition.

## High-Sensitivity Proxy

The primary high-sensitivity proxy is `HIGH_C05_S3`, equal to one if a project has existing C05 RAP-intensive comparison evidence, explicit WES/WGS evidence, or at least one current public UKB field-page link to an `s3` cost-tier field.

The C03 counterpart, `HIGH_C03_S3`, is retained as robustness.

Field-tier evidence is a current Showcase crosswalk. The timing-conservative variant excludes linked fields whose public field debut date is after the project's public Start date.

## Low-Sensitivity Proxy

`LOW_STRICT` is limited to projects whose existing Stage 3 modality evidence is a nonempty subset of questionnaire/assessment, physical-measure, or environmental/geospatial modalities and that have no high-sensitivity evidence. `NOT_HIGH` is the inclusive complement of `HIGH_C05_S3`.
"""
    (design_dir / "project_entry2_design.md").write_text(text.rstrip() + "\n", encoding="utf-8")


def build_high_sensitivity_outputs(
    project_universe_path: Path = PROJECT_UNIVERSE,
    stage3_path: Path = STAGE3_CLASSIFICATION,
    control_review_path: Path = CONTROL_EXPANSION_REVIEW,
    output_paths: Outputs | None = None,
    refresh_schema: bool = False,
    refresh_field_pages: bool = False,
    no_fetch_field_pages: bool = False,
    sleep_seconds: float = 0.05,
) -> dict[str, object]:
    out = output_paths or Outputs()
    write_design_note()
    schema_refreshed = ensure_schema_snapshot(out.schema_snapshot, refresh=refresh_schema)
    fields = parse_field_schema(out.schema_snapshot)
    field_links, fetch_log = fetch_field_links(
        fields,
        out,
        refresh_pages=refresh_field_pages,
        no_fetch_pages=no_fetch_field_pages,
        sleep_seconds=sleep_seconds,
    )
    projects = read_csv(project_universe_path)
    stage3 = read_csv(stage3_path)
    control_review = read_csv(control_review_path)
    rows = build_project_classification_rows(projects, stage3, control_review, field_links)

    classification_fields = [
        "app_id",
        "start_date",
        "month",
        "pre_post_july_2024",
        "title",
        "institution",
        "website_url",
        "HIGH_C03_S3",
        "HIGH_C05_S3",
        "HIGH_C03_S3_TIMING_CONSERVATIVE",
        "HIGH_C05_S3_TIMING_CONSERVATIVE",
        "LOW_STRICT",
        "NOT_HIGH",
        "S3_ONLY",
        "C05_ONLY",
        "C05_OR_S3",
        "C03_OR_S3",
        "C05_OR_S3_OR_O2",
        "hs_c03",
        "hs_c05",
        "hs_explicit_wes_wgs",
        "hs_s3_field",
        "hs_o2_field",
        "hs_restricted_field",
        "hs_s3_field_timing_conservative",
        "linked_field_count",
        "linked_s3_field_count",
        "linked_s3_field_count_timing_conservative",
        "linked_o2_field_count",
        "linked_restricted_field_count",
        "field_debut_after_project_start",
        "field_debut_after_project_start_ids",
        "control_layer",
        "previous_classification",
        "previous_confidence",
        "legacy_route_modalities",
        "already_rap_modalities",
        "evidence_source",
        "evidence_detail",
        "classification_reason",
    ]
    write_csv(out.classification, rows, classification_fields)

    link_fields = [
        "app_id",
        "field_id",
        "field_title",
        "field_tier",
        "tier_source",
        "field_private",
        "item_type",
        "main_category",
        "debut",
        "version",
        "has_s3",
        "has_o2",
        "application_title_from_field_page",
        "source_url",
        "snapshot_path",
        "fetched_or_checked_at_utc",
    ]
    write_csv(out.application_field_links, field_links, link_fields)
    write_csv(
        out.field_fetch_log,
        fetch_log,
        [
            "field_id",
            "source_url",
            "snapshot_path",
            "status",
            "application_links_parsed",
            "error",
            "checked_at_utc",
        ],
    )
    write_csv(
        out.field_tier_distribution,
        field_tier_distribution_rows(fields, field_links),
        [
            "grouping",
            "value",
            "field_count",
            "application_field_link_count",
            "distinct_application_count",
        ],
    )
    write_csv(
        out.classification_counts,
        classification_count_rows(rows),
        ["period", "definition", "count", "universe_n", "share"],
    )
    write_csv(
        out.classification_overlap,
        classification_overlap_rows(rows),
        ["period", "definition_a", "definition_b", "overlap_count"],
    )

    manifest = {
        "built_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "schema1_url": SCHEMA1_URL,
        "schema_snapshot": relpath(out.schema_snapshot),
        "schema_snapshot_refreshed_this_run": schema_refreshed,
        "field_page_url_template": FIELD_URL_TEMPLATE,
        "field_page_cache_dir": relpath(FIELD_PAGE_DIR),
        "field_page_candidate_rule": "has s3 tier OR has o2 tier OR private=1",
        "source_parser_validation": {
            "field_id": "25749",
            "expected_tier_tokens": ["o2", "s3"],
            "expected_application_ids": ["17689", "22783"],
            "status": next(
                (
                    row["status"]
                    for row in fetch_log
                    if str(row["field_id"]) == "25749"
                ),
                "not_checked",
            ),
        },
        "project_universe": relpath(project_universe_path),
        "stage3_classification": relpath(stage3_path),
        "control_expansion_project_review": relpath(control_review_path),
        "control_expansion_evidence_dictionary": relpath(CONTROL_EXPANSION_DICTIONARY),
        "n_projects": len(rows),
        "n_schema_fields": len(fields),
        "n_field_page_candidates": sum(field_candidate(field) for field in fields),
        "n_application_field_links": len(field_links),
        "n_distinct_applications_with_field_links": len({str(row["app_id"]) for row in field_links}),
        "n_high_c05_s3": sum(int(row["HIGH_C05_S3"]) for row in rows),
        "n_high_c03_s3": sum(int(row["HIGH_C03_S3"]) for row in rows),
        "n_low_strict": sum(int(row["LOW_STRICT"]) for row in rows),
        "n_s3_field_applications": sum(int(row["hs_s3_field"]) for row in rows),
        "n_o2_field_applications": sum(int(row["hs_o2_field"]) for row in rows),
    }
    write_json(out.source_manifest, manifest)
    return manifest


def validate_outputs(out: Outputs | None = None) -> None:
    out = out or Outputs()
    rows = read_csv(out.classification)
    if len(rows) != 6935:
        raise AssertionError(f"expected 6,935 project rows; found {len(rows)}")
    required = {
        "app_id",
        "start_date",
        "HIGH_C03_S3",
        "HIGH_C05_S3",
        "LOW_STRICT",
        "NOT_HIGH",
        "hs_c03",
        "hs_c05",
        "hs_explicit_wes_wgs",
        "hs_s3_field",
        "hs_o2_field",
        "hs_restricted_field",
        "linked_field_count",
        "linked_s3_field_count",
        "linked_o2_field_count",
        "evidence_source",
        "evidence_detail",
        "classification_reason",
    }
    missing = sorted(required - set(rows[0]))
    if missing:
        raise AssertionError(f"classification file missing columns: {missing}")
    for row in rows:
        high = int(row["HIGH_C05_S3"])
        if int(row["NOT_HIGH"]) != 1 - high:
            raise AssertionError(f"NOT_HIGH complement failed for app {row['app_id']}")
        if int(row["LOW_STRICT"]) and high:
            raise AssertionError(f"LOW_STRICT overlaps HIGH_C05_S3 for app {row['app_id']}")
    links = read_csv(out.application_field_links)
    field_25749 = [row for row in links if row["field_id"] == "25749"]
    if field_25749:
        ids = {row["app_id"] for row in field_25749}
        if not {"17689", "22783"}.issubset(ids):
            raise AssertionError("field 25749 parser validation failed")
        tiers = {row["field_tier"] for row in field_25749}
        if not any("o2" in tier and "s3" in tier for tier in tiers):
            raise AssertionError("field 25749 tier validation failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-schema", action="store_true")
    parser.add_argument("--refresh-field-pages", action="store_true")
    parser.add_argument("--no-fetch-field-pages", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    args = parser.parse_args()
    manifest = build_high_sensitivity_outputs(
        refresh_schema=args.refresh_schema,
        refresh_field_pages=args.refresh_field_pages,
        no_fetch_field_pages=args.no_fetch_field_pages,
        sleep_seconds=args.sleep_seconds,
    )
    validate_outputs()
    print(
        "project-entry2 high-sensitivity classification built: "
        f"{manifest['n_projects']} projects, "
        f"{manifest['n_high_c05_s3']} HIGH_C05_S3, "
        f"{manifest['n_s3_field_applications']} s3-linked applications"
    )


if __name__ == "__main__":
    main()
