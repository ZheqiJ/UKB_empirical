# Design 1 Quarterly Publication Results

Source commit: `8465974b8998161d795e553a08dd737aa4b3e83a`
Policy date: `2024-07-05`

## Empirical Objective

The purpose is to test whether the 5 July 2024 UK Biobank RAP transition
changed scientific output for applications whose workflows were newly
subject to the RAP requirement, relative to applications that were already
substantially RAP-bound before the policy.

The main estimand asks whether publication output changed differentially
after the RAP policy for provisionally NEWLY_RAP_BOUND applications
relative to provisionally ALREADY_RAP_BOUND/control-candidate applications.
This is an incumbent-project policy design, not an application-approval
test and not a project-entry design.

## Sample Construction

| metric | value |
| --- | --- |
| source_commit | 8465974b8998161d795e553a08dd737aa4b3e83a |
| design_scope | quarterly |
| working_universe_projects | 6935 |
| quarter_panel_rows | 75973 |
| month_panel_rows | not_run_in_quarterly_design |
| quarter_window | 2022Q3_2026Q2 |
| month_window | not_run_in_quarterly_design |
| policy_date | 2024-07-05 |
| missing_project_start_dates | 0 |
| pre_start_panel_rows | 0 |
| publication_events_in_complete_quarter_panel | 12400 |
| schema19_publications | 14633 |
| exact_date_pub | 14633 |
| schema24_links | 12598 |
| unique_application_publication_pairs | 12598 |
| duplicate_application_publication_pairs | 0 |
| clean_events_in_working_universe | 12568 |
| publication_observation_end_date | 2026-07-16 |
| publication_before_project_start_events | 24 |
| events_after_main_complete_panel_window | 168 |
| top_1pct_high_output_apps | 72 |
| heterogeneity_triggered_count_positive_any_nonpositive | True |
| CONTROL_C0_incumbent_apps | 3374 |
| CONTROL_C0_treated_apps | 3344 |
| CONTROL_C0_control_apps | 30 |
| CONTROL_C01_incumbent_apps | 3450 |
| CONTROL_C01_treated_apps | 3338 |
| CONTROL_C01_control_apps | 112 |
| CONTROL_C03_incumbent_apps | 3455 |
| CONTROL_C03_treated_apps | 3325 |
| CONTROL_C03_control_apps | 130 |
| CONTROL_C05_incumbent_apps | 3455 |
| CONTROL_C05_treated_apps | 3324 |
| CONTROL_C05_control_apps | 131 |

## Main Quarterly DID Q0

| control_definition | outcome | n_apps | n_treated_apps | n_control_apps | estimate | clustered_se | p_value | ci_low | ci_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count | 3374 | 3344 | 30 | 0.089550 | 0.086188 | 0.298799 | -0.079378 | 0.258479 |
| CONTROL_C0 | any_publication | 3374 | 3344 | 30 | -0.007270 | 0.017895 | 0.684554 | -0.042345 | 0.027805 |
| CONTROL_C01 | publication_count | 3450 | 3338 | 112 | 0.006505 | 0.028006 | 0.816336 | -0.048388 | 0.061397 |
| CONTROL_C01 | any_publication | 3450 | 3338 | 112 | -0.012307 | 0.013155 | 0.349480 | -0.038091 | 0.013476 |
| CONTROL_C03 | publication_count | 3455 | 3325 | 130 | 0.015205 | 0.024773 | 0.539373 | -0.033351 | 0.063760 |
| CONTROL_C03 | any_publication | 3455 | 3325 | 130 | -0.004772 | 0.012242 | 0.696669 | -0.028766 | 0.019222 |
| CONTROL_C05 | publication_count | 3455 | 3324 | 131 | 0.015375 | 0.024577 | 0.531591 | -0.032796 | 0.063545 |
| CONTROL_C05 | any_publication | 3455 | 3324 | 131 | -0.002373 | 0.012360 | 0.847738 | -0.026599 | 0.021852 |

## Project-Age Adjusted Q1

| control_definition | outcome | n_apps | estimate | clustered_se | p_value | note |
| --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count | 3374 | 0.109567 | 0.083133 | 0.187511 | age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus |
| CONTROL_C0 | any_publication | 3374 | 0.005621 | 0.019475 | 0.772860 | age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus |
| CONTROL_C01 | publication_count | 3450 | 0.023196 | 0.027681 | 0.402041 | age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus |
| CONTROL_C01 | any_publication | 3450 | -0.002697 | 0.012651 | 0.831203 | age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus |
| CONTROL_C03 | publication_count | 3455 | 0.025797 | 0.024362 | 0.289644 | age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus |
| CONTROL_C03 | any_publication | 3455 | 0.001043 | 0.011710 | 0.929060 | age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus |
| CONTROL_C05 | publication_count | 3455 | 0.025244 | 0.024148 | 0.295834 | age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus |
| CONTROL_C05 | any_publication | 3455 | 0.003050 | 0.011772 | 0.795560 | age bins: q0,q1,q2,q3,q4_7,q8_11,q12_15,q16_23,q24_35,q36_47,q48_plus |

## Event-Study Joint Pretrend Tests

| control_definition | outcome | statistic_chi2 | df | p_value | verdict | warning |
| --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count | 16.166159 | 7 | 0.023641 | WARNING |  |
| CONTROL_C0 | any_publication | 15.265943 | 7 | 0.032738 | WARNING |  |
| CONTROL_C01 | publication_count | 12.776543 | 7 | 0.077744 | PASS |  |
| CONTROL_C01 | any_publication | 14.771565 | 7 | 0.039042 | WARNING |  |
| CONTROL_C03 | publication_count | 13.681310 | 7 | 0.057149 | PASS |  |
| CONTROL_C03 | any_publication | 12.237506 | 7 | 0.093014 | PASS |  |
| CONTROL_C05 | publication_count | 12.747026 | 7 | 0.078517 | PASS |  |
| CONTROL_C05 | any_publication | 9.785065 | 7 | 0.201084 | PASS |  |

## Transition Quarter Robustness

| control_definition | outcome | estimate | clustered_se | p_value | note |
| --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count | 0.069814 | 0.071165 | 0.326589 | drops 2024Q3 transition quarter; post starts 2024Q4 |
| CONTROL_C0 | any_publication | -0.015718 | 0.019154 | 0.411867 | drops 2024Q3 transition quarter; post starts 2024Q4 |
| CONTROL_C01 | publication_count | 0.008471 | 0.025445 | 0.739206 | drops 2024Q3 transition quarter; post starts 2024Q4 |
| CONTROL_C01 | any_publication | -0.010197 | 0.014343 | 0.477140 | drops 2024Q3 transition quarter; post starts 2024Q4 |
| CONTROL_C03 | publication_count | 0.018387 | 0.022668 | 0.417294 | drops 2024Q3 transition quarter; post starts 2024Q4 |
| CONTROL_C03 | any_publication | -0.001387 | 0.013043 | 0.915330 | drops 2024Q3 transition quarter; post starts 2024Q4 |
| CONTROL_C05 | publication_count | 0.017940 | 0.022496 | 0.425180 | drops 2024Q3 transition quarter; post starts 2024Q4 |
| CONTROL_C05 | any_publication | 0.000691 | 0.013092 | 0.957920 | drops 2024Q3 transition quarter; post starts 2024Q4 |

## Post Window Summaries For CONTROL_C05

| period | metric | value | treated_n | control_n | note |
| --- | --- | --- | --- | --- | --- |
| short_run_2024Q3_Q4 | publication_count | -0.008588 | 3324 | 131 | raw_post_window_difference |
| short_run_2024Q3_Q4 | any_publication | -0.005412 | 3324 | 131 | raw_post_window_difference |
| medium_run_2025Q1_Q4 | publication_count | 0.027034 | 3324 | 131 | raw_post_window_difference |
| medium_run_2025Q1_Q4 | any_publication | 0.021391 | 3324 | 131 | raw_post_window_difference |
| later_post_2026Q1_Q2 | publication_count | -0.001461 | 3324 | 131 | raw_post_window_difference |
| later_post_2026Q1_Q2 | any_publication | 0.025688 | 3324 | 131 | raw_post_window_difference |

## Drop First Partial Quarter

| control_definition | outcome | estimate | clustered_se | p_value | note |
| --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count | 0.088149 | 0.090706 | 0.331144 | drops first partial at-risk quarter |
| CONTROL_C0 | any_publication | -0.011544 | 0.018596 | 0.534753 | drops first partial at-risk quarter |
| CONTROL_C01 | publication_count | 0.002298 | 0.029117 | 0.937105 | drops first partial at-risk quarter |
| CONTROL_C01 | any_publication | -0.015434 | 0.013505 | 0.253101 | drops first partial at-risk quarter |
| CONTROL_C03 | publication_count | 0.010855 | 0.025616 | 0.671752 | drops first partial at-risk quarter |
| CONTROL_C03 | any_publication | -0.007945 | 0.012525 | 0.525865 | drops first partial at-risk quarter |
| CONTROL_C05 | publication_count | 0.011006 | 0.025404 | 0.664851 | drops first partial at-risk quarter |
| CONTROL_C05 | any_publication | -0.005467 | 0.012645 | 0.665514 | drops first partial at-risk quarter |

## Count Outlier Robustness

| control_definition | outcome | estimate | clustered_se | p_value | note |
| --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count | 0.000880 | 0.017431 | 0.959734 | excluded_top_1pct_apps=72 |
| CONTROL_C01 | publication_count | -0.014089 | 0.016044 | 0.379848 | excluded_top_1pct_apps=72 |
| CONTROL_C03 | publication_count | -0.002539 | 0.015220 | 0.867530 | excluded_top_1pct_apps=72 |
| CONTROL_C05 | publication_count | -0.002238 | 0.015104 | 0.882183 | excluded_top_1pct_apps=72 |

## Pre-Policy Productivity Strata

| control_definition | outcome | n_apps | n_treated_apps | n_control_apps | estimate | clustered_se | p_value | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C05 | publication_count | 2518 | 2414 | 104 | 0.014228 | 0.010575 | 0.178489 | stratum=no_pre_policy_publication; stratum_defined_with_pre_policy_publications_only |
| CONTROL_C05 | any_publication | 2518 | 2414 | 104 | 0.004848 | 0.009803 | 0.620937 | stratum=no_pre_policy_publication; stratum_defined_with_pre_policy_publications_only |
| CONTROL_C05 | publication_count | 937 | 910 | 27 | 0.052825 | 0.100848 | 0.600410 | stratum=positive_pre_policy_publication; stratum_defined_with_pre_policy_publications_only |
| CONTROL_C05 | any_publication | 937 | 910 | 27 | 0.004813 | 0.040213 | 0.904733 | stratum=positive_pre_policy_publication; stratum_defined_with_pre_policy_publications_only |

## Monthly Robustness

Not run in Design 1. Monthly timing robustness is intentionally held for the next sequential design.

## Control Sensitivity

| control_definition | outcome | treated_n | control_n | q0_estimate | q0_se | q1_age_adjusted_estimate | pretrend_p_value | pretrend_verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count | 3344 | 30 | 0.089550 | 0.086188 | 0.109567 | 0.023641 | WARNING |
| CONTROL_C0 | any_publication | 3344 | 30 | -0.007270 | 0.017895 | 0.005621 | 0.032738 | WARNING |
| CONTROL_C01 | publication_count | 3338 | 112 | 0.006505 | 0.028006 | 0.023196 | 0.077744 | PASS |
| CONTROL_C01 | any_publication | 3338 | 112 | -0.012307 | 0.013155 | -0.002697 | 0.039042 | WARNING |
| CONTROL_C03 | publication_count | 3325 | 130 | 0.015205 | 0.024773 | 0.025797 | 0.057149 | PASS |
| CONTROL_C03 | any_publication | 3325 | 130 | -0.004772 | 0.012242 | 0.001043 | 0.093014 | PASS |
| CONTROL_C05 | publication_count | 3324 | 131 | 0.015375 | 0.024577 | 0.025244 | 0.078517 | PASS |
| CONTROL_C05 | any_publication | 3324 | 131 | -0.002373 | 0.012360 | 0.003050 | 0.201084 | PASS |

## Interpretation Guardrails

- C0-C5 are provisional controls, not final clean controls.
- Post-policy entrants are not used for incumbent DID identification.
- Pre-project periods are absent from the risk set, not coded as zero.
- Publication is lagged; 2024Q3 effects should be interpreted cautiously.
- Current data do not verify project end dates, active status, access dates, RAP migration dates, or RAP usage logs.
