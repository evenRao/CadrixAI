from __future__ import annotations

import json
import os
import re
import uuid
from typing import Literal, Optional, List, Dict, Any, Tuple

import numpy as np
import trimesh
import requests
import cadquery as cq
from cadquery import exporters

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE_DIR, "out")
os.makedirs(OUT_DIR, exist_ok=True)

app = FastAPI(title="CadrixAI (Intent-Driven Parametric CAD)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Supported model types
# ----------------------------
ModelType = Literal[
    # Boxes / containers
    "box_open",
    "box_with_lid",
    "tray",
    "drawer_bin",
    "cyl_container",

    # Stands / holders
    "phone_stand",
    "tablet_stand",
    "desk_nameplate",

    # Brackets / plates / mounts
    "l_bracket",
    "corner_brace",
    "flat_plate",

    # Hardware
    "spacer",
    "washer",
    "standoff",

    # Clips / grommets
    "cable_clip",
    "cable_grommet",

    # Hooks
    "wall_hook",

    # Simple shapes / toys
    "coin",
    "fidget_coin",
    "keychain_tag",
]

ProcessType = Literal["FDM"]


# ----------------------------
# API models
# ----------------------------
class PlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=800)
    units: Literal["mm"] = "mm"
    use_ollama: bool = False


class PlanResponse(BaseModel):
    model_type: ModelType
    params: Dict[str, Any]
    questions: List[str]
    assumptions: List[str]


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=800)
    model_type: ModelType
    params: Dict[str, Any]


class GenerateResponse(BaseModel):
    model_type: ModelType
    file_id: str
    stl_download_url: str
    preview_glb_url: str
    params_used: Dict[str, Any]


class CapabilityItem(BaseModel):
    model_type: str
    title: str
    description: str
    examples: List[str]


class CapabilitiesResponse(BaseModel):
    app_name: str
    tagline: str
    categories: List[str]
    supported: List[CapabilityItem]
    not_supported: List[str]


# ----------------------------
# Parsing helpers
# ----------------------------
TRIPLE_RE = re.compile(
    r"(?P<a>\d+(?:\.\d+)?)\s*[xX]\s*(?P<b>\d+(?:\.\d+)?)\s*[xX]\s*(?P<c>\d+(?:\.\d+)?)\s*(?P<u>mm|cm|in|inch|inches)\b",
    re.IGNORECASE,
)
UNIT_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|in|inch|inches)\b", re.IGNORECASE)

def unit_to_mm(v: float, unit: str) -> float:
    u = unit.lower()
    if u == "mm":
        return v
    if u == "cm":
        return v * 10.0
    if u in ("in", "inch", "inches"):
        return v * 25.4
    return v

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def contains_any(p: str, words: List[str]) -> bool:
    pl = p.lower()
    return any(w in pl for w in words)

def extract_triple_mm(prompt: str) -> Optional[Tuple[float, float, float]]:
    m = TRIPLE_RE.search(prompt)
    if not m:
        return None
    a = unit_to_mm(float(m.group("a")), m.group("u"))
    b = unit_to_mm(float(m.group("b")), m.group("u"))
    c = unit_to_mm(float(m.group("c")), m.group("u"))
    return (a, b, c)

def extract_numbers_mm(prompt: str) -> List[float]:
    return [unit_to_mm(float(m.group("num")), m.group("unit")) for m in UNIT_RE.finditer(prompt)]

def safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


# ----------------------------
# Capability data (single source of truth for UI)
# ----------------------------
CAPABILITIES: List[Dict[str, Any]] = [
    # Boxes / containers
    {
        "model_type": "box_open",
        "title": "Open box",
        "description": "Open-top box with configurable wall and floor thickness.",
        "examples": ["open box 120x80x60 mm", "box 100x100x50 mm"],
    },
    {
        "model_type": "box_with_lid",
        "title": "Box with friction-fit lid",
        "description": "A printable storage box with a friction-fit lid using tolerance.",
        "examples": ["box with lid 120x80x60 mm", "container with lid 90x60x40 mm"],
    },
    {
        "model_type": "tray",
        "title": "Tray",
        "description": "Low-height tray for desk or drawer organization.",
        "examples": ["tray 200x120x20 mm", "desk tray 180x100x25 mm"],
    },
    {
        "model_type": "drawer_bin",
        "title": "Drawer bin",
        "description": "Rounded bin, good for drawer organizers.",
        "examples": ["drawer bin 120x80x50 mm", "organizer bin 150x90x60 mm"],
    },
    {
        "model_type": "cyl_container",
        "title": "Cylindrical container (open)",
        "description": "Cylinder container by diameter and height.",
        "examples": ["cyl container 80mm 120mm", "cylinder 60mm 90mm"],
    },

    # Stands / holders
    {
        "model_type": "phone_stand",
        "title": "Phone stand",
        "description": "Simple desk stand with lip and phone slot.",
        "examples": ["phone stand 90x120x70 mm", "phone holder 100x140x80 mm"],
    },
    {
        "model_type": "tablet_stand",
        "title": "Tablet stand",
        "description": "Wider and stronger stand suitable for tablets.",
        "examples": ["tablet stand 140x180x90 mm", "ipad stand 160x200x100 mm"],
    },
    {
        "model_type": "desk_nameplate",
        "title": "Desk nameplate (no text yet)",
        "description": "A simple angled nameplate blank that can be labeled later.",
        "examples": ["nameplate 140x40x6 mm", "desk nameplate 160x50x8 mm"],
    },

    # Brackets / mounts
    {
        "model_type": "l_bracket",
        "title": "L-bracket",
        "description": "Two-leg bracket with holes.",
        "examples": ["l bracket 60x60x5 mm", "bracket 80x50x6 mm"],
    },
    {
        "model_type": "corner_brace",
        "title": "Corner brace",
        "description": "A right-angle brace with a triangular gusset.",
        "examples": ["corner brace 60x60x5 mm", "angle brace 80x80x6 mm"],
    },
    {
        "model_type": "flat_plate",
        "title": "Flat plate (mounting plate)",
        "description": "Rectangular plate with optional hole pattern.",
        "examples": ["plate 120x60x4 mm", "mounting plate 100x50x3 mm"],
    },

    # Hardware
    {
        "model_type": "spacer",
        "title": "Spacer",
        "description": "Spacer by inner diameter, outer diameter, and height.",
        "examples": ["spacer 5mm 12mm 10mm", "standoff spacer 3mm 8mm 12mm"],
    },
    {
        "model_type": "washer",
        "title": "Washer",
        "description": "Washer by inner diameter, outer diameter, and thickness.",
        "examples": ["washer 5mm 12mm 2mm", "washer 3mm 9mm 1.5mm"],
    },
    {
        "model_type": "standoff",
        "title": "Standoff (solid cylinder)",
        "description": "Solid cylinder standoff by diameter and height.",
        "examples": ["standoff 10mm 20mm", "cylinder standoff 8mm 15mm"],
    },

    # Clips / grommets
    {
        "model_type": "cable_clip",
        "title": "Cable clip",
        "description": "U-clip for holding a cable (slot width).",
        "examples": ["cable clip 6mm 12mm", "wire clip 8mm 14mm"],
    },
    {
        "model_type": "cable_grommet",
        "title": "Cable grommet",
        "description": "Desk grommet ring by outer diameter and inner diameter.",
        "examples": ["grommet 50mm 35mm 5mm", "cable grommet 60mm 40mm 6mm"],
    },

    # Hooks
    {
        "model_type": "wall_hook",
        "title": "Wall hook",
        "description": "Simple wall hook with plate and screw holes.",
        "examples": ["hook 50x70x5 mm", "wall hook 60x90x6 mm"],
    },

    # Simple shapes / toys
    {
        "model_type": "coin",
        "title": "Coin (disc)",
        "description": "Disc by diameter and thickness.",
        "examples": ["coin 30mm 2mm", "token 25mm 3mm"],
    },
    {
        "model_type": "fidget_coin",
        "title": "Fidget coin (grooved disc)",
        "description": "Coin with grooves for tactile fidgeting.",
        "examples": ["fidget coin 35mm 3mm", "grooved coin 30mm 2.5mm"],
    },
    {
        "model_type": "keychain_tag",
        "title": "Keychain tag (blank)",
        "description": "Rounded rectangle tag with a hole.",
        "examples": ["keychain tag 60x25x3 mm", "tag 70x30x4 mm"],
    },
]

CATEGORIES = [
    "Functional parts and household objects",
    "Organizers, stands, holders",
    "Boxes, lids, containers",
    "Brackets, spacers, hooks",
    "Phone accessories",
    "Simple toys and shapes",
]

NOT_SUPPORTED = [
    "Organic models (hands, faces, characters)",
    "Copyrighted characters and logos",
    "Complex mechanical assemblies without explicit specs",
]


# ----------------------------
# Template selection
# ----------------------------
def guess_template(prompt: str) -> ModelType:
    p = prompt.lower()

    # Explicit blocks (avoid lying)
    if any(w in p for w in ["hand", "face", "human", "person", "anime", "character"]):
        # Still return something, but planner will ask user to pick supported objects
        return "box_with_lid"

    if contains_any(p, ["box with lid", "lid", "container with lid"]):
        return "box_with_lid"
    if contains_any(p, ["open box", "open-top box"]):
        return "box_open"
    if contains_any(p, ["tray"]):
        return "tray"
    if contains_any(p, ["drawer bin", "organizer bin", "bin"]):
        return "drawer_bin"
    if contains_any(p, ["cyl container", "cylinder container", "cylindrical container"]):
        return "cyl_container"

    if contains_any(p, ["tablet stand", "ipad stand"]):
        return "tablet_stand"
    if contains_any(p, ["phone stand", "phone holder", "dock", "stand"]):
        return "phone_stand"
    if contains_any(p, ["nameplate", "desk nameplate"]):
        return "desk_nameplate"

    if contains_any(p, ["corner brace", "angle brace", "gusset"]):
        return "corner_brace"
    if contains_any(p, ["l bracket", "bracket", "angle bracket"]):
        return "l_bracket"
    if contains_any(p, ["mounting plate", "plate"]):
        return "flat_plate"

    if contains_any(p, ["washer"]):
        return "washer"
    if contains_any(p, ["spacer", "standoff spacer"]):
        return "spacer"
    if contains_any(p, ["standoff"]):
        return "standoff"

    if contains_any(p, ["grommet"]):
        return "cable_grommet"
    if contains_any(p, ["cable clip", "wire clip", "clip"]):
        return "cable_clip"

    if contains_any(p, ["hook", "hanger"]):
        return "wall_hook"

    if contains_any(p, ["fidget coin", "grooved coin"]):
        return "fidget_coin"
    if contains_any(p, ["coin", "token", "disc", "disk"]):
        return "coin"
    if contains_any(p, ["keychain", "tag"]):
        return "keychain_tag"

    return "box_with_lid"


# ----------------------------
# Defaults
# ----------------------------
def default_print_settings() -> Dict[str, Any]:
    return {
        "process": "FDM",
        "nozzle_mm": 0.4,
        "tolerance_mm": 0.3,
        "wall_mm": 2.4,
    }


# ----------------------------
# Planning logic (questions + assumptions + safe defaults)
# ----------------------------
def plan_for(model_type: ModelType, prompt: str) -> PlanResponse:
    assumptions: List[str] = []
    questions: List[str] = []
    params: Dict[str, Any] = {}

    params.update(default_print_settings())
    triple = extract_triple_mm(prompt)
    nums = extract_numbers_mm(prompt)

    # Guardrails: be honest for unsupported prompts
    p = prompt.lower()
    if any(w in p for w in ["hand", "face", "human", "person", "anime", "character"]):
        return PlanResponse(
            model_type="box_with_lid",
            params=params,
            questions=["This app generates functional printable parts only. Pick a supported object from the list below (box with lid, phone stand, bracket, spacer, hook, etc.)."],
            assumptions=["Refused organic/character request to avoid fake output."],
        )

    # Boxes / containers
    if model_type == "box_open":
        if triple:
            L, W, H = triple
            params.update({"length_mm": clamp(L, 30, 350), "width_mm": clamp(W, 30, 350), "height_mm": clamp(H, 15, 300)})
            assumptions.append("Interpreted AxBxC as length x width x height.")
        else:
            params.update({"length_mm": 120, "width_mm": 80, "height_mm": 60})
            questions.append("Give box size like 120x80x60 mm (length x width x height).")
        params.update({"floor_mm": 2.4, "corner_radius_mm": 2.0})

    elif model_type == "box_with_lid":
        if triple:
            L, W, H = triple
            params.update({"length_mm": clamp(L, 30, 350), "width_mm": clamp(W, 30, 350), "height_mm": clamp(H, 20, 300)})
            assumptions.append("Interpreted AxBxC as length x width x height.")
        else:
            params.update({"length_mm": 120, "width_mm": 80, "height_mm": 60})
            questions.append("Give box size like 120x80x60 mm (length x width x height).")
        params.update({
            "floor_mm": 2.4,
            "lid_height_mm": 18,
            "lid_wall_mm": 2.4,
            "lip_depth_mm": 8,
            "corner_radius_mm": 2.0,
        })
        assumptions.append("Lid is friction fit with tolerance_mm.")

    elif model_type == "tray":
        if triple:
            L, W, H = triple
            params.update({"length_mm": clamp(L, 60, 400), "width_mm": clamp(W, 40, 400), "height_mm": clamp(H, 8, 60)})
            assumptions.append("Interpreted AxBxC as length x width x height.")
        else:
            params.update({"length_mm": 200, "width_mm": 120, "height_mm": 20})
            questions.append("Give tray size like 200x120x20 mm.")
        params.update({"floor_mm": 2.0, "corner_radius_mm": 3.0})

    elif model_type == "drawer_bin":
        if triple:
            L, W, H = triple
            params.update({"length_mm": clamp(L, 60, 400), "width_mm": clamp(W, 40, 400), "height_mm": clamp(H, 25, 250)})
            assumptions.append("Interpreted AxBxC as length x width x height.")
        else:
            params.update({"length_mm": 140, "width_mm": 90, "height_mm": 60})
            questions.append("Give bin size like 140x90x60 mm.")
        params.update({"floor_mm": 2.4, "corner_radius_mm": 6.0})

    elif model_type == "cyl_container":
        # expects diameter + height (first two numbers)
        if len(nums) >= 2:
            params.update({"diameter_mm": clamp(nums[0], 20, 250), "height_mm": clamp(nums[1], 20, 300)})
            assumptions.append("Used first number as diameter and second as height.")
        else:
            params.update({"diameter_mm": 80, "height_mm": 120})
            questions.append("Give cylinder size like 80mm 120mm (diameter height).")
        params.update({"floor_mm": 2.4})

    # Stands / holders
    elif model_type == "phone_stand":
        if triple:
            W, D, H = triple
            params.update({"width_mm": clamp(W, 60, 200), "depth_mm": clamp(D, 70, 250), "height_mm": clamp(H, 40, 140)})
            assumptions.append("Interpreted AxBxC as width x depth x height.")
        else:
            params.update({"width_mm": 90, "depth_mm": 120, "height_mm": 70})
        params.update({"angle_deg": 65, "lip_height_mm": 8, "slot_thickness_mm": 14, "base_thickness_mm": 8})
        if "case" in prompt.lower():
            questions.append("What is your phone thickness including case (mm)? If unsure, 14mm is ok.")

    elif model_type == "tablet_stand":
        if triple:
            W, D, H = triple
            params.update({"width_mm": clamp(W, 120, 260), "depth_mm": clamp(D, 120, 320), "height_mm": clamp(H, 60, 180)})
            assumptions.append("Interpreted AxBxC as width x depth x height.")
        else:
            params.update({"width_mm": 160, "depth_mm": 220, "height_mm": 110})
        params.update({"angle_deg": 68, "lip_height_mm": 10, "slot_thickness_mm": 18, "base_thickness_mm": 10})
        assumptions.append("Tablet stand uses thicker base by default.")

    elif model_type == "desk_nameplate":
        if triple:
            L, W, T = triple
            params.update({"length_mm": clamp(L, 80, 250), "height_mm": clamp(W, 25, 90), "thickness_mm": clamp(T, 3, 15)})
            assumptions.append("Interpreted AxBxC as length x height x thickness.")
        else:
            params.update({"length_mm": 160, "height_mm": 50, "thickness_mm": 8})
            questions.append("Give nameplate size like 160x50x8 mm (length x height x thickness).")
        params.update({"angle_deg": 18})

    # Brackets / mounts
    elif model_type == "l_bracket":
        if triple:
            A, B, T = triple
            params.update({"leg_a_mm": clamp(A, 20, 250), "leg_b_mm": clamp(B, 20, 250), "thickness_mm": clamp(T, 2, 20)})
            assumptions.append("Interpreted AxBxC as legA x legB x thickness.")
        else:
            params.update({"leg_a_mm": 60, "leg_b_mm": 60, "thickness_mm": 5})
            questions.append("Give bracket size like 60x60x5 mm (legA x legB x thickness).")
        params.update({"width_mm": 25, "hole_d_mm": 5, "hole_offset_mm": 15, "holes_per_leg": 2, "fillet_mm": 1.5})

    elif model_type == "corner_brace":
        if triple:
            A, B, T = triple
            params.update({"leg_a_mm": clamp(A, 30, 250), "leg_b_mm": clamp(B, 30, 250), "thickness_mm": clamp(T, 2, 20)})
            assumptions.append("Interpreted AxBxC as legA x legB x thickness.")
        else:
            params.update({"leg_a_mm": 70, "leg_b_mm": 70, "thickness_mm": 5})
            questions.append("Give brace size like 70x70x5 mm (legA x legB x thickness).")
        params.update({"width_mm": 25, "hole_d_mm": 5, "hole_offset_mm": 18, "holes_per_leg": 2, "gusset_mm": 8, "fillet_mm": 1.2})

    elif model_type == "flat_plate":
        if triple:
            L, W, T = triple
            params.update({"length_mm": clamp(L, 30, 350), "width_mm": clamp(W, 20, 300), "thickness_mm": clamp(T, 2, 20)})
            assumptions.append("Interpreted AxBxC as length x width x thickness.")
        else:
            params.update({"length_mm": 120, "width_mm": 60, "thickness_mm": 4})
            questions.append("Give plate size like 120x60x4 mm.")
        params.update({"hole_d_mm": 5, "hole_margin_mm": 12, "hole_pattern": "corners"})  # corners|none

    # Hardware
    elif model_type == "spacer":
        if len(nums) >= 3:
            params.update({"inner_d_mm": clamp(nums[0], 1, 60), "outer_d_mm": clamp(nums[1], 3, 120), "height_mm": clamp(nums[2], 1, 120)})
            assumptions.append("Used first 3 dimensions as inner_d, outer_d, height.")
        else:
            params.update({"inner_d_mm": 5, "outer_d_mm": 12, "height_mm": 10})
            questions.append("Give spacer like 5mm 12mm 10mm (ID OD height).")
        params.update({"chamfer_mm": 0.6})

    elif model_type == "washer":
        if len(nums) >= 3:
            params.update({"inner_d_mm": clamp(nums[0], 1, 60), "outer_d_mm": clamp(nums[1], 3, 120), "thickness_mm": clamp(nums[2], 0.8, 12)})
            assumptions.append("Used first 3 dimensions as inner_d, outer_d, thickness.")
        else:
            params.update({"inner_d_mm": 5, "outer_d_mm": 12, "thickness_mm": 2})
            questions.append("Give washer like 5mm 12mm 2mm (ID OD thickness).")
        params.update({"chamfer_mm": 0.4})

    elif model_type == "standoff":
        if len(nums) >= 2:
            params.update({"diameter_mm": clamp(nums[0], 3, 80), "height_mm": clamp(nums[1], 2, 120)})
            assumptions.append("Used first number as diameter and second as height.")
        else:
            params.update({"diameter_mm": 10, "height_mm": 20})
            questions.append("Give standoff like 10mm 20mm (diameter height).")

    # Clips / grommets
    elif model_type == "cable_clip":
        # expects cable_d and clip_width (first two nums)
        if len(nums) >= 2:
            params.update({"cable_d_mm": clamp(nums[0], 2, 25), "clip_width_mm": clamp(nums[1], 8, 40)})
            assumptions.append("Used first number as cable diameter and second as clip width.")
        else:
            params.update({"cable_d_mm": 6, "clip_width_mm": 12})
            questions.append("Give clip like 6mm 12mm (cable diameter, clip width).")
        params.update({"thickness_mm": 3.0, "gap_mm": 1.0})

    elif model_type == "cable_grommet":
        # expects OD, ID, thickness
        if len(nums) >= 3:
            params.update({"outer_d_mm": clamp(nums[0], 20, 120), "inner_d_mm": clamp(nums[1], 10, 100), "thickness_mm": clamp(nums[2], 2, 20)})
            assumptions.append("Used first 3 dimensions as outer_d, inner_d, thickness.")
        else:
            params.update({"outer_d_mm": 50, "inner_d_mm": 35, "thickness_mm": 5})
            questions.append("Give grommet like 50mm 35mm 5mm (OD ID thickness).")

    # Hooks
    elif model_type == "wall_hook":
        params.update({"plate_w_mm": 50, "plate_h_mm": 70, "plate_t_mm": 5, "hook_t_mm": 8, "hook_reach_mm": 35, "hook_drop_mm": 45, "screw_hole_d_mm": 5, "screw_hole_spacing_mm": 40})
        if triple:
            W, H, T = triple
            params["plate_w_mm"] = clamp(W, 30, 160)
            params["plate_h_mm"] = clamp(H, 40, 220)
            params["plate_t_mm"] = clamp(T, 3, 18)
            assumptions.append("Interpreted AxBxC as plate width x plate height x plate thickness.")

    # Simple shapes / toys
    elif model_type == "coin":
        if len(nums) >= 2:
            params.update({"diameter_mm": clamp(nums[0], 8, 150), "thickness_mm": clamp(nums[1], 0.8, 20)})
            assumptions.append("Used first number as diameter and second as thickness.")
        else:
            params.update({"diameter_mm": 30, "thickness_mm": 2})
            questions.append("Give coin like 30mm 2mm (diameter thickness).")

    elif model_type == "fidget_coin":
        if len(nums) >= 2:
            params.update({"diameter_mm": clamp(nums[0], 15, 150), "thickness_mm": clamp(nums[1], 1.2, 20)})
            assumptions.append("Used first number as diameter and second as thickness.")
        else:
            params.update({"diameter_mm": 35, "thickness_mm": 3})
            questions.append("Give fidget coin like 35mm 3mm (diameter thickness).")
        params.update({"grooves": 12, "groove_depth_mm": 0.6})

    elif model_type == "keychain_tag":
        if triple:
            L, W, T = triple
            params.update({"length_mm": clamp(L, 30, 120), "width_mm": clamp(W, 15, 80), "thickness_mm": clamp(T, 2, 12)})
            assumptions.append("Interpreted AxBxC as length x width x thickness.")
        else:
            params.update({"length_mm": 60, "width_mm": 25, "thickness_mm": 3})
            questions.append("Give tag like 60x25x3 mm.")
        params.update({"corner_radius_mm": 4.0, "hole_d_mm": 5.0, "hole_margin_mm": 8.0})

    else:
        raise HTTPException(400, "Unsupported template")

    # Common sanity clamps
    params["tolerance_mm"] = clamp(float(params.get("tolerance_mm", 0.3)), 0.1, 0.8)
    params["wall_mm"] = clamp(float(params.get("wall_mm", 2.4)), 1.2, 6.0)

    return PlanResponse(
        model_type=model_type,
        params=params,
        questions=questions[:3],
        assumptions=assumptions[:8],
    )


# ----------------------------
# Optional: Ollama refinement
# ----------------------------
def ollama_refine(prompt: str, current: PlanResponse) -> PlanResponse:
    try:
        schema = {
            "model_type": "one of supported model types",
            "params": "object (mm units)",
            "questions": ["string"],
            "assumptions": ["string"],
        }
        instruction = f"""
Return ONLY valid JSON. No extra text.
Schema:
{json.dumps(schema, indent=2)}
Rules:
- Use mm units
- Keep parameters realistic for FDM printing
- If unclear, ask 1-2 short questions
Prompt: {prompt}
Supported model_type values:
{[c["model_type"] for c in CAPABILITIES]}

Current plan:
{current.model_dump_json()}
"""
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.1:8b", "prompt": instruction, "stream": False},
            timeout=20,
        )
        if r.status_code != 200:
            return current

        text = (r.json().get("response") or "").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start == -1 or end == -1:
                return current
            data = json.loads(text[start : end + 1])

        allowed = {c["model_type"] for c in CAPABILITIES}
        mt = data.get("model_type", current.model_type)
        if mt not in allowed:
            mt = current.model_type

        params = current.params.copy()
        if isinstance(data.get("params"), dict):
            for k, v in data["params"].items():
                fv = safe_float(v)
                if fv is not None:
                    params[k] = fv

        questions = data.get("questions", current.questions)
        assumptions = data.get("assumptions", current.assumptions)

        return PlanResponse(
            model_type=mt,  # type: ignore
            params=params,
            questions=[str(x) for x in questions][:3] if isinstance(questions, list) else current.questions,
            assumptions=[str(x) for x in assumptions][:8] if isinstance(assumptions, list) else current.assumptions,
        )
    except Exception:
        return current


# ----------------------------
# CadQuery generators
# ----------------------------
def cq_open_box(p: Dict[str, Any]) -> cq.Workplane:
    L, W, H = float(p["length_mm"]), float(p["width_mm"]), float(p["height_mm"])
    wall, floor = float(p["wall_mm"]), float(p["floor_mm"])
    r = float(p.get("corner_radius_mm", 0.0))

    outer = cq.Workplane("XY").rect(L, W).extrude(H)
    if r > 0:
        outer = outer.edges("|Z").fillet(min(r, min(L, W) * 0.12))

    inner_L, inner_W = max(L - 2 * wall, 2), max(W - 2 * wall, 2)
    inner_H = max(H - floor, 1)
    inner = cq.Workplane("XY").rect(inner_L, inner_W).extrude(inner_H).translate((0, 0, floor))
    return outer.cut(inner)

def cq_box_with_lid(p: Dict[str, Any]) -> cq.Workplane:
    L, W, H = float(p["length_mm"]), float(p["width_mm"]), float(p["height_mm"])
    wall, floor = float(p["wall_mm"]), float(p["floor_mm"])
    r = float(p.get("corner_radius_mm", 0.0))
    tol = float(p["tolerance_mm"])

    base = cq_open_box(p)

    lid_h = float(p["lid_height_mm"])
    lid_wall = float(p["lid_wall_mm"])
    lip = float(p["lip_depth_mm"])

    lid_outer_L = L + 2 * lid_wall
    lid_outer_W = W + 2 * lid_wall

    lid_outer = cq.Workplane("XY").rect(lid_outer_L, lid_outer_W).extrude(lid_h).translate((0, 0, H + 2))
    if r > 0:
        lid_outer = lid_outer.edges("|Z").fillet(min(r, min(lid_outer_L, lid_outer_W) * 0.12))

    fit_L, fit_W = L + tol, W + tol
    cavity = cq.Workplane("XY").rect(fit_L, fit_W).extrude(lid_h - 1).translate((0, 0, H + 3))

    stop_L, stop_W = fit_L - 2 * lip, fit_W - 2 * lip
    if stop_L > 6 and stop_W > 6:
        stop_cut = cq.Workplane("XY").rect(stop_L, stop_W).extrude(lid_h).translate((0, 0, H + 2))
        lid = lid_outer.cut(cavity).cut(stop_cut)
    else:
        lid = lid_outer.cut(cavity)

    return base.union(lid)

def cq_tray(p: Dict[str, Any]) -> cq.Workplane:
    # tray is basically a shallow open box with thinner floor
    return cq_open_box(p)

def cq_drawer_bin(p: Dict[str, Any]) -> cq.Workplane:
    # bin is open box with larger corner radius
    return cq_open_box(p)

def cq_cyl_container(p: Dict[str, Any]) -> cq.Workplane:
    d, h = float(p["diameter_mm"]), float(p["height_mm"])
    wall, floor = float(p["wall_mm"]), float(p["floor_mm"])
    outer = cq.Workplane("XY").circle(d / 2).extrude(h)
    inner_d = max(d - 2 * wall, 2)
    inner_h = max(h - floor, 1)
    inner = cq.Workplane("XY").circle(inner_d / 2).extrude(inner_h).translate((0, 0, floor))
    return outer.cut(inner)

def cq_phone_stand(p: Dict[str, Any]) -> cq.Workplane:
    W, D, H = float(p["width_mm"]), float(p["depth_mm"]), float(p["height_mm"])
    angle = float(p["angle_deg"])
    lip_h = float(p["lip_height_mm"])
    base_t = float(p["base_thickness_mm"])

    base = cq.Workplane("XY").rect(W, D).extrude(base_t)

    support = cq.Workplane("XY").rect(W, D * 0.65).extrude(H).translate((0, D * 0.175, base_t))
    cutter = (
        cq.Workplane("XY")
        .rect(W * 2, D * 2)
        .extrude(H * 2)
        .translate((0, D * 0.3, base_t + H * 0.2))
        .rotate((0, 0, 0), (1, 0, 0), angle)
    )
    support = support.cut(cutter)
    body = base.union(support)

    slot_w = W * 0.9
    slot_d = max(D * 0.22, 18)
    slot_h = base_t + lip_h + 8
    slot_cut = cq.Workplane("XY").rect(slot_w, slot_d).extrude(slot_h).translate((0, -D * 0.35, 0))
    body = body.cut(slot_cut)

    lip = cq.Workplane("XY").rect(W, slot_d).extrude(lip_h).translate((0, -D * 0.35, base_t))
    return body.union(lip)

def cq_tablet_stand(p: Dict[str, Any]) -> cq.Workplane:
    # reuse phone stand but chunkier
    return cq_phone_stand(p)

def cq_desk_nameplate(p: Dict[str, Any]) -> cq.Workplane:
    L, H, T = float(p["length_mm"]), float(p["height_mm"]), float(p["thickness_mm"])
    ang = float(p["angle_deg"])

    plate = cq.Workplane("XY").rect(L, H).extrude(T)
    # create wedge base to tilt
    base = cq.Workplane("XY").rect(L, H).extrude(T * 0.8).translate((0, 0, -T * 0.8))
    wedge_cutter = (
        cq.Workplane("XY")
        .rect(L * 2, H * 2)
        .extrude(T * 3)
        .translate((0, 0, -T))
        .rotate((0, 0, 0), (0, 1, 0), ang)
    )
    base = base.cut(wedge_cutter)
    return plate.union(base)

def cq_l_bracket(p: Dict[str, Any]) -> cq.Workplane:
    A, B, T = float(p["leg_a_mm"]), float(p["leg_b_mm"]), float(p["thickness_mm"])
    W = float(p["width_mm"])
    hole_d = float(p["hole_d_mm"])
    off = float(p["hole_offset_mm"])
    n = int(p["holes_per_leg"])
    fil = float(p.get("fillet_mm", 0))

    # Build with boxes for reliability:
    # leg1: A (X) x W (Y) x T (Z), sitting on Z=0
    leg1 = cq.Workplane("XY").box(A, W, T, centered=(True, True, False))

    # leg2: T (X) x W (Y) x B (Z), sitting on Z=0, placed at +X end of leg1
    leg2 = cq.Workplane("XY").box(T, W, B, centered=(True, True, False)).translate((A / 2 - T / 2, 0, 0))

    br = leg1.union(leg2)

    # Holes on leg1 (top face >Z). Workplane is attached to the face, so hole() is valid.
    if n >= 1:
        spacing1 = (A - 2 * off) / max(n - 1, 1)
        xs = [(-A / 2 + off + i * spacing1) for i in range(n)]
        br = br.faces(">Z").workplane().pushPoints([(x, 0) for x in xs]).hole(hole_d)

        # Holes on leg2 outer face (>X). On that face, workplane coords are (Y, Z).
        spacing2 = (B - 2 * off) / max(n - 1, 1)
        zs = [(-B / 2 + off + i * spacing2) for i in range(n)]
        br = br.faces(">X").workplane().pushPoints([(0, z) for z in zs]).hole(hole_d)

    # Optional fillet (keep small to avoid failures)
    if fil and fil > 0:
        br = br.edges().fillet(min(fil, 2.0))

    return br


def cq_corner_brace(p: Dict[str, Any]) -> cq.Workplane:
    # Start from the fixed L-bracket
    br = cq_l_bracket(p)

    A, B, T = float(p["leg_a_mm"]), float(p["leg_b_mm"]), float(p["thickness_mm"])
    W = float(p["width_mm"])
    gus = float(p.get("gusset_mm", 8))

    # Add a triangular gusset on the inside corner
    # Triangle in XZ, extruded along Y (width W)
    tri = (
        cq.Workplane("XZ")
        .polyline([(0, 0), (gus, 0), (0, gus)])
        .close()
        .extrude(W)
    )

    # Move gusset to inside corner region:
    # leg1 spans x: [-A/2, +A/2], leg2 starts near x=+A/2 - T
    # Place near the corner at x ~ (A/2 - T), z ~ 0
    tri = tri.translate((A / 2 - T - gus / 2, 0, gus / 2))

    return br.union(tri)

def cq_flat_plate(p: Dict[str, Any]) -> cq.Workplane:
    L, W, T = float(p["length_mm"]), float(p["width_mm"]), float(p["thickness_mm"])
    hole_d = float(p["hole_d_mm"])
    margin = float(p["hole_margin_mm"])
    pattern = str(p.get("hole_pattern", "corners"))

    plate = cq.Workplane("XY").rect(L, W).extrude(T)

    if pattern == "none":
        return plate

    # corners pattern
    pts = [
        (-L/2 + margin, -W/2 + margin),
        ( L/2 - margin, -W/2 + margin),
        (-L/2 + margin,  W/2 - margin),
        ( L/2 - margin,  W/2 - margin),
    ]
    plate = plate.faces(">Z").workplane().pushPoints(pts).hole(hole_d)
    return plate

def cq_spacer(p: Dict[str, Any]) -> cq.Workplane:
    ID, OD, H = float(p["inner_d_mm"]), float(p["outer_d_mm"]), float(p["height_mm"])
    cham = float(p.get("chamfer_mm", 0.0))

    if OD <= ID + 1.0:
        raise HTTPException(400, "Spacer OD must be larger than ID.")

    outer = cq.Workplane("XY").circle(OD / 2).extrude(H)
    inner = cq.Workplane("XY").circle(ID / 2).extrude(H)
    s = outer.cut(inner)

    if cham > 0:
        c = min(cham, 1.2)
        # Chamfer top and bottom edges (circular edges)
        try:
            s = s.edges(">Z").chamfer(c)
            s = s.edges("<Z").chamfer(c)
        except Exception:
            # If edge selection fails for any reason, skip chamfer rather than crashing
            pass

    return s


def cq_washer(p: Dict[str, Any]) -> cq.Workplane:
    ID, OD, T = float(p["inner_d_mm"]), float(p["outer_d_mm"]), float(p["thickness_mm"])
    cham = float(p.get("chamfer_mm", 0.0))

    if OD <= ID + 1.0:
        raise HTTPException(400, "Washer OD must be larger than ID.")

    outer = cq.Workplane("XY").circle(OD / 2).extrude(T)
    inner = cq.Workplane("XY").circle(ID / 2).extrude(T)
    s = outer.cut(inner)

    if cham > 0:
        c = min(cham, 1.2)
        try:
            s = s.edges(">Z").chamfer(c)
            s = s.edges("<Z").chamfer(c)
        except Exception:
            pass

    return s

def cq_standoff(p: Dict[str, Any]) -> cq.Workplane:
    d, h = float(p["diameter_mm"]), float(p["height_mm"])
    return cq.Workplane("XY").circle(d/2).extrude(h)

def cq_cable_clip(p: Dict[str, Any]) -> cq.Workplane:
    cd = float(p["cable_d_mm"])
    w = float(p["clip_width_mm"])
    t = float(p["thickness_mm"])
    gap = float(p["gap_mm"])

    # U shape: outer block minus inner block + top gap
    outer_r = (cd/2) + t
    inner_r = (cd/2) + gap

    outer = cq.Workplane("YZ").circle(outer_r).extrude(w)
    inner = cq.Workplane("YZ").circle(inner_r).extrude(w)

    clip = outer.cut(inner)

    # cut an opening slot
    slot = cq.Workplane("YZ").rect(outer_r*2, outer_r*2).extrude(w).translate((0, outer_r*0.8, 0))
    clip = clip.cut(slot)

    return clip

def cq_cable_grommet(p: Dict[str, Any]) -> cq.Workplane:
    OD, ID, T = float(p["outer_d_mm"]), float(p["inner_d_mm"]), float(p["thickness_mm"])
    if OD <= ID + 2.0:
        raise HTTPException(400, "Grommet OD must be larger than ID.")
    outer = cq.Workplane("XY").circle(OD/2).extrude(T)
    inner = cq.Workplane("XY").circle(ID/2).extrude(T)
    return outer.cut(inner)

def cq_wall_hook(p: Dict[str, Any]) -> cq.Workplane:
    pw = float(p["plate_w_mm"])
    ph = float(p["plate_h_mm"])
    pt = float(p["plate_t_mm"])
    ht = float(p["hook_t_mm"])
    reach = float(p["hook_reach_mm"])
    drop = float(p["hook_drop_mm"])
    hd = float(p["screw_hole_d_mm"])
    hs = float(p["screw_hole_spacing_mm"])

    plate = cq.Workplane("XY").rect(pw, ph).extrude(pt)
    plate = plate.faces(">Z").workplane().pushPoints([(0, -hs/2), (0, hs/2)]).hole(hd)

    path = cq.Workplane("XZ").polyline(
        [(pw/2, pt), (pw/2 + reach, pt), (pw/2 + reach, pt - drop)]
    ).wire()

    profile = cq.Workplane("YZ").circle(ht / 2)
    arm = profile.sweep(path)
    return plate.union(arm)

def cq_coin(p: Dict[str, Any]) -> cq.Workplane:
    d, t = float(p["diameter_mm"]), float(p["thickness_mm"])
    return cq.Workplane("XY").circle(d/2).extrude(t)

def cq_fidget_coin(p: Dict[str, Any]) -> cq.Workplane:
    d, t = float(p["diameter_mm"]), float(p["thickness_mm"])
    grooves = int(p["grooves"])
    depth = float(p["groove_depth_mm"])

    disc = cq.Workplane("XY").circle(d/2).extrude(t)

    # cut radial grooves on top face
    if grooves > 0 and depth > 0:
        top = disc.faces(">Z").workplane()
        for i in range(grooves):
            ang = (360.0 / grooves) * i
            groove = (
                cq.Workplane("XY")
                .rect(d * 0.08, d * 0.6)
                .extrude(depth)
                .translate((0, 0, t - depth))
                .rotate((0, 0, 0), (0, 0, 1), ang)
            )
            disc = disc.cut(groove)

    return disc

def cq_keychain_tag(p: Dict[str, Any]) -> cq.Workplane:
    L, W, T = float(p["length_mm"]), float(p["width_mm"]), float(p["thickness_mm"])
    r = float(p["corner_radius_mm"])
    hole_d = float(p["hole_d_mm"])
    margin = float(p["hole_margin_mm"])

    tag = cq.Workplane("XY").rect(L, W).extrude(T)
    if r > 0:
        tag = tag.edges("|Z").fillet(min(r, min(L, W) * 0.2))

    # hole near one end
    x = -L/2 + margin
    tag = tag.faces(">Z").workplane().pushPoints([(x, 0)]).hole(hole_d)
    return tag


GENERATORS: Dict[str, Any] = {
    "box_open": cq_open_box,
    "box_with_lid": cq_box_with_lid,
    "tray": cq_tray,
    "drawer_bin": cq_drawer_bin,
    "cyl_container": cq_cyl_container,

    "phone_stand": cq_phone_stand,
    "tablet_stand": cq_tablet_stand,
    "desk_nameplate": cq_desk_nameplate,

    "l_bracket": cq_l_bracket,
    "corner_brace": cq_corner_brace,
    "flat_plate": cq_flat_plate,

    "spacer": cq_spacer,
    "washer": cq_washer,
    "standoff": cq_standoff,

    "cable_clip": cq_cable_clip,
    "cable_grommet": cq_cable_grommet,

    "wall_hook": cq_wall_hook,

    "coin": cq_coin,
    "fidget_coin": cq_fidget_coin,
    "keychain_tag": cq_keychain_tag,
}


# ----------------------------
# Export helpers
# ----------------------------
def export_stl_and_glb(solid: cq.Workplane, file_id: str) -> None:
    stl_path = os.path.join(OUT_DIR, f"{file_id}.stl")
    glb_path = os.path.join(OUT_DIR, f"{file_id}.glb")

    exporters.export(solid, stl_path)

    mesh = trimesh.load(stl_path)
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = mesh.dump(concatenate=True)

    mesh.apply_translation(-mesh.centroid)
    trimesh.Scene(mesh).export(glb_path)


# ----------------------------
# Routes
# ----------------------------
@app.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities():
    return CapabilitiesResponse(
        app_name="CadrixAI",
        tagline="Intent-driven parametric CAD for 3D printing",
        categories=CATEGORIES,
        supported=[CapabilityItem(**c) for c in CAPABILITIES],
        not_supported=NOT_SUPPORTED,
    )

@app.post("/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
    mt = guess_template(req.prompt)
    base = plan_for(mt, req.prompt)

    if req.use_ollama:
        base = ollama_refine(req.prompt, base)

    return base

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    # Trust the plan. Never re-guess.
    if req.model_type not in GENERATORS:
        raise HTTPException(400, "Unsupported model_type")

    file_id = f"mdl_{uuid.uuid4().hex[:12]}"

    gen = GENERATORS[req.model_type]
    try:
        solid = gen(req.params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Generator failed: {e}")

    export_stl_and_glb(solid, file_id)

    return GenerateResponse(
        model_type=req.model_type,
        file_id=file_id,
        stl_download_url=f"http://localhost:8000/files/{file_id}.stl",
        preview_glb_url=f"http://localhost:8000/files/{file_id}.glb",
        params_used=req.params,
    )

@app.get("/files/{filename}")
def get_file(filename: str):
    safe = re.fullmatch(r"[A-Za-z0-9_]+\.(stl|glb)", filename)
    if not safe:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = os.path.join(OUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "model/stl" if filename.endswith(".stl") else "model/gltf-binary"
    return FileResponse(path, media_type=media_type, filename=filename)
