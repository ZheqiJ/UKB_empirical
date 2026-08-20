#!/usr/bin/env python3
"""Build C0-C6 incremental already-RAP-bound control-candidate expansion.

This script preserves the conservative Stage 3 classifier. It treats the
existing ALREADY_RAP_BOUND rows as C0, then assigns additional projects to the
first expansion layer for which reviewable evidence is found.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_DATE = date(2024, 7, 5)
DEFAULT_STAGE3_CLASSIFICATION = (
    ROOT / "data" / "processed" / "stage3_project_rap_exposure_classification.csv"
)
DEFAULT_SCHEMA19 = ROOT / "data" / "raw" / "ukb_schema19_publications.tsv"
DEFAULT_SCHEMA24 = ROOT / "data" / "raw" / "ukb_schema24_publication_applications.tsv"
DEFAULT_OUTPUT_DIR = ROOT


@dataclass(frozen=True)
class EvidenceTerm:
    term_id: str
    term_or_expression: str
    regex: str
    used_in_layers: tuple[str, ...]
    evidence_type: str
    underlying_data_product: str
    why_implies_pre_policy_rap_exposure: str
    official_ukb_source: str
    official_evidence: str
    effective_date: str
    evidence_strength: str
    requires_ukb_proximity_in_publications: bool = True


@dataclass(frozen=True)
class MatchEvidence:
    term: EvidenceTerm
    source_type: str
    source_label: str
    source_date: str
    source_url: str
    pub_id: str
    pub_date: str
    doi: str
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class ExpansionPaths:
    project_review: Path
    evidence_dictionary: Path
    layer_counts: Path
    previous_class_counts: Path
    examples: Path
    summary_json: Path
    report: Path


UKB_RAP_TRANSITION_SOURCE = (
    "https://community.ukbiobank.ac.uk/hc/en-gb/community/posts/"
    "19996604847133-Changing-the-way-UK-Biobank-data-is-made-available-"
    "to-researchers-around-the-world"
)
PAST_RELEASES_SOURCE = (
    "https://community.ukbiobank.ac.uk/hc/en-gb/articles/26655145866269-Past-data-releases"
)
WES_SOURCE = "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=170"
WGS_SOURCE = "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=180"
WGS_DRAGEN_SOURCE = "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=185"
WGS_GRAPHTYPER_SOURCE = "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=270"
WGS_PREVIOUS_SOURCE = "https://biobank.ndph.ox.ac.uk/ukb/label.cgi?id=271"
OMOP_SOURCE = "https://biobank.ndph.ox.ac.uk/ukb/field.cgi?id=20142"


def term(
    term_id: str,
    expression: str,
    regex: str,
    layers: tuple[str, ...],
    evidence_type: str,
    product: str,
    why: str,
    source: str,
    official_evidence: str,
    effective_date: str,
    strength: str,
    requires_ukb_proximity_in_publications: bool = True,
) -> EvidenceTerm:
    return EvidenceTerm(
        term_id=term_id,
        term_or_expression=expression,
        regex=regex,
        used_in_layers=layers,
        evidence_type=evidence_type,
        underlying_data_product=product,
        why_implies_pre_policy_rap_exposure=why,
        official_ukb_source=source,
        official_evidence=official_evidence,
        effective_date=effective_date,
        evidence_strength=strength,
        requires_ukb_proximity_in_publications=requires_ukb_proximity_in_publications,
    )


C1_TERMS = [
    term(
        "C1_WGS_ABBREVIATION",
        "WGS",
        r"\bWGS\b",
        ("C1", "C6"),
        "explicit_sequence_data_wording",
        "Whole genome sequencing data",
        "WGS is UKB's standard abbreviation for whole genome sequencing.",
        WGS_SOURCE,
        "Category 180 is titled Whole genome sequences and documents the 200k and 500k WGS releases.",
        "2021-11",
        "high",
    ),
    term(
        "C1_WES_ABBREVIATION",
        "WES",
        r"\bWES\b",
        ("C1", "C6"),
        "explicit_sequence_data_wording",
        "Whole exome sequencing data",
        "WES is UKB's standard abbreviation for whole exome sequencing.",
        WES_SOURCE,
        "Category 170 describes UKB whole exome sequencing (WES) and in-situ RAP access.",
        "2021-11",
        "high",
    ),
    term(
        "C1_WHOLE_GENOME_SEQUENCE",
        "whole genome sequencing / whole-genome sequence",
        r"whole[- ]genome sequenc(?:ing|e|ed)?",
        ("C1", "C6"),
        "explicit_sequence_data_wording",
        "Whole genome sequencing data",
        "The expression names the UKB WGS modality directly.",
        WGS_SOURCE,
        "Category 180 states that whole genome sequencing data were released in late 2021 and late 2023.",
        "2021-11",
        "high",
    ),
    term(
        "C1_WHOLE_EXOME_SEQUENCE",
        "whole exome sequencing / whole-exome sequence",
        r"whole[- ]exome sequenc(?:ing|e|ed)?",
        ("C1", "C6"),
        "explicit_sequence_data_wording",
        "Whole exome sequencing data",
        "The expression names the UKB WES modality directly.",
        WES_SOURCE,
        "Category 170 states that UKB WES fields are accessed in-situ via UKB-RAP.",
        "2021-11",
        "high",
    ),
    term(
        "C1_EXOME_SEQUENCE",
        "exome sequencing / exome sequence",
        r"exome[- ]sequenc(?:ing|e|ed)",
        ("C1", "C6"),
        "explicit_sequence_data_wording",
        "Whole exome sequencing data",
        "In UKB project text, exome sequencing directly points to the WES data product.",
        WES_SOURCE,
        "Category 170 is the Exome sequences category and documents WES processing and RAP access.",
        "2021-11",
        "high",
    ),
    term(
        "C1_GENOME_SEQUENCE_DATA",
        "genome sequence data / genomic sequence data",
        r"(?:genome|genomic)[- ]sequenc(?:ing|e|ed)? data",
        ("C1", "C6"),
        "explicit_sequence_data_wording",
        "Whole genome sequencing data",
        "UKB uses genomic sequence data to describe the pre-policy RAP-only sequence products.",
        UKB_RAP_TRANSITION_SOURCE,
        "The UKB RAP transition notice says UKB-RAP was already the only means of access to genomic sequence data.",
        "2021",
        "high",
    ),
    term(
        "C1_EXOME_DATA",
        "exome data / exome variants",
        r"exome (?:data|variants?)",
        ("C1", "C6"),
        "explicit_sequence_data_wording",
        "Whole exome sequencing data",
        "Exome data and exome variants refer to the WES-derived variant data product.",
        WES_SOURCE,
        "Category 170 lists population-level exome OQFE variants and exome VCF/CRAM fields.",
        "2021-11",
        "high",
    ),
    term(
        "C1_SEQUENCED_GENOMES",
        "sequenced genomes / sequenced exomes",
        r"sequenced (?:genomes?|exomes?)",
        ("C1", "C6"),
        "explicit_sequence_data_wording",
        "WGS/WES sequence data",
        "The expression describes participant genomes or exomes having been sequenced.",
        WGS_SOURCE + "; " + WES_SOURCE,
        "UKB WGS/WES category pages describe sequenced genomes and exomes and their release tranches.",
        "2021-11",
        "high",
    ),
]


C2_TERMS = [
    term(
        "C2_OQFE",
        "OQFE",
        r"\bOQFE\b",
        ("C2", "C6"),
        "sequence_specific_technical_fingerprint",
        "Whole exome sequencing OQFE pipeline/output",
        "OQFE is the UKB WES processing protocol and appears in exome VCF/CRAM field names.",
        WES_SOURCE,
        "Category 170 describes OQFE CRAMs, gVCFs, GLnexus, pVCF, and final exome OQFE fields.",
        "2021-11",
        "high",
    ),
    term(
        "C2_DEEPVARIANT_GLNEXUS_WECALL",
        "DeepVariant / GLnexus / WeCall",
        r"\b(?:DeepVariant|GLnexus|WeCall)\b",
        ("C2", "C6"),
        "sequence_specific_technical_fingerprint",
        "WES variant-calling pipeline",
        "These are named WES small-variant calling and joint-genotyping tools in UKB exome documentation.",
        WES_SOURCE,
        "Category 170 says OQFE CRAMs were called with DeepVariant and joint-genotyped with GLnexus; earlier SPB used WeCall.",
        "2021-11",
        "high",
    ),
    term(
        "C2_PVCF_GVCF",
        "pVCF / gVCF",
        r"\b[pg]VCFs?\b",
        ("C2", "C6"),
        "sequence_specific_technical_fingerprint",
        "Sequence variant-call product",
        "Project-level pVCFs and per-sample gVCFs are WES/WGS sequence variant-call products in UKB documentation.",
        WES_SOURCE + "; " + WGS_GRAPHTYPER_SOURCE,
        "Category 170 documents exome gVCFs and pVCFs; Category 270 lists GraphTyper WGS variants in pVCF format.",
        "2021-11",
        "high",
    ),
    term(
        "C2_CRAM_FASTQ",
        "CRAM / FASTQ",
        r"\b(?:CRAMs?|FASTQs?)\b",
        ("C2", "C6"),
        "sequence_specific_technical_fingerprint",
        "Sequence alignment/read files",
        "CRAM and FASTQ references in UKB WES/WGS contexts indicate sequence reads or alignments.",
        WES_SOURCE + "; " + WGS_GRAPHTYPER_SOURCE,
        "UKB WES and WGS pages list CRAM files and describe FASTQ processing.",
        "2021-11",
        "high",
    ),
    term(
        "C2_DRAGEN",
        "DRAGEN",
        r"\bDRAGEN\b",
        ("C2", "C6"),
        "sequence_specific_technical_fingerprint",
        "DRAGEN WGS processing release",
        "DRAGEN is the named UKB WGS reprocessing pipeline and category.",
        WGS_DRAGEN_SOURCE,
        "Category 185 is DRAGEN WGS and lists CRAM, gVCF, SV, STR, CNV, PLINK2 and BGEN outputs.",
        "2023-11",
        "high",
    ),
    term(
        "C2_GRAPHTYPER_GATK_BWA",
        "GraphTyper / BWA-mem / GATK variant calls",
        r"\bGraphTyper\b|BWA[- ]mem|GATK[^.]{0,80}variant call",
        ("C2", "C6"),
        "sequence_specific_technical_fingerprint",
        "WGS GATK/GraphTyper processing release",
        "These names identify the UKB WGS processing and joint-call release.",
        WGS_GRAPHTYPER_SOURCE,
        "Category 270 describes WGS data produced using BWA-mem/GATK and GraphTyper joint variant calling.",
        "2021-11",
        "high",
    ),
    term(
        "C2_WGS_STRUCTURAL_PRODUCTS",
        "Manta, SV, STR, ExpansionHunter",
        r"\bManta[- ]called\b|\bExpansionHunter\b|whole genome (?:SV|STR|CNV) ",
        ("C2", "C6"),
        "sequence_specific_technical_fingerprint",
        "WGS structural variant and repeat products",
        "These are named UKB WGS technical outputs rather than general genetics terms.",
        WGS_DRAGEN_SOURCE + "; " + WGS_PREVIOUS_SOURCE,
        "Categories 185 and 271 list Manta-called, SV, STR, CNV and ExpansionHunter WGS products.",
        "2021-11",
        "high",
    ),
    term(
        "C2_PHASED_SEQUENCE",
        "phased sequence data / BEAGLE or SHAPEIT phased VCFs",
        r"phased sequence|BEAGLE Phased VCFs?|SHAPEIT Phased VCFs?|150,?119 sequenced genomes",
        ("C2", "C6"),
        "sequence_specific_technical_fingerprint",
        "WGS phased VCF sequence product",
        "UKB previous WGS releases include BEAGLE/SHAPEIT phased VCFs for sequenced genomes.",
        WGS_PREVIOUS_SOURCE + "; " + PAST_RELEASES_SOURCE,
        "Category 271 lists BEAGLE and SHAPEIT phased VCFs; release notes describe 200k WGS phased data.",
        "2023-07",
        "high",
    ),
]


C3_TERMS = [
    term(
        "C3_RARE_CODING",
        "rare coding variants / coding variation",
        r"rare coding variants?|coding variation",
        ("C3", "C6"),
        "broader_contextual_sequence_evidence",
        "Likely WES/WGS coding variant analysis",
        "UKB WES summary documentation centers on exome sequencing and coding variation.",
        WES_SOURCE,
        "Category 170 links the WES resource Exome sequencing and characterization of coding variation.",
        "2021-11",
        "medium",
    ),
    term(
        "C3_LOF_PLOF",
        "loss-of-function / pLoF / protein-truncating variants",
        r"protein[- ]truncating variants?|\bpLoF\b|predicted loss[- ]of[- ]function|loss[- ]of[- ]function variants?|\bLoF variants?\b|loss of function genetic variants",
        ("C3", "C6"),
        "broader_contextual_sequence_evidence",
        "Likely WES/WGS rare coding variant analysis",
        "LoF/pLoF/protein-truncating analyses commonly require sequence-resolved coding variation.",
        WES_SOURCE,
        "UKB WES documentation describes exome-derived small variants and coding variation resources.",
        "2021-11",
        "medium",
    ),
    term(
        "C3_MISSENSE_NONSENSE",
        "nonsense and missense / rare functional variants",
        r"nonsense (?:and )?missense|rare functional variants?|rare protein[- ]altering variants?|deleterious exonic variants?|rare deleterious variants?|protein coding variants?",
        ("C3", "C6"),
        "broader_contextual_sequence_evidence",
        "Likely WES/WGS protein-coding variant analysis",
        "These phrases are not generic genetics alone; they point to coding-sequence variant dependence.",
        WES_SOURCE,
        "Category 170 describes WES targets, coding genes, and variant-call products.",
        "2021-11",
        "medium",
    ),
    term(
        "C3_BURDEN_TEST",
        "gene burden / variant burden / collapsing analysis",
        r"gene[- ]based burden|variant burden|burden test|collapsing analysis",
        ("C3", "C6"),
        "broader_contextual_sequence_evidence",
        "Likely WES/WGS rare variant burden analysis",
        "Burden/collapsing analyses in UKB linked publications often refer to exome or rare coding variant data.",
        WES_SOURCE,
        "UKB WES documentation identifies exome sequence variant products suited to rare variant analyses.",
        "2021-11",
        "medium",
    ),
    term(
        "C3_HUMAN_KNOCKOUTS",
        "human gene knockouts",
        r"human gene knockouts?",
        ("C3", "C6"),
        "broader_contextual_sequence_evidence",
        "Likely WES/WGS loss-of-function discovery",
        "Human knockout discovery normally depends on rare loss-of-function coding variants.",
        WES_SOURCE,
        "UKB WES fields provide exome variant calls used to identify rare coding and LoF variants.",
        "2021-11",
        "medium",
    ),
]


C4_TERMS = [
    term(
        "C4_OMOP",
        "OMOP / OMOP Common Data Model",
        r"\bOMOP\b|Observational Medical Outcomes Partnership|common data model|\bOHDSI\b",
        ("C4", "C6"),
        "other_pre_policy_rap_only_product",
        "OMOP Common Data Model dataset, Field 20142",
        "UKB release notes identify OMOP as a transformed dataset available on RAP in July 2023.",
        PAST_RELEASES_SOURCE + "; " + OMOP_SOURCE,
        "Past releases list OMOP release on RAP in July 2023; Field 20142 is Present in OMOP dataset.",
        "2023-07",
        "medium",
    )
]


C5_TERMS = [
    term(
        "C5_UKB_RAP",
        "UKB-RAP / UK Biobank Research Analysis Platform",
        r"UKB[- ]RAP|UK Biobank Research Analysis Platform|Research Analysis Platform service|UK Biobank \(UKB\) Research Analysis Platform|cloud-based UK Biobank Research Analysis Platform",
        ("C5",),
        "direct_pre_policy_rap_use_evidence",
        "Direct UKB-RAP analysis environment evidence",
        "A pre-policy publication stating use of UKB-RAP directly establishes pre-policy RAP use.",
        UKB_RAP_TRANSITION_SOURCE,
        "The UKB transition notice identifies UKB-RAP as the cloud-based Research Analysis Platform.",
        "2021",
        "high",
        requires_ukb_proximity_in_publications=False,
    ),
    term(
        "C5_DNANEXUS",
        "UKB DNAnexus / DNAnexus JupyterLab",
        r"UKB DNAnexus|DNAnexus JupyterLab|UK Biobank DNAnexus",
        ("C5",),
        "direct_pre_policy_rap_use_evidence",
        "Direct DNAnexus/UKB-RAP analysis environment evidence",
        "DNAnexus/JupyterLab phrasing in a UKB publication is direct cloud-platform environment evidence.",
        UKB_RAP_TRANSITION_SOURCE,
        "UKB-RAP is the cloud-based platform used for hosted analyses; DNAnexus is the platform provider context.",
        "2021",
        "medium",
        requires_ukb_proximity_in_publications=False,
    ),
]


EVIDENCE_TERMS = C1_TERMS + C2_TERMS + C3_TERMS + C4_TERMS + C5_TERMS
TERMS_BY_LAYER = {
    "C1": C1_TERMS,
    "C2": C2_TERMS,
    "C3": C3_TERMS,
    "C4": C4_TERMS,
    "C5": C5_TERMS,
    "C6": C1_TERMS + C2_TERMS + C3_TERMS + C4_TERMS,
}


REVIEW_FIELDS = [
    "app_id",
    "start_date",
    "policy_period",
    "expansion_layer",
    "previous_classification",
    "previous_confidence",
    "proposed_new_classification",
    "evidence_type",
    "evidence_source",
    "source_timing",
    "supporting_text_excerpt",
    "inferred_underlying_data_product_or_rap_use",
    "matched_term_or_expression",
    "evidence_dictionary_term_id",
    "confidence",
    "manual_review_flag",
    "manual_review_reason",
    "source_pub_id",
    "source_pub_date",
    "source_doi",
    "previous_already_rap_modalities",
    "previous_legacy_route_modalities",
    "schema27_title",
    "website_url",
]


def clean(value: object) -> str:
    return "" if value is None else str(value)


def squash(value: str) -> str:
    return re.sub(r"\s+", " ", clean(value)).strip()


def strip_html(value: str) -> str:
    value = html.unescape(clean(value))
    value = re.sub(r"<[^>]+>", " ", value)
    return squash(value)


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


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


def output_paths(output_dir: Path) -> ExpansionPaths:
    return ExpansionPaths(
        project_review=(
            output_dir / "data" / "processed" / "stage3_control_expansion_project_review.csv"
        ),
        evidence_dictionary=(
            output_dir / "data" / "processed" / "stage3_control_expansion_evidence_dictionary.csv"
        ),
        layer_counts=output_dir / "data" / "processed" / "stage3_control_expansion_layer_counts.csv",
        previous_class_counts=(
            output_dir
            / "data"
            / "processed"
            / "stage3_control_expansion_new_by_previous_classification.csv"
        ),
        examples=output_dir / "data" / "processed" / "stage3_control_expansion_examples.csv",
        summary_json=output_dir / "data" / "processed" / "stage3_control_expansion_summary.json",
        report=output_dir / "reports" / "stage3_control_expansion.md",
    )


def compile_terms(terms: list[EvidenceTerm]) -> list[tuple[EvidenceTerm, re.Pattern[str]]]:
    return [(evidence_term, re.compile(evidence_term.regex, re.IGNORECASE)) for evidence_term in terms]


COMPILED_BY_LAYER = {
    layer: compile_terms(terms) for layer, terms in TERMS_BY_LAYER.items()
}
UKB_MENTION_RE = re.compile(r"UK Biobank|\bUKBB?\b", re.IGNORECASE)
EXTERNAL_SEQUENCE_CONTEXT_RE = re.compile(
    r"second dataset|external dataset|another dataset|independent dataset|"
    r"separate dataset|non[- ]UK Biobank|non[- ]UKB|other cohorts?|external cohorts?",
    re.IGNORECASE,
)


def project_text(row: dict[str, str]) -> str:
    return "\n".join(
        [
            f"schema27_title: {row.get('schema27_title', '')}",
            f"schema27_notes: {row.get('schema27_notes', '')}",
            f"website_excerpt: {row.get('website_excerpt', '')}",
        ]
    )


def publication_text(pub: dict[str, str]) -> str:
    return "\n".join(
        [
            f"publication_title: {pub.get('title', '')}",
            f"publication_keywords: {pub.get('keywords', '')}",
            f"publication_abstract: {strip_html(pub.get('abstract', ''))}",
        ]
    )


def has_ukb_proximity(text: str, start: int, end: int, window: int = 140) -> bool:
    for match in UKB_MENTION_RE.finditer(text):
        if abs(start - match.end()) <= window or abs(match.start() - end) <= window:
            return True
    return False


def has_external_sequence_context(text: str, start: int, end: int, window: int = 180) -> bool:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return bool(EXTERNAL_SEQUENCE_CONTEXT_RE.search(text[left:right]))


def find_first_match(
    layer: str,
    text: str,
    source_type: str,
    source_label: str,
    source_date: str = "",
    source_url: str = "",
    pub_id: str = "",
    pub_date: str = "",
    doi: str = "",
    require_ukb_proximity: bool = False,
    skip_external_sequence_context: bool = False,
) -> MatchEvidence | None:
    for evidence_term, pattern in COMPILED_BY_LAYER[layer]:
        for match in pattern.finditer(text):
            if skip_external_sequence_context and has_external_sequence_context(
                text, match.start(), match.end()
            ):
                continue
            if (
                require_ukb_proximity
                and evidence_term.requires_ukb_proximity_in_publications
                and not has_ukb_proximity(text, match.start(), match.end())
            ):
                continue
            return MatchEvidence(
                term=evidence_term,
                source_type=source_type,
                source_label=source_label,
                source_date=source_date,
                source_url=source_url,
                pub_id=pub_id,
                pub_date=pub_date,
                doi=doi,
                text=text,
                start=match.start(),
                end=match.end(),
            )
    return None


def snippet(text: str, start: int, end: int, width: int = 360) -> str:
    half = max(60, width // 2)
    left = max(0, start - half)
    right = min(len(text), end + half)
    value = squash(text[left:right])
    if left > 0:
        value = "..." + value
    if right < len(text):
        value += "..."
    return value


def policy_period(start_date: str) -> str:
    return "after_policy" if parse_iso_date(start_date) >= POLICY_DATE else "before_policy"


def source_timing(evidence: MatchEvidence | None, start_date: str) -> str:
    if evidence is None:
        return "stage3_current_classifier"
    if evidence.source_type == "publication":
        if evidence.pub_date and evidence.pub_date < POLICY_DATE.isoformat():
            return "pre_policy_publication"
        if evidence.pub_date:
            return "post_policy_publication_product_evidence"
        return "publication_date_missing"
    if parse_iso_date(start_date) < POLICY_DATE:
        return "pre_policy_project_text"
    return "post_policy_project_text"


def confidence_for_layer(layer: str, evidence: MatchEvidence | None, previous_classification: str) -> str:
    if layer == "C0":
        return "HIGH_BASELINE"
    if layer in {"C1", "C2"}:
        return "HIGH" if previous_classification != "MIXED" else "HIGH_NEEDS_MIXED_REVIEW"
    if layer == "C3":
        return "MEDIUM_CONTEXTUAL"
    if layer == "C4":
        return "MEDIUM_VERIFIED_PRODUCT"
    if layer == "C5":
        if evidence and evidence.source_type == "publication" and evidence.pub_date < POLICY_DATE.isoformat():
            return "HIGH_DIRECT_PRE_POLICY_RAP"
        return "MEDIUM_DIRECT_RAP_REVIEW"
    if layer == "C6":
        if evidence and evidence.pub_date and evidence.pub_date < POLICY_DATE.isoformat():
            return "MEDIUM_PUBLICATION_MODALITY_PRE_POLICY"
        return "MEDIUM_PUBLICATION_MODALITY"
    return "LOW"


def manual_review(layer: str, evidence: MatchEvidence | None, previous_classification: str) -> tuple[str, str]:
    reasons: list[str] = []
    if layer == "C0":
        return "no", "fixed_C0_baseline_from_current_classifier"
    if previous_classification == "MIXED":
        reasons.append("previous_stage3_classification_was_mixed")
    if layer in {"C3", "C4", "C6"}:
        reasons.append("lower_than_C1_C2_precision_layer")
    if layer == "C5" and (not evidence or evidence.source_type != "publication"):
        reasons.append("direct_rap_evidence_not_from_pre_policy_publication")
    if evidence and evidence.source_type == "publication" and evidence.pub_date >= POLICY_DATE.isoformat():
        reasons.append("post_policy_publication_reveals_product_not_pre_policy_rap_use")
    return ("yes" if reasons else "no"), "|".join(reasons)


def review_row(
    row: dict[str, str],
    layer: str,
    evidence: MatchEvidence | None,
) -> dict[str, object]:
    previous_classification = row.get("classification", "")
    confidence = confidence_for_layer(layer, evidence, previous_classification)
    review_flag, review_reason = manual_review(layer, evidence, previous_classification)
    if layer == "C0":
        evidence_type = "current_conservative_classifier"
        evidence_source = "data/processed/stage3_project_rap_exposure_classification.csv"
        source_excerpt = row.get("source_text_evidence", "")
        product = row.get("already_rap_modalities", "")
        matched_expression = row.get("already_rap_modalities", "")
        term_id = "C0_CURRENT_STAGE3_ALREADY_RAP_BOUND"
        timing = "stage3_current_classifier"
        pub_id = pub_date = doi = ""
    else:
        assert evidence is not None
        evidence_type = evidence.term.evidence_type
        evidence_source = evidence.source_label or evidence.source_url
        source_excerpt = snippet(evidence.text, evidence.start, evidence.end)
        product = evidence.term.underlying_data_product
        matched_expression = evidence.term.term_or_expression
        term_id = evidence.term.term_id
        timing = source_timing(evidence, row["project_start_date"])
        pub_id = evidence.pub_id
        pub_date = evidence.pub_date
        doi = evidence.doi
    return {
        "app_id": row.get("app_id", ""),
        "start_date": row.get("project_start_date", ""),
        "policy_period": policy_period(row.get("project_start_date", "")),
        "expansion_layer": layer,
        "previous_classification": previous_classification,
        "previous_confidence": row.get("confidence", ""),
        "proposed_new_classification": f"CONTROL_CANDIDATE_{layer}",
        "evidence_type": evidence_type,
        "evidence_source": evidence_source,
        "source_timing": timing,
        "supporting_text_excerpt": source_excerpt,
        "inferred_underlying_data_product_or_rap_use": product,
        "matched_term_or_expression": matched_expression,
        "evidence_dictionary_term_id": term_id,
        "confidence": confidence,
        "manual_review_flag": review_flag,
        "manual_review_reason": review_reason,
        "source_pub_id": pub_id,
        "source_pub_date": pub_date,
        "source_doi": doi,
        "previous_already_rap_modalities": row.get("already_rap_modalities", ""),
        "previous_legacy_route_modalities": row.get("legacy_route_modalities", ""),
        "schema27_title": row.get("schema27_title", ""),
        "website_url": row.get("website_url", ""),
    }


def load_publication_links(
    schema19_path: Path, schema24_path: Path
) -> dict[str, list[dict[str, str]]]:
    if not schema19_path.exists() or not schema24_path.exists():
        return {}
    pubs = {row["pub_id"]: row for row in read_csv(schema19_path, delimiter="\t")}
    app_to_pubs: dict[str, list[dict[str, str]]] = defaultdict(list)
    for link in read_csv(schema24_path, delimiter="\t"):
        pub = pubs.get(link.get("pub_id", ""))
        if pub:
            app_to_pubs[link["app_id"]].append(pub)
    for app_id in app_to_pubs:
        app_to_pubs[app_id].sort(key=lambda pub: (pub.get("date_pub", ""), pub.get("pub_id", "")))
    return app_to_pubs


def assign_project_text_layer(
    row: dict[str, str], layer: str
) -> MatchEvidence | None:
    text = project_text(row)
    return find_first_match(
        layer=layer,
        text=text,
        source_type="project_text",
        source_label="Schema 27 title/notes plus UKB Projects website excerpt",
        source_date=row.get("project_start_date", ""),
        source_url=row.get("website_url", ""),
        require_ukb_proximity=False,
        skip_external_sequence_context=layer in {"C1", "C2"},
    )


def assign_c5(
    row: dict[str, str], publications: list[dict[str, str]]
) -> MatchEvidence | None:
    # Project text can be suggestive, but publication evidence is preferred.
    if parse_iso_date(row["project_start_date"]) < POLICY_DATE:
        evidence = assign_project_text_layer(row, "C5")
        if evidence:
            return evidence
    for pub in publications:
        pub_date = pub.get("date_pub", "")
        if not pub_date or pub_date >= POLICY_DATE.isoformat():
            continue
        text = publication_text(pub)
        evidence = find_first_match(
            layer="C5",
            text=text,
            source_type="publication",
            source_label=f"Schema 19 publication {pub.get('pub_id', '')}: {pub.get('title', '')}",
            source_date=pub_date,
            source_url=pub.get("url") or pub.get("doi", ""),
            pub_id=pub.get("pub_id", ""),
            pub_date=pub_date,
            doi=pub.get("doi", ""),
            require_ukb_proximity=False,
        )
        if evidence:
            return evidence
    return None


def assign_c6(
    publications: list[dict[str, str]]
) -> MatchEvidence | None:
    for pub in publications:
        text = publication_text(pub)
        evidence = find_first_match(
            layer="C6",
            text=text,
            source_type="publication",
            source_label=f"Schema 19 publication {pub.get('pub_id', '')}: {pub.get('title', '')}",
            source_date=pub.get("date_pub", ""),
            source_url=pub.get("url") or pub.get("doi", ""),
            pub_id=pub.get("pub_id", ""),
            pub_date=pub.get("date_pub", ""),
            doi=pub.get("doi", ""),
            require_ukb_proximity=True,
        )
        if evidence:
            return evidence
    return None


def evidence_dictionary_rows() -> list[dict[str, object]]:
    rows = [
        {
            "term_id": "C0_CURRENT_STAGE3_ALREADY_RAP_BOUND",
            "term_or_expression": "Current Stage 3 ALREADY_RAP_BOUND classification",
            "regex": "",
            "underlying_data_modality_or_product": "Existing conservative already-RAP-bound evidence",
            "why_it_implies_pre_policy_rap_exposure": (
                "Fixed baseline supplied by the previous conservative classifier; not redefined here."
            ),
            "official_ukb_source": UKB_RAP_TRANSITION_SOURCE,
            "official_evidence": (
                "The current classifier used official UKB WGS/WES/OMOP access evidence."
            ),
            "effective_date": "fixed_C0",
            "evidence_strength": "baseline_high_precision",
            "used_in_layers": "C0",
        }
    ]
    for evidence_term in EVIDENCE_TERMS:
        rows.append(
            {
                "term_id": evidence_term.term_id,
                "term_or_expression": evidence_term.term_or_expression,
                "regex": evidence_term.regex,
                "underlying_data_modality_or_product": evidence_term.underlying_data_product,
                "why_it_implies_pre_policy_rap_exposure": (
                    evidence_term.why_implies_pre_policy_rap_exposure
                ),
                "official_ukb_source": evidence_term.official_ukb_source,
                "official_evidence": evidence_term.official_evidence,
                "effective_date": evidence_term.effective_date,
                "evidence_strength": evidence_term.evidence_strength,
                "used_in_layers": "|".join(evidence_term.used_in_layers),
            }
        )
    return rows


def layer_order() -> list[str]:
    return ["C0", "C1", "C2", "C3", "C4", "C5", "C6"]


def build_review_rows(
    stage3_rows: list[dict[str, str]],
    app_to_pubs: dict[str, list[dict[str, str]]],
) -> list[dict[str, object]]:
    assigned: set[str] = set()
    output: list[dict[str, object]] = []
    rows_by_id = {row["app_id"]: row for row in stage3_rows}

    for app_id in sorted(
        [row["app_id"] for row in stage3_rows if row["classification"] == "ALREADY_RAP_BOUND"],
        key=lambda value: int(value),
    ):
        row = rows_by_id[app_id]
        assigned.add(app_id)
        output.append(review_row(row, "C0", None))

    for layer in ("C1", "C2", "C3", "C4"):
        for row in stage3_rows:
            if row["app_id"] in assigned:
                continue
            evidence = assign_project_text_layer(row, layer)
            if evidence:
                assigned.add(row["app_id"])
                output.append(review_row(row, layer, evidence))

    for row in stage3_rows:
        if row["app_id"] in assigned:
            continue
        evidence = assign_c5(row, app_to_pubs.get(row["app_id"], []))
        if evidence:
            assigned.add(row["app_id"])
            output.append(review_row(row, "C5", evidence))

    for row in stage3_rows:
        if row["app_id"] in assigned:
            continue
        evidence = assign_c6(app_to_pubs.get(row["app_id"], []))
        if evidence:
            assigned.add(row["app_id"])
            output.append(review_row(row, "C6", evidence))

    return output


def in_window(start: date, months: int, side: str) -> bool:
    if side == "before":
        return add_months(POLICY_DATE, -months) <= start <= POLICY_DATE - timedelta(days=1)
    return POLICY_DATE <= start <= add_months(POLICY_DATE, months)


def count_window(rows: list[dict[str, object]], months: int, side: str) -> int:
    return sum(in_window(parse_iso_date(clean(row["start_date"])), months, side) for row in rows)


def layer_count_rows(review_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows_by_layer: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in review_rows:
        rows_by_layer[clean(row["expansion_layer"])].append(row)

    cumulative: list[dict[str, object]] = []
    output: list[dict[str, object]] = []
    for layer in layer_order():
        new_rows = rows_by_layer.get(layer, [])
        cumulative.extend(new_rows)
        new_previous = Counter(clean(row["previous_classification"]) for row in new_rows)
        new_evidence = Counter(clean(row["evidence_type"]) for row in new_rows)
        output.append(
            {
                "layer": layer,
                "new_projects": len(new_rows),
                "cumulative_projects": len(cumulative),
                "new_before_policy": sum(row["policy_period"] == "before_policy" for row in new_rows),
                "new_after_policy": sum(row["policy_period"] == "after_policy" for row in new_rows),
                "cumulative_before_policy": sum(
                    row["policy_period"] == "before_policy" for row in cumulative
                ),
                "cumulative_after_policy": sum(
                    row["policy_period"] == "after_policy" for row in cumulative
                ),
                "new_within_6m_before": count_window(new_rows, 6, "before"),
                "new_within_6m_after": count_window(new_rows, 6, "after"),
                "new_within_12m_before": count_window(new_rows, 12, "before"),
                "new_within_12m_after": count_window(new_rows, 12, "after"),
                "cumulative_within_6m_before": count_window(cumulative, 6, "before"),
                "cumulative_within_6m_after": count_window(cumulative, 6, "after"),
                "cumulative_within_12m_before": count_window(cumulative, 12, "before"),
                "cumulative_within_12m_after": count_window(cumulative, 12, "after"),
                "new_from_previous_classification": "; ".join(
                    f"{key}={value}" for key, value in sorted(new_previous.items())
                ),
                "new_evidence_types": "; ".join(
                    f"{key}={value}" for key, value in sorted(new_evidence.items())
                ),
            }
        )
    return output


def previous_class_count_rows(review_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    counts = Counter(
        (clean(row["expansion_layer"]), clean(row["previous_classification"]))
        for row in review_rows
    )
    rows = []
    for layer in layer_order():
        for previous in ["ALREADY_RAP_BOUND", "NEWLY_RAP_BOUND", "MIXED", "UNCLEAR"]:
            rows.append(
                {
                    "layer": layer,
                    "previous_classification": previous,
                    "new_projects": counts[(layer, previous)],
                }
            )
    return rows


def example_rows(review_rows: list[dict[str, object]], per_layer: int = 8) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    rank = {
        "HIGH_BASELINE": 0,
        "HIGH": 1,
        "HIGH_DIRECT_PRE_POLICY_RAP": 1,
        "HIGH_NEEDS_MIXED_REVIEW": 2,
        "MEDIUM_VERIFIED_PRODUCT": 3,
        "MEDIUM_CONTEXTUAL": 4,
        "MEDIUM_PUBLICATION_MODALITY_PRE_POLICY": 4,
        "MEDIUM_PUBLICATION_MODALITY": 5,
        "MEDIUM_DIRECT_RAP_REVIEW": 5,
    }
    for layer in layer_order():
        candidates = [row for row in review_rows if row["expansion_layer"] == layer]
        candidates.sort(
            key=lambda row: (
                rank.get(clean(row["confidence"]), 9),
                clean(row["previous_classification"]),
                clean(row["start_date"]),
                int(clean(row["app_id"]) or 0),
            )
        )
        selected: list[dict[str, object]] = []
        seen_previous: set[str] = set()
        for row in candidates:
            previous = clean(row["previous_classification"])
            if previous not in seen_previous or len(selected) < 3:
                selected.append(row)
                seen_previous.add(previous)
            if len(selected) >= per_layer:
                break
        if len(selected) < per_layer:
            for row in candidates:
                if row not in selected:
                    selected.append(row)
                if len(selected) >= per_layer:
                    break
        for row in selected:
            output.append(
                {
                    "layer": row["expansion_layer"],
                    "app_id": row["app_id"],
                    "start_date": row["start_date"],
                    "previous_classification": row["previous_classification"],
                    "evidence_type": row["evidence_type"],
                    "matched_term_or_expression": row["matched_term_or_expression"],
                    "confidence": row["confidence"],
                    "manual_review_flag": row["manual_review_flag"],
                    "title": textwrap.shorten(clean(row["schema27_title"]), width=110, placeholder="..."),
                    "supporting_text_excerpt": row["supporting_text_excerpt"],
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


def write_report(
    paths: ExpansionPaths,
    review_rows: list[dict[str, object]],
    layer_rows: list[dict[str, object]],
    previous_rows: list[dict[str, object]],
    examples: list[dict[str, object]],
    source_commit: str,
) -> None:
    previous_summary = []
    for layer in layer_order():
        pieces = [
            f"{row['previous_classification']}={row['new_projects']}"
            for row in previous_rows
            if row["layer"] == layer and int(row["new_projects"]) > 0
        ]
        previous_summary.append({"layer": layer, "new_from_previous_classification": "; ".join(pieces)})

    compact_examples = [
        {
            "layer": row["layer"],
            "app_id": row["app_id"],
            "start_date": row["start_date"],
            "previous": row["previous_classification"],
            "evidence": row["evidence_type"],
            "term": row["matched_term_or_expression"],
            "confidence": row["confidence"],
            "title": row["title"],
        }
        for row in examples
    ]
    manual_review_count = sum(row["manual_review_flag"] == "yes" for row in review_rows)
    report = f"""# Stage 3 Control Expansion Frontier

Policy date: `{POLICY_DATE.isoformat()}`. This step preserves the current
conservative classifier. The existing 42 `ALREADY_RAP_BOUND` projects are
treated as fixed C0 and are not reclassified. No treatment/control status is
finalised, no outcomes are constructed, and no DID regressions are run.

Source commit: `{source_commit or "not recorded"}`.

## Layer Definitions

- `C0`: fixed current `ALREADY_RAP_BOUND` baseline.
- `C1`: explicit WGS/WES or whole-genome/whole-exome sequence wording in
  project text.
- `C2`: sequence-specific products, file types, pipelines, and processing
  fingerprints in project text.
- `C3`: broader contextual sequence evidence in project text, excluding generic
  genetic/genomic/variant/sequencing language alone.
- `C4`: verified non-WGS/WES data products already RAP-only before
  5 July 2024.
- `C5`: direct pre-policy RAP-use evidence from project or linked publication
  text.
- `C6`: linked-publication recovery of WGS/WES or other verified RAP-only data
  dependence when application text is vague.

## Incremental Counts

{markdown_table(layer_rows, ["layer", "new_projects", "cumulative_projects", "new_before_policy", "new_after_policy", "cumulative_before_policy", "cumulative_after_policy", "new_within_6m_before", "new_within_6m_after", "new_within_12m_before", "new_within_12m_after"])}

## Previous Classification Of Newly Added Projects

{markdown_table(previous_summary, ["layer", "new_from_previous_classification"])}

## Evidence Types By Layer

{markdown_table(layer_rows, ["layer", "new_evidence_types"])}

## Examples

{markdown_table(compact_examples, ["layer", "app_id", "start_date", "previous", "evidence", "term", "confidence", "title"])}

## Evidence Notes

- C1 and C2 are the highest-precision expansion layers. C2 may add zero
  projects if all technical fingerprints in the available project text also
  appear with explicit sequence wording or are already in C0/C1.
- C3 is intentionally lower confidence and reviewable. It only uses specific
  rare/coding/burden/LoF phrases, not generic genetic/genomic/gene/variant or
  sequencing words alone.
- C4 currently has one verified non-WGS/WES product class: OMOP Field 20142,
  released on RAP in July 2023. No entire modality or tier is assumed RAP-only.
- C5 publication evidence must be pre-policy to count as direct pre-policy RAP
  use. Project text RAP mentions without an independent pre-policy publication
  timestamp are flagged for review.
- C6 uses local Schema 19/24 linked publication metadata, titles, abstracts,
  dates, DOI/PMID, and requires UK Biobank/UKB proximity to the modality term.
  It does not fetch arbitrary full text, so full-text methods review remains a
  follow-up audit item.
- `{manual_review_count:,}` cumulative candidate rows are flagged for manual
  review, primarily C3/C4/C6 rows, prior `MIXED` rows, and post-policy
  publication-product evidence.

## Official UKB Sources Used

- UKB RAP transition notice: {UKB_RAP_TRANSITION_SOURCE}
- UKB past data releases: {PAST_RELEASES_SOURCE}
- WES category 170: {WES_SOURCE}
- WGS category 180: {WGS_SOURCE}
- WGS DRAGEN category 185: {WGS_DRAGEN_SOURCE}
- WGS GATK/GraphTyper category 270: {WGS_GRAPHTYPER_SOURCE}
- Previous WGS releases category 271: {WGS_PREVIOUS_SOURCE}
- OMOP Field 20142: {OMOP_SOURCE}

## Outputs

- `{display_path(paths.project_review)}`
- `{display_path(paths.evidence_dictionary)}`
- `{display_path(paths.layer_counts)}`
- `{display_path(paths.previous_class_counts)}`
- `{display_path(paths.examples)}`
- `{display_path(paths.summary_json)}`
"""
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(report, encoding="utf-8")


def build_control_expansion_outputs(
    stage3_classification_path: Path,
    schema19_path: Path,
    schema24_path: Path,
    output_dir: Path,
    expected_working: int,
    source_commit: str,
) -> dict[str, object]:
    stage3_rows = read_csv(stage3_classification_path)
    if len(stage3_rows) != expected_working:
        raise ValueError(
            f"Expected {expected_working:,} Stage 3 project rows; found {len(stage3_rows):,}."
        )
    c0_count = sum(row["classification"] == "ALREADY_RAP_BOUND" for row in stage3_rows)
    if c0_count != 42:
        raise ValueError(f"Expected fixed C0 baseline of 42 projects; found {c0_count}.")

    app_to_pubs = load_publication_links(schema19_path, schema24_path)
    review_rows = build_review_rows(stage3_rows, app_to_pubs)
    evidence_rows = evidence_dictionary_rows()
    layer_rows = layer_count_rows(review_rows)
    previous_rows = previous_class_count_rows(review_rows)
    examples = example_rows(review_rows)

    paths = output_paths(output_dir)
    write_csv(paths.project_review, review_rows, REVIEW_FIELDS)
    write_csv(
        paths.evidence_dictionary,
        evidence_rows,
        [
            "term_id",
            "term_or_expression",
            "regex",
            "underlying_data_modality_or_product",
            "why_it_implies_pre_policy_rap_exposure",
            "official_ukb_source",
            "official_evidence",
            "effective_date",
            "evidence_strength",
            "used_in_layers",
        ],
    )
    write_csv(
        paths.layer_counts,
        layer_rows,
        [
            "layer",
            "new_projects",
            "cumulative_projects",
            "new_before_policy",
            "new_after_policy",
            "cumulative_before_policy",
            "cumulative_after_policy",
            "new_within_6m_before",
            "new_within_6m_after",
            "new_within_12m_before",
            "new_within_12m_after",
            "cumulative_within_6m_before",
            "cumulative_within_6m_after",
            "cumulative_within_12m_before",
            "cumulative_within_12m_after",
            "new_from_previous_classification",
            "new_evidence_types",
        ],
    )
    write_csv(
        paths.previous_class_counts,
        previous_rows,
        ["layer", "previous_classification", "new_projects"],
    )
    write_csv(
        paths.examples,
        examples,
        [
            "layer",
            "app_id",
            "start_date",
            "previous_classification",
            "evidence_type",
            "matched_term_or_expression",
            "confidence",
            "manual_review_flag",
            "title",
            "supporting_text_excerpt",
        ],
    )

    summary = {
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "source_commit": source_commit,
        "policy_date": POLICY_DATE.isoformat(),
        "stage": "stage3_control_expansion_frontier_only",
        "did_regressions_run": False,
        "outcome_analysis_run": False,
        "stage3_classification_file": display_path(stage3_classification_path),
        "stage3_classification_file_sha256": file_sha256(stage3_classification_path),
        "schema19_file": display_path(schema19_path),
        "schema19_file_sha256": file_sha256(schema19_path) if schema19_path.exists() else "",
        "schema24_file": display_path(schema24_path),
        "schema24_file_sha256": file_sha256(schema24_path) if schema24_path.exists() else "",
        "working_universe_projects": len(stage3_rows),
        "fixed_c0_projects": c0_count,
        "cumulative_control_candidate_projects": len(review_rows),
        "manual_review_candidate_projects": sum(
            row["manual_review_flag"] == "yes" for row in review_rows
        ),
        "layer_counts": layer_rows,
        "previous_class_counts": previous_rows,
        "evidence_dictionary_terms": len(evidence_rows),
        "publication_linked_app_ids": len(app_to_pubs),
    }
    paths.summary_json.parent.mkdir(parents=True, exist_ok=True)
    paths.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(
        paths=paths,
        review_rows=review_rows,
        layer_rows=layer_rows,
        previous_rows=previous_rows,
        examples=examples,
        source_commit=source_commit,
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage3-classification", type=Path, default=DEFAULT_STAGE3_CLASSIFICATION)
    parser.add_argument("--schema19", type=Path, default=DEFAULT_SCHEMA19)
    parser.add_argument("--schema24", type=Path, default=DEFAULT_SCHEMA24)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-working", type=int, default=6935)
    parser.add_argument("--source-commit", default="")
    args = parser.parse_args(argv)

    summary = build_control_expansion_outputs(
        stage3_classification_path=args.stage3_classification,
        schema19_path=args.schema19,
        schema24_path=args.schema24,
        output_dir=args.output_dir,
        expected_working=args.expected_working,
        source_commit=args.source_commit,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
