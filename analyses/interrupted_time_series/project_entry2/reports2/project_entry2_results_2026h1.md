# Project Entry2 Results Through 2026 H1

Extended estimation window: 2019-01 through 2026-06. Breakpoint remains July 2024, with July 2024 `time_after_july2024 = 0` and June 2026 `time_after_july2024 = 23`.

## A. 2026 H1 Data Audit

| Month | All starts | High | Lower | High share |
| --- | ---: | ---: | ---: | ---: |
| 2026-01 | 145 | 34 | 111 | 0.2345 |
| 2026-02 | 119 | 18 | 101 | 0.1513 |
| 2026-03 | 141 | 32 | 109 | 0.2270 |
| 2026-04 | 63 | 11 | 52 | 0.1746 |
| 2026-05 | 0 | 0 | 0 |  |
| 2026-06 | 0 | 0 | 0 |  |

2026 Jan-Jun total recorded starts = 468. 2026 Jan-Jun High = 95. 2026 Jan-Jun Lower = 373. For every 2026 H1 month, `High + Lower = All`.

Zero-start months in 2026 H1: 2026-05, 2026-06. They are retained.

## B. Test 1

Outcome: `high_sensitivity_count`. Specification: OLS with Newey-West HAC standard errors, lag(3), plus month-of-year fixed effects.

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 10.4153 | 2.1729 | 0.0000 | [6.1564, 14.6743] |
| Time | -0.0103 | 0.0194 | 0.5948 | [-0.0483, 0.0277] |
| PostJuly2024 | 4.7240 | 4.3758 | 0.2803 | [-3.8526, 13.3007] |
| TimeAfterJuly2024 | 0.2823 | 0.3910 | 0.4703 | [-0.4841, 1.0487] |

| Quantity | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| PreSlope beta1 | -0.0103 | 0.0194 | 0.5948 | [-0.0483, 0.0277] |
| PostSlope beta1 + beta3 | 0.2720 | 0.3874 | 0.4827 | [-0.4874, 1.0314] |

Linear-combination test for `H0: beta1 + beta3 = 0`: p = 0.4827.

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

| Quantity | Estimate | SE / p-value |
| --- | ---: | ---: |
| Lower pre slope | 0.7606 | 0.2533 / 0.0027 |
| Lower post slope | -0.1808 | 5.4798 / 0.9737 |
| Lower slope change | -0.9414 | 5.5631 / 0.8656 |
| High pre slope | -0.1303 | 0.2450 / 0.5948 |
| High post slope | 3.4389 | 4.8986 / 0.4827 |
| High slope change | 3.5692 | 4.9438 / 0.4703 |
| Differential immediate change \(\delta_2\) | -28.9489 | 20.3442 / 0.1547 |
| **Differential slope change \(\delta_3\)** | 4.5106 | 1.8634 / 0.0155 |

High trajectory strengthened significantly more than Lower.

The Newey-West implementation remains the three-series equivalent: Lower index, High index, and High-minus-Lower index difference, all over the same 90 calendar months.

## E. Raw-Count Test 3 Robustness

ROBUSTNESS ONLY. This raw-count comparison asks whether the normalized result is purely created by pre-mean normalization. It is not the primary Test 3 because the High and Lower group sizes differ sharply.

| Quantity | Estimate | SE / p-value |
| --- | ---: | ---: |
| Lower pre slope | 0.3344 | 0.1114 / 0.0027 |
| Lower post slope | -0.0795 | 2.4095 / 0.9737 |
| Lower slope change | -0.4139 | 2.4461 / 0.8656 |
| High pre slope | -0.0103 | 0.0194 / 0.5948 |
| High post slope | 0.2720 | 0.3874 / 0.4827 |
| High slope change | 0.2823 | 0.3910 / 0.4703 |
| Differential immediate change \(\delta_2\) | -34.2673 | 25.3254 / 0.1760 |
| **Differential slope change \(\delta_3\)** | 0.6962 | 2.0810 / 0.7380 |

Raw-count robustness differential slope change: 0.6962 (SE 2.0810, p 0.7380, 95% CI [-3.3826, 4.7750]).

## F. Interpretation

Test 1 and Test 2 continue to ask whether high-sensitivity entry and share changed after July 2024. Test 3 continues to ask the stricter comparative question: did High strengthen more than the Lower complement after normalizing each group by its own pre-transition monthly mean? The extended normalized Test 3 result remains governed by `delta3`.

## G. Stata Status

Stata status: `STATA_NOT_AVAILABLE_ON_RUNNER`.
