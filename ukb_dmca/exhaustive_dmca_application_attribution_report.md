# Exhaustive DMCA Application Attribution Report

## Scope

This report expands the application-attribution layer across the full current
DMCA repository universe without restarting the DMCA matching pipeline. It
preserves the existing 52 application-level leakage-risk links and adds an
exhaustive candidate table from the already harvested public README, metadata,
publication, crosswalk, fork/source, and Wayback evidence.

The canonical empirical leakage sample remains
`ukb_dmca/curated_dmca_application_links.csv`. The exhaustive table is broader:
it includes confirmed, probable, ambiguous, B-level candidate, and weak candidate attributions so
coverage can be inspected without hiding uncertainty.

## Summary

| metric | value |
| --- | --- |
| total_dmca_repository_rows | 1826 |
| total_dmca_unique_repo_urls | 194 |
| total_dmca_lineages | 193 |
| total_repository_families | 130 |
| total_families_reviewed | 130 |
| families_linked_to_at_least_one_application_supported_or_ambiguous | 32 |
| families_with_any_retained_candidate_including_weak | 130 |
| confirmed_links | 74 |
| probable_links | 4 |
| candidate_links | 281 |
| excluded_false_positive_rows | 3 |
| ambiguous_multi_application_families | 13 |
| weak_candidate_only_families | 98 |
| unresolved_families_no_candidate | 0 |
| unresolved_families_without_supported_or_ambiguous_link | 98 |
| total_unique_applications_identified_supported_or_ambiguous | 274 |
| total_unique_applications_identified_including_weak | 1158 |
| current_curated_application_baseline | 52 |
| new_unique_applications_beyond_current_52_supported_or_ambiguous | 222 |
| new_unique_applications_beyond_current_52_including_weak | 1106 |
| attribution_row_count | 3899 |

## Family Status Counts

| status | families |
| --- | --- |
| ambiguous | 3 |
| ambiguous_multi_application | 13 |
| confirmed | 12 |
| probable | 4 |
| weak_candidate_only | 98 |

## Attribution Row Counts

| status | rows |
| --- | --- |
| ambiguous | 9 |
| candidate | 281 |
| confirmed | 74 |
| excluded_false_positive | 3 |
| probable | 4 |
| weak_candidate | 3528 |

## Strong Or Ambiguous Family Preview

The full family table is saved at
`ukb_dmca/exhaustive_dmca_family_attribution_summary.csv`.

| family_id | family_status | lineage_count | supported_or_ambiguous_application_count | supported_or_ambiguous_application_ids | candidate_application_count | new_unique_candidate_count_beyond_52 |
| --- | --- | --- | --- | --- | --- | --- |
| family_anyajacobs_ukbiobank | ambiguous_multi_application | 1 | 20 | 1417; 8835; 9946; 19189; 19526; 27477; 28231; 37126; 44411; 56757; 56902; 63871; 64689; 67575; 86321; 98679; 104784; 1054981; 1159532; 1209696 | 20 | 18 |
| family_anyalasagne1_ukbiobank | confirmed | 1 | 1 | 56757 | 21 | 20 |
| family_cancerrisk | confirmed | 2 | 1 | 45761 | 22 | 21 |
| family_divergence-pipeline | probable | 1 | 1 | 17984 | 21 | 20 |
| family_evidence-embracing-nm | ambiguous_multi_application | 1 | 20 | 14575; 40436; 45227; 52446; 62093; 68416; 83990; 101622; 115757; 148925; 519005; 592266; 714779; 753669; 762904; 778098; 807154; 922920; 1124550; 1252926 | 20 | 20 |
| family_genepy-2 | probable | 1 | 1 | 72911 | 21 | 19 |
| family_genetic-survival-analysis-in-ukb | ambiguous_multi_application | 1 | 20 | 16097; 16577; 19542; 33896; 44290; 56859; 57266; 58919; 60434; 69196; 77512; 82416; 84103; 93173; 104811; 104980; 106223; 692259; 903785; 1012028 | 20 | 18 |
| family_gogogpcr | confirmed | 2 | 1 | 55955 | 20 | 19 |
| family_gxsex | confirmed | 1 | 1 | 61666 | 20 | 19 |
| family_human-sex-ratio | confirmed | 1 | 1 | 177030 | 20 | 19 |
| family_imds-wes | ambiguous_multi_application | 2 | 20 | 9616; 19542; 54336; 56902; 70483; 71870; 72821; 74025; 78210; 85253; 93379; 95030; 95599; 100014; 107825; 116200; 276785; 317703; 673794; 1203422 | 40 | 39 |
| family_keloids-clustering | ambiguous | 1 | 1 | 146079 | 20 | 20 |
| family_main-pipeline-and-images-based-models-pipeline-deep-learning-and-aging-main-pipeline-and-images-based-models-pipeline | confirmed | 1 | 1 | 52887 | 20 | 18 |
| family_mh-in-ukb | confirmed | 1 | 1 | 47267 | 21 | 20 |
| family_omniprs | ambiguous_multi_application | 1 | 17 | 44098; 51628; 52031; 65814; 84038; 88159; 94340; 148757; 171511; 190346; 474802; 578405; 899824; 1110109; 1127907; 1141727; 1221902 | 20 | 19 |
| family_pain-proteomics | confirmed | 1 | 1 | 19542 | 21 | 20 |
| family_popmodel-ml-mh | ambiguous_multi_application | 1 | 2 | 23827; 47267 | 2 | 1 |
| family_ptrs-ukb | confirmed | 3 | 1 | 19526 | 21 | 20 |
| family_retinapd | ambiguous_multi_application | 2 | 20 | 31615; 35698; 37539; 41664; 46146; 48388; 60928; 62811; 63121; 63454; 65206; 67263; 71550; 76517; 80610; 82002; 83259; 85139; 96326; 100274 | 40 | 39 |
| family_rooty29_ukbiobank | confirmed | 1 | 1 | 56757 | 21 | 20 |
| family_sas-sample-extraction | ambiguous | 1 | 1 | 51830 | 20 | 19 |
| family_shapeit5 | ambiguous_multi_application | 10 | 20 | 236; 3501; 7898; 8370; 9616; 40709; 65027; 66995; 72298; 78795; 79237; 95030; 98772; 100014; 107825; 190333; 317703; 680373; 1059547; 1145019 | 40 | 39 |
| family_t2dm-ukb-predictions | ambiguous_multi_application | 2 | 20 | 15678; 16577; 28784; 42256; 58105; 77583; 85224; 93173; 93351; 99967; 104811; 106223; 176486; 214427; 494920; 680373; 692259; 888618; 903785; 1168445 | 40 | 39 |
| family_uk-biobank-study-1 | probable | 1 | 1 | 84709 | 21 | 20 |
| family_ukb-download-and-prep-template | ambiguous | 3 | 1 | 54520 | 40 | 40 |
| family_ukb-idears | ambiguous_multi_application | 1 | 20 | 41664; 51709; 75525; 91995; 93141; 209139; 341475; 423966; 564547; 579398; 639461; 795542; 905766; 1012351; 1029266; 1040154; 1061558; 1063834; 1108389; 1237419 | 20 | 20 |
| family_ukbanalytica | ambiguous_multi_application | 3 | 40 | 14762; 15168; 18177; 20650; 30603; 31615; 45227; 45340; 51980; 54218; 60434; 60651; 60928; 61147; 61467; 65252; 66813; 67263; 68250; 68353; 69972; 73507; 73759; 75556; 77202; 77717; 79325; 80154; 207159; 412140; 532367; 672457; 822932; 826232; 1061558; 1078387; 1084290; 1146999; 1188902; 1290541 | 40 | 39 |
| family_ukbb-risk | ambiguous_multi_application | 2 | 20 | 30603; 44891; 51347; 51830; 56329; 60520; 73860; 76085; 87802; 90519; 99541; 109607; 134960; 775744; 778098; 784342; 789279; 823964; 881679; 940419 | 38 | 37 |
| family_ukbbmriutils | probable | 1 | 1 | 89197 | 21 | 20 |
| family_ukbcc | ambiguous_multi_application | 2 | 20 | 761; 11425; 19705; 33087; 45289; 46631; 48405; 51064; 51830; 57189; 59456; 63956; 67263; 73507; 85457; 87480; 92681; 96326; 523060; 532322 | 20 | 19 |
| family_ukbython | confirmed | 1 | 1 | 103356 | 1 | 0 |
| family_zhishenppp_ukbiobank | confirmed | 1 | 1 | 56757 | 21 | 20 |

## Interpretation

- `confirmed`, `probable`, `ambiguous`, and `candidate` rows are the supported
  attribution layer. `candidate` rows retain B-level alternatives without
  promoting them to true probable links.
- `weak_candidate` rows are retained for coverage and auditability, but they
  are not treated as confirmed/probable empirical leakage links.
- Existing 52 curated applications are marked with `existing_curated_52` or
  `existing_curated_52_application_only`.
- New candidate application IDs beyond the 52 are marked with
  `new_unique_beyond_current_52=1`.
- Multiple plausible applications for the same family are preserved rather
  than collapsed to a single forced assignment.
