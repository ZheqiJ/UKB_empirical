# Timing Feasibility

Policy date: `2024-07-05`.

This step uses only the fixed working research-project universe: `6,935`
Schema 27 applications matched to the UKB Projects website with one recovered
start date. The `132` unmatched Schema 27 records are excluded from
the working sample and retained only in the audit output.

These counts are for timing feasibility only. They describe project-start
cohort sizes around the policy date and must not be interpreted as a policy
effect. No treatment/control classification and no DID regression is run here.

Source commit: `0336c4ed5bdc8ecec64b77a4e0f7e4caa7f88924`.

## Policy Windows

The policy date itself is counted with the after-policy side.

| window_months | before_start_inclusive | before_end_inclusive | before_projects | after_start_inclusive | after_end_inclusive | after_projects |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | 2024-04-05 | 2024-07-04 | 101 | 2024-07-05 | 2024-10-05 | 39 |
| 6 | 2024-01-05 | 2024-07-04 | 307 | 2024-07-05 | 2025-01-05 | 481 |
| 12 | 2023-07-05 | 2024-07-04 | 682 | 2024-07-05 | 2025-07-05 | 1292 |

## Quarterly Counts

| quarter | quarter_start | quarter_end | new_projects |
| --- | --- | --- | --- |
| 2023Q1 | 2023-01-01 | 2023-03-31 | 180 |
| 2023Q2 | 2023-04-01 | 2023-06-30 | 197 |
| 2023Q3 | 2023-07-01 | 2023-09-30 | 177 |
| 2023Q4 | 2023-10-01 | 2023-12-31 | 188 |
| 2024Q1 | 2024-01-01 | 2024-03-31 | 209 |
| 2024Q2 | 2024-04-01 | 2024-06-30 | 115 |
| 2024Q3 | 2024-07-01 | 2024-09-30 | 4 |
| 2024Q4 | 2024-10-01 | 2024-12-31 | 470 |
| 2025Q1 | 2025-01-01 | 2025-03-31 | 320 |
| 2025Q2 | 2025-04-01 | 2025-06-30 | 467 |
| 2025Q3 | 2025-07-01 | 2025-09-30 | 473 |
| 2025Q4 | 2025-10-01 | 2025-12-31 | 402 |

## Monthly Counts

| month | month_start | month_end | new_projects |
| --- | --- | --- | --- |
| 2023-01 | 2023-01-01 | 2023-01-31 | 58 |
| 2023-02 | 2023-02-01 | 2023-02-28 | 49 |
| 2023-03 | 2023-03-01 | 2023-03-31 | 73 |
| 2023-04 | 2023-04-01 | 2023-04-30 | 58 |
| 2023-05 | 2023-05-01 | 2023-05-31 | 63 |
| 2023-06 | 2023-06-01 | 2023-06-30 | 76 |
| 2023-07 | 2023-07-01 | 2023-07-31 | 62 |
| 2023-08 | 2023-08-01 | 2023-08-31 | 58 |
| 2023-09 | 2023-09-01 | 2023-09-30 | 57 |
| 2023-10 | 2023-10-01 | 2023-10-31 | 71 |
| 2023-11 | 2023-11-01 | 2023-11-30 | 80 |
| 2023-12 | 2023-12-01 | 2023-12-31 | 37 |
| 2024-01 | 2024-01-01 | 2024-01-31 | 75 |
| 2024-02 | 2024-02-01 | 2024-02-29 | 51 |
| 2024-03 | 2024-03-01 | 2024-03-31 | 83 |
| 2024-04 | 2024-04-01 | 2024-04-30 | 72 |
| 2024-05 | 2024-05-01 | 2024-05-31 | 33 |
| 2024-06 | 2024-06-01 | 2024-06-30 | 10 |
| 2024-07 | 2024-07-01 | 2024-07-31 | 3 |
| 2024-08 | 2024-08-01 | 2024-08-31 | 0 |
| 2024-09 | 2024-09-01 | 2024-09-30 | 1 |
| 2024-10 | 2024-10-01 | 2024-10-31 | 208 |
| 2024-11 | 2024-11-01 | 2024-11-30 | 156 |
| 2024-12 | 2024-12-01 | 2024-12-31 | 106 |
| 2025-01 | 2025-01-01 | 2025-01-31 | 100 |
| 2025-02 | 2025-02-01 | 2025-02-28 | 110 |
| 2025-03 | 2025-03-01 | 2025-03-31 | 110 |
| 2025-04 | 2025-04-01 | 2025-04-30 | 181 |
| 2025-05 | 2025-05-01 | 2025-05-31 | 126 |
| 2025-06 | 2025-06-01 | 2025-06-30 | 160 |
| 2025-07 | 2025-07-01 | 2025-07-31 | 191 |
| 2025-08 | 2025-08-01 | 2025-08-31 | 117 |
| 2025-09 | 2025-09-01 | 2025-09-30 | 165 |
| 2025-10 | 2025-10-01 | 2025-10-31 | 131 |
| 2025-11 | 2025-11-01 | 2025-11-30 | 169 |
| 2025-12 | 2025-12-01 | 2025-12-31 | 102 |

## Outputs

- `data/processed/timing_working_research_project_universe.csv`
- `data/processed/timing_unmatched_schema27_audit.csv`
- `data/processed/timing_monthly_project_starts_2023_2025.csv`
- `data/processed/timing_quarterly_project_starts_2023_2025.csv`
- `data/processed/timing_policy_window_counts.csv`
- `data/processed/timing_feasibility_summary.json`
- `figures/timing_project_starts_monthly_2023_2025.svg`
