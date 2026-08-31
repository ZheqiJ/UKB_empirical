# Publication Measurement Note

## Source Tables

- Schema19 publications: 14,633
- Schema24 app-publication links: 12,598
- All cleaned publication-app events after matching and pre-start exclusions: 12,568
- Cleaned incumbent publication-app events used: 12,110
- Cleaned unique publication IDs used: 11,535
- Cleaned apps with any publication: 2,229

## Linkage Audit

- Publication IDs linked to multiple applications in Schema24: 549
- Publication-before-project-start exclusions: 24
- Unmatched app links: 6
- Unmatched publication links: 0
- Latest exact Schema19 publication date: 2026-07-16
- Latest cleaned incumbent publication date: 2026-07-16

## Measures Must Not Be Interchanged

`publication_app_links` counts app-publication links and can double count a publication linked to multiple applications.

`unique_publication_ids` counts distinct publication IDs in a period.

`fractional_publication_count` is operationally equivalent to distinct publication IDs in this public linked dataset after period-level de-duplication; it is retained as the primary intensity numerator to avoid full multi-application double counting.

`apps_with_any_publication` counts applications with at least one linked publication in the period and supports the extensive-margin rate.

## Publication Lag

The lag distribution is project-start-to-publication lag, not RAP-to-publication lag. Median lag is 41.000 months. Shares by lag bin are: 0-6 months 1.15%, 7-12 months 4.04%, 13-24 months 15.73%, 25-48 months 38.78%, and 49+ months 40.30%.

Because publication lags are long, publications appearing shortly after July 2024 generally reflect substantial work initiated before the transition.
