# Interrupted Time-Series And Stylized-Facts Analysis

The objective is descriptive rather than causal: to document temporal and cross-project patterns surrounding the July 2024 UK Biobank RAP transition and use robust stylized facts to motivate and discipline the analytical model.

## Contents

- `design/stylized_facts_inventory.md`: broad inventory of candidate facts, data coverage, limitations, and priority.
- `design/its_design_proposal.md`: technical proposal for aggregate, comparative, and event-time descriptive ITS designs.
- `design/institutional_timeline_project_entry.md`: official-source chronology for project-entry timing and breakpoint justification.
- `design/project_entry_jom_style_design.md`: structured institutional chronology design for project-entry ITS before estimation.
- `reports/preliminary_feasibility_report.md`: supervisor-facing feasibility report.
- `reports/its_data_construction_audit.md`: pre-regression audit for incumbent samples, modalities, publication multiplicity, and right-edge completeness.
- `reports/project_entry_measurement_note.md`: measurement note for public project Start dates.
- `reports/project_entry_its_results.md`: paper-ready project-entry ITS results, diagnostics, and interpretation.
- `data/`: generated feasibility tables from shared public UKB metadata and archived DID panel outputs.
- `figures/`: preliminary raw figures used to assess candidate stylized facts.
- `scripts/build_its_feasibility.py`: reproducible builder for this package.
- `scripts/project_entry_its_analysis.py`: reproducible project-entry ITS analysis and diagnostics.

## Run

```bash
python3 analyses/interrupted_time_series/scripts/build_its_feasibility.py
```

The package does not use participant-level UK Biobank data and does not use DMCA outcomes.
