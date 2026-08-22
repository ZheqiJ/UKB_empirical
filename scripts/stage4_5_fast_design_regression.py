#!/usr/bin/env python3
"""Build fast Stage 4/5 exploratory design and regression outputs.

This is intentionally a quick, reproducible empirical pass. It does not refine
Stage 3 measurement. It uses the fixed 6,935 matched application universe,
existing Stage 3 classifications, C0-C5 provisional control candidates, UKB
publication metadata, and a frozen curated DMCA application list.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_DATE = date(2024, 7, 5)
P1_PRE_START = date(2022, 7, 5)
P1_PRE_END = date(2024, 7, 4)
P1_POST_START = date(2024, 7, 5)
P1_POST_END = date(2026, 7, 4)
P2_ENTRY_PRE_START = date(2023, 7, 5)
P2_ENTRY_PRE_END = date(2024, 7, 4)
P2_ENTRY_POST_START = date(2024, 7, 5)
P2_ENTRY_POST_END = date(2025, 7, 4)

DEFAULT_TIMING_METADATA = ROOT / "data" / "processed" / "timing_working_research_project_universe.csv"
DEFAULT_STAGE3 = ROOT / "data" / "processed" / "stage3_project_rap_exposure_classification.csv"
DEFAULT_CONTROL_EXPANSION = ROOT / "data" / "processed" / "stage3_control_expansion_project_review.csv"
DEFAULT_SCHEMA19 = ROOT / "data" / "raw" / "ukb_schema19_publications.tsv"
DEFAULT_SCHEMA24 = ROOT / "data" / "raw" / "ukb_schema24_publication_applications.tsv"
DEFAULT_DMCA_MANUAL_REVIEW = ROOT / "ukb_dmca" / "ukb_dmca_manual_review.csv"
DEFAULT_OUTPUT_DIR = ROOT

STRICT_21 = {
    "103356",
    "47267",
    "66995",
    "87802",
    "48388",
    "45761",
    "177030",
    "88159",
    "822932",
    "19542",
    "84103",
    "28784",
    "19526",
    "61666",
    "55955",
    "51157",
    "69610",
    "61054",
    "52887",
    "33923",
    "52293",
}
MAIN_EXTRA_6 = {"30418", "65805", "57232", "27837", "55288", "92005"}
BROAD_EXTRA_21 = {
    "31063",
    "74395",
    "10279",
    "22224",
    "24247",
    "46122",
    "56757",
    "61785",
    "62254",
    "64823",
    "88878",
    "49777",
    "51064",
    "79957",
    "40161",
    "867484",
    "23668",
    "12184",
    "10035",
    "19136",
    "59070",
}
MAIN_27 = STRICT_21 | MAIN_EXTRA_6
BROAD_48 = MAIN_27 | BROAD_EXTRA_21

CONTROL_ORDER = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5, "C6": 6}
CONTROL_DEFS = {
    "CONTROL_C0": {"C0"},
    "CONTROL_C01": {"C0", "C1"},
    "CONTROL_C03": {"C0", "C1", "C2", "C3"},
    "CONTROL_C05": {"C0", "C1", "C2", "C3", "C4", "C5"},
}


@dataclass(frozen=True)
class FastPaths:
    application_outcomes: Path
    publication_events: Path
    publication_period_panel: Path
    dmca_crosswalk: Path
    dmca_unmatched_apps: Path
    regression_results: Path
    group_means: Path
    dmca_2x2: Path
    summary_json: Path
    report: Path
    publication_did_figure: Path
    publication_cohort_figure: Path
    dmca_rates_figure: Path


def output_paths(output_dir: Path) -> FastPaths:
    processed = output_dir / "data" / "processed"
    reports = output_dir / "reports"
    figures = output_dir / "figures"
    return FastPaths(
        application_outcomes=processed / "stage4_fast_application_outcomes.csv",
        publication_events=processed / "stage4_fast_publication_events.csv",
        publication_period_panel=processed / "stage4_fast_publication_period_panel.csv",
        dmca_crosswalk=processed / "stage4_fast_dmca_crosswalk.csv",
        dmca_unmatched_apps=processed / "stage4_fast_dmca_unmatched_apps.csv",
        regression_results=processed / "stage5_fast_regression_results.csv",
        group_means=processed / "stage5_fast_group_means.csv",
        dmca_2x2=processed / "stage5_fast_dmca_2x2.csv",
        summary_json=processed / "stage5_fast_summary.json",
        report=reports / "stage5_fast_results.md",
        publication_did_figure=figures / "stage5_publication_did.png",
        publication_cohort_figure=figures / "stage5_publication_cohort.png",
        dmca_rates_figure=figures / "stage5_dmca_rates.png",
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


def parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            return parsed if fmt != "%Y" else date(parsed.year, 1, 1)
        except ValueError:
            continue
    return None


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(
        value.day,
        [
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
        ][month - 1],
    )
    return date(year, month, day)


def months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + end.month - start.month
    if end.day < start.day:
        months -= 1
    return months


def safe_int(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def pct(value: float | int, denom: float | int) -> str:
    denom = float(denom)
    if denom == 0:
        return ""
    return f"{100 * float(value) / denom:.3f}"


def fmt(value: object, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f"{value:.{digits}f}"
    return str(value)


def uniq(values: list[str]) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        for part in str(value or "").split(";"):
            item = part.strip()
            if item and item not in seen:
                seen.add(item)
                out.append(item)
    return "; ".join(out)


def control_flags(layer: str) -> dict[str, bool]:
    return {
        "cumulative_control_C0": layer == "C0",
        "cumulative_control_C01": layer in {"C0", "C1"},
        "cumulative_control_C03": layer in {"C0", "C1", "C2", "C3"},
        "cumulative_control_C05": layer in {"C0", "C1", "C2", "C3", "C4", "C5"},
        "cumulative_control_C06": layer in {"C0", "C1", "C2", "C3", "C4", "C5", "C6"},
    }


def regression_group(classification: str, layer: str, definition: str) -> str:
    if layer in CONTROL_DEFS[definition]:
        if classification == "NEWLY_RAP_BOUND":
            return "control_overlap_original_newly_rap_bound"
        if classification == "MIXED":
            return "control_overlap_original_mixed"
        if classification == "UNCLEAR":
            return "control_overlap_original_unclear"
        return "control"
    if classification == "NEWLY_RAP_BOUND":
        return "treated"
    if classification == "MIXED":
        return "excluded_mixed"
    if classification == "UNCLEAR":
        return "excluded_unclear"
    if classification == "ALREADY_RAP_BOUND":
        return "excluded_already_rap_not_in_definition"
    return "excluded_other"


def group_is_control(value: str) -> bool:
    return value == "control" or value.startswith("control_overlap_original_")


def group_is_treated(value: str) -> bool:
    return value == "treated"


def build_project_rows(
    stage3_path: Path,
    control_expansion_path: Path,
    expected_universe: int | None,
    timing_metadata_path: Path | None = DEFAULT_TIMING_METADATA,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    stage3_rows = read_csv(stage3_path)
    if expected_universe is not None and len(stage3_rows) != expected_universe:
        raise ValueError(f"Expected {expected_universe} matched projects; found {len(stage3_rows)}")
    timing_by_app: dict[str, dict[str, str]] = {}
    if timing_metadata_path and timing_metadata_path.exists():
        timing_by_app = {row.get("app_id", ""): row for row in read_csv(timing_metadata_path)}

    layer_by_app: dict[str, str] = {}
    layer_duplicates: Counter[str] = Counter()
    for row in read_csv(control_expansion_path):
        app_id = row.get("app_id", "")
        layer = row.get("expansion_layer", "")
        if layer not in CONTROL_ORDER:
            continue
        if app_id in layer_by_app:
            layer_duplicates[app_id] += 1
            if CONTROL_ORDER[layer] >= CONTROL_ORDER[layer_by_app[app_id]]:
                continue
        layer_by_app[app_id] = layer

    rows: list[dict[str, object]] = []
    missing_start_date = 0
    for st3 in stage3_rows:
        app_id = st3["app_id"]
        timing = timing_by_app.get(app_id, {})
        start = parse_date(st3.get("project_start_date", "")) or parse_date(timing.get("start_date", ""))
        if not start:
            missing_start_date += 1
        classification = st3.get("classification", "")
        layer = layer_by_app.get(app_id, "")
        flags = control_flags(layer)
        out: dict[str, object] = {
            "app_id": app_id,
            "project_start_date": start.isoformat() if start else "",
            "project_start_year": start.year if start else "",
            "post_policy_start": int(bool(start and start >= POLICY_DATE)),
            "original_stage3_classification": classification,
            "stage3_confidence": st3.get("confidence", ""),
            "control_layer": layer,
            **{key: int(value) for key, value in flags.items()},
            "stage3_already_rap_modalities": st3.get("already_rap_modalities", ""),
            "stage3_legacy_route_modalities": st3.get("legacy_route_modalities", ""),
            "schema27_title": st3.get("schema27_title", "") or timing.get("schema27_title", ""),
            "schema27_pi": st3.get("schema27_pi", "") or timing.get("schema27_pi", ""),
            "schema27_institution": st3.get("schema27_institution", "") or timing.get("schema27_institution", ""),
            "website_url": st3.get("website_url", "") or timing.get("website_url", ""),
        }
        for definition in CONTROL_DEFS:
            out[f"regression_group_{definition}"] = regression_group(classification, layer, definition)
        rows.append(out)

    summary = {
        "working_universe_projects": len(rows),
        "fixed_universe_source": str(stage3_path.relative_to(ROOT)) if stage3_path.is_relative_to(ROOT) else str(stage3_path),
        "timing_metadata_source": str(timing_metadata_path.relative_to(ROOT)) if timing_metadata_path and timing_metadata_path.exists() and timing_metadata_path.is_relative_to(ROOT) else str(timing_metadata_path or ""),
        "missing_project_start_date_rows": missing_start_date,
        "control_layer_duplicate_apps": len(layer_duplicates),
        "control_layer_counts": dict(Counter(str(row["control_layer"] or "none") for row in rows)),
    }
    return rows, summary


def build_publication_events(
    project_rows: list[dict[str, object]],
    schema19_path: Path,
    schema24_path: Path,
) -> tuple[list[dict[str, object]], dict[str, list[date]], date]:
    project_by_app = {str(row["app_id"]): row for row in project_rows}
    publications = read_csv(schema19_path, delimiter="\t")
    pub_by_id = {row.get("pub_id", ""): row for row in publications}
    links = read_csv(schema24_path, delimiter="\t")

    dates_by_app: dict[str, list[date]] = defaultdict(list)
    events: list[dict[str, object]] = []
    max_pub_date = date(2026, 7, 4)
    for link in links:
        app_id = link.get("app_id", "")
        pub_id = link.get("pub_id", "")
        project = project_by_app.get(app_id)
        pub = pub_by_id.get(pub_id)
        if project is None or pub is None:
            continue
        pub_date = parse_date(pub.get("date_pub", "")) or parse_date(pub.get("year_pub", ""))
        start = parse_date(str(project.get("project_start_date", "")))
        if pub_date is None or start is None:
            continue
        max_pub_date = max(max_pub_date, pub_date)
        dates_by_app[app_id].append(pub_date)
        events.append(
            {
                "app_id": app_id,
                "pub_id": pub_id,
                "publication_date": pub_date.isoformat(),
                "publication_year": pub_date.year,
                "project_start_date": start.isoformat(),
                "months_since_project_start": months_between(start, pub_date),
                "publication_before_or_after_policy": "after_policy" if pub_date >= POLICY_DATE else "before_policy",
                "title": pub.get("title", ""),
                "doi": pub.get("doi", ""),
                "pubmed_id": pub.get("pubmed_id", ""),
                "journal": pub.get("journal", ""),
            }
        )
    for app_id in dates_by_app:
        dates_by_app[app_id].sort()
    return events, dates_by_app, max_pub_date


def count_in_window(dates: list[date], start: date, end: date) -> int:
    return sum(1 for value in dates if start <= value <= end)


def count_within_months(dates: list[date], start: date, months: int) -> int:
    horizon_end = add_months(start, months)
    return sum(1 for value in dates if start <= value < horizon_end)


def append_publication_outcomes(
    project_rows: list[dict[str, object]],
    dates_by_app: dict[str, list[date]],
    publication_observation_end: date,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in project_rows:
        out = dict(row)
        app_id = str(row["app_id"])
        start = parse_date(str(row.get("project_start_date", "")))
        dates = dates_by_app.get(app_id, [])
        pub_pre24 = count_in_window(dates, P1_PRE_START, P1_PRE_END)
        pub_post24 = count_in_window(dates, P1_POST_START, P1_POST_END)
        out.update(
            {
                "pub_pre24": pub_pre24,
                "pub_post24": pub_post24,
                "any_pub_pre24": int(pub_pre24 > 0),
                "any_pub_post24": int(pub_post24 > 0),
                "delta_pub24": pub_post24 - pub_pre24,
                "delta_any_pub24": int(pub_post24 > 0) - int(pub_pre24 > 0),
                "p1_existing_project_sample": int(bool(start and start < POLICY_DATE)),
            }
        )
        for horizon in (6, 12, 18):
            sufficient = bool(start and add_months(start, horizon) <= publication_observation_end + timedelta(days=1))
            count = count_within_months(dates, start, horizon) if start and sufficient else 0
            out[f"publication_{horizon}m"] = count
            out[f"any_publication_{horizon}m"] = int(count > 0)
            out[f"sufficient_followup_{horizon}m"] = int(sufficient)
        out["p2_entry_cohort"] = (
            "pre12_entry"
            if start and P2_ENTRY_PRE_START <= start <= P2_ENTRY_PRE_END
            else "post12_entry"
            if start and P2_ENTRY_POST_START <= start <= P2_ENTRY_POST_END
            else "outside_entry_window"
        )
        rows.append(out)
    return rows


def build_period_panel(app_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in app_rows:
        for period in ("pre24", "post24"):
            count_col = "pub_pre24" if period == "pre24" else "pub_post24"
            any_col = "any_pub_pre24" if period == "pre24" else "any_pub_post24"
            rows.append(
                {
                    "app_id": row["app_id"],
                    "period": period,
                    "period_start": P1_PRE_START.isoformat() if period == "pre24" else P1_POST_START.isoformat(),
                    "period_end": P1_PRE_END.isoformat() if period == "pre24" else P1_POST_END.isoformat(),
                    "publication_count": row[count_col],
                    "any_publication": row[any_col],
                    "project_start_date": row["project_start_date"],
                    "p1_existing_project_sample": row["p1_existing_project_sample"],
                    "original_stage3_classification": row["original_stage3_classification"],
                    "control_layer": row["control_layer"],
                    **{f"regression_group_{definition}": row[f"regression_group_{definition}"] for definition in CONTROL_DEFS},
                }
            )
    return rows


def build_dmca_crosswalk(
    project_rows: list[dict[str, object]],
    dmca_manual_review_path: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, dict[str, object]]]:
    project_by_app = {str(row["app_id"]): row for row in project_rows}
    evidence_rows_by_app: dict[str, list[dict[str, str]]] = defaultdict(list)
    if dmca_manual_review_path.exists():
        for row in read_csv(dmca_manual_review_path):
            app_id = row.get("candidate_app_id", "").strip()
            if app_id in BROAD_48:
                evidence_rows_by_app[app_id].append(row)

    crosswalk: list[dict[str, object]] = []
    unmatched: list[dict[str, object]] = []
    dmca_by_app: dict[str, dict[str, object]] = {}
    for app_id in sorted(BROAD_48, key=lambda value: int(value)):
        evidence_rows = evidence_rows_by_app.get(app_id, [])
        notices = sorted({row.get("notice_id", "") for row in evidence_rows if row.get("notice_id")})
        lineages = sorted({row.get("lineage_id", "") for row in evidence_rows if row.get("lineage_id")})
        repo_urls = sorted({row.get("repo_url", "") for row in evidence_rows if row.get("repo_url")})
        dates = sorted(value for value in (parse_date(row.get("notice_date", "")) for row in evidence_rows) if value is not None)
        in_universe = app_id in project_by_app
        set_name = "STRICT_21" if app_id in STRICT_21 else "MAIN_EXTRA_6" if app_id in MAIN_EXTRA_6 else "BROAD_EXTRA_21"
        row = {
            "app_id": app_id,
            "curated_set": set_name,
            "dmca_strict_21": int(app_id in STRICT_21),
            "dmca_main_27": int(app_id in MAIN_27),
            "dmca_broad_48": 1,
            "merged_to_working_universe": int(in_universe),
            "dmca_notice_count_available_evidence": len(notices),
            "dmca_lineage_count_available_evidence": len(lineages),
            "dmca_notice_count_lower_bound": max(1, len(notices)),
            "dmca_lineage_count_lower_bound": max(1, len(lineages)),
            "first_dmca_notice_date": dates[0].isoformat() if dates else "",
            "notice_ids": "; ".join(notices),
            "lineage_ids": "; ".join(lineages),
            "repo_urls": "; ".join(repo_urls),
            "evidence_classes": uniq([row.get("evidence_class", "") for row in evidence_rows]),
            "match_grades": uniq([row.get("match_grade", "") for row in evidence_rows]),
            "count_note": "available_notice_lineage_evidence" if notices or lineages else "curated_app_only_lower_bound_1",
        }
        if in_universe:
            project = project_by_app[app_id]
            row.update(
                {
                    "project_start_date": project.get("project_start_date", ""),
                    "original_stage3_classification": project.get("original_stage3_classification", ""),
                    "control_layer": project.get("control_layer", ""),
                    "schema27_title": project.get("schema27_title", ""),
                }
            )
            dmca_by_app[app_id] = row
        else:
            unmatched.append(row)
        crosswalk.append(row)
    return crosswalk, unmatched, dmca_by_app


def append_dmca_outcomes(
    app_rows: list[dict[str, object]],
    dmca_by_app: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in app_rows:
        app_id = str(row["app_id"])
        dmca = dmca_by_app.get(app_id, {})
        out = dict(row)
        out.update(
            {
                "dmca_strict_21": int(app_id in STRICT_21),
                "dmca_main_27": int(app_id in MAIN_27),
                "dmca_broad_48": int(app_id in BROAD_48),
                "dmca_notice_count": safe_int(dmca.get("dmca_notice_count_lower_bound", 0)),
                "dmca_lineage_count": safe_int(dmca.get("dmca_lineage_count_lower_bound", 0)),
                "first_dmca_notice_date": dmca.get("first_dmca_notice_date", ""),
                "dmca_count_note": dmca.get("count_note", ""),
            }
        )
        rows.append(out)
    return rows


def invert_matrix(matrix: list[list[float]]) -> list[list[float]] | None:
    n = len(matrix)
    aug = [[float(matrix[i][j]) for j in range(n)] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) < 1e-10:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        denom = aug[col][col]
        aug[col] = [value / denom for value in aug[col]]
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


def ols_robust(
    rows: list[dict[str, object]],
    outcome: str,
    treatment_col: str,
    controls: list[str] | None = None,
) -> dict[str, object]:
    controls = controls or []
    clean: list[dict[str, object]] = []
    for row in rows:
        y_value = row.get(outcome, "")
        t_value = row.get(treatment_col, "")
        if y_value == "" or t_value == "":
            continue
        clean.append(row)
    if len(clean) < 3:
        return {"n": len(clean), "estimate": None, "robust_se": None, "p_value": None, "warning": "too_few_rows"}

    control_levels: dict[str, list[str]] = {}
    for control in controls:
        levels = sorted({str(row.get(control, "")) for row in clean if str(row.get(control, ""))})
        if len(levels) > 1:
            control_levels[control] = levels[1:]

    names = ["intercept", treatment_col]
    for control, levels in control_levels.items():
        names.extend([f"{control}_{level}" for level in levels])

    x_rows: list[list[float]] = []
    y: list[float] = []
    for row in clean:
        values = [1.0, float(row.get(treatment_col, 0))]
        for control, levels in control_levels.items():
            current = str(row.get(control, ""))
            values.extend([1.0 if current == level else 0.0 for level in levels])
        x_rows.append(values)
        y.append(float(row.get(outcome, 0)))

    k = len(names)
    xtx = [[sum(x[i] * x[j] for x in x_rows) for j in range(k)] for i in range(k)]
    inv = invert_matrix(xtx)
    warning = ""
    if inv is None and controls:
        return ols_robust(rows, outcome, treatment_col, controls=[])
    if inv is None:
        return {"n": len(clean), "estimate": None, "robust_se": None, "p_value": None, "warning": "singular_design"}

    xty = [sum(x[i] * y_value for x, y_value in zip(x_rows, y)) for i in range(k)]
    beta = mat_vec(inv, xty)
    residuals = [y_value - sum(x[i] * beta[i] for i in range(k)) for x, y_value in zip(x_rows, y)]
    meat = [[0.0 for _ in range(k)] for _ in range(k)]
    for x, resid in zip(x_rows, residuals):
        for i in range(k):
            for j in range(k):
                meat[i][j] += resid * resid * x[i] * x[j]
    variance = mat_mul(mat_mul(inv, meat), inv)
    scale = len(clean) / max(1, len(clean) - k)
    diag = max(0.0, variance[1][1] * scale)
    se = math.sqrt(diag)
    estimate = beta[1]
    p_value = math.erfc(abs(estimate / se) / math.sqrt(2)) if se > 0 else None
    if controls and not control_levels:
        warning = "controls_dropped_no_variation"
    return {
        "n": len(clean),
        "estimate": estimate,
        "robust_se": se,
        "p_value": p_value,
        "warning": warning,
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def p1_analysis(app_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    regression_rows: list[dict[str, object]] = []
    mean_rows: list[dict[str, object]] = []
    base = [row for row in app_rows if safe_int(row.get("p1_existing_project_sample", 0)) == 1]
    for definition in CONTROL_DEFS:
        tagged: list[dict[str, object]] = []
        for row in base:
            group = str(row[f"regression_group_{definition}"])
            if not (group_is_treated(group) or group_is_control(group)):
                continue
            tagged_row = dict(row)
            tagged_row["treated_vs_control"] = 1 if group_is_treated(group) else 0
            tagged.append(tagged_row)

        for outcome, label in (("delta_pub24", "publication_count_delta_24m"), ("delta_any_pub24", "any_publication_delta_24m")):
            fit = ols_robust(tagged, outcome, "treated_vs_control")
            regression_rows.append(
                {
                    "design": "P1_existing_project_policy_did_first_difference",
                    "model": "ols_first_difference_robust_se",
                    "control_definition": definition,
                    "outcome": label,
                    "coefficient": "treated_minus_control_did",
                    "n": fit["n"],
                    "estimate": fmt(fit["estimate"]),
                    "robust_se": fmt(fit["robust_se"]),
                    "p_value": fmt(fit["p_value"]),
                    "warning": fit["warning"],
                }
            )

        treated = [row for row in tagged if safe_int(row["treated_vs_control"]) == 1]
        control = [row for row in tagged if safe_int(row["treated_vs_control"]) == 0]
        for outcome_prefix, pre_col, post_col in (
            ("publication_count", "pub_pre24", "pub_post24"),
            ("any_publication", "any_pub_pre24", "any_pub_post24"),
        ):
            t_pre = mean([float(row[pre_col]) for row in treated])
            t_post = mean([float(row[post_col]) for row in treated])
            c_pre = mean([float(row[pre_col]) for row in control])
            c_post = mean([float(row[post_col]) for row in control])
            mean_rows.append(
                {
                    "design": "P1_existing_project_policy_did",
                    "control_definition": definition,
                    "outcome": outcome_prefix,
                    "treated_n": len(treated),
                    "control_n": len(control),
                    "treated_pre_mean": fmt(t_pre),
                    "treated_post_mean": fmt(t_post),
                    "control_pre_mean": fmt(c_pre),
                    "control_post_mean": fmt(c_post),
                    "did_difference": fmt((t_post - t_pre) - (c_post - c_pre)),
                    "note": "post_policy_start_projects_excluded",
                }
            )
    return regression_rows, mean_rows


def p2_analysis(app_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    regression_rows: list[dict[str, object]] = []
    mean_rows: list[dict[str, object]] = []
    for horizon in (6, 12, 18):
        sample = [
            dict(row, p2_post_policy_start=1 if row.get("p2_entry_cohort") == "post12_entry" else 0)
            for row in app_rows
            if row.get("p2_entry_cohort") in {"pre12_entry", "post12_entry"}
            and safe_int(row.get(f"sufficient_followup_{horizon}m", 0)) == 1
        ]
        for outcome in (f"publication_{horizon}m", f"any_publication_{horizon}m"):
            fit = ols_robust(sample, outcome, "p2_post_policy_start")
            regression_rows.append(
                {
                    "design": "P2_project_entry_cohort_before_after",
                    "model": "ols_post_policy_start_robust_se",
                    "control_definition": "all_projects",
                    "outcome": outcome,
                    "coefficient": "post_policy_start",
                    "n": fit["n"],
                    "estimate": fmt(fit["estimate"]),
                    "robust_se": fmt(fit["robust_se"]),
                    "p_value": fmt(fit["p_value"]),
                    "warning": fit["warning"],
                }
            )
        pre = [row for row in sample if safe_int(row["p2_post_policy_start"]) == 0]
        post = [row for row in sample if safe_int(row["p2_post_policy_start"]) == 1]
        mean_rows.append(
            {
                "design": f"P2_project_entry_cohort_{horizon}m",
                "control_definition": "all_projects",
                "outcome": f"publication_{horizon}m",
                "treated_n": "",
                "control_n": "",
                "pre_policy_start_n": len(pre),
                "post_policy_start_n": len(post),
                "pre_policy_start_mean": fmt(mean([float(row[f"publication_{horizon}m"]) for row in pre])),
                "post_policy_start_mean": fmt(mean([float(row[f"publication_{horizon}m"]) for row in post])),
                "difference": fmt(
                    mean([float(row[f"publication_{horizon}m"]) for row in post])
                    - mean([float(row[f"publication_{horizon}m"]) for row in pre])
                ),
                "note": "not_did_sufficient_followup_required",
            }
        )
        mean_rows.append(
            {
                "design": f"P2_project_entry_cohort_{horizon}m",
                "control_definition": "all_projects",
                "outcome": f"any_publication_{horizon}m",
                "treated_n": "",
                "control_n": "",
                "pre_policy_start_n": len(pre),
                "post_policy_start_n": len(post),
                "pre_policy_start_mean": fmt(mean([float(row[f"any_publication_{horizon}m"]) for row in pre])),
                "post_policy_start_mean": fmt(mean([float(row[f"any_publication_{horizon}m"]) for row in post])),
                "difference": fmt(
                    mean([float(row[f"any_publication_{horizon}m"]) for row in post])
                    - mean([float(row[f"any_publication_{horizon}m"]) for row in pre])
                ),
                "note": "not_did_sufficient_followup_required",
            }
        )

    for definition in CONTROL_DEFS:
        sample = []
        for row in app_rows:
            group = str(row[f"regression_group_{definition}"])
            if row.get("p2_entry_cohort") not in {"pre12_entry", "post12_entry"}:
                continue
            if safe_int(row.get("sufficient_followup_12m", 0)) != 1:
                continue
            if not (group_is_treated(group) or group_is_control(group)):
                continue
            p2_post = 1 if row.get("p2_entry_cohort") == "post12_entry" else 0
            exposed = 1 if group_is_treated(group) else 0
            sample.append(dict(row, p2_post_policy_start=p2_post, p2_exposed=exposed, p2_post_x_exposed=p2_post * exposed))
        for outcome in ("publication_12m", "any_publication_12m"):
            fit = ols_robust(sample, outcome, "p2_post_x_exposed", controls=["p2_post_policy_start", "p2_exposed"])
            regression_rows.append(
                {
                    "design": "P2_project_entry_cohort_group_interaction",
                    "model": "ols_interaction_robust_se",
                    "control_definition": definition,
                    "outcome": outcome,
                    "coefficient": "post_policy_start_x_provisional_treated",
                    "n": fit["n"],
                    "estimate": fmt(fit["estimate"]),
                    "robust_se": fmt(fit["robust_se"]),
                    "p_value": fmt(fit["p_value"]),
                    "warning": fit["warning"],
                }
            )
    return regression_rows, mean_rows


def fisher_exact_two_sided(treated_event: int, treated_non: int, control_event: int, control_non: int) -> float:
    row1 = treated_event + treated_non
    row2 = control_event + control_non
    col1 = treated_event + control_event
    n = row1 + row2
    if n == 0:
        return 1.0

    def log_prob(x: int) -> float:
        if x < max(0, col1 - row2) or x > min(row1, col1):
            return float("-inf")
        return (
            math.lgamma(row1 + 1)
            - math.lgamma(x + 1)
            - math.lgamma(row1 - x + 1)
            + math.lgamma(row2 + 1)
            - math.lgamma(col1 - x + 1)
            - math.lgamma(row2 - (col1 - x) + 1)
            - math.lgamma(n + 1)
            + math.lgamma(col1 + 1)
            + math.lgamma(n - col1 + 1)
        )

    observed = math.exp(log_prob(treated_event))
    probs = []
    for x in range(max(0, col1 - row2), min(row1, col1) + 1):
        p = math.exp(log_prob(x))
        if p <= observed + 1e-12:
            probs.append(p)
    return min(1.0, sum(probs))


def dmca_analysis(app_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    regression_rows: list[dict[str, object]] = []
    mean_rows: list[dict[str, object]] = []
    table_rows: list[dict[str, object]] = []
    primary = [row for row in app_rows if parse_date(str(row.get("project_start_date", ""))) and parse_date(str(row.get("project_start_date", ""))) < POLICY_DATE]
    for definition in CONTROL_DEFS:
        tagged = []
        for row in primary:
            group = str(row[f"regression_group_{definition}"])
            if not (group_is_treated(group) or group_is_control(group)):
                continue
            tagged.append(dict(row, treated_vs_control=1 if group_is_treated(group) else 0))
        for outcome in ("dmca_strict_21", "dmca_main_27", "dmca_broad_48"):
            treated = [row for row in tagged if safe_int(row["treated_vs_control"]) == 1]
            control = [row for row in tagged if safe_int(row["treated_vs_control"]) == 0]
            t_event = sum(safe_int(row[outcome]) for row in treated)
            c_event = sum(safe_int(row[outcome]) for row in control)
            t_non = len(treated) - t_event
            c_non = len(control) - c_event
            fisher = fisher_exact_two_sided(t_event, t_non, c_event, c_non)
            zero_warning = "zero_cell" if min(t_event, t_non, c_event, c_non) == 0 else ""
            table_rows.append(
                {
                    "control_definition": definition,
                    "outcome": outcome,
                    "treated_event": t_event,
                    "treated_non_event": t_non,
                    "control_event": c_event,
                    "control_non_event": c_non,
                    "treated_n": len(treated),
                    "control_n": len(control),
                    "treated_event_rate": fmt(t_event / len(treated) if treated else 0),
                    "control_event_rate": fmt(c_event / len(control) if control else 0),
                    "fisher_exact_p": fmt(fisher),
                    "warning": zero_warning,
                }
            )
            mean_rows.append(
                {
                    "design": "DMCA_application_level_rare_outcome",
                    "control_definition": definition,
                    "outcome": outcome,
                    "treated_n": len(treated),
                    "control_n": len(control),
                    "treated_mean": fmt(t_event / len(treated) if treated else 0),
                    "control_mean": fmt(c_event / len(control) if control else 0),
                    "difference": fmt((t_event / len(treated) if treated else 0) - (c_event / len(control) if control else 0)),
                    "note": "exploratory_association_not_policy_did",
                }
            )
            fit = ols_robust(tagged, outcome, "treated_vs_control", controls=["project_start_year"])
            regression_rows.append(
                {
                    "design": "DMCA_application_level_rare_outcome",
                    "model": "lpm_ols_start_year_fe_robust_se",
                    "control_definition": definition,
                    "outcome": outcome,
                    "coefficient": "provisional_treated",
                    "n": fit["n"],
                    "estimate": fmt(fit["estimate"]),
                    "robust_se": fmt(fit["robust_se"]),
                    "p_value": fmt(fit["p_value"]),
                    "warning": "; ".join(part for part in [fit["warning"], zero_warning] if part),
                }
            )
        fit_count = ols_robust(tagged, "dmca_lineage_count", "treated_vs_control", controls=["project_start_year"])
        regression_rows.append(
            {
                "design": "DMCA_application_level_count_secondary",
                "model": "ols_count_start_year_fe_robust_se",
                "control_definition": definition,
                "outcome": "dmca_lineage_count",
                "coefficient": "provisional_treated",
                "n": fit_count["n"],
                "estimate": fmt(fit_count["estimate"]),
                "robust_se": fmt(fit_count["robust_se"]),
                "p_value": fmt(fit_count["p_value"]),
                "warning": fit_count["warning"],
            }
        )
    return regression_rows, mean_rows, table_rows


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_bar_png(path: Path, values: list[float], colors: list[tuple[int, int, int]], width: int = 900, height: int = 420) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bg = (255, 255, 255)
    pixels = [[bg for _ in range(width)] for _ in range(height)]
    left, right, top, bottom = 70, 30, 30, 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    for x in range(left, width - right):
        pixels[height - bottom][x] = (60, 60, 60)
    for y in range(top, height - bottom + 1):
        pixels[y][left] = (60, 60, 60)
    if not values:
        values = [0.0]
    max_value = max(values) if max(values) > 0 else 1.0
    slot = plot_w / len(values)
    for i, value in enumerate(values):
        bar_h = int((value / max_value) * (plot_h - 10))
        x0 = int(left + i * slot + slot * 0.18)
        x1 = int(left + (i + 1) * slot - slot * 0.18)
        y0 = height - bottom - bar_h
        color = colors[i % len(colors)]
        for y in range(max(top, y0), height - bottom):
            for x in range(max(left, x0), min(width - right, x1)):
                pixels[y][x] = color
    raw = b"".join(b"\x00" + bytes(component for pixel in row for component in pixel) for row in pixels)
    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(raw, 9))
    data += png_chunk(b"IEND", b"")
    path.write_bytes(data)


def build_figures(paths: FastPaths, group_means: list[dict[str, object]], dmca_tables: list[dict[str, object]]) -> None:
    p1_c05 = [row for row in group_means if row.get("design") == "P1_existing_project_policy_did" and row.get("control_definition") == "CONTROL_C05" and row.get("outcome") == "publication_count"]
    if p1_c05:
        row = p1_c05[0]
        values = [
            float(row.get("treated_pre_mean") or 0),
            float(row.get("treated_post_mean") or 0),
            float(row.get("control_pre_mean") or 0),
            float(row.get("control_post_mean") or 0),
        ]
    else:
        values = [0.0, 0.0, 0.0, 0.0]
    write_bar_png(paths.publication_did_figure, values, [(37, 99, 235), (30, 64, 175), (245, 158, 11), (180, 83, 9)])

    p2_12 = [row for row in group_means if row.get("design") == "P2_project_entry_cohort_12m"]
    if p2_12:
        row = p2_12[0]
        values = [float(row.get("pre_policy_start_mean") or 0), float(row.get("post_policy_start_mean") or 0)]
    else:
        values = [0.0, 0.0]
    write_bar_png(paths.publication_cohort_figure, values, [(22, 163, 74), (220, 38, 38)])

    dmca_c05 = [row for row in dmca_tables if row.get("control_definition") == "CONTROL_C05"]
    values = []
    for outcome in ("dmca_strict_21", "dmca_main_27", "dmca_broad_48"):
        row = next((item for item in dmca_c05 if item.get("outcome") == outcome), None)
        if row:
            values.extend([float(row.get("treated_event_rate") or 0), float(row.get("control_event_rate") or 0)])
    write_bar_png(paths.dmca_rates_figure, values or [0.0], [(147, 51, 234), (107, 33, 168), (20, 184, 166), (15, 118, 110)])


def markdown_table(rows: list[dict[str, object]], columns: list[str], limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in selected:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def group_count_rows(app_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for definition in CONTROL_DEFS:
        counts = Counter(str(row.get(f"regression_group_{definition}", "")) for row in app_rows)
        rows.append(
            {
                "control_definition": definition,
                "treated": counts.get("treated", 0),
                "control_clean": counts.get("control", 0),
                "control_overlap_original_newly_rap_bound": counts.get("control_overlap_original_newly_rap_bound", 0),
                "control_overlap_original_mixed": counts.get("control_overlap_original_mixed", 0),
                "control_overlap_original_unclear": counts.get("control_overlap_original_unclear", 0),
                "excluded_mixed": counts.get("excluded_mixed", 0),
                "excluded_unclear": counts.get("excluded_unclear", 0),
                "excluded_already_rap_not_in_definition": counts.get("excluded_already_rap_not_in_definition", 0),
            }
        )
    return rows


def build_report(
    paths: FastPaths,
    summary: dict[str, object],
    app_rows: list[dict[str, object]],
    regression_rows: list[dict[str, object]],
    group_means: list[dict[str, object]],
    dmca_tables: list[dict[str, object]],
    source_commit: str,
) -> None:
    p1_means = [row for row in group_means if row.get("design") == "P1_existing_project_policy_did"]
    p2_means = [row for row in group_means if str(row.get("design", "")).startswith("P2_project_entry_cohort_")]
    dmca_means = [row for row in group_means if row.get("design") == "DMCA_application_level_rare_outcome"]
    p1_regs = [row for row in regression_rows if row.get("design") == "P1_existing_project_policy_did_first_difference"]
    p2_regs = [row for row in regression_rows if str(row.get("design", "")).startswith("P2_project_entry_cohort")]
    dmca_regs = [row for row in regression_rows if row.get("design") == "DMCA_application_level_rare_outcome"]
    dmca_count_regs = [row for row in regression_rows if row.get("design") == "DMCA_application_level_count_secondary"]

    parts = [
        "# Stage 5 Fast Exploratory Results",
        "",
        f"Source commit: `{source_commit}`",
        f"Policy date: `{POLICY_DATE.isoformat()}`",
        "",
        "This fast run is provisional. It preserves the existing Stage 3 measurement,",
        "uses C0-C5 as broad control-candidate sensitivity definitions, excludes C6",
        "from main controls, and does not finalize treatment/control status.",
        "",
        "DMCA outcomes mean an application is linked by evidence to a DMCA-targeted",
        "repository lineage. They are not findings of unlawful conduct or policy",
        "violation.",
        "",
        "## Diagnostics",
        "",
        markdown_table(
            [
                {"metric": key, "value": value}
                for key, value in summary.items()
                if key
                in {
                    "working_universe_projects",
                    "p1_existing_project_apps",
                    "p1_post_policy_start_apps_excluded",
                    "publication_events",
                    "publication_observation_end",
                    "dmca_strict_21_merged",
                    "dmca_main_27_merged",
                    "dmca_broad_48_merged",
                    "dmca_curated_unmatched_apps",
                    "control_c0_projects",
                    "control_c01_projects",
                    "control_c03_projects",
                    "control_c05_projects",
                    "c6_preserved_flag_projects",
                }
            ],
            ["metric", "value"],
        ),
        "",
        "## Control And Exclusion Counts",
        "",
        "Controls include explicit overlap labels when C1-C5 pulls in projects",
        "whose original Stage 3 classification was NEWLY_RAP_BOUND, MIXED, or",
        "UNCLEAR. Those rows are excluded from the treated group under that",
        "control definition.",
        "",
        markdown_table(
            group_count_rows(app_rows),
            [
                "control_definition",
                "treated",
                "control_clean",
                "control_overlap_original_newly_rap_bound",
                "control_overlap_original_mixed",
                "control_overlap_original_unclear",
                "excluded_mixed",
                "excluded_unclear",
                "excluded_already_rap_not_in_definition",
            ],
        ),
        "",
        "## P1 Publication DID Means",
        "",
        markdown_table(
            p1_means,
            [
                "control_definition",
                "outcome",
                "treated_n",
                "control_n",
                "treated_pre_mean",
                "treated_post_mean",
                "control_pre_mean",
                "control_post_mean",
                "did_difference",
            ],
        ),
        "",
        "## P1 Publication DID Regressions",
        "",
        markdown_table(
            p1_regs,
            ["control_definition", "outcome", "n", "estimate", "robust_se", "p_value", "warning"],
        ),
        "",
        "## P2 Entry Cohort Means",
        "",
        markdown_table(
            p2_means,
            ["design", "outcome", "pre_policy_start_n", "post_policy_start_n", "pre_policy_start_mean", "post_policy_start_mean", "difference", "note"],
        ),
        "",
        "## P2 Entry Cohort Regressions",
        "",
        markdown_table(
            p2_regs,
            ["design", "control_definition", "outcome", "coefficient", "n", "estimate", "robust_se", "p_value", "warning"],
        ),
        "",
        "## DMCA 2x2 Tables",
        "",
        markdown_table(
            dmca_tables,
            [
                "control_definition",
                "outcome",
                "treated_event",
                "treated_n",
                "control_event",
                "control_n",
                "treated_event_rate",
                "control_event_rate",
                "fisher_exact_p",
                "warning",
            ],
        ),
        "",
        "## DMCA LPM Regressions",
        "",
        markdown_table(
            dmca_regs,
            ["control_definition", "outcome", "n", "estimate", "robust_se", "p_value", "warning"],
        ),
        "",
        "## DMCA Lineage Count Secondary Regressions",
        "",
        markdown_table(
            dmca_count_regs,
            ["control_definition", "outcome", "n", "estimate", "robust_se", "p_value", "warning"],
        ),
        "",
        "## Output Files",
        "",
        "- `data/processed/stage4_fast_application_outcomes.csv`",
        "- `data/processed/stage4_fast_publication_events.csv`",
        "- `data/processed/stage4_fast_publication_period_panel.csv`",
        "- `data/processed/stage4_fast_dmca_crosswalk.csv`",
        "- `data/processed/stage4_fast_dmca_unmatched_apps.csv`",
        "- `data/processed/stage5_fast_regression_results.csv`",
        "- `data/processed/stage5_fast_group_means.csv`",
        "- `data/processed/stage5_fast_dmca_2x2.csv`",
        "- `figures/stage5_publication_did.png`",
        "- `figures/stage5_publication_cohort.png`",
        "- `figures/stage5_dmca_rates.png`",
        "",
        "## Limitations To Revisit",
        "",
        "- C0-C5 are provisional broad controls, not final causal controls.",
        "- C6 is preserved in flags but excluded from main fast-run controls.",
        "- P2 is a project-entry before/after cohort design, not a DID.",
        "- DMCA regressions are rare-outcome exploratory associations, not a",
        "  conventional pre/post policy DID.",
        "- Curated DMCA application-only links use a lower-bound count of one when",
        "  notice/lineage evidence is not available in the current local audit files.",
    ]
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text("\n".join(parts) + "\n", encoding="utf-8")


def build_fast_outputs(
    stage3_path: Path = DEFAULT_STAGE3,
    timing_metadata_path: Path = DEFAULT_TIMING_METADATA,
    control_expansion_path: Path = DEFAULT_CONTROL_EXPANSION,
    schema19_path: Path = DEFAULT_SCHEMA19,
    schema24_path: Path = DEFAULT_SCHEMA24,
    dmca_manual_review_path: Path = DEFAULT_DMCA_MANUAL_REVIEW,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    expected_universe: int | None = 6935,
    source_commit: str = "",
) -> dict[str, object]:
    paths = output_paths(output_dir)
    project_rows, project_summary = build_project_rows(
        stage3_path=stage3_path,
        control_expansion_path=control_expansion_path,
        expected_universe=expected_universe,
        timing_metadata_path=timing_metadata_path,
    )
    pub_events, dates_by_app, publication_observation_end = build_publication_events(project_rows, schema19_path, schema24_path)
    app_rows = append_publication_outcomes(project_rows, dates_by_app, publication_observation_end)
    dmca_crosswalk, dmca_unmatched, dmca_by_app = build_dmca_crosswalk(app_rows, dmca_manual_review_path)
    app_rows = append_dmca_outcomes(app_rows, dmca_by_app)
    period_panel = build_period_panel(app_rows)

    p1_regs, p1_means = p1_analysis(app_rows)
    p2_regs, p2_means = p2_analysis(app_rows)
    dmca_regs, dmca_means, dmca_tables = dmca_analysis(app_rows)
    regression_rows = [*p1_regs, *p2_regs, *dmca_regs]
    group_means = [*p1_means, *p2_means, *dmca_means]

    app_fieldnames = [
        "app_id",
        "project_start_date",
        "project_start_year",
        "post_policy_start",
        "original_stage3_classification",
        "stage3_confidence",
        "control_layer",
        "cumulative_control_C0",
        "cumulative_control_C01",
        "cumulative_control_C03",
        "cumulative_control_C05",
        "cumulative_control_C06",
        "regression_group_CONTROL_C0",
        "regression_group_CONTROL_C01",
        "regression_group_CONTROL_C03",
        "regression_group_CONTROL_C05",
        "pub_pre24",
        "pub_post24",
        "any_pub_pre24",
        "any_pub_post24",
        "delta_pub24",
        "delta_any_pub24",
        "p1_existing_project_sample",
        "publication_6m",
        "publication_12m",
        "publication_18m",
        "any_publication_6m",
        "any_publication_12m",
        "any_publication_18m",
        "sufficient_followup_6m",
        "sufficient_followup_12m",
        "sufficient_followup_18m",
        "p2_entry_cohort",
        "dmca_strict_21",
        "dmca_main_27",
        "dmca_broad_48",
        "dmca_notice_count",
        "dmca_lineage_count",
        "first_dmca_notice_date",
        "dmca_count_note",
        "stage3_already_rap_modalities",
        "stage3_legacy_route_modalities",
        "schema27_title",
        "schema27_pi",
        "schema27_institution",
        "website_url",
    ]
    write_csv(paths.application_outcomes, app_rows, app_fieldnames)
    write_csv(
        paths.publication_events,
        pub_events,
        [
            "app_id",
            "pub_id",
            "publication_date",
            "publication_year",
            "project_start_date",
            "months_since_project_start",
            "publication_before_or_after_policy",
            "title",
            "doi",
            "pubmed_id",
            "journal",
        ],
    )
    write_csv(
        paths.publication_period_panel,
        period_panel,
        [
            "app_id",
            "period",
            "period_start",
            "period_end",
            "publication_count",
            "any_publication",
            "project_start_date",
            "p1_existing_project_sample",
            "original_stage3_classification",
            "control_layer",
            "regression_group_CONTROL_C0",
            "regression_group_CONTROL_C01",
            "regression_group_CONTROL_C03",
            "regression_group_CONTROL_C05",
        ],
    )
    write_csv(
        paths.dmca_crosswalk,
        dmca_crosswalk,
        [
            "app_id",
            "curated_set",
            "dmca_strict_21",
            "dmca_main_27",
            "dmca_broad_48",
            "merged_to_working_universe",
            "project_start_date",
            "original_stage3_classification",
            "control_layer",
            "schema27_title",
            "dmca_notice_count_available_evidence",
            "dmca_lineage_count_available_evidence",
            "dmca_notice_count_lower_bound",
            "dmca_lineage_count_lower_bound",
            "first_dmca_notice_date",
            "notice_ids",
            "lineage_ids",
            "repo_urls",
            "evidence_classes",
            "match_grades",
            "count_note",
        ],
    )
    write_csv(paths.dmca_unmatched_apps, dmca_unmatched, list(dmca_crosswalk[0].keys()) if dmca_crosswalk else ["app_id"])
    write_csv(
        paths.regression_results,
        regression_rows,
        ["design", "model", "control_definition", "outcome", "coefficient", "n", "estimate", "robust_se", "p_value", "warning"],
    )
    group_fields = sorted({key for row in group_means for key in row})
    write_csv(paths.group_means, group_means, group_fields)
    write_csv(
        paths.dmca_2x2,
        dmca_tables,
        [
            "control_definition",
            "outcome",
            "treated_event",
            "treated_non_event",
            "control_event",
            "control_non_event",
            "treated_n",
            "control_n",
            "treated_event_rate",
            "control_event_rate",
            "fisher_exact_p",
            "warning",
        ],
    )

    summary: dict[str, object] = {
        **project_summary,
        "source_commit": source_commit,
        "policy_date": POLICY_DATE.isoformat(),
        "publication_events": len(pub_events),
        "publication_observation_end": publication_observation_end.isoformat(),
        "p1_existing_project_apps": sum(safe_int(row["p1_existing_project_sample"]) for row in app_rows),
        "p1_post_policy_start_apps_excluded": sum(1 for row in app_rows if safe_int(row["p1_existing_project_sample"]) == 0),
        "p2_pre12_entry_apps": sum(1 for row in app_rows if row["p2_entry_cohort"] == "pre12_entry"),
        "p2_post12_entry_apps": sum(1 for row in app_rows if row["p2_entry_cohort"] == "post12_entry"),
        "control_c0_projects": sum(safe_int(row["cumulative_control_C0"]) for row in app_rows),
        "control_c01_projects": sum(safe_int(row["cumulative_control_C01"]) for row in app_rows),
        "control_c03_projects": sum(safe_int(row["cumulative_control_C03"]) for row in app_rows),
        "control_c05_projects": sum(safe_int(row["cumulative_control_C05"]) for row in app_rows),
        "c6_preserved_flag_projects": sum(safe_int(row["cumulative_control_C06"]) for row in app_rows)
        - sum(safe_int(row["cumulative_control_C05"]) for row in app_rows),
        "dmca_strict_21_merged": sum(1 for row in dmca_crosswalk if row["dmca_strict_21"] and row["merged_to_working_universe"]),
        "dmca_main_27_merged": sum(1 for row in dmca_crosswalk if row["dmca_main_27"] and row["merged_to_working_universe"]),
        "dmca_broad_48_merged": sum(1 for row in dmca_crosswalk if row["dmca_broad_48"] and row["merged_to_working_universe"]),
        "dmca_curated_unmatched_apps": len(dmca_unmatched),
        "did_regressions_label": "provisional_exploratory_publication_p1_only",
        "dmca_design_label": "exploratory_application_level_association_not_policy_did",
    }
    paths.summary_json.parent.mkdir(parents=True, exist_ok=True)
    paths.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    build_figures(paths, group_means, dmca_tables)
    build_report(paths, summary, app_rows, regression_rows, group_means, dmca_tables, source_commit=source_commit or "local")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage3", type=Path, default=DEFAULT_STAGE3)
    parser.add_argument("--timing-metadata", type=Path, default=DEFAULT_TIMING_METADATA)
    parser.add_argument("--control-expansion", type=Path, default=DEFAULT_CONTROL_EXPANSION)
    parser.add_argument("--schema19", type=Path, default=DEFAULT_SCHEMA19)
    parser.add_argument("--schema24", type=Path, default=DEFAULT_SCHEMA24)
    parser.add_argument("--dmca-manual-review", type=Path, default=DEFAULT_DMCA_MANUAL_REVIEW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-universe", type=int, default=6935)
    parser.add_argument("--source-commit", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_fast_outputs(
        stage3_path=args.stage3,
        timing_metadata_path=args.timing_metadata,
        control_expansion_path=args.control_expansion,
        schema19_path=args.schema19,
        schema24_path=args.schema24,
        dmca_manual_review_path=args.dmca_manual_review,
        output_dir=args.output_dir,
        expected_universe=args.expected_universe,
        source_commit=args.source_commit,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
