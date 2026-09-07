# UKB DMCA Application Leakage Analysis

This directory is the canonical home for the application-level leakage analysis used by the UKB-DMCA empirical module.

DMCA notices are used only as ex post public evidence for identifying applications linked to targeted repository/project lineages. The empirical time variable is the UK Biobank application/project start date. Notice dates, targeted commit dates, and repository commit dates are not used as outcome timing.

## Inputs

- `ukb_dmca/ukb_dmca_*.csv`: reproducible automated public DMCA audit outputs.
- `analyses/did_archive/data/intermediate/fast_pipeline/stage4_fast_dmca_crosswalk.csv`: archived researcher-confirmed strict/main/broad application crosswalk.
- `data/intermediate/stage2_universe/stage2_master_projects.csv`: UKB application metadata.
- `data/intermediate/start_date_matching/stage2_5_app_start_dates.csv`: application/project start dates.

## Curated Samples

- `strict_21`: original strict manually confirmed set.
- `main_27`: original main manually confirmed set.
- `archived_broad_48`: fixed researcher-confirmed empirical baseline.
- `final_expanded`: `archived_broad_48` plus new unique credible applications from the completed remaining-23 review.

The current automated matcher remains an audit/discovery layer. It does not replace, downgrade, or delete the researcher-confirmed broad-48 baseline.

## Run

```bash
python3 ukb_dmca/leakage_application_analysis/scripts/leakage_its_analysis.py
python3 ukb_dmca/leakage_application_analysis/scripts/leakage_its_analysis.py --validate-only
```

## Key Outputs

- `ukb_dmca/curated_dmca_application_links.csv`: canonical application-level crosswalk, one row per final leakage-risk application.
- `ukb_dmca/curated_dmca_repository_family_links.csv`: repository/family evidence layer.
- `ukb_dmca/remaining_23_repo_review.csv`: completed 23-family public-evidence review.
- `data/application_level_leakage.csv`: full UKB application-level outcome data.
- `data/monthly_application_start_cohorts.csv`: monthly application-start cohorts.
- `data/quarterly_application_start_cohorts.csv`: quarterly application-start cohorts.
- `tables/pre_post_comparison.csv`: raw pre/post descriptive comparison.
- `tables/application_level_regressions.csv`: application-level LPM estimates.
- `tables/monthly_its_results.csv`: monthly application-start-cohort ITS.
- `tables/quarterly_its_results.csv`: quarterly ITS and Poisson count-rate robustness.
- `tables/linkage_sensitivity.csv`: strict/main/broad/final sample sensitivity.
- `reports/leakage_its_results.md`: final leakage analysis report.
- `reports/remaining_repo_linkage_report.md`: completed 23-family linkage report.
