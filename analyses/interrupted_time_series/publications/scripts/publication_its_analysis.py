#!/usr/bin/env python3
"""Build publication-output outputs under the revised Y hierarchy."""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA_DIR = PACKAGE / "data"
FIGURE_DIR = PACKAGE / "figures"
REPORT_DIR = PACKAGE / "reports"
DESIGN_DIR = PACKAGE / "design"

PUBLICATIONS = ROOT / "data" / "raw" / "ukb_schema19_publications.tsv"
PUBLICATION_APPS = ROOT / "data" / "raw" / "ukb_schema24_publication_applications.tsv"
PROJECT_UNIVERSE = ROOT / "data" / "intermediate" / "timing_feasibility" / "timing_working_research_project_universe.csv"

BREAK_DATE = date(2024, 7, 5)
BREAK_MONTH = date(2024, 7, 1)
PRIMARY_START = date(2019, 1, 1)
PRIMARY_END = date(2025, 12, 1)
RIGHT_EDGE_END = date(2026, 6, 1)
CENSOR_DATE = date(2025, 12, 31)
PRIMARY_HAC_LAG = 3
FOLLOWUP_HORIZONS = [12, 18, 24]
FIXED_COHORT_CUTOFFS = [date(2021, 7, 1), date(2022, 1, 1), date(2022, 7, 1)]
AGE_BINS = [
    ("0_6_months", 0, 6),
    ("7_12_months", 7, 12),
    ("13_24_months", 13, 24),
    ("25_48_months", 25, 48),
    ("49_plus_months", 49, None),
]


@dataclass(frozen=True)
class Outputs:
    readme: Path = PACKAGE / "README.md"
    design: Path = DESIGN_DIR / "publication_its_design.md"
    reading_guide: Path = REPORT_DIR / "publication_reading_guide.md"
    measurement_note: Path = REPORT_DIR / "publication_measurement_note.md"
    results_report: Path = REPORT_DIR / "publication_its_results.md"
    stata_style_output: Path = REPORT_DIR / "publication_stata_style_results.txt"

    clean_events: Path = DATA_DIR / "publication_clean_event_links.csv"
    system_monthly: Path = DATA_DIR / "publication_system_total_monthly.csv"
    outcome_summary: Path = DATA_DIR / "publication_outcome_summary.csv"
    cohort_summary: Path = DATA_DIR / "publication_project_cohort_summary.csv"
    project_followup: Path = DATA_DIR / "publication_project_followup_outcomes.csv"
    first_pub_timing: Path = DATA_DIR / "publication_first_pub_timing.csv"
    project_month_panel: Path = DATA_DIR / "publication_project_month_panel.csv"
    by_project_age: Path = DATA_DIR / "publication_by_project_age.csv"
    age_band_profile: Path = DATA_DIR / "publication_age_band_profile.csv"
    pipeline_age_profile: Path = DATA_DIR / "publication_pipeline_age_profile.csv"
    pipeline_expected: Path = DATA_DIR / "publication_pipeline_expected.csv"
    pipeline_gap: Path = DATA_DIR / "publication_pipeline_gap.csv"
    outcome_audit: Path = DATA_DIR / "publication_outcome_universe_audit.csv"
    its_results: Path = DATA_DIR / "publication_its_results_table.csv"
    measurement_sensitivity_its: Path = DATA_DIR / "publication_measurement_sensitivity_its.csv"
    autocorrelation: Path = DATA_DIR / "publication_its_autocorrelation_diagnostics.csv"
    hac_sensitivity: Path = DATA_DIR / "publication_its_hac_lag_sensitivity.csv"
    ar1_results: Path = DATA_DIR / "publication_its_ar1_robustness.csv"
    poisson_results: Path = DATA_DIR / "publication_poisson_count_robustness.csv"
    placebo_results: Path = DATA_DIR / "publication_placebo_results.csv"
    fixed_cohort_monthly: Path = DATA_DIR / "publication_fixed_cohort_monthly.csv"
    fixed_cohort_results: Path = DATA_DIR / "publication_fixed_cohort_its_results.csv"

    incumbent_monthly: Path = DATA_DIR / "its_incumbent_publications_monthly.csv"
    incumbent_quarterly: Path = DATA_DIR / "its_incumbent_publications_quarterly.csv"
    lag: Path = DATA_DIR / "its_publication_lag.csv"
    measure_sensitivity: Path = DATA_DIR / "its_publication_measure_sensitivity.csv"
    recent_completeness: Path = DATA_DIR / "its_recent_publication_completeness.csv"
    total_monthly_figure: Path = FIGURE_DIR / "publication_total_monthly.svg"
    measure_comparison_figure: Path = FIGURE_DIR / "publication_measure_comparison.svg"
    project_age_figure: Path = FIGURE_DIR / "publication_project_age_profile.svg"
    pipeline_expected_figure: Path = FIGURE_DIR / "publication_observed_vs_pipeline_expected.svg"
    pipeline_gap_figure: Path = FIGURE_DIR / "publication_pipeline_gap.svg"
    cohort_followup_figure: Path = FIGURE_DIR / "publication_cohort_followup.svg"
    fixed_cohort_figure: Path = FIGURE_DIR / "publication_fixed_cohort_monthly.svg"
    incumbent_figure: Path = FIGURE_DIR / "publication_incumbent_pool_monthly.svg"
    lag_figure: Path = FIGURE_DIR / "publication_lag_distribution.svg"
    acf_figure: Path = FIGURE_DIR / "publication_its_residual_acf.svg"
    pacf_figure: Path = FIGURE_DIR / "publication_its_residual_pacf.svg"


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


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


def fmt(value: float | int | None, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return f"{float(value):.{digits}f}"


def month_label(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    return date(value.year + month // 12, month % 12 + 1, 1)


def add_months_exact(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    first_next = date(year + (month // 12), (month % 12) + 1, 1) if month < 12 else date(year + 1, 1, 1)
    last_day = (first_next - timedelta(days=1)).day
    return date(year, month, min(value.day, last_day))


def month_end(value: date) -> date:
    return add_months(value, 1) - timedelta(days=1)


def month_range(start: date, end: date) -> list[date]:
    months = []
    current = date(start.year, start.month, 1)
    stop = date(end.year, end.month, 1)
    while current <= stop:
        months.append(current)
        current = add_months(current, 1)
    return months


def quarter_label(value: date) -> str:
    return f"{value.year}Q{((value.month - 1) // 3) + 1}"


def age_months(start: date, later: date) -> int:
    return (later.year - start.year) * 12 + later.month - start.month


def age_bin(age: int) -> str:
    for label, lo, hi in AGE_BINS:
        if age >= lo and (hi is None or age <= hi):
            return label
    raise ValueError(f"unsupported age month {age}")


def project_cohort(start: date) -> str:
    return "post_rap_project_start" if start >= BREAK_DATE else "pre_rap_project_start"


def two_sided_normal_pvalue(estimate: float, se: float) -> float:
    if se <= 0:
        return math.nan
    return math.erfc(abs(estimate / se) / math.sqrt(2.0))


def mat_vec_mul(a: list[list[float]], v: list[float]) -> list[float]:
    return [sum(row[j] * v[j] for j in range(len(v))) for row in a]


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def invert(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    aug = [[float(a[i][j]) for j in range(n)] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("singular regression design")
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
    beta = [math.log(max(sum(y) / len(y), 0.1))] + [0.0] * (k - 1)
    for _ in range(100):
        eta = [max(min(sum(row[j] * beta[j] for j in range(k)), 30.0), -30.0) for row in X]
        mu = [math.exp(v) for v in eta]
        z = [eta[i] + (y[i] - mu[i]) / max(mu[i], 1e-8) for i in range(n)]
        lhs = [[0.0] * k for _ in range(k)]
        rhs = [0.0] * k
        for i, row in enumerate(X):
            for a in range(k):
                rhs[a] += row[a] * mu[i] * z[i]
                for b in range(k):
                    lhs[a][b] += row[a] * mu[i] * row[b]
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
    return {"beta": beta, "fitted": mu, "resid": [y[i] - mu[i] for i in range(n)], "vcov": vcov, "se": se, "pearson_dispersion": pearson}


def design_rows(months: list[date], break_month: date = BREAK_MONTH) -> tuple[list[list[float]], list[str]]:
    names = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"] + [f"month_{m:02d}" for m in range(2, 13)]
    X = []
    for idx, mo in enumerate(months, start=1):
        post = 1.0 if mo >= break_month else 0.0
        time_after = float((mo.year - break_month.year) * 12 + mo.month - break_month.month + 1) if post else 0.0
        X.append([1.0, float(idx), post, time_after] + [1.0 if mo.month == m else 0.0 for m in range(2, 13)])
    return X, names


def durbin_watson(resid: list[float]) -> float:
    return sum((resid[i] - resid[i - 1]) ** 2 for i in range(1, len(resid))) / max(sum(e * e for e in resid), 1e-12)


def acf_values(series: list[float], max_lag: int) -> list[float]:
    mean = sum(series) / len(series)
    denom = sum((v - mean) ** 2 for v in series)
    return [sum((series[t] - mean) * (series[t - lag] - mean) for t in range(lag, len(series))) / max(denom, 1e-12) for lag in range(1, max_lag + 1)]


def pacf_values(series: list[float], max_lag: int) -> list[float]:
    vals = []
    for lag in range(1, max_lag + 1):
        y = [series[t] for t in range(lag, len(series))]
        X = [[1.0] + [series[t - j] for j in range(1, lag + 1)] for t in range(lag, len(series))]
        fit = ols(X, y, hac_lag=None)
        vals.append(fit["beta"][lag])
    return vals


def chi2_sf_wilson_hilferty(x: float, df: int) -> float:
    if x <= 0:
        return 1.0
    z = ((x / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(2.0 / (9.0 * df))
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def ljung_box(series: list[float], lag: int) -> tuple[float, float]:
    acfs = acf_values(series, lag)
    n = len(series)
    q = n * (n + 2) * sum((acfs[k - 1] ** 2) / max(n - k, 1) for k in range(1, lag + 1))
    return q, chi2_sf_wilson_hilferty(q, lag)


def prais_winsten_ar1(X: list[list[float]], y: list[float]) -> dict[str, object]:
    base = ols(X, y, hac_lag=None)
    resid = base["resid"]
    rho = sum(resid[t] * resid[t - 1] for t in range(1, len(resid))) / max(sum(resid[t - 1] ** 2 for t in range(1, len(resid))), 1e-12)
    rho = max(min(rho, 0.95), -0.95)
    factor = math.sqrt(1.0 - rho * rho)
    y_t = [factor * y[0]]
    X_t = [[factor * v for v in X[0]]]
    for t in range(1, len(y)):
        y_t.append(y[t] - rho * y[t - 1])
        X_t.append([X[t][j] - rho * X[t - 1][j] for j in range(len(X[0]))])
    fit = ols(X_t, y_t, hac_lag=None)
    fit["rho"] = rho
    fit["original_resid"] = [y[i] - sum(X[i][j] * fit["beta"][j] for j in range(len(fit["beta"]))) for i in range(len(y))]
    return fit


def load_inputs() -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]], list[dict[str, str]]]:
    projects = {}
    for row in read_csv(PROJECT_UNIVERSE):
        app_id = row["app_id"].strip()
        start = parse_date(row["start_date"])
        projects[app_id] = {
            "app_id": app_id,
            "start_date": start,
            "start_month": date(start.year, start.month, 1),
            "institution": row["schema27_institution"].strip() or "UNKNOWN",
        }
    pubs = {}
    for row in read_csv(PUBLICATIONS, delimiter="\t"):
        pubs[row["pub_id"].strip()] = {"pub_id": row["pub_id"].strip(), "date_pub": parse_date(row["date_pub"])}
    return projects, pubs, read_csv(PUBLICATION_APPS, delimiter="\t")


def build_events(projects: dict[str, dict[str, object]], pubs: dict[str, dict[str, object]], links: list[dict[str, str]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    candidates = []
    unmatched_app_links = 0
    unmatched_publication_links = 0
    publication_before_project_start_exclusions = 0
    raw_pub_link_counts = Counter(r["pub_id"].strip() for r in links)
    for link in links:
        app_id = link["app_id"].strip()
        pub_id = link["pub_id"].strip()
        if app_id not in projects:
            unmatched_app_links += 1
            continue
        if pub_id not in pubs:
            unmatched_publication_links += 1
            continue
        project_start = projects[app_id]["start_date"]
        publication_date = pubs[pub_id]["date_pub"]
        if publication_date < project_start:
            publication_before_project_start_exclusions += 1
            continue
        candidates.append(
            {
                "app_id": app_id,
                "pub_id": pub_id,
                "project_start_date": project_start,
                "publication_date": publication_date,
                "publication_month": date(publication_date.year, publication_date.month, 1),
                "project_age_months": age_months(project_start, publication_date),
                "project_cohort": project_cohort(project_start),
            }
        )
    valid_links_per_pub = Counter(e["pub_id"] for e in candidates)
    events = []
    for e in candidates:
        weight = 1.0 / valid_links_per_pub[e["pub_id"]]
        events.append({**e, "fractional_weight": weight})
    audit = {
        "total_schema19_publications": len(pubs),
        "total_schema24_app_publication_links": len(links),
        "publication_ids_linked_to_multiple_applications_raw": sum(1 for c in raw_pub_link_counts.values() if c > 1),
        "publication_ids_linked_to_multiple_valid_applications": sum(1 for c in valid_links_per_pub.values() if c > 1),
        "unmatched_app_links": unmatched_app_links,
        "unmatched_publication_links": unmatched_publication_links,
        "publication_before_project_start_exclusions": publication_before_project_start_exclusions,
        "cleaned_publication_app_events": len(events),
        "cleaned_unique_publication_ids": len(valid_links_per_pub),
        "cleaned_apps_with_any_publication": len({e["app_id"] for e in events}),
        "latest_exact_schema19_publication_date": max(p["date_pub"] for p in pubs.values()).isoformat(),
        "latest_cleaned_publication_date": max(e["publication_date"] for e in events).isoformat(),
        "pre_rap_project_count": sum(1 for p in projects.values() if p["start_date"] < BREAK_DATE),
        "post_rap_project_count": sum(1 for p in projects.values() if p["start_date"] >= BREAK_DATE),
        "reliable_censor_date_used_for_project_followup": CENSOR_DATE.isoformat(),
    }
    return events, audit


def write_clean_events(events: list[dict[str, object]], out: Outputs) -> None:
    rows = []
    for e in sorted(events, key=lambda r: (r["publication_date"], r["pub_id"], r["app_id"])):
        rows.append(
            {
                "app_id": e["app_id"],
                "pub_id": e["pub_id"],
                "project_start_date": e["project_start_date"].isoformat(),
                "publication_date": e["publication_date"].isoformat(),
                "publication_month": e["publication_month"].isoformat(),
                "project_age_months": e["project_age_months"],
                "project_age_bin": age_bin(int(e["project_age_months"])),
                "project_cohort": e["project_cohort"],
                "fractional_weight": fmt(float(e["fractional_weight"]), 8),
            }
        )
    write_csv(out.clean_events, rows, list(rows[0].keys()))


def system_monthly(events: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    by_month = defaultdict(list)
    for e in events:
        by_month[e["publication_month"]].append(e)
    rows = []
    for mo in month_range(PRIMARY_START, RIGHT_EDGE_END):
        evs = by_month.get(mo, [])
        app_links = len(evs)
        unique = len({e["pub_id"] for e in evs})
        fractional = sum(float(e["fractional_weight"]) for e in evs)
        rows.append(
            {
                "month": month_label(mo),
                "month_start": mo.isoformat(),
                "publication_app_links": app_links,
                "unique_publication_ids": unique,
                "fractional_publication_count": fmt(fractional, 3),
                "apps_with_any_publication": len({e["app_id"] for e in evs}),
                "calendar_post_july_2024": 1 if mo >= BREAK_MONTH else 0,
                "jul_sep_2024_window": 1 if date(2024, 7, 1) <= mo <= date(2024, 9, 1) else 0,
                "right_edge_2026": 1 if mo.year == 2026 else 0,
            }
        )
    write_csv(out.system_monthly, rows, list(rows[0].keys()))
    return rows


def incumbent_pool_monthly(projects: dict[str, dict[str, object]], events: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    pre_projects = {app_id: p for app_id, p in projects.items() if p["start_date"] < BREAK_DATE}
    incumbent_events = [e for e in events if e["app_id"] in pre_projects]
    by_month = defaultdict(list)
    for e in incumbent_events:
        by_month[e["publication_month"]].append(e)
    rows = []
    for mo in month_range(PRIMARY_START, RIGHT_EDGE_END):
        denom = sum(1 for p in pre_projects.values() if p["start_date"] <= month_end(mo))
        evs = by_month.get(mo, [])
        app_links = len(evs)
        unique = len({e["pub_id"] for e in evs})
        fractional = sum(float(e["fractional_weight"]) for e in evs)
        apps_any = len({e["app_id"] for e in evs})
        rows.append(
            {
                "month": month_label(mo),
                "month_start": mo.isoformat(),
                "post_start_incumbent_projects": denom,
                "publication_app_links": app_links,
                "unique_publication_ids": unique,
                "fractional_publication_count": fmt(fractional, 3),
                "apps_with_any_publication": apps_any,
                "app_links_per_100_post_start_incumbents": fmt(100.0 * app_links / denom if denom else 0.0, 2),
                "unique_publications_per_100_post_start_incumbents": fmt(100.0 * unique / denom if denom else 0.0, 2),
                "fractional_publications_per_100_post_start_incumbents": fmt(100.0 * fractional / denom if denom else 0.0, 2),
                "any_publication_rate_percent": fmt(100.0 * apps_any / denom if denom else 0.0, 2),
                "calendar_post_july_2024": 1 if mo >= BREAK_MONTH else 0,
                "jul_sep_2024_window": 1 if date(2024, 7, 1) <= mo <= date(2024, 9, 1) else 0,
                "right_edge_2026": 1 if mo.year == 2026 else 0,
                "interpretation_role": "supplementary incumbent-pool diagnostic, not primary system-level Y",
            }
        )
    write_csv(out.incumbent_monthly, rows, list(rows[0].keys()))

    grouped = defaultdict(list)
    for r in rows:
        grouped[quarter_label(parse_date(str(r["month_start"])))].append(r)
    quarterly = []
    for q in sorted(grouped):
        rs = grouped[q]
        start = parse_date(str(rs[0]["month_start"]))
        denom = int(rs[-1]["post_start_incumbent_projects"])
        links = sum(int(r["publication_app_links"]) for r in rs)
        unique = sum(int(r["unique_publication_ids"]) for r in rs)
        frac = sum(float(r["fractional_publication_count"]) for r in rs)
        apps_any = sum(int(r["apps_with_any_publication"]) for r in rs)
        quarterly.append(
            {
                "quarter": q,
                "quarter_start": start.isoformat(),
                "quarter_end": month_end(parse_date(str(rs[-1]["month_start"]))).isoformat(),
                "post_start_incumbent_projects": denom,
                "publication_app_links": links,
                "unique_publication_ids": unique,
                "fractional_publication_count": fmt(frac, 3),
                "apps_with_any_publication": apps_any,
                "app_links_per_100_post_start_incumbents": fmt(100.0 * links / denom if denom else 0.0, 2),
                "unique_publications_per_100_post_start_incumbents": fmt(100.0 * unique / denom if denom else 0.0, 2),
                "fractional_publications_per_100_post_start_incumbents": fmt(100.0 * frac / denom if denom else 0.0, 2),
                "any_publication_rate_percent": fmt(100.0 * apps_any / denom if denom else 0.0, 2),
                "calendar_post_july_2024": 1 if start >= BREAK_MONTH else 0,
                "interpretation_role": "supplementary incumbent-pool diagnostic, not primary system-level Y",
            }
        )
    write_csv(out.incumbent_quarterly, quarterly, list(quarterly[0].keys()))
    return rows, quarterly


def write_lag(events: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    lags = [int(e["project_age_months"]) for e in events]
    sorted_lags = sorted(lags)
    median = sorted_lags[len(sorted_lags) // 2]
    rows = []
    for label, lo, hi in AGE_BINS:
        count = sum(1 for lag in lags if lag >= lo and (hi is None or lag <= hi))
        rows.append({"lag_bin": label, "min_lag_months": lo, "max_lag_months": "" if hi is None else hi, "publication_app_links": count, "share_percent": fmt(100.0 * count / len(lags), 2), "median_lag_months_all_events": fmt(median, 3)})
    write_csv(out.lag, rows, list(rows[0].keys()))
    return rows


def write_measurement_sensitivity(system_rows: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    rows = []
    for r in system_rows:
        links = int(r["publication_app_links"])
        unique = int(r["unique_publication_ids"])
        frac = float(r["fractional_publication_count"])
        rows.append(
            {
                "period": r["month"],
                "period_start": r["month_start"],
                "publication_app_links": links,
                "unique_publication_ids": unique,
                "fractional_publication_count": fmt(frac, 3),
                "app_links_minus_unique_ids": links - unique,
                "app_links_minus_fractional_count": fmt(links - frac, 3),
                "unique_id_reduction_percent_vs_app_links": fmt(100.0 * (links - unique) / links if links else 0.0, 2),
                "fractional_reduction_percent_vs_app_links": fmt(100.0 * (links - frac) / links if links else 0.0, 2),
                "note": "System-level measurement sensitivity; differences reflect publications linked to multiple UKB applications.",
            }
        )
    write_csv(out.measure_sensitivity, rows, list(rows[0].keys()))
    return rows


def primary_rows(rows: list[dict[str, object]], outcome: str) -> tuple[list[date], list[float]]:
    selected = [r for r in rows if PRIMARY_START <= parse_date(str(r["month_start"])) <= PRIMARY_END]
    return [parse_date(str(r["month_start"])) for r in selected], [float(r[outcome]) for r in selected]


def model_output_row(model: str, outcome: str, n: int, pre: int, post: int, term: str, estimate: float, se: float, notes: str) -> dict[str, object]:
    return {
        "model": model,
        "outcome": outcome,
        "window": "2019-01_to_2025-12",
        "n_months": n,
        "pre_months": pre,
        "post_months": post,
        "term": term,
        "estimate": fmt(estimate, 4),
        "std_error": fmt(se, 4),
        "p_value": fmt(two_sided_normal_pvalue(estimate, se), 4),
        "ci_low": fmt(estimate - 1.96 * se, 4),
        "ci_high": fmt(estimate + 1.96 * se, 4),
        "notes": notes,
    }


def run_primary_its(system_rows: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], dict[str, object]]:
    months, y = primary_rows(system_rows, "fractional_publication_count")
    X, names = design_rows(months)
    fit = ols(X, y, hac_lag=PRIMARY_HAC_LAG)
    pre = sum(1 for m in months if m < BREAK_MONTH)
    post = len(months) - pre
    rows = []
    for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
        idx = names.index(term)
        notes = {
            "Time": "pre-transition monthly trend in total fractional publication output",
            "PostJuly2024": "descriptive immediate calendar-time level change at July 2024; not an immediate RAP productivity effect",
            "TimeAfterJuly2024": "descriptive post-July 2024 monthly slope change in total output",
        }[term]
        rows.append(model_output_row("Primary total-output ITS, linear HAC(3)", "fractional_publication_count", len(months), pre, post, term, fit["beta"][idx], fit["se"][idx], notes))
    write_csv(out.its_results, rows, list(rows[0].keys()))
    return rows, {"months": months, "y": y, "X": X, "names": names, "fit": fit}


def run_measurement_sensitivity_its(system_rows: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    rows = []
    for outcome in ["publication_app_links", "unique_publication_ids", "fractional_publication_count"]:
        months, y = primary_rows(system_rows, outcome)
        X, names = design_rows(months)
        fit = ols(X, y, hac_lag=PRIMARY_HAC_LAG)
        for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            rows.append(model_output_row("Aggregate-output measurement sensitivity HAC(3)", outcome, len(months), 66, 18, term, fit["beta"][idx], fit["se"][idx], "same calendar-time ITS, alternative publication numerator"))
    write_csv(out.measurement_sensitivity_its, rows, list(rows[0].keys()))
    return rows


def hac_lag_sensitivity(primary: dict[str, object], out: Outputs) -> list[dict[str, object]]:
    months = primary["months"]
    y = primary["y"]
    X = primary["X"]
    names = primary["names"]
    rows = []
    for lag in [1, 3, 6, 12]:
        fit = ols(X, y, hac_lag=lag)
        for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            rows.append(model_output_row(f"Primary total-output ITS, linear HAC({lag})", "fractional_publication_count", len(months), 66, 18, term, fit["beta"][idx], fit["se"][idx], "HAC lag sensitivity; OLS point estimates should be invariant"))
    write_csv(out.hac_sensitivity, rows, list(rows[0].keys()))
    return rows


def autocorrelation_diagnostics(primary: dict[str, object], out: Outputs) -> list[dict[str, object]]:
    resid = primary["fit"]["resid"]
    acfs = acf_values(resid, 12)
    pacfs = pacf_values(resid, 12)
    dw = durbin_watson(resid)
    rows = []
    for lag in range(1, 13):
        q, p = ljung_box(resid, lag)
        rows.append({"diagnostic": "primary_total_output_residual_acf_pacf", "lag": lag, "acf": fmt(acfs[lag - 1], 4), "pacf": fmt(pacfs[lag - 1], 4), "durbin_watson_primary_model": fmt(dw, 4), "ljung_box_q": fmt(q, 4), "ljung_box_p_value": fmt(p, 4), "interpretation": "diagnostic after trend, July terms, and month-of-year fixed effects; not a pass/fail test"})
    write_csv(out.autocorrelation, rows, list(rows[0].keys()))
    return rows


def ar1_robustness(primary: dict[str, object], out: Outputs) -> list[dict[str, object]]:
    X = primary["X"]
    y = primary["y"]
    names = primary["names"]
    fit = prais_winsten_ar1(X, y)
    rows = []
    for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
        idx = names.index(term)
        rows.append(model_output_row("Primary total-output ITS, Prais-Winsten AR(1)", "fractional_publication_count", len(y), 66, 18, term, fit["beta"][idx], fit["se"][idx], f"estimated rho = {fit['rho']:.3f}"))
    write_csv(out.ar1_results, rows, list(rows[0].keys()))
    return rows


def poisson_robustness(system_rows: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    months, y = primary_rows(system_rows, "unique_publication_ids")
    X, names = design_rows(months)
    fit = poisson_qmle(X, y, hac_lag=PRIMARY_HAC_LAG)
    rows = []
    for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
        idx = names.index(term)
        rows.append(model_output_row("Poisson QMLE count robustness HAC(3)", "unique_publication_ids", len(months), 66, 18, term, fit["beta"][idx], fit["se"][idx], f"Pearson dispersion = {fit['pearson_dispersion']:.2f}; IRR = {math.exp(fit['beta'][idx]):.3f}"))
    write_csv(out.poisson_results, rows, list(rows[0].keys()))
    return rows


def placebo_models(system_rows: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    pre_rows = [r for r in system_rows if PRIMARY_START <= parse_date(str(r["month_start"])) < BREAK_MONTH]
    months = [parse_date(str(r["month_start"])) for r in pre_rows]
    y = [float(r["fractional_publication_count"]) for r in pre_rows]
    rows = []
    for placebo in [date(2021, 7, 1), date(2022, 7, 1), date(2023, 7, 1)]:
        X, names = design_rows(months, break_month=placebo)
        fit = ols(X, y, hac_lag=PRIMARY_HAC_LAG)
        for term in ["PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            rows.append(model_output_row(f"Pre-transition placebo July {placebo.year}", "fractional_publication_count", len(months), len([m for m in months if m < placebo]), len([m for m in months if m >= placebo]), term, fit["beta"][idx], fit["se"][idx], "contextual diagnostic using only pre-July-2024 calendar months"))
    write_csv(out.placebo_results, rows, list(rows[0].keys()))
    return rows


def project_age_outputs(projects: dict[str, dict[str, object]], events: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    reliable_events = [e for e in events if e["publication_date"] <= CENSOR_DATE]
    max_age = max(age_months(p["start_date"], CENSOR_DATE) for p in projects.values() if p["start_date"] <= CENSOR_DATE)
    event_by_age = defaultdict(list)
    for e in reliable_events:
        event_by_age[int(e["project_age_months"])].append(e)
    rows = []
    cumulative = 0.0
    for age in range(0, max_age + 1):
        at_risk = [p for p in projects.values() if add_months_exact(p["start_date"], age) <= CENSOR_DATE]
        evs = event_by_age.get(age, [])
        frac = sum(float(e["fractional_weight"]) for e in evs)
        cumulative += frac
        denom = len(at_risk)
        rows.append({"project_age_months": age, "project_age_bin": age_bin(age), "projects_with_complete_followup_to_age": denom, "publication_app_links_at_age": len(evs), "unique_publication_ids_at_age": len({e["pub_id"] for e in evs}), "fractional_publication_count_at_age": fmt(frac, 3), "publications_per_100_projects_at_risk": fmt(100.0 * frac / denom if denom else 0.0, 4), "cumulative_fractional_publications": fmt(cumulative, 3)})
    write_csv(out.by_project_age, rows, list(rows[0].keys()))

    band_rows = []
    for label, lo, hi in AGE_BINS:
        ages = [r for r in rows if int(r["project_age_months"]) >= lo and (hi is None or int(r["project_age_months"]) <= hi)]
        project_months = sum(int(r["projects_with_complete_followup_to_age"]) for r in ages)
        frac = sum(float(r["fractional_publication_count_at_age"]) for r in ages)
        band_rows.append({"project_age_bin": label, "min_age_months": lo, "max_age_months": "" if hi is None else hi, "project_months_with_complete_followup": project_months, "publication_app_links": sum(int(r["publication_app_links_at_age"]) for r in ages), "unique_publication_ids": sum(int(r["unique_publication_ids_at_age"]) for r in ages), "fractional_publication_count": fmt(frac, 3), "fractional_publications_per_100_project_months": fmt(100.0 * frac / project_months if project_months else 0.0, 4)})
    write_csv(out.age_band_profile, band_rows, list(band_rows[0].keys()))
    return rows, band_rows


def project_month_panel(projects: dict[str, dict[str, object]], events: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    event_map = defaultdict(float)
    event_any = defaultdict(int)
    for e in events:
        mo = e["publication_month"]
        if PRIMARY_START <= mo <= PRIMARY_END and e["publication_date"] <= CENSOR_DATE:
            key = (e["app_id"], mo)
            event_map[key] += float(e["fractional_weight"])
            event_any[key] = 1
    rows = []
    for app_id, p in sorted(projects.items(), key=lambda kv: int(kv[0])):
        for mo in month_range(max(PRIMARY_START, p["start_month"]), PRIMARY_END):
            if p["start_date"] > month_end(mo):
                continue
            age = age_months(p["start_date"], mo)
            rows.append({"app_id": app_id, "calendar_month": month_label(mo), "month_start": mo.isoformat(), "project_start_date": p["start_date"].isoformat(), "project_age_months": age, "project_age_bin": age_bin(age), "calendar_post_july_2024": 1 if mo >= BREAK_MONTH else 0, "project_cohort_post_rap": 1 if p["start_date"] >= BREAK_DATE else 0, "project_cohort": project_cohort(p["start_date"]), "institution": p["institution"], "fractional_publication_count": fmt(event_map[(app_id, mo)], 6), "any_publication": event_any[(app_id, mo)]})
    write_csv(out.project_month_panel, rows, list(rows[0].keys()))
    return rows


def fixed_followup_outputs(projects: dict[str, dict[str, object]], events: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    by_project = defaultdict(list)
    for e in events:
        if e["publication_date"] <= CENSOR_DATE:
            by_project[e["app_id"]].append(e)
    project_rows = []
    for app_id, p in sorted(projects.items(), key=lambda kv: int(kv[0])):
        row = {"app_id": app_id, "project_start_date": p["start_date"].isoformat(), "project_cohort": project_cohort(p["start_date"]), "project_cohort_post_rap": 1 if p["start_date"] >= BREAK_DATE else 0}
        for h in FOLLOWUP_HORIZONS:
            eligible = add_months_exact(p["start_date"], h) <= CENSOR_DATE
            evs = [e for e in by_project.get(app_id, []) if int(e["project_age_months"]) <= h]
            row[f"followup_eligible_{h}m"] = 1 if eligible else 0
            row[f"pub{h}_fractional"] = fmt(sum(float(e["fractional_weight"]) for e in evs), 6) if eligible else ""
            row[f"anypub{h}"] = 1 if eligible and evs else (0 if eligible else "")
        project_rows.append(row)
    write_csv(out.project_followup, project_rows, list(project_rows[0].keys()))

    summary = []
    for cohort in ["pre_rap_project_start", "post_rap_project_start"]:
        cohort_rows = [r for r in project_rows if r["project_cohort"] == cohort]
        for h in FOLLOWUP_HORIZONS:
            eligible = [r for r in cohort_rows if r[f"followup_eligible_{h}m"] == 1]
            mean_pub = sum(float(r[f"pub{h}_fractional"]) for r in eligible) / len(eligible) if eligible else math.nan
            any_rate = 100.0 * sum(int(r[f"anypub{h}"]) for r in eligible) / len(eligible) if eligible else math.nan
            summary.append({"project_cohort": cohort, "followup_horizon_months": h, "eligible_projects": len(eligible), "total_projects_in_cohort": len(cohort_rows), "mean_fractional_publications": fmt(mean_pub, 6), "any_publication_rate_percent": fmt(any_rate, 3), "followup_limitation": "feasible" if eligible else "not feasible for this cohort under 2025-12 reliable censor date"})
    write_csv(out.cohort_summary, summary, list(summary[0].keys()))

    first_age = {}
    for app_id, evs in by_project.items():
        first_age[app_id] = min(int(e["project_age_months"]) for e in evs)
    timing = []
    for cohort in ["pre_rap_project_start", "post_rap_project_start"]:
        cohort_projects = {app_id: p for app_id, p in projects.items() if project_cohort(p["start_date"]) == cohort}
        for age in range(0, 61):
            eligible = [app_id for app_id, p in cohort_projects.items() if add_months_exact(p["start_date"], age) <= CENSOR_DATE]
            had = [app_id for app_id in eligible if app_id in first_age and first_age[app_id] <= age]
            timing.append({"project_cohort": cohort, "project_age_months": age, "projects_with_complete_followup_to_age": len(eligible), "projects_with_first_publication_by_age": len(had), "cumulative_first_publication_probability_percent": fmt(100.0 * len(had) / len(eligible) if eligible else math.nan, 3), "censor_date": CENSOR_DATE.isoformat()})
    write_csv(out.first_pub_timing, timing, list(timing[0].keys()))
    return project_rows, summary, timing


def fixed_cohort_outputs(projects: dict[str, dict[str, object]], events: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows = []
    results = []
    for cutoff in FIXED_COHORT_CUTOFFS:
        cohort = {app_id for app_id, p in projects.items() if p["start_date"] < cutoff}
        by_month = defaultdict(list)
        for e in events:
            if e["app_id"] in cohort and PRIMARY_START <= e["publication_month"] <= PRIMARY_END and e["publication_date"] <= CENSOR_DATE:
                by_month[e["publication_month"]].append(e)
        start_month = date(cutoff.year, cutoff.month, 1)
        months = month_range(start_month, PRIMARY_END)
        y = []
        for mo in months:
            evs = by_month.get(mo, [])
            frac = sum(float(e["fractional_weight"]) for e in evs)
            yval = 100.0 * frac / len(cohort)
            y.append(yval)
            rows.append({"cohort_cutoff": cutoff.isoformat(), "calendar_month": month_label(mo), "month_start": mo.isoformat(), "fixed_cohort_projects": len(cohort), "fractional_publication_count": fmt(frac, 3), "fractional_publications_per_100_fixed_cohort": fmt(yval, 4), "calendar_post_july_2024": 1 if mo >= BREAK_MONTH else 0})
        X, names = design_rows(months)
        fit = ols(X, y, hac_lag=PRIMARY_HAC_LAG)
        for term in ["PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            results.append(model_output_row("Fixed-cohort publication intensity HAC(3)", f"fractional_publications_per_100_fixed_cohort_cutoff_{cutoff.isoformat()}", len(months), sum(m < BREAK_MONTH for m in months), sum(m >= BREAK_MONTH for m in months), term, fit["beta"][idx], fit["se"][idx], "denominator and membership fixed by prespecified cutoff"))
    write_csv(out.fixed_cohort_monthly, rows, list(rows[0].keys()))
    write_csv(out.fixed_cohort_results, results, list(results[0].keys()))
    return rows, results


def pipeline_expected(projects: dict[str, dict[str, object]], system_rows: list[dict[str, object]], panel_rows: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, float]]:
    pre_panel = [r for r in panel_rows if r["month_start"] < BREAK_MONTH.isoformat()]
    by_bin = defaultdict(lambda: {"risk": 0, "pubs": 0.0})
    for r in pre_panel:
        b = r["project_age_bin"]
        by_bin[b]["risk"] += 1
        by_bin[b]["pubs"] += float(r["fractional_publication_count"])
    profile = []
    rates = {}
    for label, lo, hi in AGE_BINS:
        risk = by_bin[label]["risk"]
        pubs = by_bin[label]["pubs"]
        rate = pubs / risk if risk else 0.0
        rates[label] = rate
        profile.append({"project_age_bin": label, "min_age_months": lo, "max_age_months": "" if hi is None else hi, "pre_transition_project_months": risk, "pre_transition_fractional_publications": fmt(pubs, 3), "monthly_fractional_publications_per_project": fmt(rate, 8), "estimated_using_calendar_months_before": BREAK_MONTH.isoformat()})
    write_csv(out.pipeline_age_profile, profile, list(profile[0].keys()))

    actual = {r["month_start"]: float(r["fractional_publication_count"]) for r in system_rows}
    rows = []
    cumulative = 0.0
    for mo in month_range(PRIMARY_START, PRIMARY_END):
        expected = 0.0
        for p in projects.values():
            if p["start_date"] <= month_end(mo):
                expected += rates[age_bin(age_months(p["start_date"], mo))]
        obs = actual[mo.isoformat()]
        gap = obs - expected
        if mo >= BREAK_MONTH:
            cumulative += gap
        rows.append({"month": month_label(mo), "month_start": mo.isoformat(), "actual_fractional_publication_count": fmt(obs, 3), "pipeline_expected_fractional_publication_count": fmt(expected, 3), "pipeline_gap_actual_minus_expected": fmt(gap, 3), "pipeline_ratio_actual_over_expected": fmt(obs / expected if expected else math.nan, 4), "calendar_post_july_2024": 1 if mo >= BREAK_MONTH else 0, "cumulative_pipeline_gap_since_july_2024": fmt(cumulative, 3) if mo >= BREAK_MONTH else "", "benchmark_source": "pre-transition project-age-bin profile only"})
    write_csv(out.pipeline_expected, rows, list(rows[0].keys()))
    write_csv(out.pipeline_gap, rows, list(rows[0].keys()))
    post = [r for r in rows if r["calendar_post_july_2024"] == 1]
    metrics = {
        "jul_2024_mar_2025_gap": sum(float(r["pipeline_gap_actual_minus_expected"]) for r in post[:9]),
        "calendar_2025_gap": sum(float(r["pipeline_gap_actual_minus_expected"]) for r in post[6:18]),
        "final_cumulative_gap": float(post[-1]["cumulative_pipeline_gap_since_july_2024"]),
        "mean_2025_ratio": sum(float(r["pipeline_ratio_actual_over_expected"]) for r in post[6:18]) / 12,
    }
    return rows, profile, metrics


def write_audits_and_summaries(audit: dict[str, object], system_rows: list[dict[str, object]], cohort_summary: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    audit_rows = [{"metric": k, "value": v} for k, v in audit.items()]
    audit_rows += [
        {"metric": "primary_system_output_start", "value": PRIMARY_START.isoformat()},
        {"metric": "primary_system_output_end", "value": PRIMARY_END.isoformat()},
        {"metric": "primary_system_output_months", "value": len([r for r in system_rows if PRIMARY_START <= parse_date(str(r["month_start"])) <= PRIMARY_END])},
        {"metric": "primary_pre_transition_months", "value": len([r for r in system_rows if PRIMARY_START <= parse_date(str(r["month_start"])) < BREAK_MONTH])},
        {"metric": "primary_post_transition_months", "value": len([r for r in system_rows if BREAK_MONTH <= parse_date(str(r["month_start"])) <= PRIMARY_END])},
        {"metric": "right_edge_decision", "value": "calendar-time primary analyses end at 2025-12; 2026 retained only as right-edge completeness diagnostic"},
    ]
    write_csv(out.outcome_audit, audit_rows, ["metric", "value"])

    outcome_rows = [
        {"y_family": "Y1 total monthly publications", "unit_of_observation": "calendar month", "numerator": "fractional_publication_count", "denominator": "none", "time_index": "calendar month", "pre_post_definition": "month before/after July 2024", "primary_question": "system-level scientific output", "feasibility_status": "primary feasible", "followup_limitation": "publication lag complicates immediate interpretation"},
        {"y_family": "Y2 incumbent-pool publication intensity", "unit_of_observation": "calendar month", "numerator": "fractional publication credit linked to pre-transition incumbents", "denominator": "post-start incumbent projects observable by month end", "time_index": "calendar month", "pre_post_definition": "month before/after July 2024", "primary_question": "supplementary decomposition of dynamic incumbent pool", "feasibility_status": "supplementary feasible", "followup_limitation": "changing denominator and project-age composition"},
        {"y_family": "Y3 fixed-cohort publication intensity", "unit_of_observation": "calendar month x fixed cohort", "numerator": "fractional publication credit from fixed cohort", "denominator": "fixed cohort size", "time_index": "calendar month", "pre_post_definition": "month before/after July 2024", "primary_question": "stable-membership publication intensity", "feasibility_status": "robustness feasible", "followup_limitation": "older-cohort composition differs from new project pipeline"},
        {"y_family": "Y4 project-age lifecycle output", "unit_of_observation": "project age month or age band", "numerator": "fractional publication credit at age", "denominator": "projects with complete follow-up to age", "time_index": "months since project start", "pre_post_definition": "not a calendar pre/post object", "primary_question": "publication productivity by project age", "feasibility_status": "feasible", "followup_limitation": "right-censoring handled by age-specific risk sets"},
        {"y_family": "Y5 fixed-follow-up publication count", "unit_of_observation": "project", "numerator": "fractional publications within H months", "denominator": "eligible projects with complete H-month follow-up", "time_index": "project age horizon", "pre_post_definition": "project start before/after 2024-07-05", "primary_question": "RAP-era project early productivity", "feasibility_status": "12-month post cohort feasible; 18/24-month post cohort infeasible", "followup_limitation": "post-RAP projects have short follow-up"},
        {"y_family": "Y6 any publication within fixed follow-up", "unit_of_observation": "project", "numerator": "indicator of any linked publication within H months", "denominator": "eligible projects with complete H-month follow-up", "time_index": "project age horizon", "pre_post_definition": "project start before/after 2024-07-05", "primary_question": "early extensive-margin productivity", "feasibility_status": "12-month post cohort feasible; 18/24-month post cohort infeasible", "followup_limitation": "post-RAP projects have short follow-up"},
        {"y_family": "Y7 time to first publication", "unit_of_observation": "project x age", "numerator": "first publication by age", "denominator": "projects with complete follow-up to age", "time_index": "months since project start", "pre_post_definition": "project start before/after 2024-07-05", "primary_question": "publication timing", "feasibility_status": "early post-cohort timing feasible only at short ages", "followup_limitation": "post-RAP timing cannot yet be evaluated at mature ages"},
        {"y_family": "Y8 project-month publication panel", "unit_of_observation": "project x calendar month", "numerator": "fractional publication count linked to project in month", "denominator": "not normalized in row; age and calendar controls available", "time_index": "calendar month and project age", "pre_post_definition": "calendar post indicator separate from project cohort indicator", "primary_question": "lifecycle-adjusted descriptive regressions", "feasibility_status": "constructed", "followup_limitation": "descriptive only; July 2024 is not every incumbent's treatment date"},
        {"y_family": "Y9 pipeline-adjusted publication gap", "unit_of_observation": "calendar month", "numerator": "actual fractional publication count minus pipeline expected count", "denominator": "historical project-age profile estimated before July 2024", "time_index": "calendar month", "pre_post_definition": "month before/after July 2024", "primary_question": "pipeline-adjusted system output", "feasibility_status": "feasible as historical benchmark", "followup_limitation": "not a causal untreated potential outcome"},
    ]
    write_csv(out.outcome_summary, outcome_rows, list(outcome_rows[0].keys()))

    recent_rows = [
        {"grain": "summary", "period": "latest_schema19_exact_publication", "period_start": audit["latest_exact_schema19_publication_date"], "period_end": audit["latest_exact_schema19_publication_date"], "publication_app_links": "", "unique_publication_ids": "", "fractional_publication_count": "", "note": "Latest exact publication date in the local public UKB Schema19 snapshot."},
        {"grain": "summary", "period": "reliable_censor_date_used_for_project_followup", "period_start": CENSOR_DATE.isoformat(), "period_end": CENSOR_DATE.isoformat(), "publication_app_links": "", "unique_publication_ids": "", "fractional_publication_count": "", "note": "Conservative reliable end date used for primary calendar-time analyses and fixed follow-up eligibility."},
    ]
    for r in system_rows:
        mo = parse_date(str(r["month_start"]))
        if mo >= date(2025, 8, 1):
            recent_rows.append({"grain": "month", "period": r["month"], "period_start": r["month_start"], "period_end": month_end(mo).isoformat(), "publication_app_links": r["publication_app_links"], "unique_publication_ids": r["unique_publication_ids"], "fractional_publication_count": r["fractional_publication_count"], "note": "Right edge may be incomplete until external bibliographic completeness is validated."})
    write_csv(out.recent_completeness, recent_rows, list(recent_rows[0].keys()))
    return outcome_rows


def moving_average(values: list[float], width: int = 3) -> list[float]:
    out = []
    for i in range(len(values)):
        lo = max(0, i - width + 1)
        out.append(sum(values[lo : i + 1]) / (i - lo + 1))
    return out


def svg_time_chart(path: Path, title: str, series: list[tuple[date, float, str]], y_label: str, start: date, end: date, break_line: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1060, 520
    left, right, top, bottom = 78, 30, 46, 62
    vals = [v for _, v, _ in series] or [0.0]
    ymin, ymax = min(vals), max(vals)
    pad = (ymax - ymin) * 0.12 or 1.0
    ymin -= pad
    ymax += pad
    total = max(age_months(start, end), 1)

    def x(mo: date) -> float:
        return left + age_months(start, mo) / total * (width - left - right)

    def y(val: float) -> float:
        return top + (ymax - val) / (ymax - ymin) * (height - top - bottom)

    colors = {"observed": "#1f6feb", "rolling3": "#0f766e", "expected": "#b42318", "app_links": "#8250df", "unique": "#1f6feb", "fractional": "#2da44e", "gap": "#b42318", "2021-07-01": "#1f6feb", "2022-01-01": "#2da44e", "2022-07-01": "#8250df", "incumbent": "#6b7280"}
    groups = defaultdict(list)
    for mo, val, label in series:
        groups[label].append((mo, val))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#ffffff"/>', f'<text x="{left}" y="28" font-family="Arial" font-size="20" font-weight="700">{title}</text>', f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" font-family="Arial" font-size="13" fill="#444">{y_label}</text>']
    for i in range(5):
        yy = top + i * (height - top - bottom) / 4
        val = ymax - i * (ymax - ymin) / 4
        parts.append(f'<line x1="{left}" x2="{width-right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{val:.1f}</text>')
    if break_line:
        bx = x(BREAK_MONTH)
        parts.append(f'<line x1="{bx:.1f}" x2="{bx:.1f}" y1="{top}" y2="{height-bottom}" stroke="#111827" stroke-dasharray="5 5"/>')
        parts.append(f'<text x="{bx+7:.1f}" y="{top+16}" font-family="Arial" font-size="12" fill="#111827">Jul 2024 transition marker</text>')
    for label, pts in groups.items():
        pts = sorted(pts)
        path_d = " ".join(("M" if i == 0 else "L") + f"{x(mo):.1f},{y(val):.1f}" for i, (mo, val) in enumerate(pts))
        parts.append(f'<path d="{path_d}" fill="none" stroke="{colors.get(label, "#374151")}" stroke-width="2.4"/>')
        for mo, val in pts:
            if label == "observed":
                parts.append(f'<circle cx="{x(mo):.1f}" cy="{y(val):.1f}" r="2.5" fill="{colors.get(label, "#374151")}" opacity="0.75"/>')
    for yr in range(start.year, end.year + 1):
        mo = date(yr, 1, 1)
        if start <= mo <= end:
            parts.append(f'<text x="{x(mo):.1f}" y="{height-24}" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">{yr}</text>')
    parts.append("</svg>")
    write_text(path, "\n".join(parts))


def svg_xy_chart(path: Path, title: str, series: list[tuple[float, float, str]], x_label: str, y_label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 900, 460
    left, right, top, bottom = 78, 30, 46, 62
    xs = [x for x, _, _ in series] or [0.0]
    ys = [y for _, y, _ in series] or [0.0]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    ypad = (ymax - ymin) * 0.12 or 1.0
    ymin -= ypad
    ymax += ypad

    def sx(v: float) -> float:
        return left + (v - xmin) / max(xmax - xmin, 1e-12) * (width - left - right)

    def sy(v: float) -> float:
        return top + (ymax - v) / max(ymax - ymin, 1e-12) * (height - top - bottom)

    colors = {"profile": "#1f6feb", "pre_rap_project_start": "#1f6feb", "post_rap_project_start": "#b42318", "acf": "#1f6feb", "pacf": "#8250df"}
    groups = defaultdict(list)
    for xv, yv, label in series:
        groups[label].append((xv, yv))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#ffffff"/>', f'<text x="{left}" y="28" font-family="Arial" font-size="20" font-weight="700">{title}</text>', f'<text x="{width/2}" y="{height-18}" text-anchor="middle" font-family="Arial" font-size="13" fill="#444">{x_label}</text>', f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" font-family="Arial" font-size="13" fill="#444">{y_label}</text>']
    for i in range(5):
        yy = top + i * (height - top - bottom) / 4
        val = ymax - i * (ymax - ymin) / 4
        parts.append(f'<line x1="{left}" x2="{width-right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{val:.2f}</text>')
    for label, pts in groups.items():
        pts = sorted(pts)
        path_d = " ".join(("M" if i == 0 else "L") + f"{sx(xv):.1f},{sy(yv):.1f}" for i, (xv, yv) in enumerate(pts))
        parts.append(f'<path d="{path_d}" fill="none" stroke="{colors.get(label, "#374151")}" stroke-width="2.4"/>')
    parts.append("</svg>")
    write_text(path, "\n".join(parts))


def svg_bar_chart(path: Path, title: str, rows: list[dict[str, object]]) -> None:
    width, height = 860, 420
    left, top, bottom = 78, 42, 70
    maxv = max(float(r["share_percent"]) for r in rows)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#ffffff"/>', f'<text x="{left}" y="28" font-family="Arial" font-size="20" font-weight="700">{title}</text>']
    for i, r in enumerate(rows):
        x = left + i * 150
        h = float(r["share_percent"]) / maxv * (height - top - bottom)
        y = height - bottom - h
        parts.append(f'<rect x="{x}" y="{y:.1f}" width="110" height="{h:.1f}" fill="#1f6feb"/>')
        parts.append(f'<text x="{x+55}" y="{y-8:.1f}" text-anchor="middle" font-family="Arial" font-size="12">{float(r["share_percent"]):.1f}%</text>')
        parts.append(f'<text x="{x+55}" y="{height-42}" text-anchor="middle" font-family="Arial" font-size="11">{str(r["lag_bin"]).replace("_", " ")}</text>')
    parts.append("</svg>")
    write_text(path, "\n".join(parts))


def make_figures(system_rows: list[dict[str, object]], measure_rows: list[dict[str, object]], age_rows: list[dict[str, object]], pipeline_rows: list[dict[str, object]], timing_rows: list[dict[str, object]], fixed_rows: list[dict[str, object]], incumbent_rows: list[dict[str, object]], lag_rows: list[dict[str, object]], ac_rows: list[dict[str, object]], out: Outputs) -> None:
    primary_system = [r for r in system_rows if PRIMARY_START <= parse_date(str(r["month_start"])) <= PRIMARY_END]
    months = [parse_date(str(r["month_start"])) for r in primary_system]
    frac = [float(r["fractional_publication_count"]) for r in primary_system]
    smooth = moving_average(frac, 3)
    svg_time_chart(out.total_monthly_figure, "Total Monthly UKB-Linked Publication Output", [(m, v, "observed") for m, v in zip(months, frac)] + [(m, v, "rolling3") for m, v in zip(months, smooth)], "Fractional publication count", PRIMARY_START, PRIMARY_END)
    svg_time_chart(out.measure_comparison_figure, "Publication Measurement Comparison", [(parse_date(str(r["period_start"])), float(r["publication_app_links"]), "app_links") for r in measure_rows if PRIMARY_START <= parse_date(str(r["period_start"])) <= PRIMARY_END] + [(parse_date(str(r["period_start"])), float(r["unique_publication_ids"]), "unique") for r in measure_rows if PRIMARY_START <= parse_date(str(r["period_start"])) <= PRIMARY_END] + [(parse_date(str(r["period_start"])), float(r["fractional_publication_count"]), "fractional") for r in measure_rows if PRIMARY_START <= parse_date(str(r["period_start"])) <= PRIMARY_END], "Monthly count", PRIMARY_START, PRIMARY_END)
    age_plot = [r for r in age_rows if int(r["project_age_months"]) <= 96]
    svg_xy_chart(out.project_age_figure, "Publication Output By Project Age", [(float(r["project_age_months"]), float(r["publications_per_100_projects_at_risk"]), "profile") for r in age_plot], "Project age in months", "Fractional publications per 100 at-risk projects")
    svg_time_chart(out.pipeline_expected_figure, "Observed Versus Pipeline-Expected Publication Output", [(parse_date(str(r["month_start"])), float(r["actual_fractional_publication_count"]), "observed") for r in pipeline_rows] + [(parse_date(str(r["month_start"])), float(r["pipeline_expected_fractional_publication_count"]), "expected") for r in pipeline_rows], "Fractional publication count", PRIMARY_START, PRIMARY_END)
    svg_time_chart(out.pipeline_gap_figure, "Pipeline Gap: Actual Minus Historical Pipeline Expected", [(parse_date(str(r["month_start"])), float(r["pipeline_gap_actual_minus_expected"]), "gap") for r in pipeline_rows], "Actual minus expected", PRIMARY_START, PRIMARY_END)
    timing_plot = [r for r in timing_rows if int(r["project_age_months"]) <= 12 and r["cumulative_first_publication_probability_percent"]]
    svg_xy_chart(out.cohort_followup_figure, "First Publication Timing By Project Cohort", [(float(r["project_age_months"]), float(r["cumulative_first_publication_probability_percent"]), str(r["project_cohort"])) for r in timing_plot], "Project age in months", "Cumulative probability of first publication (%)")
    svg_time_chart(out.fixed_cohort_figure, "Fixed-Cohort Publication Intensity", [(parse_date(str(r["month_start"])), float(r["fractional_publications_per_100_fixed_cohort"]), str(r["cohort_cutoff"])) for r in fixed_rows], "Fractional publications per 100 fixed-cohort projects", date(2021, 7, 1), PRIMARY_END)
    svg_time_chart(out.incumbent_figure, "Supplementary Incumbent-Pool Publication Intensity", [(parse_date(str(r["month_start"])), float(r["fractional_publications_per_100_post_start_incumbents"]), "incumbent") for r in incumbent_rows if PRIMARY_START <= parse_date(str(r["month_start"])) <= PRIMARY_END], "Fractional publications per 100 dynamic incumbents", PRIMARY_START, PRIMARY_END)
    svg_bar_chart(out.lag_figure, "Project-Start To Publication Lag Distribution", lag_rows)
    svg_xy_chart(out.acf_figure, "Primary Total-Output ITS Residual ACF", [(float(r["lag"]), float(r["acf"]), "acf") for r in ac_rows], "Lag", "ACF")
    svg_xy_chart(out.pacf_figure, "Primary Total-Output ITS Residual PACF", [(float(r["lag"]), float(r["pacf"]), "pacf") for r in ac_rows], "Lag", "PACF")


def stata_style_results(
    its_rows: list[dict[str, object]],
    sens_its: list[dict[str, object]],
    hac_rows: list[dict[str, object]],
    ar1_rows: list[dict[str, object]],
    poisson_rows: list[dict[str, object]],
) -> str:
    def z_stat(row: dict[str, object]) -> float:
        return float(row["estimate"]) / float(row["std_error"])

    def reg_line(name: str, row: dict[str, object], irr: bool = False) -> str:
        base = (
            f"{name:<20} |"
            f"{float(row['estimate']):>12.4f}"
            f"{float(row['std_error']):>11.4f}"
            f"{z_stat(row):>8.2f}"
            f"{float(row['p_value']):>9.4f}"
            f"{float(row['ci_low']):>12.4f}"
            f"{float(row['ci_high']):>12.4f}"
        )
        if irr:
            base += f"{math.exp(float(row['estimate'])):>10.3f}"
        return base

    primary = {r["term"]: r for r in its_rows}
    ar1 = {r["term"]: r for r in ar1_rows}
    poisson = {r["term"]: r for r in poisson_rows}
    sens_lines = [
        f"{r['outcome']:<36} {r['term']:<19} {float(r['estimate']):>10.4f} {float(r['std_error']):>10.4f} {float(r['p_value']):>8.4f} {float(r['ci_low']):>10.4f} {float(r['ci_high']):>10.4f}"
        for r in sens_its
        if r["term"] in {"PostJuly2024", "TimeAfterJuly2024"}
    ]
    hac_lines = [
        f"{r['model'].replace('Primary total-output ITS, linear ', ''):<8} {r['term']:<19} {float(r['estimate']):>10.4f} {float(r['std_error']):>10.4f} {float(r['p_value']):>8.4f} {float(r['ci_low']):>10.4f} {float(r['ci_high']):>10.4f}"
        for r in hac_rows
        if r["term"] in {"PostJuly2024", "TimeAfterJuly2024"}
    ]
    return f"""Publication total-output segmented ITS, primary model
Outcome: monthly total fractional publication count
Sample: 2019-01 to 2025-12                 Number of obs = 84
Seasonality: month-of-year fixed effects  Newey-West lag = 3
Inference: OLS with Newey-West HAC standard errors

------------------------------------------------------------------------------
 fractional_count    | Coefficient  Std. err.       z    P>|z|      [95% conf. interval]
---------------------+--------------------------------------------------------
{reg_line('Time', primary['Time'])}
{reg_line('PostJuly2024', primary['PostJuly2024'])}
{reg_line('TimeAfterJuly2024', primary['TimeAfterJuly2024'])}
 Month FE            |         Yes
------------------------------------------------------------------------------

Aggregate-output measurement sensitivity, same ITS specification
-----------------------------------------------------------------------------------------------
 Outcome                              Term                    Coef.  Std. err.    P>|z|     CI low    CI high
-----------------------------------------------------------------------------------------------
{chr(10).join(sens_lines)}
-----------------------------------------------------------------------------------------------

Newey-West HAC lag sensitivity, primary total-output outcome
--------------------------------------------------------------------------------
 HAC lag  Term                    Coef.  Std. err.    P>|z|     CI low    CI high
--------------------------------------------------------------------------------
{chr(10).join(hac_lines)}
--------------------------------------------------------------------------------

Prais-Winsten AR(1) robustness
Estimated rho: {ar1['Time']['notes'].replace('estimated rho = ', '')}
------------------------------------------------------------------------------
 fractional_count    | Coefficient  Std. err.       z    P>|z|      [95% conf. interval]
---------------------+--------------------------------------------------------
{reg_line('Time', ar1['Time'])}
{reg_line('PostJuly2024', ar1['PostJuly2024'])}
{reg_line('TimeAfterJuly2024', ar1['TimeAfterJuly2024'])}
------------------------------------------------------------------------------

Poisson QMLE count robustness
Outcome: monthly unique publication IDs
Inference: Poisson QMLE with HAC standard errors
----------------------------------------------------------------------------------------
 unique_pub_ids      | Coefficient  Std. err.       z    P>|z|      [95% conf. interval]       IRR
---------------------+------------------------------------------------------------------
{reg_line('Time', poisson['Time'], irr=True)}
{reg_line('PostJuly2024', poisson['PostJuly2024'], irr=True)}
{reg_line('TimeAfterJuly2024', poisson['TimeAfterJuly2024'], irr=True)}
----------------------------------------------------------------------------------------

Notes:
1. This is Stata-style formatting of the repository's generated Python estimates, not a separate Stata execution log.
2. The primary publication outcome is system-level total fractional output, not publication output per incumbent project.
3. Coefficients are descriptive calendar-time changes and should not be interpreted as causal RAP treatment effects."""


def docs(out: Outputs, audit: dict[str, object], lag_rows: list[dict[str, object]], system_rows: list[dict[str, object]], its_rows: list[dict[str, object]], sens_its: list[dict[str, object]], ac_rows: list[dict[str, object]], hac_rows: list[dict[str, object]], ar1_rows: list[dict[str, object]], poisson_rows: list[dict[str, object]], cohort_summary: list[dict[str, object]], fixed_results: list[dict[str, object]], pipeline_metrics: dict[str, float]) -> None:
    primary = {r["term"]: r for r in its_rows}
    ar1 = {r["term"]: r for r in ar1_rows}
    poisson = {r["term"]: r for r in poisson_rows}
    pre = [r for r in system_rows if PRIMARY_START <= parse_date(str(r["month_start"])) < BREAK_MONTH]
    post = [r for r in system_rows if BREAK_MONTH <= parse_date(str(r["month_start"])) <= PRIMARY_END]
    pre_mean = sum(float(r["fractional_publication_count"]) for r in pre) / len(pre)
    post_mean = sum(float(r["fractional_publication_count"]) for r in post) / len(post)
    jul_sep = [r for r in post if r["jul_sep_2024_window"] == 1]
    jul_sep_mean = sum(float(r["fractional_publication_count"]) for r in jul_sep) / len(jul_sep)
    mean_2025 = sum(float(r["fractional_publication_count"]) for r in post[6:18]) / 12
    multi_share = 100.0 * audit["publication_ids_linked_to_multiple_valid_applications"] / audit["cleaned_unique_publication_ids"]
    lb = {int(r["lag"]): r for r in ac_rows}
    post12 = next(r for r in cohort_summary if r["project_cohort"] == "post_rap_project_start" and r["followup_horizon_months"] == 12)
    pre12 = next(r for r in cohort_summary if r["project_cohort"] == "pre_rap_project_start" and r["followup_horizon_months"] == 12)
    post18 = next(r for r in cohort_summary if r["project_cohort"] == "post_rap_project_start" and r["followup_horizon_months"] == 18)
    post24 = next(r for r in cohort_summary if r["project_cohort"] == "post_rap_project_start" and r["followup_horizon_months"] == 24)
    fixed_main = next(r for r in fixed_results if "2022-07-01" in r["outcome"] and r["term"] == "TimeAfterJuly2024")
    system_class = "C. gradual increase"
    productivity_class = "D. higher early productivity at the feasible 12-month horizon; 18/24-month post-RAP follow-up is insufficient"
    timing_class = "D. faster at the feasible 12-month horizon; mature timing remains insufficiently observed"
    if pipeline_metrics["calendar_2025_gap"] > 0 and pipeline_metrics["final_cumulative_gap"] > 0:
        pipeline_class = "C. above historical pipeline expectation"
    elif pipeline_metrics["calendar_2025_gap"] > 0 and pipeline_metrics["final_cumulative_gap"] <= 0:
        pipeline_class = "D. mixed"
    else:
        pipeline_class = "A. below historical pipeline expectation"
    stata_output = stata_style_results(its_rows, sens_its, hac_rows, ar1_rows, poisson_rows)
    write_text(out.stata_style_output, stata_output)

    write_text(out.readme, """# Publication-Output Module

This module implements the revised publication outcome hierarchy.

Start with:

1. `reports/publication_reading_guide.md`
2. `reports/publication_measurement_note.md`
3. `reports/publication_its_results.md`
4. `figures/publication_total_monthly.svg`
5. `figures/publication_observed_vs_pipeline_expected.svg`

The primary publication outcome is total monthly `fractional_publication_count`, not publications per incumbent project.
""")

    write_text(out.design, """# Publication ITS Design

The publication analysis separates system-level output, project-level productivity/timing, and pipeline-adjusted output. Total scientific output is interpreted as the product of project entry, project-level productivity, and publication timing.

| Candidate Y | Definition | Research Question | Main Limitations | How Limitations Are Addressed |
| --- | --- | --- | --- | --- |
| Y1 Total monthly publications | Monthly total `fractional_publication_count` | Did system-level UKB-linked publication flow change around July 2024? | Publication response is lagged; total output mixes entry and productivity. | Treat as descriptive calendar-time ITS; report lag and pipeline diagnostics. |
| Y2 Publications per dynamic incumbent pool | 100 x fractional publications linked to pre-transition incumbents / post-start incumbents | How does incumbent-pool intensity evolve? | Denominator grows before July 2024 and age composition changes. | Demoted to supplementary decomposition. |
| Y3 Fixed-cohort publication intensity | 100 x cohort publications / fixed cohort size | Does a stable pre-transition cohort show similar movement? | Older cohorts are not representative of all system output. | Prespecified cutoffs, no selection by significance. |
| Y4 Project-age-standardized publication rate | Publication output by project age month or age band | How strongly does output vary over the project lifecycle? | Right-censoring at long ages for recent cohorts. | Age-specific risk sets with complete follow-up. |
| Y5 Publications within fixed follow-up window | Project-level fractional publications within H months | Are RAP-era projects similarly productive at comparable early ages? | Post-RAP cohorts currently have limited follow-up. | Only eligible projects with complete follow-up are included. |
| Y6 Any publication within fixed follow-up window | Project-level any-publication indicator within H months | Do RAP-era projects reach first output at similar early rates? | Same short follow-up problem. | Report feasible 12-month horizon and mark 18/24 months infeasible for post cohorts. |
| Y7 Time to first publication | Cumulative first-publication probability by project age | Does timing differ across project-start cohorts? | Mature post-RAP timing is not observed. | Transparent cumulative-incidence tables, no causal survival claim. |
| Y8 Project-month publication count | Project x calendar month fractional output | How do calendar time and project age jointly describe output? | High-dimensional descriptive panel; July is not individual treatment for incumbents. | Calendar post and project age are separate variables. |
| Y9 Pipeline-adjusted publication gap | Actual total output minus expected output from pre-transition age profile and project pipeline | Is post-July total output unusual relative to the evolving project pipeline? | Historical benchmark, not causal counterfactual. | Estimate age profile only from pre-transition information. |

Alternative outcomes are Y1 measurement variants and Y2/Y3 rate definitions. Y4-Y9 diagnose limitations in total-output interpretation.
""")

    write_text(out.measurement_note, f"""# Publication Measurement Note

## Core Definitions

Publication date is the exact `date_pub` in public Schema19. An application-publication link is one row in Schema24 joining `app_id` to `pub_id`. A unique publication is a distinct `pub_id`.

Fractional publication credit gives each cleaned application-publication link weight `1 / number of cleaned valid application links for that publication`. The fractional weights for one publication sum to one, so total fractional monthly output avoids full multi-application double counting.

Project start date is the public UKB project `Start date`. Project age is the exact month difference between publication date and project start date. Incumbent means project start date before 2024-07-05. Fixed cohort means a prespecified set of projects started before a cutoff such as 2022-07-01.

Calendar-time post means publication month >= 2024-07. Project-cohort post means project start date >= 2024-07-05. These are different indicators.

Censoring date for project-level follow-up is {CENSOR_DATE.isoformat()}. A project is eligible for an H-month outcome only if its project start date plus H months is on or before that censoring date.

## Audit

- Schema19 publications: {audit['total_schema19_publications']:,}
- Schema24 app-publication links: {audit['total_schema24_app_publication_links']:,}
- Cleaned publication-app events: {audit['cleaned_publication_app_events']:,}
- Cleaned unique publication IDs: {audit['cleaned_unique_publication_ids']:,}
- Publication IDs linked to multiple valid applications: {audit['publication_ids_linked_to_multiple_valid_applications']:,} ({multi_share:.2f}%)
- Publication-before-project-start exclusions: {audit['publication_before_project_start_exclusions']:,}
- Unmatched app links: {audit['unmatched_app_links']:,}
- Latest exact Schema19 publication date: {audit['latest_exact_schema19_publication_date']}

A publication observed in March 2025 does not imply that the associated project began in March 2025. Publications may be produced years after project initiation.

## Publication Lag

This is project-start-to-publication lag, not RAP-to-publication lag. The median is {lag_rows[0]['median_lag_months_all_events']} months. Shares are 0-6 months {lag_rows[0]['share_percent']}%, 7-12 months {lag_rows[1]['share_percent']}%, 13-24 months {lag_rows[2]['share_percent']}%, 25-48 months {lag_rows[3]['share_percent']}%, and 49+ months {lag_rows[4]['share_percent']}%.
""")

    write_text(out.results_report, f"""# Publication ITS Results

## 1. Research Question

The publication analysis now separates three empirical objects: system-level scientific output, project-level productivity and timing, and pipeline-adjusted output.

## 2. Why Publications Require A Pipeline Framework

Total scientific output equals project entry multiplied by project-level productivity and publication timing. Project entry is dynamic, and publication output has a long project-start-to-publication lag.

## 3. Publication Data And Linkage Construction

The analysis starts from {audit['total_schema19_publications']:,} Schema19 publications and {audit['total_schema24_app_publication_links']:,} Schema24 app-publication links. After matching to the project universe and excluding publication-before-start links, it uses {audit['cleaned_publication_app_events']:,} cleaned links and {audit['cleaned_unique_publication_ids']:,} unique publications.

## 4. Candidate Outcome Hierarchy

Y1 total monthly fractional publication output is primary. Y2 incumbent-pool intensity is supplementary. Y3 fixed cohorts, Y4 project-age profiles, Y5/Y6 fixed follow-up, Y7 time to first publication, Y8 project-month panel, and Y9 pipeline gaps diagnose mechanisms and limitations.

## 5. Primary Outcome: Total Monthly Publication Flow

The primary outcome is monthly total `fractional_publication_count`, with no incumbent denominator. This is closest to the theoretical question about the total number of scientific outcomes and allows project entry to be part of the system-level mechanism.

## 6. Raw Calendar-Time Pattern

In the 2019-01 to 2025-12 primary window, mean monthly total fractional output is {pre_mean:.2f} before July 2024 and {post_mean:.2f} after July 2024. July-September 2024 averages {jul_sep_mean:.2f}, while calendar 2025 averages {mean_2025:.2f}. The raw total-output series does not show a sharp immediate collapse around July 2024; 2025 is higher.

## 7. Primary Segmented ITS

The primary model is a monthly linear segmented ITS with month-of-year fixed effects and Newey-West HAC lag 3. There are 84 months: 66 pre-transition and 18 post-transition.

| Term | Estimate | SE | p-value | 95% CI | Economic reading |
| --- | ---: | ---: | ---: | ---: | --- |
| Time | {primary['Time']['estimate']} | {primary['Time']['std_error']} | {primary['Time']['p_value']} | [{primary['Time']['ci_low']}, {primary['Time']['ci_high']}] | pre-transition monthly trend in total fractional publication output |
| PostJuly2024 | {primary['PostJuly2024']['estimate']} | {primary['PostJuly2024']['std_error']} | {primary['PostJuly2024']['p_value']} | [{primary['PostJuly2024']['ci_low']}, {primary['PostJuly2024']['ci_high']}] | immediate descriptive level change at the institutional marker |
| TimeAfterJuly2024 | {primary['TimeAfterJuly2024']['estimate']} | {primary['TimeAfterJuly2024']['std_error']} | {primary['TimeAfterJuly2024']['p_value']} | [{primary['TimeAfterJuly2024']['ci_low']}, {primary['TimeAfterJuly2024']['ci_high']}] | post-July monthly slope change in total output |

Because publication response is lagged, `PostJuly2024` should not be interpreted as an immediate RAP productivity response.

### Stata-Style Output For Reporting

The following block is a Stata-style presentation of the generated publication regressions. It is also saved as `reports/publication_stata_style_results.txt`.

```text
{stata_output}
```

## 8. Autocorrelation And HAC Inference

After trend, July terms, and month fixed effects, Durbin-Watson is {lb[1]['durbin_watson_primary_model']}. Ljung-Box p-values are {lb[1]['ljung_box_p_value']} at lag 1, {lb[3]['ljung_box_p_value']} at lag 3, {lb[6]['ljung_box_p_value']} at lag 6, and {lb[12]['ljung_box_p_value']} at lag 12. These diagnostics are reported descriptively, not as pass/fail tests.

HAC(1), HAC(3), HAC(6), and HAC(12) keep identical OLS point estimates; only uncertainty changes. AR(1) robustness estimates rho = {ar1['Time']['notes'].replace('estimated rho = ', '')}; the slope-change estimate is {ar1['TimeAfterJuly2024']['estimate']} with SE {ar1['TimeAfterJuly2024']['std_error']}.

## 9. Publication Measurement Sensitivity

{audit['publication_ids_linked_to_multiple_valid_applications']:,} publications are linked to multiple valid applications. Measurement sensitivity compares app links, unique publications, and fractional counts. The broad total-output trajectory is not driven only by multi-application linking.

## 10. Project-Start-To-Publication Lag

Median project-start-to-publication lag is {lag_rows[0]['median_lag_months_all_events']} months, and {float(lag_rows[3]['share_percent']) + float(lag_rows[4]['share_percent']):.2f}% of links occur after 24 months. This is not RAP-to-publication lag. It is why immediate post-July publications mostly reflect work initiated earlier.

## 11. Project-Age Publication Profile

Project-age profiles show publication productivity varies strongly over the project lifecycle. The age profile is therefore central to interpreting total-output growth.

## 12. Fixed-Cohort Analysis

Fixed cohorts are constructed using prespecified cutoffs 2021-07-01, 2022-01-01, and 2022-07-01. For the 2022-07-01 cohort, the post-July slope estimate is {fixed_main['estimate']} with SE {fixed_main['std_error']}. This is a stable-membership diagnostic, not the primary system-level outcome.

## 13. Fixed-Follow-Up Project Productivity

At 12 months, eligible pre-RAP projects number {pre12['eligible_projects']} and eligible post-RAP projects number {post12['eligible_projects']}. Mean Pub12 is {pre12['mean_fractional_publications']} for pre-RAP starts and {post12['mean_fractional_publications']} for post-RAP starts; AnyPub12 is {pre12['any_publication_rate_percent']}% versus {post12['any_publication_rate_percent']}%. Post-RAP 18- and 24-month outcomes are {post18['followup_limitation']} and {post24['followup_limitation']} under the {CENSOR_DATE.isoformat()} censor date.

## 14. Time To First Publication

Time-to-first-publication outputs use age-specific complete-follow-up denominators. They support only early post-RAP comparisons; mature publication timing for RAP-era projects is not yet observable.

## 15. Pipeline-Adjusted Expected Publication Output

The pipeline benchmark estimates the historical project-age publication profile using only calendar months before July 2024, then applies that profile to the evolving project pipeline. Calendar 2025 actual output is {pipeline_metrics['calendar_2025_gap']:.2f} fractional publications above the pipeline benchmark, with mean actual/expected ratio {pipeline_metrics['mean_2025_ratio']:.3f}; however, the cumulative July 2024-December 2025 pipeline gap is {pipeline_metrics['final_cumulative_gap']:.2f}, because late 2024 is below the pipeline benchmark. This is a historical benchmark, not a causal counterfactual.

## 16. Right-Edge Completeness

Primary calendar-time analyses end at 2025-12. The local snapshot contains publications through {audit['latest_exact_schema19_publication_date']}, but 2026 is retained only as a right-edge diagnostic.

## 17. Robustness

Robustness outputs include aggregate measurement sensitivity, HAC lag sensitivity, AR(1), Poisson QMLE for raw counts, fixed cohorts, project-follow-up outcomes, first-publication timing, and pre-transition placebo July breakpoints.

## 18. What The Evidence Supports

System output: {system_class}. Project productivity: {productivity_class}. Publication timing: {timing_class}. Pipeline-adjusted output: {pipeline_class}.

## 19. What The Evidence Cannot Establish

The evidence cannot establish that RAP caused publications to increase or decrease. July 5, 2024 is not the verified individual RAP-exposure date for every incumbent project. Total publication growth is not the same object as project-level productivity growth, and the fitted historical pipeline expected output is not a causal untreated potential outcome.

## 20. Paper-Ready Stylized Fact

> UKB-linked total publication output shows no sharp immediate collapse around the July 2024 institutional transition marker and rises through 2025 in the public publication series.

> Because project-start-to-publication lags are long, post-July 2024 publications largely reflect projects and research pipelines that began before the transition.

> Relative to a historical project-age pipeline benchmark, 2025 publication output is above expected after a below-benchmark late-2024 period; this should be interpreted as a descriptive pipeline-adjusted pattern rather than a causal RAP effect.

## Main Outputs

- Main ITS table: `data/publication_its_results_table.csv`
- Stata-style regression output: `reports/publication_stata_style_results.txt`
- Outcome hierarchy: `data/publication_outcome_summary.csv`
- System monthly series: `data/publication_system_total_monthly.csv`
- Project cohort summary: `data/publication_project_cohort_summary.csv`
- Main figures: `figures/publication_total_monthly.svg`, `figures/publication_measure_comparison.svg`, `figures/publication_project_age_profile.svg`, `figures/publication_observed_vs_pipeline_expected.svg`, `figures/publication_cohort_followup.svg`
""")

    write_text(out.reading_guide, f"""# Publication Results Reading Guide

The publication analysis separates total system-level publication output, project-level productivity/timing, and pipeline-adjusted output. Do not collapse these into one regression or interpret total publication growth as project-level RAP productivity.

## Read In This Order

1. `reports/publication_measurement_note.md`
2. `reports/publication_its_results.md`
3. `figures/publication_total_monthly.svg`
4. `figures/publication_project_age_profile.svg`
5. `figures/publication_observed_vs_pipeline_expected.svg`
6. `data/publication_its_results_table.csv`
7. `reports/publication_stata_style_results.txt`

## Main Numbers

- Primary Y: total monthly `fractional_publication_count`.
- Window: 2019-01 to 2025-12.
- Observations: 84 total, 66 pre-July-2024, 18 post-July-2024.
- Raw mean monthly output: {pre_mean:.2f} pre, {post_mean:.2f} post.
- Primary pre-trend: {primary['Time']['estimate']} (SE {primary['Time']['std_error']}).
- Primary level change: {primary['PostJuly2024']['estimate']} (SE {primary['PostJuly2024']['std_error']}, 95% CI [{primary['PostJuly2024']['ci_low']}, {primary['PostJuly2024']['ci_high']}]).
- Primary slope change: {primary['TimeAfterJuly2024']['estimate']} (SE {primary['TimeAfterJuly2024']['std_error']}, 95% CI [{primary['TimeAfterJuly2024']['ci_low']}, {primary['TimeAfterJuly2024']['ci_high']}]).
- Pipeline 2025 gap: {pipeline_metrics['calendar_2025_gap']:.2f}; cumulative July 2024-December 2025 gap: {pipeline_metrics['final_cumulative_gap']:.2f}; mean 2025 actual/expected ratio: {pipeline_metrics['mean_2025_ratio']:.3f}.
- Publication lag: median {lag_rows[0]['median_lag_months_all_events']} months from project start to publication.

## Main Figures

- `figures/publication_total_monthly.svg`
- `figures/publication_measure_comparison.svg`
- `figures/publication_project_age_profile.svg`
- `figures/publication_observed_vs_pipeline_expected.svg`
- `figures/publication_cohort_followup.svg`

## Main Tables

- `data/publication_its_results_table.csv`
- `reports/publication_stata_style_results.txt`
- `data/publication_outcome_summary.csv`
- `data/publication_project_cohort_summary.csv`

## Supplementary And Appendix Outputs

- `data/its_incumbent_publications_monthly.csv`
- `figures/publication_incumbent_pool_monthly.svg`
- `data/publication_fixed_cohort_monthly.csv`
- `figures/publication_fixed_cohort_monthly.svg`
- `data/publication_by_project_age.csv`
- `data/publication_age_band_profile.csv`
- `data/publication_project_followup_outcomes.csv`
- `data/publication_first_pub_timing.csv`
- `data/publication_project_month_panel.csv`
- `data/publication_pipeline_expected.csv`
- `data/publication_pipeline_gap.csv`
- `data/publication_its_autocorrelation_diagnostics.csv`
- `data/publication_its_hac_lag_sensitivity.csv`
- `data/publication_its_ar1_robustness.csv`
- `data/publication_poisson_count_robustness.csv`
- `data/publication_placebo_results.csv`
- `data/its_recent_publication_completeness.csv`

## Interpretation

System output: {system_class}. Project productivity: {productivity_class}. Publication timing: {timing_class}. Pipeline-adjusted output: {pipeline_class}.

Use descriptive language: post-transition publication trajectory, system-level publication output, RAP-era project cohort, historical project-age publication profile, and pipeline-adjusted historical benchmark.
""")


def validate_outputs(out: Outputs | None = None) -> None:
    out = out or Outputs()
    events = read_csv(out.clean_events)
    system_rows = read_csv(out.system_monthly)
    event_month = defaultdict(lambda: {"links": 0, "pubs": set(), "frac": 0.0})
    pub_weight = defaultdict(float)
    for e in events:
        assert int(e["project_age_months"]) >= 0
        assert e["publication_date"] >= e["project_start_date"]
        m = e["publication_month"]
        event_month[m]["links"] += 1
        event_month[m]["pubs"].add(e["pub_id"])
        event_month[m]["frac"] += float(e["fractional_weight"])
        pub_weight[e["pub_id"]] += float(e["fractional_weight"])
    assert all(abs(v - 1.0) < 1e-5 for v in pub_weight.values())
    jan2019 = next(r for r in system_rows if r["month"] == "2019-01")
    assert int(jan2019["publication_app_links"]) == event_month["2019-01-01"]["links"]
    assert int(jan2019["unique_publication_ids"]) == len(event_month["2019-01-01"]["pubs"])
    assert abs(float(jan2019["fractional_publication_count"]) - event_month["2019-01-01"]["frac"]) < 0.01
    primary_system = [r for r in system_rows if PRIMARY_START.isoformat() <= r["month_start"] <= PRIMARY_END.isoformat()]
    assert len(primary_system) == 84
    assert sum(1 for r in primary_system if r["month_start"] < BREAK_MONTH.isoformat()) == 66
    assert sum(1 for r in primary_system if r["month_start"] >= BREAK_MONTH.isoformat()) == 18
    assert all(r["right_edge_2026"] == "0" for r in primary_system)
    assert next(r for r in system_rows if r["month"] == "2024-06")["calendar_post_july_2024"] == "0"
    assert next(r for r in system_rows if r["month"] == "2024-07")["calendar_post_july_2024"] == "1"
    incumbent = read_csv(out.incumbent_monthly)
    assert "jul_sep_2024_window" in incumbent[0]
    assert all(not key.startswith("transition_pause") for key in incumbent[0])
    fixed = read_csv(out.fixed_cohort_monthly)
    for cutoff in {r["cohort_cutoff"] for r in fixed}:
        assert len({r["fixed_cohort_projects"] for r in fixed if r["cohort_cutoff"] == cutoff}) == 1
    follow = read_csv(out.project_followup)
    for r in follow:
        if r["followup_eligible_18m"] == "0":
            assert r["pub18_fractional"] == ""
        if r["followup_eligible_24m"] == "0":
            assert r["pub24_fractional"] == ""
        expected_cohort = "1" if r["project_start_date"] >= BREAK_DATE.isoformat() else "0"
        assert r["project_cohort_post_rap"] == expected_cohort
    profile = read_csv(out.pipeline_age_profile)
    assert all(r["estimated_using_calendar_months_before"] == BREAK_MONTH.isoformat() for r in profile)
    hac = read_csv(out.hac_sensitivity)
    for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
        assert len({r["estimate"] for r in hac if r["term"] == term}) == 1
    pipeline = read_csv(out.pipeline_gap)
    cumulative = 0.0
    for r in [r for r in pipeline if r["calendar_post_july_2024"] == "1"]:
        cumulative += float(r["pipeline_gap_actual_minus_expected"])
        assert abs(cumulative - float(r["cumulative_pipeline_gap_since_july_2024"])) < 0.02


def main() -> None:
    out = Outputs()
    projects, pubs, links = load_inputs()
    events, audit = build_events(projects, pubs, links)
    write_clean_events(events, out)
    system_rows = system_monthly(events, out)
    incumbent_rows, incumbent_quarterly = incumbent_pool_monthly(projects, events, out)
    lag_rows = write_lag(events, out)
    measure_rows = write_measurement_sensitivity(system_rows, out)
    its_rows, primary = run_primary_its(system_rows, out)
    sens_its = run_measurement_sensitivity_its(system_rows, out)
    hac_rows = hac_lag_sensitivity(primary, out)
    ac_rows = autocorrelation_diagnostics(primary, out)
    ar1_rows = ar1_robustness(primary, out)
    poisson_rows = poisson_robustness(system_rows, out)
    placebo_models(system_rows, out)
    age_rows, age_band_rows = project_age_outputs(projects, events, out)
    panel_rows = project_month_panel(projects, events, out)
    project_followup, cohort_summary, timing_rows = fixed_followup_outputs(projects, events, out)
    fixed_rows, fixed_results = fixed_cohort_outputs(projects, events, out)
    pipeline_rows, pipeline_profile, pipeline_metrics = pipeline_expected(projects, system_rows, panel_rows, out)
    write_audits_and_summaries(audit, system_rows, cohort_summary, out)
    make_figures(system_rows, measure_rows, age_rows, pipeline_rows, timing_rows, fixed_rows, incumbent_rows, lag_rows, ac_rows, out)
    docs(out, audit, lag_rows, system_rows, its_rows, sens_its, ac_rows, hac_rows, ar1_rows, poisson_rows, cohort_summary, fixed_results, pipeline_metrics)
    validate_outputs(out)
    print("publication ITS outputs built")


if __name__ == "__main__":
    main()
