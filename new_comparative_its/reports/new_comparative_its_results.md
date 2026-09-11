# New Comparative ITS: Within-High RAP-Exposure Comparative ITS

## Group Definitions

This is a descriptive comparative ITS within the existing `HIGH_SENSITIVITY` universe. It does not identify observed project-level RAP users, actual migration dates, RAP usage logs, or verified local-to-RAP transitions.

The treatment proxy is the higher incremental July-2024 RAP-exposure proxy: `HIGH_SENSITIVITY=1` and `hs_wes_wgs_sequence=0`. The control proxy is sequence-based because the Stage 3 access-route matrix classifies WES and WGS as `already_rap_only` before July 2024.

| Specification | Treatment definition N | Control definition N | Treatment starts in window | Control starts in window |
| --- | ---: | ---: | ---: | ---: |
| STRICT (`NEW_CITS_STRICT`) | 589 | 427 | 380 | 231 |
| BROAD (`NEW_CITS_BROAD`) | 589 | 459 | 380 | 255 |

The broad control includes 32 sequence projects excluded from the strict control. Their exclusion reason is s3-type high-sensitivity evidence: `hs_s3_text=1` for all 32; `hs_s3_direct=1` for 0.

## Raw Monthly-Count Comparative ITS

The outcome is the absolute number of project starts per calendar month. The model uses 55 complete calendar months from October 2021 through April 2026, month fixed effects, and Newey-West HAC lag 3. September 2021 is excluded because the sequence control starts on 2021-09-28 and that month is incomplete. July 2024 has `TimeAfterJuly2024=0`.

| Quantity | STRICT | BROAD |
| --- | ---: | ---: |
| Control pre slope | -0.1066 | -0.1118 |
| Control post slope | 0.1372 | 0.2007 |
| Control slope change | 0.2438 | 0.3125 |
| Treatment pre slope | 0.0669 | 0.0669 |
| Treatment post slope | 0.5420 | 0.5420 |
| Treatment slope change | 0.4751 | 0.4751 |
| delta1 | 0.1734 | 0.1787 |
| delta2 | -4.6637 | -4.5455 |
| delta3 | 0.2313 | 0.1626 |
| SE(delta3) | 0.1000 | 0.0963 |
| 95% CI(delta3) | [0.0353, 0.4274] | [-0.0261, 0.3513] |
| p(delta3) | 0.0208 | 0.0912 |
| H0 delta3=0 rejected? | Yes | No |

The displayed interaction parameterization has Control as the reference group. The `beta` coefficients use the Control-series HAC inference; the `delta` coefficients use the Treatment-minus-Control raw-count difference-series HAC inference. This is the algebraically equivalent three-series Newey-West implementation, rather than a built-in Stata `newey` regression on a stacked data set with duplicated monthly time values.

## Independent Pre-Shock Pretrend Diagnostic

This diagnostic re-estimates a separate 66-row stacked comparative ITS using only October 2021 through June 2024 (33 calendar months), before the July 2024 transition. It includes common calendar-month fixed effects but no Treatment x calendar-month fixed effects. Time is zero in October 2021. For HAC inference, the two group-level score vectors are aggregated within each calendar month before applying Newey-West lag 3 across the 33 months.

The primary pretrend test is `H0: Treated x Time = 0`: no differential linear pre-shock trajectory. The supplementary joint Wald test, `H0: Treated = 0` and `Treated x Time = 0`, also tests the October-2021 group-level difference; it is therefore broader than a pure parallel-trend test. Omitting Treatment x month fixed effects assumes that both groups share the same month-of-year seasonality.

| Diagnostic | STRICT | BROAD |
| --- | ---: | ---: |
| Treated | -0.7897 | -1.0535 |
| p(Treated) | 0.3607 | 0.2540 |
| Treated x Time | 0.1554 | 0.1568 |
| HAC SE(Treated x Time) | 0.0476 | 0.0501 |
| p(Treated x Time) | 0.0011 | 0.0017 |
| 95% CI(Treated x Time) | [0.0621, 0.2488] | [0.0586, 0.2549] |
| Joint Wald chi-square(2) | 19.7805 | 16.9730 |
| Joint Wald p-value | 0.0001 | 0.0002 |

Both specifications reject the no-differential-pretrend hypothesis. The treatment proxy had a faster pre-shock raw-count trajectory than its sequence control proxy, so the post-transition `delta3` comparisons should not be read as causal DID effects or as evidence conditional on parallel pretrends.

## Comparative Reading

1. Strict design: `delta3` is **positive** (0.2313); it is **statistically significant** at 5% (p=0.0208).
2. Broad design: `delta3` is **positive** (0.1626); it is **not statistically significant** at 5% (p=0.0912).
3. The `delta3` sign is stable across the 427-vs-589 and 459-vs-589 comparisons. Including the 32 mixed sequence+s3 projects changes `delta3` by -0.0687 monthly starts per month.
4. Differential pre-trends (`delta1`) are 0.1734 in STRICT (p=0.0000) and 0.1787 in BROAD (p=0.0000).
5. Differential immediate level changes (`delta2`) are -4.6637 in STRICT (p=0.0030) and -4.5455 in BROAD (p=0.0050); `delta3` captures the gradual differential post-transition slope change.

When `delta3>0`, the descriptive reading is: the post-transition entry trajectory strengthened more for high-sensitivity project types with higher incremental exposure to the July 2024 RAP transition than for sequence-based projects whose relevant data were already RAP-only before the transition. This is not a causal DID estimate and does not show that treatment projects moved from local access to RAP.

## Figures

- [Strict observed monthly counts](../figures/figure_strict_observed_monthly_counts.svg)
- [Strict fitted monthly counts](../figures/figure_strict_fitted_monthly_counts.svg)
- [Broad observed monthly counts](../figures/figure_broad_observed_monthly_counts.svg)
- [Broad fitted monthly counts](../figures/figure_broad_fitted_monthly_counts.svg)
