from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from cadrix_v2.registry import ModelSpec
from cadrix_v2.schemas import ValidationIssue


@dataclass
class ValidationResult:
    parameters: Dict[str, Any]
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def printability_score(self) -> int:
        score = 100 - (len(self.errors) * 25) - (len(self.warnings) * 8)
        return max(0, min(100, score))


def _issue(
    severity: str,
    message: str,
    *,
    field: str | None = None,
    suggestion: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(severity=severity, message=message, field=field, suggestion=suggestion)


def _positive_number(issues: list[ValidationIssue], parameters: Dict[str, Any], key: str, label: str) -> None:
    value = parameters.get(key)
    if value is None:
        return
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        issues.append(_issue("error", f"{label} must be numeric.", field=key))
        return
    if numeric <= 0:
        issues.append(_issue("error", f"{label} must be greater than 0.", field=key))


def validate_parameters(spec: ModelSpec, parameters: Dict[str, Any]) -> ValidationResult:
    normalized = {**parameters}
    issues: list[ValidationIssue] = []

    for definition in spec.parameter_definitions:
        if definition.required and normalized.get(definition.key) is None:
            issues.append(
                _issue(
                    "error",
                    f"{definition.label} is required.",
                    field=definition.key,
                )
            )
        value = normalized.get(definition.key)
        if value is None:
            continue
        if definition.type in {"number", "integer"}:
            _positive_number(issues, normalized, definition.key, definition.label)
            numeric = float(value)
            if definition.minimum is not None and numeric < definition.minimum:
                issues.append(
                    _issue(
                        "error",
                        f"{definition.label} must be at least {definition.minimum}{definition.unit or ''}.",
                        field=definition.key,
                        suggestion=f"Increase {definition.label.lower()} to {definition.minimum}{definition.unit or ''} or more.",
                    )
                )
            if definition.maximum is not None and numeric > definition.maximum:
                issues.append(
                    _issue(
                        "error",
                        f"{definition.label} must be at most {definition.maximum}{definition.unit or ''}.",
                        field=definition.key,
                        suggestion=f"Reduce {definition.label.lower()} to {definition.maximum}{definition.unit or ''} or less.",
                    )
                )

    if spec.model_type == "phone_stand":
        _validate_phone_stand(normalized, issues)
    elif spec.model_type == "box_with_lid":
        _validate_box_with_lid(normalized, issues)
    elif spec.model_type == "wall_hook":
        _validate_wall_hook(normalized, issues)
    elif spec.model_type == "bottle_holder":
        _validate_bottle_holder(normalized, issues)
    elif spec.model_type == "laptop_stand":
        _validate_laptop_stand(normalized, issues)
    elif spec.model_type == "card_holder":
        _validate_card_holder(normalized, issues)
    elif spec.model_type == "remote_holder":
        _validate_remote_holder(normalized, issues)
    elif spec.model_type == "hinge":
        _validate_hinge(normalized, issues)
    elif spec.model_type == "nut_and_bolt_basic":
        _validate_nut_and_bolt_basic(normalized, issues)
    elif spec.model_type == "spacer":
        _validate_spacer(normalized, issues)
    elif spec.model_type == "snap_fit_box":
        _validate_snap_fit_box(normalized, issues)
    elif spec.model_type == "cable_clip":
        _validate_cable_clip(normalized, issues)
    elif spec.model_type == "simple_gear":
        _validate_simple_gear(normalized, issues)
    elif spec.model_type == "pcb_enclosure":
        _validate_pcb_enclosure(normalized, issues)
    elif spec.model_type == "test_tube_rack":
        _validate_test_tube_rack(normalized, issues)
    elif spec.model_type == "sensor_mount":
        _validate_sensor_mount(normalized, issues)
    elif spec.model_type == "ventilation_box":
        _validate_ventilation_box(normalized, issues)
    elif spec.model_type == "stackable_box":
        _validate_stackable_box(normalized, issues)
    elif spec.model_type == "gridfinity_bin":
        _validate_gridfinity_bin(normalized, issues)
    elif spec.model_type == "interlocking_panel":
        _validate_interlocking_panel(normalized, issues)
    elif not spec.implemented:
        issues.append(
            _issue(
                "warning",
                f"{spec.title} is registered in V2, but the geometry generator is still pending.",
                suggestion=spec.todo,
            )
        )

    return ValidationResult(parameters=normalized, issues=issues)


def _validate_phone_stand(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    angle = float(parameters.get("angle_degrees", 68))
    wall = float(parameters.get("wall_thickness_mm", 3))
    base_t = float(parameters.get("base_thickness_mm", 6))
    lip = float(parameters.get("front_lip_mm", 12))
    back_h = float(parameters.get("back_support_height_mm", 110))

    if wall < 1.2:
        issues.append(
            _issue(
                "error",
                "Wall thickness must be at least 1.2mm for reliable FDM printing.",
                field="wall_thickness_mm",
                suggestion="Increase wall thickness to 2.4mm or 3mm for a sturdier stand.",
            )
        )
    if base_t < 4:
        issues.append(
            _issue(
                "warning",
                "A base thinner than 4mm may flex under the device load.",
                field="base_thickness_mm",
                suggestion="Increase base thickness to 5mm or more.",
            )
        )
    if angle > 75:
        issues.append(
            _issue(
                "warning",
                "Support angles above 75 degrees can increase unsupported overhang risk near the back edge.",
                field="angle_degrees",
                suggestion="Reduce the support angle or thicken the back support.",
            )
        )
    if lip >= back_h * 0.4:
        issues.append(
            _issue(
                "warning",
                "A very tall front lip can interfere with the device screen area.",
                field="front_lip_mm",
                suggestion="Reduce the front lip height to around 8-14mm.",
            )
        )
    if parameters.get("cable_slot") and float(parameters.get("cable_slot_width_mm", 14)) < 8:
        issues.append(
            _issue(
                "warning",
                "Cable slots below 8mm may be too small for common charging cables after print shrinkage.",
                field="cable_slot_width_mm",
                suggestion="Increase the cable slot width to 10-14mm.",
            )
        )


def _validate_box_with_lid(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    wall = float(parameters.get("wall_thickness_mm", 3))
    floor = float(parameters.get("floor_thickness_mm", 3))
    tolerance = float(parameters.get("lid_clearance_mm", parameters.get("tolerance_mm", 0.4)))
    length = float(parameters.get("length_mm", 120))
    width = float(parameters.get("width_mm", 80))
    height = float(parameters.get("height_mm", 60))

    if wall < 1.2:
        issues.append(
            _issue(
                "error",
                "Wall thickness must be at least 1.2mm for reliable FDM printing.",
                field="wall_thickness_mm",
                suggestion="Increase wall thickness to 2.4mm or 3mm.",
            )
        )
    if floor < 1.2:
        issues.append(
            _issue(
                "error",
                "Floor thickness must be at least 1.2mm to avoid a fragile base.",
                field="floor_thickness_mm",
                suggestion="Increase floor thickness to 2.4mm or more.",
            )
        )
    if tolerance < 0.25:
        issues.append(
            _issue(
                "warning",
                "Lid clearance below 0.25mm is likely to fuse or fit too tightly on most FDM printers.",
                field="lid_clearance_mm",
                suggestion="Increase lid clearance to 0.35mm to 0.5mm.",
            )
        )
    if min(length, width, height) <= wall * 3:
        issues.append(
            _issue(
                "error",
                "The requested box dimensions leave too little interior space once wall thickness is applied.",
                suggestion="Increase the outer size or reduce wall thickness within safe limits.",
            )
        )


def _validate_wall_hook(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    plate_height = float(parameters.get("plate_height_mm", 70))
    hook_depth = float(parameters.get("hook_depth_mm", 35))
    hook_drop = float(parameters.get("hook_drop_mm", 24))
    hole_diameter = float(parameters.get("screw_hole_diameter_mm", 5))
    hole_spacing = float(parameters.get("screw_hole_spacing_mm", 40))

    if hook_depth <= 12:
        issues.append(_issue("warning", "Very short hook reach limits usable hanging depth.", field="hook_depth_mm", suggestion="Increase hook depth to 20mm or more."))
    if hole_spacing + hole_diameter >= plate_height:
        issues.append(_issue("error", "The screw hole spacing is too large for the plate height.", field="screw_hole_spacing_mm", suggestion="Reduce the screw hole spacing or increase the plate height."))
    if hook_drop >= hook_depth * 1.8:
        issues.append(_issue("warning", "A deep vertical drop can weaken the hook tip on smaller wall hooks.", field="hook_drop_mm", suggestion="Reduce hook drop or increase hook diameter."))


def _validate_bottle_holder(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    bottle_diameter = float(parameters.get("bottle_diameter_mm", 70))
    holder_height = float(parameters.get("holder_height_mm", 90))
    opening = float(parameters.get("front_opening_mm", 28))
    wall = float(parameters.get("wall_thickness_mm", 3))

    if holder_height <= bottle_diameter * 0.35:
        issues.append(_issue("warning", "A very short holder may not retain the bottle securely.", field="holder_height_mm", suggestion="Increase holder height to at least 40% of the bottle diameter."))
    if opening >= bottle_diameter + wall:
        issues.append(_issue("error", "The front opening is too wide and would leave too little material to retain the bottle.", field="front_opening_mm", suggestion="Reduce the opening width or increase the bottle diameter target."))


def _validate_laptop_stand(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    wall = float(parameters.get("wall_thickness_mm", 5))
    width = float(parameters.get("laptop_width_mm", 250))
    cutout = float(parameters.get("center_cutout_width_mm", 110))

    if wall < 2.4:
        issues.append(_issue("warning", "Thin laptop stand walls may flex under load.", field="wall_thickness_mm", suggestion="Increase wall thickness to at least 3mm."))
    if cutout >= width - 20:
        issues.append(_issue("warning", "An oversized center cutout leaves very little side rail material.", field="center_cutout_width_mm", suggestion="Reduce the cutout width or increase the overall stand width."))


def _validate_remote_holder(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    remote_height = float(parameters.get("remote_height_mm", 130))
    front_window = float(parameters.get("front_window_height_mm", 70))

    if front_window >= remote_height:
        issues.append(_issue("warning", "A full-height front cutout reduces how much of the remote body is retained.", field="front_window_height_mm", suggestion="Reduce the front window height to leave more wall above the cutout."))


def _validate_card_holder(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    holder_height = float(parameters.get("holder_height_mm", 45))
    front_lip = float(parameters.get("front_lip_mm", 12))

    if front_lip >= holder_height - 4:
        issues.append(_issue("warning", "A very tall front lip will hide too much of the card face.", field="front_lip_mm", suggestion="Reduce the front lip or increase the holder height."))


def _validate_hinge(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    knuckle_diameter = float(parameters.get("knuckle_diameter_mm", 10))
    pin_diameter = float(parameters.get("pin_diameter_mm", 4.2))
    clearance = float(parameters.get("clearance_mm", 0.4))
    knuckle_count = int(parameters.get("knuckle_count", 5))

    if pin_diameter + (2.0 * clearance) >= knuckle_diameter:
        issues.append(_issue("error", "The hinge pin is too large for the requested knuckle diameter and clearance.", field="pin_diameter_mm", suggestion="Reduce the pin diameter or increase the knuckle diameter."))
    if knuckle_count % 2 == 0:
        issues.append(_issue("warning", "Odd knuckle counts usually produce a more balanced hinge layout.", field="knuckle_count", suggestion="Use 3, 5, or 7 knuckles for a typical hinge."))


def _validate_nut_and_bolt_basic(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    shaft_diameter = float(parameters.get("shaft_diameter_mm", 8))
    head_diameter = float(parameters.get("head_diameter_mm", 14))
    nut_width = float(parameters.get("nut_width_mm", 15))
    fit_clearance = float(parameters.get("fit_clearance_mm", 0.4))

    if head_diameter <= shaft_diameter + 1.0:
        issues.append(_issue("error", "The bolt head diameter must be larger than the shaft diameter.", field="head_diameter_mm", suggestion="Increase the bolt head diameter."))
    if nut_width <= shaft_diameter + (2.0 * fit_clearance):
        issues.append(_issue("error", "The nut width is too small for the requested shaft size and clearance.", field="nut_width_mm", suggestion="Increase the nut width or reduce the shaft diameter."))


def _validate_spacer(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    inner_diameter = float(parameters.get("inner_diameter_mm", 5))
    outer_diameter = float(parameters.get("outer_diameter_mm", 12))

    if outer_diameter <= inner_diameter + 1.0:
        issues.append(_issue("error", "The spacer outer diameter must be larger than the inner diameter.", field="outer_diameter_mm", suggestion="Increase the outer diameter or reduce the inner diameter."))


def _validate_cable_clip(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    cable_d = float(parameters.get("cable_diameter_mm", 6))
    wall = float(parameters.get("wall_thickness_mm", 3))
    gap = float(parameters.get("opening_gap_mm", 1.5))

    if wall < 1.2:
        issues.append(
            _issue(
                "error",
                "Clip wall thickness must be at least 1.2mm for reliable FDM printing.",
                field="wall_thickness_mm",
                suggestion="Increase wall thickness to 2mm or more.",
            )
        )
    if gap < 0.8:
        issues.append(
            _issue(
                "warning",
                "Opening gaps below 0.8mm can print shut or become too stiff to flex open.",
                field="opening_gap_mm",
                suggestion="Increase the opening gap to 1mm or more.",
            )
        )
    if parameters.get("screw_hole") and not parameters.get("mounting_base"):
        issues.append(
            _issue(
                "warning",
                "A screw hole without a mounting base leaves nowhere to place the fastener.",
                field="mounting_base",
                suggestion="Enable the mounting base or disable the screw hole.",
            )
        )
    if parameters.get("screw_hole") and float(parameters.get("screw_hole_diameter_mm", 4.2)) < 3:
        issues.append(
            _issue(
                "warning",
                "Very small screw holes may close up during printing.",
                field="screw_hole_diameter_mm",
                suggestion="Increase the screw hole diameter to at least 3mm.",
            )
        )
    if cable_d < 3 and wall > cable_d:
        issues.append(
            _issue(
                "warning",
                "For tiny cables, a thick clip wall can make the clip unnecessarily bulky.",
                suggestion="Reduce wall thickness slightly or increase the cable diameter target.",
            )
        )


def _validate_snap_fit_box(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    length = float(parameters.get("length_mm", 90))
    width = float(parameters.get("width_mm", 60))
    height = float(parameters.get("height_mm", 35))
    wall = float(parameters.get("wall_thickness_mm", 2.8))
    floor = float(parameters.get("floor_thickness_mm", 3))
    lid_height = float(parameters.get("lid_height_mm", 18))
    lid_clearance = float(parameters.get("lid_clearance_mm", parameters.get("tolerance_mm", 0.4)))
    tab_width = float(parameters.get("snap_tab_width_mm", 14))
    tab_height = float(parameters.get("snap_tab_height_mm", 12))
    tab_thickness = float(parameters.get("snap_tab_thickness_mm", 2.4))
    relief_gap = float(parameters.get("snap_tab_relief_gap_mm", 0.8))
    hook_depth = float(parameters.get("snap_hook_depth_mm", 1.0))
    hook_height = float(parameters.get("snap_hook_height_mm", 2.4))
    tab_count = int(parameters.get("tab_count_per_side", 2))
    covered_depth = lid_height - max(1.8, wall * 0.85)
    tab_projection = relief_gap + tab_thickness + hook_depth
    body_width = width - (2.0 * tab_projection)

    if wall < 1.6:
        issues.append(
            _issue(
                "error",
                "Snap-fit box walls must be at least 1.6mm thick to support cantilever tabs reliably.",
                field="wall_thickness_mm",
                suggestion="Increase wall thickness to 2.4mm to 3mm for more durable snap features.",
            )
        )
    if floor < 1.2:
        issues.append(
            _issue(
                "error",
                "Floor thickness must be at least 1.2mm to avoid a fragile base.",
                field="floor_thickness_mm",
                suggestion="Increase floor thickness to 2.4mm or more.",
            )
        )
    if lid_clearance < 0.25:
        issues.append(
            _issue(
                "warning",
                "Snap-fit lid clearance below 0.25mm is likely to bind after printing.",
                field="lid_clearance_mm",
                suggestion="Increase lid clearance to 0.35mm to 0.5mm.",
            )
        )
    if relief_gap < 0.5:
        issues.append(
            _issue(
                "warning",
                "Relief gaps below 0.5mm can fuse to the wall and stop the tab from flexing.",
                field="snap_tab_relief_gap_mm",
                suggestion="Increase the relief gap to 0.6mm to 1mm.",
            )
        )
    if tab_thickness < 1.8:
        issues.append(
            _issue(
                "warning",
                "Very thin snap tabs can fatigue or break during repeated assembly.",
                field="snap_tab_thickness_mm",
                suggestion="Increase snap tab thickness to around 2.2mm to 2.8mm.",
            )
        )
    if hook_depth > 1.6:
        issues.append(
            _issue(
                "warning",
                "Deep snap hooks increase assembly force and can overstress the cantilever beam.",
                field="snap_hook_depth_mm",
                suggestion="Reduce hook depth to about 0.8mm to 1.4mm.",
            )
        )
    if hook_height >= tab_height * 0.55:
        issues.append(
            _issue(
                "warning",
                "A very tall locking hook leaves less free beam length for the tab to flex.",
                field="snap_hook_height_mm",
                suggestion="Reduce hook height or increase the tab height.",
            )
        )
    if covered_depth <= tab_height + 2.0:
        issues.append(
            _issue(
                "error",
                "The lid is too shallow for the requested snap tab height and mating pocket depth.",
                field="lid_height_mm",
                suggestion="Increase lid height or shorten the snap tab height.",
            )
        )
    if height <= floor + tab_height + 4.0:
        issues.append(
            _issue(
                "error",
                "The box height is too short to fit the requested cantilever snap tabs above the floor.",
                field="height_mm",
                suggestion="Increase the box height or shorten the snap tab height.",
            )
        )
    if body_width <= (2.0 * wall) + 6.0:
        issues.append(
            _issue(
                "error",
                "The requested box width leaves too little room once the snap-tab flex channel is reserved.",
                field="width_mm",
                suggestion="Increase the box width or reduce the tab thickness, relief gap, or hook depth.",
            )
        )
    required_span = (tab_count * tab_width) + ((tab_count + 1) * 8.0)
    if length < required_span:
        issues.append(
            _issue(
                "error",
                "The box length is too short for the requested number of snap tabs and safe edge margins.",
                field="length_mm",
                suggestion="Increase the box length, reduce the tab width, or reduce the tabs per side.",
            )
        )


def _validate_simple_gear(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    teeth = int(parameters.get("tooth_count", 24))
    outer_d = float(parameters.get("outer_diameter_mm", 40))
    thickness = float(parameters.get("thickness_mm", 8))
    bore = float(parameters.get("bore_diameter_mm", 5))
    module = outer_d / max(teeth + 2, 1)

    if teeth < 8:
        issues.append(
            _issue(
                "error",
                "Simple gears need at least 8 teeth to generate a usable profile.",
                field="tooth_count",
                suggestion="Increase the tooth count to 8 or more.",
            )
        )
    if thickness < 2:
        issues.append(
            _issue(
                "error",
                "Gear thickness must be at least 2mm to avoid fragile teeth.",
                field="thickness_mm",
                suggestion="Increase gear thickness to 4mm or more.",
            )
        )
    if bore >= outer_d * 0.6:
        issues.append(
            _issue(
                "error",
                "The center bore is too large relative to the gear diameter.",
                field="bore_diameter_mm",
                suggestion="Reduce the bore diameter or increase the overall gear size.",
            )
        )
    if module < 1.4:
        issues.append(
            _issue(
                "warning",
                "The current tooth size is very fine for FDM printing and may print poorly.",
                suggestion="Increase the outer diameter or reduce the tooth count.",
            )
        )
    if teeth > 60 and outer_d < 80:
        issues.append(
            _issue(
                "warning",
                "High tooth count on a small gear creates tiny teeth that can wear or print badly.",
                suggestion="Reduce the tooth count or increase the diameter.",
            )
        )


def _validate_pcb_enclosure(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    wall = float(parameters.get("wall_thickness_mm", 3))
    floor = float(parameters.get("floor_thickness_mm", 3))
    clearance = float(parameters.get("board_clearance_mm", 1.2))
    standoff_height = float(parameters.get("standoff_height_mm", 6))
    board_thickness = float(parameters.get("board_thickness_mm", 1.6))
    enclosure_height = float(parameters.get("enclosure_height_mm", 25))
    standoff_diameter = float(parameters.get("standoff_diameter_mm", 8))
    hole_d = float(parameters.get("screw_hole_diameter_mm", 3))

    if wall < 1.2:
        issues.append(
            _issue(
                "error",
                "Wall thickness must be at least 1.2mm for reliable FDM printing.",
                field="wall_thickness_mm",
                suggestion="Increase wall thickness to 2.4mm or 3mm.",
            )
        )
    if floor < 1.2:
        issues.append(
            _issue(
                "error",
                "Floor thickness must be at least 1.2mm for reliable FDM printing.",
                field="floor_thickness_mm",
                suggestion="Increase floor thickness to 2.4mm or more.",
            )
        )
    if clearance < 0.8:
        issues.append(
            _issue(
                "warning",
                "Board clearance below 0.8mm may make PCB installation difficult after printing.",
                field="board_clearance_mm",
                suggestion="Increase board clearance to 1mm or more.",
            )
        )
    if enclosure_height <= standoff_height + board_thickness + 4:
        issues.append(
            _issue(
                "warning",
                "The enclosure height is tight once the PCB and standoffs are installed.",
                field="enclosure_height_mm",
                suggestion="Increase the enclosure height by 4-6mm.",
            )
        )
    if parameters.get("screw_holes") and standoff_diameter <= hole_d + 2:
        issues.append(
            _issue(
                "warning",
                "The standoff diameter leaves very little material around the screw hole.",
                field="standoff_diameter_mm",
                suggestion="Increase standoff diameter or reduce the screw hole diameter.",
            )
        )
    if parameters.get("ventilation_slots") and float(parameters.get("lid_height_mm", 10)) < 6:
        issues.append(
            _issue(
                "warning",
                "Very shallow lids leave limited room for clean ventilation slots.",
                field="lid_height_mm",
                suggestion="Increase lid height to 8mm or more.",
            )
        )


def _validate_test_tube_rack(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    tube_count = int(parameters.get("tube_count", 6))
    row_count = int(parameters.get("row_count", 2))
    rack_height = float(parameters.get("rack_height_mm", 55))
    tube_diameter = float(parameters.get("tube_diameter_mm", 16))

    if row_count > tube_count:
        issues.append(_issue("error", "Row count cannot exceed total tube count.", field="row_count", suggestion="Reduce the row count or increase the tube count."))
    if rack_height <= tube_diameter:
        issues.append(_issue("warning", "Rack height close to the tube diameter leaves little vertical guidance.", field="rack_height_mm", suggestion="Increase the rack height for better tube stability."))


def _validate_sensor_mount(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    standoff_diameter = float(parameters.get("standoff_diameter_mm", 8))
    hole_diameter = float(parameters.get("hole_diameter_mm", 3))

    if standoff_diameter <= hole_diameter + 1.2:
        issues.append(_issue("warning", "The standoff diameter leaves very little material around the hole.", field="standoff_diameter_mm", suggestion="Increase standoff diameter or reduce the hole diameter."))


def _validate_ventilation_box(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    width = float(parameters.get("width_mm", 80))
    cable_hole_diameter = float(parameters.get("cable_hole_diameter_mm", 8))

    if cable_hole_diameter >= width * 0.6:
        issues.append(_issue("warning", "A very large cable hole removes a lot of side-wall material.", field="cable_hole_diameter_mm", suggestion="Reduce the cable hole diameter or increase the box width."))


def _validate_stackable_box(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    height = float(parameters.get("height_mm", 60))
    lip_height = float(parameters.get("stack_lip_height_mm", 6))

    if lip_height >= height * 0.5:
        issues.append(_issue("warning", "A very tall stacking lip consumes a lot of the box height.", field="stack_lip_height_mm", suggestion="Reduce the stacking lip height."))


def _validate_gridfinity_bin(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    grid_units_x = int(parameters.get("grid_units_x", 2))
    grid_units_y = int(parameters.get("grid_units_y", 2))
    height_units = int(parameters.get("height_units", 3))

    if min(grid_units_x, grid_units_y, height_units) <= 0:
        issues.append(_issue("error", "Gridfinity bins require positive unit counts.", suggestion="Use grid unit values of 1 or greater."))


def _validate_interlocking_panel(parameters: Dict[str, Any], issues: list[ValidationIssue]) -> None:
    length = float(parameters.get("length_mm", 120))
    tab_depth = float(parameters.get("tab_depth_mm", 8))
    slot_clearance = float(parameters.get("slot_clearance_mm", 0.35))
    tab_width = float(parameters.get("tab_width_mm", 16))

    if length <= (2.0 * tab_depth) + 8.0:
        issues.append(_issue("error", "The panel length is too short for the requested tab depth.", field="length_mm", suggestion="Increase panel length or reduce tab depth."))
    if slot_clearance >= tab_width * 0.4:
        issues.append(_issue("warning", "Very large slot clearance can make the panel fit loose.", field="slot_clearance_mm", suggestion="Reduce slot clearance to around 0.2mm to 0.5mm."))
