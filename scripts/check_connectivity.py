#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
        unknown = [k for k in overrides.keys() if k not in params]
        if unknown:
            raise ValueError(f"Unknown PARAMS keys: {', '.join(sorted(unknown))}")
        params.update(overrides)
    return params


def verbose_report(part_name: str, part) -> None:
    """Print extended diagnostics: topology counts, bbox, volume, watertight."""
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_VERTEX
    from OCP.TopExp import TopExp_Explorer

    wrapped = part.val().wrapped

    for label, ttype in [
        ("shells", TopAbs_SHELL),
        ("faces", TopAbs_FACE),
        ("edges", TopAbs_EDGE),
        ("vertices", TopAbs_VERTEX),
    ]:
        exp = TopExp_Explorer(wrapped, ttype)
        n = 0
        while exp.More():
            n += 1
            exp.Next()
        print(f"  {part_name} {label}: {n}")

    box = Bnd_Box()
    BRepBndLib.Add_s(wrapped, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    print(
        f"  {part_name} bbox: ({xmin:.1f}, {ymin:.1f}, {zmin:.1f})"
        f" -> ({xmax:.1f}, {ymax:.1f}, {zmax:.1f})"
    )
    print(
        f"  {part_name} size: "
        f"{xmax - xmin:.1f} x {ymax - ymin:.1f} x {zmax - zmin:.1f} mm"
    )

    props = GProp_GProps()
    try:
        BRepGProp.VolumeProperties_s(wrapped, props)
        print(f"  {part_name} volume: {props.Mass():.1f} mm3")
    except Exception:
        pass

    props2 = GProp_GProps()
    try:
        BRepGProp.SurfaceProperties_s(wrapped, props2)
        print(f"  {part_name} surface_area: {props2.Mass():.1f} mm2")
    except Exception:
        pass

    solid_count = part.solids().size()
    shell_exp = TopExp_Explorer(wrapped, TopAbs_SHELL)
    shell_count = 0
    while shell_exp.More():
        shell_count += 1
        shell_exp.Next()
    if solid_count > 0 and shell_count == solid_count:
        print(f"  {part_name} watertight: yes")
    elif solid_count == 0:
        print(f"  {part_name} watertight: n/a")
    else:
        print(
            f"  {part_name} watertight: possibly not"
            f" ({shell_count} shells / {solid_count} solids)"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check model connectivity/validity")
    parser.add_argument(
        "--model",
        required=True,
        help="Python module name (e.g. zero2w_waveshare213_ir_case)",
    )
    parser.add_argument("--params", type=Path, help="JSON file for PARAMS overrides")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show extended diagnostics (topology, bbox, volume)",
    )
    args = parser.parse_args()
    model_module = importlib.import_module(args.model)
    if not hasattr(model_module, "build_model"):
        raise ValueError(f"Model module '{args.model}' must define build_model(p=PARAMS)")
    overrides = load_overrides(args.params) if args.params else None
    params = merged_params(model_module, overrides)
    model = model_module.build_model(p=params)

    model_name = model.get("name", args.model)
    parts = model.get("parts")
    if not isinstance(parts, dict) or not parts:
        raise ValueError("build_model() must return a non-empty 'parts' dict")

    print(f"[{model_name}]")
    all_ok = True
    for part_name, part in parts.items():
        solid_count = part.solids().size()
        is_valid = part.val().isValid()
        print(f"{part_name} solids: {solid_count}")
        print(f"{part_name} isValid: {is_valid}")
        if args.verbose:
            verbose_report(part_name, part)
        all_ok = all_ok and solid_count == 1 and is_valid
    print(f"PASS: {all_ok}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
