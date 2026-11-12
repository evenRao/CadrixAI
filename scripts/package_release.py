"""Create a portable, checksummed source + built-frontend distribution."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ("README.md", "package.json", ".node-version", ".env.example", ".gitignore", ".gitattributes", "Dockerfile", ".dockerignore", "compose.yaml", ".github", "docs", "scripts", "backend/main.py", "backend/cadrix_v2", "backend/tests", "backend/pyproject.toml", "backend/uv.lock", "backend/.python-version", "frontend/package.json", "frontend/package-lock.json", "frontend/index.html", "frontend/vite.config.js", "frontend/.env.example", "frontend/src")
EXCLUDED = {"node_modules", "__pycache__", ".git", ".ci-tools", ".reports", ".release", "out", "dist"}


def validate_version(tag, root=ROOT):
    if not re.fullmatch(r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", tag):
        raise ValueError("Releases require a stable vMAJOR.MINOR.PATCH tag.")
    version = tag[1:]
    manifests = [json.loads((root / "package.json").read_text())["version"], json.loads((root / "frontend/package.json").read_text())["version"], tomllib.loads((root / "backend/pyproject.toml").read_text())["project"]["version"]]
    if any(item != version for item in manifests):
        raise ValueError(f"Tag {tag} must match root, frontend, and backend versions: {manifests}")
    return version


def collect_files(root, frontend_dir):
    files = {}
    for entry in ALLOW:
        path = root / entry
        if not path.exists():
            continue
        for item in sorted(path.rglob("*")) if path.is_dir() else [path]:
            relative = item.relative_to(root)
            if item.is_symlink() or not item.is_file() or not item.resolve().is_relative_to(root.resolve()):
                continue
            if any(part in EXCLUDED or part.startswith(".venv") for part in relative.parts):
                continue
            if item.name.startswith(".env") and item.name != ".env.example":
                continue
            if item.suffix in {".pyc", ".log"}:
                continue
            files[relative.as_posix()] = item.read_bytes()
    if not (frontend_dir / "index.html").is_file():
        raise ValueError("Build the frontend before creating a release.")
    for item in sorted(frontend_dir.rglob("*")):
        if item.is_file() and not item.is_symlink() and item.resolve().is_relative_to(frontend_dir.resolve()):
            files["frontend/dist/" + item.relative_to(frontend_dir).as_posix()] = item.read_bytes()
    return files


def package(tag, output, frontend_dir, commit="working-tree", root=ROOT):
    version = validate_version(tag, root)
    files = collect_files(root, frontend_dir)
    manifest = {"version": version, "tag": tag, "commit": commit, "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    files["release-manifest.json"] = manifest_bytes
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"cadrixai-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(f"cadrixai-{version}/{name}", date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data)
    (output / "release-manifest.json").write_bytes(manifest_bytes)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default=os.getenv("RELEASE_TAG"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / ".release")
    parser.add_argument("--frontend-dir", type=Path, default=ROOT / "frontend/dist")
    args = parser.parse_args()
    tag = args.tag or (os.getenv("GITHUB_REF_NAME") if os.getenv("GITHUB_REF_TYPE") == "tag" else None) or "v" + json.loads((ROOT / "package.json").read_text())["version"]
    version = validate_version(tag)
    if os.getenv("GITHUB_OUTPUT"):
        repository = os.getenv("GITHUB_REPOSITORY", "").lower()
        if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", repository):
            raise ValueError("Invalid GitHub repository name")
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"version={version}\nimage=ghcr.io/{repository}\n")
    if args.check:
        print(f"Release tag and all package versions agree: {tag}")
    else:
        print(package(tag, args.output, args.frontend_dir, os.getenv("GITHUB_SHA", "working-tree")))


if __name__ == "__main__":
    main()
