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

Each outcome is an entry index normalized to its own full pre-July-2024 monthly mean (`2021-10` through `2024-06` = 100). The model uses 55 complete calendar months from October 2021 through April 2026, month fixed effects, and Newey-West HAC lag 3. September 2021 is excluded. July 2024 has `TimeAfterJuly2024=0`.

| Quantity | STRICT | BROAD |
| --- | ---: | ---: |
| Control pre slope | -3.4814 | -3.3837 |
| Control post slope | 4.4833 | 6.0767 |
| Control slope change | 7.9646 | 9.4603 |
| Treatment pre slope | 1.4061 | 1.4061 |
| Treatment post slope | 11.3923 | 11.3923 |
| Treatment slope change | 9.9862 | 9.9862 |
| delta1 | 4.8875 | 4.7898 |
| delta2 | -137.2598 | -125.6085 |
| delta3 | 2.0215 | 0.5258 |
| SE(delta3) | 3.2093 | 2.8891 |
| 95% CI(delta3) | [-4.2687, 8.3117] | [-5.1369, 6.1885] |
| p(delta3) | 0.5288 | 0.8556 |
| H0 delta3=0 rejected? | No | No |

The displayed interaction parameterization has Control as the reference group. The `beta` coefficients use the Control-series HAC inference; the `delta` coefficients use the Treatment-minus-Control normalized difference-series HAC inference. This is the algebraically equivalent three-series Newey-West implementation, rather than a built-in Stata `newey` regression on a stacked data set with duplicated monthly time values.

## Comparative Reading

1. Strict design: `delta3` is **positive** (2.0215); it is **not statistically significant** at 5% (p=0.5288).
2. Broad design: `delta3` is **positive** (0.5258); it is **not statistically significant** at 5% (p=0.8556).
3. The `delta3` sign is stable across the 427-vs-589 and 459-vs-589 comparisons. Including the 32 mixed sequence+s3 projects changes `delta3` by -1.4957 index points per month.
4. Differential pre-trends (`delta1`) are 4.8875 in STRICT (p=0.0000) and 4.7898 in BROAD (p=0.0000).
5. Differential immediate level changes (`delta2`) are -137.2598 in STRICT (p=0.0065) and -125.6085 in BROAD (p=0.0094); `delta3` captures the gradual differential post-transition slope change.

When `delta3>0`, the descriptive reading is: the post-transition entry trajectory strengthened more for high-sensitivity project types with higher incremental exposure to the July 2024 RAP transition than for sequence-based projects whose relevant data were already RAP-only before the transition. This is not a causal DID estimate and does not show that treatment projects moved from local access to RAP.

## Raw-Count Robustness

Raw counts retain the same comparative ITS construction but measure absolute monthly starts, not relative trajectories from each group's historical baseline. They are a robustness output because the group sizes differ.

| Raw-count result | STRICT | BROAD |
| --- | ---: | ---: |
| delta3 | 0.2313 | 0.1626 |
| HAC SE(delta3) | 0.1000 | 0.0963 |
| p(delta3) | 0.0208 | 0.0912 |

## Figures

- [Strict observed entry index](../figures/figure_strict_observed_entry_index.svg)
- [Strict fitted entry index](../figures/figure_strict_fitted_entry_index.svg)
- [Broad observed entry index](../figures/figure_broad_observed_entry_index.svg)
- [Broad fitted entry index](../figures/figure_broad_fitted_entry_index.svg)
- [Strict segmented trends, month FE netted out](../figures/figure_strict_segmented_trends.svg)
- [Broad segmented trends, month FE netted out](../figures/figure_broad_segmented_trends.svg)
