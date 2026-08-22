#!/usr/bin/env python3
"""Classify provisional UKB project dependence on pre-policy RAP-only data.

Stage 3 is deliberately limited to treatment-status measurement. It does not
run outcome construction, treatment/control finalization, or DID regressions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKING_UNIVERSE = (
    ROOT
    / "data"
    / "intermediate"
    / "timing_feasibility"
    / "timing_working_research_project_universe.csv"
)
DEFAULT_MASTER = ROOT / "data" / "intermediate" / "stage2_universe" / "stage2_master_projects.csv"
DEFAULT_WEBSITE_LISTING = ROOT / "data" / "raw" / "ukb_projects_website_listing.csv"
DEFAULT_OUTPUT_DIR = ROOT
POLICY_DATE = date(2024, 7, 5)
STRICT_SEQUENCE_CONTEXT_DATE = date(2021, 11, 1)


@dataclass(frozen=True)
class EvidenceRule:
    modality: str
    route_group: str
    patterns: tuple[str, ...]
    specificity: str
    rationale: str


@dataclass(frozen=True)
class Stage3Paths:
    project_classification: Path
    class_counts: Path
    period_counts: Path
    modality_counts: Path
    examples: Path
    access_matrix: Path
    summary_json: Path
    report: Path


OFFICIAL_ACCESS_MATRIX = [
    {
        "modality_family": "Whole genome sequencing (WGS)",
        "pre_july_2024_access_route": "already_rap_only",
        "classification_role": "Explicit WGS dependence is already-RAP-bound evidence.",
        "official_basis": (
            "UKB's RAP transition notice says genomic sequence data were already "
            "accessible only through UKB-RAP; WGS Showcase documents the late-2021 "
            "200k and late-2023 500k WGS releases."
        ),
        "source_urls": (
            "https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/"
            "19996604847133-Changing-the-way-UK-Biobank-data-is-made-available-"
            "to-researchers-around-the-world; "
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=180; "
            "https://community.ukbiobank.ac.uk/hc/en-gb/articles/"
            "25118589261213-500k-Whole-Genome-Sequencing-General-FAQs"
        ),
    },
    {
        "modality_family": "Whole exome sequencing (WES)",
        "pre_july_2024_access_route": "already_rap_only",
        "classification_role": "Explicit WES/exome sequencing dependence is already-RAP-bound evidence.",
        "official_basis": (
            "UKB's RAP transition notice says genomic sequence data were already "
            "RAP-only; the Exome sequences Showcase category says WES fields are "
            "accessed in situ via UKB-RAP."
        ),
        "source_urls": (
            "https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/"
            "19996604847133-Changing-the-way-UK-Biobank-data-is-made-available-"
            "to-researchers-around-the-world; "
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=170"
        ),
    },
    {
        "modality_family": "OMOP Common Data Model transformation",
        "pre_july_2024_access_route": "already_rap_only",
        "classification_role": "Explicit OMOP dependence is treated as medium-confidence RAP-only evidence.",
        "official_basis": "UKB's July 2023 release list describes the OMOP release as available on RAP.",
        "source_urls": (
            "https://community.ukbiobank.ac.uk/hc/en-gb/articles/"
            "26655145866269-Past-data-releases"
        ),
    },
    {
        "modality_family": "Genotyping array, imputation, GWAS, PRS, HLA, CNV",
        "pre_july_2024_access_route": "legacy_download_or_local_access",
        "classification_role": (
            "Specific array/imputation/GWAS language is newly-RAP-bound evidence, "
            "not already-RAP-bound evidence."
        ),
        "official_basis": (
            "UKB genotype/imputation documentation describes gfetch/resource "
            "downloads of array calls, imputation BGENs, haplotypes, HLA and CNV "
            "data before the RAP-by-default transition."
        ),
        "source_urls": (
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=263; "
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=100319; "
            "https://biobank.ndph.ox.ac.uk/ukb/ukb/docs/ukbgene_instruct.html"
        ),
    },
    {
        "modality_family": "Imaging and image-derived phenotypes",
        "pre_july_2024_access_route": "legacy_download_or_local_access",
        "classification_role": "Imaging-only dependence is newly-RAP-bound evidence.",
        "official_basis": (
            "UKB release history lists repeated imaging releases and the imaging "
            "guidance documents MRI, DXA, ultrasound, OCT, DICOM, NIFTI and IDPs. "
            "WGS/WES, not imaging, are singled out as pre-policy RAP-only."
        ),
        "source_urls": (
            "https://community.ukbiobank.ac.uk/hc/en-gb/articles/"
            "26655145866269-Past-data-releases; "
            "https://community.ukbiobank.ac.uk/hc/en-gb/articles/"
            "24618819821981-Imaging-Data"
        ),
    },
    {
        "modality_family": "Linked health records",
        "pre_july_2024_access_route": "legacy_data_portal_or_download_route",
        "classification_role": "Linked-record-only dependence is newly-RAP-bound evidence.",
        "official_basis": (
            "UKB hospital inpatient documentation says record-level tables were "
            "accessed through the online Data Portal via a project's Download page; "
            "release history lists primary care, death, cancer, COVID-19 and HES "
            "updates through the Data Portal."
        ),
        "source_urls": (
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=2000; "
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=2006; "
            "https://community.ukbiobank.ac.uk/hc/en-gb/articles/"
            "26655145866269-Past-data-releases"
        ),
    },
    {
        "modality_family": "Questionnaires, assessment-centre fields, wearables, environmental data",
        "pre_july_2024_access_route": "legacy_download_or_local_access",
        "classification_role": "Specific questionnaire/assessment/environmental terms are newly-RAP-bound evidence.",
        "official_basis": (
            "UKB's release history states baseline data were first available in "
            "2012 and subsequent questionnaire, assessment, accelerometry and "
            "environmental releases were made available for download."
        ),
        "source_urls": (
            "https://community.ukbiobank.ac.uk/hc/en-gb/articles/"
            "26655145866269-Past-data-releases"
        ),
    },
    {
        "modality_family": "Biochemistry, biomarkers, NMR metabolomics, Olink proteomics",
        "pre_july_2024_access_route": "legacy_download_or_data_portal_route",
        "classification_role": "Specific assay/biomarker/proteomics terms are newly-RAP-bound evidence.",
        "official_basis": (
            "UKB release history lists biochemistry, metabolomics and Olink "
            "proteomics releases. Showcase proteomics documentation says Olink NPX "
            "data are made available in the Data Portal; NMR metabolomics is a "
            "tabular biomarker category."
        ),
        "source_urls": (
            "https://community.ukbiobank.ac.uk/hc/en-gb/articles/"
            "26655145866269-Past-data-releases; "
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=1839; "
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=220"
        ),
    },
    {
        "modality_family": "Generic genetic/genomic language",
        "pre_july_2024_access_route": "ambiguous_from_project_text",
        "classification_role": (
            "Generic genetic/genomic/gene/variant terms are recorded as ambiguity "
            "signals and do not by themselves imply WGS/WES or already-RAP exposure."
        ),
        "official_basis": (
            "UKB documentation distinguishes array/imputation genetic data from "
            "genomic sequence data; this stage therefore requires specific WGS/WES "
            "terms for already-RAP-bound classification."
        ),
        "source_urls": (
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=263; "
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=170; "
            "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=180"
        ),
    },
]


EVIDENCE_RULES = [
    EvidenceRule(
        modality="WGS",
        route_group="already_rap_only",
        specificity="high",
        rationale="Explicit whole-genome sequencing dependence was RAP-only before July 2024.",
        patterns=(
            r"\bWGS\b",
            r"whole[- ]genome sequenc",
            r"whole genome data",
            r"genomic sequence data",
            r"\bDRAGEN\b",
            r"\bGraphTyper\b",
            r"\bgVCF\b",
            r"\bpVCF\b",
            r"\bCRAM\b",
        ),
    ),
    EvidenceRule(
        modality="WES",
        route_group="already_rap_only",
        specificity="high",
        rationale="Explicit whole-exome/exome sequencing dependence was RAP-only before July 2024.",
        patterns=(
            r"\bWES\b",
            r"whole[- ]exome sequenc",
            r"exome sequenc",
            r"exome data",
            r"exome variant",
            r"\bOQFE\b",
        ),
    ),
    EvidenceRule(
        modality="OMOP_RAP_ONLY",
        route_group="already_rap_only",
        specificity="medium",
        rationale="UKB's OMOP Common Data Model release was described as available on RAP.",
        patterns=(r"\bOMOP\b", r"common data model"),
    ),
    EvidenceRule(
        modality="GENOTYPING_IMPUTATION",
        route_group="legacy_route",
        specificity="high",
        rationale="Array genotyping and imputation had legacy download/gfetch access before July 2024.",
        patterns=(
            r"\bGWAS\b",
            r"genome[- ]wide association",
            r"genomewide association",
            r"genetic association",
            r"\bgenotyp",
            r"\bimput",
            r"\bSNPs?\b",
            r"polygenic",
            r"\bPRS\b",
            r"Mendelian randomi[sz]ation",
            r"\bHLA\b",
            r"\bCNV\b",
            r"copy[- ]number",
            r"\bloci\b",
            r"\ballele",
        ),
    ),
    EvidenceRule(
        modality="IMAGING",
        route_group="legacy_route",
        specificity="high",
        rationale="Imaging and image-derived phenotypes were not singled out as pre-policy RAP-only.",
        patterns=(
            r"\bMRI\b",
            r"\bfMRI\b",
            r"\bimaging\b",
            r"image[- ]derived",
            r"\bIDP\b",
            r"\bDICOM\b",
            r"\bNIFTI\b",
            r"\bDXA\b",
            r"\bOCT\b",
            r"optical coherence",
            r"\bfundus\b",
            r"\bretinal\b",
            r"\bultrasound\b",
            r"brain scan",
            r"cardiac magnetic resonance",
            r"body composition",
        ),
    ),
    EvidenceRule(
        modality="LINKED_HEALTH_RECORDS",
        route_group="legacy_route",
        specificity="high",
        rationale="Linked health records had a pre-policy Data Portal/download route.",
        patterns=(
            r"\bHES\b",
            r"hospital episode",
            r"hospital inpatient",
            r"primary care",
            r"\bGP\b records?",
            r"\bGP\b data",
            r"death registr",
            r"cancer registr",
            r"linked health",
            r"record linkage",
            r"\bEHR\b",
            r"electronic health",
            r"\bICD[- ]?\d*\b",
            r"\bOPCS\b",
            r"first occurrence",
            r"prescription records?",
            r"medical records?",
        ),
    ),
    EvidenceRule(
        modality="QUESTIONNAIRES_ASSESSMENT",
        route_group="legacy_route",
        specificity="medium",
        rationale="Questionnaire, assessment and wearable fields were legacy-accessible before July 2024.",
        patterns=(
            r"questionnaire",
            r"self[- ]report",
            r"diet(?:ary)? recall",
            r"24[- ]hour recall",
            r"lifestyle",
            r"physical activity",
            r"acceleromet",
            r"actigraphy",
            r"assessment cent(?:re|er)",
            r"cognitive function",
            r"smoking",
            r"alcohol consumption",
            r"occupational",
            r"sleep",
        ),
    ),
    EvidenceRule(
        modality="BIOMARKERS_ASSAYS",
        route_group="legacy_route",
        specificity="high",
        rationale="Biochemistry, NMR metabolomics and Olink proteomics were not pre-policy RAP-only.",
        patterns=(
            r"biomarkers?",
            r"biochemistry",
            r"\bassay",
            r"\bserum\b",
            r"\bplasma\b",
            r"\burine\b",
            r"\bNMR\b",
            r"metabolomic",
            r"metabolites?",
            r"proteomic",
            r"\bOlink\b",
            r"protein biomarker",
            r"protein levels?",
        ),
    ),
    EvidenceRule(
        modality="PHYSICAL_MEASURES",
        route_group="legacy_route",
        specificity="medium",
        rationale="Standard tabular physical measures were available through the legacy route before July 2024.",
        patterns=(
            r"blood pressure",
            r"lung function",
            r"spirometr",
            r"anthropometric",
            r"\bBMI\b",
            r"body mass index",
            r"bone mineral density",
            r"heel bone",
            r"arterial stiffness",
            r"grip strength",
        ),
    ),
    EvidenceRule(
        modality="ENVIRONMENT_GEOSPATIAL",
        route_group="legacy_route",
        specificity="medium",
        rationale="Environmental and geospatial fields were not pre-policy RAP-only.",
        patterns=(
            r"air pollution",
            r"\bnoise\b",
            r"greenspace",
            r"built environment",
            r"geospatial",
            r"home location",
            r"residential",
            r"environmental exposure",
        ),
    ),
    EvidenceRule(
        modality="GENERIC_GENETIC_LANGUAGE",
        route_group="ambiguous",
        specificity="low",
        rationale="Generic genetic wording is not enough to infer WGS/WES.",
        patterns=(
            r"\bgenetic\b",
            r"\bgenetics\b",
            r"\bgenomic\b",
            r"\bgenomics\b",
            r"\bgene\b",
            r"\bgenes\b",
            r"\bDNA\b",
            r"\bvariants?\b",
        ),
    ),
    EvidenceRule(
        modality="GENERIC_SEQUENCE_LANGUAGE",
        route_group="ambiguous",
        specificity="low",
        rationale="Generic sequencing wording requires review unless it names WGS/WES/exome data.",
        patterns=(
            r"\bsequencing\b",
            r"\bsequenced\b",
            r"sequence variation",
            r"sequence variants?",
        ),
    ),
    EvidenceRule(
        modality="PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE",
        route_group="ambiguous",
        specificity="low",
        rationale="References to samples or external assays may not represent UKB data-download/RAP dependence.",
        patterns=(
            r"\bDNA samples?\b",
            r"\bblood samples?\b",
            r"\bplasma samples?\b",
            r"\bbiospecimens?\b",
            r"\bsample access\b",
            r"\bwet lab\b",
        ),
    ),
]


SOURCE_FIELDS = (
    ("schema27_title", "schema27_title"),
    ("schema27_notes", "notes"),
    ("website_excerpt", "excerpt"),
)


OUTPUT_FIELDS = [
    "app_id",
    "project_start_date",
    "policy_period",
    "classification",
    "confidence",
    "manual_review_recommended",
    "review_reasons",
    "already_rap_modalities",
    "legacy_route_modalities",
    "ambiguous_modality_signals",
    "matched_terms",
    "evidence_source_fields",
    "source_text_evidence",
    "strict_already_rap_control_candidate",
    "broader_already_rap_candidate",
    "any_already_rap_modality_candidate",
    "schema27_title",
    "schema27_notes",
    "website_excerpt",
    "website_url",
    "schema27_institution",
    "schema27_pi",
]


def clean(value: object) -> str:
    return "" if value is None else str(value)


def squash(value: str) -> str:
    return re.sub(r"\s+", " ", clean(value)).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
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


def output_paths(output_dir: Path) -> Stage3Paths:
    processed = output_dir / "data" / "intermediate" / "rap_classification"
    return Stage3Paths(
        project_classification=processed / "stage3_project_rap_exposure_classification.csv",
        class_counts=processed / "stage3_rap_exposure_counts.csv",
        period_counts=processed / "stage3_rap_exposure_counts_by_policy_period.csv",
        modality_counts=processed / "stage3_rap_exposure_modality_counts.csv",
        examples=processed / "stage3_rap_exposure_examples.csv",
        access_matrix=processed / "stage3_modality_access_matrix.csv",
        summary_json=processed / "stage3_rap_exposure_summary.json",
        report=output_dir / "reports" / "stage3_rap_exposure_classification.md",
    )


def compile_rules(rules: list[EvidenceRule]) -> list[tuple[EvidenceRule, list[re.Pattern[str]]]]:
    return [
        (rule, [re.compile(pattern, re.IGNORECASE) for pattern in rule.patterns])
        for rule in rules
    ]


COMPILED_RULES = compile_rules(EVIDENCE_RULES)


def find_rule_matches(text_by_field: dict[str, str]) -> dict[str, dict[str, object]]:
    evidence: dict[str, dict[str, object]] = {}
    for rule, patterns in COMPILED_RULES:
        terms: set[str] = set()
        fields: set[str] = set()
        positions: list[tuple[str, int, int]] = []
        for field_name, text in text_by_field.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    term = squash(match.group(0))
                    if term:
                        terms.add(term)
                        fields.add(field_name)
                        positions.append((field_name, match.start(), match.end()))
        if terms:
            evidence[rule.modality] = {
                "route_group": rule.route_group,
                "specificity": rule.specificity,
                "terms": sorted(terms, key=lambda value: value.lower()),
                "fields": sorted(fields),
                "positions": positions,
            }
    return evidence


def joined(values: list[str] | set[str] | tuple[str, ...]) -> str:
    return "|".join(clean(value) for value in values if clean(value))


def route_modalities(evidence: dict[str, dict[str, object]], route_group: str) -> list[str]:
    return sorted(
        modality for modality, detail in evidence.items() if detail["route_group"] == route_group
    )


def matched_terms(evidence: dict[str, dict[str, object]]) -> str:
    pieces = []
    for rule in EVIDENCE_RULES:
        modality = rule.modality
        if modality not in evidence:
            continue
        terms = evidence[modality].get("terms", [])
        pieces.append(f"{modality}:{joined(list(terms))}")
    return "; ".join(pieces)


def evidence_source_fields(evidence: dict[str, dict[str, object]]) -> str:
    fields: set[str] = set()
    for detail in evidence.values():
        fields.update(detail.get("fields", []))
    return joined(sorted(fields))


def text_snippet(text: str, start: int, end: int, width: int = 220) -> str:
    half = max(20, width // 2)
    left = max(0, start - half)
    right = min(len(text), end + half)
    snippet = squash(text[left:right])
    if left > 0:
        snippet = "..." + snippet
    if right < len(text):
        snippet += "..."
    return snippet


def source_text_evidence(
    text_by_field: dict[str, str], evidence: dict[str, dict[str, object]]
) -> str:
    snippets: list[str] = []
    for rule in EVIDENCE_RULES:
        modality = rule.modality
        if modality not in evidence:
            continue
        detail = evidence[modality]
        positions = detail.get("positions", [])
        if not positions:
            continue
        field_name, start, end = positions[0]
        snippet = text_snippet(text_by_field[field_name], int(start), int(end))
        snippets.append(f"{modality} [{field_name}]: {snippet}")
        if len(snippets) >= 4:
            break
    if snippets:
        return " || ".join(snippets)
    fallback = " ".join(
        text_by_field.get(field, "") for field in ("schema27_title", "schema27_notes")
    )
    return textwrap.shorten(squash(fallback), width=360, placeholder="...")


def classify_project(
    working_row: dict[str, str],
    master_row: dict[str, str],
    website_row: dict[str, str],
) -> dict[str, object]:
    text_by_field = {
        "schema27_title": squash(working_row.get("schema27_title", "")),
        "schema27_notes": squash(master_row.get("notes", "")),
        "website_excerpt": squash(website_row.get("excerpt", "")),
    }
    evidence = find_rule_matches(text_by_field)
    already = route_modalities(evidence, "already_rap_only")
    legacy = route_modalities(evidence, "legacy_route")
    ambiguous = route_modalities(evidence, "ambiguous")

    if already and legacy:
        classification = "MIXED"
    elif already:
        classification = "ALREADY_RAP_BOUND"
    elif legacy:
        classification = "NEWLY_RAP_BOUND"
    else:
        classification = "UNCLEAR"

    if classification in {"ALREADY_RAP_BOUND", "MIXED"}:
        confidence = "HIGH" if {"WGS", "WES"} & set(already) else "MEDIUM"
    elif classification == "NEWLY_RAP_BOUND":
        high_modalities = {
            "GENOTYPING_IMPUTATION",
            "IMAGING",
            "LINKED_HEALTH_RECORDS",
            "BIOMARKERS_ASSAYS",
        }
        confidence = "HIGH" if len(legacy) >= 2 or high_modalities & set(legacy) else "MEDIUM"
    else:
        confidence = "LOW"

    project_start_date = parse_iso_date(working_row["start_date"])
    review_reasons: list[str] = []
    if classification == "UNCLEAR":
        review_reasons.append("no_specific_modality_evidence")
    if classification == "MIXED":
        review_reasons.append("mixed_rap_only_and_legacy_route_modalities")
    if confidence != "HIGH":
        review_reasons.append("not_high_confidence")
    if "GENERIC_SEQUENCE_LANGUAGE" in ambiguous and not {"WGS", "WES"} & set(already):
        review_reasons.append("generic_sequence_language_without_wgs_wes")
    if ambiguous and classification == "UNCLEAR":
        review_reasons.append("ambiguous_language_only")
    if {"WGS", "WES"} & set(already) and project_start_date < STRICT_SEQUENCE_CONTEXT_DATE:
        review_reasons.append("pre_2021_sequence_project_context")
    if "PHYSICAL_SAMPLE_OR_EXTERNAL_ASSAY_LANGUAGE" in ambiguous:
        review_reasons.append("physical_sample_or_external_assay_language")
    if already == ["OMOP_RAP_ONLY"]:
        review_reasons.append("omop_only_medium_confidence")

    strict_already_control = (
        classification == "ALREADY_RAP_BOUND"
        and confidence == "HIGH"
        and bool({"WGS", "WES"} & set(already))
        and project_start_date >= STRICT_SEQUENCE_CONTEXT_DATE
        and not review_reasons
    )
    broader_already_candidate = classification == "ALREADY_RAP_BOUND"
    any_already_candidate = bool(already)

    return {
        "app_id": working_row.get("app_id", ""),
        "project_start_date": working_row.get("start_date", ""),
        "policy_period": "after_policy" if project_start_date >= POLICY_DATE else "before_policy",
        "classification": classification,
        "confidence": confidence,
        "manual_review_recommended": "yes" if review_reasons else "no",
        "review_reasons": joined(review_reasons),
        "already_rap_modalities": joined(already),
        "legacy_route_modalities": joined(legacy),
        "ambiguous_modality_signals": joined(ambiguous),
        "matched_terms": matched_terms(evidence),
        "evidence_source_fields": evidence_source_fields(evidence),
        "source_text_evidence": source_text_evidence(text_by_field, evidence),
        "strict_already_rap_control_candidate": "yes" if strict_already_control else "no",
        "broader_already_rap_candidate": "yes" if broader_already_candidate else "no",
        "any_already_rap_modality_candidate": "yes" if any_already_candidate else "no",
        "schema27_title": working_row.get("schema27_title", ""),
        "schema27_notes": master_row.get("notes", ""),
        "website_excerpt": website_row.get("excerpt", ""),
        "website_url": working_row.get("website_url", ""),
        "schema27_institution": working_row.get("schema27_institution", ""),
        "schema27_pi": working_row.get("schema27_pi", ""),
    }


def load_website_by_url(path: Path) -> dict[str, dict[str, str]]:
    return {row.get("url", "").rstrip("/"): row for row in read_csv(path)}


def validate_working_universe(rows: list[dict[str, str]], expected_working: int) -> None:
    if len(rows) != expected_working:
        raise ValueError(
            f"Expected {expected_working:,} projects in fixed working universe; "
            f"found {len(rows):,}."
        )
    bad_rows = [
        row.get("app_id", "")
        for row in rows
        if row.get("website_match_status") != "matched_one_website_record"
        or not row.get("start_date")
    ]
    if bad_rows:
        sample = ", ".join(bad_rows[:10])
        raise ValueError(
            "Working universe must contain only unique website matches with start dates; "
            f"violating app_id sample: {sample}"
        )


def classification_counts(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    class_order = ["ALREADY_RAP_BOUND", "NEWLY_RAP_BOUND", "MIXED", "UNCLEAR"]
    counts = Counter(clean(row["classification"]) for row in rows)
    confidence_counts = Counter(
        (clean(row["classification"]), clean(row["confidence"])) for row in rows
    )
    return [
        {
            "classification": classification,
            "projects": counts[classification],
            "high_confidence": confidence_counts[(classification, "HIGH")],
            "medium_confidence": confidence_counts[(classification, "MEDIUM")],
            "low_confidence": confidence_counts[(classification, "LOW")],
        }
        for classification in class_order
    ]


def period_count_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    class_order = ["ALREADY_RAP_BOUND", "NEWLY_RAP_BOUND", "MIXED", "UNCLEAR"]
    counts = Counter(
        (clean(row["classification"]), clean(row["policy_period"])) for row in rows
    )
    return [
        {
            "classification": classification,
            "before_policy_projects": counts[(classification, "before_policy")],
            "after_policy_projects": counts[(classification, "after_policy")],
            "total_projects": (
                counts[(classification, "before_policy")]
                + counts[(classification, "after_policy")]
            ),
            "policy_date_counted_with": "after_policy",
        }
        for classification in class_order
    ]


def modality_count_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    for row in rows:
        classification = clean(row["classification"])
        for modality in clean(row["already_rap_modalities"]).split("|"):
            if modality:
                counts[(classification, "already_rap_only", modality)] += 1
        for modality in clean(row["legacy_route_modalities"]).split("|"):
            if modality:
                counts[(classification, "legacy_route", modality)] += 1
        for modality in clean(row["ambiguous_modality_signals"]).split("|"):
            if modality:
                counts[(classification, "ambiguous", modality)] += 1
    rows_out = [
        {
            "classification": classification,
            "modality_type": modality_type,
            "modality": modality,
            "project_count": count,
        }
        for (classification, modality_type, modality), count in sorted(counts.items())
    ]
    return rows_out


def representative_examples(rows: list[dict[str, object]], per_class: int = 8) -> list[dict[str, object]]:
    class_order = ["ALREADY_RAP_BOUND", "NEWLY_RAP_BOUND", "MIXED", "UNCLEAR"]
    confidence_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    output: list[dict[str, object]] = []
    for classification in class_order:
        candidates = [
            row for row in rows if clean(row["classification"]) == classification
        ]
        candidates.sort(
            key=lambda row: (
                confidence_rank.get(clean(row["confidence"]), 9),
                clean(row["project_start_date"]),
                int(clean(row["app_id"]) or 0),
            )
        )
        selected: list[dict[str, object]] = []
        seen_modalities: set[str] = set()
        for row in candidates:
            modality_key = (
                clean(row["already_rap_modalities"])
                or clean(row["legacy_route_modalities"])
                or clean(row["ambiguous_modality_signals"])
                or "none"
            )
            if modality_key not in seen_modalities or len(selected) < 3:
                selected.append(row)
                seen_modalities.add(modality_key)
            if len(selected) >= per_class:
                break
        if len(selected) < per_class:
            for row in candidates:
                if row not in selected:
                    selected.append(row)
                if len(selected) >= per_class:
                    break
        for row in selected:
            output.append(
                {
                    "classification": row["classification"],
                    "app_id": row["app_id"],
                    "project_start_date": row["project_start_date"],
                    "confidence": row["confidence"],
                    "already_rap_modalities": row["already_rap_modalities"],
                    "legacy_route_modalities": row["legacy_route_modalities"],
                    "ambiguous_modality_signals": row["ambiguous_modality_signals"],
                    "schema27_title": row["schema27_title"],
                    "source_text_evidence": row["source_text_evidence"],
                    "website_url": row["website_url"],
                }
            )
    return output


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


def top_modalities_by_class(
    modality_rows: list[dict[str, object]], classification: str, modality_type: str
) -> str:
    selected = [
        row
        for row in modality_rows
        if row["classification"] == classification and row["modality_type"] == modality_type
    ]
    selected.sort(key=lambda row: (-int(row["project_count"]), clean(row["modality"])))
    if not selected:
        return ""
    return "; ".join(
        f"{row['modality']}={row['project_count']}" for row in selected[:8]
    )


def write_report(
    paths: Stage3Paths,
    rows: list[dict[str, object]],
    class_rows: list[dict[str, object]],
    period_rows: list[dict[str, object]],
    modality_rows: list[dict[str, object]],
    example_rows: list[dict[str, object]],
    source_commit: str,
) -> None:
    strict_count = sum(row["strict_already_rap_control_candidate"] == "yes" for row in rows)
    broader_pure_count = sum(row["broader_already_rap_candidate"] == "yes" for row in rows)
    any_already_count = sum(row["any_already_rap_modality_candidate"] == "yes" for row in rows)
    manual_review_count = sum(row["manual_review_recommended"] == "yes" for row in rows)

    modality_summary = []
    for class_row in class_rows:
        classification = clean(class_row["classification"])
        modality_summary.append(
            {
                "classification": classification,
                "already_rap_only_modalities": top_modalities_by_class(
                    modality_rows, classification, "already_rap_only"
                ),
                "legacy_route_modalities": top_modalities_by_class(
                    modality_rows, classification, "legacy_route"
                ),
                "ambiguous_signals": top_modalities_by_class(
                    modality_rows, classification, "ambiguous"
                ),
            }
        )

    compact_examples = [
        {
            "classification": row["classification"],
            "app_id": row["app_id"],
            "start": row["project_start_date"],
            "confidence": row["confidence"],
            "modalities": "; ".join(
                part
                for part in (
                    f"RAP-only:{row['already_rap_modalities']}"
                    if row["already_rap_modalities"]
                    else "",
                    f"legacy:{row['legacy_route_modalities']}"
                    if row["legacy_route_modalities"]
                    else "",
                    f"ambiguous:{row['ambiguous_modality_signals']}"
                    if row["ambiguous_modality_signals"]
                    else "",
                )
                if part
            )
            or "none",
            "title": textwrap.shorten(clean(row["schema27_title"]), width=100, placeholder="..."),
        }
        for row in example_rows
    ]

    access_rows = [
        {
            "modality_family": row["modality_family"],
            "pre_july_2024_access_route": row["pre_july_2024_access_route"],
            "classification_role": row["classification_role"],
        }
        for row in OFFICIAL_ACCESS_MATRIX
    ]

    report = f"""# Stage 3 RAP Exposure Classification

Policy date: `{POLICY_DATE.isoformat()}`. This is a provisional measurement
step only. It does not finalise treatment/control status, optimise group
definitions for sample size, construct outcomes, or run DID regressions.

The input universe is fixed to the `{len(rows):,}` Schema 27 applications
matched to one UKB Projects website record with one recovered start date. The
132 unmatched Schema 27 records remain outside this classification working
sample and are preserved only in the timing audit file.

Source commit: `{source_commit or "not recorded"}`.

## Official Access Matrix

{markdown_table(access_rows, ["modality_family", "pre_july_2024_access_route", "classification_role"])}

Key official sources used for the matrix:

- UKB RAP transition notice: https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/19996604847133-Changing-the-way-UK-Biobank-data-is-made-available-to-researchers-around-the-world
- UKB past data releases: https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases
- WES Showcase category: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=170
- WGS Showcase category: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=180
- Genotypes and imputation documentation: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=263 and https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=100319
- Legacy genetic-data download guide: https://biobank.ndph.ox.ac.uk/ukb/ukb/docs/ukbgene_instruct.html
- Hospital inpatient/Data Portal documentation: https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=2000 and https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=2006
- Imaging, proteomics and NMR documentation: https://community.ukbiobank.ac.uk/hc/en-gb/articles/24618819821981-Imaging-Data, https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=1839, and https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=220

## Classification Logic

- `ALREADY_RAP_BOUND`: the project text contains explicit pre-policy RAP-only
  evidence, such as WGS, WES, exome sequencing, whole-genome sequencing, or
  OMOP, and no specific legacy-route modality is detected.
- `NEWLY_RAP_BOUND`: the project text contains specific legacy-route evidence
  such as genotyping/imputation/GWAS/PRS, imaging, linked health records,
  questionnaires/assessment fields, biomarkers/proteomics/metabolomics, physical
  measures, or environmental/geospatial fields, and no WGS/WES/OMOP evidence is
  detected.
- `MIXED`: both explicit already-RAP-only evidence and specific legacy-route
  evidence are detected.
- `UNCLEAR`: no specific modality evidence is detected. Generic words such as
  genetic, genomic, gene, variant, or sequencing are recorded as ambiguity
  signals but do not by themselves imply WGS/WES or already-RAP exposure.

## Preliminary Counts

{markdown_table(class_rows, ["classification", "projects", "high_confidence", "medium_confidence", "low_confidence"])}

The policy date itself is counted with `after_policy`.

{markdown_table(period_rows, ["classification", "before_policy_projects", "after_policy_projects", "total_projects"])}

Manual review is recommended for `{manual_review_count:,}` projects, mainly
`MIXED`, `UNCLEAR`, medium/low-confidence classifications, generic sequencing
without WGS/WES, physical-sample language, or pre-2021 sequencing contexts.

## Modality Drivers

{markdown_table(modality_summary, ["classification", "already_rap_only_modalities", "legacy_route_modalities", "ambiguous_signals"])}

## Representative Examples

{markdown_table(compact_examples, ["classification", "app_id", "start", "confidence", "modalities", "title"])}

## Already-RAP-Bound Control Candidates

- Strict pure already-RAP-bound controls: `{strict_count:,}` projects. This
  requires `ALREADY_RAP_BOUND`, high confidence, explicit WGS/WES evidence, no
  specific legacy-route evidence, and project start on or after
  `{STRICT_SEQUENCE_CONTEXT_DATE.isoformat()}`.
- Broader pure already-RAP-bound candidates: `{broader_pure_count:,}` projects.
  This is all provisional `ALREADY_RAP_BOUND` projects, including medium
  confidence OMOP-only and earlier sequencing contexts.
- Any already-RAP-only modality candidates: `{any_already_count:,}` projects.
  This includes provisional `MIXED` projects and should not be treated as a
  strict control group without manual review.

## Ambiguities And Misclassification Risks

- Earlier sequencing projects may describe investigator-generated sequencing or
  DNA/sample work before UKB's public RAP sequence releases. These are flagged,
  and the strict control count excludes starts before
  `{STRICT_SEQUENCE_CONTEXT_DATE.isoformat()}`.
- Generic genetic/genomic language is frequent and intentionally does not imply
  WGS/WES. Specific GWAS, SNP, genotype, imputation, PRS, HLA or CNV language is
  treated as legacy-route genomic evidence.
- Project descriptions often name diseases, traits, or broad aims rather than
  approved basket fields. `UNCLEAR` is therefore a real measurement category,
  not a residual treatment/control group.
- `MIXED` projects are not forced into either control or treated groups because
  their text indicates both prior RAP-only and legacy-route data dependence.
- Physical samples, external assays, or industry sequencing language can look
  like UKB data requirements but may reflect data generation outside the UKB
  access route; these rows are flagged for review.

## Outputs

- `{display_path(paths.project_classification)}`
- `{display_path(paths.class_counts)}`
- `{display_path(paths.period_counts)}`
- `{display_path(paths.modality_counts)}`
- `{display_path(paths.examples)}`
- `{display_path(paths.access_matrix)}`
- `{display_path(paths.summary_json)}`
"""
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(report, encoding="utf-8")


def build_stage3_outputs(
    working_universe_path: Path,
    master_path: Path,
    website_listing_path: Path,
    output_dir: Path,
    expected_working: int,
    source_commit: str,
) -> dict[str, object]:
    working_rows = read_csv(working_universe_path)
    validate_working_universe(working_rows, expected_working)
    master_by_app_id = {row["app_id"]: row for row in read_csv(master_path)}
    website_by_url = load_website_by_url(website_listing_path)

    rows: list[dict[str, object]] = []
    missing_master = 0
    missing_website = 0
    for working_row in working_rows:
        master_row = master_by_app_id.get(working_row["app_id"], {})
        website_row = website_by_url.get(working_row.get("website_url", "").rstrip("/"), {})
        if not master_row:
            missing_master += 1
        if not website_row:
            missing_website += 1
        rows.append(classify_project(working_row, master_row, website_row))

    paths = output_paths(output_dir)
    class_rows = classification_counts(rows)
    period_rows = period_count_rows(rows)
    modality_rows = modality_count_rows(rows)
    example_rows = representative_examples(rows)

    write_csv(paths.project_classification, rows, OUTPUT_FIELDS)
    write_csv(
        paths.class_counts,
        class_rows,
        ["classification", "projects", "high_confidence", "medium_confidence", "low_confidence"],
    )
    write_csv(
        paths.period_counts,
        period_rows,
        [
            "classification",
            "before_policy_projects",
            "after_policy_projects",
            "total_projects",
            "policy_date_counted_with",
        ],
    )
    write_csv(
        paths.modality_counts,
        modality_rows,
        ["classification", "modality_type", "modality", "project_count"],
    )
    write_csv(
        paths.examples,
        example_rows,
        [
            "classification",
            "app_id",
            "project_start_date",
            "confidence",
            "already_rap_modalities",
            "legacy_route_modalities",
            "ambiguous_modality_signals",
            "schema27_title",
            "source_text_evidence",
            "website_url",
        ],
    )
    write_csv(
        paths.access_matrix,
        OFFICIAL_ACCESS_MATRIX,
        [
            "modality_family",
            "pre_july_2024_access_route",
            "classification_role",
            "official_basis",
            "source_urls",
        ],
    )

    strict_count = sum(row["strict_already_rap_control_candidate"] == "yes" for row in rows)
    broader_pure_count = sum(row["broader_already_rap_candidate"] == "yes" for row in rows)
    any_already_count = sum(row["any_already_rap_modality_candidate"] == "yes" for row in rows)
    manual_review_count = sum(row["manual_review_recommended"] == "yes" for row in rows)
    summary = {
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source_commit": source_commit,
        "policy_date": POLICY_DATE.isoformat(),
        "classification_stage": "stage3_provisional_rap_exposure_classification_only",
        "did_regressions_run": False,
        "outcome_analysis_run": False,
        "working_universe_projects": len(rows),
        "excluded_unmatched_schema27_records": 132,
        "working_universe_file": display_path(working_universe_path),
        "working_universe_file_sha256": file_sha256(working_universe_path),
        "master_project_file": display_path(master_path),
        "master_project_file_sha256": file_sha256(master_path),
        "website_listing_file": display_path(website_listing_path),
        "website_listing_file_sha256": file_sha256(website_listing_path),
        "missing_master_rows": missing_master,
        "missing_website_rows": missing_website,
        "classification_counts": class_rows,
        "classification_counts_by_policy_period": period_rows,
        "strict_already_rap_control_projects": strict_count,
        "broader_pure_already_rap_candidate_projects": broader_pure_count,
        "any_already_rap_modality_candidate_projects": any_already_count,
        "manual_review_recommended_projects": manual_review_count,
        "strict_sequence_context_date": STRICT_SEQUENCE_CONTEXT_DATE.isoformat(),
        "official_access_matrix": OFFICIAL_ACCESS_MATRIX,
    }
    paths.summary_json.parent.mkdir(parents=True, exist_ok=True)
    paths.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(
        paths=paths,
        rows=rows,
        class_rows=class_rows,
        period_rows=period_rows,
        modality_rows=modality_rows,
        example_rows=example_rows,
        source_commit=source_commit,
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--working-universe", type=Path, default=DEFAULT_WORKING_UNIVERSE)
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--website-listing", type=Path, default=DEFAULT_WEBSITE_LISTING)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-working", type=int, default=6935)
    parser.add_argument("--source-commit", default="")
    args = parser.parse_args(argv)

    summary = build_stage3_outputs(
        working_universe_path=args.working_universe,
        master_path=args.master,
        website_listing_path=args.website_listing,
        output_dir=args.output_dir,
        expected_working=args.expected_working,
        source_commit=args.source_commit,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
