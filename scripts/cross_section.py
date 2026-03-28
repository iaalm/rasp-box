#!/usr/bin/env python3
"""Cross-section a 3D model at a specified plane, outputting a 2D profile PNG.

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


def parse_plane(plane_str: str) -> tuple[str, float]:
    axis, val = plane_str.split("=")
    return axis.upper().strip(), float(val.strip())


def section_occ_shape(wrapped, axis: str, value: float):
    """Section an OCC TopoDS_Shape at the given axis-aligned plane."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.GCPnts import GCPnts_UniformAbscissa
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Dir, gp_Pln, gp_Pnt

    dirs = {"X": gp_Dir(1, 0, 0), "Y": gp_Dir(0, 1, 0), "Z": gp_Dir(0, 0, 1)}
    origins = {
        "X": gp_Pnt(value, 0, 0),
        "Y": gp_Pnt(0, value, 0),
        "Z": gp_Pnt(0, 0, value),
    }
    plane = gp_Pln(origins[axis], dirs[axis])

    section = BRepAlgoAPI_Section(wrapped, plane)
    section.Build()
    result = section.Shape()

    segments = []
    exp = TopExp_Explorer(result, TopAbs_EDGE)
    while exp.More():
        edge = TopoDS.Edge_s(exp.Value())
        curve = BRepAdaptor_Curve(edge)
        u_start = curve.FirstParameter()
        u_end = curve.LastParameter()
        n_pts = max(2, int((u_end - u_start) * 20) + 2)
        try:
            discretizer = GCPnts_UniformAbscissa(curve, n_pts, u_start, u_end)
            pts = []
            for i in range(1, discretizer.NbPoints() + 1):
                u = discretizer.Parameter(i)
                p = curve.Value(u)
                pts.append((p.X(), p.Y(), p.Z()))
        except Exception:
            pts = []
            for i in range(n_pts):
                u = u_start + (u_end - u_start) * i / (n_pts - 1)
                p = curve.Value(u)
                pts.append((p.X(), p.Y(), p.Z()))
        if len(pts) >= 2:
            segments.append(np.array(pts))
        exp.Next()

    return segments


def section_stl(filepath: str, axis: str, value: float):
    """Compute STL triangle-plane intersections."""
    with open(filepath, "rb") as f:
        f.seek(80)
        num_tri = struct.unpack("<I", f.read(4))[0]
        triangles = np.zeros((num_tri, 3, 3), dtype=np.float32)
        for i in range(num_tri):
            data = f.read(50)
            vals = struct.unpack("<12fH", data)
            triangles[i, 0] = vals[3:6]
            triangles[i, 1] = vals[6:9]
            triangles[i, 2] = vals[9:12]

    axis_idx = {"X": 0, "Y": 1, "Z": 2}[axis]
    segments = []
    for tri in triangles:
        pts = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            va, vb = a[axis_idx] - value, b[axis_idx] - value
            if va * vb < 0:
                t = va / (va - vb)
                pts.append(a + t * (b - a))
            elif abs(va) < 1e-6:
                pts.append(a.copy())
        if len(pts) >= 2:
            segments.append(np.array(pts[:2]))
    return segments


def section_step(filepath: str, axis: str, value: float):
    """Load STEP and section using OCC."""
    from OCP.STEPControl import STEPControl_Reader

    reader = STEPControl_Reader()
    reader.ReadFile(filepath)
    reader.TransferRoots()
    shape = reader.OneShape()
    return section_occ_shape(shape, axis, value)


def plot_section(segments, axis: str, value: float, title: str, output_path: Path):
    axis_map = {
        "X": ("Y", "Z", 1, 2),
        "Y": ("X", "Z", 0, 2),
        "Z": ("X", "Y", 0, 1),
    }
    xlabel, ylabel, idx_h, idx_v = axis_map[axis]

    fig, ax = plt.subplots(figsize=(10, 8))
    for seg in segments:
        ax.plot(seg[:, idx_h], seg[:, idx_v], "b-", linewidth=1.0)
    ax.set_xlabel(f"{xlabel} (mm)", fontsize=12)
    ax.set_ylabel(f"{ylabel} (mm)", fontsize=12)
    ax.set_title(f"{title} — section at {axis}={value} mm", fontsize=14)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
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
    parser = argparse.ArgumentParser(
        description="Cross-section 3D model at a plane"
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--model", help="Python module name (e.g. prism_case)")
    src.add_argument("--file", type=Path, help="Path to STL or STEP file")
    parser.add_argument(
        "--params", type=Path, help="JSON file for PARAMS overrides (--model only)"
    )
    parser.add_argument(
        "--plane", required=True, help="Cutting plane, e.g. Z=35, Y=4, X=10"
    )
    parser.add_argument("--part", help="Section a single part (--model only)")
    parser.add_argument(
        "--out", type=Path, default=ROOT / "renders", help="Output directory"
    )
    args = parser.parse_args()

    axis, value = parse_plane(args.plane)
    args.out.mkdir(parents=True, exist_ok=True)

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
        model_name = model.get("name", args.model)
        for pname, shape in parts.items():
            if args.part and pname != args.part:
                continue
            wrapped = shape.val().wrapped
            print(f"Sectioning {pname} at {axis}={value}...")
            segments = section_occ_shape(wrapped, axis, value)
            print(f"  {len(segments)} edge segments")
            if not segments:
                print("  WARNING: No intersections. Check plane is within bounds.")
                continue
            out_path = args.out / f"{model_name}_{pname}_section_{axis}{int(value)}.png"
            plot_section(segments, axis, value, f"{model_name} {pname}", out_path)
            print(f"  -> {out_path}")
    else:
        fp = args.file
        ext = fp.suffix.lower().lstrip(".")
        print(f"Sectioning {fp} at {axis}={value}...")
        if ext in ("step", "stp"):
            segments = section_step(str(fp), axis, value)
        elif ext == "stl":
            segments = section_stl(str(fp), axis, value)
        else:
            raise ValueError(f"Unsupported format: {ext}")
        print(f"  {len(segments)} edge segments")
        if not segments:
            print("  WARNING: No intersections. Check plane is within bounds.")
            return
        out_path = args.out / f"{fp.stem}_section_{axis}{int(value)}.png"
        plot_section(segments, axis, value, fp.stem, out_path)
        print(f"  -> {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
