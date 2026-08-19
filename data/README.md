# Input Data

Place the UK Biobank approved applications TSV here only if you want a
repo-local input copy.

The pipeline defaults to:

```bash
/mnt/data/application (1)(1).txt
```

You can point to another copy without changing the repository:

```bash
python3 scripts/ukb_dmca_pipeline.py --applications "/path/to/applications.tsv"
```

The expected fields are `app_id`, `title`, `pi`, `institution`, and `notes`.
Participant-level UK Biobank data must never be stored in this repository.

`public_metadata_seeds.tsv` is an optional, hand-curated overlay for small
public metadata chains that automated repository crawling cannot recover
reliably after a DMCA takedown. Each row is limited to public metadata such as
repository/project names, DOI, PMID, publication title, authors, UKB application
number, institution, and evidence URLs. It must not contain participant-level
UKB data and it must not change the fixed 110-notice universe.
