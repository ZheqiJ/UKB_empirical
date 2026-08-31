# Project-Entry Structured Institutional Chronology Design

## Design Logic

This project-entry design deliberately follows the JOM-style logic discussed for the paper:

```text
institutional evidence
-> timeline of system evolution
-> institutionally justified periods
-> quantitative trajectory
-> segmented ITS
```

This is a structured institutional chronology, not formal qualitative open/axial coding. The institutional periods below are derived only from the evidence in `analyses/interrupted_time_series/project_entry/design/institutional_timeline_project_entry.md`.

## A. System-Evolution Periods

Smallest defensible periodization:

| Period | Start date | End date | Institutional basis | Process stage affected | Why it may matter for recorded project starts | Confidence | ITS role |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pre-transition operating regime | 2012-03 for system history; 2019-01 for recommended estimation window | 2024-06 | UKB data had long been available through the pre-RAP-default access system; RAP existed from 2021 but was not default for all new projects/additional data | Application, approval, MTA, payment, data release under historical access model | Provides historical project-start trajectory before system-wide RAP-default transition | HIGH | Primary pre-period |
| RAP-default transition/onboarding context | 2024-07 | 2025-03 | 5 July 2024 RAP-default transition; transition-phase data-update hold until Q4 2024; mandatory training released in October 2024; existing-user training deadline 31 March 2025 | Access modality, training, RAP enablement, data dispensing, exemptions | New and additional-data projects faced RAP-default access path and training/onboarding gates | MEDIUM-HIGH | Secondary transition-window specification or contextual overlay |
| Post-training-deadline RAP-default operating context | 2025-04 | 2025-12 for current paper window | Existing-user training deadline passed; RAP-default policy and exemption governance continued | RAP-default operation and compliance | Provides post-transition period after the major documented onboarding deadline | MEDIUM | Context and post-period description |

Do not force separate May-June, July-September, or October 2024 institutional periods. Those are observed-data labels only.

## B. Institutional Overlay With Raw Starts

Figure created:

`analyses/interrupted_time_series/project_entry/figures/project_entry_institutional_timeline_raw_starts.svg`

The figure uses distinct conventions:

- Solid vertical line: documented July 2024 RAP-default institutional breakpoint.
- Shaded region: externally supported transition/onboarding context from July 2024 through March 2025.
- Red outlined point annotations: outcome-defined unusual months, with no independent institutional status.

Descriptive table from `analyses/interrupted_time_series/project_entry/data/its_project_starts_monthly.csv`:

| Institutional period | Months | Mean starts | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pre-transition operating regime, 2019-01 to 2024-06 | 66 | 51.88 | 51 | 5 | 94 |
| RAP-default transition/onboarding context, 2024-07 to 2025-03 | 9 | 88.22 | 106 | 0 | 208 |
| Post-training-deadline RAP-default operating context, 2025-04 to 2025-12 | 9 | 149.11 | 160 | 102 | 191 |

These summaries are descriptive overlays after fixing institutional periods. They are not estimates of a final ITS.

## C. Primary Paper-Ready ITS

Primary monthly segmented ITS:

```text
Y_t = beta_0
    + beta_1 Time_t
    + beta_2 PostTransition_t
    + beta_3 TimeAfterTransition_t
    + month-of-year FE
    + epsilon_t
```

Definitions:

- `Y_t`: recorded UKB project starts in month `t`.
- `Time_t`: linear calendar-month index.
- `PostTransition_t`: equals 1 for July 2024 onward, 0 otherwise.
- `TimeAfterTransition_t`: equals 0 before July 2024 and increments monthly after the transition.
- `month-of-year FE`: seasonality controls for recurring calendar-month differences.

Interpretation:

- `beta_1`: pre-transition recorded-start trajectory.
- `beta_2`: descriptive level change around the institutional transition.
- `beta_3`: descriptive change in post-transition slope.

Do not call `beta_2` or `beta_3` a causal policy effect.

Secondary institutionally justified specification:

```text
Y_t = beta_0
    + beta_1 Time_t
    + beta_2 TransitionOnboardingWindow_t
    + beta_3 PostTrainingDeadline_t
    + month-of-year FE
    + epsilon_t
```

Where `TransitionOnboardingWindow_t` equals 1 for July 2024 through March 2025 and `PostTrainingDeadline_t` equals 1 for April 2025 onward. This is justified only as a broad transition/onboarding characterization. It should not be described as a formal July-September pause or October restart.

## D. Exploratory / Data-Driven Characterization

Keep these analyses separate from the primary institutionally anchored ITS:

- Month-specific event-time indicators around 2024.
- Flexible monthly coefficients for 2024.
- Structural-break or change-point detection.
- Historical rarity of rolling 3-month troughs.
- Exact-date clustering or batching diagnostics.

Label all such outputs `EXPLORATORY / DATA-DRIVEN CHARACTERIZATION`.

## E. Estimation Window

Candidate windows:

| Window | Strengths | Limitations | Use |
| --- | --- | --- | --- |
| 2019-2025 | Captures several pre-transition years, includes COVID-era irregularity, and retains enough pre-period seasonality | COVID-era disruptions and secular UKB growth may challenge one linear trend | Recommended primary window |
| 2021-2025 | Begins with RAP launch era and avoids earliest low-volume history | RAP launch itself may be part of the institutional evolution; fewer pre-period years | Robustness window |
| 2022-2025 | Focuses on modern high-volume project-entry system | Short pre-period for seasonality and trend; more sensitive to 2023-2024 growth | Robustness/sensitivity window |

Do not use 2012-2026 as the main window for a single linear trend. The full 2012-2026 series spans the launch ramp-up, secular growth in researcher demand, major data releases, COVID irregularities, the 2024 RAP transition, and 2026 platform shocks/right-edge incompleteness. It is better suited for historical context and plots.

Recommended primary window: 2019-2025. Prespecified robustness windows: 2021-2025 and 2022-2025. Do not select the window based on statistical significance.

## F. Paper-Ready Economic Magnitudes

The final analysis should translate coefficients into descriptive magnitudes:

1. Fit expected monthly recorded starts from the pre-transition path.
2. Compute monthly observed-minus-expected gaps.
3. Accumulate the monthly gaps into a cumulative shortfall/surplus.
4. Measure duration of interruption as consecutive months below the fitted pre-transition expectation.
5. Measure rebound magnitude as the largest positive post-transition observed-minus-expected gap, with October 2024 labelled descriptive unless institutionally documented later.
6. Report the date when the cumulative gap is recovered, if ever.
7. Compare post-transition average and trajectory against the fitted pre-transition expected path.

These are descriptive deviations from a fitted historical path, not causal counterfactual treatment effects.

## G. Prespecified Robustness

Limit robustness to a small paper-ready set:

1. Alternative pre-periods: 2019-2025 primary, 2021-2025 and 2022-2025 robustness.
2. OLS segmented ITS with HAC/Newey-West uncertainty.
3. Poisson QMLE/count ITS.
4. Month-of-year seasonality.
5. Historical rarity / rolling-window comparison.
6. Placebo institutional dates, chosen before inspecting significance.
7. Exact-date batching audit.
8. Institution concentration of unusual start months.

Do not expand this into a specification search.

## H. Final Paper Outputs

### Figure 1: Project Entry Around The RAP Transition

Panel A: raw monthly recorded project starts plus institutional timeline.

Panel B: observed versus fitted pre-transition expected starts.

Panel C: cumulative observed-minus-expected gap.

### Table 1: Compact Segmented ITS Estimates

Report coefficients, HAC uncertainty, count-model robustness, and economic magnitudes. Keep interpretation descriptive.

### Appendix

Include exact-date batching, institution concentration, alternative windows, Poisson robustness, exploratory month-by-month/event-time patterns, and the structured institutional chronology.

Candidate stylized-fact statements:

> Recorded UK Biobank project starts exhibit an unusually sharp interruption around the 2024 RAP-default access transition, followed by a pronounced rebound in the public project-start series.

> The public project-start series shows a large but descriptive disruption around the July 2024 access transition; the institutional evidence supports July 2024 as the primary breakpoint, not a separately documented July-September pause or October restart.

> Because public `Start date` appears to capture a downstream recorded project-start or operational-access date, the outcome should be interpreted as project entry into the operational UKB access system rather than new application submissions.

## Stopping Point

This design stops before final segmented-regression estimation. The next step should be review of whether the July 2024 breakpoint and the July 2024 to March 2025 transition/onboarding window are institutionally defensible enough for the paper.
