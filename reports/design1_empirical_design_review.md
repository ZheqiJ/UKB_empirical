# Design 1 Empirical Design Review

This report records implementation-generated empirical diagnostics in the
same PASS / WARNING / FAIL structure used by the independent review agent.

## Checkpoint Summary

| checkpoint | verdict | basis |
| --- | --- | --- |
| R0 Design Review | WARNING / PROCEED | Quarterly incumbent DID is worth running, but controls are provisional and active-project exposure is not directly observed. |
| R1 Panel/Data Construction | PASS | Exact project starts, publication-date audit, no pre-start panel rows, and no incomplete 2026Q3 main-period rows. |
| R2 Identification/Pretrend | WARNING | App FE, calendar-quarter FE, age-adjusted Q1, transition robustness, and joint pretrend tests are produced. |
| R3 Result/Robustness | WARNING | Control definitions, transition timing, first partial quarter, outlier, and productivity-stratum checks are reported. |

## 1. Target Estimand

**PASS.** The target is an incumbent-project ITT-like DID: differential
publication output after the RAP transition for provisional NEWLY_RAP_BOUND
applications relative to provisional already-RAP-bound control candidates.

## 2. Why Quarterly DID Is Tried First

**PASS.** The quarterly panel preserves timing, avoids pre-start zeroes,
and permits pretrend and lag diagnostics while keeping the panel less noisy
than monthly data.

## 3. Unit Of Observation And Risk Set

**PASS.** Unit is application-quarter for Design 1.
Rows are generated only for at-risk periods after project start; first
partial quarters are flagged. Monthly robustness is not run in this
sequential checkpoint.

## 4. Treatment/Control Definitions

**WARNING.** Treatment/control status remains provisional. C0 is high
precision but very small; C01/C03/C05 improve precision but mix evidence
quality and include overlap labels from original Stage 3 classes.

## 5. Data Sufficiency

**PASS.** Exact date coverage and missing starts
are reported in the risk-set diagnostics. Year-only dates are not converted
to January/Q1 for panel regressions.

## 6. Missing Data

**WARNING.** Public data lack project active/closed status, actual access
dates, RAP migration dates, and RAP usage logs. This limits interpretation
to policy-exposure intent, not verified migration/use.

## 7. Pre-Trend Assessment

**WARNING.** Joint pretrend tests are reported for
event-time -8 through -2, with 2024Q2 omitted as reference. A WARNING means
at least one outcome/control definition rejects at conventional levels or
the test is otherwise fragile.

## 8. Project-Age/Lifecycle Assessment

**PASS.** Q1 adds project-age-bin fixed effects. Material
movement from Q0 to Q1 should be treated as lifecycle confounding.

## 9. Inference Assessment

**WARNING.** Application-clustered SE are primary and institution-clustered
SE are reported for Q0 robustness. Some control cells remain small, especially
C0.

## 10. Control-Definition Robustness

**PASS.** C01/C03/C05 are compared without
selecting based on significance. Sign instability implies measurement is
the bottleneck.

## 11. Publication Lag / Transition Timing

**WARNING.** 2024Q3 is a transition quarter and publication output is lagged.
The report compares treating 2024Q3 as post with dropping it and starting
stable post in 2024Q4.

## 12. Alternative Designs

**WARNING.** If pretrends or lifecycle diagnostics are weak, stronger
alternatives are balanced-incumbent DID, start-cohort matched/weighted DID,
and project-entry cohort designs. Common support is limited because controls
are small.

## 13. Decision Tree

- CASE 1: If pretrends are acceptable and coefficients are stable across
  C01/C03/C05, quarterly incumbent DID remains the preferred main design.
- CASE 2: If full risk-set pretrends are poor but balanced incumbents improve
  them, use balanced-incumbent DID as stronger and keep full risk set secondary.
- CASE 3: If pretrends remain poor, do not make causal claims; pursue
  start-cohort matching/weighting.
- CASE 4: If Q0/Q1 differ materially, lifecycle is a major confounder.
- CASE 5: If effects appear only in 2024Q3, treat timing as suspicious.
- CASE 6: If effects emerge later, emphasize lagged publication production.
- CASE 7: If count and any-publication diverge, decompose intensive versus
  extensive margins using pre-policy productivity strata only.
- CASE 8: If top 1% projects drive count effects, weaken average-effect
  interpretation and use outlier/count robustness.
- CASE 9: If signs change across C01/C03/C05, return to Stage 3 measurement.

## 14. Final Reviewer Verdict

**WARNING.** The current outputs can be interpreted as
exploratory ITT-like incumbent-project publication designs. They cannot by
themselves establish a causal RAP effect unless pretrend, lifecycle, timing,
and control-definition diagnostics are satisfactory. The next data priorities
are project active/closed status, actual access dates, RAP migration dates,
and RAP usage logs.
