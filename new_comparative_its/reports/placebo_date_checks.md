# Placebo Intervention-Date Checks

This supplementary exercise checks the stability of the comparative ITS around artificial earlier intervention dates. It is separate from the main July 2024 analysis and does not alter the main estimates or classification.

## Model and source data

For each candidate date tau, the model is:

`D_t = a + b*time_t + level*1(t >= tau) + slope*max(t - tau, 0) + month-of-year FE + error_t`,

where `D_t` is the raw monthly treatment-minus-control difference. The pre-period slope is unrestricted. The coefficients of interest are the artificial level and slope changes. Inference uses the same Bartlett Newey-West HAC lag 3 convention as the repository, without a finite-sample scaling factor. P-values use large-sample normal approximations and the joint break test uses a chi-square(2) approximation.

The source data are the saved `new_comparative_its/data/monthly_strict.csv` and `monthly_broad.csv` files. The primary placebo exercise uses only October 2021 through June 2024 and tests October 2022 through July 2023. The companion exercise uses identical 18 pre-date and 12 post-date month windows.

## Strict control

Control definition: strict already-RAP-bound control proxy. The candidate grid is every month from October 2022 through July 2023. All fits use the raw monthly difference `treatment starts - control starts`, a linear time trend, artificial level and slope breaks, month-of-year fixed effects, and Bartlett Newey-West HAC lag 3 without finite-sample scaling.

### Primary artificial-date exercise

Only October 2021 through June 2024 is used. This is 33 pre-transition calendar months. The 15-coefficient model leaves 18 residual degrees of freedom. The 10 candidate dates each have at least 12 observations before and 12 observations on or after the candidate date.

| Artificial date | Pre n | Post n | Level | Level p | Slope | Slope p | Slope Holm p | Joint p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 12 | 21 | 1.101738 | 0.215008 | -0.257669 | 0.006803 | 0.006803 | 0.000020 |
| 2022-11 | 13 | 20 | -0.211547 | 0.820169 | -0.334035 | 0.000003 | 0.000014 | 0.000008 |
| 2022-12 | 14 | 19 | 0.073685 | 0.915745 | -0.311767 | 0.000004 | 0.000017 | 0.000024 |
| 2023-01 | 15 | 18 | 0.640819 | 0.192722 | -0.301611 | 0.000008 | 0.000023 | <0.000001 |
| 2023-02 | 16 | 17 | 0.796711 | 0.151293 | -0.315856 | <0.000001 | <0.000001 | <0.000001 |
| 2023-03 | 17 | 16 | 0.805926 | 0.279789 | -0.337782 | <0.000001 | <0.000001 | <0.000001 |
| 2023-04 | 18 | 15 | -0.614888 | 0.302485 | -0.330312 | <0.000001 | <0.000001 | <0.000001 |
| 2023-05 | 19 | 14 | -0.992906 | 0.203735 | -0.313280 | <0.000001 | <0.000001 | <0.000001 |
| 2023-06 | 20 | 13 | -0.573983 | 0.359796 | -0.328191 | <0.000001 | <0.000001 | <0.000001 |
| 2023-07 | 21 | 12 | -0.761759 | 0.372354 | -0.322086 | 0.000263 | 0.000526 | <0.000001 |

Artificial slope changes range from -0.338 to -0.258. 10 of 10 have two-sided slope p < .05, 10 remain below .05 after within-panel Holm correction, and 0 have a positive and individually significant artificial slope. All 10 reject the joint no-level/no-slope-break hypothesis at the nominal 5% level.

### Same-window companion check

The matched-window exercise uses 18 pre-date months and 12 post-date months. The four earlier dates are April through July 2023. The actual July 2024 estimate is also re-estimated over January 2023 through June 2025 with the same 18/12 window.

| Artificial date | Level | Level p | Slope | Slope p | Slope Holm p | Joint p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-04 | -0.386525 | 0.555249 | -0.361702 | 0.000008 | 0.000030 | 0.000017 |
| 2023-05 | -2.054778 | 0.037072 | -0.132139 | 0.195959 | 0.195959 | 0.003618 |
| 2023-06 | -0.323722 | 0.714663 | -0.273236 | 0.001997 | 0.003994 | 0.001114 |
| 2023-07 | -0.771323 | 0.378980 | -0.296753 | 0.000741 | 0.002223 | 0.000001 |

In the matched-window exercise, 3 of 4 artificial slope changes have p < .05 and 3 remain below .05 after within-panel Holm correction. All 4 joint tests reject at the nominal 5% level.

### Actual July 2024 comparison

| Window | Pre n | Post n | Level | Level p | Slope change | Slope SE | Slope p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original full window | 33 | 22 | -4.663656 | 0.003026 | 0.231333 | 0.100037 | 0.020751 |
| Matched 18/12 window | 18 | 12 | -5.276222 | 0.004119 | 0.735722 | 0.228857 | 0.001305 |

### Interpretation

These artificial-date fits are overlapping diagnostics on the same short pre-transition series, not independent historical events and not a randomization test. Their frequent negative artificial slope breaks suggest that the pre-period treatment-control gap may contain curvature or earlier changes that are not captured by one stable linear differential trend. The negative signs do not show that arbitrary earlier dates reproduce the actual positive July 2024 acceleration.

The actual July 2024 full-window model shows a negative relative level change followed by a positive relative slope change. The matched-window estimates are larger, which demonstrates that magnitude and inference are sensitive to the time window. The current evidence supports a descriptive comparative-ITS interpretation only. It does not establish a causal DID effect, observed RAP migration, or that any particular artificial date is free of other UKB data releases or access changes.

The 33-month history and seasonal controls make all p-values approximate. Holm correction is within each control-definition panel and does not fix small-sample calibration or model misspecification. Institutional chronology should be reviewed before treating any artificial date as a substantive no-event control.

## Broad control

Control definition: broad sequence control proxy. The candidate grid is every month from October 2022 through July 2023. All fits use the raw monthly difference `treatment starts - control starts`, a linear time trend, artificial level and slope breaks, month-of-year fixed effects, and Bartlett Newey-West HAC lag 3 without finite-sample scaling.

### Primary artificial-date exercise

Only October 2021 through June 2024 is used. This is 33 pre-transition calendar months. The 15-coefficient model leaves 18 residual degrees of freedom. The 10 candidate dates each have at least 12 observations before and 12 observations on or after the candidate date.

| Artificial date | Pre n | Post n | Level | Level p | Slope | Slope p | Slope Holm p | Joint p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 12 | 21 | 1.880879 | 0.022760 | -0.165644 | 0.089746 | 0.089746 | 0.000225 |
| 2022-11 | 13 | 20 | 0.289154 | 0.766176 | -0.279336 | 0.000375 | 0.000751 | 0.000843 |
| 2022-12 | 14 | 19 | 0.451665 | 0.576222 | -0.274309 | 0.000249 | 0.000747 | 0.001022 |
| 2023-01 | 15 | 18 | 0.951997 | 0.052957 | -0.274421 | 0.000183 | 0.000732 | 0.000006 |
| 2023-02 | 16 | 17 | 1.429854 | 0.011342 | -0.295520 | 0.000002 | 0.000012 | <0.000001 |
| 2023-03 | 17 | 16 | 1.235780 | 0.090587 | -0.329361 | <0.000001 | <0.000001 | <0.000001 |
| 2023-04 | 18 | 15 | 0.189997 | 0.743764 | -0.340886 | <0.000001 | <0.000001 | <0.000001 |
| 2023-05 | 19 | 14 | -0.718218 | 0.431134 | -0.323496 | <0.000001 | <0.000001 | <0.000001 |
| 2023-06 | 20 | 13 | -0.248597 | 0.698538 | -0.349229 | <0.000001 | <0.000001 | <0.000001 |
| 2023-07 | 21 | 12 | -0.307771 | 0.710533 | -0.365031 | 0.000013 | 0.000066 | <0.000001 |

Artificial slope changes range from -0.365 to -0.166. 9 of 10 have two-sided slope p < .05, 9 remain below .05 after within-panel Holm correction, and 0 have a positive and individually significant artificial slope. All 10 reject the joint no-level/no-slope-break hypothesis at the nominal 5% level.

### Same-window companion check

The matched-window exercise uses 18 pre-date months and 12 post-date months. The four earlier dates are April through July 2023. The actual July 2024 estimate is also re-estimated over January 2023 through June 2025 with the same 18/12 window.

| Artificial date | Level | Level p | Slope | Slope p | Slope Holm p | Joint p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-04 | 0.730356 | 0.319464 | -0.422172 | 0.000003 | 0.000013 | 0.000012 |
| 2023-05 | -1.724151 | 0.152429 | -0.152296 | 0.191752 | 0.191752 | 0.029595 |
| 2023-06 | 0.060657 | 0.948525 | -0.306831 | 0.000616 | 0.001231 | 0.001285 |
| 2023-07 | -0.333193 | 0.697810 | -0.343785 | 0.000032 | 0.000097 | 0.000000 |

In the matched-window exercise, 3 of 4 artificial slope changes have p < .05 and 3 remain below .05 after within-panel Holm correction. All 4 joint tests reject at the nominal 5% level.

### Actual July 2024 comparison

| Window | Pre n | Post n | Level | Level p | Slope change | Slope SE | Slope p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original full window | 33 | 22 | -4.545463 | 0.004958 | 0.162621 | 0.096290 | 0.091243 |
| Matched 18/12 window | 18 | 12 | -5.265071 | 0.005168 | 0.680851 | 0.226395 | 0.002635 |

### Interpretation

These artificial-date fits are overlapping diagnostics on the same short pre-transition series, not independent historical events and not a randomization test. Their frequent negative artificial slope breaks suggest that the pre-period treatment-control gap may contain curvature or earlier changes that are not captured by one stable linear differential trend. The negative signs do not show that arbitrary earlier dates reproduce the actual positive July 2024 acceleration.

The actual July 2024 full-window model shows a negative relative level change followed by a positive relative slope change. The matched-window estimates are larger, which demonstrates that magnitude and inference are sensitive to the time window. The current evidence supports a descriptive comparative-ITS interpretation only. It does not establish a causal DID effect, observed RAP migration, or that any particular artificial date is free of other UKB data releases or access changes.

The 33-month history and seasonal controls make all p-values approximate. Holm correction is within each control-definition panel and does not fix small-sample calibration or model misspecification. Institutional chronology should be reviewed before treating any artificial date as a substantive no-event control.
