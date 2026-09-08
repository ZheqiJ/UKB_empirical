# New Comparative ITS: Within-High RAP-Exposure Comparative ITS

## Group Definitions

This is a descriptive comparative ITS within the existing `HIGH_SENSITIVITY` universe. It does not identify observed project-level RAP users, actual migration dates, RAP usage logs, or verified local-to-RAP transitions.

The treatment proxy is the higher incremental July-2024 RAP-exposure proxy: `HIGH_SENSITIVITY=1` and `hs_wes_wgs_sequence=0`. The control proxy is sequence-based because the Stage 3 access-route matrix classifies WES and WGS as `already_rap_only` before July 2024.

| Specification | Treatment: higher-incremental-exposure proxy | Control: already-RAP-bound sequence proxy |
| --- | ---: | ---: |
| STRICT (`NEW_CITS_STRICT`) | 589 | 427 |
| BROAD (`NEW_CITS_BROAD`) | 589 | 459 |

The broad control includes 32 sequence projects excluded from the strict control. Their exclusion reason is s3-type high-sensitivity evidence: `hs_s3_text=1` for all 32; `hs_s3_direct=1` for 0.

## Primary Normalized Comparative ITS

Each outcome is an entry index normalized to its own full pre-July-2024 monthly mean (`2019-01` through `2024-06` = 100). The model uses all 88 calendar months through April 2026, month fixed effects, and Newey-West HAC lag 3. July 2024 has `TimeAfterJuly2024=0`.

| Quantity | STRICT | BROAD |
| --- | ---: | ---: |
| Control pre slope | -0.9524 | -0.8373 |
| Control post slope | 3.9194 | 5.7498 |
| Control slope change | 4.8718 | 6.5870 |
| Treatment pre slope | 0.3741 | 0.3741 |
| Treatment post slope | 12.2800 | 12.2800 |
| Treatment slope change | 11.9060 | 11.9060 |
| delta1 | 1.3265 | 1.2113 |
| delta2 | -82.3741 | -69.8507 |
| delta3 | 7.0342 | 5.3189 |
| SE(delta3) | 2.6577 | 2.3495 |
| 95% CI(delta3) | [1.8251, 12.2432] | [0.7139, 9.9240] |
| p(delta3) | 0.0081 | 0.0236 |
| H0 delta3=0 rejected? | Yes | Yes |

The displayed interaction parameterization has Control as the reference group. The `beta` coefficients use the Control-series HAC inference; the `delta` coefficients use the Treatment-minus-Control normalized difference-series HAC inference. This is the algebraically equivalent three-series Newey-West implementation, rather than a built-in Stata `newey` regression on a stacked data set with duplicated monthly time values.

## Comparative Reading

1. Strict design: `delta3` is **positive** (7.0342); it is **statistically significant** at 5% (p=0.0081).
2. Broad design: `delta3` is **positive** (5.3189); it is **statistically significant** at 5% (p=0.0236).
3. The `delta3` sign is stable across the 427-vs-589 and 459-vs-589 comparisons. Including the 32 mixed sequence+s3 projects changes `delta3` by -1.7152 index points per month.
4. Differential pre-trends (`delta1`) are 1.3265 in STRICT (p=0.0032) and 1.2113 in BROAD (p=0.0050).
5. Differential immediate level changes (`delta2`) are -82.3741 in STRICT (p=0.0343) and -69.8507 in BROAD (p=0.0667); `delta3` captures the gradual differential post-transition slope change.

When `delta3>0`, the descriptive reading is: the post-transition entry trajectory strengthened more for high-sensitivity project types with higher incremental exposure to the July 2024 RAP transition than for sequence-based projects whose relevant data were already RAP-only before the transition. This is not a causal DID estimate and does not show that treatment projects moved from local access to RAP.

## Raw-Count Robustness

Raw counts retain the same comparative ITS construction but measure absolute monthly starts, not relative trajectories from each group's historical baseline. They are a robustness output because the group sizes differ.

| Raw-count result | STRICT | BROAD |
| --- | ---: | ---: |
| delta3 | 0.3666 | 0.2972 |
| HAC SE(delta3) | 0.0885 | 0.0827 |
| p(delta3) | 0.0000 | 0.0003 |

## Figures

- [Strict observed entry index](../figures/figure_strict_observed_entry_index.svg)
- [Strict fitted entry index](../figures/figure_strict_fitted_entry_index.svg)
- [Broad observed entry index](../figures/figure_broad_observed_entry_index.svg)
- [Broad fitted entry index](../figures/figure_broad_fitted_entry_index.svg)
- [Strict segmented trends, month FE netted out](../figures/figure_strict_segmented_trends.svg)
- [Broad segmented trends, month FE netted out](../figures/figure_broad_segmented_trends.svg)
