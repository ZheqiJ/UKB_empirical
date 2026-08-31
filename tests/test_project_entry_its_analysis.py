import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analyses" / "interrupted_time_series" / "scripts" / "project_entry_its_analysis.py"


def load_module():
    spec = importlib.util.spec_from_file_location("project_entry_its_analysis", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ProjectEntryITSAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = load_module()

    def test_project_entry_outputs_validate(self):
        self.analysis.validate_outputs()

    def test_breakpoint_coding(self):
        months = self.analysis.month_range(self.analysis.PRIMARY_START, self.analysis.PRIMARY_END)
        X, names = self.analysis.design_rows(months)
        post_idx = names.index("PostJuly2024")
        time_after_idx = names.index("TimeAfterJuly2024")
        june = months.index(self.analysis.date(2024, 6, 1))
        july = months.index(self.analysis.date(2024, 7, 1))
        self.assertEqual(X[june][post_idx], 0.0)
        self.assertEqual(X[june][time_after_idx], 0.0)
        self.assertEqual(X[july][post_idx], 1.0)
        self.assertEqual(X[july][time_after_idx], 1.0)


if __name__ == "__main__":
    unittest.main()
