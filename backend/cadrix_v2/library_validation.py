"""Geometric relationships for the expanded library, before invoking the CAD kernel."""
from __future__ import annotations

import math

from cadrix_v2.schemas import ValidationIssue


def validate_library_parameters(model_type, p, issues):
    def error(message, field):
        issues.append(ValidationIssue(severity="error", message=message, field=field))

    def warning(message, field=None):
        issues.append(ValidationIssue(severity="warning", message=message, field=field))

    wall = float(p.get("wall_thickness_mm", 2.4))
    floor = float(p.get("floor_thickness_mm", 2.4))
    if model_type in {"box_with_lid", "snap_fit_box", "desk_organizer", "ventilation_box", "stackable_box", "parts_tray"}:
        if min(p["length_mm"], p["width_mm"]) <= 2 * wall + 2:
            error("The outer footprint must leave at least 2mm of usable space inside the walls.", "wall_thickness_mm")
        if p["height_mm"] <= floor + 1:
            error("Height must exceed floor thickness by at least 1mm.", "floor_thickness_mm")
    if model_type in {"desk_organizer", "parts_tray"}:
        count = int(p["compartment_count"])
        usable = p["length_mm"] - 2 * wall - (count - 1) * p["divider_thickness_mm"]
        if usable / count < 6:
            error("The compartment layout leaves less than 6mm in each pocket. Reduce the count or divider thickness.", "compartment_count")
    elif model_type == "planter":
        bottom = p["diameter_mm"] / 2 - p["taper_mm"]
        if bottom <= wall + 3:
            error("Taper and walls leave too little room in the planter base. Reduce taper or increase diameter.", "taper_mm")
        if p["height_mm"] <= floor + 5:
            error("Planter height must leave at least 5mm above the floor.", "floor_thickness_mm")
        if p["drainage_holes"] and (bottom / 2 <= p["drain_hole_diameter_mm"] + 1.2 or bottom / 2 + p["drain_hole_diameter_mm"] / 2 + 1.2 >= bottom - wall):
            error("Drain holes are too large for the planter base. Reduce their diameter or reduce taper.", "drain_hole_diameter_mm")
        if p["drip_tray"] and floor >= 9:
            error("The drip tray needs a floor thinner than 9mm.", "floor_thickness_mm")
    elif model_type == "funnel":
        if p["outlet_diameter_mm"] <= 2 * wall + 1:
            error("Outlet diameter must exceed twice the wall thickness by at least 1mm to keep the throat open.", "outlet_diameter_mm")
        if p["mouth_diameter_mm"] <= p["outlet_diameter_mm"] + 2 * wall:
            error("The funnel mouth must be wider than its outlet plus two wall thicknesses.", "mouth_diameter_mm")
        if p["height_mm"] <= p["neck_length_mm"] + 2 * wall:
            error("Height must leave room for the tapered bowl above the neck.", "neck_length_mm")
        elif (p["mouth_diameter_mm"] - p["outlet_diameter_mm"]) / 2 > p["height_mm"] - p["neck_length_mm"]:
            warning("The shallow funnel cone may need supports or a different print orientation.", "height_mm")
    elif model_type == "angle_bracket":
        if min(p["leg_length_mm"], p["leg_height_mm"]) <= 3 * wall:
            error("Each bracket leg must be longer than three wall thicknesses.", "wall_thickness_mm")
        if p["mounting_holes"] and (p["screw_hole_diameter_mm"] + 2 * wall >= p["width_mm"] or p["screw_hole_diameter_mm"] / 2 + 1.2 >= min(p["leg_length_mm"], p["leg_height_mm"]) * 0.3):
            error("Mounting holes leave insufficient edge material. Reduce hole diameter or increase the bracket size.", "screw_hole_diameter_mm")
    elif model_type == "drawer_pull":
        if p["height_mm"] <= p["grip_thickness_mm"] + 6:
            error("The handle needs at least 6mm of finger space beneath the grip.", "height_mm")
        if p["hole_depth_mm"] >= p["height_mm"] - p["grip_thickness_mm"]:
            error("Blind holes must end below the gripping bar. Reduce hole depth or increase handle height.", "hole_depth_mm")
        if p["post_diameter_mm"] <= p["screw_hole_diameter_mm"] + 2.4:
            error("Posts need at least 1.2mm of wall around each mounting bore.", "post_diameter_mm")
        if p["post_diameter_mm"] > p["grip_width_mm"]:
            error("Grip width must be at least the post diameter.", "grip_width_mm")
    elif model_type == "desk_grommet":
        if p["flange_diameter_mm"] < p["desk_hole_diameter_mm"] + 2 * wall:
            error("The flange must overhang the desktop hole by at least one wall thickness on each side.", "flange_diameter_mm")
        if p["desk_hole_diameter_mm"] <= 2 * (wall + p["fit_clearance_mm"]) + 2:
            error("The sleeve walls and clearance close the cable opening.", "wall_thickness_mm")
        if p["cable_notch"] and p["notch_width_mm"] >= p["desk_hole_diameter_mm"] * 0.7:
            error("Notch width must be less than 70% of the desk-hole diameter.", "notch_width_mm")
    elif model_type == "hose_adapter":
        if min(p["inlet_diameter_mm"], p["outlet_diameter_mm"]) <= 2 * wall + 2:
            error("Both hose ends need at least a 2mm open bore after applying wall thickness.", "wall_thickness_mm")
        if p["length_mm"] <= 2 * p["end_length_mm"] + wall:
            error("Length must leave a transition section between the two insertion ends.", "end_length_mm")
    elif model_type == "cable_comb":
        if p["cable_spacing_mm"] < p["cable_diameter_mm"] + 2 * p["fit_clearance_mm"] + wall:
            error("Cable spacing must leave at least one wall thickness between neighboring pockets.", "cable_spacing_mm")
        if p["mounting_holes"] and p["screw_hole_diameter_mm"] + 2.4 >= p["depth_mm"]:
            error("The mounting ears need at least 1.2mm around the screw holes.", "screw_hole_diameter_mm")
    elif model_type == "battery_organizer":
        if p["row_count"] > p["cell_count"]:
            error("Row count cannot exceed the number of cells.", "row_count")
        columns = math.ceil(p["cell_count"] / p["row_count"])
        if columns * (p["cell_diameter_mm"] + 2 * p["fit_clearance_mm"] + wall) + wall > 250:
            warning("This battery layout is over 250mm long. Check your build volume or use more rows.", "row_count")
    elif model_type == "tube_end_cap":
        if p["height_mm"] <= floor + 3:
            error("The cap needs at least 3mm of insertion depth above its closed end.", "floor_thickness_mm")
