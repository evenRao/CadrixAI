from __future__ import annotations

import os
from pathlib import Path

import cadquery as cq
import trimesh
from cadquery import exporters
from fastapi import Request

from cadrix_v2.geometry import GeneratedGeometry
from cadrix_v2.schemas import DownloadLink, FileBundle


BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "out"
OUT_DIR.mkdir(exist_ok=True)

APP_NAME = "CadrixAI"


def export_stl(solid: cq.Workplane, stl_path: Path) -> None:
    file_id = stl_path.stem
    exporters.export(solid, str(stl_path), exportType="STL", opt={"ascii": True})
    try:
        lines = stl_path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
        if lines and lines[0].lower().startswith("solid"):
            lines[0] = f"solid {APP_NAME}_{file_id}\n"
            stl_path.write_text("".join(lines), encoding="utf-8")
    except Exception:
        pass


def export_step(solid: cq.Workplane, step_path: Path) -> None:
    exporters.export(solid, str(step_path), exportType="STEP")


def export_glb_from_stl(stl_path: Path, glb_path: Path) -> None:
    mesh = trimesh.load(str(stl_path), force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = mesh.dump(concatenate=True)
    mesh.apply_translation(-mesh.centroid)
    scene = trimesh.Scene(mesh)
    scene.metadata["generator"] = APP_NAME
    scene.metadata["unit"] = "millimeter"
    scene.export(str(glb_path))


def _url_for_file(request: Request, filename: str) -> str:
    return str(request.url_for("get_file", filename=filename))


def export_generated_geometry(geometry: GeneratedGeometry, file_id: str, request: Request) -> FileBundle:
    primary_stl = OUT_DIR / f"{file_id}.stl"
    primary_step = OUT_DIR / f"{file_id}.step"
    primary_glb = OUT_DIR / f"{file_id}.glb"
    export_stl(geometry.primary_solid, primary_stl)
    export_step(geometry.primary_solid, primary_step)
    export_glb_from_stl(primary_stl, primary_glb)

    preview_glb_url = _url_for_file(request, primary_glb.name)
    if geometry.preview_solid is not geometry.primary_solid:
        preview_stl = OUT_DIR / f"{file_id}_preview.stl"
        preview_glb = OUT_DIR / f"{file_id}_preview.glb"
        export_stl(geometry.preview_solid, preview_stl)
        export_glb_from_stl(preview_stl, preview_glb)
        preview_glb_url = _url_for_file(request, preview_glb.name)

    extras: list[DownloadLink] = []
    for part in geometry.extra_parts:
        stem = f"{file_id}_{part.file_suffix}"
        extra_stl = OUT_DIR / f"{stem}.stl"
        extra_step = OUT_DIR / f"{stem}.step"
        export_stl(part.solid, extra_stl)
        export_step(part.solid, extra_step)
        extras.append(DownloadLink(label=f"{part.label} STL", url=_url_for_file(request, extra_stl.name)))
        extras.append(DownloadLink(label=f"{part.label} STEP", url=_url_for_file(request, extra_step.name)))

    return FileBundle(
        stl=_url_for_file(request, primary_stl.name),
        glb=preview_glb_url,
        step=_url_for_file(request, primary_step.name),
        extra_downloads=extras,
    )
