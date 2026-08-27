#!/usr/bin/env python3
"""Compatibility entrypoint for the archived DID Stage 4/5 script."""

try:
    from scripts._archive_loader import load_archived_script
except ModuleNotFoundError:
    from _archive_loader import load_archived_script

_module = load_archived_script(
    "stage4_5_fast_design_regression.py",
    "_archived_stage4_5_fast_design_regression",
)
globals().update({name: value for name, value in vars(_module).items() if not name.startswith("__")})

if __name__ == "__main__":
    main()
