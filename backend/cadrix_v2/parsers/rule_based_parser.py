from __future__ import annotations

import re
from typing import Any, Callable

from cadrix_v2.parsers.parser_interface import DesignParser, ParserOutput
from cadrix_v2.prompt_utils import (
    coerce_bool_feature,
    extract_angle_degrees,
    extract_dimension_pair_mm,
    extract_dimension_triple_mm,
    extract_labeled_integer,
    extract_labeled_length_mm,
    extract_measurements,
    extract_size_word,
)
from cadrix_v2.registry import ModelSpec, detect_model_type, get_model_spec
from cadrix_v2.schemas import DesignIntent


class RuleBasedParser(DesignParser):
    def parse(self, prompt: str, requested_model_type: str | None = None) -> ParserOutput:
        model_type = detect_model_type(prompt, requested_model_type)
        if not model_type:
            return ParserOutput(
                intent=None,
                errors=["Could not match the prompt to a supported V2 build. Try naming a supported object such as phone stand, box with lid, cable clip, gear, or PCB enclosure."],
            )

        spec = get_model_spec(model_type)
        if not spec:
            return ParserOutput(intent=None, errors=[f"Unsupported V2 model type: {model_type}."])

        dimensions: dict[str, Any] = {}
        features: dict[str, Any] = {}
        print_settings: dict[str, Any] = {}
        assumptions: list[str] = []
        warnings: list[str] = []

        size_word = extract_size_word(prompt)
        if size_word and spec.size_presets.get(size_word):
            dimensions.update(spec.size_presets[size_word])
            assumptions.append(f"Applied the {size_word} size preset for {spec.title}.")

        wall = extract_labeled_length_mm(prompt, ["wall thickness", "wall"])
        if wall is not None:
            print_settings["wall_thickness_mm"] = wall

        tolerance = extract_labeled_length_mm(prompt, ["tolerance", "clearance"])
        if tolerance is not None:
            print_settings["tolerance_mm"] = tolerance

        rounded_edges = coerce_bool_feature(
            prompt,
            ["rounded edges", "rounded", "fillet", "filleted"],
            ["sharp edges", "square edges", "no rounded edges"],
        )
        if rounded_edges is not None:
            features["rounded_edges"] = rounded_edges

        parser = getattr(self, f"_parse_{model_type}", None)
        if parser is not None:
            parser(prompt, dimensions, features, print_settings, assumptions, warnings)
        else:
            self._parse_from_spec(spec, prompt, dimensions, features, print_settings, assumptions, warnings)

        intent = DesignIntent(
            model_type=model_type,
            dimensions=dimensions,
            features=features,
            print_settings=print_settings,
        )
        return ParserOutput(intent=intent, assumptions=assumptions, warnings=warnings)

    def _parse_phone_stand(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        triple = extract_dimension_triple_mm(prompt)
        if triple:
            width_mm, _, height_mm = triple
            dimensions.setdefault("phone_width_mm", width_mm)
            dimensions.setdefault("back_support_height_mm", height_mm)
            assumptions.append("Interpreted the first and third dimensions as phone width and back support height.")

        width = extract_labeled_length_mm(prompt, ["phone width", "wide phone", "phone wide", "device width"])
        if width is not None:
            dimensions["phone_width_mm"] = width

        device_thickness = extract_labeled_length_mm(prompt, ["phone thickness", "device thickness", "case thickness"])
        if device_thickness is not None:
            dimensions["device_thickness_mm"] = device_thickness

        base_t = extract_labeled_length_mm(prompt, ["base thickness"])
        if base_t is not None:
            dimensions["base_thickness_mm"] = base_t

        lip = extract_labeled_length_mm(prompt, ["front lip", "lip height"])
        if lip is not None:
            dimensions["front_lip_mm"] = lip

        cable_slot_width = extract_labeled_length_mm(prompt, ["cable slot width", "cable hole width", "charger slot width"])
        if cable_slot_width is not None:
            dimensions["cable_slot_width_mm"] = cable_slot_width

        angle = extract_angle_degrees(prompt, ["angle", "tilt"])
        if angle is not None:
            if angle < 45:
                dimensions["angle_degrees"] = 90 - angle
                assumptions.append("Converted the low phone stand angle into a back-support angle from the build plate.")
            else:
                dimensions["angle_degrees"] = angle

        cable_feature = coerce_bool_feature(prompt, ["cable hole", "cable slot", "charger slot", "cable management"])
        if cable_feature is not None:
            features["cable_hole"] = cable_feature

        if "phone_width_mm" not in dimensions:
            assumptions.append("Used the default phone width because no explicit device width was found.")
        if "angle_degrees" not in dimensions:
            assumptions.append("Used the default stand angle because no explicit angle was found.")

    def _parse_box_with_lid(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        triple = extract_dimension_triple_mm(prompt)
        if triple:
            dimensions["length_mm"], dimensions["width_mm"], dimensions["height_mm"] = triple
        else:
            pair = extract_dimension_pair_mm(prompt)
            if pair:
                dimensions["length_mm"], dimensions["width_mm"] = pair
                assumptions.append("Used the two provided box dimensions and kept the default height.")

        floor = extract_labeled_length_mm(prompt, ["floor thickness", "base thickness"])
        if floor is not None:
            dimensions["floor_thickness_mm"] = floor

        lid_height = extract_labeled_length_mm(prompt, ["lid height"])
        if lid_height is not None:
            dimensions["lid_height_mm"] = lid_height

        corner_radius = extract_labeled_length_mm(prompt, ["corner radius"])
        if corner_radius is not None:
            dimensions["corner_radius_mm"] = corner_radius

        snap_fit = coerce_bool_feature(prompt, ["snap fit", "snap-fit", "snap lid"])
        if snap_fit is not None:
            features["snap_fit_lip"] = snap_fit

        if "length_mm" not in dimensions:
            assumptions.append("Used medium box dimensions because no explicit outer size was found.")

    def _parse_cable_clip(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        pair = extract_dimension_pair_mm(prompt)
        if pair:
            dimensions.setdefault("cable_diameter_mm", pair[0])
            dimensions.setdefault("clip_width_mm", pair[1])
            assumptions.append("Interpreted the first two cable clip dimensions as cable diameter and clip width.")

        cable_d = extract_labeled_length_mm(prompt, ["cable diameter", "wire diameter", "cord diameter"])
        if cable_d is not None:
            dimensions["cable_diameter_mm"] = cable_d

        clip_width = extract_labeled_length_mm(prompt, ["clip width"])
        if clip_width is not None:
            dimensions["clip_width_mm"] = clip_width

        gap = extract_labeled_length_mm(prompt, ["opening gap", "clip gap"])
        if gap is not None:
            dimensions["opening_gap_mm"] = gap

        base_length = extract_labeled_length_mm(prompt, ["base length", "mounting base"])
        if base_length is not None:
            dimensions["base_length_mm"] = base_length

        screw_hole_diameter = extract_labeled_length_mm(prompt, ["screw hole", "screw hole diameter"])
        if screw_hole_diameter is not None:
            dimensions["screw_hole_diameter_mm"] = screw_hole_diameter

        mounting_base = coerce_bool_feature(prompt, ["mounting base", "mounted base", "screw mount"])
        if mounting_base is not None:
            features["mounting_base"] = mounting_base

        screw_hole = coerce_bool_feature(prompt, ["screw hole", "mounting hole"])
        if screw_hole is not None:
            features["screw_hole"] = screw_hole

        if "cable_diameter_mm" not in dimensions:
            assumptions.append("Used the default cable diameter because none was detected.")

    def _parse_simple_gear(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        teeth = extract_labeled_integer(prompt, ["teeth", "tooth"])
        if teeth is not None:
            dimensions["tooth_count"] = teeth

        outer_diameter = extract_labeled_length_mm(prompt, ["outer diameter", "gear diameter", "diameter"])
        if outer_diameter is not None:
            dimensions["outer_diameter_mm"] = outer_diameter

        pitch_radius = extract_labeled_length_mm(prompt, ["pitch radius"])
        if pitch_radius is not None and "outer_diameter_mm" not in dimensions:
            dimensions["outer_diameter_mm"] = pitch_radius * 2.0
            assumptions.append("Approximated outer diameter directly from the requested pitch radius.")

        thickness = extract_labeled_length_mm(prompt, ["gear thickness", "thickness"])
        if thickness is not None:
            dimensions["thickness_mm"] = thickness

        bore = extract_labeled_length_mm(prompt, ["bore", "center bore", "bore diameter"])
        if bore is not None:
            dimensions["bore_diameter_mm"] = bore

        if "tooth_count" not in dimensions:
            assumptions.append("Used the default tooth count because none was explicitly given.")

    def _parse_pcb_enclosure(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        triple = extract_dimension_triple_mm(prompt)
        if triple:
            dimensions["board_length_mm"], dimensions["board_width_mm"], dimensions["enclosure_height_mm"] = triple
            assumptions.append("Interpreted the PCB enclosure triple as board length, board width, and enclosure height.")
        else:
            pair = extract_dimension_pair_mm(prompt)
            if pair:
                dimensions["board_length_mm"], dimensions["board_width_mm"] = pair
                assumptions.append("Interpreted the PCB enclosure pair as board length and board width.")

        board_length = extract_labeled_length_mm(prompt, ["board length", "pcb length"])
        if board_length is not None:
            dimensions["board_length_mm"] = board_length

        board_width = extract_labeled_length_mm(prompt, ["board width", "pcb width"])
        if board_width is not None:
            dimensions["board_width_mm"] = board_width

        board_thickness = extract_labeled_length_mm(prompt, ["board thickness", "pcb thickness"])
        if board_thickness is not None:
            dimensions["board_thickness_mm"] = board_thickness

        clearance = extract_labeled_length_mm(prompt, ["board clearance", "clearance"])
        if clearance is not None:
            dimensions["board_clearance_mm"] = clearance

        standoff_height = extract_labeled_length_mm(prompt, ["standoff height", "post height"])
        if standoff_height is not None:
            dimensions["standoff_height_mm"] = standoff_height

        screw_hole_d = extract_labeled_length_mm(prompt, ["screw hole", "screw hole diameter"])
        if screw_hole_d is not None:
            dimensions["screw_hole_diameter_mm"] = screw_hole_d

        lid_height = extract_labeled_length_mm(prompt, ["lid height"])
        if lid_height is not None:
            dimensions["lid_height_mm"] = lid_height

        ventilation = coerce_bool_feature(prompt, ["ventilation", "vents", "ventilation slots"], ["sealed", "no vents"])
        if ventilation is not None:
            features["ventilation_slots"] = ventilation

        removable_lid = coerce_bool_feature(prompt, ["removable lid", "removeable lid", "with lid"], ["sealed lid", "fixed lid"])
        if removable_lid is not None:
            features["removable_lid"] = removable_lid

        screw_holes = coerce_bool_feature(prompt, ["screw holes", "mounting screws", "screws"])
        if screw_holes is not None:
            features["screw_holes"] = screw_holes

        if "board_length_mm" not in dimensions or "board_width_mm" not in dimensions:
            assumptions.append("Used medium PCB enclosure board dimensions because no explicit board footprint was found.")

    def _parse_snap_fit_box(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        triple = extract_dimension_triple_mm(prompt)
        if triple:
            dimensions["length_mm"], dimensions["width_mm"], dimensions["height_mm"] = triple
        else:
            pair = extract_dimension_pair_mm(prompt)
            if pair:
                dimensions["length_mm"], dimensions["width_mm"] = pair
                assumptions.append("Used the two provided snap-fit box dimensions and kept the default height.")

        floor = extract_labeled_length_mm(prompt, ["floor thickness", "base thickness"])
        if floor is not None:
            dimensions["floor_thickness_mm"] = floor

        lid_height = extract_labeled_length_mm(prompt, ["lid height"])
        if lid_height is not None:
            dimensions["lid_height_mm"] = lid_height

        tab_width = extract_labeled_length_mm(prompt, ["snap tab width", "tab width", "snap tabs"])
        if tab_width is not None:
            dimensions["snap_tab_width_mm"] = tab_width

        tab_height = extract_labeled_length_mm(prompt, ["snap tab height", "tab height"])
        if tab_height is not None:
            dimensions["snap_tab_height_mm"] = tab_height

        tab_thickness = extract_labeled_length_mm(prompt, ["snap tab thickness", "tab thickness"])
        if tab_thickness is not None:
            dimensions["snap_tab_thickness_mm"] = tab_thickness

        relief_gap = extract_labeled_length_mm(prompt, ["relief gap", "tab relief gap", "snap gap"])
        if relief_gap is not None:
            dimensions["snap_tab_relief_gap_mm"] = relief_gap

        hook_depth = extract_labeled_length_mm(prompt, ["hook depth", "snap depth", "latch depth"])
        if hook_depth is not None:
            dimensions["snap_hook_depth_mm"] = hook_depth

        hook_height = extract_labeled_length_mm(prompt, ["hook height", "latch height"])
        if hook_height is not None:
            dimensions["snap_hook_height_mm"] = hook_height

        corner_radius = extract_labeled_length_mm(prompt, ["corner radius"])
        if corner_radius is not None:
            dimensions["corner_radius_mm"] = corner_radius

        tabs_per_side = extract_labeled_integer(prompt, ["tabs per side", "tab count per side"])
        if tabs_per_side is not None:
            dimensions["tab_count_per_side"] = tabs_per_side

        if "length_mm" not in dimensions:
            assumptions.append("Used medium snap-fit box dimensions because no explicit outer size was found.")

    def _parse_bottle_holder(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        self._parse_from_spec(get_model_spec("bottle_holder"), prompt, dimensions, features, print_settings, assumptions, warnings)
        measurements = extract_measurements(prompt)
        if measurements and "bottle_diameter_mm" not in dimensions:
            dimensions["bottle_diameter_mm"] = measurements[0].value_mm
            assumptions.append("Used the first detected measurement as the bottle diameter.")
        if len(measurements) >= 2 and "holder_height_mm" not in dimensions:
            dimensions["holder_height_mm"] = measurements[1].value_mm
            assumptions.append("Used the second detected measurement as the holder height.")

    def _parse_test_tube_rack(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        self._parse_from_spec(get_model_spec("test_tube_rack"), prompt, dimensions, features, print_settings, assumptions, warnings)
        measurements = extract_measurements(prompt)
        if measurements and "tube_diameter_mm" not in dimensions:
            dimensions["tube_diameter_mm"] = measurements[0].value_mm
            assumptions.append("Used the first detected measurement as the tube diameter.")

        tube_count_match = re.search(r"(?P<count>\d+)\s*(?:tube|tubes)\b", prompt, re.IGNORECASE)
        if tube_count_match and "tube_count" not in dimensions:
            dimensions["tube_count"] = int(tube_count_match.group("count"))

        row_count_match = re.search(r"(?P<count>\d+)\s*(?:row|rows)\b", prompt, re.IGNORECASE)
        if row_count_match and "row_count" not in dimensions:
            dimensions["row_count"] = int(row_count_match.group("count"))

    def _parse_gridfinity_bin(
        self,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        normalized = prompt.lower()
        grid_match = re.search(r"(?P<x>\d+)\s*(?:x|by)\s*(?P<y>\d+)\b", normalized)
        if grid_match:
            dimensions["grid_units_x"] = int(grid_match.group("x"))
            dimensions["grid_units_y"] = int(grid_match.group("y"))

        height_match = re.search(r"(?P<h>\d+)\s*(?:unit|units)\s*tall\b", normalized)
        if height_match:
            dimensions["height_units"] = int(height_match.group("h"))
        else:
            labeled_height = extract_labeled_integer(prompt, ["height units"])
            if labeled_height is not None:
                dimensions["height_units"] = labeled_height

        scoop = coerce_bool_feature(prompt, ["scoop front", "scoop"], ["flat front", "no scoop"])
        if scoop is not None:
            features["scoop_front"] = scoop

        magnets = coerce_bool_feature(prompt, ["magnet holes", "magnets"], ["no magnets", "no magnet holes"])
        if magnets is not None:
            features["magnet_holes"] = magnets

        if "grid_units_x" not in dimensions or "grid_units_y" not in dimensions:
            assumptions.append("Used the default Gridfinity footprint because no unit count was found.")

    def _parse_from_spec(
        self,
        spec: ModelSpec,
        prompt: str,
        dimensions: dict[str, Any],
        features: dict[str, Any],
        print_settings: dict[str, Any],
        assumptions: list[str],
        warnings: list[str],
    ) -> None:
        explicit_matches = 0
        mm_defs = [
            definition
            for definition in spec.parameter_definitions
            if definition.type == "number" and definition.unit != "deg" and definition.key not in {"wall_thickness_mm", "tolerance_mm"}
        ]

        triple = extract_dimension_triple_mm(prompt)
        if triple and len(mm_defs) >= 3:
            for definition, value in zip(mm_defs[:3], triple):
                dimensions.setdefault(definition.key, value)
            explicit_matches += min(3, len(mm_defs))
            assumptions.append(f"Interpreted the dimension triple using the primary dimensions for {spec.title}.")

        pair = extract_dimension_pair_mm(prompt)
        if pair and len(mm_defs) >= 2:
            for definition, value in zip(mm_defs[:2], pair):
                dimensions.setdefault(definition.key, value)
            explicit_matches += min(2, len(mm_defs))
            assumptions.append(f"Used the first two provided dimensions for {spec.title}.")

        for definition in spec.parameter_definitions:
            if definition.key in dimensions or definition.key in features or definition.key in print_settings:
                continue

            labels = self._definition_labels(definition)
            value = None
            if definition.type == "boolean":
                negative_labels = [f"no {label}" for label in labels[:2]] + [f"without {label}" for label in labels[:2]]
                value = coerce_bool_feature(prompt, labels, negative_labels)
                if value is not None:
                    features[definition.key] = value
                    explicit_matches += 1
                continue

            if definition.type == "integer":
                value = extract_labeled_integer(prompt, labels)
                if value is not None:
                    dimensions[definition.key] = value
                    explicit_matches += 1
                continue

            if definition.type == "number":
                if definition.unit == "deg":
                    value = extract_angle_degrees(prompt, labels)
                else:
                    value = extract_labeled_length_mm(prompt, labels)
                if value is not None:
                    dimensions[definition.key] = value
                    explicit_matches += 1

        if explicit_matches == 0:
            assumptions.append(f"Used the default {spec.title.lower()} dimensions because the prompt did not provide exact values.")

    @staticmethod
    def _definition_labels(definition) -> list[str]:
        cleaned_key = (
            definition.key.replace("_mm", "")
            .replace("_degrees", "")
            .replace("_diameter", " diameter")
            .replace("_count", " count")
            .replace("_", " ")
            .strip()
        )
        labels = [
            definition.label.lower(),
            cleaned_key,
        ]
        if cleaned_key.endswith(" width"):
            labels.append(cleaned_key.replace(" width", " wide"))
        if cleaned_key.endswith(" height"):
            labels.append(cleaned_key.replace(" height", " tall"))
        return list(dict.fromkeys(label for label in labels if label))
