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

For the publication-output stylized fact, start here:

1. `publications/reports/publication_reading_guide.md`
2. `publications/reports/publication_measurement_note.md`
3. `publications/reports/publication_its_results.md`
4. `publications/figures/publication_total_monthly.svg`
5. `publications/figures/publication_observed_vs_pipeline_expected.svg`

## Folder Map

- `shared/`: common ITS design, institutional timeline material, and
  cross-module data-audit outputs.
- `project_entry/`: completed project-entry stylized fact using recorded public
  UKB project Start dates.
- `publications/`: total publication-output, project-age/productivity, and
  pipeline-adjusted publication diagnostics.
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
python3 analyses/interrupted_time_series/publications/scripts/publication_its_analysis.py
```

`make its` runs the shared ITS feasibility builder. `make test` runs the
repository tests plus the project-entry and publication module tests.
