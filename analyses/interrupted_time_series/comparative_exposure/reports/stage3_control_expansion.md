# Stage 3 Control Expansion Frontier

Policy date: `2024-07-05`. This step preserves the current
conservative classifier. The existing 42 `ALREADY_RAP_BOUND` projects are
treated as fixed C0 and are not reclassified. No treatment/control status is
finalised, no outcomes are constructed, and no DID regressions are run.

Source commit: `651b16d06071b73df93e240aef701a072549b7cd`.

## Layer Definitions

- `C0`: fixed current `ALREADY_RAP_BOUND` baseline.
- `C1`: explicit WGS/WES or whole-genome/whole-exome sequence wording in
  project text.
- `C2`: sequence-specific products, file types, pipelines, and processing
  fingerprints in project text.
- `C3`: broader contextual sequence evidence in project text, excluding generic
  genetic/genomic/variant/sequencing language alone.
- `C4`: verified non-WGS/WES data products already RAP-only before
  5 July 2024.
- `C5`: direct pre-policy RAP-use evidence from project or linked publication
  text.
- `C6`: linked-publication recovery of WGS/WES or other verified RAP-only data
  dependence when application text is vague.

## Incremental Counts

| layer | new_projects | cumulative_projects | new_before_policy | new_after_policy | cumulative_before_policy | cumulative_after_policy | new_within_6m_before | new_within_6m_after | new_within_12m_before | new_within_12m_after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | 42 | 42 | 30 | 12 | 30 | 12 | 2 | 3 | 5 | 6 |
| C1 | 195 | 237 | 82 | 113 | 112 | 125 | 5 | 20 | 9 | 54 |
| C2 | 0 | 237 | 0 | 0 | 112 | 125 | 0 | 0 | 0 | 0 |
| C3 | 30 | 267 | 18 | 12 | 130 | 137 | 0 | 0 | 1 | 4 |
| C4 | 1 | 268 | 0 | 1 | 130 | 138 | 0 | 0 | 0 | 0 |
| C5 | 1 | 269 | 1 | 0 | 131 | 138 | 0 | 0 | 0 | 0 |
| C6 | 169 | 438 | 166 | 3 | 297 | 141 | 4 | 2 | 10 | 3 |

## Previous Classification Of Newly Added Projects

| layer | new_from_previous_classification |
| --- | --- |
| C0 | ALREADY_RAP_BOUND=42 |
| C1 | NEWLY_RAP_BOUND=13; MIXED=179; UNCLEAR=3 |
| C2 |  |
| C3 | NEWLY_RAP_BOUND=23; UNCLEAR=7 |
| C4 | MIXED=1 |
| C5 | NEWLY_RAP_BOUND=1 |
| C6 | NEWLY_RAP_BOUND=135; UNCLEAR=34 |

## Evidence Types By Layer

| layer | new_evidence_types |
| --- | --- |
| C0 | current_conservative_classifier=42 |
| C1 | explicit_sequence_data_wording=195 |
| C2 |  |
| C3 | broader_contextual_sequence_evidence=30 |
| C4 | other_pre_policy_rap_only_product=1 |
| C5 | direct_pre_policy_rap_use_evidence=1 |
| C6 | broader_contextual_sequence_evidence=27; explicit_sequence_data_wording=141; other_pre_policy_rap_only_product=1 |

## Examples

| layer | app_id | start_date | previous | evidence | term | confidence | title |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0 | 7089 | 2015-01-01 | ALREADY_RAP_BOUND | current_conservative_classifier | WES | HIGH_BASELINE | Exome Sequencing of All Premature Coronary Artery Disease Participants in UK Biobank |
| C0 | 53279 | 2019-12-23 | ALREADY_RAP_BOUND | current_conservative_classifier | WES | HIGH_BASELINE | Prediction of the tumor mutation burden and its predictive value in UK biobank cancer patients: using... |
| C0 | 58864 | 2020-04-20 | ALREADY_RAP_BOUND | current_conservative_classifier | WGS | HIGH_BASELINE | Monitoring tumour burden in circulating free DNA by low coverage whole genome sequencing |
| C0 | 62905 | 2020-07-27 | ALREADY_RAP_BOUND | current_conservative_classifier | WES | HIGH_BASELINE | Analyzing unmappable ("camouflaged") genome regions in UK Biobank exome sequencing data using the LPA gene... |
| C0 | 60111 | 2020-08-17 | ALREADY_RAP_BOUND | current_conservative_classifier | WES | HIGH_BASELINE | Using whole exome sequencing to identify rare functional variants of severe neurological disorders |
| C0 | 62824 | 2020-08-19 | ALREADY_RAP_BOUND | current_conservative_classifier | OMOP_RAP_ONLY | HIGH_BASELINE | UK Biobank OMOP based analyses (including COVID-19 network study) |
| C0 | 62659 | 2021-01-11 | ALREADY_RAP_BOUND | current_conservative_classifier | WES | HIGH_BASELINE | Co-analysis of the International Mouse Phenotyping Consortium (IMPC) data and the UK Biobank exome... |
| C0 | 53589 | 2021-01-27 | ALREADY_RAP_BOUND | current_conservative_classifier | WGS | HIGH_BASELINE | Evolution and consequence of endogenous HHV-6 |
| C1 | 52467 | 2019-11-01 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | genome sequence data / genomic sequence data | HIGH | Systematic identification of genetic associations with drug-induced adverse reactions |
| C1 | 70956 | 2021-03-01 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | exome sequencing / exome sequence | HIGH | Understanding of the genetic interplay of rare and common variation in shaping human disease |
| C1 | 71699 | 2021-12-07 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | genome sequence data / genomic sequence data | HIGH | Identifying mechanisms and risk markers for metabolic dysfunction, diabetes and diabetes related... |
| C1 | 50000 | 2019-05-29 | UNCLEAR | explicit_sequence_data_wording | genome sequence data / genomic sequence data | HIGH | Using human population sequencing data to explore protein structure and function |
| C1 | 648 | 2012-11-01 | MIXED | explicit_sequence_data_wording | exome data / exome variants | HIGH_NEEDS_MIXED_REVIEW | Common and rare genetic variants in respiratory health: the UK Biobank Lung Exome Variant Evaluation (UK... |
| C1 | 91747 | 2022-08-25 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | genome sequence data / genomic sequence data | HIGH | Racial Disparities in Head and Neck Cancer Diagnosis and Surgical Outcomes in the UK: A Retrospective... |
| C1 | 88969 | 2022-09-16 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | genome sequence data / genomic sequence data | HIGH | Using the UK Biobank genome sequencing data as a reference panel for genotype imputation and genetic... |
| C1 | 93379 | 2022-12-06 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | genome sequence data / genomic sequence data | HIGH | Identifying non-coding regulatory variants associated with mature B cell neoplasms and B cell mediated... |
| C3 | 16097 | 2016-01-01 | NEWLY_RAP_BOUND | broader_contextual_sequence_evidence | gene burden / variant burden / collapsing analysis | MEDIUM_CONTEXTUAL | Phenome-wide association studies of drug targets |
| C3 | 17085 | 2016-01-01 | NEWLY_RAP_BOUND | broader_contextual_sequence_evidence | gene burden / variant burden / collapsing analysis | MEDIUM_CONTEXTUAL | Dissemination of shared genetics across phenotypes associated with reproductive health and related... |
| C3 | 16013 | 2016-02-01 | NEWLY_RAP_BOUND | broader_contextual_sequence_evidence | loss-of-function / pLoF / protein-truncating variants | MEDIUM_CONTEXTUAL | Integrative analysis of disease association variants and electronic medical records to delineate the... |
| C3 | 48839 | 2019-10-01 | UNCLEAR | broader_contextual_sequence_evidence | rare coding variants / coding variation | MEDIUM_CONTEXTUAL | Evaluating the effects of coding variation in inflammatory genes in cardio-metabolic disease |
| C3 | 24983 | 2017-02-16 | NEWLY_RAP_BOUND | broader_contextual_sequence_evidence | loss-of-function / pLoF / protein-truncating variants | MEDIUM_CONTEXTUAL | Generating effective therapeutic hypotheses from genomic and hospital linkage data |
| C3 | 21677 | 2018-03-27 | NEWLY_RAP_BOUND | broader_contextual_sequence_evidence | loss-of-function / pLoF / protein-truncating variants | MEDIUM_CONTEXTUAL | Genetic and environment studies of myopia and refractive error in the UK Biobank |
| C3 | 32974 | 2019-01-09 | NEWLY_RAP_BOUND | broader_contextual_sequence_evidence | nonsense and missense / rare functional variants | MEDIUM_CONTEXTUAL | Rare, functionally validated, nonsense and missense mutations and human anthropometric and metabolic traits |
| C3 | 42890 | 2019-02-22 | NEWLY_RAP_BOUND | broader_contextual_sequence_evidence | loss-of-function / pLoF / protein-truncating variants | MEDIUM_CONTEXTUAL | Association of loss-of-function variants and incompletely penetrant alleles with UKBB phenotypes |
| C4 | 98512 | 2025-08-28 | MIXED | other_pre_policy_rap_only_product | OMOP / OMOP Common Data Model | MEDIUM_VERIFIED_PRODUCT | Discovering Polytopes in High Dimensional, Heterogeneous Datasets using Bayesian Archetypal Analysis |
| C5 | 19934 | 2016-05-01 | NEWLY_RAP_BOUND | direct_pre_policy_rap_use_evidence | UKB-RAP / UK Biobank Research Analysis Platform | HIGH_DIRECT_PRE_POLICY_RAP | Statistical and Computational Genetics Methods Development |
| C6 | 2112 | 2013-03-04 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | exome sequencing / exome sequence | MEDIUM_PUBLICATION_MODALITY_PRE_POLICY | Automated macular thickness measurements and association with potential risk factors and systemic disease |
| C6 | 9055 | 2015-01-05 | NEWLY_RAP_BOUND | broader_contextual_sequence_evidence | gene burden / variant burden / collapsing analysis | MEDIUM_PUBLICATION_MODALITY_PRE_POLICY | The Genetics of type 2 diabetes aetiology and progression |
| C6 | 9072 | 2015-01-05 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | exome data / exome variants | MEDIUM_PUBLICATION_MODALITY_PRE_POLICY | The Genetics of anthropometric traits ? Height, weight, BMI and waist circumference |
| C6 | 9905 | 2014-12-01 | UNCLEAR | explicit_sequence_data_wording | exome sequencing / exome sequence | MEDIUM_PUBLICATION_MODALITY_PRE_POLICY | Using genetics to elucidate the relationship between socioeconomic/behavioural traits and disease |
| C6 | 10438 | 2015-05-01 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | exome sequencing / exome sequence | MEDIUM_PUBLICATION_MODALITY_PRE_POLICY | Application of fast mixed model association and principal component analysis methods |
| C6 | 1251 | 2015-07-01 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | exome sequencing / exome sequence | MEDIUM_PUBLICATION_MODALITY_PRE_POLICY | The metabolically healthy obese and metabolically obese normal-weight in the UK Biobank: Prevalence, genes... |
| C6 | 12514 | 2015-08-28 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | exome sequencing / exome sequence | MEDIUM_PUBLICATION_MODALITY_PRE_POLICY | The limits of predicting complex traits and diseases from genetic data |
| C6 | 14631 | 2015-10-01 | NEWLY_RAP_BOUND | explicit_sequence_data_wording | whole exome sequencing / whole-exome sequence | MEDIUM_PUBLICATION_MODALITY_PRE_POLICY | Genetic and environmental influences on ageing well |

## Evidence Notes

- C1 and C2 are the highest-precision expansion layers. C2 may add zero
  projects if all technical fingerprints in the available project text also
  appear with explicit sequence wording or are already in C0/C1.
- C3 is intentionally lower confidence and reviewable. It only uses specific
  rare/coding/burden/LoF phrases, not generic genetic/genomic/gene/variant or
  sequencing words alone.
- C4 currently has one verified non-WGS/WES product class: OMOP Field 20142,
  released on RAP in July 2023. No entire modality or tier is assumed RAP-only.
- C5 publication evidence must be pre-policy to count as direct pre-policy RAP
  use. Project text RAP mentions without an independent pre-policy publication
  timestamp are flagged for review.
- C6 uses local Schema 19/24 linked publication metadata, titles, abstracts,
  dates, DOI/PMID, and requires UK Biobank/UKB proximity to the modality term.
  It does not fetch arbitrary full text, so full-text methods review remains a
  follow-up audit item.
- `379` cumulative candidate rows are flagged for manual
  review, primarily C3/C4/C6 rows, prior `MIXED` rows, and post-policy
  publication-product evidence.

## Official UKB Sources Used

- UKB RAP transition notice: https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/19996604847133-Changing-the-way-UK-Biobank-data-is-made-available-to-researchers-around-the-world
- UKB past data releases: https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases
- WES category 170: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=170
- WGS category 180: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=180
- WGS DRAGEN category 185: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=185
- WGS GATK/GraphTyper category 270: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=270
- Previous WGS releases category 271: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=271
- OMOP Field 20142: https://biobank.ndph.ox.ac.uk/ukb/field.cgi?id=20142

## Outputs

- `data/intermediate/control_expansion/stage3_control_expansion_project_review.csv`
- `data/intermediate/control_expansion/stage3_control_expansion_evidence_dictionary.csv`
- `data/intermediate/control_expansion/stage3_control_expansion_layer_counts.csv`
- `data/intermediate/control_expansion/stage3_control_expansion_new_by_previous_classification.csv`
- `data/intermediate/control_expansion/stage3_control_expansion_examples.csv`
- `data/intermediate/control_expansion/stage3_control_expansion_summary.json`
