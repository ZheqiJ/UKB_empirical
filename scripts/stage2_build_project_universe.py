#!/usr/bin/env python3
"""Build Stage 2 UK Biobank public project metadata summaries.

Inputs are public UK Biobank Showcase schema downloads:
- Schema 27 approved applications
- Schema 19 publications
- Schema 24 publication-to-application links

The script intentionally uses only the Python standard library to keep memory
use modest and make the audit trail easy to inspect.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "intermediate" / "stage2_universe"
REPORTS = ROOT / "analyses" / "interrupted_time_series" / "shared" / "data_audit"

SCHEMA27 = RAW / "ukb_schema27_applications.tsv"
SCHEMA19 = RAW / "ukb_schema19_publications.tsv"
SCHEMA24 = RAW / "ukb_schema24_publication_applications.tsv"
SCHEMA4 = RAW / "ukb_schema4_returned_datasets.tsv"

MASTER = PROCESSED / "stage2_master_projects.csv"
SOURCE_SUMMARY = PROCESSED / "stage2_source_summary.csv"
COVERAGE = PROCESSED / "stage2_variable_coverage.csv"
LINK_SUMMARY = PROCESSED / "stage2_linkage_summary.csv"
SCHEMA27_DUPLICATES = PROCESSED / "stage2_schema27_duplicate_app_ids.csv"
SCHEMA4_UNMATCHED = PROCESSED / "stage2_schema4_unmatched_returned_datasets.csv"
PUBLICATION_YEAR_COUNTS = PROCESSED / "stage2_publication_year_counts.csv"
APPLICATION_PUBLICATION_COUNT_DISTRIBUTION = (
    PROCESSED / "stage2_application_publication_count_distribution.csv"
)
MANIFEST = RAW / "stage2_source_manifest.json"
REPORT = REPORTS / "stage2_data_universe.md"


APP_START_RE = re.compile(r"^\d+\t")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\r", " ")).strip()


def parse_schema27(path: Path) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Parse Schema 27, whose notes field contains unquoted raw line breaks."""
    rows: list[dict[str, str]] = []
    stats = Counter()
    current: dict[str, str] | None = None
    continuation_lines = 0

    with path.open("r", encoding="latin-1", newline="") as f:
        header = f.readline().rstrip("\r\n").split("\t")
        if header != ["app_id", "title", "pi", "institution", "notes"]:
            raise ValueError(f"Unexpected Schema 27 header: {header}")

        for line in f:
            line = line.rstrip("\r\n")
            if APP_START_RE.match(line):
                if current is not None:
                    current["notes"] = clean_text(current["notes"])
                    rows.append(current)
                parts = line.split("\t", 4)
                if len(parts) != 5:
                    stats["malformed_start_lines"] += 1
                    continue
                current = dict(zip(header, parts))
            else:
                continuation_lines += 1
                if current is None:
                    stats["orphan_continuation_lines"] += 1
                else:
                    current["notes"] += "\n" + line

    if current is not None:
        current["notes"] = clean_text(current["notes"])
        rows.append(current)

    stats["continuation_lines"] = continuation_lines
    return rows, dict(stats)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="latin-1", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def nonempty(value: str | None) -> bool:
    return bool((value or "").strip())


def pct(numer: int, denom: int) -> str:
    return "" if denom == 0 else f"{100 * numer / denom:.2f}"


def parse_date(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    applications, schema27_parse_stats = parse_schema27(SCHEMA27)
    publications = read_tsv(SCHEMA19)
    pub_links = read_tsv(SCHEMA24)
    returned_datasets = read_tsv(SCHEMA4)

    app_id_counts = Counter(row["app_id"] for row in applications)
    applications_unique: list[dict[str, str]] = []
    apps_by_id: dict[str, dict[str, str]] = {}
    duplicate_audit_rows: list[dict[str, object]] = []
    for row in applications:
        app_id = row["app_id"]
        if app_id not in apps_by_id:
            apps_by_id[app_id] = row
            applications_unique.append(row)
            continue
        first = apps_by_id[app_id]
        duplicate_audit_rows.append(
            {
                "app_id": app_id,
                "is_exact_duplicate_of_first_seen": row == first,
                "title": clean_text(row.get("title", "")),
                "pi": clean_text(row.get("pi", "")),
                "institution": clean_text(row.get("institution", "")),
                "notes": row.get("notes", ""),
            }
        )

    pub_by_id = {row["pub_id"]: row for row in publications}
    pub_id_counts = Counter(row["pub_id"] for row in publications)

    pubs_by_app: dict[str, list[dict[str, str]]] = defaultdict(list)
    returns_by_app: dict[str, list[dict[str, str]]] = defaultdict(list)
    link_pairs = Counter()
    link_stats = Counter()
    for link in pub_links:
        app_id = link.get("app_id", "")
        pub_id = link.get("pub_id", "")
        link_pairs[(app_id, pub_id)] += 1
        if app_id not in apps_by_id:
            link_stats["links_to_missing_schema27_app"] += 1
        if pub_id not in pub_by_id:
            link_stats["links_to_missing_schema19_pub"] += 1
        pub = pub_by_id.get(pub_id)
        if pub is not None:
            pubs_by_app[app_id].append(pub)

    archive_id_counts = Counter(row.get("archive_id", "") for row in returned_datasets)
    return_stats = Counter()
    unmatched_return_rows: list[dict[str, str]] = []
    for row in returned_datasets:
        app_id = row.get("application_id", "")
        if app_id not in apps_by_id:
            return_stats["returns_to_missing_schema27_app"] += 1
            unmatched_return_rows.append(row)
        returns_by_app[app_id].append(row)

    master_rows: list[dict[str, object]] = []
    for app in applications_unique:
        app_id = app["app_id"]
        pubs = pubs_by_app.get(app_id, [])
        returns = returns_by_app.get(app_id, [])
        pub_dates = [parse_date(pub.get("date_pub", "")) for pub in pubs]
        pub_dates = [d for d in pub_dates if d is not None]
        dois = [pub.get("doi", "") for pub in pubs if nonempty(pub.get("doi", ""))]
        pmids = [pub.get("pubmed_id", "") for pub in pubs if nonempty(pub.get("pubmed_id", ""))]
        master_rows.append(
            {
                "app_id": app_id,
                "title": clean_text(app.get("title", "")),
                "pi": clean_text(app.get("pi", "")),
                "institution": clean_text(app.get("institution", "")),
                "notes": app.get("notes", ""),
                "schema24_publication_links": len(pubs),
                "linked_publications_with_doi": len(set(dois)),
                "linked_publications_with_pubmed_id": len(set(pmids)),
                "first_publication_date": min(pub_dates).date().isoformat() if pub_dates else "",
                "last_publication_date": max(pub_dates).date().isoformat() if pub_dates else "",
                "returned_dataset_count": len(returns),
                "returned_dataset_personal_count": sum(1 for r in returns if r.get("personal") == "1"),
                "returned_dataset_availability_values": "|".join(
                    sorted({r.get("availability", "") for r in returns if nonempty(r.get("availability", ""))})
                ),
            }
        )

    source_summary_rows = [
        {
            "source": "UKB Showcase Schema 27 approved applications",
            "path": str(SCHEMA27.relative_to(ROOT)),
            "rows": len(applications),
            "unique_primary_ids": len(app_id_counts),
            "duplicate_primary_ids": sum(1 for count in app_id_counts.values() if count > 1),
            "notes": "Application-level public metadata; notes can contain raw line breaks.",
        },
        {
            "source": "UKB Showcase Schema 19 publications",
            "path": str(SCHEMA19.relative_to(ROOT)),
            "rows": len(publications),
            "unique_primary_ids": len(pub_id_counts),
            "duplicate_primary_ids": sum(1 for count in pub_id_counts.values() if count > 1),
            "notes": "Publication-level public metadata with DOI/PMID/date/citation fields.",
        },
        {
            "source": "UKB Showcase Schema 24 publication-application links",
            "path": str(SCHEMA24.relative_to(ROOT)),
            "rows": len(pub_links),
            "unique_primary_ids": len(link_pairs),
            "duplicate_primary_ids": sum(count - 1 for count in link_pairs.values() if count > 1),
            "notes": "Crosswalk table; app_id links to Schema 27 and pub_id links to Schema 19.",
        },
        {
            "source": "UKB Showcase Schema 4 returned datasets from applications",
            "path": str(SCHEMA4.relative_to(ROOT)),
            "rows": len(returned_datasets),
            "unique_primary_ids": len(archive_id_counts),
            "duplicate_primary_ids": sum(1 for count in archive_id_counts.values() if count > 1),
            "notes": "Application-level returned dataset metadata; application_id links to Schema 27 app_id.",
        },
    ]

    coverage_rows: list[dict[str, object]] = []
    tables = {
        "schema27_applications": applications,
        "schema19_publications": publications,
        "schema24_pub_app_links": pub_links,
        "schema4_returned_datasets": returned_datasets,
        "stage2_master_projects": master_rows,
    }
    for table, rows in tables.items():
        if not rows:
            continue
        fields = list(rows[0].keys())
        for field in fields:
            n_nonmissing = sum(1 for row in rows if nonempty(str(row.get(field, ""))))
            coverage_rows.append(
                {
                    "table": table,
                    "variable": field,
                    "rows": len(rows),
                    "nonmissing": n_nonmissing,
                    "missing": len(rows) - n_nonmissing,
                    "nonmissing_pct": pct(n_nonmissing, len(rows)),
                }
            )

    linked_apps = {app_id for app_id, pubs in pubs_by_app.items() if pubs and app_id in apps_by_id}
    apps_with_returns = {app_id for app_id, rows in returns_by_app.items() if rows and app_id in apps_by_id}
    link_summary_rows = [
        {
            "metric": "schema27_application_records_raw",
            "value": len(applications),
        },
        {
            "metric": "schema27_unique_app_ids",
            "value": len(applications_unique),
        },
        {
            "metric": "schema27_duplicate_app_ids",
            "value": sum(1 for count in app_id_counts.values() if count > 1),
        },
        {
            "metric": "schema27_duplicate_rows_beyond_first",
            "value": len(duplicate_audit_rows),
        },
        {
            "metric": "schema19_publications",
            "value": len(publications),
        },
        {
            "metric": "schema19_unique_pub_ids",
            "value": len(pub_id_counts),
        },
        {
            "metric": "schema24_links",
            "value": len(pub_links),
        },
        {
            "metric": "schema24_unique_app_pub_pairs",
            "value": len(link_pairs),
        },
        {
            "metric": "schema27_apps_with_linked_publication",
            "value": len(linked_apps),
        },
        {
            "metric": "schema27_apps_without_linked_publication",
            "value": len(applications_unique) - len(linked_apps),
        },
        {
            "metric": "schema24_links_to_missing_schema27_app",
            "value": link_stats["links_to_missing_schema27_app"],
        },
        {
            "metric": "schema24_links_to_missing_schema19_pub",
            "value": link_stats["links_to_missing_schema19_pub"],
        },
        {
            "metric": "schema4_returned_dataset_records",
            "value": len(returned_datasets),
        },
        {
            "metric": "schema4_unique_archive_ids",
            "value": len(archive_id_counts),
        },
        {
            "metric": "schema27_apps_with_returned_dataset",
            "value": len(apps_with_returns),
        },
        {
            "metric": "schema4_returns_to_missing_schema27_app",
            "value": return_stats["returns_to_missing_schema27_app"],
        },
        {
            "metric": "schema27_continuation_lines_in_notes",
            "value": schema27_parse_stats.get("continuation_lines", 0),
        },
        {
            "metric": "schema27_orphan_continuation_lines",
            "value": schema27_parse_stats.get("orphan_continuation_lines", 0),
        },
    ]

    write_csv(
        MASTER,
        master_rows,
        [
            "app_id",
            "title",
            "pi",
            "institution",
            "notes",
            "schema24_publication_links",
            "linked_publications_with_doi",
            "linked_publications_with_pubmed_id",
            "first_publication_date",
            "last_publication_date",
            "returned_dataset_count",
            "returned_dataset_personal_count",
            "returned_dataset_availability_values",
        ],
    )
    write_csv(
        SOURCE_SUMMARY,
        source_summary_rows,
        ["source", "path", "rows", "unique_primary_ids", "duplicate_primary_ids", "notes"],
    )
    write_csv(
        COVERAGE,
        coverage_rows,
        ["table", "variable", "rows", "nonmissing", "missing", "nonmissing_pct"],
    )
    write_csv(LINK_SUMMARY, link_summary_rows, ["metric", "value"])
    write_csv(
        SCHEMA27_DUPLICATES,
        duplicate_audit_rows,
        ["app_id", "is_exact_duplicate_of_first_seen", "title", "pi", "institution", "notes"],
    )
    write_csv(
        SCHEMA4_UNMATCHED,
        unmatched_return_rows,
        ["archive_id", "application_id", "title", "availability", "personal", "notes"],
    )

    publication_year_rows = [
        {"year_pub": year, "publications": count}
        for year, count in sorted(Counter(pub.get("year_pub", "") for pub in publications).items())
    ]
    write_csv(PUBLICATION_YEAR_COUNTS, publication_year_rows, ["year_pub", "publications"])

    app_pub_count_distribution = Counter(
        int(row["schema24_publication_links"]) for row in master_rows
    )
    app_pub_count_rows = [
        {"publication_count": count, "applications": apps}
        for count, apps in sorted(app_pub_count_distribution.items())
    ]
    write_csv(
        APPLICATION_PUBLICATION_COUNT_DISTRIBUTION,
        app_pub_count_rows,
        ["publication_count", "applications"],
    )

    manifest = {
        "created_by": "scripts/stage2_build_project_universe.py",
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "sources": [
            {
                "name": "UKB Showcase Schema 4 returned datasets from applications",
                "url": "https://biobank.ndph.ox.ac.uk/ukb/scdown.cgi?fmt=txt&id=4",
                "local_path": str(SCHEMA4.relative_to(ROOT)),
            },
            {
                "name": "UKB Showcase Schema 27 approved applications",
                "url": "https://biobank.ndph.ox.ac.uk/ukb/scdown.cgi?fmt=txt&id=27",
                "local_path": str(SCHEMA27.relative_to(ROOT)),
            },
            {
                "name": "UKB Showcase Schema 19 publications",
                "url": "https://biobank.ndph.ox.ac.uk/ukb/scdown.cgi?fmt=txt&id=19",
                "local_path": str(SCHEMA19.relative_to(ROOT)),
            },
            {
                "name": "UKB Showcase Schema 24 publication-application links",
                "url": "https://biobank.ndph.ox.ac.uk/ukb/scdown.cgi?fmt=txt&id=24",
                "local_path": str(SCHEMA24.relative_to(ROOT)),
            },
        ],
        "notes": [
            "These are public UK Biobank Showcase metadata files.",
            "Schema 27 notes contain raw line breaks; the parser joins continuation lines into notes.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    report = f"""# Stage 2 Data Universe

This report is generated from public UK Biobank Showcase metadata only. It does
not contain participant-level UK Biobank data.

## Source Summary

| Source | Rows | Unique IDs | Duplicate IDs |
| --- | ---: | ---: | ---: |
| Schema 27 approved applications | {len(applications):,} raw records | {len(applications_unique):,} application IDs | {sum(1 for count in app_id_counts.values() if count > 1):,} duplicated IDs; {len(duplicate_audit_rows):,} repeated rows |
| Schema 19 publications | {len(publications):,} | {len(pub_id_counts):,} | {sum(1 for count in pub_id_counts.values() if count > 1):,} |
| Schema 24 app-publication links | {len(pub_links):,} | {len(link_pairs):,} unique app-pub pairs | {sum(count - 1 for count in link_pairs.values() if count > 1):,} duplicate link rows |
| Schema 4 returned datasets | {len(returned_datasets):,} | {len(archive_id_counts):,} archive IDs | {sum(1 for count in archive_id_counts.values() if count > 1):,} duplicated archive IDs |

## Linkage Summary

- Unique Schema 27 applications with at least one linked publication: {len(linked_apps):,}
- Unique Schema 27 applications without linked publication: {len(applications_unique) - len(linked_apps):,}
- Schema 24 links pointing to missing Schema 27 app IDs: {link_stats["links_to_missing_schema27_app"]:,}
- Schema 24 links pointing to missing Schema 19 publication IDs: {link_stats["links_to_missing_schema19_pub"]:,}
- Unique Schema 27 applications with at least one returned dataset: {len(apps_with_returns):,}
- Schema 4 returned dataset rows pointing to missing Schema 27 app IDs: {return_stats["returns_to_missing_schema27_app"]:,}

## Produced Files

- `{MASTER.relative_to(ROOT)}`
- `{SOURCE_SUMMARY.relative_to(ROOT)}`
- `{COVERAGE.relative_to(ROOT)}`
- `{LINK_SUMMARY.relative_to(ROOT)}`
- `{SCHEMA27_DUPLICATES.relative_to(ROOT)}`
- `{SCHEMA4_UNMATCHED.relative_to(ROOT)}`
- `{PUBLICATION_YEAR_COUNTS.relative_to(ROOT)}`
- `{APPLICATION_PUBLICATION_COUNT_DISTRIBUTION.relative_to(ROOT)}`
- `{MANIFEST.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")

    print(f"Wrote {MASTER.relative_to(ROOT)} with {len(master_rows):,} unique applications")
    print(f"Wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
