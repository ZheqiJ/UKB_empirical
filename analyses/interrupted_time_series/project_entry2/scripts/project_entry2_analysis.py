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
    stata_style_python_table: Path = REPORT_DIR / "project_entry2_stata_style_regression_results.txt"
    reading_guide: Path = REPORT_DIR / "project_entry2_reading_guide.md"
    measurement_note: Path = REPORT_DIR / "project_entry2_measurement_note.md"
    results_report: Path = REPORT_DIR / "project_entry2_results.md"
    test1_figure: Path = FIGURE_DIR / "figure_test1_high_sensitivity_entry.svg"
    test2_figure: Path = FIGURE_DIR / "figure_test2_high_sensitivity_share.svg"
    test3_raw_figure: Path = FIGURE_DIR / "figure_test3_high_vs_low_raw.svg"
    test3_indexed_figure: Path = FIGURE_DIR / "figure_test3_high_vs_low_indexed.svg"


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
            "test3_difference_index_pre_mean",
            "Test 3 indexed difference",
            "index_diff_pre_mean",
            "Index_H - Index_L",
            "full pre-transition monthly mean",
        ),
        (
            "test3_high_sensitivity_count",
            "Test 3 component",
            "high_sensitivity_count",
            "HIGH_SENSITIVITY",
            "",
        ),
        (
            "test3_lower_sensitivity_count",
            "Test 3 component",
            "lower_sensitivity_count",
            "LOWER_SENSITIVITY_COMPARISON",
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
        "Observed high/all share": ("#24536b", "", 2.4),
        "Fitted high/all share": ("#24536b", "6 4", 2.4),
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
        fits["test1_high_sensitivity_count"],
        "high_sensitivity_count",
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
        fits["test2_high_share_all"],
        "high_sensitivity_share_all",
        "Observed high/all share",
        "Fitted high/all share",
    )
    make_svg_time_series(
        out.test2_figure,
        "Test 2: High-Sensitivity Share",
        test2_series,
        "Share of all project starts that are high sensitivity",
        y_min=0,
        y_max=1,
        percent_axis=True,
    )

    raw_series = []
    for row in monthly_rows:
        raw_series.append({"month_start": row["month_start"], "value": row["high_sensitivity_count"], "label": "High"})
        raw_series.append({"month_start": row["month_start"], "value": row["lower_sensitivity_count"], "label": "Lower"})
    make_svg_time_series(
        out.test3_raw_figure,
        "Test 3: High Versus Lower Project Starts",
        raw_series,
        "Monthly starts",
        y_min=0,
    )

    index_series = []
    for row in monthly_rows:
        index_series.append(
            {
                "month_start": row["month_start"],
                "value": row["index_high_pre_mean"],
                "label": "High",
            }
        )
        index_series.append(
            {
                "month_start": row["month_start"],
                "value": row["index_lower_pre_mean"],
                "label": "Lower",
            }
        )
    make_svg_time_series(
        out.test3_indexed_figure,
        "Test 3: High Versus Lower Indexed To Full Pre-Transition Mean",
        index_series,
        "Index, pre-transition monthly mean = 100",
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


def model_n(regression_rows: list[dict[str, object]], model_id: str) -> int:
    row = next(row for row in regression_rows if row["model_id"] == model_id and row["term"] == "Intercept")
    return int(row["n_obs"])


def zero_month_preservation_check(
    monthly_rows: list[dict[str, object]],
    regression_rows: list[dict[str, object]],
) -> bool:
    by_month = {str(row["month"]): row for row in monthly_rows}
    required_n = {
        "test1_high_sensitivity_count": 84,
        "test3_high_sensitivity_count": 84,
        "test3_lower_sensitivity_count": 84,
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

newey index_diff_pre_mean time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_difference_index_pre_mean index_diff_pre_mean

newey high_sensitivity_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_high_sensitivity_count high_sensitivity_count

newey lower_sensitivity_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_lower_sensitivity_count lower_sensitivity_count

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
        "test3_difference_index_pre_mean": (
            "newey index_diff_pre_mean time post_july2024 "
            "time_after_july2024 i.month_of_year_stata, lag(3)"
        ),
        "test3_high_sensitivity_count": (
            "newey high_sensitivity_count time post_july2024 "
            "time_after_july2024 i.month_of_year_stata, lag(3)"
        ),
        "test3_lower_sensitivity_count": (
            "newey lower_sensitivity_count time post_july2024 "
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
        "Source estimates: data/project_entry2_regression_results.csv",
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

    t1 = report_key_line(regression_rows, "test1_high_sensitivity_count")
    t2 = report_key_line(regression_rows, "test2_high_share_all")
    t3_diff = report_key_line(regression_rows, "test3_difference_index_pre_mean")
    t3_high = report_key_line(regression_rows, "test3_high_sensitivity_count")
    t3_lower = report_key_line(regression_rows, "test3_lower_sensitivity_count")

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

## D. Test 3 - Indexed High Vs Lower Difference

Question: was the post-transition trajectory stronger for high-sensitivity than for low-sensitivity project types?

Primary formal test: `D_t = Index_H,t - Index_L,t`, where both indexes use the full pre-transition monthly mean as 100.

{compact_coef(regression_rows, "test3_difference_index_pre_mean")}

Difference key terms: {t3_diff}.

Raw High component: {t3_high}.

Raw Lower component: {t3_lower}.

The indexed figure uses the full pre-transition mean. `index_high_2023_mean` and `index_lower_2023_mean` remain in the monthly CSV as a visual check.

Zero-month preservation check: {zero_check}. Test 1, Test 3 High count, and Test 3 Lower count each retain 84 monthly observations.

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
- `reports/project_entry2_stata_style_regression_results.txt`
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
        "test3_difference_index_pre_mean",
        "test3_high_sensitivity_count",
        "test3_lower_sensitivity_count",
    ]:
        for term in ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024", "month_12"]:
            if (model_id, term) not in terms:
                raise AssertionError(f"missing {model_id} {term}")
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
    if "test3_difference_index_pre_mean" not in table_text:
        raise AssertionError("Stata-style table missing Test 3 difference model")


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
    write_stata_style_python_output(out, regression_rows)
    make_figures(monthly_rows, fits, out)
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
        f"{summary['high_sensitivity']} HIGH_SENSITIVITY, "
        f"{summary['lower_sensitivity']} LOWER_SENSITIVITY_COMPARISON, "
        f"Stata status {summary['stata_status']}"
    )


if __name__ == "__main__":
    main()
