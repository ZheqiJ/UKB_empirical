# Stage 5 Fast Exploratory Results

Source commit: `88292d3-plus-c06`
Policy date: `2024-07-05`

This fast run is provisional. It preserves the existing Stage 3 measurement,
uses C0-C6 as broad control-candidate sensitivity definitions, and does
not finalize treatment/control status.

DMCA outcomes mean an application is linked by evidence to a DMCA-targeted
repository lineage. They are not findings of unlawful conduct or policy
violation.

## Diagnostics

| metric | value |
| --- | --- |
| working_universe_projects | 6935 |
| publication_events | 12592 |
| publication_observation_end | 2026-07-16 |
| p1_existing_project_apps | 4332 |
| p1_post_policy_start_apps_excluded | 2603 |
| control_c0_projects | 42 |
| control_c01_projects | 237 |
| control_c03_projects | 267 |
| control_c05_projects | 269 |
| control_c06_projects | 438 |
| c06_added_projects | 169 |
| dmca_strict_21_merged | 21 |
| dmca_main_27_merged | 27 |
| dmca_broad_48_merged | 48 |
| dmca_curated_unmatched_apps | 0 |

## Control And Exclusion Counts

Controls include explicit overlap labels when C1-C5 pulls in projects
whose original Stage 3 classification was NEWLY_RAP_BOUND, MIXED, or
UNCLEAR. Those rows are excluded from the treated group under that
control definition.

| control_definition | treated | control_clean | control_overlap_original_newly_rap_bound | control_overlap_original_mixed | control_overlap_original_unclear | excluded_mixed | excluded_unclear | excluded_already_rap_not_in_definition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | 5561 | 42 | 0 | 0 | 0 | 183 | 1149 | 0 |
| CONTROL_C01 | 5548 | 42 | 13 | 179 | 3 | 4 | 1146 | 0 |
| CONTROL_C03 | 5525 | 42 | 36 | 179 | 10 | 4 | 1139 | 0 |
| CONTROL_C05 | 5524 | 42 | 37 | 180 | 10 | 3 | 1139 | 0 |
| CONTROL_C06 | 5389 | 42 | 172 | 180 | 44 | 3 | 1105 | 0 |

## P1 Publication DID Means

| control_definition | outcome | treated_n | control_n | treated_pre_mean | treated_post_mean | control_pre_mean | control_post_mean | did_difference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count | 3346 | 30 | 0.855350 | 1.210102 | 1.466667 | 1.133333 | 0.688085 |
| CONTROL_C0 | any_publication | 3346 | 30 | 0.276151 | 0.339809 | 0.100000 | 0.233333 | -0.069675 |
| CONTROL_C01 | publication_count | 3340 | 112 | 0.856587 | 1.211677 | 0.964286 | 1.196429 | 0.122947 |
| CONTROL_C01 | any_publication | 3340 | 112 | 0.276347 | 0.340120 | 0.187500 | 0.348214 | -0.096942 |
| CONTROL_C03 | publication_count | 3327 | 130 | 0.856628 | 1.214908 | 0.930769 | 1.107692 | 0.181358 |
| CONTROL_C03 | any_publication | 3327 | 130 | 0.275924 | 0.340547 | 0.207692 | 0.346154 | -0.073839 |
| CONTROL_C05 | publication_count | 3326 | 131 | 0.855683 | 1.214071 | 0.954198 | 1.129771 | 0.182816 |
| CONTROL_C05 | any_publication | 3326 | 131 | 0.275707 | 0.340349 | 0.213740 | 0.351145 | -0.072762 |
| CONTROL_C06 | publication_count | 3193 | 297 | 0.715315 | 1.064203 | 2.582492 | 3.070707 | -0.139327 |
| CONTROL_C06 | any_publication | 3193 | 297 | 0.254933 | 0.321015 | 0.515152 | 0.606061 | -0.024827 |

## P1 Publication DID Regressions

| control_definition | outcome | n | estimate | robust_se | p_value | warning |
| --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | publication_count_delta_24m | 3376 | 0.688085 | 0.579621 | 0.235177 |  |
| CONTROL_C0 | any_publication_delta_24m | 3376 | -0.069675 | 0.078498 | 0.374755 |  |
| CONTROL_C01 | publication_count_delta_24m | 3452 | 0.122947 | 0.199550 | 0.537814 |  |
| CONTROL_C01 | any_publication_delta_24m | 3452 | -0.096942 | 0.042050 | 0.021146 |  |
| CONTROL_C03 | publication_count_delta_24m | 3457 | 0.181358 | 0.177766 | 0.307631 |  |
| CONTROL_C03 | any_publication_delta_24m | 3457 | -0.073839 | 0.041395 | 0.074459 |  |
| CONTROL_C05 | publication_count_delta_24m | 3457 | 0.182816 | 0.176490 | 0.300276 |  |
| CONTROL_C05 | any_publication_delta_24m | 3457 | -0.072762 | 0.041108 | 0.076725 |  |
| CONTROL_C06 | publication_count_delta_24m | 3490 | -0.139327 | 0.199940 | 0.485899 |  |
| CONTROL_C06 | any_publication_delta_24m | 3490 | -0.024827 | 0.032701 | 0.447724 |  |

## P2 Entry Cohort Means

| design | outcome | pre_policy_start_n | post_policy_start_n | pre_policy_start_mean | post_policy_start_mean | difference | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P2_project_entry_cohort_6m | publication_6m | 682 | 1292 | 0.020528 | 0.022446 | 0.001918 | not_did_sufficient_followup_required |
| P2_project_entry_cohort_6m | any_publication_6m | 682 | 1292 | 0.017595 | 0.018576 | 0.000981 | not_did_sufficient_followup_required |
| P2_project_entry_cohort_12m | publication_12m | 682 | 1292 | 0.118768 | 0.116873 | -0.001895 | not_did_sufficient_followup_required |
| P2_project_entry_cohort_12m | any_publication_12m | 682 | 1292 | 0.070381 | 0.084365 | 0.013984 | not_did_sufficient_followup_required |
| P2_project_entry_cohort_18m | publication_18m | 682 | 538 | 0.310850 | 0.381041 | 0.070190 | not_did_sufficient_followup_required |
| P2_project_entry_cohort_18m | any_publication_18m | 682 | 538 | 0.161290 | 0.215613 | 0.054323 | not_did_sufficient_followup_required |

## P2 Entry Cohort Regressions

| design | control_definition | outcome | coefficient | n | estimate | robust_se | p_value | warning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P2_project_entry_cohort_before_after | all_projects | publication_6m | post_policy_start | 1974 | 0.001918 | 0.008045 | 0.811558 |  |
| P2_project_entry_cohort_before_after | all_projects | any_publication_6m | post_policy_start | 1974 | 0.000981 | 0.006285 | 0.876015 |  |
| P2_project_entry_cohort_before_after | all_projects | publication_12m | post_policy_start | 1974 | -0.001895 | 0.024597 | 0.938582 |  |
| P2_project_entry_cohort_before_after | all_projects | any_publication_12m | post_policy_start | 1974 | 0.013984 | 0.012485 | 0.262694 |  |
| P2_project_entry_cohort_before_after | all_projects | publication_18m | post_policy_start | 1220 | 0.070190 | 0.055968 | 0.209799 |  |
| P2_project_entry_cohort_before_after | all_projects | any_publication_18m | post_policy_start | 1220 | 0.054323 | 0.022662 | 0.016524 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C0 | publication_12m | post_policy_start_x_provisional_treated | 1576 | -0.006128 | 0.030189 | 0.839150 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C0 | any_publication_12m | post_policy_start_x_provisional_treated | 1576 | 0.013330 | 0.014657 | 0.363090 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C01 | publication_12m | post_policy_start_x_provisional_treated | 1634 | -0.017429 | 0.086579 | 0.840461 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C01 | any_publication_12m | post_policy_start_x_provisional_treated | 1634 | 0.018519 | 0.077488 | 0.811113 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C03 | publication_12m | post_policy_start_x_provisional_treated | 1634 | -0.016754 | 0.081816 | 0.837746 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C03 | any_publication_12m | post_policy_start_x_provisional_treated | 1634 | 0.018119 | 0.072751 | 0.803313 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C05 | publication_12m | post_policy_start_x_provisional_treated | 1634 | -0.016754 | 0.081816 | 0.837746 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C05 | any_publication_12m | post_policy_start_x_provisional_treated | 1634 | 0.018119 | 0.072751 | 0.803313 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C06 | publication_12m | post_policy_start_x_provisional_treated | 1636 | -0.120523 | 0.078487 | 0.124639 |  |
| P2_project_entry_cohort_group_interaction | CONTROL_C06 | any_publication_12m | post_policy_start_x_provisional_treated | 1636 | -0.053636 | 0.056212 | 0.339995 |  |

## DMCA 2x2 Tables

| control_definition | outcome | treated_event | treated_n | control_event | control_n | treated_event_rate | control_event_rate | fisher_exact_p | warning |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | dmca_strict_21 | 13 | 3346 | 0 | 30 | 0.003885 | 0.000000 | 1.000000 | zero_cell |
| CONTROL_C0 | dmca_main_27 | 19 | 3346 | 0 | 30 | 0.005678 | 0.000000 | 1.000000 | zero_cell |
| CONTROL_C0 | dmca_broad_48 | 34 | 3346 | 0 | 30 | 0.010161 | 0.000000 | 1.000000 | zero_cell |
| CONTROL_C01 | dmca_strict_21 | 13 | 3340 | 1 | 112 | 0.003892 | 0.008929 | 0.370386 |  |
| CONTROL_C01 | dmca_main_27 | 19 | 3340 | 1 | 112 | 0.005689 | 0.008929 | 0.483930 |  |
| CONTROL_C01 | dmca_broad_48 | 34 | 3340 | 1 | 112 | 0.010180 | 0.008929 | 1.000000 |  |
| CONTROL_C03 | dmca_strict_21 | 13 | 3327 | 1 | 130 | 0.003907 | 0.007692 | 0.415883 |  |
| CONTROL_C03 | dmca_main_27 | 19 | 3327 | 1 | 130 | 0.005711 | 0.007692 | 0.536412 |  |
| CONTROL_C03 | dmca_broad_48 | 34 | 3327 | 1 | 130 | 0.010219 | 0.007692 | 1.000000 |  |
| CONTROL_C05 | dmca_strict_21 | 13 | 3326 | 1 | 131 | 0.003909 | 0.007634 | 0.418341 |  |
| CONTROL_C05 | dmca_main_27 | 19 | 3326 | 1 | 131 | 0.005713 | 0.007634 | 0.539199 |  |
| CONTROL_C05 | dmca_broad_48 | 34 | 3326 | 1 | 131 | 0.010222 | 0.007634 | 1.000000 |  |
| CONTROL_C06 | dmca_strict_21 | 10 | 3193 | 4 | 297 | 0.003132 | 0.013468 | 0.025935 |  |
| CONTROL_C06 | dmca_main_27 | 15 | 3193 | 5 | 297 | 0.004698 | 0.016835 | 0.023023 |  |
| CONTROL_C06 | dmca_broad_48 | 28 | 3193 | 7 | 297 | 0.008769 | 0.023569 | 0.025355 |  |

## DMCA LPM Regressions

| control_definition | outcome | n | estimate | robust_se | p_value | warning |
| --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | dmca_strict_21 | 3376 | 0.002230 | 0.001013 | 0.027708 | zero_cell |
| CONTROL_C0 | dmca_main_27 | 3376 | 0.003510 | 0.001298 | 0.006853 | zero_cell |
| CONTROL_C0 | dmca_broad_48 | 3376 | 0.005932 | 0.001751 | 0.000706 | zero_cell |
| CONTROL_C01 | dmca_strict_21 | 3452 | -0.005530 | 0.009003 | 0.539019 |  |
| CONTROL_C01 | dmca_main_27 | 3452 | -0.003862 | 0.009010 | 0.668222 |  |
| CONTROL_C01 | dmca_broad_48 | 3452 | -0.000604 | 0.009069 | 0.946873 |  |
| CONTROL_C03 | dmca_strict_21 | 3457 | -0.003692 | 0.007823 | 0.636944 |  |
| CONTROL_C03 | dmca_main_27 | 3457 | -0.001978 | 0.007839 | 0.800754 |  |
| CONTROL_C03 | dmca_broad_48 | 3457 | 0.001877 | 0.007930 | 0.812856 |  |
| CONTROL_C05 | dmca_strict_21 | 3457 | -0.003573 | 0.007768 | 0.645512 |  |
| CONTROL_C05 | dmca_main_27 | 3457 | -0.001872 | 0.007784 | 0.809915 |  |
| CONTROL_C05 | dmca_broad_48 | 3457 | 0.002091 | 0.007880 | 0.790706 |  |
| CONTROL_C06 | dmca_strict_21 | 3490 | -0.009471 | 0.006899 | 0.169845 |  |
| CONTROL_C06 | dmca_main_27 | 3490 | -0.010960 | 0.007660 | 0.152499 |  |
| CONTROL_C06 | dmca_broad_48 | 3490 | -0.012364 | 0.008999 | 0.169480 |  |

## DMCA Lineage Count Secondary Regressions

| control_definition | outcome | n | estimate | robust_se | p_value | warning |
| --- | --- | --- | --- | --- | --- | --- |
| CONTROL_C0 | dmca_lineage_count | 3376 | 0.011880 | 0.005739 | 0.038447 |  |
| CONTROL_C01 | dmca_lineage_count | 3452 | 0.005602 | 0.010266 | 0.585259 |  |
| CONTROL_C03 | dmca_lineage_count | 3457 | 0.008542 | 0.009290 | 0.357862 |  |
| CONTROL_C05 | dmca_lineage_count | 3457 | 0.008843 | 0.009245 | 0.338793 |  |
| CONTROL_C06 | dmca_lineage_count | 3490 | -0.042697 | 0.035076 | 0.223504 |  |

## Output Files

- `data/analysis/design1_quarterly_publication/project_outcomes_input.csv`
- `data/intermediate/fast_pipeline/stage4_fast_publication_events.csv`
- `data/intermediate/fast_pipeline/stage4_fast_publication_period_panel.csv`
- `data/intermediate/fast_pipeline/stage4_fast_dmca_crosswalk.csv`
- `data/intermediate/fast_pipeline/stage4_fast_dmca_unmatched_apps.csv`
- `data/intermediate/fast_pipeline/stage5_fast_regression_results.csv`
- `data/intermediate/fast_pipeline/stage5_fast_group_means.csv`
- `data/intermediate/fast_pipeline/stage5_fast_dmca_2x2.csv`
- `figures/stage5_publication_did.png`
- `figures/stage5_publication_cohort.png`
- `figures/stage5_dmca_rates.png`

## Limitations To Revisit

- C0-C6 are provisional broad controls, not final causal controls.
- P2 is a project-entry before/after cohort design, not a DID.
- DMCA regressions are rare-outcome exploratory associations, not a
  conventional pre/post policy DID.
- Curated DMCA application-only links use a lower-bound count of one when
  notice/lineage evidence is not available in the current local audit files.
