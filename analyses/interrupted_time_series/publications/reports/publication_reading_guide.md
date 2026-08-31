# Publication Results Reading Guide

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
- Raw pre-transition mean: 3.47.
- Raw post-transition mean: 4.64.
- Primary level change: -0.2439 (SE 0.1969, 95% CI [-0.6299, 0.1421]).
- Primary slope change: 0.1051 (SE 0.0169, 95% CI [0.0719, 0.1383]).
- Durbin-Watson: 1.7624; Ljung-Box lag 12 p-value: 0.5523.
- AR(1): estimated rho = 0.103.
- Publication lag: median 41.000 months from project start to publication.

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
