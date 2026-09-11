# Publication ITS Results

## Research Question

This module asks descriptively how UKB-linked publication output changed around and after the July 2024 institutional transition. It does not treat July 2024 as the individual treatment date for every project and does not claim causal RAP effects.

The analysis starts from 14,633 Schema19 publications and 12,598 Schema24 app-publication links. After matching to the project universe and excluding publication-before-start links, it uses 12,568 cleaned links and 11,959 unique publications.

Y1 monthly unique UKB-linked publication output is the primary H2 publication outcome. At the aggregate system-month level, `fractional_publication_count` equals `unique_publication_ids` by construction, while `publication_app_links` is the meaningful alternative numerator because it counts project-publication links.

Publication lag here means project-start-to-publication lag, not RAP-to-publication lag.

## 1. How Did Total Publication Output Change Around And After July 2024?

In the 2019-01 to 2025-12 primary window, mean monthly unique publication output is 89.65 before July 2024 and 208.06 after July 2024. July-September 2024 averages 170.33, while calendar 2025 averages 229.17.

The primary model is a monthly linear segmented ITS with month-of-year fixed effects and Newey-West HAC lag 3. There are 84 months: 66 pre-transition and 18 post-transition. `TimeAfterJuly2024` is coded 0 in July 2024 and 1 in August 2024, so `PostJuly2024` directly represents the fitted July level shift.

| Term | Estimate | SE | p-value | 95% CI | Economic reading |
| --- | ---: | ---: | ---: | ---: | --- |
| Time | 2.0861 | 0.0753 | 0.0000 | [1.9384, 2.2337] | pre-transition monthly growth in unique publication output |
| PostJuly2024 | -5.1224 | 7.6605 | 0.5037 | [-20.1369, 9.8921] | immediate descriptive level change at the institutional marker |
| TimeAfterJuly2024 | 4.3330 | 0.7125 | 0.0000 | [2.9366, 5.7294] | post-transition monthly slope change in total output |

The linear model describes absolute changes in monthly publication counts. The Poisson/QMLE model describes multiplicative changes: its post-transition slope coefficient is 0.0083 with IRR 1.008. The immediate July level-change inference is specification-sensitive across the linear and Poisson functional forms. The common finding across specifications is a higher post-transition publication trajectory/slope, while the immediate July level shift should be read cautiously.

Fitted differences relative to continuation of the pre-July trend are in `data/publication_pretrend_fitted_differences.csv`. At 12 months, the fitted monthly difference is 42.5406 publications (23.35% versus the pre-trend benchmark). At 18 months, it is 68.5386 publications (37.23%).

Cumulative observed differences relative to the fitted pre-trend benchmark are 176.265 publications for July 2024-June 2025 and 570.745 for July 2024-December 2025. The corresponding fitted cumulative differences are 224.509 and 570.746. These are descriptive pre-trend benchmark differences, not causal counterfactual effects.

Transition-window and lagged-response sensitivity is in `data/publication_transition_lag_sensitivity.csv`. The baseline slope change is 4.3330; allowing response onset in October 2024 gives 5.2505; allowing response onset in January 2025 gives 4.3392. This checks sensitivity to gradual implementation or delayed publication response without redefining the institutional marker.

Right-edge endpoint sensitivity is in `data/publication_right_edge_endpoint_sensitivity.csv`. The December 2025 endpoint slope estimate is 4.3330; shorter endpoints are reported because recent publication months have not been externally validated as complete.

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

Descriptive pre-trend benchmark fitted differences
-----------------------------------------------------------------------------------------------
 Horizon  Month      Diff/mo  Std. err.    P>|z|     CI low    CI high     Percent
-----------------------------------------------------------------------------------------------
      3 2024-09        3.5436     6.5757   0.5900    -9.3448    16.4320      2.34
      6 2024-12       16.5426     5.2622   0.0017     6.2287    26.8564     10.40
     12 2025-06       42.5406     4.8991   0.0000    32.9384    52.1428     23.35
     18 2025-12       68.5386     7.5404   0.0000    53.7594    83.3178     37.23
-----------------------------------------------------------------------------------------------

Transition-window and lagged-response sensitivity
----------------------------------------------------------------------------------------------------------------
 Specification                         Onset           Level   Level SE Level p      Slope   Slope SE  Slope p
----------------------------------------------------------------------------------------------------------------
baseline_immediate_response          2024-07-01    -5.1224     7.6605   0.5037     4.3330     0.7125   0.0000
lagged_response_3_months             2024-10-01    -1.7734     4.4281   0.6888     5.2505     0.5785   0.0000
lagged_response_6_months             2025-01-01    21.0513     7.1283   0.0031     4.3392     0.9181   0.0000
transition_window_3_months_excluded  2024-10-01     5.7162     4.2778   0.1815     5.3038     0.5940   0.0000
transition_window_6_months_excluded  2025-01-01    34.9076     6.2772   0.0000     4.2973     0.9515   0.0000
----------------------------------------------------------------------------------------------------------------

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

Lifecycle-adjusted project-month models
---------------------------------------------------------------------------------------------------------------------------------
 Model                                   Outcome                        Term                    Coef.   Proj SE    P>|z|     CI low    CI high      IRR
---------------------------------------------------------------------------------------------------------------------------------
Lifecycle-adjusted project-month PPML   fractional_publication_count   PostJuly2024           -0.0374     0.0499   0.4543    -0.1352     0.0605   0.9633
Lifecycle-adjusted project-month PPML   fractional_publication_count   TimeAfterJuly2024       0.0173     0.0043   0.0001     0.0089     0.0257   1.0174
Lifecycle-adjusted project-month LPM    any_publication                PostJuly2024           -0.0012     0.0015   0.4288    -0.0041     0.0017
Lifecycle-adjusted project-month LPM    any_publication                TimeAfterJuly2024       0.0006     0.0001   0.0000     0.0004     0.0008
---------------------------------------------------------------------------------------------------------------------------------

Fixed-follow-up pooled project-cohort comparisons
-----------------------------------------------------------------------------------------
 Horizon Estimability                              Pre N   Post N    Pub diff    Pub p    Any pp diff   Any p
-----------------------------------------------------------------------------------------
     12 post-transition cohort estimable             4332      471     0.053953   0.0164        4.988   0.0007
     18 post-transition cohort not yet estimable     4329        0
     24 post-transition cohort not yet estimable     4005        0
-----------------------------------------------------------------------------------------

Right-edge endpoint sensitivity
-----------------------------------------------------------------------------------------------
 Window             Term                    Coef.  Std. err.    P>|z|     CI low    CI high
-----------------------------------------------------------------------------------------------
2019-01_to_2025-06 PostJuly2024            7.9712     7.8159   0.3078    -7.3481    23.2904
2019-01_to_2025-06 TimeAfterJuly2024       1.3087     1.0445   0.2102    -0.7385     3.3558
2019-01_to_2025-09 PostJuly2024           -3.5072     8.3260   0.6736   -19.8261    12.8118
2019-01_to_2025-09 TimeAfterJuly2024       3.9971     1.0123   0.0001     2.0130     5.9812
2019-01_to_2025-12 PostJuly2024           -5.1224     7.6605   0.5037   -20.1369     9.8921
2019-01_to_2025-12 TimeAfterJuly2024       4.3330     0.7125   0.0000     2.9366     5.7294
-----------------------------------------------------------------------------------------------

Notes:
1. This is Stata-style formatting of the repository's generated Python estimates, not a separate Stata execution log.
2. The primary publication outcome is system-level unique publication output, not publication output per incumbent project.
3. Coefficients are descriptive calendar-time changes around the July 2024 institutional transition and should not be interpreted as causal RAP treatment effects.
```

## 2. Who Generated The Post-July Publication Output?

Using fractional publication attribution, `data/publication_project_start_cohort_contributions.csv` decomposes every monthly Y1 total into pre-transition-start and post-transition-start project contributions. It verifies that pre-start contribution plus post-start contribution equals aggregate fractional output, which equals unique publication output at the system-month level.

In calendar 2025, post-transition-start projects contribute 136.20 of 2750.00 total fractional/unique publications, or 4.95%. By December 2025 the post-transition-start share is 8.491%. This is descriptive: it shows whether growth is still mainly generated by projects initiated before the institutional transition or increasingly by RAP-era project cohorts.

Y3 fixed-cohort publication intensity is retained as a stable-membership incumbent-cohort diagnostic. Fixed cohorts use prespecified cutoffs 2021-07-01, 2022-01-01, and 2022-07-01. For the 2022-07-01 cohort, the post-transition slope estimate is 0.0265 with SE 0.0139. This is not a causal RAP effect.

## 3. Can Lifecycle And Pipeline Composition Account For The Pattern?

Y4 project-age profiles show that publication intensity varies strongly over the project lifecycle. The age profile is diagnostic; it does not structurally identify a pure age effect.

Y8 now estimates project-month lifecycle-adjusted descriptive models instead of leaving `publication_project_month_panel.csv` as only a construction output. The PPML model for fractional output uses fine project-age bins, a common calendar trend, July 2024 segmented terms, and month-of-year effects; project-clustered inference is primary and institution-clustered inference is reported when sufficiently populated. The PPML post-transition slope estimate is 0.0173 with project-clustered SE 0.0043; the immediate level estimate is -0.0374 with SE 0.0499. The LPM for `any_publication` gives a slope estimate of 0.0006 with SE 0.0001. This is a lifecycle-adjusted descriptive calendar-transition analysis and does not separately identify unrestricted age, period, and cohort effects.

Y9 estimates expected output from pre-July publication behavior by project age and applies that profile to the realized project pipeline. The benchmark now uses smoothed monthly project-age rates, with 120 project-level bootstrap replications for monthly expected-output and gap intervals. July 2024-June 2025 actual output is -120.135 publications relative to the age-profile benchmark; July 2024-December 2025 is 34.342. A trend-adjusted sensitivity that allows a smooth pre-transition calendar productivity factor gives 117.257 and 450.484 for the same windows. Because the age-profile and trend-adjusted benchmarks imply materially different post-transition gaps, the magnitude of the pipeline-adjusted gap is specification-sensitive. This is a descriptive pipeline benchmark, not a causal untreated potential outcome.

The pipeline benchmark adjusts for realized project entry and project age. Because it conditions on the realized post-transition project-entry channel, it does not capture any total effect operating through project entry, and it does not fully settle secular calendar-time productivity growth.

## 4. How Do Post-Transition Project-Start Cohorts Perform At Comparable Early Ages?

Y5/Y6 fixed-follow-up outcomes now use exact date cutoffs: PubH includes only publications with `publication_date <= add_months_exact(project_start_date, H)`, and projects are eligible only when that H-month date is on or before 2025-12-31.

At 12 months, eligible pre-transition projects number 4332 and eligible post-transition projects number 471 out of 2603 total post-transition projects. The observable 12-month post-transition sample is concentrated in the earliest transition-era start cohorts and is not representative of the full post-transition project universe. Mean Pub12 is 0.082352 for pre-transition starts and 0.136306 for post-transition starts; the pooled post-minus-pre difference is 0.053953 with p-value 0.0164. AnyPub12 is 5.840% versus 10.828%; the difference is 4.988 percentage points with p-value 0.0007. Post-transition 18- and 24-month outcomes are not yet estimable for this cohort under 2025-12 reliable censor date and not yet estimable for this cohort under 2025-12 reliable censor date.

Six-month start-cohort tables are in `data/publication_pub12_by_start_cohort.csv`, with figures `publication_pub12_by_start_cohort.svg` and `publication_anypub12_by_start_cohort.svg`. The 2024H2 start cohort has 474 eligible projects, Pub12 mean 0.135443, and AnyPub12 10.759%.

Y7 now reports Kaplan-Meier `1 - S(age)` curves with confidence intervals and number-at-risk tables. At project age 12 months, the estimated share with first publication is 5.817% for pre-transition starts and 8.938% for post-transition starts. Mature post-transition timing remains infeasible because the post-transition cohort has limited support at older project ages.

## Robustness And Completeness Checks

Autocorrelation diagnostics remain descriptive: Durbin-Watson is 2.3022; Ljung-Box p-values are 0.1389 at lag 1, 0.2625 at lag 3, 0.2887 at lag 6, and 0.0827 at lag 12. HAC lag sensitivity, AR(1), Poisson QMLE, measurement sensitivity, fixed cohorts, placebo breakpoints, endpoint sensitivity, and right-edge completeness diagnostics are retained in supplementary outputs.

Primary calendar-time analyses end at 2025-12. The local snapshot contains publications through 2026-07-16, but 2026 is retained only as a right-edge diagnostic.

## What The Evidence Supports

System output: C. gradual increase. Project productivity: suggestive higher early 12-month output in the observable early post-transition cohort; mature productivity remains infeasible. Publication timing: suggestive higher 12-month first-publication incidence in the observable early post-transition project-start cohort; mature timing remains infeasible. Pipeline-adjusted output: C. above historical pipeline expectation.

## What The Evidence Cannot Establish

The evidence cannot establish that RAP caused publications to increase or decrease. July 2024 is an institutional transition marker, not the verified individual exposure date for every project. Total publication growth is not the same object as project-level productivity growth, and the fitted historical pipeline expected output is not a causal untreated potential outcome.

## Completion Checklist

1. Preserved existing correct pieces: cleaned publication/application linkage, unique and fractional construction, Y1 segmented ITS, measurement sensitivity, HAC lag sensitivity, AR(1), Poisson/QMLE, residual diagnostics, placebo checks, right-edge completeness diagnostics, Y3 fixed cohorts, Y4 age profiles, incumbent supplementary series, and pipeline output framework.
2. Corrected existing pieces: exact fixed-follow-up eligibility and PubH inclusion, Y7 presentation now uses proper Kaplan-Meier for the main timing analysis, Y9 uses smoothed monthly age profiles instead of coarse bins, and reports are reorganized around four empirical questions.
3. Added new tables: fitted pre-trend differences, cumulative pre-trend gaps, project-start cohort contribution decomposition, Y8 lifecycle-adjusted project-month regressions, fixed-follow-up pooled comparisons, six-month Pub12 start-cohort summary, Kaplan-Meier/risk tables, transition/lag sensitivity, endpoint sensitivity, and pipeline benchmark sensitivity.
4. Added new figures: fitted/pretrend Y1 main figure content, project-start cohort stacked contribution figure, post-start share figure, Pub12 and AnyPub12 start-cohort figures, and Kaplan-Meier first-publication figure.
5. Infeasible because of follow-up/data limitations: mature post-transition 18/24-month project productivity, mature post-transition time-to-first-publication curves, externally verified completeness of very recent publication months, and any causal interpretation of RAP publication effects.
6. Short four-question summary: total output rises on a steeper post-transition trajectory; 2025 output is still mostly from pre-transition-start projects but post-transition starts contribute an increasing share; lifecycle/pipeline-adjusted benchmarks show 2025 catch-up above age-profile expectations but remain descriptive; observable early post-transition start cohorts have higher 12-month output/timing than pooled historical starts, but mature project productivity and timing are not yet estimable.

## Output Index

- Main ITS table: `data/publication_its_results_table.csv`
- Stata-style regression output: `reports/publication_stata_style_results.txt`
- Fitted benchmark differences: `data/publication_pretrend_fitted_differences.csv`
- Cumulative benchmark gaps: `data/publication_cumulative_pretrend_gaps.csv`
- Project-start decomposition: `data/publication_project_start_cohort_contributions.csv`
- Y8 project-month regressions: `data/publication_project_month_lifecycle_regression.csv`
- Fixed-follow-up pooled table: `data/publication_fixed_followup_pooled_table.csv`
- Six-month start-cohort table: `data/publication_pub12_by_start_cohort.csv`
- Kaplan-Meier table: `data/publication_first_pub_km.csv`
- Pipeline benchmark sensitivity: `data/publication_pipeline_benchmark_sensitivity.csv`
- Transition/lag sensitivity: `data/publication_transition_lag_sensitivity.csv`
- Endpoint sensitivity: `data/publication_right_edge_endpoint_sensitivity.csv`
- Main figures: `figures/publication_total_monthly.svg`, `figures/publication_project_start_contribution_stacked.svg`, `figures/publication_post_start_share.svg`, `figures/publication_observed_vs_pipeline_expected.svg`, `figures/publication_pipeline_benchmark_comparison.svg`, `figures/publication_pub12_by_start_cohort.svg`, `figures/publication_anypub12_by_start_cohort.svg`, `figures/publication_first_pub_km.svg`
