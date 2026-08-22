# UKB_empirical

This repository contains the empirical pipeline for studying the July 2024 UK
Biobank Research Analysis Platform (RAP) transition. The project currently
focuses on whether the policy changed downstream scientific output for existing
UK Biobank research projects, with publication outcomes as the primary working
outcome and DMCA-linked repository notices kept as a separate auxiliary outcome
family.

The repository is intentionally audit-first: each stage writes reproducible
processed data, reports, and figures through GitHub Actions so large pipeline
runs do not depend on local memory.

## Current Empirical Status

The current completed design is **Design 1: quarterly incumbent-project DID for
publication outcomes**.

- Working project universe: 6,935 matched UK Biobank projects with unique start
  dates.
- Quarterly panel: application-quarter risk-set panel from 2022Q3 to 2026Q2.
- Policy date: 5 July 2024.
- Main outcome family: publication count and any publication.
- Main current specification: application fixed effects plus calendar-quarter
  fixed effects, clustered by application.
- Current interpretation: the pipeline runs end to end, but the first quarterly
  publication results do not show a robust or precisely estimated post-RAP
  differential change. Remaining concerns are the small/provisional control
  group, incomplete actual-exposure information, and publication timing.

Key reports:

- `reports/stage6_design1_supervisor_memo.md`: concise supervisor-facing memo.
- `reports/stage6_panel_results.md`: full Design 1 quarterly result report.
- `reports/stage6_empirical_design_review.md`: implementation and empirical
  diagnostic review.
- `data/processed/stage6_panel_regression_results.csv`: Design 1 regression
  table.

Generated reports and data are stored in git on `main`; local copies can be
deleted and restored from GitHub when needed.

## Repository Layout

- `scripts/`: pipeline scripts for public UKB project construction, timing,
  provisional RAP exposure classification, publication panels, and DMCA matching.
- `tests/`: unit tests for the pipeline components.
- `data/raw/`: public input snapshots used by the remote workflow.
- `data/processed/`: generated stage outputs.
- `figures/`: generated figures.
- `reports/`: generated reports and empirical memos.
- `ukb_dmca/`: DMCA-specific notices, lineage evidence, matching outputs, and
  the DMCA methodology notes.

## Remote Execution

Open the `UKB Remote Pipeline` workflow in GitHub Actions and choose a
`run_scope`:

- `timing`: timing-feasibility counts around the policy date.
- `stage3_classification`: provisional RAP exposure classification.
- `stage3_control_expansion`: control-candidate expansion frontier.
- `fast_design_regression`: earlier fast publication/DMCA checkpoint.
- `stage6_quarterly_panel_regression`: Design 1 quarterly publication DID.
- `dmca`: UKB-DMCA repository lineage and application matching.
- `all`: public project universe, start-date matching, and DMCA pipeline.

The remote workflow commits generated outputs back to the triggering branch when
`commit_outputs=true`.

## DMCA Module

The UKB-DMCA matching pipeline is now contained under `ukb_dmca/`. See
`ukb_dmca/README.md` and `ukb_dmca/MATCHING_METHODOLOGY.md` for the notice
matching, lineage construction, and application-linkage methodology.

Important interpretation note: a DMCA notice means UK Biobank made a takedown
claim. It does not mean GitHub, a court, or this project has found that any
application, PI, institution, or repository owner acted unlawfully.

## Suggested Next Empirical Step

Proceed sequentially:

1. Run **Design 2: monthly timing robustness** for the publication outcome.
2. Add balance/common-support diagnostics for start timing, project age,
   institution, and pre-policy publication productivity.
3. Use matched or weighted DID only if those diagnostics reveal substantial
   comparability problems.
4. Keep DMCA as a separate auxiliary design rather than folding it into the
   publication panel.
