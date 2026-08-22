# Design 1 Memo: Quarterly Incumbent DID for Publication Outcomes

## 1. Question and Design

We now have a working quarterly incumbent-project DID and event-study pipeline for the 5 July 2024 UK Biobank RAP transition. The question is whether publication output changed differentially after the policy for projects provisionally classified as newly RAP-bound, relative to already-RAP-bound or already-RAP-bound-like incumbent controls.

This is an **incumbent-project design**, not a project-entry design. Using the fixed universe of 6,935 matched UK Biobank projects, we construct an application-quarter post-entry risk-set panel from 2022Q3 to 2026Q2. Under the broad C05 provisional treatment/control definition, the incumbent DID estimation sample contains 3,324 treated projects and 131 control projects.

The baseline specification is:

```text
Y_iq = beta * Treated_i * Post_q + project FE_i + quarter FE_q + error_iq
```

where `Y_iq` is either quarterly publication count or an indicator for any publication. Standard errors are clustered by application. A lifecycle-adjusted diagnostic specification adds project-age-bin fixed effects.

Important interpretation: the panel begins only after each recorded project start date. This prevents pre-start quarters from being coded as zero-output observations. It does **not** imply that every project remains actively using UK Biobank data in every subsequent quarter; this is an ITT-like exposure design, not a verified active-user design.

## 2. What We Fixed Since the Earlier Fast Run

The current design improves on the initial 24-month before/after pipeline in five ways:

- It uses a quarterly risk-set panel rather than two coarse pre/post windows.
- Project quarters before recorded project start are excluded, not coded as zero.
- Publication timing is audited using exact Schema 19 dates and Schema 24 application-publication links.
- The main window excludes incomplete 2026Q3 observations and ends at 2026Q2.
- The design now reports app FE + quarter FE DID, lifecycle adjustment, transition-quarter robustness, first-partial-quarter robustness, top-output sensitivity, and formal event-study pretrend tests.

Data construction passes the main checks:

| Item | Value |
|---|---:|
| Fixed working universe | 6,935 projects |
| Application-quarter rows | 75,973 |
| Main window | 2022Q3-2026Q2 |
| Publication events in complete quarter panel | 12,400 |
| Duplicate application-publication pairs | 0 |
| Publication events before project start | 24, audited and excluded |
| Events after 2026Q2 complete window | 168, audited and excluded |
| Pre-start panel rows | 0 |

## 3. Main Result

The preferred working summary is C05, because it gives the largest provisional control sample while preserving the cumulative C0-C5 evidence hierarchy. I would show C03 as a close robustness check and put C0/C01 in the appendix.

Main estimates:

| Specification | Publication count | Any publication |
|---|---:|---:|
| C05 Q0: app FE + quarter FE | 0.015 (0.025), p = 0.532 | -0.002 (0.012), p = 0.848 |
| C05 Q1: plus project-age-bin FE | 0.025 (0.024), p = 0.296 | 0.003 (0.012), p = 0.796 |
| C05, drop 2024Q3 transition quarter | 0.018 (0.022), p = 0.425 | 0.001 (0.013), p = 0.958 |
| C05, drop first partial at-risk quarter | 0.011 (0.025), p = 0.665 | -0.005 (0.013), p = 0.666 |
| C05, exclude top 1% high-output apps | -0.002 (0.015), p = 0.882 | -- |
| C03 Q0: app FE + quarter FE | 0.015 (0.025), p = 0.539 | -0.005 (0.012), p = 0.697 |

Economic magnitude should be interpreted relative to the pre-policy quarterly baseline. In C05, treated projects averaged 0.122 publications per pre-policy project-quarter and 8.45% had any publication; control projects averaged 0.134 publications and 6.99% had any publication. The C05 count estimate of 0.015 publications per project-quarter is about 12.6% of the treated pre-policy mean, but it is imprecise and not robust to excluding the upper tail of high-output projects. The any-publication estimate is about -0.24 percentage points relative to an 8.45% treated pre-policy baseline.

The positive full-sample mean-count estimate is sensitive to the upper tail of the publication distribution: excluding the top 1% of high-output applications reduces the estimate from 0.015 to approximately zero. This does not imply that these projects are invalid observations; it shows that the average-count result is not broadly robust across the outcome distribution.

Bottom line: there is currently no robust or precisely estimated differential publication response in the quarterly incumbent design.

## 4. Identification Diagnostics

The implementation/data checkpoint passes, but identification remains a warning.

| Definition | Count pretrend p-value | Any-publication pretrend p-value | Interpretation |
|---|---:|---:|---|
| C0 | 0.0236 | 0.0327 | Joint pretrend rejected |
| C01 | 0.0777 | 0.0390 | Mixed across outcomes |
| C03 | 0.0571 | 0.0930 | Not rejected at 5%, but borderline |
| C05 | 0.0785 | 0.2011 | Not rejected; count test remains borderline |

Failure to reject a joint pretrend test is not proof of parallel trends, especially with only 130-131 controls in the broader control definitions. C05 is therefore a useful working specification, not a final validated control group. The remaining concerns are: small/provisional controls, incomplete information on actual RAP migration or active use, publication lag, and upper-tail sensitivity in count outcomes.

## 5. What We Learn and Recommended Next Step

What we learn from Design 1:

1. The quarterly publication DID pipeline now runs end to end and is reproducible through GitHub Actions.
2. The earlier coarse before/after publication signal does not appear as a strong quarterly pattern.
3. C03 and C05 give similar point estimates, which is reassuring for current control-definition sensitivity.
4. The count estimate is sensitive to high-output applications, so mean-count OLS should not be over-interpreted.
5. Current data support an exploratory ITT-like policy-exposure design, not a verified active-RAP-use design.

Suggested supervisor headline:

> We now have a working quarterly incumbent-project DID and event-study pipeline. The first results do not show a robust differential change in publication output after the RAP transition; the remaining identification concerns are the small/provisional control group, incomplete information on actual policy exposure, and publication timing.

Recommended next step:

1. Run **Design 2: monthly timing robustness** to check whether quarterly aggregation hides short-run timing patterns, pre-policy drift, or delayed separation.
2. Add compact balance/common-support diagnostics: project start quarter, project age, institution, pre-policy publication count, and pre-policy any-publication.
3. If comparability looks poor, then run a matched or weighted quarterly DID. Matching/weighting should be diagnostic-triggered rather than the immediate next default.
4. If results become sensitive to C03/C05 definitions or common-support restrictions, return to treatment/control measurement.
5. Keep DMCA as a separate auxiliary design because the application-notice linkage is sparse and not naturally suited to the same quarterly publication DID.

Later robustness, if the design becomes central to the paper, should include event-study confidence intervals, PPML as the main count-model robustness, and possibly Honest DiD-style sensitivity for borderline pretrends. Winsorized or trimmed outcomes should remain sensitivity checks rather than the primary result.

## Appendix: Full Control Sensitivity

| Control definition | Outcome | Q0 estimate | SE | p-value | Q1 estimate |
|---|---|---:|---:|---:|---:|
| C0 | Publication count | 0.0896 | 0.0862 | 0.299 | 0.1096 |
| C0 | Any publication | -0.0073 | 0.0179 | 0.685 | 0.0056 |
| C01 | Publication count | 0.0065 | 0.0280 | 0.816 | 0.0232 |
| C01 | Any publication | -0.0123 | 0.0132 | 0.349 | -0.0027 |
| C03 | Publication count | 0.0152 | 0.0248 | 0.539 | 0.0258 |
| C03 | Any publication | -0.0048 | 0.0122 | 0.697 | 0.0010 |
| C05 | Publication count | 0.0154 | 0.0246 | 0.532 | 0.0252 |
| C05 | Any publication | -0.0024 | 0.0124 | 0.848 | 0.0031 |
