# Project Entry2 Results Through 2026 Jan-Apr

Extended estimation window: 2019-01 through 2026-04. Breakpoint remains July 2024, with July 2024 `time_after_july2024 = 0` and April 2026 `time_after_july2024 = 21`.

## A. 2026 Jan-Apr Data Audit

| Month | All starts | High | Lower | High share |
| --- | ---: | ---: | ---: | ---: |
| 2026-01 | 145 | 34 | 111 | 0.2345 |
| 2026-02 | 119 | 18 | 101 | 0.1513 |
| 2026-03 | 141 | 32 | 109 | 0.2270 |
| 2026-04 | 63 | 11 | 52 | 0.1746 |

2026 Jan-Apr total recorded starts = 468. 2026 Jan-Apr High = 95. 2026 Jan-Apr Lower = 373. For every 2026 Jan-Apr month, `High + Lower = All`.

No 2026 Jan-Apr month has zero recorded starts.

## B. Test 1

Outcome: `high_sensitivity_count`. Specification: OLS with Newey-West HAC standard errors, lag(3), plus month-of-year fixed effects.

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 9.8826 | 1.8564 | 0.0000 | [6.2441, 13.5210] |
| Time | -0.0126 | 0.0179 | 0.4806 | [-0.0477, 0.0225] |
| PostJuly2024 | 1.5664 | 3.1766 | 0.6219 | [-4.6596, 7.7925] |
| TimeAfterJuly2024 | 0.7563 | 0.2448 | 0.0020 | [0.2765, 1.2361] |

| Quantity | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| PreSlope beta1 | -0.0126 | 0.0179 | 0.4806 | [-0.0477, 0.0225] |
| PostSlope beta1 + beta3 | 0.7437 | 0.2394 | 0.0019 | [0.2744, 1.2130] |

Linear-combination test for `H0: beta1 + beta3 = 0`: p = 0.0019.

## C. Test 2

Outcome: `high_sensitivity_share_all`. Calendar time is retained when total monthly starts are zero; the share outcome is missing for such months.

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 0.1933 | 0.0184 | 0.0000 | [0.1573, 0.2293] |
| Time | -0.0011 | 0.0004 | 0.0025 | [-0.0019, -0.0004] |
| PostJuly2024 | -0.0466 | 0.0273 | 0.0876 | [-0.1001, 0.0069] |
| TimeAfterJuly2024 | 0.0069 | 0.0016 | 0.0000 | [0.0037, 0.0100] |

| Quantity | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| PreSlope beta1 | -0.0011 | 0.0004 | 0.0025 | [-0.0019, -0.0004] |
| PostSlope beta1 + beta3 | 0.0057 | 0.0016 | 0.0004 | [0.0026, 0.0089] |
| SlopeChange beta3 | 0.0069 | 0.0016 | 0.0000 | [0.0037, 0.0100] |

Beta3 remains positive: yes. Beta3 remains significant: yes. Post slope remains positive: yes. Post slope is statistically positive: yes.

## D. Test 3

Test 3 asks whether the post-transition change in entry trajectory differs between the high-sensitivity and lower-sensitivity partitions. The conceptual model remains the High-vs-Lower stacked partition interaction with Lower omitted:

$$
\begin{aligned}
Y_{g,t} ={}& \beta_0 + \beta_1 Time_t + \beta_2 Post_t + \beta_3 TimeAfter_t \\
&+ \delta_0 High_g
+ \delta_1 High_g \times Time_t
+ \delta_2 High_g \times Post_t \\
&+ \delta_3 High_g \times TimeAfter_t
+ MonthFE
+ High_g \times MonthFE
+ \epsilon_{g,t}.
\end{aligned}
$$

Each group outcome is normalized as `100 * N_g,t / pre-transition monthly mean`. The pre-transition denominator is the same full pre-July-2024 mean used in the 2025-12 baseline.

Primary displayed Test 3 interaction coefficient table:

| Parameter | Term | HAC inference source | Estimate | SE | p-value | 95% CI |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| β0 | Intercept | Lower-series regression | 83.5582 | 14.8620 | 0.0000 | [54.4286, 112.6878] |
| β1 | Time | Lower-series regression | 0.7352 | 0.2513 | 0.0034 | [0.2428, 1.2277] |
| β2 | PostJuly2024 | Lower-series regression | 53.5475 | 56.0741 | 0.3396 | [-56.3578, 163.4528] |
| β3 | TimeAfterJuly2024 | Lower-series regression | 4.3385 | 4.7926 | 0.3653 | [-5.0550, 13.7320] |
| δ0 | High | High-minus-Lower difference regression | 41.3936 | 22.2423 | 0.0627 | [-2.2013, 84.9885] |
| δ1 | High × Time | High-minus-Lower difference regression | -0.8949 | 0.2569 | 0.0005 | [-1.3985, -0.3913] |
| δ2 | High × PostJuly2024 | High-minus-Lower difference regression | -33.7419 | 23.1931 | 0.1457 | [-79.2003, 11.7166] |
| δ3 | High × TimeAfterJuly2024 | High-minus-Lower difference regression | 5.2239 | 2.3572 | 0.0267 | [0.6037, 9.8441] |

Month FE = Yes. High × Month FE = Yes. Observations = 176 group-month observations. Calendar months = 88. HAC lag = 3.

Linear combinations / interpretation:

| Linear combination / interpretation | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Lower pre slope = β1 | 0.7352 | 0.2513 | 0.0034 | [0.2428, 1.2277] |
| Lower post slope = β1 + β3 | 5.0737 | 4.6943 | 0.2798 | [-4.1270, 14.2744] |
| High pre slope = β1 + δ1 | -0.1597 | 0.2264 | 0.4806 | [-0.6034, 0.2840] |
| High post slope = β1 + δ1 + β3 + δ3 | 9.4027 | 3.0274 | 0.0019 | [3.4691, 15.3364] |
| Lower slope change = β3 | 4.3385 | 4.7926 | 0.3653 | [-5.0550, 13.7320] |
| High slope change = β3 + δ3 | 9.5624 | 3.0949 | 0.0020 | [3.4963, 15.6285] |
| Differential slope change = δ3 | 5.2239 | 2.3572 | 0.0267 | [0.6037, 9.8441] |

Main hypothesis: \(H_0: \delta_3 = 0\). Current result: \(\delta_3 = 5.2238977\), SE = 2.3572440, p = 0.0266844, 95% CI [0.6036994, 9.8440960].

High trajectory strengthened significantly more than Lower.

The displayed interaction table is the stacked-model parameterization of the existing algebraically equivalent three-series Newey-West implementation. β coefficients come from the Lower series and δ coefficients from the High-minus-Lower series.

The Newey-West implementation remains the three-series equivalent: Lower index, High index, and High-minus-Lower index difference, all over the same 88 calendar months. Built-in Stata `newey` is not presented as if it were run on the 176-row stacked dataset with duplicate month values.

## E. Raw-Count Test 3 Robustness

ROBUSTNESS ONLY. This raw-count comparison asks whether the normalized result is purely created by pre-mean normalization. It is not the primary Test 3 because the High and Lower group sizes differ sharply.

| Quantity | Estimate | SE / p-value |
| --- | ---: | ---: |
| Lower pre slope | 0.3233 | 0.1105 / 0.0034 |
| Lower post slope | 2.2309 | 2.0640 / 0.2798 |
| Lower slope change | 1.9076 | 2.1073 / 0.3653 |
| High pre slope | -0.0126 | 0.0179 / 0.4806 |
| High post slope | 0.7437 | 0.2394 / 0.0019 |
| High slope change | 0.7563 | 0.2448 / 0.0020 |
| Differential immediate change \(\delta_2\) | -21.9782 | 21.7084 / 0.3113 |
| **Differential slope change \(\delta_3\)** | -1.1513 | 1.8873 / 0.5418 |

Raw-count robustness differential slope change: -1.1513 (SE 1.8873, p 0.5418, 95% CI [-4.8505, 2.5478]).

## F. Interpretation

Test 1 and Test 2 continue to ask whether high-sensitivity entry and share changed after July 2024. Test 3 continues to ask the stricter comparative question: did High strengthen more than the Lower complement after normalizing each group by its own pre-transition monthly mean? The extended normalized Test 3 result remains governed by `delta3`.

## G. Stata Status

Stata status: `STATA_NOT_AVAILABLE_ON_RUNNER`.
