#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import zero2w_waveshare213_ir_case as model


def load_overrides(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("params JSON must be an object of key/value pairs")
    return data


def merged_params(overrides: dict | None) -> dict:
    params = dict(model.PARAMS)
    if overrides:
        unknown = [k for k in overrides.keys() if k not in params]
        if unknown:
            raise ValueError(f"Unknown PARAMS keys: {', '.join(sorted(unknown))}")
        params.update(overrides)
    return params


def main() -> None:
    parser = argparse.ArgumentParser(description="Export case STL/STEP files")
    parser.add_argument("--prefix", default="zero2w_waveshare213_ir_case")
    parser.add_argument("--params", type=Path, help="JSON file for PARAMS overrides")
    parser.add_argument("--out", type=Path, default=ROOT / "exports")
    args = parser.parse_args()

    overrides = load_overrides(args.params) if args.params else None
    params = merged_params(overrides)
    model.export_all(prefix=args.prefix, p=params, output_dir=args.out)

    outputs = [
        f"{args.prefix}_base.stl",
        f"{args.prefix}_lid.stl",
        f"{args.prefix}_base.step",
        f"{args.prefix}_lid.step",
        f"{args.prefix}.step",
    ]
    print("Export complete:")
    for name in outputs:
        print(f"  - {args.out / name}")


if __name__ == "__main__":
    main()
