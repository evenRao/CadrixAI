"""Shared dimensions, printable solids, and finishing for the model library."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cadquery as cq
from cadquery.occ_impl.geom import BoundBox
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

EPS = 0.05


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


def exact_bounding_box(solid: cq.Workplane) -> BoundBox:
    box = Bnd_Box()
    # Exporting populates triangulation caches. Ignoring them keeps reported
    # dimensions independent of tessellation tolerance and export order.
    BRepBndLib.AddOptimal_s(solid.val().wrapped, box, False, False)
    return BoundBox(box)


def normalize_to_build_plate(solid: cq.Workplane) -> cq.Workplane:
    box = exact_bounding_box(solid)
    return solid.translate((-(box.xmin + box.xmax) / 2, -(box.ymin + box.ymax) / 2, -box.zmin))


def estimate_dimensions_mm(solid: cq.Workplane) -> dict[str, float]:
    box = exact_bounding_box(solid)
    return {axis: round(float(value), 2) for axis, value in zip("xyz", (box.xlen, box.ylen, box.zlen))}


def rounded_prism(length: float, width: float, height: float, radius: float = 0) -> cq.Workplane:
    """Round the footprint before hollowing, preserving the requested envelope."""
    body = cq.Workplane("XY").box(length, width, height, centered=(True, True, False))
    radius = min(radius, min(length, width) / 2 - EPS)
    return body.edges("|Z").fillet(radius) if radius > EPS else body


def open_shell(length: float, width: float, height: float, wall: float, floor: float, radius: float = 0) -> cq.Workplane:
    if min(length, width) <= 2 * wall or height <= floor:
        raise ValueError("Shell dimensions must leave room for the walls and floor.")
    radius = min(radius, min(length, width) / 2 - EPS)
    outer = rounded_prism(length, width, height, radius)
    inner = rounded_prism(length - 2 * wall, width - 2 * wall, height - floor + EPS, max(radius - wall, 0))
    return outer.cut(inner.translate((0, 0, floor)))


def soften_edges(body: cq.Workplane, radius: float, selector: str = ">Z") -> cq.Workplane:
    """Small edge breaks are optional; a failed cosmetic operation keeps the solid."""
    if radius <= 0:
        return body
    try:
        candidate = body.faces(selector).edges().chamfer(radius)
        if candidate.val().isValid() and candidate.solids().size() == body.solids().size():
            return candidate
    except Exception:
        pass
    return body


def single_part(body: cq.Workplane) -> GeneratedGeometry:
    body = normalize_to_build_plate(body)
    return GeneratedGeometry(primary_solid=body, preview_solid=body)


def divided_tray(parameters: dict[str, Any]) -> cq.Workplane:
    length, width, height = (float(parameters[key]) for key in ("length_mm", "width_mm", "height_mm"))
    wall = float(parameters.get("wall_thickness_mm", 2.4))
    floor = float(parameters.get("floor_thickness_mm", 2.4))
    radius = float(parameters.get("corner_radius_mm", 6))
    divider = float(parameters.get("divider_thickness_mm", wall))
    count = int(parameters.get("compartment_count", 1))
    body = open_shell(length, width, height, wall, floor, radius)
    inner_length = length - 2 * wall
    compartment_width = (inner_length - (count - 1) * divider) / count
    for index in range(1, count):
        x = -inner_length / 2 + index * compartment_width + (index - 0.5) * divider
        partition = cq.Workplane("XY").box(divider, width - 2 * wall + 2 * EPS, height - floor + EPS, centered=(True, True, False)).translate((x, 0, floor - EPS))
        body = body.union(partition)
    return body
