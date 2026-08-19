#!/usr/bin/env python3
"""Run UKB DMCA matching with public repository/package metadata enrichment."""

from __future__ import annotations

import json
from pathlib import Path

try:
    import ukb_dmca_enriched_appid_runner as runner
    import ukb_dmca_public_metadata_seed_overlay as seed_overlay
    import ukb_public_metadata_enrichment as public_meta
except ImportError:
    from scripts import ukb_dmca_enriched_appid_runner as runner
    from scripts import ukb_dmca_public_metadata_seed_overlay as seed_overlay
    from scripts import ukb_public_metadata_enrichment as public_meta


_ORIG_REPO_ENRICH = runner._ENRICHED_REPO_ENRICH
_ORIG_MAKE_LINEAGES = runner._ENRICHED_MAKE_LINEAGES
_ORIG_POSTPROCESS_OUTPUTS = runner.postprocess_outputs


def repo_enrich(client, targets: list[dict[str, str]], wayback_limit: int) -> list[dict[str, str]]:
    rows = _ORIG_REPO_ENRICH(client, targets, wayback_limit)
    rows = public_meta.enrich_repo_rows(client, targets, rows, wayback_limit, runner.base, runner.identifiers)
    return [runner._append_direct_app_ids(row) for row in rows]


def make_lineages(repo_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = _ORIG_MAKE_LINEAGES(repo_rows)
    rows = public_meta.rollup_lineage_fields(rows, repo_rows)
    return [runner._append_direct_app_ids(row) for row in rows]


def install() -> None:
    runner.enriched.install_enrichment()
    public_meta.extend_fields(runner.base)
    runner.base.identifiers = runner.identifiers
    runner.enriched.identifiers = runner.identifiers
    runner.enriched.repo_enrich = repo_enrich
    runner.enriched.make_lineages = make_lineages
    runner.enriched.score = runner.score
    runner.enriched.final_label = runner.final_label
    runner.base.repo_enrich = repo_enrich
    runner.base.make_lineages = make_lineages
    runner.base.score = runner.score
    runner.base.final_label = runner.final_label


def postprocess_outputs(raw_argv: list[str]) -> None:
    _ORIG_POSTPROCESS_OUTPUTS(raw_argv)
    out = Path(runner._arg_value(raw_argv, "--output-dir") or ".")
    apps_path = Path(runner._arg_value(raw_argv, "--applications") or "data/applications.tsv")
    seed_overlay.apply_public_metadata_seeds(out, apps_path)
    summary_path = out / "evidence/logs/result_summary.json"
    lineages = runner._read_csv(out / "ukb_dmca_lineages.csv")
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    summary.update(public_meta.summary_counts(lineages))
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    runner.install = install
    runner.postprocess_outputs = postprocess_outputs
    return runner.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
