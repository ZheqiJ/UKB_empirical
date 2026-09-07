# UKB DMCA Application Matching Methodology

This project treats the 110 manually verified UK Biobank-related DMCA notices as the fixed notice universe. The pipeline does not re-expand that universe during enrichment runs.

## Interpretation

A match means: a UK Biobank approved application is linked by public evidence to a DMCA-targeted repository lineage.

It does not mean that the application, PI, institution, or original research team violated UKB policy or uploaded participant-level data. DMCA notices are takedown allegations/requests, not legal findings.

## Three Result Layers

The module keeps three related but distinct layers separate.

1. Automated DMCA lineage matcher. This is the reproducible audit-first
   pipeline that discovers notices/repositories, enriches public metadata, and
   labels lineages as `confirmed`, `probable`, `ambiguous`, `unresolved`, or
   `not_application_attributable`. Its conservative current output is retained
   in `ukb_dmca_application_candidates.csv`,
   `ukb_dmca_application_match_evidence.csv`, `ukb_dmca_application_matches.csv`,
   and `ukb_dmca_unresolved.csv`.

2. Researcher-confirmed curated empirical application crosswalk. This layer
   preserves the completed manual research work. The original 48 broad
   applications are researcher-confirmed manual matches and are not dependent
   on the current automated matcher reproducing them. They are retained in
   `curated_dmca_application_links.csv` with
   `manual_confirmation_status=confirmed_by_researcher`, including application
   rows that lack a current automated lineage ID.

3. Exhaustive attribution expansion. This broader coverage layer starts from
   the current curated state and the existing automated candidate/evidence
   files, then retains confirmed, probable, ambiguous, B-level candidate, weak
   candidate, and manually excluded false-positive rows for all current DMCA
   repository families. It is written to
   `exhaustive_dmca_application_attribution.csv` and summarized in
   `exhaustive_dmca_family_attribution_summary.csv`. This layer is designed to
   maximize application-attribution coverage while preserving uncertainty; it
   does not restart notice discovery and does not overwrite the 52-link
   empirical leakage baseline.

4. Application-level leakage-risk empirical outcome. This layer defines
   `Leak_i = 1` when UKB application `i` belongs to the final curated
   leakage-risk application set. The final set is the fixed broad-48 baseline
   plus new unique credible applications identified during the completed
   remaining-23 repository/family review. The outcome is analyzed by UKB
   application/project start date in `leakage_application_analysis/`; DMCA
   notice dates and repository commit dates are not empirical event dates.

## Evidence Sources

The pipeline uses public metadata only:

- GitHub DMCA notice text and target URLs.
- GitHub repository metadata, fork/source/parent metadata, public owner profile name/company, README, and citation metadata files. Citation metadata is searched both at repository root and in public tree locations such as nested `CITATION.cff`, `codemeta.json`, `.zenodo.json`, `DESCRIPTION`, `pyproject.toml`, and `package.json`.
- Exact targeted commit metadata when a DMCA URL contains a 40-character commit SHA.
- GitHub file commit history for the targeted path when available.
- Internet Archive CDX metadata as a fallback for inaccessible repositories, plus README/raw README snapshots when available.
- Public package/archive metadata reached from repository evidence, including Zenodo records, PyPI project metadata, and CRAN/R `DESCRIPTION` package metadata. The enrichment layer can also try exact PyPI/CRAN package lookups from non-generic repository/package basenames.
- Public record search metadata from exact repository URL queries, currently Zenodo and Europe PMC exact `github.com/{owner}/{repo}` probes.
- Public DOI/PubMed/Crossref metadata.
- Optional UK Biobank Schema 19 publication metadata and Schema 24 publication-to-application mappings.
- UKB approved application `title`, `pi`, `institution`, and `notes`.
- Optional `data/public_metadata_seeds.tsv` rows containing hand-curated public
  metadata chains for lineages where automated crawling cannot recover enough
  metadata after takedown. Seed rows are limited to DOI, PMID, publication title,
  authors, institution, UKB application number, repository/package/project name,
  source-relation notes, and evidence URLs.

The pipeline must not download, store, or reproduce files alleged to contain participant-level UKB data.

## Deterministic Matching

Deterministic evidence can produce `confirmed` only when it uniquely identifies an application:

- `A1_DIRECT_APP_ID`: a unique UKB application/project/app number appears in notice or public repository evidence.
- `A2_DOI_UKB_CROSSWALK`: a repository-linked DOI maps through Schema 19 and Schema 24 to application(s).
- `A3_PMID_UKB_CROSSWALK`: a repository-linked PMID maps through Schema 19 and Schema 24 to application(s).
- `A4_EXACT_REPO_PUBLICATION_APPLICATION_CHAIN`: exact public repository-publication-application chains, including manually curated public metadata seed rows when the seed records an exact repository/publication link and a unique UKB publication/application link.

Repository-linked DOI/PMID values include identifiers written directly in public
repository evidence and conservative identifiers derived from public publication
URLs. For example, a PubMed URL contributes its PMID, and deterministic Nature
article URLs such as `/articles/s41588-...` contribute the corresponding
`10.1038/...` DOI. Ambiguous legacy URL slugs are left unresolved rather than
guessed.

If a live repository points to Zenodo, PyPI, or CRAN, or if a non-generic
repository basename exactly matches a public PyPI/CRAN package, the pipeline fetches only
public package/archive metadata such as title, DOI, PMID, authors, related
identifiers, project URLs, and descriptions. It does not fetch targeted data
files. Exact repository URL probes against Zenodo and Europe PMC are used only
as metadata search: they can contribute DOI, PMID, title, author, archive URL,
or application-number text when those are publicly returned. For deleted repositories, Wayback is used only to recover README-like
public metadata snapshots; `wayback_readme_first_capture` is an archival
observation date, not a creation date or leakage date.

Seeded publication/package search results can provide metadata evidence for a
lineage, but they do not override GitHub fork/source metadata. Fork lineage is
still determined by GitHub-displayed fork/source relationships when those are
available.

When public metadata links a publication/code repository to a unique UKB
application, but the DMCA-targeted lineage is a same-topic author, first-author,
or lab-owned repository without GitHub-displayed fork/source proof, the seed may
record the line as `B1_AUTHOR_LAB_PROJECT_NAME_TOPIC_CONSISTENCY`. B1 rows
preserve empirical signal for manual review and sensitivity analyses, but they
can produce only `probable`, never `confirmed`.

When an unresolved lineage has the same normalized repository/package basename
as an existing confirmed/probable public metadata anchor or seeded public
metadata chain, the overlay can derive
`B2_PROJECT_FAMILY_NAME_PROPAGATION`. B2 is a probable-only empirical linkage:
it preserves the anchor publication/application evidence and records the target
lineage's public repository URLs, but it does not assert that GitHub displayed a
fork/source relationship. Generic project names such as `ukb`, `ukbiobank`,
`001`, `data`, and `phenotype` are excluded from propagation.

When an unresolved lineage shares the same public GitHub target content
fingerprint as an existing confirmed/probable anchor or seeded public metadata
chain, the overlay can derive
`B3_EXACT_TARGET_CONTENT_FINGERPRINT_PROPAGATION`. The fingerprint is based on
public notice/repository URLs containing the same Git blob/tree/raw commit SHA
and path. B3 is also probable-only or ambiguous; it does not assert who created
or uploaded the content and does not treat the target commit date as a leakage
date.

If a DOI/PMID maps to multiple applications, the lineage is `ambiguous` unless independent identity/context evidence clearly favors one candidate; that case can become `probable`, not `confirmed`.

## Supporting Evidence

B-level evidence supports candidate ranking and `probable` labels:

- DOI/PMID appearing directly in application notes.
- Exact or near-exact publication title evidence.
- Paper author to application PI match.
- Repository owner to paper author match.
- Commit author to paper author match.
- Institution match.
- Multiple mutually consistent public metadata sources.
- `B1_AUTHOR_LAB_PROJECT_NAME_TOPIC_CONSISTENCY`: a manually curated seed where
  a unique public publication/application chain exists for a closely matching
  project, and the DMCA-targeted lineage matches an author/lab owner plus
  repository or package name, but exact GitHub fork/source proof is unavailable.
- `B2_PROJECT_FAMILY_NAME_PROPAGATION`: an automated seed overlay where an
  unresolved lineage shares an exact normalized repository/package basename with
  an existing confirmed/probable anchor or public metadata seed. This is useful
  for sensitivity analyses over repeated forks/reuploads, but remains
  `probable` or `ambiguous`, never `confirmed`.
- `B3_EXACT_TARGET_CONTENT_FINGERPRINT_PROPAGATION`: an automated seed overlay
  where an unresolved lineage shares the same public GitHub blob/tree/raw commit
  SHA and path with an existing confirmed/probable anchor or public metadata
  seed. This is useful for reupload/fork-family sensitivity analyses and remains
  `probable` or `ambiguous`, never `confirmed`.

C-level evidence is weak and is used only for candidate generation/ranking:

- Topic overlap.
- Application notes topic overlap.
- Repository/path similarity.
- Alleged data type similarity.

Generic words such as `cancer`, `genetic`, `imaging`, `risk`, `disease`, `UKB`, and `data` are down-weighted. Data type alone can never produce `confirmed` or `probable`.

## Final Labels

- `confirmed`: unique direct app ID, or a unique deterministic DOI/PMID Schema 19/24 crosswalk from repository-linked publication evidence.
- `probable`: no unique A-level evidence, but several independent B-level components identify one application and the top candidate clearly dominates competitors.
- `ambiguous`: multiple applications remain plausible, including multi-application publication crosswalks that cannot be disambiguated.
- `unresolved`: evidence is missing, generic, or weak.
- `not_application_attributable`: third-party propagation/reposting is evident but no original UKB application can be established.

## Audit Outputs

- `ukb_dmca/ukb_dmca_application_candidates.csv` preserves all retained candidates and scores.
- `ukb_dmca/ukb_dmca_application_match_evidence.csv` stores one row per lineage x candidate application x evidence component.
- `ukb_dmca/evidence/lineages/*.md` records public repository metadata, README/CITATION/package/Wayback sources, public metadata seed rows when present, target commit metadata, publication IDs, crosswalk details, and candidate reasons.
- `ukb_dmca/evidence/logs/result_summary.json` reports method contribution counts, including direct app ID, DOI crosswalk, PMID crosswalk, public metadata seed usage, B2/B3 propagation usage, probable, ambiguous, unresolved, and unique applications linked.
- `ukb_dmca/curated_dmca_application_links.csv` is the canonical manually curated application-level crosswalk used for the empirical leakage outcome.
- `ukb_dmca/curated_dmca_repository_family_links.csv` stores the repository/family evidence layer used to construct and audit the curated crosswalk.
- `ukb_dmca/remaining_23_repo_review.csv` records the completed 23-family public-evidence review, including unresolved and false-positive cases.
- `ukb_dmca/exhaustive_dmca_application_attribution.csv` records the expanded full-universe attribution table, including supported, ambiguous, weak, and manually excluded candidates.
- `ukb_dmca/exhaustive_dmca_family_attribution_summary.csv` summarizes attribution coverage at the repository-family level.
- `ukb_dmca/exhaustive_dmca_application_attribution_report.md` reports full-universe attribution counts and interpretation guidance.
- `ukb_dmca/leakage_application_analysis/` contains the application-level leakage outcome, descriptive tables, regression tables, ITS tables, figures, and reports.

## Current Limitations

Deleted repositories often lack public GitHub metadata. Wayback captures are treated only as archived observations, not repository creation or leakage dates. Commit dates are named targeted/observed commit dates and are not interpreted as leakage dates. Without Schema 19/24 files, DOI/PMID crosswalk matching is disabled and those method contribution counts remain zero.
