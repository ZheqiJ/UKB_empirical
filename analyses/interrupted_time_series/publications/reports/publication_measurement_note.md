# Publication Measurement Note

## Core Definitions

Publication date is the exact `date_pub` in public Schema19. An application-publication link is one row in Schema24 joining `app_id` to `pub_id`. A unique publication is a distinct `pub_id`.

Fractional publication credit gives each cleaned application-publication link weight `1 / number of cleaned valid application links for that publication`. The fractional weights for one publication sum to one. At the aggregate system-month level, `fractional_publication_count` equals `unique_publication_ids` by construction; fractional credit remains useful for project-level attribution and cohort decomposition.

Project start date is the public UKB project `Start date`. Project age is calculated from exact project start date and exact publication date where possible. Calendar-time post means publication month >= 2024-07. Project-cohort post means project start date >= 2024-07-05. These are different indicators; July 2024 is not assigned as the individual treatment date for all projects.

Censoring date for project-level follow-up is 2025-12-31. A project is eligible for an H-month outcome only if `add_months_exact(project_start_date, H) <= 2025-12-31`. A publication belongs to PubH only if its exact publication date is on or before that exact H-month cutoff.

## Audit

- Schema19 publications: 14,633
- Schema24 app-publication links: 12,598
- Cleaned publication-app events: 12,568
- Cleaned unique publication IDs: 11,959
- Publication IDs linked to multiple valid applications: 541 (4.52%)
- Publication-before-project-start exclusions: 24
- Unmatched app links: 6
- Latest exact Schema19 publication date: 2026-07-16

Publication lag in this module is project-start-to-publication lag, not RAP-to-publication lag. The median is 41.000 months.
