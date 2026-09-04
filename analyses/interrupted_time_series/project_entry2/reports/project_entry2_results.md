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

## D. Test 3 - Indexed High Vs Lower Difference

Question: was the post-transition trajectory stronger for high-sensitivity than for low-sensitivity project types?

Primary formal test: `D_t = Index_H,t - Index_L,t`, where both indexes use the full pre-transition monthly mean as 100.

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 20.6950 | 15.2614 | 0.1751 | [-9.2174, 50.6073] |
| Time | -0.9195 | 0.2437 | 0.0002 | [-1.3972, -0.4418] |
| PostJuly2024 | 1.4773 | 17.3884 | 0.9323 | [-32.6039, 35.5585] |
| TimeAfterJuly2024 | -0.7412 | 1.6153 | 0.6463 | [-3.9071, 2.4247] |

Difference key terms: Time=-0.9195 (SE 0.2437); PostJuly2024=1.4773 (SE 17.3884); TimeAfterJuly2024=-0.7412 (SE 1.6153).

Raw High component: Time=-0.0134 (SE 0.0181); PostJuly2024=0.8439 (SE 3.6627); TimeAfterJuly2024=0.8615 (SE 0.3673).

Raw Lower component: Time=0.3298 (SE 0.1122); PostJuly2024=4.0421 (SE 23.6294); TimeAfterJuly2024=5.1155 (SE 2.3323).

The indexed figure uses the full pre-transition mean. `index_high_2023_mean` and `index_lower_2023_mean` remain in the monthly CSV as a visual check.

Zero-month preservation check: PASS. Test 1, Test 3 High count, and Test 3 Lower count each retain 84 monthly observations.

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
- `data/stata_python_replication_check.csv`
- `figures/figure_test1_high_sensitivity_entry.svg`
- `figures/figure_test2_high_sensitivity_share.svg`
- `figures/figure_test3_high_vs_low_raw.svg`
- `figures/figure_test3_high_vs_low_indexed.svg`
- `reports/project_entry2_stata_style_regression_results.txt`
- `reports/project_entry2_stata_full.log`
- `reports/project_entry2_stata_regression_table.csv`

Stata status: `STATA_NOT_AVAILABLE_ON_RUNNER`.
