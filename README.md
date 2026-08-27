# UKB_empirical

This repository contains public-metadata empirical work on the July 2024 UK
Biobank Research Analysis Platform (RAP) transition. The active main logic is now
descriptive interrupted time-series and stylized-facts work, not a causal DID
claim.

The repository is audit-first: source snapshots, intermediate construction
tables, analysis outputs, reports, and figures are kept in git so remote runs can
be reproduced without relying on local memory.

## Current Empirical Status

The active package is **interrupted time-series and stylized facts**:

- `analyses/interrupted_time_series/`: active descriptive feasibility package.
- `analyses/interrupted_time_series/scripts/build_its_feasibility.py`:
  reproducible builder for the ITS data, reports, and figures.
- `analyses/interrupted_time_series/reports/preliminary_feasibility_report.md`:
  current supervisor-facing feasibility report.
- `analyses/interrupted_time_series/design/`: proposed specifications and
  candidate stylized facts.

The old quarterly DID work is preserved as an archive:

- `analyses/did_archive/`: historical DID-style exploratory outputs and scripts.
- `analyses/did_archive/manifest.csv`: old-to-new path mapping.
- `scripts/stage4_5_fast_design_regression.py`,
  `scripts/stage6_panel_regression.py`, and `scripts/design1_stata_table.py`:
  compatibility wrappers that call the archived implementations.

The archived DID estimates should be treated as diagnostics only. The public
data do not observe actual project-level RAP migration, active/expired project
status, refresh requests, or actual RAP use, so the main causal interpretation
has been set aside.

## Repository Layout

- `scripts/`: shared pipeline scripts plus compatibility wrappers for archived
  DID scripts.
- `tests/`: unit tests for the pipeline components.
- `data/raw/`: public input snapshots used by the remote workflow.
- `data/intermediate/`: shared construction, audit, timing, and classification
  outputs retained for reproducibility.
- `analyses/interrupted_time_series/`: current main descriptive ITS package.
- `analyses/did_archive/`: archived DID-era files kept for provenance.
- `reports/supervisor/`: frozen supervisor-facing memos retained unchanged.
- `ukb_dmca/`: frozen DMCA-specific notices, lineage evidence, matching outputs,
  and methodology notes.

Participant-level UK Biobank data must never be stored in this repository.

## Remote Execution

Open the `UKB Remote Pipeline` workflow in GitHub Actions and choose a
`run_scope`:

- `timing`: timing-feasibility counts around the policy date.
- `stage3_classification`: provisional RAP exposure classification.
- `stage3_control_expansion`: control-candidate expansion frontier.
- `interrupted_time_series`: active descriptive ITS feasibility package.
- `fast_design_regression`: archived fast publication/DMCA checkpoint.
- `design1_quarterly_publication`: archived Design 1 quarterly publication DID.
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

1. Start with the project-entry interruption/restart plot and monthly segmented
   count ITS.
2. Add aggregate incumbent publication trajectories with delayed post-transition
   windows.
3. Use C05/C03/C06 only as descriptive exposure-proxy sensitivity checks.
4. Keep DMCA as a separate auxiliary module rather than folding it into the
   publication ITS package.
