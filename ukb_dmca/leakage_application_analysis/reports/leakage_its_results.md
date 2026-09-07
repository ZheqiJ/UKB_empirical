# Leakage-Risk Application ITS Results

This module studies whether UK Biobank applications initiated after the July 2024 RAP transition are less likely to be subsequently linked to observed leakage exposure. DMCA is used only as an ex post public evidence source for application linkage. The analysis time variable is the UKB application/project start date.

## 1. Credibly Identified Leakage-Risk Applications

The final expanded canonical application sample contains 52 applications: the researcher-confirmed broad baseline of 48 plus 4 new unique applications from the remaining-23 public-evidence review. The strict archived sample contains 21 applications and the main archived sample contains 27 applications. At the repository-evidence level, the current audit has 193 self-repository lineages, conservatively grouped into 130 repository families; 47 named lineages are linked after reconciliation. 30 baseline applications remain application-only lower-bound rows because the current local audit files do not carry lineage IDs for them.

## 2. When Those Applications Started

The final expanded leakage-risk applications are concentrated before the policy date. In the full start-dated application universe, 50 final leakage-risk applications started before 2024-07-05 and 2 started on or after that date. The leakage-risk application table is saved at `data/leakage_risk_applications.csv`, with project start month/year and exact `post_july2024` coding.

## 3-5. Raw Pre/Post Comparison

| Sample | Pre July 2024 | Post July 2024 | Difference pp | p-value |
| --- | --- | --- | --- | --- |
| strict_21 | 20/4332 (0.4617%) | 1/2603 (0.0384%) | -0.4233 | 0.00189456 |
| archived_broad_48 | 46/4332 (1.0619%) | 2/2603 (0.0768%) | -0.9850 | 0.00000166 |
| final_expanded | 50/4332 (1.1542%) | 2/2603 (0.0768%) | -1.0774 | 0.00000048 |
| final_expanded_drop_recent_12m | 50/4332 (1.1542%) | 1/1507 (0.0664%) | -1.0878 | 0.00009260 |

For the final expanded sample, the full-universe post/pre ratio is 0.066569. The raw difference is economically visible because the post-July 2024 leakage-risk share is about 1.08 percentage points lower than the pre-transition share. This is a descriptive association, not a causal RAP effect.

## 6. Pre-Transition Trend

The application-level LPM estimates the raw final-expanded post indicator at -1.0774 percentage points (robust SE 0.1712, p = 0.000000). After adding a smooth start-month trend, the post indicator is -0.2389 percentage points (robust SE 0.2627, p = 0.363148). The logit robustness check gives an odds ratio of 0.065852 for post-July starts.

## 7. Level Or Slope Break Around July 2024

Monthly application-start-cohort ITS estimates the final-expanded leakage-rate level break at -0.0483 percentage points (SE 0.3010, p = 0.872589) and the slope break at 0.0514 percentage points per month (SE 0.0234, p = 0.027781). The monthly count/rate Poisson QMLE, using `D_t` with `log(N_t)` as an offset, is not reported because the sparse monthly event series produced `singular regression matrix`. As the count/rate robustness check on quarterly application cohorts, Poisson QMLE gives an immediate-level IRR of 0.000789 and a post-slope IRR of 4.953877 per quarter.

## 8. Monthly Versus Quarterly

Quarterly ITS estimates the final-expanded level break at 0.0187 percentage points (SE 0.2588, p = 0.942406) and the slope break at 0.1539 percentage points per quarter (SE 0.0413, p = 0.000194). Monthly and quarterly raw cohort data are saved explicitly in `data/monthly_application_start_cohorts.csv` and `data/quarterly_application_start_cohorts.csv`, including zero-leakage cohorts.

## 9. Linkage-Confidence Sensitivity

Strict, main, broad baseline, and final expanded samples are saved separately and compared in `tables/linkage_sensitivity.csv`. The qualitative pattern is similar: post-July 2024 application cohorts have fewer subsequently observed leakage-risk links, with the final expanded sample naturally giving larger pre-policy rates because it includes additional manual application-level links.

## 10. Follow-Up Limitation

Applications beginning after July 2024 are younger and have had less calendar time in which leakage exposure could become publicly observable. The outcome should therefore be read as subsequently observed leakage-risk linkage as of the current data cutoff, not as permanent lifetime leakage probability. The simple drop-recent sensitivity excludes applications started after 2025-08-17 (12 months before the latest observed start date, 2026-08-17); the final-expanded post-pre difference remains -1.0878 percentage points with p = 0.00009260. This does not fully solve differential follow-up.

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
