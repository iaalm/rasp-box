#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import zero2w_billboard_case as model


def load_overrides(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("params JSON must be an object")
    return data


def merged_params(overrides: dict | None) -> dict:
    p = dict(model.PARAMS)
    if overrides:
        bad = [k for k in overrides if k not in p]
        if bad:
            raise ValueError(f"Unknown PARAMS keys: {', '.join(sorted(bad))}")
        p.update(overrides)
    return p


def main() -> None:
    parser = argparse.ArgumentParser(description="Export billboard case STL/STEP")
    parser.add_argument("--prefix", default="zero2w_billboard_case")
    parser.add_argument("--params", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "exports")
    args = parser.parse_args()

    overrides = load_overrides(args.params) if args.params else None
    p = merged_params(overrides)
    model.export_all(prefix=args.prefix, p=p, output_dir=args.out)

    files = [
        f"{args.prefix}_body.stl",
        f"{args.prefix}_lid.stl",
        f"{args.prefix}_body.step",
        f"{args.prefix}_lid.step",
        f"{args.prefix}.step",
    ]
    print("Export complete:")
    for f in files:
        print(f"  - {args.out / f}")


if __name__ == "__main__":
    main()
