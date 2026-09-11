#!/usr/bin/env python3
"""Compatibility wrapper for the canonical UKB-DMCA leakage analysis."""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    for parent in Path(__file__).resolve().parents:
        target = parent / "ukb_dmca" / "leakage_application_analysis" / "scripts" / "leakage_its_analysis.py"
        if target.exists():
            runpy.run_path(str(target), run_name="__main__")
            return
    raise RuntimeError("Could not find ukb_dmca/leakage_application_analysis/scripts/leakage_its_analysis.py")


if __name__ == "__main__":
    main()
