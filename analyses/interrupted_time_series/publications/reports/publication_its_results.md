# Publication ITS Results

## 1. Research Question

The publication analysis now separates three empirical objects: system-level scientific output, project-level productivity and timing, and pipeline-adjusted output.

## 2. Why Publications Require A Pipeline Framework

Total scientific output equals project entry multiplied by project-level productivity and publication timing. Project entry is dynamic, and publication output has a long project-start-to-publication lag.

## 3. Publication Data And Linkage Construction

The analysis starts from 14,633 Schema19 publications and 12,598 Schema24 app-publication links. After matching to the project universe and excluding publication-before-start links, it uses 12,568 cleaned links and 11,959 unique publications.

## 4. Candidate Outcome Hierarchy

Y1 total monthly fractional publication output is primary. Y2 incumbent-pool intensity is supplementary. Y3 fixed cohorts, Y4 project-age profiles, Y5/Y6 fixed follow-up, Y7 time to first publication, Y8 project-month panel, and Y9 pipeline gaps diagnose mechanisms and limitations.

## 5. Primary Outcome: Total Monthly Publication Flow

The primary outcome is monthly total `fractional_publication_count`, with no incumbent denominator. This is closest to the theoretical question about the total number of scientific outcomes and allows project entry to be part of the system-level mechanism.

## 6. Raw Calendar-Time Pattern

In the 2019-01 to 2025-12 primary window, mean monthly total fractional output is 89.65 before July 2024 and 208.06 after July 2024. July-September 2024 averages 170.33, while calendar 2025 averages 229.17. The raw total-output series does not show a sharp immediate collapse around July 2024; 2025 is higher.

## 7. Primary Segmented ITS

The primary model is a monthly linear segmented ITS with month-of-year fixed effects and Newey-West HAC lag 3. There are 84 months: 66 pre-transition and 18 post-transition.

| Term | Estimate | SE | p-value | 95% CI | Economic reading |
| --- | ---: | ---: | ---: | ---: | --- |
| Time | 2.0861 | 0.0753 | 0.0000 | [1.9384, 2.2337] | pre-transition monthly trend in total fractional publication output |
| PostJuly2024 | -9.4554 | 8.2418 | 0.2513 | [-25.6092, 6.6984] | immediate descriptive level change at the institutional marker |
| TimeAfterJuly2024 | 4.3330 | 0.7125 | 0.0000 | [2.9366, 5.7294] | post-July monthly slope change in total output |

Because publication response is lagged, `PostJuly2024` should not be interpreted as an immediate RAP productivity response.

## 8. Autocorrelation And HAC Inference

After trend, July terms, and month fixed effects, Durbin-Watson is 2.3022. Ljung-Box p-values are 0.1389 at lag 1, 0.2625 at lag 3, 0.2887 at lag 6, and 0.0827 at lag 12. These diagnostics are reported descriptively, not as pass/fail tests.

HAC(1), HAC(3), HAC(6), and HAC(12) keep identical OLS point estimates; only uncertainty changes. AR(1) robustness estimates rho = -0.159; the slope-change estimate is 4.3547 with SE 0.5989.

## 9. Publication Measurement Sensitivity

541 publications are linked to multiple valid applications. Measurement sensitivity compares app links, unique publications, and fractional counts. The broad total-output trajectory is not driven only by multi-application linking.

## 10. Project-Start-To-Publication Lag

Median project-start-to-publication lag is 41.000 months, and 79.08% of links occur after 24 months. This is not RAP-to-publication lag. It is why immediate post-July publications mostly reflect work initiated earlier.

## 11. Project-Age Publication Profile

Project-age profiles show publication productivity varies strongly over the project lifecycle. The age profile is therefore central to interpreting total-output growth.

## 12. Fixed-Cohort Analysis

Fixed cohorts are constructed using prespecified cutoffs 2021-07-01, 2022-01-01, and 2022-07-01. For the 2022-07-01 cohort, the post-July slope estimate is 0.0265 with SE 0.0139. This is a stable-membership diagnostic, not the primary system-level outcome.

## 13. Fixed-Follow-Up Project Productivity

At 12 months, eligible pre-RAP projects number 4332 and eligible post-RAP projects number 471. Mean Pub12 is 0.093433 for pre-RAP starts and 0.152229 for post-RAP starts; AnyPub12 is 6.648% versus 11.465%. Post-RAP 18- and 24-month outcomes are not feasible for this cohort under 2025-12 reliable censor date and not feasible for this cohort under 2025-12 reliable censor date under the 2025-12-31 censor date.

## 14. Time To First Publication

Time-to-first-publication outputs use age-specific complete-follow-up denominators. They support only early post-RAP comparisons; mature publication timing for RAP-era projects is not yet observable.

## 15. Pipeline-Adjusted Expected Publication Output

The pipeline benchmark estimates the historical project-age publication profile using only calendar months before July 2024, then applies that profile to the evolving project pipeline. Calendar 2025 actual output is 117.68 fractional publications above the pipeline benchmark, with mean actual/expected ratio 1.043; however, the cumulative July 2024-December 2025 pipeline gap is -13.74, because late 2024 is below the pipeline benchmark. This is a historical benchmark, not a causal counterfactual.

## 16. Right-Edge Completeness

Primary calendar-time analyses end at 2025-12. The local snapshot contains publications through 2026-07-16, but 2026 is retained only as a right-edge diagnostic.

## 17. Robustness

Robustness outputs include aggregate measurement sensitivity, HAC lag sensitivity, AR(1), Poisson QMLE for raw counts, fixed cohorts, project-follow-up outcomes, first-publication timing, and pre-transition placebo July breakpoints.

## 18. What The Evidence Supports

System output: C. gradual increase. Project productivity: D. higher early productivity at the feasible 12-month horizon; 18/24-month post-RAP follow-up is insufficient. Publication timing: D. faster at the feasible 12-month horizon; mature timing remains insufficiently observed. Pipeline-adjusted output: D. mixed.

## 19. What The Evidence Cannot Establish

The evidence cannot establish that RAP caused publications to increase or decrease. July 5, 2024 is not the verified individual RAP-exposure date for every incumbent project. Total publication growth is not the same object as project-level productivity growth, and the fitted historical pipeline expected output is not a causal untreated potential outcome.

## 20. Paper-Ready Stylized Fact

> UKB-linked total publication output shows no sharp immediate collapse around the July 2024 institutional transition marker and rises through 2025 in the public publication series.

> Because project-start-to-publication lags are long, post-July 2024 publications largely reflect projects and research pipelines that began before the transition.

> Relative to a historical project-age pipeline benchmark, 2025 publication output is above expected after a below-benchmark late-2024 period; this should be interpreted as a descriptive pipeline-adjusted pattern rather than a causal RAP effect.

## Main Outputs

- Main ITS table: `data/publication_its_results_table.csv`
- Outcome hierarchy: `data/publication_outcome_summary.csv`
- System monthly series: `data/publication_system_total_monthly.csv`
- Project cohort summary: `data/publication_project_cohort_summary.csv`
- Main figures: `figures/publication_total_monthly.svg`, `figures/publication_measure_comparison.svg`, `figures/publication_project_age_profile.svg`, `figures/publication_observed_vs_pipeline_expected.svg`, `figures/publication_cohort_followup.svg`
