#!/usr/bin/env python3
"""Compatibility entrypoint for the archived DID Stata-style table script."""

try:
    from scripts._archive_loader import load_archived_script
except ModuleNotFoundError:
    from _archive_loader import load_archived_script

_module = load_archived_script("design1_stata_table.py", "_archived_design1_stata_table")
globals().update({name: value for name, value in vars(_module).items() if not name.startswith("__")})

if __name__ == "__main__":
    main()
