# Stage 3 RAP Exposure Classification

Policy date: `2024-07-05`. This is a provisional measurement
step only. It does not finalise treatment/control status, optimise group
definitions for sample size, construct outcomes, or run DID regressions.

The input universe is fixed to the `6,935` Schema 27 applications
matched to one UKB Projects website record with one recovered start date. The
132 unmatched Schema 27 records remain outside this classification working
sample and are preserved only in the timing audit file.

Source commit: `055a799ef296cd2891d25aa710cdb022017c6d09`.

## Official Access Matrix

| modality_family | pre_july_2024_access_route | classification_role |
| --- | --- | --- |
| Whole genome sequencing (WGS) | already_rap_only | Explicit WGS dependence is already-RAP-bound evidence. |
| Whole exome sequencing (WES) | already_rap_only | Explicit WES/exome sequencing dependence is already-RAP-bound evidence. |
| OMOP Common Data Model transformation | already_rap_only | Explicit OMOP dependence is treated as medium-confidence RAP-only evidence. |
| Genotyping array, imputation, GWAS, PRS, HLA, CNV | legacy_download_or_local_access | Specific array/imputation/GWAS language is newly-RAP-bound evidence, not already-RAP-bound evidence. |
| Imaging and image-derived phenotypes | legacy_download_or_local_access | Imaging-only dependence is newly-RAP-bound evidence. |
| Linked health records | legacy_data_portal_or_download_route | Linked-record-only dependence is newly-RAP-bound evidence. |
| Questionnaires, assessment-centre fields, wearables, environmental data | legacy_download_or_local_access | Specific questionnaire/assessment/environmental terms are newly-RAP-bound evidence. |
| Biochemistry, biomarkers, NMR metabolomics, Olink proteomics | legacy_download_or_data_portal_route | Specific assay/biomarker/proteomics terms are newly-RAP-bound evidence. |
| Generic genetic/genomic language | ambiguous_from_project_text | Generic genetic/genomic/gene/variant terms are recorded as ambiguity signals and do not by themselves imply WGS/WES or already-RAP exposure. |

Key official sources used for the matrix:

- UKB RAP transition notice: https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/19996604847133-Changing-the-way-UK-Biobank-data-is-made-available-to-researchers-around-the-world
- UKB past data releases: https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases
- WES Showcase category: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=170
- WGS Showcase category: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=180
- Genotypes and imputation documentation: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=263 and https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=100319
- Legacy genetic-data download guide: https://biobank.ndph.ox.ac.uk/ukb/ukb/docs/ukbgene_instruct.html
- Hospital inpatient/Data Portal documentation: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=2000 and https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=2006
- Imaging, proteomics and NMR documentation: https://community.ukbiobank.ac.uk/hc/en-gb/articles/24618819821981-Imaging-Data, https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=1839, and https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=220

## Classification Logic

- `ALREADY_RAP_BOUND`: the project text contains explicit pre-policy RAP-only
  evidence, such as WGS, WES, exome sequencing, whole-genome sequencing, or
  OMOP, and no specific legacy-route modality is detected.
- `NEWLY_RAP_BOUND`: the project text contains specific legacy-route evidence
  such as genotyping/imputation/GWAS/PRS, imaging, linked health records,
  questionnaires/assessment fields, biomarkers/proteomics/metabolomics, physical
  measures, or environmental/geospatial fields, and no WGS/WES/OMOP evidence is
  detected.
- `MIXED`: both explicit already-RAP-only evidence and specific legacy-route
  evidence are detected.
- `UNCLEAR`: no specific modality evidence is detected. Generic words such as
  genetic, genomic, gene, variant, or sequencing are recorded as ambiguity
  signals but do not by themselves imply WGS/WES or already-RAP exposure.

## Preliminary Counts

| classification | projects | high_confidence | medium_confidence | low_confidence |
| --- | --- | --- | --- | --- |
| ALREADY_RAP_BOUND | 42 | 41 | 1 | 0 |
| NEWLY_RAP_BOUND | 5561 | 4674 | 887 | 0 |
| MIXED | 183 | 182 | 1 | 0 |
| UNCLEAR | 1149 | 0 | 0 | 1149 |

The policy date itself is counted with `after_policy`.

| classification | before_policy_projects | after_policy_projects | total_projects |
| --- | --- | --- | --- |
| ALREADY_RAP_BOUND | 30 | 12 | 42 |
| NEWLY_RAP_BOUND | 3346 | 2215 | 5561 |
| MIXED | 77 | 106 | 183 |
| UNCLEAR | 879 | 270 | 1149 |

Manual review is recommended for `2,421` projects, mainly
`MIXED`, `UNCLEAR`, medium/low-confidence classifications, generic sequencing
without WGS/WES, physical-sample language, or pre-2021 sequencing contexts.

## Modality Drivers

| classification | already_rap_only_modalities | legacy_route_modalities | ambiguous_signals |
| --- | --- | --- | --- |
| ALREADY_RAP_BOUND | WES=25; WGS=20; OMOP_RAP_ONLY=1 |  | GENERIC_GENETIC_LANGUAGE=38; GENERIC_SEQUENCE_LANGUAGE=36; PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE=3 |
| NEWLY_RAP_BOUND |  | QUESTIONNAIRES_ASSESSMENT=2774; BIOMARKERS_ASSAYS=2178; GENOTYPING_IMPUTATION=2096; IMAGING=1580; PHYSICAL_MEASURES=835; ENVIRONMENT_GEOSPATIAL=569; LINKED_HEALTH_RECORDS=432 | GENERIC_GENETIC_LANGUAGE=3832; GENERIC_SEQUENCE_LANGUAGE=138; PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE=64 |
| MIXED | WGS=129; WES=76; OMOP_RAP_ONLY=1 | GENOTYPING_IMPUTATION=142; BIOMARKERS_ASSAYS=72; QUESTIONNAIRES_ASSESSMENT=55; IMAGING=50; LINKED_HEALTH_RECORDS=31; PHYSICAL_MEASURES=25; ENVIRONMENT_GEOSPATIAL=18 | GENERIC_GENETIC_LANGUAGE=178; GENERIC_SEQUENCE_LANGUAGE=152; PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE=10 |
| UNCLEAR |  |  | GENERIC_GENETIC_LANGUAGE=715; GENERIC_SEQUENCE_LANGUAGE=44; PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE=13 |

## Representative Examples

| classification | app_id | start | confidence | modalities | title |
| --- | --- | --- | --- | --- | --- |
| ALREADY_RAP_BOUND | 7089 | 2015-01-01 | HIGH | RAP-only:WES; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE | Exome Sequencing of All Premature Coronary Artery Disease Participants in UK Biobank |
| ALREADY_RAP_BOUND | 53279 | 2019-12-23 | HIGH | RAP-only:WES; ambiguous:GENERIC_SEQUENCE_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | Prediction of the tumor mutation burden and its predictive value in UK biobank cancer patients:... |
| ALREADY_RAP_BOUND | 58864 | 2020-04-20 | HIGH | RAP-only:WGS; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE | Monitoring tumour burden in circulating free DNA by low coverage whole genome sequencing |
| ALREADY_RAP_BOUND | 82590 | 2022-06-07 | HIGH | RAP-only:WES|WGS; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE | Elucidating the Genetic Landscape of Frontotemporal Dementia (FTD) and Parkinson's Disease (PD) |
| ALREADY_RAP_BOUND | 62824 | 2020-08-19 | MEDIUM | RAP-only:OMOP_RAP_ONLY | UK Biobank OMOP based analyses (including COVID-19 network study) |
| ALREADY_RAP_BOUND | 62905 | 2020-07-27 | HIGH | RAP-only:WES; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE | Analyzing unmappable ("camouflaged") genome regions in UK Biobank exome sequencing data using the... |
| ALREADY_RAP_BOUND | 60111 | 2020-08-17 | HIGH | RAP-only:WES; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE | Using whole exome sequencing to identify rare functional variants of severe neurological disorders |
| ALREADY_RAP_BOUND | 62659 | 2021-01-11 | HIGH | RAP-only:WES; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE | Co-analysis of the International Mouse Phenotyping Consortium (IMPC) data and the UK Biobank... |
| NEWLY_RAP_BOUND | 289 | 2012-07-01 | HIGH | legacy:PHYSICAL_MEASURES|QUESTIONNAIRES_ASSESSMENT | Development of normative values for hand grip strength |
| NEWLY_RAP_BOUND | 291 | 2012-09-01 | HIGH | legacy:PHYSICAL_MEASURES|QUESTIONNAIRES_ASSESSMENT | Multimorbidity in participants with and without COPD |
| NEWLY_RAP_BOUND | 761 | 2012-09-19 | HIGH | legacy:PHYSICAL_MEASURES|QUESTIONNAIRES_ASSESSMENT; ambiguous:GENERIC_GENETIC_LANGUAGE | Risk of type 2 Diabetes and development of disease |
| NEWLY_RAP_BOUND | 13489 | 2012-09-24 | HIGH | legacy:ENVIRONMENT_GEOSPATIAL|QUESTIONNAIRES_ASSESSMENT | Relation between hearing and demographic, behavioural and biological markers in middle aged people |
| NEWLY_RAP_BOUND | 774 | 2012-11-05 | HIGH | legacy:BIOMARKERS_ASSAYS|PHYSICAL_MEASURES|QUESTIONNAIRES_ASSESSMENT | Cross-sectional study to investigate ethnic differences in cardiovascular risk and mental health |
| NEWLY_RAP_BOUND | 788 | 2013-02-01 | HIGH | legacy:ENVIRONMENT_GEOSPATIAL|PHYSICAL_MEASURES|QUESTIONNAIRES_ASSESSMENT; ambiguous:GENERIC_GENETIC_LANGUAGE | Heritability of disease frequency |
| NEWLY_RAP_BOUND | 2112 | 2013-03-04 | HIGH | legacy:IMAGING|QUESTIONNAIRES_ASSESSMENT | Automated macular thickness measurements and association with potential risk factors and systemic... |
| NEWLY_RAP_BOUND | 338 | 2013-04-15 | HIGH | legacy:BIOMARKERS_ASSAYS|IMAGING|QUESTIONNAIRES_ASSESSMENT | Using the Vascular Assessment and Measurement Platform for Images of the Retina (VAMPIRE) to... |
| MIXED | 648 | 2012-11-01 | HIGH | RAP-only:WES; legacy:PHYSICAL_MEASURES|QUESTIONNAIRES_ASSESSMENT; ambiguous:GENERIC_GENETIC_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | Common and rare genetic variants in respiratory health: the UK Biobank Lung Exome Variant... |
| MIXED | 9616 | 2016-01-01 | HIGH | RAP-only:WGS; legacy:GENOTYPING_IMPUTATION|QUESTIONNAIRES_ASSESSMENT; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | The Genetics of Extreme Blood Indices by Whole Genome Sequencing |
| MIXED | 4477 | 2016-06-01 | HIGH | RAP-only:WES; legacy:GENOTYPING_IMPUTATION; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | Identification and characterisation of naturally-occurring human gene knockouts. |
| MIXED | 26041 | 2017-01-03 | HIGH | RAP-only:WES|WGS; legacy:BIOMARKERS_ASSAYS|GENOTYPING_IMPUTATION; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | Large-Scale Sequencing in the UK Biobank to Facilitate Gene Discovery, Genome Sciences, and... |
| MIXED | 98512 | 2025-08-28 | MEDIUM | RAP-only:OMOP_RAP_ONLY; legacy:LINKED_HEALTH_RECORDS | Discovering Polytopes in High Dimensional, Heterogeneous Datasets using Bayesian Archetypal Analysis |
| MIXED | 23359 | 2016-11-01 | HIGH | RAP-only:WGS; legacy:GENOTYPING_IMPUTATION; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | Osteoarthritis |
| MIXED | 24299 | 2017-01-01 | HIGH | RAP-only:WGS; legacy:GENOTYPING_IMPUTATION|LINKED_HEALTH_RECORDS|PHYSICAL_MEASURES|QUESTIONNAIRES_ASSESSMENT; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | COPD follow up ? access to genotype and phenotype information and DNA samples |
| MIXED | 40436 | 2018-07-24 | HIGH | RAP-only:WES; legacy:GENOTYPING_IMPUTATION|PHYSICAL_MEASURES|QUESTIONNAIRES_ASSESSMENT; ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE | Prediction models of health and wellness traits based on genetics, anthropometric, and clinical data |
| UNCLEAR | 132 | 2012-08-31 | LOW | none | Prevalence of stroke and identification of associated risk factors |
| UNCLEAR | 1383 | 2012-12-01 | LOW | none | Environmental risk factors of non-cancer illness |
| UNCLEAR | 4047 | 2014-06-03 | LOW | none | Quantification of Variation in Blood |
| UNCLEAR | 9905 | 2014-12-01 | LOW | ambiguous:GENERIC_GENETIC_LANGUAGE | Using genetics to elucidate the relationship between socioeconomic/behavioural traits and disease |
| UNCLEAR | 16971 | 2016-04-18 | LOW | ambiguous:GENERIC_GENETIC_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | Trinean DNA Contamination detection project |
| UNCLEAR | 41018 | 2018-10-16 | LOW | ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE | Interpreting Gene Expression in the Gut-Brain Axis Through the Lens of Human Genetics |
| UNCLEAR | 57617 | 2020-04-21 | LOW | ambiguous:PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | Understanding the social outcomes of survivors of critical illness: a cross sectional population... |
| UNCLEAR | 156992 | 2024-11-27 | LOW | ambiguous:GENERIC_GENETIC_LANGUAGE|GENERIC_SEQUENCE_LANGUAGE|PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE | Discovery of new genetic rare and common variants for Prostate Cancer in the UK Biobank and the... |

## Already-RAP-Bound Control Candidates

- Strict pure already-RAP-bound controls: `28` projects. This
  requires `ALREADY_RAP_BOUND`, high confidence, explicit WGS/WES evidence, no
  specific legacy-route evidence, and project start on or after
  `2021-11-01`.
- Broader pure already-RAP-bound candidates: `42` projects.
  This is all provisional `ALREADY_RAP_BOUND` projects, including medium
  confidence OMOP-only and earlier sequencing contexts.
- Any already-RAP-only modality candidates: `225` projects.
  This includes provisional `MIXED` projects and should not be treated as a
  strict control group without manual review.

## Ambiguities And Misclassification Risks

- Earlier sequencing projects may describe investigator-generated sequencing or
  DNA/sample work before UKB's public RAP sequence releases. These are flagged,
  and the strict control count excludes starts before
  `2021-11-01`.
- Generic genetic/genomic language is frequent and intentionally does not imply
  WGS/WES. Specific GWAS, SNP, genotype, imputation, PRS, HLA or CNV language is
  treated as legacy-route genomic evidence.
- Project descriptions often name diseases, traits, or broad aims rather than
  approved basket fields. `UNCLEAR` is therefore a real measurement category,
  not a residual treatment/control group.
- `MIXED` projects are not forced into either control or treated groups because
  their text indicates both prior RAP-only and legacy-route data dependence.
- Physical samples, external assays, or industry sequencing language can look
  like UKB data requirements but may reflect data generation outside the UKB
  access route; these rows are flagged for review.

## Outputs

- `data/intermediate/rap_classification/stage3_project_rap_exposure_classification.csv`
- `data/intermediate/rap_classification/stage3_rap_exposure_counts.csv`
- `data/intermediate/rap_classification/stage3_rap_exposure_counts_by_policy_period.csv`
- `data/intermediate/rap_classification/stage3_rap_exposure_modality_counts.csv`
- `data/intermediate/rap_classification/stage3_rap_exposure_examples.csv`
- `data/intermediate/rap_classification/stage3_modality_access_matrix.csv`
- `data/intermediate/rap_classification/stage3_rap_exposure_summary.json`
