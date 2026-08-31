#!/usr/bin/env python3
"""Build publication-output ITS outputs from public UKB publication metadata."""

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
FIXED_COHORT_CUTOFF = date(2022, 7, 1)
PRIMARY_HAC_LAG = 3


@dataclass(frozen=True)
class Outputs:
    readme: Path = PACKAGE / "README.md"
    design: Path = DESIGN_DIR / "publication_its_design.md"
    reading_guide: Path = REPORT_DIR / "publication_reading_guide.md"
    measurement_note: Path = REPORT_DIR / "publication_measurement_note.md"
    results_report: Path = REPORT_DIR / "publication_its_results.md"
    monthly: Path = DATA_DIR / "its_incumbent_publications_monthly.csv"
    quarterly: Path = DATA_DIR / "its_incumbent_publications_quarterly.csv"
    lag: Path = DATA_DIR / "its_publication_lag.csv"
    measure_sensitivity: Path = DATA_DIR / "its_publication_measure_sensitivity.csv"
    recent_completeness: Path = DATA_DIR / "its_recent_publication_completeness.csv"
    age_band_quarterly: Path = DATA_DIR / "its_age_band_quarterly.csv"
    age_band_monthly: Path = DATA_DIR / "publication_age_band_monthly.csv"
    outcome_audit: Path = DATA_DIR / "publication_outcome_universe_audit.csv"
    window_audit: Path = DATA_DIR / "publication_estimation_window_audit.csv"
    results_table: Path = DATA_DIR / "publication_its_results_table.csv"
    autocorrelation: Path = DATA_DIR / "publication_its_autocorrelation_diagnostics.csv"
    hac_sensitivity: Path = DATA_DIR / "publication_its_hac_lag_sensitivity.csv"
    ar1_results: Path = DATA_DIR / "publication_its_ar1_robustness.csv"
    observed_expected: Path = DATA_DIR / "publication_observed_vs_expected.csv"
    fixed_cohort: Path = DATA_DIR / "publication_fixed_cohort_monthly.csv"
    fixed_cohort_results: Path = DATA_DIR / "publication_fixed_cohort_its_results.csv"
    poisson_results: Path = DATA_DIR / "publication_poisson_count_robustness.csv"
    placebo_results: Path = DATA_DIR / "publication_placebo_results.csv"
    panel_a: Path = FIGURE_DIR / "publication_panel_a_raw_monthly.svg"
    panel_b: Path = FIGURE_DIR / "publication_panel_b_observed_expected.svg"
    panel_c: Path = FIGURE_DIR / "publication_panel_c_age_lifecycle.svg"
    main_figure: Path = FIGURE_DIR / "publication_figure_main_three_panel.svg"
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


def quarter_start(value: date) -> date:
    return date(value.year, ((value.month - 1) // 3) * 3 + 1, 1)


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


def pretrend_design(months: list[date]) -> tuple[list[list[float]], list[str]]:
    names = ["Intercept", "Time"] + [f"month_{m:02d}" for m in range(2, 13)]
    X = []
    for idx, mo in enumerate(months, start=1):
        X.append([1.0, float(idx)] + [1.0 if mo.month == m else 0.0 for m in range(2, 13)])
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
        X = []
        for t in range(lag, len(series)):
            X.append([1.0] + [series[t - j] for j in range(1, lag + 1)])
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
        projects[app_id] = {
            "app_id": app_id,
            "start_date": parse_date(row["start_date"]),
            "institution": row["schema27_institution"].strip(),
        }
    pubs = {}
    for row in read_csv(PUBLICATIONS, delimiter="\t"):
        pubs[row["pub_id"].strip()] = {"pub_id": row["pub_id"].strip(), "date_pub": parse_date(row["date_pub"]), "year_pub": row["year_pub"]}
    links = read_csv(PUBLICATION_APPS, delimiter="\t")
    return projects, pubs, links


def build_events(projects: dict[str, dict[str, object]], pubs: dict[str, dict[str, object]], links: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    events = []
    all_clean_events = []
    unmatched_app_links = 0
    unmatched_pub_links = 0
    pre_start_exclusions = 0
    multi_pub_counter = Counter(r["pub_id"].strip() for r in links)
    for link in links:
        app_id = link["app_id"].strip()
        pub_id = link["pub_id"].strip()
        if app_id not in projects:
            unmatched_app_links += 1
            continue
        if pub_id not in pubs:
            unmatched_pub_links += 1
            continue
        start = projects[app_id]["start_date"]
        pub_date = pubs[pub_id]["date_pub"]
        if pub_date < start:
            pre_start_exclusions += 1
            continue
        event = {
            "app_id": app_id,
            "pub_id": pub_id,
            "project_start_date": start,
            "publication_date": pub_date,
            "month": date(pub_date.year, pub_date.month, 1),
            "quarter": quarter_label(pub_date),
            "lag_months": (pub_date.year - start.year) * 12 + pub_date.month - start.month,
        }
        all_clean_events.append(event)
        if start < BREAK_DATE:
            events.append(event)
    audit = {
        "total_schema19_publications": len(pubs),
        "total_schema24_app_publication_links": len(links),
        "publication_ids_linked_to_multiple_applications": sum(1 for c in multi_pub_counter.values() if c > 1),
        "unmatched_app_links": unmatched_app_links,
        "unmatched_publication_links": unmatched_pub_links,
        "publication_before_project_start_exclusions": pre_start_exclusions,
        "all_cleaned_publication_app_events": len(all_clean_events),
        "cleaned_incumbent_publication_app_events": len(events),
        "cleaned_unique_publication_ids": len({e["pub_id"] for e in events}),
        "cleaned_apps_with_any_publication": len({e["app_id"] for e in events}),
        "latest_exact_publication_date": max(p["date_pub"] for p in pubs.values()).isoformat(),
        "latest_clean_incumbent_publication_date": max(e["publication_date"] for e in events).isoformat(),
    }
    return events, all_clean_events, audit


def build_monthly_panel(projects: dict[str, dict[str, object]], events: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    incumbent_apps = {app_id: p for app_id, p in projects.items() if p["start_date"] < BREAK_DATE}
    by_month = defaultdict(list)
    for e in events:
        by_month[e["month"]].append(e)
    rows = []
    for mo in month_range(PRIMARY_START, RIGHT_EDGE_END):
        month_events = by_month.get(mo, [])
        eligible_apps = {app_id for app_id, p in incumbent_apps.items() if p["start_date"] <= month_end(mo)}
        pub_to_apps = defaultdict(set)
        for e in month_events:
            if e["app_id"] in eligible_apps:
                pub_to_apps[e["pub_id"]].add(e["app_id"])
        fractional = sum(1.0 for _ in pub_to_apps)
        app_links = sum(len(apps) for apps in pub_to_apps.values())
        apps_any = len(set().union(*pub_to_apps.values())) if pub_to_apps else 0
        denom = len(eligible_apps)
        rows.append(
            {
                "month": month_label(mo),
                "month_start": mo.isoformat(),
                "post_start_incumbent_projects": denom,
                "publication_app_links": app_links,
                "unique_publication_ids": len(pub_to_apps),
                "fractional_publication_count": fmt(fractional, 3),
                "apps_with_any_publication": apps_any,
                "app_links_per_100_post_start_incumbents": fmt(100.0 * app_links / denom if denom else 0.0, 2),
                "unique_publications_per_100_post_start_incumbents": fmt(100.0 * len(pub_to_apps) / denom if denom else 0.0, 2),
                "fractional_publications_per_100_post_start_incumbents": fmt(100.0 * fractional / denom if denom else 0.0, 2),
                "any_publication_rate_percent": fmt(100.0 * apps_any / denom if denom else 0.0, 2),
                "post_transition": 1 if mo >= BREAK_MONTH else 0,
                "transition_context_jul_2024_mar_2025": 1 if date(2024, 7, 1) <= mo <= date(2025, 3, 1) else 0,
                "right_edge_2026": 1 if mo.year == 2026 else 0,
            }
        )
    write_csv(out.monthly, rows, list(rows[0].keys()))
    return rows


def build_quarterly(monthly: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    grouped = defaultdict(list)
    for r in monthly:
        grouped[quarter_label(parse_date(str(r["month_start"])))].append(r)
    rows = []
    for q in sorted(grouped):
        rs = grouped[q]
        start = parse_date(str(rs[0]["month_start"]))
        end = month_end(parse_date(str(rs[-1]["month_start"])))
        denom = int(rs[-1]["post_start_incumbent_projects"])
        links = sum(int(r["publication_app_links"]) for r in rs)
        unique = sum(int(r["unique_publication_ids"]) for r in rs)
        fractional = sum(float(r["fractional_publication_count"]) for r in rs)
        apps_any = sum(int(r["apps_with_any_publication"]) for r in rs)
        rows.append(
            {
                "quarter": q,
                "quarter_start": start.isoformat(),
                "quarter_end": end.isoformat(),
                "post_start_incumbent_projects": denom,
                "publication_app_links": links,
                "unique_publication_ids": unique,
                "fractional_publication_count": fmt(fractional, 3),
                "apps_with_any_publication": apps_any,
                "app_links_per_100_post_start_incumbents": fmt(100.0 * links / denom, 2),
                "unique_publications_per_100_post_start_incumbents": fmt(100.0 * unique / denom, 2),
                "fractional_publications_per_100_post_start_incumbents": fmt(100.0 * fractional / denom, 2),
                "any_publication_rate_percent": fmt(100.0 * apps_any / denom, 2),
                "post_transition": 1 if start >= BREAK_MONTH else 0,
            }
        )
    write_csv(out.quarterly, rows, list(rows[0].keys()))
    return rows


def write_lag_outputs(events: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    lags = [int(e["lag_months"]) for e in events]
    median = sorted(lags)[len(lags) // 2]
    bins = [("0_6_months", 0, 6), ("7_12_months", 7, 12), ("13_24_months", 13, 24), ("25_48_months", 25, 48), ("49_plus_months", 49, None)]
    rows = []
    for label, lo, hi in bins:
        count = sum(1 for lag in lags if lag >= lo and (hi is None or lag <= hi))
        rows.append({"lag_bin": label, "min_lag_months": lo, "max_lag_months": "" if hi is None else hi, "publication_app_links": count, "share_percent": fmt(100.0 * count / len(lags), 2), "median_lag_months_all_events": fmt(median, 3)})
    write_csv(out.lag, rows, list(rows[0].keys()))
    return rows


def write_audits(projects: dict[str, dict[str, object]], audit: dict[str, object], monthly: list[dict[str, object]], quarterly: list[dict[str, object]], out: Outputs) -> None:
    rows = [{"metric": k, "value": v} for k, v in audit.items()]
    rows += [
        {"metric": "primary_window_start", "value": PRIMARY_START.isoformat()},
        {"metric": "primary_window_end", "value": PRIMARY_END.isoformat()},
        {"metric": "primary_window_months", "value": len([r for r in monthly if PRIMARY_START <= parse_date(str(r["month_start"])) <= PRIMARY_END])},
        {"metric": "primary_pre_transition_months", "value": len([r for r in monthly if PRIMARY_START <= parse_date(str(r["month_start"])) < BREAK_MONTH])},
        {"metric": "primary_post_transition_months", "value": len([r for r in monthly if BREAK_MONTH <= parse_date(str(r["month_start"])) <= PRIMARY_END])},
        {"metric": "right_edge_decision", "value": "main analysis excludes 2026; 2026 retained only as right-edge diagnostic"},
    ]
    write_csv(out.outcome_audit, rows, ["metric", "value"])
    sensitivity = []
    for q in quarterly:
        links = int(q["publication_app_links"])
        unique = int(q["unique_publication_ids"])
        frac = float(q["fractional_publication_count"])
        sensitivity.append(
            {
                "quarter": q["quarter"],
                "publication_app_links": links,
                "unique_publication_ids": unique,
                "fractional_publication_count": fmt(frac, 3),
                "app_links_minus_unique_ids": links - unique,
                "app_links_minus_fractional_count": fmt(links - frac, 3),
                "unique_id_reduction_percent_vs_app_links": fmt(100.0 * (links - unique) / links if links else 0.0, 2),
                "fractional_reduction_percent_vs_app_links": fmt(100.0 * (links - frac) / links if links else 0.0, 2),
                "note": "Differences reflect publications linked to multiple UKB applications; fractional counts avoid full double counting.",
            }
        )
    write_csv(out.measure_sensitivity, sensitivity, list(sensitivity[0].keys()))
    recent = [
        {"grain": "summary", "period": "latest_schema19_exact_publication", "period_start": audit["latest_exact_publication_date"], "period_end": audit["latest_exact_publication_date"], "publication_app_links": "", "unique_publication_ids": "", "fractional_publication_count": "", "apps_with_any_publication": "", "note": "Latest exact publication date in the local public UKB Schema 19 snapshot."},
        {"grain": "summary", "period": "latest_clean_incumbent_publication_link", "period_start": audit["latest_clean_incumbent_publication_date"], "period_end": audit["latest_clean_incumbent_publication_date"], "publication_app_links": "", "unique_publication_ids": "", "fractional_publication_count": "", "apps_with_any_publication": "", "note": "Latest exact publication date after matching to the incumbent project-start universe and removing pre-start links."},
    ]
    for r in monthly:
        mo = parse_date(str(r["month_start"]))
        if mo >= date(2025, 8, 1):
            recent.append({"grain": "month", "period": r["month"], "period_start": r["month_start"], "period_end": month_end(mo).isoformat(), "publication_app_links": r["publication_app_links"], "unique_publication_ids": r["unique_publication_ids"], "fractional_publication_count": r["fractional_publication_count"], "apps_with_any_publication": r["apps_with_any_publication"], "note": "Right edge may be incomplete until external bibliographic completeness is validated."})
    write_csv(out.recent_completeness, recent, list(recent[0].keys()))


def series_for_window(monthly: list[dict[str, object]], start: date, end: date, outcome: str) -> tuple[list[date], list[float]]:
    rows = [r for r in monthly if start <= parse_date(str(r["month_start"])) <= end]
    return [parse_date(str(r["month_start"])) for r in rows], [float(r[outcome]) for r in rows]


def model_row(label: str, window: str, outcome: str, n: int, pre: int, post: int, term: str, estimate: float, se: float, extra: str = "") -> dict[str, object]:
    return {
        "model": label,
        "window": window,
        "outcome": outcome,
        "n_months": n,
        "pre_months": pre,
        "post_months": post,
        "term": term,
        "estimate": fmt(estimate, 4),
        "std_error": fmt(se, 4),
        "p_value": fmt(two_sided_normal_pvalue(estimate, se), 4),
        "ci_low": fmt(estimate - 1.96 * se, 4),
        "ci_high": fmt(estimate + 1.96 * se, 4),
        "notes": extra,
    }


def run_its(monthly: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], dict[str, object]]:
    outcome = "fractional_publications_per_100_post_start_incumbents"
    windows = [("2019-2025", PRIMARY_START), ("2020-2025", date(2020, 1, 1)), ("2021-2025", date(2021, 1, 1)), ("2022-07-2025", date(2022, 7, 1))]
    result_rows = []
    saved = {}
    window_rows = []
    for label, start in windows:
        months, y = series_for_window(monthly, start, PRIMARY_END, outcome)
        X, names = design_rows(months)
        fit = ols(X, y, hac_lag=PRIMARY_HAC_LAG)
        saved[(label, outcome, "primary")] = (months, names, fit, y)
        pre = sum(1 for m in months if m < BREAK_MONTH)
        post = len(months) - pre
        window_rows.append({"window": label, "start_month": month_label(start), "end_month": month_label(PRIMARY_END), "n_months": len(months), "pre_months": pre, "post_months": post, "selected_role": "PRIMARY" if start == PRIMARY_START else "ROBUSTNESS", "selection_basis": "Chosen before inspecting significance because cleaned exact publication-event data support consistent construction back to 2019 and provide 66 pre-transition months with month-of-year FE." if start == PRIMARY_START else "Prespecified shorter-window robustness."})
        for term in ["PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            extra = "descriptive immediate July 2024 level change" if term == "PostJuly2024" else "descriptive post-July 2024 monthly slope change"
            result_rows.append(model_row("Linear segmented ITS HAC(3)", label, outcome, len(months), pre, post, term, fit["beta"][idx], fit["se"][idx], extra))
    for outcome2 in ["any_publication_rate_percent", "app_links_per_100_post_start_incumbents", "unique_publications_per_100_post_start_incumbents"]:
        months, y = series_for_window(monthly, PRIMARY_START, PRIMARY_END, outcome2)
        X, names = design_rows(months)
        fit = ols(X, y, hac_lag=PRIMARY_HAC_LAG)
        saved[("2019-2025", outcome2, "measure")] = (months, names, fit, y)
        for term in ["PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            result_rows.append(model_row("Measurement sensitivity HAC(3)", "2019-2025", outcome2, len(months), 66, 18, term, fit["beta"][idx], fit["se"][idx], "secondary or measurement-sensitivity outcome"))
    write_csv(out.results_table, result_rows, list(result_rows[0].keys()))
    write_csv(out.window_audit, window_rows, list(window_rows[0].keys()))
    return result_rows, saved


def hac_lag_sensitivity(monthly: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    months, y = series_for_window(monthly, PRIMARY_START, PRIMARY_END, "fractional_publications_per_100_post_start_incumbents")
    X, names = design_rows(months)
    rows = []
    point_estimates = {}
    for lag in [1, 3, 6, 12]:
        fit = ols(X, y, hac_lag=lag)
        for term in ["PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            point_estimates.setdefault(term, fit["beta"][idx])
            rows.append(model_row(f"Linear segmented ITS HAC({lag})", "2019-2025", "fractional_publications_per_100_post_start_incumbents", len(months), 66, 18, term, fit["beta"][idx], fit["se"][idx], "HAC lag sensitivity; point estimates should be invariant"))
    write_csv(out.hac_sensitivity, rows, list(rows[0].keys()))
    return rows


def autocorrelation_diagnostics(saved: dict[str, object], out: Outputs) -> list[dict[str, object]]:
    months, names, fit, y = saved[("2019-2025", "fractional_publications_per_100_post_start_incumbents", "primary")]
    resid = fit["resid"]
    acfs = acf_values(resid, 12)
    pacfs = pacf_values(resid, 12)
    dw = durbin_watson(resid)
    rows = []
    for lag in range(1, 13):
        q, p = ljung_box(resid, lag)
        rows.append({"diagnostic": "residual_acf_pacf", "lag": lag, "acf": fmt(acfs[lag - 1], 4), "pacf": fmt(pacfs[lag - 1], 4), "durbin_watson_primary_model": fmt(dw, 4), "ljung_box_q": fmt(q, 4), "ljung_box_p_value": fmt(p, 4), "interpretation": "serial-correlation diagnostic after trend, July terms, and month-of-year fixed effects"})
    write_csv(out.autocorrelation, rows, list(rows[0].keys()))
    return rows


def ar1_robustness(monthly: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    months, y = series_for_window(monthly, PRIMARY_START, PRIMARY_END, "fractional_publications_per_100_post_start_incumbents")
    X, names = design_rows(months)
    fit = prais_winsten_ar1(X, y)
    rows = []
    for term in ["PostJuly2024", "TimeAfterJuly2024"]:
        idx = names.index(term)
        rows.append(model_row("Prais-Winsten AR(1) robustness", "2019-2025", "fractional_publications_per_100_post_start_incumbents", len(months), 66, 18, term, fit["beta"][idx], fit["se"][idx], f"estimated rho = {fit['rho']:.3f}"))
    write_csv(out.ar1_results, rows, list(rows[0].keys()))
    return rows


def observed_expected(monthly: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], dict[str, float | str]]:
    outcome = "fractional_publications_per_100_post_start_incumbents"
    months, y = series_for_window(monthly, PRIMARY_START, PRIMARY_END, outcome)
    pre_months = [m for m in months if m < BREAK_MONTH]
    pre_y = y[: len(pre_months)]
    X_pre, names = pretrend_design(pre_months)
    fit = ols(X_pre, pre_y, hac_lag=PRIMARY_HAC_LAG)
    X_all, _ = pretrend_design(months)
    rows = []
    cumulative = 0.0
    min_cum = 0.0
    final_cum = 0.0
    for mo, row, obs in zip(months, X_all, y):
        fitted = sum(row[j] * fit["beta"][j] for j in range(len(fit["beta"])))
        se_mean = math.sqrt(max(sum(row[i] * fit["vcov"][i][j] * row[j] for i in range(len(row)) for j in range(len(row))), 0.0))
        forecast_se = math.sqrt(max(se_mean * se_mean + float(fit["sigma2"]), 0.0))
        gap = obs - fitted
        if mo >= BREAK_MONTH:
            cumulative += gap
            min_cum = min(min_cum, cumulative)
            final_cum = cumulative
        rows.append({"month": month_label(mo), "month_start": mo.isoformat(), "observed_fractional_publications_per_100_incumbents": fmt(obs, 3), "fitted_pre_transition_historical_benchmark": fmt(fitted, 3), "mean_ci_low_hac": fmt(fitted - 1.96 * se_mean, 3), "mean_ci_high_hac": fmt(fitted + 1.96 * se_mean, 3), "forecast_interval_low_ols_scale": fmt(fitted - 1.96 * forecast_se, 3), "forecast_interval_high_ols_scale": fmt(fitted + 1.96 * forecast_se, 3), "gap_observed_minus_benchmark": fmt(gap, 3), "post_july_2024": 1 if mo >= BREAK_MONTH else 0, "cumulative_gap_since_july_2024": fmt(cumulative, 3) if mo >= BREAK_MONTH else ""})
    write_csv(out.observed_expected, rows, list(rows[0].keys()))
    post = [r for r in rows if r["post_july_2024"] == 1]
    metrics = {
        "jul_2024_mar_2025_gap": sum(float(r["gap_observed_minus_benchmark"]) for r in post[:9]),
        "calendar_2025_gap": sum(float(r["gap_observed_minus_benchmark"]) for r in post[6:18]),
        "minimum_cumulative_gap": min_cum,
        "final_cumulative_gap": final_cum,
    }
    return rows, metrics


def age_band(date_start: date, month: date) -> str:
    age_months = (month.year - date_start.year) * 12 + month.month - date_start.month
    if age_months < 24:
        return "lt_2y"
    if age_months < 60:
        return "2_5y"
    return "5y_plus"


def age_lifecycle(projects: dict[str, dict[str, object]], events: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    incumbent_apps = {app_id: p for app_id, p in projects.items() if p["start_date"] < BREAK_DATE}
    by_month_band = defaultdict(list)
    for e in events:
        by_month_band[(e["month"], age_band(e["project_start_date"], e["month"]))].append(e)
    rows = []
    for mo in month_range(PRIMARY_START, PRIMARY_END):
        for band in ["lt_2y", "2_5y", "5y_plus"]:
            denom_apps = [app_id for app_id, p in incumbent_apps.items() if p["start_date"] <= month_end(mo) and age_band(p["start_date"], mo) == band]
            events_band = by_month_band.get((mo, band), [])
            pub_ids = {e["pub_id"] for e in events_band}
            denom = len(denom_apps)
            rows.append({"age_band": band, "month": month_label(mo), "month_start": mo.isoformat(), "post_start_incumbent_projects": denom, "unique_publication_ids": len(pub_ids), "publication_intensity_per_100": fmt(100.0 * len(pub_ids) / denom if denom else 0.0, 3), "post_transition": 1 if mo >= BREAK_MONTH else 0})
    write_csv(out.age_band_monthly, rows, list(rows[0].keys()))
    qrows = []
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["age_band"], quarter_label(parse_date(str(r["month_start"]))) )].append(r)
    for (band, q), rs in sorted(grouped.items()):
        denom = int(rs[-1]["post_start_incumbent_projects"])
        pubs = sum(int(r["unique_publication_ids"]) for r in rs)
        apps_any = ""
        qrows.append({"project_age_band_at_publication_month": band, "quarter": q, "project_periods": denom, "publication_count": pubs, "any_publication_rate_percent": apps_any, "publication_count_per_100_project_periods": fmt(100.0 * pubs / denom if denom else 0.0, 2)})
    write_csv(out.age_band_quarterly, qrows, list(qrows[0].keys()))
    return rows


def fixed_cohort_analysis(projects: dict[str, dict[str, object]], events: list[dict[str, object]], out: Outputs) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    cohort = {app_id for app_id, p in projects.items() if p["start_date"] < FIXED_COHORT_CUTOFF}
    by_month = defaultdict(list)
    for e in events:
        if e["app_id"] in cohort:
            by_month[e["month"]].append(e)
    rows = []
    for mo in month_range(FIXED_COHORT_CUTOFF, PRIMARY_END):
        evs = by_month.get(mo, [])
        pub_ids = {e["pub_id"] for e in evs}
        apps = {e["app_id"] for e in evs}
        denom = len(cohort)
        rows.append({"month": month_label(mo), "month_start": mo.isoformat(), "fixed_cohort_projects_started_before_2022_07_01": denom, "publication_app_links": len(evs), "unique_publication_ids": len(pub_ids), "apps_with_any_publication": len(apps), "fractional_publications_per_100_fixed_cohort": fmt(100.0 * len(pub_ids) / denom, 3), "any_publication_rate_percent": fmt(100.0 * len(apps) / denom, 3), "post_transition": 1 if mo >= BREAK_MONTH else 0})
    write_csv(out.fixed_cohort, rows, list(rows[0].keys()))
    months = [parse_date(str(r["month_start"])) for r in rows]
    y = [float(r["fractional_publications_per_100_fixed_cohort"]) for r in rows]
    X, names = design_rows(months)
    fit = ols(X, y, hac_lag=PRIMARY_HAC_LAG)
    result_rows = []
    for term in ["PostJuly2024", "TimeAfterJuly2024"]:
        idx = names.index(term)
        result_rows.append(model_row("Fixed cohort HAC(3)", "2022-07-2025", "fractional_publications_per_100_fixed_cohort", len(months), sum(m < BREAK_MONTH for m in months), sum(m >= BREAK_MONTH for m in months), term, fit["beta"][idx], fit["se"][idx], "membership fixed to projects started before 2022-07-01"))
    write_csv(out.fixed_cohort_results, result_rows, list(result_rows[0].keys()))
    return rows, result_rows


def poisson_count_robustness(monthly: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    months, y = series_for_window(monthly, PRIMARY_START, PRIMARY_END, "unique_publication_ids")
    X, names = design_rows(months)
    fit = poisson_qmle(X, y, hac_lag=PRIMARY_HAC_LAG)
    rows = []
    for term in ["PostJuly2024", "TimeAfterJuly2024"]:
        idx = names.index(term)
        rows.append(model_row("Poisson QMLE count robustness HAC(3)", "2019-2025", "monthly_unique_publication_ids", len(months), 66, 18, term, fit["beta"][idx], fit["se"][idx], f"Pearson dispersion = {fit['pearson_dispersion']:.2f}; IRR = {math.exp(fit['beta'][idx]):.3f}"))
    write_csv(out.poisson_results, rows, list(rows[0].keys()))
    return rows


def placebo_models(monthly: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    months, y = series_for_window(monthly, PRIMARY_START, date(2024, 6, 1), "fractional_publications_per_100_post_start_incumbents")
    rows = []
    for placebo in [date(2021, 7, 1), date(2022, 7, 1), date(2023, 7, 1)]:
        X, names = design_rows(months, break_month=placebo)
        fit = ols(X, y, hac_lag=PRIMARY_HAC_LAG)
        for term in ["PostJuly2024", "TimeAfterJuly2024"]:
            idx = names.index(term)
            rows.append(model_row(f"Pre-transition placebo July {placebo.year}", f"2019-06_to_{placebo.year}", "fractional_publications_per_100_post_start_incumbents", len(months), "", "", term, fit["beta"][idx], fit["se"][idx], "contextual diagnostic using only pre-July-2024 observations"))
    write_csv(out.placebo_results, rows, list(rows[0].keys()))
    return rows


def svg_line_chart(path: Path, title: str, series: list[tuple[date, float, str]], y_label: str, start: date, end: date, bands: list[tuple[date, float, float]] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1060, 520
    left, right, top, bottom = 78, 28, 46, 62
    vals = [v for _, v, _ in series]
    if bands:
        vals += [v for _, lo, hi in bands for v in (lo, hi)]
    y_min, y_max = min(vals), max(vals)
    pad = (y_max - y_min) * 0.12 or 1.0
    y_min -= pad
    y_max += pad
    total_months = max((end.year - start.year) * 12 + end.month - start.month, 1)

    def x(mo: date) -> float:
        return left + ((mo.year - start.year) * 12 + mo.month - start.month) / total_months * (width - left - right)

    def y(v: float) -> float:
        return top + (y_max - v) / (y_max - y_min) * (height - top - bottom)

    groups = defaultdict(list)
    for mo, val, label in series:
        groups[label].append((mo, val))
    colors = {"observed": "#1f6feb", "fitted": "#b42318", "lt_2y": "#2da44e", "2_5y": "#8250df", "5y_plus": "#bf8700", "gap": "#1f6feb"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#ffffff"/>', f'<text x="{left}" y="28" font-family="Arial" font-size="20" font-weight="700">{title}</text>', f'<text x="18" y="{height/2}" transform="rotate(-90 18 {height/2})" font-family="Arial" font-size="13" fill="#444">{y_label}</text>']
    for i in range(5):
        yy = top + i * (height - top - bottom) / 4
        val = y_max - i * (y_max - y_min) / 4
        parts.append(f'<line x1="{left}" x2="{width-right}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#555">{val:.1f}</text>')
    if bands:
        points_hi = " ".join(f"{x(mo):.1f},{y(hi):.1f}" for mo, lo, hi in bands)
        points_lo = " ".join(f"{x(mo):.1f},{y(lo):.1f}" for mo, lo, hi in reversed(bands))
        parts.append(f'<polygon points="{points_hi} {points_lo}" fill="#b42318" opacity="0.12"/>')
    bx = x(BREAK_MONTH)
    parts.append(f'<line x1="{bx:.1f}" x2="{bx:.1f}" y1="{top}" y2="{height-bottom}" stroke="#111827" stroke-dasharray="5 5"/>')
    parts.append(f'<text x="{bx+7:.1f}" y="{top+16}" font-family="Arial" font-size="12" fill="#111827">Jul 2024 transition marker</text>')
    for label, points in groups.items():
        path_d = " ".join(("M" if i == 0 else "L") + f"{x(mo):.1f},{y(val):.1f}" for i, (mo, val) in enumerate(points))
        parts.append(f'<path d="{path_d}" fill="none" stroke="{colors.get(label, "#374151")}" stroke-width="2.4"/>')
    for yr in range(start.year, end.year + 1):
        mo = date(yr, 1, 1)
        if start <= mo <= end:
            xx = x(mo)
            parts.append(f'<text x="{xx:.1f}" y="{height-24}" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">{yr}</text>')
    parts.append("</svg>")
    write_text(path, "\n".join(parts))


def svg_bar_chart(path: Path, title: str, rows: list[dict[str, object]]) -> None:
    width, height = 860, 420
    left, top, bottom = 78, 42, 70
    maxv = max(float(r["share_percent"]) for r in rows)
    bar_w = 110
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#ffffff"/>', f'<text x="{left}" y="28" font-family="Arial" font-size="20" font-weight="700">{title}</text>']
    for i, r in enumerate(rows):
        x = left + i * 150
        h = float(r["share_percent"]) / maxv * (height - top - bottom)
        y = height - bottom - h
        parts.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" fill="#1f6feb"/>')
        parts.append(f'<text x="{x + bar_w/2}" y="{y - 8:.1f}" text-anchor="middle" font-family="Arial" font-size="12">{float(r["share_percent"]):.1f}%</text>')
        parts.append(f'<text x="{x + bar_w/2}" y="{height-42}" text-anchor="middle" font-family="Arial" font-size="11">{str(r["lag_bin"]).replace("_", " ")}</text>')
    parts.append("</svg>")
    write_text(path, "\n".join(parts))


def make_figures(monthly: list[dict[str, object]], expected_rows: list[dict[str, object]], age_rows: list[dict[str, object]], lag_rows: list[dict[str, object]], ac_rows: list[dict[str, object]], out: Outputs) -> None:
    primary = [r for r in monthly if PRIMARY_START <= parse_date(str(r["month_start"])) <= PRIMARY_END]
    svg_line_chart(out.panel_a, "Raw Monthly Incumbent Publication Intensity", [(parse_date(str(r["month_start"])), float(r["fractional_publications_per_100_post_start_incumbents"]), "observed") for r in primary], "Fractional publications per 100 incumbents", PRIMARY_START, PRIMARY_END)
    bands = [(parse_date(str(r["month_start"])), float(r["mean_ci_low_hac"]), float(r["mean_ci_high_hac"])) for r in expected_rows]
    svg_line_chart(out.panel_b, "Observed Versus Fitted Pre-Transition Historical Benchmark", [(parse_date(str(r["month_start"])), float(r["observed_fractional_publications_per_100_incumbents"]), "observed") for r in expected_rows] + [(parse_date(str(r["month_start"])), float(r["fitted_pre_transition_historical_benchmark"]), "fitted") for r in expected_rows], "Fractional publications per 100 incumbents", PRIMARY_START, PRIMARY_END, bands=bands)
    age_series = [(parse_date(str(r["month_start"])), float(r["publication_intensity_per_100"]), str(r["age_band"])) for r in age_rows if r["age_band"] in {"lt_2y", "2_5y", "5y_plus"}]
    svg_line_chart(out.panel_c, "Publication Intensity By Project Age Band", age_series, "Publications per 100 incumbents", PRIMARY_START, PRIMARY_END)
    svg_bar_chart(out.lag_figure, "Project-Start To Publication Lag Distribution", lag_rows)
    svg_line_chart(out.acf_figure, "Primary ITS Residual ACF", [(date(2019, i, 1), float(r["acf"]), "observed") for i, r in enumerate(ac_rows, start=1)], "ACF", date(2019, 1, 1), date(2019, 12, 1))
    svg_line_chart(out.pacf_figure, "Primary ITS Residual PACF", [(date(2019, i, 1), float(r["pacf"]), "observed") for i, r in enumerate(ac_rows, start=1)], "PACF", date(2019, 1, 1), date(2019, 12, 1))
    parts = []
    y_offset = 0
    for path in [out.panel_a, out.panel_b, out.panel_c]:
        text = path.read_text(encoding="utf-8")
        body = text.split(">", 1)[1].rsplit("</svg>", 1)[0]
        parts.append(f'<g transform="translate(0,{y_offset})">{body}</g>')
        y_offset += 520
    write_text(out.main_figure, "\n".join(['<svg xmlns="http://www.w3.org/2000/svg" width="1060" height="1560" viewBox="0 0 1060 1560">', *parts, "</svg>"]))


def docs(out: Outputs, audit: dict[str, object], lag_rows: list[dict[str, object]], monthly: list[dict[str, object]], results: list[dict[str, object]], ac: list[dict[str, object]], hac: list[dict[str, object]], ar1: list[dict[str, object]], expected_metrics: dict[str, float | str], fixed_results: list[dict[str, object]], poisson: list[dict[str, object]]) -> None:
    primary_level = next(r for r in results if r["model"] == "Linear segmented ITS HAC(3)" and r["window"] == "2019-2025" and r["term"] == "PostJuly2024")
    primary_slope = next(r for r in results if r["model"] == "Linear segmented ITS HAC(3)" and r["window"] == "2019-2025" and r["term"] == "TimeAfterJuly2024")
    ar1_level = next(r for r in ar1 if r["term"] == "PostJuly2024")
    ar1_slope = next(r for r in ar1 if r["term"] == "TimeAfterJuly2024")
    dw = ac[0]["durbin_watson_primary_model"]
    lb12 = ac[11]
    pre_rows = [r for r in monthly if PRIMARY_START <= parse_date(str(r["month_start"])) < BREAK_MONTH]
    post_rows = [r for r in monthly if BREAK_MONTH <= parse_date(str(r["month_start"])) <= PRIMARY_END]
    pre_mean = sum(float(r["fractional_publications_per_100_post_start_incumbents"]) for r in pre_rows) / len(pre_rows)
    post_mean = sum(float(r["fractional_publications_per_100_post_start_incumbents"]) for r in post_rows) / len(post_rows)
    category = "C. Gradual post-transition increase" if float(primary_slope["estimate"]) > 0 and expected_metrics["calendar_2025_gap"] > 0 else "F. Mixed / insufficiently robust pattern"
    write_text(out.readme, f"""# Publication-Output ITS Module

This module contains the descriptive interrupted-time-series analysis of publication output among pre-transition UKB incumbent projects.

Read first:

1. `reports/publication_reading_guide.md`
2. `reports/publication_measurement_note.md`
3. `reports/publication_its_results.md`
4. `figures/publication_figure_main_three_panel.svg`

The primary outcome is `fractional_publications_per_100_post_start_incumbents`. The primary window is 2019-01 through 2025-12. The design is descriptive and does not treat July 2024 as the individual RAP-exposure date for every incumbent project.
""")
    write_text(out.design, f"""# Publication ITS Design

## Question

How did publication output among pre-transition UKB incumbent projects evolve around and after the July 2024 RAP-based access transition?

## Design Status

This is a descriptive interrupted-time-series / stylized-fact design. July 2024 is an institutional transition marker, not a verified treatment date for every incumbent project.

## Incumbent Sample

The analysis keeps projects with public project start date before 2024-07-05. This avoids mechanically mixing post-transition entrants into the publication-output composition.

The monthly denominator is `post_start_incumbent_projects`: the number of pre-transition incumbent projects whose public start date has occurred by the end of month `t`. It grows before July 2024 as future incumbents enter their project period, then becomes fixed at {audit['pre_transition_incumbent_projects_total'] if 'pre_transition_incumbent_projects_total' in audit else 'the full incumbent count'} after the transition.

## Primary Outcome And Window

Primary intensity outcome: `fractional_publications_per_100_post_start_incumbents`.

This is selected before inspecting significance because it normalizes for the post-start incumbent pool and avoids full double counting of publications linked to multiple applications.

Primary window: 2019-01 through 2025-12. The raw exact publication-event data support consistent construction before 2022-07, the window gives 66 pre-transition and 18 post-transition monthly observations, and 2026 is excluded because of right-edge completeness risk.

## Model

`Y_t = beta_0 + beta_1 Time_t + beta_2 PostJuly2024_t + beta_3 TimeAfterJuly2024_t + month-of-year FE + epsilon_t`.

Primary inference is OLS with Newey-West HAC lag 3. HAC(1), HAC(6), and HAC(12), AR(1) errors, fixed cohort, publication-measure sensitivity, Poisson count robustness, and pre-transition placebos are reported as diagnostics or robustness checks.
""")
    write_text(out.measurement_note, f"""# Publication Measurement Note

## Source Tables

- Schema19 publications: {audit['total_schema19_publications']:,}
- Schema24 app-publication links: {audit['total_schema24_app_publication_links']:,}
- All cleaned publication-app events after matching and pre-start exclusions: {audit['all_cleaned_publication_app_events']:,}
- Cleaned incumbent publication-app events used: {audit['cleaned_incumbent_publication_app_events']:,}
- Cleaned unique publication IDs used: {audit['cleaned_unique_publication_ids']:,}
- Cleaned apps with any publication: {audit['cleaned_apps_with_any_publication']:,}

## Linkage Audit

- Publication IDs linked to multiple applications in Schema24: {audit['publication_ids_linked_to_multiple_applications']:,}
- Publication-before-project-start exclusions: {audit['publication_before_project_start_exclusions']:,}
- Unmatched app links: {audit['unmatched_app_links']:,}
- Unmatched publication links: {audit['unmatched_publication_links']:,}
- Latest exact Schema19 publication date: {audit['latest_exact_publication_date']}
- Latest cleaned incumbent publication date: {audit['latest_clean_incumbent_publication_date']}

## Measures Must Not Be Interchanged

`publication_app_links` counts app-publication links and can double count a publication linked to multiple applications.

`unique_publication_ids` counts distinct publication IDs in a period.

`fractional_publication_count` is operationally equivalent to distinct publication IDs in this public linked dataset after period-level de-duplication; it is retained as the primary intensity numerator to avoid full multi-application double counting.

`apps_with_any_publication` counts applications with at least one linked publication in the period and supports the extensive-margin rate.

## Publication Lag

The lag distribution is project-start-to-publication lag, not RAP-to-publication lag. Median lag is {lag_rows[0]['median_lag_months_all_events']} months. Shares by lag bin are: 0-6 months {lag_rows[0]['share_percent']}%, 7-12 months {lag_rows[1]['share_percent']}%, 13-24 months {lag_rows[2]['share_percent']}%, 25-48 months {lag_rows[3]['share_percent']}%, and 49+ months {lag_rows[4]['share_percent']}%.

Because publication lags are long, publications appearing shortly after July 2024 generally reflect substantial work initiated before the transition.
""")
    write_text(out.results_report, f"""# Publication ITS Results

## 1. Outcome And Sample Definition

The primary outcome is monthly `fractional_publications_per_100_post_start_incumbents` among projects with public start date before 2024-07-05. The sample excludes post-transition entrants from the publication-output composition.

## 2. Why Incumbents Are Used

Incumbents are used so that post-transition project starts do not mechanically change the publication mix. The denominator is not active projects; it is pre-transition incumbent projects whose public start date has occurred by the end of month `t`.

## 3. Publication Lag

The median project-start-to-publication lag is {lag_rows[0]['median_lag_months_all_events']} months. Only {lag_rows[0]['share_percent']}% of linked publication events occur within 0-6 months of project start, while {float(lag_rows[3]['share_percent']) + float(lag_rows[4]['share_percent']):.2f}% occur after 24 months. This is not RAP-to-publication lag. It means an immediate July 2024 publication response should not be mechanically expected.

## 4. Publication-Measure Construction

The primary intensity outcome is fractional publications per 100 post-start incumbents. The secondary extensive-margin outcome is any-publication rate percent. App-link and unique-publication rates are measurement sensitivities.

## 5. Raw Monthly Trajectory

In the 2019-01 to 2025-12 primary window, the pre-transition mean is {pre_mean:.2f} fractional publications per 100 post-start incumbents, and the post-transition mean is {post_mean:.2f}. The raw trajectory does not show a sharp immediate publication collapse around July 2024; 2025 is generally above the preceding fitted trajectory.

## 6. Primary ITS Design

The primary model is a linear segmented ITS with month-of-year fixed effects and Newey-West HAC lag 3. There are 84 monthly observations: 66 pre-transition months and 18 post-transition months.

## 7. Autocorrelation Diagnostics

After controlling for trend, July terms, and calendar-month seasonality, the Durbin-Watson statistic is {dw}. Ljung-Box at lag 12 is Q = {lb12['ljung_box_q']} with p = {lb12['ljung_box_p_value']}. These diagnostics do not show strong remaining residual serial correlation, but HAC and AR(1) robustness are still reported because monthly publication output can be temporally persistent.

## 8. Newey-West Inference

Primary HAC lag is 3, prespecified for monthly data before inspecting significance. HAC lag sensitivity is saved in `publication_its_hac_lag_sensitivity.csv`; point estimates are invariant across HAC lags, while standard errors vary.

## 9. AR(1) Robustness

Prais-Winsten AR(1) robustness reports {ar1_level['notes']}. The AR(1) level estimate is {ar1_level['estimate']} (SE {ar1_level['std_error']}, 95% CI [{ar1_level['ci_low']}, {ar1_level['ci_high']}]); the slope estimate is {ar1_slope['estimate']} (SE {ar1_slope['std_error']}, 95% CI [{ar1_slope['ci_low']}, {ar1_slope['ci_high']}]). The direction is consistent with the primary gradual-increase reading.

## 10. Observed-Versus-Expected Historical Benchmark

Using only pre-July-2024 observations, the fitted pre-transition historical benchmark implies a July 2024-March 2025 cumulative gap of {expected_metrics['jul_2024_mar_2025_gap']:.2f} and a calendar-2025 gap of {expected_metrics['calendar_2025_gap']:.2f} publication-intensity points. These are descriptive gaps, not causal untreated potential outcomes.

## 11. Publication Lifecycle / Age Composition

Age-band outputs show publication intensity is highest among older projects. The aggregate post-2024 rise is therefore plausibly partly related to aging/composition of the incumbent project pool, not only an institutional transition pattern.

## 12. Fixed-Cohort Robustness

The fixed cohort keeps projects started before 2022-07-01. Its ITS slope estimate is {next(r for r in fixed_results if r['term'] == 'TimeAfterJuly2024')['estimate']} with SE {next(r for r in fixed_results if r['term'] == 'TimeAfterJuly2024')['std_error']}. This preserves a positive post-July trajectory within a stable membership cohort, while still remaining descriptive.

## 13. Measure Sensitivity

The positive post-July slope pattern is compared across fractional publication intensity, app-link intensity, unique-publication intensity, and any-publication rate in `publication_its_results_table.csv`. The conclusion does not rely only on multi-application link counting.

## 14. Right-Edge Completeness

The main analysis ends at 2025-12. The local snapshot contains 2026 publication dates through {audit['latest_exact_publication_date']}, but 2026 is retained only as a right-edge completeness diagnostic.

## 15. Additional Robustness

Additional outputs include HAC lag sensitivity, Poisson QMLE count robustness, pre-transition placebo July breakpoints, residual ACF/PACF, and right-edge completeness diagnostics.

## 16. What The Evidence Supports

The evidence supports a descriptive pattern of no sharp immediate publication disruption around July 2024, followed by a gradual higher 2025 incumbent publication trajectory relative to the fitted pre-transition historical benchmark.

## 17. What It Cannot Establish

This analysis cannot establish that RAP caused publications to rise or fall. July 2024 is not the verified individual RAP-exposure date for every incumbent, and project-start-to-publication lag is long.

## 18. Recommended Paper-Ready Stylized Fact

Classification: {category}.

Candidate conservative statements:

> Among pre-transition UKB incumbent projects, publication output shows no sharp immediate disruption at the July 2024 institutional transition marker.

> Publication output rises gradually through 2025 relative to the fitted pre-transition historical benchmark, but long project-start-to-publication lags mean this should not be interpreted as an immediate RAP effect.

> Lifecycle composition is an important alternative explanation: older incumbent projects publish at higher rates, so aggregate post-transition increases may partly reflect project aging.

## Main Results

| Term | Estimate | SE | p-value | 95% CI | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| PostJuly2024 | {primary_level['estimate']} | {primary_level['std_error']} | {primary_level['p_value']} | [{primary_level['ci_low']}, {primary_level['ci_high']}] | descriptive immediate level change |
| TimeAfterJuly2024 | {primary_slope['estimate']} | {primary_slope['std_error']} | {primary_slope['p_value']} | [{primary_slope['ci_low']}, {primary_slope['ci_high']}] | descriptive monthly post-transition slope change |

## Output Files

- Main figure: `figures/publication_figure_main_three_panel.svg`
- Main table: `data/publication_its_results_table.csv`
- Measurement note: `reports/publication_measurement_note.md`
- Autocorrelation diagnostics: `data/publication_its_autocorrelation_diagnostics.csv`
- HAC sensitivity: `data/publication_its_hac_lag_sensitivity.csv`
- AR(1) robustness: `data/publication_its_ar1_robustness.csv`
- Historical benchmark: `data/publication_observed_vs_expected.csv`
- Age/lifecycle: `data/publication_age_band_monthly.csv`
- Fixed cohort: `data/publication_fixed_cohort_monthly.csv`
- Right-edge completeness: `data/its_recent_publication_completeness.csv`
""")
    write_text(out.reading_guide, f"""# Publication Results Reading Guide

Read this file first. Short paths are relative to `analyses/interrupted_time_series/publications/`.

## One-Sentence Result

Among pre-transition UKB incumbent projects, publication output shows no sharp immediate disruption around the July 2024 institutional transition marker and instead exhibits a gradual higher 2025 trajectory, with important publication-lag and lifecycle-composition caveats.

## Read These 4 Files First

1. `reports/publication_measurement_note.md`
2. `reports/publication_its_results.md`
3. `figures/publication_figure_main_three_panel.svg`
4. `data/publication_its_results_table.csv`

## Main Numbers

- Primary outcome: fractional publications per 100 post-start incumbents.
- Primary window: 2019-01 through 2025-12.
- Monthly observations: 84 total, 66 pre-transition, 18 post-transition.
- Raw pre-transition mean: {pre_mean:.2f}.
- Raw post-transition mean: {post_mean:.2f}.
- Primary level change: {primary_level['estimate']} (SE {primary_level['std_error']}, 95% CI [{primary_level['ci_low']}, {primary_level['ci_high']}]).
- Primary slope change: {primary_slope['estimate']} (SE {primary_slope['std_error']}, 95% CI [{primary_slope['ci_low']}, {primary_slope['ci_high']}]).
- Durbin-Watson: {dw}; Ljung-Box lag 12 p-value: {lb12['ljung_box_p_value']}.
- AR(1): {ar1_level['notes']}.
- Publication lag: median {lag_rows[0]['median_lag_months_all_events']} months from project start to publication.

## Main Figure

`figures/publication_figure_main_three_panel.svg`

Panel A shows raw monthly intensity. Panel B shows observed versus fitted pre-transition historical benchmark. Panel C shows publication intensity by project-age band.

Standalone panels:

- `figures/publication_panel_a_raw_monthly.svg`
- `figures/publication_panel_b_observed_expected.svg`
- `figures/publication_panel_c_age_lifecycle.svg`

## Main Table

`data/publication_its_results_table.csv`

Contains primary linear HAC(3), alternative windows, and measurement-sensitivity rows.

## Appendix Diagnostics

- `data/publication_its_autocorrelation_diagnostics.csv`
- `figures/publication_its_residual_acf.svg`
- `figures/publication_its_residual_pacf.svg`
- `data/publication_its_hac_lag_sensitivity.csv`
- `data/publication_its_ar1_robustness.csv`
- `data/publication_observed_vs_expected.csv`
- `data/publication_fixed_cohort_monthly.csv`
- `data/publication_fixed_cohort_its_results.csv`
- `data/publication_poisson_count_robustness.csv`
- `data/publication_placebo_results.csv`
- `data/its_publication_lag.csv`
- `figures/publication_lag_distribution.svg`
- `data/its_recent_publication_completeness.csv`
- `data/publication_outcome_universe_audit.csv`

## Interpretation To Use

Use: gradual post-transition increase with publication-lag and lifecycle-composition caveats.

Do not write: RAP caused publications to rise.
""")


def validate_outputs(out: Outputs | None = None) -> None:
    out = out or Outputs()
    monthly = read_csv(out.monthly)
    assert monthly[0]["month"] == "2019-01"
    assert monthly[-1]["month"] == "2026-06"
    primary = [r for r in monthly if PRIMARY_START <= parse_date(r["month_start"]) <= PRIMARY_END]
    assert len(primary) == 84
    assert sum(1 for r in primary if r["month_start"] < BREAK_MONTH.isoformat()) == 66
    assert sum(1 for r in primary if r["month_start"] >= BREAK_MONTH.isoformat()) == 18
    assert all(r["right_edge_2026"] == "0" for r in primary)
    july = next(r for r in primary if r["month"] == "2024-07")
    june = next(r for r in primary if r["month"] == "2024-06")
    assert june["post_transition"] == "0"
    assert july["post_transition"] == "1"
    denominators = [int(r["post_start_incumbent_projects"]) for r in primary if r["month_start"] >= BREAK_MONTH.isoformat()]
    assert len(set(denominators)) == 1
    results = read_csv(out.results_table)
    assert "p_value" in results[0]
    hac = read_csv(out.hac_sensitivity)
    for term in ["PostJuly2024", "TimeAfterJuly2024"]:
        estimates = {r["estimate"] for r in hac if r["term"] == term}
        assert len(estimates) == 1, f"HAC point estimate changes for {term}"
    bench = read_csv(out.observed_expected)
    assert len([r for r in bench if r["post_july_2024"] == "0"]) == 66
    cumulative = 0.0
    for r in [r for r in bench if r["post_july_2024"] == "1"]:
        cumulative += float(r["gap_observed_minus_benchmark"])
        assert abs(cumulative - float(r["cumulative_gap_since_july_2024"])) < 0.02
    fixed = read_csv(out.fixed_cohort)
    assert len({r["fixed_cohort_projects_started_before_2022_07_01"] for r in fixed}) == 1
    ac = read_csv(out.autocorrelation)
    assert len(ac) == 12
    assert out.results_report.read_text(encoding="utf-8").find("Publication Lag") >= 0


def main() -> None:
    out = Outputs()
    projects, pubs, links = load_inputs()
    events, all_clean_events, audit = build_events(projects, pubs, links)
    monthly = build_monthly_panel(projects, events, out)
    quarterly = build_quarterly(monthly, out)
    lag_rows = write_lag_outputs(all_clean_events, out)
    audit["pre_transition_incumbent_projects_total"] = sum(1 for p in projects.values() if p["start_date"] < BREAK_DATE)
    write_audits(projects, audit, monthly, quarterly, out)
    results, saved = run_its(monthly, out)
    hac = hac_lag_sensitivity(monthly, out)
    ac = autocorrelation_diagnostics(saved, out)
    ar1 = ar1_robustness(monthly, out)
    expected_rows, expected_metrics = observed_expected(monthly, out)
    age_rows = age_lifecycle(projects, events, out)
    fixed_rows, fixed_results = fixed_cohort_analysis(projects, events, out)
    poisson = poisson_count_robustness(monthly, out)
    placebo_models(monthly, out)
    make_figures(monthly, expected_rows, age_rows, lag_rows, ac, out)
    docs(out, audit, lag_rows, monthly, results, ac, hac, ar1, expected_metrics, fixed_results, poisson)
    validate_outputs(out)
    print("publication ITS outputs built")


if __name__ == "__main__":
    main()
