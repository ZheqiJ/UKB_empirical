# Project Entry2 Measurement Note

## Sources

The project universe is `data/intermediate/timing_feasibility/timing_working_research_project_universe.csv`, which contains 6,935 projects with exact public Start dates.

Existing C03/C05 evidence comes from `data/intermediate/control_expansion/stage3_control_expansion_project_review.csv` and its evidence dictionary. C03 is layers C0-C3. C05 is layers C0-C5.

Field-tier evidence comes from UKB Schema 1 (`https://biobank.ndph.ox.ac.uk/ukb/scdown.cgi?fmt=txt&id=1`) and cached public field pages under `data/source_snapshots/field_pages/`.

## Field-Tier Interpretation

Current Schema 1 exposes `cost_do`, `cost_on`, and `cost_sc` columns rather than one literal `tier` column. This pipeline reconstructs tier tokens from those columns: positive `cost_do` becomes `d#`, positive `cost_on` becomes `o#`, and positive `cost_sc` becomes `s#`. The parser validation case is field 25749, which reconstructs as `o2 s3` and links to applications 17689 and 22783.

`s3` is treated as the primary field-tier high-sensitivity proxy. `o2` is retained for broader robustness and audit; o2 alone is not part of the primary high-sensitivity definition.

## Historical Measurement Limitation

The Application x Field crosswalk is current public Showcase information. It may include later amendments and may not equal the field basket approved at the project Start date. For this reason the output includes `field_debut_after_project_start` and timing-conservative high definitions that exclude `s3` links where the field debut date is after the project's public Start date.

## Interpretation Limits

The public Start date is not observed application submission, approval, first RAP access, or first data-use timing. Field tier is a sensitivity/granularity proxy, not observed leakage risk. The ITS outputs are descriptive and comparative; they should not be described as causal RAP treatment effects.
