# New Comparative ITS: Within-High RAP-Exposure Comparative ITS

## Group Definitions

This is a descriptive comparative ITS within the existing `HIGH_SENSITIVITY` universe. It does not identify observed project-level RAP users, actual migration dates, RAP usage logs, or verified local-to-RAP transitions.

The treatment proxy is the higher incremental July-2024 RAP-exposure proxy: `HIGH_SENSITIVITY=1` and `hs_wes_wgs_sequence=0`. The control proxy is sequence-based because the Stage 3 access-route matrix classifies WES and WGS as `already_rap_only` before July 2024.

| Specification | Treatment definition N | Control definition N | Treatment starts in window | Control starts in window |
| --- | ---: | ---: | ---: | ---: |
| STRICT (`NEW_CITS_STRICT`) | 589 | 427 | 380 | 231 |
| BROAD (`NEW_CITS_BROAD`) | 589 | 459 | 380 | 255 |

The broad control includes 32 sequence projects excluded from the strict control. Their exclusion reason is s3-type high-sensitivity evidence: `hs_s3_text=1` for all 32; `hs_s3_direct=1` for 0.

## Primary Normalized Comparative ITS

Each outcome is an entry index normalized to its own full pre-July-2024 monthly mean (`2021-09-28` through `2024-06` = 100). The model uses 56 calendar months from September 2021 through April 2026, month fixed effects, and Newey-West HAC lag 3. The September 2021 bin begins on September 28, so it is a deliberately truncated first month. July 2024 has `TimeAfterJuly2024=0`.

| Quantity | STRICT | BROAD |
| --- | ---: | ---: |
| Control pre slope | -2.8422 | -2.6674 |
| Control post slope | 4.4389 | 6.0626 |
| Control slope change | 7.2811 | 8.7299 |
| Treatment pre slope | 1.7094 | 1.7094 |
| Treatment post slope | 11.6744 | 11.6744 |
| Treatment slope change | 9.9650 | 9.9650 |
| delta1 | 4.5516 | 4.3768 |
| delta2 | -137.4270 | -124.8108 |
| delta3 | 2.6840 | 1.2351 |
| SE(delta3) | 3.2618 | 2.9134 |
| 95% CI(delta3) | [-3.7092, 9.0771] | [-4.4751, 6.9453] |
| p(delta3) | 0.4106 | 0.6716 |
| H0 delta3=0 rejected? | No | No |

The displayed interaction parameterization has Control as the reference group. The `beta` coefficients use the Control-series HAC inference; the `delta` coefficients use the Treatment-minus-Control normalized difference-series HAC inference. This is the algebraically equivalent three-series Newey-West implementation, rather than a built-in Stata `newey` regression on a stacked data set with duplicated monthly time values.

## Comparative Reading

1. Strict design: `delta3` is **positive** (2.6840); it is **not statistically significant** at 5% (p=0.4106).
2. Broad design: `delta3` is **positive** (1.2351); it is **not statistically significant** at 5% (p=0.6716).
3. The `delta3` sign is stable across the 427-vs-589 and 459-vs-589 comparisons. Including the 32 mixed sequence+s3 projects changes `delta3` by -1.4489 index points per month.
4. Differential pre-trends (`delta1`) are 4.5516 in STRICT (p=0.0000) and 4.3768 in BROAD (p=0.0000).
5. Differential immediate level changes (`delta2`) are -137.4270 in STRICT (p=0.0071) and -124.8108 in BROAD (p=0.0103); `delta3` captures the gradual differential post-transition slope change.

When `delta3>0`, the descriptive reading is: the post-transition entry trajectory strengthened more for high-sensitivity project types with higher incremental exposure to the July 2024 RAP transition than for sequence-based projects whose relevant data were already RAP-only before the transition. This is not a causal DID estimate and does not show that treatment projects moved from local access to RAP.

## Raw-Count Robustness

Raw counts retain the same comparative ITS construction but measure absolute monthly starts, not relative trajectories from each group's historical baseline. They are a robustness output because the group sizes differ.

| Raw-count result | STRICT | BROAD |
| --- | ---: | ---: |
| delta3 | 0.2439 | 0.1803 |
| HAC SE(delta3) | 0.0982 | 0.0936 |
| p(delta3) | 0.0130 | 0.0540 |

## Figures

- [Strict observed entry index](../figures/figure_strict_observed_entry_index.svg)
- [Strict fitted entry index](../figures/figure_strict_fitted_entry_index.svg)
- [Broad observed entry index](../figures/figure_broad_observed_entry_index.svg)
- [Broad fitted entry index](../figures/figure_broad_fitted_entry_index.svg)
- [Strict segmented trends, month FE netted out](../figures/figure_strict_segmented_trends.svg)
- [Broad segmented trends, month FE netted out](../figures/figure_broad_segmented_trends.svg)
