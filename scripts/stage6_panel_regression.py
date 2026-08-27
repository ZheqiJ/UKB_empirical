#!/usr/bin/env python3
"""Compatibility entrypoint for the archived DID Design 1 panel script."""

try:
    from scripts._archive_loader import load_archived_script
except ModuleNotFoundError:
    from _archive_loader import load_archived_script

_module = load_archived_script(
    "stage6_panel_regression.py",
    "_archived_stage6_panel_regression",
)
globals().update({name: value for name, value in vars(_module).items() if not name.startswith("__")})

if __name__ == "__main__":
    main()
