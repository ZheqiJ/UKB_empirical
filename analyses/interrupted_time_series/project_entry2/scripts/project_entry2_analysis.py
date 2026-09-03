#!/usr/bin/env python3
"""Run project-entry2 high-sensitivity ITS analyses."""

from __future__ import annotations

import argparse
import csv
import math
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
FIGURE_DIR = PACKAGE / "figures"
REPORT_DIR = PACKAGE / "reports"
SCRIPT_DIR = PACKAGE / "scripts"

PRIMARY_START = date(2019, 1, 1)
PRIMARY_END = date(2025, 12, 1)
BREAK_MONTH = date(2024, 7, 1)
HAC_LAG = 3


@dataclass(frozen=True)
class Outputs:
    monthly: Path = DATA_DIR / "project_entry2_monthly.csv"
    regression_results: Path = DATA_DIR / "project_entry2_regression_results.csv"
    replication_check: Path = DATA_DIR / "stata_python_replication_check.csv"
    stata_do: Path = SCRIPT_DIR / "project_entry2_its.do"
    stata_log: Path = REPORT_DIR / "project_entry2_stata_full.log"
    stata_table: Path = REPORT_DIR / "project_entry2_stata_regression_table.csv"
    reading_guide: Path = REPORT_DIR / "project_entry2_reading_guide.md"
    measurement_note: Path = REPORT_DIR / "project_entry2_measurement_note.md"
    results_report: Path = REPORT_DIR / "project_entry2_results.md"
    test1_figure: Path = FIGURE_DIR / "figure_test1_high_sensitivity_entry.svg"
    test2_figure: Path = FIGURE_DIR / "figure_test2_high_sensitivity_share.svg"
    test3_raw_figure: Path = FIGURE_DIR / "figure_test3_high_vs_low_raw.svg"
    test3_indexed_figure: Path = FIGURE_DIR / "figure_test3_high_vs_low_indexed.svg"


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


def build_design(months: list[date]) -> tuple[list[list[float]], list[str]]:
    names = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"] + [
        f"month_{month:02d}" for month in range(2, 13)
    ]
    X = []
    for idx, month in enumerate(months, start=1):
        post = 1.0 if month >= BREAK_MONTH else 0.0
        time_after = (
            float((month.year - BREAK_MONTH.year) * 12 + month.month - BREAK_MONTH.month + 1)
            if post
            else 0.0
        )
        X.append(
            [1.0, float(idx), post, time_after]
            + [1.0 if month.month == fixed_month else 0.0 for fixed_month in range(2, 13)]
        )
    return X, names


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


def monthly_panel(classification_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    rows_by_month = defaultdict(list)
    for row in classification_rows:
        start = parse_date(row["start_date"])
        rows_by_month[date(start.year, start.month, 1)].append(row)

    output = []
    for idx, month in enumerate(month_range(PRIMARY_START, PRIMARY_END), start=1):
        rows = rows_by_month.get(month, [])

        def count(flag: str) -> int:
            return sum(int(row[flag]) for row in rows)

        all_count = len(rows)
        high_c05 = count("HIGH_C05_S3")
        high_c03 = count("HIGH_C03_S3")
        high_c05_cons = count("HIGH_C05_S3_TIMING_CONSERVATIVE")
        low = count("LOW_STRICT")
        not_high = count("NOT_HIGH")
        classified_denom = high_c05 + low
        c03_classified_denom = high_c03 + low
        output.append(
            {
                "month": month_label(month),
                "month_start": month.isoformat(),
                "time": idx,
                "post_july2024": 1 if month >= BREAK_MONTH else 0,
                "time_after_july2024": (
                    (month.year - BREAK_MONTH.year) * 12 + month.month - BREAK_MONTH.month + 1
                    if month >= BREAK_MONTH
                    else 0
                ),
                "month_of_year": month.month,
                "all_count": all_count,
                "high_c05_s3_count": high_c05,
                "high_c03_s3_count": high_c03,
                "high_c05_s3_timing_cons_count": high_c05_cons,
                "low_strict_count": low,
                "not_high_count": not_high,
                "s3_only_count": count("S3_ONLY"),
                "c05_only_count": count("C05_ONLY"),
                "c05_or_s3_or_o2_count": count("C05_OR_S3_OR_O2"),
                "hs_s3_field_count": count("hs_s3_field"),
                "hs_o2_field_count": count("hs_o2_field"),
                "classified_denom_c05_s3": classified_denom,
                "high_share_classified_c05_s3": fmt(high_c05 / classified_denom if classified_denom else math.nan, 8),
                "high_share_all_c05_s3": fmt(high_c05 / all_count if all_count else math.nan, 8),
                "high_share_classified_c03_s3": fmt(
                    high_c03 / c03_classified_denom if c03_classified_denom else math.nan, 8
                ),
                "low_share_all": fmt(low / all_count if all_count else math.nan, 8),
            }
        )
    return output


def run_model(
    monthly_rows: list[dict[str, object]],
    outcome: str,
    model_id: str,
    test: str,
    classification_definition: str,
    denominator: str = "",
) -> tuple[list[dict[str, object]], dict[str, object]]:
    months: list[date] = []
    y: list[float] = []
    for row in monthly_rows:
        raw = clean(row.get(outcome))
        if not raw:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if math.isnan(value) or math.isinf(value):
            continue
        months.append(parse_date(str(row["month_start"])))
        y.append(value)
    X, names = build_design(months)
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
    fit["y"] = y
    fit["model_id"] = model_id
    return rows, fit


def run_all_models(monthly_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    specs = [
        (
            "test1_primary_high_c05_s3",
            "Test 1",
            "high_c05_s3_count",
            "HIGH_C05_S3",
            "",
        ),
        (
            "test1_robust_high_c03_s3",
            "Test 1 robustness",
            "high_c03_s3_count",
            "HIGH_C03_S3",
            "",
        ),
        (
            "test1_timing_conservative_high_c05_s3",
            "Test 1 timing conservative",
            "high_c05_s3_timing_cons_count",
            "HIGH_C05_S3_TIMING_CONSERVATIVE",
            "",
        ),
        (
            "test2_primary_high_share_classified",
            "Test 2",
            "high_share_classified_c05_s3",
            "HIGH_C05_S3",
            "HIGH_C05_S3 + LOW_STRICT",
        ),
        (
            "test2_robust_high_share_all",
            "Test 2 robustness",
            "high_share_all_c05_s3",
            "HIGH_C05_S3",
            "all recorded project starts",
        ),
        (
            "test2_robust_c03_high_share_classified",
            "Test 2 C03 robustness",
            "high_share_classified_c03_s3",
            "HIGH_C03_S3",
            "HIGH_C03_S3 + LOW_STRICT",
        ),
        (
            "test3_high_c05_s3",
            "Test 3",
            "high_c05_s3_count",
            "HIGH_C05_S3",
            "",
        ),
        (
            "test3_low_strict",
            "Test 3",
            "low_strict_count",
            "LOW_STRICT",
            "",
        ),
        (
            "test3_not_high",
            "Test 3 robustness",
            "not_high_count",
            "NOT_HIGH",
            "",
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
) -> None:
    width, height = 1080, 540
    ml, mr, mt, mb = 88, 210, 52, 66
    pw, ph = width - ml - mr, height - mt - mb
    months = month_range(PRIMARY_START, PRIMARY_END)
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
    for year in range(PRIMARY_START.year, PRIMARY_END.year + 1):
        xx = x(date(year, 1, 1))
        svg.append(f'<line x1="{xx:.1f}" y1="{mt}" x2="{xx:.1f}" y2="{height-mb}" stroke="#eeeeee"/>')
        svg.append(f'<text x="{xx:.1f}" y="{height-28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#444">{year}</text>')
    break_x = x(BREAK_MONTH)
    svg.append(f'<line x1="{break_x:.1f}" y1="{mt}" x2="{break_x:.1f}" y2="{height-mb}" stroke="#111" stroke-width="2.2"/>')
    svg.append(f'<text x="{break_x+7:.1f}" y="{mt+16}" font-family="Arial, sans-serif" font-size="11" fill="#111">Jul 2024</text>')

    style = {
        "Observed high": ("#24536b", "", 2.4),
        "Fitted high": ("#24536b", "6 4", 2.4),
        "Observed primary share": ("#24536b", "", 2.4),
        "Fitted primary share": ("#24536b", "6 4", 2.4),
        "Observed high/all share": ("#8a5a22", "", 2.0),
        "Fitted high/all share": ("#8a5a22", "6 4", 2.0),
        "High": ("#24536b", "", 2.4),
        "Low strict": ("#b24a38", "", 2.4),
        "Not high": ("#777777", "5 5", 1.8),
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
        if "Observed" in label or label in {"High", "Low strict", "Not high"}:
            for px, py in points:
                svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.7" fill="{color}"/>')
        ly = legend_y + i * 22
        svg.append(f'<line x1="{width-mr+28}" y1="{ly}" x2="{width-mr+58}" y2="{ly}" stroke="{color}" stroke-width="{line_width}"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")
        svg.append(f'<text x="{width-mr+66}" y="{ly+4}" font-family="Arial, sans-serif" font-size="12" fill="#333">{label}</text>')

    svg.append(f'<text x="20" y="{mt+ph/2}" transform="rotate(-90 20 {mt+ph/2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">{y_label}</text>')
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
    out: Outputs,
) -> None:
    test1_series = figure_rows_from_fit(
        monthly_rows,
        fits["test1_primary_high_c05_s3"],
        "high_c05_s3_count",
        "Observed high",
        "Fitted high",
    )
    make_svg_time_series(
        out.test1_figure,
        "Test 1: High-Sensitivity Project Entry",
        test1_series,
        "Monthly high-sensitivity starts",
        y_min=0,
    )

    test2_series = figure_rows_from_fit(
        monthly_rows,
        fits["test2_primary_high_share_classified"],
        "high_share_classified_c05_s3",
        "Observed primary share",
        "Fitted primary share",
    )
    test2_series.extend(
        figure_rows_from_fit(
            monthly_rows,
            fits["test2_robust_high_share_all"],
            "high_share_all_c05_s3",
            "Observed high/all share",
            "Fitted high/all share",
        )
    )
    make_svg_time_series(
        out.test2_figure,
        "Test 2: High-Sensitivity Share",
        test2_series,
        "Share of classified project starts that are high sensitivity",
        y_min=0,
        y_max=1,
        percent_axis=True,
    )

    raw_series = []
    for row in monthly_rows:
        raw_series.append({"month_start": row["month_start"], "value": row["high_c05_s3_count"], "label": "High"})
        raw_series.append({"month_start": row["month_start"], "value": row["low_strict_count"], "label": "Low strict"})
    make_svg_time_series(
        out.test3_raw_figure,
        "Test 3: High Versus Low Project Starts",
        raw_series,
        "Monthly starts",
        y_min=0,
    )

    baseline = defaultdict(list)
    for row in monthly_rows:
        month = parse_date(str(row["month_start"]))
        if month.year == 2023:
            baseline["High"].append(float(row["high_c05_s3_count"]))
            baseline["Low strict"].append(float(row["low_strict_count"]))
    high_base = sum(baseline["High"]) / len(baseline["High"])
    low_base = sum(baseline["Low strict"]) / len(baseline["Low strict"])
    index_series = []
    for row in monthly_rows:
        index_series.append(
            {
                "month_start": row["month_start"],
                "value": 100 * float(row["high_c05_s3_count"]) / high_base if high_base else "",
                "label": "High",
            }
        )
        index_series.append(
            {
                "month_start": row["month_start"],
                "value": 100 * float(row["low_strict_count"]) / low_base if low_base else "",
                "label": "Low strict",
            }
        )
    make_svg_time_series(
        out.test3_indexed_figure,
        "Test 3: High Versus Low Indexed To 2023 Mean",
        index_series,
        "Index, 2023 monthly mean = 100",
        y_min=0,
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


def write_stata_do(out: Outputs) -> None:
    text = r'''version 18.0
clear all
set more off
capture log close _all

log using "../reports/project_entry2_stata_full.log", text replace

import delimited "../data/project_entry2_monthly.csv", clear
gen mdate = monthly(month, "YM")
format mdate %tm
tsset mdate
gen byte month_of_year_stata = month(dofm(mdate))

tempname handle
postfile `handle' str45 model_id str32 outcome str32 term double estimate std_error statistic p_value ci_low ci_high n_obs r_squared using "../data/project_entry2_stata_results_tmp.dta", replace
global PROJECT_ENTRY2_POST_HANDLE "`handle'"

program define _post_newey_rows
    args model_id outcome
    local terms "_cons time post_july2024 time_after_july2024 2.month_of_year_stata 3.month_of_year_stata 4.month_of_year_stata 5.month_of_year_stata 6.month_of_year_stata 7.month_of_year_stata 8.month_of_year_stata 9.month_of_year_stata 10.month_of_year_stata 11.month_of_year_stata 12.month_of_year_stata"
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
end

newey high_c05_s3_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test1_primary_high_c05_s3 high_c05_s3_count

newey high_c03_s3_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test1_robust_high_c03_s3 high_c03_s3_count

newey high_c05_s3_timing_cons_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test1_timing_conservative_high_c05_s3 high_c05_s3_timing_cons_count

newey high_share_classified_c05_s3 time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test2_primary_high_share_classified high_share_classified_c05_s3

newey high_share_all_c05_s3 time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test2_robust_high_share_all high_share_all_c05_s3

newey high_share_classified_c03_s3 time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test2_robust_c03_high_share_classified high_share_classified_c03_s3

newey high_c05_s3_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_high_c05_s3 high_c05_s3_count

newey low_strict_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_low_strict low_strict_count

newey not_high_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_not_high not_high_count

postclose `handle'
macro drop PROJECT_ENTRY2_POST_HANDLE
use "../data/project_entry2_stata_results_tmp.dta", clear
gen str24 stata_status = "STATA_EXECUTED"
export delimited "../reports/project_entry2_stata_regression_table.csv", replace

log close _all
'''
    write_text(out.stata_do, text)


def run_stata_if_available(out: Outputs, regression_rows: list[dict[str, object]]) -> str:
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
            "The committed project_entry2_its.do file and project_entry2_monthly.csv are Stata-ready. "
            "Python estimates are saved separately in data/project_entry2_regression_results.csv.\n",
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
        [exe, "-b", "do", str(out.stata_do.name)],
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
    high_n = int(counts["HIGH_C05_S3"]["count"])
    high_c03_n = int(counts["HIGH_C03_S3"]["count"])
    low_n = int(counts["LOW_STRICT"]["count"])
    s3_apps = int(counts["hs_s3_field"]["count"])
    c05_n = int(counts["hs_c05"]["count"])
    s3_only = int(counts["S3_ONLY"]["count"])
    c05_only = int(counts["C05_ONLY"]["count"])
    timing_high = int(counts["HIGH_C05_S3_TIMING_CONSERVATIVE"]["count"])

    t1 = report_key_line(regression_rows, "test1_primary_high_c05_s3")
    t1_c03 = report_key_line(regression_rows, "test1_robust_high_c03_s3")
    t2 = report_key_line(regression_rows, "test2_primary_high_share_classified")
    t2_all = report_key_line(regression_rows, "test2_robust_high_share_all")
    t3_high = report_key_line(regression_rows, "test3_high_c05_s3")
    t3_low = report_key_line(regression_rows, "test3_low_strict")
    t3_not_high = report_key_line(regression_rows, "test3_not_high")

    high_slope = float(term_row(regression_rows, "test3_high_c05_s3", "TimeAfterJuly2024")["estimate"])
    low_slope = float(term_row(regression_rows, "test3_low_strict", "TimeAfterJuly2024")["estimate"])
    faster = "high-sensitivity" if high_slope > low_slope else "strict low-sensitivity"

    write_text(
        out.measurement_note,
        f"""# Project Entry2 Measurement Note

## Sources

The project universe is `data/intermediate/timing_feasibility/timing_working_research_project_universe.csv`, which contains 6,935 projects with exact public Start dates.

Existing C03/C05 evidence comes from `data/intermediate/control_expansion/stage3_control_expansion_project_review.csv` and its evidence dictionary. C03 is layers C0-C3. C05 is layers C0-C5.

Field-tier evidence comes from UKB Schema 1 (`{classification_builder.SCHEMA1_URL}`) and cached public field pages under `data/source_snapshots/field_pages/`.

## Field-Tier Interpretation

Current Schema 1 exposes `cost_do`, `cost_on`, and `cost_sc` columns rather than one literal `tier` column. This pipeline reconstructs tier tokens from those columns: positive `cost_do` becomes `d#`, positive `cost_on` becomes `o#`, and positive `cost_sc` becomes `s#`. The parser validation case is field 25749, which reconstructs as `o2 s3` and links to applications 17689 and 22783.

`s3` is treated as the primary field-tier high-sensitivity proxy. `o2` is retained for broader robustness and audit; o2 alone is not part of the primary high-sensitivity definition.

## Historical Measurement Limitation

The Application x Field crosswalk is current public Showcase information. It may include later amendments and may not equal the field basket approved at the project Start date. For this reason the output includes `field_debut_after_project_start` and timing-conservative high definitions that exclude `s3` links where the field debut date is after the project's public Start date.

## Interpretation Limits

The public Start date is not observed application submission, approval, first RAP access, or first data-use timing. Field tier is a sensitivity/granularity proxy, not observed leakage risk. The ITS outputs are descriptive and comparative; they should not be described as causal RAP treatment effects.
""",
    )

    write_text(
        out.reading_guide,
        """# Project Entry2 Reading Guide

Start with `reports/project_entry2_results.md`, then inspect `data/project_high_sensitivity_classification.csv`, `data/project_entry2_monthly.csv`, and `data/project_entry2_regression_results.csv`.

The real Stata runner file is `scripts/project_entry2_its.do`. If no licensed Stata executable was available locally, `reports/project_entry2_stata_full.log` explicitly says `STATA_NOT_AVAILABLE_ON_RUNNER` and no Stata-like estimates are fabricated.
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

Primary window: 2019-01 through 2025-12. Breakpoint: July 2024.
""",
    )

    pre_high = pre_counts["HIGH_C05_S3"]["count"]
    post_high = post_counts["HIGH_C05_S3"]["count"]
    pre_low = pre_counts["LOW_STRICT"]["count"]
    post_low = post_counts["LOW_STRICT"]["count"]

    results = f"""# Project Entry2 Results

## A. What Is High Sensitivity?

Primary high sensitivity is `HIGH_C05_S3`: existing C05 RAP-intensive comparison evidence, explicit WES/WGS evidence, or at least one current UKB field-page link to an `s3` field. It is a proxy for higher-granularity or more sensitive data use, not observed leakage risk.

Project counts:

| Definition | N |
| --- | ---: |
| HIGH_C05_S3 | {high_n:,} |
| HIGH_C03_S3 | {high_c03_n:,} |
| HIGH_C05_S3_TIMING_CONSERVATIVE | {timing_high:,} |
| LOW_STRICT | {low_n:,} |
| hs_c05 | {c05_n:,} |
| hs_s3_field | {s3_apps:,} |
| S3_ONLY | {s3_only:,} |
| C05_ONLY | {c05_only:,} |

Pre/post counts use the exact policy date 2024-07-05 at the project level: HIGH_C05_S3 is {pre_high} pre-July-2024 and {post_high} post-July-2024; LOW_STRICT is {pre_low} pre-July-2024 and {post_low} post-July-2024.

The full audit files are `classification_counts.csv`, `classification_overlap.csv`, `field_tier_distribution.csv`, and `application_field_tier_links.csv`.

## B. Test 1 - High-Sensitivity Entry Count

Question: did the absolute number of high-sensitivity project starts change around/after July 2024?

Primary HIGH_C05_S3:

{compact_coef(regression_rows, "test1_primary_high_c05_s3")}

Key terms: {t1}.

C03+S3 robustness: {t1_c03}.

## C. Test 2 - High-Sensitivity Share

Question: did the composition of project entry shift toward high-sensitivity projects?

Primary denominator is `HIGH_C05_S3 + LOW_STRICT`; the all-start denominator is reported separately.

{compact_coef(regression_rows, "test2_primary_high_share_classified")}

Key terms: {t2}.

High/all robustness: {t2_all}.

## D. Test 3 - High Vs Low Partition

Question: was the post-transition trajectory stronger for high-sensitivity than for low-sensitivity project types?

High sensitivity: {t3_high}.

Strict low sensitivity: {t3_low}.

Inclusive NOT_HIGH robustness: {t3_not_high}.

The post-July slope change is {high_slope:.4f} for high-sensitivity starts and {low_slope:.4f} for strict low-sensitivity starts, so the descriptive post-transition trajectory grows faster for the {faster} series in this specification. Test 2 remains the formal composition test.

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
- `data/stata_python_replication_check.csv`
- `figures/figure_test1_high_sensitivity_entry.svg`
- `figures/figure_test2_high_sensitivity_share.svg`
- `figures/figure_test3_high_vs_low_raw.svg`
- `figures/figure_test3_high_vs_low_indexed.svg`
- `reports/project_entry2_stata_full.log`
- `reports/project_entry2_stata_regression_table.csv`

Stata status: `{stata_status}`.
"""
    write_text(out.results_report, results)


def validate_outputs(out: Outputs | None = None) -> None:
    out = out or Outputs()
    monthly = read_csv(out.monthly)
    if len(monthly) != 84:
        raise AssertionError(f"expected 84 monthly rows; found {len(monthly)}")
    if monthly[0]["month"] != "2019-01" or monthly[-1]["month"] != "2025-12":
        raise AssertionError("primary window month range changed")
    for row in monthly:
        high = int(row["high_c05_s3_count"])
        low = int(row["low_strict_count"])
        denom = int(row["classified_denom_c05_s3"])
        if denom != high + low:
            raise AssertionError(f"classified denominator mismatch in {row['month']}")
    regressions = read_csv(out.regression_results)
    terms = {(row["model_id"], row["term"]) for row in regressions}
    for model_id in ["test1_primary_high_c05_s3", "test2_primary_high_share_classified", "test3_low_strict"]:
        for term in ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024", "month_12"]:
            if (model_id, term) not in terms:
                raise AssertionError(f"missing {model_id} {term}")
    for path in [out.test1_figure, out.test2_figure, out.test3_raw_figure, out.test3_indexed_figure]:
        if not path.exists() or "<svg" not in path.read_text(encoding="utf-8")[:100]:
            raise AssertionError(f"missing or invalid figure {path}")
    if not out.stata_do.exists() or "newey" not in out.stata_do.read_text(encoding="utf-8"):
        raise AssertionError("Stata do-file missing newey regressions")


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
            "high_c05_s3_count",
            "high_c03_s3_count",
            "high_c05_s3_timing_cons_count",
            "low_strict_count",
            "not_high_count",
            "s3_only_count",
            "c05_only_count",
            "c05_or_s3_or_o2_count",
            "hs_s3_field_count",
            "hs_o2_field_count",
            "classified_denom_c05_s3",
            "high_share_classified_c05_s3",
            "high_share_all_c05_s3",
            "high_share_classified_c03_s3",
            "low_share_all",
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
    make_figures(monthly_rows, fits, out)
    stata_status = run_stata_if_available(out, regression_rows)
    write_reports(classification_rows, monthly_rows, regression_rows, stata_status, out)
    validate_outputs(out)
    return {
        "high_c05_s3": period_count(classification_rows, "HIGH_C05_S3"),
        "high_c03_s3": period_count(classification_rows, "HIGH_C03_S3"),
        "low_strict": period_count(classification_rows, "LOW_STRICT"),
        "s3_apps": period_count(classification_rows, "hs_s3_field"),
        "s3_only": period_count(classification_rows, "S3_ONLY"),
        "stata_status": stata_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-classification", action="store_true")
    parser.add_argument("--refresh-schema", action="store_true")
    parser.add_argument("--refresh-field-pages", action="store_true")
    parser.add_argument("--no-fetch-field-pages", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    args = parser.parse_args()
    summary = build_project_entry2_outputs(
        rebuild_classification=not args.skip_classification,
        refresh_schema=args.refresh_schema,
        refresh_field_pages=args.refresh_field_pages,
        no_fetch_field_pages=args.no_fetch_field_pages,
        sleep_seconds=args.sleep_seconds,
    )
    print(
        "project-entry2 analysis built: "
        f"{summary['high_c05_s3']} HIGH_C05_S3, "
        f"{summary['low_strict']} LOW_STRICT, "
        f"Stata status {summary['stata_status']}"
    )


if __name__ == "__main__":
    main()
