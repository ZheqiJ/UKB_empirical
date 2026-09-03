# Project Entry2 Results

## A. What Is High Sensitivity?

Primary high sensitivity is `HIGH_C05_S3`: existing C05 RAP-intensive comparison evidence, explicit WES/WGS evidence, or at least one current UKB field-page link to an `s3` field. It is a proxy for higher-granularity or more sensitive data use, not observed leakage risk.

Project counts:

| Definition | N |
| --- | ---: |
| HIGH_C05_S3 | 463 |
| HIGH_C03_S3 | 462 |
| HIGH_C05_S3_TIMING_CONSERVATIVE | 463 |
| LOW_STRICT | 1,147 |
| hs_c05 | 269 |
| hs_s3_field | 2 |
| S3_ONLY | 2 |
| C05_ONLY | 2 |

Pre/post counts use the exact policy date 2024-07-05 at the project level: HIGH_C05_S3 is 317 pre-July-2024 and 146 post-July-2024; LOW_STRICT is 806 pre-July-2024 and 341 post-July-2024.

The full audit files are `classification_counts.csv`, `classification_overlap.csv`, `field_tier_distribution.csv`, and `application_field_tier_links.csv`.

## B. Test 1 - High-Sensitivity Entry Count

Question: did the absolute number of high-sensitivity project starts change around/after July 2024?

Primary HIGH_C05_S3:

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 4.1672 | 0.9793 | 0.0000 | [2.2479, 6.0866] |
| Time | -0.0141 | 0.0102 | 0.1681 | [-0.0341, 0.0059] |
| PostJuly2024 | 4.4655 | 1.1692 | 0.0001 | [2.1738, 6.7571] |
| TimeAfterJuly2024 | 0.0149 | 0.1082 | 0.8901 | [-0.1971, 0.2270] |

Key terms: Time=-0.0141 (SE 0.0102); PostJuly2024=4.4655 (SE 1.1692); TimeAfterJuly2024=0.0149 (SE 0.1082).

C03+S3 robustness: Time=-0.0141 (SE 0.0102); PostJuly2024=4.4973 (SE 1.1517); TimeAfterJuly2024=0.0056 (SE 0.1054).

## C. Test 2 - High-Sensitivity Share

Question: did the composition of project entry shift toward high-sensitivity projects?

Primary denominator is `HIGH_C05_S3 + LOW_STRICT`; the all-start denominator is reported separately.

| Term | Estimate | SE | p-value | 95% CI |
| --- | ---: | ---: | ---: | ---: |
| Intercept | 0.3488 | 0.0475 | 0.0000 | [0.2557, 0.4418] |
| Time | -0.0028 | 0.0012 | 0.0227 | [-0.0051, -0.0004] |
| PostJuly2024 | 0.0205 | 0.1048 | 0.8450 | [-0.1849, 0.2258] |
| TimeAfterJuly2024 | 0.0083 | 0.0059 | 0.1582 | [-0.0032, 0.0198] |

Key terms: Time=-0.0028 (SE 0.0012); PostJuly2024=0.0205 (SE 0.1048); TimeAfterJuly2024=0.0083 (SE 0.0059).

High/all robustness: Time=-0.0008 (SE 0.0002); PostJuly2024=-0.0085 (SE 0.0232); TimeAfterJuly2024=0.0022 (SE 0.0014).

## D. Test 3 - High Vs Low Partition

Question: was the post-transition trajectory stronger for high-sensitivity than for low-sensitivity project types?

High sensitivity: Time=-0.0141 (SE 0.0102); PostJuly2024=4.4655 (SE 1.1692); TimeAfterJuly2024=0.0149 (SE 0.1082).

Strict low sensitivity: Time=0.0718 (SE 0.0364); PostJuly2024=5.3995 (SE 3.6837); TimeAfterJuly2024=0.0872 (SE 0.3378).

Inclusive NOT_HIGH robustness: Time=0.3330 (SE 0.1172); PostJuly2024=12.7555 (SE 25.3081); TimeAfterJuly2024=4.5438 (SE 2.3670).

The post-July slope change is 0.0149 for high-sensitivity starts and 0.0872 for strict low-sensitivity starts, so the descriptive post-transition trajectory grows faster for the strict low-sensitivity series in this specification. Test 2 remains the formal composition test.

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
- `reports/project_entry2_stata_full.log`
- `reports/project_entry2_stata_regression_table.csv`

Stata status: `STATA_NOT_AVAILABLE_ON_RUNNER`.
