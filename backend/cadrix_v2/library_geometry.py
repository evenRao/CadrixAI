"""Additional functional parts, with connected bodies and explicit mating clearances."""
from __future__ import annotations

import math
from typing import Any

import cadquery as cq

from cadrix_v2.geometry_core import EPS, GeneratedGeometry, GeneratedPart, divided_tray, normalize_to_build_plate, rounded_prism, single_part, soften_edges


def generate_parts_tray(p: dict[str, Any]) -> GeneratedGeometry:
    return single_part(soften_edges(divided_tray(p), min(0.4, float(p["wall_thickness_mm"]) * 0.15)))


def generate_planter(p: dict[str, Any]) -> GeneratedGeometry:
    diameter, height = float(p["diameter_mm"]), float(p["height_mm"])
    wall, floor = float(p["wall_thickness_mm"]), float(p["floor_thickness_mm"])
    taper = float(p["taper_mm"])
    bottom_r, top_r = diameter / 2 - taper, diameter / 2
    body = cq.Workplane("XY").circle(bottom_r).workplane(offset=height).circle(top_r).loft(ruled=True)
    # Offset the inner cone at the floor to retain a uniform radial wall.
    inner_bottom = bottom_r + taper * floor / height - wall
    cavity = cq.Workplane("XY").workplane(offset=floor).circle(inner_bottom).workplane(offset=height - floor + EPS).circle(top_r - wall + taper * EPS / height).loft(ruled=True)
    body = body.cut(cavity)
    rim = cq.Workplane("XY").circle(top_r + 1).circle(top_r - wall).extrude(2).translate((0, 0, height - 2))
    body = body.union(rim)
    if p["drainage_holes"]:
        hole_r = float(p["drain_hole_diameter_mm"]) / 2
        for x, y in [(0, 0), *[(bottom_r * 0.5 * math.cos(i * math.pi / 2), bottom_r * 0.5 * math.sin(i * math.pi / 2)) for i in range(4)]]:
            body = body.cut(cq.Workplane("XY").circle(hole_r).extrude(floor + EPS).translate((x, y, 0)))
    body = normalize_to_build_plate(soften_edges(body, min(0.35, wall * 0.15)))
    if not p["drip_tray"]:
        return GeneratedGeometry(body, body)
    tray_height = 10.0
    tray_radius = bottom_r + float(p["tray_clearance_mm"]) + wall
    tray = cq.Workplane("XY").circle(tray_radius).extrude(tray_height).cut(cq.Workplane("XY").circle(tray_radius - wall).extrude(tray_height).translate((0, 0, floor)))
    tray = soften_edges(tray, min(0.35, wall * 0.15))
    preview = body.union(tray.translate((diameter + 15, 0, 0)))
    return GeneratedGeometry(body, preview, [GeneratedPart("Drip tray", "drip_tray", tray)])


def generate_funnel(p: dict[str, Any]) -> GeneratedGeometry:
    mouth_r, outlet_r = float(p["mouth_diameter_mm"]) / 2, float(p["outlet_diameter_mm"]) / 2
    height, neck, wall = float(p["height_mm"]), float(p["neck_length_mm"]), float(p["wall_thickness_mm"])
    bowl = cq.Workplane("XY").workplane(offset=neck).circle(outlet_r).workplane(offset=height - neck).circle(mouth_r).loft(ruled=True)
    spout = cq.Workplane("XY").circle(outlet_r).extrude(neck + EPS)
    inner_bowl = cq.Workplane("XY").workplane(offset=neck - EPS).circle(outlet_r - wall).workplane(offset=height - neck + 2 * EPS).circle(mouth_r - wall).loft(ruled=True)
    inner_neck = cq.Workplane("XY").circle(outlet_r - wall).extrude(neck + EPS).translate((0, 0, -EPS))
    body = bowl.union(spout).cut(inner_bowl.union(inner_neck))
    rim = cq.Workplane("XY").circle(mouth_r).circle(mouth_r - wall).extrude(1.2).translate((0, 0, height - 1.2))
    body = body.union(rim)
    return single_part(soften_edges(body, min(0.3, wall * 0.12)))


def generate_angle_bracket(p: dict[str, Any]) -> GeneratedGeometry:
    length, height, width = (float(p[key]) for key in ("leg_length_mm", "leg_height_mm", "width_mm"))
    wall = float(p["wall_thickness_mm"])
    body = cq.Workplane("XY").box(length, width, wall, centered=(False, True, False))
    upright = cq.Workplane("XY").box(wall, width, height, centered=(False, True, False))
    body = body.union(upright)
    if p["gussets"]:
        thickness = min(wall, width * 0.15)
        brace = cq.Workplane("XZ").polyline([(wall - EPS, wall - EPS), (length * 0.75, wall - EPS), (wall - EPS, height * 0.75)]).close().extrude(thickness / 2, both=True)
        for side in (-1, 1):
            body = body.union(brace.translate((0, side * (width / 2 - thickness / 2), 0)))
    if p["mounting_holes"]:
        hole_r = float(p["screw_hole_diameter_mm"]) / 2
        body = body.cut(cq.Workplane("XY").circle(hole_r).extrude(wall + 2 * EPS).translate((length * 0.7, 0, -EPS)))
        body = body.cut(cq.Workplane("YZ").circle(hole_r).extrude(wall + 2 * EPS).translate((-EPS, 0, height * 0.7)))
    return single_part(soften_edges(body, min(0.4, wall * 0.12)))


def generate_drawer_pull(p: dict[str, Any]) -> GeneratedGeometry:
    spacing, height, grip_width = (float(p[key]) for key in ("hole_spacing_mm", "height_mm", "grip_width_mm"))
    grip = float(p["grip_thickness_mm"])
    post_r = float(p["post_diameter_mm"]) / 2
    body = rounded_prism(spacing + 2 * post_r, max(grip_width, 2 * post_r), grip, min(grip_width, 2 * post_r) / 2 - EPS).translate((0, 0, height - grip))
    for x in (-spacing / 2, spacing / 2):
        body = body.union(cq.Workplane("XY").circle(post_r).extrude(height - grip + EPS).translate((x, 0, 0)))
        bore = cq.Workplane("XY").circle(float(p["screw_hole_diameter_mm"]) / 2).extrude(float(p["hole_depth_mm"]) + EPS).translate((x, 0, -EPS))
        body = body.cut(bore)
    return single_part(soften_edges(body, min(0.6, grip * 0.15)))


def generate_desk_grommet(p: dict[str, Any]) -> GeneratedGeometry:
    outer_r = float(p["desk_hole_diameter_mm"]) / 2 - float(p["fit_clearance_mm"])
    wall, flange = float(p["wall_thickness_mm"]), float(p["flange_thickness_mm"])
    depth, flange_r = float(p["sleeve_depth_mm"]), float(p["flange_diameter_mm"]) / 2
    body = cq.Workplane("XY").circle(outer_r).circle(outer_r - wall).extrude(depth + flange)
    body = body.union(cq.Workplane("XY").circle(flange_r).circle(outer_r - wall).extrude(flange))
    if p["cable_notch"]:
        notch = cq.Workplane("XY").box(float(p["notch_width_mm"]), flange_r + 2, depth + flange + 2 * EPS, centered=(True, False, False)).translate((0, 0, -EPS))
        body = body.cut(notch)
    return single_part(soften_edges(body, min(0.4, wall * 0.15)))


def generate_hose_adapter(p: dict[str, Any]) -> GeneratedGeometry:
    inlet, outlet = float(p["inlet_diameter_mm"]) / 2, float(p["outlet_diameter_mm"]) / 2
    length, end, wall = float(p["length_mm"]), float(p["end_length_mm"]), float(p["wall_thickness_mm"])
    body = cq.Workplane("XY").circle(inlet).workplane(offset=end).circle(inlet).workplane(offset=length - 2 * end).circle(outlet).workplane(offset=end).circle(outlet).loft(ruled=True)
    bore = cq.Workplane("XY").workplane(offset=-EPS).circle(inlet - wall).workplane(offset=end + EPS).circle(inlet - wall).workplane(offset=length - 2 * end).circle(outlet - wall).workplane(offset=end + EPS).circle(outlet - wall).loft(ruled=True)
    body = body.cut(bore)
    if p["retention_ridges"]:
        for z, radius in ((end * 0.4, inlet), (length - end * 0.5, outlet)):
            ridge = cq.Workplane("XY").circle(radius + float(p["ridge_height_mm"])).circle(radius - wall).extrude(1.2).translate((0, 0, z))
            body = body.union(ridge)
    return single_part(soften_edges(body, min(0.4, wall * 0.15)))


def generate_cable_comb(p: dict[str, Any]) -> GeneratedGeometry:
    diameter, count = float(p["cable_diameter_mm"]), int(p["cable_count"])
    spacing, depth = float(p["cable_spacing_mm"]), float(p["depth_mm"])
    wall, floor = float(p["wall_thickness_mm"]), float(p["floor_thickness_mm"])
    radius = diameter / 2 + float(p["fit_clearance_mm"])
    length, height = (count - 1) * spacing + 2 * (radius + wall), floor + 2 * radius + wall
    margin = float(p["screw_hole_diameter_mm"]) + 2 * wall if p["mounting_holes"] else 0
    body = rounded_prism(length + 2 * margin, depth, floor, min(2, depth / 4))
    body = body.union(rounded_prism(length, depth, height, min(1, wall / 2)))
    for index in range(count):
        x = (index - (count - 1) / 2) * spacing
        hole = cq.Workplane("XZ").circle(radius).extrude(depth / 2 + EPS, both=True).translate((x, 0, floor + radius))
        slot = cq.Workplane("XY").box(diameter * 0.8, depth + 2 * EPS, height, centered=(True, True, False)).translate((x, 0, floor + radius))
        body = body.cut(hole).cut(slot)
    if p["mounting_holes"]:
        for side in (-1, 1):
            hole = cq.Workplane("XY").circle(float(p["screw_hole_diameter_mm"]) / 2).extrude(floor + EPS).translate((side * (length / 2 + margin / 2), 0, 0))
            body = body.cut(hole)
    return single_part(soften_edges(body, min(0.25, wall * 0.1)))


def generate_battery_organizer(p: dict[str, Any]) -> GeneratedGeometry:
    diameter, count, rows = float(p["cell_diameter_mm"]), int(p["cell_count"]), int(p["row_count"])
    depth, wall, floor = float(p["pocket_depth_mm"]), float(p["wall_thickness_mm"]), float(p["floor_thickness_mm"])
    radius = diameter / 2 + float(p["fit_clearance_mm"])
    pitch = 2 * radius + wall
    columns = math.ceil(count / rows)
    length, width = columns * pitch + wall, rows * pitch + wall
    body = rounded_prism(length, width, depth + floor, min(4, wall * 1.5))
    for index in range(count):
        column, row = index // rows, index % rows
        x, y = (column - (columns - 1) / 2) * pitch, (row - (rows - 1) / 2) * pitch
        body = body.cut(cq.Workplane("XY").circle(radius).extrude(depth + EPS).translate((x, y, floor)))
    return single_part(soften_edges(body, min(0.5, wall * 0.2)))


def generate_tube_end_cap(p: dict[str, Any]) -> GeneratedGeometry:
    inner = float(p["tube_diameter_mm"]) / 2 + float(p["fit_clearance_mm"])
    height, wall, floor = float(p["height_mm"]), float(p["wall_thickness_mm"]), float(p["floor_thickness_mm"])
    outer = inner + wall
    body = cq.Workplane("XY").circle(outer).extrude(height)
    body = body.cut(cq.Workplane("XY").circle(inner).extrude(height - floor + EPS).translate((0, 0, floor)))
    if p["grip_ribs"]:
        for index in range(3):
            z = floor + (height - floor) * (index + 0.5) / 3
            body = body.union(cq.Workplane("XY").circle(outer + 0.6).circle(inner).extrude(0.8).translate((0, 0, z)))
    return single_part(soften_edges(body, min(0.4, wall * 0.15)))


LIBRARY_GENERATORS = {
    "parts_tray": generate_parts_tray,
    "planter": generate_planter,
    "funnel": generate_funnel,
    "angle_bracket": generate_angle_bracket,
    "drawer_pull": generate_drawer_pull,
    "desk_grommet": generate_desk_grommet,
    "hose_adapter": generate_hose_adapter,
    "cable_comb": generate_cable_comb,
    "battery_organizer": generate_battery_organizer,
    "tube_end_cap": generate_tube_end_cap,
}
