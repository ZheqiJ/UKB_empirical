# Publication ITS Results

## 1. Research Question

The publication analysis now separates three empirical objects: system-level scientific output, project-level productivity and timing, and pipeline-adjusted output.

## 2. Why Publications Require A Pipeline Framework

Total scientific output equals project entry multiplied by project-level productivity and publication timing. Project entry is dynamic, and publication output has a long project-start-to-publication lag.

## 3. Publication Data And Linkage Construction

The analysis starts from 14,633 Schema19 publications and 12,598 Schema24 app-publication links. After matching to the project universe and excluding publication-before-start links, it uses 12,568 cleaned links and 11,959 unique publications.

## 4. Candidate Outcome Hierarchy

Y1 monthly unique UKB-linked publication output is primary. At the aggregate system level, fractional publication count equals unique publication count by construction. Y2 incumbent-pool intensity is supplementary. Y3 fixed cohorts, Y4 project-age profiles, Y5/Y6 fixed follow-up, Y7 time to first publication, Y8 project-month panel, and Y9 pipeline gaps diagnose mechanisms and limitations.

## 5. Primary Outcome: Total Monthly Publication Flow

The primary outcome is the monthly number of unique UKB-linked publications, `unique_publication_ids`, with no incumbent denominator. The aggregate `fractional_publication_count` is kept in the data but is identical to unique publications at the system-month level. `publication_app_links` is the genuine alternative aggregate measure because it counts project-publication links rather than unique scientific outputs.

## 6. Raw Calendar-Time Pattern

In the 2019-01 to 2025-12 primary window, mean monthly unique publication output is 89.65 before July 2024 and 208.06 after July 2024. July-September 2024 averages 170.33, while calendar 2025 averages 229.17. The raw total-output series does not show a sharp immediate collapse around July 2024; 2025 is higher.

## 7. Primary Segmented ITS

The primary model is a monthly linear segmented ITS with month-of-year fixed effects and Newey-West HAC lag 3. There are 84 months: 66 pre-transition and 18 post-transition. `TimeAfterJuly2024` is coded 0 in July 2024 and 1 in August 2024, so `PostJuly2024` directly represents the fitted July level shift.

| Term | Estimate | SE | p-value | 95% CI | Economic reading |
| --- | ---: | ---: | ---: | ---: | --- |
| Time | 2.0861 | 0.0753 | 0.0000 | [1.9384, 2.2337] | pre-transition monthly trend in total fractional publication output |
| PostJuly2024 | -5.1224 | 7.6605 | 0.5037 | [-20.1369, 9.8921] | immediate descriptive level change at the institutional marker |
| TimeAfterJuly2024 | 4.3330 | 0.7125 | 0.0000 | [2.9366, 5.7294] | post-July monthly slope change in total output |

Because publication response is lagged, `PostJuly2024` should not be interpreted as an immediate RAP productivity response.

### Stata-Style Output For Reporting

The following block is a Stata-style presentation of the generated publication regressions. It is also saved as `reports/publication_stata_style_results.txt`.

```text
Publication total-output segmented ITS, primary model
Outcome: monthly number of unique UKB-linked publications
Sample: 2019-01 to 2025-12                 Number of obs = 84
Seasonality: month-of-year fixed effects  Newey-West lag = 3
Inference: OLS with Newey-West HAC standard errors

------------------------------------------------------------------------------
 unique_publications | Coefficient  Std. err.       z    P>|z|      [95% conf. interval]
---------------------+--------------------------------------------------------
Time                 |      2.0861     0.0753   27.70   0.0000      1.9384      2.2337
PostJuly2024         |     -5.1224     7.6605   -0.67   0.5037    -20.1369      9.8921
TimeAfterJuly2024    |      4.3330     0.7125    6.08   0.0000      2.9366      5.7294
 Month FE            |         Yes
------------------------------------------------------------------------------

Aggregate-output measurement sensitivity, same ITS specification
-----------------------------------------------------------------------------------------------
 Outcome                              Term                    Coef.  Std. err.    P>|z|     CI low    CI high
-----------------------------------------------------------------------------------------------
publication_app_links                PostJuly2024           -3.9844     8.6114   0.6436   -20.8627    12.8940
publication_app_links                TimeAfterJuly2024       4.2856     0.7722   0.0000     2.7721     5.7992
unique_publication_ids               PostJuly2024           -5.1224     7.6605   0.5037   -20.1369     9.8921
unique_publication_ids               TimeAfterJuly2024       4.3330     0.7125   0.0000     2.9366     5.7294
fractional_publication_count         PostJuly2024           -5.1224     7.6605   0.5037   -20.1369     9.8921
fractional_publication_count         TimeAfterJuly2024       4.3330     0.7125   0.0000     2.9366     5.7294
-----------------------------------------------------------------------------------------------

Newey-West HAC lag sensitivity, primary total-output outcome
--------------------------------------------------------------------------------
 HAC lag  Term                    Coef.  Std. err.    P>|z|     CI low    CI high
--------------------------------------------------------------------------------
HAC(1)   PostJuly2024           -5.1224     8.0556   0.5249   -20.9114    10.6666
HAC(1)   TimeAfterJuly2024       4.3330     0.7328   0.0000     2.8967     5.7693
HAC(3)   PostJuly2024           -5.1224     7.6605   0.5037   -20.1369     9.8921
HAC(3)   TimeAfterJuly2024       4.3330     0.7125   0.0000     2.9366     5.7294
HAC(6)   PostJuly2024           -5.1224     6.3052   0.4166   -17.4807     7.2358
HAC(6)   TimeAfterJuly2024       4.3330     0.5872   0.0000     3.1822     5.4838
HAC(12)  PostJuly2024           -5.1224     6.0115   0.3942   -16.9050     6.6602
HAC(12)  TimeAfterJuly2024       4.3330     0.5419   0.0000     3.2709     5.3951
--------------------------------------------------------------------------------

Prais-Winsten AR(1) robustness
Estimated rho: -0.159
------------------------------------------------------------------------------
 unique_publications | Coefficient  Std. err.       z    P>|z|      [95% conf. interval]
---------------------+--------------------------------------------------------
Time                 |      2.0913     0.0825   25.35   0.0000      1.9295      2.2531
PostJuly2024         |     -5.8409     6.7627   -0.86   0.3878    -19.0959      7.4140
TimeAfterJuly2024    |      4.3547     0.5989    7.27   0.0000      3.1809      5.5284
------------------------------------------------------------------------------

Poisson QMLE count robustness
Outcome: monthly unique publication IDs
Inference: Poisson QMLE with HAC standard errors
----------------------------------------------------------------------------------------
 unique_pub_ids      | Coefficient  Std. err.       z    P>|z|      [95% conf. interval]       IRR
---------------------+------------------------------------------------------------------
Time                 |      0.0241     0.0012   20.08   0.0000      0.0217      0.0266     1.024
PostJuly2024         |     -0.1482     0.0486   -3.05   0.0023     -0.2435     -0.0529     0.862
TimeAfterJuly2024    |      0.0083     0.0029    2.86   0.0040      0.0027      0.0140     1.008
----------------------------------------------------------------------------------------

Notes:
1. This is Stata-style formatting of the repository's generated Python estimates, not a separate Stata execution log.
2. The primary publication outcome is system-level unique publication output, not publication output per incumbent project.
3. Coefficients are descriptive calendar-time changes and should not be interpreted as causal RAP treatment effects.
```

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

At 12 months, eligible pre-RAP projects number 4332 and eligible post-RAP projects number 471 out of 2603 total post-RAP projects. The observable post-RAP 12-month sample is concentrated in the earliest transition-era start cohorts and is not representative of the full post-RAP project universe. Mean Pub12 is 0.093433 for pre-RAP starts and 0.152229 for post-RAP starts; AnyPub12 is 6.648% versus 11.465%. Post-RAP 18- and 24-month outcomes are not feasible for this cohort under 2025-12 reliable censor date and not feasible for this cohort under 2025-12 reliable censor date under the 2025-12-31 censor date.

## 14. Time To First Publication

Time-to-first-publication outputs use age-specific complete-follow-up denominators and report the share with first publication by age among projects observable to that age. This is not a Kaplan-Meier estimate or a true cumulative-incidence curve because the risk set changes across ages. The main figure is restricted to ages 0-12 months for the post-RAP cohort.

## 15. Pipeline-Adjusted Expected Publication Output

The pipeline benchmark estimates the historical project-age publication profile using only calendar months before July 2024, then applies that profile to the evolving project pipeline. Calendar 2025 actual output is 117.68 publications above the pipeline benchmark, with mean actual/expected ratio 1.043; however, the cumulative July 2024-December 2025 pipeline gap is -13.74, because late 2024 is below the pipeline benchmark. This is a historical age-profile benchmark conditional on the realized project-entry pipeline, not a causal counterfactual. It does not fully absorb secular calendar-time growth in publication productivity, and because it conditions on realized post-transition project entry it does not capture the total effect of any policy-induced change in project entry.

## 16. Right-Edge Completeness

Primary calendar-time analyses end at 2025-12. The local snapshot contains publications through 2026-07-16, but 2026 is retained only as a right-edge diagnostic.

## 17. Robustness

Robustness outputs include aggregate measurement sensitivity, HAC lag sensitivity, AR(1), Poisson QMLE for raw counts, fixed cohorts, project-follow-up outcomes, first-publication timing, and pre-transition placebo July breakpoints.

## 18. What The Evidence Supports

System output: C. gradual increase. Project productivity: suggestive higher early 12-month output in the observable early post-transition cohort; mature productivity remains infeasible. Publication timing: suggestive higher 12-month first-publication incidence in the observable early post-transition cohort; mature timing remains infeasible. Pipeline-adjusted output: D. mixed.

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
