# Project Entry2 Design

## Question

Following the July 2024 RAP transition, did recorded UKB project entry shift toward projects using higher-sensitivity or higher-granularity data?

This is a descriptive interrupted time-series and comparative composition analysis. It does not estimate a causal RAP treatment effect.

## Sample

The project-entry2 pipeline uses the same full public project-start universe as `project_entry`: 6,935 projects with exact public Start dates. It does not impose the earlier publication DID restriction that projects must have started before July 2024.

Primary estimation window: 2019-01 through 2025-12.

Breakpoint: July 2024, anchored to the 2024-07-05 UKB RAP transition.

## High-Sensitivity Proxy

The primary proxy is `HIGH_SENSITIVITY`, equal to one if any observable evidence channel is present: explicit WES/WGS or sequence-product evidence, a direct current public UKB field-page link to an `s3` field, or high-precision application text derived from the 199 Schema 1 `s3` fields.

Existing control-expansion layers are retained only as audit metadata. They are not competing high-sensitivity definitions.

## Low-Sensitivity Proxy

The primary lower-sensitivity comparison is the exhaustive complement, `LOWER_SENSITIVITY_COMPARISON = 1 - HIGH_SENSITIVITY`. This means no identified high evidence under the observable proxy, not proof that every complement project is low-risk. `LOW_STRICT` is retained only as an audit flag.
