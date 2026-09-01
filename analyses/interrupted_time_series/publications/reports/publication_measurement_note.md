# Publication Measurement Note

## Core Definitions

Publication date is the exact `date_pub` in public Schema19. An application-publication link is one row in Schema24 joining `app_id` to `pub_id`. A unique publication is a distinct `pub_id`.

Fractional publication credit gives each cleaned application-publication link weight `1 / number of cleaned valid application links for that publication`. The fractional weights for one publication sum to one. At the aggregate system-month level, `fractional_publication_count` equals `unique_publication_ids` by construction; fractional credit remains useful for project-level attribution.

Project start date is the public UKB project `Start date`. Project age is the exact month difference between publication date and project start date. Incumbent means project start date before 2024-07-05. Fixed cohort means a prespecified set of projects started before a cutoff such as 2022-07-01.

Calendar-time post means publication month >= 2024-07. Project-cohort post means project start date >= 2024-07-05. These are different indicators.

Censoring date for project-level follow-up is 2025-12-31. A project is eligible for an H-month outcome only if its project start date plus H months is on or before that censoring date.

## Audit

- Schema19 publications: 14,633
- Schema24 app-publication links: 12,598
- Cleaned publication-app events: 12,568
- Cleaned unique publication IDs: 11,959
- Publication IDs linked to multiple valid applications: 541 (4.52%)
- Publication-before-project-start exclusions: 24
- Unmatched app links: 6
- Latest exact Schema19 publication date: 2026-07-16

A publication observed in March 2025 does not imply that the associated project began in March 2025. Publications may be produced years after project initiation.

## Publication Lag

This is project-start-to-publication lag, not RAP-to-publication lag. The median is 41.000 months. Shares are 0-6 months 1.15%, 7-12 months 4.04%, 13-24 months 15.73%, 25-48 months 38.78%, and 49+ months 40.30%.
