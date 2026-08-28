"""Helpers for compatibility entrypoints that load archived analysis scripts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_archived_script(filename: str, module_name: str) -> ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]

    path = Path(__file__).resolve().parents[1] / "analyses" / "did_archive" / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load archived script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module
