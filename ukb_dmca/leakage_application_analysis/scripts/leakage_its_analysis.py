#!/usr/bin/env python3
"""Build application-start-cohort leakage ITS outputs.

The analysis unit is the UK Biobank application. DMCA records are used only as
ex post public evidence for linking an application to a targeted repository
lineage/family; DMCA notice dates are never used as the application timing
variable.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


def find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "ukb_dmca").is_dir() and (parent / "data").is_dir():
            return parent
    raise RuntimeError("Could not find repository root containing ukb_dmca/ and data/.")


ROOT = find_repo_root()
PACKAGE = ROOT / "ukb_dmca" / "leakage_application_analysis"
DATA_DIR = PACKAGE / "data"
FIGURE_DIR = PACKAGE / "figures"
REPORT_DIR = PACKAGE / "reports"
TABLE_DIR = PACKAGE / "tables"

STAGE2_MASTER = ROOT / "data" / "intermediate" / "stage2_universe" / "stage2_master_projects.csv"
START_DATES = ROOT / "data" / "intermediate" / "start_date_matching" / "stage2_5_app_start_dates.csv"
ARCHIVED_DMCA_CROSSWALK = (
    ROOT
    / "analyses"
    / "did_archive"
    / "data"
    / "intermediate"
    / "fast_pipeline"
    / "stage4_fast_dmca_crosswalk.csv"
)
DMCA_LINEAGES = ROOT / "ukb_dmca" / "ukb_dmca_lineages.csv"
DMCA_REPOSITORIES = ROOT / "ukb_dmca" / "ukb_dmca_repositories.csv"
DMCA_MATCHES = ROOT / "ukb_dmca" / "ukb_dmca_application_matches.csv"
DMCA_UNRESOLVED = ROOT / "ukb_dmca" / "ukb_dmca_unresolved.csv"
DMCA_NOTICES = ROOT / "ukb_dmca" / "ukb_dmca_notices.csv"

POLICY_DATE = date(2024, 7, 5)
BREAK_MONTH = date(2024, 7, 1)
PRIMARY_START = date(2019, 1, 1)
PRIMARY_END = date(2025, 12, 1)
HAC_LAG_MONTHLY = 3
HAC_LAG_QUARTERLY = 1

STRICT_21 = {
    "103356",
    "47267",
    "66995",
    "87802",
    "48388",
    "45761",
    "177030",
    "88159",
    "822932",
    "19542",
    "84103",
    "28784",
    "19526",
    "61666",
    "55955",
    "51157",
    "69610",
    "61054",
    "52887",
    "33923",
    "52293",
}
MAIN_EXTRA_6 = {"30418", "65805", "57232", "27837", "55288", "92005"}
BROAD_EXTRA_21 = {
    "31063",
    "74395",
    "10279",
    "22224",
    "24247",
    "46122",
    "56757",
    "61785",
    "62254",
    "64823",
    "88878",
    "49777",
    "51064",
    "79957",
    "40161",
    "867484",
    "23668",
    "12184",
    "10035",
    "19136",
    "59070",
}
MAIN_27 = STRICT_21 | MAIN_EXTRA_6
BROAD_48 = MAIN_27 | BROAD_EXTRA_21

# Generic repository names are kept as separate public repository families. This
# prevents weak names such as "UKB", "UKBB", or "001" from propagating matches.
GENERIC_REPO_FAMILY_NAMES = {"001", "data", "ukb", "ukbb", "ukbiobank"}

REMAINING_23_REVIEWS: list[dict[str, str]] = [
    {
        "review_unit_id": "family_ukbb-gwas-dev",
        "candidate_application_ids": "32285; 36827",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "publication/application leads without a repository-owner bridge",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "https://www.ukbiobank.ac.uk/enable-your-research/approved-research/uk-biobank-infectious-disease-genetics-study",
        "review_notes": "Prior manual round explicitly left UKBB_GWAS_dev unfrozen. Public evidence supports UKB applications/papers in nearby GWAS areas, but not the target repo owners/family.",
    },
    {
        "review_unit_id": "family_cnv-ukb",
        "candidate_application_ids": "40980; 24898; 68574; 68601; 82094",
        "review_status": "ambiguous",
        "final_application_id": "",
        "evidence_type": "multiple plausible CNV UKB applications",
        "confidence": "ambiguous",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "Public CNV/UKB evidence points to several applications; no direct application ID, repo-publication chain, or identity bridge uniquely identifies the targeted repository family.",
    },
    {
        "review_unit_id": "family_ukbbcov2risk",
        "candidate_application_ids": "",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "generic COVID-19 risk topic only",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "Search did not recover a direct application number or repository-linked publication/application chain for kennethcywong/ukbbcov2risk.",
    },
    {
        "review_unit_id": "family_ukbbmriutils",
        "candidate_application_ids": "89197",
        "review_status": "new_application_linked",
        "final_application_id": "89197",
        "evidence_type": "organization/project/topic consistency plus public UKB project evidence",
        "confidence": "probable",
        "final_sample_action": "add_new_application",
        "evidence_urls": "https://www.ukbiobank.ac.uk/enable-your-research/approved-research/effects-of-copy-number-variants-on-the-morphological-structure-of-the-brain-across-multiple-brain-disorders",
        "review_notes": "STALICLA-RnD repository family aligns with the STALICLA application on CNV effects on brain morphology. Public project metadata gives UKB application 89197 and start date 2023-06-29.",
    },
    {
        "review_unit_id": "family_t40-rsfmri",
        "candidate_application_ids": "25057",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "paper app lead without owner identity bridge",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "A TOMM40/APOE resting-state fMRI paper reports UKB application 25057, but the target owner is pseudonymous and public evidence does not bridge the repo to the paper team.",
    },
    {
        "review_unit_id": "family_ukb-bmi",
        "candidate_application_ids": "48799",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "legacy application clue not in current start-date universe",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "Historical review noted application 48799, but this ID is not present in the current start-date application universe and no stronger public chain was recovered.",
    },
    {
        "review_unit_id": "family_divergence-pipeline",
        "candidate_application_ids": "17984",
        "review_status": "new_application_linked",
        "final_application_id": "17984",
        "evidence_type": "author/project/topic consistency plus public UKB project evidence",
        "confidence": "probable",
        "final_sample_action": "add_new_application",
        "evidence_urls": "https://www.ukbiobank.ac.uk/enable-your-research/approved-research/genotype-environment-interactions-and-sub-classification-of-disease",
        "review_notes": "The AdrianHarris96 Divergence_Pipeline lead is consistent with Adrian M. Harris, the Georgia Tech divergence/Gini work, and UKB application 17984. The chain is credible but not a direct repo README app-ID match.",
    },
    {
        "review_unit_id": "family_genepy-2",
        "candidate_application_ids": "72911",
        "review_status": "new_application_linked",
        "final_application_id": "72911",
        "evidence_type": "repo-publication-UKB application chain",
        "confidence": "confirmed",
        "final_sample_action": "add_new_application",
        "evidence_urls": "https://www.ukbiobank.ac.uk/enable-your-research/publications/stratification-of-inflammatory-bowel-disease-by-integrating-genomic-data-and-biological-pathways-using-the-genepy-approach; https://github.com/UoS-HGIG/GenePy-2",
        "review_notes": "The GenePy-2 project has a public repo-publication chain and UKB publication metadata reports application 72911.",
    },
    {
        "review_unit_id": "family_gwas-phenotype",
        "candidate_application_ids": "22418",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "candidate is a UKB field/resource ID, not an application",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "The historical 22418 lead is not treated as a UKB application ID; no replacement direct application evidence was recovered.",
    },
    {
        "review_unit_id": "family_uk-biobank-study-1",
        "candidate_application_ids": "84709",
        "review_status": "new_application_linked",
        "final_application_id": "84709",
        "evidence_type": "repo-publication-UKB application chain",
        "confidence": "confirmed",
        "final_sample_action": "add_new_application",
        "evidence_urls": "https://www.ukbiobank.ac.uk/enable-your-research/approved-research/risk-and-prognosis-factors-of-cardiovascular-disease-on-different-genetic-background-and-exposures",
        "review_notes": "Prior repository metadata tied xx2383/UK-Biobank-study-1 to DOI 10.1016/j.crtox.2025.100226. The linked UKB project page reports application 84709 and a related publication on the same exposure/outcome chain.",
    },
    {
        "review_unit_id": "family_ukb-gen-clocks",
        "candidate_application_ids": "29256",
        "review_status": "excluded_false_positive",
        "final_application_id": "",
        "evidence_type": "automated propagation false positive",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "Current automated matcher propagated application 29256 through weak publication/topic signals. Manual review treats this as a false positive for UKB-gen-clocks and does not add 29256.",
    },
    {
        "review_unit_id": "family_pain-proteomics",
        "candidate_application_ids": "19542",
        "review_status": "linked_to_existing_baseline",
        "final_application_id": "19542",
        "evidence_type": "paper text/application chain to an existing baseline app",
        "confidence": "confirmed",
        "final_sample_action": "link_existing_baseline_application",
        "evidence_urls": "https://www.ukbiobank.ac.uk/enable-your-research/approved-research/identifying-multi-level-biomarkers-and-disease-mechanisms-for-major-mental-disorders",
        "review_notes": "Pain proteomics public paper evidence reports UKB application 19542, already present in the fixed broad-48 baseline.",
    },
    {
        "review_unit_id": "family_mh-in-ukb",
        "candidate_application_ids": "47267",
        "review_status": "linked_to_existing_baseline",
        "final_application_id": "47267",
        "evidence_type": "repo-publication-application chain to an existing baseline app",
        "confidence": "confirmed",
        "final_sample_action": "link_existing_baseline_application",
        "evidence_urls": "https://github.com/PersonomicsLab/MH_in_UKB; https://www.ukbiobank.ac.uk/enable-your-research/approved-research/cross-diagnostic-and-cross-platform-multimodal-analysis-of-uk-biobank-imaging-data",
        "review_notes": "The MH_in_UKB code availability chain and paper evidence link to UKB application 47267, already present in the fixed broad-48 baseline.",
    },
    {
        "review_unit_id": "family_uk-biobank-survival",
        "candidate_application_ids": "45761",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "possible existing-baseline relation but weak public bridge",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "The family may relate to an existing baseline application, but public evidence does not establish a direct repo-publication/application or identity chain.",
    },
    {
        "review_unit_id": "family_keloids-clustering",
        "candidate_application_ids": "146079",
        "review_status": "ambiguous",
        "final_application_id": "",
        "evidence_type": "topic/institution-only application lead",
        "confidence": "ambiguous",
        "final_sample_action": "do_not_add",
        "evidence_urls": "https://www.ukbiobank.ac.uk/enable-your-research/approved-research/epidemiological-and-genetic-risk-factors-for-keloid-and-hypertrophic-scar",
        "review_notes": "UKB application 146079 is topically compatible with keloids, but the repository-to-application bridge is insufficient.",
    },
    {
        "review_unit_id": "family_ukb-atherosclerosis-prediction",
        "candidate_application_ids": "",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "no public application bridge found",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "No direct application ID, repository-linked publication, or strong identity evidence was recovered.",
    },
    {
        "review_unit_id": "family_prs-dash-boxplot-app",
        "candidate_application_ids": "29256",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "weak automated/publication propagation not accepted",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "The 29256 automated context is not accepted for this repository family; no stronger direct application evidence was recovered.",
    },
    {
        "review_unit_id": "family_ukb-download-and-prep-template",
        "candidate_application_ids": "",
        "review_status": "ambiguous",
        "final_application_id": "",
        "evidence_type": "template/common-code family with no unique app",
        "confidence": "ambiguous",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "The family contains multiple copied/template repositories and no unique application-level public evidence.",
    },
    {
        "review_unit_id": "family_ukb-api",
        "candidate_application_ids": "",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "generic utility/API repository family",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "Generic UKB API utility family; no direct application or repo-publication chain was found.",
    },
    {
        "review_unit_id": "family_ukb-tools",
        "candidate_application_ids": "",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "generic utility repository family",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "Generic tools family; no unique UKB application could be assigned.",
    },
    {
        "review_unit_id": "family_ukbiobank-table-conversion",
        "candidate_application_ids": "",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "common table-conversion code family",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "Table-conversion family has multiple copies and no unique application/publication bridge.",
    },
    {
        "review_unit_id": "family_jm-gwas",
        "candidate_application_ids": "",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "common GWAS code family with no unique app",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "Multiple repositories share JM-GWAS material, but public evidence does not identify one UKB application.",
    },
    {
        "review_unit_id": "family_multi-outcome",
        "candidate_application_ids": "",
        "review_status": "unresolved",
        "final_application_id": "",
        "evidence_type": "generic multi-outcome analysis family",
        "confidence": "unresolved",
        "final_sample_action": "do_not_add",
        "evidence_urls": "",
        "review_notes": "No direct application ID, linked paper, or owner identity bridge was recovered.",
    },
]

REMAINING_23_BY_FAMILY = {row["review_unit_id"]: row for row in REMAINING_23_REVIEWS}
FINAL_REVIEW_NEW_APPLICATIONS = {
    row["final_application_id"]
    for row in REMAINING_23_REVIEWS
    if row["final_sample_action"] == "add_new_application" and row["final_application_id"]
}
FINAL_EXPANDED_APPLICATIONS = BROAD_48 | FINAL_REVIEW_NEW_APPLICATIONS


@dataclass(frozen=True)
class Outputs:
    ukb_curated_links: Path = ROOT / "ukb_dmca" / "curated_dmca_application_links.csv"
    ukb_repository_family_links: Path = ROOT / "ukb_dmca" / "curated_dmca_repository_family_links.csv"
    ukb_remaining_23_review: Path = ROOT / "ukb_dmca" / "remaining_23_repo_review.csv"
    ukb_remaining_unmatched: Path = ROOT / "ukb_dmca" / "remaining_unmatched_lineages.csv"
    ukb_linkage_report: Path = REPORT_DIR / "remaining_repo_linkage_report.md"
    curated_application_links: Path = DATA_DIR / "curated_application_links.csv"
    leakage_risk_applications: Path = DATA_DIR / "leakage_risk_applications.csv"
    application_level: Path = DATA_DIR / "application_level_leakage.csv"
    monthly_cohorts: Path = DATA_DIR / "monthly_application_start_cohorts.csv"
    quarterly_cohorts: Path = DATA_DIR / "quarterly_application_start_cohorts.csv"
    strict_sample: Path = DATA_DIR / "strict_sample.csv"
    main_sample: Path = DATA_DIR / "main_sample.csv"
    broad_sample: Path = DATA_DIR / "broad_baseline_sample.csv"
    expanded_sample: Path = DATA_DIR / "final_expanded_sample.csv"
    prepost_table: Path = TABLE_DIR / "pre_post_comparison.csv"
    app_lpm_table: Path = TABLE_DIR / "application_level_regressions.csv"
    app_robust_table: Path = TABLE_DIR / "application_level_robustness_models.csv"
    monthly_its_table: Path = TABLE_DIR / "monthly_its_results.csv"
    quarterly_its_table: Path = TABLE_DIR / "quarterly_its_results.csv"
    sensitivity_table: Path = TABLE_DIR / "linkage_sensitivity.csv"
    stata_style_tables: Path = REPORT_DIR / "leakage_stata_style_regression_tables.txt"
    results_report: Path = REPORT_DIR / "leakage_its_results.md"
    start_distribution_figure: Path = FIGURE_DIR / "leakage_start_date_distribution.svg"
    monthly_count_figure: Path = FIGURE_DIR / "leakage_monthly_counts_by_start_month.svg"
    monthly_rate_figure: Path = FIGURE_DIR / "leakage_monthly_rate_by_start_cohort.svg"
    quarterly_rate_figure: Path = FIGURE_DIR / "leakage_quarterly_rate_by_start_cohort.svg"
    its_fitted_figure: Path = FIGURE_DIR / "leakage_monthly_its_fitted_final_expanded.svg"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


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


def parse_date(value: str) -> date | None:
    value = clean(value)
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    return date(value.year + month // 12, month % 12 + 1, 1)


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def quarter_start(value: date) -> date:
    return date(value.year, ((value.month - 1) // 3) * 3 + 1, 1)


def month_range(start: date, end: date) -> list[date]:
    out = []
    current = month_start(start)
    stop = month_start(end)
    while current <= stop:
        out.append(current)
        current = add_months(current, 1)
    return out


def quarter_range(start: date, end: date) -> list[date]:
    out = []
    current = quarter_start(start)
    stop = quarter_start(end)
    while current <= stop:
        out.append(current)
        current = add_months(current, 3)
    return out


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def month_label(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def quarter_label(value: date) -> str:
    return f"{value.year:04d}Q{((value.month - 1) // 3) + 1}"


def fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f"{value:.{digits}f}"
    return str(value)


def fmt_pct(value: float | None, digits: int = 2) -> str:
    if value is None or math.isnan(value) or math.isinf(value):
        return ""
    return f"{100.0 * value:.{digits}f}%"


def split_parts(value: str) -> list[str]:
    if not value:
        return []
    parts: list[str] = []
    for chunk in re.split(r";|\|", value):
        item = clean(chunk)
        if item and item not in parts:
            parts.append(item)
    return parts


def uniq(values: list[str] | set[str]) -> str:
    out: list[str] = []
    for value in values:
        for part in split_parts(value):
            if part and part not in out:
                out.append(part)
    return "; ".join(out)


def normal_pvalue(estimate: float, se: float) -> float:
    if se <= 0 or math.isnan(se):
        return math.nan
    return math.erfc(abs(estimate / se) / math.sqrt(2.0))


def wilson_ci(events: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (math.nan, math.nan)
    p = events / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def prop_diff_test(pre_events: int, pre_n: int, post_events: int, post_n: int) -> dict[str, float]:
    pre_rate = pre_events / pre_n if pre_n else math.nan
    post_rate = post_events / post_n if post_n else math.nan
    diff = post_rate - pre_rate
    se = math.sqrt(
        (pre_rate * (1 - pre_rate) / pre_n if pre_n else 0.0)
        + (post_rate * (1 - post_rate) / post_n if post_n else 0.0)
    )
    pooled = (pre_events + post_events) / (pre_n + post_n) if pre_n + post_n else math.nan
    pooled_se = math.sqrt(pooled * (1 - pooled) * (1 / pre_n + 1 / post_n)) if pre_n and post_n else math.nan
    z = diff / pooled_se if pooled_se and pooled_se > 0 else math.nan
    p = normal_pvalue(diff, pooled_se) if pooled_se and pooled_se > 0 else math.nan
    return {
        "pre_rate": pre_rate,
        "post_rate": post_rate,
        "difference": diff,
        "difference_ci_low": diff - 1.96 * se if se else math.nan,
        "difference_ci_high": diff + 1.96 * se if se else math.nan,
        "z": z,
        "p_value": p,
        "ratio_post_pre": post_rate / pre_rate if pre_rate and pre_rate > 0 else math.nan,
    }


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    rows, cols, inner = len(a), len(b[0]), len(b)
    return [[sum(a[i][k] * b[k][j] for k in range(inner)) for j in range(cols)] for i in range(rows)]


def mat_vec_mul(a: list[list[float]], v: list[float]) -> list[float]:
    return [sum(row[j] * v[j] for j in range(len(v))) for row in a]


def invert(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    aug = [[float(a[i][j]) for j in range(n)] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("singular regression matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        denom = aug[col][col]
        aug[col] = [value / denom for value in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor:
                aug[row] = [aug[row][i] - factor * aug[col][i] for i in range(2 * n)]
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
    for row, value in zip(X, y):
        for i in range(k):
            out[i] += row[i] * value
    return out


def outer(a: list[float], b: list[float]) -> list[list[float]]:
    return [[ai * bj for bj in b] for ai in a]


def mat_add_inplace(a: list[list[float]], b: list[list[float]], scale: float = 1.0) -> None:
    for i in range(len(a)):
        for j in range(len(a[i])):
            a[i][j] += scale * b[i][j]


def sandwich_from_scores(bread: list[list[float]], scores: list[list[float]], lag: int = 0) -> list[list[float]]:
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


def ols(X: list[list[float]], y: list[float], hac_lag: int | None = None, hc1: bool = False) -> dict[str, object]:
    inv = invert(xtx(X))
    beta = mat_vec_mul(inv, xty(X, y))
    fitted = [sum(row[j] * beta[j] for j in range(len(beta))) for row in X]
    resid = [value - pred for value, pred in zip(y, fitted)]
    n, k = len(y), len(beta)
    if hac_lag is None and not hc1:
        rss = sum(err * err for err in resid)
        sigma2 = rss / max(n - k, 1)
        vcov = [[sigma2 * inv[i][j] for j in range(k)] for i in range(k)]
        inference = "OLS homoskedastic"
    else:
        scores = [[row[j] * err for j in range(k)] for row, err in zip(X, resid)]
        vcov = sandwich_from_scores(inv, scores, hac_lag or 0)
        if hc1:
            scale = n / max(n - k, 1)
            vcov = [[scale * value for value in row] for row in vcov]
            inference = "OLS HC1 robust SE"
        else:
            inference = f"OLS Newey-West HAC lag {hac_lag}"
    se = [math.sqrt(max(vcov[i][i], 0.0)) for i in range(k)]
    return {"beta": beta, "fitted": fitted, "resid": resid, "vcov": vcov, "se": se, "inference": inference}


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def logit_mle(X: list[list[float]], y: list[float]) -> dict[str, object]:
    n, k = len(y), len(X[0])
    events = sum(y)
    if events <= 0 or events >= n:
        raise ValueError("logit has no variation in outcome")
    beta = [math.log((events + 0.5) / (n - events + 0.5))] + [0.0] * (k - 1)
    converged = False
    for _ in range(100):
        probs = [sigmoid(max(min(sum(row[j] * beta[j] for j in range(k)), 35.0), -35.0)) for row in X]
        grad = [0.0] * k
        hess = [[0.0] * k for _ in range(k)]
        for row, outcome, prob in zip(X, y, probs):
            weight = max(prob * (1 - prob), 1e-10)
            for a in range(k):
                grad[a] += row[a] * (outcome - prob)
                for b in range(k):
                    hess[a][b] += row[a] * weight * row[b]
        step = mat_vec_mul(invert(hess), grad)
        beta = [beta[i] + step[i] for i in range(k)]
        if max(abs(value) for value in step) < 1e-8:
            converged = True
            break
    probs = [sigmoid(max(min(sum(row[j] * beta[j] for j in range(k)), 35.0), -35.0)) for row in X]
    hess = [[0.0] * k for _ in range(k)]
    for row, prob in zip(X, probs):
        weight = max(prob * (1 - prob), 1e-10)
        for a in range(k):
            for b in range(k):
                hess[a][b] += row[a] * weight * row[b]
    vcov = invert(hess)
    se = [math.sqrt(max(vcov[i][i], 0.0)) for i in range(k)]
    return {"beta": beta, "fitted": probs, "se": se, "vcov": vcov, "converged": converged}


def poisson_qmle(
    X: list[list[float]],
    y: list[float],
    offset: list[float] | None = None,
    hac_lag: int = 0,
) -> dict[str, object]:
    n, k = len(y), len(X[0])
    if offset is None:
        offset = [0.0] * n
    exposure = sum(math.exp(value) for value in offset)
    events = sum(y)
    if exposure <= 0:
        raise ValueError("poisson exposure is zero")
    beta = [math.log((events + 0.1) / exposure)] + [0.0] * (k - 1)
    converged = False
    for _ in range(100):
        eta = [max(min(offset[i] + sum(X[i][j] * beta[j] for j in range(k)), 30.0), -30.0) for i in range(n)]
        mu = [math.exp(value) for value in eta]
        grad = [0.0] * k
        hess = [[0.0] * k for _ in range(k)]
        for i, row in enumerate(X):
            for a in range(k):
                grad[a] += row[a] * (y[i] - mu[i])
                for b in range(k):
                    hess[a][b] += row[a] * mu[i] * row[b]
        step = mat_vec_mul(invert(hess), grad)
        beta = [beta[i] + step[i] for i in range(k)]
        if max(abs(value) for value in step) < 1e-8:
            converged = True
            break
    eta = [max(min(offset[i] + sum(X[i][j] * beta[j] for j in range(k)), 30.0), -30.0) for i in range(n)]
    mu = [math.exp(value) for value in eta]
    hess = [[0.0] * k for _ in range(k)]
    for i, row in enumerate(X):
        for a in range(k):
            for b in range(k):
                hess[a][b] += row[a] * mu[i] * row[b]
    bread = invert(hess)
    scores = [[X[i][j] * (y[i] - mu[i]) for j in range(k)] for i in range(n)]
    vcov = sandwich_from_scores(bread, scores, hac_lag)
    se = [math.sqrt(max(vcov[i][i], 0.0)) for i in range(k)]
    pearson = sum((y[i] - mu[i]) ** 2 / max(mu[i], 1e-10) for i in range(n)) / max(n - k, 1)
    return {
        "beta": beta,
        "fitted": mu,
        "se": se,
        "vcov": vcov,
        "pearson_dispersion": pearson,
        "converged": converged,
        "inference": f"Poisson QMLE Newey-West HAC lag {hac_lag}",
    }


def repo_basename(source_repo: str) -> str:
    value = clean(source_repo).split("/", 1)[-1].lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "unknown"


def family_id_for_lineage(lineage: dict[str, str]) -> str:
    basename = repo_basename(lineage.get("source_repo", ""))
    if basename in GENERIC_REPO_FAMILY_NAMES:
        suffix = clean(lineage["lineage_id"]).removeprefix("lineage_")
        return f"family_{suffix}"
    return f"family_{basename}"


def evidence_type_for_class(value: str) -> str:
    parts = set(split_parts(value))
    labels = []
    if "A1_DIRECT_APP_ID" in parts:
        labels.append("direct UKB application number")
    if "A2_DOI_UKB_CROSSWALK" in parts or "A3_PMID_UKB_CROSSWALK" in parts:
        labels.append("repository-linked DOI/PMID to UKB publication/application crosswalk")
    if "A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN" in parts:
        labels.append("exact repository-publication-application chain")
    if "B1_AUTHOR_LAB_PROJECT_NAME_TOPIC_CONSISTENCY" in parts:
        labels.append("author/lab/project/topic consistency")
    if "B2_PROJECT_FAMILY_NAME_PROPAGATION" in parts:
        labels.append("project-family name propagation")
    if "B3_EXACT_TARGET_CONTENT_FINGERPRINT_PROPAGATION" in parts:
        labels.append("target-content fingerprint propagation")
    if "B" in parts:
        labels.append("supporting B-level identity/topic evidence")
    if "C" in parts:
        labels.append("weak C-level topic/path evidence")
    return "; ".join(labels) if labels else uniq([value])


def sample_membership(app_id_text: str, final_apps: set[str] | None = None) -> str:
    final_apps = final_apps or FINAL_EXPANDED_APPLICATIONS
    app_ids = set(split_parts(app_id_text)) or {app_id_text}
    labels = []
    if app_ids & STRICT_21:
        labels.append("strict_21")
    if app_ids & MAIN_27:
        labels.append("main_27")
    if app_ids & BROAD_48:
        labels.append("archived_broad_48")
    if app_ids & final_apps:
        labels.append("final_expanded")
    return "; ".join(labels)


def load_applications() -> list[dict[str, object]]:
    master = {row["app_id"]: row for row in read_csv(STAGE2_MASTER)}
    rows: list[dict[str, object]] = []
    for row in read_csv(START_DATES):
        app_id = row["app_id"]
        meta = master.get(app_id, {})
        start = parse_date(row.get("start_date", ""))
        rows.append(
            {
                "app_id": app_id,
                "application_title": row.get("schema27_title") or meta.get("title", ""),
                "application_pi": row.get("schema27_pi") or meta.get("pi", ""),
                "application_institution": row.get("schema27_institution") or meta.get("institution", ""),
                "application_notes": meta.get("notes", ""),
                "project_start_date": start,
                "website_match_status": row.get("website_match_status", ""),
                "website_match_count": row.get("website_match_count", ""),
                "website_url": row.get("website_url", ""),
                "match_methods": row.get("match_methods", ""),
            }
        )
    return rows


def aggregate_rows(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if clean(row.get(key)):
            out[clean(row[key])].append(row)
    return out


def aggregate_current_matches() -> dict[str, dict[str, object]]:
    grouped = aggregate_rows(read_csv(DMCA_MATCHES), "lineage_id")
    out: dict[str, dict[str, object]] = {}
    for lineage_id, rows in grouped.items():
        apps = sorted({clean(row.get("candidate_app_id", "")) for row in rows if clean(row.get("candidate_app_id", ""))})
        grades = sorted({clean(row.get("match_grade", "")) for row in rows if clean(row.get("match_grade", ""))})
        out[lineage_id] = {
            "lineage_id": lineage_id,
            "application_ids": apps,
            "match_grades": grades,
            "evidence_classes": uniq([row.get("evidence_class", "") for row in rows]),
            "evidence_components": uniq([row.get("evidence_components", "") for row in rows]),
            "match_reasons": uniq([row.get("match_reason", "") for row in rows]),
            "evidence_urls": uniq([row.get("evidence_urls", "") for row in rows]),
            "doi": uniq([row.get("doi", "") or row.get("repo_linked_doi", "") for row in rows]),
            "pubmed_id": uniq([row.get("pubmed_id", "") or row.get("repo_linked_pmid", "") for row in rows]),
            "paper_title": uniq([row.get("paper_title", "") or row.get("repo_linked_publication_title", "") for row in rows]),
            "paper_authors": uniq([row.get("paper_authors", "") for row in rows]),
            "application_titles": uniq([row.get("application_title", "") for row in rows]),
            "application_pis": uniq([row.get("application_pi", "") for row in rows]),
            "application_institutions": uniq([row.get("application_institution", "") for row in rows]),
            "curation_source": "current_confirmed_probable_match",
        }
    return out


def aggregate_unresolved() -> dict[str, dict[str, object]]:
    grouped = aggregate_rows(read_csv(DMCA_UNRESOLVED), "lineage_id")
    out: dict[str, dict[str, object]] = {}
    for lineage_id, rows in grouped.items():
        out[lineage_id] = {
            "lineage_id": lineage_id,
            "candidate_application_ids": uniq([row.get("candidate_app_id", "") for row in rows[:10]]),
            "candidate_application_titles": uniq([row.get("application_title", "") for row in rows[:10]]),
            "match_grades": sorted({clean(row.get("match_grade", "")) for row in rows if clean(row.get("match_grade", ""))}),
            "evidence_classes": uniq([row.get("evidence_class", "") for row in rows]),
            "match_reasons": uniq([row.get("match_reason", "") for row in rows]),
            "evidence_urls": uniq([row.get("evidence_urls", "") for row in rows]),
            "doi": uniq([row.get("doi", "") or row.get("repo_linked_doi", "") for row in rows]),
            "pubmed_id": uniq([row.get("pubmed_id", "") or row.get("repo_linked_pmid", "") for row in rows]),
            "paper_title": uniq([row.get("paper_title", "") or row.get("repo_linked_publication_title", "") for row in rows]),
            "paper_authors": uniq([row.get("paper_authors", "") for row in rows]),
        }
    return out


def load_archived_crosswalk() -> tuple[dict[str, dict[str, str]], dict[str, list[dict[str, str]]]]:
    rows = read_csv(ARCHIVED_DMCA_CROSSWALK)
    by_app = {row["app_id"]: row for row in rows}
    by_lineage: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        for lineage_id in split_parts(row.get("lineage_ids", "")):
            by_lineage[lineage_id].append(row)
    return by_app, by_lineage


def repository_stats_by_lineage() -> dict[str, dict[str, object]]:
    grouped = aggregate_rows(read_csv(DMCA_REPOSITORIES), "lineage_id")
    out: dict[str, dict[str, object]] = {}
    for lineage_id, rows in grouped.items():
        out[lineage_id] = {
            "repo_urls": sorted({clean(row.get("repo_url", "")) for row in rows if clean(row.get("repo_url", ""))}),
            "notice_ids": sorted({clean(row.get("notice_id", "")) for row in rows if clean(row.get("notice_id", ""))}),
            "notice_dates": sorted({clean(row.get("notice_date", "")) for row in rows if clean(row.get("notice_date", ""))}),
            "targeted_row_count": len(rows),
        }
    return out


def best_match_status(grades: list[str], archived_rows: list[dict[str, str]]) -> str:
    grade_set = set(grades)
    if "confirmed" in grade_set:
        return "confirmed"
    if "probable" in grade_set:
        return "probable"
    if archived_rows:
        return "probable"
    if "ambiguous" in grade_set:
        return "ambiguous"
    if "not_application_attributable" in grade_set:
        return "not_application_attributable"
    return "unresolved"


def build_curated_links(
    applications: list[dict[str, object]],
    out: Outputs,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, set[str]], dict[str, object]]:
    app_by_id = {str(row["app_id"]): row for row in applications}
    lineages = read_csv(DMCA_LINEAGES)
    current_matches = aggregate_current_matches()
    current_unresolved = aggregate_unresolved()
    archived_by_app, archived_by_lineage = load_archived_crosswalk()
    repos_by_lineage = repository_stats_by_lineage()
    current_linked_apps = {
        app_id
        for link in current_matches.values()
        for app_id in link["application_ids"]
        if app_id
    }

    family_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for lineage in lineages:
        family_groups[family_id_for_lineage(lineage)].append(lineage)

    family_rows: list[dict[str, object]] = []
    real_lineages_linked: set[str] = set()
    for family_id, members in sorted(family_groups.items()):
        member_lineage_ids = [row["lineage_id"] for row in members]
        review = REMAINING_23_BY_FAMILY.get(family_id)
        archived_app_ids: set[str] = set()
        current_candidate_ids: list[str] = []
        current_grades: list[str] = []
        evidence_classes: list[str] = []
        match_reasons: list[str] = []
        evidence_urls: list[str] = []
        doi_values: list[str] = []
        pmid_values: list[str] = []
        paper_titles: list[str] = []
        paper_authors: list[str] = []
        app_titles: list[str] = []
        app_pis: list[str] = []
        app_institutions: list[str] = []
        archived_rows_for_family: list[dict[str, str]] = []
        for lineage_id in member_lineage_ids:
            if lineage_id in current_matches:
                link = current_matches[lineage_id]
                current_candidate_ids.extend(str(value) for value in link["application_ids"])
                current_grades.extend(str(value) for value in link["match_grades"])
                evidence_classes.append(str(link["evidence_classes"]))
                match_reasons.append(str(link["match_reasons"]))
                evidence_urls.append(str(link["evidence_urls"]))
                doi_values.append(str(link["doi"]))
                pmid_values.append(str(link["pubmed_id"]))
                paper_titles.append(str(link["paper_title"]))
                paper_authors.append(str(link["paper_authors"]))
                app_titles.append(str(link["application_titles"]))
                app_pis.append(str(link["application_pis"]))
                app_institutions.append(str(link["application_institutions"]))
            for archived in archived_by_lineage.get(lineage_id, []):
                archived_rows_for_family.append(archived)
                archived_app_ids.add(archived["app_id"])
                evidence_classes.append(archived.get("evidence_classes", ""))
                evidence_urls.append(archived.get("repo_urls", ""))
                app_titles.append(archived.get("schema27_title", ""))

            unres = current_unresolved.get(lineage_id, {})
            current_candidate_ids.extend(split_parts(str(unres.get("candidate_application_ids", ""))))
            current_grades.extend(str(value) for value in unres.get("match_grades", []))
            evidence_classes.append(str(unres.get("evidence_classes", "")))
            match_reasons.append(str(unres.get("match_reasons", "")))
            evidence_urls.append(str(unres.get("evidence_urls", "")))
            doi_values.append(str(unres.get("doi", "")))
            pmid_values.append(str(unres.get("pubmed_id", "")))
            paper_titles.append(str(unres.get("paper_title", "")))
            paper_authors.append(str(unres.get("paper_authors", "")))

        repo_urls = sorted(
            {
                url
                for lineage_id in member_lineage_ids
                for url in repos_by_lineage.get(lineage_id, {}).get("repo_urls", [])
                if url
            }
            | {url for member in members for url in split_parts(member.get("repo_urls", ""))}
        )
        notices = sorted(
            {
                notice
                for lineage_id in member_lineage_ids
                for notice in repos_by_lineage.get(lineage_id, {}).get("notice_ids", [])
                if notice
            }
            | {notice for member in members for notice in split_parts(member.get("notice_ids", ""))}
        )
        targeted_rows = sum(int(repos_by_lineage.get(lineage_id, {}).get("targeted_row_count", 0)) for lineage_id in member_lineage_ids)

        current_automated_status = best_match_status(current_grades, [])
        source_tags: set[str] = set()
        link_app_ids: set[str] = set()
        if review and review["final_application_id"]:
            link_app_ids.add(review["final_application_id"])
            status = "confirmed" if review["confidence"] == "confirmed" else "probable"
            confidence = review["confidence"]
            evidence_classes.append(review["evidence_type"])
            evidence_urls.append(review["evidence_urls"])
            match_reasons.append(review["review_notes"])
            source_tags.add("remaining_23_manual_review")
            real_lineages_linked.update(member_lineage_ids)
        elif archived_app_ids:
            link_app_ids.update(archived_app_ids)
            status = "confirmed"
            confidence = "confirmed"
            source_tags.add("researcher_confirmed_baseline_48")
            real_lineages_linked.update(member_lineage_ids)
        elif review:
            status = review["review_status"]
            confidence = review["confidence"]
            evidence_classes.append(review["evidence_type"])
            evidence_urls.append(review["evidence_urls"])
            match_reasons.append(review["review_notes"])
            source_tags.add("remaining_23_manual_review_unlinked")
        else:
            status = "unresolved"
            confidence = "unresolved"
            source_tags.add("current_audit_not_manually_linked")

        app_id_text = "; ".join(sorted(link_app_ids, key=lambda value: int(value) if value.isdigit() else 10**12))
        for app_id in split_parts(app_id_text):
            app = app_by_id.get(app_id, {})
            if app:
                app_titles.append(str(app.get("application_title", "")))
                app_pis.append(str(app.get("application_pi", "")))
                app_institutions.append(str(app.get("application_institution", "")))
        candidate_app_ids = review["candidate_application_ids"] if review else uniq(current_candidate_ids)
        reason = uniq(match_reasons)
        if not reason:
            if status in {"confirmed", "probable"}:
                reason = "Researcher-confirmed or remaining-23 manual review evidence links this repository family to one or more UKB applications."
            elif status == "ambiguous":
                reason = "Multiple applications remain plausible from public evidence; this family is not used as a leakage outcome assignment."
            else:
                reason = "Evidence is missing, generic, or too weak to assign a UKB application."
        curation_source = "; ".join(sorted(source_tags)) if source_tags else "current_unresolved_or_weak_candidate"
        family_rows.append(
            {
                "record_type": "repository_family",
                "family_id": family_id,
                "member_lineage_count": len(member_lineage_ids),
                "member_lineage_ids": "; ".join(member_lineage_ids),
                "source_repositories": "; ".join(sorted({row.get("source_repo", "") for row in members if row.get("source_repo", "")})),
                "all_repo_urls": "; ".join(repo_urls),
                "repo_count": len(repo_urls),
                "notice_ids": "; ".join(notices),
                "notice_count": len(notices),
                "targeted_row_count": targeted_rows,
                "application_id": app_id_text if status in {"confirmed", "probable"} else "",
                "candidate_application_ids": candidate_app_ids,
                "application_title": uniq(app_titles) or uniq([str(app_by_id.get(app_id_text, {}).get("application_title", ""))]),
                "matching_status": status,
                "confidence": confidence,
                "current_automated_status": current_automated_status,
                "evidence_grade": uniq(evidence_classes),
                "evidence_type": evidence_type_for_class(uniq(evidence_classes)),
                "doi": uniq(doi_values),
                "pmid": uniq(pmid_values),
                "publication_title": uniq(paper_titles),
                "publication_authors": uniq(paper_authors),
                "pi_author_institution_evidence": uniq([*app_pis, *paper_authors, *app_institutions]),
                "evidence_urls": uniq(evidence_urls + repo_urls),
                "curation_source": curation_source,
                "sample_membership": sample_membership(app_id_text) if app_id_text else "",
                "reviewer_explanation": reason,
            }
        )

    family_fieldnames = [
        "record_type",
        "family_id",
        "member_lineage_count",
        "member_lineage_ids",
        "source_repositories",
        "all_repo_urls",
        "repo_count",
        "notice_ids",
        "notice_count",
        "targeted_row_count",
        "application_id",
        "candidate_application_ids",
        "application_title",
        "matching_status",
        "confidence",
        "current_automated_status",
        "evidence_grade",
        "evidence_type",
        "doi",
        "pmid",
        "publication_title",
        "publication_authors",
        "pi_author_institution_evidence",
        "evidence_urls",
        "curation_source",
        "sample_membership",
        "reviewer_explanation",
    ]
    write_csv(out.ukb_repository_family_links, family_rows, family_fieldnames)
    remaining = [
        row
        for row in family_rows
        if row["record_type"] == "repository_family" and row["matching_status"] not in {"confirmed", "probable"}
    ]
    write_csv(out.ukb_remaining_unmatched, remaining, family_fieldnames)

    family_by_id = {clean(row["family_id"]): row for row in family_rows}
    remaining_23_rows: list[dict[str, object]] = []
    for review in REMAINING_23_REVIEWS:
        family = family_by_id.get(review["review_unit_id"], {})
        source_repos = split_parts(clean(family.get("source_repositories", "")))
        first_repo = source_repos[0] if source_repos else ""
        repo_owner, repo_name = ("", "")
        if "/" in first_repo:
            repo_owner, repo_name = first_repo.split("/", 1)
        remaining_23_rows.append(
            {
                "family_id": review["review_unit_id"],
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "repo_url": split_parts(clean(family.get("all_repo_urls", "")))[0] if family.get("all_repo_urls") else "",
                "related_repo_urls": family.get("all_repo_urls", ""),
                "lineage_ids": family.get("member_lineage_ids", ""),
                "lineage_count": family.get("member_lineage_count", ""),
                "notice_id": family.get("notice_ids", ""),
                "targeted_row_count": family.get("targeted_row_count", ""),
                "current_automated_status": family.get("current_automated_status", ""),
                "candidate_application_ids": review["candidate_application_ids"],
                "review_status": review["review_status"],
                "final_application_id": review["final_application_id"],
                "evidence_type": review["evidence_type"],
                "confidence": review["confidence"],
                "final_sample_action": review["final_sample_action"],
                "evidence_urls": review["evidence_urls"],
                "review_notes": review["review_notes"],
            }
        )
    remaining_23_fieldnames = [
        "family_id",
        "repo_owner",
        "repo_name",
        "repo_url",
        "related_repo_urls",
        "lineage_ids",
        "lineage_count",
        "notice_id",
        "targeted_row_count",
        "current_automated_status",
        "candidate_application_ids",
        "review_status",
        "final_application_id",
        "evidence_type",
        "confidence",
        "final_sample_action",
        "evidence_urls",
        "review_notes",
    ]
    write_csv(out.ukb_remaining_23_review, remaining_23_rows, remaining_23_fieldnames)

    linked_family_rows_by_app: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in family_rows:
        if clean(row.get("matching_status", "")) not in {"confirmed", "probable"}:
            continue
        for app_id in split_parts(clean(row.get("application_id", ""))):
            linked_family_rows_by_app[app_id].append(row)

    app_rows: list[dict[str, object]] = []
    for app_id in sorted(FINAL_EXPANDED_APPLICATIONS, key=lambda value: int(value)):
        app = app_by_id.get(app_id, {})
        archived = archived_by_app.get(app_id, {})
        linked_families = linked_family_rows_by_app.get(app_id, [])
        lineage_ids = set(split_parts(archived.get("lineage_ids", "")))
        repo_urls = set(split_parts(archived.get("repo_urls", "")))
        notice_ids = set(split_parts(archived.get("notice_ids", "")))
        family_ids = set()
        targeted_row_count = 0
        evidence_classes_for_app = []
        match_grades_for_app = []
        explanations = []
        for family in linked_families:
            family_ids.add(clean(family.get("family_id", "")))
            for lineage_id in split_parts(clean(family.get("member_lineage_ids", ""))):
                lineage_ids.add(lineage_id)
            for url in split_parts(clean(family.get("all_repo_urls", ""))):
                repo_urls.add(url)
            for notice in split_parts(clean(family.get("notice_ids", ""))):
                notice_ids.add(notice)
            targeted_row_count += int(family.get("targeted_row_count") or 0)
            evidence_classes_for_app.append(clean(family.get("evidence_grade", "")))
            match_grades_for_app.append(clean(family.get("confidence", "")))
            explanations.append(clean(family.get("reviewer_explanation", "")))
        if archived:
            evidence_classes_for_app.append(archived.get("evidence_classes", ""))
            match_grades_for_app.append(archived.get("match_grades", ""))
            explanations.append(archived.get("count_note", ""))
        new_review = next((row for row in REMAINING_23_REVIEWS if row["final_application_id"] == app_id), None)
        manual_status = "confirmed_by_researcher"
        if app_id not in BROAD_48 and new_review:
            manual_status = "confirmed_after_remaining_23_review" if new_review["confidence"] == "confirmed" else "probable_after_remaining_23_review"
        provenance = (
            "archived researcher-confirmed manual crosswalk"
            if app_id in BROAD_48
            else "remaining-23 public evidence review"
        )
        app_rows.append(
            {
                "application_id": app_id,
                "application_title": archived.get("schema27_title") or str(app.get("application_title", "")),
                "project_start_date": archived.get("project_start_date") or (app["project_start_date"].isoformat() if isinstance(app.get("project_start_date"), date) else ""),
                "application_pi": str(app.get("application_pi", "")),
                "application_institution": str(app.get("application_institution", "")),
                "doi": "10.1016/j.crtox.2025.100226" if app_id == "84709" else "",
                "pmid": "",
                "publication_title": "In utero tobacco exposure and offspring childhood cancers: A multicohort analysis" if app_id == "84709" else "",
                "curated_set": archived.get("curated_set") or "final_expanded_new_from_remaining_23",
                "dmca_strict_21": int(app_id in STRICT_21),
                "dmca_main_27": int(app_id in MAIN_27),
                "dmca_broad_48": int(app_id in BROAD_48),
                "final_expanded_sample": int(app_id in FINAL_EXPANDED_APPLICATIONS),
                "baseline_or_new": "previously_confirmed_baseline_48" if app_id in BROAD_48 else "new_from_remaining_23_review",
                "manual_confirmation_status": manual_status,
                "lineage_id_available": int(bool(lineage_ids)),
                "lineage_ids": "; ".join(sorted(lineage_ids)),
                "linked_repository_family_ids": "; ".join(sorted(family_ids)),
                "linked_repo_urls": "; ".join(sorted(repo_urls)),
                "repo_count": len(repo_urls),
                "notice_ids": "; ".join(sorted(notice_ids)),
                "notice_count": len(notice_ids) if notice_ids else clean(archived.get("dmca_notice_count_lower_bound", "")),
                "first_dmca_notice_date": archived.get("first_dmca_notice_date", ""),
                "linked_targeted_row_count": targeted_row_count,
                "evidence_classes": uniq(evidence_classes_for_app),
                "match_grades": uniq(match_grades_for_app),
                "curation_source": provenance,
                "provenance": provenance,
                "count_note": archived.get("count_note", "") or ("new unique application from remaining 23 review" if app_id not in BROAD_48 else ""),
                "reviewer_explanation": uniq(explanations) or (new_review["review_notes"] if new_review else ""),
            }
        )

    app_fieldnames = [
        "application_id",
        "application_title",
        "project_start_date",
        "application_pi",
        "application_institution",
        "doi",
        "pmid",
        "publication_title",
        "curated_set",
        "dmca_strict_21",
        "dmca_main_27",
        "dmca_broad_48",
        "final_expanded_sample",
        "baseline_or_new",
        "manual_confirmation_status",
        "lineage_id_available",
        "lineage_ids",
        "linked_repository_family_ids",
        "linked_repo_urls",
        "repo_count",
        "notice_ids",
        "notice_count",
        "first_dmca_notice_date",
        "linked_targeted_row_count",
        "evidence_classes",
        "match_grades",
        "curation_source",
        "provenance",
        "count_note",
        "reviewer_explanation",
    ]
    write_csv(out.ukb_curated_links, app_rows, app_fieldnames)
    write_csv(out.curated_application_links, app_rows, app_fieldnames)

    linked_by_sample = {
        "strict_21": set(STRICT_21),
        "main_27": set(MAIN_27),
        "archived_broad_48": set(BROAD_48),
        "final_expanded": set(FINAL_EXPANDED_APPLICATIONS),
    }
    remaining_23_linked = [
        row
        for row in REMAINING_23_REVIEWS
        if row["final_sample_action"] in {"add_new_application", "link_existing_baseline_application"}
    ]
    remaining_23_unresolved = [
        row
        for row in REMAINING_23_REVIEWS
        if row["final_sample_action"] == "do_not_add"
    ]
    summary = {
        "current_dmca_notice_count": len(read_csv(DMCA_NOTICES)),
        "current_dmca_repository_lineages": len(lineages),
        "curated_repository_families": len(family_rows),
        "canonical_curated_application_rows": len(app_rows),
        "application_only_manual_rows": sum(1 for row in app_rows if clean(row["lineage_id_available"]) == "0" and row["baseline_or_new"] == "previously_confirmed_baseline_48"),
        "manual_archived_linked_applications_before_task": len(BROAD_48),
        "manual_archived_named_lineages_before_task": len(archived_by_lineage),
        "remaining_23_review_rows": len(REMAINING_23_REVIEWS),
        "remaining_23_successfully_linked_families": len(remaining_23_linked),
        "remaining_23_linked_existing_baseline_families": sum(1 for row in remaining_23_linked if row["final_sample_action"] == "link_existing_baseline_application"),
        "remaining_23_new_application_families": sum(1 for row in remaining_23_linked if row["final_sample_action"] == "add_new_application"),
        "remaining_23_unresolved_or_ambiguous_families": len(remaining_23_unresolved),
        "new_unique_applications_from_remaining_23": len(FINAL_REVIEW_NEW_APPLICATIONS),
        "current_confirmed_probable_lineages": len(current_matches),
        "current_confirmed_probable_applications": len(current_linked_apps),
        "automated_current_only_applications_not_added": sorted(current_linked_apps - BROAD_48 - FINAL_REVIEW_NEW_APPLICATIONS, key=lambda value: int(value)),
        "final_unique_linked_applications_expanded": len(FINAL_EXPANDED_APPLICATIONS),
        "final_named_linked_lineages": len(real_lineages_linked),
        "remaining_unmatched_repository_families": len(remaining),
        "family_status_counts": dict(Counter(str(row["matching_status"]) for row in family_rows)),
        "manual_confirmation_status_counts": dict(Counter(str(row["manual_confirmation_status"]) for row in app_rows)),
        "remaining_23_status_counts": dict(Counter(row["review_status"] for row in REMAINING_23_REVIEWS)),
        "new_applications_from_remaining_23": sorted(FINAL_REVIEW_NEW_APPLICATIONS, key=lambda value: int(value)),
    }
    return app_rows, remaining, linked_by_sample, summary


def subtract_one_year(value: date) -> date:
    try:
        return date(value.year - 1, value.month, value.day)
    except ValueError:
        return date(value.year - 1, value.month, 28)


def app_link_summaries(
    curated_rows: list[dict[str, object]],
    linked_by_sample: dict[str, set[str]],
) -> dict[str, dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for sample_name, app_ids in linked_by_sample.items():
        for app_id in app_ids:
            summaries.setdefault(
                app_id,
                {
                    "application_id": app_id,
                    "linked_lineages": set(),
                    "linked_families": set(),
                    "repo_urls": set(),
                    "notice_ids": set(),
                    "targeted_row_count": 0,
                    "linkage_confidence": "",
                    "evidence_grades": set(),
                    "count_notes": set(),
                },
            )
            summaries[app_id]["linkage_confidence"] = sample_membership(app_id)
    for row in curated_rows:
        app_id = clean(row.get("application_id", ""))
        if not app_id:
            continue
        summary = summaries.setdefault(
            app_id,
            {
                "application_id": app_id,
                "linked_lineages": set(),
                "linked_families": set(),
                "repo_urls": set(),
                "notice_ids": set(),
                "targeted_row_count": 0,
                "linkage_confidence": sample_membership(app_id),
                "evidence_grades": set(),
                "count_notes": set(),
            },
        )
        for family_id in split_parts(clean(row.get("linked_repository_family_ids", ""))):
            summary["linked_families"].add(family_id)
        for lineage_id in split_parts(clean(row.get("lineage_ids", ""))):
            summary["linked_lineages"].add(lineage_id)
        for url in split_parts(clean(row.get("linked_repo_urls", ""))):
            summary["repo_urls"].add(url)
        for notice in split_parts(clean(row.get("notice_ids", ""))):
            summary["notice_ids"].add(notice)
        summary["targeted_row_count"] += int(row.get("linked_targeted_row_count") or 0)
        if clean(row.get("lineage_id_available", "")) == "0":
            summary["count_notes"].add("application_only_lower_bound_1")
        for grade in split_parts(clean(row.get("evidence_classes", ""))):
            summary["evidence_grades"].add(grade)
    for app_id, summary in summaries.items():
        if not summary["linked_lineages"] and app_id in linked_by_sample["final_expanded"]:
            summary["linked_lineages"].add("application_only_lower_bound_1")
        if not summary["linked_families"] and app_id in linked_by_sample["final_expanded"]:
            summary["linked_families"].add("application_only_lower_bound_1")
    return summaries


def build_application_dataset(
    applications: list[dict[str, object]],
    linked_by_sample: dict[str, set[str]],
    link_summaries: dict[str, dict[str, object]],
    out: Outputs,
) -> tuple[list[dict[str, object]], date, date]:
    starts = [row["project_start_date"] for row in applications if isinstance(row["project_start_date"], date)]
    min_start = min(starts)
    max_start = max(starts)
    drop_recent_cutoff = subtract_one_year(max_start)
    rows: list[dict[str, object]] = []
    for row in applications:
        app_id = str(row["app_id"])
        start = row["project_start_date"]
        summary = link_summaries.get(app_id, {})
        post = "" if not isinstance(start, date) else int(start >= POLICY_DATE)
        start_month = month_start(start) if isinstance(start, date) else None
        start_quarter = quarter_start(start) if isinstance(start, date) else None
        out_row = {
            "application_id": app_id,
            "application_title": row.get("application_title", ""),
            "application_pi": row.get("application_pi", ""),
            "application_institution": row.get("application_institution", ""),
            "project_start_date": start.isoformat() if isinstance(start, date) else "",
            "project_start_month": month_label(start_month) if start_month else "",
            "project_start_year": start.year if isinstance(start, date) else "",
            "project_start_quarter": quarter_label(start_quarter) if start_quarter else "",
            "post_july2024": post,
            "analysis_eligible_start_date": int(isinstance(start, date)),
            "primary_its_window_2019_2025": int(isinstance(start, date) and PRIMARY_START <= start <= date(2025, 12, 31)),
            "drop_recent_12m_sample": int(isinstance(start, date) and start <= drop_recent_cutoff),
            "website_match_status": row.get("website_match_status", ""),
            "website_url": row.get("website_url", ""),
            "leak_strict_21": int(app_id in linked_by_sample["strict_21"]),
            "leak_main_27": int(app_id in linked_by_sample["main_27"]),
            "leak_archived_broad_48": int(app_id in linked_by_sample["archived_broad_48"]),
            "leak_final_expanded": int(app_id in linked_by_sample["final_expanded"]),
            "linkage_confidence": summary.get("linkage_confidence", ""),
            "linked_lineage_count": len(summary.get("linked_lineages", set())),
            "linked_family_count": len(summary.get("linked_families", set())),
            "linked_repo_count": len(summary.get("repo_urls", set())),
            "linked_notice_count": len(summary.get("notice_ids", set())),
            "linked_targeted_row_count": summary.get("targeted_row_count", 0),
            "linked_lineages": "; ".join(sorted(summary.get("linked_lineages", set()))),
            "linked_repo_urls": "; ".join(sorted(summary.get("repo_urls", set()))),
            "evidence_grades": "; ".join(sorted(summary.get("evidence_grades", set()))),
            "count_notes": "; ".join(sorted(summary.get("count_notes", set()))),
        }
        rows.append(out_row)
    fields = [
        "application_id",
        "application_title",
        "application_pi",
        "application_institution",
        "project_start_date",
        "project_start_month",
        "project_start_year",
        "project_start_quarter",
        "post_july2024",
        "analysis_eligible_start_date",
        "primary_its_window_2019_2025",
        "drop_recent_12m_sample",
        "website_match_status",
        "website_url",
        "leak_strict_21",
        "leak_main_27",
        "leak_archived_broad_48",
        "leak_final_expanded",
        "linkage_confidence",
        "linked_lineage_count",
        "linked_family_count",
        "linked_repo_count",
        "linked_notice_count",
        "linked_targeted_row_count",
        "linked_lineages",
        "linked_repo_urls",
        "evidence_grades",
        "count_notes",
    ]
    write_csv(out.application_level, rows, fields)
    leak_rows = [row for row in rows if row["leak_final_expanded"] == 1]
    write_csv(
        out.leakage_risk_applications,
        leak_rows,
        [
            "application_id",
            "application_title",
            "project_start_date",
            "project_start_month",
            "project_start_year",
            "post_july2024",
            "linkage_confidence",
            "linked_lineage_count",
            "linked_repo_count",
            "linked_notice_count",
            "evidence_grades",
        ],
    )
    for path, key in [
        (out.strict_sample, "leak_strict_21"),
        (out.main_sample, "leak_main_27"),
        (out.broad_sample, "leak_archived_broad_48"),
        (out.expanded_sample, "leak_final_expanded"),
    ]:
        write_csv(path, [row for row in rows if row[key] == 1], fields)
    return rows, max_start, drop_recent_cutoff


def application_sample_filter(rows: list[dict[str, object]], sample: str, max_start: date, drop_cutoff: date) -> list[dict[str, object]]:
    out = []
    for row in rows:
        start = parse_date(clean(row.get("project_start_date", "")))
        if not start:
            continue
        if sample == "full_start_date_universe":
            out.append(row)
        elif sample == "drop_recent_12m" and start <= drop_cutoff:
            out.append(row)
        elif sample == "its_primary_2019_2025" and PRIMARY_START <= start <= date(2025, 12, 31):
            out.append(row)
        elif sample == "through_dmca_notice_cutoff" and start <= max_start:
            out.append(row)
    return out


def build_prepost_table(rows: list[dict[str, object]], max_start: date, drop_cutoff: date, out: Outputs) -> list[dict[str, object]]:
    leakage_samples = [
        ("strict_21", "leak_strict_21"),
        ("main_27", "leak_main_27"),
        ("archived_broad_48", "leak_archived_broad_48"),
        ("final_expanded", "leak_final_expanded"),
    ]
    app_samples = ["full_start_date_universe", "drop_recent_12m", "its_primary_2019_2025"]
    results: list[dict[str, object]] = []
    for app_sample in app_samples:
        selected = application_sample_filter(rows, app_sample, max_start, drop_cutoff)
        pre = [row for row in selected if clean(row["post_july2024"]) == "0"]
        post = [row for row in selected if clean(row["post_july2024"]) == "1"]
        for label, key in leakage_samples:
            pre_events = sum(int(row[key]) for row in pre)
            post_events = sum(int(row[key]) for row in post)
            stats = prop_diff_test(pre_events, len(pre), post_events, len(post))
            pre_ci = wilson_ci(pre_events, len(pre))
            post_ci = wilson_ci(post_events, len(post))
            results.append(
                {
                    "linkage_sample": label,
                    "application_sample": app_sample,
                    "pre_applications": len(pre),
                    "pre_leakage_risk_applications": pre_events,
                    "pre_leakage_rate": fmt(stats["pre_rate"], 8),
                    "pre_leakage_rate_percent": fmt(100 * stats["pre_rate"], 4),
                    "pre_rate_ci_low": fmt(pre_ci[0], 8),
                    "pre_rate_ci_high": fmt(pre_ci[1], 8),
                    "post_applications": len(post),
                    "post_leakage_risk_applications": post_events,
                    "post_leakage_rate": fmt(stats["post_rate"], 8),
                    "post_leakage_rate_percent": fmt(100 * stats["post_rate"], 4),
                    "post_rate_ci_low": fmt(post_ci[0], 8),
                    "post_rate_ci_high": fmt(post_ci[1], 8),
                    "difference_post_minus_pre": fmt(stats["difference"], 8),
                    "difference_percentage_points": fmt(100 * stats["difference"], 4),
                    "difference_ci_low": fmt(stats["difference_ci_low"], 8),
                    "difference_ci_high": fmt(stats["difference_ci_high"], 8),
                    "ratio_post_pre": fmt(stats["ratio_post_pre"], 6),
                    "two_proportion_z": fmt(stats["z"], 6),
                    "two_proportion_p_value": fmt(stats["p_value"], 8),
                    "policy_cutoff": POLICY_DATE.isoformat(),
                }
            )
    write_csv(
        out.prepost_table,
        results,
        [
            "linkage_sample",
            "application_sample",
            "pre_applications",
            "pre_leakage_risk_applications",
            "pre_leakage_rate",
            "pre_leakage_rate_percent",
            "pre_rate_ci_low",
            "pre_rate_ci_high",
            "post_applications",
            "post_leakage_risk_applications",
            "post_leakage_rate",
            "post_leakage_rate_percent",
            "post_rate_ci_low",
            "post_rate_ci_high",
            "difference_post_minus_pre",
            "difference_percentage_points",
            "difference_ci_low",
            "difference_ci_high",
            "ratio_post_pre",
            "two_proportion_z",
            "two_proportion_p_value",
            "policy_cutoff",
        ],
    )
    return results


def lpm_design(selected: list[dict[str, object]], trend: bool) -> tuple[list[list[float]], list[str]]:
    starts = [parse_date(clean(row["project_start_date"])) for row in selected]
    min_month = min(month_start(start) for start in starts if start)
    names = ["Intercept", "PostJuly2024"]
    if trend:
        names.append("StartMonthIndex")
    X: list[list[float]] = []
    for row in selected:
        start = parse_date(clean(row["project_start_date"]))
        assert start is not None
        values = [1.0, 1.0 if start >= POLICY_DATE else 0.0]
        if trend:
            values.append(float(months_between(min_month, month_start(start))))
        X.append(values)
    return X, names


def fit_application_models(
    rows: list[dict[str, object]],
    max_start: date,
    drop_cutoff: date,
    out: Outputs,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    leakage_samples = [
        ("strict_21", "leak_strict_21"),
        ("main_27", "leak_main_27"),
        ("archived_broad_48", "leak_archived_broad_48"),
        ("final_expanded", "leak_final_expanded"),
    ]
    app_samples = ["full_start_date_universe", "drop_recent_12m", "its_primary_2019_2025"]
    lpm_rows: list[dict[str, object]] = []
    robust_rows: list[dict[str, object]] = []
    for app_sample in app_samples:
        selected = application_sample_filter(rows, app_sample, max_start, drop_cutoff)
        for label, key in leakage_samples:
            y = [float(row[key]) for row in selected]
            for trend in [False, True]:
                model_name = "LPM: Leak_i on PostJuly2024_i" if not trend else "LPM: plus smooth start-month trend"
                X, names = lpm_design(selected, trend)
                try:
                    fit = ols(X, y, hc1=True)
                    for term in ["PostJuly2024"] + (["StartMonthIndex"] if trend else []):
                        idx = names.index(term)
                        beta = float(fit["beta"][idx])
                        se = float(fit["se"][idx])
                        lpm_rows.append(
                            {
                                "linkage_sample": label,
                                "application_sample": app_sample,
                                "model": model_name,
                                "coefficient": term,
                                "n_applications": len(selected),
                                "estimate": fmt(beta, 8),
                                "estimate_percentage_points": fmt(100 * beta, 4),
                                "robust_se": fmt(se, 8),
                                "robust_se_percentage_points": fmt(100 * se, 4),
                                "p_value": fmt(normal_pvalue(beta, se), 6),
                                "ci_low": fmt(beta - 1.96 * se, 8),
                                "ci_high": fmt(beta + 1.96 * se, 8),
                                "inference": fit["inference"],
                                "warning": "",
                            }
                        )
                except Exception as exc:
                    lpm_rows.append(
                        {
                            "linkage_sample": label,
                            "application_sample": app_sample,
                            "model": model_name,
                            "coefficient": "PostJuly2024",
                            "n_applications": len(selected),
                            "warning": str(exc),
                        }
                    )
            try:
                X, names = lpm_design(selected, False)
                fit = logit_mle(X, y)
                idx = names.index("PostJuly2024")
                beta = float(fit["beta"][idx])
                se = float(fit["se"][idx])
                robust_rows.append(
                    {
                        "linkage_sample": label,
                        "application_sample": app_sample,
                        "model": "Logit: Leak_i on PostJuly2024_i",
                        "coefficient": "PostJuly2024",
                        "n_applications": len(selected),
                        "estimate_log_odds": fmt(beta, 8),
                        "odds_ratio": fmt(math.exp(beta), 6),
                        "std_error": fmt(se, 8),
                        "p_value": fmt(normal_pvalue(beta, se), 6),
                        "ci_low_log_odds": fmt(beta - 1.96 * se, 8),
                        "ci_high_log_odds": fmt(beta + 1.96 * se, 8),
                        "converged": int(bool(fit["converged"])),
                        "warning": "" if fit["converged"] else "did_not_meet_strict_convergence_tolerance",
                    }
                )
            except Exception as exc:
                robust_rows.append(
                    {
                        "linkage_sample": label,
                        "application_sample": app_sample,
                        "model": "Logit: Leak_i on PostJuly2024_i",
                        "coefficient": "PostJuly2024",
                        "n_applications": len(selected),
                        "warning": str(exc),
                    }
                )
    lpm_fields = [
        "linkage_sample",
        "application_sample",
        "model",
        "coefficient",
        "n_applications",
        "estimate",
        "estimate_percentage_points",
        "robust_se",
        "robust_se_percentage_points",
        "p_value",
        "ci_low",
        "ci_high",
        "inference",
        "warning",
    ]
    robust_fields = [
        "linkage_sample",
        "application_sample",
        "model",
        "coefficient",
        "n_applications",
        "estimate_log_odds",
        "odds_ratio",
        "std_error",
        "p_value",
        "ci_low_log_odds",
        "ci_high_log_odds",
        "converged",
        "warning",
    ]
    write_csv(out.app_lpm_table, lpm_rows, lpm_fields)
    write_csv(out.app_robust_table, robust_rows, robust_fields)
    return lpm_rows, robust_rows


def build_cohorts(rows: list[dict[str, object]], frequency: str, out: Outputs) -> list[dict[str, object]]:
    starts = [parse_date(clean(row["project_start_date"])) for row in rows if clean(row.get("project_start_date", ""))]
    starts = [start for start in starts if start]
    periods = month_range(min(starts), max(starts)) if frequency == "monthly" else quarter_range(min(starts), max(starts))
    period_fn = month_start if frequency == "monthly" else quarter_start
    label_fn = month_label if frequency == "monthly" else quarter_label
    grouped: dict[date, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        start = parse_date(clean(row.get("project_start_date", "")))
        if start:
            grouped[period_fn(start)].append(row)
    cohort_rows: list[dict[str, object]] = []
    for period in periods:
        selected = grouped.get(period, [])
        n = len(selected)
        out_row = {
            "period": label_fn(period),
            "period_start": period.isoformat(),
            "frequency": frequency,
            "applications_started": n,
            "post_july2024_period": int(period >= BREAK_MONTH),
            "exact_post_july2024_applications": sum(1 for row in selected if clean(row.get("post_july2024", "")) == "1"),
        }
        for key in ["strict_21", "main_27", "archived_broad_48", "final_expanded"]:
            leak_col = f"leak_{key}" if key != "archived_broad_48" else "leak_archived_broad_48"
            events = sum(int(row[leak_col]) for row in selected)
            out_row[f"{key}_leakage_risk_applications"] = events
            out_row[f"{key}_leakage_rate"] = fmt(events / n, 8) if n else ""
            out_row[f"{key}_leakage_rate_percent"] = fmt(100 * events / n, 5) if n else ""
        cohort_rows.append(out_row)
    fields = [
        "period",
        "period_start",
        "frequency",
        "applications_started",
        "post_july2024_period",
        "exact_post_july2024_applications",
        "strict_21_leakage_risk_applications",
        "strict_21_leakage_rate",
        "strict_21_leakage_rate_percent",
        "main_27_leakage_risk_applications",
        "main_27_leakage_rate",
        "main_27_leakage_rate_percent",
        "archived_broad_48_leakage_risk_applications",
        "archived_broad_48_leakage_rate",
        "archived_broad_48_leakage_rate_percent",
        "final_expanded_leakage_risk_applications",
        "final_expanded_leakage_rate",
        "final_expanded_leakage_rate_percent",
    ]
    write_csv(out.monthly_cohorts if frequency == "monthly" else out.quarterly_cohorts, cohort_rows, fields)
    return cohort_rows


def its_design(periods: list[date], frequency: str) -> tuple[list[list[float]], list[str]]:
    if frequency == "monthly":
        names = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"] + [f"month_{m:02d}" for m in range(2, 13)]
        start = periods[0]
        X = []
        for period in periods:
            post = 1.0 if period >= BREAK_MONTH else 0.0
            time_after = float(max(0, months_between(BREAK_MONTH, period))) if post else 0.0
            X.append(
                [1.0, float(months_between(start, period)), post, time_after]
                + [1.0 if period.month == m else 0.0 for m in range(2, 13)]
            )
        return X, names
    names = ["Intercept", "Time", "PostJuly2024", "TimeAfterJuly2024"] + [f"quarter_{q}" for q in range(2, 5)]
    start = periods[0]
    X = []
    for period in periods:
        post = 1.0 if period >= BREAK_MONTH else 0.0
        time_after = float(max(0, months_between(BREAK_MONTH, period) // 3)) if post else 0.0
        q = ((period.month - 1) // 3) + 1
        X.append([1.0, float(months_between(start, period) // 3), post, time_after] + [1.0 if q == val else 0.0 for val in range(2, 5)])
    return X, names


def fit_cohort_its(
    cohort_rows: list[dict[str, object]],
    frequency: str,
    out: Outputs,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    leakage_samples = ["strict_21", "main_27", "archived_broad_48", "final_expanded"]
    sample_windows = [
        ("primary_2019_2025", PRIMARY_START, PRIMARY_END),
        ("drop_recent_12m", PRIMARY_START, date(2025, 8, 1) if frequency == "monthly" else date(2025, 7, 1)),
    ]
    results: list[dict[str, object]] = []
    saved: dict[str, dict[str, object]] = {}
    for sample_name, start, end in sample_windows:
        selected_rows = [
            row
            for row in cohort_rows
            if start <= parse_date(clean(row["period_start"])) <= end and int(row["applications_started"]) > 0
        ]
        periods = [parse_date(clean(row["period_start"])) for row in selected_rows]
        periods = [period for period in periods if period]
        X, names = its_design(periods, frequency)
        lag = HAC_LAG_MONTHLY if frequency == "monthly" else HAC_LAG_QUARTERLY
        for leakage_sample in leakage_samples:
            y = [
                int(row[f"{leakage_sample}_leakage_risk_applications"]) / int(row["applications_started"])
                for row in selected_rows
            ]
            counts = [float(row[f"{leakage_sample}_leakage_risk_applications"]) for row in selected_rows]
            offsets = [math.log(float(row["applications_started"])) for row in selected_rows]
            try:
                fit = ols(X, y, hac_lag=lag)
                key = f"{frequency}:{sample_name}:{leakage_sample}:ols"
                saved[key] = {"periods": periods, "names": names, "fit": fit, "rows": selected_rows}
                for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
                    idx = names.index(term)
                    beta = float(fit["beta"][idx])
                    se = float(fit["se"][idx])
                    results.append(
                        {
                            "frequency": frequency,
                            "linkage_sample": leakage_sample,
                            "application_sample": sample_name,
                            "model": "OLS rate segmented ITS",
                            "coefficient": term,
                            "n_periods": len(selected_rows),
                            "estimate": fmt(beta, 8),
                            "estimate_percentage_points": fmt(100 * beta, 4),
                            "std_error": fmt(se, 8),
                            "std_error_percentage_points": fmt(100 * se, 4),
                            "p_value": fmt(normal_pvalue(beta, se), 6),
                            "ci_low": fmt(beta - 1.96 * se, 8),
                            "ci_high": fmt(beta + 1.96 * se, 8),
                            "irr": "",
                            "inference": fit["inference"],
                            "warning": "",
                        }
                    )
            except Exception as exc:
                for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
                    results.append(
                        {
                            "frequency": frequency,
                            "linkage_sample": leakage_sample,
                            "application_sample": sample_name,
                            "model": "OLS rate segmented ITS",
                            "coefficient": term,
                            "n_periods": len(selected_rows),
                            "estimate": "",
                            "estimate_percentage_points": "",
                            "std_error": "",
                            "std_error_percentage_points": "",
                            "p_value": "",
                            "ci_low": "",
                            "ci_high": "",
                            "irr": "",
                            "inference": "",
                            "warning": str(exc),
                        }
                    )
            try:
                pfit = poisson_qmle(X, counts, offset=offsets, hac_lag=lag)
                key = f"{frequency}:{sample_name}:{leakage_sample}:poisson"
                saved[key] = {"periods": periods, "names": names, "fit": pfit, "rows": selected_rows}
                for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
                    idx = names.index(term)
                    beta = float(pfit["beta"][idx])
                    se = float(pfit["se"][idx])
                    results.append(
                        {
                            "frequency": frequency,
                            "linkage_sample": leakage_sample,
                            "application_sample": sample_name,
                            "model": "Poisson QMLE count/rate ITS with log(N_t) offset",
                            "coefficient": term,
                            "n_periods": len(selected_rows),
                            "estimate": fmt(beta, 8),
                            "estimate_percentage_points": "",
                            "std_error": fmt(se, 8),
                            "std_error_percentage_points": "",
                            "p_value": fmt(normal_pvalue(beta, se), 6),
                            "ci_low": fmt(beta - 1.96 * se, 8),
                            "ci_high": fmt(beta + 1.96 * se, 8),
                            "irr": fmt(math.exp(beta), 6),
                            "inference": pfit["inference"] + f"; Pearson dispersion {pfit['pearson_dispersion']:.3f}",
                            "warning": "" if pfit["converged"] else "did_not_meet_strict_convergence_tolerance",
                        }
                    )
            except Exception as exc:
                for term in ["Time", "PostJuly2024", "TimeAfterJuly2024"]:
                    results.append(
                        {
                            "frequency": frequency,
                            "linkage_sample": leakage_sample,
                            "application_sample": sample_name,
                            "model": "Poisson QMLE count/rate ITS with log(N_t) offset",
                            "coefficient": term,
                            "n_periods": len(selected_rows),
                            "estimate": "",
                            "estimate_percentage_points": "",
                            "std_error": "",
                            "std_error_percentage_points": "",
                            "p_value": "",
                            "ci_low": "",
                            "ci_high": "",
                            "irr": "",
                            "inference": "",
                            "warning": str(exc),
                        }
                    )
    fields = [
        "frequency",
        "linkage_sample",
        "application_sample",
        "model",
        "coefficient",
        "n_periods",
        "estimate",
        "estimate_percentage_points",
        "std_error",
        "std_error_percentage_points",
        "p_value",
        "ci_low",
        "ci_high",
        "irr",
        "inference",
        "warning",
    ]
    write_csv(out.monthly_its_table if frequency == "monthly" else out.quarterly_its_table, results, fields)
    return results, saved


def build_sensitivity_table(prepost: list[dict[str, object]], monthly_its: list[dict[str, object]], quarterly_its: list[dict[str, object]], out: Outputs) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for pp in prepost:
        if pp["application_sample"] != "full_start_date_universe":
            continue
        if pp["linkage_sample"] not in {"strict_21", "main_27", "archived_broad_48", "final_expanded"}:
            continue
        rows.append(
            {
                "comparison": "pre_post_descriptive",
                "linkage_sample": pp["linkage_sample"],
                "estimate_type": "post_minus_pre_percentage_points",
                "estimate": pp["difference_percentage_points"],
                "p_value": pp["two_proportion_p_value"],
                "n": int(pp["pre_applications"]) + int(pp["post_applications"]),
                "note": "Application-level pre/post comparison using exact 2024-07-05 start-date cutoff.",
            }
        )
    for source, label in [(monthly_its, "monthly_its"), (quarterly_its, "quarterly_its")]:
        for result in source:
            if (
                result.get("application_sample") == "primary_2019_2025"
                and result.get("model") == "OLS rate segmented ITS"
                and result.get("coefficient") in {"PostJuly2024", "TimeAfterJuly2024"}
            ):
                rows.append(
                    {
                        "comparison": label,
                        "linkage_sample": result["linkage_sample"],
                        "estimate_type": str(result["coefficient"]) + "_percentage_points",
                        "estimate": result.get("estimate_percentage_points", ""),
                        "p_value": result.get("p_value", ""),
                        "n": result.get("n_periods", ""),
                        "note": "OLS cohort leakage-rate ITS; time axis is application start cohort.",
                    }
                )
    write_csv(out.sensitivity_table, rows, ["comparison", "linkage_sample", "estimate_type", "estimate", "p_value", "n", "note"])
    return rows


def xscale(period: date, start: date, end: date, left: float, width: float) -> float:
    return left + (period - start).days / max((end - start).days, 1) * width


def write_svg_time_chart(
    path: Path,
    title: str,
    series: list[tuple[date, float, str]],
    y_label: str,
    start: date,
    end: date,
    y_min: float = 0.0,
    y_max: float | None = None,
    bars: bool = False,
) -> None:
    width, height = 1060, 520
    left, right, top, bottom = 86, 44, 52, 64
    plot_w, plot_h = width - left - right, height - top - bottom
    values = [value for _, value, _ in series] or [0.0]
    hi = max(values) if y_max is None else y_max
    if hi <= y_min:
        hi = y_min + 1.0
    hi = hi * 1.12

    def x(period: date) -> float:
        return xscale(period, start, end, left, plot_w)

    def y(value: float) -> float:
        return top + (hi - value) / (hi - y_min) * plot_h

    colors = {
        "final_expanded": "#24536b",
        "archived_broad_48": "#5c6f68",
        "strict_21": "#8f3e46",
        "main_27": "#52796f",
        "observed": "#24536b",
        "fitted": "#9a4d2f",
    }
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="29" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="700">{html.escape(title)}</text>',
    ]
    break_x = x(BREAK_MONTH)
    svg.append(f'<line x1="{break_x:.1f}" y1="{top}" x2="{break_x:.1f}" y2="{height-bottom}" stroke="#111" stroke-width="2"/>')
    svg.append(f'<text x="{break_x+7:.1f}" y="{top+16}" font-family="Arial, sans-serif" font-size="11" fill="#111">Jul 2024</text>')
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        val = y_min + frac * (hi - y_min)
        yy = y(val)
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#dedede"/>')
        svg.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#444">{val:.2f}</text>')
    for year in range(start.year, end.year + 1):
        xx = x(date(year, 1, 1))
        svg.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{height-bottom}" stroke="#eeeeee"/>')
        svg.append(f'<text x="{xx:.1f}" y="{height-30}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#444">{year}</text>')
    grouped: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for period, value, label in series:
        grouped[label].append((period, value))
    if bars:
        bar_w = max(2.0, plot_w / max(len({period for period, _, _ in series}), 1) * 0.68)
        for label, points in grouped.items():
            color = colors.get(label, "#24536b")
            for period, value in points:
                px = x(period) - bar_w / 2
                py = y(value)
                svg.append(
                    f'<rect x="{px:.1f}" y="{py:.1f}" width="{bar_w:.1f}" height="{height-bottom-py:.1f}" fill="{color}" opacity="0.78"/>'
                )
    else:
        for label, points in grouped.items():
            color = colors.get(label, "#24536b")
            pts = " ".join(f"{x(period):.1f},{y(value):.1f}" for period, value in points)
            dash = ' stroke-dasharray="5 4"' if label == "fitted" else ""
            svg.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.4"{dash} points="{pts}"/>')
            for period, value in points:
                svg.append(f'<circle cx="{x(period):.1f}" cy="{y(value):.1f}" r="2.6" fill="{color}"/>')
    legend_x = width - right - 230
    legend_y = top + 12
    for i, label in enumerate(grouped):
        yy = legend_y + i * 18
        color = colors.get(label, "#24536b")
        svg.append(f'<line x1="{legend_x}" y1="{yy}" x2="{legend_x+26}" y2="{yy}" stroke="{color}" stroke-width="3"/>')
        svg.append(f'<text x="{legend_x+34}" y="{yy+4}" font-family="Arial, sans-serif" font-size="12" fill="#333">{html.escape(label)}</text>')
    svg.append(f'<text x="18" y="{top + plot_h/2}" transform="rotate(-90 18 {top + plot_h/2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">{html.escape(y_label)}</text>')
    svg.append(
        f'<text x="{left}" y="{height-8}" font-family="Arial, sans-serif" font-size="11" fill="#333">Time axis is application/project start cohort; DMCA notice date is not used as the outcome date.</text>'
    )
    svg.append("</svg>")
    write_text(path, "\n".join(svg))


def write_svg_year_distribution(path: Path, leak_rows: list[dict[str, object]]) -> None:
    counts = Counter(int(row["project_start_year"]) for row in leak_rows if clean(row.get("project_start_year", "")))
    years = list(range(min(counts), max(counts) + 1))
    width, height = 900, 480
    left, right, top, bottom = 74, 36, 48, 62
    plot_w, plot_h = width - left - right, height - top - bottom
    y_max = max(counts.values()) if counts else 1
    bar_w = plot_w / max(len(years), 1) * 0.62

    def x(i: int) -> float:
        return left + (i + 0.5) * plot_w / max(len(years), 1)

    def y(value: float) -> float:
        return top + (y_max * 1.15 - value) / (y_max * 1.15) * plot_h

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width/2}" y="28" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="700">Start-Year Distribution Of Final Expanded Leakage-Risk Applications</text>',
    ]
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        val = frac * y_max * 1.15
        yy = y(val)
        svg.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}" stroke="#dedede"/>')
        svg.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#444">{val:.0f}</text>')
    for i, year in enumerate(years):
        value = counts.get(year, 0)
        px = x(i) - bar_w / 2
        py = y(value)
        color = "#8f3e46" if year >= 2024 else "#24536b"
        svg.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{bar_w:.1f}" height="{height-bottom-py:.1f}" fill="{color}" opacity="0.84"/>')
        svg.append(f'<text x="{x(i):.1f}" y="{height-34}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#444">{year}</text>')
    svg.append(f'<text x="18" y="{top+plot_h/2}" transform="rotate(-90 18 {top+plot_h/2})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12">Applications</text>')
    svg.append(f'<text x="{left}" y="{height-8}" font-family="Arial, sans-serif" font-size="11" fill="#333">Red bars start in 2024 or later; exact post-policy classification uses 2024-07-05.</text>')
    svg.append("</svg>")
    write_text(path, "\n".join(svg))


def write_figures(
    app_rows: list[dict[str, object]],
    monthly_rows: list[dict[str, object]],
    quarterly_rows: list[dict[str, object]],
    saved_its: dict[str, dict[str, object]],
    out: Outputs,
) -> None:
    leak_rows = [row for row in app_rows if row["leak_final_expanded"] == 1]
    write_svg_year_distribution(out.start_distribution_figure, leak_rows)
    months = [parse_date(clean(row["period_start"])) for row in monthly_rows]
    months = [month for month in months if month and PRIMARY_START <= month <= PRIMARY_END]
    month_lookup = {parse_date(clean(row["period_start"])): row for row in monthly_rows}
    write_svg_time_chart(
        out.monthly_count_figure,
        "Monthly Count Of Final Expanded Leakage-Risk Applications By Start Cohort",
        [(month, float(month_lookup[month]["final_expanded_leakage_risk_applications"]), "final_expanded") for month in months],
        "Leakage-risk applications",
        PRIMARY_START,
        PRIMARY_END,
        bars=True,
    )
    write_svg_time_chart(
        out.monthly_rate_figure,
        "Monthly Final Expanded Leakage Rate By Application-Start Cohort",
        [(month, float(month_lookup[month]["final_expanded_leakage_rate_percent"] or 0.0), "final_expanded") for month in months],
        "Leakage rate (%)",
        PRIMARY_START,
        PRIMARY_END,
    )
    quarters = [parse_date(clean(row["period_start"])) for row in quarterly_rows]
    quarters = [quarter for quarter in quarters if quarter and PRIMARY_START <= quarter <= PRIMARY_END]
    quarter_lookup = {parse_date(clean(row["period_start"])): row for row in quarterly_rows}
    write_svg_time_chart(
        out.quarterly_rate_figure,
        "Quarterly Final Expanded Leakage Rate By Application-Start Cohort",
        [(quarter, float(quarter_lookup[quarter]["final_expanded_leakage_rate_percent"] or 0.0), "final_expanded") for quarter in quarters],
        "Leakage rate (%)",
        PRIMARY_START,
        PRIMARY_END,
    )
    saved_key = "monthly:primary_2019_2025:final_expanded:ols"
    fit_info = saved_its[saved_key]
    periods = fit_info["periods"]
    fit = fit_info["fit"]
    rows = fit_info["rows"]
    series = []
    for period, row, fitted in zip(periods, rows, fit["fitted"]):
        series.append((period, float(row["final_expanded_leakage_rate_percent"] or 0.0), "observed"))
        series.append((period, 100.0 * float(fitted), "fitted"))
    write_svg_time_chart(
        out.its_fitted_figure,
        "Monthly Segmented ITS Fit For Final Expanded Leakage Rate",
        series,
        "Leakage rate (%)",
        PRIMARY_START,
        PRIMARY_END,
    )


def markdown_table(rows: list[dict[str, object]], columns: list[str], labels: dict[str, str] | None = None) -> str:
    labels = labels or {}
    lines = ["| " + " | ".join(labels.get(col, col) for col in columns) + " |"]
    lines.append("| " + " | ".join(["---" for _ in columns]) + " |")
    for row in rows:
        lines.append("| " + " | ".join(clean(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def selected_result(rows: list[dict[str, object]], **criteria: str) -> dict[str, object]:
    for row in rows:
        if all(clean(row.get(key, "")) == value for key, value in criteria.items()):
            return row
    raise KeyError(criteria)


def optional_result(rows: list[dict[str, object]], **criteria: str) -> dict[str, object] | None:
    for row in rows:
        if all(clean(row.get(key, "")) == value for key, value in criteria.items()):
            return row
    return None


def has_field(row: dict[str, object] | None, field: str) -> bool:
    return row is not None and clean(row.get(field, "")) != ""


def write_linkage_report(
    summary: dict[str, object],
    remaining: list[dict[str, object]],
    out: Outputs,
) -> None:
    del remaining
    review_rows = [
        {
            "repo_family": row["review_unit_id"],
            "evidence_found": row["evidence_type"],
            "application_id": row["final_application_id"] or row["candidate_application_ids"],
            "confidence": row["confidence"],
            "reason": row["review_notes"],
            "final_status": row["review_status"],
        }
        for row in REMAINING_23_REVIEWS
    ]
    new_app_rows = [
        {
            "application_id": row["final_application_id"],
            "repo_family": row["review_unit_id"],
            "confidence": row["confidence"],
            "evidence_chain": row["review_notes"],
            "public_urls": row["evidence_urls"],
        }
        for row in REMAINING_23_REVIEWS
        if row["final_sample_action"] == "add_new_application"
    ]
    report = f"""# Curated DMCA-Application Linkage Report

## Scope

This report completes the remaining repository/family linkage review for the application-level leakage analysis. The current `ukb_dmca` repository output remains the reproducible public DMCA audit snapshot. The manually curated empirical crosswalk is separate: the 48 previously researcher-confirmed applications are retained as the fixed baseline, and the 23 remaining repository/family units are reviewed as an expansion layer.

## Reconciliation Summary

| metric | value |
| --- | ---: |
| UKB DMCA notices in current snapshot | {summary['current_dmca_notice_count']} |
| Current repository lineages | {summary['current_dmca_repository_lineages']} |
| Curated repository families after conservative basename grouping | {summary['curated_repository_families']} |
| Previously confirmed baseline applications | {summary['manual_archived_linked_applications_before_task']} |
| Archived manual named lineages before this task | {summary['manual_archived_named_lineages_before_task']} |
| Remaining repository/family units reviewed | {summary['remaining_23_review_rows']} |
| Remaining units successfully linked | {summary['remaining_23_successfully_linked_families']} |
| Remaining units linked to existing baseline apps | {summary['remaining_23_linked_existing_baseline_families']} |
| Remaining units adding new apps | {summary['remaining_23_new_application_families']} |
| Remaining units unresolved/ambiguous/excluded | {summary['remaining_23_unresolved_or_ambiguous_families']} |
| New unique applications from remaining review | {summary['new_unique_applications_from_remaining_23']} |
| Final unique leakage-risk applications | {summary['final_unique_linked_applications_expanded']} |
| Final named linked repository lineages | {summary['final_named_linked_lineages']} |
| Application-only manual rows without lineage IDs in current audit | {summary['application_only_manual_rows']} |
| Remaining unmatched/ambiguous repository families | {summary['remaining_unmatched_repository_families']} |

Automated-only current applications not added to the empirical outcome: {', '.join(summary['automated_current_only_applications_not_added']) or 'none'}.

## Remaining 23 Review Table

{markdown_table(review_rows, ['repo_family', 'evidence_found', 'application_id', 'confidence', 'reason', 'final_status'], {'repo_family': 'Repo/family', 'evidence_found': 'Evidence found', 'application_id': 'Application ID', 'confidence': 'Confidence', 'reason': 'Reason', 'final_status': 'Final status'})}

## New Application Evidence Chains

{markdown_table(new_app_rows, ['application_id', 'repo_family', 'confidence', 'evidence_chain', 'public_urls'], {'application_id': 'Application ID', 'repo_family': 'Repo/family', 'confidence': 'Confidence', 'evidence_chain': 'Evidence chain', 'public_urls': 'Public URLs'})}

## Notes

- `ukb_dmca/remaining_23_repo_review.csv` contains exactly one row for each of the 23 remaining repository/family units from the historical manual exercise.
- `ukb_dmca/curated_dmca_application_links.csv` is the canonical application-level crosswalk. It contains one row per final leakage-risk application and preserves all 48 researcher-confirmed baseline applications with `manual_confirmation_status=confirmed_by_researcher`.
- `ukb_dmca/curated_dmca_repository_family_links.csv` keeps the repository/family evidence layer separate from the application-level outcome.
- The current audit contains 193 self-repository lineages. The historical manual matching exercise worked at a more aggregated repository/family level; this report preserves that 23-unit completion queue rather than replacing it with all current lineage rows.
- No DMCA notice date, targeted commit date, or repository commit date is used to classify applications as pre- or post-July 2024.
"""
    write_text(out.ukb_linkage_report, report)


def write_stata_style_tables(
    prepost: list[dict[str, object]],
    app_lpm: list[dict[str, object]],
    monthly_its: list[dict[str, object]],
    quarterly_its: list[dict[str, object]],
    out: Outputs,
) -> None:
    pp = selected_result(prepost, linkage_sample="final_expanded", application_sample="full_start_date_universe")
    lpm = selected_result(
        app_lpm,
        linkage_sample="final_expanded",
        application_sample="full_start_date_universe",
        model="LPM: Leak_i on PostJuly2024_i",
        coefficient="PostJuly2024",
    )
    lpm_trend = selected_result(
        app_lpm,
        linkage_sample="final_expanded",
        application_sample="full_start_date_universe",
        model="LPM: plus smooth start-month trend",
        coefficient="PostJuly2024",
    )
    monthly_post = selected_result(
        monthly_its,
        frequency="monthly",
        linkage_sample="final_expanded",
        application_sample="primary_2019_2025",
        model="OLS rate segmented ITS",
        coefficient="PostJuly2024",
    )
    monthly_slope = selected_result(
        monthly_its,
        frequency="monthly",
        linkage_sample="final_expanded",
        application_sample="primary_2019_2025",
        model="OLS rate segmented ITS",
        coefficient="TimeAfterJuly2024",
    )
    quarterly_post = selected_result(
        quarterly_its,
        frequency="quarterly",
        linkage_sample="final_expanded",
        application_sample="primary_2019_2025",
        model="OLS rate segmented ITS",
        coefficient="PostJuly2024",
    )
    quarterly_slope = selected_result(
        quarterly_its,
        frequency="quarterly",
        linkage_sample="final_expanded",
        application_sample="primary_2019_2025",
        model="OLS rate segmented ITS",
        coefficient="TimeAfterJuly2024",
    )
    text = f"""Leakage-Risk Application ITS: Stata-Style Summary

Outcome language: applications subsequently linked to observed leakage exposure.
Timing variable: UKB application/project start date.
Policy cutoff: {POLICY_DATE.isoformat()}.

Pre/Post Descriptive, Final Expanded Sample
    Pre applications              {pp['pre_applications']}
    Pre leakage-risk apps          {pp['pre_leakage_risk_applications']}
    Pre leakage rate (%)           {pp['pre_leakage_rate_percent']}
    Post applications             {pp['post_applications']}
    Post leakage-risk apps         {pp['post_leakage_risk_applications']}
    Post leakage rate (%)          {pp['post_leakage_rate_percent']}
    Difference, post-pre (pp)      {pp['difference_percentage_points']}
    Ratio, post/pre                {pp['ratio_post_pre']}
    Two-proportion p-value         {pp['two_proportion_p_value']}

Application-Level LPM, Final Expanded Sample
    PostJuly2024, raw (pp)         {lpm['estimate_percentage_points']}   SE {lpm['robust_se_percentage_points']}   p {lpm['p_value']}
    PostJuly2024, trend (pp)       {lpm_trend['estimate_percentage_points']}   SE {lpm_trend['robust_se_percentage_points']}   p {lpm_trend['p_value']}

Application-Start-Cohort ITS, Final Expanded Sample
    Monthly level break (pp)       {monthly_post['estimate_percentage_points']}   SE {monthly_post['std_error_percentage_points']}   p {monthly_post['p_value']}
    Monthly slope break (pp/mo)    {monthly_slope['estimate_percentage_points']}   SE {monthly_slope['std_error_percentage_points']}   p {monthly_slope['p_value']}
    Quarterly level break (pp)     {quarterly_post['estimate_percentage_points']}   SE {quarterly_post['std_error_percentage_points']}   p {quarterly_post['p_value']}
    Quarterly slope break (pp/qtr) {quarterly_slope['estimate_percentage_points']}   SE {quarterly_slope['std_error_percentage_points']}   p {quarterly_slope['p_value']}
"""
    write_text(out.stata_style_tables, text)


def write_results_report(
    summary: dict[str, object],
    prepost: list[dict[str, object]],
    app_lpm: list[dict[str, object]],
    robust: list[dict[str, object]],
    monthly_its: list[dict[str, object]],
    quarterly_its: list[dict[str, object]],
    sensitivity: list[dict[str, object]],
    max_start: date,
    drop_cutoff: date,
    out: Outputs,
) -> None:
    pp_expanded = selected_result(prepost, linkage_sample="final_expanded", application_sample="full_start_date_universe")
    pp_broad = selected_result(prepost, linkage_sample="archived_broad_48", application_sample="full_start_date_universe")
    pp_strict = selected_result(prepost, linkage_sample="strict_21", application_sample="full_start_date_universe")
    pp_drop = selected_result(prepost, linkage_sample="final_expanded", application_sample="drop_recent_12m")
    lpm_raw = selected_result(app_lpm, linkage_sample="final_expanded", application_sample="full_start_date_universe", model="LPM: Leak_i on PostJuly2024_i", coefficient="PostJuly2024")
    lpm_trend = selected_result(app_lpm, linkage_sample="final_expanded", application_sample="full_start_date_universe", model="LPM: plus smooth start-month trend", coefficient="PostJuly2024")
    logit = selected_result(robust, linkage_sample="final_expanded", application_sample="full_start_date_universe", model="Logit: Leak_i on PostJuly2024_i", coefficient="PostJuly2024")
    monthly_level = selected_result(monthly_its, frequency="monthly", linkage_sample="final_expanded", application_sample="primary_2019_2025", model="OLS rate segmented ITS", coefficient="PostJuly2024")
    monthly_slope = selected_result(monthly_its, frequency="monthly", linkage_sample="final_expanded", application_sample="primary_2019_2025", model="OLS rate segmented ITS", coefficient="TimeAfterJuly2024")
    monthly_pois_level = optional_result(monthly_its, frequency="monthly", linkage_sample="final_expanded", application_sample="primary_2019_2025", model="Poisson QMLE count/rate ITS with log(N_t) offset", coefficient="PostJuly2024")
    monthly_pois_slope = optional_result(monthly_its, frequency="monthly", linkage_sample="final_expanded", application_sample="primary_2019_2025", model="Poisson QMLE count/rate ITS with log(N_t) offset", coefficient="TimeAfterJuly2024")
    quarterly_level = selected_result(quarterly_its, frequency="quarterly", linkage_sample="final_expanded", application_sample="primary_2019_2025", model="OLS rate segmented ITS", coefficient="PostJuly2024")
    quarterly_slope = selected_result(quarterly_its, frequency="quarterly", linkage_sample="final_expanded", application_sample="primary_2019_2025", model="OLS rate segmented ITS", coefficient="TimeAfterJuly2024")
    quarterly_pois_level = optional_result(quarterly_its, frequency="quarterly", linkage_sample="final_expanded", application_sample="primary_2019_2025", model="Poisson QMLE count/rate ITS with log(N_t) offset", coefficient="PostJuly2024")
    quarterly_pois_slope = optional_result(quarterly_its, frequency="quarterly", linkage_sample="final_expanded", application_sample="primary_2019_2025", model="Poisson QMLE count/rate ITS with log(N_t) offset", coefficient="TimeAfterJuly2024")

    if has_field(monthly_pois_level, "irr") and has_field(monthly_pois_slope, "irr"):
        poisson_sentence = (
            "The count/rate Poisson QMLE, using `D_t` with `log(N_t)` as an offset, "
            f"gives an immediate-level IRR of {monthly_pois_level['irr']} and a post-slope IRR of "
            f"{monthly_pois_slope['irr']} per month."
        )
    elif has_field(quarterly_pois_level, "irr") and has_field(quarterly_pois_slope, "irr"):
        monthly_warning = clean((monthly_pois_level or monthly_pois_slope or {}).get("warning", "")) or "no identified monthly Poisson fit"
        quarterly_warning = clean(quarterly_pois_level.get("warning", "")) or clean(quarterly_pois_slope.get("warning", ""))
        warning_text = f" The quarterly Poisson row carries this warning: `{quarterly_warning}`." if quarterly_warning else ""
        poisson_sentence = (
            "The monthly count/rate Poisson QMLE, using `D_t` with `log(N_t)` as an offset, "
            f"is not reported because the sparse monthly event series produced `{monthly_warning}`. "
            f"As the count/rate robustness check on quarterly application cohorts, Poisson QMLE gives an "
            f"immediate-level IRR of {quarterly_pois_level['irr']} and a post-slope IRR of "
            f"{quarterly_pois_slope['irr']} per quarter.{warning_text}"
        )
    else:
        poisson_warning = clean((monthly_pois_level or monthly_pois_slope or quarterly_pois_level or quarterly_pois_slope or {}).get("warning", ""))
        poisson_sentence = (
            "The count/rate Poisson QMLE robustness check could not be estimated cleanly from these sparse "
            f"event cohorts. The recorded warning is `{poisson_warning or 'unavailable'}`."
        )

    prepost_rows = [
        {
            "sample": "strict_21",
            "pre": f"{pp_strict['pre_leakage_risk_applications']}/{pp_strict['pre_applications']} ({pp_strict['pre_leakage_rate_percent']}%)",
            "post": f"{pp_strict['post_leakage_risk_applications']}/{pp_strict['post_applications']} ({pp_strict['post_leakage_rate_percent']}%)",
            "diff_pp": pp_strict["difference_percentage_points"],
            "p": pp_strict["two_proportion_p_value"],
        },
        {
            "sample": "archived_broad_48",
            "pre": f"{pp_broad['pre_leakage_risk_applications']}/{pp_broad['pre_applications']} ({pp_broad['pre_leakage_rate_percent']}%)",
            "post": f"{pp_broad['post_leakage_risk_applications']}/{pp_broad['post_applications']} ({pp_broad['post_leakage_rate_percent']}%)",
            "diff_pp": pp_broad["difference_percentage_points"],
            "p": pp_broad["two_proportion_p_value"],
        },
        {
            "sample": "final_expanded",
            "pre": f"{pp_expanded['pre_leakage_risk_applications']}/{pp_expanded['pre_applications']} ({pp_expanded['pre_leakage_rate_percent']}%)",
            "post": f"{pp_expanded['post_leakage_risk_applications']}/{pp_expanded['post_applications']} ({pp_expanded['post_leakage_rate_percent']}%)",
            "diff_pp": pp_expanded["difference_percentage_points"],
            "p": pp_expanded["two_proportion_p_value"],
        },
        {
            "sample": "final_expanded_drop_recent_12m",
            "pre": f"{pp_drop['pre_leakage_risk_applications']}/{pp_drop['pre_applications']} ({pp_drop['pre_leakage_rate_percent']}%)",
            "post": f"{pp_drop['post_leakage_risk_applications']}/{pp_drop['post_applications']} ({pp_drop['post_leakage_rate_percent']}%)",
            "diff_pp": pp_drop["difference_percentage_points"],
            "p": pp_drop["two_proportion_p_value"],
        },
    ]
    sensitivity_preview = [row for row in sensitivity if row["comparison"] == "pre_post_descriptive"]
    sensitivity_preview = sensitivity_preview[:4]
    report = f"""# Leakage-Risk Application ITS Results

This module studies whether UK Biobank applications initiated after the July 2024 RAP transition are less likely to be subsequently linked to observed leakage exposure. DMCA is used only as an ex post public evidence source for application linkage. The analysis time variable is the UKB application/project start date.

## 1. Credibly Identified Leakage-Risk Applications

The final expanded canonical application sample contains {summary['final_unique_linked_applications_expanded']} applications: the researcher-confirmed broad baseline of 48 plus {summary['new_unique_applications_from_remaining_23']} new unique applications from the remaining-23 public-evidence review. The strict archived sample contains 21 applications and the main archived sample contains 27 applications. At the repository-evidence level, the current audit has {summary['current_dmca_repository_lineages']} self-repository lineages, conservatively grouped into {summary['curated_repository_families']} repository families; {summary['final_named_linked_lineages']} named lineages are linked after reconciliation. {summary['application_only_manual_rows']} baseline applications remain application-only lower-bound rows because the current local audit files do not carry lineage IDs for them.

## 2. When Those Applications Started

The final expanded leakage-risk applications are concentrated before the policy date. In the full start-dated application universe, {pp_expanded['pre_leakage_risk_applications']} final leakage-risk applications started before {POLICY_DATE.isoformat()} and {pp_expanded['post_leakage_risk_applications']} started on or after that date. The leakage-risk application table is saved at `data/leakage_risk_applications.csv`, with project start month/year and exact `post_july2024` coding.

## 3-5. Raw Pre/Post Comparison

{markdown_table(prepost_rows, ['sample', 'pre', 'post', 'diff_pp', 'p'], {'sample': 'Sample', 'pre': 'Pre July 2024', 'post': 'Post July 2024', 'diff_pp': 'Difference pp', 'p': 'p-value'})}

For the final expanded sample, the full-universe post/pre ratio is {pp_expanded['ratio_post_pre']}. The raw difference is economically visible because the post-July 2024 leakage-risk share is about {abs(float(pp_expanded['difference_percentage_points'])):.2f} percentage points lower than the pre-transition share. This is a descriptive association, not a causal RAP effect.

## 6. Pre-Transition Trend

The application-level LPM estimates the raw final-expanded post indicator at {lpm_raw['estimate_percentage_points']} percentage points (robust SE {lpm_raw['robust_se_percentage_points']}, p = {lpm_raw['p_value']}). After adding a smooth start-month trend, the post indicator is {lpm_trend['estimate_percentage_points']} percentage points (robust SE {lpm_trend['robust_se_percentage_points']}, p = {lpm_trend['p_value']}). The logit robustness check gives an odds ratio of {logit.get('odds_ratio', '')} for post-July starts.

## 7. Level Or Slope Break Around July 2024

Monthly application-start-cohort ITS estimates the final-expanded leakage-rate level break at {monthly_level['estimate_percentage_points']} percentage points (SE {monthly_level['std_error_percentage_points']}, p = {monthly_level['p_value']}) and the slope break at {monthly_slope['estimate_percentage_points']} percentage points per month (SE {monthly_slope['std_error_percentage_points']}, p = {monthly_slope['p_value']}). {poisson_sentence}

## 8. Monthly Versus Quarterly

Quarterly ITS estimates the final-expanded level break at {quarterly_level['estimate_percentage_points']} percentage points (SE {quarterly_level['std_error_percentage_points']}, p = {quarterly_level['p_value']}) and the slope break at {quarterly_slope['estimate_percentage_points']} percentage points per quarter (SE {quarterly_slope['std_error_percentage_points']}, p = {quarterly_slope['p_value']}). Monthly and quarterly raw cohort data are saved explicitly in `data/monthly_application_start_cohorts.csv` and `data/quarterly_application_start_cohorts.csv`, including zero-leakage cohorts.

## 9. Linkage-Confidence Sensitivity

Strict, main, broad baseline, and final expanded samples are saved separately and compared in `tables/linkage_sensitivity.csv`. The qualitative pattern is similar: post-July 2024 application cohorts have fewer subsequently observed leakage-risk links, with the final expanded sample naturally giving larger pre-policy rates because it includes additional manual application-level links.

## 10. Follow-Up Limitation

Applications beginning after July 2024 are younger and have had less calendar time in which leakage exposure could become publicly observable. The outcome should therefore be read as subsequently observed leakage-risk linkage as of the current data cutoff, not as permanent lifetime leakage probability. The simple drop-recent sensitivity excludes applications started after {drop_cutoff.isoformat()} (12 months before the latest observed start date, {max_start.isoformat()}); the final-expanded post-pre difference remains {pp_drop['difference_percentage_points']} percentage points with p = {pp_drop['two_proportion_p_value']}. This does not fully solve differential follow-up.

## Outputs

- `ukb_dmca/curated_dmca_application_links.csv`
- `ukb_dmca/curated_dmca_repository_family_links.csv`
- `ukb_dmca/remaining_23_repo_review.csv`
- `ukb_dmca/remaining_unmatched_lineages.csv`
- `data/application_level_leakage.csv`
- `data/monthly_application_start_cohorts.csv`
- `data/quarterly_application_start_cohorts.csv`
- `tables/pre_post_comparison.csv`
- `tables/application_level_regressions.csv`
- `tables/monthly_its_results.csv`
- `tables/quarterly_its_results.csv`
- `figures/leakage_start_date_distribution.svg`
- `figures/leakage_monthly_counts_by_start_month.svg`
- `figures/leakage_monthly_rate_by_start_cohort.svg`
- `figures/leakage_quarterly_rate_by_start_cohort.svg`
- `figures/leakage_monthly_its_fitted_final_expanded.svg`
"""
    write_text(out.results_report, report)


def validate_outputs(out: Outputs, summary: dict[str, object]) -> None:
    required = [
        out.ukb_curated_links,
        out.ukb_repository_family_links,
        out.ukb_remaining_23_review,
        out.ukb_remaining_unmatched,
        out.curated_application_links,
        out.leakage_risk_applications,
        out.application_level,
        out.monthly_cohorts,
        out.quarterly_cohorts,
        out.strict_sample,
        out.main_sample,
        out.broad_sample,
        out.expanded_sample,
        out.prepost_table,
        out.app_lpm_table,
        out.app_robust_table,
        out.monthly_its_table,
        out.quarterly_its_table,
        out.sensitivity_table,
        out.ukb_linkage_report,
        out.results_report,
        out.start_distribution_figure,
        out.its_fitted_figure,
    ]
    for path in required:
        if not path.exists():
            raise AssertionError(f"missing output: {path}")
    if int(summary["final_unique_linked_applications_expanded"]) < len(BROAD_48):
        raise AssertionError("expanded sample dropped archived manual application links")
    app_rows = read_csv(out.ukb_curated_links)
    review_rows = read_csv(out.ukb_remaining_23_review)
    final_app_ids = {row["application_id"] for row in app_rows}
    if len(app_rows) != len(FINAL_EXPANDED_APPLICATIONS):
        raise AssertionError("canonical curated application file is not one row per final leakage-risk application")
    if not BROAD_48 <= final_app_ids:
        raise AssertionError("canonical curated application file dropped one or more researcher-confirmed baseline apps")
    if "29256" in final_app_ids:
        raise AssertionError("automated-only application 29256 must not enter the curated empirical outcome")
    if len(review_rows) != 23:
        raise AssertionError("remaining_23_repo_review.csv must contain exactly 23 rows")
    confirmed_baseline = [
        row
        for row in app_rows
        if row["application_id"] in BROAD_48 and row["manual_confirmation_status"] == "confirmed_by_researcher"
    ]
    if len(confirmed_baseline) != 48:
        raise AssertionError("the 48 baseline applications must remain confirmed_by_researcher")
    for fig in [out.start_distribution_figure, out.monthly_count_figure, out.monthly_rate_figure, out.quarterly_rate_figure, out.its_fitted_figure]:
        text = fig.read_text(encoding="utf-8")[:100]
        if "<svg" not in text:
            raise AssertionError(f"figure is not SVG: {fig}")


def build_outputs(out: Outputs = Outputs()) -> dict[str, object]:
    applications = load_applications()
    curated_rows, remaining, linked_by_sample, summary = build_curated_links(applications, out)
    link_summaries = app_link_summaries(curated_rows, linked_by_sample)
    app_rows, max_start, drop_cutoff = build_application_dataset(applications, linked_by_sample, link_summaries, out)
    prepost = build_prepost_table(app_rows, max_start, drop_cutoff, out)
    app_lpm, robust = fit_application_models(app_rows, max_start, drop_cutoff, out)
    monthly_rows = build_cohorts(app_rows, "monthly", out)
    quarterly_rows = build_cohorts(app_rows, "quarterly", out)
    monthly_its, monthly_saved = fit_cohort_its(monthly_rows, "monthly", out)
    quarterly_its, quarterly_saved = fit_cohort_its(quarterly_rows, "quarterly", out)
    sensitivity = build_sensitivity_table(prepost, monthly_its, quarterly_its, out)
    write_figures(app_rows, monthly_rows, quarterly_rows, monthly_saved | quarterly_saved, out)
    write_linkage_report(summary, remaining, out)
    write_stata_style_tables(prepost, app_lpm, monthly_its, quarterly_its, out)
    write_results_report(summary, prepost, app_lpm, robust, monthly_its, quarterly_its, sensitivity, max_start, drop_cutoff, out)
    validate_outputs(out, summary)
    summary_path = DATA_DIR / "leakage_analysis_summary.json"
    write_text(summary_path, json.dumps({**summary, "max_project_start_date": max_start.isoformat(), "drop_recent_12m_cutoff": drop_cutoff.isoformat()}, indent=2, sort_keys=True))
    return {**summary, "max_project_start_date": max_start.isoformat(), "drop_recent_12m_cutoff": drop_cutoff.isoformat()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Check required outputs after a prior run.")
    args = parser.parse_args()
    out = Outputs()
    if args.validate_only:
        summary = json.loads((DATA_DIR / "leakage_analysis_summary.json").read_text(encoding="utf-8"))
        validate_outputs(out, summary)
        return
    summary = build_outputs(out)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
