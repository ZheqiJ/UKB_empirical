# New Comparative ITS

This is the only current empirical analysis on this branch.

## Results

Start with:

1. [`reports/new_comparative_its_results.md`](reports/new_comparative_its_results.md)
2. [`reports/new_comparative_its_stata_style_results.txt`](reports/new_comparative_its_stata_style_results.txt)
3. The fitted and observed figures in [`figures/`](figures/)

The main outcome is the raw monthly number of project starts. The sample starts
in October 2021 because the already-RAP-bound control proxy first appears on 28
September 2021, leaving September as an incomplete month. The endpoint is April
2026 and the breakpoint is July 2024.

## Main Files

- `data/partition_results_strict.csv` and `data/partition_results_broad.csv`:
  main comparative ITS coefficients and derived slopes.
- `data/pretrend_results_strict.csv` and `data/pretrend_results_broad.csv`:
  independent pre-shock slope and joint Wald tests.
- `data/group_definition_audit.csv`: project-level group audit.
- `scripts/new_comparative_its.py`: reproducible analysis builder.
- `tests/test_new_comparative_its.py`: focused regression checks.

## Interpretation

The treatment and control labels are exposure proxies. They do not identify
observed RAP use or verified migration. The analysis is descriptive and should
not be described as a causal DID.

## Run

From the repository root:

```bash
python3 new_comparative_its/scripts/new_comparative_its.py
python3 -m unittest discover -s new_comparative_its/tests
```
