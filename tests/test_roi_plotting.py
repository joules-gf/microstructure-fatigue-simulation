import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "00_Main_Scripts" / "roi_plotting.py"


def load_module():
    spec = importlib.util.spec_from_file_location("roi_plotting", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RoiPlottingTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_format_roi_label_puts_side_first_and_replaces_underscores(self):
        self.assertEqual(self.module.format_roi_label("roi_left_01"), "Left roi 01")
        self.assertEqual(self.module.format_roi_label("roi_right_09"), "Right roi 09")

    def test_roi_ordering_supports_side_grouped_and_height_paired_views(self):
        roi_names = ["roi_right_02", "roi_left_01", "roi_right_01", "roi_left_02"]
        self.assertEqual(
            self.module.ordered_roi_names(roi_names, mode="grouped_by_side"),
            ["roi_left_01", "roi_left_02", "roi_right_01", "roi_right_02"],
        )
        self.assertEqual(
            self.module.ordered_roi_names(roi_names, mode="paired_by_height"),
            ["roi_left_01", "roi_right_01", "roi_left_02", "roi_right_02"],
        )

    def test_frame_context_uses_nearest_global_cycle_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "case.csv"
            csv_path.write_text(
                "ODB file name: case\n\n"
                "Step Time,U_Y,Total RF Y\n\n"
                "0.84,0.009,500\n"
                "0.85,0.010,523\n"
                "0.96,-0.009,-500\n"
            )
            context = self.module.frame_context_from_cycle_csv(csv_path, step_time=0.851)
        self.assertAlmostEqual(context.step_time, 0.85)
        self.assertAlmostEqual(context.global_strain, 0.010)
        self.assertAlmostEqual(context.global_stress, 523.0)

    def test_representative_roi_selection_uses_absolute_stress_magnitude(self):
        rows = [
            {"roi_name": "roi_left_01", "average_stress_mpa": -90.0, "average_plastic_strain": 0.010, "Phase 0": 25, "Phase 1": 25, "Phase 2": 25, "Phase 3": 25},
            {"roi_name": "roi_left_02", "average_stress_mpa": -130.0, "average_plastic_strain": 0.001, "Phase 0": 25, "Phase 1": 25, "Phase 2": 25, "Phase 3": 25},
            {"roi_name": "roi_right_01", "average_stress_mpa": -100.0, "average_plastic_strain": 0.005, "Phase 0": 25, "Phase 1": 25, "Phase 2": 25, "Phase 3": 25},
            {"roi_name": "roi_right_02", "average_stress_mpa": -85.0, "average_plastic_strain": 0.020, "Phase 0": 25, "Phase 1": 25, "Phase 2": 25, "Phase 3": 25},
        ]
        frame_data = pd.DataFrame(rows)
        selected = self.module.select_representative_rois(
            frame_data,
            global_stress=-110.0,
            global_plastic_strain=0.004,
        )
        self.assertEqual(selected.low_stress_high_plastic_roi, "roi_right_02")
        self.assertEqual(selected.high_stress_low_plastic_roi, "roi_left_02")
        self.assertGreater(selected.metrics.loc["roi_left_02", "stress_ratio"], 1.0)
        self.assertLess(selected.metrics.loc["roi_right_02", "stress_ratio"], 1.0)

    def test_frame_title_mentions_global_strain_and_frame_context(self):
        title = self.module.build_frame_title("Full ROI response", frame_number=85, step_time=0.85, global_strain=0.01)
        self.assertIn("Frame 85", title)
        self.assertIn("Step time 0.850", title)
        self.assertIn("global strain +0.0100", title)


if __name__ == "__main__":
    unittest.main()
