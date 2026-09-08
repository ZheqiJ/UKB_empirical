#!/usr/bin/env python3
"""Audit observed DMCA notice timing for the fixed Broad-55 application set.

This diagnostic never reruns DMCA matching. It reconstructs notice dates only
from preserved curated application/family linkage evidence and the notice index.
"""

from __future__ import annotations

import csv
import html
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

from leakage_its_analysis import POLICY_DATE, clean, parse_date, write_csv, write_text


ROOT = Path(__file__).resolve().parents[3]
UKB = ROOT / "ukb_dmca"
PACKAGE = UKB / "leakage_application_analysis"
DATA_DIR = PACKAGE / "data"
TABLE_DIR = PACKAGE / "tables"
FIGURE_DIR = PACKAGE / "figures"
REPORT_DIR = PACKAGE / "reports"

APPLICATION_UNIVERSE = DATA_DIR / "application_level_leakage_curated52_broad55.csv"
TIER4_ADDITIONS = DATA_DIR / "tier4_added_applications_broad55.csv"
APPLICATION_LINKS = UKB / "curated_dmca_application_links.csv"
FAMILY_LINKS = UKB / "curated_dmca_repository_family_links.csv"
NOTICES = UKB / "ukb_dmca_notices.csv"

FROZEN_OUT = DATA_DIR / "broad55_frozen_application_ids.csv"
AUDIT_OUT = DATA_DIR / "broad55_dmca_notice_timing_audit.csv"
COUNTS_OUT = TABLE_DIR / "broad55_notice_window_counts.csv"
REPORT_OUT = REPORT_DIR / "broad55_dmca_notice_window_diagnostic.md"

MASTER_SVG = FIGURE_DIR / "broad55_start_to_first_notice_lag.svg"
ZOOM_SVGS = {
    "within_1y": FIGURE_DIR / "broad55_notice_within_1y_july2024_zoom.svg",
    "within_18m": FIGURE_DIR / "broad55_notice_within_18m_july2024_zoom.svg",
    "within_2y": FIGURE_DIR / "broad55_notice_within_2y_july2024_zoom.svg",
}
PANEL_SVG = FIGURE_DIR / "broad55_notice_window_july2024_3panel.svg"
WINDOWS = [("within_1y", "1 year"), ("within_18m", "18 months"), ("within_2y", "2 years")]
COLORS = {"yes": "#1f6b75", "no": "#b65736"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def split_values(value: str) -> list[str]:
    values: list[str] = []
    for part in value.replace("|", ";").split(";"):
        item = clean(part)
        if item and item not in values:
            values.append(item)
    return values


def sorted_unique(values: list[str]) -> list[str]:
    return sorted(set(values))


def add_months(value: date, months: int) -> date:
    raw_month = value.month - 1 + months
    year, month = value.year + raw_month // 12, raw_month % 12 + 1
    month_end = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(value.day, month_end))


def add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=28)


def bool_text(value: bool | None) -> str:
    return "yes" if value is True else "no" if value is False else ""


def family_matches_app(family: dict[str, str], application_id: str, include_candidate: bool) -> bool:
    if application_id in split_values(family.get("application_id", "")):
        return True
    return include_candidate and application_id in split_values(family.get("candidate_application_ids", ""))


def reconstruct() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    universe = read_csv(APPLICATION_UNIVERSE)
    application_links = read_csv(APPLICATION_LINKS)
    family_links = read_csv(FAMILY_LINKS)
    notices = read_csv(NOTICES)
    tier4 = read_csv(TIER4_ADDITIONS)

    broad_rows = [row for row in universe if row.get("Leak55") == "1"]
    curated_rows = [row for row in universe if row.get("Leak52") == "1"]
    broad_ids = {row["application_id"] for row in broad_rows}
    curated_ids = {row["application_id"] for row in curated_rows}
    tier4_ids = {row["application_id"] for row in tier4}
    if len(broad_ids) != 55:
        raise ValueError(f"Broad55 must contain 55 unique IDs; found {len(broad_ids)}.")
    if len(curated_ids) != 52:
        raise ValueError(f"Curated52 must contain 52 unique IDs; found {len(curated_ids)}.")
    if not curated_ids < broad_ids:
        raise ValueError("Curated52 is not a proper subset of Broad55.")
    if broad_ids - curated_ids != tier4_ids or len(tier4_ids) != 3:
        raise ValueError("Broad55 additions are not exactly the existing three Tier-4 additions.")

    notice_by_id: dict[str, date] = {}
    for row in notices:
        notice_id = clean(row.get("notice_id", ""))
        notice_date = parse_date(clean(row.get("notice_date", "")))
        if notice_id and notice_date:
            notice_by_id[notice_id] = notice_date
    app_by_id = {row["application_id"]: row for row in application_links}
    tier4_by_id = {row["application_id"]: row for row in tier4}
    frozen_rows = [
        {
            "application_id": row["application_id"],
            "application_title": row["application_title"],
            "curated52": "yes" if row["application_id"] in curated_ids else "no",
            "broad55": "yes",
            "broad55_addition": "yes" if row["application_id"] in tier4_ids else "no",
        }
        for row in sorted(broad_rows, key=lambda item: int(item["application_id"]))
    ]

    audit: list[dict[str, str]] = []
    for row in sorted(broad_rows, key=lambda item: int(item["application_id"])):
        application_id = row["application_id"]
        application_link = app_by_id.get(application_id, {})
        is_tier4 = application_id in tier4_ids
        family_evidence = [
            family
            for family in family_links
            if family_matches_app(family, application_id, include_candidate=is_tier4)
        ]
        direct_families = split_values(application_link.get("linked_repository_family_ids", ""))
        direct_repos = split_values(application_link.get("linked_repo_urls", ""))
        evidence_families = list(direct_families)
        evidence_repos = list(direct_repos)
        notice_ids = split_values(application_link.get("notice_ids", ""))
        source_parts: list[str] = []
        if notice_ids or direct_families or direct_repos:
            source_parts.append("curated_dmca_application_links")
        for family in family_evidence:
            family_id = clean(family.get("family_id", ""))
            if family_id:
                evidence_families.append(family_id)
            evidence_repos.extend(split_values(family.get("all_repo_urls", "")))
            notice_ids.extend(split_values(family.get("notice_ids", "")))
            source_parts.append(
                "curated_dmca_repository_family_links_tier4_candidate" if is_tier4 and application_id not in split_values(family.get("application_id", "")) else "curated_dmca_repository_family_links"
            )
        notice_ids = sorted_unique(notice_ids)
        valid_pairs = sorted((notice_by_id[notice_id], notice_id) for notice_id in notice_ids if notice_id in notice_by_id)
        invalid_notice_ids = sorted(notice_id for notice_id in notice_ids if notice_id not in notice_by_id)
        earliest_date, earliest_id = valid_pairs[0] if valid_pairs else (None, "")
        start = parse_date(row["project_start_date"])
        if not start:
            raise ValueError(f"Broad55 application {application_id} lacks a valid project start date.")
        after_start = earliest_date >= start if earliest_date else None
        if earliest_date is None:
            status = "missing_or_unresolved_notice_date"
            mapping_note = "No reproducibly linked valid notice ID/date in current curated application/family evidence."
        elif not after_start:
            status = "notice_before_project_start"
            mapping_note = "Earliest reproducibly linked notice predates project initiation and is not used for a post-initiation timing window."
        else:
            status = "reconstructed_valid_post_start_notice"
            mapping_note = "Earliest date is the minimum valid date among reconstructed linked notice IDs."
        if invalid_notice_ids:
            mapping_note += " Notice IDs lacking a valid notice-index date: " + "; ".join(invalid_notice_ids) + "."
        stored = clean(application_link.get("first_dmca_notice_date", ""))
        reconstructed = earliest_date.isoformat() if earliest_date else ""
        if stored and stored != reconstructed:
            mapping_note += f" Stored first_dmca_notice_date ({stored}) differs from reconstructed minimum ({reconstructed or 'missing'})."
        lag_days = (earliest_date - start).days if earliest_date and after_start else None
        within_1y = earliest_date is not None and after_start and earliest_date <= add_years(start, 1)
        within_18m = earliest_date is not None and after_start and earliest_date <= add_months(start, 18)
        within_2y = earliest_date is not None and after_start and earliest_date <= add_years(start, 2)
        audit.append(
            {
                "application_id": application_id,
                "application_title": row["application_title"],
                "project_start_date": start.isoformat(),
                "curated52": "yes" if application_id in curated_ids else "no",
                "broad55": "yes",
                "linked_repository_family_ids": "; ".join(sorted_unique(evidence_families)),
                "linked_repo_urls": "; ".join(sorted_unique(evidence_repos)),
                "all_linked_notice_ids": "; ".join(notice_id for _, notice_id in valid_pairs),
                "all_linked_notice_dates": "; ".join(notice_date.isoformat() for notice_date, _ in valid_pairs),
                "notice_count_reconstructed": str(len(valid_pairs)),
                "earliest_dmca_notice_id": earliest_id,
                "earliest_dmca_notice_date": reconstructed,
                "stored_first_dmca_notice_date": stored,
                "notice_date_source": "; ".join(sorted_unique([*source_parts, *(["ukb_dmca_notices.csv"] if valid_pairs else [])])),
                "timing_mapping_status": status,
                "timing_mapping_note": mapping_note,
                "lag_days": str(lag_days) if lag_days is not None else "",
                "lag_months": f"{lag_days / 30.4375:.4f}" if lag_days is not None else "",
                "lag_years": f"{lag_days / 365.2425:.4f}" if lag_days is not None else "",
                "notice_after_project_start": bool_text(after_start),
                "within_1y": bool_text(within_1y),
                "within_1_5y": bool_text(within_18m),
                "within_18m": bool_text(within_18m),
                "within_2y": bool_text(within_2y),
                "post_july2024_start": bool_text(start >= POLICY_DATE),
            }
        )
    if len({row["application_id"] for row in audit}) != 55 or len(audit) != 55:
        raise ValueError("Duplicate or missing Broad55 rows in final timing audit.")
    validate(audit, curated_ids)
    return frozen_rows, audit, window_counts(audit)


def validate(audit: list[dict[str, str]], curated_ids: set[str]) -> None:
    for row in audit:
        dates = [parse_date(value) for value in split_values(row["all_linked_notice_dates"])]
        dates = [value for value in dates if value]
        earliest = parse_date(row["earliest_dmca_notice_date"])
        if dates and earliest != min(dates):
            raise ValueError(f"Earliest date is not the reconstructed minimum for application {row['application_id']}.")
        for field in ("within_1y", "within_1_5y", "within_18m", "within_2y"):
            if row[field] == "yes" and (not earliest or row["notice_after_project_start"] != "yes"):
                raise ValueError(f"{field} is invalid for application {row['application_id']}.")
        if row["within_1y"] == "yes" and row["within_18m"] != "yes":
            raise ValueError(f"within_1y is not a subset of within_18m for {row['application_id']}.")
        if row["within_18m"] == "yes" and row["within_2y"] != "yes":
            raise ValueError(f"within_18m is not a subset of within_2y for {row['application_id']}.")
        if row["within_1_5y"] != row["within_18m"]:
            raise ValueError(f"within_1_5y and within_18m disagree for {row['application_id']}.")
    if sum(row["curated52"] == "yes" for row in audit) != len(curated_ids):
        raise ValueError("Curated52 membership changed during audit.")


def window_counts(audit: list[dict[str, str]]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for definition, selected in (("Broad55", audit), ("Curated52", [row for row in audit if row["curated52"] == "yes"])):
        for window, label in [("all_valid_post_start", "all valid post-start notices"), *WINDOWS]:
            retained = [row for row in selected if row[window] == "yes"] if window != "all_valid_post_start" else [row for row in selected if row["notice_after_project_start"] == "yes"]
            results.append(
                {
                    "definition": definition,
                    "window": label,
                    "total_positive_cases": str(len(selected)),
                    "dated_cases": str(sum(bool(row["earliest_dmca_notice_date"]) for row in selected)),
                    "retained_cases": str(len(retained)),
                    "pre_july2024_cases": str(sum(row["post_july2024_start"] == "no" for row in retained)),
                    "post_july2024_cases": str(sum(row["post_july2024_start"] == "yes" for row in retained)),
                    "missing_notice_date": str(sum(not row["earliest_dmca_notice_date"] for row in selected)),
                    "notice_before_start": str(sum(row["timing_mapping_status"] == "notice_before_project_start" for row in selected)),
                }
            )
    return results


def svg_root(width: int, height: int) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#ffffff"/>']


def date_x(value: date, start: date, end: date, left: float, width: float) -> float:
    return left + ((value - start).days / max((end - start).days, 1)) * width


def scatter_svg(path: Path, rows: list[dict[str, str]], title: str, subtitle: str, x_start: date, x_end: date, y_max: float, zoom: bool = False) -> None:
    width, height = (1120, 620) if not zoom else (980, 500)
    left, right, top, bottom = 95, 38, 70, 92
    plot_width, plot_height = width - left - right, height - top - bottom
    y_max = max(1.0, y_max)
    def y(value: float) -> float:
        return top + (y_max - value) / y_max * plot_height
    lines = svg_root(width, height)
    lines += [
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-family="Arial, sans-serif" font-size="19" font-weight="700">{html.escape(title)}</text>',
        f'<text x="{width / 2}" y="49" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#444">{html.escape(subtitle)}</text>',
    ]
    for fraction in (0, 0.25, 0.5, 0.75, 1):
        value = y_max * fraction
        yy = y(value)
        lines.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width - right}" y2="{yy:.1f}" stroke="#e4e4e4"/>')
        lines.append(f'<text x="{left - 9}" y="{yy + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#444">{value:.0f}</text>')
    for months, label in ((12, "12 months"), (18, "18 months"), (24, "24 months")):
        if months <= y_max:
            yy = y(months)
            lines.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width - right}" y2="{yy:.1f}" stroke="#8a8a8a" stroke-dasharray="4 3"/>')
            lines.append(f'<text x="{width - right - 3}" y="{yy - 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="10" fill="#555">{label}</text>')
    for year in range(x_start.year, x_end.year + 1):
        tick = date(year, 1, 1)
        if x_start <= tick <= x_end:
            xx = date_x(tick, x_start, x_end, left, plot_width)
            lines.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{height - bottom}" stroke="#f0f0f0"/>')
            lines.append(f'<text x="{xx:.1f}" y="{height - bottom + 22}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#444">{year}</text>')
    policy_x = date_x(POLICY_DATE, x_start, x_end, left, plot_width)
    if left <= policy_x <= width - right:
        lines.append(f'<line x1="{policy_x:.1f}" y1="{top}" x2="{policy_x:.1f}" y2="{height - bottom}" stroke="#111" stroke-width="1.5"/>')
        lines.append(f'<text x="{policy_x + 5:.1f}" y="{top + 14}" font-family="Arial, sans-serif" font-size="11" fill="#111">Jul 5, 2024</text>')
    for row in rows:
        start = parse_date(row["project_start_date"])
        lag = float(row["lag_months"])
        if not start or not (x_start <= start <= x_end):
            continue
        xx, yy = date_x(start, x_start, x_end, left, plot_width), y(lag)
        color = COLORS[row["curated52"]]
        lines.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="4" fill="{color}" fill-opacity="0.84" stroke="#ffffff" stroke-width="0.7"/>')
    legend_y = height - 29
    lines += [
        f'<circle cx="{left}" cy="{legend_y - 3}" r="4" fill="{COLORS["yes"]}"/><text x="{left + 9}" y="{legend_y}" font-family="Arial, sans-serif" font-size="11">Curated 52</text>',
        f'<circle cx="{left + 110}" cy="{legend_y - 3}" r="4" fill="{COLORS["no"]}"/><text x="{left + 119}" y="{legend_y}" font-family="Arial, sans-serif" font-size="11">Broad-55 addition</text>',
        f'<text x="18" y="{top + plot_height / 2:.1f}" transform="rotate(-90 18 {top + plot_height / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">Months from project initiation to earliest observed DMCA notice</text>',
        f'<text x="{left + plot_width / 2:.1f}" y="{height - 7}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">UKB project/application initiation date</text>',
        '</svg>',
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def panel_svg(path: Path, audit: list[dict[str, str]], x_start: date, x_end: date) -> None:
    width, height, left, top, bottom, gap = 1500, 440, 72, 62, 70, 34
    panel_width = (width - 2 * left - 2 * gap) / 3
    lines = svg_root(width, height)
    lines.append(f'<text x="{width / 2}" y="27" text-anchor="middle" font-family="Arial, sans-serif" font-size="17" font-weight="700">Broad-55 applications with first observed DMCA notice within common timing windows</text>')
    for panel, (window, label) in enumerate(WINDOWS):
        x_left = left + panel * (panel_width + gap)
        y_max = {"within_1y": 12, "within_18m": 18, "within_2y": 24}[window]
        plot_height = height - top - bottom
        retained = [row for row in audit if row[window] == "yes"]
        def y(value: float) -> float:
            return top + (y_max - value) / y_max * plot_height
        lines.append(f'<text x="{x_left + panel_width / 2:.1f}" y="48" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700">Notice within {label}</text>')
        for fraction in (0, 0.5, 1):
            yy = y(y_max * fraction)
            lines.append(f'<line x1="{x_left:.1f}" y1="{yy:.1f}" x2="{x_left + panel_width:.1f}" y2="{yy:.1f}" stroke="#e4e4e4"/>')
            lines.append(f'<text x="{x_left - 7:.1f}" y="{yy + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="9" fill="#444">{y_max * fraction:.0f}</text>')
        for year in range(x_start.year, x_end.year + 1):
            tick = date(year, 1, 1)
            if x_start <= tick <= x_end:
                xx = date_x(tick, x_start, x_end, x_left, panel_width)
                lines.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{height - bottom}" stroke="#f0f0f0"/>')
                lines.append(f'<text x="{xx:.1f}" y="{height - bottom + 19}" text-anchor="middle" font-family="Arial, sans-serif" font-size="9" fill="#444">{year}</text>')
        policy_x = date_x(POLICY_DATE, x_start, x_end, x_left, panel_width)
        lines.append(f'<line x1="{policy_x:.1f}" y1="{top}" x2="{policy_x:.1f}" y2="{height - bottom}" stroke="#111" stroke-width="1.3"/>')
        if panel == 0:
            lines.append(f'<text x="{policy_x + 4:.1f}" y="{top + 13}" font-family="Arial, sans-serif" font-size="9">Jul 5, 2024</text>')
        for row in retained:
            start = parse_date(row["project_start_date"])
            if start:
                xx = date_x(start, x_start, x_end, x_left, panel_width)
                lines.append(f'<circle cx="{xx:.1f}" cy="{y(float(row["lag_months"])):.1f}" r="4" fill="{COLORS[row["curated52"]]}" fill-opacity="0.85" stroke="#ffffff" stroke-width="0.7"/>')
        if panel == 0:
            lines.append(f'<text x="{x_left + panel_width / 2:.1f}" y="{height - 5}" text-anchor="middle" font-family="Arial, sans-serif" font-size="10">Project initiation date; y = lag months</text>')
    lines.append('</svg>')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report(audit: list[dict[str, str]], counts: list[dict[str, str]], zoom_start: date, zoom_end: date) -> str:
    count_by = {(row["definition"], row["window"]): row for row in counts}
    def row(definition: str, window: str) -> str:
        current = count_by[(definition, window)]
        return f"| {window} | {current['retained_cases']} | {current['pre_july2024_cases']} | {current['post_july2024_cases']} |"
    unresolved = [item for item in audit if item["timing_mapping_status"] == "missing_or_unresolved_notice_date"]
    predates = [item for item in audit if item["timing_mapping_status"] == "notice_before_project_start"]
    discrepancies = [item for item in audit if item["stored_first_dmca_notice_date"] and item["stored_first_dmca_notice_date"] != item["earliest_dmca_notice_date"]]
    broad_all = count_by[("Broad55", "all valid post-start notices")]
    curated_all = count_by[("Curated52", "all valid post-start notices")]
    format_apps = lambda entries: "; ".join(f"{item['application_id']} ({item['application_title']})" for item in entries) or "None."
    recommendation = []
    for window, label in WINDOWS:
        current = count_by[("Broad55", label)]
        pre, post = int(current["pre_july2024_cases"]), int(current["post_july2024_cases"])
        recommendation.append(f"{label}: {pre} pre-cutoff and {post} post-cutoff positive cases remain. " + ("This is only a sparse feasibility diagnostic and is not enough by itself for a stable causal analysis." if min(pre, post) < 10 else "The positive-case balance is larger, but a future analysis would still need a defined risk set and follow-up design."))
    discrepancy_text = "; ".join(f"{item['application_id']}: stored {item['stored_first_dmca_notice_date']}, reconstructed {item['earliest_dmca_notice_date']}" for item in discrepancies) or "None."
    return f"""# Broad-55 DMCA Notice-Timing Feasibility Diagnostic

## Data Definition

Broad 55 membership is frozen from the existing application-level file: 52 curated applications plus the existing three Broad-55 additions. Project initiation date is the cohort date and x-axis. The event date is the earliest **observed DMCA notice** reproducibly linked to an application through the current curated application/family evidence. It is not treated as a date of leakage, public exposure, repository upload, discovery, or underlying posting.

## Notice-Date Reconstruction

Notice IDs were reconstructed from `curated_dmca_application_links.csv` and matching rows in `curated_dmca_repository_family_links.csv`, then dated using `ukb_dmca_notices.csv`. For the three frozen additions, a family notice was used only where the current family record explicitly listed that exact application as its candidate/application link. If multiple valid notice IDs were linked, the minimum notice date was retained. Missing mappings were left missing.

Broad 55 has {broad_all['total_positive_cases']} applications: {broad_all['dated_cases']} have a reproducibly identified earliest notice date, {broad_all['missing_notice_date']} are unresolved/missing, and {broad_all['notice_before_start']} have an earliest notice before project initiation. Curated 52 has {curated_all['dated_cases']} dated, {curated_all['missing_notice_date']} unresolved/missing, and {curated_all['notice_before_start']} notice-before-start cases.

Stored `first_dmca_notice_date` disagreements with the reconstructed minimum: {len(discrepancies)}. {discrepancy_text}

## Main Timing Table

| Broad-55 timing window | Retained cases | Pre Jul 5 2024 | On/after Jul 5 2024 |
|---|---:|---:|---:|
{chr(10).join(row('Broad55', label) for _, label in WINDOWS)}

| Curated-52 timing window | Retained cases | Pre Jul 5 2024 | On/after Jul 5 2024 |
|---|---:|---:|---:|
{chr(10).join(row('Curated52', label) for _, label in WINDOWS)}

## July-2024 Diagnostics

The three zoom figures display project initiation on the x-axis and lag months on the y-axis, using the symmetric displayed range {zoom_start.isoformat()} through {zoom_end.isoformat()} around the 5 July 2024 cutoff. This range contains every retained Broad-55 positive case in the plotted windows. The combined panel and the three individual figures apply the relevant common timing rule before plotting.

## Unresolved and Invalid Timing Mappings

Missing/unresolved notice dates ({len(unresolved)}): {format_apps(unresolved)}

Earliest notice before project initiation ({len(predates)}): {format_apps(predates)}

## Feasibility Recommendation

{' '.join(recommendation)} A later application-level common-window analysis should define a complete application risk set and should not treat notice timing as a leakage-occurrence date.

## Interpretation Limitation

The timing variable is the date of the first observed DMCA notice, not the date of the underlying leakage or public posting. Therefore this exercise studies documented notice timing relative to project initiation.

No RAP causal effect is estimated or claimed here.
"""


def main() -> None:
    for directory in (DATA_DIR, TABLE_DIR, FIGURE_DIR, REPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    frozen, audit, counts = reconstruct()
    write_csv(FROZEN_OUT, frozen, list(frozen[0]))
    write_csv(AUDIT_OUT, audit, list(audit[0]))
    write_csv(COUNTS_OUT, counts, list(counts[0]))
    dated_post = [row for row in audit if row["notice_after_project_start"] == "yes"]
    if not dated_post:
        raise ValueError("No valid post-start notice dates available for master plot.")
    all_starts = [parse_date(row["project_start_date"]) for row in dated_post]
    x_start, x_end = min(item for item in all_starts if item), max(item for item in all_starts if item)
    master_ymax = math.ceil(max(float(row["lag_months"]) for row in dated_post) / 12) * 12
    scatter_svg(MASTER_SVG, dated_post, "Time From UKB Project Initiation to First Observed DMCA Notice", f"Broad 55 applications; {len(dated_post)} with reproducibly linked notice dates plotted; earliest used when multiple notices exist.", x_start, x_end, master_ymax)
    retained_any = [row for row in audit if any(row[key] == "yes" for key, _ in WINDOWS)]
    retained_starts = [parse_date(row["project_start_date"]) for row in retained_any]
    half_years = max(2, math.ceil(max((POLICY_DATE - item).days for item in retained_starts if item) / 365.2425), math.ceil(max((item - POLICY_DATE).days for item in retained_starts if item) / 365.2425))
    zoom_start, zoom_end = add_years(POLICY_DATE, -half_years), add_years(POLICY_DATE, half_years)
    for window, label in WINDOWS:
        retained = [row for row in audit if row[window] == "yes"]
        scatter_svg(ZOOM_SVGS[window], retained, f"Broad-55: First Observed DMCA Notice Within {label}", f"Project initiation date on x-axis; lag months on y-axis; displayed {zoom_start.isoformat()} to {zoom_end.isoformat()}.", zoom_start, zoom_end, {"within_1y": 12, "within_18m": 18, "within_2y": 24}[window], zoom=True)
    panel_svg(PANEL_SVG, audit, zoom_start, zoom_end)
    write_text(REPORT_OUT, report(audit, counts, zoom_start, zoom_end))
    broad = [row for row in counts if row["definition"] == "Broad55"]
    print("Broad55 notice timing summary")
    for row in broad:
        print(f"{row['window']}: dated={row['dated_cases']} retained={row['retained_cases']} pre={row['pre_july2024_cases']} post={row['post_july2024_cases']} missing={row['missing_notice_date']} before_start={row['notice_before_start']}")


if __name__ == "__main__":
    main()
