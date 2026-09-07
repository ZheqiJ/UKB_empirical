# Curated DMCA-Application Linkage Report

## Scope

This report completes the remaining repository/family linkage review for the application-level leakage analysis. The current `ukb_dmca` repository output remains the reproducible public DMCA audit snapshot. The manually curated empirical crosswalk is separate: the 48 previously researcher-confirmed applications are retained as the fixed baseline, and the 23 remaining repository/family units are reviewed as an expansion layer.

## Reconciliation Summary

| metric | value |
| --- | ---: |
| UKB DMCA notices in current snapshot | 110 |
| Current repository lineages | 193 |
| Curated repository families after conservative basename grouping | 130 |
| Previously confirmed baseline applications | 48 |
| Archived manual named lineages before this task | 41 |
| Remaining repository/family units reviewed | 23 |
| Remaining units successfully linked | 6 |
| Remaining units linked to existing baseline apps | 2 |
| Remaining units adding new apps | 4 |
| Remaining units unresolved/ambiguous/excluded | 17 |
| New unique applications from remaining review | 4 |
| Final unique leakage-risk applications | 52 |
| Final named linked repository lineages | 47 |
| Application-only manual rows without lineage IDs in current audit | 30 |
| Remaining unmatched/ambiguous repository families | 103 |

Automated-only current applications not added to the empirical outcome: 29256.

## Remaining 23 Review Table

| Repo/family | Evidence found | Application ID | Confidence | Reason | Final status |
| --- | --- | --- | --- | --- | --- |
| family_ukbb-gwas-dev | publication/application leads without a repository-owner bridge | 32285; 36827 | unresolved | Prior manual round explicitly left UKBB_GWAS_dev unfrozen. Public evidence supports UKB applications/papers in nearby GWAS areas, but not the target repo owners/family. | unresolved |
| family_cnv-ukb | multiple plausible CNV UKB applications | 40980; 24898; 68574; 68601; 82094 | ambiguous | Public CNV/UKB evidence points to several applications; no direct application ID, repo-publication chain, or identity bridge uniquely identifies the targeted repository family. | ambiguous |
| family_ukbbcov2risk | generic COVID-19 risk topic only |  | unresolved | Search did not recover a direct application number or repository-linked publication/application chain for kennethcywong/ukbbcov2risk. | unresolved |
| family_ukbbmriutils | organization/project/topic consistency plus public UKB project evidence | 89197 | probable | STALICLA-RnD repository family aligns with the STALICLA application on CNV effects on brain morphology. Public project metadata gives UKB application 89197 and start date 2023-06-29. | new_application_linked |
| family_t40-rsfmri | paper app lead without owner identity bridge | 25057 | unresolved | A TOMM40/APOE resting-state fMRI paper reports UKB application 25057, but the target owner is pseudonymous and public evidence does not bridge the repo to the paper team. | unresolved |
| family_ukb-bmi | legacy application clue not in current start-date universe | 48799 | unresolved | Historical review noted application 48799, but this ID is not present in the current start-date application universe and no stronger public chain was recovered. | unresolved |
| family_divergence-pipeline | author/project/topic consistency plus public UKB project evidence | 17984 | probable | The AdrianHarris96 Divergence_Pipeline lead is consistent with Adrian M. Harris, the Georgia Tech divergence/Gini work, and UKB application 17984. The chain is credible but not a direct repo README app-ID match. | new_application_linked |
| family_genepy-2 | repo-publication-UKB application chain | 72911 | confirmed | The GenePy-2 project has a public repo-publication chain and UKB publication metadata reports application 72911. | new_application_linked |
| family_gwas-phenotype | candidate is a UKB field/resource ID, not an application | 22418 | unresolved | The historical 22418 lead is not treated as a UKB application ID; no replacement direct application evidence was recovered. | unresolved |
| family_uk-biobank-study-1 | repo-publication-UKB application chain | 84709 | confirmed | Prior repository metadata tied xx2383/UK-Biobank-study-1 to DOI 10.1016/j.crtox.2025.100226. The linked UKB project page reports application 84709 and a related publication on the same exposure/outcome chain. | new_application_linked |
| family_ukb-gen-clocks | automated propagation false positive | 29256 | unresolved | Current automated matcher propagated application 29256 through weak publication/topic signals. Manual review treats this as a false positive for UKB-gen-clocks and does not add 29256. | excluded_false_positive |
| family_pain-proteomics | paper text/application chain to an existing baseline app | 19542 | confirmed | Pain proteomics public paper evidence reports UKB application 19542, already present in the fixed broad-48 baseline. | linked_to_existing_baseline |
| family_mh-in-ukb | repo-publication-application chain to an existing baseline app | 47267 | confirmed | The MH_in_UKB code availability chain and paper evidence link to UKB application 47267, already present in the fixed broad-48 baseline. | linked_to_existing_baseline |
| family_uk-biobank-survival | possible existing-baseline relation but weak public bridge | 45761 | unresolved | The family may relate to an existing baseline application, but public evidence does not establish a direct repo-publication/application or identity chain. | unresolved |
| family_keloids-clustering | topic/institution-only application lead | 146079 | ambiguous | UKB application 146079 is topically compatible with keloids, but the repository-to-application bridge is insufficient. | ambiguous |
| family_ukb-atherosclerosis-prediction | no public application bridge found |  | unresolved | No direct application ID, repository-linked publication, or strong identity evidence was recovered. | unresolved |
| family_prs-dash-boxplot-app | weak automated/publication propagation not accepted | 29256 | unresolved | The 29256 automated context is not accepted for this repository family; no stronger direct application evidence was recovered. | unresolved |
| family_ukb-download-and-prep-template | template/common-code family with no unique app |  | ambiguous | The family contains multiple copied/template repositories and no unique application-level public evidence. | ambiguous |
| family_ukb-api | generic utility/API repository family |  | unresolved | Generic UKB API utility family; no direct application or repo-publication chain was found. | unresolved |
| family_ukb-tools | generic utility repository family |  | unresolved | Generic tools family; no unique UKB application could be assigned. | unresolved |
| family_ukbiobank-table-conversion | common table-conversion code family |  | unresolved | Table-conversion family has multiple copies and no unique application/publication bridge. | unresolved |
| family_jm-gwas | common GWAS code family with no unique app |  | unresolved | Multiple repositories share JM-GWAS material, but public evidence does not identify one UKB application. | unresolved |
| family_multi-outcome | generic multi-outcome analysis family |  | unresolved | No direct application ID, linked paper, or owner identity bridge was recovered. | unresolved |

## New Application Evidence Chains

| Application ID | Repo/family | Confidence | Evidence chain | Public URLs |
| --- | --- | --- | --- | --- |
| 89197 | family_ukbbmriutils | probable | STALICLA-RnD repository family aligns with the STALICLA application on CNV effects on brain morphology. Public project metadata gives UKB application 89197 and start date 2023-06-29. | https://www.ukbiobank.ac.uk/enable-your-research/approved-research/effects-of-copy-number-variants-on-the-morphological-structure-of-the-brain-across-multiple-brain-disorders |
| 17984 | family_divergence-pipeline | probable | The AdrianHarris96 Divergence_Pipeline lead is consistent with Adrian M. Harris, the Georgia Tech divergence/Gini work, and UKB application 17984. The chain is credible but not a direct repo README app-ID match. | https://www.ukbiobank.ac.uk/enable-your-research/approved-research/genotype-environment-interactions-and-sub-classification-of-disease |
| 72911 | family_genepy-2 | confirmed | The GenePy-2 project has a public repo-publication chain and UKB publication metadata reports application 72911. | https://www.ukbiobank.ac.uk/enable-your-research/publications/stratification-of-inflammatory-bowel-disease-by-integrating-genomic-data-and-biological-pathways-using-the-genepy-approach; https://github.com/UoS-HGIG/GenePy-2 |
| 84709 | family_uk-biobank-study-1 | confirmed | Prior repository metadata tied xx2383/UK-Biobank-study-1 to DOI 10.1016/j.crtox.2025.100226. The linked UKB project page reports application 84709 and a related publication on the same exposure/outcome chain. | https://www.ukbiobank.ac.uk/enable-your-research/approved-research/risk-and-prognosis-factors-of-cardiovascular-disease-on-different-genetic-background-and-exposures |

## Notes

- `ukb_dmca/remaining_23_repo_review.csv` contains exactly one row for each of the 23 remaining repository/family units from the historical manual exercise.
- `ukb_dmca/curated_dmca_application_links.csv` is the canonical application-level crosswalk. It contains one row per final leakage-risk application and preserves all 48 researcher-confirmed baseline applications with `manual_confirmation_status=confirmed_by_researcher`.
- `ukb_dmca/curated_dmca_repository_family_links.csv` keeps the repository/family evidence layer separate from the application-level outcome.
- The current audit contains 193 self-repository lineages. The historical manual matching exercise worked at a more aggregated repository/family level; this report preserves that 23-unit completion queue rather than replacing it with all current lineage rows.
- No DMCA notice date, targeted commit date, or repository commit date is used to classify applications as pre- or post-July 2024.
