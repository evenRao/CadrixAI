from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cadquery as cq
import trimesh

from cadrix_v2.geometry import estimate_dimensions_mm, generate_geometry
from cadrix_v2.geometry_core import open_shell
from cadrix_v2.exporters import OUT_DIR, export_stl, export_step
from cadrix_v2.library_geometry import LIBRARY_GENERATORS
from cadrix_v2.registry import MODEL_REGISTRY, detect_model_type
from cadrix_v2.service import generate_design, plan_design
from cadrix_v2.validators import validate_parameters
from test_generation import make_request


class ModelQualityTests(unittest.TestCase):
    def assert_solid(self, body, count=1):
        self.assertTrue(body.val().isValid())
        self.assertEqual(body.solids().size(), count)
        self.assertGreater(body.val().Volume(), 0)
        self.assertAlmostEqual(body.val().BoundingBox().zmin, 0, places=5)

    def test_all_default_models_have_valid_watertight_print_meshes(self):
        with tempfile.TemporaryDirectory(prefix="mesh_quality_", dir=OUT_DIR) as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to(OUT_DIR.resolve()))
            for name, spec in MODEL_REGISTRY.items():
                with self.subTest(model=name):
                    self.assertFalse(validate_parameters(spec, spec.defaults).errors)
                    geometry = generate_geometry(name, spec.defaults)
                    self.assert_solid(geometry.primary_solid, 2 if name == "hinge" else 1)
                    self.assertTrue(geometry.preview_solid.val().isValid())
                    for part in geometry.extra_parts:
                        self.assert_solid(part.solid)
                    path = Path(folder) / f"{name}.stl"
                    export_stl(geometry.primary_solid, path)
                    mesh = trimesh.load_mesh(io.BytesIO(path.read_bytes()), file_type="stl")
                    self.assertTrue(mesh.is_watertight)
                    self.assertTrue(mesh.is_winding_consistent)
                    self.assertGreater(mesh.volume, 0)

    def test_every_example_resolves_to_its_own_model(self):
        for name, spec in MODEL_REGISTRY.items():
            for example in spec.examples:
                with self.subTest(model=name, example=example):
                    plan = plan_design(example)
                    self.assertEqual(plan.model_type, name)
                    self.assertTrue(plan.success, plan.errors)

    def test_catalog_presets_and_feature_variants_generate(self):
        for name, spec in MODEL_REGISTRY.items():
            variants = [*spec.size_presets.values(), *[{item.key: not item.default} for item in spec.parameter_definitions if item.type == "boolean"]]
            for overrides in variants:
                with self.subTest(model=name, overrides=overrides):
                    parameters = {**spec.defaults, **overrides}
                    self.assertFalse(validate_parameters(spec, parameters).errors)
                    self.assert_solid(generate_geometry(name, parameters).primary_solid, 2 if name == "hinge" else 1)

    def test_new_numeric_boundaries_build_when_the_layout_is_valid(self):
        for name in LIBRARY_GENERATORS:
            spec = MODEL_REGISTRY[name]
            for definition in spec.parameter_definitions:
                if definition.type not in {"integer", "number"}:
                    continue
                for value in (definition.minimum, definition.maximum):
                    if value is None:
                        continue
                    parameters = {**spec.defaults, definition.key: value}
                    if validate_parameters(spec, parameters).errors:
                        continue
                    with self.subTest(model=name, field=definition.key, value=value):
                        self.assert_solid(generate_geometry(name, parameters).primary_solid)

    def test_export_preserves_cad_dimensions_and_step_units(self):
        p = {**MODEL_REGISTRY["parts_tray"].defaults, "length_mm": 120, "width_mm": 80, "compartment_count": 3}
        body = generate_geometry("parts_tray", p).primary_solid
        before = estimate_dimensions_mm(body)
        with tempfile.TemporaryDirectory(prefix="export_quality_", dir=OUT_DIR) as folder:
            self.assertTrue(Path(folder).resolve().is_relative_to(OUT_DIR.resolve()))
            export_stl(body, Path(folder) / "tray.stl")
            export_step(body, Path(folder) / "tray.step")
            restored = cq.importers.importStep(str(Path(folder) / "tray.step"))
            self.assertEqual(estimate_dimensions_mm(restored), {"x": 120, "y": 80, "z": 20})
            self.assertEqual(estimate_dimensions_mm(body), before)

    def test_new_multipart_model_exports_a_loadable_preview_and_accessories(self):
        result = generate_design("Planter 90x80 mm with drainage holes and drip tray.", make_request())
        self.assertTrue(result.success, result.errors)
        self.assertEqual({part.label for part in result.files.extra_downloads}, {"Drip tray STL", "Drip tray STEP"})
        preview = OUT_DIR / result.files.glb.rsplit("/", 1)[-1]
        scene = trimesh.load(io.BytesIO(preview.read_bytes()), file_type="glb", force="scene")
        self.assertTrue(scene.geometry)
        for mesh in scene.geometry.values():
            self.assertTrue(mesh.is_watertight)

    def test_refined_models_preserve_requested_widths(self):
        phone = MODEL_REGISTRY["phone_stand"].defaults
        size = estimate_dimensions_mm(generate_geometry("phone_stand", phone).primary_solid)
        self.assertEqual(size["x"], phone["phone_width_mm"] + 2 * phone["side_margin_mm"])
        for mounted in (False, True):
            clip = {**MODEL_REGISTRY["cable_clip"].defaults, "clip_width_mm": 17, "mounting_base": mounted}
            self.assertEqual(estimate_dimensions_mm(generate_geometry("cable_clip", clip).primary_solid)["y"], 17)
        laptop = MODEL_REGISTRY["laptop_stand"].defaults
        self.assertEqual(estimate_dimensions_mm(generate_geometry("laptop_stand", laptop).primary_solid)["y"], laptop["laptop_width_mm"])

    def test_lightweight_phone_frame_and_cable_slot_remove_material(self):
        p = MODEL_REGISTRY["phone_stand"].defaults
        solid = generate_geometry("phone_stand", {**p, "lightweight": False}).primary_solid
        light = generate_geometry("phone_stand", p).primary_solid
        slotted = generate_geometry("phone_stand", {**p, "cable_slot": True}).primary_solid
        self.assertLess(light.val().Volume(), solid.val().Volume())
        self.assertLess(slotted.val().Volume(), light.val().Volume())
        self.assert_solid(slotted)

    def test_funnel_and_hose_have_a_continuous_open_bore(self):
        for name in ("funnel", "hose_adapter"):
            spec = MODEL_REGISTRY[name]
            body = generate_geometry(name, spec.defaults).primary_solid.val()
            height = estimate_dimensions_mm(cq.Workplane(obj=body))["z"]
            for fraction in (0.01, 0.2, 0.5, 0.8, 0.99):
                self.assertFalse(body.isInside(cq.Vector(0, 0, height * fraction)), name)

    def test_planter_tray_has_mating_clearance_and_separate_export(self):
        p = MODEL_REGISTRY["planter"].defaults
        geometry = generate_geometry("planter", p)
        self.assertEqual(len(geometry.extra_parts), 1)
        tray = geometry.extra_parts[0].solid
        inner_diameter = estimate_dimensions_mm(tray)["x"] - 2 * p["wall_thickness_mm"]
        pot_bottom_diameter = p["diameter_mm"] - 2 * p["taper_mm"]
        self.assertAlmostEqual(inner_diameter - pot_bottom_diameter, 2 * p["tray_clearance_mm"])
        self.assert_solid(tray)

    def test_drawer_mounting_bores_are_blind(self):
        p = MODEL_REGISTRY["drawer_pull"].defaults
        body = generate_geometry("drawer_pull", p).primary_solid.val()
        for x in (-p["hole_spacing_mm"] / 2, p["hole_spacing_mm"] / 2):
            self.assertFalse(body.isInside(cq.Vector(x, 0, p["hole_depth_mm"] / 2)))
            self.assertTrue(body.isInside(cq.Vector(x, 0, p["hole_depth_mm"] + 1)))

    def test_stackable_boxes_fit_without_intersecting(self):
        p = MODEL_REGISTRY["stackable_box"].defaults
        body = generate_geometry("stackable_box", p).primary_solid
        upper = body.translate((0, 0, p["height_mm"] - p["stack_lip_height_mm"]))
        self.assertLess(body.intersect(upper).val().Volume(), 1e-5)

    def test_rounded_shell_keeps_a_floor_and_declared_envelope(self):
        body = open_shell(80, 50, 20, 2.4, 3, 8)
        self.assertEqual(estimate_dimensions_mm(body), {"x": 80.0, "y": 50.0, "z": 20.0})
        self.assertTrue(body.val().isInside(cq.Vector(0, 0, 1)))
        self.assertFalse(body.val().isInside(cq.Vector(0, 0, 4)))

    def test_parser_reads_counts_and_explicit_dimensions_after_presets(self):
        tray = plan_design("Small parts tray 170x110x24 mm with 4 compartments.")
        self.assertEqual([tray.parameters[key] for key in ("length_mm", "width_mm", "height_mm", "compartment_count")], [170, 110, 24, 4])
        battery = plan_design("Battery organizer with 18mm cell diameter, 12 cells, and 3 rows.")
        self.assertEqual([battery.parameters[key] for key in ("cell_diameter_mm", "cell_count", "row_count")], [18, 12, 3])
        clip = plan_design("Cable clip for 10mm cable.")
        self.assertEqual(clip.parameters["cable_diameter_mm"], 10)
        self.assertIsNone(detect_model_type("A model with enough capacity"))

    def test_invalid_numeric_inputs_return_validation_errors(self):
        spec = MODEL_REGISTRY["parts_tray"]
        for value in ("nonsense", float("nan"), float("inf"), -1):
            with self.subTest(value=value):
                self.assertTrue(validate_parameters(spec, {**spec.defaults, "length_mm": value}).errors)
        self.assertTrue(validate_parameters(spec, {**spec.defaults, "compartment_count": 2.5}).errors)
        self.assertFalse(validate_parameters(spec, {**spec.defaults, "corner_radius_mm": 0}).errors)

    def test_explicit_clearance_replaces_fit_defaults(self):
        for prompt, key, value in (
            ("Box with lid with 0.7mm clearance.", "lid_clearance_mm", 0.7),
            ("Tube end cap with 0.6mm clearance.", "fit_clearance_mm", 0.6),
            ("Desk grommet with 0.5mm clearance.", "fit_clearance_mm", 0.5),
            ("PCB enclosure with 1.5mm clearance.", "board_clearance_mm", 1.5),
        ):
            with self.subTest(prompt=prompt):
                plan = plan_design(prompt)
                self.assertTrue(plan.success, plan.errors)
                self.assertEqual(plan.parameters[key], value)

    def test_fractional_counts_are_rejected_in_generation(self):
        result = generate_design("Parts tray.", make_request(), parameter_overrides={"compartment_count": 2.5})
        self.assertFalse(result.success)
        self.assertTrue(any("whole number" in error for error in result.errors))

    def test_impossible_new_model_relationships_are_rejected(self):
        bad = {
            "funnel": {"outlet_diameter_mm": 6, "wall_thickness_mm": 4},
            "planter": {"diameter_mm": 40, "taper_mm": 20},
            "parts_tray": {"length_mm": 40, "compartment_count": 8},
            "angle_bracket": {"leg_length_mm": 20, "wall_thickness_mm": 8},
            "drawer_pull": {"hole_depth_mm": 25},
            "desk_grommet": {"flange_diameter_mm": 40},
            "hose_adapter": {"length_mm": 25, "end_length_mm": 20},
            "cable_comb": {"cable_diameter_mm": 16, "cable_spacing_mm": 6},
            "battery_organizer": {"cell_count": 2, "row_count": 3},
            "tube_end_cap": {"height_mm": 8, "floor_thickness_mm": 8},
        }
        for name, overrides in bad.items():
            with self.subTest(model=name):
                self.assertTrue(validate_parameters(MODEL_REGISTRY[name], {**MODEL_REGISTRY[name].defaults, **overrides}).errors)

    def test_parameter_corrections_can_recover_a_failed_plan(self):
        result = generate_design("Parts tray 20x100x20 mm.", make_request(), parameter_overrides={"length_mm": 120})
        self.assertTrue(result.success, result.errors)
        self.assertEqual(result.metadata.estimated_dimensions_mm["x"], 120)

    def test_cad_failure_is_a_structured_response(self):
        with patch("cadrix_v2.service.generate_geometry", side_effect=ValueError("invalid solid")), self.assertLogs("cadrix_v2.service", level="ERROR"):
            result = generate_design("Parts tray 120x80x20 mm.", make_request())
        self.assertFalse(result.success)
        self.assertTrue(result.errors)
        self.assertIsNone(result.files.stl)


if __name__ == "__main__":
    unittest.main()
