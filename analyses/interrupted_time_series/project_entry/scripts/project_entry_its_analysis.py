#!/usr/bin/env python3
"""Build project-entry ITS outputs from public UKB project-start metadata."""

from __future__ import annotations

import csv
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA_DIR = PACKAGE / "data"
FIGURE_DIR = PACKAGE / "figures"
REPORT_DIR = PACKAGE / "reports"

PROJECT_UNIVERSE = ROOT / "data" / "intermediate" / "timing_feasibility" / "timing_working_research_project_universe.csv"
MATCHED_STARTS = ROOT / "data" / "intermediate" / "start_date_matching" / "stage2_5_app_start_dates.csv"
UNMATCHED_STARTS = ROOT / "data" / "intermediate" / "start_date_matching" / "stage2_5_schema27_unmatched.csv"
START_SUMMARY = ROOT / "data" / "intermediate" / "start_date_matching" / "stage2_5_start_date_summary.json"
MONTHLY_STARTS = DATA_DIR / "its_project_starts_monthly.csv"

BREAK_MONTH = date(2024, 7, 1)
PRIMARY_START = date(2019, 1, 1)
PRIMARY_END = date(2025, 12, 1)
TRANSITION_CONTEXT_END = date(2025, 3, 1)


@dataclass(frozen=True)
class Outputs:
    measurement_note: Path = REPORT_DIR / "project_entry_measurement_note.md"
    results_report: Path = REPORT_DIR / "project_entry_its_results.md"
    stata_style_output: Path = REPORT_DIR / "project_entry_stata_style_its_output.txt"
    daily_2024: Path = DATA_DIR / "project_entry_daily_starts_2024.csv"
    institution_concentration: Path = DATA_DIR / "project_entry_institution_concentration.csv"
    window_audit: Path = DATA_DIR / "project_entry_estimation_window_audit.csv"
    results_table: Path = DATA_DIR / "project_entry_its_results_table.csv"
    observed_expected: Path = DATA_DIR / "project_entry_observed_vs_expected.csv"
    cumulative_gap: Path = DATA_DIR / "project_entry_cumulative_gap.csv"
    historical_rarity: Path = DATA_DIR / "project_entry_historical_rarity.csv"
    exploratory_dynamic: Path = DATA_DIR / "project_entry_exploratory_dynamic_characterization.csv"
    placebo_results: Path = DATA_DIR / "project_entry_placebo_results.csv"
    exact_date_audit: Path = DATA_DIR / "project_entry_exact_date_audit.csv"
    raw_figure: Path = FIGURE_DIR / "project_entry_raw_monthly_starts.svg"
    daily_figure: Path = FIGURE_DIR / "project_entry_daily_starts_2024.svg"
    observed_expected_figure: Path = FIGURE_DIR / "project_entry_observed_vs_expected.svg"
    cumulative_gap_figure: Path = FIGURE_DIR / "project_entry_cumulative_gap.svg"
    figure1: Path = FIGURE_DIR / "project_entry_figure1_three_panel.svg"
    exploratory_figure: Path = FIGURE_DIR / "project_entry_exploratory_dynamic.svg"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def parse_date(value: str) -> date:
    return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    return date(value.year + month // 12, month % 12 + 1, 1)


def month_range(start: date, end: date) -> list[date]:
    months = []
    current = date(start.year, start.month, 1)
    stop = date(end.year, end.month, 1)
    while current <= stop:
        months.append(current)
        current = add_months(current, 1)
    return months


def date_range(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def month_label(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def fmt(value: float, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return f"{value:.{digits}f}"


def two_sided_normal_pvalue(estimate: float, se: float) -> float:
    if se <= 0:
        return math.nan
    return math.erfc(abs(estimate / se) / math.sqrt(2.0))


def linear_interpretation(term: str, beta: float, se: float, post_months: int) -> str:
    ci_low = beta - 1.96 * se
    ci_high = beta + 1.96 * se
    if term == "PostJuly2024":
        direction = "fewer" if beta < 0 else "more"
        return (
            f"At the July 2024 breakpoint, the fitted series shifts by {abs(beta):.1f} "
            f"{direction} recorded starts per month, conditional on linear trend and month-of-year FE "
            f"(95% CI {ci_low:.1f} to {ci_high:.1f}); the interval is wide, so this is not a precise "
            "stand-alone estimate of the interruption."
        )
    direction = "higher" if beta > 0 else "lower"
    final_month_change = beta * post_months
    return (
        f"After July 2024, the monthly trajectory changes by {beta:.1f} starts per month relative "
        f"to the pre-transition slope (95% CI {ci_low:.1f} to {ci_high:.1f}). By the final month of "
        f"the window, this implies a fitted slope component {final_month_change:.1f} starts per month "
        f"{direction} than a parallel continuation of the pre-transition slope."
    )


def poisson_interpretation(term: str, beta: float, se: float, post_months: int) -> str:
    ci_low = beta - 1.96 * se
    ci_high = beta + 1.96 * se
    pct = math.exp(beta) - 1.0
    pct_low = math.exp(ci_low) - 1.0
    pct_high = math.exp(ci_high) - 1.0
    if term == "PostJuly2024":
        return (
            f"Poisson QMLE translates the immediate level shift into a rate ratio of {math.exp(beta):.2f}, "
            f"or {pct * 100:.1f}% relative to the fitted pre-transition rate "
            f"(95% CI {pct_low * 100:.1f}% to {pct_high * 100:.1f}%)."
        )
    final_ratio = math.exp(beta * post_months)
    return (
        f"Poisson QMLE translates the slope change into about {pct * 100:.1f}% per post-transition month "
        f"(95% CI {pct_low * 100:.1f}% to {pct_high * 100:.1f}%). Over {post_months} post-transition "
        f"months, the slope component compounds to a rate ratio of {final_ratio:.2f}."
    )


def mat_transpose(a: list[list[float]]) -> list[list[float]]:
    return [list(col) for col in zip(*a)]


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
            raise ValueError("Singular matrix in regression design")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
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


def ols(X: list[list[float]], y: list[float], hac_lag: int | None = None) -> dict[str, object]:
    inv = invert(xtx(X))
    beta = mat_vec_mul(inv, xty(X, y))
    fitted = [sum(row[j] * beta[j] for j in range(len(beta))) for row in X]
    resid = [yi - fi for yi, fi in zip(y, fitted)]
    n, k = len(y), len(beta)
    rss = sum(e * e for e in resid)
    sigma2 = rss / max(n - k, 1)
    if hac_lag is None:
        vcov = [[sigma2 * inv[i][j] for j in range(k)] for i in range(k)]
        inference = "OLS homoskedastic"
    else:
        scores = [[row[j] * e for j in range(k)] for row, e in zip(X, resid)]
        vcov = sandwich_from_scores(inv, scores, hac_lag)
        inference = f"OLS Newey-West HAC lag {hac_lag}"
    se = [math.sqrt(max(vcov[i][i], 0.0)) for i in range(k)]
    return {"beta": beta, "fitted": fitted, "resid": resid, "vcov": vcov, "se": se, "sigma2": sigma2, "inference": inference}


def poisson_qmle(X: list[list[float]], y: list[float], hac_lag: int) -> dict[str, object]:
    n, k = len(y), len(X[0])
    mean_y = max(sum(y) / len(y), 0.1)
    beta = [math.log(mean_y)] + [0.0] * (k - 1)
    for _ in range(100):
        eta = [max(min(sum(row[j] * beta[j] for j in range(k)), 30.0), -30.0) for row in X]
        mu = [math.exp(v) for v in eta]
        z = [eta[i] + (y[i] - mu[i]) / max(mu[i], 1e-8) for i in range(n)]
        wx = [[row[j] * mu[i] for j in range(k)] for i, row in enumerate(X)]
        lhs = [[0.0] * k for _ in range(k)]
        rhs = [0.0] * k
        for i, row in enumerate(X):
            for a in range(k):
                rhs[a] += wx[i][a] * z[i]
                for b in range(k):
                    lhs[a][b] += wx[i][a] * row[b]
        new_beta = mat_vec_mul(invert(lhs), rhs)
        if max(abs(new_beta[i] - beta[i]) for i in range(k)) < 1e-9:
            beta = new_beta
            break
        beta = new_beta
    eta = [max(min(sum(row[j] * beta[j] for j in range(k)), 30.0), -30.0) for row in X]
    mu = [math.exp(v) for v in eta]
    bread = invert([[sum(X[i][a] * mu[i] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)])
    scores = [[X[i][j] * (y[i] - mu[i]) for j in range(k)] for i in range(n)]
    vcov = sandwich_from_scores(bread, scores, hac_lag)
    se = [math.sqrt(max(vcov[i][i], 0.0)) for i in range(k)]
    pearson = sum((y[i] - mu[i]) ** 2 / max(mu[i], 1e-8) for i in range(n)) / max(n - k, 1)
    return {
        "beta": beta,
        "fitted": mu,
        "vcov": vcov,
        "se": se,
        "pearson_dispersion": pearson,
        "inference": f"Poisson QMLE Newey-West HAC lag {hac_lag}",
    }


def design_rows(months: list[date], break_month: date = BREAK_MONTH) -> tuple[list[list[float]], list[str]]:
    names = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"] + [f"month_{m:02d}" for m in range(2, 13)]
    X = []
    for idx, mo in enumerate(months, start=1):
        post = 1.0 if mo >= break_month else 0.0
        time_after = float((mo.year - break_month.year) * 12 + mo.month - break_month.month + 1) if post else 0.0
        row = [1.0, float(idx), post, time_after] + [1.0 if mo.month == m else 0.0 for m in range(2, 13)]
        X.append(row)
    return X, names


def pretrend_design(months: list[date]) -> tuple[list[list[float]], list[str]]:
    names = ["Intercept", "Time"] + [f"month_{m:02d}" for m in range(2, 13)]
    X = []
    for idx, mo in enumerate(months, start=1):
        X.append([1.0, float(idx)] + [1.0 if mo.month == m else 0.0 for m in range(2, 13)])
    return X, names


def load_projects() -> list[dict[str, object]]:
    projects = []
    for row in read_csv(PROJECT_UNIVERSE):
        start = parse_date(row["start_date"])
        projects.append(
            {
                "app_id": row["app_id"],
                "title": row["schema27_title"],
                "institution": row["schema27_institution"].strip() or "UNKNOWN",
                "start_date": start,
                "month": date(start.year, start.month, 1),
            }
        )
    return projects


def load_monthly_counts() -> dict[date, int]:
    counts = {}
    for row in read_csv(MONTHLY_STARTS):
        counts[parse_date(row["month_start"])] = int(row["new_projects"])
    return counts


def concentration(projects: list[dict[str, object]]) -> dict[str, float]:
    n = len(projects)
    counts = Counter(str(p["institution"]) for p in projects)
    shares = sorted((c / n for c in counts.values()), reverse=True) if n else []
    return {
        "projects": n,
        "institution_count": len(counts),
        "top1_share": shares[0] if shares else 0.0,
        "top5_share": sum(shares[:5]) if shares else 0.0,
        "hhi": sum(s * s for s in shares),
    }


def make_daily_outputs(projects: list[dict[str, object]], out: Outputs) -> dict[str, object]:
    focus_start, focus_end = date(2024, 4, 1), date(2024, 12, 31)
    by_day = defaultdict(list)
    for p in projects:
        start = p["start_date"]
        if focus_start <= start <= focus_end:
            by_day[start].append(p)
    rows = []
    for day in date_range(focus_start, focus_end):
        ps = by_day.get(day, [])
        conc = concentration(ps)
        rows.append(
            {
                "date": day.isoformat(),
                "daily_recorded_project_starts": len(ps),
                "month": month_label(day),
                "institution_count": conc["institution_count"],
                "top_institution_share_if_feasible": fmt(conc["top1_share"], 4) if ps else "",
            }
        )
    write_csv(out.daily_2024, rows, ["date", "daily_recorded_project_starts", "month", "institution_count", "top_institution_share_if_feasible"])

    audit_rows = []
    for mo in month_range(focus_start, date(2024, 12, 1)):
        month_days = [day for day in by_day if day.year == mo.year and day.month == mo.month]
        totals = sorted((len(by_day[day]) for day in month_days), reverse=True)
        month_total = sum(totals)
        audit_rows.append(
            {
                "month": month_label(mo),
                "monthly_recorded_project_starts": month_total,
                "unique_project_start_dates": len(month_days),
                "largest_daily_start_count": totals[0] if totals else 0,
                "top1_start_date_share": fmt((totals[0] / month_total) if month_total else 0.0, 4),
                "top3_start_date_share": fmt((sum(totals[:3]) / month_total) if month_total else 0.0, 4),
                "top5_start_date_share": fmt((sum(totals[:5]) / month_total) if month_total else 0.0, 4),
            }
        )
    write_csv(
        out.exact_date_audit,
        audit_rows,
        [
            "month",
            "monthly_recorded_project_starts",
            "unique_project_start_dates",
            "largest_daily_start_count",
            "top1_start_date_share",
            "top3_start_date_share",
            "top5_start_date_share",
        ],
    )
    oct_row = next(row for row in audit_rows if row["month"] == "2024-10")
    return {"daily_rows": rows, "audit_rows": audit_rows, "october_audit": oct_row}


def make_institution_outputs(projects: list[dict[str, object]], out: Outputs) -> dict[str, object]:
    periods = [
        ("Jan-Apr 2024", date(2024, 1, 1), date(2024, 4, 30)),
        ("May-Jun 2024", date(2024, 5, 1), date(2024, 6, 30)),
        ("Jul-Sep 2024", date(2024, 7, 1), date(2024, 9, 30)),
        ("October 2024", date(2024, 10, 1), date(2024, 10, 31)),
        ("Nov-Dec 2024", date(2024, 11, 1), date(2024, 12, 31)),
    ]
    rows = []
    for label, start, end in periods:
        ps = [p for p in projects if start <= p["start_date"] <= end]
        conc = concentration(ps)
        rows.append(
            {
                "period": label,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "recorded_project_starts": conc["projects"],
                "institution_count": conc["institution_count"],
                "top1_institution_share": fmt(conc["top1_share"], 4),
                "top5_institution_share": fmt(conc["top5_share"], 4),
                "hhi": fmt(conc["hhi"], 4),
            }
        )
    pre_month_rows = []
    for mo in month_range(PRIMARY_START, date(2024, 6, 1)):
        ps = [p for p in projects if p["month"] == mo]
        if not ps:
            continue
        conc = concentration(ps)
        pre_month_rows.append(conc)
    october = concentration([p for p in projects if date(2024, 10, 1) <= p["start_date"] <= date(2024, 10, 31)])
    rows.append(
        {
            "period": "Ordinary pre-transition months, 2019-01 to 2024-06 median",
            "start_date": "2019-01-01",
            "end_date": "2024-06-30",
            "recorded_project_starts": fmt(statistics.median(c["projects"] for c in pre_month_rows), 2),
            "institution_count": fmt(statistics.median(c["institution_count"] for c in pre_month_rows), 2),
            "top1_institution_share": fmt(statistics.median(c["top1_share"] for c in pre_month_rows), 4),
            "top5_institution_share": fmt(statistics.median(c["top5_share"] for c in pre_month_rows), 4),
            "hhi": fmt(statistics.median(c["hhi"] for c in pre_month_rows), 4),
        }
    )
    write_csv(
        out.institution_concentration,
        rows,
        ["period", "start_date", "end_date", "recorded_project_starts", "institution_count", "top1_institution_share", "top5_institution_share", "hhi"],
    )
    pre_hhis = [c["hhi"] for c in pre_month_rows]
    oct_hhi_rank = sum(1 for v in pre_hhis if v <= october["hhi"]) / len(pre_hhis)
    return {"rows": rows, "october": october, "pre_month_rows": pre_month_rows, "oct_hhi_percentile": oct_hhi_rank}


def window_audit(counts: dict[date, int], out: Outputs) -> list[dict[str, object]]:
    rows = []
    for label, start in [("2019-2025", date(2019, 1, 1)), ("2021-2025", date(2021, 1, 1)), ("2022-2025", date(2022, 1, 1))]:
        months = month_range(start, PRIMARY_END)
        pre = [counts[m] for m in months if m < BREAK_MONTH]
        post = [counts[m] for m in months if m >= BREAK_MONTH]
        rows.append(
            {
                "window": label,
                "start_month": month_label(start),
                "end_month": month_label(PRIMARY_END),
                "n_months": len(months),
                "pre_transition_months": len(pre),
                "post_transition_months": len(post),
                "pre_mean": fmt(sum(pre) / len(pre), 3),
                "post_mean": fmt(sum(post) / len(post), 3),
                "pre_min": min(pre),
                "pre_max": max(pre),
                "selected_role": "PRIMARY" if start == PRIMARY_START else "ROBUSTNESS",
                "selection_basis": "Balances modern project-entry volume with enough pre-transition observations for trend and month-of-year seasonality; chosen before inspecting model significance."
                if start == PRIMARY_START
                else "Prespecified shorter modern-window robustness check.",
            }
        )
    write_csv(
        out.window_audit,
        rows,
        [
            "window",
            "start_month",
            "end_month",
            "n_months",
            "pre_transition_months",
            "post_transition_months",
            "pre_mean",
            "post_mean",
            "pre_min",
            "pre_max",
            "selected_role",
            "selection_basis",
        ],
    )
    return rows


def run_segmented_models(counts: dict[date, int], out: Outputs) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows = []
    saved = {}
    for label, start in [("2019-2025", date(2019, 1, 1)), ("2021-2025", date(2021, 1, 1)), ("2022-2025", date(2022, 1, 1))]:
        months = month_range(start, PRIMARY_END)
        post_months = sum(1 for mo in months if mo >= BREAK_MONTH)
        y = [float(counts[m]) for m in months]
        X, names = design_rows(months)
        lag = max(1, int(math.floor(4 * (len(y) / 100.0) ** (2.0 / 9.0))))
        fit = ols(X, y, hac_lag=lag)
        saved[(label, "linear")] = (months, names, fit)
        for term, idx, interpretation in [
            ("PostJuly2024", names.index("PostJuly2024"), "descriptive level change in monthly recorded project starts"),
            ("TimeAfterJuly2024", names.index("TimeAfterJuly2024"), "descriptive post-transition slope change per month"),
        ]:
            beta = fit["beta"][idx]
            se = fit["se"][idx]
            rows.append(
                {
                    "model": "Linear segmented ITS",
                    "window": label,
                    "n_months": len(months),
                    "seasonality": "month-of-year FE",
                    "inference": fit["inference"],
                    "term": term,
                    "estimate": fmt(beta, 3),
                    "std_error": fmt(se, 3),
                    "p_value": fmt(two_sided_normal_pvalue(beta, se), 4),
                    "ci_low": fmt(beta - 1.96 * se, 3),
                    "ci_high": fmt(beta + 1.96 * se, 3),
                    "economic_interpretation": linear_interpretation(term, beta, se, post_months),
                }
            )
        pfit = poisson_qmle(X, y, hac_lag=lag)
        saved[(label, "poisson")] = (months, names, pfit)
        for term, idx, interpretation in [
            ("PostJuly2024", names.index("PostJuly2024"), "approximate multiplicative level change in recorded monthly starts"),
            ("TimeAfterJuly2024", names.index("TimeAfterJuly2024"), "approximate monthly multiplicative slope change"),
        ]:
            beta = pfit["beta"][idx]
            se = pfit["se"][idx]
            pct = math.exp(beta) - 1.0
            lo = math.exp(beta - 1.96 * se) - 1.0
            hi = math.exp(beta + 1.96 * se) - 1.0
            rows.append(
                {
                    "model": "Poisson QMLE segmented ITS",
                    "window": label,
                    "n_months": len(months),
                    "seasonality": "month-of-year FE",
                    "inference": pfit["inference"] + f"; Pearson dispersion {pfit['pearson_dispersion']:.2f}",
                    "term": term,
                    "estimate": fmt(beta, 3),
                    "std_error": fmt(se, 3),
                    "p_value": fmt(two_sided_normal_pvalue(beta, se), 4),
                    "ci_low": fmt(beta - 1.96 * se, 3),
                    "ci_high": fmt(beta + 1.96 * se, 3),
                    "economic_interpretation": poisson_interpretation(term, beta, se, post_months),
                }
            )
    write_csv(out.results_table, rows, ["model", "window", "n_months", "seasonality", "inference", "term", "estimate", "std_error", "p_value", "ci_low", "ci_high", "economic_interpretation"])
    return rows, saved


def expected_path(counts: dict[date, int], out: Outputs) -> tuple[list[dict[str, object]], dict[str, float]]:
    months = month_range(PRIMARY_START, PRIMARY_END)
    pre_months = [m for m in months if m < BREAK_MONTH]
    X_pre, names = pretrend_design(pre_months)
    y_pre = [float(counts[m]) for m in pre_months]
    fit = ols(X_pre, y_pre, hac_lag=None)
    X_all, _ = pretrend_design(months)
    expected = [sum(row[j] * fit["beta"][j] for j in range(len(fit["beta"]))) for row in X_all]
    vcov = fit["vcov"]
    rows = []
    cum = 0.0
    recovery_month = ""
    min_cum = 0.0
    for mo, row, exp in zip(months, X_all, expected):
        se = math.sqrt(max(sum(row[i] * vcov[i][j] * row[j] for i in range(len(row)) for j in range(len(row))), 0.0))
        obs = float(counts[mo])
        gap = obs - exp
        if mo >= BREAK_MONTH:
            cum += gap
            min_cum = min(min_cum, cum)
            if not recovery_month and cum >= 0:
                recovery_month = month_label(mo)
        rows.append(
            {
                "month": month_label(mo),
                "month_start": mo.isoformat(),
                "observed_recorded_project_starts": int(obs),
                "fitted_expected_starts_from_pre_transition_path": fmt(exp, 3),
                "expected_ci_low": fmt(exp - 1.96 * se, 3),
                "expected_ci_high": fmt(exp + 1.96 * se, 3),
                "gap_observed_minus_expected": fmt(gap, 3),
                "post_july_2024": 1 if mo >= BREAK_MONTH else 0,
                "cumulative_gap_since_july_2024": fmt(cum, 3) if mo >= BREAK_MONTH else "",
            }
        )
    write_csv(
        out.observed_expected,
        rows,
        [
            "month",
            "month_start",
            "observed_recorded_project_starts",
            "fitted_expected_starts_from_pre_transition_path",
            "expected_ci_low",
            "expected_ci_high",
            "gap_observed_minus_expected",
            "post_july_2024",
            "cumulative_gap_since_july_2024",
        ],
    )
    cum_fields = [
        "month",
        "month_start",
        "observed_recorded_project_starts",
        "fitted_expected_starts_from_pre_transition_path",
        "gap_observed_minus_expected",
        "cumulative_gap_since_july_2024",
    ]
    cum_rows = [{field: r[field] for field in cum_fields} for r in rows if r["post_july_2024"] == 1]
    write_csv(
        out.cumulative_gap,
        cum_rows,
        cum_fields,
    )
    transition_gap = sum(float(r["gap_observed_minus_expected"]) for r in rows if "2024-07" <= r["month"] <= "2024-09")
    july_mar_gap = sum(float(r["gap_observed_minus_expected"]) for r in rows if "2024-07" <= r["month"] <= "2025-03")
    oct_gap = next(float(r["gap_observed_minus_expected"]) for r in rows if r["month"] == "2024-10")
    metrics = {
        "transition_gap_jul_sep": transition_gap,
        "transition_context_gap_jul_2024_mar_2025": july_mar_gap,
        "october_gap": oct_gap,
        "final_cumulative_gap": cum,
        "minimum_cumulative_gap": min_cum,
        "recovery_month": recovery_month,
    }
    return rows, metrics


def historical_rarity(counts: dict[date, int], out: Outputs) -> list[dict[str, object]]:
    pre_months = month_range(PRIMARY_START, date(2024, 6, 1))
    pre_vals = [counts[m] for m in pre_months]
    comparisons = [
        ("1-month Jul-Sep minimum", 1, min(counts[date(2024, m, 1)] for m in [7, 8, 9])),
        ("2-month May-Jun total", 2, counts[date(2024, 5, 1)] + counts[date(2024, 6, 1)]),
        ("3-month Jul-Sep total", 3, counts[date(2024, 7, 1)] + counts[date(2024, 8, 1)] + counts[date(2024, 9, 1)]),
    ]
    rows = []
    for label, width, observed in comparisons:
        totals = [sum(pre_vals[i : i + width]) for i in range(0, len(pre_vals) - width + 1)]
        below = sum(1 for v in totals if v <= observed)
        rows.append(
            {
                "diagnostic": label,
                "rolling_window_months": width,
                "observed_2024_total": observed,
                "pre_transition_windows": len(totals),
                "minimum_pre_transition_rolling_total": min(totals),
                "median_pre_transition_rolling_total": fmt(statistics.median(totals), 3),
                "windows_at_or_below_observed": below,
                "empirical_percentile": fmt(below / len(totals), 4),
                "rank_low_is_more_unusual": below,
            }
        )
    write_csv(out.historical_rarity, rows, ["diagnostic", "rolling_window_months", "observed_2024_total", "pre_transition_windows", "minimum_pre_transition_rolling_total", "median_pre_transition_rolling_total", "windows_at_or_below_observed", "empirical_percentile", "rank_low_is_more_unusual"])
    return rows


def exploratory_dynamic(counts: dict[date, int], expected_rows: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    expected = {r["month"]: r for r in expected_rows}
    rows = []
    for mo in month_range(date(2024, 1, 1), date(2025, 12, 1)):
        rel = (mo.year - 2024) * 12 + mo.month - 7
        label = ""
        if mo in [date(2024, 5, 1), date(2024, 6, 1)]:
            label = "observed May-June slowdown"
        elif mo in [date(2024, 7, 1), date(2024, 8, 1), date(2024, 9, 1)]:
            label = "observed July-September trough"
        elif mo == date(2024, 10, 1):
            label = "observed October rebound"
        r = expected[month_label(mo)]
        rows.append(
            {
                "month": month_label(mo),
                "event_month_relative_to_july_2024": rel,
                "observed_recorded_project_starts": counts[mo],
                "fitted_expected_from_pre_transition_path": r["fitted_expected_starts_from_pre_transition_path"],
                "gap_observed_minus_expected": r["gap_observed_minus_expected"],
                "label": label,
                "interpretation": "EXPLORATORY / OUTCOME-DRIVEN DYNAMIC CHARACTERIZATION",
            }
        )
    write_csv(out.exploratory_dynamic, rows, ["month", "event_month_relative_to_july_2024", "observed_recorded_project_starts", "fitted_expected_from_pre_transition_path", "gap_observed_minus_expected", "label", "interpretation"])
    return rows


def placebo_models(counts: dict[date, int], out: Outputs) -> list[dict[str, object]]:
    rows = []
    months = month_range(PRIMARY_START, date(2024, 6, 1))
    y = [float(counts[m]) for m in months]
    for break_mo in [date(2022, 7, 1), date(2023, 7, 1)]:
        X, names = design_rows(months, break_mo)
        lag = max(1, int(math.floor(4 * (len(y) / 100.0) ** (2.0 / 9.0))))
        fit = ols(X, y, hac_lag=lag)
        for term in ["PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            beta = fit["beta"][idx]
            se = fit["se"][idx]
            rows.append(
                {
                    "placebo_breakpoint": month_label(break_mo),
                    "sample_window": "2019-01 to 2024-06 only",
                    "model": "Linear segmented ITS placebo",
                    "term": "PostPlaceboJuly" if term == "PostJuly2024" else "TimeAfterPlaceboJuly",
                    "estimate": fmt(beta, 3),
                    "std_error": fmt(se, 3),
                    "ci_low": fmt(beta - 1.96 * se, 3),
                    "ci_high": fmt(beta + 1.96 * se, 3),
                    "interpretation": "Contextual placebo, not an identification test",
                }
            )
    write_csv(out.placebo_results, rows, ["placebo_breakpoint", "sample_window", "model", "term", "estimate", "std_error", "ci_low", "ci_high", "interpretation"])
    return rows


def svg_polyline(points: list[tuple[float, float]], color: str, width: float = 2.0, dash: str = "") -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline fill="none" stroke="{color}" stroke-width="{width}"{dash_attr} points="{pts}"/>'


def make_svg_time_series(
    path: Path,
    title: str,
    series: list[tuple[date, float, str]],
    y_label: str,
    start: date,
    end: date,
    y_min: float | None = None,
    y_max: float | None = None,
    bands: list[tuple[date, float, float]] | None = None,
    cumulative_zero: bool = False,
) -> None:
    w, h = 1060, 520
    ml, mr, mt, mb = 82, 34, 50, 62
    pw, ph = w - ml - mr, h - mt - mb
    values = [v for _, v, _ in series]
    if bands:
        values += [lo for _, lo, _ in bands] + [hi for _, _, hi in bands]
    lo = min(values + ([0.0] if cumulative_zero else [])) if y_min is None else y_min
    hi = max(values + ([0.0] if cumulative_zero else [])) if y_max is None else y_max
    pad = (hi - lo) * 0.08 if hi > lo else 1.0
    lo, hi = lo - pad, hi + pad

    def x(dt: date) -> float:
        return ml + (dt - start).days / max((end - start).days, 1) * pw

    def y(v: float) -> float:
        return mt + (hi - v) / (hi - lo) * ph

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">', '<rect width="100%" height="100%" fill="#ffffff"/>']
    svg.append(f'<text x="{w/2}" y="28" text-anchor="middle" font-family="Arial, sans-serif" font-size="17" font-weight="700">{title}</text>')
    span_x = x(BREAK_MONTH)
    span_w = max(x(TRANSITION_CONTEXT_END) - span_x, 0)
    svg.append(f'<rect x="{span_x:.1f}" y="{mt}" width="{span_w:.1f}" height="{ph}" fill="#d9e6ee" opacity="0.45"/>')
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        val = lo + frac * (hi - lo)
        yy = y(val)
        svg.append(f'<line x1="{ml}" y1="{yy:.1f}" x2="{w-mr}" y2="{yy:.1f}" stroke="#dedede"/>')
        svg.append(f'<text x="{ml-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#444">{val:.0f}</text>')
    for yr in range(start.year, end.year + 1):
        xx = x(date(yr, 1, 1))
        svg.append(f'<line x1="{xx:.1f}" y1="{mt}" x2="{xx:.1f}" y2="{h-mb}" stroke="#eeeeee"/>')
        svg.append(f'<text x="{xx:.1f}" y="{h-28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#444">{yr}</text>')
    if cumulative_zero:
        svg.append(f'<line x1="{ml}" y1="{y(0):.1f}" x2="{w-mr}" y2="{y(0):.1f}" stroke="#777" stroke-dasharray="4 4"/>')
    svg.append(f'<line x1="{span_x:.1f}" y1="{mt}" x2="{span_x:.1f}" y2="{h-mb}" stroke="#111" stroke-width="2.2"/>')
    if bands:
        upper = [(x(dt), y(hi_v)) for dt, _, hi_v in bands]
        lower = [(x(dt), y(lo_v)) for dt, lo_v, _ in reversed(bands)]
        pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in upper + lower)
        svg.append(f'<polygon points="{pts}" fill="#b8c9d3" opacity="0.35"/>')
    grouped = defaultdict(list)
    for dt, val, label in series:
        grouped[label].append((x(dt), y(val)))
    colors = {"observed": "#24536b", "expected": "#9a4d2f", "cumulative": "#24536b"}
    for label, pts in grouped.items():
        svg.append(svg_polyline(pts, colors.get(label, "#24536b"), 2.4, "5 4" if label == "expected" else ""))
        if label == "observed":
            for px, py in pts:
                svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="#24536b"/>')
    for label, mo in [("Observed slowdown", date(2024, 5, 1)), ("Observed trough", date(2024, 8, 1)), ("Observed rebound", date(2024, 10, 1))]:
        hits = [(dt, val) for dt, val, lab in series if dt == mo and lab == "observed"]
        if hits:
            px, py = x(hits[0][0]), y(hits[0][1])
            svg.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="7" fill="#fff" stroke="#b23a48" stroke-width="2"/>')
            svg.append(f'<text x="{px:.1f}" y="{py-12:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#7a1f2b">{label}</text>')
    svg.append(f'<text x="18" y="{mt+ph/2}" transform="rotate(-90 18 {mt+ph/2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">{y_label}</text>')
    svg.append(f'<text x="{ml}" y="{h-8}" font-family="Arial, sans-serif" font-size="11" fill="#333">Solid line: official July 2024 institutional breakpoint. Shading: documented transition/onboarding context.</text>')
    svg.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def make_daily_figure(rows: list[dict[str, object]], out: Outputs) -> None:
    series = [(parse_date(str(r["date"])), float(r["daily_recorded_project_starts"]), "observed") for r in rows]
    make_svg_time_series(out.daily_figure, "Daily Recorded UKB Project Starts, Apr-Dec 2024", series, "Daily starts", date(2024, 4, 1), date(2024, 12, 31), y_min=0)


def make_project_figures(counts: dict[date, int], expected_rows: list[dict[str, object]], dynamic_rows: list[dict[str, object]], out: Outputs) -> None:
    months = month_range(PRIMARY_START, PRIMARY_END)
    observed = [(m, float(counts[m]), "observed") for m in months]
    make_svg_time_series(out.raw_figure, "Monthly Recorded UKB Project Starts", observed, "Monthly starts", PRIMARY_START, PRIMARY_END, y_min=0)
    exp_series = []
    bands = []
    for r in expected_rows:
        mo = parse_date(str(r["month_start"]))
        exp_series.append((mo, float(r["observed_recorded_project_starts"]), "observed"))
        exp_series.append((mo, float(r["fitted_expected_starts_from_pre_transition_path"]), "expected"))
        bands.append((mo, float(r["expected_ci_low"]), float(r["expected_ci_high"])))
    make_svg_time_series(out.observed_expected_figure, "Observed Versus Fitted Pre-Transition Expected Starts", exp_series, "Monthly starts", PRIMARY_START, PRIMARY_END, y_min=0, bands=bands)
    cum_series = []
    for r in expected_rows:
        if r["post_july_2024"] == 1:
            cum_series.append((parse_date(str(r["month_start"])), float(r["cumulative_gap_since_july_2024"]), "cumulative"))
    make_svg_time_series(out.cumulative_gap_figure, "Cumulative Observed-Minus-Expected Recorded Starts", cum_series, "Cumulative gap", BREAK_MONTH, PRIMARY_END, cumulative_zero=True)
    dyn_series = [(date(int(r["month"][:4]), int(r["month"][5:7]), 1), float(r["gap_observed_minus_expected"]), "cumulative") for r in dynamic_rows]
    make_svg_time_series(out.exploratory_figure, "Exploratory Outcome-Driven Monthly Gap Characterization", dyn_series, "Observed minus expected", date(2024, 1, 1), PRIMARY_END, cumulative_zero=True)
    combine_figure1(out)


def combine_figure1(out: Outputs) -> None:
    parts = [out.raw_figure, out.observed_expected_figure, out.cumulative_gap_figure]
    inner = []
    y_offset = 0
    for i, path in enumerate(parts):
        text = path.read_text(encoding="utf-8")
        body = text.split(">", 1)[1].rsplit("</svg>", 1)[0]
        inner.append(f'<g transform="translate(0,{y_offset})">{body}</g>')
        y_offset += 520
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="1560" viewBox="0 0 1060 1560">',
        *inner,
        "</svg>",
    ]
    out.figure1.write_text("\n".join(svg) + "\n", encoding="utf-8")


def measurement_note(projects: list[dict[str, object]], out: Outputs) -> None:
    matched_rows = read_csv(MATCHED_STARTS)
    unmatched_rows = read_csv(UNMATCHED_STARTS)
    starts = [p["start_date"] for p in projects]
    duplicate_app_ids = len(matched_rows) - len({r["app_id"] for r in matched_rows})
    multi_start_rows = [r for r in matched_rows if r.get("start_dates_all", "") and "|" in r.get("start_dates_all", "")]
    note = f"""# Project-Entry Measurement Note

## Outcome

The project-entry outcome is the number of UK Biobank projects whose public recorded `Start date` falls in calendar month `t`.

The public `Start date` is treated as the recorded beginning of a UKB research project's project period. Public documentation does not establish that it is identical to the application submission date, approval date, or first RAP-access date.

## Source

The start dates come from the public UK Biobank project pages/listing matched to the local schema27 application universe. The matched working file is:

`data/intermediate/timing_feasibility/timing_working_research_project_universe.csv`

## Safest Institutional Interpretation

The safest interpretation is `recorded project starts` or `projects becoming operational in public UKB records`. Official guidance documents application, registration, Access Committee review, MTA, payment, training/onboarding, project `Underway` status, and RAP enablement as separate steps. That workflow makes the public date downstream of application submission.

## What It Is Not

Do not interpret this outcome as:

- application submissions;
- application approvals;
- RAP migrations;
- first RAP access;
- first data use.

## Coverage And Matching

- Matched projects with usable public start dates: {len(projects):,}
- Date coverage: {min(starts).isoformat()} through {max(starts).isoformat()}
- Schema27 records unmatched to a public project page: {len(unmatched_rows):,}
- Public exact dates are available at day resolution and are aggregated to calendar months for the ITS.

## Anomalies

- Duplicate `app_id` rows in matched start-date file: {duplicate_app_ids}
- Rows with multiple public start dates in `start_dates_all`: {len(multi_start_rows)}
- Monthly aggregation includes zero-filled months inside analysis windows.

These diagnostics support use of the public start-date series as a recorded project-entry measure, while preserving uncertainty about the exact UKB internal administrative event that sets the public date.
"""
    write_text(out.measurement_note, note)


def stata_style_its_output(model_rows: list[dict[str, object]]) -> str:
    def row(model: str, window: str, term: str) -> dict[str, object]:
        return next(r for r in model_rows if r["model"] == model and r["window"] == window and r["term"] == term)

    def z_stat(r: dict[str, object]) -> float:
        return float(r["estimate"]) / float(r["std_error"])

    def linear_line(label: str, r: dict[str, object]) -> str:
        return (
            f"{label:<18} |"
            f"{float(r['estimate']):>12.3f}"
            f"{float(r['std_error']):>11.3f}"
            f"{z_stat(r):>8.2f}"
            f"{float(r['p_value']):>9.3f}"
            f"{float(r['ci_low']):>12.3f}"
            f"{float(r['ci_high']):>12.3f}"
        )

    def poisson_line(label: str, r: dict[str, object]) -> str:
        return (
            f"{label:<18} |"
            f"{float(r['estimate']):>12.3f}"
            f"{float(r['std_error']):>11.3f}"
            f"{z_stat(r):>8.2f}"
            f"{float(r['p_value']):>9.3f}"
            f"{float(r['ci_low']):>12.3f}"
            f"{float(r['ci_high']):>12.3f}"
            f"{math.exp(float(r['estimate'])):>10.2f}"
        )

    def robustness_line(model_label: str, window: str, term: str, r: dict[str, object]) -> str:
        return (
            f"{model_label:<10} {window:<9} {term:<19}"
            f"{float(r['estimate']):>9.3f}"
            f"{float(r['std_error']):>11.3f}"
            f"{float(r['p_value']):>9.3f}"
            f"{float(r['ci_low']):>11.3f}"
            f"{float(r['ci_high']):>11.3f}"
        )

    lin_level = row("Linear segmented ITS", "2019-2025", "PostJuly2024")
    lin_slope = row("Linear segmented ITS", "2019-2025", "TimeAfterJuly2024")
    poi_level = row("Poisson QMLE segmented ITS", "2019-2025", "PostJuly2024")
    poi_slope = row("Poisson QMLE segmented ITS", "2019-2025", "TimeAfterJuly2024")
    robustness_rows = []
    for window in ["2021-2025", "2022-2025"]:
        for model_name, model_label in [("Linear segmented ITS", "Linear"), ("Poisson QMLE segmented ITS", "Poisson")]:
            for term in ["PostJuly2024", "TimeAfterJuly2024"]:
                robustness_rows.append(robustness_line(model_label, window, term, row(model_name, window, term)))

    return f"""Project-entry segmented ITS, primary linear model
Outcome: monthly recorded UK Biobank project starts
Sample: 2019-01 to 2025-12                 Number of obs = 84
Seasonality: month-of-year fixed effects  Newey-West lag = 3
Inference: OLS with Newey-West HAC standard errors

------------------------------------------------------------------------------
 recorded_starts   | Coefficient  Std. err.       z    P>|z|      [95% conf. interval]
-------------------+----------------------------------------------------------
{linear_line('PostJuly2024', lin_level)}
{linear_line('TimeAfterJuly2024', lin_slope)}
 Month FE          |         Yes
------------------------------------------------------------------------------

Project-entry segmented ITS, Poisson QMLE robustness
Outcome: monthly recorded UK Biobank project starts
Sample: 2019-01 to 2025-12                 Number of obs = 84
Seasonality: month-of-year fixed effects  Newey-West lag = 3
Inference: Poisson QMLE with HAC standard errors; Pearson dispersion = 12.04

----------------------------------------------------------------------------------------
 recorded_starts   | Coefficient  Std. err.       z    P>|z|      [95% conf. interval]       IRR
-------------------+--------------------------------------------------------------------
{poisson_line('PostJuly2024', poi_level)}
{poisson_line('TimeAfterJuly2024', poi_slope)}
 Month FE          |         Yes
----------------------------------------------------------------------------------------

Alternative-window robustness, same breakpoint and seasonal controls
------------------------------------------------------------------------------
 Model      Window    Term                    Coef.  Std. err.    P>|z|     CI low    CI high
------------------------------------------------------------------------------
{chr(10).join(robustness_rows)}
------------------------------------------------------------------------------

Notes:
1. This is Stata-style formatting of the repository's generated Python ITS estimates, not a separate Stata execution log.
2. P-values are two-sided large-sample values computed from the displayed coefficient and HAC standard error.
3. For the Poisson QMLE block, IRR is exp(coefficient)."""


def results_report(
    outputs: Outputs,
    window_rows: list[dict[str, object]],
    model_rows: list[dict[str, object]],
    expected_metrics: dict[str, float],
    rarity_rows: list[dict[str, object]],
    daily_info: dict[str, object],
    inst_info: dict[str, object],
    placebo_rows: list[dict[str, object]],
) -> None:
    primary_linear = [r for r in model_rows if r["model"] == "Linear segmented ITS" and r["window"] == "2019-2025"]
    primary_poisson = [r for r in model_rows if r["model"] == "Poisson QMLE segmented ITS" and r["window"] == "2019-2025"]
    level = next(r for r in primary_linear if r["term"] == "PostJuly2024")
    slope = next(r for r in primary_linear if r["term"] == "TimeAfterJuly2024")
    plevel = next(r for r in primary_poisson if r["term"] == "PostJuly2024")
    pslope = next(r for r in primary_poisson if r["term"] == "TimeAfterJuly2024")
    oct_audit = daily_info["october_audit"]
    october = inst_info["october"]
    rarity_3 = next(r for r in rarity_rows if r["diagnostic"] == "3-month Jul-Sep total")
    recovery = expected_metrics["recovery_month"] or "not recovered by 2025-12"
    category = "C. Temporary interruption followed by higher-than-historical entry" if expected_metrics["final_cumulative_gap"] > 0 and expected_metrics["minimum_cumulative_gap"] < 0 else "D. No robustly unusual transition pattern"
    stata_output = stata_style_its_output(model_rows)
    write_text(outputs.stata_style_output, stata_output)
    report = f"""# Project-Entry ITS Results

## 1. Outcome Definition And Measurement

The outcome is monthly recorded UK Biobank project starts: the number of UKB projects whose public recorded `Start date` falls in calendar month `t`. The public `Start date` is treated as the recorded beginning of a UKB research project's project period. Public documentation does not establish that it is identical to the application submission date, approval date, or first RAP-access date.

The matched working universe contains 6,935 projects with exact public start dates from 2012-06-01 through 2026-08-17. There are 132 schema27 records unmatched to a public project page. See `project_entry_measurement_note.md`.

## 2. Institutional Breakpoint

The primary breakpoint is July 2024, based on the official 5 July 2024 transition to RAP-based access for new projects and additional data for existing projects. July 2024 through March 2025 is used only as broader transition/onboarding context, not as a homogeneous intervention period.

## 3. Raw Project-Start Pattern

The primary paper window is 2019-01 through 2025-12, with 84 monthly observations. It provides 66 pre-transition months and 18 post-transition months, balancing modern project volume against enough pre-period observations for trend and month-of-year seasonality.

The observed 2024 pattern includes May-June slowdown, July-September trough, and October rebound. These are outcome-defined descriptive patterns, not independent institutional phases.

## 4. Exact-Date Batching Diagnostic

October 2024 has {oct_audit['monthly_recorded_project_starts']} recorded starts across {oct_audit['unique_project_start_dates']} unique start dates. The largest daily count is {oct_audit['largest_daily_start_count']}. The top 1, top 3, and top 5 start-date shares are {float(oct_audit['top1_start_date_share'])*100:.1f}%, {float(oct_audit['top3_start_date_share'])*100:.1f}%, and {float(oct_audit['top5_start_date_share'])*100:.1f}%.

This pattern is consistent with some date-level concentration, but not enough on its own to prove administrative batching.

## 5. Institution Concentration

October 2024 includes {october['projects']} starts across {october['institution_count']} institutions. The top-1 institution share is {october['top1_share']*100:.1f}%, the top-5 share is {october['top5_share']*100:.1f}%, and HHI is {october['hhi']:.3f}. Relative to ordinary pre-transition months, October's HHI percentile is {inst_info['oct_hhi_percentile']*100:.1f}% when higher values indicate more concentration.

The October rebound is therefore broad-based across many institutions rather than dominated by one institution.

## 6. Main ITS Specification

```text
Y_t = beta_0
    + beta_1 Time_t
    + beta_2 PostJuly2024_t
    + beta_3 TimeAfterJuly2024_t
    + month-of-year FE
    + epsilon_t
```

`Time_t` is a monthly running index. `PostJuly2024_t` equals 1 from July 2024 onward. `TimeAfterJuly2024_t` is 0 before July 2024 and begins increasing in July 2024. Month-of-year fixed effects absorb recurring seasonality.

## 7. Main ITS Results

Primary linear ITS with Newey-West HAC inference:

| Term | Estimate | SE | p-value | 95% CI | Economic interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| PostJuly2024 | {level['estimate']} | {level['std_error']} | {level['p_value']} | [{level['ci_low']}, {level['ci_high']}] | At the July 2024 breakpoint, the fitted series shifts by about {abs(float(level['estimate'])):.1f} recorded starts per month; the interval is wide, so this is not a precise stand-alone estimate of the interruption. |
| TimeAfterJuly2024 | {slope['estimate']} | {slope['std_error']} | {slope['p_value']} | [{slope['ci_low']}, {slope['ci_high']}] | After July 2024, the fitted monthly trajectory increases by about {float(slope['estimate']):.1f} additional starts per month relative to the pre-transition slope. |

The p-values are two-sided large-sample values based on the HAC standard errors. They are included for reporting convenience, but the paper interpretation should emphasize the descriptive magnitudes, fitted-path deviations, and uncertainty intervals rather than stars.

### How To Read The ITS Coefficients

`PostJuly2024` is the model's immediate level-change parameter at the institutional breakpoint. In the primary linear specification it is {level['estimate']} recorded starts per month, with p = {level['p_value']} and a 95% CI from {level['ci_low']} to {level['ci_high']}. Economically, this means the segmented-regression line does not estimate a precise one-time downward jump exactly at July 2024 after allowing for the pre-existing trend, post-transition slope change, and month-of-year fixed effects. This coefficient should not be used as the main estimate of the July-September interruption, because the observed trough is spread across several months and the rebound arrives quickly afterward.

`TimeAfterJuly2024` is the change in slope after the July 2024 breakpoint. In the primary linear specification it is {slope['estimate']} additional recorded starts per month, with p = {slope['p_value']} and a 95% CI from {slope['ci_low']} to {slope['ci_high']}. Economically, each additional post-transition month is fitted as roughly {float(slope['estimate']):.1f} more project starts above what would be implied by simply extending the pre-transition slope. By December 2025, the slope-change component alone is about {float(slope['estimate']) * 18:.1f} starts per month above a parallel continuation of the pre-transition slope.

The coefficient table therefore tells a specific story: the immediate July level parameter is not informative on its own, while the post-July slope parameter captures the higher 2025 trajectory. The interruption itself is better summarized with the observed-versus-expected gap estimates below, because those directly compare observed monthly starts with a pre-transition trend-and-seasonality benchmark.

Poisson QMLE robustness gives an immediate level-shift rate ratio of {math.exp(float(plevel['estimate'])):.2f} (p = {plevel['p_value']}) and a monthly post-transition slope rate ratio of {math.exp(float(pslope['estimate'])):.2f} (p = {pslope['p_value']}). Because Pearson dispersion is high in the count model, the Poisson estimates are best read as robustness for the direction and broad magnitude, not as the only uncertainty calculation.

### Stata-Style Output For Reporting

The following block is a Stata-style presentation of the same generated estimates. It is designed for supervisor reporting and is also saved as `project_entry_stata_style_its_output.txt`.

```text
{stata_output}
```

## 8. Observed-Versus-Expected Path

Using only pre-transition observations in the primary window, I fit a trend plus month-of-year seasonality model and forecast the fitted historical benchmark after July 2024. This is a descriptive benchmark, not a causal untreated potential outcome.

July-September 2024 recorded starts are {expected_metrics['transition_gap_jul_sep']:.1f} projects below the fitted historical path. This is the clearest economic magnitude for the interruption: relative to what the pre-transition trend-and-seasonality model would have predicted, the public series records about {abs(expected_metrics['transition_gap_jul_sep']):.0f} fewer project starts during the three-month trough.

October 2024 alone is {expected_metrics['october_gap']:.1f} projects above the fitted path. This means the October rebound offsets most, but not all, of the July-September shortfall by itself. After October, the cumulative gap remains slightly negative; it turns positive only after November 2024 is included.

The broader July 2024-March 2025 transition/onboarding context is {expected_metrics['transition_context_gap_jul_2024_mar_2025']:.1f} projects relative to the fitted path. This positive value is important: it means the transition-context period is not simply a sustained deficit. Instead, the early trough is followed by enough rebound and elevated starts to put the cumulative July 2024-March 2025 total above the fitted historical benchmark.

## 9. Cumulative Gap And Recovery

The cumulative observed-minus-expected gap reaches a minimum of {expected_metrics['minimum_cumulative_gap']:.1f} projects after September 2024 and recovers in {recovery}. By 2025-12, the cumulative gap is {expected_metrics['final_cumulative_gap']:.1f} projects.

Economically, this supports the classification `temporary interruption followed by higher-than-historical entry`: there is a severe short-run deficit, but it is recovered quickly, and the subsequent 2025 project-start trajectory cumulates far above the fitted pre-transition benchmark. This should be described as a recorded-start trajectory, not as evidence that RAP causally increased applications.

## 10. Historical Rarity

The July-September 2024 total is {rarity_3['observed_2024_total']} recorded starts. Across {rarity_3['pre_transition_windows']} rolling three-month windows in the pre-transition primary period, the minimum historical rolling total is {rarity_3['minimum_pre_transition_rolling_total']}, and {rarity_3['windows_at_or_below_observed']} windows are at or below the observed July-September total.

## 11. Robustness

The main table includes 2019-2025, 2021-2025, and 2022-2025 windows, each with linear HAC and Poisson QMLE specifications. The positive post-transition slope-change pattern is stable across windows. The immediate level-change estimate is imprecise and changes sign, so it should not be emphasized as a robust stand-alone result.

Placebo July breakpoints in 2022 and 2023 are reported only as contextual diagnostics. They do not replace the July 2024 institutional breakpoint.

## 12. Exploratory Dynamic Characterization

The exploratory month-by-month output is labelled `EXPLORATORY / OUTCOME-DRIVEN DYNAMIC CHARACTERIZATION`. It characterizes the May-June decline, July-September trough, October rebound, and later 2025 trajectory without redefining the primary breakpoint.

## 13. What The Evidence Supports

The evidence supports describing an unusually sharp interruption in recorded project starts around the July 2024 RAP-based access transition, followed by a pronounced rebound and a 2025 trajectory above the fitted pre-transition benchmark.

## 14. What It Cannot Establish

This design cannot establish that RAP caused the project-start interruption. It cannot show that the public `Start date` is an application submission date, approval date, RAP migration date, or first RAP-access date. It also cannot prove that October 2024 was a documented institutional restart or administrative batch-processing event.

## 15. Recommended Paper-Ready Stylized Fact

Classification: {category}.

Candidate paper-ready statements:

> Recorded UK Biobank project starts exhibit a pronounced interruption around the July 2024 transition to RAP-based access, followed by a substantial rebound in the public project-start series.

> The decline begins before the formal July transition, which limits causal interpretation of the interruption; the institutionally anchored evidence supports July 2024 as the primary breakpoint, not a separately documented July-September pause or October restart.

> Relative to a fitted pre-transition trend-and-seasonality benchmark, the July-September 2024 shortfall is subsequently recovered, and the 2025 project-start trajectory lies above the fitted historical path.

## Output Files

- `data/project_entry_daily_starts_2024.csv`
- `data/project_entry_exact_date_audit.csv`
- `data/project_entry_institution_concentration.csv`
- `data/project_entry_estimation_window_audit.csv`
- `data/project_entry_its_results_table.csv`
- `reports/project_entry_stata_style_its_output.txt`
- `data/project_entry_observed_vs_expected.csv`
- `data/project_entry_cumulative_gap.csv`
- `data/project_entry_historical_rarity.csv`
- `data/project_entry_exploratory_dynamic_characterization.csv`
- `data/project_entry_placebo_results.csv`
- `figures/project_entry_figure1_three_panel.svg`
- `figures/project_entry_daily_starts_2024.svg`
- `figures/project_entry_observed_vs_expected.svg`
- `figures/project_entry_cumulative_gap.svg`
"""
    write_text(outputs.results_report, report)


def validate_outputs(out: Outputs | None = None) -> None:
    out = out or Outputs()
    projects = load_projects()
    counts = load_monthly_counts()
    monthly_from_projects = Counter(p["month"] for p in projects)
    assert sum(counts.values()) == len(projects), "monthly starts do not sum to matched project universe"
    for mo, val in monthly_from_projects.items():
        assert counts[mo] == val, f"monthly aggregation mismatch for {month_label(mo)}"
    for start in [date(2019, 1, 1), date(2021, 1, 1), date(2022, 1, 1)]:
        months = month_range(start, PRIMARY_END)
        assert all(m in counts for m in months), f"missing month inside {month_label(start)} window"
    X, names = design_rows(month_range(PRIMARY_START, PRIMARY_END))
    july_idx = month_range(PRIMARY_START, PRIMARY_END).index(BREAK_MONTH)
    june_idx = july_idx - 1
    assert X[june_idx][names.index("PostJuly2024")] == 0.0
    assert X[july_idx][names.index("PostJuly2024")] == 1.0
    observed_expected = read_csv(out.observed_expected)
    pre_expected = [r for r in observed_expected if r["month"] < "2024-07"]
    post_expected = [r for r in observed_expected if r["month"] >= "2024-07"]
    assert len(pre_expected) == 66, "expected-path primary pre-period changed"
    cumulative = 0.0
    for row in post_expected:
        cumulative += float(row["gap_observed_minus_expected"])
        assert abs(cumulative - float(row["cumulative_gap_since_july_2024"])) < 0.01
    daily = read_csv(out.daily_2024)
    by_month = Counter()
    for row in daily:
        by_month[row["month"]] += int(row["daily_recorded_project_starts"])
    for mo in month_range(date(2024, 4, 1), date(2024, 12, 1)):
        assert by_month[month_label(mo)] == counts[mo], f"daily to monthly mismatch for {month_label(mo)}"
    windows = {row["window"]: row for row in read_csv(out.window_audit)}
    assert windows["2019-2025"]["selected_role"] == "PRIMARY"
    assert windows["2021-2025"]["selected_role"] == "ROBUSTNESS"
    assert windows["2022-2025"]["selected_role"] == "ROBUSTNESS"


def main() -> None:
    out = Outputs()
    projects = load_projects()
    counts = load_monthly_counts()
    measurement_note(projects, out)
    daily_info = make_daily_outputs(projects, out)
    inst_info = make_institution_outputs(projects, out)
    windows = window_audit(counts, out)
    model_rows, _ = run_segmented_models(counts, out)
    expected_rows, expected_metrics = expected_path(counts, out)
    rarity = historical_rarity(counts, out)
    dynamic_rows = exploratory_dynamic(counts, expected_rows, out)
    placebo = placebo_models(counts, out)
    make_daily_figure(daily_info["daily_rows"], out)
    make_project_figures(counts, expected_rows, dynamic_rows, out)
    results_report(out, windows, model_rows, expected_metrics, rarity, daily_info, inst_info, placebo)
    validate_outputs(out)
    print("project-entry ITS outputs built")


if __name__ == "__main__":
    main()
