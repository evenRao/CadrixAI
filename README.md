# CadrixAI
### Intent-driven parametric CAD for 3D printing

CadrixAI is a web app that turns text or voice prompts into printable, previewable 3D parts.

V2 moves the project beyond a small set of hardcoded templates and into a modular CAD pipeline:

`Prompt -> design parser -> model registry -> validation -> geometry generation -> STL / GLB / STEP export`

The focus is reliability, printability, and clean architecture rather than flashy but brittle mesh generation.

## V2 Overview

CadrixAI V2 adds:

- A rule-based natural language parser that extracts structured design intent
- A model registry with categories, defaults, validation metadata, and examples
- A printability validation layer with actionable warnings and auto-fix suggestions
- Twenty-two implemented V2 parametric models across functional household, custom-fit, mechanical, engineering/lab, and modular categories
- Optional local Ollama parsing that safely falls back to the rule-based parser
- Separate V2 backend routes that preserve the legacy V1 flow
- Richer frontend controls for examples, parameter editing, warnings, printability score, and downloads
- A minimal backend test suite for parser, validation, registry, generation, and API response shape

## Repository Structure

```text
CadrixAI/
├── README.md
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── out/
│   ├── cadrix_v2/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── exporters.py
│   │   ├── geometry.py
│   │   ├── prompt_utils.py
│   │   ├── registry.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── validators.py
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── llm_parser.py
│   │       ├── parser_interface.py
│   │       └── rule_based_parser.py
│   └── tests/
│       ├── test_api_shapes.py
│       ├── test_generation.py
│       ├── test_parser.py
│       ├── test_registry.py
│       └── test_validation.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── api.js
        └── main.jsx
```

## Architecture Diagram

```text
User prompt / voice input
        |
        v
frontend/src/App.jsx
        |
        v
frontend/src/api.js
        |
        v
POST /v2/plan or POST /v2/generate
        |
        v
backend/cadrix_v2/app.py
        |
        v
backend/cadrix_v2/service.py
        |
        +--> parsers/rule_based_parser.py
        |         |
        |         v
        |   structured DesignIntent JSON
        |
        +--> registry.py
        |         |
        |         v
        |   model defaults + parameter definitions + examples
        |
        +--> validators.py
        |         |
        |         v
        |   printability warnings / errors / score
        |
        +--> geometry.py
        |         |
        |         v
        |   CadQuery solids
        |
        +--> exporters.py
                  |
                  v
           STL + GLB + STEP files
```

## Supported Models

| Category | Model | Status | Notes |
|---|---|---|---|
| Functional household | `cable_clip` | Implemented | Cable diameter, wall thickness, opening gap, mounting base, screw hole |
| Functional household | `wall_hook` | Implemented | Back plate, hook reach, drop, and mounting holes |
| Functional household | `drawer_divider` | Implemented | Divider wall, stabilizing base, and simple fit allowance |
| Functional household | `bottle_holder` | Implemented | Cylindrical holder with front opening and optional mounting plate |
| Functional household | `desk_organizer` | Implemented | Open shell with configurable divider count |
| Custom-fit | `phone_stand` | Implemented | Width, angle, base thickness, lip, cable feature, rounded edges |
| Custom-fit | `laptop_stand` | Implemented | Wedge stand with tilt angle, front lip, and airflow cutout |
| Custom-fit | `remote_holder` | Implemented | Open-front remote pocket with optional mounting holes |
| Custom-fit | `card_holder` | Implemented | Low-front tray for business cards and small stacks |
| Custom-fit | `box_with_lid` | Implemented | Length, width, height, walls, lid clearance, snap-fit option, separate lid export |
| Mechanical | `simple_gear` | Implemented | Tooth count, diameter, thickness, bore, hub |
| Mechanical | `hinge` | Implemented | Alternating knuckles, pin clearance, and separate pin export |
| Mechanical | `snap_fit_box` | Implemented | Cantilever snap tabs, mating lid pockets, separate lid export |
| Mechanical | `nut_and_bolt_basic` | Implemented | Printable nut-and-bolt fit-check pair with separate nut export |
| Mechanical | `spacer` | Implemented | Inner diameter, outer diameter, height, chamfer |
| Engineering/lab | `test_tube_rack` | Implemented | Top plate, base plate, posts, tube grid |
| Engineering/lab | `pcb_enclosure` | Implemented | Board footprint, standoffs, screw holes, ventilation, removable lid |
| Engineering/lab | `sensor_mount` | Implemented | Board plate, standoffs, flange holes |
| Engineering/lab | `ventilation_box` | Implemented | Vented lid, cable exit, removable lid export |
| Modular | `stackable_box` | Implemented | Inner lip and bottom foot for stacking |
| Modular | `gridfinity_bin` | Implemented | Modular unit footprint, scoop front, optional magnet holes |
| Modular | `interlocking_panel` | Implemented | Edge tabs and matching slots for modular panels |

## Natural Language Parsing

The default parser is rule-based and does not require any paid AI API.

If you enable the optional parser toggle in the UI, V2 will try a local Ollama model first and fall back safely to the rule-based parser if Ollama is unavailable or returns invalid JSON.

It currently supports:

- explicit dimensions such as `120x80x60 mm`
- labeled measurements such as `75mm wide phone`
- vague sizes such as `small`, `medium`, `large`
- units: `mm`, `cm`, `in`, `inch`, `inches`
- optional features such as cable slots, ventilation, screw holes, and rounded edges
- fallback defaults when prompts are incomplete
- validation warnings and failure messages for impossible values

Example prompt:

```text
Make a phone stand for a 75mm wide phone with a 20 degree angle and cable hole.
```

Example structured intent:

```json
{
  "model_type": "phone_stand",
  "dimensions": {
    "phone_width_mm": 75,
    "angle_degrees": 70
  },
  "features": {
    "cable_hole": true
  },
  "print_settings": {}
}
```

Note:

- In V2, low phone stand angles such as `20 degrees` are interpreted as a recline request and converted into a printable back-support angle from the build plate.

## Validation Rules

The V2 validation layer checks:

- minimum wall thickness
- minimum clearance / tolerance
- negative or zero values
- unrealistic proportions
- too-small holes
- model-specific constraints
- rough overhang risk heuristics

Example validation feedback:

```text
Wall thickness must be at least 1.2mm for reliable FDM printing.
Increase wall thickness to 2.4mm or 3mm.
```

## API

Legacy V1 endpoints are still present.

New V2 endpoints:

- `GET /v2/capabilities`
- `POST /v2/plan`
- `POST /v2/generate`

### V2 Generation Flow

`prompt -> parse design intent -> validate -> generate -> export -> return files + metadata`

### Example `POST /v2/generate` response

```json
{
  "success": true,
  "model_type": "phone_stand",
  "title": "Phone Stand",
  "implemented": true,
  "intent": {
    "model_type": "phone_stand",
    "dimensions": {
      "phone_width_mm": 75,
      "angle_degrees": 70
    },
    "features": {
      "cable_hole": true
    },
    "print_settings": {}
  },
  "parameters": {
    "phone_width_mm": 75,
    "angle_degrees": 70,
    "device_thickness_mm": 12,
    "base_thickness_mm": 6,
    "front_lip_mm": 12,
    "back_support_height_mm": 110,
    "side_margin_mm": 8,
    "cable_slot": true,
    "cable_slot_width_mm": 14,
    "rounded_edges": true,
    "edge_radius_mm": 2,
    "wall_thickness_mm": 3,
    "tolerance_mm": 0.4
  },
  "warnings": [],
  "errors": [],
  "files": {
    "stl": "http://localhost:8000/files/v2_....stl",
    "glb": "http://localhost:8000/files/v2_....glb",
    "step": "http://localhost:8000/files/v2_....step",
    "extra_downloads": []
  },
  "metadata": {
    "estimated_dimensions_mm": {
      "x": 75.0,
      "y": 182.0,
      "z": 116.0
    },
    "printability_score": 100,
    "generator_version": "v2"
  }
}
```

## Frontend V2 Features

The updated frontend keeps the current split-pane layout and adds:

- prompt examples
- V2 supported builds section
- model category cards
- design summary
- validation warnings and errors
- printability score
- advanced parameter controls
- STL / GLB / STEP download links

Voice input is connected to the same parser pipeline as typed prompts through the shared prompt field.
The sidebar speech button requests microphone access, uses the browser microphone, and drops the transcript into the same V2 prompt box before planning or generation.

## Exports

CadrixAI V2 currently exports:

- `STL` for slicers and general printing workflows
- `GLB` for browser preview
- `STEP` for CAD and Autodesk Fusion workflows where explicit units matter

For Autodesk Fusion:

- Prefer the `STEP` file, because STL is unitless and can be interpreted inconsistently during import.

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend URLs:

- legacy docs / routes: `http://127.0.0.1:8000`
- V2 capabilities: `http://127.0.0.1:8000/v2/capabilities`

Optional local Ollama parsing:

```bash
ollama serve
export CADRIX_OLLAMA_MODEL=llama3.1:8b
```

If `CADRIX_OLLAMA_MODEL` is not set, CadrixAI V2 will try to auto-pick an installed local Ollama model.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

- `http://localhost:5173`

## Tests

Run the V2 backend test suite:

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests
```

What is covered:

- parser outputs
- validation logic
- model registry entries
- generation of the implemented models
- V2 API response shape

## Example Prompts

- `Make a phone stand for a 75mm wide phone with a 20 degree angle and cable hole.`
- `Box with lid 120x80x60 mm with 0.4mm clearance.`
- `Cable clip for 6mm cable with mounting base and screw hole.`
- `Simple gear with 24 teeth, 40mm diameter, and 5mm bore.`
- `PCB enclosure for an 80x50 mm board with ventilation slots.`
- `Large snap-fit box for small electronics.`
- `Gridfinity bin 2 by 2 units tall.`

## Limitations

- The rule-based parser is intentionally conservative and works best with clear functional prompts.
- All V2 models currently listed in the registry are implemented and generate geometry.
- Geometry is parametric and printable, but not yet assembly-aware.
- Overhang and strength analysis are heuristic, not simulation-driven.
- The frontend still uses a single-page inline-style UI and can be refactored further later.

## Future Work

- LLM-based CAD code generation
- assemblies with multiple STL exports
- print-time estimation
- material recommendation
- strength simulation
- slicing integration
- cloud LLM provider integration
- image-to-3D reference input

## Notes

- The V1 backend routes remain available for compatibility.
- The V2 parser interface is modular:

```text
backend/cadrix_v2/parsers/
├── parser_interface.py
├── rule_based_parser.py
└── llm_parser.py
```

- `llm_parser.py` now prefers a local Ollama model and falls back to the rule-based parser if local inference is unavailable.
