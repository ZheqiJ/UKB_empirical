# Publication ITS Design

The publication analysis separates system-level output, project-level productivity/timing, and pipeline-adjusted output. Total scientific output is interpreted as the product of project entry, project-level productivity, and publication timing.

| Candidate Y | Definition | Research Question | Main Limitations | How Limitations Are Addressed |
| --- | --- | --- | --- | --- |
| Y1 Total monthly publications | Monthly `unique_publication_ids`; aggregate `fractional_publication_count` is identical by construction | Did system-level UKB-linked publication flow change around July 2024? | Publication response is lagged; total output mixes entry and productivity. | Treat as descriptive calendar-time ITS; report lag and pipeline diagnostics. |
| Y2 Publications per dynamic incumbent pool | 100 x fractional publications linked to pre-transition incumbents / post-start incumbents | How does incumbent-pool intensity evolve? | Denominator grows before July 2024 and age composition changes. | Demoted to supplementary decomposition. |
| Y3 Fixed-cohort publication intensity | 100 x cohort publications / fixed cohort size | Does a stable pre-transition cohort show similar movement? | Older cohorts are not representative of all system output. | Prespecified cutoffs, no selection by significance. |
| Y4 Project-age-standardized publication rate | Publication output by project age month or age band | How strongly does output vary over the project lifecycle? | Right-censoring at long ages for recent cohorts. | Age-specific risk sets with complete follow-up. |
| Y5 Publications within fixed follow-up window | Project-level fractional publications within H months | Are RAP-era projects similarly productive at comparable early ages? | Post-RAP cohorts currently have limited follow-up. | Only eligible projects with complete follow-up are included. |
| Y6 Any publication within fixed follow-up window | Project-level any-publication indicator within H months | Do RAP-era projects reach first output at similar early rates? | Same short follow-up problem. | Report feasible 12-month horizon and mark 18/24 months infeasible for post cohorts. |
| Y7 Time to first publication | Cumulative first-publication probability by project age | Does timing differ across project-start cohorts? | Mature post-RAP timing is not observed. | Transparent cumulative-incidence tables, no causal survival claim. |
| Y8 Project-month publication count | Project x calendar month fractional output | How do calendar time and project age jointly describe output? | High-dimensional descriptive panel; July is not individual treatment for incumbents. | Calendar post and project age are separate variables. |
| Y9 Pipeline-adjusted publication gap | Actual total output minus expected output from pre-transition age profile and project pipeline | Is post-July total output unusual relative to the evolving project pipeline? | Historical benchmark, not causal counterfactual. | Estimate age profile only from pre-transition information. |

Alternative outcomes are Y1 measurement variants and Y2/Y3 rate definitions. Y4-Y9 diagnose limitations in total-output interpretation.
