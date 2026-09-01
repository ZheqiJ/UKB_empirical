# Publication ITS Design

The publication analysis asks a descriptive question: how did UKB-linked publication output change around and after the July 2024 institutional transition? July 2024 is a calendar institutional marker, not the individual treatment date for every project.

The report is organized around four questions: total output, project-start cohort contribution, lifecycle and pipeline composition, and comparable early-age project performance.

| Candidate Y | Definition | Research Question | Main Limitations | How Limitations Are Addressed |
| --- | --- | --- | --- | --- |
| Y1 Total monthly publications | Monthly `unique_publication_ids`; aggregate `fractional_publication_count` is identical by construction | Did system-level UKB-linked publication flow change around July 2024? | Publication response is lagged; total output mixes entry and productivity. | Descriptive monthly ITS; report fitted pre-trend differences, transition-window sensitivity, and endpoint sensitivity. |
| Y2 Publications per dynamic incumbent pool | 100 x fractional publications linked to pre-transition incumbents / post-start incumbents | How does incumbent-pool intensity evolve? | Denominator grows before July 2024 and age composition changes. | Retained as supplementary incumbent-pool diagnostic. |
| Y3 Fixed-cohort publication intensity | 100 x cohort publications / fixed cohort size | Does a stable pre-transition cohort show similar movement? | Older cohorts are not representative of all system output. | Prespecified cutoffs, no selection by significance. |
| Y4 Project-age-standardized publication rate | Publication output by project age month or age band | How strongly does output vary over the project lifecycle? | Right-censoring at long ages for recent cohorts. | Age-specific risk sets with complete follow-up. |
| Y5 Publications within fixed follow-up window | Project-level fractional publications within exact H-month window | Are post-transition project-start cohorts unusual at comparable early ages? | Post-transition cohorts currently have limited follow-up. | Use exact date cutoffs and mark 18/24 months not yet estimable. |
| Y6 Any publication within fixed follow-up window | Project-level any-publication indicator within exact H-month window | Do project-start cohorts reach first output at similar early rates? | Same short follow-up problem. | Report feasible 12-month horizon and six-month start cohorts. |
| Y7 Time to first publication | Kaplan-Meier `1 - S(age)` by project-start cohort | Does early first-publication timing differ across cohorts? | Mature post-transition timing has little support. | Show confidence intervals and number-at-risk table. |
| Y8 Project-month publication count | Project x calendar month fractional output and any-publication outcome | After lifecycle adjustment, is there still a July calendar transition pattern? | Age-period-cohort collinearity if saturated. | Use fine lifecycle bins plus common calendar trend and segmented July terms, not a saturated APC design. |
| Y9 Pipeline-adjusted publication gap | Actual total output minus expected output from pre-transition smoothed project-age profile and realized pipeline | Is post-July total output high or low relative to the realized project pipeline? | Descriptive benchmark, not causal counterfactual. | Estimate age profile only from pre-transition months; add trend-adjusted sensitivity and bootstrap CI. |

The main language should be descriptive: July 2024 institutional transition, post-transition publication trajectory, descriptive benchmark, RAP-era project cohort, and post-transition project-start cohort.
