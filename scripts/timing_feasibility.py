#!/usr/bin/env python3
"""Build timing-feasibility outputs from recovered UKB project start dates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT / "data" / "intermediate" / "start_date_matching" / "stage2_5_app_start_dates.csv"
)
DEFAULT_OUTPUT_DIR = ROOT
POLICY_DATE = date(2024, 7, 5)
START_YEAR = 2023
END_YEAR = 2025


@dataclass(frozen=True)
class TimingPaths:
    working_universe: Path
    unmatched_audit: Path
    monthly_counts: Path
    quarterly_counts: Path
    window_counts: Path
    summary_json: Path
    report: Path
    figure: Path


def clean(value: object) -> str:
    return "" if value is None else str(value)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    days_in_month = [
        31,
        29 if year % 400 == 0 or (year % 4 == 0 and year % 100 != 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ][month - 1]
    return date(year, month, min(value.day, days_in_month))


def quarter(value: date) -> tuple[str, date, date]:
    quarter_number = (value.month - 1) // 3 + 1
    start_month = 3 * (quarter_number - 1) + 1
    start = date(value.year, start_month, 1)
    end = add_months(start, 3) - timedelta(days=1)
    return f"{value.year}Q{quarter_number}", start, end


def split_universe(
    rows: list[dict[str, str]], expected_working: int, expected_audit: int
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    working = [
        row
        for row in rows
        if row.get("website_match_status") == "matched_one_website_record"
        and row.get("start_date")
    ]
    audit = [row for row in rows if row.get("website_match_status") == "unmatched_schema27"]
    if len(working) != expected_working:
        raise ValueError(
            f"Expected {expected_working:,} working projects with a unique start date; "
            f"found {len(working):,}."
        )
    if len(audit) != expected_audit:
        raise ValueError(
            f"Expected {expected_audit:,} unmatched audit records; found {len(audit):,}."
        )
    if len(working) + len(audit) != len(rows):
        raise ValueError(
            "Input contains records outside the fixed working/audit timing split: "
            f"{len(rows):,} total, {len(working):,} working, {len(audit):,} audit."
        )
    return working, audit


def monthly_count_rows(start_dates: list[date]) -> list[dict[str, object]]:
    counts = Counter(d.strftime("%Y-%m") for d in start_dates if START_YEAR <= d.year <= END_YEAR)
    rows: list[dict[str, object]] = []
    current = date(START_YEAR, 1, 1)
    end = date(END_YEAR, 12, 1)
    while current <= end:
        key = current.strftime("%Y-%m")
        rows.append(
            {
                "month": key,
                "month_start": current.isoformat(),
                "month_end": (add_months(current, 1) - timedelta(days=1)).isoformat(),
                "new_projects": counts[key],
            }
        )
        current = add_months(current, 1)
    return rows


def quarterly_count_rows(start_dates: list[date]) -> list[dict[str, object]]:
    counts = Counter(quarter(d)[0] for d in start_dates if START_YEAR <= d.year <= END_YEAR)
    rows: list[dict[str, object]] = []
    current = date(START_YEAR, 1, 1)
    while current <= date(END_YEAR, 10, 1):
        label, start, end = quarter(current)
        rows.append(
            {
                "quarter": label,
                "quarter_start": start.isoformat(),
                "quarter_end": end.isoformat(),
                "new_projects": counts[label],
            }
        )
        current = add_months(current, 3)
    return rows


def window_count_rows(start_dates: list[date]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for months in (3, 6, 12):
        before_start = add_months(POLICY_DATE, -months)
        before_end = POLICY_DATE - timedelta(days=1)
        after_start = POLICY_DATE
        after_end = add_months(POLICY_DATE, months)
        rows.append(
            {
                "window_months": months,
                "policy_date": POLICY_DATE.isoformat(),
                "before_start_inclusive": before_start.isoformat(),
                "before_end_inclusive": before_end.isoformat(),
                "before_projects": sum(before_start <= d <= before_end for d in start_dates),
                "after_start_inclusive": after_start.isoformat(),
                "after_end_inclusive": after_end.isoformat(),
                "after_projects": sum(after_start <= d <= after_end for d in start_dates),
                "policy_date_counted_with": "after",
            }
        )
    return rows


def output_paths(output_dir: Path) -> TimingPaths:
    processed = output_dir / "data" / "intermediate" / "timing_feasibility"
    return TimingPaths(
        working_universe=processed / "timing_working_research_project_universe.csv",
        unmatched_audit=processed / "timing_unmatched_schema27_audit.csv",
        monthly_counts=processed / "timing_monthly_project_starts_2023_2025.csv",
        quarterly_counts=processed / "timing_quarterly_project_starts_2023_2025.csv",
        window_counts=processed / "timing_policy_window_counts.csv",
        summary_json=processed / "timing_feasibility_summary.json",
        report=output_dir / "reports" / "timing_feasibility.md",
        figure=output_dir / "figures" / "timing_project_starts_monthly_2023_2025.svg",
    )


def make_monthly_figure(monthly_rows: list[dict[str, object]], figure_path: Path) -> None:
    width = 980
    height = 420
    margin_left = 68
    margin_right = 32
    margin_top = 34
    margin_bottom = 72
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    max_count = max(int(row["new_projects"]) for row in monthly_rows) if monthly_rows else 0
    y_max = max(10, ((max_count + 9) // 10) * 10)
    bar_gap = 4
    bar_width = (plot_width - bar_gap * (len(monthly_rows) - 1)) / len(monthly_rows)

    def x_for_index(index: int) -> float:
        return margin_left + index * (bar_width + bar_gap)

    def y_for_count(count: int) -> float:
        return margin_top + plot_height - (count / y_max) * plot_height

    month_starts = [parse_iso_date(clean(row["month_start"])) for row in monthly_rows]
    total_days = (date(END_YEAR, 12, 31) - date(START_YEAR, 1, 1)).days
    policy_x = margin_left + ((POLICY_DATE - date(START_YEAR, 1, 1)).days / total_days) * plot_width

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        "<title>Monthly UKB project starts, 2023-2025</title>",
        "<desc>Monthly counts for fixed matched project universe with July 5 2024 marked.</desc>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{margin_left}" y="22" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#1f2937">Monthly project starts, 2023-2025</text>',
        f'<text x="{margin_left}" y="40" font-family="Arial, sans-serif" font-size="11" fill="#4b5563">Fixed universe: 6,935 projects with unique recovered UKB Projects website start dates</text>',
    ]

    for tick in range(0, y_max + 1, max(1, y_max // 5)):
        y = y_for_count(tick)
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="10" fill="#6b7280">{tick}</text>')

    for i, row in enumerate(monthly_rows):
        count = int(row["new_projects"])
        x = x_for_index(i)
        y = y_for_count(count)
        h = margin_top + plot_height - y
        fill = "#2563eb" if month_starts[i] < POLICY_DATE else "#059669"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{h:.1f}" fill="{fill}"/>')

    parts.append(f'<line x1="{policy_x:.1f}" y1="{margin_top}" x2="{policy_x:.1f}" y2="{margin_top + plot_height}" stroke="#dc2626" stroke-width="2"/>')
    parts.append(f'<text x="{policy_x + 6:.1f}" y="{margin_top + 14}" font-family="Arial, sans-serif" font-size="11" fill="#b91c1c">5 July 2024</text>')
    parts.append(f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{width - margin_right}" y2="{margin_top + plot_height}" stroke="#374151" stroke-width="1"/>')
    parts.append(f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#374151" stroke-width="1"/>')

    for i, row in enumerate(monthly_rows):
        month = clean(row["month"])
        if month.endswith("-01") or month.endswith("-04") or month.endswith("-07") or month.endswith("-10"):
            x = x_for_index(i) + bar_width / 2
            parts.append(f'<text x="{x:.1f}" y="{height - 44}" text-anchor="end" transform="rotate(-45 {x:.1f} {height - 44})" font-family="Arial, sans-serif" font-size="10" fill="#4b5563">{escape(month)}</text>')

    parts.append(f'<text x="{margin_left + plot_width / 2:.1f}" y="{height - 12}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#374151">Project start month</text>')
    parts.append(f'<text x="16" y="{margin_top + plot_height / 2:.1f}" text-anchor="middle" transform="rotate(-90 16 {margin_top + plot_height / 2:.1f})" font-family="Arial, sans-serif" font-size="11" fill="#374151">New projects</text>')
    parts.append("</svg>")

    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure_path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def markdown_table(rows: list[dict[str, object]], fields: list[str]) -> str:
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(clean(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def write_report(
    paths: TimingPaths,
    working_count: int,
    audit_count: int,
    monthly_rows: list[dict[str, object]],
    quarterly_rows: list[dict[str, object]],
    window_rows: list[dict[str, object]],
    source_commit: str,
) -> None:
    report = f"""# Timing Feasibility

Policy date: `{POLICY_DATE.isoformat()}`.

This step uses only the fixed working research-project universe: `{working_count:,}`
Schema 27 applications matched to the UKB Projects website with one recovered
start date. The `{audit_count:,}` unmatched Schema 27 records are excluded from
the working sample and retained only in the audit output.

These counts are for timing feasibility only. They describe project-start
cohort sizes around the policy date and must not be interpreted as a policy
effect. No treatment/control classification and no DID regression is run here.

Source commit: `{source_commit or "not recorded"}`.

## Policy Windows

The policy date itself is counted with the after-policy side.

{markdown_table(window_rows, ["window_months", "before_start_inclusive", "before_end_inclusive", "before_projects", "after_start_inclusive", "after_end_inclusive", "after_projects"])}

## Quarterly Counts

{markdown_table(quarterly_rows, ["quarter", "quarter_start", "quarter_end", "new_projects"])}

## Monthly Counts

{markdown_table(monthly_rows, ["month", "month_start", "month_end", "new_projects"])}

## Outputs

- `{display_path(paths.working_universe)}`
- `{display_path(paths.unmatched_audit)}`
- `{display_path(paths.monthly_counts)}`
- `{display_path(paths.quarterly_counts)}`
- `{display_path(paths.window_counts)}`
- `{display_path(paths.summary_json)}`
- `{display_path(paths.figure)}`
"""
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(report, encoding="utf-8")


def build_timing_outputs(
    input_path: Path,
    output_dir: Path,
    expected_working: int,
    expected_audit: int,
    source_commit: str,
) -> dict[str, object]:
    rows = read_rows(input_path)
    working, audit = split_universe(rows, expected_working, expected_audit)
    start_dates = [parse_iso_date(row["start_date"]) for row in working]
    paths = output_paths(output_dir)

    working_fields = [
        "app_id",
        "schema27_title",
        "schema27_institution",
        "schema27_pi",
        "start_date",
        "website_url",
        "website_match_status",
        "website_match_count",
        "match_methods",
    ]
    working_rows = [{field: row.get(field, "") for field in working_fields} for row in working]
    audit_fields = list(rows[0].keys()) if rows else []

    monthly_rows = monthly_count_rows(start_dates)
    quarterly_rows = quarterly_count_rows(start_dates)
    window_rows = window_count_rows(start_dates)

    write_csv(paths.working_universe, working_rows, working_fields)
    write_csv(paths.unmatched_audit, audit, audit_fields)
    write_csv(paths.monthly_counts, monthly_rows, ["month", "month_start", "month_end", "new_projects"])
    write_csv(paths.quarterly_counts, quarterly_rows, ["quarter", "quarter_start", "quarter_end", "new_projects"])
    write_csv(
        paths.window_counts,
        window_rows,
        [
            "window_months",
            "policy_date",
            "before_start_inclusive",
            "before_end_inclusive",
            "before_projects",
            "after_start_inclusive",
            "after_end_inclusive",
            "after_projects",
            "policy_date_counted_with",
        ],
    )
    make_monthly_figure(monthly_rows, paths.figure)

    summary = {
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source_commit": source_commit,
        "source_file": str(input_path.relative_to(ROOT)) if input_path.is_relative_to(ROOT) else str(input_path),
        "source_file_sha256": file_sha256(input_path),
        "policy_date": POLICY_DATE.isoformat(),
        "working_universe_projects": len(working),
        "unmatched_schema27_audit_records": len(audit),
        "monthly_count_years": [START_YEAR, END_YEAR],
        "window_counts": window_rows,
    }
    paths.summary_json.parent.mkdir(parents=True, exist_ok=True)
    paths.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(paths, len(working), len(audit), monthly_rows, quarterly_rows, window_rows, source_commit)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-working", type=int, default=6935)
    parser.add_argument("--expected-audit", type=int, default=132)
    parser.add_argument("--source-commit", default="")
    args = parser.parse_args(argv)

    summary = build_timing_outputs(
        input_path=args.input,
        output_dir=args.output_dir,
        expected_working=args.expected_working,
        expected_audit=args.expected_audit,
        source_commit=args.source_commit,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
