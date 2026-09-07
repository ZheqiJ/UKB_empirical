#!/usr/bin/env python3
"""Collapse the existing DMCA attribution crosswalk to application-level tiers.

This script only reads the curated baseline and the already-built exhaustive
attribution tables. It does not fetch evidence or rerun any matching logic.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UKB = ROOT / "ukb_dmca"

CURATED = UKB / "curated_dmca_application_links.csv"
ATTRIBUTIONS = UKB / "exhaustive_dmca_application_attribution.csv"
FAMILY_SUMMARY = UKB / "exhaustive_dmca_family_attribution_summary.csv"
EXHAUSTIVE_SUMMARY = UKB / "exhaustive_dmca_application_attribution_summary.json"

OUT_TIERS = UKB / "application_level_attribution_tiers.csv"
OUT_SUMMARY = UKB / "application_level_attribution_tier_summary.csv"

EXCLUDED_STATUSES = {"excluded_false_positive"}
SUPPORTED_STATUSES = {"confirmed", "probable", "ambiguous", "candidate"}
STATUS_RANK = {
    "confirmed": 1,
    "probable": 2,
    "ambiguous": 3,
    "candidate": 4,
    "weak_candidate": 5,
}

TIER_DEFINITIONS = {
    "Tier 1": "Current curated baseline",
    "Tier 2": "Additional confirmed",
    "Tier 3": "Additional probable",
    "Tier 4": "Additional single-app ambiguous",
    "Tier 5": "Additional B-level candidate",
    "Tier 6": "Weak candidate only",
}

TIER_NOTES = {
    "Tier 1": "Curated 52 baseline. This hierarchy override applies regardless of exhaustive-table status.",
    "Tier 2": "Not in the curated baseline; retained because at least one attribution row is confirmed.",
    "Tier 3": "Not in Tiers 1-2; retained because at least one attribution row is probable.",
    "Tier 4": "Not in Tiers 1-3; retained from a family with exactly one supported/ambiguous application. Ambiguous multi-application families are excluded from this tier.",
    "Tier 5": "Not in Tiers 1-4; retained because at least one attribution row has B-level candidate evidence.",
    "Tier 6": "Not in Tiers 1-5; weak-candidate evidence only. Retained for completeness and not recommended for regression.",
    "Excluded: ambiguous_multi_application": "Ambiguous attribution from a multi-application family with no confirmed, probable, B-level candidate, or weak-candidate row. Retained as an audit row but deliberately excluded from the six-tier summary.",
}


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def ordered_unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        value = clean(value)
        if value and value not in result:
            result.append(value)
    return result


def numeric_application_sort_key(application_id: str) -> tuple[int, str]:
    return (int(application_id), application_id) if application_id.isdigit() else (10**18, application_id)


def best_status(statuses: set[str]) -> str:
    return min(statuses, key=lambda status: STATUS_RANK.get(status, 999)) if statuses else "curated_baseline"


def main() -> None:
    curated_rows = read_csv(CURATED)
    attribution_rows = read_csv(ATTRIBUTIONS)
    family_rows = read_csv(FAMILY_SUMMARY)
    exhaustive_summary = json.loads(EXHAUSTIVE_SUMMARY.read_text(encoding="utf-8"))

    curated_titles = {
        clean(row["application_id"]): clean(row.get("application_title"))
        for row in curated_rows
        if clean(row.get("application_id"))
    }
    curated_ids = set(curated_titles)
    if len(curated_rows) != 52 or len(curated_ids) != 52:
        raise ValueError("The curated baseline must contain exactly 52 unique applications.")

    family_status = {
        clean(row["family_id"]): clean(row.get("family_status"))
        for row in family_rows
        if clean(row.get("family_id"))
    }

    valid_rows = [
        row
        for row in attribution_rows
        if clean(row.get("application_id"))
        and clean(row.get("matching_status")) not in EXCLUDED_STATUSES
    ]
    by_application: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in valid_rows:
        by_application[clean(row["application_id"])].append(row)

    statuses_by_application = {
        application_id: {clean(row.get("matching_status")) for row in rows}
        for application_id, rows in by_application.items()
    }
    single_ambiguous_ids = {
        clean(row["application_id"])
        for row in valid_rows
        if clean(row.get("matching_status")) == "ambiguous"
        and family_status.get(clean(row.get("family_id"))) == "ambiguous"
    }
    multi_ambiguous_only_ids = {
        application_id
        for application_id, statuses in statuses_by_application.items()
        if "ambiguous" in statuses
        and any(
            family_status.get(clean(row.get("family_id"))) == "ambiguous_multi_application"
            for row in by_application[application_id]
            if clean(row.get("matching_status")) == "ambiguous"
        )
        and not (statuses & {"confirmed", "probable", "candidate", "weak_candidate"})
        and application_id not in curated_ids
    }

    assignments: dict[str, str] = {}
    used: set[str] = set()

    def assign(tier: str, application_ids: set[str]) -> None:
        remaining = application_ids - used
        assignments.update({application_id: tier for application_id in remaining})
        used.update(remaining)

    assign("Tier 1", curated_ids)
    assign(
        "Tier 2",
        {
            application_id
            for application_id, statuses in statuses_by_application.items()
            if "confirmed" in statuses
        },
    )
    assign(
        "Tier 3",
        {
            application_id
            for application_id, statuses in statuses_by_application.items()
            if "probable" in statuses
        },
    )
    assign("Tier 4", single_ambiguous_ids)
    assign(
        "Tier 5",
        {
            application_id
            for application_id, statuses in statuses_by_application.items()
            if "candidate" in statuses
        },
    )
    assign(
        "Tier 6",
        {
            application_id
            for application_id, statuses in statuses_by_application.items()
            if "weak_candidate" in statuses
        },
    )

    for application_id in multi_ambiguous_only_ids:
        assignments[application_id] = "Excluded: ambiguous_multi_application"

    all_eligible_ids = curated_ids | set(by_application)
    unassigned = all_eligible_ids - set(assignments)
    if unassigned:
        raise ValueError(f"Applications without a hierarchy assignment: {sorted(unassigned, key=numeric_application_sort_key)}")

    supported_count = len(
        {
            application_id
            for application_id, statuses in statuses_by_application.items()
            if statuses & SUPPORTED_STATUSES
        }
        | curated_ids
    )
    tiered_supported_count = sum(
        1
        for tier in assignments.values()
        if tier in {"Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"}
    )
    expected_supported_count = exhaustive_summary["total_unique_applications_identified_supported_or_ambiguous"]
    expected_all_count = exhaustive_summary["total_unique_applications_identified_including_weak"]
    if supported_count != expected_supported_count:
        raise ValueError(f"Supported count {supported_count} does not match exhaustive summary {expected_supported_count}.")
    if tiered_supported_count + len(multi_ambiguous_only_ids) != expected_supported_count:
        raise ValueError("Tiered supported applications plus excluded ambiguous-multi audit rows do not reconcile.")
    if len(assignments) != expected_all_count:
        raise ValueError(f"Application count {len(assignments)} does not match exhaustive summary {expected_all_count}.")

    output_rows: list[dict[str, object]] = []
    for application_id, tier in assignments.items():
        rows = by_application.get(application_id, [])
        statuses = statuses_by_application.get(application_id, set())
        title = curated_titles.get(application_id) or next(
            (clean(row.get("application_title")) for row in rows if clean(row.get("application_title"))),
            "",
        )
        output_rows.append(
            {
                "application_id": application_id,
                "application_title": title,
                "tier": tier,
                "best_matching_status": best_status(statuses),
                "existing_curated_52": "yes" if application_id in curated_ids else "no",
                "family_ids": "; ".join(ordered_unique([row.get("family_id", "") for row in rows])),
                "repo_urls": "; ".join(ordered_unique([row.get("repo_url", "") for row in rows])),
                "evidence_type": "; ".join(ordered_unique([row.get("evidence_type", "") for row in rows])),
                "confidence_note": TIER_NOTES[tier],
                "included_in_tier_summary": "yes" if tier.startswith("Tier ") else "no",
            }
        )

    tier_order = {f"Tier {number}": number for number in range(1, 7)}
    output_rows.sort(
        key=lambda row: (
            tier_order.get(str(row["tier"]), 99),
            numeric_application_sort_key(str(row["application_id"])),
        )
    )
    tier_fields = [
        "application_id",
        "application_title",
        "tier",
        "best_matching_status",
        "existing_curated_52",
        "family_ids",
        "repo_urls",
        "evidence_type",
        "confidence_note",
        "included_in_tier_summary",
    ]
    write_csv(OUT_TIERS, output_rows, tier_fields)

    summary_rows: list[dict[str, object]] = []
    cumulative = 0
    for tier in TIER_DEFINITIONS:
        additional = sum(1 for assigned_tier in assignments.values() if assigned_tier == tier)
        cumulative += additional
        summary_rows.append(
            {
                "Tier": tier.removeprefix("Tier "),
                "Definition": TIER_DEFINITIONS[tier],
                "Additional unique apps": additional,
                "Cumulative unique apps": cumulative,
            }
        )
    write_csv(
        OUT_SUMMARY,
        summary_rows,
        ["Tier", "Definition", "Additional unique apps", "Cumulative unique apps"],
    )

    print(f"Tier 1-5 cumulative: {tiered_supported_count}")
    print(f"Excluded ambiguous-multi audit rows: {len(multi_ambiguous_only_ids)}")
    print(f"Supported/ambiguous/candidate reconciliation: {tiered_supported_count} + {len(multi_ambiguous_only_ids)} = {expected_supported_count}")
    print(f"Tier 1-6 cumulative: {sum(1 for tier in assignments.values() if tier.startswith('Tier '))}")
    print(f"All eligible applications including audit rows: {len(assignments)}")


if __name__ == "__main__":
    main()
