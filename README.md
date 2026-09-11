# UKB Empirical: New Comparative ITS

This branch has one current empirical result: the within-High RAP-exposure
comparative interrupted time-series analysis in [`new_comparative_its/`](new_comparative_its/).
Earlier specifications are retained under [`archive/`](archive/) for provenance
and are not current results.

## Read First

1. [Main results](new_comparative_its/reports/new_comparative_its_results.md)
2. [Stata-style output](new_comparative_its/reports/new_comparative_its_stata_style_results.txt)
3. [Strict fitted monthly counts](new_comparative_its/figures/figure_strict_fitted_monthly_counts.svg)
4. [Broad fitted monthly counts](new_comparative_its/figures/figure_broad_fitted_monthly_counts.svg)

## Current Design

The analysis compares two proxies within the existing `HIGH_SENSITIVITY`
classification:

- Treatment proxy: higher incremental July-2024 RAP exposure.
- Control proxy: sequence-based projects whose relevant data were already
  RAP-only before the transition.

The control proxy first appears on 28 September 2021. September is therefore a
partial month and is excluded. The raw monthly-count comparative ITS uses 55
complete calendar months from October 2021 through April 2026, with July 2024
as the breakpoint and Newey-West HAC lag 3.

The separate pretrend diagnostic uses October 2021 through June 2024. It
includes common month fixed effects, excludes Treatment-by-month fixed effects,
and aggregates the stacked-model score vectors by calendar month before HAC
inference.

This is a descriptive comparative ITS. Public data do not contain actual
project-level RAP migration dates or usage logs, so estimates are not causal
DID effects.

## Repository Map

- `new_comparative_its/`: current reports, figures, data, script, and tests.
- `archive/`: prior empirical specifications grouped by major analysis stage.
- `data/`: shared public inputs and intermediate classification sources.
- `scripts/` and `tests/`: repository-level public-metadata pipeline support.
- `ukb_dmca/`: separate DMCA evidence and matching module.

Participant-level UK Biobank data must never be stored in this repository.

## Run

```bash
python3 new_comparative_its/scripts/new_comparative_its.py
make test
```
