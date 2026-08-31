# Interrupted Time-Series Design Proposal

## Objective

The empirical objective is descriptive: document temporal and cross-project patterns around the 5 July 2024 UKB access transition. The transition date is an institutional/policy marker, not an observed treatment date for every incumbent project.

## ITS-1: Aggregate Project Starts

Unit: calendar month. Primary outcome: number of new project starts.

Baseline segmented specification:

```text
Y_t = alpha + beta1 time_t + beta2 PostTransition_t
    + beta3 TimeAfterTransition_t + month-of-year FE + error_t
```

The raw data strongly suggest testing a transition-window parameterization before a one-month break:

```text
Y_t = alpha + beta1 time_t + beta2 JulSep2024_t
    + beta3 Oct2024Restart_t + beta4 PostOct2024_t
    + month-of-year FE + error_t
```

Linear models should report HAC/Newey-West uncertainty. Count-model robustness can use Poisson or negative-binomial models, but coefficients remain descriptive.

## ITS-2: Aggregate Incumbent Publication Trajectory

Unit: project-month or project-quarter. Sample: projects started before 2024-07-05. Outcomes:

- publication app-links per post-start incumbent project-period;
- any-publication rate;
- raw publication count.

Suggested descriptive windows:

- immediate transition: 2024Q3-Q4;
- early lag: 2025Q1-Q2;
- mid lag: 2025Q3-Q4;
- April 2026 institutional-platform robustness marker: 2026Q2 separately.

Publication lag is central. Do not redefine 2025 as the policy date; use delayed windows to describe timing.

## ITS-3: Comparative Descriptive ITS

Primary comparison: C05 legacy-exposure proxy versus RAP-intensive comparison group. Use C03 and C06 as measurement-sensitivity diagnostics.

Descriptive structure:

```text
Y_gt = alpha_g + gamma_t + beta1 LegacyProxy_g * PostTransition_t
    + beta2 LegacyProxy_g * TimeAfterTransition_t
    + beta3 LegacyProxy_g * JulSep2024_t
    + beta4 LegacyProxy_g * PostOct2024_t
    + error_gt
```

The interaction is a post-transition differential change, not a treatment effect. Report raw group trajectories and baseline composition before any adjusted model.

## ITS-4: Descriptive Event-Time Presentation

Retain event-time plots only as descriptive dynamic trajectories around 2024Q3. Do not label pretrend p-values as PASS/FAIL for identification. Report coefficients, confidence intervals, raw trajectories, and economic magnitudes.

## Transition And Shock Coding

- `PostTransition_t`: periods beginning 2024Q3 or later for quarterly models, July 2024 or later for monthly models.
- `JulSep2024_t`: July, August, and September 2024 administrative pause window.
- `Oct2024Restart_t`: October 2024 batch restart.
- `April2026InstitutionalPlatformShock_t`: 2026Q2 or April 2026 onward, reported separately or excluded from the main post-transition window.

## Robustness Strategy

1. Plot raw series first.
2. Report aggregate starts before comparative publication designs.
3. Use C03/C05/C06 as prespecified exposure-proxy sensitivity, not as a p-value search.
4. Separate extensive and intensive publication margins.
5. Add project-age and multi-label modality diagnostics before interpreting group differences.
6. End the main window before April 2026 where appropriate and report 2026Q2 separately.

## Current Feasibility Ratings

| Design | Feasibility |
| --- | --- |
| project_entry_starts | HIGH |
| aggregate_incumbent_publications | HIGH |
| comparative_exposure_proxy_its | MEDIUM |
| recent_vs_mature_projects | MEDIUM |
| modality_heterogeneity | MEDIUM |
| institution_country_patterns | LOW_MEDIUM |
| returned_data_timing | LOW |
