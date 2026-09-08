#!/usr/bin/env python3
"""Build the within-High RAP-exposure comparative ITS analyses.

This is a descriptive comparison between an already-RAP-bound sequence proxy
and a higher-incremental-exposure proxy. It does not observe RAP use or
project-level migration dates and it does not alter the Project Entry2 Test 1-3
classification or outputs.
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
PROJECT_ENTRY2 = PACKAGE.parent
ROOT = PROJECT_ENTRY2.parents[2]
PROJECT_ENTRY2_SCRIPT_DIR = PROJECT_ENTRY2 / "scripts"
if str(PROJECT_ENTRY2_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_ENTRY2_SCRIPT_DIR))

import project_entry2_analysis as core


DATA_DIR = PACKAGE / "data"
REPORT_DIR = PACKAGE / "reports"
FIGURE_DIR = PACKAGE / "figures"
CLASSIFICATION_PATH = PROJECT_ENTRY2 / "data" / "project_high_sensitivity_classification.csv"
STAGE3_MATRIX_PATH = ROOT / "data" / "intermediate" / "rap_classification" / "stage3_modality_access_matrix.csv"

WINDOW_START_DATE = date(2021, 9, 28)
START_MONTH = date(2021, 9, 1)
END_MONTH = date(2026, 4, 1)
WINDOW_END_DATE = date(2026, 4, 30)
BREAK_MONTH = date(2024, 7, 1)
HAC_LAG = 3
CALENDAR_MONTHS = 56
SAMPLE_DATES_LABEL = "2021-09-28 through 2026-04"

SPECS = {
    "strict": {
        "label": "NEW_CITS_STRICT",
        "control_label": "Strict already-RAP-bound control proxy",
        "control_short": "Strict control",
        "description": "Strict already-RAP-bound control vs higher-exposure treatment",
    },
    "broad": {
        "label": "NEW_CITS_BROAD",
        "control_label": "Broad sequence control proxy",
        "control_short": "Broad control",
        "description": "Broad sequence control vs higher-exposure treatment",
    },
}

REGRESSION_FIELDS = [
    "specification",
    "model_id",
    "test",
    "outcome",
    "outcome_scale",
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
]


def parse_flag(row: dict[str, str], name: str) -> int:
    return int(row[name])


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise ZeroDivisionError("pre-transition mean is zero; normalized index is undefined")
    return 100.0 * numerator / denominator


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    core.write_csv(path, rows, fieldnames)


def write_text(path: Path, text: str) -> None:
    core.write_text(path, text)


def read_classification() -> list[dict[str, str]]:
    rows = core.read_csv(CLASSIFICATION_PATH)
    required = {
        "app_id",
        "start_date",
        "HIGH_SENSITIVITY",
        "hs_wes_wgs_sequence",
        "hs_s3_direct",
        "hs_s3_text",
    }
    if not rows or not required.issubset(rows[0]):
        raise AssertionError("project-level classification is missing required HIGH_SENSITIVITY fields")
    return rows


def validate_stage3_access_route() -> None:
    rows = core.read_csv(STAGE3_MATRIX_PATH)
    routes = {row["modality_family"]: row["pre_july_2024_access_route"] for row in rows}
    for modality in ["Whole exome sequencing (WES)", "Whole genome sequencing (WGS)"]:
        if routes.get(modality) != "already_rap_only":
            raise AssertionError(f"Stage 3 access-route matrix does not classify {modality} as already_rap_only")


def add_groups(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    audit_rows: list[dict[str, object]] = []
    for row in rows:
        if parse_flag(row, "HIGH_SENSITIVITY") != 1:
            continue
        sequence = parse_flag(row, "hs_wes_wgs_sequence")
        direct = parse_flag(row, "hs_s3_direct")
        text = parse_flag(row, "hs_s3_text")
        treatment = int(sequence == 0)
        control_broad = int(sequence == 1)
        control_strict = int(sequence == 1 and direct == 0 and text == 0)
        start = core.parse_date(row["start_date"])
        audit_rows.append(
            {
                "app_id": row["app_id"],
                "HIGH_SENSITIVITY": 1,
                "hs_wes_wgs_sequence": sequence,
                "hs_s3_direct": direct,
                "hs_s3_text": text,
                "treatment": treatment,
                "control_strict": control_strict,
                "control_broad": control_broad,
                "group_strict": "Treatment" if treatment else ("Strict control" if control_strict else "Excluded from strict control"),
                "group_broad": "Treatment" if treatment else "Broad control",
                "start_date": row["start_date"],
                "pre_post": "pre_july_2024" if start < BREAK_MONTH else "post_july_2024",
                "in_analysis_window": int(WINDOW_START_DATE <= start <= WINDOW_END_DATE),
            }
        )
    audit_rows.sort(key=lambda row: (str(row["start_date"]), int(row["app_id"])))
    return audit_rows


def group_counts(audit_rows: list[dict[str, object]]) -> dict[str, int]:
    return {
        "high_total": len(audit_rows),
        "treatment": sum(int(row["treatment"]) for row in audit_rows),
        "strict_control": sum(int(row["control_strict"]) for row in audit_rows),
        "broad_control": sum(int(row["control_broad"]) for row in audit_rows),
    }


def in_window_group_counts(audit_rows: list[dict[str, object]]) -> dict[str, int]:
    return {
        "treatment": sum(int(row["treatment"]) for row in audit_rows if int(row["in_analysis_window"]) == 1),
        "strict_control": sum(int(row["control_strict"]) for row in audit_rows if int(row["in_analysis_window"]) == 1),
        "broad_control": sum(int(row["control_broad"]) for row in audit_rows if int(row["in_analysis_window"]) == 1),
    }


def composition(rows: list[dict[str, object]]) -> dict[str, int]:
    direct = sum(int(row["hs_s3_direct"]) for row in rows)
    text = sum(int(row["hs_s3_text"]) for row in rows)
    both = sum(int(row["hs_s3_direct"]) and int(row["hs_s3_text"]) for row in rows)
    any_s3 = sum(int(row["hs_s3_direct"]) or int(row["hs_s3_text"]) for row in rows)
    return {
        "n": len(rows),
        "hs_s3_direct": direct,
        "hs_s3_text": text,
        "both": both,
        "any_s3": any_s3,
        "neither_s3": len(rows) - any_s3,
    }


def sample_rows(audit_rows: list[dict[str, object]], specification: str, group: str) -> list[dict[str, object]]:
    flag = "treatment" if group == "treatment" else f"control_{specification}"
    return [row for row in audit_rows if int(row[flag]) == 1]


def monthly_rows_for_spec(audit_rows: list[dict[str, object]], specification: str) -> list[dict[str, object]]:
    treatment_rows = sample_rows(audit_rows, specification, "treatment")
    control_rows = sample_rows(audit_rows, specification, "control")
    counts: dict[str, Counter[date]] = {
        "treatment": Counter(),
        "control": Counter(),
    }
    for group, rows in [("treatment", treatment_rows), ("control", control_rows)]:
        for row in rows:
            started = core.parse_date(str(row["start_date"]))
            month = date(started.year, started.month, 1)
            if WINDOW_START_DATE <= started <= WINDOW_END_DATE:
                counts[group][month] += 1

    months = core.month_range(START_MONTH, END_MONTH)
    pre_months = [month for month in months if month < BREAK_MONTH]
    treatment_pre_mean = sum(counts["treatment"][month] for month in pre_months) / len(pre_months)
    control_pre_mean = sum(counts["control"][month] for month in pre_months) / len(pre_months)
    output = []
    for time, month in enumerate(months, start=1):
        treatment_count = counts["treatment"][month]
        control_count = counts["control"][month]
        time_after = (
            (month.year - BREAK_MONTH.year) * 12 + month.month - BREAK_MONTH.month if month >= BREAK_MONTH else 0
        )
        output.append(
            {
                "specification": specification,
                "month": core.month_label(month),
                "month_start": month.isoformat(),
                "time": time,
                "post_july2024": int(month >= BREAK_MONTH),
                "time_after_july2024": time_after,
                "month_of_year": month.month,
                "treatment_count": treatment_count,
                "control_count": control_count,
                "treatment_pre_mean": core.fmt(treatment_pre_mean, 8),
                "control_pre_mean": core.fmt(control_pre_mean, 8),
                "treatment_index_pre_mean": core.fmt(safe_divide(treatment_count, treatment_pre_mean), 8),
                "control_index_pre_mean": core.fmt(safe_divide(control_count, control_pre_mean), 8),
                "index_diff_treatment_minus_control": core.fmt(
                    safe_divide(treatment_count, treatment_pre_mean) - safe_divide(control_count, control_pre_mean), 8
                ),
                "raw_diff_treatment_minus_control": treatment_count - control_count,
            }
        )
    if len(output) != CALENDAR_MONTHS:
        raise AssertionError(f"{specification} should have {CALENDAR_MONTHS} calendar months; found {len(output)}")
    return output


def stacked_rows(monthly_rows: list[dict[str, object]], specification: str) -> list[dict[str, object]]:
    output = []
    for row in monthly_rows:
        shared = {
            field: row[field]
            for field in ["specification", "month", "month_start", "time", "post_july2024", "time_after_july2024", "month_of_year"]
        }
        output.append(
            {
                **shared,
                "group": "Control",
                "treated": 0,
                "raw_count": row["control_count"],
                "entry_index_pre_mean": row["control_index_pre_mean"],
            }
        )
        output.append(
            {
                **shared,
                "group": "Treatment",
                "treated": 1,
                "raw_count": row["treatment_count"],
                "entry_index_pre_mean": row["treatment_index_pre_mean"],
            }
        )
    return output


def model_rows(
    monthly_rows: list[dict[str, object]], specification: str, scale: str
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    if scale == "normalized":
        control_outcome = "control_index_pre_mean"
        treatment_outcome = "treatment_index_pre_mean"
        difference_outcome = "index_diff_treatment_minus_control"
        denominator = "each group's full pre-July-2024 monthly mean"
    elif scale == "raw":
        control_outcome = "control_count"
        treatment_outcome = "treatment_count"
        difference_outcome = "raw_diff_treatment_minus_control"
        denominator = "raw monthly project counts"
    else:
        raise ValueError(scale)
    prefix = f"new_cits_{specification}_{scale}"
    specifications = [
        (f"{prefix}_control", "Control series", control_outcome, "sequence control proxy"),
        (f"{prefix}_treatment", "Treatment series", treatment_outcome, "higher-incremental-exposure proxy"),
        (f"{prefix}_treatment_minus_control", "Treatment-minus-Control difference series", difference_outcome, "Treatment - Control"),
    ]
    output: list[dict[str, object]] = []
    fits: dict[str, dict[str, object]] = {}
    for model_id, test, outcome, definition in specifications:
        rows, fit = core.run_model(
            monthly_rows,
            outcome,
            model_id,
            test,
            definition,
            denominator,
        )
        for row in rows:
            row["specification"] = specification
            row["outcome_scale"] = scale
            row["sample_dates"] = SAMPLE_DATES_LABEL
        output.extend(rows)
        fits[model_id] = fit
    return output, fits


def coefficient_row(rows: list[dict[str, object]], model_id: str, term: str) -> dict[str, object]:
    return next(row for row in rows if row["model_id"] == model_id and row["term"] == term)


def result_from_regression_row(row: dict[str, object]) -> dict[str, object]:
    return {key: row[key] for key in ["estimate", "std_error", "p_value", "ci_low", "ci_high"]}


def interaction_and_partition_rows(
    regression_rows: list[dict[str, object]], fits: dict[str, dict[str, object]], specification: str, scale: str
) -> list[dict[str, object]]:
    prefix = f"new_cits_{specification}_{scale}"
    control_model = f"{prefix}_control"
    treatment_model = f"{prefix}_treatment"
    difference_model = f"{prefix}_treatment_minus_control"
    parameter_map = [
        ("beta0", "Intercept", "_cons", control_model, "Intercept", "Control-series regression"),
        ("beta1", "Time", "Time", control_model, "Time", "Control-series regression"),
        ("beta2", "PostJuly2024", "PostJuly2024", control_model, "PostJuly2024", "Control-series regression"),
        ("beta3", "TimeAfterJuly2024", "TimeAfterJuly2024", control_model, "TimeAfterJuly2024", "Control-series regression"),
        ("delta0", "Treated", "Treated", difference_model, "Intercept", "Treatment-minus-Control difference regression"),
        ("delta1", "Treated x Time", "Treated x Time", difference_model, "Time", "Treatment-minus-Control difference regression"),
        ("delta2", "Treated x PostJuly2024", "Treated x PostJuly2024", difference_model, "PostJuly2024", "Treatment-minus-Control difference regression"),
        ("delta3", "Treated x TimeAfterJuly2024", "Treated x TimeAfterJuly2024", difference_model, "TimeAfterJuly2024", "Treatment-minus-Control difference regression"),
    ]
    output = []
    for parameter, quantity, stata_term, model_id, term, source in parameter_map:
        source_row = coefficient_row(regression_rows, model_id, term)
        output.append(
            {
                "role": "interaction_coefficient",
                "quantity": quantity,
                "parameter": parameter,
                "stata_term": stata_term,
                "inference_source": source,
                **result_from_regression_row(source_row),
            }
        )
    combinations = [
        ("control_pre_slope", "Control pre slope", control_model, {"Time": 1.0}),
        ("control_post_slope", "Control post slope", control_model, {"Time": 1.0, "TimeAfterJuly2024": 1.0}),
        ("control_slope_change", "Control slope change", control_model, {"TimeAfterJuly2024": 1.0}),
        ("treatment_pre_slope", "Treatment pre slope", treatment_model, {"Time": 1.0}),
        ("treatment_post_slope", "Treatment post slope", treatment_model, {"Time": 1.0, "TimeAfterJuly2024": 1.0}),
        ("treatment_slope_change", "Treatment slope change", treatment_model, {"TimeAfterJuly2024": 1.0}),
        ("delta1", "Differential pre slope (delta1)", difference_model, {"Time": 1.0}),
        ("delta2", "Differential immediate change (delta2)", difference_model, {"PostJuly2024": 1.0}),
        ("delta3", "Differential slope change (delta3)", difference_model, {"TimeAfterJuly2024": 1.0}),
    ]
    for key, quantity, model_id, weights in combinations:
        output.append(
            {
                "role": "linear_combination",
                "quantity": quantity,
                "parameter": key,
                "stata_term": "",
                "inference_source": "Newey-West HAC from the named component series",
                **core.linear_combination(fits[model_id], weights),
            }
        )
    return output


def partition_lookup(rows: list[dict[str, object]], parameter: str) -> dict[str, object]:
    return next(row for row in rows if row["role"] == "linear_combination" and row["parameter"] == parameter)


def interaction_lookup(rows: list[dict[str, object]], parameter: str) -> dict[str, object]:
    return next(row for row in rows if row["role"] == "interaction_coefficient" and row["parameter"] == parameter)


def number(value: object, digits: int = 4) -> str:
    return f"{float(value):.{digits}f}"


def ci(row: dict[str, object], digits: int = 4) -> str:
    return f"[{number(row['ci_low'], digits)}, {number(row['ci_high'], digits)}]"


def escaped(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_svg(
    path: Path,
    title: str,
    rows: list[dict[str, object]],
    labels: list[str],
    y_label: str,
    reference_y: float | None = 100.0,
) -> None:
    width, height = 1080, 540
    ml, mr, mt, mb = 90, 230, 52, 66
    pw, ph = width - ml - mr, height - mt - mb
    months = core.month_range(START_MONTH, END_MONTH)
    values = [float(row["value"]) for row in rows]
    low = min(0.0, min(values))
    high = max(values)
    padding = (high - low) * 0.08 if high > low else 1.0
    low -= padding
    high += padding

    def x(month: date) -> float:
        return ml + months.index(month) / (len(months) - 1) * pw

    def y(value: float) -> float:
        return mt + (high - value) / (high - low) * ph

    style = {
        labels[0]: ("#b24a38", "", 2.4),
        labels[1]: ("#24536b", "", 2.4),
    }
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="28" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" font-weight="700">{escaped(title)}</text>',
    ]
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        value = low + frac * (high - low)
        yy = y(value)
        svg.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{width - mr}" y2="{yy:.1f}" stroke="#dedede"/>')
        svg.append(f'<text x="{ml - 10}" y="{yy + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#444">{value:.0f}</text>')
    for year in range(START_MONTH.year, END_MONTH.year + 1):
        tick_month = START_MONTH if year == START_MONTH.year else date(year, 1, 1)
        xx = x(tick_month)
        svg.append(f'<line x1="{xx:.1f}" y1="{mt}" x2="{xx:.1f}" y2="{height - mb}" stroke="#eeeeee"/>')
        svg.append(f'<text x="{xx:.1f}" y="{height - 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#444">{year}</text>')
    if reference_y is not None and low <= reference_y <= high:
        yy = y(reference_y)
        svg.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{width - mr}" y2="{yy:.1f}" stroke="#777" stroke-width="1.2" stroke-dasharray="2 5"/>')
        svg.append(f'<text x="{width - mr - 8}" y="{yy - 5:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="10" fill="#555">100</text>')
    break_x = x(BREAK_MONTH)
    svg.append(f'<line x1="{break_x:.1f}" y1="{mt}" x2="{break_x:.1f}" y2="{height - mb}" stroke="#111" stroke-width="2.2"/>')
    svg.append(f'<text x="{break_x + 7:.1f}" y="{mt + 16}" font-family="Arial, sans-serif" font-size="11" fill="#111">Jul 2024</text>')
    by_label: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for row in rows:
        by_label[str(row["label"])].append((core.parse_date(str(row["month_start"])), float(row["value"])))
    for index, label in enumerate(labels):
        color, dash, line_width = style[label]
        points = [(x(month), y(value)) for month, value in sorted(by_label[label])]
        points_text = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        svg.append(f'<polyline fill="none" stroke="{color}" stroke-width="{line_width}"{dash_attr} points="{points_text}"/>')
        if "Observed" in label:
            for px, py in points:
                svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.7" fill="{color}"/>')
        legend_y = mt + 8 + index * 22
        svg.append(f'<line x1="{width - mr + 28}" y1="{legend_y}" x2="{width - mr + 58}" y2="{legend_y}" stroke="{color}" stroke-width="{line_width}"{dash_attr}/>')
        svg.append(f'<text x="{width - mr + 66}" y="{legend_y + 4}" font-family="Arial, sans-serif" font-size="12" fill="#333">{escaped(label)}</text>')
    svg.append(f'<text x="20" y="{mt + ph / 2}" transform="rotate(-90 20 {mt + ph / 2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">{escaped(y_label)}</text>')
    svg.append(f'<text x="{ml}" y="{height - 8}" font-family="Arial, sans-serif" font-size="11" fill="#333">Vertical line marks the July 2024 breakpoint.</text>')
    svg.append("</svg>")
    write_text(path, "\n".join(svg))


def fit_by_month(fit: dict[str, object]) -> dict[str, float]:
    return {core.month_label(month): value for month, value in zip(fit["months"], fit["fitted"])}


def net_month_fe_fit(monthly_rows: list[dict[str, object]], fit: dict[str, object]) -> list[float]:
    coefficients = dict(zip(fit["names"], fit["beta"]))
    return [
        float(coefficients["Intercept"])
        + float(coefficients["Time"]) * float(row["time"])
        + float(coefficients["PostJuly2024"]) * float(row["post_july2024"])
        + float(coefficients["TimeAfterJuly2024"]) * float(row["time_after_july2024"])
        for row in monthly_rows
    ]


def make_figures(monthly_rows: list[dict[str, object]], fits: dict[str, dict[str, object]], specification: str) -> None:
    prefix = f"new_cits_{specification}_normalized"
    control_fit = fits[f"{prefix}_control"]
    treatment_fit = fits[f"{prefix}_treatment"]
    control_fitted = fit_by_month(control_fit)
    treatment_fitted = fit_by_month(treatment_fit)
    title_control = "Strict Control" if specification == "strict" else "Broad Control"
    observed_rows = []
    fitted_rows = []
    for row in monthly_rows:
        observed_rows.extend(
            [
                {"month_start": row["month_start"], "value": row["control_index_pre_mean"], "label": "Observed control"},
                {"month_start": row["month_start"], "value": row["treatment_index_pre_mean"], "label": "Observed treatment"},
            ]
        )
        fitted_rows.extend(
            [
                {"month_start": row["month_start"], "value": control_fitted[str(row["month"])], "label": "Fitted control"},
                {"month_start": row["month_start"], "value": treatment_fitted[str(row["month"])], "label": "Fitted treatment"},
            ]
        )
    make_svg(
        FIGURE_DIR / f"figure_{specification}_observed_entry_index.svg",
        f"New Comparative ITS: Treatment vs {title_control} - Observed Entry Index",
        observed_rows,
        ["Observed control", "Observed treatment"],
        "Entry index (pre-transition monthly mean = 100)",
    )
    make_svg(
        FIGURE_DIR / f"figure_{specification}_fitted_entry_index.svg",
        f"New Comparative ITS: Treatment vs {title_control} - Fitted Entry Index",
        fitted_rows,
        ["Fitted control", "Fitted treatment"],
        "Entry index (pre-transition monthly mean = 100)",
    )
    trend_rows = []
    for row, control_value, treatment_value in zip(
        monthly_rows, net_month_fe_fit(monthly_rows, control_fit), net_month_fe_fit(monthly_rows, treatment_fit)
    ):
        trend_rows.extend(
            [
                {"month_start": row["month_start"], "value": control_value, "label": "Fitted control"},
                {"month_start": row["month_start"], "value": treatment_value, "label": "Fitted treatment"},
            ]
        )
    make_svg(
        FIGURE_DIR / f"figure_{specification}_segmented_trends.svg",
        f"New Comparative ITS: Treatment vs {title_control} - Segmented Trends",
        trend_rows,
        ["Fitted control", "Fitted treatment"],
        "Entry index (month fixed effects netted out)",
        reference_y=100.0,
    )


def interaction_markdown_table(rows: list[dict[str, object]]) -> str:
    labels = [
        ("beta0", "Intercept"),
        ("beta1", "Time"),
        ("beta2", "PostJuly2024"),
        ("beta3", "TimeAfterJuly2024"),
        ("delta0", "Treated"),
        ("delta1", "Treated x Time"),
        ("delta2", "Treated x PostJuly2024"),
        ("delta3", "Treated x TimeAfterJuly2024"),
    ]
    lines = [
        "| Parameter | Term | Estimate | HAC SE | p-value | 95% CI |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for parameter, label in labels:
        row = interaction_lookup(rows, parameter)
        lines.append(f"| {parameter} | {label} | {number(row['estimate'])} | {number(row['std_error'])} | {number(row['p_value'])} | {ci(row)} |")
    return "\n".join(lines)


def stata_table(
    specification: str,
    rows: list[dict[str, object]],
    group_n: dict[str, int],
    in_window_n: dict[str, int],
) -> str:
    title = "Strict" if specification == "strict" else "Broad"
    labels = [
        ("beta0", "_cons"),
        ("beta1", "Time"),
        ("beta2", "PostJuly2024"),
        ("beta3", "TimeAfterJuly2024"),
        ("delta0", "Treated"),
        ("delta1", "Treated x Time"),
        ("delta2", "Treated x PostJuly2024"),
        ("delta3", "Treated x TimeAfterJuly2024"),
    ]
    lines = [
        f"{title} specification: Treatment vs {SPECS[specification]['control_short']}",
        "",
        "------------------------------------------------------------------------------",
        " entry_index | Coefficient   std. err.      z    P>|z|    [95% conf. interval]",
        "-------------+----------------------------------------------------------------",
    ]
    for parameter, label in labels:
        row = interaction_lookup(rows, parameter)
        estimate = float(row["estimate"])
        se = float(row["std_error"])
        z = estimate / se if se else math.nan
        lines.append(
            f"{label:>20} | {estimate:11.7f} {se:11.7f} {z:7.2f} {float(row['p_value']):8.4f}"
            f" [{float(row['ci_low']):10.7f}, {float(row['ci_high']):10.7f}]"
        )
    lines.extend(
        [
            "------------------------------------------------------------------------------",
            "Month FE                       = Yes",
            "Treated x Month FE             = Yes",
            f"Observations                   = {2 * CALENDAR_MONTHS} group-month observations",
            f"Calendar months                = {CALENDAR_MONTHS}",
            f"Treatment projects (definition) = {group_n['treatment']}",
            f"Treatment starts in window     = {in_window_n['treatment']}",
            f"Control projects (definition)  = {group_n[f'{specification}_control']}",
            f"Control starts in window       = {in_window_n[f'{specification}_control']}",
            f"HAC lag                        = {HAC_LAG}",
            "",
            "Linear combinations / interpretation",
            "------------------------------------------------------------------------------",
            " Quantity                         Estimate     SE    P>|z|    [95% conf. interval]",
        ]
    )
    for key, label in [
        ("control_pre_slope", "Control pre slope = beta1"),
        ("control_post_slope", "Control post slope = beta1 + beta3"),
        ("control_slope_change", "Control slope change = beta3"),
        ("treatment_pre_slope", "Treatment pre slope = beta1 + delta1"),
        ("treatment_post_slope", "Treatment post slope = beta1 + delta1 + beta3 + delta3"),
        ("treatment_slope_change", "Treatment slope change = beta3 + delta3"),
        ("delta3", "Differential slope change = delta3"),
    ]:
        row = partition_lookup(rows, key)
        lines.append(
            f" {label:<43} {float(row['estimate']):10.4f} {float(row['std_error']):8.4f} "
            f"{float(row['p_value']):8.4f} [{float(row['ci_low']):9.4f}, {float(row['ci_high']):9.4f}]"
        )
    delta3 = interaction_lookup(rows, "delta3")
    lines.extend(
        [
            "",
            "Main hypothesis: H0: delta3 = 0",
            f"delta3 = {float(delta3['estimate']):.7f}; SE = {float(delta3['std_error']):.7f}; "
            f"p = {float(delta3['p_value']):.7f}; 95% CI = [{float(delta3['ci_low']):.7f}, {float(delta3['ci_high']):.7f}]",
        ]
    )
    return "\n".join(lines)


def report_comparison_table(strict: list[dict[str, object]], broad: list[dict[str, object]]) -> str:
    line_items = [
        ("Control pre slope", "control_pre_slope"),
        ("Control post slope", "control_post_slope"),
        ("Control slope change", "control_slope_change"),
        ("Treatment pre slope", "treatment_pre_slope"),
        ("Treatment post slope", "treatment_post_slope"),
        ("Treatment slope change", "treatment_slope_change"),
        ("delta1", "delta1"),
        ("delta2", "delta2"),
        ("delta3", "delta3"),
        ("SE(delta3)", "delta3_se"),
        ("95% CI(delta3)", "delta3_ci"),
        ("p(delta3)", "delta3_p"),
        ("H0 delta3=0 rejected?", "delta3_reject"),
    ]

    def value(rows: list[dict[str, object]], key: str) -> str:
        if key == "delta3_se":
            return number(interaction_lookup(rows, "delta3")["std_error"])
        if key == "delta3_ci":
            return ci(interaction_lookup(rows, "delta3"))
        if key == "delta3_p":
            return number(interaction_lookup(rows, "delta3")["p_value"])
        if key == "delta3_reject":
            return "Yes" if float(interaction_lookup(rows, "delta3")["p_value"]) < 0.05 else "No"
        return number(partition_lookup(rows, key)["estimate"])

    lines = ["| Quantity | STRICT | BROAD |", "| --- | ---: | ---: |"]
    for label, key in line_items:
        lines.append(f"| {label} | {value(strict, key)} | {value(broad, key)} |")
    return "\n".join(lines)


def write_reports(
    audit_rows: list[dict[str, object]],
    group_n: dict[str, int],
    in_window_n: dict[str, int],
    partitions: dict[str, list[dict[str, object]]],
    raw_partitions: dict[str, list[dict[str, object]]],
) -> None:
    strict, broad = partitions["strict"], partitions["broad"]
    strict_raw, broad_raw = raw_partitions["strict"], raw_partitions["broad"]
    treatment_comp = composition(sample_rows(audit_rows, "strict", "treatment"))
    strict_comp = composition(sample_rows(audit_rows, "strict", "control"))
    broad_comp = composition(sample_rows(audit_rows, "broad", "control"))
    excluded = [row for row in audit_rows if int(row["control_broad"]) == 1 and int(row["control_strict"]) == 0]
    excluded_comp = composition(excluded)
    strict_delta3 = interaction_lookup(strict, "delta3")
    broad_delta3 = interaction_lookup(broad, "delta3")
    strict_delta1 = interaction_lookup(strict, "delta1")
    broad_delta1 = interaction_lookup(broad, "delta1")
    strict_delta2 = interaction_lookup(strict, "delta2")
    broad_delta2 = interaction_lookup(broad, "delta2")
    raw_strict_delta3 = interaction_lookup(strict_raw, "delta3")
    raw_broad_delta3 = interaction_lookup(broad_raw, "delta3")
    delta3_change = float(broad_delta3["estimate"]) - float(strict_delta3["estimate"])

    strict_positive = float(strict_delta3["estimate"]) > 0
    broad_positive = float(broad_delta3["estimate"]) > 0
    strict_sig = float(strict_delta3["p_value"]) < 0.05
    broad_sig = float(broad_delta3["p_value"]) < 0.05
    same_sign = strict_positive == broad_positive
    report = f"""# New Comparative ITS: Within-High RAP-Exposure Comparative ITS

## Group Definitions

This is a descriptive comparative ITS within the existing `HIGH_SENSITIVITY` universe. It does not identify observed project-level RAP users, actual migration dates, RAP usage logs, or verified local-to-RAP transitions.

The treatment proxy is the higher incremental July-2024 RAP-exposure proxy: `HIGH_SENSITIVITY=1` and `hs_wes_wgs_sequence=0`. The control proxy is sequence-based because the Stage 3 access-route matrix classifies WES and WGS as `already_rap_only` before July 2024.

| Specification | Treatment definition N | Control definition N | Treatment starts in window | Control starts in window |
| --- | ---: | ---: | ---: | ---: |
| STRICT (`NEW_CITS_STRICT`) | {group_n['treatment']} | {group_n['strict_control']} | {in_window_n['treatment']} | {in_window_n['strict_control']} |
| BROAD (`NEW_CITS_BROAD`) | {group_n['treatment']} | {group_n['broad_control']} | {in_window_n['treatment']} | {in_window_n['broad_control']} |

The broad control includes {len(excluded)} sequence projects excluded from the strict control. Their exclusion reason is s3-type high-sensitivity evidence: `hs_s3_text=1` for all {len(excluded)}; `hs_s3_direct=1` for {excluded_comp['hs_s3_direct']}.

## Primary Normalized Comparative ITS

Each outcome is an entry index normalized to its own full pre-July-2024 monthly mean (`2021-09-28` through `2024-06` = 100). The model uses 56 calendar months from September 2021 through April 2026, month fixed effects, and Newey-West HAC lag 3. The September 2021 bin begins on September 28, so it is a deliberately truncated first month. July 2024 has `TimeAfterJuly2024=0`.

{report_comparison_table(strict, broad)}

The displayed interaction parameterization has Control as the reference group. The `beta` coefficients use the Control-series HAC inference; the `delta` coefficients use the Treatment-minus-Control normalized difference-series HAC inference. This is the algebraically equivalent three-series Newey-West implementation, rather than a built-in Stata `newey` regression on a stacked data set with duplicated monthly time values.

## Comparative Reading

1. Strict design: `delta3` is **{'positive' if strict_positive else 'not positive'}** ({number(strict_delta3['estimate'])}); it is **{'statistically significant' if strict_sig else 'not statistically significant'}** at 5% (p={number(strict_delta3['p_value'])}).
2. Broad design: `delta3` is **{'positive' if broad_positive else 'not positive'}** ({number(broad_delta3['estimate'])}); it is **{'statistically significant' if broad_sig else 'not statistically significant'}** at 5% (p={number(broad_delta3['p_value'])}).
3. The `delta3` sign is {'stable' if same_sign else 'not stable'} across the 427-vs-589 and 459-vs-589 comparisons. Including the {len(excluded)} mixed sequence+s3 projects changes `delta3` by {number(delta3_change)} index points per month.
4. Differential pre-trends (`delta1`) are {number(strict_delta1['estimate'])} in STRICT (p={number(strict_delta1['p_value'])}) and {number(broad_delta1['estimate'])} in BROAD (p={number(broad_delta1['p_value'])}).
5. Differential immediate level changes (`delta2`) are {number(strict_delta2['estimate'])} in STRICT (p={number(strict_delta2['p_value'])}) and {number(broad_delta2['estimate'])} in BROAD (p={number(broad_delta2['p_value'])}); `delta3` captures the gradual differential post-transition slope change.

When `delta3>0`, the descriptive reading is: the post-transition entry trajectory strengthened more for high-sensitivity project types with higher incremental exposure to the July 2024 RAP transition than for sequence-based projects whose relevant data were already RAP-only before the transition. This is not a causal DID estimate and does not show that treatment projects moved from local access to RAP.

## Raw-Count Robustness

Raw counts retain the same comparative ITS construction but measure absolute monthly starts, not relative trajectories from each group's historical baseline. They are a robustness output because the group sizes differ.

| Raw-count result | STRICT | BROAD |
| --- | ---: | ---: |
| delta3 | {number(raw_strict_delta3['estimate'])} | {number(raw_broad_delta3['estimate'])} |
| HAC SE(delta3) | {number(raw_strict_delta3['std_error'])} | {number(raw_broad_delta3['std_error'])} |
| p(delta3) | {number(raw_strict_delta3['p_value'])} | {number(raw_broad_delta3['p_value'])} |

## Figures

- [Strict observed entry index](../figures/figure_strict_observed_entry_index.svg)
- [Strict fitted entry index](../figures/figure_strict_fitted_entry_index.svg)
- [Broad observed entry index](../figures/figure_broad_observed_entry_index.svg)
- [Broad fitted entry index](../figures/figure_broad_fitted_entry_index.svg)
- [Strict segmented trends, month FE netted out](../figures/figure_strict_segmented_trends.svg)
- [Broad segmented trends, month FE netted out](../figures/figure_broad_segmented_trends.svg)
"""
    write_text(REPORT_DIR / "new_comparative_its_results.md", report)

    stata_text = f"""New Comparative ITS: Within-High RAP-Exposure Comparative ITS
Sample: 2021-09-28 through 2026-04; breakpoint: July 2024; normalized outcome: own pre-July-2024 monthly mean = 100. The 2021-09 monthly bin begins on 2021-09-28.

The displayed interaction tables are the stacked-model parameterization of the existing algebraically equivalent three-series Newey-West implementation. Beta coefficients come from the Control series and delta coefficients from the Treatment-minus-Control difference series. Built-in Stata newey was not run on a 112-row stacked data set with duplicate monthly time values.

{stata_table('strict', strict, group_n, in_window_n)}

{stata_table('broad', broad, group_n, in_window_n)}

Raw-count robustness (absolute monthly project-count trajectory)
------------------------------------------------------------------------------
Specification       delta3      std. err.      z    P>|z|    [95% conf. interval]
STRICT          {float(raw_strict_delta3['estimate']):11.7f} {float(raw_strict_delta3['std_error']):11.7f} {float(raw_strict_delta3['estimate']) / float(raw_strict_delta3['std_error']):7.2f} {float(raw_strict_delta3['p_value']):8.4f} [{float(raw_strict_delta3['ci_low']):10.7f}, {float(raw_strict_delta3['ci_high']):10.7f}]
BROAD           {float(raw_broad_delta3['estimate']):11.7f} {float(raw_broad_delta3['std_error']):11.7f} {float(raw_broad_delta3['estimate']) / float(raw_broad_delta3['std_error']):7.2f} {float(raw_broad_delta3['p_value']):8.4f} [{float(raw_broad_delta3['ci_low']):10.7f}, {float(raw_broad_delta3['ci_high']):10.7f}]

Stata executed: No. HAC estimates were produced by the repository's Python implementation used for the existing Project Entry2 Test 3 three-series analysis.
"""
    write_text(REPORT_DIR / "new_comparative_its_stata_style_results.txt", stata_text)

    audit_report = f"""# New Comparative ITS Group-Definition Audit

## Project-Level Counts

| Group | N | hs_s3_direct | hs_s3_text | both | any s3-type evidence | neither s3-type evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| HIGH_SENSITIVITY total | {group_n['high_total']} | {sum(int(row['hs_s3_direct']) for row in audit_rows)} | {sum(int(row['hs_s3_text']) for row in audit_rows)} | {sum(int(row['hs_s3_direct']) and int(row['hs_s3_text']) for row in audit_rows)} | {sum(int(row['hs_s3_direct']) or int(row['hs_s3_text']) for row in audit_rows)} | {sum(not (int(row['hs_s3_direct']) or int(row['hs_s3_text'])) for row in audit_rows)} |
| Treatment: non-sequence High sensitivity | {treatment_comp['n']} | {treatment_comp['hs_s3_direct']} | {treatment_comp['hs_s3_text']} | {treatment_comp['both']} | {treatment_comp['any_s3']} | {treatment_comp['neither_s3']} |
| Strict control: sequence, no s3 text/direct | {strict_comp['n']} | {strict_comp['hs_s3_direct']} | {strict_comp['hs_s3_text']} | {strict_comp['both']} | {strict_comp['any_s3']} | {strict_comp['neither_s3']} |
| Broad control: all sequence | {broad_comp['n']} | {broad_comp['hs_s3_direct']} | {broad_comp['hs_s3_text']} | {broad_comp['both']} | {broad_comp['any_s3']} | {broad_comp['neither_s3']} |
| Broad minus strict | {excluded_comp['n']} | {excluded_comp['hs_s3_direct']} | {excluded_comp['hs_s3_text']} | {excluded_comp['both']} | {excluded_comp['any_s3']} | {excluded_comp['neither_s3']} |

## Audit Checks

- Treatment intersect StrictControl: empty.
- Treatment intersect BroadControl: empty.
- StrictControl is a subset of BroadControl.
- BroadControl minus StrictControl contains the {excluded_comp['n']} sequence projects carrying s3-type evidence. In the current classification these are `hs_s3_text=1`; none has `hs_s3_direct=1`.
- Each specification retains 56 calendar months from 2021-09 through 2026-04, including monthly zeros. The first monthly bin begins on 2021-09-28.
- The treatment and control indices use the same pre-July-2024 calendar period, 2021-09-28 through 2024-06, while retaining each group's own mean as the denominator.

## Source Scope

The source is the existing project-level classification, not observed RAP usage. The Stage 3 modality-access matrix marks Whole exome sequencing (WES) and Whole genome sequencing (WGS) as `already_rap_only`; this motivates the sequence control as an already-RAP-bound proxy only.
"""
    write_text(REPORT_DIR / "group_definition_audit.md", audit_report)


def validate(
    audit_rows: list[dict[str, object]],
    group_n: dict[str, int],
    in_window_n: dict[str, int],
    monthly: dict[str, list[dict[str, object]]],
    partitions: dict[str, list[dict[str, object]]],
) -> None:
    treatment = {str(row["app_id"]) for row in audit_rows if int(row["treatment"]) == 1}
    strict = {str(row["app_id"]) for row in audit_rows if int(row["control_strict"]) == 1}
    broad = {str(row["app_id"]) for row in audit_rows if int(row["control_broad"]) == 1}
    if treatment & strict or treatment & broad:
        raise AssertionError("treatment must not overlap either control")
    if not strict < broad:
        raise AssertionError("strict control must be a proper subset of broad control")
    if group_n != {"high_total": 1048, "treatment": 589, "strict_control": 427, "broad_control": 459}:
        raise AssertionError(f"unexpected project-level group counts: {group_n}")
    if in_window_n != {"treatment": 380, "strict_control": 231, "broad_control": 255}:
        raise AssertionError(f"unexpected in-window group counts: {in_window_n}")
    mixed = [row for row in audit_rows if str(row["app_id"]) in broad - strict]
    if len(mixed) != 32 or any(int(row["hs_s3_direct"]) or not int(row["hs_s3_text"]) for row in mixed):
        raise AssertionError("broad-minus-strict must be the 32 sequence plus s3-text overlap projects")
    for specification, rows in monthly.items():
        if len(rows) != CALENDAR_MONTHS or len({row["month"] for row in rows}) != CALENDAR_MONTHS:
            raise AssertionError(f"{specification} lost a calendar month")
        july = next(row for row in rows if row["month"] == "2024-07")
        august = next(row for row in rows if row["month"] == "2024-08")
        if july["time_after_july2024"] != 0 or august["time_after_july2024"] != 1:
            raise AssertionError(f"{specification} uses the wrong July/August time-after convention")
        if not any(int(row["treatment_count"]) == 0 for row in rows):
            raise AssertionError(f"{specification} did not retain treatment zero months")
        if not any(int(row["control_count"]) == 0 for row in rows):
            raise AssertionError(f"{specification} did not retain control zero months")
        for key in ["delta1", "delta2", "delta3"]:
            row = interaction_lookup(partitions[specification], key)
            if not all(math.isfinite(float(row[field])) for field in ["estimate", "std_error", "p_value", "ci_low", "ci_high"]):
                raise AssertionError(f"{specification} {key} lacks finite HAC inference")
    for path in [
        DATA_DIR / "group_definition_audit.csv",
        DATA_DIR / "monthly_strict.csv",
        DATA_DIR / "monthly_broad.csv",
        DATA_DIR / "stacked_strict.csv",
        DATA_DIR / "stacked_broad.csv",
        DATA_DIR / "regression_results_strict.csv",
        DATA_DIR / "regression_results_broad.csv",
        DATA_DIR / "partition_results_strict.csv",
        DATA_DIR / "partition_results_broad.csv",
        DATA_DIR / "raw_partition_results_strict.csv",
        DATA_DIR / "raw_partition_results_broad.csv",
        DATA_DIR / "strict_vs_broad_comparison.csv",
        REPORT_DIR / "new_comparative_its_results.md",
        REPORT_DIR / "new_comparative_its_stata_style_results.txt",
        REPORT_DIR / "group_definition_audit.md",
        FIGURE_DIR / "figure_strict_observed_entry_index.svg",
        FIGURE_DIR / "figure_strict_fitted_entry_index.svg",
        FIGURE_DIR / "figure_broad_observed_entry_index.svg",
        FIGURE_DIR / "figure_broad_fitted_entry_index.svg",
        FIGURE_DIR / "figure_strict_segmented_trends.svg",
        FIGURE_DIR / "figure_broad_segmented_trends.svg",
    ]:
        if not path.exists() or path.stat().st_size == 0:
            raise AssertionError(f"missing output: {path}")


def main() -> None:
    validate_stage3_access_route()
    classification_rows = read_classification()
    audit_rows = add_groups(classification_rows)
    group_n = group_counts(audit_rows)
    in_window_n = in_window_group_counts(audit_rows)
    audit_fields = [
        "app_id",
        "HIGH_SENSITIVITY",
        "hs_wes_wgs_sequence",
        "hs_s3_direct",
        "hs_s3_text",
        "treatment",
        "control_strict",
        "control_broad",
        "group_strict",
        "group_broad",
        "start_date",
        "pre_post",
        "in_analysis_window",
    ]
    write_csv(DATA_DIR / "group_definition_audit.csv", audit_rows, audit_fields)

    monthly: dict[str, list[dict[str, object]]] = {}
    partitions: dict[str, list[dict[str, object]]] = {}
    raw_partitions: dict[str, list[dict[str, object]]] = {}
    comparison_rows = []
    for specification in SPECS:
        monthly_rows = monthly_rows_for_spec(audit_rows, specification)
        monthly[specification] = monthly_rows
        write_csv(
            DATA_DIR / f"monthly_{specification}.csv",
            monthly_rows,
            [
                "specification", "month", "month_start", "time", "post_july2024", "time_after_july2024", "month_of_year",
                "treatment_count", "control_count", "treatment_pre_mean", "control_pre_mean", "treatment_index_pre_mean",
                "control_index_pre_mean", "index_diff_treatment_minus_control", "raw_diff_treatment_minus_control",
            ],
        )
        write_csv(
            DATA_DIR / f"stacked_{specification}.csv",
            stacked_rows(monthly_rows, specification),
            ["specification", "month", "month_start", "time", "post_july2024", "time_after_july2024", "month_of_year", "group", "treated", "raw_count", "entry_index_pre_mean"],
        )
        regression_rows, fits = model_rows(monthly_rows, specification, "normalized")
        write_csv(DATA_DIR / f"regression_results_{specification}.csv", regression_rows, REGRESSION_FIELDS)
        partition_rows = interaction_and_partition_rows(regression_rows, fits, specification, "normalized")
        partitions[specification] = partition_rows
        partition_fields = ["role", "quantity", "parameter", "stata_term", "inference_source", "estimate", "std_error", "p_value", "ci_low", "ci_high"]
        write_csv(DATA_DIR / f"partition_results_{specification}.csv", partition_rows, partition_fields)
        raw_regression_rows, raw_fits = model_rows(monthly_rows, specification, "raw")
        raw_partition_rows = interaction_and_partition_rows(raw_regression_rows, raw_fits, specification, "raw")
        raw_partitions[specification] = raw_partition_rows
        write_csv(DATA_DIR / f"raw_partition_results_{specification}.csv", raw_partition_rows, partition_fields)
        make_figures(monthly_rows, fits, specification)

    for parameter in ["delta1", "delta2", "delta3"]:
        strict = interaction_lookup(partitions["strict"], parameter)
        broad = interaction_lookup(partitions["broad"], parameter)
        comparison_rows.append(
            {
                "quantity": parameter,
                "strict_estimate": strict["estimate"],
                "strict_std_error": strict["std_error"],
                "strict_p_value": strict["p_value"],
                "strict_ci_low": strict["ci_low"],
                "strict_ci_high": strict["ci_high"],
                "broad_estimate": broad["estimate"],
                "broad_std_error": broad["std_error"],
                "broad_p_value": broad["p_value"],
                "broad_ci_low": broad["ci_low"],
                "broad_ci_high": broad["ci_high"],
                "broad_minus_strict_estimate": core.fmt(float(broad["estimate"]) - float(strict["estimate"]), 8),
            }
        )
    write_csv(
        DATA_DIR / "strict_vs_broad_comparison.csv",
        comparison_rows,
        [
            "quantity", "strict_estimate", "strict_std_error", "strict_p_value", "strict_ci_low", "strict_ci_high",
            "broad_estimate", "broad_std_error", "broad_p_value", "broad_ci_low", "broad_ci_high", "broad_minus_strict_estimate",
        ],
    )
    write_reports(audit_rows, group_n, in_window_n, partitions, raw_partitions)
    validate(audit_rows, group_n, in_window_n, monthly, partitions)
    print(
        "new comparative ITS built: "
        f"treatment={group_n['treatment']}, strict_control={group_n['strict_control']}, broad_control={group_n['broad_control']}"
    )


if __name__ == "__main__":
    main()
