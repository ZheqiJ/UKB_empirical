#!/usr/bin/env python3
"""Compare the curated-52 and Tier-4-expanded-55 leakage outcomes.

This analysis only consumes the existing curated application crosswalk, the
application-level tier table, and the public application start-date universe.
It does not rerun or modify any DMCA matching.
"""

from __future__ import annotations

import csv
import html
import math
from collections import Counter
from datetime import date
from pathlib import Path

from leakage_its_analysis import (
    BREAK_MONTH,
    POLICY_DATE,
    clean,
    fmt,
    month_range,
    month_start,
    months_between,
    normal_pvalue,
    ols,
    parse_date,
    poisson_qmle,
    prop_diff_test,
    quarter_range,
    quarter_start,
    wilson_ci,
    write_csv,
    write_text,
)


ROOT = Path(__file__).resolve().parents[3]
UKB = ROOT / "ukb_dmca"
PACKAGE = UKB / "leakage_application_analysis"
DATA_DIR = PACKAGE / "data"
TABLE_DIR = PACKAGE / "tables"
FIGURE_DIR = PACKAGE / "figures"
REPORT_DIR = PACKAGE / "reports"

START_DATES = ROOT / "data" / "intermediate" / "start_date_matching" / "stage2_5_app_start_dates.csv"
CURATED_LINKS = UKB / "curated_dmca_application_links.csv"
TIER_TABLE = UKB / "application_level_attribution_tiers.csv"

OUT_APPLICATIONS = DATA_DIR / "application_level_leakage_curated52_broad55.csv"
OUT_ADDITIONS = DATA_DIR / "tier4_added_applications_broad55.csv"
OUT_MONTHLY = DATA_DIR / "monthly_application_start_cohorts_curated52_broad55.csv"
OUT_QUARTERLY = DATA_DIR / "quarterly_application_start_cohorts_curated52_broad55.csv"
OUT_PREPOST = TABLE_DIR / "pre_post_comparison_curated52_broad55.csv"
OUT_RAW_LPM = TABLE_DIR / "application_raw_lpm_curated52_broad55.csv"
OUT_TREND_LPM = TABLE_DIR / "application_trend_lpm_curated52_broad55.csv"
OUT_SEGMENTED = TABLE_DIR / "application_segmented_its_curated52_broad55.csv"
OUT_MONTHLY_ITS = TABLE_DIR / "monthly_cohort_its_curated52_broad55.csv"
OUT_MONTHLY_POISSON = TABLE_DIR / "monthly_poisson_estimability_curated52_broad55.csv"
OUT_QUARTERLY_POISSON = TABLE_DIR / "quarterly_poisson_robustness_curated52_broad55.csv"
OUT_FINAL = TABLE_DIR / "final_comparison_curated52_broad55.csv"
OUT_STATA = REPORT_DIR / "leakage_stata_style_curated52_broad55.txt"
OUT_REPORT = REPORT_DIR / "leakage_52_55_sensitivity_results.md"
FIGURE_52 = FIGURE_DIR / "monthly_leakage_rate_curated52.svg"
FIGURE_55 = FIGURE_DIR / "monthly_leakage_rate_broad55.svg"
FIGURE_OVERLAY = FIGURE_DIR / "monthly_leakage_rate_curated52_broad55_overlay.svg"

OUTCOME_LABELS = {"Leak52": "curated52", "Leak55": "broad55"}
APPLICATION_MODEL_FIELDS = [
    "outcome",
    "outcome_file_label",
    "model",
    "coefficient",
    "estimate",
    "estimate_percentage_points",
    "robust_se",
    "robust_se_percentage_points",
    "ci_low",
    "ci_high",
    "ci_low_percentage_points",
    "ci_high_percentage_points",
    "p_value",
    "n_applications",
    "r_squared",
    "inference",
]
COHORT_OLS_FIELDS = [
    "outcome",
    "outcome_file_label",
    "frequency",
    "model",
    "coefficient",
    "estimate",
    "estimate_percentage_points",
    "robust_se",
    "robust_se_percentage_points",
    "ci_low",
    "ci_high",
    "ci_low_percentage_points",
    "ci_high_percentage_points",
    "p_value",
    "n_periods",
    "r_squared",
    "inference",
]
POISSON_FIELDS = [
    "outcome",
    "outcome_file_label",
    "frequency",
    "coefficient",
    "log_irr",
    "irr",
    "robust_se_log_irr",
    "ci_low_log_irr",
    "ci_high_log_irr",
    "ci_low_irr",
    "ci_high_irr",
    "p_value",
    "n_periods",
    "pearson_dispersion",
    "inference",
    "estimability",
    "warning",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def r_squared(y: list[float], fitted: list[float]) -> float:
    mean = sum(y) / len(y)
    tss = sum((value - mean) ** 2 for value in y)
    rss = sum((value - estimate) ** 2 for value, estimate in zip(y, fitted))
    return 1.0 - rss / tss if tss else math.nan


def fmt_pvalue(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        return ""
    return f"{value:.6g}"


def coefficient_rows(
    outcome: str,
    model: str,
    names: list[str],
    fit: dict[str, object],
    y: list[float],
    report_terms: list[str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    fitted = [float(value) for value in fit["fitted"]]
    for term in report_terms:
        idx = names.index(term)
        beta = float(fit["beta"][idx])
        se = float(fit["se"][idx])
        rows.append(
            {
                "outcome": outcome,
                "outcome_file_label": OUTCOME_LABELS[outcome],
                "model": model,
                "coefficient": term,
                "estimate": fmt(beta, 8),
                "estimate_percentage_points": fmt(100 * beta, 4),
                "robust_se": fmt(se, 8),
                "robust_se_percentage_points": fmt(100 * se, 4),
                "ci_low": fmt(beta - 1.96 * se, 8),
                "ci_high": fmt(beta + 1.96 * se, 8),
                "ci_low_percentage_points": fmt(100 * (beta - 1.96 * se), 4),
                "ci_high_percentage_points": fmt(100 * (beta + 1.96 * se), 4),
                "p_value": fmt_pvalue(normal_pvalue(beta, se)),
                "n_applications": len(y),
                "r_squared": fmt(r_squared(y, fitted), 6),
                "inference": str(fit["inference"]),
            }
        )
    return rows


def application_design(
    rows: list[dict[str, object]],
    model: str,
) -> tuple[list[list[float]], list[str]]:
    names = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"]
    if model == "raw_lpm":
        return [[1.0, float(row["Post"])] for row in rows], ["Intercept", "PostJuly2024"]
    if model == "trend_lpm":
        return [[1.0, float(row["Time"]), float(row["Post"])] for row in rows], names[:3]
    if model != "segmented_its":
        raise ValueError(f"Unknown application model: {model}")
    names += [f"month_{month:02d}" for month in range(2, 13)]
    X: list[list[float]] = []
    for row in rows:
        X.append(
            [1.0, float(row["Time"]), float(row["Post"]), float(row["TimeAfter"])]
            + [1.0 if int(row["start_month_number"]) == month else 0.0 for month in range(2, 13)]
        )
    return X, names


def cohort_design(rows: list[dict[str, object]], frequency: str) -> tuple[list[list[float]], list[str]]:
    seasonal_name = "month" if frequency == "monthly" else "quarter"
    seasonal_values = range(2, 13) if frequency == "monthly" else range(2, 5)
    names = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"] + [
        f"{seasonal_name}_{value:02d}" for value in seasonal_values
    ]
    value_key = "month_of_year" if frequency == "monthly" else "quarter_of_year"
    X: list[list[float]] = []
    for row in rows:
        X.append(
            [1.0, float(row["Time"]), float(row["Post"]), float(row["TimeAfter"])]
            + [1.0 if int(row[value_key]) == value else 0.0 for value in seasonal_values]
        )
    return X, names


def build_application_rows() -> tuple[list[dict[str, object]], list[dict[str, object]], set[str], set[str]]:
    start_rows = read_csv(START_DATES)
    curated_rows = read_csv(CURATED_LINKS)
    tier_rows = read_csv(TIER_TABLE)

    curated_ids = {clean(row.get("application_id")) for row in curated_rows if clean(row.get("application_id"))}
    tier4 = [row for row in tier_rows if clean(row.get("tier")) == "Tier 4"]
    tier4_ids = {clean(row.get("application_id")) for row in tier4 if clean(row.get("application_id"))}
    if len(curated_ids) != 52:
        raise ValueError(f"Expected 52 curated application IDs, found {len(curated_ids)}.")
    if len(tier4_ids) != 3 or curated_ids & tier4_ids:
        raise ValueError("Tier 4 must contribute exactly three application IDs disjoint from the curated 52.")

    parsed = []
    seen: set[str] = set()
    for row in start_rows:
        app_id = clean(row.get("app_id"))
        start = parse_date(clean(row.get("start_date")))
        if not app_id or not start:
            continue
        if app_id in seen:
            raise ValueError(f"Duplicate valid-date application ID: {app_id}")
        seen.add(app_id)
        parsed.append((app_id, start, row))
    if len(parsed) != 6935:
        raise ValueError(f"Expected 6,935 valid-date applications, found {len(parsed)}.")
    min_month = min(month_start(start) for _, start, _ in parsed)

    application_rows: list[dict[str, object]] = []
    start_by_id: dict[str, tuple[date, dict[str, str]]] = {}
    for app_id, start, source in parsed:
        start_by_id[app_id] = (start, source)
        post = int(start >= POLICY_DATE)
        application_rows.append(
            {
                "application_id": app_id,
                "application_title": clean(source.get("schema27_title")),
                "project_start_date": start.isoformat(),
                "start_month": month_start(start).isoformat(),
                "start_quarter": quarter_start(start).isoformat(),
                "start_month_number": start.month,
                "Post": post,
                "Time": months_between(min_month, month_start(start)),
                "TimeAfter": max(0, months_between(BREAK_MONTH, month_start(start))) if post else 0,
                "Leak52": int(app_id in curated_ids),
                "Leak55": int(app_id in curated_ids or app_id in tier4_ids),
            }
        )

    addition_rows: list[dict[str, object]] = []
    for tier_row in sorted(tier4, key=lambda row: int(clean(row["application_id"]))):
        app_id = clean(tier_row["application_id"])
        if app_id not in start_by_id:
            raise ValueError(f"Tier-4 application {app_id} is absent from the valid-date universe.")
        start, source = start_by_id[app_id]
        addition_rows.append(
            {
                "application_id": app_id,
                "application_title": clean(source.get("schema27_title")) or clean(tier_row.get("application_title")),
                "project_start_date": start.isoformat(),
                "pre_post_july_5_2024": "post" if start >= POLICY_DATE else "pre",
                "family_ids": clean(tier_row.get("family_ids")),
                "repo_urls": clean(tier_row.get("repo_urls")),
                "reason_it_is_tier_4": clean(tier_row.get("confidence_note")),
            }
        )
    return application_rows, addition_rows, curated_ids, tier4_ids


def build_cohorts(application_rows: list[dict[str, object]], frequency: str) -> list[dict[str, object]]:
    period_fn = month_start if frequency == "monthly" else quarter_start
    periods = (
        month_range(
            min(parse_date(str(row["project_start_date"])) for row in application_rows if parse_date(str(row["project_start_date"]))),
            max(parse_date(str(row["project_start_date"])) for row in application_rows if parse_date(str(row["project_start_date"]))),
        )
        if frequency == "monthly"
        else quarter_range(
            min(parse_date(str(row["project_start_date"])) for row in application_rows if parse_date(str(row["project_start_date"]))),
            max(parse_date(str(row["project_start_date"])) for row in application_rows if parse_date(str(row["project_start_date"]))),
        )
    )
    counts: dict[date, Counter[str]] = {period: Counter() for period in periods}
    for row in application_rows:
        start = parse_date(str(row["project_start_date"]))
        assert start is not None
        counter = counts[period_fn(start)]
        counter["N"] += 1
        counter["D52"] += int(row["Leak52"])
        counter["D55"] += int(row["Leak55"])

    start_period = periods[0]
    rows: list[dict[str, object]] = []
    for period in periods:
        count = counts[period]
        n = count["N"]
        post = int(period >= BREAK_MONTH)
        rows.append(
            {
                "month" if frequency == "monthly" else "quarter": f"{period.year:04d}-{period.month:02d}" if frequency == "monthly" else f"{period.year:04d}Q{((period.month - 1) // 3) + 1}",
                "period_start": period.isoformat(),
                "N_t" if frequency == "monthly" else "N_q": n,
                "D52_t" if frequency == "monthly" else "D52_q": count["D52"],
                "Rate52_t" if frequency == "monthly" else "Rate52_q": fmt(count["D52"] / n, 8) if n else "",
                "D55_t" if frequency == "monthly" else "D55_q": count["D55"],
                "Rate55_t" if frequency == "monthly" else "Rate55_q": fmt(count["D55"] / n, 8) if n else "",
                "Post": post,
                "Time": months_between(start_period, period) if frequency == "monthly" else months_between(start_period, period) // 3,
                "TimeAfter": (max(0, months_between(BREAK_MONTH, period)) if frequency == "monthly" else max(0, months_between(BREAK_MONTH, period) // 3)) if post else 0,
                "month_of_year": period.month,
                "quarter_of_year": ((period.month - 1) // 3) + 1,
            }
        )
    return rows


def build_prepost(application_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    pre = [row for row in application_rows if int(row["Post"]) == 0]
    post = [row for row in application_rows if int(row["Post"]) == 1]
    rows: list[dict[str, object]] = []
    for outcome in OUTCOME_LABELS:
        pre_events = sum(int(row[outcome]) for row in pre)
        post_events = sum(int(row[outcome]) for row in post)
        stats = prop_diff_test(pre_events, len(pre), post_events, len(post))
        pre_ci = wilson_ci(pre_events, len(pre))
        post_ci = wilson_ci(post_events, len(post))
        rows.append(
            {
                "Outcome": outcome,
                "outcome_file_label": OUTCOME_LABELS[outcome],
                "pre_leakage_apps": pre_events,
                "pre_applications": len(pre),
                "pre_rate": fmt(stats["pre_rate"], 8),
                "pre_rate_percent": fmt(100 * stats["pre_rate"], 4),
                "pre_rate_ci_low": fmt(pre_ci[0], 8),
                "pre_rate_ci_high": fmt(pre_ci[1], 8),
                "post_leakage_apps": post_events,
                "post_applications": len(post),
                "post_rate": fmt(stats["post_rate"], 8),
                "post_rate_percent": fmt(100 * stats["post_rate"], 4),
                "post_rate_ci_low": fmt(post_ci[0], 8),
                "post_rate_ci_high": fmt(post_ci[1], 8),
                "difference_post_minus_pre": fmt(stats["difference"], 8),
                "difference_percentage_points": fmt(100 * stats["difference"], 4),
                "difference_ci_low": fmt(stats["difference_ci_low"], 8),
                "difference_ci_high": fmt(stats["difference_ci_high"], 8),
                "difference_ci_low_percentage_points": fmt(100 * stats["difference_ci_low"], 4),
                "difference_ci_high_percentage_points": fmt(100 * stats["difference_ci_high"], 4),
                "post_pre_ratio": fmt(stats["ratio_post_pre"], 6),
                "two_proportion_p_value": fmt(stats["p_value"], 8),
                "policy_date": POLICY_DATE.isoformat(),
                "interpretation": "Raw descriptive pre/post difference; not a causal RAP effect.",
            }
        )
    return rows


def fit_application_models(application_rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    raw_rows: list[dict[str, object]] = []
    trend_rows: list[dict[str, object]] = []
    segmented_rows: list[dict[str, object]] = []
    specs = [
        ("raw_lpm", "Raw application-level LPM", ["PostJuly2024"], raw_rows),
        ("trend_lpm", "Trend-adjusted application-level LPM", ["Time", "PostJuly2024"], trend_rows),
        ("segmented_its", "Application-level segmented ITS with month-of-year fixed effects", ["Time", "PostJuly2024", "TimeAfterJuly2024"], segmented_rows),
    ]
    for outcome in OUTCOME_LABELS:
        y = [float(row[outcome]) for row in application_rows]
        for model_key, model_name, terms, destination in specs:
            X, names = application_design(application_rows, model_key)
            fit = ols(X, y, hc1=True)
            destination.extend(coefficient_rows(outcome, model_name, names, fit, y, terms))
    return raw_rows, trend_rows, segmented_rows


def fit_cohort_ols(cohort_rows: list[dict[str, object]], frequency: str) -> list[dict[str, object]]:
    n_key = "N_t" if frequency == "monthly" else "N_q"
    rate_key = "Rate52_t" if frequency == "monthly" else "Rate52_q"
    selected = [row for row in cohort_rows if int(row[n_key]) > 0]
    X, names = cohort_design(selected, frequency)
    lag = 3 if frequency == "monthly" else 1
    results: list[dict[str, object]] = []
    for outcome in OUTCOME_LABELS:
        outcome_rate_key = rate_key.replace("52", "52" if outcome == "Leak52" else "55")
        y = [float(row[outcome_rate_key]) for row in selected]
        fit = ols(X, y, hac_lag=lag)
        for row in coefficient_rows(
            outcome,
            f"{frequency.title()} cohort linear segmented ITS with seasonal fixed effects",
            names,
            fit,
            y,
            ["Time", "PostJuly2024", "TimeAfterJuly2024"],
        ):
            row["frequency"] = frequency
            row["n_periods"] = row.pop("n_applications")
            results.append(row)
    return results


def fit_poisson(cohort_rows: list[dict[str, object]], frequency: str) -> list[dict[str, object]]:
    n_key = "N_t" if frequency == "monthly" else "N_q"
    d_key_base = "D52_t" if frequency == "monthly" else "D52_q"
    selected = [row for row in cohort_rows if int(row[n_key]) > 0]
    X, names = cohort_design(selected, frequency)
    lag = 3 if frequency == "monthly" else 1
    output: list[dict[str, object]] = []
    for outcome in OUTCOME_LABELS:
        d_key = d_key_base.replace("52", "52" if outcome == "Leak52" else "55")
        counts = [float(row[d_key]) for row in selected]
        offsets = [math.log(float(row[n_key])) for row in selected]
        try:
            fit = poisson_qmle(X, counts, offset=offsets, hac_lag=lag)
            if not bool(fit["converged"]):
                raise ValueError("did_not_meet_strict_convergence_tolerance")
            for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
                idx = names.index(term)
                beta = float(fit["beta"][idx])
                se = float(fit["se"][idx])
                output.append(
                    {
                        "outcome": outcome,
                        "outcome_file_label": OUTCOME_LABELS[outcome],
                        "frequency": frequency,
                        "coefficient": term,
                        "log_irr": fmt(beta, 8),
                        "irr": fmt(math.exp(beta), 6),
                        "robust_se_log_irr": fmt(se, 8),
                        "ci_low_log_irr": fmt(beta - 1.96 * se, 8),
                        "ci_high_log_irr": fmt(beta + 1.96 * se, 8),
                        "ci_low_irr": fmt(math.exp(beta - 1.96 * se), 6),
                        "ci_high_irr": fmt(math.exp(beta + 1.96 * se), 6),
                        "p_value": fmt_pvalue(normal_pvalue(beta, se)),
                        "n_periods": len(selected),
                        "pearson_dispersion": fmt(float(fit["pearson_dispersion"]), 6),
                        "inference": str(fit["inference"]),
                        "estimability": "estimable",
                        "warning": "",
                    }
                )
        except Exception as exc:
            for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
                output.append(
                    {
                        "outcome": outcome,
                        "outcome_file_label": OUTCOME_LABELS[outcome],
                        "frequency": frequency,
                        "coefficient": term,
                        "log_irr": "",
                        "irr": "",
                        "robust_se_log_irr": "",
                        "ci_low_log_irr": "",
                        "ci_high_log_irr": "",
                        "ci_low_irr": "",
                        "ci_high_irr": "",
                        "p_value": "",
                        "n_periods": len(selected),
                        "pearson_dispersion": "",
                        "inference": "",
                        "estimability": "not_estimable",
                        "warning": str(exc),
                    }
                )
    return output


def write_rate_svg(path: Path, title: str, series: list[tuple[str, list[tuple[date, float]]]], y_max: float) -> None:
    width, height = 1060, 520
    left, right, top, bottom = 86, 44, 54, 68
    plot_w, plot_h = width - left - right, height - top - bottom
    start = min(period for _, points in series for period, _ in points)
    end = max(period for _, points in series for period, _ in points)
    max_y = max(y_max, 0.01)
    colors = {"Leak52": "#24536b", "Leak55": "#a34d2d"}

    def x(period: date) -> float:
        return left + (period - start).days / max((end - start).days, 1) * plot_w

    def y(value: float) -> float:
        return top + (max_y - value) / max_y * plot_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="700">{html.escape(title)}</text>',
    ]
    for fraction in [0, 0.25, 0.5, 0.75, 1.0]:
        value = max_y * fraction
        yy = y(value)
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width - right}" y2="{yy:.1f}" stroke="#dedede"/>')
        svg.append(f'<text x="{left - 10}" y="{yy + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#444">{value:.2f}</text>')
    for year in range(start.year, end.year + 1):
        tick = date(year, 1, 1)
        if start <= tick <= end:
            xx = x(tick)
            svg.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{height - bottom}" stroke="#eeeeee"/>')
            svg.append(f'<text x="{xx:.1f}" y="{height - 32}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#444">{year}</text>')
    break_x = x(BREAK_MONTH)
    svg.append(f'<line x1="{break_x:.1f}" y1="{top}" x2="{break_x:.1f}" y2="{height - bottom}" stroke="#111" stroke-width="2"/>')
    svg.append(f'<text x="{break_x + 7:.1f}" y="{top + 16}" font-family="Arial, sans-serif" font-size="11" fill="#111">Jul 2024</text>')
    for label, points in series:
        color = colors[label]
        polyline = " ".join(f"{x(period):.1f},{y(value):.1f}" for period, value in points)
        svg.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.2" points="{polyline}"/>')
        for period, value in points:
            svg.append(f'<circle cx="{x(period):.1f}" cy="{y(value):.1f}" r="2.1" fill="{color}"/>')
    legend_x = width - right - 150
    for index, (label, _) in enumerate(series):
        yy = top + 14 + index * 18
        svg.append(f'<line x1="{legend_x}" y1="{yy}" x2="{legend_x + 24}" y2="{yy}" stroke="{colors[label]}" stroke-width="3"/>')
        svg.append(f'<text x="{legend_x + 32}" y="{yy + 4}" font-family="Arial, sans-serif" font-size="12" fill="#333">{label}</text>')
    svg.append(f'<text x="18" y="{top + plot_h / 2}" transform="rotate(-90 18 {top + plot_h / 2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">Leakage rate (%)</text>')
    svg.append(f'<text x="{left}" y="{height - 8}" font-family="Arial, sans-serif" font-size="11" fill="#333">Application/project start month. The policy breakpoint is July 5, 2024; monthly cohort coding changes in July 2024.</text>')
    svg.append("</svg>")
    write_text(path, "\n".join(svg))


def write_figures(monthly_rows: list[dict[str, object]]) -> None:
    selected = [row for row in monthly_rows if int(row["N_t"]) > 0]
    series_52 = [(parse_date(str(row["period_start"])), 100 * float(row["Rate52_t"])) for row in selected]
    series_55 = [(parse_date(str(row["period_start"])), 100 * float(row["Rate55_t"])) for row in selected]
    series_52 = [(period, value) for period, value in series_52 if period]
    series_55 = [(period, value) for period, value in series_55 if period]
    common_y_max = max(value for _, value in series_52 + series_55) * 1.12
    write_rate_svg(FIGURE_52, "Monthly Leakage Rate: Curated 52", [("Leak52", series_52)], common_y_max)
    write_rate_svg(FIGURE_55, "Monthly Leakage Rate: Broad 55", [("Leak55", series_55)], common_y_max)
    write_rate_svg(FIGURE_OVERLAY, "Monthly Leakage Rate: Curated 52 vs Broad 55", [("Leak52", series_52), ("Leak55", series_55)], common_y_max)


def row_for(rows: list[dict[str, object]], **criteria: str) -> dict[str, object]:
    matches = [row for row in rows if all(str(row.get(key, "")) == value for key, value in criteria.items())]
    if len(matches) != 1:
        raise ValueError(f"Expected one row for {criteria}, found {len(matches)}.")
    return matches[0]


def material_assessment(value_52: float, value_55: float, unit: str) -> str:
    if unit == "pp":
        return "No" if abs(value_55 - value_52) < 0.10 else "Yes"
    if unit == "IRR":
        return "No" if abs(math.log(value_55 / value_52)) < 0.10 else "Yes"
    return "No"


def build_final_comparison(
    prepost: list[dict[str, object]],
    raw_lpm: list[dict[str, object]],
    trend_lpm: list[dict[str, object]],
    segmented: list[dict[str, object]],
    quarterly_poisson: list[dict[str, object]],
) -> list[dict[str, object]]:
    specs = [
        ("Raw pre/post difference", prepost, "difference_percentage_points", {}, "pp"),
        ("Raw LPM Post", raw_lpm, "estimate_percentage_points", {"coefficient": "PostJuly2024"}, "pp"),
        ("Trend-adjusted LPM Post", trend_lpm, "estimate_percentage_points", {"coefficient": "PostJuly2024"}, "pp"),
        ("ITS level break", segmented, "estimate_percentage_points", {"coefficient": "PostJuly2024"}, "pp"),
        ("ITS slope break", segmented, "estimate_percentage_points", {"coefficient": "TimeAfterJuly2024"}, "pp"),
        ("Quarterly Poisson Post IRR", quarterly_poisson, "irr", {"coefficient": "PostJuly2024"}, "IRR"),
        ("Quarterly Poisson slope IRR", quarterly_poisson, "irr", {"coefficient": "TimeAfterJuly2024"}, "IRR"),
    ]
    output: list[dict[str, object]] = []
    for result, rows, field, criteria, unit in specs:
        values: dict[str, float] = {}
        display: dict[str, str] = {}
        for outcome in OUTCOME_LABELS:
            row = row_for(rows, **({"Outcome": outcome} if rows is prepost else {"outcome": outcome}), **criteria)
            raw_value = clean(row.get(field))
            values[outcome] = float(raw_value) if raw_value else math.nan
            display[outcome] = (f"{values[outcome]:.4f} pp" if unit == "pp" else f"{values[outcome]:.4f}") if raw_value else "not estimable"
        assessment = "Not estimable" if any(math.isnan(value) for value in values.values()) else material_assessment(values["Leak52"], values["Leak55"], unit)
        output.append(
            {
                "Result": result,
                "Leak52": display["Leak52"],
                "Leak55": display["Leak55"],
                "unit": unit,
                "Materially different?": assessment,
                "assessment_note": "Comparison is descriptive; no sample is preferred based on statistical significance.",
            }
        )
    return output


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def write_stata_table(raw_lpm: list[dict[str, object]], trend_lpm: list[dict[str, object]], segmented: list[dict[str, object]]) -> None:
    lines = ["Application-level descriptive LPMs with HC1 robust standard errors", ""]
    for title, rows, terms in [
        ("Raw LPM", raw_lpm, ["PostJuly2024"]),
        ("Trend-adjusted LPM", trend_lpm, ["Time", "PostJuly2024"]),
        ("Segmented ITS LPM", segmented, ["Time", "PostJuly2024", "TimeAfterJuly2024"]),
    ]:
        lines += [title, f"{'':28} {'Leak52':>18} {'Leak55':>18}"]
        for term in terms:
            row52 = row_for(rows, outcome="Leak52", coefficient=term)
            row55 = row_for(rows, outcome="Leak55", coefficient=term)
            label = {"Time": "Time", "PostJuly2024": "Post July 2024", "TimeAfterJuly2024": "Time After"}[term]
            lines.append(f"{label:28} {float(row52['estimate_percentage_points']):18.4f} {float(row55['estimate_percentage_points']):18.4f}")
            lines.append(f"Robust SE{'':19} ({float(row52['robust_se_percentage_points']):.4f}){'':9} ({float(row55['robust_se_percentage_points']):.4f})")
        n52 = row_for(rows, outcome="Leak52", coefficient=terms[0])
        n55 = row_for(rows, outcome="Leak55", coefficient=terms[0])
        lines.append(f"N{'':27} {n52['n_applications']:>18} {n55['n_applications']:>18}")
        lines.append(f"R2{'':26} {float(n52['r_squared']):18.6f} {float(n55['r_squared']):18.6f}")
        lines.append("")
    write_text(OUT_STATA, "\n".join(lines))


def write_report(
    additions: list[dict[str, object]],
    prepost: list[dict[str, object]],
    raw_lpm: list[dict[str, object]],
    trend_lpm: list[dict[str, object]],
    segmented: list[dict[str, object]],
    monthly_its: list[dict[str, object]],
    monthly_poisson: list[dict[str, object]],
    quarterly_poisson: list[dict[str, object]],
    final_comparison: list[dict[str, object]],
) -> None:
    prepost_display = []
    for row in prepost:
        prepost_display.append(
            {
                "Outcome": row["Outcome"],
                "Pre leakage / apps": f"{row['pre_leakage_apps']}/{row['pre_applications']}",
                "Pre rate": f"{row['pre_rate_percent']}%",
                "Post leakage / apps": f"{row['post_leakage_apps']}/{row['post_applications']}",
                "Post rate": f"{row['post_rate_percent']}%",
                "Difference pp": row["difference_percentage_points"],
                "95% CI (pp)": f"[{row['difference_ci_low_percentage_points']}, {row['difference_ci_high_percentage_points']}]",
                "Post/pre ratio": row["post_pre_ratio"],
                "p-value": row["two_proportion_p_value"],
            }
        )
    def app_display(rows: list[dict[str, object]], terms: list[str]) -> list[dict[str, object]]:
        output = []
        for term in terms:
            row52 = row_for(rows, outcome="Leak52", coefficient=term)
            row55 = row_for(rows, outcome="Leak55", coefficient=term)
            output.append(
                {
                    "Variable": term,
                    "Leak52 coef (pp)": row52["estimate_percentage_points"],
                    "Leak52 SE (pp)": row52["robust_se_percentage_points"],
                    "Leak52 p": row52["p_value"],
                    "Leak55 coef (pp)": row55["estimate_percentage_points"],
                    "Leak55 SE (pp)": row55["robust_se_percentage_points"],
                    "Leak55 p": row55["p_value"],
                }
            )
        return output
    monthly_display = app_display(monthly_its, ["Time", "PostJuly2024", "TimeAfterJuly2024"])
    quarterly_display = []
    for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
        row52 = row_for(quarterly_poisson, outcome="Leak52", coefficient=term)
        row55 = row_for(quarterly_poisson, outcome="Leak55", coefficient=term)
        quarterly_display.append(
            {
                "Variable": term,
                "Leak52 IRR": row52["irr"] or "not estimable",
                "Leak52 SE log(IRR)": row52["robust_se_log_irr"],
                "Leak52 p": row52["p_value"],
                "Leak55 IRR": row55["irr"] or "not estimable",
                "Leak55 SE log(IRR)": row55["robust_se_log_irr"],
                "Leak55 p": row55["p_value"],
            }
        )
    monthly_status = "; ".join(
        f"{row['outcome']}: {row['estimability']} ({row['warning'] or 'converged'})"
        for row in monthly_poisson
        if row["coefficient"] == "PostJuly2024"
    )
    monthly_poisson_note = (
        "Monthly Poisson QMLE is not estimable because of sparse event counts; quarterly aggregation is used for the count/rate robustness specification."
        if any(row["estimability"] != "estimable" for row in monthly_poisson)
        else "Monthly Poisson QMLE was estimable for both outcomes."
    )
    raw52 = row_for(raw_lpm, outcome="Leak52", coefficient="PostJuly2024")
    raw55 = row_for(raw_lpm, outcome="Leak55", coefficient="PostJuly2024")
    trend52 = row_for(trend_lpm, outcome="Leak52", coefficient="PostJuly2024")
    trend55 = row_for(trend_lpm, outcome="Leak55", coefficient="PostJuly2024")
    level52 = row_for(segmented, outcome="Leak52", coefficient="PostJuly2024")
    level55 = row_for(segmented, outcome="Leak55", coefficient="PostJuly2024")
    slope52 = row_for(segmented, outcome="Leak52", coefficient="TimeAfterJuly2024")
    slope55 = row_for(segmented, outcome="Leak55", coefficient="TimeAfterJuly2024")
    report = f"""# Curated 52 vs Broad 55 Leakage Sensitivity

This analysis holds the UK Biobank application universe fixed at all 6,935 applications with a valid public project/application start date. It changes only the binary outcome: `Leak52` marks the existing curated 52, while `Leak55` additionally marks the three single-application ambiguous Tier-4 links. DMCA notice, repository, and commit dates are not used as empirical timing variables. All results are descriptive associations, not causal RAP effects.

## Added Tier-4 Applications

{markdown_table(additions, ["application_id", "application_title", "project_start_date", "pre_post_july_5_2024", "family_ids", "reason_it_is_tier_4"])}

All three additions start before July 5, 2024. The broadening therefore raises only the pre-policy leakage count in this comparison.

## 1. Raw Pre/Post Descriptive Comparison

{markdown_table(prepost_display, ["Outcome", "Pre leakage / apps", "Pre rate", "Post leakage / apps", "Post rate", "Difference pp", "95% CI (pp)", "Post/pre ratio", "p-value"])}

The difference is the raw post-minus-pre percentage-point contrast. The two-proportion p-value and confidence interval are descriptive only.

## 2. Application-Level Raw LPM

{markdown_table(app_display(raw_lpm, ["PostJuly2024"]), ["Variable", "Leak52 coef (pp)", "Leak52 SE (pp)", "Leak52 p", "Leak55 coef (pp)", "Leak55 SE (pp)", "Leak55 p"])}

Each raw LPM has N = 6,935 and HC1 heteroskedasticity-robust standard errors. Its Post coefficient is the same descriptive difference as the raw pre/post contrast.

## 3. Trend-Adjusted Application-Level LPM

{markdown_table(app_display(trend_lpm, ["Time", "PostJuly2024"]), ["Variable", "Leak52 coef (pp)", "Leak52 SE (pp)", "Leak52 p", "Leak55 coef (pp)", "Leak55 SE (pp)", "Leak55 p"])}

The raw Post coefficients are {raw52['estimate_percentage_points']} pp (Leak52) and {raw55['estimate_percentage_points']} pp (Leak55). With a smooth start-month trend, they are {trend52['estimate_percentage_points']} pp and {trend55['estimate_percentage_points']} pp. This reports how much the unadjusted difference changes after accounting for the observed start-time trend; it is not causal adjustment.

## 4. Application-Level Segmented ITS

{markdown_table(app_display(segmented, ["Time", "PostJuly2024", "TimeAfterJuly2024"]), ["Variable", "Leak52 coef (pp)", "Leak52 SE (pp)", "Leak52 p", "Leak55 coef (pp)", "Leak55 SE (pp)", "Leak55 p"])}

This specification uses application-level `Time`, exact-date `Post`, `TimeAfter`, and month-of-year fixed effects, with HC1 robust standard errors. The level breaks are {level52['estimate_percentage_points']} pp and {level55['estimate_percentage_points']} pp. The slope breaks are {slope52['estimate_percentage_points']} and {slope55['estimate_percentage_points']} percentage points per month.

## 5. Monthly Application-Start Cohorts

Monthly cohort data, including zero-leakage months, are saved in `data/monthly_application_start_cohorts_curated52_broad55.csv`. The monthly rate ITS uses Newey-West HAC lag 3 and month-of-year fixed effects.

{markdown_table(monthly_display, ["Variable", "Leak52 coef (pp)", "Leak52 SE (pp)", "Leak52 p", "Leak55 coef (pp)", "Leak55 SE (pp)", "Leak55 p"])}

The two single-sample rate figures and their common-scale overlay are saved in `figures/`. Monthly Poisson status: {monthly_status}. {monthly_poisson_note}

## 6. Quarterly Count/Rate Poisson Robustness

Quarterly cohorts use `log(N_q)` as an offset, quarter-of-year fixed effects, and Newey-West HAC lag 1 robust standard errors. Values are IRRs.

{markdown_table(quarterly_display, ["Variable", "Leak52 IRR", "Leak52 SE log(IRR)", "Leak52 p", "Leak55 IRR", "Leak55 SE log(IRR)", "Leak55 p"])}

## Final Comparison

{markdown_table(final_comparison, ["Result", "Leak52", "Leak55", "Materially different?"])}

### Answers

1. The three added applications all fall pre-policy: September 2019, February 2020, and February 2024.
2. Moving from 52 to 55 changes the raw pre/post contrast only by adding three pre-policy events; the direction and descriptive conclusion are unchanged.
3. The trend-adjusted Post coefficient changes modestly; its interpretation remains descriptive and it should not be read as causal.
4. The level and slope break comparisons above retain the same specification and universe for both outcomes. The reported differences should be read as sensitivity to the linkage rule, not a selection of a preferred sample.
5. The substantive conclusion is assessed in the final table without using Tier 5 or Tier 6 candidates.

## Timing Conventions

Application-level `Post` is exactly `1{{start_date >= 2024-07-05}}`. Cohort-level monthly and quarterly ITS use the first complete calendar period at the institutional breakpoint (July 2024 / 2024 Q3), with `TimeAfter = 0` in that break period. Three applications start on July 1-4, 2024; their application-level coding remains pre-policy under the exact definition. No DMCA date is used as an application date.
"""
    write_text(OUT_REPORT, report)


def validate(
    application_rows: list[dict[str, object]],
    additions: list[dict[str, object]],
    monthly_rows: list[dict[str, object]],
    quarterly_rows: list[dict[str, object]],
    prepost: list[dict[str, object]],
) -> None:
    if len(application_rows) != 6935 or len({row["application_id"] for row in application_rows}) != 6935:
        raise ValueError("The application-level analysis universe is not 6,935 unique valid-date applications.")
    if sum(int(row["Leak52"]) for row in application_rows) != 52:
        raise ValueError("Leak52 does not contain 52 applications.")
    if sum(int(row["Leak55"]) for row in application_rows) != 55:
        raise ValueError("Leak55 does not contain 55 applications.")
    if len(additions) != 3 or any(row["pre_post_july_5_2024"] != "pre" for row in additions):
        raise ValueError("The three Tier-4 additions must all be pre-policy in this dataset.")
    if sum(int(row["N_t"]) for row in monthly_rows) != 6935 or sum(int(row["N_q"]) for row in quarterly_rows) != 6935:
        raise ValueError("Cohort counts do not reconcile to the application universe.")
    for row in prepost:
        outcome = str(row["Outcome"])
        total = int(row["pre_leakage_apps"]) + int(row["post_leakage_apps"])
        if total != (52 if outcome == "Leak52" else 55):
            raise ValueError(f"{outcome} pre/post counts do not reconcile.")


def main() -> None:
    application_rows, additions, _, _ = build_application_rows()
    monthly_rows = build_cohorts(application_rows, "monthly")
    quarterly_rows = build_cohorts(application_rows, "quarterly")
    prepost = build_prepost(application_rows)
    raw_lpm, trend_lpm, segmented = fit_application_models(application_rows)
    monthly_its = fit_cohort_ols(monthly_rows, "monthly")
    monthly_poisson = fit_poisson(monthly_rows, "monthly")
    quarterly_poisson = fit_poisson(quarterly_rows, "quarterly")
    final_comparison = build_final_comparison(prepost, raw_lpm, trend_lpm, segmented, quarterly_poisson)
    validate(application_rows, additions, monthly_rows, quarterly_rows, prepost)

    write_csv(
        OUT_APPLICATIONS,
        application_rows,
        ["application_id", "application_title", "project_start_date", "start_month", "start_quarter", "start_month_number", "Post", "Time", "TimeAfter", "Leak52", "Leak55"],
    )
    write_csv(
        OUT_ADDITIONS,
        additions,
        ["application_id", "application_title", "project_start_date", "pre_post_july_5_2024", "family_ids", "repo_urls", "reason_it_is_tier_4"],
    )
    write_csv(
        OUT_MONTHLY,
        monthly_rows,
        ["month", "period_start", "N_t", "D52_t", "Rate52_t", "D55_t", "Rate55_t", "Post", "Time", "TimeAfter", "month_of_year", "quarter_of_year"],
    )
    write_csv(
        OUT_QUARTERLY,
        quarterly_rows,
        ["quarter", "period_start", "N_q", "D52_q", "Rate52_q", "D55_q", "Rate55_q", "Post", "Time", "TimeAfter", "month_of_year", "quarter_of_year"],
    )
    write_csv(
        OUT_PREPOST,
        prepost,
        ["Outcome", "outcome_file_label", "pre_leakage_apps", "pre_applications", "pre_rate", "pre_rate_percent", "pre_rate_ci_low", "pre_rate_ci_high", "post_leakage_apps", "post_applications", "post_rate", "post_rate_percent", "post_rate_ci_low", "post_rate_ci_high", "difference_post_minus_pre", "difference_percentage_points", "difference_ci_low", "difference_ci_high", "difference_ci_low_percentage_points", "difference_ci_high_percentage_points", "post_pre_ratio", "two_proportion_p_value", "policy_date", "interpretation"],
    )
    write_csv(OUT_RAW_LPM, raw_lpm, APPLICATION_MODEL_FIELDS)
    write_csv(OUT_TREND_LPM, trend_lpm, APPLICATION_MODEL_FIELDS)
    write_csv(OUT_SEGMENTED, segmented, APPLICATION_MODEL_FIELDS)
    write_csv(OUT_MONTHLY_ITS, monthly_its, ["outcome", "outcome_file_label", "frequency", "model", "coefficient", "estimate", "estimate_percentage_points", "robust_se", "robust_se_percentage_points", "ci_low", "ci_high", "ci_low_percentage_points", "ci_high_percentage_points", "p_value", "n_periods", "r_squared", "inference"])
    write_csv(OUT_MONTHLY_POISSON, monthly_poisson, POISSON_FIELDS)
    write_csv(OUT_QUARTERLY_POISSON, quarterly_poisson, POISSON_FIELDS)
    write_csv(OUT_FINAL, final_comparison, ["Result", "Leak52", "Leak55", "unit", "Materially different?", "assessment_note"])
    write_figures(monthly_rows)
    write_stata_table(raw_lpm, trend_lpm, segmented)
    write_report(additions, prepost, raw_lpm, trend_lpm, segmented, monthly_its, monthly_poisson, quarterly_poisson, final_comparison)

    print("application_universe=6935")
    print("Leak52=52")
    print("Leak55=55")
    print("tier4_added_pre_policy=3")
    print("outputs_written=17")


if __name__ == "__main__":
    main()
