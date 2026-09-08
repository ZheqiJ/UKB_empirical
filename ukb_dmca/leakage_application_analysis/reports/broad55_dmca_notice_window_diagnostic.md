# Broad-55 DMCA Notice-Timing Feasibility Diagnostic

## Data Definition

Broad 55 membership is frozen from the existing application-level file: 52 curated applications plus the existing three Broad-55 additions. Project initiation date is the cohort date and x-axis. The event date is the earliest **observed DMCA notice** reproducibly linked to an application through the current curated application/family evidence. It is not treated as a date of leakage, public exposure, repository upload, discovery, or underlying posting.

## Notice-Date Reconstruction

Notice IDs were reconstructed from `curated_dmca_application_links.csv` and matching rows in `curated_dmca_repository_family_links.csv`, then dated using `ukb_dmca_notices.csv`. For the three frozen additions, a family notice was used only where the current family record explicitly listed that exact application as its candidate/application link. If multiple valid notice IDs were linked, the minimum notice date was retained. Missing mappings were left missing.

Broad 55 has 55 applications: 24 have a reproducibly identified earliest notice date, 31 are unresolved/missing, and 0 have an earliest notice before project initiation. Curated 52 has 22 dated, 30 unresolved/missing, and 0 notice-before-start cases.

Stored `first_dmca_notice_date` disagreements with the reconstructed minimum: 2. 19542: stored 2025-12-01, reconstructed 2025-10-15; 47267: stored 2025-11-12, reconstructed 2025-10-20

## Main Timing Table

| Broad-55 timing window | Retained cases | Pre Jul 5 2024 | On/after Jul 5 2024 |
|---|---:|---:|---:|
| 1 year | 1 | 0 | 1 |
| 18 months | 1 | 0 | 1 |
| 2 years | 2 | 1 | 1 |

| Curated-52 timing window | Retained cases | Pre Jul 5 2024 | On/after Jul 5 2024 |
|---|---:|---:|---:|
| 1 year | 1 | 0 | 1 |
| 18 months | 1 | 0 | 1 |
| 2 years | 2 | 1 | 1 |

## July-2024 Diagnostics

The three zoom figures display project initiation on the x-axis and lag months on the y-axis, using the symmetric displayed range 2022-07-05 through 2026-07-05 around the 5 July 2024 cutoff. This range contains every retained Broad-55 positive case in the plotted windows. The combined panel and the three individual figures apply the relevant common timing rule before plotting.

## Unresolved and Invalid Timing Mappings

Missing/unresolved notice dates (31): 10035 (Risk factors and associated causal pathways linked to blood pressure); 10279 (The relationship of cognitive function and negative emotions with morbidity and mortality: an aetiological investigation); 12184 (Type 2 diabetes, physical activity, sedentary behaviour and sleep.); 19136 (Lung Health: Genes and environment); 22224 (Prospective studies of ageing and age-related diseases); 23668 (Genetic and environmental factors including nutritional and lifestyle influences on neurodevelopmental disorders/traits (including impulsivity/compulsivity) and their brain correlates); 24247 (Searching Identity-by-descent segments in biobank-scale cohorts); 27837 (Statistical Methods for Large Scale Genetic Studies); 30418 (Biomarker profiling by NMR metabolomics for the study of chronic disease risk and underlying risk factors); 31063 (Methodological extensions to estimate genetic heritability and shared risk factors for phenotypes of the UK Biobank); 33923 (Genetic risk prediction and variance in diverse populations); 40161 (Application of deep learning for the characterisation of motion patterns in the heart); 46122 (Characterizing the contribution of short tandem repeats to human phenotypes.); 49777 (Identification of genetic and lifestyle risk factors of unhealthy brain ageing to direct mechanistic studies using post-mortem brain tissue); 51157 (Stratification and modelling of competing risks in cardiovascular disease events based on multi-level patient characteristics and genetics); 52293 (Large-scale whole genome sequencing of the UK Biobank cohort to generate and evaluate therapeutic hypotheses regarding targets, biomarkers and pathways implicated in disease); 54520 (Constructing risk scores of longevity, dementia, and related disorders); 55288 (Early life, adulthood, and genomic risk factors for early-onset cancers); 57232 (Estimating the overall impact of genetic variation on morbidity and mortality and assessing differential risk conditional on environmental and genetic factors.); 59070 (Statistical machine learning of wearable sensor data to predict disease outcomes); 61054 (Social and Environmental Adversity in Relation to All-Cause Mortality); 61785 (Physiological and Bioinformatics Analyses of Genetic Variants in the Glucagon Receptor); 62254 (Optimisation of time use for health and wellbeing); 64823 (A Genomic Data Science Framework for the 1000 Arab genome project); 65805 (Genetic factors on Type 2 diabetes and hypertension); 69610 (Genetic stratification of immunosuppressive drugs on neurodegenerative disorders incidence); 74395 (Interpretion of health data with artificial intelligence for study of cardiovascular risk factors and their relation to diseases); 79957 (Deep learning based causal inference methods for variant interpretation); 88878 (The cardiovascular digital twin of the adult population: defining the population ranges.); 92005 (Integrative analysis of genomic, molecular, cellular, and biochemical measures to inform cancer etiology); 867484 (Identifying predictors for persistent pain after joint replacement in osteoarthritis patients by integrative analysis of multimodal data)

Earliest notice before project initiation (0): None.

## Feasibility Recommendation

1 year: 0 pre-cutoff and 1 post-cutoff positive cases remain. This is only a sparse feasibility diagnostic and is not enough by itself for a stable causal analysis. 18 months: 0 pre-cutoff and 1 post-cutoff positive cases remain. This is only a sparse feasibility diagnostic and is not enough by itself for a stable causal analysis. 2 years: 1 pre-cutoff and 1 post-cutoff positive cases remain. This is only a sparse feasibility diagnostic and is not enough by itself for a stable causal analysis. A later application-level common-window analysis should define a complete application risk set and should not treat notice timing as a leakage-occurrence date.

## Interpretation Limitation

The timing variable is the date of the first observed DMCA notice, not the date of the underlying leakage or public posting. Therefore this exercise studies documented notice timing relative to project initiation.

No RAP causal effect is estimated or claimed here.
