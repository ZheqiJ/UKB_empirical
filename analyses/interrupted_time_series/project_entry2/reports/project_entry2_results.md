# Project Entry2 Results

## A. What Is High Sensitivity?

Primary high sensitivity is `HIGH_SENSITIVITY`: explicit WES/WGS or sequence-product evidence, direct application-field links to `s3` fields, or high-precision application text derived from the 199 Schema 1 `s3` fields. It is a proxy for higher-granularity or more sensitive data use, not observed leakage risk.

Project counts:

| Definition | N |
| --- | ---: |
| HIGH_SENSITIVITY | 1,048 |
| LOWER_SENSITIVITY_COMPARISON | 5,887 |
| hs_wes_wgs_sequence | 459 |
| hs_s3_direct | 2 |
| hs_s3_text | 621 |
| LOW_STRICT | 1,147 |

Evidence-channel overlap and net additions:

| Channel | N | Overlap with previous channels | Net additions | Pre N | Post N |
| --- | ---: | ---: | ---: | ---: | ---: |
| WES/WGS_SEQUENCE | 459 | 0 | 459 | 313 | 146 |
| DIRECT_S3_FIELD_LINK | 2 | 0 | 2 | 2 | 0 |
| S3_DERIVED_APPLICATION_TEXT | 621 | 34 | 587 | 382 | 239 |

Pre/post counts use the exact policy date 2024-07-05 at the project level: HIGH_SENSITIVITY is 679 pre-July-2024 and 369 post-July-2024; LOWER_SENSITIVITY_COMPARISON is 3653 pre-July-2024 and 2234 post-July-2024.

The lower comparison is the exhaustive complement, meaning no identified high evidence under the observable proxy, not proof that every complement project is low-risk.

The full audit files are `classification_counts.csv`, `classification_overlap.csv`, `s3_field_dictionary.csv`, `s3_application_keyword_dictionary.csv`, `s3_text_audit_examples.csv`, `field_tier_distribution.csv`, and `application_field_tier_links.csv`.

## B. Test 1 - High-Sensitivity Entry Count

Question: did the absolute number of high-sensitivity project starts change around/after July 2024?

Primary HIGH_SENSITIVITY:

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 8.4939 | 1.5108 | 0.0000 | [5.5327, 11.4552] |
| Time | -0.0134 | 0.0181 | 0.4590 | [-0.0489, 0.0221] |
| PostJuly2024 | 0.8439 | 3.6627 | 0.8178 | [-6.3350, 8.0228] |
| TimeAfterJuly2024 | 0.8615 | 0.3673 | 0.0190 | [0.1417, 1.5814] |

Key terms: Time=-0.0134 (SE 0.0181); PostJuly2024=0.8439 (SE 3.6627); TimeAfterJuly2024=0.8615 (SE 0.3673).

## C. Test 2 - High-Sensitivity Share

Question: did the composition of project entry shift toward high-sensitivity projects?

Primary denominator is all recorded project starts because HIGH and LOWER are exhaustive. If `N_All,t=0`, the share is missing but calendar time is preserved.

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 0.1848 | 0.0177 | 0.0000 | [0.1502, 0.2195] |
| Time | -0.0011 | 0.0004 | 0.0022 | [-0.0019, -0.0004] |
| PostJuly2024 | -0.0372 | 0.0336 | 0.2682 | [-0.1031, 0.0287] |
| TimeAfterJuly2024 | 0.0054 | 0.0025 | 0.0335 | [0.0004, 0.0104] |

Key terms: Time=-0.0011 (SE 0.0004); PostJuly2024=-0.0372 (SE 0.0336); TimeAfterJuly2024=0.0054 (SE 0.0025).

## D. Test 3 - High Vs Lower Partition Interaction

**Test 3 asks whether the post-transition change in entry trajectory differs between the high-sensitivity and lower-sensitivity partitions.**

The 6,935 projects are partitioned into `HIGH_SENSITIVITY` and the exhaustive `LOWER_SENSITIVITY_COMPARISON`. For each group, monthly entry is normalized to that group's own pre-transition monthly mean:

$$
Y_{H,t} = 100 N_{H,t} / \overline{N}_{H,pre},
\quad
Y_{L,t} = 100 N_{L,t} / \overline{N}_{L,pre}.
$$

The conceptual model is the stacked partition interaction model, with Lower as the omitted group:

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

Coefficient translation:

Lower-sensitivity group:

$$
PreSlope_L = \beta_1, \quad
PostSlope_L = \beta_1 + \beta_3, \quad
SlopeChange_L = \beta_3.
$$

High-sensitivity group:

$$
PreSlope_H = \beta_1 + \delta_1, \quad
PostSlope_H = \beta_1 + \delta_1 + \beta_3 + \delta_3, \quad
SlopeChange_H = \beta_3 + \delta_3.
$$

Therefore, the primary Test 3 coefficient is:

$$
\delta_3 = SlopeChange_H - SlopeChange_L.
$$

\(\delta_3 > 0\) means that the post-transition trajectory strengthened more for high-sensitivity projects than for lower-sensitivity projects, relative to each group's own pre-transition trajectory. \(\delta_2\) is the High-vs-Lower differential immediate level change at July 2024. The main hypothesis is \(H_0: \delta_3 = 0\); the secondary hypothesis is \(H_0: \delta_2 = 0\).

For Newey-West inference, the pipeline does not run built-in Stata `newey` on the 168-row stacked transparency file because that file has two observations per calendar month. Instead it runs three monthly ITS regressions on the same 84 months and design matrix: Lower index, High index, and \(D_t = Y_{H,t} - Y_{L,t}\). Because the High and Lower regressions use the same design matrix, the difference-series coefficients equal the High-minus-Lower interaction coefficients: \(\delta_j = \beta_{jH} - \beta_{jL}\). The difference regression is therefore the Newey-West implementation of the interaction comparison, and it supplies the formal standard error for \(\delta_3\) while incorporating contemporaneous covariance between the High and Lower series.

| Quantity | Estimate | SE / p-value |
| --- | ---: | ---: |
| Lower pre slope | 0.7500 | 0.2551 / 0.0033 |
| Lower post slope | 12.3843 | 5.2126 / 0.0175 |
| Lower slope change | 11.6342 | 5.3043 / 0.0283 |
| High pre slope | -0.1694 | 0.2288 / 0.4590 |
| High post slope | 10.7236 | 4.5881 / 0.0194 |
| High slope change | 10.8930 | 4.6434 / 0.0190 |
| Differential immediate change \(\delta_2\) | 1.4773 | 17.3884 / 0.9323 |
| **Differential slope change \(\delta_3\)** | -0.7412 | 1.6153 / 0.6463 |

No statistically detectable differential strengthening of High relative to Lower.

Test 3 model outputs:

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 86.6997 | 15.3885 | 0.0000 | [56.5383, 116.8611] |
| Time | 0.7500 | 0.2551 | 0.0033 | [0.2500, 1.2500] |
| PostJuly2024 | 9.1929 | 53.7402 | 0.8642 | [-96.1379, 114.5236] |
| TimeAfterJuly2024 | 11.6342 | 5.3043 | 0.0283 | [1.2378, 22.0306] |

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 107.3947 | 19.1026 | 0.0000 | [69.9536, 144.8357] |
| Time | -0.1694 | 0.2288 | 0.4590 | [-0.6179, 0.2790] |
| PostJuly2024 | 10.6701 | 46.3101 | 0.8178 | [-80.0977, 101.4379] |
| TimeAfterJuly2024 | 10.8930 | 4.6434 | 0.0190 | [1.7919, 19.9941] |

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 20.6950 | 15.2614 | 0.1751 | [-9.2174, 50.6073] |
| Time | -0.9195 | 0.2437 | 0.0002 | [-1.3972, -0.4418] |
| PostJuly2024 | 1.4773 | 17.3884 | 0.9323 | [-32.6039, 35.5585] |
| TimeAfterJuly2024 | -0.7412 | 1.6153 | 0.6463 | [-3.9071, 2.4247] |

The stacked transparency dataset is `data/project_entry2_test3_stacked.csv`. It has 168 group-month rows and is not used for the built-in Stata `newey` call.

Zero-month preservation check: PASS. Test 3 Lower index, Test 3 High index, and Test 3 High-minus-Lower difference each retain 84 monthly observations.

## E. Measurement Limitations

Start date is not application submission, approval, or first RAP access. Current Application x Field links may reflect later amendments. Field tier is a sensitivity/granularity proxy, not observed leakage risk. The design is descriptive ITS/comparative ITS, not causal DID.

## Output Files

- `data/project_high_sensitivity_classification.csv`
- `data/application_field_tier_links.csv`
- `data/field_tier_distribution.csv`
- `data/classification_counts.csv`
- `data/classification_overlap.csv`
- `data/project_entry2_monthly.csv`
- `data/project_entry2_regression_results.csv`
- `data/project_entry2_test3_stacked.csv`
- `data/project_entry2_test3_partition_results.csv`
- `data/stata_python_replication_check.csv`
- `figures/figure_test1_high_sensitivity_entry.svg`
- `figures/figure_test2_high_sensitivity_share.svg`
- `figures/figure_test3_high_vs_low_raw.svg`
- `figures/figure_test3_high_vs_low_indexed.svg`
- `reports/project_entry2_stata_style_regression_results.txt`
- `reports/project_entry2_stata_full.log`
- `reports/project_entry2_stata_regression_table.csv`

Stata status: `STATA_NOT_AVAILABLE_ON_RUNNER`.
