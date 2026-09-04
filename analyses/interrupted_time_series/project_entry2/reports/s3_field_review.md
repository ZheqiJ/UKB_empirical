# S3 Field Review

The cached UKB Schema 1 snapshot contains 199 fields with an `s3` tier token. The observed s3 fields are overwhelmingly image files, scan-derived files, and imaging/device outputs rather than generic questionnaire or tabular baseline variables.

## Field Families

| Family | s3 fields |
| --- | ---: |
| Brain MRI/imaging | 89 |
| Embargoed imaging replicas | 30 |
| Cardiac MRI/imaging | 20 |
| Carotid ultrasound | 15 |
| Pancreas imaging | 12 |
| Kidney imaging | 10 |
| Liver imaging | 9 |
| Brain MRI source files | 4 |
| Abdominal/internal fat imaging | 3 |
| DXA imaging | 3 |
| Heart MRI source files | 2 |
| SWI/QSM brain imaging files | 1 |
| T1 structural brain files | 1 |

Brain MRI/imaging fields: 95. This count includes direct brain MRI file fields, NIFTI/DICOM brain images, dMRI/fMRI/SWI/QSM/ASL outputs, native parcellation/surface files, MNI transforms, CIFTI output, and PANDORA brain-imaging outputs.

## Main Categories

| Main category | Local label | s3 fields |
| --- | --- | ---: |
| 1000 | Embargoed imaging replicas | 108 |
| 539 | PANDORA brain imaging outputs | 26 |
| 507 | Brain MRI source files | 13 |
| 102 | Heart MRI source files | 8 |
| 201 | Native diffusion MRI parcellations | 8 |
| 101 | Carotid ultrasound source files | 6 |
| 202 | Native surface and segmentation files | 5 |
| 131 | Pancreas imaging source files | 4 |
| 156 | Kidney imaging source files | 4 |
| 126 | Liver imaging source files | 3 |
| 109 | SWI/QSM brain imaging files | 2 |
| 110 | T1 structural brain files | 2 |
| 103 | DXA image files | 1 |
| 105 | Internal fat DICOM files | 1 |
| 106 | Task fMRI NIFTI files | 1 |
| 107 | Diffusion MRI NIFTI files | 1 |
| 111 | Resting fMRI NIFTI files | 1 |
| 112 | T2 FLAIR NIFTI files | 1 |
| 119 | ASL NIFTI files | 1 |
| 198 | fMRI CIFTI files | 1 |
| 200 | MNI transform files | 1 |
| 538 | Cardiac mesh files | 1 |

## Item Types

| Item type | s3 fields |
| --- | ---: |
| 0 | 26 |
| 10 | 1 |
| 20 | 172 |

## Sequence, Genomic, And Linked-Record Check

Schema 1 s3 titles naming genomic/exome/WES/WGS evidence: 0. No s3 title in the cached 199-field dictionary names WES, WGS, genome sequence data, exome sequence data, linked health records, or OMOP. The word `sequence` appears in 3 MRI sequence-image titles; those are treated as imaging evidence, not genomic sequence data. The word `linked` appears in 54 embargoed imaging-replica titles; those are treated as imaging-file evidence, not linked-record evidence.

## Representative Titles

- 20158: DXA images (DXA imaging)
- 20216: T1 structural brain images - DICOM (Brain MRI/imaging)
- 20218: Multiband diffusion brain images - DICOM (Brain MRI/imaging)
- 20227: Functional brain images - resting - NIFTI (Brain MRI/imaging)
- 20250: Multiband diffusion brain images - NIFTI (Brain MRI/imaging)
- 20251: Susceptibility weighted brain images - NIFTI (Brain MRI/imaging)
- 20263: T1 surface model files and additional structural segmentations (T1 structural brain files)
- 26300: Arterial spin labelling brain images - NIFTI (Brain MRI/imaging)
- 30005: Carotid Artery Ultrasound (MAT format) (Carotid ultrasound)
- 30099: Cardiac biventricular mesh models (Cardiac MRI/imaging)

## Application Text Dictionary

The generated application-text dictionary contains 157 high-precision terms. It excludes generic terms such as `brain`, `genetic`, `health`, and `data`, and uses exact field-title phrases, file-format terms, and modality phrases supported by the 199 s3 fields.
