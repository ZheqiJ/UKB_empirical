#!/usr/bin/env python3
"""Run project-entry2 high-sensitivity ITS analyses."""

from __future__ import annotations

import argparse
import csv
import math
import os
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import build_high_sensitivity_classification as classification_builder


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA_DIR = PACKAGE / "data"
DATA2_DIR = PACKAGE / "data2"
FIGURE_DIR = PACKAGE / "figures"
FIGURE2_DIR = PACKAGE / "figures2"
REPORT_DIR = PACKAGE / "reports"
REPORT2_DIR = PACKAGE / "reports2"
SCRIPT_DIR = PACKAGE / "scripts"

PRIMARY_START = date(2019, 1, 1)
PRIMARY_END = date(2025, 12, 1)
EXTENDED_END = date(2026, 6, 1)
BREAK_MONTH = date(2024, 7, 1)
HAC_LAG = 3


@dataclass(frozen=True)
class Outputs:
    monthly: Path = DATA_DIR / "project_entry2_monthly.csv"
    regression_results: Path = DATA_DIR / "project_entry2_regression_results.csv"
    test3_stacked: Path = DATA_DIR / "project_entry2_test3_stacked.csv"
    test3_partition_results: Path = DATA_DIR / "project_entry2_test3_partition_results.csv"
    replication_check: Path = DATA_DIR / "stata_python_replication_check.csv"
    stata_tmp: Path = DATA_DIR / "project_entry2_stata_results_tmp.dta"
    stata_do: Path = SCRIPT_DIR / "project_entry2_its.do"
    stata_log: Path = REPORT_DIR / "project_entry2_stata_full.log"
    stata_table: Path = REPORT_DIR / "project_entry2_stata_regression_table.csv"
    stata_style_python_table: Path = REPORT_DIR / "project_entry2_stata_style_regression_results.txt"
    reading_guide: Path = REPORT_DIR / "project_entry2_reading_guide.md"
    measurement_note: Path = REPORT_DIR / "project_entry2_measurement_note.md"
    results_report: Path = REPORT_DIR / "project_entry2_results.md"
    test1_figure: Path = FIGURE_DIR / "figure_test1_high_sensitivity_entry.svg"
    test2_figure: Path = FIGURE_DIR / "figure_test2_high_sensitivity_share.svg"
    test3_raw_figure: Path = FIGURE_DIR / "figure_test3_high_vs_low_raw.svg"
    test3_indexed_figure: Path = FIGURE_DIR / "figure_test3_high_vs_low_indexed.svg"


@dataclass(frozen=True)
class ExtendedOutputs:
    monthly: Path = DATA2_DIR / "project_entry2_monthly_2026h1.csv"
    audit_2026h1: Path = DATA2_DIR / "project_entry2_2026h1_audit.csv"
    regression_results: Path = DATA2_DIR / "project_entry2_regression_results_2026h1.csv"
    test3_stacked: Path = DATA2_DIR / "project_entry2_test3_stacked_2026h1.csv"
    test3_partition_results: Path = DATA2_DIR / "project_entry2_test3_partition_results_2026h1.csv"
    test3_raw_partition_results: Path = DATA2_DIR / "project_entry2_test3_raw_partition_results.csv"
    window_comparison: Path = DATA2_DIR / "project_entry2_window_comparison.csv"
    replication_check: Path = DATA2_DIR / "stata_python_replication_check_2026h1.csv"
    stata_tmp: Path = DATA2_DIR / "project_entry2_stata_results_2026h1_tmp.dta"
    stata_do: Path = SCRIPT_DIR / "project_entry2_its.do"
    stata_log: Path = REPORT2_DIR / "project_entry2_stata_full_2026h1.log"
    stata_table: Path = REPORT2_DIR / "project_entry2_stata_regression_table_2026h1.csv"
    stata_style_python_table: Path = REPORT2_DIR / "project_entry2_stata_style_regression_results_2026h1.txt"
    results_report: Path = REPORT2_DIR / "project_entry2_results_2026h1.md"
    window_comparison_report: Path = REPORT2_DIR / "project_entry2_window_comparison.md"
    test1_figure: Path = FIGURE2_DIR / "figure_test1_high_sensitivity_entry_2026h1.svg"
    test2_figure: Path = FIGURE2_DIR / "figure_test2_high_sensitivity_share_2026h1.svg"
    test3_raw_figure: Path = FIGURE2_DIR / "figure_test3_high_vs_low_raw_2026h1.svg"
    test3_indexed_figure: Path = FIGURE2_DIR / "figure_test3_high_vs_low_indexed_2026h1.svg"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def is_missing_outcome(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "na", "n/a", "none"}


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    return date(value.year + month // 12, month % 12 + 1, 1)


def month_range(start: date, end: date) -> list[date]:
    out = []
    current = date(start.year, start.month, 1)
    stop = date(end.year, end.month, 1)
    while current <= stop:
        out.append(current)
        current = add_months(current, 1)
    return out


def month_label(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f"{value:.{digits}f}"
    return str(value)


def two_sided_normal_pvalue(estimate: float, se: float) -> float:
    if se <= 0:
        return math.nan
    return math.erfc(abs(estimate / se) / math.sqrt(2.0))


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    rows, cols, inner = len(a), len(b[0]), len(b)
    return [[sum(a[i][k] * b[k][j] for k in range(inner)) for j in range(cols)] for i in range(rows)]


def mat_vec_mul(a: list[list[float]], v: list[float]) -> list[float]:
    return [sum(row[j] * v[j] for j in range(len(v))) for row in a]


def invert(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    aug = [[float(a[i][j]) for j in range(n)] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("singular regression matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [value / scale for value in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [aug[row][j] - factor * aug[col][j] for j in range(2 * n)]
    return [row[n:] for row in aug]


def xtx(X: list[list[float]]) -> list[list[float]]:
    k = len(X[0])
    out = [[0.0] * k for _ in range(k)]
    for row in X:
        for i in range(k):
            for j in range(k):
                out[i][j] += row[i] * row[j]
    return out


def xty(X: list[list[float]], y: list[float]) -> list[float]:
    k = len(X[0])
    out = [0.0] * k
    for row, yi in zip(X, y):
        for i in range(k):
            out[i] += row[i] * yi
    return out


def outer(a: list[float], b: list[float]) -> list[list[float]]:
    return [[ai * bj for bj in b] for ai in a]


def mat_add_inplace(a: list[list[float]], b: list[list[float]], scale: float = 1.0) -> None:
    for i in range(len(a)):
        for j in range(len(a[i])):
            a[i][j] += scale * b[i][j]


def sandwich_from_scores(bread: list[list[float]], scores: list[list[float]], lag: int) -> list[list[float]]:
    k = len(scores[0])
    meat = [[0.0] * k for _ in range(k)]
    for score in scores:
        mat_add_inplace(meat, outer(score, score))
    for ell in range(1, lag + 1):
        weight = 1.0 - ell / (lag + 1.0)
        for t in range(ell, len(scores)):
            mat_add_inplace(meat, outer(scores[t], scores[t - ell]), weight)
            mat_add_inplace(meat, outer(scores[t - ell], scores[t]), weight)
    return mat_mul(mat_mul(bread, meat), bread)


def design_row_from_monthly_row(row: dict[str, object]) -> list[float]:
    month_of_year = int(row["month_of_year"])
    return [
        1.0,
        float(row["time"]),
        float(row["post_july2024"]),
        float(row["time_after_july2024"]),
    ] + [1.0 if month_of_year == fixed_month else 0.0 for fixed_month in range(2, 13)]


def build_design(monthly_rows: list[dict[str, object]]) -> tuple[list[list[float]], list[str]]:
    names = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"] + [
        f"month_{month:02d}" for month in range(2, 13)
    ]
    return [design_row_from_monthly_row(row) for row in monthly_rows], names


def ols_hac(X: list[list[float]], y: list[float], lag: int = HAC_LAG) -> dict[str, object]:
    inv = invert(xtx(X))
    beta = mat_vec_mul(inv, xty(X, y))
    fitted = [sum(row[j] * beta[j] for j in range(len(beta))) for row in X]
    resid = [yi - fi for yi, fi in zip(y, fitted)]
    mean_y = sum(y) / len(y)
    rss = sum(e * e for e in resid)
    tss = sum((yi - mean_y) ** 2 for yi in y)
    r2 = 1.0 - rss / tss if tss > 0 else math.nan
    n, k = len(y), len(beta)
    scores = [[row[j] * e for j in range(k)] for row, e in zip(X, resid)]
    vcov = sandwich_from_scores(inv, scores, lag)
    se = [math.sqrt(max(vcov[i][i], 0.0)) for i in range(k)]
    f_stat = ((tss - rss) / max(k - 1, 1)) / (rss / max(n - k, 1)) if rss > 0 and k > 1 else math.nan
    return {
        "beta": beta,
        "fitted": fitted,
        "resid": resid,
        "vcov": vcov,
        "se": se,
        "n_obs": n,
        "k_params": k,
        "df_resid": n - k,
        "r_squared": r2,
        "model_f_statistic_classical": f_stat,
        "nw_lag": lag,
    }


def monthly_panel(
    classification_rows: list[dict[str, str]],
    end_month: date = PRIMARY_END,
) -> list[dict[str, object]]:
    rows_by_month = defaultdict(list)
    for row in classification_rows:
        start = parse_date(row["start_date"])
        rows_by_month[date(start.year, start.month, 1)].append(row)

    output = []
    for idx, month in enumerate(month_range(PRIMARY_START, end_month), start=1):
        rows = rows_by_month.get(month, [])

        def count(flag: str) -> int:
            return sum(int(row[flag]) for row in rows)

        all_count = len(rows)
        high = count("HIGH_SENSITIVITY")
        lower = count("LOWER_SENSITIVITY_COMPARISON")
        low = count("LOW_STRICT")
        time_after = (
            (month.year - BREAK_MONTH.year) * 12 + month.month - BREAK_MONTH.month
            if month >= BREAK_MONTH
            else 0
        )
        output.append(
            {
                "month": month_label(month),
                "month_start": month.isoformat(),
                "time": idx,
                "post_july2024": 1 if month >= BREAK_MONTH else 0,
                "time_after_july2024": time_after,
                "month_of_year": month.month,
                "all_count": all_count,
                "high_sensitivity_count": high,
                "lower_sensitivity_count": lower,
                "low_strict_count": low,
                "hs_wes_wgs_sequence_count": count("hs_wes_wgs_sequence"),
                "hs_s3_direct_count": count("hs_s3_direct"),
                "hs_s3_text_count": count("hs_s3_text"),
                "hs_o2_field_count": count("hs_o2_field"),
                "classified_denom_high_lower": high + lower,
                "high_sensitivity_share_all": fmt(high / all_count if all_count else None, 8),
                "low_share_all": fmt(low / all_count if all_count else math.nan, 8),
            }
        )

    pre_rows = [row for row in output if parse_date(str(row["month_start"])) < BREAK_MONTH]
    rows_2023 = [row for row in output if parse_date(str(row["month_start"])).year == 2023]

    def mean(rows: list[dict[str, object]], column: str) -> float:
        values = [float(row[column]) for row in rows]
        return sum(values) / len(values) if values else math.nan

    high_pre_mean = mean(pre_rows, "high_sensitivity_count")
    lower_pre_mean = mean(pre_rows, "lower_sensitivity_count")
    high_2023_mean = mean(rows_2023, "high_sensitivity_count")
    lower_2023_mean = mean(rows_2023, "lower_sensitivity_count")
    for row in output:
        high_index = 100.0 * float(row["high_sensitivity_count"]) / high_pre_mean if high_pre_mean else math.nan
        lower_index = 100.0 * float(row["lower_sensitivity_count"]) / lower_pre_mean if lower_pre_mean else math.nan
        high_2023_index = 100.0 * float(row["high_sensitivity_count"]) / high_2023_mean if high_2023_mean else math.nan
        lower_2023_index = 100.0 * float(row["lower_sensitivity_count"]) / lower_2023_mean if lower_2023_mean else math.nan
        row["index_high_pre_mean"] = fmt(high_index, 8)
        row["index_lower_pre_mean"] = fmt(lower_index, 8)
        row["index_diff_pre_mean"] = fmt(high_index - lower_index, 8)
        row["index_high_2023_mean"] = fmt(high_2023_index, 8)
        row["index_lower_2023_mean"] = fmt(lower_2023_index, 8)
        row["index_diff_2023_mean"] = fmt(high_2023_index - lower_2023_index, 8)
    return output


def run_model(
    monthly_rows: list[dict[str, object]],
    outcome: str,
    model_id: str,
    test: str,
    classification_definition: str,
    denominator: str = "",
) -> tuple[list[dict[str, object]], dict[str, object]]:
    included_rows: list[dict[str, object]] = []
    months: list[date] = []
    y: list[float] = []
    for row in monthly_rows:
        raw = row.get(outcome)
        if is_missing_outcome(raw):
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if math.isnan(value) or math.isinf(value):
            continue
        included_rows.append(row)
        months.append(parse_date(str(row["month_start"])))
        y.append(value)
    X, names = build_design(included_rows)
    fit = ols_hac(X, y, HAC_LAG)
    rows = []
    for term, beta, se in zip(names, fit["beta"], fit["se"]):
        p_value = two_sided_normal_pvalue(float(beta), float(se))
        rows.append(
            {
                "model_id": model_id,
                "test": test,
                "outcome": outcome,
                "classification_definition": classification_definition,
                "denominator": denominator,
                "term": term,
                "estimate": fmt(float(beta), 8),
                "std_error": fmt(float(se), 8),
                "statistic": fmt(float(beta) / float(se) if float(se) > 0 else math.nan, 8),
                "p_value": fmt(p_value, 8),
                "ci_low": fmt(float(beta) - 1.96 * float(se), 8),
                "ci_high": fmt(float(beta) + 1.96 * float(se), 8),
                "n_obs": fit["n_obs"],
                "r_squared": fmt(float(fit["r_squared"]), 8),
                "model_f_statistic_classical": fmt(float(fit["model_f_statistic_classical"]), 8),
                "nw_lag": HAC_LAG,
                "inference": "OLS Newey-West HAC",
                "sample_dates": f"{month_label(min(months))} through {month_label(max(months))}",
            }
        )
    fit["names"] = names
    fit["months"] = months
    fit["included_rows"] = included_rows
    fit["X"] = X
    fit["y"] = y
    fit["model_id"] = model_id
    return rows, fit


def run_all_models(monthly_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    specs = [
        (
            "test1_high_sensitivity_count",
            "Test 1",
            "high_sensitivity_count",
            "HIGH_SENSITIVITY",
            "",
        ),
        (
            "test2_high_share_all",
            "Test 2",
            "high_sensitivity_share_all",
            "HIGH_SENSITIVITY",
            "all recorded project starts",
        ),
        (
            "test3_lower_index",
            "Test 3 lower partition",
            "index_lower_pre_mean",
            "LOWER_SENSITIVITY_COMPARISON",
            "own pre-transition monthly mean",
        ),
        (
            "test3_high_index",
            "Test 3 high partition",
            "index_high_pre_mean",
            "HIGH_SENSITIVITY",
            "own pre-transition monthly mean",
        ),
        (
            "test3_high_minus_lower_difference",
            "Test 3 High-minus-Lower partition difference",
            "index_diff_pre_mean",
            "Index_H - Index_L",
            "own pre-transition monthly means",
        ),
    ]
    rows: list[dict[str, object]] = []
    fits: dict[str, dict[str, object]] = {}
    for model_id, test, outcome, definition, denominator in specs:
        model_rows, fit = run_model(monthly_rows, outcome, model_id, test, definition, denominator)
        rows.extend(model_rows)
        fits[model_id] = fit
    return rows, fits


def svg_polyline(points: list[tuple[float, float]], color: str, width: float = 2.2, dash: str = "") -> str:
    if not points:
        return ""
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline fill="none" stroke="{color}" stroke-width="{width}"{dash_attr} points="{pts}"/>'


def make_svg_time_series(
    path: Path,
    title: str,
    series: list[dict[str, object]],
    y_label: str,
    y_min: float | None = None,
    y_max: float | None = None,
    percent_axis: bool = False,
    reference_y: float | None = None,
    annotation: str = "",
    end_month: date = PRIMARY_END,
) -> None:
    width, height = 1080, 540
    ml, mr, mt, mb = 88, 210, 52, 66
    pw, ph = width - ml - mr, height - mt - mb
    months = month_range(PRIMARY_START, end_month)
    values = [float(row["value"]) for row in series if clean(row.get("value"))]
    lo = min(values + [0.0]) if y_min is None else y_min
    hi = max(values + [0.0]) if y_max is None else y_max
    pad = (hi - lo) * 0.08 if hi > lo else 1.0
    lo = lo - pad if y_min is None else y_min
    hi = hi + pad if y_max is None else y_max

    def x(month: date) -> float:
        return ml + months.index(month) / max(len(months) - 1, 1) * pw

    def y(value: float) -> float:
        return mt + (hi - value) / max(hi - lo, 1e-9) * ph

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial, sans-serif" font-size="17" font-weight="700">{title}</text>',
    ]
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        val = lo + frac * (hi - lo)
        yy = y(val)
        label = f"{val * 100:.0f}%" if percent_axis else f"{val:.0f}"
        svg.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{width-mr}" y2="{yy:.1f}" stroke="#dedede"/>')
        svg.append(f'<text x="{ml-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#444">{label}</text>')
    for year in range(PRIMARY_START.year, end_month.year + 1):
        xx = x(date(year, 1, 1))
        svg.append(f'<line x1="{xx:.1f}" y1="{mt}" x2="{xx:.1f}" y2="{height-mb}" stroke="#eeeeee"/>')
        svg.append(f'<text x="{xx:.1f}" y="{height-28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#444">{year}</text>')
    if reference_y is not None and lo <= reference_y <= hi:
        ref_y = y(reference_y)
        svg.append(
            f'<line x1="{ml}" y1="{ref_y:.1f}" x2="{width-mr}" y2="{ref_y:.1f}" '
            'stroke="#777" stroke-width="1.2" stroke-dasharray="2 5"/>'
        )
        svg.append(
            f'<text x="{width-mr-8}" y="{ref_y-5:.1f}" text-anchor="end" '
            'font-family="Arial, sans-serif" font-size="10" fill="#555">100</text>'
        )
    break_x = x(BREAK_MONTH)
    svg.append(f'<line x1="{break_x:.1f}" y1="{mt}" x2="{break_x:.1f}" y2="{height-mb}" stroke="#111" stroke-width="2.2"/>')
    svg.append(f'<text x="{break_x+7:.1f}" y="{mt+16}" font-family="Arial, sans-serif" font-size="11" fill="#111">Jul 2024</text>')

    style = {
        "Observed high": ("#24536b", "", 2.4),
        "Fitted high": ("#24536b", "6 4", 2.4),
        "Observed high/all share": ("#24536b", "", 2.4),
        "Fitted high/all share": ("#24536b", "6 4", 2.4),
        "Observed High": ("#24536b", "", 2.4),
        "Fitted High": ("#24536b", "6 4", 2.4),
        "Observed Lower": ("#b24a38", "", 2.4),
        "Fitted Lower": ("#b24a38", "6 4", 2.4),
        "High": ("#24536b", "", 2.4),
        "Lower": ("#b24a38", "", 2.4),
    }
    by_label = defaultdict(list)
    for row in series:
        if not clean(row.get("value")):
            continue
        by_label[str(row["label"])].append((parse_date(str(row["month_start"])), float(row["value"])))
    legend_y = mt + 8
    for i, (label, values_for_label) in enumerate(by_label.items()):
        color, dash, line_width = style.get(label, ("#24536b", "", 2.2))
        points = [(x(month), y(value)) for month, value in sorted(values_for_label)]
        svg.append(svg_polyline(points, color, line_width, dash))
        if "Observed" in label or label in {"High", "Lower"}:
            for px, py in points:
                svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.7" fill="{color}"/>')
        ly = legend_y + i * 22
        svg.append(f'<line x1="{width-mr+28}" y1="{ly}" x2="{width-mr+58}" y2="{ly}" stroke="{color}" stroke-width="{line_width}"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")
        svg.append(f'<text x="{width-mr+66}" y="{ly+4}" font-family="Arial, sans-serif" font-size="12" fill="#333">{label}</text>')

    svg.append(f'<text x="20" y="{mt+ph/2}" transform="rotate(-90 20 {mt+ph/2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">{y_label}</text>')
    if annotation:
        svg.append(
            f'<text x="{ml+12}" y="{mt+18}" font-family="Arial, sans-serif" '
            f'font-size="12" fill="#222">{annotation}</text>'
        )
    svg.append(f'<text x="{ml}" y="{height-8}" font-family="Arial, sans-serif" font-size="11" fill="#333">Vertical line marks the July 2024 breakpoint. Fitted paths are segmented ITS fits with month-of-year fixed effects.</text>')
    svg.append("</svg>")
    write_text(path, "\n".join(svg))


def figure_rows_from_fit(
    monthly_rows: list[dict[str, object]],
    fit: dict[str, object],
    outcome: str,
    observed_label: str,
    fitted_label: str,
) -> list[dict[str, object]]:
    rows = []
    fitted = list(fit["fitted"])
    fit_months = [month_label(month) for month in fit["months"]]  # type: ignore[index]
    fitted_by_month = dict(zip(fit_months, fitted))
    for row in monthly_rows:
        if row["month"] not in fitted_by_month:
            continue
        rows.append({"month_start": row["month_start"], "value": row[outcome], "label": observed_label})
        rows.append(
            {
                "month_start": row["month_start"],
                "value": fitted_by_month[str(row["month"])],
                "label": fitted_label,
            }
        )
    return rows


def make_figures(
    monthly_rows: list[dict[str, object]],
    fits: dict[str, dict[str, object]],
    regression_rows: list[dict[str, object]],
    out: Outputs,
    end_month: date = PRIMARY_END,
    title_suffix: str = "",
) -> None:
    test1_series = figure_rows_from_fit(
        monthly_rows,
        fits["test1_high_sensitivity_count"],
        "high_sensitivity_count",
        "Observed high",
        "Fitted high",
    )
    make_svg_time_series(
        out.test1_figure,
        f"Test 1: High-Sensitivity Project Entry{title_suffix}",
        test1_series,
        "Monthly high-sensitivity starts",
        y_min=0,
        end_month=end_month,
    )

    test2_series = figure_rows_from_fit(
        monthly_rows,
        fits["test2_high_share_all"],
        "high_sensitivity_share_all",
        "Observed high/all share",
        "Fitted high/all share",
    )
    make_svg_time_series(
        out.test2_figure,
        f"Test 2: High-Sensitivity Share{title_suffix}",
        test2_series,
        "Share of all project starts that are high sensitivity",
        y_min=0,
        y_max=1,
        percent_axis=True,
        end_month=end_month,
    )

    raw_series = []
    for row in monthly_rows:
        raw_series.append({"month_start": row["month_start"], "value": row["high_sensitivity_count"], "label": "High"})
        raw_series.append({"month_start": row["month_start"], "value": row["lower_sensitivity_count"], "label": "Lower"})
    make_svg_time_series(
        out.test3_raw_figure,
        f"Test 3A: Monthly Project Starts by Sensitivity Group{title_suffix}",
        raw_series,
        "Monthly starts",
        y_min=0,
        end_month=end_month,
    )

    index_series = figure_rows_from_fit(
        monthly_rows,
        fits["test3_high_index"],
        "index_high_pre_mean",
        "Observed High",
        "Fitted High",
    )
    index_series.extend(
        figure_rows_from_fit(
            monthly_rows,
            fits["test3_lower_index"],
            "index_lower_pre_mean",
            "Observed Lower",
            "Fitted Lower",
        )
    )
    delta3 = term_row(regression_rows, "test3_high_minus_lower_difference", "TimeAfterJuly2024")
    make_svg_time_series(
        out.test3_indexed_figure,
        f"Test 3: High vs Lower Sensitivity Entry Trajectories{title_suffix}",
        index_series,
        "Entry index (pre-transition monthly mean = 100)",
        y_min=0,
        reference_y=100,
        annotation=f"delta3 = {float(delta3['estimate']):.3f}; p = {float(delta3['p_value']):.3f}",
        end_month=end_month,
    )


def term_row(rows: list[dict[str, object]], model_id: str, term: str) -> dict[str, object]:
    return next(row for row in rows if row["model_id"] == model_id and row["term"] == term)


def compact_coef(rows: list[dict[str, object]], model_id: str) -> str:
    terms = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"]
    lines = ["| Term | Estimate | SE | p-value | 95% CI |", "| --- | ---: | ---: | ---: | ---: |"]
    for term in terms:
        row = term_row(rows, model_id, term)
        lines.append(
            f"| {term} | {float(row['estimate']):.4f} | {float(row['std_error']):.4f} | "
            f"{float(row['p_value']):.4f} | [{float(row['ci_low']):.4f}, {float(row['ci_high']):.4f}] |"
        )
    return "\n".join(lines)


def period_count(rows: list[dict[str, str]], definition: str, period: str = "all") -> int:
    subset = rows if period == "all" else [row for row in rows if row["pre_post_july_2024"] == period]
    return sum(int(row[definition]) for row in subset)


def report_key_line(rows: list[dict[str, object]], model_id: str) -> str:
    values = []
    for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
        row = term_row(rows, model_id, term)
        values.append(f"{term}={float(row['estimate']):.4f} (SE {float(row['std_error']):.4f})")
    return "; ".join(values)


def model_n(regression_rows: list[dict[str, object]], model_id: str) -> int:
    row = next(row for row in regression_rows if row["model_id"] == model_id and row["term"] == "Intercept")
    return int(row["n_obs"])


def linear_combination(fit: dict[str, object], weights: dict[str, float]) -> dict[str, str]:
    names = list(fit["names"])  # type: ignore[arg-type]
    beta = [float(value) for value in fit["beta"]]  # type: ignore[arg-type]
    vcov = fit["vcov"]  # type: ignore[assignment]
    vector = [float(weights.get(str(name), 0.0)) for name in names]
    estimate = sum(weight * value for weight, value in zip(vector, beta))
    variance = 0.0
    for i, wi in enumerate(vector):
        for j, wj in enumerate(vector):
            variance += wi * wj * float(vcov[i][j])  # type: ignore[index]
    std_error = math.sqrt(max(variance, 0.0))
    p_value = two_sided_normal_pvalue(estimate, std_error)
    return {
        "estimate": fmt(estimate, 8),
        "std_error": fmt(std_error, 8),
        "p_value": fmt(p_value, 8),
        "ci_low": fmt(estimate - 1.96 * std_error, 8),
        "ci_high": fmt(estimate + 1.96 * std_error, 8),
    }


def test3_partition_result_rows_for_models(
    fits: dict[str, dict[str, object]],
    lower_model_id: str,
    high_model_id: str,
    difference_model_id: str,
    role: str = "",
) -> list[dict[str, object]]:
    specs = [
        ("lower_pre_slope", lower_model_id, {"Time": 1.0}),
        ("lower_post_slope", lower_model_id, {"Time": 1.0, "TimeAfterJuly2024": 1.0}),
        ("lower_slope_change", lower_model_id, {"TimeAfterJuly2024": 1.0}),
        ("high_pre_slope", high_model_id, {"Time": 1.0}),
        ("high_post_slope", high_model_id, {"Time": 1.0, "TimeAfterJuly2024": 1.0}),
        ("high_slope_change", high_model_id, {"TimeAfterJuly2024": 1.0}),
        ("differential_level_change_delta2", difference_model_id, {"PostJuly2024": 1.0}),
        ("differential_slope_change_delta3", difference_model_id, {"TimeAfterJuly2024": 1.0}),
    ]
    rows = []
    for quantity, model_id, weights in specs:
        row = {"quantity": quantity}
        if role:
            row["role"] = role
        row.update(linear_combination(fits[model_id], weights))
        rows.append(row)
    return rows


def test3_partition_result_rows(fits: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    return test3_partition_result_rows_for_models(
        fits,
        "test3_lower_index",
        "test3_high_index",
        "test3_high_minus_lower_difference",
    )


def with_raw_count_difference(monthly_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            **row,
            "raw_count_diff_high_minus_lower": int(row["high_sensitivity_count"])
            - int(row["lower_sensitivity_count"]),
        }
        for row in monthly_rows
    ]


def run_test3_raw_partition_models(
    monthly_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    raw_rows = with_raw_count_difference(monthly_rows)
    specs = [
        (
            "test3_raw_lower_count",
            "Test 3 raw-count robustness lower partition",
            "lower_sensitivity_count",
            "LOWER_SENSITIVITY_COMPARISON",
            "ROBUSTNESS ONLY",
        ),
        (
            "test3_raw_high_count",
            "Test 3 raw-count robustness high partition",
            "high_sensitivity_count",
            "HIGH_SENSITIVITY",
            "ROBUSTNESS ONLY",
        ),
        (
            "test3_raw_high_minus_lower_difference",
            "Test 3 raw-count robustness High-minus-Lower difference",
            "raw_count_diff_high_minus_lower",
            "raw count High - Lower",
            "ROBUSTNESS ONLY",
        ),
    ]
    rows: list[dict[str, object]] = []
    fits: dict[str, dict[str, object]] = {}
    for model_id, test, outcome, definition, denominator in specs:
        model_rows, fit = run_model(raw_rows, outcome, model_id, test, definition, denominator)
        rows.extend(model_rows)
        fits[model_id] = fit
    return rows, fits


def test3_raw_partition_result_rows(fits: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    return test3_partition_result_rows_for_models(
        fits,
        "test3_raw_lower_count",
        "test3_raw_high_count",
        "test3_raw_high_minus_lower_difference",
        role="ROBUSTNESS ONLY",
    )


def build_test3_stacked_rows(monthly_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for row in monthly_rows:
        common = {
            "month": row["month"],
            "month_start": row["month_start"],
            "time": row["time"],
            "post_july2024": row["post_july2024"],
            "time_after_july2024": row["time_after_july2024"],
            "month_of_year": row["month_of_year"],
        }
        rows.append(
            {
                **common,
                "group": "High",
                "high_group": 1,
                "raw_count": row["high_sensitivity_count"],
                "entry_index_pre_mean": row["index_high_pre_mean"],
            }
        )
        rows.append(
            {
                **common,
                "group": "Lower",
                "high_group": 0,
                "raw_count": row["lower_sensitivity_count"],
                "entry_index_pre_mean": row["index_lower_pre_mean"],
            }
        )
    return rows


def partition_result_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["quantity"]: row for row in rows}


def partition_report_table(rows: list[dict[str, str]]) -> str:
    by_quantity = partition_result_map(rows)
    labels = [
        ("Lower pre slope", "lower_pre_slope"),
        ("Lower post slope", "lower_post_slope"),
        ("Lower slope change", "lower_slope_change"),
        ("High pre slope", "high_pre_slope"),
        ("High post slope", "high_post_slope"),
        ("High slope change", "high_slope_change"),
        ("Differential immediate change \\(\\delta_2\\)", "differential_level_change_delta2"),
        ("**Differential slope change \\(\\delta_3\\)**", "differential_slope_change_delta3"),
    ]
    lines = [
        "| Quantity | Estimate | SE / p-value |",
        "| --- | ---: | ---: |",
    ]
    for label, quantity in labels:
        row = by_quantity[quantity]
        lines.append(
            f"| {label} | {float(row['estimate']):.4f} | "
            f"{float(row['std_error']):.4f} / {float(row['p_value']):.4f} |"
        )
    return "\n".join(lines)


def result_values(row: dict[str, object]) -> dict[str, str]:
    return {
        "estimate": clean(row.get("estimate")),
        "std_error": clean(row.get("std_error")),
        "p_value": clean(row.get("p_value")),
        "ci_low": clean(row.get("ci_low")),
        "ci_high": clean(row.get("ci_high")),
    }


def fit_result(
    regression_rows: list[dict[str, object]],
    model_id: str,
    term: str,
) -> dict[str, str]:
    return result_values(term_row(regression_rows, model_id, term))


def comparison_row(
    test: str,
    quantity: str,
    old: dict[str, str],
    new: dict[str, str],
) -> dict[str, object]:
    return {
        "test": test,
        "quantity": quantity,
        "through_2025_12_estimate": old["estimate"],
        "through_2025_12_std_error": old["std_error"],
        "through_2025_12_p_value": old["p_value"],
        "through_2025_12_ci_low": old["ci_low"],
        "through_2025_12_ci_high": old["ci_high"],
        "through_2026_06_estimate": new["estimate"],
        "through_2026_06_std_error": new["std_error"],
        "through_2026_06_p_value": new["p_value"],
        "through_2026_06_ci_low": new["ci_low"],
        "through_2026_06_ci_high": new["ci_high"],
        "change_estimate": fmt(float(new["estimate"]) - float(old["estimate"]), 8),
    }


def window_comparison_rows(
    baseline_regression_rows: list[dict[str, object]],
    baseline_fits: dict[str, dict[str, object]],
    baseline_partition_rows: list[dict[str, object]],
    extended_regression_rows: list[dict[str, object]],
    extended_fits: dict[str, dict[str, object]],
    extended_partition_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    baseline_partition = partition_result_map([{key: str(value) for key, value in row.items()} for row in baseline_partition_rows])
    extended_partition = partition_result_map([{key: str(value) for key, value in row.items()} for row in extended_partition_rows])
    rows = []
    for test, model_id in [
        ("Test 1", "test1_high_sensitivity_count"),
        ("Test 2", "test2_high_share_all"),
    ]:
        for quantity, term in [("beta1", "Time"), ("beta2", "PostJuly2024"), ("beta3", "TimeAfterJuly2024")]:
            rows.append(
                comparison_row(
                    test,
                    quantity,
                    fit_result(baseline_regression_rows, model_id, term),
                    fit_result(extended_regression_rows, model_id, term),
                )
            )
        rows.append(
            comparison_row(
                test,
                "post slope",
                linear_combination(baseline_fits[model_id], {"Time": 1.0, "TimeAfterJuly2024": 1.0}),
                linear_combination(extended_fits[model_id], {"Time": 1.0, "TimeAfterJuly2024": 1.0}),
            )
        )
    for quantity, label in [
        ("high_pre_slope", "High pre slope"),
        ("high_post_slope", "High post slope"),
        ("high_slope_change", "High slope change"),
        ("lower_pre_slope", "Lower pre slope"),
        ("lower_post_slope", "Lower post slope"),
        ("lower_slope_change", "Lower slope change"),
        ("differential_level_change_delta2", "delta2"),
        ("differential_slope_change_delta3", "delta3"),
    ]:
        rows.append(comparison_row("Test 3", label, baseline_partition[quantity], extended_partition[quantity]))
    return rows


def audit_2026h1_rows(monthly_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    wanted = {month_label(month) for month in month_range(date(2026, 1, 1), EXTENDED_END)}
    rows = []
    for row in monthly_rows:
        if row["month"] not in wanted:
            continue
        all_count = int(row["all_count"])
        high = int(row["high_sensitivity_count"])
        lower = int(row["lower_sensitivity_count"])
        if high + lower != all_count:
            raise AssertionError(f"HIGH/LOWER monthly complement mismatch in {row['month']}")
        rows.append(
            {
                "month": row["month"],
                "all_count": all_count,
                "high_sensitivity_count": high,
                "lower_sensitivity_count": lower,
                "high_sensitivity_share_all": row["high_sensitivity_share_all"],
            }
        )
    if len(rows) != 6:
        raise AssertionError(f"expected six 2026 H1 audit rows; found {len(rows)}")
    return rows


def sum_column(rows: list[dict[str, object]], column: str) -> int:
    return sum(int(row[column]) for row in rows)


def report_number(value: object, digits: int = 4) -> str:
    text = clean(value)
    if not text:
        return ""
    return f"{float(text):.{digits}f}"


def report_ci(row: dict[str, object], digits: int = 4) -> str:
    return f"[{report_number(row['ci_low'], digits)}, {report_number(row['ci_high'], digits)}]"


def comparison_lookup(rows: list[dict[str, object]], test: str, quantity: str) -> dict[str, object]:
    return next(row for row in rows if row["test"] == test and row["quantity"] == quantity)


def comparison_markdown_table(rows: list[dict[str, object]], test: str) -> str:
    selected = [row for row in rows if row["test"] == test]
    lines = [
        "| Quantity | Through 2025-12 | Through 2026-06 | Change |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in selected:
        lines.append(
            f"| {row['quantity']} | {report_number(row['through_2025_12_estimate'])} "
            f"(SE {report_number(row['through_2025_12_std_error'])}, p {report_number(row['through_2025_12_p_value'])}) | "
            f"{report_number(row['through_2026_06_estimate'])} "
            f"(SE {report_number(row['through_2026_06_std_error'])}, p {report_number(row['through_2026_06_p_value'])}) | "
            f"{report_number(row['change_estimate'])} |"
        )
    return "\n".join(lines)


def zero_month_preservation_check(
    monthly_rows: list[dict[str, object]],
    regression_rows: list[dict[str, object]],
) -> bool:
    by_month = {str(row["month"]): row for row in monthly_rows}
    required_n = {
        "test1_high_sensitivity_count": 84,
        "test3_lower_index": 84,
        "test3_high_index": 84,
        "test3_high_minus_lower_difference": 84,
    }
    return (
        by_month.get("2024-07", {}).get("time_after_july2024") in {0, "0"}
        and by_month.get("2024-08", {}).get("time_after_july2024") in {1, "1"}
        and all(model_n(regression_rows, model_id) == expected for model_id, expected in required_n.items())
    )


def write_stata_do(out: Outputs) -> None:
    text = r'''version 18.0
clear all
set more off
capture log close _all

args input_csv log_file table_csv tmp_dta end_ym

if "`input_csv'" == "" local input_csv "../data/project_entry2_monthly.csv"
if "`log_file'" == "" local log_file "../reports/project_entry2_stata_full.log"
if "`table_csv'" == "" local table_csv "../reports/project_entry2_stata_regression_table.csv"
if "`tmp_dta'" == "" local tmp_dta "../data/project_entry2_stata_results_tmp.dta"
if "`end_ym'" == "" local end_ym "2025-12"

log using "`log_file'", text replace

import delimited "`input_csv'", clear
gen mdate = monthly(month, "YM")
format mdate %tm
local end_mdate = monthly("`end_ym'", "YM")
keep if mdate <= `end_mdate'
tsset mdate
gen byte month_of_year_stata = month(dofm(mdate))

tempname handle
postfile `handle' str45 model_id str32 outcome str32 term double estimate std_error statistic p_value ci_low ci_high n_obs r_squared using "`tmp_dta'", replace
global PROJECT_ENTRY2_POST_HANDLE "`handle'"

program define _post_newey_rows
    args model_id outcome
    local terms "_cons time post_july2024 time_after_july2024"
    local r2 = .
    capture local r2 = e(r2)
    foreach term of local terms {
        local b = _b[`term']
        local se = _se[`term']
        local t = `b' / `se'
        local p = 2 * ttail(e(df_r), abs(`t'))
        local lo = `b' - invttail(e(df_r), 0.025) * `se'
        local hi = `b' + invttail(e(df_r), 0.025) * `se'
        post $PROJECT_ENTRY2_POST_HANDLE ("`model_id'") ("`outcome'") ("`term'") (`b') (`se') (`t') (`p') (`lo') (`hi') (e(N)) (`r2')
    }
    post $PROJECT_ENTRY2_POST_HANDLE ("`model_id'") ("`outcome'") ("monthFE") (.) (.) (.) (.) (.) (.) (e(N)) (`r2')
end

newey high_sensitivity_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test1_high_sensitivity_count high_sensitivity_count

newey high_sensitivity_share_all time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test2_high_share_all high_sensitivity_share_all
lincom time + time_after_july2024

* Test 3A: Lower group
newey index_lower_pre_mean ///
    time post_july2024 time_after_july2024 ///
    i.month_of_year_stata, lag(3)
_post_newey_rows test3_lower_index index_lower_pre_mean
lincom time + time_after_july2024

* Test 3B: High group
newey index_high_pre_mean ///
    time post_july2024 time_after_july2024 ///
    i.month_of_year_stata, lag(3)
_post_newey_rows test3_high_index index_high_pre_mean
lincom time + time_after_july2024

* Test 3C: High minus Lower
newey index_diff_pre_mean ///
    time post_july2024 time_after_july2024 ///
    i.month_of_year_stata, lag(3)
_post_newey_rows test3_high_minus_lower_difference index_diff_pre_mean
test time_after_july2024 = 0

postclose `handle'
macro drop PROJECT_ENTRY2_POST_HANDLE
use "`tmp_dta'", clear
gen str24 stata_status = "STATA_EXECUTED"
export delimited "`table_csv'", replace

log close _all
'''
    write_text(out.stata_do, text)


def stata_arg_path(path: Path) -> str:
    return os.path.relpath(path, SCRIPT_DIR)


def run_stata_if_available(
    out: Outputs,
    regression_rows: list[dict[str, object]],
    end_month: date = PRIMARY_END,
) -> str:
    write_stata_do(out)
    exe = None
    for candidate in ["stata-mp", "stata-se", "stata"]:
        found = shutil.which(candidate)
        if found:
            exe = found
            break
    if not exe:
        write_text(
            out.stata_log,
            "STATA_NOT_AVAILABLE_ON_RUNNER\n\n"
            "Checked executables: stata-mp, stata-se, stata.\n"
            f"The committed project_entry2_its.do file and {stata_arg_path(out.monthly)} are Stata-ready. "
            f"Python estimates are saved separately in {stata_arg_path(out.regression_results)}. "
            f"Requested Stata end month: {month_label(end_month)}.\n",
        )
        write_csv(
            out.stata_table,
            [
                {
                    "stata_status": "STATA_NOT_AVAILABLE_ON_RUNNER",
                    "model_id": "",
                    "outcome": "",
                    "term": "",
                    "estimate": "",
                    "std_error": "",
                    "note": "No licensed Stata executable found on this runner; no Stata estimates fabricated.",
                }
            ],
            ["stata_status", "model_id", "outcome", "term", "estimate", "std_error", "note"],
        )
        write_csv(
            out.replication_check,
            [
                {
                    "model_id": "all",
                    "term": "",
                    "python_estimate": "",
                    "stata_estimate": "",
                    "absolute_difference": "",
                    "tolerance": "",
                    "status": "STATA_NOT_AVAILABLE_ON_RUNNER",
                }
            ],
            ["model_id", "term", "python_estimate", "stata_estimate", "absolute_difference", "tolerance", "status"],
        )
        return "STATA_NOT_AVAILABLE_ON_RUNNER"

    result = subprocess.run(
        [
            exe,
            "-b",
            "do",
            str(out.stata_do.name),
            stata_arg_path(out.monthly),
            stata_arg_path(out.stata_log),
            stata_arg_path(out.stata_table),
            stata_arg_path(out.stata_tmp),
            month_label(end_month),
        ],
        cwd=SCRIPT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        write_text(
            out.stata_log,
            "STATA_EXECUTION_FAILED\n\n"
            f"Command: {exe} -b do {out.stata_do.name}\n\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}\n",
        )
        return "STATA_EXECUTION_FAILED"

    return write_replication_check(out, regression_rows)


def write_replication_check(out: Outputs, regression_rows: list[dict[str, object]]) -> str:
    if not out.stata_table.exists():
        write_csv(
            out.replication_check,
            [
                {
                    "model_id": "all",
                    "term": "",
                    "python_estimate": "",
                    "stata_estimate": "",
                    "absolute_difference": "",
                    "tolerance": "",
                    "status": "STATA_TABLE_MISSING",
                }
            ],
            ["model_id", "term", "python_estimate", "stata_estimate", "absolute_difference", "tolerance", "status"],
        )
        return "STATA_TABLE_MISSING"

    stata_rows = read_csv(out.stata_table)
    if stata_rows and stata_rows[0].get("stata_status") == "STATA_NOT_AVAILABLE_ON_RUNNER":
        write_csv(
            out.replication_check,
            [
                {
                    "model_id": "all",
                    "term": "",
                    "python_estimate": "",
                    "stata_estimate": "",
                    "absolute_difference": "",
                    "tolerance": "",
                    "status": "STATA_NOT_AVAILABLE_ON_RUNNER",
                }
            ],
            ["model_id", "term", "python_estimate", "stata_estimate", "absolute_difference", "tolerance", "status"],
        )
        return "STATA_NOT_AVAILABLE_ON_RUNNER"

    term_map = {
        "_cons": "Intercept",
        "time": "Time",
        "post_july2024": "PostJuly2024",
        "time_after_july2024": "TimeAfterJuly2024",
    }
    python_by_key = {
        (str(row["model_id"]), str(row["term"])): row
        for row in regression_rows
        if row["term"] in {"Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"}
    }
    check_rows = []
    tolerance = 1e-6
    for srow in stata_rows:
        mapped = term_map.get(srow.get("term", ""))
        if not mapped:
            continue
        key = (srow["model_id"], mapped)
        prow = python_by_key.get(key)
        if not prow:
            continue
        p = float(prow["estimate"])
        s = float(srow["estimate"])
        diff = abs(p - s)
        check_rows.append(
            {
                "model_id": srow["model_id"],
                "term": mapped,
                "python_estimate": fmt(p, 10),
                "stata_estimate": fmt(s, 10),
                "absolute_difference": fmt(diff, 10),
                "tolerance": tolerance,
                "status": "PASS" if diff <= tolerance else "CHECK",
            }
        )
    status = "PASS" if check_rows and all(row["status"] == "PASS" for row in check_rows) else "CHECK"
    write_csv(
        out.replication_check,
        check_rows
        or [
            {
                "model_id": "all",
                "term": "",
                "python_estimate": "",
                "stata_estimate": "",
                "absolute_difference": "",
                "tolerance": tolerance,
                "status": "NO_COMPARABLE_STATA_ROWS",
            }
        ],
        ["model_id", "term", "python_estimate", "stata_estimate", "absolute_difference", "tolerance", "status"],
    )
    return status


def stata_term_name(term: object) -> str:
    text = clean(term)
    if text == "Intercept":
        return "_cons"
    if text == "Time":
        return "time"
    if text == "PostJuly2024":
        return "post_july2024"
    if text == "TimeAfterJuly2024":
        return "time_after_july2024"
    match = re_match_month_fe(text)
    return f"{int(match):d}.month_of_year" if match else text


def re_match_month_fe(term: str) -> str:
    if len(term) == 8 and term.startswith("month_") and term[-2:].isdigit():
        return term[-2:]
    return ""


def stata_num(value: object, digits: int = 7) -> str:
    text = clean(value)
    if not text:
        return "."
    try:
        number = float(text)
    except ValueError:
        return text
    if math.isnan(number) or math.isinf(number):
        return "."
    if abs(number) < 1 and number != 0:
        rendered = f"{number:.{digits}f}"
        rendered = rendered.replace("-0.", "-.", 1).replace("0.", ".", 1)
        return rendered.rstrip("0").rstrip(".")
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def stata_pvalue(value: object) -> str:
    text = clean(value)
    if not text:
        return "."
    try:
        number = float(text)
    except ValueError:
        return text
    if math.isnan(number) or math.isinf(number):
        return "."
    return "0.000" if number < 0.0005 else f"{number:.3f}"


def write_stata_style_python_output(out: Outputs, regression_rows: list[dict[str, object]]) -> None:
    commands = {
        "test1_high_sensitivity_count": (
            "newey high_sensitivity_count time post_july2024 "
            "time_after_july2024 i.month_of_year_stata, lag(3)"
        ),
        "test2_high_share_all": (
            "newey high_sensitivity_share_all time post_july2024 "
            "time_after_july2024 i.month_of_year_stata, lag(3)"
        ),
        "test3_lower_index": (
            "newey index_lower_pre_mean time post_july2024 "
            "time_after_july2024 i.month_of_year_stata, lag(3)"
        ),
        "test3_high_index": (
            "newey index_high_pre_mean time post_july2024 "
            "time_after_july2024 i.month_of_year_stata, lag(3)"
        ),
        "test3_high_minus_lower_difference": (
            "newey index_diff_pre_mean time post_july2024 "
            "time_after_july2024 i.month_of_year_stata, lag(3)"
        ),
    }
    order = list(dict.fromkeys(str(row["model_id"]) for row in regression_rows))
    rows_by_model: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in regression_rows:
        rows_by_model[str(row["model_id"])].append(row)
    variable_width = 32
    separator = "-" * variable_width + "-+----------------------------------------------------------------"

    lines = [
        "Project Entry2 Stata-Style Regression Results",
        "",
        f"Source estimates: {stata_arg_path(out.regression_results)}",
        "Estimator: OLS with Newey-West HAC standard errors, lag(3).",
        "Note: no licensed Stata executable was available locally; this is a Stata-style rendering of the Python HAC estimates.",
        "P-values and confidence intervals use the normal approximation used by the Python pipeline.",
        "",
    ]
    for model_id in order:
        model_rows = rows_by_model[model_id]
        display_rows = [
            row
            for row in model_rows
            if clean(row["term"]) in {"Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"}
        ]
        header = model_rows[0]
        n_obs = int(header["n_obs"])
        k_params = len(model_rows)
        df_resid = n_obs - k_params
        f_stat = stata_num(header.get("model_f_statistic_classical"), 4)
        r2 = stata_num(header.get("r_squared"), 4)
        outcome = clean(header.get("outcome"))
        sample_dates = clean(header.get("sample_dates"))
        title = f"{model_id}: {clean(header.get('test'))}"
        lines.extend(
            [
                title,
                f". {commands.get(model_id, 'newey ' + outcome + ' ... , lag(3)')}",
                "",
                "Regression with Newey-West standard errors".ljust(52)
                + f"Number of obs     = {n_obs:>10d}",
                f"Maximum lag = {HAC_LAG}".ljust(52)
                + f"F({k_params - 1:>2d}, {df_resid:>3d})        = {f_stat:>10}",
                "HAC kernel: Bartlett".ljust(52) + "Prob > F          =          .",
                f"Sample dates: {sample_dates}".ljust(52) + f"R-squared         = {r2:>10}",
                "",
                separator,
                f"{outcome[:variable_width]:>{variable_width}} |             Newey-West",
                f"{'':>{variable_width}} | Coefficient  std. err.      z    P>|z|     [95% conf. interval]",
                separator,
            ]
        )
        for row in display_rows:
            term = stata_term_name(row["term"])
            coef = stata_num(row["estimate"])
            se = stata_num(row["std_error"])
            z_stat = stata_num(row["statistic"], 2)
            p_value = stata_pvalue(row["p_value"])
            lo = stata_num(row["ci_low"])
            hi = stata_num(row["ci_high"])
            lines.append(
                f"{term[:variable_width]:>{variable_width}} | "
                f"{coef:>11} {se:>10} {z_stat:>7} {p_value:>8} {lo:>12} {hi:>12}"
            )
        lines.extend([separator, "monthFE = Yes", ""])

    write_text(out.stata_style_python_table, "\n".join(lines))


def write_reports(
    classification_rows: list[dict[str, str]],
    monthly_rows: list[dict[str, object]],
    regression_rows: list[dict[str, object]],
    stata_status: str,
    out: Outputs,
) -> None:
    counts = {row["definition"]: row for row in read_csv(classification_builder.Outputs().classification_counts) if row["period"] == "all"}
    pre_counts = {row["definition"]: row for row in read_csv(classification_builder.Outputs().classification_counts) if row["period"] == "pre_july_2024"}
    post_counts = {row["definition"]: row for row in read_csv(classification_builder.Outputs().classification_counts) if row["period"] == "post_july_2024"}
    overlap_rows = read_csv(classification_builder.Outputs().classification_overlap)
    overlap_by_channel = {row["channel"]: row for row in overlap_rows}
    high_n = int(counts["HIGH_SENSITIVITY"]["count"])
    lower_n = int(counts["LOWER_SENSITIVITY_COMPARISON"]["count"])
    low_n = int(counts["LOW_STRICT"]["count"])
    wes_n = int(counts["hs_wes_wgs_sequence"]["count"])
    direct_s3_n = int(counts["hs_s3_direct"]["count"])
    text_s3_n = int(counts["hs_s3_text"]["count"])
    pre_high = pre_counts["HIGH_SENSITIVITY"]["count"]
    post_high = post_counts["HIGH_SENSITIVITY"]["count"]
    pre_lower = pre_counts["LOWER_SENSITIVITY_COMPARISON"]["count"]
    post_lower = post_counts["LOWER_SENSITIVITY_COMPARISON"]["count"]
    zero_check = "PASS" if zero_month_preservation_check(monthly_rows, regression_rows) else "FAIL"
    test3_partition_rows = read_csv(out.test3_partition_results)
    test3_partition = partition_result_map(test3_partition_rows)
    delta3_partition = test3_partition["differential_slope_change_delta3"]
    if float(delta3_partition["estimate"]) > 0 and float(delta3_partition["p_value"]) < 0.05:
        test3_bottom_line = "High trajectory strengthened significantly more than Lower."
    else:
        test3_bottom_line = "No statistically detectable differential strengthening of High relative to Lower."

    t1 = report_key_line(regression_rows, "test1_high_sensitivity_count")
    t2 = report_key_line(regression_rows, "test2_high_share_all")

    channel_lines = []
    for label in ["WES/WGS_SEQUENCE", "DIRECT_S3_FIELD_LINK", "S3_DERIVED_APPLICATION_TEXT"]:
        row = overlap_by_channel[label]
        channel_lines.append(
            f"| {label} | {int(row['N']):,} | {int(row['overlap'] or 0):,} | "
            f"{int(row['net_additions']):,} | {int(row['pre_N']):,} | {int(row['post_N']):,} |"
        )

    write_text(
        out.measurement_note,
        f"""# Project Entry2 Measurement Note

## Sources

The project universe is `data/intermediate/timing_feasibility/timing_working_research_project_universe.csv`, which contains 6,935 projects with exact public Start dates.

Existing control-expansion evidence comes from `data/intermediate/control_expansion/stage3_control_expansion_project_review.csv` and its evidence dictionary. Expansion layer is retained as audit metadata only; it is not itself a high-sensitivity definition.

Field-tier evidence comes from UKB Schema 1 (`{classification_builder.SCHEMA1_URL}`) and cached public field pages under `data/source_snapshots/field_pages/`.

## Field-Tier Interpretation

Current Schema 1 exposes `cost_do`, `cost_on`, and `cost_sc` columns rather than one literal `tier` column. This pipeline reconstructs tier tokens from those columns: positive `cost_do` becomes `d#`, positive `cost_on` becomes `o#`, and positive `cost_sc` becomes `s#`. The parser validation case is field 25749, which reconstructs as `o2 s3` and links to applications 17689 and 22783.

`s3` enters high sensitivity in two ways: direct application-field links and high-precision application-text terms derived from the 199 s3 Schema 1 fields. `o2` is retained for audit; o2 alone is not part of the primary high-sensitivity definition.

## High And Lower Groups

`HIGH_SENSITIVITY` is the union of explicit WES/WGS or sequence-product evidence, direct s3 field links, and s3-derived application text. `LOWER_SENSITIVITY_COMPARISON` is the exhaustive complement. Complement status means no identified high evidence under the observable proxy, not proof that every project is low-risk.

## Interpretation Limits

The public Start date is not observed application submission, approval, first RAP access, or first data-use timing. Field tier and text evidence are sensitivity/granularity proxies, not observed leakage risk. The ITS outputs are descriptive and comparative; they should not be described as causal RAP treatment effects.
""",
    )

    write_text(
        out.reading_guide,
        """# Project Entry2 Reading Guide

Start with `reports/project_entry2_results.md`, then inspect `reports/project_entry2_stata_style_regression_results.txt`, `data/project_high_sensitivity_classification.csv`, `data/project_entry2_monthly.csv`, and `data/project_entry2_regression_results.csv`.

The real Stata runner file is `scripts/project_entry2_its.do`. If no licensed Stata executable was available locally, `reports/project_entry2_stata_full.log` explicitly says `STATA_NOT_AVAILABLE_ON_RUNNER`. The text file `reports/project_entry2_stata_style_regression_results.txt` is a Stata-style rendering of the Python Newey-West estimates, not fabricated Stata execution.
""",
    )

    write_text(
        PACKAGE / "README.md",
        """# Project Entry2

Independent high-sensitivity project-entry ITS pipeline.

Run:

```bash
python3 analyses/interrupted_time_series/project_entry2/scripts/build_high_sensitivity_classification.py
python3 analyses/interrupted_time_series/project_entry2/scripts/project_entry2_analysis.py --skip-classification
```

Primary window: 2019-01 through 2025-12. Breakpoint: July 2024, with `time_after_july2024 = 0` in July 2024, 1 in August 2024, and so on.
""",
    )

    results = f"""# Project Entry2 Results

## A. What Is High Sensitivity?

Primary high sensitivity is `HIGH_SENSITIVITY`: explicit WES/WGS or sequence-product evidence, direct application-field links to `s3` fields, or high-precision application text derived from the 199 Schema 1 `s3` fields. It is a proxy for higher-granularity or more sensitive data use, not observed leakage risk.

Project counts:

| Definition | N |
| --- | ---: |
| HIGH_SENSITIVITY | {high_n:,} |
| LOWER_SENSITIVITY_COMPARISON | {lower_n:,} |
| hs_wes_wgs_sequence | {wes_n:,} |
| hs_s3_direct | {direct_s3_n:,} |
| hs_s3_text | {text_s3_n:,} |
| LOW_STRICT | {low_n:,} |

Evidence-channel overlap and net additions:

| Channel | N | Overlap with previous channels | Net additions | Pre N | Post N |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(channel_lines)}

Pre/post counts use the exact policy date 2024-07-05 at the project level: HIGH_SENSITIVITY is {pre_high} pre-July-2024 and {post_high} post-July-2024; LOWER_SENSITIVITY_COMPARISON is {pre_lower} pre-July-2024 and {post_lower} post-July-2024.

The lower comparison is the exhaustive complement, meaning no identified high evidence under the observable proxy, not proof that every complement project is low-risk.

The full audit files are `classification_counts.csv`, `classification_overlap.csv`, `s3_field_dictionary.csv`, `s3_application_keyword_dictionary.csv`, `s3_text_audit_examples.csv`, `field_tier_distribution.csv`, and `application_field_tier_links.csv`.

## B. Test 1 - High-Sensitivity Entry Count

Question: did the absolute number of high-sensitivity project starts change around/after July 2024?

Primary HIGH_SENSITIVITY:

{compact_coef(regression_rows, "test1_high_sensitivity_count")}

Key terms: {t1}.

## C. Test 2 - High-Sensitivity Share

Question: did the composition of project entry shift toward high-sensitivity projects?

Primary denominator is all recorded project starts because HIGH and LOWER are exhaustive. If `N_All,t=0`, the share is missing but calendar time is preserved.

{compact_coef(regression_rows, "test2_high_share_all")}

Key terms: {t2}.

## D. Test 3 - High Vs Lower Partition Interaction

**Test 3 asks whether the post-transition change in entry trajectory differs between the high-sensitivity and lower-sensitivity partitions.**

The 6,935 projects are partitioned into `HIGH_SENSITIVITY` and the exhaustive `LOWER_SENSITIVITY_COMPARISON`. For each group, monthly entry is normalized to that group's own pre-transition monthly mean:

$$
Y_{{H,t}} = 100 N_{{H,t}} / \\overline{{N}}_{{H,pre}},
\\quad
Y_{{L,t}} = 100 N_{{L,t}} / \\overline{{N}}_{{L,pre}}.
$$

The conceptual model is the stacked partition interaction model, with Lower as the omitted group:

$$
\\begin{{aligned}}
Y_{{g,t}} ={{}}& \\beta_0 + \\beta_1 Time_t + \\beta_2 Post_t + \\beta_3 TimeAfter_t \\\\
&+ \\delta_0 High_g
+ \\delta_1 High_g \\times Time_t
+ \\delta_2 High_g \\times Post_t \\\\
&+ \\delta_3 High_g \\times TimeAfter_t
+ MonthFE
+ High_g \\times MonthFE
+ \\epsilon_{{g,t}}.
\\end{{aligned}}
$$

Coefficient translation:

Lower-sensitivity group:

$$
PreSlope_L = \\beta_1, \\quad
PostSlope_L = \\beta_1 + \\beta_3, \\quad
SlopeChange_L = \\beta_3.
$$

High-sensitivity group:

$$
PreSlope_H = \\beta_1 + \\delta_1, \\quad
PostSlope_H = \\beta_1 + \\delta_1 + \\beta_3 + \\delta_3, \\quad
SlopeChange_H = \\beta_3 + \\delta_3.
$$

Therefore, the primary Test 3 coefficient is:

$$
\\delta_3 = SlopeChange_H - SlopeChange_L.
$$

\\(\\delta_3 > 0\\) means that the post-transition trajectory strengthened more for high-sensitivity projects than for lower-sensitivity projects, relative to each group's own pre-transition trajectory. \\(\\delta_2\\) is the High-vs-Lower differential immediate level change at July 2024. The main hypothesis is \\(H_0: \\delta_3 = 0\\); the secondary hypothesis is \\(H_0: \\delta_2 = 0\\).

For Newey-West inference, the pipeline does not run built-in Stata `newey` on the 168-row stacked transparency file because that file has two observations per calendar month. Instead it runs three monthly ITS regressions on the same 84 months and design matrix: Lower index, High index, and \\(D_t = Y_{{H,t}} - Y_{{L,t}}\\). Because the High and Lower regressions use the same design matrix, the difference-series coefficients equal the High-minus-Lower interaction coefficients: \\(\\delta_j = \\beta_{{jH}} - \\beta_{{jL}}\\). The difference regression is therefore the Newey-West implementation of the interaction comparison, and it supplies the formal standard error for \\(\\delta_3\\) while incorporating contemporaneous covariance between the High and Lower series.

{partition_report_table(test3_partition_rows)}

{test3_bottom_line}

Test 3 model outputs:

{compact_coef(regression_rows, "test3_lower_index")}

{compact_coef(regression_rows, "test3_high_index")}

{compact_coef(regression_rows, "test3_high_minus_lower_difference")}

The stacked transparency dataset is `data/project_entry2_test3_stacked.csv`. It has 168 group-month rows and is not used for the built-in Stata `newey` call.

Zero-month preservation check: {zero_check}. Test 3 Lower index, Test 3 High index, and Test 3 High-minus-Lower difference each retain 84 monthly observations.

## E. Measurement Limitations

Start date is not application submission, approval, or first RAP access. Current Application x Field links may reflect later amendments. Field tier is a sensitivity/granularity proxy, not observed leakage risk. The design is descriptive ITS/comparative ITS, not causal DID.

## Output Files

- `data/project_high_sensitivity_classification.csv`
- `data/application_field_tier_links.csv`
- `data/field_tier_distribution.csv`
- `data/classification_counts.csv`
- `data/classification_overlap.csv`
- `data/project_entry2_monthly.csv`
- `data/project_entry2_regression_results.csv`
- `data/project_entry2_test3_stacked.csv`
- `data/project_entry2_test3_partition_results.csv`
- `data/stata_python_replication_check.csv`
- `figures/figure_test1_high_sensitivity_entry.svg`
- `figures/figure_test2_high_sensitivity_share.svg`
- `figures/figure_test3_high_vs_low_raw.svg`
- `figures/figure_test3_high_vs_low_indexed.svg`
- `reports/project_entry2_stata_style_regression_results.txt`
- `reports/project_entry2_stata_full.log`
- `reports/project_entry2_stata_regression_table.csv`

Stata status: `{stata_status}`.
"""
    write_text(out.results_report, results)


def audit_markdown_table(rows: list[dict[str, object]]) -> str:
    lines = [
        "| Month | All starts | High | Lower | High share |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        share = clean(row["high_sensitivity_share_all"])
        share_text = f"{float(share):.4f}" if share else ""
        lines.append(
            f"| {row['month']} | {int(row['all_count']):,} | "
            f"{int(row['high_sensitivity_count']):,} | {int(row['lower_sensitivity_count']):,} | "
            f"{share_text} |"
        )
    return "\n".join(lines)


def slope_summary_table(rows: list[dict[str, object]]) -> str:
    lines = [
        "| Quantity | Estimate | SE | p-value | 95% CI |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['quantity']} | {report_number(row['estimate'])} | "
            f"{report_number(row['std_error'])} | {report_number(row['p_value'])} | {report_ci(row)} |"
        )
    return "\n".join(lines)


def bool_word(value: bool) -> str:
    return "yes" if value else "no"


def significance_change(old_p: object, new_p: object) -> str:
    old_sig = float(old_p) < 0.05
    new_sig = float(new_p) < 0.05
    if old_sig and new_sig:
        return "remained significant and strengthened" if float(new_p) < float(old_p) else "remained significant but weakened"
    if old_sig and not new_sig:
        return "lost conventional significance"
    if not old_sig and new_sig:
        return "became significant"
    return "remained statistically indistinct from zero"


def write_extended_results_report(
    audit_rows: list[dict[str, object]],
    regression_rows: list[dict[str, object]],
    partition_rows: list[dict[str, object]],
    raw_partition_rows: list[dict[str, object]],
    fits: dict[str, dict[str, object]],
    stata_status: str,
    out: ExtendedOutputs,
) -> None:
    audit_total = sum_column(audit_rows, "all_count")
    audit_high = sum_column(audit_rows, "high_sensitivity_count")
    audit_lower = sum_column(audit_rows, "lower_sensitivity_count")
    zero_start_months = [str(row["month"]) for row in audit_rows if int(row["all_count"]) == 0]
    zero_start_note = (
        f"Zero-start months in 2026 H1: {', '.join(zero_start_months)}. They are retained."
        if zero_start_months
        else "No 2026 H1 month has zero recorded starts."
    )
    t1_post = linear_combination(fits["test1_high_sensitivity_count"], {"Time": 1.0, "TimeAfterJuly2024": 1.0})
    t2_post = linear_combination(fits["test2_high_share_all"], {"Time": 1.0, "TimeAfterJuly2024": 1.0})
    t1_slopes = [
        {"quantity": "PreSlope beta1", **fit_result(regression_rows, "test1_high_sensitivity_count", "Time")},
        {"quantity": "PostSlope beta1 + beta3", **t1_post},
    ]
    t2_slopes = [
        {"quantity": "PreSlope beta1", **fit_result(regression_rows, "test2_high_share_all", "Time")},
        {"quantity": "PostSlope beta1 + beta3", **t2_post},
        {"quantity": "SlopeChange beta3", **fit_result(regression_rows, "test2_high_share_all", "TimeAfterJuly2024")},
    ]
    t2_beta3 = fit_result(regression_rows, "test2_high_share_all", "TimeAfterJuly2024")
    partition_map = partition_result_map([{key: str(value) for key, value in row.items()} for row in partition_rows])
    delta3 = partition_map["differential_slope_change_delta3"]
    raw_map = partition_result_map([{key: str(value) for key, value in row.items()} for row in raw_partition_rows])
    raw_delta3 = raw_map["differential_slope_change_delta3"]
    test3_bottom_line = (
        "High trajectory strengthened significantly more than Lower."
        if float(delta3["estimate"]) > 0 and float(delta3["p_value"]) < 0.05
        else "No statistically detectable differential strengthening of High relative to Lower."
    )
    results = f"""# Project Entry2 Results Through 2026 H1

Extended estimation window: 2019-01 through 2026-06. Breakpoint remains July 2024, with July 2024 `time_after_july2024 = 0` and June 2026 `time_after_july2024 = 23`.

## A. 2026 H1 Data Audit

{audit_markdown_table(audit_rows)}

2026 Jan-Jun total recorded starts = {audit_total:,}. 2026 Jan-Jun High = {audit_high:,}. 2026 Jan-Jun Lower = {audit_lower:,}. For every 2026 H1 month, `High + Lower = All`.

{zero_start_note}

## B. Test 1

Outcome: `high_sensitivity_count`. Specification: OLS with Newey-West HAC standard errors, lag(3), plus month-of-year fixed effects.

{compact_coef(regression_rows, "test1_high_sensitivity_count")}

{slope_summary_table(t1_slopes)}

Linear-combination test for `H0: beta1 + beta3 = 0`: p = {report_number(t1_post["p_value"])}.

## C. Test 2

Outcome: `high_sensitivity_share_all`. Calendar time is retained when total monthly starts are zero; the share outcome is missing for such months.

{compact_coef(regression_rows, "test2_high_share_all")}

{slope_summary_table(t2_slopes)}

Beta3 remains positive: {bool_word(float(t2_beta3["estimate"]) > 0)}. Beta3 remains significant: {bool_word(float(t2_beta3["p_value"]) < 0.05)}. Post slope remains positive: {bool_word(float(t2_post["estimate"]) > 0)}. Post slope is statistically positive: {bool_word(float(t2_post["estimate"]) > 0 and float(t2_post["p_value"]) < 0.05)}.

## D. Test 3

Test 3 asks whether the post-transition change in entry trajectory differs between the high-sensitivity and lower-sensitivity partitions. The conceptual model remains the High-vs-Lower stacked partition interaction with Lower omitted:

$$
\\begin{{aligned}}
Y_{{g,t}} ={{}}& \\beta_0 + \\beta_1 Time_t + \\beta_2 Post_t + \\beta_3 TimeAfter_t \\\\
&+ \\delta_0 High_g
+ \\delta_1 High_g \\times Time_t
+ \\delta_2 High_g \\times Post_t \\\\
&+ \\delta_3 High_g \\times TimeAfter_t
+ MonthFE
+ High_g \\times MonthFE
+ \\epsilon_{{g,t}}.
\\end{{aligned}}
$$

Each group outcome is normalized as `100 * N_g,t / pre-transition monthly mean`. The pre-transition denominator is the same full pre-July-2024 mean used in the 2025-12 baseline.

{partition_report_table([{key: str(value) for key, value in row.items()} for row in partition_rows])}

{test3_bottom_line}

The Newey-West implementation remains the three-series equivalent: Lower index, High index, and High-minus-Lower index difference, all over the same 90 calendar months.

## E. Raw-Count Test 3 Robustness

ROBUSTNESS ONLY. This raw-count comparison asks whether the normalized result is purely created by pre-mean normalization. It is not the primary Test 3 because the High and Lower group sizes differ sharply.

{partition_report_table([{key: str(value) for key, value in row.items()} for row in raw_partition_rows])}

Raw-count robustness differential slope change: {report_number(raw_delta3["estimate"])} (SE {report_number(raw_delta3["std_error"])}, p {report_number(raw_delta3["p_value"])}, 95% CI {report_ci(raw_delta3)}).

## F. Interpretation

Test 1 and Test 2 continue to ask whether high-sensitivity entry and share changed after July 2024. Test 3 continues to ask the stricter comparative question: did High strengthen more than the Lower complement after normalizing each group by its own pre-transition monthly mean? The extended normalized Test 3 result remains governed by `delta3`.

## G. Stata Status

Stata status: `{stata_status}`.
"""
    write_text(out.results_report, results)


def write_window_comparison_report(
    comparison_rows: list[dict[str, object]],
    raw_partition_rows: list[dict[str, object]],
    stata_status: str,
    out: ExtendedOutputs,
) -> None:
    t1_beta3 = comparison_lookup(comparison_rows, "Test 1", "beta3")
    t1_post = comparison_lookup(comparison_rows, "Test 1", "post slope")
    t2_beta3 = comparison_lookup(comparison_rows, "Test 2", "beta3")
    t2_post = comparison_lookup(comparison_rows, "Test 2", "post slope")
    t3_delta3 = comparison_lookup(comparison_rows, "Test 3", "delta3")
    raw_map = partition_result_map([{key: str(value) for key, value in row.items()} for row in raw_partition_rows])
    raw_delta3 = raw_map["differential_slope_change_delta3"]
    se_shrank = float(t3_delta3["through_2026_06_std_error"]) < float(t3_delta3["through_2025_12_std_error"])
    ci_old_width = float(t3_delta3["through_2025_12_ci_high"]) - float(t3_delta3["through_2025_12_ci_low"])
    ci_new_width = float(t3_delta3["through_2026_06_ci_high"]) - float(t3_delta3["through_2026_06_ci_low"])
    sign_changed = (float(t3_delta3["through_2025_12_estimate"]) > 0) != (
        float(t3_delta3["through_2026_06_estimate"]) > 0
    )
    main_conclusion = "UNCHANGED"
    if float(t1_beta3["through_2026_06_p_value"]) < float(t1_beta3["through_2025_12_p_value"]) and float(
        t2_beta3["through_2026_06_p_value"]
    ) < float(t2_beta3["through_2025_12_p_value"]):
        main_conclusion = "STRENGTHENED"
    if sign_changed and float(t3_delta3["through_2026_06_p_value"]) < 0.05:
        main_conclusion = "REVERSED"
    results = f"""# Project Entry2 Window Comparison

Question: after adding January-June 2026, did the substantive conclusions change?

## Test 1

Did the High post-transition slope remain positive? {bool_word(float(t1_post["through_2026_06_estimate"]) > 0)}.

Did significance strengthen/weaken/disappear? The beta3 result {significance_change(t1_beta3["through_2025_12_p_value"], t1_beta3["through_2026_06_p_value"])}.

{comparison_markdown_table(comparison_rows, "Test 1")}

## Test 2

Did the High share still switch from declining pretrend to increasing posttrend? {bool_word(float(comparison_lookup(comparison_rows, "Test 2", "beta1")["through_2026_06_estimate"]) < 0 and float(t2_post["through_2026_06_estimate"]) > 0)}.

Did beta3 remain positive/significant? Positive: {bool_word(float(t2_beta3["through_2026_06_estimate"]) > 0)}. Significant: {bool_word(float(t2_beta3["through_2026_06_p_value"]) < 0.05)}.

Did the post slope remain positive? {bool_word(float(t2_post["through_2026_06_estimate"]) > 0)}. H0 post slope = 0 p-value: {report_number(t2_post["through_2026_06_p_value"])}.

{comparison_markdown_table(comparison_rows, "Test 2")}

## Test 3

Did High begin to strengthen more than Lower? {bool_word(float(t3_delta3["through_2026_06_estimate"]) > 0 and float(t3_delta3["through_2026_06_p_value"]) < 0.05)}.

What happened to delta3? It changed from {report_number(t3_delta3["through_2025_12_estimate"])} to {report_number(t3_delta3["through_2026_06_estimate"])}.

Did its SE shrink? {bool_word(se_shrank)}.

Did its CI narrow? {bool_word(ci_new_width < ci_old_width)}.

Did its sign change? {bool_word(sign_changed)}.

{comparison_markdown_table(comparison_rows, "Test 3")}

Raw-count Test 3 robustness delta3: {report_number(raw_delta3["estimate"])} (SE {report_number(raw_delta3["std_error"])}, p {report_number(raw_delta3["p_value"])}, 95% CI {report_ci(raw_delta3)}). This is ROBUSTNESS ONLY.

## Main Substantive Conclusion

{main_conclusion}

Stata status: `{stata_status}`.
"""
    write_text(out.window_comparison_report, results)


def validate_outputs(out: Outputs | None = None) -> None:
    out = out or Outputs()
    monthly = read_csv(out.monthly)
    if len(monthly) != 84:
        raise AssertionError(f"expected 84 monthly rows; found {len(monthly)}")
    if monthly[0]["month"] != "2019-01" or monthly[-1]["month"] != "2025-12":
        raise AssertionError("primary window month range changed")
    required_monthly_columns = {"hs_wes_wgs_sequence_count", "high_sensitivity_count"}
    missing_monthly = sorted(required_monthly_columns - set(monthly[0]))
    if missing_monthly:
        raise AssertionError(f"monthly file missing Test 1 columns: {missing_monthly}")
    if monthly[66]["month"] != "2024-07" or int(monthly[66]["time_after_july2024"]) != 0:
        raise AssertionError("July 2024 must have time_after_july2024 = 0")
    if monthly[67]["month"] != "2024-08" or int(monthly[67]["time_after_july2024"]) != 1:
        raise AssertionError("August 2024 must have time_after_july2024 = 1")
    for row in monthly:
        high = int(row["high_sensitivity_count"])
        lower = int(row["lower_sensitivity_count"])
        all_count = int(row["all_count"])
        denom = int(row["classified_denom_high_lower"])
        if denom != all_count or high + lower != all_count:
            raise AssertionError(f"HIGH/LOWER monthly complement mismatch in {row['month']}")
    regressions = read_csv(out.regression_results)
    terms = {(row["model_id"], row["term"]) for row in regressions}
    for model_id in [
        "test1_high_sensitivity_count",
        "test2_high_share_all",
        "test3_lower_index",
        "test3_high_index",
        "test3_high_minus_lower_difference",
    ]:
        for term in ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024", "month_12"]:
            if (model_id, term) not in terms:
                raise AssertionError(f"missing {model_id} {term}")
    for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
        lower = float(term_row(regressions, "test3_lower_index", term)["estimate"])
        high = float(term_row(regressions, "test3_high_index", term)["estimate"])
        diff = float(term_row(regressions, "test3_high_minus_lower_difference", term)["estimate"])
        if abs(diff - (high - lower)) > 1e-6:
            raise AssertionError(f"Test 3 difference coefficient mismatch for {term}")
    stacked = read_csv(out.test3_stacked)
    if len(stacked) != 168:
        raise AssertionError(f"expected 168 Test 3 stacked rows; found {len(stacked)}")
    groups = Counter(row["group"] for row in stacked)
    if groups["High"] != 84 or groups["Lower"] != 84:
        raise AssertionError(f"expected 84 High and 84 Lower stacked rows; found {groups}")
    july_stacked = [row for row in stacked if row["month"] == "2024-07"]
    if len(july_stacked) != 2 or any(int(row["time_after_july2024"]) != 0 for row in july_stacked):
        raise AssertionError("Test 3 stacked July 2024 rows must have time_after_july2024 = 0")
    if not any(row["group"] == "High" and int(row["raw_count"]) == 0 for row in stacked):
        raise AssertionError("Test 3 stacked file lost High zero-count months")
    if not any(row["group"] == "Lower" and int(row["raw_count"]) == 0 for row in stacked):
        raise AssertionError("Test 3 stacked file lost Lower zero-count months")
    partition_rows = read_csv(out.test3_partition_results)
    partition_quantities = {row["quantity"] for row in partition_rows}
    for quantity in [
        "lower_pre_slope",
        "lower_post_slope",
        "lower_slope_change",
        "high_pre_slope",
        "high_post_slope",
        "high_slope_change",
        "differential_level_change_delta2",
        "differential_slope_change_delta3",
    ]:
        if quantity not in partition_quantities:
            raise AssertionError(f"missing Test 3 partition result {quantity}")
    if not zero_month_preservation_check(monthly, regressions):
        raise AssertionError("zero-month/calendar-time preservation check failed")
    for path in [
        out.test1_figure,
        out.test2_figure,
        out.test3_raw_figure,
        out.test3_indexed_figure,
    ]:
        if not path.exists() or "<svg" not in path.read_text(encoding="utf-8")[:100]:
            raise AssertionError(f"missing or invalid figure {path}")
    if not out.stata_do.exists() or "newey" not in out.stata_do.read_text(encoding="utf-8"):
        raise AssertionError("Stata do-file missing newey regressions")
    if not out.stata_style_python_table.exists():
        raise AssertionError("Stata-style Python regression table missing")
    table_text = out.stata_style_python_table.read_text(encoding="utf-8")
    if "Regression with Newey-West standard errors" not in table_text:
        raise AssertionError("Stata-style table missing Newey-West header")
    if "monthFE = Yes" not in table_text:
        raise AssertionError("Stata-style table missing compressed monthFE indicator")
    if "2.month_of_year" in table_text or "12.month_of_year" in table_text:
        raise AssertionError("Stata-style table should not print month fixed-effect coefficients")
    if "test3_high_minus_lower_difference" not in table_text:
        raise AssertionError("Stata-style table missing Test 3 difference model")


def validate_extended_outputs(out: ExtendedOutputs | None = None) -> None:
    out = out or ExtendedOutputs()
    baseline_monthly = read_csv(Outputs().monthly)
    if len(baseline_monthly) != 84 or baseline_monthly[-1]["month"] != "2025-12":
        raise AssertionError("baseline data/ monthly output was overwritten")
    monthly = read_csv(out.monthly)
    if len(monthly) != 90:
        raise AssertionError(f"expected 90 extended monthly rows; found {len(monthly)}")
    if monthly[0]["month"] != "2019-01" or monthly[-1]["month"] != "2026-06":
        raise AssertionError("extended window month range changed")
    by_month = {row["month"]: row for row in monthly}
    for label in ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]:
        if label not in by_month:
            raise AssertionError(f"missing extended month {label}")
    if by_month["2024-07"]["time_after_july2024"] != "0":
        raise AssertionError("July 2024 must have time_after_july2024 = 0 in extended output")
    if by_month["2024-08"]["time_after_july2024"] != "1":
        raise AssertionError("August 2024 must have time_after_july2024 = 1 in extended output")
    if by_month["2026-06"]["time_after_july2024"] != "23":
        raise AssertionError("June 2026 must have time_after_july2024 = 23")
    for row in monthly:
        high = int(row["high_sensitivity_count"])
        lower = int(row["lower_sensitivity_count"])
        all_count = int(row["all_count"])
        if high + lower != all_count:
            raise AssertionError(f"HIGH/LOWER monthly complement mismatch in {row['month']}")
    regressions = read_csv(out.regression_results)
    n_by_model = {
        row["model_id"]: int(row["n_obs"])
        for row in regressions
        if row["term"] == "Intercept"
    }
    for model_id in [
        "test1_high_sensitivity_count",
        "test3_lower_index",
        "test3_high_index",
        "test3_high_minus_lower_difference",
    ]:
        if n_by_model.get(model_id) != 90:
            raise AssertionError(f"expected N=90 for {model_id}; found {n_by_model.get(model_id)}")
    terms = {(row["model_id"], row["term"]) for row in regressions}
    for model_id in [
        "test1_high_sensitivity_count",
        "test2_high_share_all",
        "test3_lower_index",
        "test3_high_index",
        "test3_high_minus_lower_difference",
    ]:
        for term in ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024", "month_12"]:
            if (model_id, term) not in terms:
                raise AssertionError(f"missing extended {model_id} {term}")
    for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
        lower = float(term_row(regressions, "test3_lower_index", term)["estimate"])
        high = float(term_row(regressions, "test3_high_index", term)["estimate"])
        diff = float(term_row(regressions, "test3_high_minus_lower_difference", term)["estimate"])
        if abs(diff - (high - lower)) > 1e-6:
            raise AssertionError(f"extended Test 3 difference coefficient mismatch for {term}")
    stacked = read_csv(out.test3_stacked)
    if len(stacked) != 180:
        raise AssertionError(f"expected 180 extended Test 3 stacked rows; found {len(stacked)}")
    groups = Counter(row["group"] for row in stacked)
    if groups["High"] != 90 or groups["Lower"] != 90:
        raise AssertionError(f"expected 90 High and 90 Lower stacked rows; found {groups}")
    if not any(row["group"] == "High" and int(row["raw_count"]) == 0 for row in stacked):
        raise AssertionError("extended Test 3 stacked file lost High zero-count months")
    if not any(row["group"] == "Lower" and int(row["raw_count"]) == 0 for row in stacked):
        raise AssertionError("extended Test 3 stacked file lost Lower zero-count months")
    audit_rows = read_csv(out.audit_2026h1)
    if [row["month"] for row in audit_rows] != ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]:
        raise AssertionError("2026 H1 audit months are incomplete")
    for path in [
        out.test1_figure,
        out.test2_figure,
        out.test3_raw_figure,
        out.test3_indexed_figure,
        out.results_report,
        out.window_comparison_report,
        out.stata_log,
        out.stata_table,
        out.stata_style_python_table,
        out.test3_partition_results,
        out.test3_raw_partition_results,
        out.window_comparison,
    ]:
        if not path.exists():
            raise AssertionError(f"missing extended output {path}")
    for figure in [out.test1_figure, out.test2_figure, out.test3_raw_figure, out.test3_indexed_figure]:
        if "<svg" not in figure.read_text(encoding="utf-8")[:100]:
            raise AssertionError(f"missing or invalid extended figure {figure}")


def build_project_entry2_outputs(
    rebuild_classification: bool = True,
    refresh_schema: bool = False,
    refresh_field_pages: bool = False,
    no_fetch_field_pages: bool = False,
    sleep_seconds: float = 0.05,
) -> dict[str, object]:
    out = Outputs()
    if rebuild_classification or not classification_builder.Outputs().classification.exists():
        classification_builder.build_high_sensitivity_outputs(
            refresh_schema=refresh_schema,
            refresh_field_pages=refresh_field_pages,
            no_fetch_field_pages=no_fetch_field_pages,
            sleep_seconds=sleep_seconds,
        )
        classification_builder.validate_outputs()

    classification_rows = read_csv(classification_builder.Outputs().classification)
    monthly_rows = monthly_panel(classification_rows)
    write_csv(
        out.monthly,
        monthly_rows,
        [
            "month",
            "month_start",
            "time",
            "post_july2024",
            "time_after_july2024",
            "month_of_year",
            "all_count",
            "high_sensitivity_count",
            "lower_sensitivity_count",
            "low_strict_count",
            "hs_wes_wgs_sequence_count",
            "hs_s3_direct_count",
            "hs_s3_text_count",
            "hs_o2_field_count",
            "classified_denom_high_lower",
            "high_sensitivity_share_all",
            "low_share_all",
            "index_high_pre_mean",
            "index_lower_pre_mean",
            "index_diff_pre_mean",
            "index_high_2023_mean",
            "index_lower_2023_mean",
            "index_diff_2023_mean",
        ],
    )
    regression_rows, fits = run_all_models(monthly_rows)
    write_csv(
        out.regression_results,
        regression_rows,
        [
            "model_id",
            "test",
            "outcome",
            "classification_definition",
            "denominator",
            "term",
            "estimate",
            "std_error",
            "statistic",
            "p_value",
            "ci_low",
            "ci_high",
            "n_obs",
            "r_squared",
            "model_f_statistic_classical",
            "nw_lag",
            "inference",
            "sample_dates",
        ],
    )
    write_csv(
        out.test3_stacked,
        build_test3_stacked_rows(monthly_rows),
        [
            "month",
            "month_start",
            "time",
            "post_july2024",
            "time_after_july2024",
            "month_of_year",
            "group",
            "high_group",
            "raw_count",
            "entry_index_pre_mean",
        ],
    )
    write_csv(
        out.test3_partition_results,
        test3_partition_result_rows(fits),
        ["quantity", "estimate", "std_error", "p_value", "ci_low", "ci_high"],
    )
    write_stata_style_python_output(out, regression_rows)
    make_figures(monthly_rows, fits, regression_rows, out)
    stata_status = run_stata_if_available(out, regression_rows)
    write_reports(classification_rows, monthly_rows, regression_rows, stata_status, out)
    validate_outputs(out)
    return {
        "high_sensitivity": period_count(classification_rows, "HIGH_SENSITIVITY"),
        "lower_sensitivity": period_count(classification_rows, "LOWER_SENSITIVITY_COMPARISON"),
        "hs_wes_wgs_sequence": period_count(classification_rows, "hs_wes_wgs_sequence"),
        "hs_s3_direct": period_count(classification_rows, "hs_s3_direct"),
        "hs_s3_text": period_count(classification_rows, "hs_s3_text"),
        "low_strict": period_count(classification_rows, "LOW_STRICT"),
        "stata_status": stata_status,
    }


def build_project_entry2_extended_outputs() -> dict[str, object]:
    out = ExtendedOutputs()
    classification_path = classification_builder.Outputs().classification
    if not classification_path.exists():
        raise FileNotFoundError(
            "classification output is required for the extended run; "
            "this task does not rebuild or redefine HIGH_SENSITIVITY"
        )
    classification_rows = read_csv(classification_path)
    baseline_monthly_rows = monthly_panel(classification_rows, end_month=PRIMARY_END)
    baseline_regression_rows, baseline_fits = run_all_models(baseline_monthly_rows)
    baseline_partition_rows = test3_partition_result_rows(baseline_fits)

    monthly_rows = monthly_panel(classification_rows, end_month=EXTENDED_END)
    monthly_fieldnames = [
        "month",
        "month_start",
        "time",
        "post_july2024",
        "time_after_july2024",
        "month_of_year",
        "all_count",
        "high_sensitivity_count",
        "lower_sensitivity_count",
        "low_strict_count",
        "hs_wes_wgs_sequence_count",
        "hs_s3_direct_count",
        "hs_s3_text_count",
        "hs_o2_field_count",
        "classified_denom_high_lower",
        "high_sensitivity_share_all",
        "low_share_all",
        "index_high_pre_mean",
        "index_lower_pre_mean",
        "index_diff_pre_mean",
        "index_high_2023_mean",
        "index_lower_2023_mean",
        "index_diff_2023_mean",
    ]
    write_csv(out.monthly, monthly_rows, monthly_fieldnames)

    audit_rows = audit_2026h1_rows(monthly_rows)
    write_csv(
        out.audit_2026h1,
        audit_rows,
        [
            "month",
            "all_count",
            "high_sensitivity_count",
            "lower_sensitivity_count",
            "high_sensitivity_share_all",
        ],
    )

    regression_rows, fits = run_all_models(monthly_rows)
    write_csv(
        out.regression_results,
        regression_rows,
        [
            "model_id",
            "test",
            "outcome",
            "classification_definition",
            "denominator",
            "term",
            "estimate",
            "std_error",
            "statistic",
            "p_value",
            "ci_low",
            "ci_high",
            "n_obs",
            "r_squared",
            "model_f_statistic_classical",
            "nw_lag",
            "inference",
            "sample_dates",
        ],
    )

    write_csv(
        out.test3_stacked,
        build_test3_stacked_rows(monthly_rows),
        [
            "month",
            "month_start",
            "time",
            "post_july2024",
            "time_after_july2024",
            "month_of_year",
            "group",
            "high_group",
            "raw_count",
            "entry_index_pre_mean",
        ],
    )

    partition_rows = test3_partition_result_rows(fits)
    write_csv(
        out.test3_partition_results,
        partition_rows,
        ["quantity", "estimate", "std_error", "p_value", "ci_low", "ci_high"],
    )

    _, raw_fits = run_test3_raw_partition_models(monthly_rows)
    raw_partition_rows = test3_raw_partition_result_rows(raw_fits)
    write_csv(
        out.test3_raw_partition_results,
        raw_partition_rows,
        ["role", "quantity", "estimate", "std_error", "p_value", "ci_low", "ci_high"],
    )

    comparison_rows = window_comparison_rows(
        baseline_regression_rows,
        baseline_fits,
        baseline_partition_rows,
        regression_rows,
        fits,
        partition_rows,
    )
    comparison_fieldnames = [
        "test",
        "quantity",
        "through_2025_12_estimate",
        "through_2025_12_std_error",
        "through_2025_12_p_value",
        "through_2025_12_ci_low",
        "through_2025_12_ci_high",
        "through_2026_06_estimate",
        "through_2026_06_std_error",
        "through_2026_06_p_value",
        "through_2026_06_ci_low",
        "through_2026_06_ci_high",
        "change_estimate",
    ]
    write_csv(out.window_comparison, comparison_rows, comparison_fieldnames)

    write_stata_style_python_output(out, regression_rows)
    make_figures(
        monthly_rows,
        fits,
        regression_rows,
        out,
        end_month=EXTENDED_END,
        title_suffix=" Through Jun 2026",
    )
    stata_status = run_stata_if_available(out, regression_rows, end_month=EXTENDED_END)
    write_extended_results_report(audit_rows, regression_rows, partition_rows, raw_partition_rows, fits, stata_status, out)
    write_window_comparison_report(comparison_rows, raw_partition_rows, stata_status, out)
    validate_extended_outputs(out)
    return {
        "h1_all": sum_column(audit_rows, "all_count"),
        "h1_high": sum_column(audit_rows, "high_sensitivity_count"),
        "h1_lower": sum_column(audit_rows, "lower_sensitivity_count"),
        "stata_status": stata_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-classification", action="store_true")
    parser.add_argument("--extended-2026h1", action="store_true")
    parser.add_argument("--refresh-schema", action="store_true")
    parser.add_argument("--refresh-field-pages", action="store_true")
    parser.add_argument("--no-fetch-field-pages", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    args = parser.parse_args()
    if args.extended_2026h1:
        summary = build_project_entry2_extended_outputs()
        print(
            "project-entry2 extended analysis built: "
            f"{summary['h1_all']} 2026H1 starts, "
            f"{summary['h1_high']} HIGH_SENSITIVITY, "
            f"{summary['h1_lower']} LOWER_SENSITIVITY_COMPARISON, "
            f"Stata status {summary['stata_status']}"
        )
    else:
        summary = build_project_entry2_outputs(
            rebuild_classification=not args.skip_classification,
            refresh_schema=args.refresh_schema,
            refresh_field_pages=args.refresh_field_pages,
            no_fetch_field_pages=args.no_fetch_field_pages,
            sleep_seconds=args.sleep_seconds,
        )
        print(
            "project-entry2 analysis built: "
            f"{summary['high_sensitivity']} HIGH_SENSITIVITY, "
            f"{summary['lower_sensitivity']} LOWER_SENSITIVITY_COMPARISON, "
            f"Stata status {summary['stata_status']}"
        )


if __name__ == "__main__":
    main()
