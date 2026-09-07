# Application-Level Modified Poisson Results: 52, 55, and Candidate-Inclusive Attribution Outcomes

## Outcome Construction

The analysis unit is a UK Biobank application in the fixed public valid-start-date universe (`N = 6,935`). `Leak52` marks the current curated 52 applications. `Leak55` adds the three existing Tier-4 single-application ambiguous additions. `Leak269` is the candidate-inclusive upper-bound attribution outcome based on all Tier 1-5 application IDs in the existing tier table.

The candidate-inclusive source membership contains 269 unique application IDs. Three Tier-5 UK Biobank internal applications (`68250`, `77202`, and `80154`) have no public valid start date, so they cannot enter a model with application timing and are not added to or imputed into the fixed 6,935-application universe. Consequently, `Leak269` has 266 analytic positive applications. This is a timing-data limitation, not a rematch or a revision to the 269-ID source set.

## Raw Descriptive Rates

The table shows raw application-start-date rates before and after 5 July 2024. These descriptive differences are not causal estimates.

| Outcome | Source membership | Analytic positives | Pre rate | Post rate | Post beta | Clustered SE | p-value | 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Curated 52 attribution outcome | 52 | 52 | 1.154% | 0.077% | -3.5975 | 1.2740 | 0.004746 | [-6.0945, -1.1005] |
| Broad 55 attribution outcome | 55 | 55 | 1.223% | 0.077% | -3.6679 | 1.2698 | 0.003871 | [-6.1568, -1.1790] |
| Candidate-inclusive upper-bound attribution outcome | 269 | 266 | 4.409% | 2.881% | -0.4830 | 0.2747 | 0.07872 | [-1.0214, 0.0555] |

## Primary Modified Poisson Specification

For each outcome, the primary model is `log E[Leak_s,i | X] = beta0 + beta1 Time + beta2 PostJuly2024 + beta3 TimeAfterJuly2024 + month-of-year fixed effects`, where `PostJuly2024 = 1[start_date >= 2024-07-05]`. It is estimated as Poisson QMLE (modified Poisson). Primary inference uses CR1 sandwich standard errors clustered by application start month; the full results include all month-of-year indicators and their Stata-style omission status. The raw beta coefficients are the primary estimands. Exponentiated coefficients are reported separately as risk ratios.

`PostJuly2024` is a level discontinuity on the log expected leakage-probability scale conditional on the pre-policy time trend and month-of-year fixed effects. `Time` is the pre-policy monthly log-scale slope and `TimeAfterJuly2024` is the change in that monthly slope after July 2024. These associations use application start dates only; they do not use DMCA notice, repository, or commit dates as timing.

## Post-Policy Slope

The post-policy monthly log-scale slope is `beta_Time + beta_TimeAfterJuly2024`; delta-method CR1 inference is below.

| Outcome | beta(Time + TimeAfter) | Clustered SE | p-value | 95% CI |
|---|---:|---:|---:|---:|
| Curated 52 attribution outcome | 0.11808759 | 0.08084948 | 0.144129 | [-0.04037740, 0.27655258] |
| Broad 55 attribution outcome | 0.11479982 | 0.07990058 | 0.15078 | [-0.04180532, 0.27140495] |
| Candidate-inclusive upper-bound attribution outcome | 0.02992910 | 0.01849576 | 0.105628 | [-0.00632259, 0.06618079] |

## Robustness and Figures

For `Leak52` and `Leak55`, January has zero events and therefore perfectly predicts zero under a saturated month-FE Poisson model. The finite QMLE component follows the separation limit: January is explicitly shown as omitted for perfect zero prediction, its fitted mean is zero, and the remaining finite coefficients use 6,284 applications. The analytic universe remains the fixed 6,935 applications; this handling avoids presenting divergent coefficients as valid estimates. `Leak269` has a finite month-FE model on all 6,935 applications.

The companion inference table contrasts the primary start-month-clustered sandwich SE with unclustered HC1 sandwich SE. The figures aggregate application-level observed outcomes and fitted Poisson predictions to start month only for display; no monthly or quarterly model is used as the primary estimator. The common-scale plot is a visual diagnostic.

This observational application-timing analysis does not establish a causal effect of the July 2024 RAP transition. It does not select a preferred outcome based on statistical significance. The candidate-inclusive upper-bound outcome is deliberately kept separate from the curated and broad outcomes because its attribution evidence is weaker by construction.
