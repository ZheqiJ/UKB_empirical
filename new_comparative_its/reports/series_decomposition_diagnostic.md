# Comparative ITS Series-Decomposition Diagnostic

## Diagnostic question

Are the significant negative pre-period artificial breaks in the existing comparative ITS generated mainly by curvature or breaks in the treatment series, in the control series, or only in the treatment-minus-control difference?

## Design

This diagnostic does not replace or modify the existing comparative ITS. It uses the saved raw monthly project-start series from October 2021 through April 2026, the July 2024 intervention date, month-of-year fixed effects, and Bartlett Newey-West HAC lag 3 without finite-sample scaling.

For each series, the model is `Y_t = alpha + beta*time + gamma*Post + delta*TimeAfter + month-of-year FE + error`. The primary placebo exercise completely excludes July 2024 and later observations and applies the prespecified October 2022 through July 2023 artificial dates to the 33 true pre-transition months. Holm adjustments are calculated separately within each 10-date series panel.

These are specification diagnostics, not causal estimates or randomized placebo tests. No alternative dates or models were searched to improve the results.

## Final comparison

| Object | Actual slope change | HAC SE | p-value | 95% CI | Placebo slope range | Significant placebo slopes | Holm-significant | Placebo signs | Actual vs placebo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Treatment only | 0.4751 | 0.1267 | 0.000176 | [0.2268, 0.7234] | [-0.4495, -0.2664] | 10/10 | 10/10 | 10 negative, 0 positive | Above all pre-period placebo slopes |
| Strict control only | 0.2438 | 0.1390 | 0.079472 | [-0.0287, 0.5162] | [-0.1213, 0.0454] | 0/10 | 0/10 | 4 negative, 6 positive | Above all pre-period placebo slopes |
| Broad control only | 0.3125 | 0.1410 | 0.026639 | [0.0362, 0.5888] | [-0.1544, 0.0343] | 0/10 | 0/10 | 6 negative, 4 positive | Above all pre-period placebo slopes |
| Treatment minus strict control | 0.2313 | 0.1000 | 0.020751 | [0.0353, 0.4274] | [-0.3378, -0.2577] | 10/10 | 10/10 | 10 negative, 0 positive | Above all pre-period placebo slopes |
| Treatment minus broad control | 0.1626 | 0.0963 | 0.091243 | [-0.0261, 0.3513] | [-0.3650, -0.1656] | 9/10 | 9/10 | 10 negative, 0 positive | Above all pre-period placebo slopes |

All five actual July 2024 slope changes lie above every corresponding pre-period artificial slope estimate. This sign separation is descriptive; the artificial dates are overlapping fits to the same short series and are not exchangeable event assignments.

## Main finding

Treatment alone has 10 nominally significant artificial slope breaks; strict control has 0, and broad control has 0. The treatment placebo slopes contain 10 negative and 0 positive estimates. Strict-control slopes contain 4 negative and 6 positive estimates; broad-control slopes contain 6 negative and 4 positive estimates.

The pattern is generated mainly by instability in the treatment series. Every treatment-only artificial slope change is negative and significant before and after Holm correction, while neither control series has a significant artificial slope change at any candidate date. Differencing therefore carries the treatment-series negative breaks into both comparative placebo panels; the selected control changes their magnitude but is not the primary source of the slope-placebo problem.

The negative comparative placebo breaks are not a difference-series artifact: the point-estimate identities reproduce exactly from the separately estimated treatment and control series. The decomposition tables below show which component moves more at each date. Statistical significance cannot be decomposed by subtracting the separate-series standard errors because treatment and control estimates share calendar-time variation; the saved difference-series HAC inference remains the relevant inference for the comparative coefficient.

## Actual July 2024 single-series ITS

| Series | Quantity | Estimate | HAC SE | p-value | 95% CI |
| --- | --- | ---: | ---: | ---: | ---: |
| Treatment only | Pre-trend | 0.066898 | 0.039849 | 0.093196 | [-0.0112, 0.1450] |
| Treatment only | Level change | -1.297138 | 1.263031 | 0.304419 | [-3.7727, 1.1784] |
| Treatment only | Slope change | 0.475100 | 0.126660 | 0.000176 | [0.2268, 0.7234] |
| Strict control only | Pre-trend | -0.106550 | 0.032446 | 0.001024 | [-0.1701, -0.0430] |
| Strict control only | Level change | 3.366519 | 1.798789 | 0.061269 | [-0.1591, 6.8921] |
| Strict control only | Slope change | 0.243766 | 0.138997 | 0.079472 | [-0.0287, 0.5162] |
| Broad control only | Pre-trend | -0.111763 | 0.034072 | 0.001037 | [-0.1785, -0.0450] |
| Broad control only | Level change | 3.248325 | 1.872744 | 0.082825 | [-0.4223, 6.9189] |
| Broad control only | Slope change | 0.312478 | 0.140961 | 0.026639 | [0.0362, 0.5888] |

The treatment-only actual slope change is the existing treatment slope change. The control-only slope changes are the existing strict and broad control slope changes. Their point-estimate differences reproduce the existing comparative `delta3` values.

## Treatment-only pre-period placebos

| Artificial date | Pre n | Post n | Level | SE | p | Holm p | Slope | SE | p | Holm p | Joint p | Joint Holm p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 12 | 21 | -0.1875 | 0.9994 | 0.851207 | 1.000000 | -0.3200 | 0.1022 | 0.001738 | 0.004774 | 0.001208 | 0.004834 |
| 2022-11 | 13 | 20 | -0.2881 | 0.7310 | 0.693494 | 1.000000 | -0.3053 | 0.0783 | 0.000097 | 0.000876 | 0.000493 | 0.003946 |
| 2022-12 | 14 | 19 | 0.5621 | 0.8121 | 0.488779 | 1.000000 | -0.2664 | 0.0916 | 0.003645 | 0.004774 | 0.002893 | 0.005785 |
| 2023-01 | 15 | 18 | 0.3018 | 0.6729 | 0.653800 | 1.000000 | -0.2795 | 0.0819 | 0.000645 | 0.003508 | 0.002916 | 0.005785 |
| 2023-02 | 16 | 17 | 0.2595 | 0.6624 | 0.695293 | 1.000000 | -0.2861 | 0.0832 | 0.000585 | 0.003508 | 0.001867 | 0.005602 |
| 2023-03 | 17 | 16 | 0.2329 | 0.6522 | 0.721014 | 1.000000 | -0.2950 | 0.0885 | 0.000856 | 0.003508 | 0.000962 | 0.004809 |
| 2023-04 | 18 | 15 | 0.2318 | 0.7070 | 0.743024 | 1.000000 | -0.3077 | 0.0974 | 0.001591 | 0.004774 | 0.000568 | 0.003946 |
| 2023-05 | 19 | 14 | 1.0738 | 0.6567 | 0.102048 | 0.918435 | -0.3581 | 0.0925 | 0.000107 | 0.000876 | 0.000542 | 0.003946 |
| 2023-06 | 20 | 13 | 1.8191 | 0.9427 | 0.053640 | 0.536399 | -0.4495 | 0.0889 | <0.000001 | 0.000004 | 0.000003 | 0.000025 |
| 2023-07 | 21 | 12 | 0.1552 | 0.7606 | 0.838267 | 1.000000 | -0.4070 | 0.1158 | 0.000443 | 0.003103 | 0.000433 | 0.003898 |

## Strict-control pre-period placebos

| Artificial date | Pre n | Post n | Level | SE | p | Holm p | Slope | SE | p | Holm p | Joint p | Joint Holm p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 12 | 21 | -1.2892 | 0.8300 | 0.120386 | 0.963086 | -0.0624 | 0.0892 | 0.484314 | 1.000000 | 0.299099 | 1.000000 |
| 2022-11 | 13 | 20 | -0.0766 | 0.7975 | 0.923526 | 1.000000 | 0.0288 | 0.0859 | 0.737918 | 1.000000 | 0.928134 | 1.000000 |
| 2022-12 | 14 | 19 | 0.4885 | 0.8707 | 0.574811 | 1.000000 | 0.0454 | 0.0821 | 0.580229 | 1.000000 | 0.729379 | 1.000000 |
| 2023-01 | 15 | 18 | -0.3390 | 0.7837 | 0.665303 | 1.000000 | 0.0222 | 0.0798 | 0.781264 | 1.000000 | 0.885171 | 1.000000 |
| 2023-02 | 16 | 17 | -0.5373 | 0.8183 | 0.511443 | 1.000000 | 0.0297 | 0.0825 | 0.718734 | 1.000000 | 0.800666 | 1.000000 |
| 2023-03 | 17 | 16 | -0.5730 | 0.9144 | 0.530896 | 1.000000 | 0.0427 | 0.0967 | 0.658342 | 1.000000 | 0.820502 | 1.000000 |
| 2023-04 | 18 | 15 | 0.8467 | 0.5797 | 0.144150 | 1.000000 | 0.0227 | 0.1007 | 0.821893 | 1.000000 | 0.284108 | 1.000000 |
| 2023-05 | 19 | 14 | 2.0667 | 0.8085 | 0.010583 | 0.105832 | -0.0448 | 0.0861 | 0.602378 | 1.000000 | 0.030062 | 0.300617 |
| 2023-06 | 20 | 13 | 2.3931 | 1.0406 | 0.021463 | 0.193171 | -0.1213 | 0.0919 | 0.186597 | 1.000000 | 0.067618 | 0.608562 |
| 2023-07 | 21 | 12 | 0.9170 | 1.0266 | 0.371721 | 1.000000 | -0.0849 | 0.1226 | 0.488932 | 1.000000 | 0.635385 | 1.000000 |

## Broad-control pre-period placebos

| Artificial date | Pre n | Post n | Level | SE | p | Holm p | Slope | SE | p | Holm p | Joint p | Joint Holm p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | 12 | 21 | -2.0683 | 0.8425 | 0.014094 | 0.140938 | -0.1544 | 0.0833 | 0.063849 | 0.638493 | 0.031417 | 0.314168 |
| 2022-11 | 13 | 20 | -0.5773 | 0.8613 | 0.502739 | 1.000000 | -0.0259 | 0.0897 | 0.772261 | 1.000000 | 0.794184 | 1.000000 |
| 2022-12 | 14 | 19 | 0.1105 | 0.9412 | 0.906559 | 1.000000 | 0.0079 | 0.0845 | 0.925127 | 1.000000 | 0.988478 | 1.000000 |
| 2023-01 | 15 | 18 | -0.6502 | 0.7735 | 0.400550 | 1.000000 | -0.0050 | 0.0834 | 0.951828 | 1.000000 | 0.691982 | 1.000000 |
| 2023-02 | 16 | 17 | -1.1704 | 0.8381 | 0.162582 | 1.000000 | 0.0094 | 0.0852 | 0.912375 | 1.000000 | 0.351600 | 1.000000 |
| 2023-03 | 17 | 16 | -1.0029 | 0.8780 | 0.253348 | 1.000000 | 0.0343 | 0.1005 | 0.732665 | 1.000000 | 0.478773 | 1.000000 |
| 2023-04 | 18 | 15 | 0.0418 | 0.6063 | 0.945047 | 1.000000 | 0.0332 | 0.1117 | 0.765976 | 1.000000 | 0.929513 | 1.000000 |
| 2023-05 | 19 | 14 | 1.7920 | 0.9495 | 0.059106 | 0.531956 | -0.0346 | 0.0946 | 0.714291 | 1.000000 | 0.131716 | 1.000000 |
| 2023-06 | 20 | 13 | 2.0677 | 1.1569 | 0.073897 | 0.591177 | -0.1003 | 0.1004 | 0.318009 | 1.000000 | 0.189649 | 1.000000 |
| 2023-07 | 21 | 12 | 0.4630 | 1.0376 | 0.655433 | 1.000000 | -0.0419 | 0.1266 | 0.740596 | 1.000000 | 0.890811 | 1.000000 |

## Point-estimate decomposition of existing comparative placebos

### Strict comparison

| Date | Treatment slope break | Control slope break | Treatment - Control | Saved difference result | Residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | -0.3200 | -0.0624 | -0.2577 | -0.2577 | 0.00000000 |
| 2022-11 | -0.3053 | 0.0288 | -0.3340 | -0.3340 | 0.00000001 |
| 2022-12 | -0.2664 | 0.0454 | -0.3118 | -0.3118 | 0.00000000 |
| 2023-01 | -0.2795 | 0.0222 | -0.3016 | -0.3016 | 0.00000000 |
| 2023-02 | -0.2861 | 0.0297 | -0.3159 | -0.3159 | -0.00000001 |
| 2023-03 | -0.2950 | 0.0427 | -0.3378 | -0.3378 | -0.00000001 |
| 2023-04 | -0.3077 | 0.0227 | -0.3303 | -0.3303 | 0.00000000 |
| 2023-05 | -0.3581 | -0.0448 | -0.3133 | -0.3133 | -0.00000001 |
| 2023-06 | -0.4495 | -0.1213 | -0.3282 | -0.3282 | -0.00000001 |
| 2023-07 | -0.4070 | -0.0849 | -0.3221 | -0.3221 | -0.00000000 |

### Broad comparison

| Date | Treatment slope break | Control slope break | Treatment - Control | Saved difference result | Residual |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022-10 | -0.3200 | -0.1544 | -0.1656 | -0.1656 | 0.00000000 |
| 2022-11 | -0.3053 | -0.0259 | -0.2793 | -0.2793 | 0.00000000 |
| 2022-12 | -0.2664 | 0.0079 | -0.2743 | -0.2743 | 0.00000000 |
| 2023-01 | -0.2795 | -0.0050 | -0.2744 | -0.2744 | 0.00000001 |
| 2023-02 | -0.2861 | 0.0094 | -0.2955 | -0.2955 | -0.00000001 |
| 2023-03 | -0.2950 | 0.0343 | -0.3294 | -0.3294 | 0.00000000 |
| 2023-04 | -0.3077 | 0.0332 | -0.3409 | -0.3409 | -0.00000001 |
| 2023-05 | -0.3581 | -0.0346 | -0.3235 | -0.3235 | 0.00000000 |
| 2023-06 | -0.4495 | -0.1003 | -0.3492 | -0.3492 | -0.00000001 |
| 2023-07 | -0.4070 | -0.0419 | -0.3650 | -0.3650 | -0.00000001 |

The zero residuals verify that each saved comparative placebo slope break equals the treatment-only break minus the corresponding control-only break, up to output rounding.

## Secondary matched 18-pre/12-post exercise

This secondary exercise uses April through July 2023 artificial dates with 18 pre-date and 12 post-date months. It is retained for comparability with the existing placebo report and does not replace the full-window actual estimates.

### Treatment only

| Artificial date | Pre n | Post n | Level | SE | p | Holm p | Slope | SE | p | Holm p | Joint p | Joint Holm p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-04 | 18 | 12 | -0.0338 | 0.5193 | 0.948060 | 1.000000 | -0.2520 | 0.0782 | 0.001282 | 0.005128 | 0.001470 | 0.005879 |
| 2023-05 | 18 | 12 | -0.1439 | 0.4832 | 0.765761 | 1.000000 | -0.1411 | 0.0841 | 0.093529 | 0.093529 | 0.166775 | 0.166775 |
| 2023-06 | 18 | 12 | 0.9474 | 0.5326 | 0.075281 | 0.301125 | -0.1848 | 0.0654 | 0.004744 | 0.009489 | 0.016419 | 0.032838 |
| 2023-07 | 18 | 12 | 0.3796 | 0.6519 | 0.560340 | 1.000000 | -0.3449 | 0.1111 | 0.001904 | 0.005712 | 0.005524 | 0.016571 |
Matched actual July 2024: slope change 1.2833, SE 0.1601, p=<0.000001, 95% CI [0.9696, 1.5970].
### Strict control only

| Artificial date | Pre n | Post n | Level | SE | p | Holm p | Slope | SE | p | Holm p | Joint p | Joint Holm p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-04 | 18 | 12 | 0.3527 | 0.6086 | 0.562223 | 0.562223 | 0.1097 | 0.1019 | 0.281395 | 1.000000 | 0.366733 | 0.733467 |
| 2023-05 | 18 | 12 | 1.9108 | 1.0113 | 0.058835 | 0.235340 | -0.0090 | 0.0986 | 0.927574 | 1.000000 | 0.164935 | 0.494806 |
| 2023-06 | 18 | 12 | 1.2711 | 0.8614 | 0.140049 | 0.420146 | 0.0885 | 0.0821 | 0.281055 | 1.000000 | 0.115520 | 0.462081 |
| 2023-07 | 18 | 12 | 1.1509 | 1.0109 | 0.254901 | 0.509803 | -0.0482 | 0.1267 | 0.703917 | 1.000000 | 0.522762 | 0.733467 |
Matched actual July 2024: slope change 0.5476, SE 0.2375, p=0.021137, 95% CI [0.0821, 1.0131].
### Broad control only

| Artificial date | Pre n | Post n | Level | SE | p | Holm p | Slope | SE | p | Holm p | Joint p | Joint Holm p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-04 | 18 | 12 | -0.7642 | 0.6827 | 0.263010 | 0.791385 | 0.1702 | 0.1145 | 0.137290 | 0.549161 | 0.308778 | 0.926335 |
| 2023-05 | 18 | 12 | 1.5802 | 1.2271 | 0.197846 | 0.791385 | 0.0112 | 0.1174 | 0.924025 | 1.000000 | 0.415575 | 0.926335 |
| 2023-06 | 18 | 12 | 0.8868 | 1.0008 | 0.375592 | 0.791385 | 0.1221 | 0.0928 | 0.188619 | 0.565858 | 0.223038 | 0.892150 |
| 2023-07 | 18 | 12 | 0.7128 | 0.9886 | 0.470892 | 0.791385 | -0.0011 | 0.1294 | 0.993094 | 1.000000 | 0.762279 | 0.926335 |
Matched actual July 2024: slope change 0.6025, SE 0.2399, p=0.012020, 95% CI [0.1323, 1.0726].

## Interpretation limits

The decomposition identifies where the fitted instability appears in the observed series. It does not establish why either series changes, certify artificial dates as event-free, or support a causal RAP effect. The short 33-month pre-period, 15 fitted coefficients, overlapping placebo windows, and large-sample HAC approximations limit precision. Institutional chronology should be reviewed before assigning substantive meaning to any individual artificial break.

## Files

- `data/series_decomposition_results.csv`: all actual, primary placebo, and matched-window single-series estimates.
- `data/series_decomposition_summary.csv`: final treatment/control/difference comparison.
- `figures/figure_treatment_only_its_placebos.svg`
- `figures/figure_strict_control_only_its_placebos.svg`
- `figures/figure_broad_control_only_its_placebos.svg`
- `scripts/series_decomposition_diagnostic.py`
- `reports/series_decomposition_stata_style_results.txt`
