# Publication ITS Design

## Question

How did publication output among pre-transition UKB incumbent projects evolve around and after the July 2024 RAP-based access transition?

## Design Status

This is a descriptive interrupted-time-series / stylized-fact design. July 2024 is an institutional transition marker, not a verified treatment date for every incumbent project.

## Incumbent Sample

The analysis keeps projects with public project start date before 2024-07-05. This avoids mechanically mixing post-transition entrants into the publication-output composition.

The monthly denominator is `post_start_incumbent_projects`: the number of pre-transition incumbent projects whose public start date has occurred by the end of month `t`. It grows before July 2024 as future incumbents enter their project period, then becomes fixed at 4332 after the transition.

## Primary Outcome And Window

Primary intensity outcome: `fractional_publications_per_100_post_start_incumbents`.

This is selected before inspecting significance because it normalizes for the post-start incumbent pool and avoids full double counting of publications linked to multiple applications.

Primary window: 2019-01 through 2025-12. The raw exact publication-event data support consistent construction before 2022-07, the window gives 66 pre-transition and 18 post-transition monthly observations, and 2026 is excluded because of right-edge completeness risk.

## Model

`Y_t = beta_0 + beta_1 Time_t + beta_2 PostJuly2024_t + beta_3 TimeAfterJuly2024_t + month-of-year FE + epsilon_t`.

Primary inference is OLS with Newey-West HAC lag 3. HAC(1), HAC(6), and HAC(12), AR(1) errors, fixed cohort, publication-measure sensitivity, Poisson count robustness, and pre-transition placebos are reported as diagnostics or robustness checks.
