# Design 1 Supervisor Memo: Quarterly Incumbent DID for Publication Outcomes

## Executive Summary

This first quarterly design is best presented as a successful empirical pipeline and design-feasibility checkpoint, not as a final causal result. Using the fixed working universe of 6,935 matched UK Biobank projects, we construct an application-quarter risk-set panel from 2022Q3 to 2026Q2 and estimate incumbent-project DID specifications around the 5 July 2024 RAP transition. The data construction passes the main integrity checks: no pre-project periods are coded as zero, publication dates are audited, incomplete 2026Q3 observations are excluded, and project-entry after the policy is not used for incumbent DID identification.

The main publication estimates are small and statistically imprecise. Under the broadest provisional control definition, CONTROL_C05, the quarterly DID estimate is 0.015 additional publications per project-quarter (SE 0.025, p = 0.532) and -0.002 for any publication (SE 0.012, p = 0.848). Adding project-age-bin fixed effects, dropping the 2024Q3 transition quarter, and dropping the first partial at-risk quarter do not materially change the conclusion. However, the identification remains fragile because the control group is small and partly provisional, C0 fails formal pretrend tests, and the count result is sensitive to top-output projects.

The cleanest message to a supervisor is: the design is now running end to end and produces a credible quarterly panel, but the current evidence does not show a robust publication effect of the July 2024 RAP transition. The next priority is to improve treatment/control measurement and comparability before interpreting the DID estimates as causal.

## Data

The working universe is the fixed set of 6,935 UK Biobank projects previously matched to public project records with unique project start dates. The publication data come from UKB Schema 19 publication metadata and Schema 24 publication-application links.

Key data checks:

| Item | Value |
|---|---:|
| Working projects | 6,935 |
| Application-quarter rows | 75,973 |
| Main quarterly window | 2022Q3-2026Q2 |
| Publication events used in complete quarter panel | 12,400 |
| Exact Schema 19 publication dates | 14,633 |
| Schema 24 application-publication links | 12,598 |
| Duplicate application-publication pairs | 0 |
| Publication events before project start | 24, audited and excluded |
| Events after 2026Q2 complete window | 168, audited and excluded |
| Pre-project panel rows | 0 |

The panel is an at-risk panel: rows begin only once a project is active according to its recovered project start date. This avoids the main mechanical bias in a naive calendar panel, where pre-start periods would be incorrectly coded as zero-output periods.

## Design

The estimand is an incumbent-project DID: did publication output change differentially after 5 July 2024 for projects provisionally classified as newly RAP-bound, relative to projects that were already RAP-bound or likely control candidates before the policy?

The baseline specification is:

```text
Y_iq = beta * Treated_i * Post_q + project FE_i + quarter FE_q + error_iq
```

where `Y_iq` is either publication count or an indicator for any publication in project-quarter `q`. Standard errors are clustered by application. The preferred robustness specification adds project-age-bin fixed effects.

The design is intentionally not a project-entry or approval design. Projects starting after the policy are excluded from the incumbent DID sample because they do not provide genuine pre-policy at-risk periods.

The current treatment/control definitions remain provisional:

| Definition | Treated projects | Control projects | Comment |
|---|---:|---:|---|
| CONTROL_C0 | 3,344 | 30 | Strictest but very small |
| CONTROL_C01 | 3,338 | 112 | Larger but still partly fragile |
| CONTROL_C03 | 3,325 | 130 | Better precision and pretrend behavior |
| CONTROL_C05 | 3,324 | 131 | Broadest current candidate control |

## Main Results

The main results do not show a robust or precise publication effect.

| Control definition | Outcome | Q0 estimate | SE | p-value | Q1 age-adjusted estimate |
|---|---|---:|---:|---:|---:|
| CONTROL_C0 | Publication count | 0.0896 | 0.0862 | 0.299 | 0.1096 |
| CONTROL_C0 | Any publication | -0.0073 | 0.0179 | 0.685 | 0.0056 |
| CONTROL_C01 | Publication count | 0.0065 | 0.0280 | 0.816 | 0.0232 |
| CONTROL_C01 | Any publication | -0.0123 | 0.0132 | 0.349 | -0.0027 |
| CONTROL_C03 | Publication count | 0.0152 | 0.0248 | 0.539 | 0.0258 |
| CONTROL_C03 | Any publication | -0.0048 | 0.0122 | 0.697 | 0.0010 |
| CONTROL_C05 | Publication count | 0.0154 | 0.0246 | 0.532 | 0.0252 |
| CONTROL_C05 | Any publication | -0.0024 | 0.0124 | 0.848 | 0.0031 |

For CONTROL_C05, dropping the 2024Q3 transition quarter gives a count estimate of 0.0179 (p = 0.425) and an any-publication estimate of 0.0007 (p = 0.958). Dropping first partial at-risk quarters also leaves estimates close to zero.

The count outcome is sensitive to highly productive projects: excluding the top 1% of publication-output projects changes the CONTROL_C05 count estimate from 0.0154 to -0.0022 (p = 0.882). This suggests that any positive count signal is not broadly distributed across projects.

## Identification Assessment

The data-construction checkpoint passes, but the identification checkpoint remains a warning.

Pretrend tests:

| Control definition | Publication count pretrend p-value | Any-publication pretrend p-value | Assessment |
|---|---:|---:|---|
| CONTROL_C0 | 0.0236 | 0.0327 | Fails |
| CONTROL_C01 | 0.0777 | 0.0390 | Mixed |
| CONTROL_C03 | 0.0571 | 0.0930 | Pass-ish, still borderline |
| CONTROL_C05 | 0.0785 | 0.2011 | Best among current definitions |

For a supervisor, I would not lead with CONTROL_C0 despite its conceptual cleanliness, because it has only 30 controls and fails pretrend tests. CONTROL_C05 is the most practical current summary because it gives the largest control group and the best pretrend behavior, but it should still be described as provisional rather than final.

The strongest interpretation is descriptive and exploratory: within the current provisional treatment/control definitions, there is no clear evidence that publication output changed differentially after the RAP transition. The estimates are small, imprecise, and not stable enough to support a causal headline.

## What Not to Overclaim

Do not say that the RAP transition had no effect on publications. The defensible statement is narrower: this first incumbent-project quarterly DID does not detect a robust publication effect through 2026Q2.

Do not present CONTROL_C0 as the main empirical result. It is conceptually clean but has only 30 controls and fails the joint pretrend tests. I would present CONTROL_C05 as the current main working specification and show C0/C01/C03 as sensitivity checks.

Do not describe treatment/control assignment as final. It is a provisional measurement layer inherited from Stage 3 and remains the main source of empirical risk.

Do not generalize this design to project entry, new applications, DMCA outcomes, or longer-run publication effects. Those require separate designs.

## How I Would Present This to the Supervisor

I would frame this as a productive milestone:

1. We have moved from a simple before/after check to a proper quarterly risk-set DID panel.
2. The pipeline is reproducible through GitHub Actions and can now support alternative designs quickly.
3. The current result is not a strong policy-effect result; it is a diagnostic result showing that publication outcomes are hard to move and hard to identify over this short horizon.
4. The main bottleneck is not computation anymore. The main bottleneck is empirical design quality: control-group credibility, project lifecycle, active status, and publication lag.

Suggested one-sentence headline:

> We now have a working quarterly incumbent-project DID pipeline; the first publication results do not show a robust post-RAP change, but the design diagnostics show that treatment/control measurement and project lifecycle comparability must be improved before making causal claims.

For a short meeting, I would show four items only: the risk-set construction table, the C05 main-results table, the C05 event-study figure with 2024Q2 as reference, and a one-slide limitations/next-step table. The goal is to make the progress obvious without overselling the estimate.

## How to Improve the Result and Design

The best way to make the result stronger is to improve credibility and precision, not to search across definitions for significance.

Priority 1: strengthen the control group.

The current control bottleneck is severe: the strict control group has only 30 projects, and even the broadest control has 131. We should expand high-confidence already-RAP-bound controls using project text and modality evidence, especially projects clearly dependent on pre-policy RAP-only modalities. This could improve both power and pretrend credibility.

Priority 2: improve common support.

The treated and control projects likely differ in start timing, project age, and productivity lifecycle. The next design should report a compact balance table and then restrict or reweight projects by project start quarter, pre-policy publication productivity, institution, and broad research area. A matched or weighted incumbent DID may be more credible than the full-sample panel.

Priority 3: account for publication lag and active status.

Publication outcomes may respond slowly, and many older projects may no longer be actively producing publications by July 2024. We should try to identify active projects using recent pre-policy publications, project website status where available, or post-start project age restrictions. A more active-project sample could reduce attenuation.

Priority 4: add monthly timing only as robustness.

Monthly timing can show whether any short-run pattern is concentrated around July 2024, but it should not replace the quarterly design. It is useful mainly to diagnose transition timing and publication-date bunching.

Priority 5: add formal sensitivity for borderline pretrends.

For the preferred C05 event-study, add an event-study figure with confidence intervals and consider Honest DiD / Rambachan-Roth style sensitivity bounds. This would make the "pretrends are acceptable but not perfect" argument more referee-facing.

Priority 6: improve count-model robustness.

Because count results are sensitive to top-output projects, add winsorized counts, PPML or negative binomial models where feasible, and separate extensive-margin and intensive-margin analyses based only on pre-policy productivity strata.

Priority 7: keep DMCA separate.

DMCA should be treated as a separate outcome family because the application-notice linkage is sparse and not naturally suited to the same quarterly DID structure. It can be presented as an auxiliary design rather than folded into the publication panel.

## Recommended Next Step

Before moving to a final publication effect table, I recommend one design-improvement pass:

1. Build a matched or weighted quarterly incumbent DID using CONTROL_C03/C05 candidates.
2. Match or weight on project start quarter, pre-policy publication count, pre-policy any-publication, institution, and broad text-derived research area if available.
3. Re-run Q0/Q1, event-study pretrends, drop-2024Q3, top-1% exclusion, and productivity strata.
4. Only after that, run the monthly timing robustness as Design 2.

This gives the project a better empirical story: the first design proves the pipeline works, and the next design directly addresses the biggest identification objections.
