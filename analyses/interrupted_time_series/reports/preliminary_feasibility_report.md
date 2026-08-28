# Preliminary ITS Feasibility Report

## 1. New Empirical Objective

The new objective is descriptive. We document temporal and cross-project patterns surrounding the July 2024 UK Biobank data-access transition and use robust stylized facts to motivate and discipline the existing theoretical model.

## 2. Why The Previous Causal DID Interpretation Was Set Aside

The public data do not observe actual project-level RAP migration dates, refresh requests, active/expired project status, or actual RAP use. Existing C0-C6 classifications are useful legacy-exposure proxies, but they do not create a clean untreated counterfactual. Publication is also a lagged downstream outcome, and April 2026 is a distinct platform-governance shock.

## 3. Repository/Data Inventory

The reorganized package uses shared source data in `data/raw` and `data/intermediate`, plus archived DID panel outputs under `analyses/did_archive/data/analysis`.

## 4. Candidate Stylized Facts Discovered

- Project starts show a very sharp 2024 transition-window pattern: April 72, May 33, June 10, July 3, August 0, September 1, October 208.
- Quarterly starts move from 2024Q2=115 to 2024Q3=4 to 2024Q4=470.
- Aggregate incumbent publications are feasible with exact Schema 19 dates; key quarters currently include {"2024Q2": {"any_publication_rate_percent": "8.36", "at_risk_incumbent_projects": 4329, "publication_app_links": 519}, "2024Q3": {"any_publication_rate_percent": "8.24", "at_risk_incumbent_projects": 4332, "publication_app_links": 539}, "2024Q4": {"any_publication_rate_percent": "8.36", "at_risk_incumbent_projects": 4332, "publication_app_links": 507}, "2025Q1": {"any_publication_rate_percent": "9.76", "at_risk_incumbent_projects": 4332, "publication_app_links": 629}, "2026Q2": {"any_publication_rate_percent": "9.37", "at_risk_incumbent_projects": 4332, "publication_app_links": 588}}.
- C05 has 3326 legacy-exposure proxy projects and 131 RAP-intensive comparison projects in the incumbent sample.
- Returned-dataset timing is not feasible from the local Schema 4 extract.

## 5. Strongest Patterns Currently Visible

The strongest fact is project entry: the July-September 2024 trough and October 2024 restart are visually and economically large relative to ordinary monthly variation. This should be described as an unusual administrative timing pattern around the institutional transition, not as proof of a RAP treatment effect.

## 6. Weak/Infeasible Candidate Facts

Returned datasets are low feasibility because the local public metadata lack usable timing. Institution/country patterns are only low-medium feasibility because institution names are not standardized into countries. C06 should remain a measurement diagnostic rather than a preferred comparison group.

## 7. Proposed ITS Designs

1. ITS-1: aggregate project starts, monthly.
2. ITS-2: aggregate incumbent publication trajectory, monthly or quarterly.
3. ITS-3: comparative ITS for prespecified exposure-proxy groups.
4. ITS-4: descriptive event-time dynamics around 2024Q3.

## 8. Exact Regression Specifications Under Consideration

For monthly starts:

```text
Y_t = alpha + beta1 time_t + beta2 JulSep2024_t
    + beta3 Oct2024Restart_t + beta4 PostOct2024_t
    + month-of-year FE + error_t
```

For comparative publication trajectories:

```text
Y_gt = group FE + calendar FE + group-specific pre-trend
    + legacy_proxy_g x post-window terms + error_gt
```

Coefficients are descriptive level/slope changes or differential trajectories.

## 9. Exact Data/Sample For Each Specification

- ITS-1: matched project starts from `data/intermediate/timing_feasibility/timing_working_research_project_universe.csv`.
- ITS-2: incumbent projects started before 2024-07-05 with exact-date Schema 19/24 publication links.
- ITS-3: archived quarterly panel rows for C03/C05/C06 eligible groups, relabelled as descriptive proxies.
- ITS-4: same quarterly panel, shown as event-time dynamics around 2024Q3.

## 10. Descriptive Hypotheses/Questions

- Was there an unusually sharp project-entry change around the transition?
- Was the entry disruption temporary or persistent?
- Did incumbent publication output show an immediate break, delayed change, or no visible discontinuity?
- Did legacy-exposure and RAP-intensive proxy groups follow different post-transition trajectories?
- Were trajectories different for recent versus mature projects and for extensive versus intensive margins?

## 11. Time Windows And Transition Coding

The main transition marker is 2024-07-05. Monthly entry models should separately code July-September 2024 and October 2024. Quarterly publication models should mark 2024Q3 and report 2026Q2 separately because April 2026 changes the platform-governance regime.

## 12. Concurrent Institutional Shocks

| Source | URL | Accessed |
| --- | --- | --- |
| OMOP release on RAP | https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases | 2026-08-27 |
| Expanded proteomics and imaging release | https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases | 2026-08-27 |
| 500k WGS release on UKB-RAP | https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/16019641094813-New-Data-release-on-UKB-RAP-WGS-Data-from-500-000-Participants-Proteomics-Data-Updated-Imaging-Data | 2026-08-27 |
| UKB data access institutional transition | https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/19996604847133-Changing-the-way-UK-Biobank-data-is-made-available-to-researchers-around-the-world | 2026-08-27 |
| Major November 2025 data release | https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases | 2026-08-27 |
| RAP participant-withdrawal enforcement/platform governance shock | https://community.ukbiobank.ac.uk/hc/en-gb/articles/34853452782621-Participant-withdrawals-on-UKB-RAP | 2026-08-27 |
| Additional UKB-RAP access requirement | https://community.ukbiobank.ac.uk/hc/en-gb/articles/22784123882909-Why-does-it-say-that-my-project-is-not-enabled-for-UKB-RAP | 2026-08-27 |

## 13. Data Limitations

The public data lack project active/expired status, observed RAP migration, refresh requests, project-level RAP use, and participant-level information. Publication dates are exact only for a subset; year-only dates are excluded from timing series. Multi-application publication links are audited and retained as app-publication links.

## 14. What Can And Cannot Be Interpreted

The package can document temporal patterns, group composition, and descriptive post-transition differential changes. It cannot identify a causal RAP effect or prove that any individual incumbent project was treated on 2024-07-05.

## 15. Recommended Order Of Implementation

Start with raw project-entry plots and a compact segmented count ITS. Then show aggregate incumbent publication trajectories with delayed windows. Only after that show C05 comparative trajectories and composition diagnostics.

## 16. Files/Figures/Tables Created

- `analyses/interrupted_time_series/data/its_project_starts_monthly.csv`
- `analyses/interrupted_time_series/data/its_project_starts_quarterly.csv`
- `analyses/interrupted_time_series/data/its_incumbent_publications_monthly.csv`
- `analyses/interrupted_time_series/data/its_incumbent_publications_quarterly.csv`
- `analyses/interrupted_time_series/data/its_comparative_quarterly.csv`
- `analyses/interrupted_time_series/data/its_group_composition.csv`
- `analyses/interrupted_time_series/data/its_modality_project_counts.csv`
- `analyses/interrupted_time_series/data/its_age_band_quarterly.csv`
- `analyses/interrupted_time_series/data/its_publication_lag.csv`
- `analyses/interrupted_time_series/data/its_returned_data_feasibility.csv`
- `analyses/interrupted_time_series/data/its_top_institutions.csv`
- `analyses/interrupted_time_series/data/its_institutional_dates.csv`
- `analyses/interrupted_time_series/figures/its_project_starts_monthly.svg`
- `analyses/interrupted_time_series/figures/its_incumbent_publications_quarterly.svg`
- `analyses/interrupted_time_series/figures/its_c05_group_quarterly_any_publication.svg`

## 17. Questions That Require Supervisor Approval

- Should the main publication window end before 2026Q2?
- Should July-September 2024 be coded as one transition pause or as separate month indicators?
- Should C05 remain the primary descriptive exposure proxy, with C03/C06 as sensitivity?
- Which modality groups are acceptable for supervisor-facing heterogeneity?

## Master Table

| Priority | Stylized fact | Data | Figure | Descriptive model | Main limitation | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Administrative-looking project-entry pause and restart | Matched starts | figures/its_project_starts_monthly.svg | Monthly segmented count ITS | Cannot attribute to RAP rather than administrative timing | Show first |
| 2 | Aggregate incumbent publication trajectory | Schema 19/24 + starts | figures/its_incumbent_publications_quarterly.svg | Quarterly ITS with delayed windows | Publication lag and no active status | Show second |
| 3 | C05 legacy-proxy vs RAP-intensive differential trajectory | Archived panel + Stage 3 proxies | figures/its_c05_group_quarterly_any_publication.svg | Comparative ITS | Proxy groups are compositionally different | Use after composition table |
| 4 | Recent vs mature project trajectories | Starts + archived panel | To add after review | Age-band comparative ITS | Age is not activity status | Medium priority diagnostic |
| 5 | Returned data timing | Schema 4 | None | None | No timing field in local extract | Mark infeasible |
