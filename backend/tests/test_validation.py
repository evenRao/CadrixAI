from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadrix_v2.registry import get_model_spec
from cadrix_v2.service import plan_design
from cadrix_v2.validators import validate_parameters


class ValidationTests(unittest.TestCase):
    def test_invalid_negative_dimension(self) -> None:
        spec = get_model_spec("phone_stand")
        result = validate_parameters(spec, {**spec.defaults, "phone_width_mm": -10})
        self.assertTrue(result.errors)
        self.assertIn("greater than 0", result.errors[0].message)

    def test_missing_required_parameter_fallback(self) -> None:
        result = plan_design("small phone stand")
        self.assertTrue(result.success)
        self.assertEqual(result.model_type, "phone_stand")
        self.assertGreater(result.parameters["phone_width_mm"], 0)
        self.assertTrue(result.assumptions)

    def test_snap_fit_box_rejects_oversized_tab_layout(self) -> None:
        spec = get_model_spec("snap_fit_box")
        result = validate_parameters(spec, {**spec.defaults, "length_mm": 42, "tab_count_per_side": 3})
        self.assertTrue(result.errors)
        self.assertTrue(any("too short" in issue.message.lower() for issue in result.errors))


if __name__ == "__main__":
    unittest.main()
