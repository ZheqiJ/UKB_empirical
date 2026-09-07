#!/usr/bin/env python3
"""Application-level modified Poisson models for curated and broad outcomes.

This script consumes the fixed public valid-start-date application universe and
the existing attribution tier table.  It does not rerun or alter DMCA matching.
"""

from __future__ import annotations

import csv
import html
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from analyze_curated52_broad55 import application_design, build_application_rows, fmt_pvalue, read_csv
from leakage_its_analysis import BREAK_MONTH, POLICY_DATE, clean, fmt, invert, mat_mul, normal_pvalue, poisson_qmle, write_csv, write_text


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "ukb_dmca" / "leakage_application_analysis"
DATA_DIR = PACKAGE / "data"
TABLE_DIR = PACKAGE / "tables"
FIGURE_DIR = PACKAGE / "figures"
REPORT_DIR = PACKAGE / "reports"
TIER_TABLE = ROOT / "ukb_dmca" / "application_level_attribution_tiers.csv"

OUTCOME_META = {
    "Leak52": {
        "label": "Curated 52 attribution outcome",
        "source_membership": 52,
        "description": "Current curated baseline applications",
    },
    "Leak55": {
        "label": "Broad 55 attribution outcome",
        "source_membership": 55,
        "description": "Curated 52 plus the three Tier-4 single-application ambiguous additions",
    },
    "Leak269": {
        "label": "Candidate-inclusive upper-bound attribution outcome",
        "source_membership": 269,
        "description": "Tier 1 through Tier 5 source membership; the fixed valid-date universe contains 266 of these applications",
    },
}
FIGURE_LABELS = {
    "Leak52": "Curated 52",
    "Leak55": "Broad 55",
    "Leak269": "Candidate-inclusive upper bound",
}
CORE_TERMS = ["Time", "PostJuly2024", "TimeAfterJuly2024"]
DISPLAY_TERMS = ["Intercept", *CORE_TERMS, *[f"month_{month:02d}" for month in range(1, 13)]]


def month_label(value: str) -> str:
    return value[:7]


def add_outer(matrix: list[list[float]], vector: list[float]) -> None:
    for i, left in enumerate(vector):
        for j, right in enumerate(vector):
            matrix[i][j] += left * right


def poisson_with_inference(X: list[list[float]], y: list[float], clusters: list[str]) -> dict[str, object]:
    """Fit Poisson QMLE and calculate CR1 clustered and HC1 sandwich VCOVs."""
    fit = poisson_qmle(X, y)
    beta = [float(value) for value in fit["beta"]]
    mu = [float(value) for value in fit["fitted"]]
    n, k = len(y), len(beta)
    hessian = [[0.0] * k for _ in range(k)]
    individual_scores: list[list[float]] = []
    grouped_scores: dict[str, list[float]] = defaultdict(lambda: [0.0] * k)
    for row, outcome, fitted, cluster in zip(X, y, mu, clusters):
        score = [value * (outcome - fitted) for value in row]
        individual_scores.append(score)
        for index, value in enumerate(score):
            grouped_scores[cluster][index] += value
        for i in range(k):
            for j in range(k):
                hessian[i][j] += row[i] * fitted * row[j]
    max_score = max(abs(sum(score[index] for score in individual_scores)) for index in range(k))
    if max_score > 1e-5:
        raise RuntimeError(f"Poisson QMLE score remains too large after fitting ({max_score:.3g}).")
    bread = invert(hessian)
    hc_meat = [[0.0] * k for _ in range(k)]
    for score in individual_scores:
        add_outer(hc_meat, score)
    hc_scale = n / (n - k)
    hc_vcov_base = mat_mul(mat_mul(bread, hc_meat), bread)
    hc_vcov = [[hc_scale * value for value in row] for row in hc_vcov_base]
    cluster_meat = [[0.0] * k for _ in range(k)]
    for score in grouped_scores.values():
        add_outer(cluster_meat, score)
    cluster_count = len(grouped_scores)
    cluster_scale = (cluster_count / (cluster_count - 1)) * ((n - 1) / (n - k))
    clustered_base = mat_mul(mat_mul(bread, cluster_meat), bread)
    clustered_vcov = [[cluster_scale * value for value in row] for row in clustered_base]
    log_pseudolikelihood = sum(
        outcome * math.log(max(fitted, 1e-300)) - fitted - math.lgamma(outcome + 1.0)
        for outcome, fitted in zip(y, mu)
    )
    return {
        "beta": beta,
        "fitted": mu,
        "cluster_vcov": clustered_vcov,
        "hc_vcov": hc_vcov,
        "cluster_count": cluster_count,
        "n": n,
        "k": k,
        "cluster_correction": cluster_scale,
        "pearson_dispersion": float(fit["pearson_dispersion"]),
        "solver_converged_flag": bool(fit["converged"]),
        "max_absolute_score": max_score,
        "log_pseudolikelihood": log_pseudolikelihood,
    }


def inference_fields(beta: float, variance: float) -> dict[str, float]:
    se = math.sqrt(max(variance, 0.0))
    z = beta / se if se else math.nan
    p_value = normal_pvalue(beta, se)
    return {
        "estimate": beta,
        "se": se,
        "z": z,
        "p_value": p_value,
        "ci_low": beta - 1.96 * se,
        "ci_high": beta + 1.96 * se,
    }


def coefficient_records(outcome: str, fit: dict[str, object]) -> list[dict[str, object]]:
    beta = fit["beta"]
    cluster_vcov = fit["cluster_vcov"]
    names = fit["names"]
    separated_months = fit["separated_months"]
    reference_month = fit["reference_month"]
    assert isinstance(beta, list) and isinstance(cluster_vcov, list) and isinstance(names, list) and isinstance(separated_months, set)
    rows: list[dict[str, object]] = []
    for term in DISPLAY_TERMS:
        month = int(term[-2:]) if term.startswith("month_") else None
        if term not in names:
            status = "omitted_perfect_zero_prediction" if month in separated_months else "reference_month_omitted"
            rows.append(
                {
                    "outcome": outcome, "outcome_label": OUTCOME_META[outcome]["label"], "coefficient": term,
                    "estimate_beta": "", "clustered_se": "", "z": "", "p_value": "", "ci_low": "", "ci_high": "",
                    "coefficient_status": status, "n_applications": fit["n"], "analytic_universe_applications": fit["analytic_universe_n"],
                    "start_month_clusters": fit["cluster_count"], "month_of_year_fixed_effects": "yes",
                    "inference": "Poisson QMLE, CR1 sandwich SE clustered by application start month",
                    "source_membership_applications": OUTCOME_META[outcome]["source_membership"], "analytic_positive_applications": "",
                }
            )
            continue
        index = names.index(term)
        stats = inference_fields(float(beta[index]), float(cluster_vcov[index][index]))
        rows.append(
            {
                "outcome": outcome,
                "outcome_label": OUTCOME_META[outcome]["label"],
                "coefficient": term,
                "estimate_beta": fmt(stats["estimate"], 8),
                "clustered_se": fmt(stats["se"], 8),
                "z": fmt(stats["z"], 6),
                "p_value": fmt_pvalue(stats["p_value"]),
                "ci_low": fmt(stats["ci_low"], 8),
                "ci_high": fmt(stats["ci_high"], 8),
                "coefficient_status": "estimated",
                "n_applications": fit["n"],
                "analytic_universe_applications": fit["analytic_universe_n"],
                "start_month_clusters": fit["cluster_count"],
                "month_of_year_fixed_effects": "yes",
                "inference": "Poisson QMLE, CR1 sandwich SE clustered by application start month",
                "source_membership_applications": OUTCOME_META[outcome]["source_membership"],
                "analytic_positive_applications": "",
            }
        )
    return rows


def raw_descriptive(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    pre = [row for row in rows if int(row["Post"]) == 0]
    post = [row for row in rows if int(row["Post"]) == 1]
    for outcome, meta in OUTCOME_META.items():
        pre_events = sum(int(row[outcome]) for row in pre)
        post_events = sum(int(row[outcome]) for row in post)
        analytic_events = pre_events + post_events
        result.append(
            {
                "outcome": outcome,
                "outcome_label": meta["label"],
                "source_membership_applications": meta["source_membership"],
                "analytic_positive_applications": analytic_events,
                "pre_applications": len(pre),
                "pre_events": pre_events,
                "pre_rate": fmt(pre_events / len(pre), 8),
                "post_applications": len(post),
                "post_events": post_events,
                "post_rate": fmt(post_events / len(post), 8),
                "post_minus_pre_percentage_points": fmt(100 * (post_events / len(post) - pre_events / len(pre)), 4),
                "policy_date": POLICY_DATE.isoformat(),
                "note": "Raw descriptive rates; not a causal estimate.",
            }
        )
    return result


def membership_audit(tier_rows: list[dict[str, str]], application_rows: list[dict[str, object]]) -> tuple[set[str], list[dict[str, object]]]:
    selected = [row for row in tier_rows if clean(row.get("tier")) in {"Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"}]
    candidate_ids = {clean(row.get("application_id")) for row in selected if clean(row.get("application_id"))}
    if len(candidate_ids) != 269:
        raise ValueError(f"Expected 269 Tier 1-5 application IDs, found {len(candidate_ids)}.")
    valid_rows = {str(row["application_id"]): row for row in application_rows}
    audit: list[dict[str, object]] = []
    for tier_row in sorted(selected, key=lambda row: int(clean(row["application_id"]))):
        app_id = clean(tier_row["application_id"])
        application = valid_rows.get(app_id)
        audit.append(
            {
                "application_id": app_id,
                "application_title": clean(tier_row.get("application_title")),
                "tier": clean(tier_row.get("tier")),
                "source_set": "candidate-inclusive upper-bound attribution",
                "has_valid_public_start_date": "yes" if application else "no",
                "project_start_date": application["project_start_date"] if application else "",
                "included_in_fixed_6935_application_universe": "yes" if application else "no",
                "exclusion_reason": "" if application else "No public valid start date; excluded without expanding the fixed 6,935-application universe.",
            }
        )
    analytic_ids = candidate_ids & set(valid_rows)
    if len(analytic_ids) != 266:
        raise ValueError(f"Expected 266 candidate-inclusive IDs in valid-date universe, found {len(analytic_ids)}.")
    return candidate_ids, audit


def outcome_design(rows: list[dict[str, object]], outcome: str) -> tuple[list[dict[str, object]], list[list[float]], list[str], set[int], int]:
    """Return the finite Poisson component after exact zero-cell separation handling.

    A calendar month with no outcome events perfectly predicts zero under a
    saturated month-of-year FE specification. Its finite MLE coefficient is
    minus infinity. The conventional Poisson separation limit drops that cell
    from finite-coefficient estimation and assigns it a zero fitted mean.
    """
    events_by_month = {month: sum(int(row[outcome]) for row in rows if int(row["start_month_number"]) == month) for month in range(1, 13)}
    separated_months = {month for month, events in events_by_month.items() if events == 0}
    estimable_months = [month for month in range(1, 13) if month not in separated_months]
    if not estimable_months:
        raise ValueError(f"{outcome} has no events in any month-of-year cell.")
    reference_month = estimable_months[0]
    names = ["Intercept", *CORE_TERMS] + [f"month_{month:02d}" for month in estimable_months if month != reference_month]
    selected = [row for row in rows if int(row["start_month_number"]) not in separated_months]
    X = [
        [1.0, float(row["Time"]), float(row["Post"]), float(row["TimeAfter"])]
        + [1.0 if int(row["start_month_number"]) == month else 0.0 for month in estimable_months if month != reference_month]
        for row in selected
    ]
    return selected, X, names, separated_months, reference_month


def monthly_series(rows: list[dict[str, object]], outcome: str, fitted: list[float]) -> list[dict[str, object]]:
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    for row, value in zip(rows, fitted):
        month = str(row["start_month"])
        totals[month]["n"] += 1
        totals[month]["events"] += int(row[outcome])
        totals[month]["fitted_sum"] += value
    out = []
    for month in sorted(totals):
        counts = totals[month]
        out.append(
            {
                "start_month": month,
                "n_applications": counts["n"],
                "observed_events": counts["events"],
                "observed_rate": counts["events"] / counts["n"],
                "fitted_rate": counts["fitted_sum"] / counts["n"],
            }
        )
    return out


def svg_chart(path: Path, series: dict[str, list[dict[str, object]]], mode: str, common_scale: bool = False) -> None:
    width, height = 1180, 440
    margin_x, top, bottom, gap = 72, 48, 60, 36
    panel_w = (width - 2 * margin_x - 2 * gap) / 3
    panel_h = height - top - bottom
    all_values = [float(point[key]) for values in series.values() for point in values for key in (["fitted_rate"] if mode == "fitted" else ["observed_rate", "fitted_rate"])]
    global_max = max(all_values) * 1.12 if all_values else 0.01
    start = date.fromisoformat(min(point["start_month"] for values in series.values() for point in values))
    end = date.fromisoformat(max(point["start_month"] for values in series.values() for point in values))
    palette = {"Leak52": "#1f6b75", "Leak55": "#b65736", "Leak269": "#5a7b3d"}

    def x(value: date, left: float) -> float:
        return left + ((value - start).days / max((end - start).days, 1)) * panel_w

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="700">Application-level Poisson: observed and fitted rates</text>' if mode == "observed_fitted" else f'<text x="{width / 2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="700">Application-level Poisson: fitted trajectories</text>',
    ]
    for panel, outcome in enumerate(OUTCOME_META):
        left = margin_x + panel * (panel_w + gap)
        points = series[outcome]
        panel_max = global_max if common_scale else max(max(float(point["observed_rate"]), float(point["fitted_rate"])) for point in points) * 1.12
        panel_max = max(panel_max, 0.005)
        def y(value: float) -> float:
            return top + (panel_max - value) / panel_max * panel_h
        svg.append(f'<text x="{left + panel_w / 2:.1f}" y="{top - 10}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700">{html.escape(FIGURE_LABELS[outcome])}</text>')
        for fraction in (0, 0.5, 1):
            value = panel_max * fraction
            yy = y(value)
            svg.append(f'<line x1="{left:.1f}" y1="{yy:.1f}" x2="{left + panel_w:.1f}" y2="{yy:.1f}" stroke="#e5e5e5"/>')
            svg.append(f'<text x="{left - 7:.1f}" y="{yy + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="9" fill="#444">{100 * value:.1f}%</text>')
        for year in range(start.year, end.year + 1):
            tick = date(year, 1, 1)
            if start <= tick <= end:
                xx = x(tick, left)
                svg.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{top + panel_h}" stroke="#f0f0f0"/>')
                svg.append(f'<text x="{xx:.1f}" y="{top + panel_h + 19}" text-anchor="middle" font-family="Arial, sans-serif" font-size="9" fill="#444">{year}</text>')
        break_x = x(BREAK_MONTH, left)
        svg.append(f'<line x1="{break_x:.1f}" y1="{top}" x2="{break_x:.1f}" y2="{top + panel_h}" stroke="#222" stroke-width="1.2"/>')
        if panel == 0:
            svg.append(f'<text x="{break_x + 4:.1f}" y="{top + 12}" font-family="Arial, sans-serif" font-size="9" fill="#222">Jul 2024</text>')
        fitted_path = " ".join(f"{'M' if index == 0 else 'L'} {x(date.fromisoformat(point['start_month']), left):.1f} {y(float(point['fitted_rate'])):.1f}" for index, point in enumerate(points))
        svg.append(f'<path d="{fitted_path}" fill="none" stroke="{palette[outcome]}" stroke-width="2.1"/>')
        if mode == "observed_fitted":
            for point in points:
                svg.append(f'<circle cx="{x(date.fromisoformat(point["start_month"]), left):.1f}" cy="{y(float(point["observed_rate"])):.1f}" r="2.2" fill="#545454"/>')
        if panel == 0:
            legend_y = top + panel_h + 41
            if mode == "observed_fitted":
                svg.append(f'<circle cx="{left:.1f}" cy="{legend_y - 3}" r="2.2" fill="#545454"/><text x="{left + 7:.1f}" y="{legend_y}" font-family="Arial, sans-serif" font-size="10">Observed monthly rate</text>')
                svg.append(f'<line x1="{left + 126:.1f}" y1="{legend_y - 3}" x2="{left + 143:.1f}" y2="{legend_y - 3}" stroke="#1f6b75" stroke-width="2"/><text x="{left + 150:.1f}" y="{legend_y}" font-family="Arial, sans-serif" font-size="10">Fitted app-level prediction</text>')
    svg.append('</svg>')
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def write_stata(results: dict[str, dict[str, object]], raw: list[dict[str, object]]) -> None:
    lines = [
        "Stata-format regression output generated by the reproducible Python analysis pipeline.",
        "This is a Stata-style layout, not a transcript from a Stata session.",
        "Timing: exact application start date; PostJuly2024 = 1[start_date >= 2024-07-05].",
        "VCE: CR1 sandwich clustered by application start month.",
        "",
    ]
    for outcome in OUTCOME_META:
        fit = results[outcome]
        beta, vcov = fit["beta"], fit["cluster_vcov"]
        names = fit["names"]
        separated_months = fit["separated_months"]
        assert isinstance(beta, list) and isinstance(vcov, list) and isinstance(names, list) and isinstance(separated_months, set)
        command = f". poisson {outcome} c.Time i.PostJuly2024 c.TimeAfterJuly2024 i.start_month_number, vce(cluster start_month)"
        lines += [command, ""]
        lines.append("Poisson regression (modified Poisson QMLE)".ljust(70) + f"Number of obs   = {fit['n']:>8}")
        lines.append("".ljust(70) + f"Number of clusters (start_month) = {fit['cluster_count']:>5}")
        lines.append(f"Log pseudolikelihood = {float(fit['log_pseudolikelihood']):>12.6f}")
        lines.append("(Std. Err. adjusted for clustering on application start month)")
        lines.append("".ljust(104, "-"))
        lines.append(f"{'':<24}|{'Robust':>27}")
        lines.append(f"{outcome:<24}|{'Coefficient':>13}{'std. err.':>13}{'z':>10}{'P>|z|':>12}{'[95% conf. interval]':>30}")
        lines.append("".ljust(104, "-"))
        stata_terms = [*CORE_TERMS, *[f"month_{month:02d}" for month in range(1, 13)], "Intercept"]
        for term in stata_terms:
            month = int(term[-2:]) if term.startswith("month_") else None
            label = f"{month}.start_month_number" if month is not None else ("_cons" if term == "Intercept" else ("1.PostJuly2024" if term == "PostJuly2024" else term))
            if term not in names:
                note = "omitted: perfect zero prediction" if month in separated_months else "base category"
                lines.append(f"{label:<24}|{note:>73}")
                continue
            index = names.index(term)
            stats = inference_fields(float(beta[index]), float(vcov[index][index]))
            lines.append(f"{label:<24}|{stats['estimate']:>13.6f}{stats['se']:>13.6f}{stats['z']:>10.3f}{stats['p_value']:>12.6g}{stats['ci_low']:>15.6f}{stats['ci_high']:>15.6f}")
        separated_text = ", ".join(str(month) for month in sorted(separated_months)) or "none"
        lines.append("".ljust(104, "-"))
        lines.append(f"Note: analytic universe = {fit['analytic_universe_n']}; finite-estimation N = {fit['n']}; zero-event separated months = {separated_text}; Pearson dispersion = {fit['pearson_dispersion']:.4f}.")
        lines.append("")
    lines.append("Raw descriptive event totals:")
    for row in raw:
        lines.append(f"{row['outcome']}: source membership={row['source_membership_applications']}, analytic positives={row['analytic_positive_applications']}, pre={row['pre_events']}/{row['pre_applications']}, post={row['post_events']}/{row['post_applications']}")
    lines.append("Leak269 source membership is 269; three Tier-5 applications lack public valid start dates, so 266 positives enter the fixed 6,935-application model.")
    write_text(REPORT_DIR / "application_modified_poisson_52_55_269_stata.txt", "\n".join(lines) + "\n")


def write_report(results: dict[str, dict[str, object]], raw: list[dict[str, object]], linear: list[dict[str, object]]) -> None:
    raw_by_outcome = {str(row["outcome"]): row for row in raw}
    core = []
    for outcome in OUTCOME_META:
        fit = results[outcome]
        beta, vcov = fit["beta"], fit["cluster_vcov"]
        names = fit["names"]
        assert isinstance(beta, list) and isinstance(vcov, list) and isinstance(names, list)
        fields = {term: inference_fields(float(beta[index]), float(vcov[index][index])) for index, term in enumerate(names)}
        post = fields["PostJuly2024"]
        raw_row = raw_by_outcome[outcome]
        core.append(
            f"| {OUTCOME_META[outcome]['label']} | {raw_row['source_membership_applications']} | {raw_row['analytic_positive_applications']} | {100 * float(raw_row['pre_rate']):.3f}% | {100 * float(raw_row['post_rate']):.3f}% | {post['estimate']:.4f} | {post['se']:.4f} | {post['p_value']:.4g} | [{post['ci_low']:.4f}, {post['ci_high']:.4f}] |"
        )
    linear_rows = []
    for row in linear:
        linear_rows.append(f"| {row['outcome_label']} | {row['estimate_beta']} | {row['clustered_se']} | {row['p_value']} | [{row['ci_low']}, {row['ci_high']}] |")
    content = f"""# Application-Level Modified Poisson Results: 52, 55, and Candidate-Inclusive Attribution Outcomes

## Outcome Construction

The analysis unit is a UK Biobank application in the fixed public valid-start-date universe (`N = 6,935`). `Leak52` marks the current curated 52 applications. `Leak55` adds the three existing Tier-4 single-application ambiguous additions. `Leak269` is the candidate-inclusive upper-bound attribution outcome based on all Tier 1-5 application IDs in the existing tier table.

The candidate-inclusive source membership contains 269 unique application IDs. Three Tier-5 UK Biobank internal applications (`68250`, `77202`, and `80154`) have no public valid start date, so they cannot enter a model with application timing and are not added to or imputed into the fixed 6,935-application universe. Consequently, `Leak269` has 266 analytic positive applications. This is a timing-data limitation, not a rematch or a revision to the 269-ID source set.

## Raw Descriptive Rates

The table shows raw application-start-date rates before and after 5 July 2024. These descriptive differences are not causal estimates.

| Outcome | Source membership | Analytic positives | Pre rate | Post rate | Post beta | Clustered SE | p-value | 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(core)}

## Primary Modified Poisson Specification

For each outcome, the primary model is `log E[Leak_s,i | X] = beta0 + beta1 Time + beta2 PostJuly2024 + beta3 TimeAfterJuly2024 + month-of-year fixed effects`, where `PostJuly2024 = 1[start_date >= 2024-07-05]`. It is estimated as Poisson QMLE (modified Poisson). Primary inference uses CR1 sandwich standard errors clustered by application start month; the full results include all month-of-year indicators and their Stata-style omission status. The raw beta coefficients are the primary estimands. Exponentiated coefficients are reported separately as risk ratios.

`PostJuly2024` is a level discontinuity on the log expected leakage-probability scale conditional on the pre-policy time trend and month-of-year fixed effects. `Time` is the pre-policy monthly log-scale slope and `TimeAfterJuly2024` is the change in that monthly slope after July 2024. These associations use application start dates only; they do not use DMCA notice, repository, or commit dates as timing.

## Post-Policy Slope

The post-policy monthly log-scale slope is `beta_Time + beta_TimeAfterJuly2024`; delta-method CR1 inference is below.

| Outcome | beta(Time + TimeAfter) | Clustered SE | p-value | 95% CI |
|---|---:|---:|---:|---:|
{chr(10).join(linear_rows)}

## Robustness and Figures

For `Leak52` and `Leak55`, January has zero events and therefore perfectly predicts zero under a saturated month-FE Poisson model. The finite QMLE component follows the separation limit: January is explicitly shown as omitted for perfect zero prediction, its fitted mean is zero, and the remaining finite coefficients use 6,284 applications. The analytic universe remains the fixed 6,935 applications; this handling avoids presenting divergent coefficients as valid estimates. `Leak269` has a finite month-FE model on all 6,935 applications.

The companion inference table contrasts the primary start-month-clustered sandwich SE with unclustered HC1 sandwich SE. The figures aggregate application-level observed outcomes and fitted Poisson predictions to start month only for display; no monthly or quarterly model is used as the primary estimator. The common-scale plot is a visual diagnostic.

This observational application-timing analysis does not establish a causal effect of the July 2024 RAP transition. It does not select a preferred outcome based on statistical significance. The candidate-inclusive upper-bound outcome is deliberately kept separate from the curated and broad outcomes because its attribution evidence is weaker by construction.
"""
    write_text(REPORT_DIR / "application_modified_poisson_52_55_269_results.md", content)


def main() -> None:
    for directory in (DATA_DIR, TABLE_DIR, FIGURE_DIR, REPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    application_rows, _, curated_ids, tier4_ids = build_application_rows()
    tier_rows = read_csv(TIER_TABLE)
    candidate_ids, audit = membership_audit(tier_rows, application_rows)
    for row in application_rows:
        row["Leak269"] = int(str(row["application_id"]) in candidate_ids)
    if sum(int(row["Leak52"]) for row in application_rows) != 52:
        raise ValueError("Leak52 membership changed unexpectedly.")
    if sum(int(row["Leak55"]) for row in application_rows) != 55:
        raise ValueError("Leak55 membership changed unexpectedly.")
    if sum(int(row["Leak269"]) for row in application_rows) != 266:
        raise ValueError("Leak269 must have 266 timed positives in the fixed universe.")
    if len(curated_ids) != 52 or len(curated_ids | tier4_ids) != 55:
        raise ValueError("Existing curated membership validation failed.")

    write_csv(DATA_DIR / "candidate_inclusive_269_membership_audit.csv", audit, list(audit[0]))
    raw = raw_descriptive(application_rows)
    write_csv(TABLE_DIR / "application_modified_poisson_52_55_269_raw_descriptive.csv", raw, list(raw[0]))
    results: dict[str, dict[str, object]] = {}
    full_rows: list[dict[str, object]] = []
    compact_rows: list[dict[str, object]] = []
    exponentiated_rows: list[dict[str, object]] = []
    robustness_rows: list[dict[str, object]] = []
    linear_rows: list[dict[str, object]] = []
    all_series: dict[str, list[dict[str, object]]] = {}
    for outcome in OUTCOME_META:
        selected_rows, X, names, separated_months, reference_month = outcome_design(application_rows, outcome)
        y = [float(row[outcome]) for row in selected_rows]
        clusters = [month_label(str(row["start_month"])) for row in selected_rows]
        fit = poisson_with_inference(X, y, clusters)
        fit.update({
            "names": names,
            "separated_months": separated_months,
            "reference_month": reference_month,
            "analytic_universe_n": len(application_rows),
        })
        results[outcome] = fit
        coefficient_rows = coefficient_records(outcome, fit)
        analytic_count = sum(int(row[outcome]) for row in application_rows)
        for row in coefficient_rows:
            row["analytic_positive_applications"] = analytic_count
        full_rows.extend(coefficient_rows)
        beta, cluster_vcov, hc_vcov = fit["beta"], fit["cluster_vcov"], fit["hc_vcov"]
        assert isinstance(beta, list) and isinstance(cluster_vcov, list) and isinstance(hc_vcov, list)
        compact = {"outcome": outcome, "outcome_label": OUTCOME_META[outcome]["label"], "n_applications": fit["n"], "analytic_universe_applications": len(application_rows), "start_month_clusters": fit["cluster_count"], "month_of_year_fixed_effects": "yes", "zero_event_months_omitted": "; ".join(str(month) for month in sorted(separated_months)), "source_membership_applications": OUTCOME_META[outcome]["source_membership"], "analytic_positive_applications": analytic_count}
        for term in CORE_TERMS:
            index = names.index(term)
            stats = inference_fields(float(beta[index]), float(cluster_vcov[index][index]))
            compact[f"{term}_beta"] = fmt(stats["estimate"], 8)
            compact[f"{term}_clustered_se"] = fmt(stats["se"], 8)
            compact[f"{term}_p_value"] = fmt_pvalue(stats["p_value"])
        compact_rows.append(compact)
        for term in CORE_TERMS:
            index = names.index(term)
            stats = inference_fields(float(beta[index]), float(cluster_vcov[index][index]))
            exponentiated_rows.append({
                "outcome": outcome, "outcome_label": OUTCOME_META[outcome]["label"], "coefficient": term,
                "risk_ratio_exp_beta": fmt(math.exp(stats["estimate"]), 8),
                "clustered_se_log_scale": fmt(stats["se"], 8),
                "rr_ci_low": fmt(math.exp(stats["ci_low"]), 8), "rr_ci_high": fmt(math.exp(stats["ci_high"]), 8),
                "p_value_log_scale": fmt_pvalue(stats["p_value"]),
            })
            for inference_name, vcov in (("primary_CR1_start_month_clustered", cluster_vcov), ("secondary_HC1_unclustered_sandwich", hc_vcov)):
                comparison = inference_fields(float(beta[index]), float(vcov[index][index]))
                robustness_rows.append({
                    "outcome": outcome, "outcome_label": OUTCOME_META[outcome]["label"], "coefficient": term,
                    "inference": inference_name, "estimate_beta": fmt(comparison["estimate"], 8), "se": fmt(comparison["se"], 8),
                    "z": fmt(comparison["z"], 6), "p_value": fmt_pvalue(comparison["p_value"]),
                    "ci_low": fmt(comparison["ci_low"], 8), "ci_high": fmt(comparison["ci_high"], 8),
                    "n_applications": fit["n"], "analytic_universe_applications": len(application_rows), "start_month_clusters": fit["cluster_count"],
                })
        time_idx, after_idx = names.index("Time"), names.index("TimeAfterJuly2024")
        linear_beta = float(beta[time_idx]) + float(beta[after_idx])
        linear_var = float(cluster_vcov[time_idx][time_idx]) + float(cluster_vcov[after_idx][after_idx]) + 2 * float(cluster_vcov[time_idx][after_idx])
        linear_stats = inference_fields(linear_beta, linear_var)
        linear_rows.append({
            "outcome": outcome, "outcome_label": OUTCOME_META[outcome]["label"], "linear_combination": "Time + TimeAfterJuly2024",
            "estimate_beta": fmt(linear_stats["estimate"], 8), "clustered_se": fmt(linear_stats["se"], 8), "z": fmt(linear_stats["z"], 6),
            "p_value": fmt_pvalue(linear_stats["p_value"]), "ci_low": fmt(linear_stats["ci_low"], 8), "ci_high": fmt(linear_stats["ci_high"], 8),
            "risk_ratio_exp_beta": fmt(math.exp(linear_stats["estimate"]), 8), "rr_ci_low": fmt(math.exp(linear_stats["ci_low"]), 8), "rr_ci_high": fmt(math.exp(linear_stats["ci_high"]), 8),
            "n_applications": fit["n"], "analytic_universe_applications": len(application_rows), "start_month_clusters": fit["cluster_count"],
        })
        fitted_by_app_id = {str(row["application_id"]): float(value) for row, value in zip(selected_rows, fit["fitted"])}
        full_fitted = [fitted_by_app_id.get(str(row["application_id"]), 0.0) for row in application_rows]
        all_series[outcome] = monthly_series(application_rows, outcome, full_fitted)

    write_csv(TABLE_DIR / "application_modified_poisson_52_55_269.csv", full_rows, list(full_rows[0]))
    write_csv(TABLE_DIR / "application_modified_poisson_52_55_269_compact.csv", compact_rows, list(compact_rows[0]))
    write_csv(TABLE_DIR / "application_modified_poisson_52_55_269_exponentiated.csv", exponentiated_rows, list(exponentiated_rows[0]))
    write_csv(TABLE_DIR / "application_modified_poisson_52_55_269_linear_combinations.csv", linear_rows, list(linear_rows[0]))
    write_csv(TABLE_DIR / "application_modified_poisson_52_55_269_inference_robustness.csv", robustness_rows, list(robustness_rows[0]))
    monthly_output = [dict(point, outcome=outcome, outcome_label=OUTCOME_META[outcome]["label"]) for outcome, points in all_series.items() for point in points]
    write_csv(DATA_DIR / "application_modified_poisson_52_55_269_monthly_observed_fitted.csv", monthly_output, list(monthly_output[0]))
    svg_chart(FIGURE_DIR / "application_modified_poisson_52_55_269_observed_fitted.svg", all_series, "observed_fitted")
    svg_chart(FIGURE_DIR / "application_modified_poisson_52_55_269_fitted_trajectories.svg", all_series, "fitted")
    svg_chart(FIGURE_DIR / "application_modified_poisson_52_55_269_common_scale.svg", all_series, "observed_fitted", common_scale=True)
    write_stata(results, raw)
    write_report(results, raw, linear_rows)


if __name__ == "__main__":
    main()
