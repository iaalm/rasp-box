#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from cadquery import exporters

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_overrides(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("params JSON must be an object")
    return data


def load_model_module(name: str):
    return importlib.import_module(name)


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified exporter for CadQuery models")
    parser.add_argument(
        "--model",
        required=True,
        help="Python module name (e.g. zero2w_waveshare213_ir_case)",
    )
    parser.add_argument("--prefix", help="output filename prefix")
    parser.add_argument("--params", type=Path, help="JSON file for PARAMS overrides")
    parser.add_argument("--out", type=Path, default=ROOT / "exports")
    args = parser.parse_args()

    model_module = load_model_module(args.model)
    if not hasattr(model_module, "build_model"):
        raise ValueError(f"Model module '{args.model}' must define build_model(p=PARAMS)")
    prefix = args.prefix or getattr(model_module, "MODEL_NAME", args.model)

    overrides = load_overrides(args.params) if args.params else None
    params = merged_params(model_module, overrides)
    args.out.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in args.out.glob(f"{prefix}*")}
    model = model_module.build_model(p=params)
    parts = model.get("parts")
    asm = model.get("assembly")
    if not isinstance(parts, dict) or not parts:
        raise ValueError("build_model() must return a non-empty 'parts' dict")

    for part_name, shape in parts.items():
        exporters.export(shape, str(args.out / f"{prefix}_{part_name}.stl"))
        exporters.export(shape, str(args.out / f"{prefix}_{part_name}.step"))
    if asm is not None:
        try:
            asm.save(str(args.out / f"{prefix}.step"))
        except Exception:
            pass
    after = {p.name for p in args.out.glob(f"{prefix}*")}
    created = sorted(after - before)

    print("Export complete:")
    if created:
        for name in created:
            print(f"  - {args.out / name}")
    else:
        for path in sorted(args.out.glob(f"{prefix}*")):
            if path.is_file():
                print(f"  - {path}")


if __name__ == "__main__":
    main()
