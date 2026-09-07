# Curated 52 vs Broad 55 Leakage Sensitivity

This analysis holds the UK Biobank application universe fixed at all 6,935 applications with a valid public project/application start date. It changes only the binary outcome: `Leak52` marks the existing curated 52, while `Leak55` additionally marks the three single-application ambiguous Tier-4 links. DMCA notice, repository, and commit dates are not used as empirical timing variables. All results are descriptive associations, not causal RAP effects.

## Added Tier-4 Applications

| application_id | application_title | project_start_date | pre_post_july_5_2024 | family_ids | reason_it_is_tier_4 |
| --- | --- | --- | --- | --- | --- |
| 51830 | Identifying genetic factors for brain ageing | 2019-09-30 | pre | family_keloids-clustering; family_sas-sample-extraction; family_ukb-api; family_ukb-download-and-prep-template; family_ukbb-risk; family_ukbcc | Not in Tiers 1-3; retained from a family with exactly one supported/ambiguous application. Ambiguous multi-application families are excluded from this tier. |
| 54520 | Constructing risk scores of longevity, dementia, and related disorders | 2020-02-04 | pre | family_ukb-download-and-prep-template | Not in Tiers 1-3; retained from a family with exactly one supported/ambiguous application. Ambiguous multi-application families are excluded from this tier. |
| 146079 | Epidemiological and Genetic Risk Factors for keloid and hypertrophic scar | 2024-02-27 | pre | family_keloids-clustering | Not in Tiers 1-3; retained from a family with exactly one supported/ambiguous application. Ambiguous multi-application families are excluded from this tier. |

All three additions start before July 5, 2024. The broadening therefore raises only the pre-policy leakage count in this comparison.

## 1. Raw Pre/Post Descriptive Comparison

| Outcome | Pre leakage / apps | Pre rate | Post leakage / apps | Post rate | Difference pp | 95% CI (pp) | Post/pre ratio | p-value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Leak52 | 50/4332 | 1.1542% | 2/2603 | 0.0768% | -1.0774 | [-1.4128, -0.7420] | 0.066569 | 0.00000048 |
| Leak55 | 53/4332 | 1.2235% | 2/2603 | 0.0768% | -1.1466 | [-1.4909, -0.8024] | 0.062801 | 0.00000019 |

The difference is the raw post-minus-pre percentage-point contrast. The two-proportion p-value and confidence interval are descriptive only.

## 2. Application-Level Raw LPM

| Variable | Leak52 coef (pp) | Leak52 SE (pp) | Leak52 p | Leak55 coef (pp) | Leak55 SE (pp) | Leak55 p |
| --- | --- | --- | --- | --- | --- | --- |
| PostJuly2024 | -1.0774 | 0.1712 | 3.08024e-10 | -1.1466 | 0.1757 | 6.68175e-11 |

Each raw LPM has N = 6,935 and HC1 heteroskedasticity-robust standard errors. Its Post coefficient is the same descriptive difference as the raw pre/post contrast.

## 3. Trend-Adjusted Application-Level LPM

| Variable | Leak52 coef (pp) | Leak52 SE (pp) | Leak52 p | Leak55 coef (pp) | Leak55 SE (pp) | Leak55 p |
| --- | --- | --- | --- | --- | --- | --- |
| Time | -0.0152 | 0.0051 | 0.00283478 | -0.0148 | 0.0052 | 0.0043025 |
| PostJuly2024 | -0.2389 | 0.2627 | 0.363148 | -0.3284 | 0.2735 | 0.229793 |

The raw Post coefficients are -1.0774 pp (Leak52) and -1.1466 pp (Leak55). With a smooth start-month trend, they are -0.2389 pp and -0.3284 pp. This reports how much the unadjusted difference changes after accounting for the observed start-time trend; it is not causal adjustment.

## 4. Application-Level Segmented ITS

| Variable | Leak52 coef (pp) | Leak52 SE (pp) | Leak52 p | Leak55 coef (pp) | Leak55 SE (pp) | Leak55 p |
| --- | --- | --- | --- | --- | --- | --- |
| Time | -0.0162 | 0.0053 | 0.00216663 | -0.0158 | 0.0054 | 0.00325308 |
| PostJuly2024 | -0.3070 | 0.2269 | 0.176117 | -0.3621 | 0.2340 | 0.121815 |
| TimeAfterJuly2024 | 0.0155 | 0.0125 | 0.212874 | 0.0126 | 0.0126 | 0.316759 |

This specification uses application-level `Time`, exact-date `Post`, `TimeAfter`, and month-of-year fixed effects, with HC1 robust standard errors. The level breaks are -0.3070 pp and -0.3621 pp. The slope breaks are 0.0155 and 0.0126 percentage points per month.

## 5. Monthly Application-Start Cohorts

Monthly cohort data, including zero-leakage months, are saved in `data/monthly_application_start_cohorts_curated52_broad55.csv`. The monthly rate ITS uses Newey-West HAC lag 3 and month-of-year fixed effects.

| Variable | Leak52 coef (pp) | Leak52 SE (pp) | Leak52 p | Leak55 coef (pp) | Leak55 SE (pp) | Leak55 p |
| --- | --- | --- | --- | --- | --- | --- |
| Time | -0.0055 | 0.0076 | 0.466661 | -0.0047 | 0.0076 | 0.539651 |
| PostJuly2024 | -0.8496 | 0.5475 | 0.120717 | -0.9828 | 0.5641 | 0.0814437 |
| TimeAfterJuly2024 | -0.0054 | 0.0244 | 0.826052 | -0.0050 | 0.0245 | 0.839559 |

The two single-sample rate figures and their common-scale overlay are saved in `figures/`. Monthly Poisson status: Leak52: not_estimable (did_not_meet_strict_convergence_tolerance); Leak55: not_estimable (did_not_meet_strict_convergence_tolerance). Monthly Poisson QMLE is not estimable because of sparse event counts; quarterly aggregation is used for the count/rate robustness specification.

## 6. Quarterly Count/Rate Poisson Robustness

Quarterly cohorts use `log(N_q)` as an offset, quarter-of-year fixed effects, and Newey-West HAC lag 1 robust standard errors. Values are IRRs.

| Variable | Leak52 IRR | Leak52 SE log(IRR) | Leak52 p | Leak55 IRR | Leak55 SE log(IRR) | Leak55 p |
| --- | --- | --- | --- | --- | --- | --- |
| Time | 0.964973 | 0.01097043 | 0.00115369 | 0.967297 | 0.01042674 | 0.00142806 |
| PostJuly2024 | 0.034224 | 1.12479214 | 0.00269619 | 0.032256 | 1.13535104 | 0.00248902 |
| TimeAfterJuly2024 | 1.430601 | 0.23344486 | 0.12504 | 1.411102 | 0.23689714 | 0.146037 |

## Final Comparison

| Result | Leak52 | Leak55 | Materially different? |
| --- | --- | --- | --- |
| Raw pre/post difference | -1.0774 pp | -1.1466 pp | No |
| Raw LPM Post | -1.0774 pp | -1.1466 pp | No |
| Trend-adjusted LPM Post | -0.2389 pp | -0.3284 pp | No |
| ITS level break | -0.3070 pp | -0.3621 pp | No |
| ITS slope break | 0.0155 pp | 0.0126 pp | No |
| Quarterly Poisson Post IRR | 0.0342 | 0.0323 | No |
| Quarterly Poisson slope IRR | 1.4306 | 1.4111 | No |

### Answers

1. The three added applications all fall pre-policy: September 2019, February 2020, and February 2024.
2. Moving from 52 to 55 changes the raw pre/post contrast only by adding three pre-policy events; the direction and descriptive conclusion are unchanged.
3. The trend-adjusted Post coefficient changes modestly; its interpretation remains descriptive and it should not be read as causal.
4. The level and slope break comparisons above retain the same specification and universe for both outcomes. The reported differences should be read as sensitivity to the linkage rule, not a selection of a preferred sample.
5. The substantive conclusion is assessed in the final table without using Tier 5 or Tier 6 candidates.

## Timing Conventions

Application-level `Post` is exactly `1{start_date >= 2024-07-05}`. Cohort-level monthly and quarterly ITS use the first complete calendar period at the institutional breakpoint (July 2024 / 2024 Q3), with `TimeAfter = 0` in that break period. Three applications start on July 1-4, 2024; their application-level coding remains pre-policy under the exact definition. No DMCA date is used as an application date.
