# New Comparative ITS Group-Definition Audit

## Project-Level Counts

| Group | N | hs_s3_direct | hs_s3_text | both | any s3-type evidence | neither s3-type evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| HIGH_SENSITIVITY total | 1048 | 2 | 621 | 2 | 621 | 427 |
| Treatment: non-sequence High sensitivity | 589 | 2 | 589 | 2 | 589 | 0 |
| Strict control: sequence, no s3 text/direct | 427 | 0 | 0 | 0 | 0 | 427 |
| Broad control: all sequence | 459 | 0 | 32 | 0 | 32 | 427 |
| Broad minus strict | 32 | 0 | 32 | 0 | 32 | 0 |

## Audit Checks

- Treatment intersect StrictControl: empty.
- Treatment intersect BroadControl: empty.
- StrictControl is a subset of BroadControl.
- BroadControl minus StrictControl contains the 32 sequence projects carrying s3-type evidence. In the current classification these are `hs_s3_text=1`; none has `hs_s3_direct=1`.
- Each specification retains 56 calendar months from 2021-09 through 2026-04, including monthly zeros. The first monthly bin begins on 2021-09-28.
- The treatment and control indices use the same pre-July-2024 calendar period, 2021-09-28 through 2024-06, while retaining each group's own mean as the denominator.

## Source Scope

The source is the existing project-level classification, not observed RAP usage. The Stage 3 modality-access matrix marks Whole exome sequencing (WES) and Whole genome sequencing (WGS) as `already_rap_only`; this motivates the sequence control as an already-RAP-bound proxy only.
