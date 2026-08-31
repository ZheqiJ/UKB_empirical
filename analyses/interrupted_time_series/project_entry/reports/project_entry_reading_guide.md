# Project-Entry Results Reading Guide

Read this file first. It gives the shortest path through the project-entry analysis and separates the main finding from diagnostics and appendices.

Short paths in this guide are relative to `analyses/interrupted_time_series/project_entry/`.

## One-Sentence Result

Recorded UK Biobank project starts show a sharp July-September 2024 interruption around the July 2024 RAP-based access transition, followed by recovery in November 2024 and a 2025 trajectory above the fitted pre-transition path. This is a descriptive project-start pattern, not a causal estimate of RAP.

## What To Read First

1. `reports/project_entry_measurement_note.md`

   Read this to understand the outcome. The public `Start date` is treated as the recorded beginning of a UKB research project's project period. It is not established to be application submission, approval, RAP migration, or first RAP access.

2. `reports/project_entry_its_results.md`

   Read Sections 1-3 for the setup, Sections 7-10 for the main results, and Sections 13-15 for the interpretation. Skip the diagnostic details on a first pass.

3. `figures/project_entry_figure1_three_panel.svg`

   Use this as the main paper figure:

   - Panel A: raw monthly recorded starts and July 2024 institutional marker.
   - Panel B: observed starts versus fitted pre-transition expected starts.
   - Panel C: cumulative observed-minus-expected gap.

4. `data/project_entry_its_results_table.csv`

   Use this as the compact model table. The main rows are the 2019-2025 linear segmented ITS and Poisson QMLE rows. The table now includes p-values and detailed economic interpretations.

## Main Numbers

Primary window: 2019-01 to 2025-12.

Monthly observations: 84.

Matched project universe: 6,935 public projects with exact start dates.

Primary breakpoint: July 2024, based on the official 5 July 2024 RAP-based access transition.

Primary linear ITS:

| Term | Estimate | p-value | 95% CI | Plain-language reading |
| --- | ---: | ---: | ---: | --- |
| `PostJuly2024` | -1.091 | 0.9706 | [-59.129, 56.947] | Immediate descriptive level change is very imprecise; do not emphasize it alone. |
| `TimeAfterJuly2024` | 5.977 | 0.0260 | [0.713, 11.241] | Post-transition monthly trajectory is about 6.0 starts/month steeper than the pre-transition path. |

Poisson QMLE robustness:

| Term | Estimate | p-value | 95% CI | Plain-language reading |
| --- | ---: | ---: | ---: | --- |
| `PostJuly2024` | 0.091 | 0.8003 | [-0.614, 0.795] | Immediate rate-ratio shift is about 1.10, but very imprecise. |
| `TimeAfterJuly2024` | 0.051 | 0.1035 | [-0.010, 0.113] | Monthly post-transition rate ratio is about 1.05; read as robustness because count overdispersion is high. |

Fitted-path deviations:

| Quantity | Estimate |
| --- | ---: |
| July-September 2024 shortfall | -177.8 starts |
| October 2024 gap | +151.3 starts |
| Recovery month for cumulative gap | 2024-11 |
| Cumulative gap by 2025-12 | +984.6 starts |

Historical rarity:

| Diagnostic | Result |
| --- | --- |
| July-September 2024 total | 4 starts |
| Minimum pre-transition rolling 3-month total, 2019-01 to 2024-06 | 74 starts |
| Pre-transition 3-month windows at or below July-September 2024 | 0 of 64 |

## How To Explain The Regression Table

For a supervisor report, do not describe `PostJuly2024` as the size of the interruption. It is the immediate level-change coefficient exactly at the July 2024 breakpoint. In the primary linear model it is -1.091 with p = 0.9706, so the model does not estimate a statistically or economically precise one-month level shift once trend, post-July slope change, and seasonality are controlled for.

The more informative ITS coefficient is `TimeAfterJuly2024`. In the primary linear model it is 5.977 with p = 0.0260, meaning the fitted post-transition trajectory increases by about 6 additional recorded starts per month relative to the pre-transition slope. By December 2025, that slope-change component is about 108 starts per month above a parallel continuation of the pre-transition path.

The economic size of the interruption should come from the fitted-path deviations rather than from the immediate level-change coefficient: July-September 2024 is about 178 starts below the historical trend-and-seasonality benchmark, October 2024 is about 151 starts above it, the cumulative gap recovers in November 2024, and by December 2025 the cumulative gap is about 985 starts above the fitted historical path.

## How To Interpret The Finding

Use this interpretation:

> Temporary interruption followed by higher-than-historical entry.

More precise version:

> Recorded UK Biobank project starts exhibit a pronounced interruption around the July 2024 transition to RAP-based access, followed by a substantial rebound. The cumulative shortfall relative to a fitted pre-transition trend-and-seasonality path is recovered by November 2024, and the 2025 trajectory is above the fitted historical benchmark.

Use this caution:

> The decline begins before the formal July transition, and the public `Start date` is a recorded project-start date rather than a documented application-submission date. The analysis is therefore descriptive and should not be written as "RAP reduced applications."

## What Not To Say

Do not write:

- RAP caused applications to fall.
- July-September 2024 was an official UKB pause.
- October 2024 was a documented restart.
- The outcome is new applications or approval counts.
- The fitted pre-transition path is a causal counterfactual.

Use instead:

- recorded project starts;
- project-start trajectory;
- institutional transition;
- descriptive level change;
- descriptive slope change;
- fitted historical benchmark;
- observed-minus-expected gap.

## Where Each Piece Lives

### Main Report

`reports/project_entry_its_results.md`

Supervisor/paper-facing writeup. This is the main written result.

### Measurement

`reports/project_entry_measurement_note.md`

Defines the public start-date outcome and its limits.

### Institutional Basis

`design/institutional_timeline_project_entry.md`

Official-source timeline. Use this to justify July 2024 as the primary breakpoint.

`design/project_entry_jom_style_design.md`

Structured institutional chronology design. Use this for the paper's design logic.

### Main Figure

`figures/project_entry_figure1_three_panel.svg`

Three-panel project-entry figure for the paper.

### Main Table

`data/project_entry_its_results_table.csv`

Compact model table: primary linear ITS, alternative windows, and Poisson robustness.

### Key Diagnostics

`data/project_entry_observed_vs_expected.csv`

Observed, fitted expected, monthly gap, and cumulative gap.

`data/project_entry_exact_date_audit.csv`

Daily-date concentration, especially October 2024.

`data/project_entry_institution_concentration.csv`

Whether unusual months are concentrated in a few institutions.

`data/project_entry_historical_rarity.csv`

How rare the July-September trough is relative to pre-transition rolling windows.

### Reproducibility

`scripts/project_entry_its_analysis.py`

Regenerates the project-entry outputs and runs built-in validation.

`tests/test_project_entry_its_analysis.py`

Automated checks for aggregation, breakpoint coding, fitted-path construction, cumulative-gap arithmetic, and window definitions.

## Suggested Paper Order

1. Measurement: public recorded `Start date` is a project-start measure, not applications.
2. Institutional chronology: July 2024 is the only high-confidence breakpoint.
3. Raw figure: show the interruption and rebound.
4. Main ITS: report descriptive level and slope changes.
5. Economic magnitudes: show observed-minus-expected and cumulative recovery.
6. Diagnostics: exact-date concentration, institution concentration, historical rarity.
7. Robustness: alternative windows and Poisson QMLE.
8. Interpretation: temporary interruption followed by higher-than-historical entry.
