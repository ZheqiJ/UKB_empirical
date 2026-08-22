# Stage 2 Data Universe

This report is generated from public UK Biobank Showcase metadata only. It does
not contain participant-level UK Biobank data.

## Source Summary

| Source | Rows | Unique IDs | Duplicate IDs |
| --- | ---: | ---: | ---: |
| Schema 27 approved applications | 7,078 raw records | 7,067 application IDs | 3 duplicated IDs; 11 repeated rows |
| Schema 19 publications | 14,633 | 14,633 | 0 |
| Schema 24 app-publication links | 12,598 | 12,598 unique app-pub pairs | 0 duplicate link rows |
| Schema 4 returned datasets | 591 | 586 archive IDs | 2 duplicated archive IDs |

## Linkage Summary

- Unique Schema 27 applications with at least one linked publication: 2,497
- Unique Schema 27 applications without linked publication: 4,570
- Schema 24 links pointing to missing Schema 27 app IDs: 0
- Schema 24 links pointing to missing Schema 19 publication IDs: 0
- Unique Schema 27 applications with at least one returned dataset: 238
- Schema 4 returned dataset rows pointing to missing Schema 27 app IDs: 46

## Produced Files

- `data/intermediate/stage2_universe/stage2_master_projects.csv`
- `data/intermediate/stage2_universe/stage2_source_summary.csv`
- `data/intermediate/stage2_universe/stage2_variable_coverage.csv`
- `data/intermediate/stage2_universe/stage2_linkage_summary.csv`
- `data/intermediate/stage2_universe/stage2_schema27_duplicate_app_ids.csv`
- `data/intermediate/stage2_universe/stage2_schema4_unmatched_returned_datasets.csv`
- `data/intermediate/stage2_universe/stage2_publication_year_counts.csv`
- `data/intermediate/stage2_universe/stage2_application_publication_count_distribution.csv`
- `data/raw/stage2_source_manifest.json`
