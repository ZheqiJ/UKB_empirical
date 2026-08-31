# Interrupted Time-Series Analysis

This is the active descriptive empirical strategy for the UK Biobank RAP
transition work. The folder is organized by outcome/module rather than keeping
all ITS data, figures, and reports in one flat directory.

## Read First

For the completed project-entry stylized fact, start here:

1. `project_entry/reports/project_entry_reading_guide.md`
2. `project_entry/reports/project_entry_its_results.md`
3. `project_entry/figures/project_entry_figure1_three_panel.svg`
4. `project_entry/data/project_entry_its_results_table.csv`

## Folder Map

- `shared/`: common ITS design, institutional timeline material, and
  cross-module data-audit outputs.
- `project_entry/`: completed project-entry stylized fact using recorded public
  UKB project Start dates.
- `publications/`: incumbent publication trajectories and publication-lag
  diagnostics for later ITS work.
- `comparative_exposure/`: C03/C05/C06 descriptive comparison-group and
  exposure-proxy diagnostics.
- `returned_data/`: returned-dataset feasibility material for a possible future
  outcome.

None of these modules are automatically causal designs. They should be read as
descriptive trajectories anchored to externally documented institutional dates.

## Run

```bash
python3 analyses/interrupted_time_series/shared/build_its_feasibility.py
python3 analyses/interrupted_time_series/project_entry/scripts/project_entry_its_analysis.py
```

`make its` runs the shared ITS feasibility builder. `make test` runs the
repository tests and the project-entry module tests.
