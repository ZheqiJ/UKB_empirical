# Project-Entry Measurement Note

## Outcome

The project-entry outcome is the number of UK Biobank projects whose public recorded `Start date` falls in calendar month `t`.

The public `Start date` is treated as the recorded beginning of a UKB research project's project period. Public documentation does not establish that it is identical to the application submission date, approval date, or first RAP-access date.

## Source

The start dates come from the public UK Biobank project pages/listing matched to the local schema27 application universe. The matched working file is:

`data/intermediate/timing_feasibility/timing_working_research_project_universe.csv`

## Safest Institutional Interpretation

The safest interpretation is `recorded project starts` or `projects becoming operational in public UKB records`. Official guidance documents application, registration, Access Committee review, MTA, payment, training/onboarding, project `Underway` status, and RAP enablement as separate steps. That workflow makes the public date downstream of application submission.

## What It Is Not

Do not interpret this outcome as:

- application submissions;
- application approvals;
- RAP migrations;
- first RAP access;
- first data use.

## Coverage And Matching

- Matched projects with usable public start dates: 6,935
- Date coverage: 2012-06-01 through 2026-08-17
- Schema27 records unmatched to a public project page: 132
- Public exact dates are available at day resolution and are aggregated to calendar months for the ITS.

## Anomalies

- Duplicate `app_id` rows in matched start-date file: 0
- Rows with multiple public start dates in `start_dates_all`: 0
- Monthly aggregation includes zero-filled months inside analysis windows.

These diagnostics support use of the public start-date series as a recorded project-entry measure, while preserving uncertainty about the exact UKB internal administrative event that sets the public date.
