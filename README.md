# CadrixAI

**v2.1.0 — Intent-driven parametric CAD for 3D printing**

CadrixAI turns a description into an editable parametric part, an interactive 3D preview, and STL, STEP, and GLB downloads. Choose from 32 functional models, describe the dimensions you need, review the parameters, and generate your part.

The workspace uses React and Three.js, the API uses FastAPI, and CadQuery builds the solid geometry. The built-in parser works without a paid API or a local language model. Optional Ollama integration interprets descriptions through the same model registry and validation pipeline.

## Demo

https://github.com/user-attachments/assets/39e051b8-d65f-4400-97b2-33e6df8a53fe

## What's new in v2.1.0

Released November 11, 2026.

- **Redesigned UI:** a focused Describe/Adjust workflow, a large 3D canvas, a searchable template library with category filters, and dedicated settings, view controls, and printability dialogs.
- **Dark mode by default:** switch to light mode from the toolbar or Settings. The browser saves your appearance preference on the device.
- **Expanded library:** 10 additional models bring the base library to 32. New parts include trays, planters, cable combs, battery organizers, drawer pulls, desk grommets, tube end caps, angle brackets, funnels, and hose adapters.
- **Refined geometry:** corrected extrusion widths, connected solids, improved rounded shells, equal-width compartments, mating clearances, and smoother STL/GLB tessellation.
- **Reliable development startup:** one command prepares the pinned Python runtime, synchronizes backend dependencies, installs frontend dependencies when needed, and starts both services.
- **CI/CD:** platform and runtime checks, dependency audits, production HTTP tests, native x64/ARM64 container checks, and versioned GitHub Releases and GHCR images.
- **Repository cleanup:** installed dependencies, build output, caches, and generated model files are excluded from version control. Manifests and lockfiles remain part of the source distribution.

The product version is **2.1.0**. The application continues to use the **`/v2` API** and V2 geometry pipeline; those identifiers describe the API/generator generation.

## Quick start

For native development, install [Node.js](https://nodejs.org/) with npm and [uv](https://docs.astral.sh/uv/getting-started/installation/), then run this command from the repository root:

```bash
npm run dev
```

`npm start` runs the same launcher. A separate root `npm install` or virtual environment activation is not required.

The launcher ensures Python **3.14.10** is installed, synchronizes `backend/uv.lock`, and installs frontend packages from `frontend/package-lock.json` when the manifests, platform, architecture, or Node major version change. This also repairs a backend virtual environment whose pinned uv Python installation was removed. Initial setup and missing-runtime repairs need internet access.

| Service | Local address |
| --- | --- |
| Frontend workspace | `http://localhost:5173` |
| Interactive API documentation | `http://localhost:8000/docs` |
| Model capabilities | `http://localhost:8000/v2/capabilities` |
| Backend health | `http://localhost:8000/healthz` |

Both services reload during development. Keep ports **5173** and **8000** available. Press **Ctrl+C** to stop both services; the launcher also stops the other service if either one exits or fails to start.

### Supported environments

| Component/platform | Configuration |
| --- | --- |
| Node.js | 26 recommended; 24 also checked in CI |
| Python | 3.14.10 by default; the locked backend also supports 3.13 |
| uv | Required for native development; CI pins 0.13.7 |
| Windows | Native x64 development |
| Linux | Native x64 development; x64 and ARM64 containers |
| macOS on Apple Silicon | Native development or ARM64 containers |
| macOS on Intel | Use Docker Desktop with the x64 Linux image |

The backend requires Python `>=3.13,<3.15`. The locked native CAD dependencies do not provide Python 3.15 support. Current Numba and NLopt dependencies also lack Intel macOS wheels. See [platform details](docs/ci-cd.md#supported-platforms-and-runtimes) before changing runtime versions.

## Using the workspace

1. **Describe** a supported part, choose a starter, or select **Browse all templates**. Add dimensions and features to your description.
2. Select **Create model** to generate directly, or **Review dimensions first** to inspect the parsed design in **Adjust**.
3. In **Adjust**, edit the dimensions and optional features. Advanced parameters are available in a disclosure section. Select **Generate model** or **Update model** to apply the changes.
4. Inspect the preview. Drag to orbit, right-drag to pan, and scroll or pinch to zoom. Toolbar controls provide front/top views, reset/fit, a grid toggle, and additional view settings.
5. Open **Printability & design details** from the status bar to inspect warnings, errors, assumptions, dimensions, the printability score, and technical details.
6. Use **Export** to download the generated part and any separate accessory parts. Changing the description or parameters marks the previous model as stale and disables export until the updated design is generated.

Preview rotation and scale affect only the viewer. Change dimensions in **Adjust** to change the exported geometry.

The microphone button fills the description using browser speech recognition. It requires microphone permission, an available speech-recognition implementation, and a suitable browser context such as localhost or HTTPS. Availability and speech processing depend on the browser; typed input remains available.

## Model library

All 32 registered models have geometry generators. Templates expose model-specific dimensions, defaults, optional features, and validation limits.

| Category | Model identifier | Main controls and features |
| --- | --- | --- |
| Functional household | `cable_clip` | Cable diameter, retaining gap, base, and screw hole |
| Functional household | `wall_hook` | Back plate, reinforced arm, retaining tip, and mounting holes |
| Functional household | `drawer_divider` | Divider dimensions, stabilizing base, and fit allowance |
| Functional household | `bottle_holder` | Bottle diameter, front opening, and optional mounting plate |
| Functional household | `desk_organizer` | Open shell with configurable dividers |
| Functional household | `parts_tray` | Rounded tray with equal-width compartments |
| Functional household | `planter` | Tapered shell, drainage holes, reinforced rim, and separate drip tray |
| Functional household | `cable_comb` | Cable pockets, retaining openings, spacing, and mounting ears |
| Functional household | `battery_organizer` | Measured cell diameter, cell count, rows, and blind pockets |
| Custom-fit | `phone_stand` | Width, support angle, lip, cable slot, and lightweight frame |
| Custom-fit | `laptop_stand` | Wedge angle, width, front lip, and airflow cutout |
| Custom-fit | `remote_holder` | Open-front pocket and optional mounting holes |
| Custom-fit | `card_holder` | Low-front card tray and stack dimensions |
| Custom-fit | `box_with_lid` | Wall/floor thickness, lid clearance, and separate lid export |
| Custom-fit | `drawer_pull` | Mounting spacing, rounded grip, and blind screw-clearance bores |
| Custom-fit | `desk_grommet` | Flanged sleeve, desk-hole clearance, and optional cable notch |
| Custom-fit | `tube_end_cap` | Tube clearance, closed end, softened rim, and grip rings |
| Mechanical | `simple_gear` | Approximate spur teeth, diameter, thickness, bore, and hub |
| Mechanical | `hinge` | Alternating knuckles, pin clearance, and separate pin export |
| Mechanical | `snap_fit_box` | Cantilever tabs, mating pockets, and separate lid export |
| Mechanical | `nut_and_bolt_basic` | Non-threaded nut-and-bolt fit-check pair with separate nut export |
| Mechanical | `spacer` | Inner/outer diameter, height, and chamfer |
| Mechanical | `angle_bracket` | Two mounting legs, holes, and optional gussets |
| Engineering/lab | `test_tube_rack` | Tube grid, top/base plates, and supporting posts |
| Engineering/lab | `pcb_enclosure` | Board footprint, standoffs, ventilation, and removable lid |
| Engineering/lab | `sensor_mount` | Board plate, standoffs, and flange holes |
| Engineering/lab | `ventilation_box` | Vented enclosure, cable exit, and removable lid |
| Engineering/lab | `funnel` | Tapered bowl, continuous open throat, and straight outlet |
| Engineering/lab | `hose_adapter` | Two hose diameters, hollow transition, and retention rings |
| Modular | `stackable_box` | Open bin with an attached locating foot and stacking clearance |
| Modular | `gridfinity_bin` | Simplified Gridfinity-style footprint, scoop, and magnet holes |
| Modular | `interlocking_panel` | Edge tabs and matching slots |

### Example descriptions

- `Make a phone stand for a 75mm wide phone with a 20 degree angle and cable hole.`
- `Box with lid 120x80x60 mm with 0.4mm clearance.`
- `Cable clip for 6mm cable with mounting base and screw hole.`
- `Simple gear with 24 teeth, 40mm diameter, and 5mm bore.`
- `PCB enclosure for an 80x50 mm board with ventilation slots.`
- `Parts tray 160x100x20 mm with 3 compartments.`
- `Planter 90x80 mm with drainage holes and drip tray.`
- `Angle bracket 40x40x30 mm with mounting holes and gussets.`
- `Drawer pull with 96mm hole spacing, 28mm height, and 14mm grip width.`
- `Battery organizer with 18mm cell diameter, 12 cells, and 3 rows.`

The parser accepts explicit dimensions, labeled measurements, size presets, and supported feature names. Measurements in mm, cm, or inches are converted to millimeters. For phone stands, low angles such as `20 degrees` are interpreted as recline from upright and converted to the support angle from the build plate.

## Geometry, validation, and exports

The pipeline resolves a supported model, merges defaults with parsed intent and edited parameters, validates the final values, builds CadQuery solids, and exports the result.

Validation checks numeric ranges, integer counts, wall thickness, clearances, model-specific relationships, and rough overhang risks. Corrected parameters can recover a failed design. CAD construction/export failures return a structured error so the parameters can be revised.

Geometry refinements in this release include connected hook arms and mounting plates, correct extrusion widths, separately offset inner/outer rounded corners, equal-width organizer pockets, and attached stackable-bin feet. CAD surfaces determine reported bounds. STL tessellation uses **0.04 mm linear** and **0.08 radian angular** deflection; GLB previews are derived from the meshes.

| Format | Use |
| --- | --- |
| STL | Slicers and mesh-based 3D printing workflows; STL does not encode units |
| STEP | Editable solid geometry with explicit units; preferred for CAD/Fusion import |
| GLB | Browser preview and model inspection; may include multiple parts |

Models with accessories provide separate STL and STEP downloads for those parts, such as lids, hinge pins, nuts, or planter drip trays. Export coordinates use millimeter values. The viewer's unit convention is millimeters; check units when importing meshes into other applications.

Generated files are stored in `backend/out` during normal native development. Set `CADRIX_OUTPUT_DIR` to use another writable location. Containers use persistent storage mounted at `/app/data`.

## Optional local Ollama parser

The default rule-based parser needs no model server. To use Ollama, install and start it, make a model available locally, and enable **Settings → Design parser → Use local Ollama**.

If no model is configured, the parser queries installed models and chooses a preferred available model, falling back to `llama3.1:8b` as its default selection. You can set `CADRIX_OLLAMA_MODEL` to an installed model name. For example, set it before starting the app:

PowerShell:

```powershell
$env:CADRIX_OLLAMA_MODEL = "llama3.1:8b"
npm run dev
```

macOS/Linux:

```bash
export CADRIX_OLLAMA_MODEL=llama3.1:8b
npm run dev
```

The V2 parser uses `http://127.0.0.1:11434` by default. Override it with `CADRIX_OLLAMA_HOST`; `OLLAMA_HOST` and `OLLAMA_MODEL` are also recognized as fallbacks. If Ollama is unreachable or its response cannot be interpreted, the application uses the rule-based result and returns a warning. Ollama provides structured intent for the existing generators; it does not generate arbitrary executable CAD code.

For Docker, configure the parser host to an address reachable from inside the container and pass the variables through the container configuration. Container loopback refers to the container itself.

## API

Use `http://localhost:8000/docs` to try requests interactively during development.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/healthz` | Readiness status and registered model count |
| GET | `/v2/capabilities` | Model categories, examples, defaults, and parameter definitions |
| POST | `/v2/plan` | Resolve and validate a design without exporting geometry |
| POST | `/v2/generate` | Validate final parameters, build geometry, and return download URLs |
| GET | `/files/{filename}` | Download an exported model file |

Example body for **`POST /v2/plan`**:

```json
{
  "prompt": "Box with lid 120x80x60 mm with 0.4mm clearance.",
  "units": "mm",
  "model_type": "box_with_lid",
  "use_llm": false
}
```

Example body for **`POST /v2/generate`**, including explicit parameter overrides:

```json
{
  "prompt": "Box with lid 120x80x60 mm with 0.4mm clearance.",
  "model_type": "box_with_lid",
  "parameters": {
    "length_mm": 120,
    "width_mm": 80,
    "height_mm": 60,
    "lid_clearance_mm": 0.4
  },
  "use_llm": false
}
```

Prompts must contain 1–800 characters. `model_type` is optional when the parser can identify a model. Generation responses include `success`, resolved `parameters`, `intent`, `warnings`, `errors`, `assumptions`, `files`, and `metadata`. The `files` object contains `stl`, `step`, `glb`, and `extra_downloads`. Metadata includes estimated dimensions and a heuristic printability score.

Check **`success` and `errors` in the JSON body**: design validation or construction failures can return HTTP 200 with `success: false`. Request-schema errors return HTTP 422. Legacy `/capabilities`, `/plan`, and `/generate` routes remain available, but the workspace uses `/v2`.

## Production and Docker

From the repository root, build and start a local production instance:

```bash
docker compose up --build -d
```

Open **`http://localhost:8000`**. The production container serves the built frontend, API, and downloads from the same origin. Windows/macOS require Docker Desktop in Linux-container mode; Linux can use Docker Engine with the Compose plugin.

The container runs as a non-root user with a read-only application filesystem. Models persist in the Compose `models` volume. The service binds to host loopback by default. Stop it with `docker compose down`; the model volume is retained unless explicitly removed.

To change the published port or select a released image, copy `.env.example` to `.env` and configure `CADRIX_PORT` or `CADRIX_IMAGE`. See [CI/CD and releases](docs/ci-cd.md) for pulling images, checksum verification, and rollback by version or digest.

### Configuration

| Variable | Purpose |
| --- | --- |
| `CADRIX_OUTPUT_DIR` | Writable directory for generated files; defaults to `backend/out` natively |
| `CADRIX_FRONTEND_DIR` | Directory containing a built frontend `index.html`; enables frontend serving by FastAPI |
| `VITE_API_BASE_URL` | Optional frontend build-time API override, including `/v2`; defaults to `/v2` on the page's origin |
| `CADRIX_CORS_ORIGINS` | Comma-separated browser origins for a split-origin backend deployment |
| `CADRIX_OLLAMA_HOST` | Optional local parser server address |
| `CADRIX_OLLAMA_MODEL` | Optional installed parser model name |
| `CADRIX_PORT` | Compose host port; defaults to 8000 |
| `CADRIX_IMAGE` | Compose image reference; defaults to `cadrixai:local` |

Root `.env` settings are consumed by Compose; they are not automatically loaded into the backend process. Pass backend variables through the shell or container configuration. Vite loads frontend environment files from `frontend`; see `frontend/.env.example`. Development proxies `/v2` and `/files` to port 8000.

## CI/CD and release versioning

The [CI workflow](.github/workflows/ci.yml) checks pull requests, pushes to `main`/`master`, merge queues, and manual runs. Six application jobs cover Windows, Linux, and Apple Silicon macOS using these runtime pairs:

- Node **26** with Python **3.14.10**.
- Node **24** with Python **3.13**.

Each application job installs locked dependencies, runs frontend API and backend tests, builds the frontend, and exercises the production app over HTTP. Additional jobs validate workflow syntax, audit npm/Python dependencies, and build/test Linux containers on native x64 and ARM64 runners. **Required checks** aggregates the results; configure it as a required status in branch protection.

The [release workflow](.github/workflows/release.yml) runs on stable `vMAJOR.MINOR.PATCH` tags. After version validation and the full CI suite, it publishes:

- Linux x64/ARM64 GHCR images with version, major/minor, `latest`, and commit tags, plus SBOM and build provenance.
- A portable source ZIP containing the tested frontend build.
- A per-file release manifest and archive checksums.

For this release, use **`v2.1.0`**. Root `package.json`, `frontend/package.json`, and `backend/pyproject.toml` must all contain `2.1.0`, with their lockfiles synchronized. Package versions are checked before publishing. Weekly Dependabot updates cover Actions, npm, uv, and Docker.

GitHub Actions permissions, package visibility, branch protection, and tag rules must be configured in the hosting repository. This pipeline delivers images and release assets; deploying to a public host requires a chosen environment. See the complete [release and rollback guide](docs/ci-cd.md).

## Development and verification

Run the services separately when needed, from the repository root:

```bash
uv sync --directory backend --locked
uv run --directory backend --locked python -m uvicorn main:app --reload --port 8000
```

In another terminal:

```bash
npm ci --prefix frontend
npm run dev --prefix frontend
```

Run the frontend API tests, backend suite, production build, and HTTP smoke check:

```bash
npm test
uv run --directory backend --locked python -m unittest discover -s tests -v
npm run build --prefix frontend
uv run --directory backend --locked python ../scripts/smoke.py
```

The backend suite currently contains **44 tests**, including parser/API behavior, registry coverage, valid CAD solids and watertight default meshes, requested dimensions, feature variants, parameter boundaries, accessory exports, STEP units, and release packaging. The Node suite checks same-origin API requests, parameter payloads, and HTTP error propagation. The HTTP smoke check serves the built frontend, generates a box and lid, and downloads the resulting files.

With Docker running, verify a production image:

```bash
docker build --tag cadrixai:ci .
uv run --directory backend --locked python ../scripts/container_smoke.py --image cadrixai:ci
```

Manage backend dependencies with `uv add --directory backend <package>` or `uv remove --directory backend <package>`. Include both `pyproject.toml` and `uv.lock` after changes. Include `frontend/package.json` and `frontend/package-lock.json` after frontend dependency changes.

### Troubleshooting

| Symptom | Action |
| --- | --- |
| `uv` is not recognized | Install uv and reopen the terminal |
| Missing uv-managed Python executable | Run `npm run dev` to restore the pinned runtime and synchronize the environment |
| An older Node installation fails to start Vite | Use Node 26 or 24, then run `npm run dev` again |
| Port 5173 or 8000 is occupied | Stop the conflicting service before using the development launcher |
| Native installation fails on an Intel Mac | Use the x64 Docker image |
| A design fails validation | Review errors in Adjust, correct the affected values, and generate again |
| Preview cannot load but generation succeeded | Inspect the preview error; the generated download files may still be available |
| Microphone or recognition is unavailable | Check browser permissions/support or enter the description as text |

## Project structure

```text
CadrixAI/
├── .github/
│   ├── workflows/             # CI and release pipelines
│   └── dependabot.yml
├── backend/
│   ├── main.py                # FastAPI, legacy routes, downloads, static frontend
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── .python-version
│   ├── cadrix_v2/
│   │   ├── app.py             # /v2 routes
│   │   ├── schemas.py
│   │   ├── registry.py        # Model definitions, defaults, and examples
│   │   ├── service.py         # Planning and generation orchestration
│   │   ├── validators.py
│   │   ├── library_validation.py
│   │   ├── geometry.py
│   │   ├── geometry_core.py   # Shared solid-building primitives
│   │   ├── library_geometry.py
│   │   ├── exporters.py
│   │   ├── runtime.py         # Shared output directory configuration
│   │   ├── prompt_utils.py
│   │   └── parsers/
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── useModelViewport.js
│       ├── styles.css
│       └── components/
├── scripts/
│   ├── dev.mjs
│   ├── smoke.py
│   ├── container_smoke.py
│   ├── package_release.py
│   └── tests/
├── docs/ci-cd.md
├── Dockerfile
├── compose.yaml
├── .env.example
├── .node-version
└── package.json
```

The request flow is:

```text
Description or template
  → rule-based parser or optional Ollama parser
  → registered model, defaults, and edited parameters
  → validation
  → CadQuery solid geometry
  → STL / STEP / GLB exports
  → browser preview and downloads
```

Keep `node_modules`, `.venv*`, `dist`, `__pycache__`, `backend/out`, local reports, release bundles, and `.env` files out of version control. Source, manifests, lockfiles, example environment files, documentation, and workflows belong in the repository. Existing local files remain usable after they are untracked.

## Current limitations

- Generation uses the registered parametric models; arbitrary free-form CAD and assembly-aware modeling are not implemented.
- Printability scores and overhang checks are heuristics. Parts have not been physically validated for strength, fit, or load capacity. Test critical dimensions with a small print; clearances are radial unless a parameter states otherwise.
- `simple_gear` uses approximate teeth; `nut_and_bolt_basic` is non-threaded. The Gridfinity-style bin is simplified. The hose adapter is intended for unpressurized hobby airflow.
- Browser speech recognition is optional and depends on browser capabilities and permissions.
- Generated model storage has no automatic retention policy. Plan storage cleanup for long-running deployments.
- The service has no authentication or per-user model isolation. Public hosting needs an appropriate HTTPS/authentication gateway, request limits, and resource limits.

Future work includes richer assemblies, improved gear/thread profiles, slicing integration, print-time estimation, material guidance, and simulation-based strength checks.

## License

CadrixAI is licensed under the [MIT License](LICENSE).
