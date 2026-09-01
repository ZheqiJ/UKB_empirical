# Publication Results Reading Guide

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

- Primary Y: monthly `unique_publication_ids`; aggregate `fractional_publication_count` equals this by construction.
- Window: 2019-01 to 2025-12.
- Observations: 84 total, 66 pre-July-2024, 18 post-July-2024.
- Raw mean monthly output: 89.65 pre, 208.06 post.
- Primary pre-trend: 2.0861 (SE 0.0753).
- Primary level change: -5.1224 (SE 7.6605, 95% CI [-20.1369, 9.8921]).
- Primary slope change: 4.3330 (SE 0.7125, 95% CI [2.9366, 5.7294]).
- Pipeline 2025 gap: 117.68; cumulative July 2024-December 2025 gap: -13.74; mean 2025 actual/expected ratio: 1.043.
- Publication lag: median 41.000 months from project start to publication.

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

System output: C. gradual increase. Project productivity: suggestive higher early 12-month output in the observable early post-transition cohort; mature productivity remains infeasible. Publication timing: suggestive higher 12-month first-publication incidence in the observable early post-transition cohort; mature timing remains infeasible. Pipeline-adjusted output: D. mixed.

Use descriptive language: post-transition publication trajectory, system-level publication output, RAP-era project cohort, historical project-age publication profile, and pipeline-adjusted historical benchmark.
