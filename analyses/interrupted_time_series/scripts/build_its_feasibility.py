#!/usr/bin/env python3
"""Build descriptive ITS feasibility outputs from public UKB metadata."""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
DID_ARCHIVE = ROOT / "analyses" / "did_archive"

POLICY_DATE = date(2024, 7, 5)
APRIL_2026_SHOCK = date(2026, 4, 1)
ACCESS_DATE = "2026-08-27"

TIMING_UNIVERSE = (
    ROOT / "data" / "intermediate" / "timing_feasibility" / "timing_working_research_project_universe.csv"
)
STAGE3_CLASSIFICATION = (
    ROOT / "data" / "intermediate" / "rap_classification" / "stage3_project_rap_exposure_classification.csv"
)
APP_OUTCOMES = (
    DID_ARCHIVE
    / "data"
    / "analysis"
    / "design1_quarterly_publication"
    / "project_outcomes_input.csv"
)
QUARTER_PANEL = (
    DID_ARCHIVE
    / "data"
    / "analysis"
    / "design1_quarterly_publication"
    / "design1_quarterly_publication_panel.csv"
)
SCHEMA19 = ROOT / "data" / "raw" / "ukb_schema19_publications.tsv"
SCHEMA24 = ROOT / "data" / "raw" / "ukb_schema24_publication_applications.tsv"
SCHEMA4 = ROOT / "data" / "raw" / "ukb_schema4_returned_datasets.tsv"

DATA_DIR = PACKAGE / "data"
FIGURE_DIR = PACKAGE / "figures"
DESIGN_DIR = PACKAGE / "design"
REPORT_DIR = PACKAGE / "reports"

CONTROL_DEFS = ["CONTROL_C03", "CONTROL_C05", "CONTROL_C06"]

INSTITUTIONAL_DATES = [
    {
        "date": "2023-07",
        "label": "OMOP release on RAP",
        "source_url": "https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases",
        "notes": "Official past-release list records OMOP Field 20142 as RAP-only in July 2023.",
    },
    {
        "date": "2023-10",
        "label": "Expanded proteomics and imaging release",
        "source_url": "https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases",
        "notes": "Official past-release list records expanded proteomics and major imaging updates in October 2023.",
    },
    {
        "date": "2023-11-30",
        "label": "500k WGS release on UKB-RAP",
        "source_url": "https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/16019641094813-New-Data-release-on-UKB-RAP-WGS-Data-from-500-000-Participants-Proteomics-Data-Updated-Imaging-Data",
        "notes": "Official UKB-RAP release post dates the 500k WGS release to 30 November 2023.",
    },
    {
        "date": "2024-07-05",
        "label": "UKB data access institutional transition",
        "source_url": "https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/19996604847133-Changing-the-way-UK-Biobank-data-is-made-available-to-researchers-around-the-world",
        "notes": "This package treats 5 July 2024 as the policy transition date, not an observed project-level treatment date.",
    },
    {
        "date": "2025-11",
        "label": "Major November 2025 data release",
        "source_url": "https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases",
        "notes": "Official past-release list records major November 2025 updates across genomics, imaging, records, and biomarkers.",
    },
    {
        "date": "2026-04-01",
        "label": "RAP participant-withdrawal enforcement/platform governance shock",
        "source_url": "https://community.ukbiobank.ac.uk/hc/en-gb/articles/34853452782621-Participant-withdrawals-on-UKB-RAP",
        "notes": "Official UKB article says DNAnexus would begin enforcing withdrawals from 1 April 2026 where required.",
    },
    {
        "date": "2026-03-31",
        "label": "Additional UKB-RAP access requirement",
        "source_url": "https://community.ukbiobank.ac.uk/hc/en-gb/articles/22784123882909-Why-does-it-say-that-my-project-is-not-enabled-for-UKB-RAP",
        "notes": "Official UKB article records a new Code Repository training-module requirement from 31 March 2026.",
    },
]


@dataclass(frozen=True)
class BuildOutputs:
    project_starts_monthly: Path
    project_starts_quarterly: Path
    incumbent_publications_monthly: Path
    incumbent_publications_quarterly: Path
    comparative_quarterly: Path
    group_composition: Path
    modality_counts: Path
    age_band_quarterly: Path
    publication_lag: Path
    returned_data_feasibility: Path
    institution_counts: Path
    institutional_dates: Path
    data_inventory: Path
    summary_json: Path
    readme: Path
    stylized_inventory: Path
    design_proposal: Path
    feasibility_report: Path
    starts_figure: Path
    incumbent_figure: Path
    comparative_figure: Path


def output_paths() -> BuildOutputs:
    return BuildOutputs(
        project_starts_monthly=DATA_DIR / "its_project_starts_monthly.csv",
        project_starts_quarterly=DATA_DIR / "its_project_starts_quarterly.csv",
        incumbent_publications_monthly=DATA_DIR / "its_incumbent_publications_monthly.csv",
        incumbent_publications_quarterly=DATA_DIR / "its_incumbent_publications_quarterly.csv",
        comparative_quarterly=DATA_DIR / "its_comparative_quarterly.csv",
        group_composition=DATA_DIR / "its_group_composition.csv",
        modality_counts=DATA_DIR / "its_modality_project_counts.csv",
        age_band_quarterly=DATA_DIR / "its_age_band_quarterly.csv",
        publication_lag=DATA_DIR / "its_publication_lag.csv",
        returned_data_feasibility=DATA_DIR / "its_returned_data_feasibility.csv",
        institution_counts=DATA_DIR / "its_top_institutions.csv",
        institutional_dates=DATA_DIR / "its_institutional_dates.csv",
        data_inventory=DATA_DIR / "its_data_inventory.csv",
        summary_json=DATA_DIR / "its_feasibility_summary.json",
        readme=PACKAGE / "README.md",
        stylized_inventory=DESIGN_DIR / "stylized_facts_inventory.md",
        design_proposal=DESIGN_DIR / "its_design_proposal.md",
        feasibility_report=REPORT_DIR / "preliminary_feasibility_report.md",
        starts_figure=FIGURE_DIR / "its_project_starts_monthly.svg",
        incumbent_figure=FIGURE_DIR / "its_incumbent_publications_quarterly.svg",
        comparative_figure=FIGURE_DIR / "its_c05_group_quarterly_any_publication.svg",
    )


def read_table(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_table(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def parse_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_int(value: object) -> int:
    try:
        return int(float(str(value or "").strip()))
    except ValueError:
        return 0


def safe_float(value: object) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return 0.0


def month_label(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def month_floor(value: date) -> date:
    return date(value.year, value.month, 1)


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    return date(value.year + month // 12, month % 12 + 1, 1)


def month_end(value: date) -> date:
    return add_months(month_floor(value), 1) - timedelta(days=1)


def month_range(start: date, end: date) -> list[date]:
    out = []
    cursor = month_floor(start)
    stop = month_floor(end)
    while cursor <= stop:
        out.append(cursor)
        cursor = add_months(cursor, 1)
    return out


def quarter_label(value: date) -> str:
    return f"{value.year}Q{((value.month - 1) // 3) + 1}"


def quarter_start(value: date) -> date:
    first_month = ((value.month - 1) // 3) * 3 + 1
    return date(value.year, first_month, 1)


def add_quarters(value: date, quarters: int) -> date:
    return add_months(quarter_start(value), quarters * 3)


def quarter_end(value: date) -> date:
    return add_quarters(value, 1) - timedelta(days=1)


def quarter_range(start: date, end: date) -> list[date]:
    out = []
    cursor = quarter_start(start)
    stop = quarter_start(end)
    while cursor <= stop:
        out.append(cursor)
        cursor = add_quarters(cursor, 1)
    return out


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def median(values: list[float]) -> str:
    return f"{statistics.median(values):.3f}" if values else ""


def mean(values: list[float]) -> str:
    return f"{statistics.mean(values):.3f}" if values else ""


def pct(numerator: float, denominator: float) -> str:
    return f"{(100 * numerator / denominator):.2f}" if denominator else ""


def md_escape(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, object]], fields: list[str]) -> str:
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(fields) + " |"
    sep = "| " + " | ".join("---" for _ in fields) + " |"
    body = ["| " + " | ".join(md_escape(row.get(field, "")) for field in fields) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def broad_modality(row: dict[str, str]) -> str:
    text = " ".join(
        [
            row.get("stage3_already_rap_modalities", ""),
            row.get("stage3_legacy_route_modalities", ""),
            row.get("already_rap_modalities", ""),
            row.get("legacy_route_modalities", ""),
            row.get("ambiguous_modality_signals", ""),
            row.get("schema27_title", ""),
        ]
    ).upper()
    if any(term in text for term in ["WGS", "WES", "EXOME", "GENOTYPING", "GENETIC", "SEQUENCE", "PRS", "GWAS"]):
        return "genetics_sequence"
    if any(term in text for term in ["IMAGING", "MRI", "RETINAL", "FUNDUS", "OCT", "DXA"]):
        return "imaging"
    if any(term in text for term in ["LINKED_HEALTH_RECORDS", "EHR", "HES", "GP", "HOSPITAL", "CANCER_REGISTRY"]):
        return "ehr_linked_records"
    if any(term in text for term in ["PROTEOM", "METABOLOM", "BIOMARKER", "NMR"]):
        return "proteomics_metabolomics_biomarkers"
    if any(term in text for term in ["QUESTIONNAIRE", "ENVIRONMENT", "LIFESTYLE", "PHYSICAL", "ASSESSMENT"]):
        return "questionnaire_environment_lifestyle"
    return "other_or_unclear"


def age_band_at_policy(start: date | None) -> str:
    if not start or start >= POLICY_DATE:
        return "post_transition_start_or_missing"
    months = months_between(start, POLICY_DATE)
    if months < 24:
        return "recent_incumbent_lt2y"
    if months < 60:
        return "mid_age_incumbent_2_5y"
    return "mature_incumbent_5y_plus"


def group_label(raw: str) -> str:
    if raw == "treated":
        return "legacy_exposure_proxy"
    if raw == "control" or raw.startswith("control_"):
        return "rap_intensive_comparison"
    return "excluded"


def load_inputs() -> dict[str, object]:
    timing = read_table(TIMING_UNIVERSE)
    stage3 = {row.get("app_id", ""): row for row in read_table(STAGE3_CLASSIFICATION)}
    app_outcomes = {row.get("app_id", ""): row for row in read_table(APP_OUTCOMES)}
    panel = read_table(QUARTER_PANEL)
    schema19 = {row.get("pub_id", ""): row for row in read_table(SCHEMA19, delimiter="\t")}
    schema24 = read_table(SCHEMA24, delimiter="\t")
    returned = read_table(SCHEMA4, delimiter="\t")

    apps: dict[str, dict[str, str]] = {}
    for row in timing:
        app_id = row.get("app_id", "")
        if not app_id:
            continue
        merged = dict(row)
        if app_id in stage3:
            merged.update(stage3[app_id])
        if app_id in app_outcomes:
            merged.update(app_outcomes[app_id])
        merged["broad_modality"] = broad_modality(merged)
        apps[app_id] = merged

    return {
        "apps": apps,
        "stage3": stage3,
        "app_outcomes": app_outcomes,
        "panel": panel,
        "schema19": schema19,
        "schema24": schema24,
        "returned": returned,
    }


def build_project_start_series(apps: dict[str, dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    start_dates = [parse_date(row.get("start_date") or row.get("project_start_date")) for row in apps.values()]
    start_dates = [value for value in start_dates if value]
    monthly_counts = Counter(month_label(value) for value in start_dates)
    quarterly_counts = Counter(quarter_label(value) for value in start_dates)

    monthly_rows = []
    for month in month_range(min(start_dates), max(start_dates)):
        label = month_label(month)
        monthly_rows.append(
            {
                "month": label,
                "month_start": month.isoformat(),
                "new_projects": monthly_counts[label],
                "post_transition_month": int(month >= date(2024, 7, 1)),
                "transition_pause_window_jul_sep_2024": int(date(2024, 7, 1) <= month <= date(2024, 9, 1)),
                "october_2024_restart": int(label == "2024-10"),
                "april_2026_platform_shock_or_after": int(month >= date(2026, 4, 1)),
            }
        )

    quarterly_rows = []
    for quarter in quarter_range(min(start_dates), max(start_dates)):
        label = quarter_label(quarter)
        quarterly_rows.append(
            {
                "quarter": label,
                "quarter_start": quarter.isoformat(),
                "quarter_end": quarter_end(quarter).isoformat(),
                "new_projects": quarterly_counts[label],
                "post_transition_quarter": int(quarter >= date(2024, 7, 1)),
                "transition_quarter_2024q3": int(label == "2024Q3"),
                "april_2026_platform_shock_or_after": int(quarter >= date(2026, 4, 1)),
            }
        )
    return monthly_rows, quarterly_rows


def build_publication_events(
    apps: dict[str, dict[str, str]],
    schema19: dict[str, dict[str, str]],
    schema24: list[dict[str, str]],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    events: list[dict[str, object]] = []
    seen_app_pub: set[tuple[str, str]] = set()
    pub_to_apps: dict[str, set[str]] = defaultdict(set)
    audit = Counter()
    for link in schema24:
        app_id = str(link.get("app_id", "")).strip()
        pub_id = str(link.get("pub_id", "")).strip()
        if not app_id or not pub_id:
            audit["missing_link_fields"] += 1
            continue
        key = (app_id, pub_id)
        if key in seen_app_pub:
            audit["duplicate_app_pub_pair"] += 1
            continue
        seen_app_pub.add(key)
        if app_id not in apps:
            audit["app_not_in_matched_timing_universe"] += 1
            continue
        pub = schema19.get(pub_id)
        if not pub:
            audit["pub_missing_schema19"] += 1
            continue
        pub_date = parse_date(pub.get("date_pub"))
        if not pub_date:
            audit["non_exact_publication_date"] += 1
            continue
        start = parse_date(apps[app_id].get("start_date") or apps[app_id].get("project_start_date"))
        if not start:
            audit["missing_project_start_date"] += 1
            continue
        if pub_date < start:
            audit["publication_before_project_start"] += 1
            continue
        pub_to_apps[pub_id].add(app_id)
        events.append(
            {
                "app_id": app_id,
                "pub_id": pub_id,
                "publication_date": pub_date.isoformat(),
                "publication_month": month_label(pub_date),
                "publication_quarter": quarter_label(pub_date),
                "project_start_date": start.isoformat(),
                "lag_months_since_project_start": months_between(start, pub_date),
                "title": pub.get("title", ""),
            }
        )
    audit["exact_publication_app_links"] = len(events)
    audit["multi_application_publication_ids"] = sum(1 for values in pub_to_apps.values() if len(values) > 1)
    return events, dict(audit)


def build_incumbent_publication_series(
    apps: dict[str, dict[str, str]],
    events: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    start_by_app = {
        app_id: parse_date(row.get("start_date") or row.get("project_start_date"))
        for app_id, row in apps.items()
    }
    incumbents = {app_id for app_id, start in start_by_app.items() if start and start < POLICY_DATE}
    monthly_events: dict[str, list[dict[str, object]]] = defaultdict(list)
    quarterly_events: dict[str, list[dict[str, object]]] = defaultdict(list)
    for event in events:
        if event["app_id"] in incumbents:
            monthly_events[str(event["publication_month"])].append(event)
            quarterly_events[str(event["publication_quarter"])].append(event)

    monthly_rows = []
    for month in month_range(date(2022, 7, 1), date(2026, 6, 1)):
        label = month_label(month)
        end = month_end(month)
        at_risk = [app_id for app_id in incumbents if start_by_app[app_id] and start_by_app[app_id] <= end]
        linked_events = monthly_events[label]
        any_apps = {event["app_id"] for event in linked_events}
        monthly_rows.append(
            {
                "month": label,
                "month_start": month.isoformat(),
                "at_risk_incumbent_projects": len(at_risk),
                "publication_app_links": len(linked_events),
                "apps_with_any_publication": len(any_apps),
                "publications_per_100_at_risk_projects": pct(len(linked_events), len(at_risk)),
                "any_publication_rate_percent": pct(len(any_apps), len(at_risk)),
                "post_transition": int(month >= date(2024, 7, 1)),
                "transition_pause_window_jul_sep_2024": int(date(2024, 7, 1) <= month <= date(2024, 9, 1)),
                "april_2026_platform_shock_or_after": int(month >= date(2026, 4, 1)),
            }
        )

    quarterly_rows = []
    for quarter in quarter_range(date(2022, 7, 1), date(2026, 6, 1)):
        label = quarter_label(quarter)
        end = quarter_end(quarter)
        at_risk = [app_id for app_id in incumbents if start_by_app[app_id] and start_by_app[app_id] <= end]
        linked_events = quarterly_events[label]
        any_apps = {event["app_id"] for event in linked_events}
        quarterly_rows.append(
            {
                "quarter": label,
                "quarter_start": quarter.isoformat(),
                "quarter_end": end.isoformat(),
                "at_risk_incumbent_projects": len(at_risk),
                "publication_app_links": len(linked_events),
                "apps_with_any_publication": len(any_apps),
                "publications_per_100_at_risk_projects": pct(len(linked_events), len(at_risk)),
                "any_publication_rate_percent": pct(len(any_apps), len(at_risk)),
                "post_transition": int(quarter >= date(2024, 7, 1)),
                "transition_quarter_2024q3": int(label == "2024Q3"),
                "april_2026_platform_shock_or_after": int(quarter >= date(2026, 4, 1)),
            }
        )
    return monthly_rows, quarterly_rows


def build_comparative_quarterly(panel: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    apps_by_cell: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in panel:
        quarter = row.get("quarter", "")
        if not quarter:
            continue
        for control_def in CONTROL_DEFS:
            label = group_label(row.get(f"regression_group_{control_def}", ""))
            if label == "excluded":
                continue
            key = (control_def, label, quarter)
            grouped[key]["publication_count"] += safe_int(row.get("publication_count"))
            grouped[key]["any_publication_sum"] += safe_int(row.get("any_publication"))
            grouped[key]["project_periods"] += 1
            apps_by_cell[key].add(row.get("app_id", ""))
    rows = []
    for key in sorted(grouped):
        control_def, label, quarter = key
        values = grouped[key]
        periods = values["project_periods"]
        rows.append(
            {
                "exposure_proxy_definition": control_def,
                "comparison_group": label,
                "quarter": quarter,
                "project_periods": int(periods),
                "apps_observed": len(apps_by_cell[key]),
                "publication_count": int(values["publication_count"]),
                "any_publication_rate_percent": pct(values["any_publication_sum"], periods),
                "publication_count_per_100_project_periods": pct(values["publication_count"], periods),
                "post_transition": int(quarter >= "2024Q3"),
                "transition_quarter_2024q3": int(quarter == "2024Q3"),
                "april_2026_platform_shock_or_after": int(quarter >= "2026Q2"),
            }
        )
    return rows


def build_age_band_quarterly(
    panel: list[dict[str, str]],
    apps: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    apps_by_cell: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in panel:
        app_id = row.get("app_id", "")
        start = parse_date(apps.get(app_id, {}).get("start_date") or row.get("project_start_date"))
        band = age_band_at_policy(start)
        if band == "post_transition_start_or_missing":
            continue
        key = (band, row.get("quarter", ""))
        grouped[key]["publication_count"] += safe_int(row.get("publication_count"))
        grouped[key]["any_publication_sum"] += safe_int(row.get("any_publication"))
        grouped[key]["project_periods"] += 1
        apps_by_cell[key].add(app_id)
    rows = []
    for key in sorted(grouped):
        band, quarter = key
        periods = grouped[key]["project_periods"]
        rows.append(
            {
                "project_age_band_at_transition": band,
                "quarter": quarter,
                "project_periods": int(periods),
                "apps_observed": len(apps_by_cell[key]),
                "publication_count": int(grouped[key]["publication_count"]),
                "any_publication_rate_percent": pct(grouped[key]["any_publication_sum"], periods),
                "publication_count_per_100_project_periods": pct(grouped[key]["publication_count"], periods),
            }
        )
    return rows


def build_group_composition(app_outcomes: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    for control_def in CONTROL_DEFS:
        for label in ["legacy_exposure_proxy", "rap_intensive_comparison"]:
            selected = [
                row
                for row in app_outcomes.values()
                if group_label(row.get(f"regression_group_{control_def}", "")) == label
                and safe_int(row.get("p1_existing_project_sample")) == 1
            ]
            class_counts = Counter(row.get("original_stage3_classification", "") for row in selected)
            modality_counts = Counter(broad_modality(row) for row in selected)
            ages = []
            for row in selected:
                start = parse_date(row.get("project_start_date"))
                if start and start < POLICY_DATE:
                    ages.append(months_between(start, POLICY_DATE) / 12)
            pre_counts = [safe_float(row.get("pub_pre24")) for row in selected]
            any_pre = [safe_float(row.get("any_pub_pre24")) for row in selected]
            rows.append(
                {
                    "exposure_proxy_definition": control_def,
                    "comparison_group": label,
                    "projects": len(selected),
                    "mean_pre_2024_publications": mean(pre_counts),
                    "any_pre_2024_publication_rate_percent": pct(sum(any_pre), len(any_pre)),
                    "median_project_age_years_at_transition": median(ages),
                    "original_class_composition": "; ".join(f"{k}={v}" for k, v in sorted(class_counts.items()) if k),
                    "broad_modality_composition": "; ".join(f"{k}={v}" for k, v in sorted(modality_counts.items())),
                }
            )
    return rows


def build_modality_counts(apps: dict[str, dict[str, str]], app_outcomes: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    by_modality: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in apps.values():
        by_modality[broad_modality(row)].append(row)
    rows = []
    for modality, selected in sorted(by_modality.items()):
        starts = [parse_date(row.get("start_date") or row.get("project_start_date")) for row in selected]
        starts = [value for value in starts if value]
        incumbent = [value for value in starts if value < POLICY_DATE]
        post = [value for value in starts if value >= POLICY_DATE]
        c05_legacy = 0
        c05_rap = 0
        for row in selected:
            app_row = app_outcomes.get(row.get("app_id", ""), {})
            if app_row.get("regression_group_CONTROL_C05") == "treated":
                c05_legacy += 1
            if app_row.get("regression_group_CONTROL_C05") == "control":
                c05_rap += 1
        rows.append(
            {
                "broad_modality": modality,
                "projects": len(selected),
                "incumbent_projects_before_2024_07_05": len(incumbent),
                "post_transition_start_projects": len(post),
                "c05_legacy_exposure_proxy_projects": c05_legacy,
                "c05_rap_intensive_comparison_projects": c05_rap,
                "first_start": min(starts).isoformat() if starts else "",
                "last_start": max(starts).isoformat() if starts else "",
            }
        )
    return rows


def build_publication_lag(events: list[dict[str, object]]) -> list[dict[str, object]]:
    bins = [
        ("0_6_months", 0, 6),
        ("7_12_months", 7, 12),
        ("13_24_months", 13, 24),
        ("25_48_months", 25, 48),
        ("49_plus_months", 49, 9999),
    ]
    counts = Counter()
    lag_values = []
    for event in events:
        lag = int(event["lag_months_since_project_start"])
        lag_values.append(lag)
        for name, low, high in bins:
            if low <= lag <= high:
                counts[name] += 1
                break
    total = len(events)
    rows = []
    for name, low, high in bins:
        rows.append(
            {
                "lag_bin": name,
                "min_lag_months": low,
                "max_lag_months": "" if high == 9999 else high,
                "publication_app_links": counts[name],
                "share_percent": pct(counts[name], total),
                "median_lag_months_all_events": median([float(value) for value in lag_values]),
            }
        )
    return rows


def build_returned_data_feasibility(returned: list[dict[str, str]]) -> list[dict[str, object]]:
    fields = sorted(returned[0].keys()) if returned else []
    date_like = [field for field in fields if "date" in field.lower() or "time" in field.lower()]
    return [
        {
            "candidate_fact": "Returned datasets timing",
            "rows": len(returned),
            "fields": "; ".join(fields),
            "date_like_fields": "; ".join(date_like),
            "feasibility": "LOW" if not date_like else "MEDIUM",
            "notes": "Schema 4 gives returned-data titles/application IDs but no usable timing field in the local public extract."
            if not date_like
            else "Date-like fields exist and need manual validation before use.",
        }
    ]


def build_institution_counts(apps: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    by_inst: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in apps.values():
        inst = row.get("schema27_institution") or row.get("institution") or "missing"
        by_inst[inst].append(row)
    rows = []
    for inst, selected in sorted(by_inst.items(), key=lambda item: (-len(item[1]), item[0]))[:25]:
        starts = [parse_date(row.get("start_date") or row.get("project_start_date")) for row in selected]
        starts = [value for value in starts if value]
        rows.append(
            {
                "institution": inst,
                "projects": len(selected),
                "starts_2024": sum(1 for value in starts if value.year == 2024),
                "starts_jul_sep_2024": sum(1 for value in starts if date(2024, 7, 1) <= value <= date(2024, 9, 30)),
                "starts_oct_2024": sum(1 for value in starts if value.year == 2024 and value.month == 10),
                "notes": "Institution strings are not country-standardized.",
            }
        )
    return rows


def build_data_inventory(inputs: dict[str, object], audit: dict[str, int]) -> list[dict[str, object]]:
    return [
        {
            "data_source": "Matched UKB project starts",
            "path": str(TIMING_UNIVERSE.relative_to(ROOT)),
            "rows": len(inputs["apps"]),
            "role": "Shared source for project-entry ITS and denominators.",
            "measurement_issue": "Excludes unmatched Schema 27 records retained in Stage 2.5 audit.",
        },
        {
            "data_source": "Stage 3 RAP exposure proxies",
            "path": str(STAGE3_CLASSIFICATION.relative_to(ROOT)),
            "rows": len(inputs["stage3"]),
            "role": "Descriptive legacy-exposure and RAP-intensive proxy construction.",
            "measurement_issue": "Proxy classifications are not observed treatment status.",
        },
        {
            "data_source": "Archived Design 1 app outcomes",
            "path": str(APP_OUTCOMES.relative_to(ROOT)),
            "rows": len(inputs["app_outcomes"]),
            "role": "C03/C05/C06 group labels and pre-policy baseline fields.",
            "measurement_issue": "Historical DID terms are relabelled descriptively in ITS outputs.",
        },
        {
            "data_source": "Archived Design 1 quarterly panel",
            "path": str(QUARTER_PANEL.relative_to(ROOT)),
            "rows": len(inputs["panel"]),
            "role": "Quarterly incumbent publication trajectories.",
            "measurement_issue": "Project activity/expiry status is not observed.",
        },
        {
            "data_source": "Schema 19 publications",
            "path": str(SCHEMA19.relative_to(ROOT)),
            "rows": len(inputs["schema19"]),
            "role": "Exact publication dates and publication metadata.",
            "measurement_issue": f"Non-exact app-publication dates skipped: {audit.get('non_exact_publication_date', 0)}.",
        },
        {
            "data_source": "Schema 24 publication-application links",
            "path": str(SCHEMA24.relative_to(ROOT)),
            "rows": len(inputs["schema24"]),
            "role": "Application-publication linkage.",
            "measurement_issue": f"Multi-application publication IDs observed: {audit.get('multi_application_publication_ids', 0)}.",
        },
        {
            "data_source": "Schema 4 returned datasets",
            "path": str(SCHEMA4.relative_to(ROOT)),
            "rows": len(inputs["returned"]),
            "role": "Candidate output metadata.",
            "measurement_issue": "No usable timing field in the local public extract.",
        },
    ]


def svg_bar_chart(path: Path, rows: list[dict[str, object]], label_field: str, value_field: str, title: str) -> None:
    plot_rows = [row for row in rows if "2023-01" <= str(row[label_field]) <= "2025-12"]
    width, height = 1000, 360
    left, right, top, bottom = 52, 20, 36, 58
    plot_w, plot_h = width - left - right, height - top - bottom
    max_value = max([safe_float(row[value_field]) for row in plot_rows] or [1])
    band = plot_w / max(1, len(plot_rows))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="24" font-family="Arial" font-size="16" font-weight="700">{title}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#333"/>',
    ]
    for idx, row in enumerate(plot_rows):
        value = safe_float(row[value_field])
        h = 0 if max_value == 0 else (value / max_value) * plot_h
        x = left + idx * band + 1
        y = top + plot_h - h
        label = str(row[label_field])
        color = "#d95f02" if "2024-07" <= label <= "2024-09" else "#1b9e77"
        color = "#7570b3" if label == "2024-10" else color
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(1, band - 2):.2f}" height="{h:.2f}" fill="{color}"/>')
        if label.endswith("-01") or label in {"2024-07", "2024-10"}:
            parts.append(f'<text x="{x:.2f}" y="{height - 22}" font-family="Arial" font-size="10" transform="rotate(45 {x:.2f},{height - 22})">{label}</text>')
    for tick in range(0, int(max_value) + 1, max(1, math.ceil(max_value / 5))):
        y = top + plot_h - (tick / max_value) * plot_h if max_value else top + plot_h
        parts.append(f'<line x1="{left - 4}" y1="{y:.2f}" x2="{left}" y2="{y:.2f}" stroke="#333"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 3:.2f}" text-anchor="end" font-family="Arial" font-size="10">{tick}</text>')
    parts.append('<text x="52" y="342" font-family="Arial" font-size="11" fill="#555">Orange = July-September 2024 pause window; purple = October 2024 restart.</text>')
    parts.append("</svg>")
    write_text(path, "\n".join(parts))


def svg_line_chart(
    path: Path,
    series: dict[str, list[tuple[str, float]]],
    title: str,
    note: str,
) -> None:
    labels = sorted({label for points in series.values() for label, _ in points})
    values = [value for points in series.values() for _, value in points]
    width, height = 1000, 360
    left, right, top, bottom = 64, 140, 36, 56
    plot_w, plot_h = width - left - right, height - top - bottom
    max_value = max(values or [1])
    min_value = min(values or [0])
    if max_value == min_value:
        max_value += 1
    x_pos = {label: left + idx * (plot_w / max(1, len(labels) - 1)) for idx, label in enumerate(labels)}

    def y_pos(value: float) -> float:
        return top + plot_h - ((value - min_value) / (max_value - min_value)) * plot_h

    colors = ["#1b9e77", "#d95f02", "#7570b3", "#666666"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="24" font-family="Arial" font-size="16" font-weight="700">{title}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#333"/>',
    ]
    for tick_idx in range(6):
        value = min_value + (max_value - min_value) * tick_idx / 5
        y = y_pos(value)
        parts.append(f'<line x1="{left - 4}" y1="{y:.2f}" x2="{left}" y2="{y:.2f}" stroke="#333"/>')
        parts.append(f'<text x="{left - 8}" y="{y + 3:.2f}" text-anchor="end" font-family="Arial" font-size="10">{value:.1f}</text>')
    for idx, label in enumerate(labels):
        if label.endswith("Q1") or label in {"2024Q3", "2026Q2"}:
            x = x_pos[label]
            parts.append(f'<text x="{x:.2f}" y="{height - 24}" font-family="Arial" font-size="10" transform="rotate(45 {x:.2f},{height - 24})">{label}</text>')
    for line_idx, (name, points) in enumerate(series.items()):
        color = colors[line_idx % len(colors)]
        path_data = " ".join(
            f'{"M" if idx == 0 else "L"} {x_pos[label]:.2f} {y_pos(value):.2f}'
            for idx, (label, value) in enumerate(points)
        )
        parts.append(f'<path d="{path_data}" fill="none" stroke="{color}" stroke-width="2.4"/>')
        for label, value in points:
            parts.append(f'<circle cx="{x_pos[label]:.2f}" cy="{y_pos(value):.2f}" r="3" fill="{color}"/>')
        legend_y = top + 18 + line_idx * 20
        parts.append(f'<rect x="{width - right + 18}" y="{legend_y - 10}" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{width - right + 36}" y="{legend_y}" font-family="Arial" font-size="11">{name}</text>')
    for marker, label in [("2024Q3", "Jul 2024"), ("2026Q2", "Apr 2026")]:
        if marker in x_pos:
            x = x_pos[marker]
            parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_h}" stroke="#555" stroke-dasharray="4 4"/>')
            parts.append(f'<text x="{x + 4:.2f}" y="{top + 12}" font-family="Arial" font-size="10" fill="#555">{label}</text>')
    parts.append(f'<text x="{left}" y="342" font-family="Arial" font-size="11" fill="#555">{note}</text>')
    parts.append("</svg>")
    write_text(path, "\n".join(parts))


def build_figures(
    paths: BuildOutputs,
    monthly_starts: list[dict[str, object]],
    incumbent_quarterly: list[dict[str, object]],
    comparative_quarterly: list[dict[str, object]],
) -> None:
    svg_bar_chart(paths.starts_figure, monthly_starts, "month", "new_projects", "Monthly UKB Project Starts")
    incumbent_series = {
        "publication app-links": [
            (str(row["quarter"]), safe_float(row["publication_app_links"]))
            for row in incumbent_quarterly
            if "2022Q3" <= str(row["quarter"]) <= "2026Q2"
        ]
    }
    svg_line_chart(
        paths.incumbent_figure,
        incumbent_series,
        "Quarterly Incumbent Publication App-Links",
        "Counts are app-publication links with exact Schema 19 dates; publication lag remains central.",
    )
    c05 = [row for row in comparative_quarterly if row["exposure_proxy_definition"] == "CONTROL_C05"]
    series: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in c05:
        series[str(row["comparison_group"])].append((str(row["quarter"]), safe_float(row["any_publication_rate_percent"])))
    svg_line_chart(
        paths.comparative_figure,
        dict(series),
        "C05 Descriptive Group Trajectories",
        "Legacy-exposure and RAP-intensive labels are descriptive proxies, not treatment/control status.",
    )


def summarize(
    monthly_starts: list[dict[str, object]],
    quarterly_starts: list[dict[str, object]],
    incumbent_quarterly: list[dict[str, object]],
    comparative: list[dict[str, object]],
    group_composition: list[dict[str, object]],
    modality_counts: list[dict[str, object]],
    publication_audit: dict[str, int],
    returned_feasibility: list[dict[str, object]],
) -> dict[str, object]:
    month_counts = {row["month"]: safe_int(row["new_projects"]) for row in monthly_starts}
    quarter_counts = {row["quarter"]: safe_int(row["new_projects"]) for row in quarterly_starts}
    pre2024_months = [row for row in monthly_starts if "2023-01" <= str(row["month"]) <= "2023-12"]
    pre2024_values = [safe_int(row["new_projects"]) for row in pre2024_months]
    inc_by_q = {row["quarter"]: row for row in incumbent_quarterly}
    c05 = [row for row in comparative if row["exposure_proxy_definition"] == "CONTROL_C05"]
    c05_groups = {
        row["comparison_group"]: row
        for row in group_composition
        if row["exposure_proxy_definition"] == "CONTROL_C05"
    }
    return {
        "source_access_date": ACCESS_DATE,
        "policy_transition_date": POLICY_DATE.isoformat(),
        "april_2026_platform_shock_date": APRIL_2026_SHOCK.isoformat(),
        "known_2024_start_pattern": {
            "2024-04": month_counts.get("2024-04", 0),
            "2024-05": month_counts.get("2024-05", 0),
            "2024-06": month_counts.get("2024-06", 0),
            "2024-07": month_counts.get("2024-07", 0),
            "2024-08": month_counts.get("2024-08", 0),
            "2024-09": month_counts.get("2024-09", 0),
            "2024-10": month_counts.get("2024-10", 0),
        },
        "project_start_quarter_pattern": {
            "2024Q2": quarter_counts.get("2024Q2", 0),
            "2024Q3": quarter_counts.get("2024Q3", 0),
            "2024Q4": quarter_counts.get("2024Q4", 0),
        },
        "calendar_2023_monthly_start_min": min(pre2024_values) if pre2024_values else 0,
        "calendar_2023_monthly_start_max": max(pre2024_values) if pre2024_values else 0,
        "calendar_2023_monthly_start_mean": round(statistics.mean(pre2024_values), 2) if pre2024_values else 0,
        "incumbent_publication_quarters": {
            key: {
                "publication_app_links": safe_int(row.get("publication_app_links")),
                "any_publication_rate_percent": row.get("any_publication_rate_percent", ""),
                "at_risk_incumbent_projects": safe_int(row.get("at_risk_incumbent_projects")),
            }
            for key, row in inc_by_q.items()
            if key in {"2024Q2", "2024Q3", "2024Q4", "2025Q1", "2026Q2"}
        },
        "c05_group_projects": {
            key: {
                "projects": safe_int(row.get("projects")),
                "mean_pre_2024_publications": row.get("mean_pre_2024_publications"),
                "any_pre_2024_publication_rate_percent": row.get("any_pre_2024_publication_rate_percent"),
                "median_project_age_years_at_transition": row.get("median_project_age_years_at_transition"),
            }
            for key, row in c05_groups.items()
        },
        "c05_quarterly_rows": len(c05),
        "modality_project_counts": {row["broad_modality"]: safe_int(row["projects"]) for row in modality_counts},
        "publication_audit": publication_audit,
        "returned_data_feasibility": returned_feasibility[0] if returned_feasibility else {},
        "feasibility_ratings": {
            "project_entry_starts": "HIGH",
            "aggregate_incumbent_publications": "HIGH",
            "comparative_exposure_proxy_its": "MEDIUM",
            "recent_vs_mature_projects": "MEDIUM",
            "modality_heterogeneity": "MEDIUM",
            "institution_country_patterns": "LOW_MEDIUM",
            "returned_data_timing": "LOW",
        },
    }


def build_readme(paths: BuildOutputs) -> str:
    return f"""# Interrupted Time-Series And Stylized-Facts Analysis

The objective is descriptive rather than causal: to document temporal and cross-project patterns surrounding the July 2024 UK Biobank RAP transition and use robust stylized facts to motivate and discipline the analytical model.

## Contents

- `design/stylized_facts_inventory.md`: broad inventory of candidate facts, data coverage, limitations, and priority.
- `design/its_design_proposal.md`: technical proposal for aggregate, comparative, and event-time descriptive ITS designs.
- `reports/preliminary_feasibility_report.md`: supervisor-facing feasibility report.
- `data/`: generated feasibility tables from shared public UKB metadata and archived DID panel outputs.
- `figures/`: preliminary raw figures used to assess candidate stylized facts.
- `scripts/build_its_feasibility.py`: reproducible builder for this package.

## Run

```bash
python3 analyses/interrupted_time_series/scripts/build_its_feasibility.py
```

The package does not use participant-level UK Biobank data and does not use DMCA outcomes.
"""


def build_stylized_inventory(summary: dict[str, object]) -> str:
    start_pattern = summary["known_2024_start_pattern"]
    c05 = summary["c05_group_projects"]
    rows = [
        {
            "Candidate fact / research question": "Was project entry unusually disrupted around the July 2024 transition?",
            "Outcome": "New project starts",
            "Unit of observation": "Calendar month",
            "Frequency": "Month and quarter",
            "Sample": "Matched UKB project-start universe",
            "Data source(s)": "Stage 2.5 matched project starts",
            "Available time coverage": "2012-08 through latest matched 2026 starts",
            "Missingness / measurement issues": "132 unmatched Schema 27 records excluded from working sample.",
            "Group/exposure proxy if applicable": "None primary; modality splits feasible.",
            "Key transition dates": "2024-07-05; July-September 2024 pause; October 2024 restart",
            "Important concurrent shocks/confounds": "Administrative batching, onboarding/training, data-refresh timing.",
            "Proposed raw figure": "Monthly starts bar chart",
            "Proposed descriptive regression, if any": "Segmented monthly count ITS with seasonality and transition-window coding.",
            "What empirical pattern would be informative": f"Verified 2024 pattern: Apr {start_pattern['2024-04']}, May {start_pattern['2024-05']}, Jun {start_pattern['2024-06']}, Jul {start_pattern['2024-07']}, Aug {start_pattern['2024-08']}, Sep {start_pattern['2024-09']}, Oct {start_pattern['2024-10']}.",
            "What the pattern CANNOT establish": "It cannot attribute the entry pause to RAP rather than administrative timing.",
            "Possible relevance to the CURRENT theoretical model": "Disciplines entry/friction timing around institutional transition.",
            "Feasibility rating": "HIGH",
            "Priority recommendation": "Highest priority first figure.",
        },
        {
            "Candidate fact / research question": "Did aggregate incumbent publications show an immediate or delayed break?",
            "Outcome": "Publication app-links and any-publication rate",
            "Unit of observation": "Incumbent project-period",
            "Frequency": "Month and quarter",
            "Sample": "Projects started before 2024-07-05",
            "Data source(s)": "Schema 19/24 publication links; matched starts",
            "Available time coverage": "Exact publication dates through 2026Q2 in local panel",
            "Missingness / measurement issues": "Publication lag; exact-date-only restriction; active status unavailable.",
            "Group/exposure proxy if applicable": "None for aggregate.",
            "Key transition dates": "2024Q3 transition; 2026Q2 platform shock period",
            "Important concurrent shocks/confounds": "Publication production lags; data releases in late 2023 and 2025.",
            "Proposed raw figure": "Quarterly incumbent publication app-link line",
            "Proposed descriptive regression, if any": "Segmented quarterly ITS with separate immediate and delayed post windows.",
            "What empirical pattern would be informative": "Immediate break, delayed 2025 movement, recovery, or no visible discontinuity.",
            "What the pattern CANNOT establish": "No observed project activity or RAP migration, so not a causal RAP effect.",
            "Possible relevance to the CURRENT theoretical model": "Constrains whether output response is immediate or lagged.",
            "Feasibility rating": "HIGH",
            "Priority recommendation": "Second priority after entry plot.",
        },
        {
            "Candidate fact / research question": "Did legacy-exposure and RAP-intensive proxy groups show different post-transition trajectories?",
            "Outcome": "Publication count and any-publication rate",
            "Unit of observation": "Project-quarter by descriptive group",
            "Frequency": "Quarter",
            "Sample": "Incumbent C03/C05/C06 eligible groups",
            "Data source(s)": "Archived Design 1 panel; Stage 3 exposure proxies",
            "Available time coverage": "2022Q3-2026Q2",
            "Missingness / measurement issues": "Proxy groups differ in baseline intensity and composition.",
            "Group/exposure proxy if applicable": "C03/C05/C06; C05 has "
            + f"{c05.get('legacy_exposure_proxy', {}).get('projects', '')} legacy-proxy and {c05.get('rap_intensive_comparison', {}).get('projects', '')} RAP-intensive comparison projects.",
            "Key transition dates": "2024Q3; 2026Q2 separately marked",
            "Important concurrent shocks/confounds": "Scientific modality and project age strongly related to exposure proxy.",
            "Proposed raw figure": "C05 group any-publication trajectory",
            "Proposed descriptive regression, if any": "Comparative segmented ITS with group-specific level/slope changes.",
            "What empirical pattern would be informative": "Post-transition differential change in trajectories after showing baseline composition.",
            "What the pattern CANNOT establish": "No untreated counterfactual; no observed migration date.",
            "Possible relevance to the CURRENT theoretical model": "Disciplines heterogeneity by legacy-data exposure.",
            "Feasibility rating": "MEDIUM",
            "Priority recommendation": "Use after raw aggregate plots and composition table.",
        },
        {
            "Candidate fact / research question": "Were recent incumbents more disrupted than mature incumbents?",
            "Outcome": "Publication count and any-publication rate",
            "Unit of observation": "Project-quarter",
            "Frequency": "Quarter",
            "Sample": "Pre-transition projects grouped by age at transition",
            "Data source(s)": "Matched starts; archived quarterly panel",
            "Available time coverage": "2022Q3-2026Q2",
            "Missingness / measurement issues": "Age does not reveal active/expired project status.",
            "Group/exposure proxy if applicable": "Recent <2 years, 2-5 years, 5+ years at 2024-07-05.",
            "Key transition dates": "2024Q3; 2026Q2 robustness period",
            "Important concurrent shocks/confounds": "Lifecycle, cohort composition, publication lag.",
            "Proposed raw figure": "Age-band quarterly trajectories",
            "Proposed descriptive regression, if any": "Age-band comparative ITS or age-bin adjusted aggregate ITS.",
            "What empirical pattern would be informative": "Different delayed trajectories by maturity.",
            "What the pattern CANNOT establish": "Age is not observed remaining project horizon.",
            "Possible relevance to the CURRENT theoretical model": "Maps to remaining-horizon and adjustment-cost mechanisms.",
            "Feasibility rating": "MEDIUM",
            "Priority recommendation": "Use as a prespecified heterogeneity check.",
        },
        {
            "Candidate fact / research question": "Do extensive and intensive publication margins diverge?",
            "Outcome": "Any publication; publication count; conditional positive count",
            "Unit of observation": "Project-period",
            "Frequency": "Quarter primary; month secondary",
            "Sample": "Incumbent projects",
            "Data source(s)": "Schema 19/24; archived panel",
            "Available time coverage": "2022Q3-2026Q2",
            "Missingness / measurement issues": "Counts are skewed; exact-date restriction.",
            "Group/exposure proxy if applicable": "Aggregate and C05/C06 groups.",
            "Key transition dates": "2024Q3 and 2026Q2",
            "Important concurrent shocks/confounds": "Publication lag and high-output projects.",
            "Proposed raw figure": "Count and any-publication panels side-by-side",
            "Proposed descriptive regression, if any": "Linear and count-model robustness, reported descriptively.",
            "What empirical pattern would be informative": "Change in probability of any output vs change in output intensity.",
            "What the pattern CANNOT establish": "Cannot identify productivity mechanism without active status.",
            "Possible relevance to the CURRENT theoretical model": "Separates extensive interruption from intensity adjustment.",
            "Feasibility rating": "HIGH",
            "Priority recommendation": "Pair with aggregate publication figure.",
        },
        {
            "Candidate fact / research question": "Are trajectories heterogeneous across data modalities?",
            "Outcome": "Starts and publications by broad modality",
            "Unit of observation": "Project or project-period",
            "Frequency": "Month/quarter",
            "Sample": "Projects with text-based modality proxy",
            "Data source(s)": "Stage 3 modality flags and project text",
            "Available time coverage": "Project starts 2012-2026; panel 2022Q3-2026Q2",
            "Missingness / measurement issues": "Text classification quality varies; categories overlap.",
            "Group/exposure proxy if applicable": "Genetics, imaging, EHR, omics/biomarkers, questionnaire/environment, other.",
            "Key transition dates": "Late 2023 WGS, 2024Q3, 2026Q2",
            "Important concurrent shocks/confounds": "WGS/WES release, proteomics/imaging releases.",
            "Proposed raw figure": "Small multiples by broad modality",
            "Proposed descriptive regression, if any": "Modality-specific descriptive ITS only if cells are large.",
            "What empirical pattern would be informative": "Different timing for data-intensive versus low-intensity modalities.",
            "What the pattern CANNOT establish": "Cannot separate modality demand from RAP exposure cleanly.",
            "Possible relevance to the CURRENT theoretical model": "Disciplines heterogeneity by data-intensity.",
            "Feasibility rating": "MEDIUM",
            "Priority recommendation": "Use only broad, populated categories.",
        },
        {
            "Candidate fact / research question": "Did project-age composition change mechanically over time?",
            "Outcome": "At-risk projects by age band",
            "Unit of observation": "Project-quarter",
            "Frequency": "Quarter",
            "Sample": "At-risk panel rows",
            "Data source(s)": "Matched starts; archived panel",
            "Available time coverage": "2022Q3-2026Q2",
            "Missingness / measurement issues": "No active/expired project status.",
            "Group/exposure proxy if applicable": "Age bands",
            "Key transition dates": "2024Q3",
            "Important concurrent shocks/confounds": "Entry pause/restart changes future composition.",
            "Proposed raw figure": "Age composition over time",
            "Proposed descriptive regression, if any": "Composition-adjusted ITS as diagnostic.",
            "What empirical pattern would be informative": "Aggregate publication pattern explained by changing risk-set composition.",
            "What the pattern CANNOT establish": "Cannot prove active-project lifecycle.",
            "Possible relevance to the CURRENT theoretical model": "Separates entry composition from incumbent output response.",
            "Feasibility rating": "MEDIUM",
            "Priority recommendation": "Diagnostic, not headline.",
        },
        {
            "Candidate fact / research question": "Do institution patterns account for entry changes?",
            "Outcome": "Project starts by institution",
            "Unit of observation": "Project",
            "Frequency": "Month/quarter",
            "Sample": "Top institutions by project count",
            "Data source(s)": "Schema 27 institution strings",
            "Available time coverage": "2012-2026 starts",
            "Missingness / measurement issues": "Institution names are not country-standardized.",
            "Group/exposure proxy if applicable": "Top institutions only.",
            "Key transition dates": "2024Q3",
            "Important concurrent shocks/confounds": "Institution-level submission batching.",
            "Proposed raw figure": "Top-institution start counts",
            "Proposed descriptive regression, if any": "Only if cells are sufficiently populated.",
            "What empirical pattern would be informative": "Whether October 2024 restart is broad-based or concentrated.",
            "What the pattern CANNOT establish": "No country-level inference without cleaning.",
            "Possible relevance to the CURRENT theoretical model": "Disciplines whether frictions are centralized or broad.",
            "Feasibility rating": "LOW_MEDIUM",
            "Priority recommendation": "Table only unless cleaned further.",
        },
        {
            "Candidate fact / research question": "What are publication-lag distributions?",
            "Outcome": "Months from project start to publication",
            "Unit of observation": "Application-publication link",
            "Frequency": "Lag bins",
            "Sample": "Exact-date app-publication links after project start",
            "Data source(s)": "Schema 19/24; matched starts",
            "Available time coverage": "All exact-date linked publications",
            "Missingness / measurement issues": "Year-only publication dates skipped; links may be multi-application.",
            "Group/exposure proxy if applicable": "Aggregate first; group splits optional.",
            "Key transition dates": "Used to justify delayed post windows.",
            "Important concurrent shocks/confounds": "Publication process lag.",
            "Proposed raw figure": "Lag histogram",
            "Proposed descriptive regression, if any": "Delayed-window ITS rather than redefining policy date.",
            "What empirical pattern would be informative": "How long post-transition publication effects could plausibly take.",
            "What the pattern CANNOT establish": "Cannot identify project activity or manuscript timing.",
            "Possible relevance to the CURRENT theoretical model": "Pins down lag structure for output response.",
            "Feasibility rating": "HIGH",
            "Priority recommendation": "Use in design justification.",
        },
        {
            "Candidate fact / research question": "Can returned-dataset timing be used?",
            "Outcome": "Returned dataset availability/timing",
            "Unit of observation": "Returned dataset metadata row",
            "Frequency": "None available locally",
            "Sample": "Schema 4 returned datasets",
            "Data source(s)": "UKB Schema 4",
            "Available time coverage": "No date field in local extract",
            "Missingness / measurement issues": "Timing unavailable.",
            "Group/exposure proxy if applicable": "Application link only.",
            "Key transition dates": "Not usable",
            "Important concurrent shocks/confounds": "Unknown",
            "Proposed raw figure": "None",
            "Proposed descriptive regression, if any": "None now.",
            "What empirical pattern would be informative": "Returned-output timing if dates become available.",
            "What the pattern CANNOT establish": "Current data cannot support timing claims.",
            "Possible relevance to the CURRENT theoretical model": "Potential output margin later.",
            "Feasibility rating": "LOW",
            "Priority recommendation": "Mark infeasible for now.",
        },
        {
            "Candidate fact / research question": "How should major institutional dates be marked?",
            "Outcome": "Plot annotations and robustness windows",
            "Unit of observation": "Institutional date",
            "Frequency": "Event markers",
            "Sample": "Official UKB public sources",
            "Data source(s)": "UKB transition page, past data releases, RAP access articles",
            "Available time coverage": "2023-2026 markers",
            "Missingness / measurement issues": "Dates are institutional markers, not project-level treatment dates.",
            "Group/exposure proxy if applicable": "Not applicable.",
            "Key transition dates": "Late 2023 WGS; 2024-07-05; 2026-04-01",
            "Important concurrent shocks/confounds": "Data releases and RAP governance changes.",
            "Proposed raw figure": "Vertical markers on raw series",
            "Proposed descriptive regression, if any": "Robustness windows excluding 2026Q2.",
            "What empirical pattern would be informative": "Whether patterns align with one transition or multiple institutional shocks.",
            "What the pattern CANNOT establish": "Cannot prove which institutional event caused a movement.",
            "Possible relevance to the CURRENT theoretical model": "Avoids treating the entire post period as homogeneous.",
            "Feasibility rating": "HIGH",
            "Priority recommendation": "Use on all main plots.",
        },
    ]
    fields = list(rows[0].keys())
    return "# Stylized Facts Inventory\n\n" + markdown_table(rows, fields)


def build_design_proposal(summary: dict[str, object]) -> str:
    return f"""# Interrupted Time-Series Design Proposal

## Objective

The empirical objective is descriptive: document temporal and cross-project patterns around the 5 July 2024 UKB access transition. The transition date is an institutional/policy marker, not an observed treatment date for every incumbent project.

## ITS-1: Aggregate Project Starts

Unit: calendar month. Primary outcome: number of new project starts.

Baseline segmented specification:

```text
Y_t = alpha + beta1 time_t + beta2 PostTransition_t
    + beta3 TimeAfterTransition_t + month-of-year FE + error_t
```

The raw data strongly suggest testing a transition-window parameterization before a one-month break:

```text
Y_t = alpha + beta1 time_t + beta2 JulSep2024_t
    + beta3 Oct2024Restart_t + beta4 PostOct2024_t
    + month-of-year FE + error_t
```

Linear models should report HAC/Newey-West uncertainty. Count-model robustness can use Poisson or negative-binomial models, but coefficients remain descriptive.

## ITS-2: Aggregate Incumbent Publication Trajectory

Unit: project-month or project-quarter. Sample: projects started before 2024-07-05. Outcomes:

- publication app-links per at-risk project-period;
- any-publication rate;
- raw publication count.

Suggested descriptive windows:

- immediate transition: 2024Q3-Q4;
- early lag: 2025Q1-Q2;
- mid lag: 2025Q3-Q4;
- platform-governance/shutdown robustness period: 2026Q2 separately.

Publication lag is central. Do not redefine 2025 as the policy date; use delayed windows to describe timing.

## ITS-3: Comparative Descriptive ITS

Primary comparison: C05 legacy-exposure proxy versus RAP-intensive comparison group. Use C03 and C06 as measurement-sensitivity diagnostics.

Descriptive structure:

```text
Y_gt = alpha_g + gamma_t + beta1 LegacyProxy_g * PostTransition_t
    + beta2 LegacyProxy_g * TimeAfterTransition_t
    + beta3 LegacyProxy_g * JulSep2024_t
    + beta4 LegacyProxy_g * PostOct2024_t
    + error_gt
```

The interaction is a post-transition differential change, not a treatment effect. Report raw group trajectories and baseline composition before any adjusted model.

## ITS-4: Descriptive Event-Time Presentation

Retain event-time plots only as descriptive dynamic trajectories around 2024Q3. Do not label pretrend p-values as PASS/FAIL for identification. Report coefficients, confidence intervals, raw trajectories, and economic magnitudes.

## Transition And Shock Coding

- `PostTransition_t`: periods beginning 2024Q3 or later for quarterly models, July 2024 or later for monthly models.
- `JulSep2024_t`: July, August, and September 2024 administrative pause window.
- `Oct2024Restart_t`: October 2024 batch restart.
- `April2026Shock_t`: 2026Q2 or April 2026 onward, reported separately or excluded from the main post-transition window.

## Robustness Strategy

1. Plot raw series first.
2. Report aggregate starts before comparative publication designs.
3. Use C03/C05/C06 as prespecified exposure-proxy sensitivity, not as a p-value search.
4. Separate extensive and intensive publication margins.
5. Add project-age and broad-modality diagnostics before interpreting group differences.
6. End the main window before April 2026 where appropriate and report 2026Q2 separately.

## Current Feasibility Ratings

{markdown_table([{"Design": key, "Feasibility": value} for key, value in summary["feasibility_ratings"].items()], ["Design", "Feasibility"])}
"""


def build_feasibility_report(summary: dict[str, object], paths: BuildOutputs) -> str:
    starts = summary["known_2024_start_pattern"]
    quarters = summary["project_start_quarter_pattern"]
    c05 = summary["c05_group_projects"]
    publication_quarters = summary["incumbent_publication_quarters"]
    master = [
        {
            "Priority": "1",
            "Stylized fact": "Administrative-looking project-entry pause and restart",
            "Data": "Matched starts",
            "Figure": str(paths.starts_figure.relative_to(PACKAGE)),
            "Descriptive model": "Monthly segmented count ITS",
            "Main limitation": "Cannot attribute to RAP rather than administrative timing",
            "Recommendation": "Show first",
        },
        {
            "Priority": "2",
            "Stylized fact": "Aggregate incumbent publication trajectory",
            "Data": "Schema 19/24 + starts",
            "Figure": str(paths.incumbent_figure.relative_to(PACKAGE)),
            "Descriptive model": "Quarterly ITS with delayed windows",
            "Main limitation": "Publication lag and no active status",
            "Recommendation": "Show second",
        },
        {
            "Priority": "3",
            "Stylized fact": "C05 legacy-proxy vs RAP-intensive differential trajectory",
            "Data": "Archived panel + Stage 3 proxies",
            "Figure": str(paths.comparative_figure.relative_to(PACKAGE)),
            "Descriptive model": "Comparative ITS",
            "Main limitation": "Proxy groups are compositionally different",
            "Recommendation": "Use after composition table",
        },
        {
            "Priority": "4",
            "Stylized fact": "Recent vs mature project trajectories",
            "Data": "Starts + archived panel",
            "Figure": "To add after review",
            "Descriptive model": "Age-band comparative ITS",
            "Main limitation": "Age is not activity status",
            "Recommendation": "Medium priority diagnostic",
        },
        {
            "Priority": "5",
            "Stylized fact": "Returned data timing",
            "Data": "Schema 4",
            "Figure": "None",
            "Descriptive model": "None",
            "Main limitation": "No timing field in local extract",
            "Recommendation": "Mark infeasible",
        },
    ]
    sources = [
        {"Source": row["label"], "URL": row["source_url"], "Accessed": ACCESS_DATE}
        for row in INSTITUTIONAL_DATES
    ]
    files = [
        str(path.relative_to(ROOT))
        for path in [
            paths.project_starts_monthly,
            paths.project_starts_quarterly,
            paths.incumbent_publications_monthly,
            paths.incumbent_publications_quarterly,
            paths.comparative_quarterly,
            paths.group_composition,
            paths.modality_counts,
            paths.age_band_quarterly,
            paths.publication_lag,
            paths.returned_data_feasibility,
            paths.institution_counts,
            paths.institutional_dates,
            paths.starts_figure,
            paths.incumbent_figure,
            paths.comparative_figure,
        ]
    ]
    return f"""# Preliminary ITS Feasibility Report

## 1. New Empirical Objective

The new objective is descriptive. We document temporal and cross-project patterns surrounding the July 2024 UK Biobank data-access transition and use robust stylized facts to motivate and discipline the existing theoretical model.

## 2. Why The Previous Causal DID Interpretation Was Set Aside

The public data do not observe actual project-level RAP migration dates, refresh requests, active/expired project status, or actual RAP use. Existing C0-C6 classifications are useful legacy-exposure proxies, but they do not create a clean untreated counterfactual. Publication is also a lagged downstream outcome, and April 2026 is a distinct platform-governance shock.

## 3. Repository/Data Inventory

The reorganized package uses shared source data in `data/raw` and `data/intermediate`, plus archived DID panel outputs under `analyses/did_archive/data/analysis`.

## 4. Candidate Stylized Facts Discovered

- Project starts show a very sharp 2024 transition-window pattern: April {starts['2024-04']}, May {starts['2024-05']}, June {starts['2024-06']}, July {starts['2024-07']}, August {starts['2024-08']}, September {starts['2024-09']}, October {starts['2024-10']}.
- Quarterly starts move from 2024Q2={quarters['2024Q2']} to 2024Q3={quarters['2024Q3']} to 2024Q4={quarters['2024Q4']}.
- Aggregate incumbent publications are feasible with exact Schema 19 dates; key quarters currently include {json.dumps(publication_quarters, sort_keys=True)}.
- C05 has {c05.get('legacy_exposure_proxy', {}).get('projects', '')} legacy-exposure proxy projects and {c05.get('rap_intensive_comparison', {}).get('projects', '')} RAP-intensive comparison projects in the incumbent sample.
- Returned-dataset timing is not feasible from the local Schema 4 extract.

## 5. Strongest Patterns Currently Visible

The strongest fact is project entry: the July-September 2024 trough and October 2024 restart are visually and economically large relative to ordinary monthly variation. This should be described as an unusual administrative timing pattern around the institutional transition, not as proof of a RAP treatment effect.

## 6. Weak/Infeasible Candidate Facts

Returned datasets are low feasibility because the local public metadata lack usable timing. Institution/country patterns are only low-medium feasibility because institution names are not standardized into countries. C06 should remain a measurement diagnostic rather than a preferred comparison group.

## 7. Proposed ITS Designs

1. ITS-1: aggregate project starts, monthly.
2. ITS-2: aggregate incumbent publication trajectory, monthly or quarterly.
3. ITS-3: comparative ITS for prespecified exposure-proxy groups.
4. ITS-4: descriptive event-time dynamics around 2024Q3.

## 8. Exact Regression Specifications Under Consideration

For monthly starts:

```text
Y_t = alpha + beta1 time_t + beta2 JulSep2024_t
    + beta3 Oct2024Restart_t + beta4 PostOct2024_t
    + month-of-year FE + error_t
```

For comparative publication trajectories:

```text
Y_gt = group FE + calendar FE + group-specific pre-trend
    + legacy_proxy_g x post-window terms + error_gt
```

Coefficients are descriptive level/slope changes or differential trajectories.

## 9. Exact Data/Sample For Each Specification

- ITS-1: matched project starts from `data/intermediate/timing_feasibility/timing_working_research_project_universe.csv`.
- ITS-2: incumbent projects started before 2024-07-05 with exact-date Schema 19/24 publication links.
- ITS-3: archived quarterly panel rows for C03/C05/C06 eligible groups, relabelled as descriptive proxies.
- ITS-4: same quarterly panel, shown as event-time dynamics around 2024Q3.

## 10. Descriptive Hypotheses/Questions

- Was there an unusually sharp project-entry change around the transition?
- Was the entry disruption temporary or persistent?
- Did incumbent publication output show an immediate break, delayed change, or no visible discontinuity?
- Did legacy-exposure and RAP-intensive proxy groups follow different post-transition trajectories?
- Were trajectories different for recent versus mature projects and for extensive versus intensive margins?

## 11. Time Windows And Transition Coding

The main transition marker is 2024-07-05. Monthly entry models should separately code July-September 2024 and October 2024. Quarterly publication models should mark 2024Q3 and report 2026Q2 separately because April 2026 changes the platform-governance regime.

## 12. Concurrent Institutional Shocks

{markdown_table(sources, ["Source", "URL", "Accessed"])}

## 13. Data Limitations

The public data lack project active/expired status, observed RAP migration, refresh requests, project-level RAP use, and participant-level information. Publication dates are exact only for a subset; year-only dates are excluded from timing series. Multi-application publication links are audited and retained as app-publication links.

## 14. What Can And Cannot Be Interpreted

The package can document temporal patterns, group composition, and descriptive post-transition differential changes. It cannot identify a causal RAP effect or prove that any individual incumbent project was treated on 2024-07-05.

## 15. Recommended Order Of Implementation

Start with raw project-entry plots and a compact segmented count ITS. Then show aggregate incumbent publication trajectories with delayed windows. Only after that show C05 comparative trajectories and composition diagnostics.

## 16. Files/Figures/Tables Created

{chr(10).join(f'- `{path}`' for path in files)}

## 17. Questions That Require Supervisor Approval

- Should the main publication window end before 2026Q2?
- Should July-September 2024 be coded as one transition pause or as separate month indicators?
- Should C05 remain the primary descriptive exposure proxy, with C03/C06 as sensitivity?
- Which modality groups are acceptable for supervisor-facing heterogeneity?

## Master Table

{markdown_table(master, ["Priority", "Stylized fact", "Data", "Figure", "Descriptive model", "Main limitation", "Recommendation"])}
"""


def run() -> dict[str, object]:
    paths = output_paths()
    inputs = load_inputs()
    apps = inputs["apps"]
    monthly_starts, quarterly_starts = build_project_start_series(apps)
    events, publication_audit = build_publication_events(apps, inputs["schema19"], inputs["schema24"])
    incumbent_monthly, incumbent_quarterly = build_incumbent_publication_series(apps, events)
    comparative_quarterly = build_comparative_quarterly(inputs["panel"])
    group_composition = build_group_composition(inputs["app_outcomes"])
    modality_counts = build_modality_counts(apps, inputs["app_outcomes"])
    age_band_quarterly = build_age_band_quarterly(inputs["panel"], apps)
    publication_lag = build_publication_lag(events)
    returned_feasibility = build_returned_data_feasibility(inputs["returned"])
    institution_counts = build_institution_counts(apps)
    data_inventory = build_data_inventory(inputs, publication_audit)
    institutional_dates = [{**row, "accessed": ACCESS_DATE} for row in INSTITUTIONAL_DATES]

    write_table(paths.project_starts_monthly, monthly_starts, list(monthly_starts[0].keys()))
    write_table(paths.project_starts_quarterly, quarterly_starts, list(quarterly_starts[0].keys()))
    write_table(paths.incumbent_publications_monthly, incumbent_monthly, list(incumbent_monthly[0].keys()))
    write_table(paths.incumbent_publications_quarterly, incumbent_quarterly, list(incumbent_quarterly[0].keys()))
    write_table(paths.comparative_quarterly, comparative_quarterly, list(comparative_quarterly[0].keys()))
    write_table(paths.group_composition, group_composition, list(group_composition[0].keys()))
    write_table(paths.modality_counts, modality_counts, list(modality_counts[0].keys()))
    write_table(paths.age_band_quarterly, age_band_quarterly, list(age_band_quarterly[0].keys()))
    write_table(paths.publication_lag, publication_lag, list(publication_lag[0].keys()))
    write_table(paths.returned_data_feasibility, returned_feasibility, list(returned_feasibility[0].keys()))
    write_table(paths.institution_counts, institution_counts, list(institution_counts[0].keys()))
    write_table(paths.institutional_dates, institutional_dates, list(institutional_dates[0].keys()))
    write_table(paths.data_inventory, data_inventory, list(data_inventory[0].keys()))
    build_figures(paths, monthly_starts, incumbent_quarterly, comparative_quarterly)

    summary = summarize(
        monthly_starts=monthly_starts,
        quarterly_starts=quarterly_starts,
        incumbent_quarterly=incumbent_quarterly,
        comparative=comparative_quarterly,
        group_composition=group_composition,
        modality_counts=modality_counts,
        publication_audit=publication_audit,
        returned_feasibility=returned_feasibility,
    )
    write_text(paths.summary_json, json.dumps(summary, indent=2, sort_keys=True))
    write_text(paths.readme, build_readme(paths))
    write_text(paths.stylized_inventory, build_stylized_inventory(summary))
    write_text(paths.design_proposal, build_design_proposal(summary))
    write_text(paths.feasibility_report, build_feasibility_report(summary, paths))
    return summary


def main() -> None:
    print(json.dumps(run(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
