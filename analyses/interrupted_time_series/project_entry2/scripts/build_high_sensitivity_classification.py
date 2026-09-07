#!/usr/bin/env python3
"""Build project-level high-sensitivity proxies for project-entry ITS.

The module intentionally keeps this analysis separate from the existing
project_entry and comparative_exposure outputs. It reuses their upstream
project-level inputs but writes only under project_entry2.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA_DIR = PACKAGE / "data"
REPORT_DIR = PACKAGE / "reports"
SNAPSHOT_DIR = DATA_DIR / "source_snapshots"
FIELD_PAGE_DIR = SNAPSHOT_DIR / "field_pages"

PROJECT_UNIVERSE = (
    ROOT
    / "data"
    / "intermediate"
    / "timing_feasibility"
    / "timing_working_research_project_universe.csv"
)
STAGE3_CLASSIFICATION = (
    ROOT
    / "data"
    / "intermediate"
    / "rap_classification"
    / "stage3_project_rap_exposure_classification.csv"
)
CONTROL_EXPANSION_REVIEW = (
    ROOT
    / "data"
    / "intermediate"
    / "control_expansion"
    / "stage3_control_expansion_project_review.csv"
)
CONTROL_EXPANSION_DICTIONARY = (
    ROOT
    / "data"
    / "intermediate"
    / "control_expansion"
    / "stage3_control_expansion_evidence_dictionary.csv"
)

SCHEMA1_URL = "https://biobank.ndph.ox.ac.uk/ukb/scdown.cgi?fmt=txt&id=1"
FIELD_URL_TEMPLATE = "https://biobank.ndph.ox.ac.uk/ukb/field.cgi?id={field_id}"
POLICY_DATE = date(2024, 7, 5)

CONTROL_ORDER = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5, "C6": 6}
LOW_STRICT_MODALITIES = {
    "QUESTIONNAIRES_ASSESSMENT",
    "PHYSICAL_MEASURES",
    "ENVIRONMENT_GEOSPATIAL",
}
FIELD_FETCH_USER_AGENT = (
    "Mozilla/5.0 (compatible; UKB-empirical-project-entry2/1.0; "
    "research pipeline contact: public-source-audit)"
)


@dataclass(frozen=True)
class Outputs:
    classification: Path = DATA_DIR / "project_high_sensitivity_classification.csv"
    application_field_links: Path = DATA_DIR / "application_field_tier_links.csv"
    s3_field_dictionary: Path = DATA_DIR / "s3_field_dictionary.csv"
    s3_keyword_dictionary: Path = DATA_DIR / "s3_application_keyword_dictionary.csv"
    s3_text_audit_examples: Path = DATA_DIR / "s3_text_audit_examples.csv"
    field_tier_distribution: Path = DATA_DIR / "field_tier_distribution.csv"
    classification_counts: Path = DATA_DIR / "classification_counts.csv"
    classification_overlap: Path = DATA_DIR / "classification_overlap.csv"
    s3_field_review: Path = REPORT_DIR / "s3_field_review.md"
    source_manifest: Path = SNAPSHOT_DIR / "source_manifest.json"
    field_fetch_log: Path = SNAPSHOT_DIR / "field_fetch_log.csv"
    schema_snapshot: Path = SNAPSHOT_DIR / "ukb_schema1_fields.tsv"


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_date(value: str) -> date | None:
    value = clean(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y"):
        try:
            parsed = datetime.strptime(value[:19] if "T" in value else value[:10], fmt).date()
            return date(parsed.year, 1, 1) if fmt == "%Y" else parsed
        except ValueError:
            continue
    return None


def fmt(value: float | int | None, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f"{value:.{digits}f}"
    return str(value)


def yes(value: bool) -> int:
    return 1 if value else 0


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fetch_url(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": FIELD_FETCH_USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def ensure_schema_snapshot(path: Path, refresh: bool = False) -> bool:
    if path.exists() and not refresh:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fetch_url(SCHEMA1_URL))
    return True


def strip_tags(fragment: str) -> str:
    text = re.sub(r"(?i)<\s*(br|p|/p|/tr|/td|/th)\b[^>]*>", " ", fragment)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def tier_tokens(row: dict[str, str]) -> tuple[str, ...]:
    if clean(row.get("tier")):
        tokens = re.findall(r"[dos]\d+", clean(row["tier"]).lower())
        return tuple(dict.fromkeys(tokens))
    tokens: list[str] = []
    for prefix, col in [("d", "cost_do"), ("o", "cost_on"), ("s", "cost_sc")]:
        raw = clean(row.get(col))
        if not raw:
            continue
        try:
            value = int(float(raw))
        except ValueError:
            continue
        if value > 0:
            tokens.append(f"{prefix}{value}")
    return tuple(tokens)


def parse_field_schema(schema_path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in read_csv(schema_path, delimiter="\t"):
        tokens = tier_tokens(row)
        field_id = clean(row.get("field_id"))
        if not field_id:
            continue
        rows.append(
            {
                "field_id": field_id,
                "field_title": clean(row.get("title")),
                "field_tier": " ".join(tokens),
                "tier_source": "schema1_cost_do_cost_on_cost_sc",
                "has_s3": yes("s3" in tokens),
                "has_o2": yes("o2" in tokens),
                "field_private": yes(clean(row.get("private")) == "1"),
                "item_type": clean(row.get("item_type")),
                "main_category": clean(row.get("main_category")),
                "debut": clean(row.get("debut")),
                "version": clean(row.get("version")),
                "cost_do": clean(row.get("cost_do")),
                "cost_on": clean(row.get("cost_on")),
                "cost_sc": clean(row.get("cost_sc")),
                "num_participants": clean(row.get("num_participants")),
                "item_count": clean(row.get("item_count")),
                "field_notes": strip_tags(clean(row.get("notes"))),
            }
        )
    return rows


def parse_field_applications(page_html: str) -> list[dict[str, str]]:
    """Parse Application IDs from a UKB field page.

    The validation case in the task is field 25749, whose page currently has
    tier "o2 s3" and application links 17689 and 22783.
    """
    application_tab = page_html
    match = re.search(
        r"(?is)<h2>\s*\d+\s+Applications\s*</h2>(?P<body>.*?)(?:</table>|</div>)",
        page_html,
    )
    if match:
        application_tab = match.group("body")

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for row_match in re.finditer(r"(?is)<tr[^>]*>(?P<body>.*?)</tr>", application_tab):
        body = row_match.group("body")
        app_match = re.search(r"app\.cgi\?id=(?P<app_id>\d+)", body)
        if not app_match:
            app_match = re.search(r'id=["\']a(?P<app_id>\d+)["\']', row_match.group(0))
        if not app_match:
            continue
        app_id = app_match.group("app_id")
        if app_id in seen:
            continue
        seen.add(app_id)
        cells = re.findall(r"(?is)<td[^>]*>(.*?)</td>", body)
        title = strip_tags(cells[-1]) if len(cells) >= 2 else ""
        rows.append({"app_id": app_id, "application_title_from_field_page": title})
    return rows


def field_candidate(row: dict[str, object]) -> bool:
    return bool(row["has_s3"] or row["has_o2"] or row["field_private"])


def fetch_field_links(
    fields: list[dict[str, object]],
    out: Outputs,
    refresh_pages: bool = False,
    no_fetch_pages: bool = False,
    sleep_seconds: float = 0.05,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    FIELD_PAGE_DIR.mkdir(parents=True, exist_ok=True)
    links: list[dict[str, object]] = []
    fetch_log: list[dict[str, object]] = []
    now = datetime.now(UTC).isoformat(timespec="seconds")
    candidates = [row for row in fields if field_candidate(row)]

    for idx, field in enumerate(candidates, start=1):
        field_id = str(field["field_id"])
        cache_path = FIELD_PAGE_DIR / f"field_{field_id}.html"
        source_url = FIELD_URL_TEMPLATE.format(field_id=field_id)
        status = "cache"
        error = ""
        if (refresh_pages or not cache_path.exists()) and not no_fetch_pages:
            try:
                cache_path.write_bytes(fetch_url(source_url))
                status = "fetched"
                if sleep_seconds > 0 and idx < len(candidates):
                    time.sleep(sleep_seconds)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                status = "fetch_error"
                error = str(exc)
        elif no_fetch_pages and not cache_path.exists():
            status = "missing_cache_no_fetch"
            error = "field page cache unavailable and --no-fetch-field-pages set"

        applications: list[dict[str, str]] = []
        if cache_path.exists():
            page = cache_path.read_text(encoding="utf-8", errors="replace")
            applications = parse_field_applications(page)
            if field_id == "25749":
                found_ids = {row["app_id"] for row in applications}
                if not {"17689", "22783"}.issubset(found_ids):
                    status = "parser_validation_warning"
                    error = "field 25749 parser did not recover expected applications 17689 and 22783"

        fetch_log.append(
            {
                "field_id": field_id,
                "source_url": source_url,
                "snapshot_path": relpath(cache_path),
                "status": status,
                "application_links_parsed": len(applications),
                "error": error,
                "checked_at_utc": now,
            }
        )
        for app in applications:
            links.append(
                {
                    "app_id": app["app_id"],
                    "field_id": field_id,
                    "field_title": field["field_title"],
                    "field_tier": field["field_tier"],
                    "tier_source": field["tier_source"],
                    "field_private": field["field_private"],
                    "item_type": field["item_type"],
                    "main_category": field["main_category"],
                    "debut": field["debut"],
                    "version": field["version"],
                    "has_s3": field["has_s3"],
                    "has_o2": field["has_o2"],
                    "application_title_from_field_page": app["application_title_from_field_page"],
                    "source_url": source_url,
                    "snapshot_path": relpath(cache_path),
                    "fetched_or_checked_at_utc": now,
                }
            )
    return links, fetch_log


def parse_modalities(value: str) -> set[str]:
    return {part.strip() for part in re.split(r"[|;]", clean(value)) if part.strip()}


SEQUENCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("WES", re.compile(r"\bWES\b", re.IGNORECASE)),
    ("WGS", re.compile(r"\bWGS\b", re.IGNORECASE)),
    (
        "whole exome sequencing",
        re.compile(r"\bwhole[- ]exome[- ]sequenc(?:ing|e|ed|es)?\b", re.IGNORECASE),
    ),
    (
        "whole genome sequencing",
        re.compile(r"\bwhole[- ]genome[- ]sequenc(?:ing|e|ed|es)?\b", re.IGNORECASE),
    ),
    ("exome sequence/data", re.compile(r"\bexome (?:sequenc(?:ing|e|ed|es)?|data|variants?)\b", re.IGNORECASE)),
    (
        "genome sequence/data",
        re.compile(r"\b(?:genome|genomic) (?:sequenc(?:ing|e|ed|es)? data|sequence|sequencing)\b", re.IGNORECASE),
    ),
    ("sequenced genomes/exomes", re.compile(r"\bsequenced (?:genomes?|exomes?)\b", re.IGNORECASE)),
    ("OQFE", re.compile(r"\bOQFE\b", re.IGNORECASE)),
    ("GLnexus/DeepVariant/WeCall", re.compile(r"\b(?:GLnexus|DeepVariant|WeCall)\b", re.IGNORECASE)),
    ("pVCF/gVCF", re.compile(r"\b[pg]VCFs?\b", re.IGNORECASE)),
    ("CRAM/FASTQ", re.compile(r"\b(?:CRAMs?|FASTQs?)\b", re.IGNORECASE)),
    ("DRAGEN", re.compile(r"\bDRAGEN\b", re.IGNORECASE)),
    ("GraphTyper/BWA/GATK sequence calls", re.compile(r"\bGraphTyper\b|BWA[- ]mem|GATK[^.]{0,80}variant call", re.IGNORECASE)),
    ("WGS structural variant products", re.compile(r"\bManta[- ]called\b|\bExpansionHunter\b|whole genome (?:SV|STR|CNV)\b", re.IGNORECASE)),
    ("phased sequence data", re.compile(r"\bphased sequence\b|BEAGLE Phased VCFs?|SHAPEIT Phased VCFs?", re.IGNORECASE)),
    ("rare coding variants", re.compile(r"\brare coding variants?\b|\bcoding variation\b", re.IGNORECASE)),
    (
        "loss-of-function / pLoF / protein-truncating variants",
        re.compile(
            r"\bprotein[- ]truncating variants?\b|\bpLoF\b|predicted loss[- ]of[- ]function|"
            r"\bloss[- ]of[- ]function variants?\b|\bLoF variants?\b|loss of function genetic variants",
            re.IGNORECASE,
        ),
    ),
    (
        "missense/nonsense/rare functional variants",
        re.compile(
            r"\bnonsense (?:and )?missense\b|\brare functional variants?\b|"
            r"\brare protein[- ]altering variants?\b|\bdeleterious exonic variants?\b|"
            r"\brare deleterious variants?\b|\bprotein coding variants?\b",
            re.IGNORECASE,
        ),
    ),
    ("gene/variant burden or collapsing analysis", re.compile(r"\bgene[- ]based burden\b|\bvariant burden\b|\bburden test\b|\bcollapsing analysis\b", re.IGNORECASE)),
    ("human gene knockouts", re.compile(r"\bhuman gene knockouts?\b", re.IGNORECASE)),
)

SEQUENCE_DICTIONARY_PREFIXES = ("C1_", "C2_", "C3_")

CATEGORY_LABELS = {
    "1000": "Embargoed imaging replicas",
    "539": "PANDORA brain imaging outputs",
    "507": "Brain MRI source files",
    "102": "Heart MRI source files",
    "201": "Native diffusion MRI parcellations",
    "202": "Native surface and segmentation files",
    "101": "Carotid ultrasound source files",
    "131": "Pancreas imaging source files",
    "156": "Kidney imaging source files",
    "126": "Liver imaging source files",
    "109": "SWI/QSM brain imaging files",
    "110": "T1 structural brain files",
    "103": "DXA image files",
    "105": "Internal fat DICOM files",
    "106": "Task fMRI NIFTI files",
    "107": "Diffusion MRI NIFTI files",
    "111": "Resting fMRI NIFTI files",
    "112": "T2 FLAIR NIFTI files",
    "119": "ASL NIFTI files",
    "198": "fMRI CIFTI files",
    "200": "MNI transform files",
    "538": "Cardiac mesh files",
}

BANNED_S3_TERMS = {
    "brain",
    "genetic",
    "health",
    "data",
    "image",
    "images",
    "imaging",
    "mri",
    "native",
    "functional",
    "structural",
    "resting",
    "task",
    "field",
    "linked",
    "unlinked",
    "embargoed",
}

S3_ACRONYM_TERMS = {"dicom", "nifti", "dmri", "fmri", "rfmri", "tfmri", "cifti", "swi", "qsm"}

S3_SIGNAL_WORDS = {
    "asl",
    "aortic",
    "aparc",
    "biventricular",
    "brain",
    "cardiac",
    "carotid",
    "cifti",
    "cine",
    "dicom",
    "diffusion",
    "dmri",
    "dxa",
    "flair",
    "fmri",
    "glasser",
    "heart",
    "kidney",
    "liver",
    "magnetic resonance",
    "mesh",
    "mni",
    "mri",
    "nifti",
    "pancreas",
    "pandora",
    "qsm",
    "raw carotid",
    "raw imaging",
    "rfmri",
    "schaefer",
    "scan",
    "segmentation",
    "shmolli",
    "swi",
    "susceptibility",
    "t1",
    "t2",
    "tfmri",
    "ultrasound",
}


def normalize_for_match(value: object) -> str:
    text = clean(value)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9+]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def phrase_in_text(term: str, text: str) -> bool:
    term_norm = normalize_for_match(term)
    text_norm = normalize_for_match(text)
    return bool(term_norm) and f" {term_norm} " in f" {text_norm} "


def compact_excerpt(text: object, term: str = "", width: int = 260) -> str:
    raw = re.sub(r"\s+", " ", clean(text))
    if not raw:
        return ""
    if term:
        first_token = normalize_for_match(term).split(" ")[0]
        match = re.search(re.escape(first_token), raw, flags=re.IGNORECASE) if first_token else None
        if match:
            start = max(match.start() - 90, 0)
            end = min(match.end() + 170, len(raw))
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(raw) else ""
            return prefix + raw[start:end].strip() + suffix
    return raw[:width].rstrip() + ("..." if len(raw) > width else "")


def project_text_sources(project: dict[str, str], stage3: dict[str, str]) -> list[tuple[str, str]]:
    return [
        ("schema27_title", clean(project.get("schema27_title")) or clean(stage3.get("schema27_title"))),
        ("schema27_notes", clean(stage3.get("schema27_notes"))),
        ("website_excerpt", clean(stage3.get("website_excerpt"))),
        ("source_text_evidence", clean(stage3.get("source_text_evidence"))),
    ]


def sequence_match(project: dict[str, str], stage3: dict[str, str], review: dict[str, str]) -> dict[str, str]:
    candidates = [
        ("stage3_already_rap_modalities", stage3.get("already_rap_modalities", "")),
        ("stage3_matched_terms", stage3.get("matched_terms", "")),
        ("stage3_source_text_evidence", stage3.get("source_text_evidence", "")),
        ("schema27_title", clean(project.get("schema27_title")) or clean(stage3.get("schema27_title"))),
        ("schema27_notes", stage3.get("schema27_notes", "")),
        ("website_excerpt", stage3.get("website_excerpt", "")),
        ("control_inferred_product", review.get("inferred_underlying_data_product_or_rap_use", "")),
        ("control_matched_term", review.get("matched_term_or_expression", "")),
        ("control_supporting_excerpt", review.get("supporting_text_excerpt", "")),
        ("control_previous_already_rap_modalities", review.get("previous_already_rap_modalities", "")),
        ("control_schema27_title", review.get("schema27_title", "")),
        ("control_dictionary_term_id", review.get("evidence_dictionary_term_id", "")),
    ]
    for source, value in candidates:
        text = clean(value)
        if not text:
            continue
        term_id = clean(review.get("evidence_dictionary_term_id", ""))
        if source == "control_dictionary_term_id" and term_id.startswith(SEQUENCE_DICTIONARY_PREFIXES):
            return {
                "matched": "1",
                "term": term_id,
                "source": source,
                "excerpt": compact_excerpt(review.get("matched_term_or_expression", term_id), term_id),
            }
        for label, pattern in SEQUENCE_PATTERNS:
            if pattern.search(text):
                return {"matched": "1", "term": label, "source": source, "excerpt": compact_excerpt(text, label)}
    return {"matched": "0", "term": "", "source": "", "excerpt": ""}


def s3_fields(fields: list[dict[str, object]]) -> list[dict[str, object]]:
    return [field for field in fields if int(field.get("has_s3", 0)) == 1]


def s3_field_family(field: dict[str, object]) -> str:
    title = normalize_for_match(field.get("field_title", ""))
    category = clean(field.get("main_category"))
    if category == "539" or any(token in title for token in ["brain", "dmri", "fmri", "rfmri", "tfmri", "pandora", "mni", "cifti", "swi", "qsm", "glasser", "schaefer", "subcortex", "aparc"]):
        return "Brain MRI/imaging"
    if any(token in title for token in ["heart", "cardiac", "aortic", "ventricular", "cine"]):
        return "Cardiac MRI/imaging"
    if "carotid" in title or "ultrasound" in title:
        return "Carotid ultrasound"
    if "liver" in title:
        return "Liver imaging"
    if "kidney" in title:
        return "Kidney imaging"
    if "pancreas" in title or "pancreatic" in title:
        return "Pancreas imaging"
    if "dxa" in title:
        return "DXA imaging"
    if "internal fat" in title:
        return "Abdominal/internal fat imaging"
    return CATEGORY_LABELS.get(category, "Other s3 imaging/file field")


def s3_field_dictionary_rows(fields: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for field in sorted(s3_fields(fields), key=lambda row: int(str(row["field_id"]))):
        rows.append(
            {
                "field_id": field["field_id"],
                "field_title": field["field_title"],
                "main_category": field["main_category"],
                "item_type": field["item_type"],
                "field_tier": field["field_tier"],
                "debut": field["debut"],
                "private": field["field_private"],
            }
        )
    return rows


def display_title_term(title: object) -> str:
    text = clean(title)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"\s+-\s+", " ", text)
    text = re.sub(r"(?i)^embargoed (?:linked|unlinked)\s*:?\s*", "", text)
    text = re.sub(r"^[\s:;-]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    for before, after in [
        ("rf MRI", "rfMRI"),
        ("tf MRI", "tfMRI"),
        ("f MRI", "fMRI"),
        ("d MRI", "dMRI"),
        ("Sh Mo LLI", "ShMoLLI"),
    ]:
        text = text.replace(before, after)
    return text


def useful_s3_term(term: str) -> bool:
    norm = normalize_for_match(term)
    if not norm or norm in BANNED_S3_TERMS:
        return False
    words = norm.split()
    if len(words) == 1:
        return norm in S3_ACRONYM_TERMS
    return any(signal in norm for signal in S3_SIGNAL_WORDS)


def source_category(fields: list[dict[str, object]]) -> str:
    families = sorted({s3_field_family(field) for field in fields})
    return families[0] if len(families) == 1 else "Mixed s3 imaging/file fields"


def build_s3_keyword_dictionary(fields: list[dict[str, object]]) -> list[dict[str, object]]:
    source_fields = s3_fields(fields)
    terms: dict[str, dict[str, object]] = {}

    def add(term: str, selected: list[dict[str, object]], precision_level: str, reason: str) -> None:
        if not selected or not useful_s3_term(term):
            return
        norm = normalize_for_match(term)
        payload = terms.setdefault(
            norm,
            {
                "term": term,
                "source_fields": {},
                "precision_level": precision_level,
                "reason": reason,
            },
        )
        payload["precision_level"] = min(str(payload["precision_level"]), precision_level)
        payload["reason"] = reason if len(reason) > len(str(payload["reason"])) else payload["reason"]
        for field in selected:
            payload["source_fields"][str(field["field_id"])] = field  # type: ignore[index]

    for field in source_fields:
        title_term = display_title_term(field["field_title"])
        add(title_term, [field], "field_title_exact", "normalized exact title of an s3 Schema 1 field")
        stripped = re.sub(r"(?i)\s+(?:DICOM|NIFTI|CIFTI|MAT format|replicas?)$", "", title_term).strip()
        add(stripped, [field], "field_title_stem", "specific s3 field title after file-format suffix removal")

    def fields_matching(*needles: str) -> list[dict[str, object]]:
        return [
            field
            for field in source_fields
            if any(needle in normalize_for_match(field["field_title"]) for needle in needles)
        ]

    family_terms = [
        ("DICOM", fields_matching("dicom"), "file_format", "DICOM appears in many s3 raw imaging field titles"),
        ("NIFTI", fields_matching("nifti"), "file_format", "NIFTI appears in s3 brain MRI field titles"),
        ("CIFTI", fields_matching("cifti"), "file_format", "CIFTI appears in an s3 fMRI connectivity field title"),
        ("brain MRI", fields_matching("brain"), "field_family_phrase", "brain MRI source files dominate the s3 dictionary"),
        ("brain imaging", fields_matching("brain", "pandora"), "field_family_phrase", "brain imaging titles and PANDORA outputs are s3 fields"),
        ("brain scan", fields_matching("brain scans", "brain"), "field_family_phrase", "brain scan source files are s3 fields"),
        ("brain scans", fields_matching("brain scans", "brain"), "field_family_phrase", "brain scan source files are s3 fields"),
        ("MRI scan", fields_matching("mri", "brain scans"), "field_family_phrase", "MRI scan files appear in s3 field titles"),
        ("MRI scans", fields_matching("mri", "brain scans"), "field_family_phrase", "MRI scan files appear in s3 field titles"),
        ("magnetic resonance imaging", fields_matching("mri", "brain scans"), "field_family_phrase", "MRI source-file fields are in the s3 dictionary"),
        ("raw imaging", fields_matching("dicom", "nifti", "cifti", "raw carotid"), "field_family_phrase", "s3 fields include raw imaging/file-format products"),
        ("raw imaging data", fields_matching("dicom", "nifti", "cifti", "raw carotid"), "field_family_phrase", "s3 fields include raw imaging/file-format products"),
        ("functional MRI", fields_matching("functional brain", "fmri"), "field_family_phrase", "functional brain MRI files are s3 fields"),
        ("fMRI", fields_matching("functional brain", "fmri"), "acronym", "fMRI files and outputs are s3 fields"),
        ("resting-state imaging", fields_matching("resting", "rfmri"), "field_family_phrase", "resting functional brain imaging fields are s3 fields"),
        ("resting state imaging", fields_matching("resting", "rfmri"), "field_family_phrase", "resting functional brain imaging fields are s3 fields"),
        ("rfMRI", fields_matching("rfmri", "resting"), "acronym", "resting fMRI fields are s3 fields"),
        ("tfMRI", fields_matching("tfmri", "task"), "acronym", "task fMRI fields are s3 fields"),
        ("task fMRI", fields_matching("task", "tfmri"), "field_family_phrase", "task fMRI fields are s3 fields"),
        ("diffusion MRI", fields_matching("diffusion", "dmri"), "field_family_phrase", "diffusion MRI fields are s3 fields"),
        ("dMRI", fields_matching("diffusion", "dmri"), "acronym", "diffusion MRI fields are s3 fields"),
        ("T1 structural", fields_matching("t1 structural"), "field_family_phrase", "T1 structural brain files are s3 fields"),
        ("T2 FLAIR", fields_matching("t2 flair"), "field_family_phrase", "T2 FLAIR brain files are s3 fields"),
        ("SWI", fields_matching("susceptibility weighted", "swi"), "acronym", "susceptibility-weighted imaging fields are s3 fields"),
        ("QSM", fields_matching("quantitative susceptibility", "qsm"), "acronym", "quantitative susceptibility mapping fields are s3 fields"),
        ("susceptibility weighted imaging", fields_matching("susceptibility weighted"), "field_family_phrase", "susceptibility-weighted brain imaging files are s3 fields"),
        ("quantitative susceptibility mapping", fields_matching("quantitative susceptibility"), "field_family_phrase", "QSM brain imaging files are s3 fields"),
        ("arterial spin labelling", fields_matching("arterial spin"), "field_family_phrase", "ASL brain imaging files are s3 fields"),
        ("MNI native transform", fields_matching("mni native transform"), "field_title_stem", "MNI transform files are s3 fields"),
        ("surface model", fields_matching("surface model"), "field_family_phrase", "surface model files are s3 fields"),
        ("structural segmentations", fields_matching("segmentations"), "field_family_phrase", "structural segmentation files are s3 fields"),
        ("cardiac MRI", fields_matching("heart", "cardiac"), "field_family_phrase", "heart/cardiac MRI source files are s3 fields"),
        ("heart MRI", fields_matching("heart"), "field_family_phrase", "heart MRI source files are s3 fields"),
        ("cardiac imaging", fields_matching("heart", "cardiac"), "field_family_phrase", "cardiac imaging source files are s3 fields"),
        ("cardiac biventricular mesh", fields_matching("biventricular mesh"), "field_title_stem", "cardiac mesh model field is s3"),
        ("cine tagging", fields_matching("cine tagging"), "field_title_stem", "cine-tagging heart images are s3 fields"),
        ("carotid ultrasound", fields_matching("carotid", "ultrasound"), "field_family_phrase", "carotid ultrasound files are s3 fields"),
        ("carotid artery ultrasound", fields_matching("carotid artery ultrasound"), "field_family_phrase", "carotid artery ultrasound files are s3 fields"),
        ("raw carotid device data", fields_matching("raw carotid device"), "field_title_exact", "raw carotid device data is an s3 field"),
        ("liver imaging", fields_matching("liver imaging"), "field_family_phrase", "liver DICOM imaging files are s3 fields"),
        ("kidney imaging", fields_matching("kidney imaging"), "field_family_phrase", "kidney DICOM imaging files are s3 fields"),
        ("pancreas imaging", fields_matching("pancreas", "pancreatic"), "field_family_phrase", "pancreas DICOM imaging files are s3 fields"),
        ("DXA images", fields_matching("dxa"), "field_title_stem", "DXA image files are s3 fields"),
    ]
    for term, selected, precision_level, reason in family_terms:
        add(term, selected, precision_level, reason)

    rows = []
    for payload in terms.values():
        selected = list(payload["source_fields"].values())  # type: ignore[union-attr]
        selected = sorted(selected, key=lambda field: int(str(field["field_id"])))
        rows.append(
            {
                "term": payload["term"],
                "term_normalized": normalize_for_match(payload["term"]),
                "source_field_ids": evidence_list([str(field["field_id"]) for field in selected], max_items=199),
                "source_field_titles": evidence_list([str(field["field_title"]) for field in selected], max_items=12),
                "source_category": source_category(selected),
                "precision_level": payload["precision_level"],
                "reason": payload["reason"],
            }
        )
    return sorted(rows, key=lambda row: (-len(normalize_for_match(row["term"]).split()), str(row["term"]).lower()))


def match_s3_text(
    project: dict[str, str],
    stage3: dict[str, str],
    keyword_rows: list[dict[str, object]],
) -> dict[str, str]:
    sources = [
        (source_name, source_text, f" {normalize_for_match(source_text)} ")
        for source_name, source_text in project_text_sources(project, stage3)
        if clean(source_text)
    ]
    for keyword in keyword_rows:
        term = clean(keyword.get("term"))
        term_norm = clean(keyword.get("term_normalized")) or normalize_for_match(term)
        if not term_norm:
            continue
        needle = f" {term_norm} "
        for source_name, source_text, source_norm in sources:
            if needle in source_norm:
                return {
                    "matched": "1",
                    "term": term,
                    "source": source_name,
                    "source_field_ids": clean(keyword.get("source_field_ids")),
                    "source_field_titles": clean(keyword.get("source_field_titles")),
                    "source_category": clean(keyword.get("source_category")),
                    "reason": clean(keyword.get("reason")),
                    "excerpt": compact_excerpt(source_text, term),
                }
    return {
        "matched": "0",
        "term": "",
        "source": "",
        "source_field_ids": "",
        "source_field_titles": "",
        "source_category": "",
        "reason": "",
        "excerpt": "",
    }


def load_control_layers(review_rows: list[dict[str, str]]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    layer_by_app: dict[str, str] = {}
    review_by_app: dict[str, dict[str, str]] = {}
    for row in review_rows:
        app_id = clean(row.get("app_id"))
        layer = clean(row.get("expansion_layer"))
        if app_id and layer in CONTROL_ORDER and (
            app_id not in layer_by_app
            or CONTROL_ORDER[layer] < CONTROL_ORDER[layer_by_app[app_id]]
        ):
            layer_by_app[app_id] = layer
            review_by_app[app_id] = row
    return layer_by_app, review_by_app


def aggregate_field_links(field_links: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    by_app: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in field_links:
        by_app[str(row["app_id"])].append(row)

    out: dict[str, dict[str, object]] = {}
    for app_id, rows in by_app.items():
        unique_fields = {str(row["field_id"]): row for row in rows}
        s3_fields = [row for row in unique_fields.values() if int(row["has_s3"]) == 1]
        o2_fields = [row for row in unique_fields.values() if int(row["has_o2"]) == 1]
        restricted_fields = [row for row in unique_fields.values() if int(row["field_private"]) == 1]
        out[app_id] = {
            "rows": list(unique_fields.values()),
            "linked_field_count": len(unique_fields),
            "linked_s3_field_count": len(s3_fields),
            "linked_o2_field_count": len(o2_fields),
            "linked_restricted_field_count": len(restricted_fields),
            "s3_field_ids": sorted(str(row["field_id"]) for row in s3_fields),
            "o2_field_ids": sorted(str(row["field_id"]) for row in o2_fields),
            "restricted_field_ids": sorted(str(row["field_id"]) for row in restricted_fields),
        }
    return out


def field_timing_counts(
    field_rows: list[dict[str, object]],
    start: date | None,
) -> dict[str, object]:
    s3_current = []
    o2_current = []
    restricted_current = []
    s3_conservative = []
    after_start = []

    for row in field_rows:
        debut = parse_date(clean(row.get("debut")))
        is_after = bool(start and debut and debut > start)
        if is_after:
            after_start.append(str(row["field_id"]))
        if int(row.get("has_s3", 0)) == 1:
            s3_current.append(row)
            if start and debut and debut <= start:
                s3_conservative.append(row)
        if int(row.get("has_o2", 0)) == 1:
            o2_current.append(row)
        if int(row.get("field_private", 0)) == 1:
            restricted_current.append(row)
    return {
        "hs_s3_field": bool(s3_current),
        "hs_o2_field": bool(o2_current),
        "hs_restricted_field": bool(restricted_current),
        "hs_s3_field_timing_conservative": bool(s3_conservative),
        "linked_s3_field_count_timing_conservative": len(s3_conservative),
        "field_debut_after_project_start": bool(after_start),
        "field_debut_after_project_start_ids": after_start,
    }


def evidence_list(values: list[str], max_items: int = 10) -> str:
    kept = [clean(v) for v in values if clean(v)]
    if len(kept) <= max_items:
        return "; ".join(kept)
    return "; ".join(kept[:max_items]) + f"; ... +{len(kept) - max_items} more"


def build_project_classification_rows(
    projects: list[dict[str, str]],
    stage3_rows: list[dict[str, str]],
    control_review_rows: list[dict[str, str]],
    field_links: list[dict[str, object]],
    s3_keyword_rows: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    stage3_by_app = {clean(row.get("app_id")): row for row in stage3_rows}
    layer_by_app, review_by_app = load_control_layers(control_review_rows)
    field_by_app = aggregate_field_links(field_links)
    s3_keyword_rows = s3_keyword_rows or []

    rows: list[dict[str, object]] = []
    for project in projects:
        app_id = clean(project.get("app_id"))
        start = parse_date(clean(project.get("start_date")))
        st3 = stage3_by_app.get(app_id, {})
        review = review_by_app.get(app_id, {})
        layer = layer_by_app.get(app_id, "")
        fields = field_by_app.get(app_id, {})
        linked_rows = fields.get("rows", [])
        timing = field_timing_counts(linked_rows, start)

        sequence = sequence_match(project, st3, review)
        s3_text = match_s3_text(project, st3, s3_keyword_rows)
        hs_wes_wgs_sequence = sequence["matched"] == "1"
        hs_s3_direct = bool(timing["hs_s3_field"])
        hs_s3_text = s3_text["matched"] == "1"
        hs_o2 = bool(timing["hs_o2_field"])
        hs_restricted = bool(timing["hs_restricted_field"])
        high_sensitivity = hs_wes_wgs_sequence or hs_s3_direct or hs_s3_text
        lower_sensitivity = not high_sensitivity

        legacy_modalities = parse_modalities(st3.get("legacy_route_modalities", ""))
        low_strict = (
            bool(legacy_modalities)
            and legacy_modalities.issubset(LOW_STRICT_MODALITIES)
            and not high_sensitivity
            and not hs_restricted
        )

        sources = []
        details = []
        reasons = []
        if hs_wes_wgs_sequence:
            sources.append("explicit WES/WGS or sequence-product evidence")
            details.append(f"{sequence['source']}={sequence['term']}")
            reasons.append("concrete WES/WGS, sequence data, or sequence-product term in observable evidence")
        if hs_s3_direct:
            sources.append("direct UKB field tier s3 link")
            details.append("s3_field_ids=" + evidence_list(fields.get("s3_field_ids", [])))
            reasons.append("linked current UKB field page has tier token s3")
        if hs_s3_text:
            sources.append("S3-derived application text")
            details.append(
                f"{s3_text['source']} term={s3_text['term']} field_family={s3_text['source_category']}"
            )
            reasons.append("application text matched high-precision term derived from the 199 s3 Schema 1 fields")
        if hs_o2:
            details.append("o2_field_ids=" + evidence_list(fields.get("o2_field_ids", [])))
        if hs_restricted:
            details.append("restricted_field_ids=" + evidence_list(fields.get("restricted_field_ids", [])))
        if low_strict:
            sources.append("Stage 3 low-granularity legacy modality")
            details.append("legacy_modalities=" + "|".join(sorted(legacy_modalities)))
            reasons.append("only strict low-granularity legacy modality evidence and no high flags")
        if not sources:
            sources.append("lower-sensitivity comparison complement")
            reasons.append("no identified high evidence under the observable proxy")

        rows.append(
            {
                "app_id": app_id,
                "start_date": start.isoformat() if start else "",
                "month": start.strftime("%Y-%m") if start else "",
                "pre_post_july_2024": "post_july_2024" if start and start >= POLICY_DATE else "pre_july_2024",
                "title": project.get("schema27_title", "") or st3.get("schema27_title", ""),
                "institution": project.get("schema27_institution", "") or st3.get("schema27_institution", ""),
                "website_url": project.get("website_url", "") or st3.get("website_url", ""),
                "HIGH_SENSITIVITY": yes(high_sensitivity),
                "LOWER_SENSITIVITY_COMPARISON": yes(lower_sensitivity),
                "LOW_STRICT": yes(low_strict),
                "hs_wes_wgs_sequence": yes(hs_wes_wgs_sequence),
                "hs_s3_direct": yes(hs_s3_direct),
                "hs_s3_text": yes(hs_s3_text),
                "hs_o2_field": yes(hs_o2),
                "hs_restricted_field": yes(hs_restricted),
                "linked_field_count": fields.get("linked_field_count", 0),
                "linked_s3_field_count": fields.get("linked_s3_field_count", 0),
                "linked_s3_field_count_timing_conservative": timing[
                    "linked_s3_field_count_timing_conservative"
                ],
                "linked_o2_field_count": fields.get("linked_o2_field_count", 0),
                "linked_restricted_field_count": fields.get("linked_restricted_field_count", 0),
                "field_debut_after_project_start": yes(bool(timing["field_debut_after_project_start"])),
                "field_debut_after_project_start_ids": evidence_list(
                    timing["field_debut_after_project_start_ids"]
                ),
                "control_layer": layer,
                "control_evidence_type": review.get("evidence_type", ""),
                "control_matched_term": review.get("matched_term_or_expression", ""),
                "control_inferred_product": review.get("inferred_underlying_data_product_or_rap_use", ""),
                "previous_classification": st3.get("classification", ""),
                "previous_confidence": st3.get("confidence", ""),
                "legacy_route_modalities": st3.get("legacy_route_modalities", ""),
                "already_rap_modalities": st3.get("already_rap_modalities", ""),
                "hs_sequence_product_term": sequence["term"],
                "hs_sequence_product_source": sequence["source"],
                "hs_sequence_product_excerpt": sequence["excerpt"],
                "hs_s3_text_term": s3_text["term"],
                "hs_s3_text_source": s3_text["source"],
                "hs_s3_text_source_field_ids": s3_text["source_field_ids"],
                "hs_s3_text_source_field_titles": s3_text["source_field_titles"],
                "hs_s3_text_family": s3_text["source_category"],
                "hs_s3_text_excerpt": s3_text["excerpt"],
                "evidence_source": evidence_list(sources),
                "evidence_detail": evidence_list(details),
                "classification_reason": evidence_list(reasons),
            }
        )
    return rows


def classification_count_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    definitions = [
        "HIGH_SENSITIVITY",
        "LOWER_SENSITIVITY_COMPARISON",
        "hs_wes_wgs_sequence",
        "hs_s3_direct",
        "hs_s3_text",
        "LOW_STRICT",
        "hs_o2_field",
        "hs_restricted_field",
    ]
    output = []
    for period in ["all", "pre_july_2024", "post_july_2024"]:
        subset = rows if period == "all" else [r for r in rows if r["pre_post_july_2024"] == period]
        denom = len(subset)
        for definition in definitions:
            count = sum(int(r[definition]) for r in subset)
            output.append(
                {
                    "period": period,
                    "definition": definition,
                    "count": count,
                    "universe_n": denom,
                    "share": fmt(count / denom if denom else math.nan, 6),
                }
            )
    return output


def classification_overlap_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    channels = [
        ("hs_wes_wgs_sequence", "WES/WGS_SEQUENCE"),
        ("hs_s3_direct", "DIRECT_S3_FIELD_LINK"),
        ("hs_s3_text", "S3_DERIVED_APPLICATION_TEXT"),
    ]
    output = []
    prior_ids: set[str] = set()
    wes_ids = {str(r["app_id"]) for r in rows if int(r["hs_wes_wgs_sequence"]) == 1}
    for order, (flag, label) in enumerate(channels, start=1):
        channel_ids = {str(r["app_id"]) for r in rows if int(r[flag]) == 1}
        net_ids = channel_ids - prior_ids
        output.append(
            {
                "channel_order": order,
                "channel": label,
                "flag": flag,
                "N": len(channel_ids),
                "overlap": len(channel_ids & prior_ids),
                "net_additions": len(net_ids),
                "pre_N": sum(
                    1
                    for r in rows
                    if int(r[flag]) == 1 and r["pre_post_july_2024"] == "pre_july_2024"
                ),
                "post_N": sum(
                    1
                    for r in rows
                    if int(r[flag]) == 1 and r["pre_post_july_2024"] == "post_july_2024"
                ),
                "overlap_with_wes_wgs": len(channel_ids & wes_ids),
                "previous_channels": evidence_list([channel for _, channel in channels[: order - 1]]),
            }
        )
        prior_ids |= channel_ids
    high_ids = {str(r["app_id"]) for r in rows if int(r["HIGH_SENSITIVITY"]) == 1}
    output.append(
        {
            "channel_order": 99,
            "channel": "HIGH_SENSITIVITY_TOTAL",
            "flag": "HIGH_SENSITIVITY",
            "N": len(high_ids),
            "overlap": "",
            "net_additions": len(high_ids),
            "pre_N": sum(1 for r in rows if int(r["HIGH_SENSITIVITY"]) == 1 and r["pre_post_july_2024"] == "pre_july_2024"),
            "post_N": sum(1 for r in rows if int(r["HIGH_SENSITIVITY"]) == 1 and r["pre_post_july_2024"] == "post_july_2024"),
            "overlap_with_wes_wgs": len(high_ids & wes_ids),
            "previous_channels": "all evidence channels",
        }
    )
    return output


def field_tier_distribution_rows(
    fields: list[dict[str, object]],
    links: list[dict[str, object]],
) -> list[dict[str, object]]:
    links_by_field = defaultdict(list)
    for row in links:
        links_by_field[str(row["field_id"])].append(row)

    rows = []
    for grouping, label_fn in [
        ("tier_combo", lambda f: str(f["field_tier"]) or "none"),
        ("tier_token", None),
        ("private", lambda f: f"private={f['field_private']}"),
        ("main_category", lambda f: str(f["main_category"]) or "missing"),
    ]:
        counts: dict[str, dict[str, object]] = defaultdict(lambda: {"fields": 0, "links": 0, "apps": set()})
        for field in fields:
            labels: list[str]
            if grouping == "tier_token":
                labels = str(field["field_tier"]).split() or ["none"]
            else:
                labels = [label_fn(field)]  # type: ignore[misc]
            field_links = links_by_field.get(str(field["field_id"]), [])
            for label in labels:
                counts[label]["fields"] += 1
                counts[label]["links"] += len(field_links)
                counts[label]["apps"].update(str(row["app_id"]) for row in field_links)  # type: ignore[union-attr]
        for label, payload in sorted(counts.items(), key=lambda item: item[0]):
            rows.append(
                {
                    "grouping": grouping,
                    "value": label,
                    "field_count": payload["fields"],
                    "application_field_link_count": payload["links"],
                    "distinct_application_count": len(payload["apps"]),  # type: ignore[arg-type]
                }
            )
    return rows


def write_s3_text_audit_examples(rows: list[dict[str, object]], out: Outputs, target_n: int = 50) -> None:
    hits = [row for row in rows if int(row["hs_s3_text"]) == 1]
    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in hits:
        by_family[clean(row.get("hs_s3_text_family")) or "Unspecified"].append(row)
    for family_rows in by_family.values():
        family_rows.sort(key=lambda row: int(str(row["app_id"])))

    selected: list[dict[str, object]] = []
    while len(selected) < min(target_n, len(hits)):
        progressed = False
        for family in sorted(by_family):
            if by_family[family] and len(selected) < min(target_n, len(hits)):
                selected.append(by_family[family].pop(0))
                progressed = True
        if not progressed:
            break

    write_csv(
        out.s3_text_audit_examples,
        [
            {
                "app_id": row["app_id"],
                "title": row["title"],
                "notes_excerpt": row["hs_s3_text_excerpt"],
                "matched_term": row["hs_s3_text_term"],
                "matched_s3_field_family": row["hs_s3_text_family"],
                "classification_reason": row["classification_reason"],
            }
            for row in selected
        ],
        [
            "app_id",
            "title",
            "notes_excerpt",
            "matched_term",
            "matched_s3_field_family",
            "classification_reason",
        ],
    )


def write_s3_field_review(fields: list[dict[str, object]], keyword_rows: list[dict[str, object]], out: Outputs) -> None:
    s3 = s3_fields(fields)
    families = Counter(s3_field_family(field) for field in s3)
    categories = Counter(clean(field.get("main_category")) or "missing" for field in s3)
    item_types = Counter(clean(field.get("item_type")) or "missing" for field in s3)
    brain_categories = {"539", "507", "201", "202", "109", "110", "111", "106", "107", "112", "119", "198", "200"}
    brain_count = sum(
        1
        for field in s3
        if clean(field.get("main_category")) in brain_categories or "brain" in s3_field_family(field).lower()
    )
    genomic_titles = [
        field for field in s3 if re.search(r"genom|exome|\bwes\b|\bwgs\b", clean(field.get("field_title")), re.IGNORECASE)
    ]
    mri_sequence_titles = [
        field for field in s3 if re.search(r"\bsequence images?\b", clean(field.get("field_title")), re.IGNORECASE)
    ]
    linked_titles = [field for field in s3 if re.search(r"\blinked\b", clean(field.get("field_title")), re.IGNORECASE)]
    representatives = [
        "20158",
        "20216",
        "20218",
        "20227",
        "20250",
        "20251",
        "20263",
        "26300",
        "30005",
        "30099",
    ]
    by_id = {str(field["field_id"]): field for field in s3}
    rep_lines = [
        f"- {field_id}: {by_id[field_id]['field_title']} ({s3_field_family(by_id[field_id])})"
        for field_id in representatives
        if field_id in by_id
    ]
    family_lines = [
        f"| {family} | {count} |"
        for family, count in sorted(families.items(), key=lambda item: (-item[1], item[0]))
    ]
    category_lines = [
        f"| {category} | {CATEGORY_LABELS.get(category, 'unlabeled in local map')} | {count} |"
        for category, count in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
    ]
    item_type_lines = [f"| {item_type} | {count} |" for item_type, count in sorted(item_types.items())]
    text = f"""# S3 Field Review

The cached UKB Schema 1 snapshot contains {len(s3):,} fields with an `s3` tier token. The observed s3 fields are overwhelmingly image files, scan-derived files, and imaging/device outputs rather than generic questionnaire or tabular baseline variables.

## Field Families

| Family | s3 fields |
| --- | ---: |
{chr(10).join(family_lines)}

Brain MRI/imaging fields: {brain_count:,}. This count includes direct brain MRI file fields, NIFTI/DICOM brain images, dMRI/fMRI/SWI/QSM/ASL outputs, native parcellation/surface files, MNI transforms, CIFTI output, and PANDORA brain-imaging outputs.

## Main Categories

| Main category | Local label | s3 fields |
| --- | --- | ---: |
{chr(10).join(category_lines)}

## Item Types

| Item type | s3 fields |
| --- | ---: |
{chr(10).join(item_type_lines)}

## Sequence, Genomic, And Linked-Record Check

Schema 1 s3 titles naming genomic/exome/WES/WGS evidence: {len(genomic_titles):,}. No s3 title in the cached 199-field dictionary names WES, WGS, genome sequence data, exome sequence data, linked health records, or OMOP. The word `sequence` appears in {len(mri_sequence_titles):,} MRI sequence-image titles; those are treated as imaging evidence, not genomic sequence data. The word `linked` appears in {len(linked_titles):,} embargoed imaging-replica titles; those are treated as imaging-file evidence, not linked-record evidence.

## Representative Titles

{chr(10).join(rep_lines)}

## Application Text Dictionary

The generated application-text dictionary contains {len(keyword_rows):,} high-precision terms. It excludes generic terms such as `brain`, `genetic`, `health`, and `data`, and uses exact field-title phrases, file-format terms, and modality phrases supported by the 199 s3 fields.
"""
    out.s3_field_review.parent.mkdir(parents=True, exist_ok=True)
    out.s3_field_review.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_design_note() -> None:
    design_dir = PACKAGE / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    text = """# Project Entry2 Design

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
"""
    (design_dir / "project_entry2_design.md").write_text(text.rstrip() + "\n", encoding="utf-8")


def build_high_sensitivity_outputs(
    project_universe_path: Path = PROJECT_UNIVERSE,
    stage3_path: Path = STAGE3_CLASSIFICATION,
    control_review_path: Path = CONTROL_EXPANSION_REVIEW,
    output_paths: Outputs | None = None,
    refresh_schema: bool = False,
    refresh_field_pages: bool = False,
    no_fetch_field_pages: bool = False,
    sleep_seconds: float = 0.05,
) -> dict[str, object]:
    out = output_paths or Outputs()
    write_design_note()
    schema_refreshed = ensure_schema_snapshot(out.schema_snapshot, refresh=refresh_schema)
    fields = parse_field_schema(out.schema_snapshot)
    s3_dictionary = s3_field_dictionary_rows(fields)
    s3_keywords = build_s3_keyword_dictionary(fields)
    write_csv(
        out.s3_field_dictionary,
        s3_dictionary,
        ["field_id", "field_title", "main_category", "item_type", "field_tier", "debut", "private"],
    )
    write_csv(
        out.s3_keyword_dictionary,
        s3_keywords,
        [
            "term",
            "source_field_ids",
            "source_field_titles",
            "source_category",
            "precision_level",
            "reason",
        ],
    )
    write_s3_field_review(fields, s3_keywords, out)
    field_links, fetch_log = fetch_field_links(
        fields,
        out,
        refresh_pages=refresh_field_pages,
        no_fetch_pages=no_fetch_field_pages,
        sleep_seconds=sleep_seconds,
    )
    projects = read_csv(project_universe_path)
    stage3 = read_csv(stage3_path)
    control_review = read_csv(control_review_path)
    rows = build_project_classification_rows(projects, stage3, control_review, field_links, s3_keywords)
    write_s3_text_audit_examples(rows, out)

    classification_fields = [
        "app_id",
        "start_date",
        "month",
        "pre_post_july_2024",
        "title",
        "institution",
        "website_url",
        "HIGH_SENSITIVITY",
        "LOWER_SENSITIVITY_COMPARISON",
        "LOW_STRICT",
        "hs_wes_wgs_sequence",
        "hs_s3_direct",
        "hs_s3_text",
        "hs_o2_field",
        "hs_restricted_field",
        "linked_field_count",
        "linked_s3_field_count",
        "linked_s3_field_count_timing_conservative",
        "linked_o2_field_count",
        "linked_restricted_field_count",
        "field_debut_after_project_start",
        "field_debut_after_project_start_ids",
        "control_layer",
        "control_evidence_type",
        "control_matched_term",
        "control_inferred_product",
        "previous_classification",
        "previous_confidence",
        "legacy_route_modalities",
        "already_rap_modalities",
        "hs_sequence_product_term",
        "hs_sequence_product_source",
        "hs_sequence_product_excerpt",
        "hs_s3_text_term",
        "hs_s3_text_source",
        "hs_s3_text_source_field_ids",
        "hs_s3_text_source_field_titles",
        "hs_s3_text_family",
        "hs_s3_text_excerpt",
        "evidence_source",
        "evidence_detail",
        "classification_reason",
    ]
    write_csv(out.classification, rows, classification_fields)

    link_fields = [
        "app_id",
        "field_id",
        "field_title",
        "field_tier",
        "tier_source",
        "field_private",
        "item_type",
        "main_category",
        "debut",
        "version",
        "has_s3",
        "has_o2",
        "application_title_from_field_page",
        "source_url",
        "snapshot_path",
        "fetched_or_checked_at_utc",
    ]
    write_csv(out.application_field_links, field_links, link_fields)
    write_csv(
        out.field_fetch_log,
        fetch_log,
        [
            "field_id",
            "source_url",
            "snapshot_path",
            "status",
            "application_links_parsed",
            "error",
            "checked_at_utc",
        ],
    )
    write_csv(
        out.field_tier_distribution,
        field_tier_distribution_rows(fields, field_links),
        [
            "grouping",
            "value",
            "field_count",
            "application_field_link_count",
            "distinct_application_count",
        ],
    )
    write_csv(
        out.classification_counts,
        classification_count_rows(rows),
        ["period", "definition", "count", "universe_n", "share"],
    )
    write_csv(
        out.classification_overlap,
        classification_overlap_rows(rows),
        [
            "channel_order",
            "channel",
            "flag",
            "N",
            "overlap",
            "net_additions",
            "pre_N",
            "post_N",
            "overlap_with_wes_wgs",
            "previous_channels",
        ],
    )

    manifest = {
        "built_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "schema1_url": SCHEMA1_URL,
        "schema_snapshot": relpath(out.schema_snapshot),
        "schema_snapshot_refreshed_this_run": schema_refreshed,
        "field_page_url_template": FIELD_URL_TEMPLATE,
        "field_page_cache_dir": relpath(FIELD_PAGE_DIR),
        "field_page_candidate_rule": "has s3 tier OR has o2 tier OR private=1",
        "source_parser_validation": {
            "field_id": "25749",
            "expected_tier_tokens": ["o2", "s3"],
            "expected_application_ids": ["17689", "22783"],
            "status": next(
                (
                    row["status"]
                    for row in fetch_log
                    if str(row["field_id"]) == "25749"
                ),
                "not_checked",
            ),
        },
        "project_universe": relpath(project_universe_path),
        "stage3_classification": relpath(stage3_path),
        "control_expansion_project_review": relpath(control_review_path),
        "control_expansion_evidence_dictionary": relpath(CONTROL_EXPANSION_DICTIONARY),
        "n_projects": len(rows),
        "n_schema_fields": len(fields),
        "n_s3_fields": len(s3_dictionary),
        "n_s3_keyword_terms": len(s3_keywords),
        "n_field_page_candidates": sum(field_candidate(field) for field in fields),
        "n_application_field_links": len(field_links),
        "n_distinct_applications_with_field_links": len({str(row["app_id"]) for row in field_links}),
        "n_high_sensitivity": sum(int(row["HIGH_SENSITIVITY"]) for row in rows),
        "n_lower_sensitivity_comparison": sum(int(row["LOWER_SENSITIVITY_COMPARISON"]) for row in rows),
        "n_hs_wes_wgs_sequence": sum(int(row["hs_wes_wgs_sequence"]) for row in rows),
        "n_hs_s3_direct": sum(int(row["hs_s3_direct"]) for row in rows),
        "n_hs_s3_text": sum(int(row["hs_s3_text"]) for row in rows),
        "n_low_strict": sum(int(row["LOW_STRICT"]) for row in rows),
        "n_o2_field_applications": sum(int(row["hs_o2_field"]) for row in rows),
    }
    write_json(out.source_manifest, manifest)
    return manifest


def validate_outputs(out: Outputs | None = None) -> None:
    out = out or Outputs()
    rows = read_csv(out.classification)
    if len(rows) != 6935:
        raise AssertionError(f"expected 6,935 project rows; found {len(rows)}")
    required = {
        "app_id",
        "start_date",
        "HIGH_SENSITIVITY",
        "LOWER_SENSITIVITY_COMPARISON",
        "LOW_STRICT",
        "hs_wes_wgs_sequence",
        "hs_s3_direct",
        "hs_s3_text",
        "hs_o2_field",
        "hs_restricted_field",
        "linked_field_count",
        "linked_s3_field_count",
        "linked_o2_field_count",
        "hs_sequence_product_term",
        "hs_s3_text_term",
        "hs_s3_text_family",
        "evidence_source",
        "evidence_detail",
        "classification_reason",
    }
    missing = sorted(required - set(rows[0]))
    if missing:
        raise AssertionError(f"classification file missing columns: {missing}")
    present_forbidden = sorted(
        column
        for column in rows[0]
        if re.fullmatch(r"HIGH_C0[35]_S3(?:_TIMING_CONSERVATIVE)?", column)
    )
    if present_forbidden:
        raise AssertionError(f"old competing high-sensitivity columns remain: {present_forbidden}")
    for row in rows:
        high = int(row["HIGH_SENSITIVITY"])
        lower = int(row["LOWER_SENSITIVITY_COMPARISON"])
        if high + lower != 1:
            raise AssertionError(f"HIGH/LOWER complement failed for app {row['app_id']}")
        if int(row["LOW_STRICT"]) and high:
            raise AssertionError(f"LOW_STRICT overlaps HIGH_SENSITIVITY for app {row['app_id']}")
    s3_rows = read_csv(out.s3_field_dictionary)
    if len(s3_rows) != 199:
        raise AssertionError(f"expected 199 s3 fields; found {len(s3_rows)}")
    keyword_rows = read_csv(out.s3_keyword_dictionary)
    if not keyword_rows:
        raise AssertionError("s3 application keyword dictionary is empty")
    examples = read_csv(out.s3_text_audit_examples)
    hs_s3_text_n = sum(int(row["hs_s3_text"]) for row in rows)
    if hs_s3_text_n and len(examples) < min(50, hs_s3_text_n):
        raise AssertionError("s3 text audit examples are below required sample size")
    links = read_csv(out.application_field_links)
    field_25749 = [row for row in links if row["field_id"] == "25749"]
    if field_25749:
        ids = {row["app_id"] for row in field_25749}
        if not {"17689", "22783"}.issubset(ids):
            raise AssertionError("field 25749 parser validation failed")
        tiers = {row["field_tier"] for row in field_25749}
        if not any("o2" in tier and "s3" in tier for tier in tiers):
            raise AssertionError("field 25749 tier validation failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-schema", action="store_true")
    parser.add_argument("--refresh-field-pages", action="store_true")
    parser.add_argument("--no-fetch-field-pages", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.05)
    args = parser.parse_args()
    manifest = build_high_sensitivity_outputs(
        refresh_schema=args.refresh_schema,
        refresh_field_pages=args.refresh_field_pages,
        no_fetch_field_pages=args.no_fetch_field_pages,
        sleep_seconds=args.sleep_seconds,
    )
    validate_outputs()
    print(
        "project-entry2 high-sensitivity classification built: "
        f"{manifest['n_projects']} projects, "
        f"{manifest['n_high_sensitivity']} HIGH_SENSITIVITY, "
        f"{manifest['n_hs_s3_direct']} direct s3-linked applications, "
        f"{manifest['n_hs_s3_text']} s3-text applications"
    )


if __name__ == "__main__":
    main()
