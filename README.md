# CadrixAI
### *Intent-driven parametric CAD for 3D printing*


CadrixAI is a web app that turns natural language (and optional voice input) into **printable, functional 3D parts**.  
It does **not** try to generate random “AI meshes.” Instead, it converts your request into **parametric CAD templates** (dimensioned, constraint-aware geometry) and exports a **manufacturable STL**.

Think: brackets, spacers, organizers, boxes, stands, simple household parts.

---

## What CadrixAI does

- Takes a **text prompt** like:  
  `l bracket 60x60x5 mm with 2 holes`
- (Optional) takes **voice input** and converts it to text (browser speech recognition) -not working right now
- Plans the model by selecting a **template** + extracting **parameters**
- Generates a **solid CAD model** (deterministic geometry)
- Exports:
  - `.stl` for 3D printing
  - `.glb` for fast web preview
- Shows an interactive **3D preview** in the browser (rotate/pan/zoom)

---

## What it is NOT

- Not free-form sculpting AI
- Not artistic text-to-3D mesh generation
- Not “model anything in the world”
- Not a replacement for professional engineering CAD

CadrixAI is intentionally scoped to **functional, printable parts**.

---

## Supported object categories (examples)

- Functional parts and household objects  
  organizers, stands, holders
- Boxes, lids, containers
- Brackets, spacers, hooks
- Phone accessories
- Simple toys and shapes

Your exact supported templates depend on what your backend `CAPABILITIES` list includes.

---

## Tech stack

### Frontend
- **React** (UI)
- **Three.js** (3D rendering)
- **GLTFLoader** (loads `.glb` previews)
- **OrbitControls** (drag rotate, pan, zoom)
- **Web Speech API** (optional voice → text, runs in browser) -not working rn
- **Vite** (dev server / build tool)

### Backend
- **Python**
- **FastAPI** (REST API)
- **Pydantic** (validation + schemas)
- **CadQuery** (parametric CAD generation)
- File export: **STL** (printing), **GLB** (preview)

### Optional AI (no paid API)
- **Ollama** (local LLM) for optional planning assistance  
  The system still works without it.

---

## How it works (high level)

1. **Prompt**: user describes an object + dimensions
2. **Planning**: system selects a template + extracts parameters  
   (rule-based by default, optional Ollama assist)
3. **Validation**: checks parameter ranges / geometric sanity
4. **CAD Generation**: CadQuery builds a solid model
5. **Export**: generates `STL` and `GLB`
6. **Preview**: frontend loads the `GLB` with Three.js

Pipeline:
`Intent → Plan → Params → CAD Solid → GLB Preview + STL Download`

---

## Requirements

- **Node.js 18+**
- **Python 3.10+** recommended  
  (If you’re on a very new Python like 3.14, expect more package issues.)
- macOS / Windows / Linux supported
- Chrome recommended for voice input

---

## Setup and run (local)

### 1) Clone the repo
```bash
git clone https://github.com/evenRao/CadrixAI
cd CadrixAI

