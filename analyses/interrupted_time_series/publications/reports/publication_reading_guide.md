# Publication Results Reading Guide

Read this module as a descriptive analysis of what changed in UKB-linked publication output around and after the July 2024 institutional transition. Do not collapse total output, project-start composition, lifecycle-adjusted output, and early project productivity into one causal claim.

## Read In This Order

1. `reports/publication_measurement_note.md`
2. `reports/publication_its_results.md`
3. `figures/publication_total_monthly.svg`
4. `figures/publication_project_start_contribution_stacked.svg`
5. `figures/publication_observed_vs_pipeline_expected.svg`
6. `figures/publication_pipeline_benchmark_comparison.svg`
7. `figures/publication_first_pub_km.svg`
8. `reports/publication_stata_style_results.txt`

## Four Questions

1. Total output: use Y1 `unique_publication_ids`, the segmented ITS, fitted pre-trend differences, cumulative descriptive gaps, transition/lag sensitivity, and endpoint sensitivity.
2. Who generated output: use project-start cohort contribution decomposition and Y3 fixed-cohort intensity.
3. Lifecycle/pipeline: use Y4 age profiles, Y8 lifecycle-adjusted project-month regressions, and Y9 pipeline benchmarks.
4. Comparable early project ages: use Y5/Y6 fixed follow-up, six-month start cohorts, and Y7 Kaplan-Meier first-publication timing.

## Main Numbers

- Primary Y: monthly `unique_publication_ids`; aggregate `fractional_publication_count` equals this by construction.
- Window: 2019-01 to 2025-12.
- Observations: 84 total, 66 pre-July-2024, 18 post-July-2024.
- Raw mean monthly output: 89.65 pre, 208.06 post.
- Primary level change: -5.1224 (SE 7.6605, p 0.5037).
- Primary slope change: 4.3330 (SE 0.7125, p 0.0000).
- 12-month fitted difference vs pretrend: 42.5406 publications per month.
- July 2024-December 2025 observed cumulative difference vs pretrend: 570.745 publications.
- 2025 post-transition-start contribution share: 4.95%.
- Pipeline 2025 gap: 153.81; cumulative July 2024-December 2025 gap: 34.34; trend-adjusted cumulative gap: 450.48.
- Y8 PPML slope change: 0.0173 (project-clustered SE 0.0043).
- Pub12 pooled post-minus-pre difference: 0.053953 (p 0.0164).
- Publication lag: median 41.000 months from project start to publication.

## Main Figures

- `figures/publication_total_monthly.svg`
- `figures/publication_project_start_contribution_stacked.svg`
- `figures/publication_post_start_share.svg`
- `figures/publication_observed_vs_pipeline_expected.svg`
- `figures/publication_pipeline_benchmark_comparison.svg`
- `figures/publication_pub12_by_start_cohort.svg`
- `figures/publication_anypub12_by_start_cohort.svg`
- `figures/publication_first_pub_km.svg`

## Main Tables

- `data/publication_its_results_table.csv`
- `reports/publication_stata_style_results.txt`
- `data/publication_pretrend_fitted_differences.csv`
- `data/publication_cumulative_pretrend_gaps.csv`
- `data/publication_project_start_cohort_contributions.csv`
- `data/publication_project_month_lifecycle_regression.csv`
- `data/publication_fixed_followup_pooled_table.csv`
- `data/publication_pub12_by_start_cohort.csv`
- `data/publication_first_pub_km.csv`
- `data/publication_pipeline_benchmark_sensitivity.csv`
- `data/publication_transition_lag_sensitivity.csv`
- `data/publication_right_edge_endpoint_sensitivity.csv`

## Supplementary Outputs

- `data/publication_measurement_sensitivity_its.csv`
- `data/publication_its_hac_lag_sensitivity.csv`
- `data/publication_its_ar1_robustness.csv`
- `data/publication_poisson_count_robustness.csv`
- `data/publication_placebo_results.csv`
- `data/publication_by_project_age.csv`
- `data/publication_age_band_profile.csv`
- `data/publication_project_month_panel.csv`
- `data/publication_project_cohort_summary.csv`
- `data/publication_first_pub_timing.csv`
- `data/publication_pipeline_expected.csv`
- `data/publication_pipeline_gap.csv`
- `data/its_recent_publication_completeness.csv`

## Interpretation

System output: C. gradual increase. Project productivity: suggestive higher early 12-month output in the observable early post-transition cohort; mature productivity remains infeasible. Publication timing: suggestive higher 12-month first-publication incidence in the observable early post-transition project-start cohort; mature timing remains infeasible. Pipeline-adjusted output: C. above historical pipeline expectation.

Use descriptive language: July 2024 institutional transition, post-transition publication trajectory, descriptive benchmark, RAP-era project cohort, and post-transition project-start cohort.
