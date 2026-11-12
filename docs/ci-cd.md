# CI/CD and releases

GitHub Actions checks pull requests, pushes to `main`/`master`, merge queues, and manual runs. A stable `vMAJOR.MINOR.PATCH` tag runs the entire pipeline again before publishing a GitHub Release and a GHCR image. Publication uses the repository's scoped `GITHUB_TOKEN`; no personal access token or cloud account is required.

## Supported platforms and runtimes

| Platform | Architectures checked | Runtime pairs |
| --- | --- | --- |
| Linux | x64 application; x64 and ARM64 containers | Node 26 / Python 3.14.10; Node 24 / Python 3.13 |
| Windows | x64 application | Both pairs |
| macOS | Apple Silicon application; Intel via x64 container | Both pairs on Apple Silicon |

The two Node lines are the [current and previous LTS lines](https://github.com/nodejs/Release), selected in November 2026. CI resolves the latest patch in each Node line and in Python 3.13. The default development and container Python is pinned to 3.14.10. Python 3.15 is excluded because the [locked native CAD package](https://pypi.org/project/cadquery-ocp/7.9.3.1.1/#files) supports Python 3.13/3.14 and has no 3.15 wheels. `requires-python` enforces this boundary.

Native Intel macOS installation is not supported by the current dependency stack: [Numba stopped publishing Intel Mac wheels starting with 0.63](https://numba.readthedocs.io/en/stable/release/0.63.0-notes.html), and the locked NLopt release also lacks them. Intel Mac users should use Docker Desktop with the Linux x64 image. This avoids silently compiling LLVM or downgrading the geometry stack.

The six application jobs install from lockfiles, test CAD geometry and release packaging, test frontend API requests, build the frontend, and start the production app over HTTP. The HTTP check loads assets, generates a box and lid, downloads STL/STEP/GLB exports, checks their origin, and verifies missing routes do not return a misleading frontend page.

Two additional jobs build and smoke-test Linux containers on native x64 and ARM64 runners. The test enforces a non-root user and a read-only filesystem with separate writable model storage. Dependency gates reject high/critical npm advisories and any reported Python dependency advisory. Workflow validation checks Actions syntax and expressions. The final **Required checks** job fails if any gate fails or is skipped.

Actions and container bases are pinned to verified digests/commits. Dependabot opens weekly updates for Actions, npm, uv, and Docker. Review those PRs through the same checks. Audit reports and the tested release bundle are retained for 14 days.

## Activate in GitHub

1. Push this project, including `.github`, both lockfiles, and all application source, to your GitHub repository.
2. Enable GitHub Actions and allow the workflow's scoped package/release write permissions under your organization policies. New GHCR packages inherit your repository/account's visibility policy; change package visibility explicitly if public pulls are desired.
3. Protect the default branch with the **Required checks** status and review requirements. Protect `v*` tags using a repository ruleset so only release maintainers can create them. The workflow does not bypass these settings.
4. Let the initial CI run pass before creating a release tag.

Fork pull requests receive read-only permissions and never publish. There is no `pull_request_target` workflow or secret-dependent check. Repository settings and GitHub-hosted macOS/Linux runners can only be validated after the first remote run.

## Publish a release

Keep the version in root `package.json`, `frontend/package.json`, and `backend/pyproject.toml` identical. Update the frontend lockfile with `npm install --prefix frontend --package-lock-only` and the backend lockfile with `uv lock --directory backend`. Commit the updated source and locks, let CI pass, then create and push the matching tag, for example:

```bash
git tag v2.1.0
git push origin v2.1.0
```

The release validates the tag against all three manifests, reruns every gate, and publishes:

- `ghcr.io/owner/repository:2.1.0`, `:2.1`, `:latest`, and a full commit tag; repository/image names are lowercase. Each image supports `linux/amd64` and `linux/arm64`, with SBOM and build provenance attestations.
- `cadrixai-2.1.0.zip`, containing application source, lockfiles, documentation, workflows, and the tested frontend build. Dependencies, Python, Node, Docker, credentials, and generated user models are excluded.
- `release-manifest.json` with per-file hashes and the originating commit, plus `SHA256SUMS` for the ZIP.

The release job downloads the tested CI artifact instead of rebuilding the ZIP. It verifies its checksum, uploads assets to a draft release, then publishes. Rerunning publication preserves assets of an already published release. Version tags must remain immutable; release a new patch for fixes.

Verify a downloaded ZIP using `sha256sum --check SHA256SUMS` on Linux or `shasum -a 256 -c SHA256SUMS` on macOS. In PowerShell, compare `(Get-FileHash .\cadrixai-2.1.0.zip -Algorithm SHA256).Hash` with the corresponding entry in `SHA256SUMS`.

## Run or roll back a container

Docker Desktop in Linux-container mode is required on Windows/macOS. Linux can use Docker Engine with the Compose plugin. From the repository or extracted release:

```bash
docker compose up --build -d
```

Open `http://localhost:8000`. The built frontend, API, and downloads share one origin. `/healthz` reports application readiness. Generated files persist in the Compose `models` volume (named `<project>_models` by default); the application filesystem is read-only. Compose binds to loopback by default.

To use a published image, copy `.env.example` to `.env`, set `CADRIX_IMAGE=ghcr.io/owner/repository:2.1.0` (or the immutable `@sha256:...` reference shown in the release), then run:

```bash
docker compose pull
docker compose up -d --no-build
```

For rollback, select the previous known-good version/digest in `.env` and repeat those two commands. The model volume survives replacement. Avoid using `latest` where repeatable deployments matter. Private packages require `docker login ghcr.io` with an account authorized to read the package.

The pipeline delivers releases and images; deploying to a public host requires a chosen environment. Before exposing this CAD service publicly, put authentication, HTTPS, request limits, and resource limits at your hosting gateway. The app currently has no user accounts or per-user model isolation.

## Local verification

On Windows, Apple Silicon macOS, or Linux, install Node 26 (or 24) and uv, then run from the repository root:

```bash
npm ci --prefix frontend
npm test
uv sync --directory backend --locked
uv run --directory backend --locked python -m unittest discover -s tests -v
npm run build --prefix frontend
uv run --directory backend --locked python ../scripts/smoke.py
uv run --directory backend --locked python ../scripts/package_release.py
docker build --tag cadrixai:ci .
python scripts/container_smoke.py --image cadrixai:ci
```

The last command can instead use `uv run --directory backend --locked python ../scripts/container_smoke.py --image cadrixai:ci` if `python` is not on PATH. To test Python 3.13, set `UV_PYTHON=3.13` and `UV_PROJECT_ENVIRONMENT` to a separate environment path before the uv commands. The normal `npm run dev` launcher continues to use pinned Python 3.14.10.

Production configuration: `CADRIX_FRONTEND_DIR` points to a built frontend directory; `CADRIX_OUTPUT_DIR` selects writable model storage. A split-origin frontend can set `VITE_API_BASE_URL` at build time and a comma-separated `CADRIX_CORS_ORIGINS` on the backend. Same-origin deployment needs neither override. Configure trusted proxy headers explicitly at the hosting gateway if it terminates HTTPS.
