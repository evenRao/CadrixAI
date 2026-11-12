from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cadrix_v2.parsers.llm_parser import LLMParser
from cadrix_v2.service import plan_design


class ParserTests(unittest.TestCase):
    def test_phone_stand_prompt(self) -> None:
        result = plan_design("Make a phone stand for a 75mm wide phone with a 20 degree angle and cable hole.")
        self.assertTrue(result.success)
        self.assertEqual(result.model_type, "phone_stand")
        self.assertEqual(result.intent.dimensions["phone_width_mm"], 75.0)
        self.assertEqual(result.intent.dimensions["angle_degrees"], 70.0)
        self.assertTrue(result.intent.features["cable_hole"])

    def test_box_with_lid_prompt(self) -> None:
        result = plan_design("Box with lid 120x80x60 mm with 0.4mm clearance.")
        self.assertTrue(result.success)
        self.assertEqual(result.model_type, "box_with_lid")
        self.assertEqual(result.parameters["length_mm"], 120.0)
        self.assertEqual(result.parameters["width_mm"], 80.0)
        self.assertEqual(result.parameters["height_mm"], 60.0)

    def test_cable_clip_prompt(self) -> None:
        result = plan_design("Cable clip for 6mm cable with mounting base and screw hole.")
        self.assertTrue(result.success)
        self.assertEqual(result.model_type, "cable_clip")
        self.assertEqual(result.parameters["cable_diameter_mm"], 6.0)
        self.assertTrue(result.parameters["mounting_base"])
        self.assertTrue(result.parameters["screw_hole"])

    def test_snap_fit_box_prompt(self) -> None:
        result = plan_design("Snap-fit box 90x60x35 mm with 0.4mm clearance and 16mm snap tabs.")
        self.assertTrue(result.success)
        self.assertEqual(result.model_type, "snap_fit_box")
        self.assertEqual(result.parameters["length_mm"], 90.0)
        self.assertEqual(result.parameters["width_mm"], 60.0)
        self.assertEqual(result.parameters["height_mm"], 35.0)
        self.assertEqual(result.parameters["snap_tab_width_mm"], 16.0)

    def test_gridfinity_prompt(self) -> None:
        result = plan_design("Gridfinity bin 2 by 2 units, 3 units tall.")
        self.assertTrue(result.success)
        self.assertEqual(result.model_type, "gridfinity_bin")
        self.assertEqual(result.parameters["grid_units_x"], 2)
        self.assertEqual(result.parameters["grid_units_y"], 2)
        self.assertEqual(result.parameters["height_units"], 3)

    def test_llm_parser_falls_back_to_rule_based_when_ollama_unavailable(self) -> None:
        parser = LLMParser()
        with patch.object(LLMParser, "_request_ollama_payload", side_effect=RuntimeError("offline")):
            result = parser.parse("Make a phone stand for a 75mm wide phone.")
        self.assertIsNotNone(result.intent)
        self.assertEqual(result.intent.model_type, "phone_stand")
        self.assertTrue(any("Falling back" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
