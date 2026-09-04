# Project Entry2

Independent high-sensitivity project-entry ITS pipeline.

Run:

```bash
python3 analyses/interrupted_time_series/project_entry2/scripts/build_high_sensitivity_classification.py
python3 analyses/interrupted_time_series/project_entry2/scripts/project_entry2_analysis.py --skip-classification
```

Primary window: 2019-01 through 2025-12. Breakpoint: July 2024, with `time_after_july2024 = 0` in July 2024, 1 in August 2024, and so on.
