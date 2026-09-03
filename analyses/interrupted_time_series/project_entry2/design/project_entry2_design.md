# Project Entry2 Design

## Question

Following the July 2024 RAP transition, did recorded UKB project entry shift toward projects using higher-sensitivity or higher-granularity data?

This is a descriptive interrupted time-series and comparative composition analysis. It does not estimate a causal RAP treatment effect.

## Sample

The project-entry2 pipeline uses the same full public project-start universe as `project_entry`: 6,935 projects with exact public Start dates. It does not impose the earlier publication DID restriction that projects must have started before July 2024.

Primary estimation window: 2019-01 through 2025-12.

Breakpoint: July 2024, anchored to the 2024-07-05 UKB RAP transition.

## High-Sensitivity Proxy

The primary high-sensitivity proxy is `HIGH_C05_S3`, equal to one if a project has existing C05 RAP-intensive comparison evidence, explicit WES/WGS evidence, or at least one current public UKB field-page link to an `s3` cost-tier field.

The C03 counterpart, `HIGH_C03_S3`, is retained as robustness.

Field-tier evidence is a current Showcase crosswalk. The timing-conservative variant excludes linked fields whose public field debut date is after the project's public Start date.

## Low-Sensitivity Proxy

`LOW_STRICT` is limited to projects whose existing Stage 3 modality evidence is a nonempty subset of questionnaire/assessment, physical-measure, or environmental/geospatial modalities and that have no high-sensitivity evidence. `NOT_HIGH` is the inclusive complement of `HIGH_C05_S3`.
