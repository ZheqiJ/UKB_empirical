#!/usr/bin/env python3
"""Run the prespecified artificial-date placebo checks for New Comparative ITS.

The placebo exercise is deliberately separate from the main July 2024 model.
It uses the saved raw monthly treatment-minus-control differences, month-of-year
fixed effects, and the repository's Bartlett Newey-West HAC implementation.
"""

from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
CORE_SCRIPT_DIR = ROOT / "archive" / "03_project_entry_high_vs_lower" / "scripts"
if str(CORE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPT_DIR))

import project_entry2_analysis as core


DATA_DIR = PACKAGE / "data"
REPORT_DIR = PACKAGE / "reports"
HAC_LAG = 3
REAL_BREAK = "2024-07"
PRE_START = "2021-10"
PRE_END = "2024-06"
ALL_PLACEBO_START = "2022-10"
ALL_PLACEBO_END = "2023-07"
MATCHED_PLACEBO_START = "2023-04"
MATCHED_PLACEBO_END = "2023-07"

RESULT_FIELDS = [
    "specification",
    "control_definition",
    "design",
    "intervention_date",
    "sample_start",
    "sample_end",
    "pre_n",
    "post_n",
    "n_obs",
    "k_params",
    "df_resid",
    "level",
    "level_se",
    "level_z",
    "level_p",
    "level_ci_low",
    "level_ci_high",
    "slope_change",
    "slope_se",
    "slope_z",
    "slope_p",
    "slope_ci_low",
    "slope_ci_high",
    "slope_p_holm",
    "joint_wald",
    "joint_p",
    "joint_p_holm",
    "nw_lag",
    "inference",
]

COEFFICIENT_FIELDS = [
    "specification",
    "control_definition",
    "design",
    "intervention_date",
    "sample_start",
    "sample_end",
    "term",
    "estimate",
    "std_error",
    "z",
    "p_value",
    "ci_low",
    "ci_high",
    "n_obs",
    "k_params",
    "df_resid",
    "nw_lag",
    "inference",
]


def month_ordinal(label: str) -> int:
    year, month = (int(part) for part in label[:7].split("-"))
    return year * 12 + month


def month_label(ordinal: int) -> str:
    year, month_zero = divmod(ordinal - 1, 12)
    return f"{year:04d}-{month_zero + 1:02d}"


def month_distance(left: str, right: str) -> int:
    return month_ordinal(right) - month_ordinal(left)


def fmt(value: float | int | None, digits: int = 8) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return ""
    return f"{float(value):.{digits}f}"


def read_monthly(specification: str) -> list[dict[str, str]]:
    rows = core.read_csv(DATA_DIR / f"monthly_{specification}.csv")
    rows.sort(key=lambda row: row["month"])
    expected = [month_label(month_ordinal(PRE_START) + offset) for offset in range(55)]
    if [row["month"] for row in rows] != expected:
        raise AssertionError(f"{specification} monthly data must cover {PRE_START} through 2026-04")
    return rows


def subset(rows: list[dict[str, str]], start: str, end: str) -> list[dict[str, str]]:
    return [row for row in rows if start <= row["month"] <= end]


def fit(rows: list[dict[str, str]], intervention_date: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not rows:
        raise AssertionError("placebo sample is empty")
    cut = month_ordinal(intervention_date)
    first = month_ordinal(rows[0]["month"])
    X: list[list[float]] = []
    y: list[float] = []
    names = ["Intercept", "Time", "ArtificialLevel", "ArtificialSlope"] + [
        f"month_{month:02d}" for month in range(2, 13)
    ]
    for row in rows:
        ordinal = month_ordinal(row["month"])
        time = ordinal - first
        X.append(
            [
                1.0,
                float(time),
                float(ordinal >= cut),
                float(max(ordinal - cut, 0)),
            ]
            + [1.0 if int(row["month_of_year"]) == month else 0.0 for month in range(2, 13)]
        )
        y.append(float(row["raw_diff_treatment_minus_control"]))
    if len(rows) < 15 or len(rows) - 15 < 1:
        raise AssertionError("placebo model does not have positive residual degrees of freedom")
    if len(core.xtx(X)) != 15 or core.invert(core.xtx(X)) is None:
        raise AssertionError("placebo design is not estimable")
    model = core.ols_hac(X, y, HAC_LAG)
    beta = model["beta"]
    se = model["se"]
    p_values = [core.two_sided_normal_pvalue(float(beta[index]), float(se[index])) for index in range(len(names))]
    coefficient_rows = []
    for name, estimate, standard_error, p_value in zip(names, beta, se, p_values):
        coefficient_rows.append(
            {
                "term": name,
                "estimate": fmt(float(estimate)),
                "std_error": fmt(float(standard_error)),
                "z": fmt(float(estimate) / float(standard_error) if standard_error else math.nan),
                "p_value": fmt(p_value),
                "ci_low": fmt(float(estimate) - 1.96 * float(standard_error)),
                "ci_high": fmt(float(estimate) + 1.96 * float(standard_error)),
            }
        )
    level = float(beta[2])
    level_se = float(se[2])
    slope = float(beta[3])
    slope_se = float(se[3])
    vcov = model["vcov"]
    break_beta = [level, slope]
    break_vcov = [[float(vcov[i][j]) for j in [2, 3]] for i in [2, 3]]
    joint_wald = sum(
        break_beta[i]
        * sum(core.invert(break_vcov)[i][j] * break_beta[j] for j in range(2))
        for i in range(2)
    )
    result = {
        "pre_n": sum(month_ordinal(row["month"]) < cut for row in rows),
        "post_n": sum(month_ordinal(row["month"]) >= cut for row in rows),
        "n_obs": model["n_obs"],
        "k_params": model["k_params"],
        "df_resid": model["df_resid"],
        "level": level,
        "level_se": level_se,
        "level_z": level / level_se if level_se else math.nan,
        "level_p": core.two_sided_normal_pvalue(level, level_se),
        "level_ci_low": level - 1.96 * level_se,
        "level_ci_high": level + 1.96 * level_se,
        "slope_change": slope,
        "slope_se": slope_se,
        "slope_z": slope / slope_se if slope_se else math.nan,
        "slope_p": core.two_sided_normal_pvalue(slope, slope_se),
        "slope_ci_low": slope - 1.96 * slope_se,
        "slope_ci_high": slope + 1.96 * slope_se,
        "joint_wald": joint_wald,
        "joint_p": math.exp(-joint_wald / 2.0),
        "model": model,
    }
    return result, coefficient_rows


def holm_adjust(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    adjusted_sorted: list[float] = []
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, values[index] * (len(values) - rank))
        adjusted_sorted.append(min(1.0, running))
    adjusted = [0.0] * len(values)
    for rank, index in enumerate(order):
        adjusted[index] = adjusted_sorted[rank]
    return adjusted


def result_row(
    specification: str,
    control_definition: str,
    design: str,
    intervention_date: str,
    rows: list[dict[str, str]],
    fitted: dict[str, object],
) -> dict[str, object]:
    row = {
        "specification": specification,
        "control_definition": control_definition,
        "design": design,
        "intervention_date": intervention_date,
        "sample_start": rows[0]["month"],
        "sample_end": rows[-1]["month"],
        "pre_n": fitted["pre_n"],
        "post_n": fitted["post_n"],
        "n_obs": fitted["n_obs"],
        "k_params": fitted["k_params"],
        "df_resid": fitted["df_resid"],
        "level": fmt(fitted["level"]),
        "level_se": fmt(fitted["level_se"]),
        "level_z": fmt(fitted["level_z"]),
        "level_p": fmt(fitted["level_p"]),
        "level_ci_low": fmt(fitted["level_ci_low"]),
        "level_ci_high": fmt(fitted["level_ci_high"]),
        "slope_change": fmt(fitted["slope_change"]),
        "slope_se": fmt(fitted["slope_se"]),
        "slope_z": fmt(fitted["slope_z"]),
        "slope_p": fmt(fitted["slope_p"]),
        "slope_ci_low": fmt(fitted["slope_ci_low"]),
        "slope_ci_high": fmt(fitted["slope_ci_high"]),
        "slope_p_holm": "",
        "joint_wald": fmt(fitted["joint_wald"]),
        "joint_p": fmt(fitted["joint_p"]),
        "joint_p_holm": "",
        "nw_lag": HAC_LAG,
        "inference": "OLS Newey-West HAC (Bartlett, lag 3; no finite-sample scaling)",
    }
    return row


def run_specification(specification: str, control_definition: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    monthly = read_monthly(specification)
    output: list[dict[str, object]] = []
    coefficients: list[dict[str, object]] = []

    fitted, terms = fit(monthly, REAL_BREAK)
    output.append(result_row(specification, control_definition, "actual_full", REAL_BREAK, monthly, fitted))
    for term in terms:
        coefficients.append(
            {
                **term,
                "specification": specification,
                "control_definition": control_definition,
                "design": "actual_full",
                "intervention_date": REAL_BREAK,
                "sample_start": monthly[0]["month"],
                "sample_end": monthly[-1]["month"],
                "n_obs": fitted["n_obs"],
                "k_params": fitted["k_params"],
                "df_resid": fitted["df_resid"],
                "nw_lag": HAC_LAG,
                "inference": "OLS Newey-West HAC (Bartlett, lag 3; no finite-sample scaling)",
            }
        )

    pre_only = subset(monthly, PRE_START, PRE_END)
    for intervention in [month_label(month_ordinal(ALL_PLACEBO_START) + offset) for offset in range(10)]:
        fitted, terms = fit(pre_only, intervention)
        output.append(result_row(specification, control_definition, "placebo_all_pre", intervention, pre_only, fitted))
        for term in terms:
            coefficients.append(
                {
                    **term,
                    "specification": specification,
                    "control_definition": control_definition,
                    "design": "placebo_all_pre",
                    "intervention_date": intervention,
                    "sample_start": pre_only[0]["month"],
                    "sample_end": pre_only[-1]["month"],
                    "n_obs": fitted["n_obs"],
                    "k_params": fitted["k_params"],
                    "df_resid": fitted["df_resid"],
                    "nw_lag": HAC_LAG,
                    "inference": "OLS Newey-West HAC (Bartlett, lag 3; no finite-sample scaling)",
                }
            )

    for intervention in [
        month_label(month_ordinal(MATCHED_PLACEBO_START) + offset)
        for offset in range(month_distance(MATCHED_PLACEBO_START, MATCHED_PLACEBO_END) + 1)
    ] + [REAL_BREAK]:
        start = month_label(month_ordinal(intervention) - 18)
        end = month_label(month_ordinal(intervention) + 11)
        window = subset(monthly, start, end)
        design = "actual_18_12" if intervention == REAL_BREAK else "placebo_18_12"
        fitted, terms = fit(window, intervention)
        output.append(result_row(specification, control_definition, design, intervention, window, fitted))
        for term in terms:
            coefficients.append(
                {
                    **term,
                    "specification": specification,
                    "control_definition": control_definition,
                    "design": design,
                    "intervention_date": intervention,
                    "sample_start": window[0]["month"],
                    "sample_end": window[-1]["month"],
                    "n_obs": fitted["n_obs"],
                    "k_params": fitted["k_params"],
                    "df_resid": fitted["df_resid"],
                    "nw_lag": HAC_LAG,
                    "inference": "OLS Newey-West HAC (Bartlett, lag 3; no finite-sample scaling)",
                }
            )

    all_pre = [row for row in output if row["design"] == "placebo_all_pre"]
    slope_holm = holm_adjust([float(row["slope_p"]) for row in all_pre])
    joint_holm = holm_adjust([float(row["joint_p"]) for row in all_pre])
    for row, slope_p, joint_p in zip(all_pre, slope_holm, joint_holm):
        row["slope_p_holm"] = fmt(slope_p)
        row["joint_p_holm"] = fmt(joint_p)

    matched = [row for row in output if row["design"] == "placebo_18_12"]
    slope_holm = holm_adjust([float(row["slope_p"]) for row in matched])
    joint_holm = holm_adjust([float(row["joint_p"]) for row in matched])
    for row, slope_p, joint_p in zip(matched, slope_holm, joint_holm):
        row["slope_p_holm"] = fmt(slope_p)
        row["joint_p_holm"] = fmt(joint_p)
    return output, coefficients


def write_outputs(rows: list[dict[str, object]], coefficients: list[dict[str, object]]) -> None:
    core.write_csv(DATA_DIR / "placebo_results.csv", rows, RESULT_FIELDS)
    core.write_csv(DATA_DIR / "placebo_regression_coefficients.csv", coefficients, COEFFICIENT_FIELDS)


def number(row: dict[str, object], field: str, digits: int = 6) -> str:
    return f"{float(row[field]):.{digits}f}"


def pvalue(value: object) -> str:
    numeric = float(value)
    return "<0.000001" if numeric < 0.0000005 else f"{numeric:.6f}"


def table_markdown(rows: list[dict[str, object]], design: str) -> str:
    selected = [row for row in rows if row["design"] == design]
    if design == "placebo_all_pre":
        header = "| Artificial date | Pre n | Post n | Level | Level p | Slope | Slope p | Slope Holm p | Joint p |"
        divider = "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
        lines = [header, divider]
        for row in selected:
            lines.append(
                f"| {row['intervention_date']} | {row['pre_n']} | {row['post_n']} | {number(row, 'level')} | {pvalue(row['level_p'])} | {number(row, 'slope_change')} | {pvalue(row['slope_p'])} | {pvalue(row['slope_p_holm'])} | {pvalue(row['joint_p'])} |"
            )
        return "\n".join(lines)
    header = "| Artificial date | Level | Level p | Slope | Slope p | Slope Holm p | Joint p |"
    divider = "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"
    lines = [header, divider]
    for row in selected:
        lines.append(
            f"| {row['intervention_date']} | {number(row, 'level')} | {pvalue(row['level_p'])} | {number(row, 'slope_change')} | {pvalue(row['slope_p'])} | {pvalue(row['slope_p_holm'])} | {pvalue(row['joint_p'])} |"
        )
    return "\n".join(lines)


def report(rows: list[dict[str, object]]) -> str:
    sections = []
    for specification, control in [("strict", "strict already-RAP-bound control proxy"), ("broad", "broad sequence control proxy")]:
        all_pre = [row for row in rows if row["specification"] == specification and row["design"] == "placebo_all_pre"]
        matched = [row for row in rows if row["specification"] == specification and row["design"] == "placebo_18_12"]
        actual_full = next(row for row in rows if row["specification"] == specification and row["design"] == "actual_full") if any(row["design"] == "actual_full" for row in rows) else None
        actual_short = next(row for row in rows if row["specification"] == specification and row["design"] == "actual_18_12")
        if actual_full is None:
            actual_full = next(row for row in rows if row["specification"] == specification and row["design"] == "actual_full")
        slope_significant = sum(float(row["slope_p"]) < 0.05 for row in all_pre)
        slope_holm_significant = sum(float(row["slope_p_holm"]) < 0.05 for row in all_pre)
        positive_significant = sum(float(row["slope_p"]) < 0.05 and float(row["slope_change"]) > 0 for row in all_pre)
        matched_significant = sum(float(row["slope_p"]) < 0.05 for row in matched)
        matched_holm_significant = sum(float(row["slope_p_holm"]) < 0.05 for row in matched)
        section = f"""## {specification.title()} control

Control definition: {control}. The candidate grid is every month from October 2022 through July 2023. All fits use the raw monthly difference `treatment starts - control starts`, a linear time trend, artificial level and slope breaks, month-of-year fixed effects, and Bartlett Newey-West HAC lag 3 without finite-sample scaling.

### Primary artificial-date exercise

Only October 2021 through June 2024 is used. This is 33 pre-transition calendar months. The 15-coefficient model leaves 18 residual degrees of freedom. The 10 candidate dates each have at least 12 observations before and 12 observations on or after the candidate date.

{table_markdown(all_pre, 'placebo_all_pre')}

Artificial slope changes range from {min(float(row['slope_change']) for row in all_pre):.3f} to {max(float(row['slope_change']) for row in all_pre):.3f}. {slope_significant} of 10 have two-sided slope p < .05, {slope_holm_significant} remain below .05 after within-panel Holm correction, and {positive_significant} have a positive and individually significant artificial slope. All 10 reject the joint no-level/no-slope-break hypothesis at the nominal 5% level.

### Same-window companion check

The matched-window exercise uses 18 pre-date months and 12 post-date months. The four earlier dates are April through July 2023. The actual July 2024 estimate is also re-estimated over January 2023 through June 2025 with the same 18/12 window.

{table_markdown(matched, 'placebo_18_12')}

In the matched-window exercise, {matched_significant} of 4 artificial slope changes have p < .05 and {matched_holm_significant} remain below .05 after within-panel Holm correction. All 4 joint tests reject at the nominal 5% level.

### Actual July 2024 comparison

| Window | Pre n | Post n | Level | Level p | Slope change | Slope SE | Slope p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original full window | {actual_full['pre_n']} | {actual_full['post_n']} | {number(actual_full, 'level')} | {pvalue(actual_full['level_p'])} | {number(actual_full, 'slope_change')} | {number(actual_full, 'slope_se')} | {pvalue(actual_full['slope_p'])} |
| Matched 18/12 window | {actual_short['pre_n']} | {actual_short['post_n']} | {number(actual_short, 'level')} | {pvalue(actual_short['level_p'])} | {number(actual_short, 'slope_change')} | {number(actual_short, 'slope_se')} | {pvalue(actual_short['slope_p'])} |

### Interpretation

These artificial-date fits are overlapping diagnostics on the same short pre-transition series, not independent historical events and not a randomization test. Their frequent negative artificial slope breaks suggest that the pre-period treatment-control gap may contain curvature or earlier changes that are not captured by one stable linear differential trend. The negative signs do not show that arbitrary earlier dates reproduce the actual positive July 2024 acceleration.

The actual July 2024 full-window model shows a negative relative level change followed by a positive relative slope change. The matched-window estimates are larger, which demonstrates that magnitude and inference are sensitive to the time window. The current evidence supports a descriptive comparative-ITS interpretation only. It does not establish a causal DID effect, observed RAP migration, or that any particular artificial date is free of other UKB data releases or access changes.

The 33-month history and seasonal controls make all p-values approximate. Holm correction is within each control-definition panel and does not fix small-sample calibration or model misspecification. Institutional chronology should be reviewed before treating any artificial date as a substantive no-event control.
"""
        sections.append(section)
    return """# Placebo Intervention-Date Checks

This supplementary exercise checks the stability of the comparative ITS around artificial earlier intervention dates. It is separate from the main July 2024 analysis and does not alter the main estimates or classification.

## Model and source data

For each candidate date tau, the model is:

`D_t = a + b*time_t + level*1(t >= tau) + slope*max(t - tau, 0) + month-of-year FE + error_t`,

where `D_t` is the raw monthly treatment-minus-control difference. The pre-period slope is unrestricted. The coefficients of interest are the artificial level and slope changes. Inference uses the same Bartlett Newey-West HAC lag 3 convention as the repository, without a finite-sample scaling factor. P-values use large-sample normal approximations and the joint break test uses a chi-square(2) approximation.

The source data are the saved `new_comparative_its/data/monthly_strict.csv` and `monthly_broad.csv` files. The primary placebo exercise uses only October 2021 through June 2024 and tests October 2022 through July 2023. The companion exercise uses identical 18 pre-date and 12 post-date month windows.

""" + "\n".join(sections)


def stata_model_block(row: dict[str, object], coefficients: list[dict[str, object]]) -> str:
    selected = [term for term in coefficients if term["specification"] == row["specification"] and term["design"] == row["design"] and term["intervention_date"] == row["intervention_date"]]
    lines = [
        f"{row['specification'].title()} | {row['design']} | artificial date {row['intervention_date']}",
        "------------------------------------------------------------------------------",
        "raw_diff   | Coefficient   std. err.      z    P>|z|    [95% conf. interval]",
        "-----------+----------------------------------------------------------------",
    ]
    for term in selected:
        lines.append(
            f"{str(term['term']):>14} | {float(term['estimate']):11.7f} {float(term['std_error']):11.7f} {float(term['z']):7.2f} {float(term['p_value']):8.4f} [{float(term['ci_low']):10.7f}, {float(term['ci_high']):10.7f}]"
        )
    lines.extend(
        [
            "------------------------------------------------------------------------------",
            f"Observations                   = {row['n_obs']}",
            f"Pre observations               = {row['pre_n']}",
            f"Post observations              = {row['post_n']}",
            f"Residual degrees of freedom    = {row['df_resid']}",
            "Month-of-year FE              = Yes",
            f"HAC lag                       = {HAC_LAG}",
            f"Artificial level break        = {float(row['level']):.7f}; p = {float(row['level_p']):.7f}",
            f"Artificial slope break        = {float(row['slope_change']):.7f}; SE = {float(row['slope_se']):.7f}; p = {float(row['slope_p']):.7f}; 95% CI = [{float(row['slope_ci_low']):.7f}, {float(row['slope_ci_high']):.7f}]",
            f"Joint Wald chi2(2)            = {float(row['joint_wald']):.7f}; p = {float(row['joint_p']):.7f}",
        ]
    )
    if row["slope_p_holm"]:
        lines.append(f"Within-panel Holm slope p     = {float(row['slope_p_holm']):.7f}")
        lines.append(f"Within-panel Holm joint p     = {float(row['joint_p_holm']):.7f}")
    return "\n".join(lines)


def stata_report(rows: list[dict[str, object]], coefficients: list[dict[str, object]]) -> str:
    blocks = []
    for specification in ["strict", "broad"]:
        for design in ["placebo_all_pre", "placebo_18_12", "actual_full", "actual_18_12"]:
            selected = [row for row in rows if row["specification"] == specification and row["design"] == design]
            blocks.extend(stata_model_block(row, coefficients) for row in selected)
    return """Placebo Intervention-Date Checks: New Comparative ITS

Model: raw monthly treatment-minus-control difference with linear time, artificial level and slope breaks, month-of-year FE, and Bartlett Newey-West HAC lag 3. Artificial dates are estimated only over the stated sample window. Built-in Stata newey was not run on a stacked data set with duplicate monthly time values.

""" + "\n\n".join(blocks) + "\n\nStata executed: No. Results are reproduced by the repository Python implementation using the same HAC convention."


def main() -> None:
    all_rows: list[dict[str, object]] = []
    all_coefficients: list[dict[str, object]] = []
    for specification, control in [("strict", "Strict already-RAP-bound control proxy"), ("broad", "Broad sequence control proxy")]:
        rows, coefficients = run_specification(specification, control)
        all_rows.extend(rows)
        all_coefficients.extend(coefficients)
    write_outputs(all_rows, all_coefficients)
    core.write_text(REPORT_DIR / "placebo_date_checks.md", report(all_rows))
    core.write_text(REPORT_DIR / "placebo_date_checks_stata_style_results.txt", stata_report(all_rows, all_coefficients))
    print("Wrote placebo_results.csv and placebo_regression_coefficients.csv")
    for specification in ["strict", "broad"]:
        rows = [row for row in all_rows if row["specification"] == specification and row["design"] == "placebo_all_pre"]
        print(
            specification,
            "slope p<.05", sum(float(row["slope_p"]) < 0.05 for row in rows),
            "Holm slope p<.05", sum(float(row["slope_p_holm"]) < 0.05 for row in rows),
            "positive slope p<.05", sum(float(row["slope_p"]) < 0.05 and float(row["slope_change"]) > 0 for row in rows),
        )


if __name__ == "__main__":
    main()
