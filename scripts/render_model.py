#!/usr/bin/env python3
"""Multi-angle 3D model renderer — outputs PNG images for visual inspection.

Supports both --model (build from module) and --file (load exported STL/STEP).
"""
from __future__ import annotations

import argparse
import importlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

VIEWS = {
    "front": (0, 0, "Front"),
    "back": (0, 180, "Back"),
    "right": (0, -90, "Right"),
    "left": (0, 90, "Left"),
    "top": (90, 0, "Top"),
    "bottom": (-90, 0, "Bottom"),
    "iso": (30, -45, "Isometric"),
    "iso2": (30, 135, "Isometric 2"),
}


def triangulate_cq_shape(shape):
    """Triangulate a CadQuery Workplane shape, returning (N, 3, 3) vertex array."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    wrapped = shape.val().wrapped
    BRepMesh_IncrementalMesh(wrapped, 0.1)

    all_tris = []
    exp = TopExp_Explorer(wrapped, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face_s(exp.Value())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            trsf = loc.Transformation()
            pts = []
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(trsf)
                pts.append((p.X(), p.Y(), p.Z()))
            pts = np.array(pts)
            for i in range(1, tri.NbTriangles() + 1):
                t = tri.Triangle(i)
                i1, i2, i3 = t.Get()
                all_tris.append([pts[i1 - 1], pts[i2 - 1], pts[i3 - 1]])
        exp.Next()

    return np.array(all_tris, dtype=np.float32)


def load_stl_triangles(filepath: str):
    """Parse binary/ASCII STL, returning (N, 3, 3) vertex array."""
    import re

    with open(filepath, "rb") as f:
        header = f.read(80)
        if b"solid" in header[:5]:
            f.seek(0)
            text = f.read().decode("ascii", errors="ignore")
            if "facet normal" in text:
                matches = re.findall(
                    r"vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", text
                )
                verts = np.array(
                    [[float(x), float(y), float(z)] for x, y, z in matches],
                    dtype=np.float32,
                )
                return verts.reshape(-1, 3, 3)
    with open(filepath, "rb") as f:
        f.seek(80)
        num_tri = struct.unpack("<I", f.read(4))[0]
    with open(filepath, "rb") as f:
        f.seek(84)
        vertices = np.zeros((num_tri, 3, 3), dtype=np.float32)
        for i in range(num_tri):
            data = f.read(50)
            vals = struct.unpack("<12fH", data)
            vertices[i, 0] = vals[3:6]
            vertices[i, 1] = vals[6:9]
            vertices[i, 2] = vals[9:12]
    return vertices


def load_step_triangles(filepath: str):
    """Load STEP file and triangulate, returning (N, 3, 3) vertex array."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    reader = STEPControl_Reader()
    reader.ReadFile(filepath)
    reader.TransferRoots()
    shape = reader.OneShape()
    BRepMesh_IncrementalMesh(shape, 0.1)

    all_tris = []
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face_s(exp.Value())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            trsf = loc.Transformation()
            pts = []
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(trsf)
                pts.append((p.X(), p.Y(), p.Z()))
            pts = np.array(pts)
            for i in range(1, tri.NbTriangles() + 1):
                t = tri.Triangle(i)
                i1, i2, i3 = t.Get()
                all_tris.append([pts[i1 - 1], pts[i2 - 1], pts[i3 - 1]])
        exp.Next()

    return np.array(all_tris, dtype=np.float32)


def render_view(triangles, elev, azim, title, output_path):
    """Render a single view to PNG."""
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection="3d")

    if len(triangles) > 20000:
        idx = np.random.choice(len(triangles), 20000, replace=False)
        tris = triangles[idx]
    else:
        tris = triangles

    poly = Poly3DCollection(
        tris, alpha=0.7, edgecolor="#444444", linewidth=0.1, facecolor="#b0c4de"
    )
    ax.add_collection3d(poly)

    all_pts = tris.reshape(-1, 3)
    mins = all_pts.min(axis=0)
    maxs = all_pts.max(axis=0)
    center = (mins + maxs) / 2
    span = (maxs - mins).max() / 2 * 1.1

    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(center[2] - span, center[2] + span)

    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title, fontsize=14)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


def load_overrides(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("params JSON must be an object")
    return data


def merged_params(model_module, overrides: dict | None) -> dict:
    if not hasattr(model_module, "PARAMS"):
        raise ValueError("Model module must define PARAMS")
    params = dict(model_module.PARAMS)
    if overrides:
        unknown = [k for k in overrides if k not in params]
        if unknown:
            raise ValueError(f"Unknown PARAMS keys: {', '.join(sorted(unknown))}")
        params.update(overrides)
    return params


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-angle 3D model renderer")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--model", help="Python module name (e.g. prism_case)")
    src.add_argument("--file", type=Path, help="Path to STL or STEP file")
    parser.add_argument(
        "--params", type=Path, help="JSON file for PARAMS overrides (--model only)"
    )
    parser.add_argument("--part", help="Render a single part (--model only)")
    parser.add_argument(
        "--out", type=Path, default=ROOT / "renders", help="Output directory"
    )
    parser.add_argument(
        "--views",
        default=None,
        help="Comma-separated: front,back,right,left,top,bottom,iso,iso2",
    )
    args = parser.parse_args()

    view_names = (
        args.views.split(",")
        if args.views
        else ["front", "right", "top", "bottom", "iso", "iso2"]
    )
    args.out.mkdir(parents=True, exist_ok=True)

    render_jobs: list[tuple[str, np.ndarray]] = []

    if args.model:
        mod = importlib.import_module(args.model)
        if not hasattr(mod, "build_model"):
            raise ValueError(f"Module '{args.model}' must define build_model()")
        overrides = load_overrides(args.params) if args.params else None
        params = merged_params(mod, overrides)
        model = mod.build_model(p=params)
        parts = model.get("parts", {})
        if not parts:
            raise ValueError("build_model() returned no parts")
        for pname, shape in parts.items():
            if args.part and pname != args.part:
                continue
            print(f"Triangulating {pname}...")
            tris = triangulate_cq_shape(shape)
            print(f"  {len(tris)} triangles")
            render_jobs.append((f"{model.get('name', args.model)}_{pname}", tris))
    else:
        fp = args.file
        ext = fp.suffix.lower().lstrip(".")
        print(f"Loading {fp}...")
        if ext in ("step", "stp"):
            tris = load_step_triangles(str(fp))
        elif ext == "stl":
            tris = load_stl_triangles(str(fp))
        else:
            raise ValueError(f"Unsupported format: {ext}")
        print(f"  {len(tris)} triangles")
        render_jobs.append((fp.stem, tris))

    for label, tris in render_jobs:
        for vname in view_names:
            elev, azim, title = VIEWS[vname]
            out_path = args.out / f"{label}_{vname}.png"
            print(f"  Rendering {label} {vname}...", end=" ", flush=True)
            render_view(tris, elev, azim, f"{label} — {title}", out_path)
            print(f"-> {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
