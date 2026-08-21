#!/usr/bin/env python3
"""Build Stage 6 quarterly publication panel design and exploratory regressions.

Stage 6 preserves the fast Stage 4/5 checkpoint. It moves the publication
analysis to a risk-set application-quarter panel while keeping treatment/control
definitions provisional. Monthly helpers are retained for the next robustness
design, but the default remote scope intentionally runs the quarterly design
only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import struct
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_DATE = date(2024, 7, 5)
QUARTER_START = date(2022, 7, 1)
QUARTER_END = date(2026, 6, 30)
MONTH_START = date(2022, 7, 1)
MONTH_END = date(2026, 6, 30)
POLICY_QUARTER = "2024Q3"
REFERENCE_QUARTER = "2024Q2"
TRANSITION_MONTH = "2024-07"
MONTHLY_STABLE_POST_START = "2024-08"

DEFAULT_APP_OUTCOMES = ROOT / "data" / "processed" / "stage4_fast_application_outcomes.csv"
DEFAULT_SCHEMA19 = ROOT / "data" / "raw" / "ukb_schema19_publications.tsv"
DEFAULT_SCHEMA24 = ROOT / "data" / "raw" / "ukb_schema24_publication_applications.tsv"
DEFAULT_OUTPUT_DIR = ROOT

CONTROL_DEFS = {
    "CONTROL_C0": {"C0"},
    "CONTROL_C01": {"C0", "C1"},
    "CONTROL_C03": {"C0", "C1", "C2", "C3"},
    "CONTROL_C05": {"C0", "C1", "C2", "C3", "C4", "C5"},
}
CONTROL_DEF_ORDER = ["CONTROL_C0", "CONTROL_C01", "CONTROL_C03", "CONTROL_C05"]
OUTCOMES = ["publication_count", "any_publication"]


@dataclass(frozen=True)
class Period:
    label: str
    start: date
    end: date
    index: int


@dataclass(frozen=True)
class Stage6Paths:
    quarter_panel: Path
    month_panel: Path
    risk_diagnostics: Path
    regression_results: Path
    event_study_results: Path
    pretrend_tests: Path
    control_sensitivity: Path
    timing_audit: Path
    summary_json: Path
    panel_report: Path
    review_report: Path
    quarterly_raw_count: Path
    quarterly_raw_any: Path
    quarterly_event_count: Path
    quarterly_event_any: Path
    monthly_timing_count: Path
    monthly_timing_any: Path
    at_risk_sample_size: Path
    project_age_by_group: Path


def output_paths(output_dir: Path) -> Stage6Paths:
    processed = output_dir / "data" / "processed"
    reports = output_dir / "reports"
    figures = output_dir / "figures"
    return Stage6Paths(
        quarter_panel=processed / "stage6_application_quarter_panel.csv",
        month_panel=processed / "stage6_application_month_panel.csv",
        risk_diagnostics=processed / "stage6_panel_risk_set_diagnostics.csv",
        regression_results=processed / "stage6_panel_regression_results.csv",
        event_study_results=processed / "stage6_event_study_results.csv",
        pretrend_tests=processed / "stage6_pretrend_tests.csv",
        control_sensitivity=processed / "stage6_control_sensitivity.csv",
        timing_audit=processed / "stage6_publication_timing_audit.csv",
        summary_json=processed / "stage6_panel_summary.json",
        panel_report=reports / "stage6_panel_results.md",
        review_report=reports / "stage6_empirical_design_review.md",
        quarterly_raw_count=figures / "stage6_quarterly_raw_publication_count.png",
        quarterly_raw_any=figures / "stage6_quarterly_raw_any_publication.png",
        quarterly_event_count=figures / "stage6_quarterly_event_study_count.png",
        quarterly_event_any=figures / "stage6_quarterly_event_study_any.png",
        monthly_timing_count=figures / "stage6_monthly_timing_count.png",
        monthly_timing_any=figures / "stage6_monthly_timing_any.png",
        at_risk_sample_size=figures / "stage6_at_risk_sample_size.png",
        project_age_by_group=figures / "stage6_project_age_by_group.png",
    )


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_exact_date(value: str) -> date | None:
    value = (value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_start_date(value: str) -> date | None:
    return parse_exact_date(value)


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    month_days = [
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ][month - 1]
    return date(year, month, min(value.day, month_days))


def quarter_label(value: date) -> str:
    return f"{value.year}Q{((value.month - 1) // 3) + 1}"


def quarter_start(value: date) -> date:
    month = ((value.month - 1) // 3) * 3 + 1
    return date(value.year, month, 1)


def quarter_end(value: date) -> date:
    start = quarter_start(value)
    return add_months(start, 3) - timedelta(days=1)


def quarter_index(label: str) -> int:
    year = int(label[:4])
    quarter = int(label[-1])
    return year * 4 + quarter - 1


def month_label(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def month_end(value: date) -> date:
    return add_months(month_start(value), 1) - timedelta(days=1)


def month_index(label: str) -> int:
    year, month = label.split("-")
    return int(year) * 12 + int(month) - 1


def build_quarters() -> list[Period]:
    periods: list[Period] = []
    cursor = quarter_start(QUARTER_START)
    while cursor <= QUARTER_END:
        label = quarter_label(cursor)
        periods.append(Period(label=label, start=cursor, end=quarter_end(cursor), index=len(periods)))
        cursor = add_months(cursor, 3)
    return periods


def build_months() -> list[Period]:
    periods: list[Period] = []
    cursor = month_start(MONTH_START)
    while cursor <= MONTH_END:
        label = month_label(cursor)
        periods.append(Period(label=label, start=cursor, end=month_end(cursor), index=len(periods)))
        cursor = add_months(cursor, 1)
    return periods


def safe_int(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f"{value:.{digits}f}"
    return str(value)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def regression_group(row: dict[str, str], definition: str) -> str:
    return row.get(f"regression_group_{definition}", "")


def is_control_group(value: str) -> bool:
    return value == "control" or value.startswith("control_overlap_original_")


def is_treated_group(value: str) -> bool:
    return value == "treated"


def age_bin(quarters_since_start: int) -> str:
    if quarters_since_start <= 0:
        return "q0"
    if quarters_since_start <= 3:
        return f"q{quarters_since_start}"
    if quarters_since_start <= 7:
        return "q4_7"
    if quarters_since_start <= 11:
        return "q8_11"
    if quarters_since_start <= 15:
        return "q12_15"
    if quarters_since_start <= 23:
        return "q16_23"
    if quarters_since_start <= 35:
        return "q24_35"
    if quarters_since_start <= 47:
        return "q36_47"
    return "q48_plus"


def month_age_bin(months_since_start: int) -> str:
    if months_since_start <= 0:
        return "m0"
    if months_since_start <= 5:
        return "m1_5"
    if months_since_start <= 11:
        return "m6_11"
    if months_since_start <= 23:
        return "m12_23"
    if months_since_start <= 35:
        return "m24_35"
    if months_since_start <= 47:
        return "m36_47"
    return "m48_plus"


def load_applications(app_outcomes_path: Path, expected_universe: int | None) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    rows = read_csv(app_outcomes_path)
    if expected_universe is not None and len(rows) != expected_universe:
        raise ValueError(f"Expected {expected_universe} applications, found {len(rows)}")
    missing_start = [row["app_id"] for row in rows if not parse_start_date(row.get("project_start_date", ""))]
    if missing_start:
        raise ValueError(f"Applications missing exact project_start_date: {missing_start[:5]}")
    return rows, {row["app_id"]: row for row in rows}


def build_publication_events(
    apps_by_id: dict[str, dict[str, str]],
    schema19_path: Path,
    schema24_path: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    publications = read_csv(schema19_path, delimiter="\t")
    links = read_csv(schema24_path, delimiter="\t")
    pub_by_id = {row.get("pub_id", ""): row for row in publications}
    date_status = Counter()
    for pub in publications:
        raw = (pub.get("date_pub") or "").strip()
        if parse_exact_date(raw):
            date_status["exact_date_pub"] += 1
        elif re.fullmatch(r"\d{4}", raw):
            date_status["year_only_date_pub"] += 1
        elif raw:
            date_status["non_exact_date_pub"] += 1
        else:
            date_status["missing_date_pub"] += 1

    pair_counts = Counter((row.get("app_id", ""), row.get("pub_id", "")) for row in links)
    duplicate_pairs = {pair: count for pair, count in pair_counts.items() if count > 1}
    audit_rows: list[dict[str, object]] = []
    for (app_id, pub_id), count in sorted(duplicate_pairs.items()):
        audit_rows.append(
            {
                "issue_type": "duplicate_app_pub_pair",
                "app_id": app_id,
                "pub_id": pub_id,
                "publication_date": "",
                "project_start_date": apps_by_id.get(app_id, {}).get("project_start_date", ""),
                "date_pub_raw": pub_by_id.get(pub_id, {}).get("date_pub", ""),
                "year_pub": pub_by_id.get(pub_id, {}).get("year_pub", ""),
                "details": f"schema24_pair_count={count}",
            }
        )

    events: list[dict[str, object]] = []
    seen_pairs: set[tuple[str, str]] = set()
    max_publication_date: date | None = None
    for link in links:
        app_id = link.get("app_id", "")
        pub_id = link.get("pub_id", "")
        if app_id not in apps_by_id or pub_id not in pub_by_id:
            continue
        pair = (app_id, pub_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        app = apps_by_id[app_id]
        pub = pub_by_id[pub_id]
        pub_date = parse_exact_date(pub.get("date_pub", ""))
        start = parse_start_date(app.get("project_start_date", ""))
        if pub_date is None:
            audit_rows.append(
                {
                    "issue_type": "non_exact_or_missing_publication_date",
                    "app_id": app_id,
                    "pub_id": pub_id,
                    "publication_date": "",
                    "project_start_date": app.get("project_start_date", ""),
                    "date_pub_raw": pub.get("date_pub", ""),
                    "year_pub": pub.get("year_pub", ""),
                    "details": "not used in monthly_or_quarterly_panel",
                }
            )
            continue
        max_publication_date = max(max_publication_date or pub_date, pub_date)
        if start and pub_date < start:
            audit_rows.append(
                {
                    "issue_type": "publication_before_project_start",
                    "app_id": app_id,
                    "pub_id": pub_id,
                    "publication_date": pub_date.isoformat(),
                    "project_start_date": start.isoformat(),
                    "date_pub_raw": pub.get("date_pub", ""),
                    "year_pub": pub.get("year_pub", ""),
                    "details": "excluded_from_panel_event_counts",
                }
            )
            continue
        if pub_date > QUARTER_END:
            audit_rows.append(
                {
                    "issue_type": "after_main_complete_panel_window",
                    "app_id": app_id,
                    "pub_id": pub_id,
                    "publication_date": pub_date.isoformat(),
                    "project_start_date": app.get("project_start_date", ""),
                    "date_pub_raw": pub.get("date_pub", ""),
                    "year_pub": pub.get("year_pub", ""),
                    "details": "excluded_from_main_quarterly_monthly_window",
                }
            )
        events.append(
            {
                "app_id": app_id,
                "pub_id": pub_id,
                "publication_date": pub_date,
                "publication_year": pub_date.year,
                "project_start_date": start,
                "title": pub.get("title", ""),
                "doi": pub.get("doi", ""),
                "pubmed_id": pub.get("pubmed_id", ""),
                "journal": pub.get("journal", ""),
            }
        )

    summary = {
        "schema19_publications": len(publications),
        **dict(date_status),
        "schema24_links": len(links),
        "unique_application_publication_pairs": len(pair_counts),
        "duplicate_application_publication_pairs": len(duplicate_pairs),
        "clean_events_in_working_universe": len(events),
        "publication_observation_end_date": max_publication_date.isoformat() if max_publication_date else "",
        "publication_before_project_start_events": sum(1 for row in audit_rows if row["issue_type"] == "publication_before_project_start"),
        "events_after_main_complete_panel_window": sum(1 for row in audit_rows if row["issue_type"] == "after_main_complete_panel_window"),
    }
    return events, audit_rows, summary


def index_events(events: list[dict[str, object]]) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], int]]:
    quarter_counts: dict[tuple[str, str], int] = defaultdict(int)
    month_counts: dict[tuple[str, str], int] = defaultdict(int)
    for event in events:
        pub_date = event["publication_date"]
        if not isinstance(pub_date, date) or pub_date > QUARTER_END:
            continue
        quarter_counts[(str(event["app_id"]), quarter_label(pub_date))] += 1
        month_counts[(str(event["app_id"]), month_label(pub_date))] += 1
    return quarter_counts, month_counts


def build_quarter_panel(
    apps: list[dict[str, str]],
    quarter_counts: dict[tuple[str, str], int],
) -> list[dict[str, object]]:
    periods = build_quarters()
    policy_idx = quarter_index(POLICY_QUARTER)
    rows: list[dict[str, object]] = []
    for app in apps:
        start = parse_start_date(app["project_start_date"])
        assert start is not None
        start_quarter = quarter_label(start)
        start_quarter_idx = quarter_index(start_quarter)
        for period in periods:
            if period.end < start:
                continue
            label_idx = quarter_index(period.label)
            at_risk_start = max(period.start, start)
            count = quarter_counts.get((app["app_id"], period.label), 0)
            row = {
                "app_id": app["app_id"],
                "quarter": period.label,
                "quarter_index": period.index,
                "project_start_date": app["project_start_date"],
                "project_start_quarter": start_quarter,
                "quarters_since_project_start": label_idx - start_quarter_idx,
                "project_age_bin": age_bin(label_idx - start_quarter_idx),
                "at_risk": 1,
                "at_risk_days": (period.end - at_risk_start).days + 1,
                "partial_first_quarter": int(start > period.start and start <= period.end),
                "publication_count": count,
                "any_publication": int(count > 0),
                "post_policy": int(label_idx >= policy_idx),
                "stable_post_q4": int(label_idx >= quarter_index("2024Q4")),
                "transition_quarter": int(period.label == POLICY_QUARTER),
                "event_time_quarter": label_idx - policy_idx,
                "original_stage3_classification": app.get("original_stage3_classification", ""),
                "control_layer": app.get("control_layer", ""),
                "institution": app.get("schema27_institution", ""),
                "pi": app.get("schema27_pi", ""),
                "schema27_title": app.get("schema27_title", ""),
            }
            for definition in CONTROL_DEF_ORDER:
                row[f"regression_group_{definition}"] = regression_group(app, definition)
                row[f"treated_{definition}"] = int(is_treated_group(row[f"regression_group_{definition}"]))
                row[f"control_{definition}"] = int(is_control_group(row[f"regression_group_{definition}"]))
            rows.append(row)
    return rows


def build_month_panel(apps: list[dict[str, str]], month_counts: dict[tuple[str, str], int]) -> list[dict[str, object]]:
    periods = build_months()
    stable_post_idx = month_index(MONTHLY_STABLE_POST_START)
    july_idx = month_index(TRANSITION_MONTH)
    rows: list[dict[str, object]] = []
    for app in apps:
        start = parse_start_date(app["project_start_date"])
        assert start is not None
        start_month = month_label(start)
        start_idx = month_index(start_month)
        for period in periods:
            if period.end < start:
                continue
            idx = month_index(period.label)
            at_risk_start = max(period.start, start)
            count = month_counts.get((app["app_id"], period.label), 0)
            row = {
                "app_id": app["app_id"],
                "month": period.label,
                "month_index": period.index,
                "project_start_date": app["project_start_date"],
                "project_start_month": start_month,
                "months_since_project_start": idx - start_idx,
                "project_age_bin": month_age_bin(idx - start_idx),
                "at_risk": 1,
                "at_risk_days": (period.end - at_risk_start).days + 1,
                "partial_first_month": int(start > period.start and start <= period.end),
                "publication_count": count,
                "any_publication": int(count > 0),
                "post_policy_primary": int(idx >= stable_post_idx),
                "post_policy_july_as_post": int(idx >= july_idx),
                "transition_month": int(period.label == TRANSITION_MONTH),
                "event_time_month": idx - stable_post_idx,
                "original_stage3_classification": app.get("original_stage3_classification", ""),
                "control_layer": app.get("control_layer", ""),
                "institution": app.get("schema27_institution", ""),
                "pi": app.get("schema27_pi", ""),
                "schema27_title": app.get("schema27_title", ""),
            }
            for definition in CONTROL_DEF_ORDER:
                row[f"regression_group_{definition}"] = regression_group(app, definition)
                row[f"treated_{definition}"] = int(is_treated_group(row[f"regression_group_{definition}"]))
                row[f"control_{definition}"] = int(is_control_group(row[f"regression_group_{definition}"]))
            rows.append(row)
    return rows


def eligible_apps(panel: list[dict[str, object]], definition: str, post_col: str = "post_policy", drop_transition: bool = False) -> set[str]:
    by_app: dict[str, dict[str, bool]] = defaultdict(lambda: {"pre": False, "post": False, "in_group": False})
    for row in panel:
        if drop_transition and safe_int(row.get("transition_quarter", 0)):
            continue
        group = str(row.get(f"regression_group_{definition}", ""))
        if not (is_treated_group(group) or is_control_group(group)):
            continue
        app_id = str(row["app_id"])
        by_app[app_id]["in_group"] = True
        if safe_int(row.get(post_col, 0)):
            by_app[app_id]["post"] = True
        else:
            by_app[app_id]["pre"] = True
    return {app for app, flags in by_app.items() if flags["in_group"] and flags["pre"] and flags["post"]}


def app_group(app_rows: dict[str, dict[str, str]], app_id: str, definition: str) -> str:
    return regression_group(app_rows[app_id], definition)


def sample_panel(
    panel: list[dict[str, object]],
    definition: str,
    eligible: set[str],
    drop_first_partial: bool = False,
    drop_transition_quarter: bool = False,
    drop_transition_month: bool = False,
    balanced_started_by: date | None = None,
    recent_start_after: date | None = None,
    exclude_apps: set[str] | None = None,
) -> list[dict[str, object]]:
    exclude_apps = exclude_apps or set()
    rows: list[dict[str, object]] = []
    for row in panel:
        app_id = str(row["app_id"])
        if app_id not in eligible or app_id in exclude_apps:
            continue
        group = str(row.get(f"regression_group_{definition}", ""))
        if not (is_treated_group(group) or is_control_group(group)):
            continue
        start = parse_start_date(str(row.get("project_start_date", "")))
        if balanced_started_by and start and start > balanced_started_by:
            continue
        if recent_start_after and start and start < recent_start_after:
            continue
        if drop_first_partial and (safe_int(row.get("partial_first_quarter", 0)) or safe_int(row.get("partial_first_month", 0))):
            continue
        if drop_transition_quarter and safe_int(row.get("transition_quarter", 0)):
            continue
        if drop_transition_month and safe_int(row.get("transition_month", 0)):
            continue
        out = dict(row)
        out["treated"] = int(is_treated_group(group))
        rows.append(out)
    return rows


def group_indices(rows: list[dict[str, object]], keys: list[str]) -> dict[str, list[list[int]]]:
    cache: dict[str, list[list[int]]] = {}
    for key in keys:
        groups: dict[str, list[int]] = defaultdict(list)
        for i, row in enumerate(rows):
            groups[str(row.get(key, ""))].append(i)
        cache[key] = list(groups.values())
    return cache


def residualize_matrix(
    rows: list[dict[str, object]],
    columns: list[str],
    fe_vars: list[str],
    max_iter: int = 12,
    tol: float = 1e-8,
) -> list[list[float]]:
    matrix = [[float(row.get(col, 0) or 0) for col in columns] for row in rows]
    if not rows or not fe_vars:
        return matrix
    groups_by_fe = group_indices(rows, fe_vars)
    for _ in range(max_iter):
        max_delta = 0.0
        for fe in fe_vars:
            for idxs in groups_by_fe[fe]:
                if not idxs:
                    continue
                sums = [0.0 for _ in columns]
                for i in idxs:
                    row = matrix[i]
                    for j in range(len(columns)):
                        sums[j] += row[j]
                means = [value / len(idxs) for value in sums]
                for i in idxs:
                    row = matrix[i]
                    for j, avg in enumerate(means):
                        old = row[j]
                        row[j] -= avg
                        max_delta = max(max_delta, abs(row[j] - old))
        if max_delta < tol:
            break
    return matrix


def invert_matrix(matrix: list[list[float]]) -> list[list[float]] | None:
    n = len(matrix)
    aug = [[float(matrix[i][j]) for j in range(n)] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-10:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        denom = aug[col][col]
        aug[col] = [v / denom for v in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor:
                aug[row] = [aug[row][i] - factor * aug[col][i] for i in range(2 * n)]
    return [row[n:] for row in aug]


def mat_vec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(row[i] * vector[i] for i in range(len(vector))) for row in matrix]


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[sum(row[k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for row in a]


def normal_p_value(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def gammaincc(a: float, x: float) -> float:
    if x <= 0:
        return 1.0
    if x < a + 1.0:
        ap = a
        summ = 1.0 / a
        delta = summ
        for _ in range(200):
            ap += 1
            delta *= x / ap
            summ += delta
            if abs(delta) < abs(summ) * 1e-14:
                break
        return max(0.0, min(1.0, 1.0 - summ * math.exp(-x + a * math.log(x) - math.lgamma(a))))
    b = x + 1.0 - a
    c = 1.0 / 1e-300
    d = 1.0 / b
    h = d
    for i in range(1, 200):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-300:
            d = 1e-300
        c = b + an / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return max(0.0, min(1.0, math.exp(-x + a * math.log(x) - math.lgamma(a)) * h))


def ols_fixed_effects(
    rows: list[dict[str, object]],
    outcome: str,
    regressors: list[str],
    fe_vars: list[str],
    cluster_var: str,
) -> dict[str, object]:
    if not rows or not regressors:
        return {"n": len(rows), "warning": "no_rows_or_regressors"}
    cols = [outcome, *regressors]
    resid = residualize_matrix(rows, cols, fe_vars)
    y = [row[0] for row in resid]
    x = [row[1:] for row in resid]
    k = len(regressors)
    xtx = [[sum(xi[i] * xi[j] for xi in x) for j in range(k)] for i in range(k)]
    inv = invert_matrix(xtx)
    if inv is None:
        return {"n": len(rows), "warning": "singular_design_after_fixed_effects"}
    xty = [sum(xi[i] * yi for xi, yi in zip(x, y)) for i in range(k)]
    beta = mat_vec(inv, xty)
    residuals = [yi - sum(xi[j] * beta[j] for j in range(k)) for xi, yi in zip(x, y)]
    clusters: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        clusters[str(row.get(cluster_var, "")) or f"missing_{i}"].append(i)
    meat = [[0.0 for _ in range(k)] for _ in range(k)]
    for idxs in clusters.values():
        score = [sum(x[i][j] * residuals[i] for i in idxs) for j in range(k)]
        for r in range(k):
            for c in range(k):
                meat[r][c] += score[r] * score[c]
    cov = mat_mul(mat_mul(inv, meat), inv)
    g = len(clusters)
    n = len(rows)
    if g > 1 and n > k:
        factor = (g / (g - 1)) * ((n - 1) / max(1, n - k))
        cov = [[value * factor for value in row] for row in cov]
    se = [math.sqrt(max(0.0, cov[i][i])) for i in range(k)]
    p_values = [normal_p_value(beta[i] / se[i]) if se[i] > 0 else None for i in range(k)]
    return {
        "n": n,
        "k": k,
        "clusters": g,
        "regressors": regressors,
        "beta": beta,
        "se": se,
        "p_values": p_values,
        "cov": cov,
        "warning": "",
    }


def wald_test(fit: dict[str, object], regressor_names: list[str]) -> tuple[float | None, int, float | None, str]:
    names = list(fit.get("regressors") or [])
    beta = list(fit.get("beta") or [])
    cov = fit.get("cov")
    if not names or not beta or not isinstance(cov, list):
        return None, len(regressor_names), None, "fit_unavailable"
    idxs = [names.index(name) for name in regressor_names if name in names]
    if len(idxs) != len(regressor_names):
        return None, len(regressor_names), None, "missing_regressor"
    b = [beta[i] for i in idxs]
    v = [[cov[i][j] for j in idxs] for i in idxs]
    inv = invert_matrix(v)
    if inv is None:
        return None, len(idxs), None, "singular_pretrend_covariance"
    stat = sum(b[i] * sum(inv[i][j] * b[j] for j in range(len(b))) for i in range(len(b)))
    p = gammaincc(len(b) / 2.0, stat / 2.0)
    return stat, len(b), p, ""


def regression_result_row(
    design: str,
    frequency: str,
    definition: str,
    outcome: str,
    model: str,
    coefficient: str,
    fit: dict[str, object],
    regressor: str,
    n_apps: int,
    n_treated_apps: int,
    n_control_apps: int,
    cluster: str,
    note: str = "",
) -> dict[str, object]:
    names = list(fit.get("regressors") or [])
    idx = names.index(regressor) if regressor in names else -1
    beta = fit.get("beta") or []
    se = fit.get("se") or []
    p_values = fit.get("p_values") or []
    estimate = beta[idx] if idx >= 0 else None
    stderr = se[idx] if idx >= 0 else None
    p_value = p_values[idx] if idx >= 0 else None
    return {
        "design": design,
        "frequency": frequency,
        "control_definition": definition,
        "outcome": outcome,
        "model": model,
        "coefficient": coefficient,
        "cluster": cluster,
        "n_obs": fit.get("n", 0),
        "n_apps": n_apps,
        "n_treated_apps": n_treated_apps,
        "n_control_apps": n_control_apps,
        "estimate": fmt(estimate),
        "clustered_se": fmt(stderr),
        "p_value": fmt(p_value),
        "ci_low": fmt(estimate - 1.96 * stderr if estimate is not None and stderr is not None else None),
        "ci_high": fmt(estimate + 1.96 * stderr if estimate is not None and stderr is not None else None),
        "warning": fit.get("warning", ""),
        "note": note,
    }


def sample_counts(rows: list[dict[str, object]]) -> tuple[int, int, int]:
    apps = {str(row["app_id"]) for row in rows}
    treated = {str(row["app_id"]) for row in rows if safe_int(row.get("treated", 0))}
    control = apps - treated
    return len(apps), len(treated), len(control)


def add_interaction(rows: list[dict[str, object]], name: str, treated_col: str, post_col: str) -> None:
    for row in rows:
        row[name] = safe_int(row.get(treated_col, 0)) * safe_int(row.get(post_col, 0))


def top_one_percent_apps(rows: list[dict[str, object]]) -> set[str]:
    totals: dict[str, int] = defaultdict(int)
    for row in rows:
        totals[str(row["app_id"])] += safe_int(row.get("publication_count", 0))
    if not totals:
        return set()
    threshold = quantile([float(v) for v in totals.values()], 0.99)
    return {app for app, total in totals.items() if total >= threshold and total > 0}


def raw_quarterly_series(panel: list[dict[str, object]], definition: str, eligible: set[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for quarter in [p.label for p in build_quarters()]:
        for group_name, predicate in (
            ("treated", lambda r: is_treated_group(str(r.get(f"regression_group_{definition}", "")))),
            ("control", lambda r: is_control_group(str(r.get(f"regression_group_{definition}", "")))),
        ):
            group_rows = [
                row
                for row in panel
                if row["quarter"] == quarter and str(row["app_id"]) in eligible and predicate(row)
            ]
            rows.append(
                {
                    "record_type": "quarterly_raw_series",
                    "control_definition": definition,
                    "period": quarter,
                    "group": group_name,
                    "treated_n": "",
                    "control_n": "",
                    "metric": "mean_publication_count",
                    "value": fmt(mean([float(row["publication_count"]) for row in group_rows])),
                    "note": "",
                }
            )
            rows.append(
                {
                    "record_type": "quarterly_raw_series",
                    "control_definition": definition,
                    "period": quarter,
                    "group": group_name,
                    "treated_n": "",
                    "control_n": "",
                    "metric": "any_publication_rate",
                    "value": fmt(mean([float(row["any_publication"]) for row in group_rows])),
                    "note": "",
                }
            )
            rows.append(
                {
                    "record_type": "quarterly_raw_series",
                    "control_definition": definition,
                    "period": quarter,
                    "group": group_name,
                    "treated_n": "",
                    "control_n": "",
                    "metric": "n_at_risk",
                    "value": len(group_rows),
                    "note": "",
                }
            )
            rows.append(
                {
                    "record_type": "quarterly_raw_series",
                    "control_definition": definition,
                    "period": quarter,
                    "group": group_name,
                    "treated_n": "",
                    "control_n": "",
                    "metric": "mean_project_age_quarters",
                    "value": fmt(mean([float(row["quarters_since_project_start"]) for row in group_rows])),
                    "note": "",
                }
            )
    return rows


def post_window_summaries(panel: list[dict[str, object]], definition: str, eligible: set[str]) -> list[dict[str, object]]:
    windows = {
        "short_run_2024Q3_Q4": {"2024Q3", "2024Q4"},
        "medium_run_2025Q1_Q4": {"2025Q1", "2025Q2", "2025Q3", "2025Q4"},
        "later_post_2026Q1_Q2": {"2026Q1", "2026Q2"},
    }
    rows: list[dict[str, object]] = []
    for window, quarters in windows.items():
        subset = [row for row in panel if row["quarter"] in quarters and str(row["app_id"]) in eligible]
        for outcome in OUTCOMES:
            treated = [float(row[outcome]) for row in subset if is_treated_group(str(row.get(f"regression_group_{definition}", "")))]
            control = [float(row[outcome]) for row in subset if is_control_group(str(row.get(f"regression_group_{definition}", "")))]
            rows.append(
                {
                    "record_type": "post_window_summary",
                    "control_definition": definition,
                    "period": window,
                    "group": "treated_minus_control",
                    "metric": outcome,
                    "value": fmt(mean(treated) - mean(control)),
                    "treated_n": len({str(row["app_id"]) for row in subset if is_treated_group(str(row.get(f"regression_group_{definition}", "")))}),
                    "control_n": len({str(row["app_id"]) for row in subset if is_control_group(str(row.get(f"regression_group_{definition}", "")))}),
                    "note": "raw_post_window_difference",
                }
            )
    return rows


def start_quarter_distributions(panel: list[dict[str, object]], definition: str, eligible: set[str]) -> list[dict[str, object]]:
    by_app: dict[str, dict[str, object]] = {}
    for row in panel:
        app_id = str(row["app_id"])
        if app_id not in eligible or app_id in by_app:
            continue
        by_app[app_id] = row

    counts: dict[tuple[str, str], int] = Counter()
    for row in by_app.values():
        group = str(row.get(f"regression_group_{definition}", ""))
        if is_treated_group(group):
            group_name = "treated"
        elif is_control_group(group):
            group_name = "control"
        else:
            continue
        counts[(group_name, str(row["project_start_quarter"]))] += 1

    rows: list[dict[str, object]] = []
    for (group_name, start_quarter), count in sorted(counts.items(), key=lambda item: (item[0][0], quarter_index(item[0][1]))):
        rows.append(
            {
                "record_type": "project_start_quarter_distribution",
                "control_definition": definition,
                "period": start_quarter,
                "group": group_name,
                "metric": "n_projects",
                "value": count,
                "treated_n": "",
                "control_n": "",
                "note": "incumbent_did_eligible_apps_only",
            }
        )
    return rows


def build_regressions(
    quarter_panel: list[dict[str, object]],
    month_panel: list[dict[str, object]] | None = None,
    include_monthly: bool = False,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    regression_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    pretrend_rows: list[dict[str, object]] = []
    sensitivity_rows: list[dict[str, object]] = []
    diagnostics_rows: list[dict[str, object]] = []
    main_estimates: dict[tuple[str, str, str], float] = {}
    event_ks = [*range(-8, -1), *range(0, 8)]
    pre_ks = list(range(-8, -1))

    all_top_apps = top_one_percent_apps(quarter_panel)
    diagnostics_rows.append(
        {
            "record_type": "outlier_distribution",
            "control_definition": "",
            "period": "2022Q3_2026Q2",
            "group": "all",
            "metric": "top_1pct_high_output_apps",
            "value": len(all_top_apps),
            "treated_n": "",
            "control_n": "",
            "note": "based_on_total_publication_count_in_main_quarter_panel",
        }
    )

    for definition in CONTROL_DEF_ORDER:
        eligible = eligible_apps(quarter_panel, definition)
        diagnostics_rows.extend(raw_quarterly_series(quarter_panel, definition, eligible))
        diagnostics_rows.extend(start_quarter_distributions(quarter_panel, definition, eligible))
        diagnostics_rows.extend(post_window_summaries(quarter_panel, definition, eligible))
        base_rows = sample_panel(quarter_panel, definition, eligible)
        n_apps, n_treated, n_control = sample_counts(base_rows)
        pre_periods = len({row["quarter"] for row in base_rows if not safe_int(row["post_policy"])})
        post_periods = len({row["quarter"] for row in base_rows if safe_int(row["post_policy"])})
        diagnostics_rows.append(
            {
                "record_type": "incumbent_did_sample",
                "control_definition": definition,
                "period": "2022Q3_2026Q2",
                "group": "treated_control",
                "metric": "eligible_apps_pre_and_post",
                "value": n_apps,
                "treated_n": n_treated,
                "control_n": n_control,
                "note": f"pre_periods={pre_periods}; post_periods={post_periods}",
            }
        )
        add_interaction(base_rows, "treated_post", "treated", "post_policy")

        for outcome in OUTCOMES:
            for cluster_var, cluster_label in (("app_id", "application"), ("institution", "institution")):
                fit = ols_fixed_effects(base_rows, outcome, ["treated_post"], ["app_id", "quarter"], cluster_var)
                row = regression_result_row(
                    "Q0_quarterly_incumbent_did",
                    "quarter",
                    definition,
                    outcome,
                    "application_fe_calendar_quarter_fe",
                    "treated_x_post",
                    fit,
                    "treated_post",
                    n_apps,
                    n_treated,
                    n_control,
                    cluster_label,
                    note=f"pre_periods={pre_periods}; post_periods={post_periods}; 2024Q3_as_post",
                )
                regression_rows.append(row)
                if cluster_label == "application":
                    main_estimates[(definition, outcome, "Q0")] = float(row["estimate"] or 0)

            fit_age = ols_fixed_effects(base_rows, outcome, ["treated_post"], ["app_id", "quarter", "project_age_bin"], "app_id")
            row_age = regression_result_row(
                "Q1_quarterly_incumbent_did_age_adjusted",
                "quarter",
                definition,
                outcome,
                "application_fe_calendar_quarter_fe_project_age_bin_fe",
                "treated_x_post",
                fit_age,
                "treated_post",
                n_apps,
                n_treated,
                n_control,
                "application",
                note="age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus",
            )
            regression_rows.append(row_age)
            main_estimates[(definition, outcome, "Q1")] = float(row_age["estimate"] or 0)

            no_partial = sample_panel(quarter_panel, definition, eligible, drop_first_partial=True)
            add_interaction(no_partial, "treated_post", "treated", "post_policy")
            fit_no_partial = ols_fixed_effects(no_partial, outcome, ["treated_post"], ["app_id", "quarter"], "app_id")
            regression_rows.append(
                regression_result_row(
                    "Q0_quarterly_drop_first_partial_period",
                    "quarter",
                    definition,
                    outcome,
                    "application_fe_calendar_quarter_fe",
                    "treated_x_post",
                    fit_no_partial,
                    "treated_post",
                    *sample_counts(no_partial),
                    "application",
                    note="drops first partial at-risk quarter",
                )
            )

            stable = sample_panel(quarter_panel, definition, eligible, drop_transition_quarter=True)
            add_interaction(stable, "treated_stable_post", "treated", "stable_post_q4")
            fit_stable = ols_fixed_effects(stable, outcome, ["treated_stable_post"], ["app_id", "quarter"], "app_id")
            regression_rows.append(
                regression_result_row(
                    "Q0_quarterly_stable_post_drop_2024Q3",
                    "quarter",
                    definition,
                    outcome,
                    "application_fe_calendar_quarter_fe",
                    "treated_x_stable_post",
                    fit_stable,
                    "treated_stable_post",
                    *sample_counts(stable),
                    "application",
                    note="drops 2024Q3 transition quarter; post starts 2024Q4",
                )
            )

            no_top = sample_panel(quarter_panel, definition, eligible, exclude_apps=all_top_apps)
            add_interaction(no_top, "treated_post", "treated", "post_policy")
            if outcome == "publication_count":
                fit_no_top = ols_fixed_effects(no_top, outcome, ["treated_post"], ["app_id", "quarter"], "app_id")
                regression_rows.append(
                    regression_result_row(
                        "Q0_quarterly_exclude_top1pct_publication_apps",
                        "quarter",
                        definition,
                        outcome,
                        "application_fe_calendar_quarter_fe",
                        "treated_x_post",
                        fit_no_top,
                        "treated_post",
                        *sample_counts(no_top),
                        "application",
                        note=f"excluded_top_1pct_apps={len(all_top_apps)}",
                    )
                )

            balanced = sample_panel(quarter_panel, definition, eligible, balanced_started_by=QUARTER_START)
            add_interaction(balanced, "treated_post", "treated", "post_policy")
            fit_balanced = ols_fixed_effects(balanced, outcome, ["treated_post"], ["app_id", "quarter"], "app_id")
            regression_rows.append(
                regression_result_row(
                    "Q0_balanced_incumbent_started_by_2022Q3",
                    "quarter",
                    definition,
                    outcome,
                    "application_fe_calendar_quarter_fe",
                    "treated_x_post",
                    fit_balanced,
                    "treated_post",
                    *sample_counts(balanced),
                    "application",
                    note="balanced incumbent sample started by 2022-07-01",
                )
            )

            for cutoff in (date(2019, 1, 1), date(2020, 1, 1)):
                recent = sample_panel(quarter_panel, definition, eligible, recent_start_after=cutoff)
                add_interaction(recent, "treated_post", "treated", "post_policy")
                fit_recent = ols_fixed_effects(recent, outcome, ["treated_post"], ["app_id", "quarter"], "app_id")
                regression_rows.append(
                    regression_result_row(
                        f"Q0_recent_projects_started_after_{cutoff.year}",
                        "quarter",
                        definition,
                        outcome,
                        "application_fe_calendar_quarter_fe",
                        "treated_x_post",
                        fit_recent,
                        "treated_post",
                        *sample_counts(recent),
                        "application",
                        note="active-project exposure robustness using pre-treatment start date only",
                    )
                )

        for outcome in OUTCOMES:
            es_rows = [dict(row) for row in base_rows]
            reg_names: list[str] = []
            for k in event_ks:
                name = f"event_k_{k:+d}".replace("+", "p").replace("-", "m")
                reg_names.append(name)
                for row in es_rows:
                    row[name] = safe_int(row.get("treated", 0)) * int(safe_int(row.get("event_time_quarter", 999)) == k)
            fit_es = ols_fixed_effects(es_rows, outcome, reg_names, ["app_id", "quarter", "project_age_bin"], "app_id")
            names = list(fit_es.get("regressors") or [])
            beta = list(fit_es.get("beta") or [])
            se = list(fit_es.get("se") or [])
            pvals = list(fit_es.get("p_values") or [])
            for k, name in zip(event_ks, reg_names):
                idx = names.index(name) if name in names else -1
                estimate = beta[idx] if idx >= 0 else None
                stderr = se[idx] if idx >= 0 else None
                event_rows.append(
                    {
                        "frequency": "quarter",
                        "control_definition": definition,
                        "outcome": outcome,
                        "event_time": k,
                        "estimate": fmt(estimate),
                        "clustered_se": fmt(stderr),
                        "p_value": fmt(pvals[idx] if idx >= 0 else None),
                        "ci_low": fmt(estimate - 1.96 * stderr if estimate is not None and stderr is not None else None),
                        "ci_high": fmt(estimate + 1.96 * stderr if estimate is not None and stderr is not None else None),
                        "reference_period": REFERENCE_QUARTER,
                        "model": "app_fe_quarter_fe_project_age_bin_fe",
                    }
                )
            pre_names = [f"event_k_{k:+d}".replace("+", "p").replace("-", "m") for k in pre_ks]
            stat, df, p_value, warning = wald_test(fit_es, pre_names)
            pretrend_rows.append(
                {
                    "frequency": "quarter",
                    "control_definition": definition,
                    "outcome": outcome,
                    "model": "event_study_app_fe_quarter_fe_age_bin_fe",
                    "tested_coefficients": "event_time_-8_to_-2",
                    "reference_period": REFERENCE_QUARTER,
                    "statistic_chi2": fmt(stat),
                    "df": df,
                    "p_value": fmt(p_value),
                    "verdict": "WARNING" if p_value is not None and p_value < 0.05 else "PASS" if not warning else "WARNING",
                    "warning": warning,
                }
            )

        if include_monthly and month_panel is not None:
            month_eligible = eligible_apps(month_panel, definition, post_col="post_policy_primary")
            primary_month = sample_panel(month_panel, definition, month_eligible, drop_transition_month=True)
            add_interaction(primary_month, "treated_post_month_primary", "treated", "post_policy_primary")
            secondary_month = sample_panel(month_panel, definition, month_eligible)
            add_interaction(secondary_month, "treated_post_month_july", "treated", "post_policy_july_as_post")
            for outcome in OUTCOMES:
                fit_month = ols_fixed_effects(primary_month, outcome, ["treated_post_month_primary"], ["app_id", "month"], "app_id")
                regression_rows.append(
                    regression_result_row(
                        "M0_monthly_timing_drop_july2024",
                        "month",
                        definition,
                        outcome,
                        "application_fe_calendar_month_fe",
                        "treated_x_post_aug2024",
                        fit_month,
                        "treated_post_month_primary",
                        *sample_counts(primary_month),
                        "application",
                        note="drops July 2024 transition month; post starts August 2024",
                    )
                )
                fit_month_july = ols_fixed_effects(secondary_month, outcome, ["treated_post_month_july"], ["app_id", "month"], "app_id")
                regression_rows.append(
                    regression_result_row(
                        "M0_monthly_timing_july2024_as_post",
                        "month",
                        definition,
                        outcome,
                        "application_fe_calendar_month_fe",
                        "treated_x_post_july2024",
                        fit_month_july,
                        "treated_post_month_july",
                        *sample_counts(secondary_month),
                        "application",
                        note="secondary sensitivity treats July 2024 as post",
                    )
                )

    if include_monthly and month_panel is not None:
        monthly_ks = [*range(-24, -1), *range(0, 24)]
        definition = "CONTROL_C05"
        month_eligible = eligible_apps(month_panel, definition, post_col="post_policy_primary")
        primary_month = sample_panel(month_panel, definition, month_eligible, drop_transition_month=True)
        for outcome in OUTCOMES:
            for k in monthly_ks:
                rows_k = [row for row in primary_month if safe_int(row.get("event_time_month", 999)) == k]
                treated_values = [float(row[outcome]) for row in rows_k if safe_int(row.get("treated", 0))]
                control_values = [float(row[outcome]) for row in rows_k if not safe_int(row.get("treated", 0))]
                estimate = mean(treated_values) - mean(control_values)
                event_rows.append(
                    {
                        "frequency": "month",
                        "control_definition": definition,
                        "outcome": outcome,
                        "event_time": k,
                        "estimate": fmt(estimate),
                        "clustered_se": "",
                        "p_value": "",
                        "ci_low": "",
                        "ci_high": "",
                        "reference_period": "2024-06",
                        "model": "raw_monthly_treated_minus_control_timing_difference",
                    }
                )

    for definition in CONTROL_DEF_ORDER:
        for outcome in OUTCOMES:
            q0 = next((row for row in regression_rows if row["design"] == "Q0_quarterly_incumbent_did" and row["control_definition"] == definition and row["outcome"] == outcome and row["cluster"] == "application"), None)
            q1 = next((row for row in regression_rows if row["design"] == "Q1_quarterly_incumbent_did_age_adjusted" and row["control_definition"] == definition and row["outcome"] == outcome), None)
            pre = next((row for row in pretrend_rows if row["control_definition"] == definition and row["outcome"] == outcome), None)
            sensitivity_rows.append(
                {
                    "control_definition": definition,
                    "outcome": outcome,
                    "treated_n": q0.get("n_treated_apps", "") if q0 else "",
                    "control_n": q0.get("n_control_apps", "") if q0 else "",
                    "q0_estimate": q0.get("estimate", "") if q0 else "",
                    "q0_se": q0.get("clustered_se", "") if q0 else "",
                    "q0_p_value": q0.get("p_value", "") if q0 else "",
                    "q1_age_adjusted_estimate": q1.get("estimate", "") if q1 else "",
                    "q1_age_adjusted_se": q1.get("clustered_se", "") if q1 else "",
                    "pretrend_p_value": pre.get("p_value", "") if pre else "",
                    "pretrend_verdict": pre.get("verdict", "") if pre else "",
                    "note": "do_not_choose_control_definition_by_significance",
                }
            )

    # Pre-policy productivity heterogeneity for broad C0-C5 if count positive and any non-positive.
    c05_count = main_estimates.get(("CONTROL_C05", "publication_count", "Q0"), 0)
    c05_any = main_estimates.get(("CONTROL_C05", "any_publication", "Q0"), 0)
    heterogeneity_triggered = c05_count > 0 and c05_any <= 0
    if heterogeneity_triggered:
        definition = "CONTROL_C05"
        eligible = eligible_apps(quarter_panel, definition)
        pre_counts: dict[str, int] = defaultdict(int)
        for row in quarter_panel:
            if str(row["app_id"]) in eligible and not safe_int(row["post_policy"]):
                pre_counts[str(row["app_id"])] += safe_int(row["publication_count"])
        for stratum, apps in (
            ("no_pre_policy_publication", {app for app in eligible if pre_counts[app] == 0}),
            ("positive_pre_policy_publication", {app for app in eligible if pre_counts[app] > 0}),
        ):
            rows = sample_panel(quarter_panel, definition, apps)
            add_interaction(rows, "treated_post", "treated", "post_policy")
            for outcome in OUTCOMES:
                fit = ols_fixed_effects(rows, outcome, ["treated_post"], ["app_id", "quarter"], "app_id")
                regression_rows.append(
                    regression_result_row(
                        "Q0_quarterly_pre_policy_productivity_stratum",
                        "quarter",
                        definition,
                        outcome,
                        "application_fe_calendar_quarter_fe",
                        "treated_x_post",
                        fit,
                        "treated_post",
                        *sample_counts(rows),
                        "application",
                        note=f"stratum={stratum}; stratum_defined_with_pre_policy_publications_only",
                    )
                )

    meta = {
        "top_1pct_high_output_apps": len(all_top_apps),
        "heterogeneity_triggered_count_positive_any_nonpositive": heterogeneity_triggered,
    }
    return regression_rows, event_rows, pretrend_rows, sensitivity_rows, diagnostics_rows, meta


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, pixels: list[list[tuple[int, int, int]]]) -> None:
    height = len(pixels)
    width = len(pixels[0]) if pixels else 1
    raw = b"".join(b"\x00" + bytes(c for pixel in row for c in pixel) for row in pixels)
    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(raw, 9))
    data += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def draw_line_chart(path: Path, series: list[tuple[list[float], tuple[int, int, int]]], width: int = 900, height: int = 420) -> None:
    bg = (255, 255, 255)
    pixels = [[bg for _ in range(width)] for _ in range(height)]
    left, right, top, bottom = 60, 30, 30, 50
    plot_w = width - left - right
    plot_h = height - top - bottom
    for x in range(left, width - right):
        pixels[height - bottom][x] = (80, 80, 80)
    for y in range(top, height - bottom + 1):
        pixels[y][left] = (80, 80, 80)
    values = [v for values, _ in series for v in values if not math.isnan(v)]
    ymin, ymax = (min(values), max(values)) if values else (0.0, 1.0)
    if abs(ymax - ymin) < 1e-9:
        ymax = ymin + 1.0

    def point(i: int, n: int, value: float) -> tuple[int, int]:
        x = int(left + (i / max(1, n - 1)) * plot_w)
        y = int(height - bottom - ((value - ymin) / (ymax - ymin)) * plot_h)
        return x, max(top, min(height - bottom, y))

    def draw_segment(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            if 0 <= x < width and 0 <= y < height:
                pixels[y][x] = color
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    for values_i, color in series:
        pts = [point(i, len(values_i), v) for i, v in enumerate(values_i)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            draw_segment(x0, y0, x1, y1, color)
        for x, y in pts:
            for yy in range(max(0, y - 2), min(height, y + 3)):
                for xx in range(max(0, x - 2), min(width, x + 3)):
                    pixels[yy][xx] = color
    write_png(path, pixels)


def values_from_raw_series(diagnostics: list[dict[str, object]], definition: str, metric: str, group: str) -> list[float]:
    rows = [
        row
        for row in diagnostics
        if row.get("record_type") == "quarterly_raw_series"
        and row.get("control_definition") == definition
        and row.get("metric") == metric
        and row.get("group") == group
    ]
    rows.sort(key=lambda r: quarter_index(str(r.get("period", "1900Q1"))))
    return [float(row.get("value") or 0) for row in rows]


def build_figures(
    paths: Stage6Paths,
    diagnostics: list[dict[str, object]],
    event_rows: list[dict[str, object]],
    include_monthly: bool = False,
) -> None:
    definition = "CONTROL_C05"
    draw_line_chart(
        paths.quarterly_raw_count,
        [
            (values_from_raw_series(diagnostics, definition, "mean_publication_count", "treated"), (37, 99, 235)),
            (values_from_raw_series(diagnostics, definition, "mean_publication_count", "control"), (220, 38, 38)),
        ],
    )
    draw_line_chart(
        paths.quarterly_raw_any,
        [
            (values_from_raw_series(diagnostics, definition, "any_publication_rate", "treated"), (37, 99, 235)),
            (values_from_raw_series(diagnostics, definition, "any_publication_rate", "control"), (220, 38, 38)),
        ],
    )
    draw_line_chart(
        paths.at_risk_sample_size,
        [
            (values_from_raw_series(diagnostics, definition, "n_at_risk", "treated"), (37, 99, 235)),
            (values_from_raw_series(diagnostics, definition, "n_at_risk", "control"), (220, 38, 38)),
        ],
    )
    draw_line_chart(
        paths.project_age_by_group,
        [
            (values_from_raw_series(diagnostics, definition, "mean_project_age_quarters", "treated"), (37, 99, 235)),
            (values_from_raw_series(diagnostics, definition, "mean_project_age_quarters", "control"), (220, 38, 38)),
        ],
    )
    for outcome, path in (("publication_count", paths.quarterly_event_count), ("any_publication", paths.quarterly_event_any)):
        rows = [
            row
            for row in event_rows
            if row.get("frequency") == "quarter" and row.get("control_definition") == definition and row.get("outcome") == outcome
        ]
        rows.sort(key=lambda r: safe_int(r.get("event_time", 0)))
        draw_line_chart(path, [([float(row.get("estimate") or 0) for row in rows], (20, 184, 166))])
    if include_monthly:
        for outcome, path in (("publication_count", paths.monthly_timing_count), ("any_publication", paths.monthly_timing_any)):
            rows = [
                row
                for row in event_rows
                if row.get("frequency") == "month" and row.get("control_definition") == definition and row.get("outcome") == outcome
            ]
            rows.sort(key=lambda r: safe_int(r.get("event_time", 0)))
            draw_line_chart(path, [([float(row.get("estimate") or 0) for row in rows], (147, 51, 234))])


def markdown_table(rows: list[dict[str, object]], columns: list[str], limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in selected:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def verdict_from_results(
    summary: dict[str, object],
    pretrends: list[dict[str, object]],
    sensitivity: list[dict[str, object]],
    regression_rows: list[dict[str, object]],
) -> dict[str, str]:
    pretrend_warnings = sum(1 for row in pretrends if row.get("verdict") == "WARNING")
    c05_count = next((row for row in sensitivity if row["control_definition"] == "CONTROL_C05" and row["outcome"] == "publication_count"), {})
    c05_any = next((row for row in sensitivity if row["control_definition"] == "CONTROL_C05" and row["outcome"] == "any_publication"), {})
    lifecycle_warning = "WARNING"
    try:
        q0 = float(c05_count.get("q0_estimate") or 0)
        q1 = float(c05_count.get("q1_age_adjusted_estimate") or 0)
        if abs(q0 - q1) <= max(0.05, abs(q0) * 0.25):
            lifecycle_warning = "PASS"
    except ValueError:
        pass
    sign_values = []
    for definition in ("CONTROL_C01", "CONTROL_C03", "CONTROL_C05"):
        row = next((r for r in sensitivity if r["control_definition"] == definition and r["outcome"] == "publication_count"), {})
        try:
            sign_values.append(math.copysign(1, float(row.get("q0_estimate") or 0)))
        except ValueError:
            pass
    control_verdict = "PASS" if len(set(sign_values)) <= 1 else "WARNING"
    final = "WARNING"
    return {
        "data_sufficiency": "PASS" if safe_int(summary.get("missing_project_start_dates", 0)) == 0 else "FAIL",
        "risk_set": "PASS" if safe_int(summary.get("pre_start_panel_rows", 0)) == 0 else "FAIL",
        "pretrend": "WARNING" if pretrend_warnings else "PASS",
        "lifecycle": lifecycle_warning,
        "control_robustness": control_verdict,
        "final": final,
        "c05_count_estimate": str(c05_count.get("q0_estimate", "")),
        "c05_any_estimate": str(c05_any.get("q0_estimate", "")),
    }


def build_reports(
    paths: Stage6Paths,
    summary: dict[str, object],
    regression_rows: list[dict[str, object]],
    pretrend_rows: list[dict[str, object]],
    sensitivity_rows: list[dict[str, object]],
    diagnostics_rows: list[dict[str, object]],
    source_commit: str,
    include_monthly: bool = False,
) -> None:
    verdicts = verdict_from_results(summary, pretrend_rows, sensitivity_rows, regression_rows)
    q0_rows = [
        row
        for row in regression_rows
        if row["design"] == "Q0_quarterly_incumbent_did" and row["cluster"] == "application"
    ]
    q1_rows = [row for row in regression_rows if row["design"] == "Q1_quarterly_incumbent_did_age_adjusted"]
    transition_rows = [row for row in regression_rows if row["design"] == "Q0_quarterly_stable_post_drop_2024Q3"]
    drop_partial_rows = [row for row in regression_rows if row["design"] == "Q0_quarterly_drop_first_partial_period"]
    outlier_rows = [row for row in regression_rows if row["design"] == "Q0_quarterly_exclude_top1pct_publication_apps"]
    heterogeneity_rows = [row for row in regression_rows if row["design"] == "Q0_quarterly_pre_policy_productivity_stratum"]
    monthly_rows = [row for row in regression_rows if row["design"].startswith("M0_monthly")]
    monthly_section = (
        markdown_table(
            monthly_rows,
            ["design", "control_definition", "outcome", "estimate", "clustered_se", "p_value", "note"],
        )
        if include_monthly
        else "Not run in Design 1. Monthly timing robustness is intentionally held for the next sequential design."
    )
    post_summaries = [row for row in diagnostics_rows if row.get("record_type") == "post_window_summary" and row.get("control_definition") == "CONTROL_C05"]

    report = [
        "# Stage 6 Quarterly Panel Publication Results",
        "",
        f"Source commit: `{source_commit or 'not recorded'}`",
        f"Policy date: `{POLICY_DATE.isoformat()}`",
        "",
        "## Empirical Objective",
        "",
        "The purpose is to test whether the 5 July 2024 UK Biobank RAP transition",
        "changed scientific output for applications whose workflows were newly",
        "subject to the RAP requirement, relative to applications that were already",
        "substantially RAP-bound before the policy.",
        "",
        "The main estimand asks whether publication output changed differentially",
        "after the RAP policy for provisionally NEWLY_RAP_BOUND applications",
        "relative to provisionally ALREADY_RAP_BOUND/control-candidate applications.",
        "This is an incumbent-project policy design, not an application-approval",
        "test and not a project-entry design.",
        "",
        "## Sample Construction",
        "",
        markdown_table(
            [{"metric": key, "value": value} for key, value in summary.items()],
            ["metric", "value"],
        ),
        "",
        "## Main Quarterly DID Q0",
        "",
        markdown_table(
            q0_rows,
            ["control_definition", "outcome", "n_apps", "n_treated_apps", "n_control_apps", "estimate", "clustered_se", "p_value", "ci_low", "ci_high"],
        ),
        "",
        "## Project-Age Adjusted Q1",
        "",
        markdown_table(
            q1_rows,
            ["control_definition", "outcome", "n_apps", "estimate", "clustered_se", "p_value", "note"],
        ),
        "",
        "## Event-Study Joint Pretrend Tests",
        "",
        markdown_table(
            pretrend_rows,
            ["control_definition", "outcome", "statistic_chi2", "df", "p_value", "verdict", "warning"],
        ),
        "",
        "## Transition Quarter Robustness",
        "",
        markdown_table(
            transition_rows,
            ["control_definition", "outcome", "estimate", "clustered_se", "p_value", "note"],
        ),
        "",
        "## Post Window Summaries For CONTROL_C05",
        "",
        markdown_table(post_summaries, ["period", "metric", "value", "treated_n", "control_n", "note"]),
        "",
        "## Drop First Partial Quarter",
        "",
        markdown_table(
            drop_partial_rows,
            ["control_definition", "outcome", "estimate", "clustered_se", "p_value", "note"],
        ),
        "",
        "## Count Outlier Robustness",
        "",
        markdown_table(
            outlier_rows,
            ["control_definition", "outcome", "estimate", "clustered_se", "p_value", "note"],
        ),
        "",
        "## Pre-Policy Productivity Strata",
        "",
        markdown_table(
            heterogeneity_rows,
            ["control_definition", "outcome", "n_apps", "n_treated_apps", "n_control_apps", "estimate", "clustered_se", "p_value", "note"],
        )
        if heterogeneity_rows
        else "Not triggered.",
        "",
        "## Monthly Robustness",
        "",
        monthly_section,
        "",
        "## Control Sensitivity",
        "",
        markdown_table(
            sensitivity_rows,
            ["control_definition", "outcome", "treated_n", "control_n", "q0_estimate", "q0_se", "q1_age_adjusted_estimate", "pretrend_p_value", "pretrend_verdict"],
        ),
        "",
        "## Interpretation Guardrails",
        "",
        "- C0-C5 are provisional controls, not final clean controls.",
        "- Post-policy entrants are not used for incumbent DID identification.",
        "- Pre-project periods are absent from the risk set, not coded as zero.",
        "- Publication is lagged; 2024Q3 effects should be interpreted cautiously.",
        "- Current data do not verify project end dates, active status, access dates, RAP migration dates, or RAP usage logs.",
    ]
    paths.panel_report.parent.mkdir(parents=True, exist_ok=True)
    paths.panel_report.write_text("\n".join(report) + "\n", encoding="utf-8")

    r1 = "PASS" if verdicts["data_sufficiency"] == "PASS" and verdicts["risk_set"] == "PASS" else "FAIL"
    r2 = verdicts["pretrend"]
    r3 = verdicts["final"]
    review = [
        "# Stage 6 Empirical Design Review",
        "",
        "This report records implementation-generated empirical diagnostics in the",
        "same PASS / WARNING / FAIL structure used by the independent review agent.",
        "",
        "## Checkpoint Summary",
        "",
        markdown_table(
            [
                {
                    "checkpoint": "R0 Design Review",
                    "verdict": "WARNING / PROCEED",
                    "basis": "Quarterly incumbent DID is worth running, but controls are provisional and active-project exposure is not directly observed.",
                },
                {
                    "checkpoint": "R1 Panel/Data Construction",
                    "verdict": r1,
                    "basis": "Exact project starts, publication-date audit, no pre-start panel rows, and no incomplete 2026Q3 main-period rows.",
                },
                {
                    "checkpoint": "R2 Identification/Pretrend",
                    "verdict": r2,
                    "basis": "App FE, calendar-quarter FE, age-adjusted Q1, transition robustness, and joint pretrend tests are produced.",
                },
                {
                    "checkpoint": "R3 Result/Robustness",
                    "verdict": r3,
                    "basis": "Control definitions, transition timing, first partial quarter, outlier, and productivity-stratum checks are reported.",
                },
            ],
            ["checkpoint", "verdict", "basis"],
        ),
        "",
        "## 1. Target Estimand",
        "",
        "**PASS.** The target is an incumbent-project ITT-like DID: differential",
        "publication output after the RAP transition for provisional NEWLY_RAP_BOUND",
        "applications relative to provisional already-RAP-bound control candidates.",
        "",
        "## 2. Why Quarterly DID Is Tried First",
        "",
        "**PASS.** The quarterly panel preserves timing, avoids pre-start zeroes,",
        "and permits pretrend and lag diagnostics while keeping the panel less noisy",
        "than monthly data.",
        "",
        "## 3. Unit Of Observation And Risk Set",
        "",
        f"**{verdicts['risk_set']}.** Unit is application-quarter for Design 1.",
        "Rows are generated only for at-risk periods after project start; first",
        "partial quarters are flagged. Monthly robustness is not run in this",
        "sequential checkpoint.",
        "",
        "## 4. Treatment/Control Definitions",
        "",
        "**WARNING.** Treatment/control status remains provisional. C0 is high",
        "precision but very small; C01/C03/C05 improve precision but mix evidence",
        "quality and include overlap labels from original Stage 3 classes.",
        "",
        "## 5. Data Sufficiency",
        "",
        f"**{verdicts['data_sufficiency']}.** Exact date coverage and missing starts",
        "are reported in the risk-set diagnostics. Year-only dates are not converted",
        "to January/Q1 for panel regressions.",
        "",
        "## 6. Missing Data",
        "",
        "**WARNING.** Public data lack project active/closed status, actual access",
        "dates, RAP migration dates, and RAP usage logs. This limits interpretation",
        "to policy-exposure intent, not verified migration/use.",
        "",
        "## 7. Pre-Trend Assessment",
        "",
        f"**{verdicts['pretrend']}.** Joint pretrend tests are reported for",
        "event-time -8 through -2, with 2024Q2 omitted as reference. A WARNING means",
        "at least one outcome/control definition rejects at conventional levels or",
        "the test is otherwise fragile.",
        "",
        "## 8. Project-Age/Lifecycle Assessment",
        "",
        f"**{verdicts['lifecycle']}.** Q1 adds project-age-bin fixed effects. Material",
        "movement from Q0 to Q1 should be treated as lifecycle confounding.",
        "",
        "## 9. Inference Assessment",
        "",
        "**WARNING.** Application-clustered SE are primary and institution-clustered",
        "SE are reported for Q0 robustness. Some control cells remain small, especially",
        "C0.",
        "",
        "## 10. Control-Definition Robustness",
        "",
        f"**{verdicts['control_robustness']}.** C01/C03/C05 are compared without",
        "selecting based on significance. Sign instability implies measurement is",
        "the bottleneck.",
        "",
        "## 11. Publication Lag / Transition Timing",
        "",
        "**WARNING.** 2024Q3 is a transition quarter and publication output is lagged.",
        "The report compares treating 2024Q3 as post with dropping it and starting",
        "stable post in 2024Q4.",
        "",
        "## 12. Alternative Designs",
        "",
        "**WARNING.** If pretrends or lifecycle diagnostics are weak, stronger",
        "alternatives are balanced-incumbent DID, start-cohort matched/weighted DID,",
        "and project-entry cohort designs. Common support is limited because controls",
        "are small.",
        "",
        "## 13. Decision Tree",
        "",
        "- CASE 1: If pretrends are acceptable and coefficients are stable across",
        "  C01/C03/C05, quarterly incumbent DID remains the preferred main design.",
        "- CASE 2: If full risk-set pretrends are poor but balanced incumbents improve",
        "  them, use balanced-incumbent DID as stronger and keep full risk set secondary.",
        "- CASE 3: If pretrends remain poor, do not make causal claims; pursue",
        "  start-cohort matching/weighting.",
        "- CASE 4: If Q0/Q1 differ materially, lifecycle is a major confounder.",
        "- CASE 5: If effects appear only in 2024Q3, treat timing as suspicious.",
        "- CASE 6: If effects emerge later, emphasize lagged publication production.",
        "- CASE 7: If count and any-publication diverge, decompose intensive versus",
        "  extensive margins using pre-policy productivity strata only.",
        "- CASE 8: If top 1% projects drive count effects, weaken average-effect",
        "  interpretation and use outlier/count robustness.",
        "- CASE 9: If signs change across C01/C03/C05, return to Stage 3 measurement.",
        "",
        "## 14. Final Reviewer Verdict",
        "",
        f"**{verdicts['final']}.** The current outputs can be interpreted as",
        "exploratory ITT-like incumbent-project publication designs. They cannot by",
        "themselves establish a causal RAP effect unless pretrend, lifecycle, timing,",
        "and control-definition diagnostics are satisfactory. The next data priorities",
        "are project active/closed status, actual access dates, RAP migration dates,",
        "and RAP usage logs.",
    ]
    paths.review_report.write_text("\n".join(review) + "\n", encoding="utf-8")


def build_stage6_outputs(
    app_outcomes_path: Path = DEFAULT_APP_OUTCOMES,
    schema19_path: Path = DEFAULT_SCHEMA19,
    schema24_path: Path = DEFAULT_SCHEMA24,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_universe: int | None = 6935,
    source_commit: str = "",
    design: str = "quarterly",
) -> dict[str, object]:
    if design not in {"quarterly", "all"}:
        raise ValueError(f"Unsupported design scope: {design}")
    include_monthly = design == "all"
    paths = output_paths(output_dir)
    apps, apps_by_id = load_applications(app_outcomes_path, expected_universe)
    events, audit_rows, publication_summary = build_publication_events(apps_by_id, schema19_path, schema24_path)
    quarter_counts, month_counts = index_events(events)
    quarter_panel = build_quarter_panel(apps, quarter_counts)
    month_panel = build_month_panel(apps, month_counts) if include_monthly else None

    quarter_period_end = {period.label: period.end for period in build_quarters()}
    pre_start_panel_rows = sum(
        1
        for row in quarter_panel
        if quarter_period_end[str(row["quarter"])] < parse_start_date(str(row["project_start_date"]))
    )
    regression_rows, event_rows, pretrend_rows, sensitivity_rows, diagnostics_rows, meta = build_regressions(
        quarter_panel,
        month_panel,
        include_monthly=include_monthly,
    )

    missing_starts = sum(1 for app in apps if not parse_start_date(app.get("project_start_date", "")))
    summary: dict[str, object] = {
        "source_commit": source_commit,
        "design_scope": design,
        "working_universe_projects": len(apps),
        "quarter_panel_rows": len(quarter_panel),
        "month_panel_rows": len(month_panel) if month_panel is not None else "not_run_in_quarterly_design",
        "quarter_window": "2022Q3_2026Q2",
        "month_window": "2022-07_2026-06" if include_monthly else "not_run_in_quarterly_design",
        "policy_date": POLICY_DATE.isoformat(),
        "missing_project_start_dates": missing_starts,
        "pre_start_panel_rows": pre_start_panel_rows,
        "publication_events_in_complete_quarter_panel": sum(quarter_counts.values()),
        **publication_summary,
        **meta,
    }
    for definition in CONTROL_DEF_ORDER:
        eligible = eligible_apps(quarter_panel, definition)
        rows = sample_panel(quarter_panel, definition, eligible)
        n_apps, n_treated, n_control = sample_counts(rows)
        summary[f"{definition}_incumbent_apps"] = n_apps
        summary[f"{definition}_treated_apps"] = n_treated
        summary[f"{definition}_control_apps"] = n_control

    risk_rows = [
        {
            "record_type": "data_integrity",
            "control_definition": "",
            "period": "",
            "group": "",
            "metric": key,
            "value": value,
            "treated_n": "",
            "control_n": "",
            "note": "",
        }
        for key, value in summary.items()
    ]
    risk_rows.extend(diagnostics_rows)

    write_csv(paths.quarter_panel, quarter_panel, [
        "app_id", "quarter", "quarter_index", "project_start_date", "project_start_quarter",
        "quarters_since_project_start", "project_age_bin", "at_risk", "at_risk_days",
        "partial_first_quarter", "publication_count", "any_publication", "post_policy",
        "stable_post_q4", "transition_quarter", "event_time_quarter",
        "original_stage3_classification", "control_layer", "regression_group_CONTROL_C0",
        "regression_group_CONTROL_C01", "regression_group_CONTROL_C03",
        "regression_group_CONTROL_C05", "institution", "pi", "schema27_title",
    ])
    if month_panel is not None:
        write_csv(paths.month_panel, month_panel, [
            "app_id", "month", "month_index", "project_start_date", "project_start_month",
            "months_since_project_start", "project_age_bin", "at_risk", "at_risk_days",
            "partial_first_month", "publication_count", "any_publication",
            "post_policy_primary", "post_policy_july_as_post", "transition_month",
            "event_time_month", "original_stage3_classification", "control_layer",
            "regression_group_CONTROL_C0", "regression_group_CONTROL_C01",
            "regression_group_CONTROL_C03", "regression_group_CONTROL_C05",
            "institution", "pi", "schema27_title",
        ])
    write_csv(paths.risk_diagnostics, risk_rows, [
        "record_type", "control_definition", "period", "group", "metric", "value",
        "treated_n", "control_n", "note",
    ])
    write_csv(paths.timing_audit, audit_rows, [
        "issue_type", "app_id", "pub_id", "publication_date", "project_start_date",
        "date_pub_raw", "year_pub", "details",
    ])
    write_csv(paths.regression_results, regression_rows, [
        "design", "frequency", "control_definition", "outcome", "model", "coefficient",
        "cluster", "n_obs", "n_apps", "n_treated_apps", "n_control_apps", "estimate",
        "clustered_se", "p_value", "ci_low", "ci_high", "warning", "note",
    ])
    write_csv(paths.event_study_results, event_rows, [
        "frequency", "control_definition", "outcome", "event_time", "estimate",
        "clustered_se", "p_value", "ci_low", "ci_high", "reference_period", "model",
    ])
    write_csv(paths.pretrend_tests, pretrend_rows, [
        "frequency", "control_definition", "outcome", "model", "tested_coefficients",
        "reference_period", "statistic_chi2", "df", "p_value", "verdict", "warning",
    ])
    write_csv(paths.control_sensitivity, sensitivity_rows, [
        "control_definition", "outcome", "treated_n", "control_n", "q0_estimate",
        "q0_se", "q0_p_value", "q1_age_adjusted_estimate", "q1_age_adjusted_se",
        "pretrend_p_value", "pretrend_verdict", "note",
    ])
    paths.summary_json.parent.mkdir(parents=True, exist_ok=True)
    paths.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    build_figures(paths, risk_rows, event_rows, include_monthly=include_monthly)
    build_reports(
        paths,
        summary,
        regression_rows,
        pretrend_rows,
        sensitivity_rows,
        risk_rows,
        source_commit,
        include_monthly=include_monthly,
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-outcomes", type=Path, default=DEFAULT_APP_OUTCOMES)
    parser.add_argument("--schema19", type=Path, default=DEFAULT_SCHEMA19)
    parser.add_argument("--schema24", type=Path, default=DEFAULT_SCHEMA24)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-universe", type=int, default=6935)
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--design", choices=["quarterly", "all"], default="quarterly")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_stage6_outputs(
        app_outcomes_path=args.app_outcomes,
        schema19_path=args.schema19,
        schema24_path=args.schema24,
        output_dir=args.output_dir,
        expected_universe=args.expected_universe,
        source_commit=args.source_commit,
        design=args.design,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
