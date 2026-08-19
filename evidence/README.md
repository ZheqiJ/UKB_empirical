# Evidence Directory

Pipeline runs write auditable evidence here:

- `notices/`: cached public DMCA notice text, with source metadata.
- `lineages/`: one review file per deduplicated repository lineage.
- `logs/`: fetch logs, run manifests, and API/search diagnostics.

The evidence files are source notes and metadata only. They do not download,
store, or republish participant-level UK Biobank data from targeted
repositories.

