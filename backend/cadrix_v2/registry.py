from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from cadrix_v2.schemas import CapabilityItemV2, ParameterDefinition


def num_param(
    key: str,
    label: str,
    description: str,
    *,
    required: bool = False,
    default: Any = None,
    minimum: float | None = None,
    maximum: float | None = None,
    unit: str | None = "mm",
) -> ParameterDefinition:
    return ParameterDefinition(
        key=key,
        label=label,
        description=description,
        type="number",
        required=required,
        default=default,
        minimum=minimum,
        maximum=maximum,
        unit=unit,
    )


def int_param(
    key: str,
    label: str,
    description: str,
    *,
    required: bool = False,
    default: Any = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> ParameterDefinition:
    return ParameterDefinition(
        key=key,
        label=label,
        description=description,
        type="integer",
        required=required,
        default=default,
        minimum=minimum,
        maximum=maximum,
        unit=None,
    )


def bool_param(
    key: str,
    label: str,
    description: str,
    *,
    default: Any = False,
) -> ParameterDefinition:
    return ParameterDefinition(
        key=key,
        label=label,
        description=description,
        type="boolean",
        required=False,
        default=default,
        unit=None,
    )


@dataclass(frozen=True)
class ModelSpec:
    model_type: str
    title: str
    category: str
    description: str
    keywords: tuple[str, ...]
    examples: tuple[str, ...]
    required_parameters: tuple[ParameterDefinition, ...]
    optional_parameters: tuple[ParameterDefinition, ...]
    defaults: Dict[str, Any]
    size_presets: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    implemented: bool = True
    todo: Optional[str] = None

    def capability_item(self) -> CapabilityItemV2:
        return CapabilityItemV2(
            model_type=self.model_type,
            title=self.title,
            description=self.description,
            category=self.category,
            implemented=self.implemented,
            examples=list(self.examples),
            required_parameters=list(self.required_parameters),
            optional_parameters=list(self.optional_parameters),
            todo=self.todo,
        )

    @property
    def parameter_definitions(self) -> list[ParameterDefinition]:
        return [*self.required_parameters, *self.optional_parameters]


HIGHLIGHTED_BUILDS = [
    "Phone Stand",
    "Box with Lid",
    "Cable Clip",
    "Gear",
    "PCB Enclosure",
    "Wall Hook",
    "Drawer Divider",
    "Bottle Holder",
    "Desk Organizer",
    "Laptop Stand",
    "Remote Holder",
    "Card Holder",
    "Hinge",
    "Nut and Bolt Basic",
    "Spacer",
    "Test Tube Rack",
    "Sensor Mount",
    "Ventilation Box",
    "Stackable Box",
    "Gridfinity Bin",
    "Interlocking Panel",
    "Snap-Fit Box",
]


MODEL_SPECS = [
    ModelSpec(
        model_type="phone_stand",
        title="Phone Stand",
        category="Custom-fit",
        description="A print-ready desk stand with tunable width, support angle, front lip, and optional cable slot.",
        keywords=("phone stand", "phone holder", "phone dock", "stand for phone"),
        examples=(
            "Make a phone stand for a 75mm wide phone with a 20 degree angle and cable hole.",
            "Large phone stand with rounded edges and a charger slot.",
        ),
        required_parameters=(
            num_param("phone_width_mm", "Phone Width", "Target phone width.", required=True, default=75, minimum=55, maximum=110),
            num_param("angle_degrees", "Support Angle", "Back support angle from the build plate.", required=True, default=68, minimum=50, maximum=80, unit="deg"),
        ),
        optional_parameters=(
            num_param("device_thickness_mm", "Device Thickness", "Phone thickness including case.", default=12, minimum=6, maximum=25),
            num_param("base_thickness_mm", "Base Thickness", "Base thickness for strength.", default=6, minimum=3, maximum=12),
            num_param("front_lip_mm", "Front Lip", "Front lip height that catches the phone.", default=12, minimum=4, maximum=25),
            num_param("back_support_height_mm", "Back Height", "Height of the support surface.", default=110, minimum=60, maximum=180),
            num_param("side_margin_mm", "Side Margin", "Margin around the device width.", default=8, minimum=3, maximum=20),
            bool_param("cable_slot", "Cable Slot", "Cuts a slot for a charging cable.", default=False),
            num_param("cable_slot_width_mm", "Cable Slot Width", "Width of the cable slot.", default=14, minimum=6, maximum=28),
            bool_param("rounded_edges", "Rounded Edges", "Adds safe fillets where possible.", default=True),
            num_param("edge_radius_mm", "Edge Radius", "Fillet radius for rounded edges.", default=2, minimum=0.5, maximum=5),
            num_param("wall_thickness_mm", "Wall Thickness", "Support thickness for FDM printing.", default=3, minimum=1.2, maximum=8),
            num_param("tolerance_mm", "Tolerance", "Clearance allowance for fit-sensitive features.", default=0.4, minimum=0.2, maximum=1.0),
        ),
        defaults={
            "phone_width_mm": 75,
            "angle_degrees": 68,
            "device_thickness_mm": 12,
            "base_thickness_mm": 6,
            "front_lip_mm": 12,
            "back_support_height_mm": 110,
            "side_margin_mm": 8,
            "cable_slot": False,
            "cable_slot_width_mm": 14,
            "rounded_edges": True,
            "edge_radius_mm": 2,
            "wall_thickness_mm": 3,
            "tolerance_mm": 0.4,
        },
        size_presets={
            "small": {"phone_width_mm": 68, "back_support_height_mm": 95},
            "medium": {"phone_width_mm": 75, "back_support_height_mm": 110},
            "large": {"phone_width_mm": 88, "back_support_height_mm": 130},
        },
    ),
    ModelSpec(
        model_type="box_with_lid",
        title="Box with Lid",
        category="Custom-fit",
        description="A storage box with printable wall thickness, lid clearance, and optional snap-fit lip.",
        keywords=("box with lid", "lid box", "container with lid", "storage box"),
        examples=(
            "Box with lid 120x80x60 mm with 0.4mm clearance.",
            "Large snap fit box for electronics.",
        ),
        required_parameters=(
            num_param("length_mm", "Length", "Outer box length.", required=True, default=120, minimum=30, maximum=300),
            num_param("width_mm", "Width", "Outer box width.", required=True, default=80, minimum=30, maximum=250),
            num_param("height_mm", "Height", "Outer box height.", required=True, default=60, minimum=20, maximum=250),
        ),
        optional_parameters=(
            num_param("wall_thickness_mm", "Wall Thickness", "Wall thickness for the base shell.", default=3, minimum=1.2, maximum=8),
            num_param("floor_thickness_mm", "Floor Thickness", "Floor thickness for the base shell.", default=3, minimum=1.2, maximum=10),
            num_param("lid_height_mm", "Lid Height", "Height of the removable lid.", default=18, minimum=8, maximum=40),
            num_param("lid_clearance_mm", "Lid Clearance", "Fit clearance between the base and lid.", default=0.4, minimum=0.2, maximum=1.2),
            bool_param("snap_fit_lip", "Snap-Fit Lip", "Adds a simple retaining lip inside the lid.", default=False),
            bool_param("rounded_edges", "Rounded Edges", "Rounds the outer vertical edges.", default=True),
            num_param("corner_radius_mm", "Corner Radius", "Outer corner radius.", default=2, minimum=0, maximum=12),
            num_param("tolerance_mm", "Tolerance", "Shared print tolerance hint.", default=0.4, minimum=0.2, maximum=1.0),
        ),
        defaults={
            "length_mm": 120,
            "width_mm": 80,
            "height_mm": 60,
            "wall_thickness_mm": 3,
            "floor_thickness_mm": 3,
            "lid_height_mm": 18,
            "lid_clearance_mm": 0.4,
            "snap_fit_lip": False,
            "rounded_edges": True,
            "corner_radius_mm": 2,
            "tolerance_mm": 0.4,
        },
        size_presets={
            "small": {"length_mm": 90, "width_mm": 60, "height_mm": 45},
            "medium": {"length_mm": 120, "width_mm": 80, "height_mm": 60},
            "large": {"length_mm": 160, "width_mm": 110, "height_mm": 80},
        },
    ),
    ModelSpec(
        model_type="cable_clip",
        title="Cable Clip",
        category="Functional household",
        description="A clip sized around a cable diameter with optional mounting base and screw hole.",
        keywords=("cable clip", "wire clip", "cord clip", "clip for cable"),
        examples=(
            "Cable clip for 6mm cable with mounting base and screw hole.",
            "Small wire clip with a 2mm opening gap.",
        ),
        required_parameters=(
            num_param("cable_diameter_mm", "Cable Diameter", "Target cable diameter.", required=True, default=6, minimum=2, maximum=25),
        ),
        optional_parameters=(
            num_param("clip_width_mm", "Clip Width", "Width of the clip body.", default=12, minimum=8, maximum=50),
            num_param("wall_thickness_mm", "Wall Thickness", "Material thickness around the clip.", default=3, minimum=1.2, maximum=8),
            num_param("opening_gap_mm", "Opening Gap", "Gap that lets the cable snap in.", default=1.5, minimum=0.6, maximum=6),
            bool_param("mounting_base", "Mounting Base", "Adds a flat base for mounting.", default=False),
            bool_param("screw_hole", "Screw Hole", "Cuts a screw hole through the mounting base.", default=False),
            num_param("base_length_mm", "Base Length", "Length of the optional mounting base.", default=24, minimum=12, maximum=60),
            num_param("base_thickness_mm", "Base Thickness", "Thickness of the optional mounting base.", default=3, minimum=1.2, maximum=8),
            num_param("screw_hole_diameter_mm", "Screw Hole Diameter", "Mounting screw hole diameter.", default=4.2, minimum=2.5, maximum=8),
            num_param("tolerance_mm", "Tolerance", "Shared print tolerance hint.", default=0.35, minimum=0.2, maximum=1.0),
        ),
        defaults={
            "cable_diameter_mm": 6,
            "clip_width_mm": 12,
            "wall_thickness_mm": 3,
            "opening_gap_mm": 1.5,
            "mounting_base": False,
            "screw_hole": False,
            "base_length_mm": 24,
            "base_thickness_mm": 3,
            "screw_hole_diameter_mm": 4.2,
            "tolerance_mm": 0.35,
        },
        size_presets={
            "small": {"cable_diameter_mm": 4, "clip_width_mm": 10},
            "medium": {"cable_diameter_mm": 6, "clip_width_mm": 12},
            "large": {"cable_diameter_mm": 10, "clip_width_mm": 16},
        },
    ),
    ModelSpec(
        model_type="simple_gear",
        title="Gear",
        category="Mechanical",
        description="A simple approximated spur gear with configurable tooth count, diameter, thickness, and bore.",
        keywords=("gear", "spur gear", "simple gear"),
        examples=(
            "Simple gear with 24 teeth, 40mm diameter, and 5mm bore.",
            "Large spur gear for a demo mechanism.",
        ),
        required_parameters=(
            int_param("tooth_count", "Tooth Count", "Number of gear teeth.", required=True, default=24, minimum=8, maximum=120),
        ),
        optional_parameters=(
            num_param("outer_diameter_mm", "Outer Diameter", "Overall gear diameter.", default=40, minimum=12, maximum=220),
            num_param("thickness_mm", "Thickness", "Gear thickness.", default=8, minimum=2, maximum=40),
            num_param("bore_diameter_mm", "Bore Diameter", "Center bore diameter.", default=5, minimum=1, maximum=80),
            num_param("hub_diameter_mm", "Hub Diameter", "Optional center hub diameter.", default=14, minimum=0, maximum=120),
            num_param("hub_thickness_mm", "Hub Thickness", "Optional center hub thickness.", default=10, minimum=0, maximum=40),
            num_param("tolerance_mm", "Tolerance", "Shared print tolerance hint.", default=0.3, minimum=0.15, maximum=1.0),
        ),
        defaults={
            "tooth_count": 24,
            "outer_diameter_mm": 40,
            "thickness_mm": 8,
            "bore_diameter_mm": 5,
            "hub_diameter_mm": 14,
            "hub_thickness_mm": 10,
            "tolerance_mm": 0.3,
        },
        size_presets={
            "small": {"tooth_count": 18, "outer_diameter_mm": 28},
            "medium": {"tooth_count": 24, "outer_diameter_mm": 40},
            "large": {"tooth_count": 32, "outer_diameter_mm": 58},
        },
    ),
    ModelSpec(
        model_type="pcb_enclosure",
        title="PCB Enclosure",
        category="Engineering/lab",
        description="A board-fit enclosure with standoffs, screw holes, ventilation slots, and a removable lid.",
        keywords=("pcb enclosure", "electronics box", "sensor enclosure", "board enclosure", "pcb case"),
        examples=(
            "PCB enclosure for an 80x50 mm board with ventilation slots.",
            "Large electronics enclosure with screw holes and removable lid.",
        ),
        required_parameters=(
            num_param("board_length_mm", "Board Length", "PCB length.", required=True, default=80, minimum=20, maximum=250),
            num_param("board_width_mm", "Board Width", "PCB width.", required=True, default=50, minimum=20, maximum=200),
        ),
        optional_parameters=(
            num_param("board_thickness_mm", "Board Thickness", "PCB thickness.", default=1.6, minimum=0.8, maximum=4),
            num_param("wall_thickness_mm", "Wall Thickness", "Outer wall thickness.", default=3, minimum=1.2, maximum=8),
            num_param("floor_thickness_mm", "Floor Thickness", "Base floor thickness.", default=3, minimum=1.2, maximum=10),
            num_param("enclosure_height_mm", "Enclosure Height", "Internal enclosure height below the lid.", default=25, minimum=10, maximum=120),
            num_param("board_clearance_mm", "Board Clearance", "Clearance around the board perimeter.", default=1.2, minimum=0.5, maximum=5),
            num_param("standoff_height_mm", "Standoff Height", "Height of PCB standoff posts.", default=6, minimum=2, maximum=20),
            num_param("standoff_diameter_mm", "Standoff Diameter", "Diameter of PCB standoff posts.", default=8, minimum=4, maximum=18),
            bool_param("screw_holes", "Screw Holes", "Adds screw holes to standoffs and the lid.", default=True),
            num_param("screw_hole_diameter_mm", "Screw Hole Diameter", "Diameter of the enclosure screw holes.", default=3, minimum=2, maximum=6),
            bool_param("ventilation_slots", "Ventilation Slots", "Cuts simple ventilation slots into the lid.", default=True),
            bool_param("removable_lid", "Removable Lid", "Exports a separate lid component.", default=True),
            num_param("lid_height_mm", "Lid Height", "Outer lid height.", default=10, minimum=6, maximum=30),
            num_param("tolerance_mm", "Tolerance", "Shared print tolerance hint.", default=0.4, minimum=0.2, maximum=1.2),
        ),
        defaults={
            "board_length_mm": 80,
            "board_width_mm": 50,
            "board_thickness_mm": 1.6,
            "wall_thickness_mm": 3,
            "floor_thickness_mm": 3,
            "enclosure_height_mm": 25,
            "board_clearance_mm": 1.2,
            "standoff_height_mm": 6,
            "standoff_diameter_mm": 8,
            "screw_holes": True,
            "screw_hole_diameter_mm": 3,
            "ventilation_slots": True,
            "removable_lid": True,
            "lid_height_mm": 10,
            "tolerance_mm": 0.4,
        },
        size_presets={
            "small": {"board_length_mm": 60, "board_width_mm": 40},
            "medium": {"board_length_mm": 80, "board_width_mm": 50},
            "large": {"board_length_mm": 100, "board_width_mm": 70},
        },
    ),
    ModelSpec(
        model_type="wall_hook",
        title="Wall Hook",
        category="Functional household",
        description="A screw-mount hook with a back plate and rounded arm for bags, cables, or lightweight tools.",
        keywords=("wall hook", "hook", "hanger"),
        examples=(
            "Wall hook 50x70x35 mm with 5mm screw holes.",
            "Large wall hook with 40mm reach.",
        ),
        required_parameters=(
            num_param("plate_width_mm", "Plate Width", "Width of the wall plate.", required=True, default=50, minimum=25, maximum=120),
            num_param("plate_height_mm", "Plate Height", "Height of the wall plate.", required=True, default=70, minimum=35, maximum=160),
            num_param("hook_depth_mm", "Hook Depth", "Horizontal reach of the hook arm.", required=True, default=35, minimum=15, maximum=90),
        ),
        optional_parameters=(
            num_param("plate_thickness_mm", "Plate Thickness", "Thickness of the mounting plate.", default=6, minimum=3, maximum=12),
            num_param("hook_diameter_mm", "Hook Diameter", "Diameter of the rounded hook arm.", default=10, minimum=4, maximum=20),
            num_param("hook_drop_mm", "Hook Drop", "Vertical drop near the tip of the hook.", default=24, minimum=8, maximum=80),
            num_param("screw_hole_diameter_mm", "Screw Hole Diameter", "Diameter of the mounting holes.", default=5, minimum=3, maximum=8),
            num_param("screw_hole_spacing_mm", "Screw Hole Spacing", "Center-to-center spacing of the plate holes.", default=40, minimum=18, maximum=100),
        ),
        defaults={
            "plate_width_mm": 50,
            "plate_height_mm": 70,
            "hook_depth_mm": 35,
            "plate_thickness_mm": 6,
            "hook_diameter_mm": 10,
            "hook_drop_mm": 24,
            "screw_hole_diameter_mm": 5,
            "screw_hole_spacing_mm": 40,
        },
        size_presets={
            "small": {"plate_width_mm": 40, "plate_height_mm": 55, "hook_depth_mm": 28},
            "medium": {"plate_width_mm": 50, "plate_height_mm": 70, "hook_depth_mm": 35},
            "large": {"plate_width_mm": 70, "plate_height_mm": 95, "hook_depth_mm": 48},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="drawer_divider",
        title="Drawer Divider",
        category="Functional household",
        description="A freestanding divider with a stabilizing base for drawers, trays, and bins.",
        keywords=("drawer divider", "divider", "drawer organizer"),
        examples=(
            "Drawer divider 150x40 mm with 24mm base width.",
            "Large drawer divider 220mm long.",
        ),
        required_parameters=(
            num_param("length_mm", "Length", "Overall divider length.", required=True, default=150, minimum=40, maximum=320),
            num_param("height_mm", "Height", "Height of the vertical divider wall.", required=True, default=40, minimum=20, maximum=120),
        ),
        optional_parameters=(
            num_param("thickness_mm", "Thickness", "Thickness of the divider wall.", default=3, minimum=1.2, maximum=8),
            num_param("base_width_mm", "Base Width", "Width of the stabilizing foot at the bottom.", default=24, minimum=10, maximum=80),
            num_param("foot_height_mm", "Foot Height", "Height of the stabilizing base section.", default=5, minimum=2, maximum=20),
            num_param("tolerance_mm", "Tolerance", "Shared fit allowance for drawer slots or bins.", default=0.3, minimum=0.15, maximum=1.0),
        ),
        defaults={
            "length_mm": 150,
            "height_mm": 40,
            "thickness_mm": 3,
            "base_width_mm": 24,
            "foot_height_mm": 5,
            "tolerance_mm": 0.3,
        },
        size_presets={
            "small": {"length_mm": 120, "height_mm": 32},
            "medium": {"length_mm": 150, "height_mm": 40},
            "large": {"length_mm": 220, "height_mm": 55},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="bottle_holder",
        title="Bottle Holder",
        category="Functional household",
        description="A wall-mountable cylindrical holder sized around a bottle, can, or similar container.",
        keywords=("bottle holder", "cup holder", "can holder"),
        examples=(
            "Bottle holder 70x90 mm with a mounting plate.",
            "Bottle holder for a 70mm bottle, 90mm tall.",
        ),
        required_parameters=(
            num_param("bottle_diameter_mm", "Bottle Diameter", "Target outside bottle diameter.", required=True, default=70, minimum=35, maximum=120),
            num_param("holder_height_mm", "Holder Height", "Height of the bottle sleeve.", required=True, default=90, minimum=35, maximum=180),
        ),
        optional_parameters=(
            num_param("wall_thickness_mm", "Wall Thickness", "Thickness of the holder wall.", default=3, minimum=1.2, maximum=8),
            num_param("floor_thickness_mm", "Floor Thickness", "Bottom floor thickness of the holder.", default=3, minimum=1.2, maximum=8),
            num_param("front_opening_mm", "Front Opening", "Width of the front access opening.", default=28, minimum=10, maximum=80),
            bool_param("mounting_plate", "Mounting Plate", "Adds a rear plate with screw holes.", default=True),
            num_param("plate_width_mm", "Plate Width", "Width of the optional rear mounting plate.", default=42, minimum=18, maximum=90),
            num_param("plate_height_mm", "Plate Height", "Height of the optional rear mounting plate.", default=90, minimum=35, maximum=200),
            num_param("screw_hole_diameter_mm", "Screw Hole Diameter", "Diameter of the mounting holes.", default=5, minimum=3, maximum=8),
            num_param("tolerance_mm", "Tolerance", "Shared fit allowance for the bottle body.", default=0.4, minimum=0.2, maximum=1.2),
        ),
        defaults={
            "bottle_diameter_mm": 70,
            "holder_height_mm": 90,
            "wall_thickness_mm": 3,
            "floor_thickness_mm": 3,
            "front_opening_mm": 28,
            "mounting_plate": True,
            "plate_width_mm": 42,
            "plate_height_mm": 90,
            "screw_hole_diameter_mm": 5,
            "tolerance_mm": 0.4,
        },
        size_presets={
            "small": {"bottle_diameter_mm": 55, "holder_height_mm": 70},
            "medium": {"bottle_diameter_mm": 70, "holder_height_mm": 90},
            "large": {"bottle_diameter_mm": 88, "holder_height_mm": 120},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="desk_organizer",
        title="Desk Organizer",
        category="Functional household",
        description="An open-top organizer with configurable dividers for pens, tools, cables, and small parts.",
        keywords=("desk organizer", "organizer", "pen organizer"),
        examples=(
            "Desk organizer 160x100x90 mm with 3 compartments.",
            "Small desk organizer with three compartments.",
        ),
        required_parameters=(
            num_param("length_mm", "Length", "Overall organizer length.", required=True, default=160, minimum=60, maximum=320),
            num_param("width_mm", "Width", "Overall organizer width.", required=True, default=100, minimum=50, maximum=220),
            num_param("height_mm", "Height", "Overall organizer height.", required=True, default=90, minimum=35, maximum=200),
        ),
        optional_parameters=(
            num_param("wall_thickness_mm", "Wall Thickness", "Outer wall thickness.", default=3, minimum=1.2, maximum=8),
            num_param("floor_thickness_mm", "Floor Thickness", "Base floor thickness.", default=3, minimum=1.2, maximum=10),
            int_param("compartment_count", "Compartment Count", "Number of vertical compartments.", default=3, minimum=2, maximum=6),
            num_param("divider_thickness_mm", "Divider Thickness", "Thickness of internal dividers.", default=3, minimum=1.2, maximum=8),
        ),
        defaults={
            "length_mm": 160,
            "width_mm": 100,
            "height_mm": 90,
            "wall_thickness_mm": 3,
            "floor_thickness_mm": 3,
            "compartment_count": 3,
            "divider_thickness_mm": 3,
        },
        size_presets={
            "small": {"length_mm": 120, "width_mm": 80, "height_mm": 70},
            "medium": {"length_mm": 160, "width_mm": 100, "height_mm": 90},
            "large": {"length_mm": 220, "width_mm": 140, "height_mm": 120},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="laptop_stand",
        title="Laptop Stand",
        category="Custom-fit",
        description="A low-profile wedge stand that lifts a laptop for airflow and typing comfort.",
        keywords=("laptop stand", "notebook stand"),
        examples=(
            "Laptop stand 250x240 mm at 16 degrees.",
            "Large laptop stand with a 14mm front lip.",
        ),
        required_parameters=(
            num_param("laptop_width_mm", "Laptop Width", "Support width across the stand.", required=True, default=250, minimum=180, maximum=380),
            num_param("stand_depth_mm", "Stand Depth", "Depth of the stand footprint.", required=True, default=240, minimum=140, maximum=360),
        ),
        optional_parameters=(
            num_param("angle_degrees", "Angle", "Tilt angle of the laptop platform.", default=16, minimum=8, maximum=28, unit="deg"),
            num_param("wall_thickness_mm", "Wall Thickness", "Thickness of the structural shell.", default=5, minimum=2.4, maximum=12),
            num_param("front_lip_mm", "Front Lip", "Height of the front stop lip.", default=12, minimum=6, maximum=24),
            num_param("center_cutout_width_mm", "Center Cutout Width", "Width of the center airflow cutout.", default=110, minimum=40, maximum=240),
        ),
        defaults={
            "laptop_width_mm": 250,
            "stand_depth_mm": 240,
            "angle_degrees": 16,
            "wall_thickness_mm": 5,
            "front_lip_mm": 12,
            "center_cutout_width_mm": 110,
        },
        size_presets={
            "small": {"laptop_width_mm": 220, "stand_depth_mm": 210},
            "medium": {"laptop_width_mm": 250, "stand_depth_mm": 240},
            "large": {"laptop_width_mm": 300, "stand_depth_mm": 280},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="remote_holder",
        title="Remote Holder",
        category="Custom-fit",
        description="An open-front holder for a TV, AC, or media remote with optional wall mounting holes.",
        keywords=("remote holder", "remote dock"),
        examples=(
            "Remote holder 50x28x130 mm.",
            "Remote holder for a 45mm remote.",
        ),
        required_parameters=(
            num_param("remote_width_mm", "Remote Width", "Maximum remote width.", required=True, default=50, minimum=25, maximum=90),
            num_param("remote_depth_mm", "Remote Depth", "Maximum remote thickness or depth.", required=True, default=28, minimum=12, maximum=60),
            num_param("remote_height_mm", "Remote Height", "Height of the remote body.", required=True, default=130, minimum=60, maximum=240),
        ),
        optional_parameters=(
            num_param("wall_thickness_mm", "Wall Thickness", "Holder wall thickness.", default=3, minimum=1.2, maximum=8),
            num_param("floor_thickness_mm", "Floor Thickness", "Base floor thickness.", default=3, minimum=1.2, maximum=8),
            num_param("front_window_height_mm", "Front Window Height", "Height of the front access cutout.", default=70, minimum=20, maximum=180),
            bool_param("mounting_holes", "Mounting Holes", "Adds screw holes in the rear wall.", default=False),
            num_param("screw_hole_diameter_mm", "Screw Hole Diameter", "Diameter of the optional rear mounting holes.", default=4.2, minimum=3, maximum=8),
            num_param("tolerance_mm", "Tolerance", "Shared fit allowance for the remote body.", default=0.4, minimum=0.2, maximum=1.0),
        ),
        defaults={
            "remote_width_mm": 50,
            "remote_depth_mm": 28,
            "remote_height_mm": 130,
            "wall_thickness_mm": 3,
            "floor_thickness_mm": 3,
            "front_window_height_mm": 70,
            "mounting_holes": False,
            "screw_hole_diameter_mm": 4.2,
            "tolerance_mm": 0.4,
        },
        size_presets={
            "small": {"remote_width_mm": 42, "remote_depth_mm": 22, "remote_height_mm": 110},
            "medium": {"remote_width_mm": 50, "remote_depth_mm": 28, "remote_height_mm": 130},
            "large": {"remote_width_mm": 65, "remote_depth_mm": 35, "remote_height_mm": 170},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="card_holder",
        title="Card Holder",
        category="Custom-fit",
        description="A low-front card tray for business cards, ID cards, or label cards.",
        keywords=("card holder", "business card holder"),
        examples=(
            "Card holder 92x20x45 mm.",
            "Card holder for business cards.",
        ),
        required_parameters=(
            num_param("card_width_mm", "Card Width", "Inside width target for the card stack.", required=True, default=92, minimum=55, maximum=120),
            num_param("stack_depth_mm", "Stack Depth", "Depth allocated to the card stack.", required=True, default=20, minimum=8, maximum=50),
            num_param("holder_height_mm", "Holder Height", "Overall holder height.", required=True, default=45, minimum=18, maximum=100),
        ),
        optional_parameters=(
            num_param("wall_thickness_mm", "Wall Thickness", "Outer wall thickness.", default=2.4, minimum=1.2, maximum=6),
            num_param("floor_thickness_mm", "Floor Thickness", "Base floor thickness.", default=2.4, minimum=1.2, maximum=6),
            num_param("front_lip_mm", "Front Lip", "Visible front lip height.", default=12, minimum=4, maximum=28),
            num_param("tolerance_mm", "Tolerance", "Shared fit allowance for the card stack.", default=0.3, minimum=0.15, maximum=0.8),
        ),
        defaults={
            "card_width_mm": 92,
            "stack_depth_mm": 20,
            "holder_height_mm": 45,
            "wall_thickness_mm": 2.4,
            "floor_thickness_mm": 2.4,
            "front_lip_mm": 12,
            "tolerance_mm": 0.3,
        },
        size_presets={
            "small": {"card_width_mm": 60, "stack_depth_mm": 16, "holder_height_mm": 35},
            "medium": {"card_width_mm": 92, "stack_depth_mm": 20, "holder_height_mm": 45},
            "large": {"card_width_mm": 105, "stack_depth_mm": 28, "holder_height_mm": 60},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="hinge",
        title="Hinge",
        category="Mechanical",
        description="A printable hinge pair with alternating knuckles and a separate pin for fit checks or assemblies.",
        keywords=("hinge", "printable hinge"),
        examples=(
            "Printable hinge 60x20 mm with 10mm knuckle diameter.",
            "Small printable hinge for a lid.",
        ),
        required_parameters=(
            num_param("length_mm", "Length", "Overall hinge length.", required=True, default=60, minimum=24, maximum=220),
            num_param("leaf_width_mm", "Leaf Width", "Width of each hinge leaf.", required=True, default=20, minimum=10, maximum=60),
        ),
        optional_parameters=(
            num_param("leaf_thickness_mm", "Leaf Thickness", "Thickness of each hinge leaf.", default=3, minimum=1.2, maximum=10),
            num_param("knuckle_diameter_mm", "Knuckle Diameter", "Outer diameter of the hinge knuckles.", default=10, minimum=4, maximum=30),
            num_param("pin_diameter_mm", "Pin Diameter", "Diameter of the hinge pin.", default=4.2, minimum=1.5, maximum=12),
            int_param("knuckle_count", "Knuckle Count", "Total number of alternating knuckles.", default=5, minimum=3, maximum=9),
            num_param("clearance_mm", "Clearance", "Clearance between pin and knuckles.", default=0.4, minimum=0.15, maximum=1.0),
        ),
        defaults={
            "length_mm": 60,
            "leaf_width_mm": 20,
            "leaf_thickness_mm": 3,
            "knuckle_diameter_mm": 10,
            "pin_diameter_mm": 4.2,
            "knuckle_count": 5,
            "clearance_mm": 0.4,
        },
        size_presets={
            "small": {"length_mm": 45, "leaf_width_mm": 16},
            "medium": {"length_mm": 60, "leaf_width_mm": 20},
            "large": {"length_mm": 90, "leaf_width_mm": 28},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="snap_fit_box",
        title="Snap-Fit Box",
        category="Mechanical",
        description="A printable enclosure base and lid that uses cantilever snap tabs with matching lid pockets.",
        keywords=("snap fit box", "snap-fit box"),
        examples=(
            "Snap-fit box 90x60x35 mm with 0.4mm clearance and 16mm snap tabs.",
            "Small snap-fit electronics box with rounded edges.",
        ),
        required_parameters=(
            num_param("length_mm", "Length", "Outer box length.", required=True, default=90, minimum=40, maximum=260),
            num_param("width_mm", "Width", "Outer box width.", required=True, default=60, minimum=30, maximum=220),
            num_param("height_mm", "Height", "Outer box height.", required=True, default=35, minimum=18, maximum=140),
        ),
        optional_parameters=(
            num_param("wall_thickness_mm", "Wall Thickness", "Base wall thickness sized for snap features.", default=2.8, minimum=1.6, maximum=6),
            num_param("floor_thickness_mm", "Floor Thickness", "Base floor thickness.", default=3, minimum=1.2, maximum=8),
            num_param("lid_height_mm", "Lid Height", "Overall lid height.", default=18, minimum=12, maximum=40),
            num_param("lid_clearance_mm", "Lid Clearance", "Running clearance between the base and the lid.", default=0.4, minimum=0.25, maximum=1.2),
            num_param("snap_tab_width_mm", "Snap Tab Width", "Width of each cantilever snap tab.", default=14, minimum=8, maximum=24),
            num_param("snap_tab_height_mm", "Snap Tab Height", "Free length of each snap tab beam.", default=12, minimum=8, maximum=20),
            num_param("snap_tab_thickness_mm", "Snap Tab Thickness", "Outward thickness of the cantilever tab beam.", default=2.4, minimum=1.6, maximum=4),
            num_param("snap_tab_relief_gap_mm", "Relief Gap", "Gap behind each tab so it can flex during assembly.", default=0.8, minimum=0.4, maximum=2),
            num_param("snap_hook_depth_mm", "Hook Depth", "Hook projection that locks into the mating lid pocket.", default=1.0, minimum=0.6, maximum=2),
            num_param("snap_hook_height_mm", "Hook Height", "Vertical height of the locking hook.", default=2.4, minimum=1.2, maximum=5),
            int_param("tab_count_per_side", "Tabs Per Side", "Number of snap tabs on each long wall.", default=2, minimum=1, maximum=3),
            bool_param("rounded_edges", "Rounded Edges", "Rounds safe outer vertical edges where possible.", default=True),
            num_param("corner_radius_mm", "Corner Radius", "Outer corner radius.", default=1.5, minimum=0, maximum=10),
            num_param("tolerance_mm", "Tolerance", "Shared print tolerance hint.", default=0.4, minimum=0.25, maximum=1.2),
        ),
        defaults={
            "length_mm": 90,
            "width_mm": 60,
            "height_mm": 35,
            "wall_thickness_mm": 2.8,
            "floor_thickness_mm": 3,
            "lid_height_mm": 18,
            "lid_clearance_mm": 0.4,
            "snap_tab_width_mm": 14,
            "snap_tab_height_mm": 12,
            "snap_tab_thickness_mm": 2.4,
            "snap_tab_relief_gap_mm": 0.8,
            "snap_hook_depth_mm": 1.0,
            "snap_hook_height_mm": 2.4,
            "tab_count_per_side": 2,
            "rounded_edges": True,
            "corner_radius_mm": 1.5,
            "tolerance_mm": 0.4,
        },
        size_presets={
            "small": {"length_mm": 75, "width_mm": 50, "height_mm": 28},
            "medium": {"length_mm": 90, "width_mm": 60, "height_mm": 35},
            "large": {"length_mm": 130, "width_mm": 85, "height_mm": 50},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="nut_and_bolt_basic",
        title="Nut and Bolt Basic",
        category="Mechanical",
        description="A printable non-threaded fastener set with a matching nut and bolt for fit checks and quick fixtures.",
        keywords=("nut and bolt", "bolt", "threaded fastener"),
        examples=(
            "Nut and bolt 8x30 mm with 15mm nut width.",
            "Basic nut and bolt for fit testing.",
        ),
        required_parameters=(
            num_param("shaft_diameter_mm", "Shaft Diameter", "Across-flats diameter of the bolt shaft.", required=True, default=8, minimum=4, maximum=24),
            num_param("bolt_length_mm", "Bolt Length", "Length of the bolt shank below the head.", required=True, default=30, minimum=12, maximum=120),
        ),
        optional_parameters=(
            num_param("head_diameter_mm", "Head Diameter", "Across-flats size of the bolt head.", default=14, minimum=8, maximum=40),
            num_param("head_height_mm", "Head Height", "Height of the bolt head.", default=5, minimum=2, maximum=20),
            num_param("nut_width_mm", "Nut Width", "Across-flats size of the mating nut.", default=15, minimum=8, maximum=45),
            num_param("nut_thickness_mm", "Nut Thickness", "Thickness of the mating nut.", default=7, minimum=3, maximum=20),
            num_param("fit_clearance_mm", "Fit Clearance", "Clearance between the nut bore and the bolt shaft.", default=0.4, minimum=0.15, maximum=1.2),
        ),
        defaults={
            "shaft_diameter_mm": 8,
            "bolt_length_mm": 30,
            "head_diameter_mm": 14,
            "head_height_mm": 5,
            "nut_width_mm": 15,
            "nut_thickness_mm": 7,
            "fit_clearance_mm": 0.4,
        },
        size_presets={
            "small": {"shaft_diameter_mm": 6, "bolt_length_mm": 24},
            "medium": {"shaft_diameter_mm": 8, "bolt_length_mm": 30},
            "large": {"shaft_diameter_mm": 12, "bolt_length_mm": 45},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="spacer",
        title="Spacer",
        category="Mechanical",
        description="A simple spacer or standoff for gap control and mounting.",
        keywords=("spacer", "standoff spacer"),
        examples=(
            "Spacer 5x12x10 mm.",
            "Spacer 5mm inner diameter, 12mm outer diameter, 10mm tall.",
        ),
        required_parameters=(
            num_param("inner_diameter_mm", "Inner Diameter", "Inside hole diameter.", required=True, default=5, minimum=1, maximum=80),
            num_param("outer_diameter_mm", "Outer Diameter", "Outside diameter of the spacer.", required=True, default=12, minimum=3, maximum=120),
            num_param("height_mm", "Height", "Spacer height.", required=True, default=10, minimum=1, maximum=120),
        ),
        optional_parameters=(
            num_param("chamfer_mm", "Chamfer", "Small chamfer on top and bottom edges.", default=0.6, minimum=0, maximum=3),
        ),
        defaults={
            "inner_diameter_mm": 5,
            "outer_diameter_mm": 12,
            "height_mm": 10,
            "chamfer_mm": 0.6,
        },
        size_presets={
            "small": {"inner_diameter_mm": 3, "outer_diameter_mm": 8, "height_mm": 6},
            "medium": {"inner_diameter_mm": 5, "outer_diameter_mm": 12, "height_mm": 10},
            "large": {"inner_diameter_mm": 8, "outer_diameter_mm": 18, "height_mm": 16},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="test_tube_rack",
        title="Test Tube Rack",
        category="Engineering/lab",
        description="A compact rack with a perforated top plate, lower support plate, and stabilizing posts for test tubes.",
        keywords=("test tube rack", "lab rack"),
        examples=(
            "Test tube rack for 16mm tubes with 6 tube count and 2 rows.",
            "Test tube rack 16mm diameter, 6 tube count, 2 rows.",
        ),
        required_parameters=(
            num_param("tube_diameter_mm", "Tube Diameter", "Target outside tube diameter.", required=True, default=16, minimum=8, maximum=40),
            int_param("tube_count", "Tube Count", "Total number of tube holes.", required=True, default=6, minimum=2, maximum=24),
        ),
        optional_parameters=(
            int_param("row_count", "Row Count", "Number of rows of tube holes.", default=2, minimum=1, maximum=4),
            num_param("spacing_mm", "Spacing", "Clear spacing between tube holes.", default=8, minimum=3, maximum=20),
            num_param("plate_thickness_mm", "Plate Thickness", "Thickness of the top and bottom plates.", default=4, minimum=2, maximum=10),
            num_param("rack_height_mm", "Rack Height", "Distance between the base and top plate.", default=55, minimum=20, maximum=140),
            num_param("foot_width_mm", "Foot Width", "Width of the base stabilizing runners.", default=12, minimum=4, maximum=30),
        ),
        defaults={
            "tube_diameter_mm": 16,
            "tube_count": 6,
            "row_count": 2,
            "spacing_mm": 8,
            "plate_thickness_mm": 4,
            "rack_height_mm": 55,
            "foot_width_mm": 12,
        },
        size_presets={
            "small": {"tube_diameter_mm": 13, "tube_count": 4},
            "medium": {"tube_diameter_mm": 16, "tube_count": 6},
            "large": {"tube_diameter_mm": 20, "tube_count": 8},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="sensor_mount",
        title="Sensor Mount",
        category="Engineering/lab",
        description="A compact breakout-board mount with standoffs and optional outer flange holes.",
        keywords=("sensor mount", "module mount"),
        examples=(
            "Sensor mount for a 35x25 mm board.",
            "Sensor mount 35x25 mm with mounting holes.",
        ),
        required_parameters=(
            num_param("board_length_mm", "Board Length", "Length of the sensor board.", required=True, default=35, minimum=15, maximum=120),
            num_param("board_width_mm", "Board Width", "Width of the sensor board.", required=True, default=25, minimum=12, maximum=100),
        ),
        optional_parameters=(
            num_param("base_thickness_mm", "Base Thickness", "Thickness of the base plate.", default=3, minimum=1.2, maximum=8),
            num_param("standoff_height_mm", "Standoff Height", "Height of the standoff posts.", default=8, minimum=2, maximum=20),
            num_param("standoff_diameter_mm", "Standoff Diameter", "Diameter of the corner standoffs.", default=8, minimum=4, maximum=18),
            num_param("hole_diameter_mm", "Hole Diameter", "Diameter of the standoff holes.", default=3, minimum=1.5, maximum=6),
            num_param("flange_width_mm", "Flange Width", "Extra flange around the board for mounting holes.", default=12, minimum=4, maximum=30),
            bool_param("mounting_holes", "Mounting Holes", "Adds holes in the side flanges.", default=True),
        ),
        defaults={
            "board_length_mm": 35,
            "board_width_mm": 25,
            "base_thickness_mm": 3,
            "standoff_height_mm": 8,
            "standoff_diameter_mm": 8,
            "hole_diameter_mm": 3,
            "flange_width_mm": 12,
            "mounting_holes": True,
        },
        size_presets={
            "small": {"board_length_mm": 30, "board_width_mm": 20},
            "medium": {"board_length_mm": 35, "board_width_mm": 25},
            "large": {"board_length_mm": 50, "board_width_mm": 35},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="ventilation_box",
        title="Ventilation Box",
        category="Engineering/lab",
        description="A vented enclosure with a removable lid and cable exit for airflow-heavy electronics or sensor rigs.",
        keywords=("ventilation box", "vented box"),
        examples=(
            "Ventilation box 100x80x40 mm with 6 vent slots.",
            "Ventilation box for a fan controller.",
        ),
        required_parameters=(
            num_param("length_mm", "Length", "Outer enclosure length.", required=True, default=100, minimum=40, maximum=260),
            num_param("width_mm", "Width", "Outer enclosure width.", required=True, default=80, minimum=30, maximum=220),
            num_param("height_mm", "Height", "Outer enclosure height.", required=True, default=40, minimum=18, maximum=140),
        ),
        optional_parameters=(
            num_param("wall_thickness_mm", "Wall Thickness", "Base wall thickness.", default=3, minimum=1.2, maximum=8),
            num_param("floor_thickness_mm", "Floor Thickness", "Base floor thickness.", default=3, minimum=1.2, maximum=8),
            num_param("lid_height_mm", "Lid Height", "Height of the removable lid.", default=16, minimum=8, maximum=40),
            int_param("vent_slot_count", "Vent Slot Count", "Number of lid ventilation slots.", default=6, minimum=2, maximum=16),
            num_param("cable_hole_diameter_mm", "Cable Hole Diameter", "Diameter of the side cable exit.", default=8, minimum=3, maximum=30),
            num_param("tolerance_mm", "Tolerance", "Shared fit allowance for the lid.", default=0.4, minimum=0.2, maximum=1.2),
        ),
        defaults={
            "length_mm": 100,
            "width_mm": 80,
            "height_mm": 40,
            "wall_thickness_mm": 3,
            "floor_thickness_mm": 3,
            "lid_height_mm": 16,
            "vent_slot_count": 6,
            "cable_hole_diameter_mm": 8,
            "tolerance_mm": 0.4,
        },
        size_presets={
            "small": {"length_mm": 80, "width_mm": 60, "height_mm": 32},
            "medium": {"length_mm": 100, "width_mm": 80, "height_mm": 40},
            "large": {"length_mm": 140, "width_mm": 110, "height_mm": 55},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="stackable_box",
        title="Stackable Box",
        category="Modular",
        description="An open-top storage box with a printable locating lip and bottom foot for stacking.",
        keywords=("stackable box", "stacking bin"),
        examples=(
            "Stackable box 120x80x60 mm with 6mm lip height.",
            "Stackable box for workshop parts.",
        ),
        required_parameters=(
            num_param("length_mm", "Length", "Outer box length.", required=True, default=120, minimum=40, maximum=260),
            num_param("width_mm", "Width", "Outer box width.", required=True, default=80, minimum=30, maximum=220),
            num_param("height_mm", "Height", "Outer box height.", required=True, default=60, minimum=20, maximum=200),
        ),
        optional_parameters=(
            num_param("wall_thickness_mm", "Wall Thickness", "Outer wall thickness.", default=3, minimum=1.2, maximum=8),
            num_param("floor_thickness_mm", "Floor Thickness", "Base floor thickness.", default=3, minimum=1.2, maximum=10),
            num_param("stack_lip_height_mm", "Stack Lip Height", "Height of the stacking lip and bottom foot.", default=6, minimum=2, maximum=20),
            num_param("stack_clearance_mm", "Stack Clearance", "Clearance between stacked parts.", default=0.5, minimum=0.2, maximum=1.5),
            bool_param("rounded_edges", "Rounded Edges", "Rounds the outer vertical edges.", default=True),
            num_param("corner_radius_mm", "Corner Radius", "Outer corner radius.", default=2, minimum=0, maximum=12),
            num_param("tolerance_mm", "Tolerance", "Shared fit allowance for the stacking interface.", default=0.4, minimum=0.2, maximum=1.0),
        ),
        defaults={
            "length_mm": 120,
            "width_mm": 80,
            "height_mm": 60,
            "wall_thickness_mm": 3,
            "floor_thickness_mm": 3,
            "stack_lip_height_mm": 6,
            "stack_clearance_mm": 0.5,
            "rounded_edges": True,
            "corner_radius_mm": 2,
            "tolerance_mm": 0.4,
        },
        size_presets={
            "small": {"length_mm": 90, "width_mm": 60, "height_mm": 45},
            "medium": {"length_mm": 120, "width_mm": 80, "height_mm": 60},
            "large": {"length_mm": 160, "width_mm": 110, "height_mm": 85},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="gridfinity_bin",
        title="Gridfinity Bin",
        category="Modular",
        description="A simplified Gridfinity-style bin with modular footprint dimensions, an optional scoop front, and optional magnet holes.",
        keywords=("gridfinity bin", "gridfinity"),
        examples=(
            "Gridfinity bin 2 by 2 units, 3 units tall.",
            "Gridfinity bin 2x2, 3 tall with scoop front.",
        ),
        required_parameters=(
            int_param("grid_units_x", "Grid Units X", "Gridfinity width in base units.", required=True, default=2, minimum=1, maximum=8),
            int_param("grid_units_y", "Grid Units Y", "Gridfinity depth in base units.", required=True, default=2, minimum=1, maximum=8),
        ),
        optional_parameters=(
            int_param("height_units", "Height Units", "Gridfinity height in vertical units.", default=3, minimum=1, maximum=12),
            num_param("wall_thickness_mm", "Wall Thickness", "Wall thickness of the bin shell.", default=2.4, minimum=1.2, maximum=8),
            num_param("floor_thickness_mm", "Floor Thickness", "Bottom floor thickness.", default=2.4, minimum=1.2, maximum=8),
            bool_param("scoop_front", "Scoop Front", "Cuts a front scoop for easier part access.", default=True),
            bool_param("magnet_holes", "Magnet Holes", "Adds four shallow bottom magnet holes.", default=False),
        ),
        defaults={
            "grid_units_x": 2,
            "grid_units_y": 2,
            "height_units": 3,
            "wall_thickness_mm": 2.4,
            "floor_thickness_mm": 2.4,
            "scoop_front": True,
            "magnet_holes": False,
        },
        size_presets={
            "small": {"grid_units_x": 1, "grid_units_y": 1, "height_units": 2},
            "medium": {"grid_units_x": 2, "grid_units_y": 2, "height_units": 3},
            "large": {"grid_units_x": 3, "grid_units_y": 3, "height_units": 5},
        },
        implemented=True,
    ),
    ModelSpec(
        model_type="interlocking_panel",
        title="Interlocking Panel",
        category="Modular",
        description="A flat panel with printed tabs and matching edge slots for quick modular assemblies.",
        keywords=("interlocking panel", "panel"),
        examples=(
            "Interlocking panel 120x80x4 mm with 16mm tabs.",
            "Interlocking panel for a small enclosure wall.",
        ),
        required_parameters=(
            num_param("length_mm", "Length", "Overall panel length.", required=True, default=120, minimum=30, maximum=260),
            num_param("width_mm", "Width", "Overall panel width.", required=True, default=80, minimum=20, maximum=220),
            num_param("thickness_mm", "Thickness", "Panel thickness.", required=True, default=4, minimum=1.2, maximum=12),
        ),
        optional_parameters=(
            num_param("tab_width_mm", "Tab Width", "Width of each interlocking tab.", default=16, minimum=6, maximum=40),
            num_param("tab_depth_mm", "Tab Depth", "Projection depth of each tab.", default=8, minimum=3, maximum=20),
            int_param("tabs_per_side", "Tabs Per Side", "Number of tabs on each tabbed edge.", default=2, minimum=1, maximum=4),
            num_param("slot_clearance_mm", "Slot Clearance", "Clearance added to the mating slots.", default=0.35, minimum=0.15, maximum=1.0),
        ),
        defaults={
            "length_mm": 120,
            "width_mm": 80,
            "thickness_mm": 4,
            "tab_width_mm": 16,
            "tab_depth_mm": 8,
            "tabs_per_side": 2,
            "slot_clearance_mm": 0.35,
        },
        size_presets={
            "small": {"length_mm": 80, "width_mm": 60, "thickness_mm": 3},
            "medium": {"length_mm": 120, "width_mm": 80, "thickness_mm": 4},
            "large": {"length_mm": 180, "width_mm": 120, "thickness_mm": 5},
        },
        implemented=True,
    ),
]


MODEL_REGISTRY: Dict[str, ModelSpec] = {spec.model_type: spec for spec in MODEL_SPECS}


def get_model_spec(model_type: str) -> Optional[ModelSpec]:
    return MODEL_REGISTRY.get(model_type)


def list_capabilities() -> list[CapabilityItemV2]:
    return [spec.capability_item() for spec in MODEL_SPECS]


def capability_categories() -> list[str]:
    return list(dict.fromkeys(spec.category for spec in MODEL_SPECS))


def detect_model_type(prompt: str, requested_model_type: Optional[str] = None) -> Optional[str]:
    if requested_model_type and requested_model_type in MODEL_REGISTRY:
        return requested_model_type

    prompt_lower = prompt.lower()
    best_match: tuple[int, Optional[str]] = (0, None)
    for spec in MODEL_SPECS:
        score = 0
        for keyword in spec.keywords:
            if keyword in prompt_lower:
                score += max(1, len(keyword.split()))
        if spec.model_type.replace("_", " ") in prompt_lower:
            score += 2
        if score > best_match[0]:
            best_match = (score, spec.model_type)

    return best_match[1]
