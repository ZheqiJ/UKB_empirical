# Historical DID Archive

This package preserves the previous UK Biobank quarterly incumbent-project DID
work as an exploratory and descriptive diagnostic archive. The design attempted
to compare incumbent projects provisionally classified as newly RAP-bound with
already-RAP-bound or already-RAP-bound-like incumbent projects around the 5 July
2024 UK Biobank data-access policy transition.

The analysis is retained because it produced useful data-construction checks,
publication-linkage audits, risk-set panel outputs, event-time diagnostics, and
control-definition sensitivity results. It should not currently be interpreted
as an identified causal RAP-effect estimate: actual project-level RAP migration,
refresh requests, local-data use, active/expired status, and observed RAP use
are not available in the public data, and publication is a lagged downstream
outcome.

Historical control definitions were cumulative C0-C6 exposure/control proxy
layers. C0 was the most conservative already-RAP-bound proxy; C01, C03, and C05
added progressively broader already-RAP-bound-like control candidates; C06 was
the broadest measurement diagnostic. C06 should remain a sensitivity diagnostic,
not a preferred clean control group by default.

Main archived outputs:

- `data/analysis/design1_quarterly_publication/`: quarterly publication panel,
  regression tables, event-study outputs, pretrend tests, timing audit, and
  summary JSON.
- `data/intermediate/fast_pipeline/`: earlier fast publication/DMCA checkpoint
  outputs used to seed Design 1.
- `figures/`: archived Design 1 and fast-checkpoint figures.
- `reports/`: full Design 1 reports and the Stage 5 fast checkpoint report.
- `scripts/`: archived DID implementation scripts. Root-level scripts are thin
  compatibility wrappers so older commands and tests still work.

Shared public source data and reusable project metadata remain outside this
archive in `data/raw/` and `data/intermediate/`.
