# Design 1 Memo: Quarterly Incumbent DID for Publication Outcomes

## 1. Question and Design

We now have a working quarterly incumbent-project DID and event-study pipeline for the 5 July 2024 UK Biobank RAP transition. The question is whether publication output changed differentially after the policy for projects provisionally classified as newly RAP-bound, relative to already-RAP-bound or already-RAP-bound-like incumbent controls.

This is an **incumbent-project design**, not a project-entry design. Using the fixed universe of 6,935 matched UK Biobank projects, we construct an application-quarter post-entry risk-set panel from 2022Q3 to 2026Q2. The panel begins only after each recorded project start date, so pre-start quarters are not coded as zero-output observations.

Control definitions are cumulative sensitivity checks:

| Definition | Incumbent treated | Incumbent controls | Interpretation |
|---|---:|---:|---|
| C03 | 3,325 | 130 | Narrower already-RAP-bound-like controls |
| C05 | 3,324 | 131 | Previous broad working specification |
| C06 | 3,191 | 297 | New broadest specification including C6 candidates |

The baseline (Q0) specification is:

```text
Y_iq = beta * Treated_i * Post_q + project FE_i + quarter FE_q + error_iq
```

where `Y_iq` is either quarterly publication count or an indicator for any publication. Standard errors are clustered by application. A lifecycle-adjusted diagnostic specification adds project-age-bin fixed effects.

(Q1)Project-age-adjusted DID:

```text
Y_iq = beta * Treated_i * Post_q + project FE_i + quarter FE_q + project-age FE_iq + error_iq
```

## 2. Data Checks

Data construction passes the main checks:

| Item | Value |
|---|---:|
| Fixed working universe | 6,935 projects |
| Application-quarter rows | 75,973 |
| Main window | 2022Q3-2026Q2 |
| Publication events in complete quarter panel | 12,400 |

## 3. Main Results

The C06 addition is informative but should be presented as a broad sensitivity check, not as a mechanically better control group. It nearly doubles the incumbent control count relative to C05, but it also pulls in many overlap/unclear projects and changes baseline comparability.



Main estimates:

| Specification | Publication count | Any publication |
|---|---:|---:|
| C05 Q0: app FE + quarter FE | 0.015 (0.025), p = 0.532 | -0.002 (0.012), p = 0.848 |
| C05 Q1: plus project-age-bin FE | 0.025 (0.024), p = 0.296 | 0.003 (0.012), p = 0.796 |
| C06 Q0: app FE + quarter FE | -0.021 (0.024), p = 0.379 | -0.016 (0.012), p = 0.187 |
| C06 Q1: plus project-age-bin FE | -0.034 (0.023), p = 0.148 | -0.024 (0.012), p = 0.034 |
| C03 Q0: app FE + quarter FE | 0.015 (0.025), p = 0.539 | -0.005 (0.012), p = 0.697 |

Economic magnitude should be interpreted relative to pre-policy quarterly baselines. In C06, treated projects averaged 0.103 publications per pre-policy project-quarter and 7.38% had any publication. C06 controls averaged 0.347 publications and 20.0% had any publication. This large baseline gap is a warning that C06 improves sample size but may worsen comparability.

Bottom line: adding C06 does not create a clean strong result. It produces more negative point estimates, including one age-adjusted any-publication estimate with p = 0.034, but the result is not stable across timing choices and the broader control group is compositionally less clean. The safest supervisor-facing conclusion remains that the quarterly pipeline runs, but publication effects are exploratory and not yet causally persuasive.

## 4. Identification Diagnostics

The implementation/data checkpoint passes, but identification remains a warning.

| Definition | Count pretrend p-value | Any-publication pretrend p-value | Interpretation |
|---|---:|---:|---|
| C0 | 0.0236 | 0.0327 | Joint pretrend rejected |
| C01 | 0.0777 | 0.0390 | Mixed across outcomes |
| C03 | 0.0571 | 0.0930 | Not rejected at 5%, but borderline |
| C05 | 0.0785 | 0.2011 | Not rejected; count test remains borderline |
| C06 | 0.0696 | 0.1561 | Not rejected; broader but less clean controls |

Failure to reject a joint pretrend test is not proof of parallel trends. C06 is useful because it shows what happens when we expand the control pool aggressively, but it also reveals that the expanded controls have much higher pre-policy publication intensity. That makes C06 a diagnostic and robustness specification, not a final preferred treatment/control definition.

## 5. What We Learn and Recommended Next Step

What we learn from Design 1 after adding C06:

1. The quarterly publication DID pipeline now runs end to end with C0, C01, C03, C05, and C06 definitions.
2. C06 increases the incumbent control group from 131 to 297, reducing the most obvious sample-size criticism.
3. C06 changes the sign of the point estimates, which means control-definition measurement remains a first-order issue.
4. The C06 controls are much more publication-intensive before the policy, so the broader control group may not be more credible despite being larger.
5. The overall evidence still does not support a strong causal claim about publication output.


Recommended next step:

1. Add compact balance/common-support diagnostics for C05 versus C06: project start quarter, project age, institution, pre-policy publication count, and pre-policy any-publication.
2. Run Design 2 monthly timing robustness to see whether C06's negative estimates are driven by a narrow timing window.
3. If C06 remains important, run a matched or weighted quarterly DID using pre-policy publication and start-timing covariates.
4. Keep DMCA as a separate auxiliary design because the application-notice linkage is sparse and not naturally suited to the same quarterly publication DID.

## Appendix: Full Control Sensitivity

| Control definition | Outcome | Q0 estimate | SE | p-value | Q1 estimate | Pretrend p-value |
|---|---|---:|---:|---:|---:|---:|
| C0 | Publication count | 0.0896 | 0.0862 | 0.299 | 0.1096 | 0.0236 |
| C0 | Any publication | -0.0073 | 0.0179 | 0.685 | 0.0056 | 0.0327 |
| C01 | Publication count | 0.0065 | 0.0280 | 0.816 | 0.0232 | 0.0777 |
| C01 | Any publication | -0.0123 | 0.0132 | 0.349 | -0.0027 | 0.0390 |
| C03 | Publication count | 0.0152 | 0.0248 | 0.539 | 0.0258 | 0.0571 |
| C03 | Any publication | -0.0048 | 0.0122 | 0.697 | 0.0010 | 0.0930 |
| C05 | Publication count | 0.0154 | 0.0246 | 0.532 | 0.0252 | 0.0785 |
| C05 | Any publication | -0.0024 | 0.0124 | 0.848 | 0.0031 | 0.2011 |
| C06 | Publication count | -0.0212 | 0.0241 | 0.379 | -0.0336 | 0.0696 |
| C06 | Any publication | -0.0160 | 0.0121 | 0.187 | -0.0245 | 0.1561 |
