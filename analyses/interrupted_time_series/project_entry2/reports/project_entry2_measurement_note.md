# Project Entry2 Measurement Note

## Sources

The project universe is `data/intermediate/timing_feasibility/timing_working_research_project_universe.csv`, which contains 6,935 projects with exact public Start dates.

Existing control-expansion evidence comes from `data/intermediate/control_expansion/stage3_control_expansion_project_review.csv` and its evidence dictionary. Expansion layer is retained as audit metadata only; it is not itself a high-sensitivity definition.

Field-tier evidence comes from UKB Schema 1 (`https://biobank.ndph.ox.ac.uk/ukb/scdown.cgi?fmt=txt&id=1`) and cached public field pages under `data/source_snapshots/field_pages/`.

## Field-Tier Interpretation

Current Schema 1 exposes `cost_do`, `cost_on`, and `cost_sc` columns rather than one literal `tier` column. This pipeline reconstructs tier tokens from those columns: positive `cost_do` becomes `d#`, positive `cost_on` becomes `o#`, and positive `cost_sc` becomes `s#`. The parser validation case is field 25749, which reconstructs as `o2 s3` and links to applications 17689 and 22783.

`s3` enters high sensitivity in two ways: direct application-field links and high-precision application-text terms derived from the 199 s3 Schema 1 fields. `o2` is retained for audit; o2 alone is not part of the primary high-sensitivity definition.

## High And Lower Groups

`HIGH_SENSITIVITY` is the union of explicit WES/WGS or sequence-product evidence, direct s3 field links, and s3-derived application text. `LOWER_SENSITIVITY_COMPARISON` is the exhaustive complement. Complement status means no identified high evidence under the observable proxy, not proof that every project is low-risk.

## Interpretation Limits

The public Start date is not observed application submission, approval, first RAP access, or first data-use timing. Field tier and text evidence are sensitivity/granularity proxies, not observed leakage risk. The ITS outputs are descriptive and comparative; they should not be described as causal RAP treatment effects.
