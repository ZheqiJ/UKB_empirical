# Input Data

Data are organized by research use:

- `raw/`: source snapshots used by remote workflows.
- `analysis/`: main regression and analysis datasets. Start here for current
  empirical results.
- `intermediate/`: construction, matching, classification, timing, and fast
  checkpoint outputs kept for audit and reproducibility.

Place the UK Biobank approved applications TSV here only if you want a
repo-local input copy.

The pipeline defaults to:

```bash
/mnt/data/application (1)(1).txt
```

You can point to another copy without changing the repository:

```bash
python3 scripts/ukb_dmca_pipeline.py \
  --applications "/path/to/applications.tsv" \
  --output-dir ukb_dmca
```

The expected fields are `app_id`, `title`, `pi`, `institution`, and `notes`.
Participant-level UK Biobank data must never be stored in this repository.

`public_metadata_seeds.tsv` is an optional, hand-curated overlay for small
public metadata chains that automated repository crawling cannot recover
reliably after a DMCA takedown. Each row is limited to public metadata such as
repository/project names, DOI, PMID, publication title, authors, UKB application
number, institution, and evidence URLs. It must not contain participant-level
UKB data and it must not change the fixed 110-notice universe.
