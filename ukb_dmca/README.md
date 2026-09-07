# UKB-DMCA Module

This folder contains a reproducible, audit-first module for matching
GitHub DMCA notices that mention UK Biobank or UKB to UK Biobank approved
applications.

Important interpretation note: a DMCA notice means UK Biobank made a takedown
claim. It does not mean GitHub, a court, or this project has found that any
application, PI, institution, or repository owner acted unlawfully. The final
variable is `application_linked_to_dmca_targeted_repository_lineage`; it is a
lineage-level evidence link, not a finding that an application violated policy.

## What The Pipeline Does

- Enumerates `github/dmca` without cloning by using GitHub REST tree
  enumeration and paginated code search.
- Searches all years for `UK Biobank`, `uk biobank`, `UKB`, `ukbiobank`, and
  `uk-biobank`, including same-day `-2`, `-3`, and later suffix notices.
- Extracts notice date, path, repository URL, owner, repo name, targeted file
  path/name, target scope, counter-notice/retraction markers, DOI/PMID/app ID
  identifiers, and alleged data type cues.
- Enriches each target with public GitHub repository metadata, fork/source
  metadata, public README/CITATION/package metadata, and optional Internet
  Archive CDX/README snapshot metadata.
- Reads public repository README files only, extracts UK Biobank application
  IDs, DOI/PMID identifiers, citation lines, paper titles, and public metadata
  snippets, then uses Crossref/PubMed summaries when identifiers are available.
- Follows public publication/package links from README/CITATION metadata to
  Zenodo, PyPI, and CRAN/R package metadata when available, extracting only
  citation-level information such as DOI, PMID, paper title, authors, and URLs.
- Runs the application evidence layer through
  `scripts/ukb_dmca_enriched_pipeline.py`, which reuses the existing notice
  discovery/filtering code and changes only enrichment, scoring, and evidence
  output.
- Deduplicates fork/source lineages conservatively.
- Scores all retained UKB application candidates and writes both candidate sets
  and final labels.
- Writes notice and lineage evidence files plus fetch logs with timestamps.

The pipeline stores public notice text and metadata only. It does not download,
store, or republish alleged participant-level UK Biobank data from targeted
repositories.

## Run Locally

```bash
export GITHUB_TOKEN=YOUR_TOKEN
python3 scripts/ukb_dmca_public_metadata_runner.py \
  --applications "data/applications.tsv" \
  --output-dir ukb_dmca \
  --cache-dir .cache/ukb_dmca
```

Use the local application file path that exists on your machine. The GitHub
workflow accepts `data/applications.tsv`, `data/application.tsv`, or uploaded
`data/application*.txt` files and copies the first valid application table to
`data/applications.tsv` before matching.

Optional UKB Schema 19 and Schema 24 publication crosswalk files can be placed
under `data/schema19*` and `data/schema24*`, or supplied as workflow inputs.
When both are available, repository-linked DOI/PMID evidence is mapped through
the UKB publication-to-application tables.

To guarantee a no-clone body scan of every Markdown notice, add:

```bash
--scan-all-markdown
```

## Run Remotely In GitHub Actions

Open the `UKB Remote Pipeline` workflow from the repository Actions tab and
choose `Run workflow`. The workflow runs on GitHub-hosted Ubuntu runners, so
large scans and output generation do not need to fit in local memory.

The `run_scope` input controls the remote job:

- `tests`: run the parser and enrichment unit tests only.
- `stage2`: build the public UKB project universe from Showcase schema files.
- `stage2_5`: build Stage 2, then match website project start dates.
- `dmca`: run the GitHub DMCA discovery and application matching pipeline.
- `all`: run Stage 2, Stage 2.5, and the DMCA pipeline in one remote job.

For the DMCA pipeline, the workflow can use either:

- `data/applications.tsv` committed to the private repository, or
- `data/raw/ukb_schema27_applications.tsv` from the public Stage 2 source set, or
- a temporary `applications_url` supplied in the workflow input.

`data/applications.tsv` and `data/application*.txt` are intentionally ignored
by git so local application exports are not committed accidentally. If you use
`applications_url`, prefer a short-lived private URL.

For Stage 2, the workflow can use committed `data/raw/ukb_schema*.tsv` files or
set `refresh_stage2_sources=true` to re-download the public UKB Showcase schema
files on the runner. Stage 2.5 additionally needs
`data/raw/ukb_projects_website_listing.csv`; commit that file or provide
`website_listing_url` when manually dispatching the workflow.

Every run uploads generated CSV, evidence, processed data, and reports as a
workflow artifact. If `commit_outputs=true`, the same generated outputs are
committed back to the triggering branch.

## Outputs

- `ukb_dmca/ukb_dmca_notices.csv`: all UKB-related DMCA notices.
- `ukb_dmca/ukb_dmca_repositories.csv`: all target repositories and historical metadata.
- `ukb_dmca/ukb_dmca_lineages.csv`: source/fork/mirror lineage rollups.
  These include enrichment fields such as `repository_readme_urls`,
  `citation_metadata_urls`, `metadata_publication_links`,
  `package_metadata_sources`, `package_metadata_urls`,
  `wayback_readme_first_capture`, and `wayback_readme_urls`.
- `ukb_dmca/ukb_dmca_application_candidates.csv`: retained candidate applications and
  scores for every lineage.
- `ukb_dmca/ukb_dmca_application_match_evidence.csv`: one row per lineage, candidate
  application, and evidence component.
- `ukb_dmca/ukb_dmca_application_matches.csv`: final `confirmed` and `probable` matches.
- `ukb_dmca/ukb_dmca_unresolved.csv`: `ambiguous`, `unresolved`, and
  `not_application_attributable` cases.
- `ukb_dmca/ukb_dmca_manual_review.csv`: compact reviewer table.
- `ukb_dmca/curated_dmca_application_links.csv`: canonical manually curated
  empirical crosswalk, one row per final leakage-risk application.
- `ukb_dmca/curated_dmca_repository_family_links.csv`: repository/family-level
  evidence layer used to preserve lineage provenance separately from the
  application-level outcome.
- `ukb_dmca/remaining_23_repo_review.csv`: completed review of the 23
  repository/family units that remained after the historical manual matching
  rounds.
- `ukb_dmca/exhaustive_dmca_application_attribution.csv`: broad attribution
  table across the full current DMCA repository universe. It preserves
  confirmed, probable, ambiguous, B-level candidate, weak-candidate, and
  manually excluded false-positive rows.
- `ukb_dmca/exhaustive_dmca_family_attribution_summary.csv`: one row per
  repository family summarizing supported, ambiguous, weak, and unresolved
  attribution coverage.
- `ukb_dmca/exhaustive_dmca_application_attribution_report.md`: concise report
  for the exhaustive attribution layer.
- `ukb_dmca/leakage_application_analysis/`: application-level leakage analysis
  using UKB project/application start dates as the time variable.
- `ukb_dmca/evidence/`: public notice text, lineage summaries, Wayback summaries, and
  fetch logs.
- `ukb_dmca/MATCHING_METHODOLOGY.md`: evidence hierarchy, label rules, limitations, and
  matching method descriptions.

## Match Labels

Allowed final labels are `confirmed`, `probable`, `ambiguous`, `unresolved`,
and `not_application_attributable`.

`confirmed` requires A-level direct evidence, such as an application ID in the
notice/repository evidence, or a complete repo-to-paper-to-application chain
from independent sources.

Direct application IDs are parsed from forms such as `UK Biobank application
123`, `project number 123`, `app #123`, and compact strings such as
`app103356`. The enriched runner scans public repository text, README excerpts,
notice-derived evidence, paper metadata, and evidence URLs for these identifiers.

For non-direct evidence, the matcher also compares repository-linked DOI/PMID
values and paper-title tokens against the UKB application `notes` field. These
signals are retained in `ukb_dmca/ukb_dmca_application_candidates.csv` as score
components such as `application_note_doi`, `application_note_pubmed_id`, and
`application_note_paper_title`; final labels remain conservative when the chain
does not uniquely identify an application.

`probable` requires paper/README-level evidence plus at least three consistent
non-direct evidence components, or a paper identifier plus independent
author/topic evidence and no close competing candidate.

`ambiguous` is used when two or more applications are plausible.

`unresolved` is used when the evidence is generic or weak.

`not_application_attributable` is reserved for third-party propagation where
the original UKB project cannot be determined.

## Current Status

The code and workflow are ready, parser tests pass, and the GitHub Actions
workflow has generated the current CSV/evidence outputs using
`data/applications.tsv`. There are now two distinct result layers in this
module.

### Automated Audit-First Matcher

The automated matcher is the reproducible discovery and evidence-audit layer.
It intentionally labels matches conservatively and keeps weak public evidence
out of the final automated confirmed/probable set.

Current automated output:

- UKB DMCA notices: 110
- Unique repository URLs: 193
- Unique repository owners: 170
- Deduplicated repository lineages: 193
- Confirmed: 2
- Probable: 0
- Ambiguous: 17
- Unresolved: 174
- Unique-application match ratio: 0.0104
- Unique applications linked by the automated matcher: 2
- Application input used: `data/applications.tsv`

See `evidence/logs/result_summary.json` for automated role counts and fetch
metadata.

### Manually Curated Empirical Crosswalk

The manually curated empirical crosswalk is separate from the automated matcher.
Before the present integration task, the researcher had already manually
confirmed 48 unique UKB applications linked to DMCA-targeted repository/project
lineages. Those 48 are the fixed broad baseline for empirical leakage analysis
and are preserved with
`manual_confirmation_status=confirmed_by_researcher` in
`curated_dmca_application_links.csv`.

Automated matching is used as supporting evidence and discovery. It is not used
to overturn, downgrade, or replace the 48 researcher-confirmed baseline
applications when the current automated matcher is more conservative.

The remaining historical 23 repository/family units were reviewed as an
expansion layer:

- Previously confirmed baseline applications: 48
- Remaining repository/family units reviewed: 23
- Remaining units linked to any UKB application: 6
- Remaining units linked to existing baseline applications: 2
- New unique applications added from the remaining review: 4
- Remaining units unresolved, ambiguous, or excluded: 17
- Final unique leakage-risk applications: 52

The final application-level leakage outcome is stored in
`leakage_application_analysis/data/application_level_leakage.csv` and equals
one when an application belongs to the final curated leakage-risk set. The time
variable remains UKB project/application start date, not DMCA notice timing.

### Exhaustive Attribution Expansion

The exhaustive attribution layer extends coverage across all 130 current
repository families and all 193 current lineages without rerunning notice
discovery or overwriting the 52-link empirical baseline. It starts from the
current curated matches, then retains every existing application candidate from
the already harvested README, repository metadata, archived-page, publication,
crosswalk, fork/source, and public evidence files.

Current exhaustive attribution summary:

- DMCA repository rows: 1,826
- Unique DMCA repository URLs: 194
- Repository lineages: 193
- Repository families reviewed: 130
- Families with supported or ambiguous attribution: 32
- Families with only weak retained candidates: 98
- Confirmed attribution rows: 74
- Probable attribution rows: 4
- Ambiguous attribution rows: 9
- B-level candidate rows: 281
- Weak candidate rows: 3,528
- Manual false-positive rows retained but excluded: 3
- Unique applications identified at supported/ambiguous tier: 274
- New unique applications beyond the current 52 at supported/ambiguous tier: 222
- Unique applications identified including weak candidates: 1,158
- New unique applications beyond the current 52 including weak candidates: 1,106

Rows marked `weak_candidate` are kept for transparency and coverage, but are not
promoted into the application-level leakage outcome. Application `29256` remains
an audit-retained manual false positive and is not counted as supported
attribution.

## Current Result Summary

- UKB DMCA notices: 110
- Unique repository URLs: 193
- Unique repository owners: 170
- Deduplicated repository lineages: 193
- Confirmed: 2
- Probable: 0
- Ambiguous: 18
- Unresolved: 173
- Unique-application match ratio: 0.0104
- Unique applications linked: 2
- Application input used: `data/applications.tsv`

See `evidence/logs/result_summary.json` for remaining cases and role counts.
