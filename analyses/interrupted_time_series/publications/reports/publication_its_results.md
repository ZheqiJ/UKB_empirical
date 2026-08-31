# Publication ITS Results

## 1. Outcome And Sample Definition

The primary outcome is monthly `fractional_publications_per_100_post_start_incumbents` among projects with public start date before 2024-07-05. The sample excludes post-transition entrants from the publication-output composition.

## 2. Why Incumbents Are Used

Incumbents are used so that post-transition project starts do not mechanically change the publication mix. The denominator is not active projects; it is pre-transition incumbent projects whose public start date has occurred by the end of month `t`.

## 3. Publication Lag

The median project-start-to-publication lag is 41.000 months. Only 1.15% of linked publication events occur within 0-6 months of project start, while 79.08% occur after 24 months. This is not RAP-to-publication lag. It means an immediate July 2024 publication response should not be mechanically expected.

## 4. Publication-Measure Construction

The primary intensity outcome is fractional publications per 100 post-start incumbents. The secondary extensive-margin outcome is any-publication rate percent. App-link and unique-publication rates are measurement sensitivities.

## 5. Raw Monthly Trajectory

In the 2019-01 to 2025-12 primary window, the pre-transition mean is 3.47 fractional publications per 100 post-start incumbents, and the post-transition mean is 4.64. The raw trajectory does not show a sharp immediate publication collapse around July 2024; 2025 is generally above the preceding fitted trajectory.

## 6. Primary ITS Design

The primary model is a linear segmented ITS with month-of-year fixed effects and Newey-West HAC lag 3. There are 84 monthly observations: 66 pre-transition months and 18 post-transition months.

## 7. Autocorrelation Diagnostics

After controlling for trend, July terms, and calendar-month seasonality, the Durbin-Watson statistic is 1.7624. Ljung-Box at lag 12 is Q = 10.7364 with p = 0.5523. These diagnostics do not show strong remaining residual serial correlation, but HAC and AR(1) robustness are still reported because monthly publication output can be temporally persistent.

## 8. Newey-West Inference

Primary HAC lag is 3, prespecified for monthly data before inspecting significance. HAC lag sensitivity is saved in `publication_its_hac_lag_sensitivity.csv`; point estimates are invariant across HAC lags, while standard errors vary.

## 9. AR(1) Robustness

Prais-Winsten AR(1) robustness reports estimated rho = 0.103. The AR(1) level estimate is -0.2183 (SE 0.2775, 95% CI [-0.7621, 0.3255]); the slope estimate is 0.1041 (SE 0.0231, 95% CI [0.0588, 0.1494]). The direction is consistent with the primary gradual-increase reading.

## 10. Observed-Versus-Expected Historical Benchmark

Using only pre-July-2024 observations, the fitted pre-transition historical benchmark implies a July 2024-March 2025 cumulative gap of 2.33 and a calendar-2025 gap of 13.44 publication-intensity points. These are descriptive gaps, not causal untreated potential outcomes.

## 11. Publication Lifecycle / Age Composition

Age-band outputs show publication intensity is highest among older projects. The aggregate post-2024 rise is therefore plausibly partly related to aging/composition of the incumbent project pool, not only an institutional transition pattern.

## 12. Fixed-Cohort Robustness

The fixed cohort keeps projects started before 2022-07-01. Its ITS slope estimate is 0.0274 with SE 0.0141. This preserves a positive post-July trajectory within a stable membership cohort, while still remaining descriptive.

## 13. Measure Sensitivity

The positive post-July slope pattern is compared across fractional publication intensity, app-link intensity, unique-publication intensity, and any-publication rate in `publication_its_results_table.csv`. The conclusion does not rely only on multi-application link counting.

## 14. Right-Edge Completeness

The main analysis ends at 2025-12. The local snapshot contains 2026 publication dates through 2026-07-16, but 2026 is retained only as a right-edge completeness diagnostic.

## 15. Additional Robustness

Additional outputs include HAC lag sensitivity, Poisson QMLE count robustness, pre-transition placebo July breakpoints, residual ACF/PACF, and right-edge completeness diagnostics.

## 16. What The Evidence Supports

The evidence supports a descriptive pattern of no sharp immediate publication disruption around July 2024, followed by a gradual higher 2025 incumbent publication trajectory relative to the fitted pre-transition historical benchmark.

## 17. What It Cannot Establish

This analysis cannot establish that RAP caused publications to rise or fall. July 2024 is not the verified individual RAP-exposure date for every incumbent, and project-start-to-publication lag is long.

## 18. Recommended Paper-Ready Stylized Fact

Classification: C. Gradual post-transition increase.

Candidate conservative statements:

> Among pre-transition UKB incumbent projects, publication output shows no sharp immediate disruption at the July 2024 institutional transition marker.

> Publication output rises gradually through 2025 relative to the fitted pre-transition historical benchmark, but long project-start-to-publication lags mean this should not be interpreted as an immediate RAP effect.

> Lifecycle composition is an important alternative explanation: older incumbent projects publish at higher rates, so aggregate post-transition increases may partly reflect project aging.

## Main Results

| Term | Estimate | SE | p-value | 95% CI | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| PostJuly2024 | -0.2439 | 0.1969 | 0.2155 | [-0.6299, 0.1421] | descriptive immediate level change |
| TimeAfterJuly2024 | 0.1051 | 0.0169 | 0.0000 | [0.0719, 0.1383] | descriptive monthly post-transition slope change |

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
