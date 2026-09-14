#!/usr/bin/env python3
"""Decompose the comparative ITS into treatment-only and control-only fits.

This diagnostic preserves the existing comparative ITS and placebo outputs.
It reuses their saved monthly counts, July 2024 breakpoint, month-of-year fixed
effects, and Bartlett Newey-West HAC lag-3 convention.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
CORE_SCRIPT_DIR = ROOT / "archive" / "03_project_entry_high_vs_lower" / "scripts"
if str(CORE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_SCRIPT_DIR))

import project_entry2_analysis as core


DATA_DIR = PACKAGE / "data"
REPORT_DIR = PACKAGE / "reports"
FIGURE_DIR = PACKAGE / "figures"

HAC_LAG = 3
REAL_BREAK = "2024-07"
FULL_START = "2021-10"
FULL_END = "2026-04"
PRE_END = "2024-06"
PLACEBO_START = "2022-10"
PLACEBO_END = "2023-07"
MATCHED_START = "2023-04"
MATCHED_END = "2023-07"

SERIES = {
    "treatment": {
        "label": "Treatment only",
        "source": "monthly_strict.csv",
        "column": "treatment_count",
        "color": "#B24A38",
        "figure_stem": "treatment_only",
    },
    "strict_control": {
        "label": "Strict control only",
        "source": "monthly_strict.csv",
        "column": "control_count",
        "color": "#24536B",
        "figure_stem": "strict_control_only",
    },
    "broad_control": {
        "label": "Broad control only",
        "source": "monthly_broad.csv",
        "column": "control_count",
        "color": "#24536B",
        "figure_stem": "broad_control_only",
    },
}

RESULT_FIELDS = [
    "series_id",
    "series_label",
    "source_file",
    "outcome_column",
    "design",
    "intervention_date",
    "sample_start",
    "sample_end",
    "pre_n",
    "post_n",
    "n_obs",
    "k_params",
    "df_resid",
    "pre_trend",
    "pre_trend_se",
    "pre_trend_z",
    "pre_trend_p",
    "pre_trend_ci_low",
    "pre_trend_ci_high",
    "level_change",
    "level_se",
    "level_z",
    "level_p",
    "level_ci_low",
    "level_ci_high",
    "level_p_holm",
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
    "month_of_year_fe",
    "nw_lag",
    "inference",
]

SUMMARY_FIELDS = [
    "object_id",
    "object_label",
    "source",
    "actual_slope_change",
    "actual_slope_se",
    "actual_slope_p",
    "actual_slope_ci_low",
    "actual_slope_ci_high",
    "placebo_n",
    "placebo_negative_n",
    "placebo_positive_n",
    "placebo_zero_n",
    "placebo_slope_min",
    "placebo_slope_max",
    "placebo_slope_mean",
    "placebo_slope_p_lt_0_05_n",
    "placebo_slope_holm_p_lt_0_05_n",
    "placebo_joint_p_lt_0_05_n",
    "placebo_joint_holm_p_lt_0_05_n",
    "actual_vs_placebo_range",
    "actual_above_all_placebos",
]


def month_ordinal(label: str) -> int:
    year, month = (int(value) for value in label[:7].split("-"))
    return year * 12 + month


def month_label(ordinal: int) -> str:
    year, month_zero = divmod(ordinal - 1, 12)
    return f"{year:04d}-{month_zero + 1:02d}"


def month_grid(start: str, end: str) -> list[str]:
    return [month_label(value) for value in range(month_ordinal(start), month_ordinal(end) + 1)]


def fmt(value: float | int | None, digits: int = 8) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return ""
    return f"{float(value):.{digits}f}"


def read_series(series_id: str) -> list[dict[str, str]]:
    metadata = SERIES[series_id]
    rows = core.read_csv(DATA_DIR / str(metadata["source"]))
    rows.sort(key=lambda row: row["month"])
    expected = month_grid(FULL_START, FULL_END)
    if [row["month"] for row in rows] != expected:
        raise AssertionError(f"{series_id} source must cover {FULL_START} through {FULL_END}")
    return rows


def subset(rows: list[dict[str, str]], start: str, end: str) -> list[dict[str, str]]:
    return [row for row in rows if start <= row["month"] <= end]


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


def fit_series(
    rows: list[dict[str, str]], outcome_column: str, intervention_date: str
) -> tuple[dict[str, object], list[float], list[float]]:
    cut = month_ordinal(intervention_date)
    first = month_ordinal(rows[0]["month"])
    X: list[list[float]] = []
    y: list[float] = []
    for row in rows:
        ordinal = month_ordinal(row["month"])
        X.append(
            [
                1.0,
                float(ordinal - first),
                float(ordinal >= cut),
                float(max(ordinal - cut, 0)),
            ]
            + [1.0 if int(row["month_of_year"]) == month else 0.0 for month in range(2, 13)]
        )
        y.append(float(row[outcome_column]))
    if len(X) < 16:
        raise AssertionError("ITS design requires positive residual degrees of freedom")
    core.invert(core.xtx(X))
    fit = core.ols_hac(X, y, HAC_LAG)
    beta = [float(value) for value in fit["beta"]]
    se = [float(value) for value in fit["se"]]
    vcov = fit["vcov"]
    break_vcov = [[float(vcov[i][j]) for j in (2, 3)] for i in (2, 3)]
    inverse = core.invert(break_vcov)
    break_beta = [beta[2], beta[3]]
    joint_wald = sum(
        break_beta[i] * sum(inverse[i][j] * break_beta[j] for j in range(2))
        for i in range(2)
    )
    fit.update(
        {
            "joint_wald": joint_wald,
            "joint_p": math.exp(-joint_wald / 2.0),
            "pre_n": sum(month_ordinal(row["month"]) < cut for row in rows),
            "post_n": sum(month_ordinal(row["month"]) >= cut for row in rows),
        }
    )
    return fit, y, X


def inference_values(
    estimate: float,
    standard_error: float,
    estimate_field: str,
    inference_prefix: str | None = None,
) -> dict[str, str]:
    prefix = inference_prefix or estimate_field
    p_value = core.two_sided_normal_pvalue(estimate, standard_error)
    return {
        estimate_field: fmt(estimate),
        f"{prefix}_se": fmt(standard_error),
        f"{prefix}_z": fmt(estimate / standard_error if standard_error else math.nan),
        f"{prefix}_p": fmt(p_value),
        f"{prefix}_ci_low": fmt(estimate - 1.96 * standard_error),
        f"{prefix}_ci_high": fmt(estimate + 1.96 * standard_error),
    }


def result_row(
    series_id: str,
    design: str,
    intervention_date: str,
    rows: list[dict[str, str]],
    fit: dict[str, object],
) -> dict[str, object]:
    metadata = SERIES[series_id]
    beta = [float(value) for value in fit["beta"]]
    se = [float(value) for value in fit["se"]]
    return {
        "series_id": series_id,
        "series_label": metadata["label"],
        "source_file": metadata["source"],
        "outcome_column": metadata["column"],
        "design": design,
        "intervention_date": intervention_date,
        "sample_start": rows[0]["month"],
        "sample_end": rows[-1]["month"],
        "pre_n": fit["pre_n"],
        "post_n": fit["post_n"],
        "n_obs": fit["n_obs"],
        "k_params": fit["k_params"],
        "df_resid": fit["df_resid"],
        **inference_values(beta[1], se[1], "pre_trend"),
        **inference_values(beta[2], se[2], "level_change", "level"),
        "level_p_holm": "",
        **inference_values(beta[3], se[3], "slope_change", "slope"),
        "slope_p_holm": "",
        "joint_wald": fmt(float(fit["joint_wald"])),
        "joint_p": fmt(float(fit["joint_p"])),
        "joint_p_holm": "",
        "month_of_year_fe": "Yes",
        "nw_lag": HAC_LAG,
        "inference": "OLS Newey-West HAC (Bartlett, lag 3; no finite-sample scaling)",
    }


def add_holm(rows: list[dict[str, object]], design: str) -> None:
    selected = [row for row in rows if row["design"] == design]
    for field in ("level_p", "slope_p", "joint_p"):
        adjusted = holm_adjust([float(row[field]) for row in selected])
        output_field = "joint_p_holm" if field == "joint_p" else field.replace("_p", "_p_holm")
        for row, value in zip(selected, adjusted):
            row[output_field] = fmt(value)


def run_one_series(series_id: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    metadata = SERIES[series_id]
    monthly = read_series(series_id)
    outcome = str(metadata["column"])
    output: list[dict[str, object]] = []

    actual_fit, actual_y, actual_X = fit_series(monthly, outcome, REAL_BREAK)
    output.append(result_row(series_id, "actual_full", REAL_BREAK, monthly, actual_fit))

    pre_only = subset(monthly, FULL_START, PRE_END)
    for intervention in month_grid(PLACEBO_START, PLACEBO_END):
        fit, _, _ = fit_series(pre_only, outcome, intervention)
        output.append(result_row(series_id, "placebo_all_pre", intervention, pre_only, fit))
    add_holm(output, "placebo_all_pre")

    for intervention in month_grid(MATCHED_START, MATCHED_END):
        window = subset(
            monthly,
            month_label(month_ordinal(intervention) - 18),
            month_label(month_ordinal(intervention) + 11),
        )
        fit, _, _ = fit_series(window, outcome, intervention)
        output.append(result_row(series_id, "placebo_18_12", intervention, window, fit))
    add_holm(output, "placebo_18_12")

    matched_actual = subset(
        monthly,
        month_label(month_ordinal(REAL_BREAK) - 18),
        month_label(month_ordinal(REAL_BREAK) + 11),
    )
    fit, _, _ = fit_series(matched_actual, outcome, REAL_BREAK)
    output.append(result_row(series_id, "actual_18_12", REAL_BREAK, matched_actual, fit))
    figure_data = {
        "monthly": monthly,
        "actual_fit": actual_fit,
        "actual_y": actual_y,
        "actual_X": actual_X,
    }
    return output, figure_data


def existing_difference_rows() -> list[dict[str, str]]:
    rows = core.read_csv(DATA_DIR / "placebo_results.csv")
    required = {"strict", "broad"}
    if {row["specification"] for row in rows} != required:
        raise AssertionError("existing placebo results do not contain strict and broad panels")
    return rows


def sign_counts(values: list[float]) -> tuple[int, int, int]:
    negative = sum(value < 0 for value in values)
    positive = sum(value > 0 for value in values)
    return negative, positive, len(values) - negative - positive


def actual_vs_range(actual: float, placebos: list[float]) -> str:
    if actual > max(placebos):
        return "Above all pre-period placebo slopes"
    if actual < min(placebos):
        return "Below all pre-period placebo slopes"
    return "Within pre-period placebo slope range"


def summary_row(
    object_id: str,
    object_label: str,
    source: str,
    actual: dict[str, object],
    placebos: list[dict[str, object]],
    slope_field: str = "slope_change",
) -> dict[str, object]:
    values = [float(row[slope_field]) for row in placebos]
    negative, positive, zero = sign_counts(values)
    actual_slope = float(actual[slope_field])
    return {
        "object_id": object_id,
        "object_label": object_label,
        "source": source,
        "actual_slope_change": fmt(actual_slope),
        "actual_slope_se": actual["slope_se"],
        "actual_slope_p": actual["slope_p"],
        "actual_slope_ci_low": actual["slope_ci_low"],
        "actual_slope_ci_high": actual["slope_ci_high"],
        "placebo_n": len(values),
        "placebo_negative_n": negative,
        "placebo_positive_n": positive,
        "placebo_zero_n": zero,
        "placebo_slope_min": fmt(min(values)),
        "placebo_slope_max": fmt(max(values)),
        "placebo_slope_mean": fmt(sum(values) / len(values)),
        "placebo_slope_p_lt_0_05_n": sum(float(row["slope_p"]) < 0.05 for row in placebos),
        "placebo_slope_holm_p_lt_0_05_n": sum(float(row["slope_p_holm"]) < 0.05 for row in placebos),
        "placebo_joint_p_lt_0_05_n": sum(float(row["joint_p"]) < 0.05 for row in placebos),
        "placebo_joint_holm_p_lt_0_05_n": sum(float(row["joint_p_holm"]) < 0.05 for row in placebos),
        "actual_vs_placebo_range": actual_vs_range(actual_slope, values),
        "actual_above_all_placebos": int(actual_slope > max(values)),
    }


def make_summary(
    new_rows: list[dict[str, object]], difference_rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    output = []
    for series_id in SERIES:
        actual = next(row for row in new_rows if row["series_id"] == series_id and row["design"] == "actual_full")
        placebos = [row for row in new_rows if row["series_id"] == series_id and row["design"] == "placebo_all_pre"]
        output.append(summary_row(series_id, str(SERIES[series_id]["label"]), "New single-series diagnostic", actual, placebos))
    for specification in ("strict", "broad"):
        actual = next(row for row in difference_rows if row["specification"] == specification and row["design"] == "actual_full")
        placebos = [row for row in difference_rows if row["specification"] == specification and row["design"] == "placebo_all_pre"]
        output.append(
            summary_row(
                f"treatment_minus_{specification}_control",
                f"Treatment minus {specification} control",
                "Existing comparative-ITS placebo_results.csv",
                actual,
                placebos,
            )
        )
    return output


def verify_decomposition(
    new_rows: list[dict[str, object]], difference_rows: list[dict[str, str]]
) -> None:
    for specification, control_id in (("strict", "strict_control"), ("broad", "broad_control")):
        for difference in difference_rows:
            if difference["specification"] != specification:
                continue
            design = difference["design"]
            intervention = difference["intervention_date"]
            treatment = next(
                row for row in new_rows
                if row["series_id"] == "treatment" and row["design"] == design and row["intervention_date"] == intervention
            )
            control = next(
                row for row in new_rows
                if row["series_id"] == control_id and row["design"] == design and row["intervention_date"] == intervention
            )
            for field in ("pre_trend", "level_change", "slope_change"):
                existing_field = {"pre_trend": "pre_trend", "level_change": "level", "slope_change": "slope_change"}[field]
                if existing_field not in difference:
                    continue
                residual = float(treatment[field]) - float(control[field]) - float(difference[existing_field])
                if abs(residual) > 2e-7:
                    raise AssertionError(
                        f"point-estimate decomposition failed for {specification} {design} {intervention} {field}: {residual}"
                    )


def p_text(value: object) -> str:
    number = float(value)
    return "<0.000001" if number < 0.0000005 else f"{number:.6f}"


def ci_text(row: dict[str, object], prefix: str) -> str:
    return f"[{float(row[f'{prefix}_ci_low']):.4f}, {float(row[f'{prefix}_ci_high']):.4f}]"


def summary_markdown(summary: list[dict[str, object]]) -> str:
    lines = [
        "| Object | Actual slope change | HAC SE | p-value | 95% CI | Placebo slope range | Significant placebo slopes | Holm-significant | Placebo signs | Actual vs placebo |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in summary:
        signs = f"{row['placebo_negative_n']} negative, {row['placebo_positive_n']} positive"
        lines.append(
            f"| {row['object_label']} | {float(row['actual_slope_change']):.4f} | {float(row['actual_slope_se']):.4f} | {p_text(row['actual_slope_p'])} | "
            f"[{float(row['actual_slope_ci_low']):.4f}, {float(row['actual_slope_ci_high']):.4f}] | "
            f"[{float(row['placebo_slope_min']):.4f}, {float(row['placebo_slope_max']):.4f}] | "
            f"{row['placebo_slope_p_lt_0_05_n']}/10 | {row['placebo_slope_holm_p_lt_0_05_n']}/10 | {signs} | {row['actual_vs_placebo_range']} |"
        )
    return "\n".join(lines)


def actual_markdown(rows: list[dict[str, object]]) -> str:
    lines = [
        "| Series | Quantity | Estimate | HAC SE | p-value | 95% CI |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for series_id in SERIES:
        row = next(item for item in rows if item["series_id"] == series_id and item["design"] == "actual_full")
        for label, estimate_field, inference_prefix in (
            ("Pre-trend", "pre_trend", "pre_trend"),
            ("Level change", "level_change", "level"),
            ("Slope change", "slope_change", "slope"),
        ):
            lines.append(
                f"| {row['series_label']} | {label} | {float(row[estimate_field]):.6f} | {float(row[f'{inference_prefix}_se']):.6f} | "
                f"{p_text(row[f'{inference_prefix}_p'])} | {ci_text(row, inference_prefix)} |"
            )
    return "\n".join(lines)


def placebo_markdown(rows: list[dict[str, object]], series_id: str, design: str) -> str:
    selected = [row for row in rows if row["series_id"] == series_id and row["design"] == design]
    lines = [
        "| Artificial date | Pre n | Post n | Level | SE | p | Holm p | Slope | SE | p | Holm p | Joint p | Joint Holm p |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in selected:
        lines.append(
            f"| {row['intervention_date']} | {row['pre_n']} | {row['post_n']} | {float(row['level_change']):.4f} | {float(row['level_se']):.4f} | "
            f"{p_text(row['level_p'])} | {p_text(row['level_p_holm'])} | {float(row['slope_change']):.4f} | {float(row['slope_se']):.4f} | "
            f"{p_text(row['slope_p'])} | {p_text(row['slope_p_holm'])} | {p_text(row['joint_p'])} | {p_text(row['joint_p_holm'])} |"
        )
    return "\n".join(lines)


def decomposition_markdown(
    new_rows: list[dict[str, object]], difference_rows: list[dict[str, str]], specification: str
) -> str:
    control_id = f"{specification}_control"
    lines = [
        "| Date | Treatment slope break | Control slope break | Treatment - Control | Saved difference result | Residual |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    selected = [row for row in difference_rows if row["specification"] == specification and row["design"] == "placebo_all_pre"]
    for difference in selected:
        treatment = next(
            row for row in new_rows
            if row["series_id"] == "treatment" and row["design"] == "placebo_all_pre" and row["intervention_date"] == difference["intervention_date"]
        )
        control = next(
            row for row in new_rows
            if row["series_id"] == control_id and row["design"] == "placebo_all_pre" and row["intervention_date"] == difference["intervention_date"]
        )
        calculated = float(treatment["slope_change"]) - float(control["slope_change"])
        saved = float(difference["slope_change"])
        lines.append(
            f"| {difference['intervention_date']} | {float(treatment['slope_change']):.4f} | {float(control['slope_change']):.4f} | {calculated:.4f} | {saved:.4f} | {calculated - saved:.8f} |"
        )
    return "\n".join(lines)


def diagnostic_conclusion(summary: list[dict[str, object]]) -> str:
    lookup = {str(row["object_id"]): row for row in summary}
    treatment = lookup["treatment"]
    strict = lookup["strict_control"]
    broad = lookup["broad_control"]
    return (
        f"Treatment alone has {treatment['placebo_slope_p_lt_0_05_n']} nominally significant artificial slope breaks; "
        f"strict control has {strict['placebo_slope_p_lt_0_05_n']}, and broad control has {broad['placebo_slope_p_lt_0_05_n']}. "
        f"The treatment placebo slopes contain {treatment['placebo_negative_n']} negative and {treatment['placebo_positive_n']} positive estimates. "
        f"Strict-control slopes contain {strict['placebo_negative_n']} negative and {strict['placebo_positive_n']} positive estimates; "
        f"broad-control slopes contain {broad['placebo_negative_n']} negative and {broad['placebo_positive_n']} positive estimates."
    )


def write_report(
    rows: list[dict[str, object]], summary: list[dict[str, object]], difference_rows: list[dict[str, str]]
) -> None:
    matched_tables = []
    for series_id in SERIES:
        matched_tables.append(f"### {SERIES[series_id]['label']}\n\n{placebo_markdown(rows, series_id, 'placebo_18_12')}")
        actual = next(row for row in rows if row["series_id"] == series_id and row["design"] == "actual_18_12")
        matched_tables.append(
            f"Matched actual July 2024: slope change {float(actual['slope_change']):.4f}, "
            f"SE {float(actual['slope_se']):.4f}, p={p_text(actual['slope_p'])}, "
            f"95% CI {ci_text(actual, 'slope')}."
        )
    report = f"""# Comparative ITS Series-Decomposition Diagnostic

## Diagnostic question

Are the significant negative pre-period artificial breaks in the existing comparative ITS generated mainly by curvature or breaks in the treatment series, in the control series, or only in the treatment-minus-control difference?

## Design

This diagnostic does not replace or modify the existing comparative ITS. It uses the saved raw monthly project-start series from October 2021 through April 2026, the July 2024 intervention date, month-of-year fixed effects, and Bartlett Newey-West HAC lag 3 without finite-sample scaling.

For each series, the model is `Y_t = alpha + beta*time + gamma*Post + delta*TimeAfter + month-of-year FE + error`. The primary placebo exercise completely excludes July 2024 and later observations and applies the prespecified October 2022 through July 2023 artificial dates to the 33 true pre-transition months. Holm adjustments are calculated separately within each 10-date series panel.

These are specification diagnostics, not causal estimates or randomized placebo tests. No alternative dates or models were searched to improve the results.

## Final comparison

{summary_markdown(summary)}

All five actual July 2024 slope changes lie above every corresponding pre-period artificial slope estimate. This sign separation is descriptive; the artificial dates are overlapping fits to the same short series and are not exchangeable event assignments.

## Main finding

{diagnostic_conclusion(summary)}

The pattern is generated mainly by instability in the treatment series. Every treatment-only artificial slope change is negative and significant before and after Holm correction, while neither control series has a significant artificial slope change at any candidate date. Differencing therefore carries the treatment-series negative breaks into both comparative placebo panels; the selected control changes their magnitude but is not the primary source of the slope-placebo problem.

The negative comparative placebo breaks are not a difference-series artifact: the point-estimate identities reproduce exactly from the separately estimated treatment and control series. The decomposition tables below show which component moves more at each date. Statistical significance cannot be decomposed by subtracting the separate-series standard errors because treatment and control estimates share calendar-time variation; the saved difference-series HAC inference remains the relevant inference for the comparative coefficient.

## Actual July 2024 single-series ITS

{actual_markdown(rows)}

The treatment-only actual slope change is the existing treatment slope change. The control-only slope changes are the existing strict and broad control slope changes. Their point-estimate differences reproduce the existing comparative `delta3` values.

## Treatment-only pre-period placebos

{placebo_markdown(rows, 'treatment', 'placebo_all_pre')}

## Strict-control pre-period placebos

{placebo_markdown(rows, 'strict_control', 'placebo_all_pre')}

## Broad-control pre-period placebos

{placebo_markdown(rows, 'broad_control', 'placebo_all_pre')}

## Point-estimate decomposition of existing comparative placebos

### Strict comparison

{decomposition_markdown(rows, difference_rows, 'strict')}

### Broad comparison

{decomposition_markdown(rows, difference_rows, 'broad')}

The zero residuals verify that each saved comparative placebo slope break equals the treatment-only break minus the corresponding control-only break, up to output rounding.

## Secondary matched 18-pre/12-post exercise

This secondary exercise uses April through July 2023 artificial dates with 18 pre-date and 12 post-date months. It is retained for comparability with the existing placebo report and does not replace the full-window actual estimates.

{chr(10).join(matched_tables)}

## Interpretation limits

The decomposition identifies where the fitted instability appears in the observed series. It does not establish why either series changes, certify artificial dates as event-free, or support a causal RAP effect. The short 33-month pre-period, 15 fitted coefficients, overlapping placebo windows, and large-sample HAC approximations limit precision. Institutional chronology should be reviewed before assigning substantive meaning to any individual artificial break.

## Files

- `data/series_decomposition_results.csv`: all actual, primary placebo, and matched-window single-series estimates.
- `data/series_decomposition_summary.csv`: final treatment/control/difference comparison.
- `figures/figure_treatment_only_its_placebos.svg`
- `figures/figure_strict_control_only_its_placebos.svg`
- `figures/figure_broad_control_only_its_placebos.svg`
- `scripts/series_decomposition_diagnostic.py`
- `reports/series_decomposition_stata_style_results.txt`
"""
    core.write_text(REPORT_DIR / "series_decomposition_diagnostic.md", report)


def stata_actual_block(row: dict[str, object]) -> str:
    lines = [
        f"Actual July 2024 ITS: {row['series_label']}",
        "------------------------------------------------------------------------------",
        "monthly_count | Coefficient   std. err.      z    P>|z|    [95% conf. interval]",
        "-------------+----------------------------------------------------------------",
    ]
    for label, estimate_field, prefix in (
        ("Time", "pre_trend", "pre_trend"),
        ("PostJuly2024", "level_change", "level"),
        ("TimeAfterJuly2024", "slope_change", "slope"),
    ):
        lines.append(
            f"{label:>20} | {float(row[estimate_field]):11.7f} {float(row[f'{prefix}_se']):11.7f} "
            f"{float(row[f'{prefix}_z']):7.2f} {float(row[f'{prefix}_p']):8.4f} "
            f"[{float(row[f'{prefix}_ci_low']):10.7f}, {float(row[f'{prefix}_ci_high']):10.7f}]"
        )
    lines.extend(
        [
            "------------------------------------------------------------------------------",
            "Month-of-year FE               = Yes",
            f"Observations                   = {row['n_obs']}",
            f"Pre observations               = {row['pre_n']}",
            f"Post observations              = {row['post_n']}",
            f"HAC lag                        = {row['nw_lag']}",
            f"Sample                          = {row['sample_start']} through {row['sample_end']}",
        ]
    )
    return "\n".join(lines)


def stata_placebo_block(rows: list[dict[str, object]], series_id: str, design: str) -> str:
    selected = [row for row in rows if row["series_id"] == series_id and row["design"] == design]
    title = "Pre-period artificial-date placebo ITS" if design == "placebo_all_pre" else "Secondary matched 18/12 placebo ITS"
    lines = [
        f"{title}: {SERIES[series_id]['label']}",
        "---------------------------------------------------------------------------------------------------------------------------------------",
        "       Date |       Level        SE     P>|z|      [95% conf. interval] |       Slope        SE     P>|z|      [95% conf. interval] | Joint p  Holm slope p",
        "------------+----------------------------------------------------------+----------------------------------------------------------+----------------------",
    ]
    for row in selected:
        lines.append(
            f" {row['intervention_date']:>10} | {float(row['level_change']):11.7f} {float(row['level_se']):9.7f} {float(row['level_p']):9.4f} "
            f"[{float(row['level_ci_low']):9.5f}, {float(row['level_ci_high']):9.5f}] | "
            f"{float(row['slope_change']):11.7f} {float(row['slope_se']):9.7f} {float(row['slope_p']):9.4f} "
            f"[{float(row['slope_ci_low']):9.5f}, {float(row['slope_ci_high']):9.5f}] | "
            f"{float(row['joint_p']):8.4f} {float(row['slope_p_holm']):13.4f}"
        )
    lines.extend(
        [
            "---------------------------------------------------------------------------------------------------------------------------------------",
            "Month-of-year FE               = Yes",
            f"Observations per regression    = {selected[0]['n_obs']}",
            f"Residual degrees of freedom    = {selected[0]['df_resid']}",
            f"HAC lag                        = {selected[0]['nw_lag']}",
            "Holm family                    = dates within this series/design panel",
        ]
    )
    return "\n".join(lines)


def write_stata_report(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    blocks = [
        "Comparative ITS Series-Decomposition Diagnostic",
        "Outcome: raw monthly project starts. Month-of-year FE. Bartlett Newey-West HAC lag 3 without finite-sample scaling.",
        "The treatment-only and control-only models are diagnostics and are not causal estimates.",
    ]
    for series_id in SERIES:
        actual = next(row for row in rows if row["series_id"] == series_id and row["design"] == "actual_full")
        matched_actual = next(row for row in rows if row["series_id"] == series_id and row["design"] == "actual_18_12")
        blocks.extend(
            [
                stata_actual_block(actual),
                stata_placebo_block(rows, series_id, "placebo_all_pre"),
                stata_placebo_block(rows, series_id, "placebo_18_12"),
                "\n".join(
                    [
                        f"Matched actual July 2024: {SERIES[series_id]['label']}",
                        f"TimeAfterJuly2024 = {float(matched_actual['slope_change']):.7f}; SE = {float(matched_actual['slope_se']):.7f}; "
                        f"p = {float(matched_actual['slope_p']):.7f}; 95% CI = [{float(matched_actual['slope_ci_low']):.7f}, {float(matched_actual['slope_ci_high']):.7f}]",
                        f"Sample = {matched_actual['sample_start']} through {matched_actual['sample_end']}; observations = {matched_actual['n_obs']}; HAC lag = {matched_actual['nw_lag']}",
                    ]
                ),
            ]
        )
    blocks.extend(
        [
            "Final actual-slope and placebo comparison",
            "----------------------------------------------------------------------------------------------------------------",
            " Object                                Actual slope       SE       p       Placebo range      Sig/10   Holm/10",
        ]
    )
    for row in summary:
        blocks.append(
            f" {str(row['object_label']):<37} {float(row['actual_slope_change']):11.7f} {float(row['actual_slope_se']):8.4f} "
            f"{float(row['actual_slope_p']):8.4f} [{float(row['placebo_slope_min']):8.4f}, {float(row['placebo_slope_max']):8.4f}] "
            f"{int(row['placebo_slope_p_lt_0_05_n']):7d} {int(row['placebo_slope_holm_p_lt_0_05_n']):9d}"
        )
    blocks.extend(
        [
            "----------------------------------------------------------------------------------------------------------------",
            "Stata executed: No. The output uses the repository's algebraically identical OLS/Newey-West implementation.",
        ]
    )
    core.write_text(REPORT_DIR / "series_decomposition_stata_style_results.txt", "\n\n".join(blocks))


def escaped(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_figure(
    series_id: str,
    rows: list[dict[str, object]],
    figure_data: dict[str, object],
) -> None:
    metadata = SERIES[series_id]
    monthly = figure_data["monthly"]
    actual_fit = figure_data["actual_fit"]
    observed = [float(value) for value in figure_data["actual_y"]]
    fitted = [float(value) for value in actual_fit["fitted"]]
    placebos = [row for row in rows if row["series_id"] == series_id and row["design"] == "placebo_all_pre"]
    actual = next(row for row in rows if row["series_id"] == series_id and row["design"] == "actual_full")

    width, height = 1080, 760
    left, right = 82, 60
    top_y, top_h = 90, 290
    bottom_y, bottom_h = 475, 205
    plot_w = width - left - right
    color = str(metadata["color"])
    fitted_color = "#2F6F48"

    y_min = min(0.0, min(observed), min(fitted))
    y_max = max(observed + fitted)
    y_padding = max(1.0, (y_max - y_min) * 0.08)
    y_min -= y_padding
    y_max += y_padding

    def top_x(index: int) -> float:
        return left + index / (len(monthly) - 1) * plot_w

    def top_scale(value: float) -> float:
        return top_y + (y_max - value) / (y_max - y_min) * top_h

    placebo_low = min(float(row["slope_ci_low"]) for row in placebos)
    placebo_high = max(float(row["slope_ci_high"]) for row in placebos)
    actual_slope = float(actual["slope_change"])
    slope_min = min(0.0, placebo_low, actual_slope)
    slope_max = max(0.0, placebo_high, actual_slope)
    slope_padding = max(0.05, (slope_max - slope_min) * 0.12)
    slope_min -= slope_padding
    slope_max += slope_padding

    def bottom_x(index: int) -> float:
        return left + index / (len(placebos) - 1) * plot_w

    def bottom_scale(value: float) -> float:
        return bottom_y + (slope_max - value) / (slope_max - slope_min) * bottom_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="31" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#222">{escaped(str(metadata["label"]))} ITS and Pre-Period Placebo Slopes</text>',
        f'<text x="{left}" y="52" font-family="Arial, sans-serif" font-size="11" fill="#555">Raw monthly project starts; month-of-year FE; Newey-West HAC lag 3</text>',
        f'<text x="{left}" y="{top_y - 12}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#333">Actual July 2024 ITS</text>',
    ]
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        value = y_min + fraction * (y_max - y_min)
        yy = top_scale(value)
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#E2E2E2"/>')
        svg.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="10" fill="#555">{value:.0f}</text>')
    for year in range(2022, 2027):
        month = f"{year:04d}-01"
        index = month_grid(FULL_START, FULL_END).index(month) if month in month_grid(FULL_START, FULL_END) else 0
        xx = top_x(index)
        svg.append(f'<line x1="{xx:.1f}" y1="{top_y}" x2="{xx:.1f}" y2="{top_y+top_h}" stroke="#F0F0F0"/>')
        svg.append(f'<text x="{xx:.1f}" y="{top_y+top_h+21}" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#555">{year}</text>')
    break_index = month_grid(FULL_START, FULL_END).index(REAL_BREAK)
    break_x = top_x(break_index)
    svg.append(f'<line x1="{break_x:.1f}" y1="{top_y}" x2="{break_x:.1f}" y2="{top_y+top_h}" stroke="#111" stroke-width="1.6" stroke-dasharray="6 4"/>')
    svg.append(f'<text x="{break_x+6:.1f}" y="{top_y+15}" font-family="Arial, sans-serif" font-size="10" fill="#111">Jul 2024</text>')
    observed_points = " ".join(f"{top_x(index):.1f},{top_scale(value):.1f}" for index, value in enumerate(observed))
    fitted_points = " ".join(f"{top_x(index):.1f},{top_scale(value):.1f}" for index, value in enumerate(fitted))
    svg.append(f'<polyline points="{observed_points}" fill="none" stroke="{color}" stroke-width="1.6"/>')
    for index, value in enumerate(observed):
        svg.append(f'<circle cx="{top_x(index):.1f}" cy="{top_scale(value):.1f}" r="2.2" fill="{color}"/>')
    svg.append(f'<polyline points="{fitted_points}" fill="none" stroke="{fitted_color}" stroke-width="2.2"/>')
    svg.append(f'<line x1="{width-245}" y1="{top_y+8}" x2="{width-215}" y2="{top_y+8}" stroke="{color}" stroke-width="2"/>')
    svg.append(f'<text x="{width-207}" y="{top_y+12}" font-family="Arial, sans-serif" font-size="10" fill="#333">Observed</text>')
    svg.append(f'<line x1="{width-145}" y1="{top_y+8}" x2="{width-115}" y2="{top_y+8}" stroke="{fitted_color}" stroke-width="2.2"/>')
    svg.append(f'<text x="{width-107}" y="{top_y+12}" font-family="Arial, sans-serif" font-size="10" fill="#333">Fitted</text>')
    svg.append(f'<text x="20" y="{top_y+top_h/2}" transform="rotate(-90 20 {top_y+top_h/2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#333">Monthly project starts</text>')

    svg.append(f'<text x="{left}" y="{bottom_y-18}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#333">Artificial slope changes using only Oct 2021-Jun 2024</text>')
    for fraction in (0.0, 0.5, 1.0):
        value = slope_min + fraction * (slope_max - slope_min)
        yy = bottom_scale(value)
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#E2E2E2"/>')
        svg.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="10" fill="#555">{value:.2f}</text>')
    zero_y = bottom_scale(0.0)
    svg.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{width-right}" y2="{zero_y:.1f}" stroke="#666" stroke-width="1.1"/>')
    actual_y = bottom_scale(actual_slope)
    svg.append(f'<line x1="{left}" y1="{actual_y:.1f}" x2="{width-right}" y2="{actual_y:.1f}" stroke="{fitted_color}" stroke-width="1.7" stroke-dasharray="7 5"/>')
    svg.append(f'<text x="{width-right-4}" y="{actual_y-6:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="10" fill="{fitted_color}">Actual Jul 2024 slope change = {actual_slope:.3f}</text>')
    for index, row in enumerate(placebos):
        xx = bottom_x(index)
        low = bottom_scale(float(row["slope_ci_low"]))
        high = bottom_scale(float(row["slope_ci_high"]))
        estimate = bottom_scale(float(row["slope_change"]))
        svg.append(f'<line x1="{xx:.1f}" y1="{low:.1f}" x2="{xx:.1f}" y2="{high:.1f}" stroke="{color}" stroke-width="1.4"/>')
        svg.append(f'<line x1="{xx-4:.1f}" y1="{low:.1f}" x2="{xx+4:.1f}" y2="{low:.1f}" stroke="{color}"/>')
        svg.append(f'<line x1="{xx-4:.1f}" y1="{high:.1f}" x2="{xx+4:.1f}" y2="{high:.1f}" stroke="{color}"/>')
        svg.append(f'<circle cx="{xx:.1f}" cy="{estimate:.1f}" r="4" fill="{color}"/>')
        svg.append(f'<text x="{xx:.1f}" y="{bottom_y+bottom_h+21}" text-anchor="middle" font-family="Arial, sans-serif" font-size="9" fill="#555">{row["intervention_date"]}</text>')
    svg.append(f'<text x="20" y="{bottom_y+bottom_h/2}" transform="rotate(-90 20 {bottom_y+bottom_h/2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#333">Slope change</text>')
    svg.append(f'<text x="{left}" y="{height-13}" font-family="Arial, sans-serif" font-size="10" fill="#555">Points show artificial slope changes; bars are 95% HAC confidence intervals. The green dashed line is the full-window actual July 2024 estimate.</text>')
    svg.append("</svg>")
    core.write_text(FIGURE_DIR / f"figure_{metadata['figure_stem']}_its_placebos.svg", "\n".join(svg))


def validate_outputs(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    if len(rows) != 48:
        raise AssertionError(f"expected 48 single-series result rows, found {len(rows)}")
    if len(summary) != 5:
        raise AssertionError(f"expected 5 comparison rows, found {len(summary)}")
    for series_id in SERIES:
        actual = [row for row in rows if row["series_id"] == series_id and row["design"] == "actual_full"]
        placebos = [row for row in rows if row["series_id"] == series_id and row["design"] == "placebo_all_pre"]
        matched = [row for row in rows if row["series_id"] == series_id and row["design"] == "placebo_18_12"]
        if len(actual) != 1 or len(placebos) != 10 or len(matched) != 4:
            raise AssertionError(f"unexpected model count for {series_id}")
        if any(int(row["n_obs"]) != 33 or int(row["df_resid"]) != 18 for row in placebos):
            raise AssertionError(f"{series_id} placebo support changed")


def main() -> None:
    all_rows: list[dict[str, object]] = []
    figure_data: dict[str, dict[str, object]] = {}
    for series_id in SERIES:
        rows, payload = run_one_series(series_id)
        all_rows.extend(rows)
        figure_data[series_id] = payload
    difference_rows = existing_difference_rows()
    verify_decomposition(all_rows, difference_rows)
    summary = make_summary(all_rows, difference_rows)
    validate_outputs(all_rows, summary)
    core.write_csv(DATA_DIR / "series_decomposition_results.csv", all_rows, RESULT_FIELDS)
    core.write_csv(DATA_DIR / "series_decomposition_summary.csv", summary, SUMMARY_FIELDS)
    write_report(all_rows, summary, difference_rows)
    write_stata_report(all_rows, summary)
    for series_id in SERIES:
        make_figure(series_id, all_rows, figure_data[series_id])
    print("Wrote series-decomposition diagnostic outputs")
    for row in summary:
        print(
            row["object_id"],
            "actual", row["actual_slope_change"],
            "placebo range", f"[{row['placebo_slope_min']}, {row['placebo_slope_max']}]",
            "significant", f"{row['placebo_slope_p_lt_0_05_n']}/{row['placebo_n']}",
        )


if __name__ == "__main__":
    main()
