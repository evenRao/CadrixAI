from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict

import cadquery as cq


@dataclass
class GeneratedPart:
    label: str
    file_suffix: str
    solid: cq.Workplane


@dataclass
class GeneratedGeometry:
    primary_solid: cq.Workplane
    preview_solid: cq.Workplane
    extra_parts: list[GeneratedPart] = field(default_factory=list)


def normalize_to_build_plate(solid: cq.Workplane) -> cq.Workplane:
    bbox = solid.val().BoundingBox()
    center_x = (bbox.xmin + bbox.xmax) / 2.0
    center_y = (bbox.ymin + bbox.ymax) / 2.0
    return solid.translate((-center_x, -center_y, -bbox.zmin))


def estimate_dimensions_mm(solid: cq.Workplane) -> Dict[str, float]:
    bbox = solid.val().BoundingBox()
    return {
        "x": round(float(bbox.xlen), 2),
        "y": round(float(bbox.ylen), 2),
        "z": round(float(bbox.zlen), 2),
    }


def _safe_fillet(solid: cq.Workplane, radius: float) -> cq.Workplane:
    if radius <= 0:
        return solid
    try:
        return solid.edges("|Z").fillet(radius)
    except Exception:
        return solid


def _open_shell(length_mm: float, width_mm: float, height_mm: float, wall_mm: float, floor_mm: float, corner_radius_mm: float = 0.0) -> cq.Workplane:
    outer = cq.Workplane("XY").box(length_mm, width_mm, height_mm, centered=(True, True, False))
    inner_length = max(length_mm - (2.0 * wall_mm), 2.0)
    inner_width = max(width_mm - (2.0 * wall_mm), 2.0)
    inner_height = max(height_mm - floor_mm, 1.0)
    inner = (
        cq.Workplane("XY")
        .box(inner_length, inner_width, inner_height, centered=(True, True, False))
        .translate((0, 0, floor_mm))
    )
    shell = outer.cut(inner)
    if corner_radius_mm > 0:
        shell = _safe_fillet(shell, min(corner_radius_mm, min(length_mm, width_mm) * 0.12))
    return shell


def generate_phone_stand(parameters: Dict[str, Any]) -> GeneratedGeometry:
    phone_width = float(parameters["phone_width_mm"])
    angle = math.radians(float(parameters["angle_degrees"]))
    device_thickness = float(parameters.get("device_thickness_mm", 12))
    base_thickness = float(parameters.get("base_thickness_mm", 6))
    front_lip = float(parameters.get("front_lip_mm", 12))
    back_height = float(parameters.get("back_support_height_mm", 110))
    side_margin = float(parameters.get("side_margin_mm", 8))
    wall = float(parameters.get("wall_thickness_mm", 3))
    cable_slot = bool(parameters.get("cable_slot", False))
    cable_slot_width = float(parameters.get("cable_slot_width_mm", 14))
    rounded_edges = bool(parameters.get("rounded_edges", True))
    edge_radius = float(parameters.get("edge_radius_mm", 2))

    overall_width = phone_width + (2 * side_margin)
    front_lip_depth = max(device_thickness + 4, 14)
    support_run = back_height / max(math.tan(angle), 0.35)
    base_depth = max(support_run + front_lip_depth + 12, overall_width * 0.55, 75)
    support_front_x = min(max(front_lip_depth + 8, base_depth - support_run), base_depth - wall)

    # The side profile is a stable wedge instead of a thin plate. That keeps the
    # stand printable without support for typical 60-70 degree usage angles.
    profile = (
        cq.Workplane("XZ")
        .polyline(
            [
                (0, 0),
                (base_depth, 0),
                (base_depth, base_thickness + back_height),
                (max(base_depth - wall, support_front_x + wall), base_thickness + back_height),
                (support_front_x, base_thickness),
                (front_lip_depth, base_thickness),
                (front_lip_depth, base_thickness + front_lip),
                (0, base_thickness + front_lip),
            ]
        )
        .close()
        .extrude(overall_width, both=True)
    )

    seat_cut = (
        cq.Workplane("XY")
        .box(overall_width * 0.9, device_thickness + 6, front_lip + base_thickness + 8, centered=(True, True, False))
        .translate((0, 0, base_thickness))
    )
    body = profile.cut(seat_cut)

    if cable_slot:
        slot = (
            cq.Workplane("XY")
            .box(cable_slot_width, max(device_thickness + 6, 12), base_thickness + 2, centered=(True, True, False))
            .translate((0, -overall_width * 0.15, 0))
        )
        body = body.cut(slot)

    if rounded_edges:
        try:
            body = body.edges("|Y").fillet(min(edge_radius, 2.5))
        except Exception:
            pass

    body = normalize_to_build_plate(body)
    return GeneratedGeometry(primary_solid=body, preview_solid=body)


def generate_box_with_lid(parameters: Dict[str, Any]) -> GeneratedGeometry:
    length_mm = float(parameters["length_mm"])
    width_mm = float(parameters["width_mm"])
    height_mm = float(parameters["height_mm"])
    wall_mm = float(parameters.get("wall_thickness_mm", 3))
    floor_mm = float(parameters.get("floor_thickness_mm", 3))
    lid_height_mm = float(parameters.get("lid_height_mm", 18))
    lid_clearance_mm = float(parameters.get("lid_clearance_mm", parameters.get("tolerance_mm", 0.4)))
    rounded_edges = bool(parameters.get("rounded_edges", True))
    corner_radius_mm = float(parameters.get("corner_radius_mm", 2))
    snap_fit_lip = bool(parameters.get("snap_fit_lip", False))

    base = _open_shell(length_mm, width_mm, height_mm, wall_mm, floor_mm, corner_radius_mm if rounded_edges else 0.0)

    lid_wall_mm = max(wall_mm * 0.9, 2.0)
    top_thickness_mm = max(1.6, wall_mm * 0.8)
    cavity_length = length_mm + (2 * lid_clearance_mm)
    cavity_width = width_mm + (2 * lid_clearance_mm)
    lid_outer_length = cavity_length + (2 * lid_wall_mm)
    lid_outer_width = cavity_width + (2 * lid_wall_mm)

    lid_outer = cq.Workplane("XY").box(lid_outer_length, lid_outer_width, lid_height_mm, centered=(True, True, False))
    lid_cavity = (
        cq.Workplane("XY")
        .box(cavity_length, cavity_width, max(lid_height_mm - top_thickness_mm, 1.0), centered=(True, True, False))
        .translate((0, 0, top_thickness_mm))
    )
    lid = lid_outer.cut(lid_cavity)

    if snap_fit_lip:
        lip_height = min(max(wall_mm, 1.2), lid_height_mm * 0.35)
        lip_length = max(length_mm - (2 * lid_clearance_mm), 6)
        lip_width = max(width_mm - (2 * lid_clearance_mm), 6)
        lip_outer = cq.Workplane("XY").box(cavity_length, cavity_width, lip_height, centered=(True, True, False))
        lip_inner = cq.Workplane("XY").box(lip_length, lip_width, lip_height, centered=(True, True, False))
        lid = lid.union(lip_outer.cut(lip_inner).translate((0, 0, lid_height_mm - lip_height)))

    if rounded_edges:
        lid = _safe_fillet(lid, min(corner_radius_mm, min(lid_outer_length, lid_outer_width) * 0.12))

    base = normalize_to_build_plate(base)
    lid = normalize_to_build_plate(lid)

    preview_gap = 8.0
    preview_lid = lid.translate((0, 0, height_mm + preview_gap))
    preview = normalize_to_build_plate(base.union(preview_lid))

    return GeneratedGeometry(
        primary_solid=base,
        preview_solid=preview,
        extra_parts=[GeneratedPart(label="Lid", file_suffix="lid", solid=lid)],
    )


def _distributed_positions(span_mm: float, count: int, edge_margin_mm: float) -> list[float]:
    if count <= 1:
        return [0.0]
    usable_span = max(span_mm - (2.0 * edge_margin_mm), 0.0)
    if usable_span <= 0:
        return [0.0 for _ in range(count)]
    start = -usable_span / 2.0
    step = usable_span / (count - 1)
    return [start + (step * index) for index in range(count)]


def _long_side_snap_tab(
    x_center: float,
    outer_width: float,
    root_z: float,
    tab_width: float,
    tab_height: float,
    tab_thickness: float,
    relief_gap: float,
    hook_depth: float,
    hook_height: float,
    positive_side: bool,
) -> cq.Workplane:
    anchor_depth = relief_gap + tab_thickness
    anchor_height = max(2.0, min(tab_height * 0.28, tab_height - 1.0))
    hook_width = max(tab_width * 0.72, tab_width - 4.0)
    hook_z = root_z + max(tab_height - hook_height - 0.6, anchor_height)

    if positive_side:
        beam_y = (outer_width / 2.0) + relief_gap
        anchor_y = outer_width / 2.0
        hook_y = beam_y + tab_thickness
    else:
        beam_y = (-outer_width / 2.0) - relief_gap - tab_thickness
        anchor_y = (-outer_width / 2.0) - anchor_depth
        hook_y = beam_y - hook_depth

    beam = (
        cq.Workplane("XY")
        .box(tab_width, tab_thickness, tab_height, centered=(True, False, False))
        .translate((x_center, beam_y, root_z))
    )
    anchor = (
        cq.Workplane("XY")
        .box(tab_width, anchor_depth, anchor_height, centered=(True, False, False))
        .translate((x_center, anchor_y, root_z))
    )
    hook = (
        cq.Workplane("XY")
        .box(hook_width, hook_depth, hook_height, centered=(True, False, False))
        .translate((x_center, hook_y, hook_z))
    )
    return anchor.union(beam).union(hook)


def generate_snap_fit_box(parameters: Dict[str, Any]) -> GeneratedGeometry:
    length_mm = float(parameters["length_mm"])
    width_mm = float(parameters["width_mm"])
    height_mm = float(parameters["height_mm"])
    wall_mm = float(parameters.get("wall_thickness_mm", 2.8))
    floor_mm = float(parameters.get("floor_thickness_mm", 3))
    lid_height_mm = float(parameters.get("lid_height_mm", 18))
    lid_clearance_mm = float(parameters.get("lid_clearance_mm", parameters.get("tolerance_mm", 0.4)))
    tab_width_mm = float(parameters.get("snap_tab_width_mm", 14))
    tab_height_mm = float(parameters.get("snap_tab_height_mm", 12))
    tab_thickness_mm = float(parameters.get("snap_tab_thickness_mm", 2.4))
    relief_gap_mm = float(parameters.get("snap_tab_relief_gap_mm", 0.8))
    hook_depth_mm = float(parameters.get("snap_hook_depth_mm", 1.0))
    hook_height_mm = float(parameters.get("snap_hook_height_mm", 2.4))
    tab_count = int(parameters.get("tab_count_per_side", 2))
    rounded_edges = bool(parameters.get("rounded_edges", True))
    corner_radius_mm = float(parameters.get("corner_radius_mm", 1.5))
    tab_projection_mm = relief_gap_mm + tab_thickness_mm + hook_depth_mm
    body_outer_width_mm = max(width_mm - (2.0 * tab_projection_mm), (2.0 * wall_mm) + 8.0)

    base = _open_shell(length_mm, body_outer_width_mm, height_mm, wall_mm, floor_mm, corner_radius_mm if rounded_edges else 0.0)

    top_thickness_mm = max(1.8, wall_mm * 0.85)
    covered_depth_mm = lid_height_mm - top_thickness_mm
    root_z = max(floor_mm + 2.0, height_mm - covered_depth_mm + 1.5)
    root_z = min(root_z, height_mm - tab_height_mm - 1.5)
    positions = _distributed_positions(length_mm, tab_count, max((tab_width_mm / 2.0) + 6.0, wall_mm * 2.0 + 4.0))

    for x_center in positions:
        base = base.union(
            _long_side_snap_tab(
                x_center,
                body_outer_width_mm,
                root_z,
                tab_width_mm,
                tab_height_mm,
                tab_thickness_mm,
                relief_gap_mm,
                hook_depth_mm,
                hook_height_mm,
                positive_side=True,
            )
        )
        base = base.union(
            _long_side_snap_tab(
                x_center,
                body_outer_width_mm,
                root_z,
                tab_width_mm,
                tab_height_mm,
                tab_thickness_mm,
                relief_gap_mm,
                hook_depth_mm,
                hook_height_mm,
                positive_side=False,
            )
        )

    pocket_clearance_mm = max(0.25, min(lid_clearance_mm + 0.1, 0.8))
    pocket_depth_mm = max((relief_gap_mm - lid_clearance_mm) + tab_thickness_mm + hook_depth_mm + pocket_clearance_mm, tab_thickness_mm + hook_depth_mm + 0.6)
    outer_skin_mm = max(1.2, wall_mm * 0.45)
    lid_wall_mm = max(wall_mm * 1.15, pocket_depth_mm + outer_skin_mm)

    cavity_length_mm = length_mm + (2.0 * lid_clearance_mm)
    cavity_width_mm = body_outer_width_mm + (2.0 * lid_clearance_mm)
    lid_outer_length_mm = cavity_length_mm + (2.0 * lid_wall_mm)
    lid_outer_width_mm = cavity_width_mm + (2.0 * lid_wall_mm)

    lid_outer = cq.Workplane("XY").box(lid_outer_length_mm, lid_outer_width_mm, lid_height_mm, centered=(True, True, False))
    lid_cavity = (
        cq.Workplane("XY")
        .box(cavity_length_mm, cavity_width_mm, max(lid_height_mm - top_thickness_mm, 1.0), centered=(True, True, False))
        .translate((0, 0, top_thickness_mm))
    )
    lid = lid_outer.cut(lid_cavity)

    hook_z = root_z + max(tab_height_mm - hook_height_mm - 0.6, max(2.0, min(tab_height_mm * 0.28, tab_height_mm - 1.0)))
    pocket_width_mm = tab_width_mm + (2.0 * pocket_clearance_mm)
    pocket_height_mm = hook_height_mm + (2.0 * pocket_clearance_mm)
    pocket_z_mm = hook_z - (height_mm - covered_depth_mm) - pocket_clearance_mm
    pocket_z_mm = max(1.0, min(pocket_z_mm, covered_depth_mm - pocket_height_mm - 0.8))
    lead_in_height_mm = min(max(hook_height_mm * 0.8, 1.0), 2.0)

    for x_center in positions:
        for positive_side in (True, False):
            if positive_side:
                pocket_y = cavity_width_mm / 2.0
            else:
                pocket_y = (-cavity_width_mm / 2.0) - pocket_depth_mm

            pocket = (
                cq.Workplane("XY")
                .box(pocket_width_mm, pocket_depth_mm, pocket_height_mm, centered=(True, False, False))
                .translate((x_center, pocket_y, pocket_z_mm))
            )
            lead_in = (
                cq.Workplane("XY")
                .box(pocket_width_mm, max(pocket_depth_mm - outer_skin_mm, hook_depth_mm), lead_in_height_mm, centered=(True, False, False))
                .translate((x_center, pocket_y, max(pocket_z_mm - lead_in_height_mm, 0.8)))
            )
            lid = lid.cut(pocket).cut(lead_in)

    if rounded_edges:
        lid = _safe_fillet(lid, min(corner_radius_mm, min(lid_outer_length_mm, lid_outer_width_mm) * 0.08))

    base = normalize_to_build_plate(base)
    lid = normalize_to_build_plate(lid)
    preview = normalize_to_build_plate(base.union(lid.translate((0, 0, height_mm + 10.0))))

    return GeneratedGeometry(
        primary_solid=base,
        preview_solid=preview,
        extra_parts=[GeneratedPart(label="Lid", file_suffix="lid", solid=lid)],
    )


def generate_cable_clip(parameters: Dict[str, Any]) -> GeneratedGeometry:
    cable_d = float(parameters["cable_diameter_mm"])
    clip_width = float(parameters.get("clip_width_mm", 12))
    wall = float(parameters.get("wall_thickness_mm", 3))
    gap = float(parameters.get("opening_gap_mm", 1.5))
    mounting_base = bool(parameters.get("mounting_base", False))
    screw_hole = bool(parameters.get("screw_hole", False))
    base_length = float(parameters.get("base_length_mm", 24))
    base_thickness = float(parameters.get("base_thickness_mm", 3))
    screw_hole_d = float(parameters.get("screw_hole_diameter_mm", 4.2))

    outer_r = (cable_d / 2.0) + wall
    inner_r = (cable_d / 2.0) + float(parameters.get("tolerance_mm", 0.35))

    clip = cq.Workplane("XZ").circle(outer_r).extrude(clip_width, both=True)
    inner = cq.Workplane("XZ").circle(inner_r).extrude(clip_width + 1, both=True)
    clip = clip.cut(inner)

    opening = (
        cq.Workplane("XY")
        .box(outer_r * 1.5, clip_width + 2, outer_r * 2.2, centered=(True, True, True))
        .translate((outer_r + (gap / 2.0), 0, outer_r * 0.25))
    )
    clip = clip.cut(opening)

    if mounting_base:
        base = (
            cq.Workplane("XY")
            .box(max(base_length, outer_r * 2.0), clip_width, base_thickness, centered=(True, True, False))
            .translate((0, 0, 0))
        )
        clip = clip.translate((0, 0, base_thickness + outer_r))
        clip = base.union(clip)
        if screw_hole:
            clip = clip.faces("<Z").workplane(origin=(0, 0, base_thickness)).hole(screw_hole_d)

    clip = normalize_to_build_plate(clip)
    return GeneratedGeometry(primary_solid=clip, preview_solid=clip)


def generate_simple_gear(parameters: Dict[str, Any]) -> GeneratedGeometry:
    tooth_count = int(parameters["tooth_count"])
    outer_diameter = float(parameters.get("outer_diameter_mm", 40))
    thickness = float(parameters.get("thickness_mm", 8))
    bore_diameter = float(parameters.get("bore_diameter_mm", 5))
    hub_diameter = float(parameters.get("hub_diameter_mm", 14))
    hub_thickness = float(parameters.get("hub_thickness_mm", thickness))

    outer_radius = outer_diameter / 2.0
    module = outer_diameter / max(tooth_count + 2, 1)
    tooth_depth = max(module * 1.25, 1.0)
    root_radius = max(outer_radius - tooth_depth, (bore_diameter / 2.0) + 1.2)
    tooth_angle = (2.0 * math.pi) / tooth_count

    points: list[tuple[float, float]] = []
    for index in range(tooth_count):
        base_angle = index * tooth_angle
        points.extend(
            [
                _polar(root_radius, base_angle - tooth_angle * 0.5),
                _polar(outer_radius, base_angle - tooth_angle * 0.18),
                _polar(outer_radius, base_angle + tooth_angle * 0.18),
                _polar(root_radius, base_angle + tooth_angle * 0.5),
            ]
        )

    profile_points = _dedupe_profile_points(points)
    gear = cq.Workplane("XY").polyline(profile_points).close().extrude(thickness)
    gear = gear.cut(cq.Workplane("XY").circle(bore_diameter / 2.0).extrude(thickness + 1.0))

    if hub_diameter > bore_diameter + 2 and hub_thickness > thickness:
        hub = cq.Workplane("XY").circle(hub_diameter / 2.0).extrude(hub_thickness)
        hub = hub.cut(cq.Workplane("XY").circle(bore_diameter / 2.0).extrude(hub_thickness + 1.0))
        gear = gear.union(hub)

    gear = normalize_to_build_plate(gear)
    return GeneratedGeometry(primary_solid=gear, preview_solid=gear)


def _polar(radius: float, angle_radians: float) -> tuple[float, float]:
    return (radius * math.cos(angle_radians), radius * math.sin(angle_radians))


def _dedupe_profile_points(points: list[tuple[float, float]], tolerance: float = 1e-6) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    for point in points:
        if not deduped:
            deduped.append(point)
            continue
        prev = deduped[-1]
        if abs(prev[0] - point[0]) <= tolerance and abs(prev[1] - point[1]) <= tolerance:
            continue
        deduped.append(point)
    if len(deduped) > 1:
        first = deduped[0]
        last = deduped[-1]
        if abs(first[0] - last[0]) <= tolerance and abs(first[1] - last[1]) <= tolerance:
            deduped.pop()
    return deduped


def generate_pcb_enclosure(parameters: Dict[str, Any]) -> GeneratedGeometry:
    board_length = float(parameters["board_length_mm"])
    board_width = float(parameters["board_width_mm"])
    board_thickness = float(parameters.get("board_thickness_mm", 1.6))
    wall = float(parameters.get("wall_thickness_mm", 3))
    floor = float(parameters.get("floor_thickness_mm", 3))
    enclosure_height = float(parameters.get("enclosure_height_mm", 25))
    board_clearance = float(parameters.get("board_clearance_mm", 1.2))
    standoff_height = float(parameters.get("standoff_height_mm", 6))
    standoff_diameter = float(parameters.get("standoff_diameter_mm", 8))
    screw_holes = bool(parameters.get("screw_holes", True))
    screw_hole_diameter = float(parameters.get("screw_hole_diameter_mm", 3))
    ventilation_slots = bool(parameters.get("ventilation_slots", True))
    removable_lid = bool(parameters.get("removable_lid", True))
    lid_height = float(parameters.get("lid_height_mm", 10))
    tolerance = float(parameters.get("tolerance_mm", 0.4))

    inner_length = board_length + (2 * board_clearance)
    inner_width = board_width + (2 * board_clearance)
    base_outer_length = inner_length + (2 * wall)
    base_outer_width = inner_width + (2 * wall)
    base_outer_height = enclosure_height + floor

    base = _open_shell(base_outer_length, base_outer_width, base_outer_height, wall, floor, 2.0)

    post_offset_x = max((board_length / 2.0) - 5.0, 4.0)
    post_offset_y = max((board_width / 2.0) - 5.0, 4.0)
    post_positions = [
        (-post_offset_x, -post_offset_y),
        (post_offset_x, -post_offset_y),
        (-post_offset_x, post_offset_y),
        (post_offset_x, post_offset_y),
    ]
    for x_pos, y_pos in post_positions:
        post = (
            cq.Workplane("XY")
            .circle(standoff_diameter / 2.0)
            .extrude(standoff_height)
            .translate((x_pos, y_pos, floor))
        )
        if screw_holes:
            post = post.cut(
                cq.Workplane("XY")
                .circle(screw_hole_diameter / 2.0)
                .extrude(standoff_height + 0.5)
                .translate((x_pos, y_pos, floor))
            )
        base = base.union(post)

    lid_extra_parts: list[GeneratedPart] = []
    preview = base
    if removable_lid:
        lid_wall = max(wall * 0.9, 2.0)
        lid_outer_length = base_outer_length + (2 * (tolerance + lid_wall))
        lid_outer_width = base_outer_width + (2 * (tolerance + lid_wall))
        lid = cq.Workplane("XY").box(lid_outer_length, lid_outer_width, lid_height, centered=(True, True, False))
        lid_cavity = (
            cq.Workplane("XY")
            .box(base_outer_length + (2 * tolerance), base_outer_width + (2 * tolerance), max(lid_height - wall, 1.0), centered=(True, True, False))
            .translate((0, 0, wall))
        )
        lid = lid.cut(lid_cavity)

        if ventilation_slots:
            slot_count = 5
            slot_length = lid_outer_length * 0.6
            slot_width = 2.5
            slot_spacing = 6.5
            slots = [
                (0, (index - ((slot_count - 1) / 2.0)) * slot_spacing)
                for index in range(slot_count)
            ]
            lid = lid.faces(">Z").workplane().pushPoints(slots).rect(slot_length, slot_width).cutBlind(-wall * 0.8)

        lid = normalize_to_build_plate(lid)
        lid_extra_parts.append(GeneratedPart(label="Lid", file_suffix="lid", solid=lid))
        preview = normalize_to_build_plate(base.union(lid.translate((0, 0, base_outer_height + 10.0))))
    else:
        preview = normalize_to_build_plate(preview)

    base = normalize_to_build_plate(base)
    return GeneratedGeometry(primary_solid=base, preview_solid=preview, extra_parts=lid_extra_parts)


def _hex_prism(size_mm: float, height_mm: float) -> cq.Workplane:
    return cq.Workplane("XY").polygon(6, size_mm).extrude(height_mm)


def generate_wall_hook(parameters: Dict[str, Any]) -> GeneratedGeometry:
    plate_width = float(parameters.get("plate_width_mm", 50))
    plate_height = float(parameters.get("plate_height_mm", 70))
    hook_depth = float(parameters.get("hook_depth_mm", 35))
    plate_thickness = float(parameters.get("plate_thickness_mm", 6))
    hook_diameter = float(parameters.get("hook_diameter_mm", 10))
    hook_drop = float(parameters.get("hook_drop_mm", 24))
    hole_diameter = float(parameters.get("screw_hole_diameter_mm", 5))
    hole_spacing = float(parameters.get("screw_hole_spacing_mm", 40))

    plate = cq.Workplane("XY").box(plate_width, plate_height, plate_thickness, centered=(True, True, False))
    if hole_diameter > 0 and hole_spacing > 0:
        plate = plate.faces(">Z").workplane().pushPoints([(0, -hole_spacing / 2.0), (0, hole_spacing / 2.0)]).hole(hole_diameter)

    path = (
        cq.Workplane("XZ")
        .polyline(
            [
                (plate_width / 2.0, plate_thickness * 0.55),
                (plate_width / 2.0 + hook_depth * 0.75, plate_thickness * 0.55),
                (plate_width / 2.0 + hook_depth, max((plate_thickness * 0.55) - hook_drop, hook_diameter * 0.55)),
            ]
        )
        .wire()
    )
    arm = cq.Workplane("YZ").circle(hook_diameter / 2.0).sweep(path)
    hook = normalize_to_build_plate(plate.union(arm))
    return GeneratedGeometry(primary_solid=hook, preview_solid=hook)


def generate_drawer_divider(parameters: Dict[str, Any]) -> GeneratedGeometry:
    length_mm = float(parameters.get("length_mm", 150))
    height_mm = float(parameters.get("height_mm", 40))
    thickness_mm = float(parameters.get("thickness_mm", 3))
    base_width_mm = float(parameters.get("base_width_mm", 24))
    foot_height_mm = float(parameters.get("foot_height_mm", 5))

    foot = cq.Workplane("XY").box(length_mm, base_width_mm, foot_height_mm, centered=(True, True, False))
    wall = (
        cq.Workplane("XY")
        .box(length_mm, thickness_mm, height_mm, centered=(True, True, False))
        .translate((0, 0, foot_height_mm))
    )
    divider = normalize_to_build_plate(foot.union(wall))
    return GeneratedGeometry(primary_solid=divider, preview_solid=divider)


def generate_bottle_holder(parameters: Dict[str, Any]) -> GeneratedGeometry:
    bottle_diameter = float(parameters.get("bottle_diameter_mm", 70))
    holder_height = float(parameters.get("holder_height_mm", 90))
    wall = float(parameters.get("wall_thickness_mm", 3))
    floor = float(parameters.get("floor_thickness_mm", 3))
    opening = float(parameters.get("front_opening_mm", 28))
    tolerance = float(parameters.get("tolerance_mm", 0.4))
    mounting_plate = bool(parameters.get("mounting_plate", True))
    plate_width = float(parameters.get("plate_width_mm", 42))
    plate_height = float(parameters.get("plate_height_mm", 90))
    screw_hole_diameter = float(parameters.get("screw_hole_diameter_mm", 5))

    outer_radius = (bottle_diameter / 2.0) + wall + tolerance
    inner_radius = (bottle_diameter / 2.0) + tolerance

    holder = cq.Workplane("XY").circle(outer_radius).extrude(holder_height)
    cavity = cq.Workplane("XY").circle(inner_radius).extrude(max(holder_height - floor, 1.0)).translate((0, 0, floor))
    holder = holder.cut(cavity)

    opening_cut = (
        cq.Workplane("XY")
        .box(max(opening, 6), (outer_radius * 2.0) + 4.0, holder_height + 1.0, centered=(True, True, False))
        .translate((0, outer_radius + 1.0, 0))
    )
    holder = holder.cut(opening_cut)

    if mounting_plate:
        plate = (
            cq.Workplane("XY")
            .box(plate_width, wall, plate_height, centered=(True, True, False))
            .translate((0, -outer_radius - (wall / 2.0), 0))
        )
        if screw_hole_diameter > 0:
            for z_pos in (plate_height * 0.28, plate_height * 0.72):
                plate = plate.cut(
                    cq.Workplane("XZ")
                    .circle(screw_hole_diameter / 2.0)
                    .extrude(wall + 2.0)
                    .translate((0, -outer_radius - wall - 1.0, z_pos))
                )
        holder = holder.union(plate)

    holder = normalize_to_build_plate(holder)
    return GeneratedGeometry(primary_solid=holder, preview_solid=holder)


def generate_desk_organizer(parameters: Dict[str, Any]) -> GeneratedGeometry:
    length_mm = float(parameters.get("length_mm", 160))
    width_mm = float(parameters.get("width_mm", 100))
    height_mm = float(parameters.get("height_mm", 90))
    wall = float(parameters.get("wall_thickness_mm", 3))
    floor = float(parameters.get("floor_thickness_mm", 3))
    compartment_count = int(parameters.get("compartment_count", 3))
    divider_thickness = float(parameters.get("divider_thickness_mm", 3))

    organizer = _open_shell(length_mm, width_mm, height_mm, wall, floor, 2.0)
    inner_width = max(width_mm - (2.0 * wall), 6.0)
    inner_height = max(height_mm - floor, 4.0)
    inner_length = max(length_mm - (2.0 * wall), 6.0)

    if compartment_count > 1:
        step = inner_length / compartment_count
        positions = [
            (-inner_length / 2.0) + (step * index)
            for index in range(1, compartment_count)
        ]
        for x_pos in positions:
            divider = (
                cq.Workplane("XY")
                .box(divider_thickness, inner_width, inner_height, centered=(True, True, False))
                .translate((x_pos, 0, floor))
            )
            organizer = organizer.union(divider)

    organizer = normalize_to_build_plate(organizer)
    return GeneratedGeometry(primary_solid=organizer, preview_solid=organizer)


def generate_laptop_stand(parameters: Dict[str, Any]) -> GeneratedGeometry:
    width_mm = float(parameters.get("laptop_width_mm", 250))
    depth_mm = float(parameters.get("stand_depth_mm", 240))
    angle_degrees = float(parameters.get("angle_degrees", 16))
    wall = float(parameters.get("wall_thickness_mm", 5))
    front_lip = float(parameters.get("front_lip_mm", 12))
    cutout_width = float(parameters.get("center_cutout_width_mm", 110))

    rise_mm = max(math.tan(math.radians(angle_degrees)) * depth_mm, front_lip + wall + 10.0)
    profile = (
        cq.Workplane("XZ")
        .polyline(
            [
                (0, 0),
                (depth_mm, 0),
                (depth_mm, rise_mm + wall),
                (0, wall),
            ]
        )
        .close()
        .extrude(width_mm, both=True)
    )

    cutout = (
        cq.Workplane("XY")
        .box(depth_mm * 0.58, min(cutout_width, width_mm - 30.0), max(rise_mm, 20.0), centered=(True, True, False))
        .translate((depth_mm * 0.45, 0, wall))
    )
    stand = profile.cut(cutout)

    lip = (
        cq.Workplane("XY")
        .box(max(wall * 1.8, 8.0), width_mm, front_lip, centered=(True, True, False))
        .translate((wall * 0.9, 0, wall))
    )
    stand = normalize_to_build_plate(stand.union(lip))
    return GeneratedGeometry(primary_solid=stand, preview_solid=stand)


def generate_remote_holder(parameters: Dict[str, Any]) -> GeneratedGeometry:
    remote_width = float(parameters.get("remote_width_mm", 50))
    remote_depth = float(parameters.get("remote_depth_mm", 28))
    remote_height = float(parameters.get("remote_height_mm", 130))
    wall = float(parameters.get("wall_thickness_mm", 3))
    floor = float(parameters.get("floor_thickness_mm", 3))
    tolerance = float(parameters.get("tolerance_mm", 0.4))
    front_window_height = float(parameters.get("front_window_height_mm", 70))
    mounting_holes = bool(parameters.get("mounting_holes", False))
    screw_hole_diameter = float(parameters.get("screw_hole_diameter_mm", 4.2))

    outer_width = remote_width + (2.0 * (wall + tolerance))
    outer_depth = remote_depth + (2.0 * (wall + tolerance))
    outer_height = remote_height + floor + tolerance

    holder = _open_shell(outer_width, outer_depth, outer_height, wall, floor, 1.5)
    window_height = min(front_window_height, outer_height - floor - 4.0)
    front_cut = (
        cq.Workplane("XY")
        .box(max(outer_width - (2.0 * wall), 6.0), wall + 2.0, window_height, centered=(True, True, False))
        .translate((0, (outer_depth / 2.0) - (wall / 2.0), floor))
    )
    holder = holder.cut(front_cut)

    if mounting_holes and screw_hole_diameter > 0:
        hole_positions = [
            (-outer_width * 0.2, outer_height * 0.35),
            (outer_width * 0.2, outer_height * 0.7),
        ]
        for x_pos, z_pos in hole_positions:
            holder = holder.cut(
                cq.Workplane("XZ")
                .circle(screw_hole_diameter / 2.0)
                .extrude(wall + 2.0)
                .translate((x_pos, (-outer_depth / 2.0) - 1.0, z_pos))
            )

    holder = normalize_to_build_plate(holder)
    return GeneratedGeometry(primary_solid=holder, preview_solid=holder)


def generate_card_holder(parameters: Dict[str, Any]) -> GeneratedGeometry:
    card_width = float(parameters.get("card_width_mm", 92))
    stack_depth = float(parameters.get("stack_depth_mm", 20))
    holder_height = float(parameters.get("holder_height_mm", 45))
    wall = float(parameters.get("wall_thickness_mm", 2.4))
    floor = float(parameters.get("floor_thickness_mm", 2.4))
    front_lip = float(parameters.get("front_lip_mm", 12))
    tolerance = float(parameters.get("tolerance_mm", 0.3))

    outer_width = card_width + (2.0 * (wall + tolerance))
    outer_depth = stack_depth + (2.0 * wall) + tolerance
    holder = _open_shell(outer_width, outer_depth, holder_height, wall, floor, 1.2)
    front_cut = (
        cq.Workplane("XY")
        .box(max(outer_width - (2.0 * wall), 6.0), wall + 2.0, max(holder_height - front_lip, 4.0), centered=(True, True, False))
        .translate((0, (outer_depth / 2.0) - (wall / 2.0), floor + front_lip))
    )
    holder = normalize_to_build_plate(holder.cut(front_cut))
    return GeneratedGeometry(primary_solid=holder, preview_solid=holder)


def generate_hinge(parameters: Dict[str, Any]) -> GeneratedGeometry:
    length_mm = float(parameters.get("length_mm", 60))
    leaf_width_mm = float(parameters.get("leaf_width_mm", 20))
    leaf_thickness_mm = float(parameters.get("leaf_thickness_mm", 3))
    knuckle_diameter_mm = float(parameters.get("knuckle_diameter_mm", 10))
    pin_diameter_mm = float(parameters.get("pin_diameter_mm", 4.2))
    knuckle_count = int(parameters.get("knuckle_count", 5))
    clearance_mm = float(parameters.get("clearance_mm", 0.4))

    leaf_a = (
        cq.Workplane("XY")
        .box(length_mm, leaf_width_mm, leaf_thickness_mm, centered=(True, False, False))
        .translate((0, -leaf_width_mm, 0))
    )
    leaf_b = cq.Workplane("XY").box(length_mm, leaf_width_mm, leaf_thickness_mm, centered=(True, False, False))

    barrel_radius = knuckle_diameter_mm / 2.0
    segment_gap = max(clearance_mm, 0.2)
    segment_length = max((length_mm - (segment_gap * (knuckle_count - 1))) / knuckle_count, leaf_thickness_mm * 1.2)
    barrel_z = max(barrel_radius, leaf_thickness_mm / 2.0)

    for index in range(knuckle_count):
        x_start = (-length_mm / 2.0) + index * (segment_length + segment_gap)
        barrel = (
            cq.Workplane("YZ")
            .circle(barrel_radius)
            .extrude(segment_length)
            .translate((x_start, 0, barrel_z))
        )
        if index % 2 == 0:
            leaf_a = leaf_a.union(barrel)
        else:
            leaf_b = leaf_b.union(barrel)

    hole_radius = (pin_diameter_mm + clearance_mm) / 2.0
    pin_channel = cq.Workplane("YZ").circle(hole_radius).extrude(length_mm + 2.0).translate(((-length_mm / 2.0) - 1.0, 0, barrel_z))
    leaf_a = leaf_a.cut(pin_channel)
    leaf_b = leaf_b.cut(pin_channel)
    pin = cq.Workplane("YZ").circle(pin_diameter_mm / 2.0).extrude(length_mm).translate((-length_mm / 2.0, 0, barrel_z))

    assembly = normalize_to_build_plate(leaf_a.union(leaf_b).union(pin))
    return GeneratedGeometry(
        primary_solid=assembly,
        preview_solid=assembly,
        extra_parts=[
            GeneratedPart(label="Leaf B", file_suffix="leaf_b", solid=normalize_to_build_plate(leaf_b)),
            GeneratedPart(label="Pin", file_suffix="pin", solid=normalize_to_build_plate(pin)),
        ],
    )


def generate_nut_and_bolt_basic(parameters: Dict[str, Any]) -> GeneratedGeometry:
    shaft_diameter = float(parameters.get("shaft_diameter_mm", 8))
    bolt_length = float(parameters.get("bolt_length_mm", 30))
    head_diameter = float(parameters.get("head_diameter_mm", 14))
    head_height = float(parameters.get("head_height_mm", 5))
    nut_width = float(parameters.get("nut_width_mm", 15))
    nut_thickness = float(parameters.get("nut_thickness_mm", 7))
    fit_clearance = float(parameters.get("fit_clearance_mm", 0.4))

    bolt = _hex_prism(head_diameter, head_height).union(
        _hex_prism(shaft_diameter, bolt_length).translate((0, 0, head_height))
    )
    nut = _hex_prism(nut_width, nut_thickness).cut(
        _hex_prism(shaft_diameter + (2.0 * fit_clearance), nut_thickness + 1.0).translate((0, 0, -0.5))
    )

    bolt = normalize_to_build_plate(bolt)
    nut = normalize_to_build_plate(nut)
    preview = normalize_to_build_plate(bolt.union(nut.translate((0, 0, head_height + bolt_length * 0.35))))
    return GeneratedGeometry(
        primary_solid=bolt,
        preview_solid=preview,
        extra_parts=[GeneratedPart(label="Nut", file_suffix="nut", solid=nut)],
    )


def generate_spacer(parameters: Dict[str, Any]) -> GeneratedGeometry:
    inner_diameter = float(parameters.get("inner_diameter_mm", 5))
    outer_diameter = float(parameters.get("outer_diameter_mm", 12))
    height_mm = float(parameters.get("height_mm", 10))
    chamfer_mm = float(parameters.get("chamfer_mm", 0.6))

    spacer = cq.Workplane("XY").circle(outer_diameter / 2.0).extrude(height_mm)
    spacer = spacer.cut(cq.Workplane("XY").circle(inner_diameter / 2.0).extrude(height_mm + 1.0))
    if chamfer_mm > 0:
        try:
            spacer = spacer.edges(">Z").chamfer(min(chamfer_mm, 1.2))
            spacer = spacer.edges("<Z").chamfer(min(chamfer_mm, 1.2))
        except Exception:
            pass
    spacer = normalize_to_build_plate(spacer)
    return GeneratedGeometry(primary_solid=spacer, preview_solid=spacer)


def generate_test_tube_rack(parameters: Dict[str, Any]) -> GeneratedGeometry:
    tube_diameter = float(parameters.get("tube_diameter_mm", 16))
    tube_count = int(parameters.get("tube_count", 6))
    row_count = max(1, int(parameters.get("row_count", 2)))
    spacing_mm = float(parameters.get("spacing_mm", 8))
    plate_thickness = float(parameters.get("plate_thickness_mm", 4))
    rack_height = float(parameters.get("rack_height_mm", 55))
    foot_width = float(parameters.get("foot_width_mm", 12))

    columns = max(1, math.ceil(tube_count / row_count))
    pitch = tube_diameter + spacing_mm
    rack_length = (columns * pitch) + (2.0 * foot_width)
    rack_width = (row_count * pitch) + (2.0 * foot_width)
    hole_diameter = tube_diameter + 1.2

    top_plate = (
        cq.Workplane("XY")
        .box(rack_length, rack_width, plate_thickness, centered=(True, True, False))
        .translate((0, 0, rack_height))
    )
    base_plate = cq.Workplane("XY").box(rack_length, rack_width, plate_thickness, centered=(True, True, False))

    positions: list[tuple[float, float]] = []
    count = 0
    for row in range(row_count):
        y_pos = ((row - ((row_count - 1) / 2.0)) * pitch)
        for column in range(columns):
            if count >= tube_count:
                break
            x_pos = ((column - ((columns - 1) / 2.0)) * pitch)
            positions.append((x_pos, y_pos))
            count += 1

    if positions:
        top_plate = top_plate.faces(">Z").workplane().pushPoints(positions).hole(hole_diameter)
        base_plate = base_plate.faces(">Z").workplane().pushPoints(positions).hole(tube_diameter * 0.55)

    post_radius = max(foot_width * 0.35, plate_thickness)
    post_positions = [
        (-rack_length / 2.0 + foot_width, -rack_width / 2.0 + foot_width),
        (rack_length / 2.0 - foot_width, -rack_width / 2.0 + foot_width),
        (-rack_length / 2.0 + foot_width, rack_width / 2.0 - foot_width),
        (rack_length / 2.0 - foot_width, rack_width / 2.0 - foot_width),
    ]
    rack = base_plate.union(top_plate)
    for x_pos, y_pos in post_positions:
        post = cq.Workplane("XY").circle(post_radius).extrude(rack_height).translate((x_pos, y_pos, plate_thickness))
        rack = rack.union(post)

    rack = normalize_to_build_plate(rack)
    return GeneratedGeometry(primary_solid=rack, preview_solid=rack)


def generate_sensor_mount(parameters: Dict[str, Any]) -> GeneratedGeometry:
    board_length = float(parameters.get("board_length_mm", 35))
    board_width = float(parameters.get("board_width_mm", 25))
    base_thickness = float(parameters.get("base_thickness_mm", 3))
    standoff_height = float(parameters.get("standoff_height_mm", 8))
    standoff_diameter = float(parameters.get("standoff_diameter_mm", 8))
    hole_diameter = float(parameters.get("hole_diameter_mm", 3))
    flange_width = float(parameters.get("flange_width_mm", 12))
    mounting_holes = bool(parameters.get("mounting_holes", True))

    outer_length = board_length + (2.0 * flange_width)
    outer_width = board_width + (2.0 * flange_width)
    mount = cq.Workplane("XY").box(outer_length, outer_width, base_thickness, centered=(True, True, False))

    post_offset_x = max((board_length / 2.0) - 4.0, 3.0)
    post_offset_y = max((board_width / 2.0) - 4.0, 3.0)
    post_positions = [
        (-post_offset_x, -post_offset_y),
        (post_offset_x, -post_offset_y),
        (-post_offset_x, post_offset_y),
        (post_offset_x, post_offset_y),
    ]
    for x_pos, y_pos in post_positions:
        standoff = cq.Workplane("XY").circle(standoff_diameter / 2.0).extrude(standoff_height).translate((x_pos, y_pos, base_thickness))
        if hole_diameter > 0:
            standoff = standoff.cut(
                cq.Workplane("XY").circle(hole_diameter / 2.0).extrude(standoff_height + 0.5).translate((x_pos, y_pos, base_thickness))
            )
        mount = mount.union(standoff)

    if mounting_holes:
        hole_positions = [
            (-outer_length / 2.0 + flange_width * 0.55, 0),
            (outer_length / 2.0 - flange_width * 0.55, 0),
        ]
        mount = mount.faces(">Z").workplane().pushPoints(hole_positions).hole(hole_diameter + 1.2)

    mount = normalize_to_build_plate(mount)
    return GeneratedGeometry(primary_solid=mount, preview_solid=mount)


def generate_ventilation_box(parameters: Dict[str, Any]) -> GeneratedGeometry:
    length_mm = float(parameters.get("length_mm", 100))
    width_mm = float(parameters.get("width_mm", 80))
    height_mm = float(parameters.get("height_mm", 40))
    wall_mm = float(parameters.get("wall_thickness_mm", 3))
    floor_mm = float(parameters.get("floor_thickness_mm", 3))
    lid_height_mm = float(parameters.get("lid_height_mm", 16))
    vent_slot_count = int(parameters.get("vent_slot_count", 6))
    cable_hole_diameter_mm = float(parameters.get("cable_hole_diameter_mm", 8))
    tolerance_mm = float(parameters.get("tolerance_mm", 0.4))

    base = _open_shell(length_mm, width_mm, height_mm, wall_mm, floor_mm, 1.6)
    if cable_hole_diameter_mm > 0:
        cable_hole = (
            cq.Workplane("XZ")
            .circle(cable_hole_diameter_mm / 2.0)
            .extrude(wall_mm + 2.0)
            .translate((0, (width_mm / 2.0) - wall_mm - 1.0, height_mm * 0.35))
        )
        base = base.cut(cable_hole)

    lid_wall_mm = max(wall_mm * 0.9, 2.0)
    lid_outer_length = length_mm + (2.0 * (tolerance_mm + lid_wall_mm))
    lid_outer_width = width_mm + (2.0 * (tolerance_mm + lid_wall_mm))
    lid = cq.Workplane("XY").box(lid_outer_length, lid_outer_width, lid_height_mm, centered=(True, True, False))
    lid_cavity = (
        cq.Workplane("XY")
        .box(length_mm + (2.0 * tolerance_mm), width_mm + (2.0 * tolerance_mm), max(lid_height_mm - wall_mm, 1.0), centered=(True, True, False))
        .translate((0, 0, wall_mm))
    )
    lid = lid.cut(lid_cavity)

    if vent_slot_count > 0:
        slot_length = lid_outer_length * 0.6
        slot_width = 2.5
        spacing = 6.0
        slots = [
            (0, (index - ((vent_slot_count - 1) / 2.0)) * spacing)
            for index in range(vent_slot_count)
        ]
        lid = lid.faces(">Z").workplane().pushPoints(slots).rect(slot_length, slot_width).cutBlind(-wall_mm * 0.8)

    base = normalize_to_build_plate(base)
    lid = normalize_to_build_plate(lid)
    preview = normalize_to_build_plate(base.union(lid.translate((0, 0, height_mm + 10.0))))
    return GeneratedGeometry(
        primary_solid=base,
        preview_solid=preview,
        extra_parts=[GeneratedPart(label="Lid", file_suffix="lid", solid=lid)],
    )


def generate_stackable_box(parameters: Dict[str, Any]) -> GeneratedGeometry:
    length_mm = float(parameters.get("length_mm", 120))
    width_mm = float(parameters.get("width_mm", 80))
    height_mm = float(parameters.get("height_mm", 60))
    wall_mm = float(parameters.get("wall_thickness_mm", 3))
    floor_mm = float(parameters.get("floor_thickness_mm", 3))
    lip_height_mm = float(parameters.get("stack_lip_height_mm", 6))
    clearance_mm = float(parameters.get("stack_clearance_mm", 0.5))
    rounded_edges = bool(parameters.get("rounded_edges", True))
    corner_radius_mm = float(parameters.get("corner_radius_mm", 2))

    box = _open_shell(length_mm, width_mm, height_mm, wall_mm, floor_mm, corner_radius_mm if rounded_edges else 0.0)
    inner_length = max(length_mm - (2.0 * wall_mm), 8.0)
    inner_width = max(width_mm - (2.0 * wall_mm), 8.0)

    lip_outer = (
        cq.Workplane("XY")
        .box(inner_length - (2.0 * clearance_mm), inner_width - (2.0 * clearance_mm), lip_height_mm, centered=(True, True, False))
        .translate((0, 0, height_mm - lip_height_mm))
    )
    lip_inner = (
        cq.Workplane("XY")
        .box(inner_length - (2.0 * (wall_mm + clearance_mm)), inner_width - (2.0 * (wall_mm + clearance_mm)), lip_height_mm, centered=(True, True, False))
        .translate((0, 0, height_mm - lip_height_mm))
    )
    box = box.union(lip_outer.cut(lip_inner))

    foot_outer = cq.Workplane("XY").box(inner_length - (2.0 * clearance_mm), inner_width - (2.0 * clearance_mm), lip_height_mm, centered=(True, True, False))
    foot_inner = cq.Workplane("XY").box(inner_length - (2.0 * (wall_mm + clearance_mm)), inner_width - (2.0 * (wall_mm + clearance_mm)), lip_height_mm, centered=(True, True, False))
    box = box.union(foot_outer.cut(foot_inner))

    box = normalize_to_build_plate(box)
    return GeneratedGeometry(primary_solid=box, preview_solid=box)


def generate_gridfinity_bin(parameters: Dict[str, Any]) -> GeneratedGeometry:
    grid_units_x = int(parameters.get("grid_units_x", 2))
    grid_units_y = int(parameters.get("grid_units_y", 2))
    height_units = int(parameters.get("height_units", 3))
    wall_mm = float(parameters.get("wall_thickness_mm", 2.4))
    floor_mm = float(parameters.get("floor_thickness_mm", 2.4))
    scoop_front = bool(parameters.get("scoop_front", True))
    magnet_holes = bool(parameters.get("magnet_holes", False))

    module_size_mm = 42.0
    height_mm = max((height_units * 7.0) + 14.0, 18.0)
    length_mm = grid_units_x * module_size_mm
    width_mm = grid_units_y * module_size_mm

    bin = _open_shell(length_mm, width_mm, height_mm, wall_mm, floor_mm, 2.0)
    base_pad = cq.Workplane("XY").box(length_mm - 4.0, width_mm - 4.0, 4.0, centered=(True, True, False))
    bin = bin.union(base_pad)

    top_lip_outer = (
        cq.Workplane("XY")
        .box(length_mm - (2.0 * wall_mm), width_mm - (2.0 * wall_mm), 4.0, centered=(True, True, False))
        .translate((0, 0, height_mm - 4.0))
    )
    top_lip_inner = (
        cq.Workplane("XY")
        .box(length_mm - (4.0 * wall_mm), width_mm - (4.0 * wall_mm), 4.0, centered=(True, True, False))
        .translate((0, 0, height_mm - 4.0))
    )
    bin = bin.union(top_lip_outer.cut(top_lip_inner))

    if scoop_front:
        scoop = (
            cq.Workplane("XZ")
            .polyline(
                [
                    (-length_mm / 2.0, height_mm * 0.55),
                    (length_mm / 2.0, height_mm * 0.55),
                    (length_mm / 2.0, height_mm),
                    (-length_mm / 2.0, height_mm),
                ]
            )
            .close()
            .extrude(width_mm * 0.45)
            .translate((0, width_mm * 0.275, 0))
        )
        bin = bin.cut(scoop)

    if magnet_holes:
        hole_pitch_x = (length_mm / 2.0) - 12.0
        hole_pitch_y = (width_mm / 2.0) - 12.0
        for x_pos in (-hole_pitch_x, hole_pitch_x):
            for y_pos in (-hole_pitch_y, hole_pitch_y):
                bin = bin.cut(
                    cq.Workplane("XY")
                    .circle(3.2)
                    .extrude(2.6)
                    .translate((x_pos, y_pos, 0))
                )

    bin = normalize_to_build_plate(bin)
    return GeneratedGeometry(primary_solid=bin, preview_solid=bin)


def generate_interlocking_panel(parameters: Dict[str, Any]) -> GeneratedGeometry:
    length_mm = float(parameters.get("length_mm", 120))
    width_mm = float(parameters.get("width_mm", 80))
    thickness_mm = float(parameters.get("thickness_mm", 4))
    tab_width_mm = float(parameters.get("tab_width_mm", 16))
    tab_depth_mm = float(parameters.get("tab_depth_mm", 8))
    tabs_per_side = int(parameters.get("tabs_per_side", 2))
    slot_clearance_mm = float(parameters.get("slot_clearance_mm", 0.35))

    base_length_mm = max(length_mm - (2.0 * tab_depth_mm), 8.0)
    panel = cq.Workplane("XY").box(base_length_mm, width_mm, thickness_mm, centered=(True, True, False))

    y_positions = _distributed_positions(width_mm, tabs_per_side, max((tab_width_mm / 2.0) + 6.0, 8.0))
    for y_pos in y_positions:
        right_tab = (
            cq.Workplane("XY")
            .box(tab_depth_mm, tab_width_mm, thickness_mm, centered=(True, True, False))
            .translate(((base_length_mm / 2.0) + (tab_depth_mm / 2.0), y_pos, 0))
        )
        left_tab = (
            cq.Workplane("XY")
            .box(tab_depth_mm, tab_width_mm, thickness_mm, centered=(True, True, False))
            .translate(((-base_length_mm / 2.0) - (tab_depth_mm / 2.0), y_pos, 0))
        )
        panel = panel.union(right_tab).union(left_tab)

    x_positions = _distributed_positions(base_length_mm, tabs_per_side, max((tab_width_mm / 2.0) + 6.0, 8.0))
    slot_width = tab_width_mm + (2.0 * slot_clearance_mm)
    slot_depth = tab_depth_mm + 1.0
    for x_pos in x_positions:
        top_slot = (
            cq.Workplane("XY")
            .box(slot_width, slot_depth, thickness_mm + 1.0, centered=(True, True, False))
            .translate((x_pos, (width_mm / 2.0) - (slot_depth / 2.0), 0))
        )
        bottom_slot = (
            cq.Workplane("XY")
            .box(slot_width, slot_depth, thickness_mm + 1.0, centered=(True, True, False))
            .translate((x_pos, (-width_mm / 2.0) + (slot_depth / 2.0), 0))
        )
        panel = panel.cut(top_slot).cut(bottom_slot)

    panel = normalize_to_build_plate(panel)
    return GeneratedGeometry(primary_solid=panel, preview_solid=panel)


def generate_geometry(model_type: str, parameters: Dict[str, Any]) -> GeneratedGeometry:
    generators = {
        "phone_stand": generate_phone_stand,
        "box_with_lid": generate_box_with_lid,
        "wall_hook": generate_wall_hook,
        "drawer_divider": generate_drawer_divider,
        "bottle_holder": generate_bottle_holder,
        "desk_organizer": generate_desk_organizer,
        "laptop_stand": generate_laptop_stand,
        "remote_holder": generate_remote_holder,
        "card_holder": generate_card_holder,
        "hinge": generate_hinge,
        "snap_fit_box": generate_snap_fit_box,
        "nut_and_bolt_basic": generate_nut_and_bolt_basic,
        "spacer": generate_spacer,
        "cable_clip": generate_cable_clip,
        "simple_gear": generate_simple_gear,
        "pcb_enclosure": generate_pcb_enclosure,
        "test_tube_rack": generate_test_tube_rack,
        "sensor_mount": generate_sensor_mount,
        "ventilation_box": generate_ventilation_box,
        "stackable_box": generate_stackable_box,
        "gridfinity_bin": generate_gridfinity_bin,
        "interlocking_panel": generate_interlocking_panel,
    }
    if model_type not in generators:
        raise ValueError(f"No V2 generator implemented for {model_type}.")
    return generators[model_type](parameters)
