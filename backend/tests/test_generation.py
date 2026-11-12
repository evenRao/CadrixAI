from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
from cadrix_v2.registry import MODEL_REGISTRY
from cadrix_v2.service import generate_design
from starlette.requests import Request


def make_request() -> Request:
    scope = {
        "type": "http",
        "scheme": "http",
        "server": ("localhost", 8000),
        "method": "POST",
        "path": "/v2/generate",
        "headers": [],
        "app": main.app,
        "router": main.app.router,
    }
    return Request(scope)


class GenerationTests(unittest.TestCase):
    def test_phone_stand_generation(self) -> None:
        result = generate_design("Make a phone stand for a 75mm wide phone with a 20 degree angle and cable hole.", make_request())
        self.assertTrue(result.success)
        self.assertTrue(result.files.stl)
        self.assertTrue(result.files.step)

    def test_box_with_lid_generation(self) -> None:
        result = generate_design("Box with lid 120x80x60 mm with 0.4mm clearance.", make_request())
        self.assertTrue(result.success)
        self.assertEqual(result.metadata.estimated_dimensions_mm["x"], 120.0)
        self.assertEqual(result.metadata.estimated_dimensions_mm["y"], 80.0)
        self.assertEqual(result.metadata.estimated_dimensions_mm["z"], 60.0)
        labels = [item.label for item in result.files.extra_downloads]
        self.assertIn("Lid STL", labels)
        self.assertIn("Lid STEP", labels)

    def test_cable_clip_generation(self) -> None:
        result = generate_design("Cable clip for 6mm cable with mounting base and screw hole.", make_request())
        self.assertTrue(result.success)
        self.assertTrue(result.files.glb)

    def test_snap_fit_box_generation(self) -> None:
        result = generate_design("Snap-fit box 90x60x35 mm with 0.4mm clearance and 16mm snap tabs.", make_request())
        self.assertTrue(result.success)
        self.assertEqual(result.metadata.estimated_dimensions_mm["x"], 90.0)
        self.assertEqual(result.metadata.estimated_dimensions_mm["y"], 60.0)
        self.assertEqual(result.metadata.estimated_dimensions_mm["z"], 35.0)
        labels = [item.label for item in result.files.extra_downloads]
        self.assertIn("Lid STL", labels)
        self.assertIn("Lid STEP", labels)

    def test_simple_gear_generation(self) -> None:
        result = generate_design("Simple gear with 24 teeth, 40mm diameter, and 5mm bore.", make_request())
        self.assertTrue(result.success)
        self.assertGreater(result.metadata.estimated_dimensions_mm["x"], 35)

    def test_pcb_enclosure_generation(self) -> None:
        result = generate_design("PCB enclosure for an 80x50 mm board with ventilation slots.", make_request())
        self.assertTrue(result.success)
        labels = [item.label for item in result.files.extra_downloads]
        self.assertIn("Lid STL", labels)

    def test_every_v2_registry_example_generates(self) -> None:
        for spec in MODEL_REGISTRY.values():
            with self.subTest(model_type=spec.model_type):
                self.assertTrue(spec.implemented, msg=f"{spec.model_type} is still marked as unimplemented.")
                self.assertTrue(spec.examples, msg=f"{spec.model_type} is missing example prompts.")
                result = generate_design(spec.examples[0], make_request())
                self.assertTrue(result.success, msg=f"{spec.model_type} failed: {result.errors}")


if __name__ == "__main__":
    unittest.main()
