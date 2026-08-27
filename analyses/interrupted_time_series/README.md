# Interrupted Time-Series And Stylized-Facts Analysis

The objective is descriptive rather than causal: to document temporal and cross-project patterns surrounding the July 2024 UK Biobank RAP transition and use robust stylized facts to motivate and discipline the analytical model.

## Contents

- `design/stylized_facts_inventory.md`: broad inventory of candidate facts, data coverage, limitations, and priority.
- `design/its_design_proposal.md`: technical proposal for aggregate, comparative, and event-time descriptive ITS designs.
- `reports/preliminary_feasibility_report.md`: supervisor-facing feasibility report.
- `data/`: generated feasibility tables from shared public UKB metadata and archived DID panel outputs.
- `figures/`: preliminary raw figures used to assess candidate stylized facts.
- `scripts/build_its_feasibility.py`: reproducible builder for this package.

## Run

```bash
python3 analyses/interrupted_time_series/scripts/build_its_feasibility.py
```

The package does not use participant-level UK Biobank data and does not use DMCA outcomes.
