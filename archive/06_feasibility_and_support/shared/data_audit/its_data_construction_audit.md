# ITS Data Construction Audit

## Purpose

This audit records data-construction fixes made before moving from feasibility tables to empirical regressions. The package remains descriptive: the July 2024 date is an institutional transition marker, not an observed project-level treatment date.

## Corrections Applied

- Comparative quarterly panels now exclude post-transition entrants. Rows are retained only when `project_start_date < 2024-07-05`.
- C03/C05/C06 comparison groups use the same `group_label()` logic everywhere, so `control_overlap_original_*` labels are counted as RAP-intensive comparison projects.
- Modality classification is multi-label. Projects can count in multiple modality flags; `other_or_unclear` is used only when no specific flag is detected.
- The old one-hot broad-modality field is retained only as `primary_modality` for convenience.
- Pre-transition baseline fields are now named `mean_pretransition_24m_publications` and `any_pretransition_24m_publication_rate_percent`.
- Denominators are named `post_start_incumbent_projects`; they are not active-project counts.
- Publication outcomes now report app-publication links, unique publication IDs, and fractional publication counts. Any-publication rates remain a separate extensive-margin measure.

## Reconciliation Results

All reconciliation checks passed: True.

Post-transition entrant panel rows excluded from comparative series: 11524.

C05 incumbent sample after corrections:

- Legacy-exposure proxy projects: 3326
- RAP-intensive comparison projects: 131

| check_name | exposure_proxy_definition | comparison_group | expected_projects | observed_projects | status | note |
| --- | --- | --- | --- | --- | --- | --- |
| comparative_incumbent_app_set | CONTROL_C03 | legacy_exposure_proxy | 3327 | 3327 | PASS | Comparative quarterly rows must contain only pre-2024-07-05 incumbent projects. |
| group_composition_incumbent_count | CONTROL_C03 | legacy_exposure_proxy | 3327 | 3327 | PASS | Group composition table must use the same incumbent definition. |
| modality_overlap_incumbent_count | CONTROL_C03 | legacy_exposure_proxy | 3327 | 3327 | PASS | Every group project must receive at least one modality flag, including other_or_unclear. |
| comparative_incumbent_app_set | CONTROL_C03 | rap_intensive_comparison | 130 | 130 | PASS | Comparative quarterly rows must contain only pre-2024-07-05 incumbent projects. |
| group_composition_incumbent_count | CONTROL_C03 | rap_intensive_comparison | 130 | 130 | PASS | Group composition table must use the same incumbent definition. |
| modality_overlap_incumbent_count | CONTROL_C03 | rap_intensive_comparison | 130 | 130 | PASS | Every group project must receive at least one modality flag, including other_or_unclear. |
| comparative_incumbent_app_set | CONTROL_C05 | legacy_exposure_proxy | 3326 | 3326 | PASS | Comparative quarterly rows must contain only pre-2024-07-05 incumbent projects. |
| group_composition_incumbent_count | CONTROL_C05 | legacy_exposure_proxy | 3326 | 3326 | PASS | Group composition table must use the same incumbent definition. |
| modality_overlap_incumbent_count | CONTROL_C05 | legacy_exposure_proxy | 3326 | 3326 | PASS | Every group project must receive at least one modality flag, including other_or_unclear. |
| comparative_incumbent_app_set | CONTROL_C05 | rap_intensive_comparison | 131 | 131 | PASS | Comparative quarterly rows must contain only pre-2024-07-05 incumbent projects. |
| group_composition_incumbent_count | CONTROL_C05 | rap_intensive_comparison | 131 | 131 | PASS | Group composition table must use the same incumbent definition. |
| modality_overlap_incumbent_count | CONTROL_C05 | rap_intensive_comparison | 131 | 131 | PASS | Every group project must receive at least one modality flag, including other_or_unclear. |
| comparative_incumbent_app_set | CONTROL_C06 | legacy_exposure_proxy | 3193 | 3193 | PASS | Comparative quarterly rows must contain only pre-2024-07-05 incumbent projects. |
| group_composition_incumbent_count | CONTROL_C06 | legacy_exposure_proxy | 3193 | 3193 | PASS | Group composition table must use the same incumbent definition. |
| modality_overlap_incumbent_count | CONTROL_C06 | legacy_exposure_proxy | 3193 | 3193 | PASS | Every group project must receive at least one modality flag, including other_or_unclear. |
| comparative_incumbent_app_set | CONTROL_C06 | rap_intensive_comparison | 297 | 297 | PASS | Comparative quarterly rows must contain only pre-2024-07-05 incumbent projects. |
| group_composition_incumbent_count | CONTROL_C06 | rap_intensive_comparison | 297 | 297 | PASS | Group composition table must use the same incumbent definition. |
| modality_overlap_incumbent_count | CONTROL_C06 | rap_intensive_comparison | 297 | 297 | PASS | Every group project must receive at least one modality flag, including other_or_unclear. |

## Publication Multiplicity Sensitivity

| quarter | publication_app_links | unique_publication_ids | fractional_publication_count | app_links_minus_unique_ids | fractional_reduction_percent_vs_app_links |
| --- | --- | --- | --- | --- | --- |
| 2024Q2 | 519 | 506 | 506.000 | 13 | 2.50 |
| 2024Q3 | 539 | 511 | 511.000 | 28 | 5.19 |
| 2024Q4 | 507 | 484 | 484.000 | 23 | 4.54 |
| 2025Q1 | 629 | 602 | 601.500 | 27 | 4.37 |
| 2026Q2 | 588 | 569 | 566.667 | 19 | 3.63 |

## Recent Publication Completeness

Latest exact publication date in cleaned application-publication links: 2026-07-16.

Latest exact publication date in local Schema 19 snapshot: 2026-07-16.

The right edge remains a completeness risk. Do not interpret a 2026Q2 movement as a platform effect until external bibliographic completeness is validated.

| grain | period | period_start | period_end | publication_app_links | unique_publication_ids | fractional_publication_count | apps_with_any_publication |
| --- | --- | --- | --- | --- | --- | --- | --- |
| month | 2026-02 | 2026-02-01 | 2026-02-28 | 256 | 245 | 245.000 | 226 |
| month | 2026-03 | 2026-03-01 | 2026-03-31 | 287 | 280 | 280.000 | 239 |
| month | 2026-04 | 2026-04-01 | 2026-04-30 | 301 | 287 | 287.000 | 252 |
| month | 2026-05 | 2026-05-01 | 2026-05-31 | 267 | 262 | 262.000 | 232 |
| month | 2026-06 | 2026-06-01 | 2026-06-30 | 167 | 158 | 158.000 | 150 |
| month | 2026-07 | 2026-07-01 | 2026-07-31 | 168 | 165 | 165.000 | 153 |

## April 2026 Institutional Marker

No official full RAP shutdown was verified. The neutral variable name is `april_2026_institutional_platform_shock_or_after`.

| Source | URL | Use |
| --- | --- | --- |
| Participant withdrawals on UKB-RAP | https://community.ukbiobank.ac.uk/hc/en-gb/articles/34853452782621-Participant-withdrawals-on-UKB-RAP | Verifies 1 April 2026 withdrawal-enforcement/platform-governance marker. |
| Project not enabled for UKB-RAP | https://community.ukbiobank.ac.uk/hc/en-gb/articles/22784123882909-Why-does-it-say-that-my-project-is-not-enabled-for-UKB-RAP | Verifies 31 March 2026 Code Repository training-module requirement. |
