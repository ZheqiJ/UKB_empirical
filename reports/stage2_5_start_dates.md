# Stage 2.5 Project Start Dates

Goal: recover `app_id -> start_date` from the UK Biobank Existing projects website.

## Scraping Route

- Listing route: `https://www.ukbiobank.ac.uk/projects/?_paged=N`
- The page is server-rendered and exposes project start date, title, URL, and
  institution in each listing card.
- The listing page reports `6,936` results.
- Direct command-line requests to the UKB main website are blocked by Cloudflare,
  and WordPress REST URLs were not usable in the browser environment. The
  server-rendered paged listing is the stable route used here.

## Matching Rule

- Match website listing rows to Schema 27 by normalized title when the title is
  unique in Schema 27.
- If a normalized title maps to multiple Schema 27 applications, resolve only
  when normalized institution uniquely identifies one candidate.
- For rows still unmatched or ambiguous after title/institution matching, use
  the project detail page `ID` when available. This was applied only to the
  small boundary set, not to every already-matched row.
- No fuzzy matching is used.

## Summary

- Schema 27 unique applications: 7,067
- Website listing rows: 6,936
- Website listing rows with start date: 6,936
- Schema 27 applications matched to website: 6,935
- Schema 27 applications with a single recovered start date: 6,935
- Schema 27 applications unmatched to website: 132
- Start year range among recovered dates: 2012-2026

## Validation

- Detail validation rows: 76
- Detail validation fetch errors: 0
- Matched validation rows with detail `ID`: 49
- Detail `ID` mismatches against matched Schema 27 app_id: 0
- Detail/listing start-date mismatches: 0

## Remaining Unmatched Pattern

- Schema 27 unmatched applications: 132
- Admin/service-like unmatched applications: 130
- Other unmatched applications: 2
- Website projects not in current Schema 27 after detail-page ID check: 1

## Produced Files

- `data/processed/stage2_5_app_start_dates.csv`
- `data/processed/stage2_5_website_listing_matches.csv`
- `data/processed/stage2_5_website_unmatched.csv`
- `data/processed/stage2_5_schema27_unmatched.csv`
- `data/processed/stage2_5_start_year_counts.csv`
- `data/processed/stage2_5_start_date_summary.json`
- `data/processed/stage2_5_website_unmatched_detail_results.csv`
- `data/processed/stage2_5_detail_validation_plan.csv`
- `data/processed/stage2_5_detail_validation_results.csv`
