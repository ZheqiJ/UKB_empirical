#!/usr/bin/env python3
"""Build a Stata/esttab-style Design 1 regression table.

The project regressions are estimated by the Python pipeline, but the supervisor
often wants the result in the compact applied-economics table format: coefficient,
clustered standard error in parentheses, model/sample rows, and star notation.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DID_ARCHIVE = ROOT / "analyses" / "did_archive"
ANALYSIS_DIR = DID_ARCHIVE / "data" / "analysis" / "design1_quarterly_publication"
REPORT_DIR = DID_ARCHIVE / "reports"

REGRESSION_RESULTS = ANALYSIS_DIR / "design1_regression_results.csv"
PRETREND_RESULTS = ANALYSIS_DIR / "design1_pretrend_tests.csv"
CSV_OUTPUT = ANALYSIS_DIR / "design1_stata_style_results_table.csv"
MD_OUTPUT = REPORT_DIR / "design1_stata_style_results_table.md"
TEX_OUTPUT = REPORT_DIR / "design1_stata_style_results_table.tex"

CONTROL_DEFS = ["CONTROL_C05", "CONTROL_C06"]
OUTCOMES = ["publication_count", "any_publication"]
PANELS = [
    ("Panel A. Q0: Application FE + calendar-quarter FE", "Q0_quarterly_incumbent_did", "No"),
    ("Panel B. Q1: Q0 + project-age-bin FE", "Q1_quarterly_incumbent_did_age_adjusted", "Yes"),
]
OUTCOME_LABELS = {
    "publication_count": "Publication count",
    "any_publication": "Any publication",
}
CONTROL_LABELS = {
    "CONTROL_C05": "C05",
    "CONTROL_C06": "C06",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fmt_num(value: str | float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def fmt_int(value: str | int) -> str:
    return f"{int(value):,}"


def stars(p_value: str) -> str:
    p = float(p_value)
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def coef_cell(row: dict[str, str]) -> str:
    return f"{fmt_num(row['estimate'])}{stars(row['p_value'])}"


def se_cell(row: dict[str, str]) -> str:
    return f"({fmt_num(row['clustered_se'])})"


def tex_coef_cell(row: dict[str, str]) -> str:
    star_text = stars(row["p_value"])
    suffix = f"\\sym{{{star_text}}}" if star_text else ""
    return f"{fmt_num(row['estimate'])}{suffix}"


def pretrend_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row["control_definition"], row["outcome"])
        out[key] = row["p_value"]
    return out


def table_columns() -> list[tuple[str, str]]:
    return [(control, outcome) for outcome in OUTCOMES for control in CONTROL_DEFS]


def select_regressions(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
    selected: dict[tuple[str, str, str], dict[str, str]] = {}
    wanted_designs = {design for _, design, _ in PANELS}
    for row in rows:
        if row["design"] not in wanted_designs:
            continue
        if row["control_definition"] not in CONTROL_DEFS:
            continue
        if row["outcome"] not in OUTCOMES:
            continue
        if row["cluster"] != "application":
            continue
        key = (row["design"], row["control_definition"], row["outcome"])
        selected[key] = row
    return selected


def build_long_table(
    regressions: dict[tuple[str, str, str], dict[str, str]],
    pretrends: dict[tuple[str, str], str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    column_id = 0
    for panel_title, design, age_fe in PANELS:
        for outcome in OUTCOMES:
            for control in CONTROL_DEFS:
                column_id += 1
                reg = regressions[(design, control, outcome)]
                rows.append(
                    {
                        "panel": panel_title,
                        "column": column_id,
                        "design": design,
                        "outcome": outcome,
                        "outcome_label": OUTCOME_LABELS[outcome],
                        "control_definition": control,
                        "control_label": CONTROL_LABELS[control],
                        "coefficient": reg["estimate"],
                        "clustered_se": reg["clustered_se"],
                        "p_value": reg["p_value"],
                        "stars": stars(reg["p_value"]),
                        "n_obs": reg["n_obs"],
                        "n_apps": reg["n_apps"],
                        "n_treated_apps": reg["n_treated_apps"],
                        "n_control_apps": reg["n_control_apps"],
                        "application_fe": "Yes",
                        "calendar_quarter_fe": "Yes",
                        "project_age_bin_fe": age_fe,
                        "cluster": "application",
                        "pretrend_p_value": pretrends[(control, outcome)],
                    }
                )
    return rows


def panel_matrix(
    regressions: dict[tuple[str, str, str], dict[str, str]],
    pretrends: dict[tuple[str, str], str],
    design: str,
    age_fe: str,
) -> list[list[str]]:
    columns = table_columns()
    regs = [regressions[(design, control, outcome)] for control, outcome in columns]
    return [
        ["Outcome", *[OUTCOME_LABELS[outcome] for _, outcome in columns]],
        ["Control definition", *[CONTROL_LABELS[control] for control, _ in columns]],
        ["Treated x Post", *[coef_cell(row) for row in regs]],
        ["", *[se_cell(row) for row in regs]],
        ["Observations", *[fmt_int(row["n_obs"]) for row in regs]],
        ["Applications", *[fmt_int(row["n_apps"]) for row in regs]],
        ["Treated apps", *[fmt_int(row["n_treated_apps"]) for row in regs]],
        ["Control apps", *[fmt_int(row["n_control_apps"]) for row in regs]],
        ["Application FE", *["Yes" for _ in regs]],
        ["Calendar-quarter FE", *["Yes" for _ in regs]],
        ["Project-age-bin FE", *[age_fe for _ in regs]],
        ["SE clustered by", *["Application" for _ in regs]],
        ["Pretrend p-value", *[fmt_num(pretrends[(control, outcome)]) for control, outcome in columns]],
    ]


def markdown_table(matrix: list[list[str]]) -> str:
    widths = [max(len(row[i]) for row in matrix) for i in range(len(matrix[0]))]
    lines = [
        "| " + " | ".join(matrix[0][i].ljust(widths[i]) for i in range(len(widths))) + " |",
        "| " + " | ".join("-" * widths[i] for i in range(len(widths))) + " |",
    ]
    for row in matrix[1:]:
        lines.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(widths))) + " |")
    return "\n".join(lines)


def build_markdown(regressions: dict[tuple[str, str, str], dict[str, str]], pretrends: dict[tuple[str, str], str]) -> str:
    parts = [
        "# Design 1 Stata-Style Regression Table",
        "",
        "Outcome variables are quarterly publication count and an indicator for any publication.",
        "The reported coefficient is `Treated x Post` from the incumbent-project DID.",
        "Application-clustered standard errors are in parentheses.",
        "",
    ]
    for panel_title, design, age_fe in PANELS:
        parts.extend(
            [
                f"## {panel_title}",
                "",
                markdown_table(panel_matrix(regressions, pretrends, design, age_fe)),
                "",
            ]
        )
    parts.extend(
        [
            "Notes: All specifications use the fixed 6,935 matched-project universe and the post-entry risk-set panel.",
            "The post period treats 2024Q3 as post. Stars follow the Stata/esttab convention: * p<0.10, ** p<0.05, *** p<0.01.",
            "C06 is the broadest provisional control sensitivity definition; it should not be interpreted as a finalized clean control group.",
            "",
        ]
    )
    return "\n".join(parts)


def tex_escape(value: str) -> str:
    return value.replace("_", "\\_").replace("%", "\\%").replace("&", "\\&")


def tex_line(cells: list[str]) -> str:
    return " & ".join(cells) + r" \\"


def build_tex(regressions: dict[tuple[str, str, str], dict[str, str]], pretrends: dict[tuple[str, str], str]) -> str:
    columns = table_columns()
    lines = [
        r"\begin{table}[!htbp]\centering",
        r"\def\sym#1{\ifmmode^{#1}\else\(^{#1}\)\fi}",
        r"\caption{Design 1 Quarterly DID: Stata-Style Results}",
        r"\label{tab:design1_stata_style}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        tex_line(["", "(1)", "(2)", "(3)", "(4)"]),
        tex_line(["Outcome", *[tex_escape(OUTCOME_LABELS[outcome]) for _, outcome in columns]]),
        tex_line(["Control definition", *[CONTROL_LABELS[control] for control, _ in columns]]),
        r"\midrule",
    ]
    for panel_title, design, age_fe in PANELS:
        regs = [regressions[(design, control, outcome)] for control, outcome in columns]
        lines.append(rf"\multicolumn{{5}}{{l}}{{\textit{{{tex_escape(panel_title)}}}}} \\")
        lines.append(tex_line([r"Treated $\times$ Post", *[tex_coef_cell(row) for row in regs]]))
        lines.append(tex_line(["", *[f"({fmt_num(row['clustered_se'])})" for row in regs]]))
        lines.append(tex_line(["Observations", *[fmt_int(row["n_obs"]) for row in regs]]))
        lines.append(tex_line(["Applications", *[fmt_int(row["n_apps"]) for row in regs]]))
        lines.append(tex_line(["Treated apps", *[fmt_int(row["n_treated_apps"]) for row in regs]]))
        lines.append(tex_line(["Control apps", *[fmt_int(row["n_control_apps"]) for row in regs]]))
        lines.append(tex_line(["Application FE", *["Yes" for _ in regs]]))
        lines.append(tex_line(["Calendar-quarter FE", *["Yes" for _ in regs]]))
        lines.append(tex_line(["Project-age-bin FE", *[age_fe for _ in regs]]))
        lines.append(tex_line(["Pretrend p-value", *[fmt_num(pretrends[(control, outcome)]) for control, outcome in columns]]))
        lines.append(r"\addlinespace")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\begin{minipage}{0.95\linewidth}",
            r"\footnotesize Notes: Application-clustered standard errors are in parentheses. "
            r"Stars follow the esttab convention: \sym{*} p<0.10, \sym{**} p<0.05, \sym{***} p<0.01. "
            r"All specifications use the fixed 6,935 matched-project universe and the post-entry risk-set panel. "
            r"C06 is the broadest provisional control sensitivity definition, not a finalized clean control group.",
            r"\end{minipage}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    regressions = select_regressions(read_csv(REGRESSION_RESULTS))
    pretrends = pretrend_lookup(read_csv(PRETREND_RESULTS))
    required_keys = [
        (design, control, outcome)
        for _, design, _ in PANELS
        for outcome in OUTCOMES
        for control in CONTROL_DEFS
    ]
    missing = [key for key in required_keys if key not in regressions]
    if missing:
        raise SystemExit(f"Missing regression rows: {missing}")
    long_rows = build_long_table(regressions, pretrends)
    write_csv(CSV_OUTPUT, long_rows, list(long_rows[0].keys()))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MD_OUTPUT.write_text(build_markdown(regressions, pretrends), encoding="utf-8")
    TEX_OUTPUT.write_text(build_tex(regressions, pretrends), encoding="utf-8")
    print(
        {
            "csv": str(CSV_OUTPUT.relative_to(ROOT)),
            "markdown": str(MD_OUTPUT.relative_to(ROOT)),
            "latex": str(TEX_OUTPUT.relative_to(ROOT)),
            "columns": len(table_columns()),
            "panels": len(PANELS),
        }
    )


if __name__ == "__main__":
    main()
