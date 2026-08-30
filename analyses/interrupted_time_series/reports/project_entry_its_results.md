# Project-Entry ITS Results

## 1. Outcome Definition And Measurement

The outcome is monthly recorded UK Biobank project starts: the number of UKB projects whose public recorded `Start date` falls in calendar month `t`. The public `Start date` is treated as the recorded beginning of a UKB research project's project period. Public documentation does not establish that it is identical to the application submission date, approval date, or first RAP-access date.

The matched working universe contains 6,935 projects with exact public start dates from 2012-06-01 through 2026-08-17. There are 132 schema27 records unmatched to a public project page. See `project_entry_measurement_note.md`.

## 2. Institutional Breakpoint

The primary breakpoint is July 2024, based on the official 5 July 2024 transition to RAP-based access for new projects and additional data for existing projects. July 2024 through March 2025 is used only as broader transition/onboarding context, not as a homogeneous intervention period.

## 3. Raw Project-Start Pattern

The primary paper window is 2019-01 through 2025-12, with 84 monthly observations. It provides 66 pre-transition months and 18 post-transition months, balancing modern project volume against enough pre-period observations for trend and month-of-year seasonality.

The observed 2024 pattern includes May-June slowdown, July-September trough, and October rebound. These are outcome-defined descriptive patterns, not independent institutional phases.

## 4. Exact-Date Batching Diagnostic

October 2024 has 208 recorded starts across 20 unique start dates. The largest daily count is 49. The top 1, top 3, and top 5 start-date shares are 23.6%, 50.0%, and 68.8%.

This pattern is consistent with some date-level concentration, but not enough on its own to prove administrative batching.

## 5. Institution Concentration

October 2024 includes 208 starts across 175 institutions. The top-1 institution share is 1.9%, the top-5 share is 8.7%, and HHI is 0.007. Relative to ordinary pre-transition months, October's HHI percentile is 0.0% when higher values indicate more concentration.

The October rebound is therefore broad-based across many institutions rather than dominated by one institution.

## 6. Main ITS Specification

```text
Y_t = beta_0
    + beta_1 Time_t
    + beta_2 PostJuly2024_t
    + beta_3 TimeAfterJuly2024_t
    + month-of-year FE
    + epsilon_t
```

`Time_t` is a monthly running index. `PostJuly2024_t` equals 1 from July 2024 onward. `TimeAfterJuly2024_t` is 0 before July 2024 and begins increasing in July 2024. Month-of-year fixed effects absorb recurring seasonality.

## 7. Main ITS Results

Primary linear ITS with Newey-West HAC inference:

| Term | Estimate | SE | 95% CI | Interpretation |
| --- | ---: | ---: | ---: | --- |
| PostJuly2024 | -1.091 | 29.611 | [-59.129, 56.947] | descriptive level change |
| TimeAfterJuly2024 | 5.977 | 2.686 | [0.713, 11.241] | descriptive post-transition slope change |

The primary linear level-change estimate is slightly negative but very imprecise. The slope-change estimate is positive, matching the later higher project-start trajectory.

## 8. Observed-Versus-Expected Path

Using only pre-transition observations in the primary window, I fit a trend plus month-of-year seasonality model and forecast the fitted historical benchmark after July 2024. This is a descriptive benchmark, not a causal untreated potential outcome.

July-September 2024 recorded starts are -177.8 projects below the fitted historical path. The broader July 2024-March 2025 transition/onboarding context is 211.8 projects relative to the fitted path. October 2024 alone is 151.3 projects above the fitted path.

## 9. Cumulative Gap And Recovery

The cumulative observed-minus-expected gap reaches a minimum of -177.8 projects and recovers in 2024-11. By 2025-12, the cumulative gap is 984.6 projects.

## 10. Historical Rarity

The July-September 2024 total is 4 recorded starts. Across 64 rolling three-month windows in the pre-transition primary period, the minimum historical rolling total is 74, and 0 windows are at or below the observed July-September total.

## 11. Robustness

The main table includes 2019-2025, 2021-2025, and 2022-2025 windows, each with linear HAC and Poisson QMLE specifications. The positive post-transition slope-change pattern is stable across windows. The immediate level-change estimate is imprecise and changes sign, so it should not be emphasized as a robust stand-alone result.

Placebo July breakpoints in 2022 and 2023 are reported only as contextual diagnostics. They do not replace the July 2024 institutional breakpoint.

## 12. Exploratory Dynamic Characterization

The exploratory month-by-month output is labelled `EXPLORATORY / OUTCOME-DRIVEN DYNAMIC CHARACTERIZATION`. It characterizes the May-June decline, July-September trough, October rebound, and later 2025 trajectory without redefining the primary breakpoint.

## 13. What The Evidence Supports

The evidence supports describing an unusually sharp interruption in recorded project starts around the July 2024 RAP-based access transition, followed by a pronounced rebound and a 2025 trajectory above the fitted pre-transition benchmark.

## 14. What It Cannot Establish

This design cannot establish that RAP caused the project-start interruption. It cannot show that the public `Start date` is an application submission date, approval date, RAP migration date, or first RAP-access date. It also cannot prove that October 2024 was a documented institutional restart or administrative batch-processing event.

## 15. Recommended Paper-Ready Stylized Fact

Classification: C. Temporary interruption followed by higher-than-historical entry.

Candidate paper-ready statements:

> Recorded UK Biobank project starts exhibit a pronounced interruption around the July 2024 transition to RAP-based access, followed by a substantial rebound in the public project-start series.

> The decline begins before the formal July transition, which limits causal interpretation of the interruption; the institutionally anchored evidence supports July 2024 as the primary breakpoint, not a separately documented July-September pause or October restart.

> Relative to a fitted pre-transition trend-and-seasonality benchmark, the July-September 2024 shortfall is subsequently recovered, and the 2025 project-start trajectory lies above the fitted historical path.

## Output Files

- `data/project_entry_daily_starts_2024.csv`
- `data/project_entry_exact_date_audit.csv`
- `data/project_entry_institution_concentration.csv`
- `data/project_entry_estimation_window_audit.csv`
- `data/project_entry_its_results_table.csv`
- `data/project_entry_observed_vs_expected.csv`
- `data/project_entry_cumulative_gap.csv`
- `data/project_entry_historical_rarity.csv`
- `data/project_entry_exploratory_dynamic_characterization.csv`
- `data/project_entry_placebo_results.csv`
- `figures/project_entry_figure1_three_panel.svg`
- `figures/project_entry_daily_starts_2024.svg`
- `figures/project_entry_observed_vs_expected.svg`
- `figures/project_entry_cumulative_gap.svg`
